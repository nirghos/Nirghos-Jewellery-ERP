from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounting import services as acc
from apps.core import jewellery as J
from apps.core.crud import viewset_for
from apps.core.models import audit, next_number
from .models import FLOW, RepairJob, RepairLog

D = Decimal
METHODS = ["cash", "upi", "card", "bank"]


class LogSer(serializers.ModelSerializer):
    class Meta:
        model = RepairLog
        fields = ["status", "note", "created_at"]


class RepairSer(serializers.ModelSerializer):
    logs = LogSer(many=True, read_only=True)
    balance = serializers.SerializerMethodField()

    class Meta:
        model = RepairJob
        fields = ["id", "number", "customer", "customer_name", "customer_phone", "kind", "item_description", "weight_in",
                  "problem", "status", "estimate", "advance", "final_charges", "balance", "karigar", "due_date",
                  "delivered_at", "notes", "logs", "created_at"]
        read_only_fields = ["id", "number", "status", "estimate", "advance", "final_charges", "delivered_at", "logs", "created_at"]

    def get_balance(self, o):
        return (o.final_charges or o.estimate) - o.advance


class RepairViewSet(viewset_for(RepairJob, "repairs", search=["number", "customer_name", "customer_phone", "item_description"],
                                filters=["status", "kind"], select=["customer"], ser=RepairSer, no_delete=True)):
    perm_map = {"set_status": "edit", "estimate": "edit", "take_advance": "create", "deliver": "approve"}

    def perform_create(self, s):
        u = self.request.user
        self._check_refs(s)
        o = s.save(company=u.company, branch=u.branch, created_by=u, number=next_number(u.company, "rep", "REP"))
        RepairLog.objects.create(job=o, status="received", note="Received", by=u)
        audit(u, "create", o)

    def _job(self):
        return RepairJob.objects.select_for_update().get(pk=self.get_object().pk)

    @action(detail=True, methods=["post"], url_path="set-status")
    @transaction.atomic
    def set_status(self, request, pk=None):
        o = self._job()
        new = request.data.get("status")
        if o.status in ("delivered", "cancelled"):
            raise ValidationError("Job is closed")
        if new == "cancelled":
            if o.advance:
                raise ValidationError("Refund the advance before cancelling")
        elif new in ("delivered",):
            raise ValidationError("Use the deliver action")
        elif new not in FLOW or FLOW.index(new) != FLOW.index(o.status) + 1:
            raise ValidationError(f"Next status after '{o.status}' is '{FLOW[FLOW.index(o.status) + 1]}'")
        elif new == "approved" and not o.estimate:
            raise ValidationError("Set an estimate before customer approval")
        o.status = new
        o.save(update_fields=["status", "updated_at"])
        RepairLog.objects.create(job=o, status=new, note=str(request.data.get("note", ""))[:300], by=request.user)
        return Response(RepairSer(o).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def estimate(self, request, pk=None):
        o = self._job()
        if o.status not in ("received", "inspection", "estimated"):
            raise ValidationError("Estimate can only be changed before approval")
        amt = J.q2(request.data.get("amount") or 0)
        if amt <= 0:
            raise ValidationError({"amount": "Must be positive"})
        o.estimate, o.status = amt, "estimated"
        o.save(update_fields=["estimate", "status", "updated_at"])
        RepairLog.objects.create(job=o, status="estimated", note=f"Estimate {amt}", by=request.user)
        return Response(RepairSer(o).data)

    @action(detail=True, methods=["post"], url_path="advance")
    @transaction.atomic
    def take_advance(self, request, pk=None):
        o, u = self._job(), request.user
        method = request.data.get("method", "cash")
        amt = J.q2(request.data.get("amount") or 0)
        if method not in METHODS or amt <= 0:
            raise ValidationError("Valid amount and method required")
        if o.status in ("delivered", "cancelled"):
            raise ValidationError("Job is closed")
        o.advance += amt
        o.save(update_fields=["advance", "updated_at"])
        acc.post(company=o.company, branch=o.branch, user=u, kind="receipt", reference=o.number,
                 narration=f"Advance {o.number}", lines=[(acc.METHOD_ACCOUNT[method], amt, 0), ("2200", 0, amt,
                                                         f"customer:{o.customer_id}" if o.customer_id else "")])
        return Response(RepairSer(o).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def deliver(self, request, pk=None):
        o, u = self._job(), request.user
        if o.status != "ready":
            raise ValidationError("Job must be 'ready' before delivery")
        final = J.q2(request.data.get("final_charges") or o.estimate)
        paid = J.q2(request.data.get("amount_paid") or 0)
        method = request.data.get("method", "cash")
        if final <= 0 or paid < 0 or method not in METHODS:
            raise ValidationError("Invalid charges / payment")
        adv_used = min(o.advance, final)
        due = final - adv_used - paid
        if due < 0:
            raise ValidationError("Payment exceeds amount due")
        party = f"customer:{o.customer_id}" if o.customer_id else ""
        if due > 0 and not o.customer_id:
            raise ValidationError("Link a customer to deliver with a pending balance")
        lines = [("2200", adv_used, 0, party), (acc.METHOD_ACCOUNT[method], paid, 0), ("1100", due, 0, party),
                 ("4100", 0, final)]
        if o.advance > adv_used:   # advance exceeded final charges -> refund excess in cash
            refund = o.advance - adv_used
            lines += [("2200", refund, 0, party), ("1000", 0, refund)]
        acc.post(company=o.company, branch=o.branch, user=u, kind="repair", reference=o.number,
                 narration=f"Repair delivered {o.number}", lines=lines)
        o.final_charges, o.status, o.delivered_at = final, "delivered", timezone.now()
        o.save()
        RepairLog.objects.create(job=o, status="delivered", note=f"Charges {final}, paid {paid}, due {due}", by=u)
        audit(u, "deliver", o)
        return Response(RepairSer(o).data)
