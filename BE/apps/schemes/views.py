from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounting import services as acc
from apps.core import jewellery as J
from apps.core.crud import viewset_for
from apps.core.models import audit, next_number
from .models import Installment, SchemeMember, SchemePlan

D = Decimal
PlanViewSet = viewset_for(SchemePlan, "schemes", search=["name"], filters=["is_active"], branch_scoped=False)


class InstSer(serializers.ModelSerializer):
    class Meta:
        model = Installment
        fields = ["seq", "amount", "paid_on", "method", "receipt_no"]


class MemberSer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    installments = InstSer(many=True, read_only=True)
    paid_total = serializers.SerializerMethodField()
    paid_count = serializers.SerializerMethodField()
    matured = serializers.SerializerMethodField()
    maturity_value = serializers.SerializerMethodField()
    missed = serializers.SerializerMethodField()

    class Meta:
        model = SchemeMember
        fields = ["id", "number", "plan", "plan_name", "customer", "customer_name", "start_date", "status",
                  "redeemed_value", "closed_on", "paid_total", "paid_count", "matured", "maturity_value", "missed",
                  "installments", "created_at"]
        read_only_fields = ["id", "number", "status", "redeemed_value", "closed_on", "created_at"]

    def _paid(self, o):
        return sum((i.amount for i in o.installments.all()), D(0))

    def get_paid_total(self, o): return self._paid(o)
    def get_paid_count(self, o): return len(o.installments.all())
    def get_matured(self, o): return len(o.installments.all()) >= o.plan.months

    def get_maturity_value(self, o):
        return self._paid(o) + (o.plan.bonus_amount if len(o.installments.all()) >= o.plan.months else D(0))

    def get_missed(self, o):
        if o.status != "active":
            return 0
        t = timezone.localdate()
        due = (t.year - o.start_date.year) * 12 + t.month - o.start_date.month + 1
        return max(min(due, o.plan.months) - len(o.installments.all()), 0)


class MemberViewSet(viewset_for(SchemeMember, "schemes", search=["number", "customer__name", "customer__phone"],
                                filters=["status", "plan"], select=["plan", "customer"], ser=MemberSer, no_delete=True)):
    perm_map = {"pay": "create", "redeem": "approve", "refund": "approve"}

    def get_queryset(self):
        return super().get_queryset().prefetch_related("installments")

    def perform_create(self, s):
        u = self.request.user
        self._check_refs(s)
        if not s.validated_data["plan"].is_active:
            raise ValidationError({"plan": "Plan is not active"})
        m = s.save(company=u.company, branch=u.branch, created_by=u, number=next_number(u.company, "sch", "SCH"))
        audit(u, "create", m)

    def _m(self):
        return SchemeMember.objects.select_for_update().select_related("plan").get(pk=self.get_object().pk)

    def _out(self, m):
        m = SchemeMember.objects.select_related("plan", "customer").prefetch_related("installments").get(pk=m.pk)
        return Response(MemberSer(m).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def pay(self, request, pk=None):
        m, u = self._m(), request.user
        if m.status != "active":
            raise ValidationError("Scheme is closed")
        seq = m.installments.count() + 1
        if seq > m.plan.months:
            raise ValidationError("All installments are already paid")
        amt = J.q2(request.data.get("amount") or m.plan.monthly_amount)
        method = request.data.get("method", "cash")
        if method not in acc.METHOD_ACCOUNT:
            raise ValidationError("Invalid method")
        if amt <= 0 or (not m.plan.flexible and amt != m.plan.monthly_amount):
            raise ValidationError(f"Installment must be {m.plan.monthly_amount}" if not m.plan.flexible else "Invalid amount")
        rc = next_number(u.company, "rcpt", "RC")
        Installment.objects.create(member=m, seq=seq, amount=amt, paid_on=timezone.localdate(), method=method, receipt_no=rc)
        acc.post(company=u.company, branch=m.branch, user=u, kind="receipt", reference=rc,
                 narration=f"Scheme {m.number} installment {seq}",
                 lines=[(acc.METHOD_ACCOUNT[method], amt, 0), ("2200", 0, amt, f"customer:{m.customer_id}")])
        return self._out(m)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def redeem(self, request, pk=None):
        """Marks a matured scheme as redeemed. The value is then applied against jewellery in billing."""
        m = self._m()
        n = m.installments.count()
        if m.status != "active" or n < m.plan.months:
            raise ValidationError("Only matured, active schemes can be redeemed")
        paid = m.installments.aggregate(s=Sum("amount"))["s"] or D(0)
        m.redeemed_value, m.status, m.closed_on = paid + m.plan.bonus_amount, "redeemed", timezone.localdate()
        m.save()
        audit(request.user, "redeem", m)
        return self._out(m)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def refund(self, request, pk=None):
        """Early closure: refund the amount paid (no bonus) in cash."""
        m, u = self._m(), request.user
        if m.status != "active":
            raise ValidationError("Scheme is closed")
        paid = m.installments.aggregate(s=Sum("amount"))["s"] or D(0)
        if paid > 0:
            acc.post(company=u.company, branch=m.branch, user=u, kind="payment", reference=m.number,
                     narration=f"Scheme refund {m.number}",
                     lines=[("2200", paid, 0, f"customer:{m.customer_id}"), ("1000", 0, paid)])
        m.status, m.redeemed_value, m.closed_on = "refunded", paid, timezone.localdate()
        m.save()
        audit(u, "refund", m)
        return self._out(m)
