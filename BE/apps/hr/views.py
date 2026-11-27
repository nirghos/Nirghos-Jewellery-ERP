import calendar
import re
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounting import services as acc
from apps.accounts.permissions import ModulePermission
from apps.core import jewellery as J
from apps.core.crud import serializer_for, viewset_for
from apps.core.models import audit
from .models import Advance, Attendance, Employee, Leave, Payslip

D = Decimal

EmployeeViewSet = viewset_for(Employee, "hr", search=["name", "code", "designation", "department"],
                              filters=["is_active", "department"], branch_scoped=False)


class AttendanceSer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.name", read_only=True)

    class Meta:
        model = Attendance
        fields = ["id", "employee", "employee_name", "date", "status"]
        read_only_fields = ["id"]
        validators = []  # re-marking a day updates the record


class AttendanceViewSet(viewset_for(Attendance, "hr", filters=["employee", "date", "status"], select=["employee"],
                                    branch_scoped=False, ser=AttendanceSer)):
    def get_queryset(self):
        qs = super().get_queryset()
        m = self.request.query_params.get("month")
        if m and re.match(r"^\d{4}-\d{2}$", m):
            qs = qs.filter(date__year=m[:4], date__month=m[5:])
        return qs

    def perform_create(self, s):
        self._check_refs(s)
        u = self.request.user
        # one record per employee per day: mark again = update
        obj, _ = Attendance.objects.update_or_create(
            employee=s.validated_data["employee"], date=s.validated_data["date"],
            defaults={"status": s.validated_data["status"], "company_id": u.company_id, "created_by": u})
        s.instance = obj


class LeaveSer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.name", read_only=True)

    class Meta:
        model = Leave
        fields = ["id", "employee", "employee_name", "from_date", "to_date", "kind", "reason", "status"]
        read_only_fields = ["id", "status"]

    def validate(self, a):
        if a["to_date"] < a["from_date"]:
            raise serializers.ValidationError("to_date is before from_date")
        return a


class LeaveViewSet(viewset_for(Leave, "hr", filters=["employee", "status"], select=["employee"], branch_scoped=False,
                               ser=LeaveSer, no_delete=True)):
    perm_map = {"decide": "approve"}

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def decide(self, request, pk=None):
        lv = Leave.objects.select_for_update().get(pk=self.get_object().pk)
        st = request.data.get("status")
        if lv.status != "pending" or st not in ("approved", "rejected"):
            raise ValidationError("Only pending leave can be approved or rejected")
        lv.status = st
        lv.save(update_fields=["status", "updated_at"])
        if st == "approved":
            from datetime import timedelta
            d = lv.from_date
            while d <= lv.to_date:
                Attendance.objects.update_or_create(employee=lv.employee, date=d, defaults={
                    "status": "leave", "company_id": lv.company_id, "created_by": request.user})
                d += timedelta(days=1)
        audit(request.user, st, lv)
        return Response(LeaveSer(lv).data)


class AdvanceSer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.name", read_only=True)
    outstanding = serializers.SerializerMethodField()

    class Meta:
        model = Advance
        fields = ["id", "employee", "employee_name", "date", "amount", "recovered", "outstanding"]
        read_only_fields = ["id", "recovered"]

    def get_outstanding(self, o):
        return o.amount - o.recovered

    def validate_amount(self, v):
        if v <= 0:
            raise serializers.ValidationError("Must be positive")
        return v


class AdvanceViewSet(viewset_for(Advance, "hr", filters=["employee"], select=["employee"], branch_scoped=False,
                                 ser=AdvanceSer, no_delete=True)):
    @transaction.atomic
    def perform_create(self, s):
        super().perform_create(s)
        a, u = s.instance, self.request.user
        acc.post(company=u.company, branch=u.branch, user=u, kind="payment", reference=f"ADV-{str(a.id)[:8]}",
                 narration=f"Salary advance {a.employee.name}", lines=[("5300", a.amount, 0), ("1000", 0, a.amount)])


class SlipSer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.name", read_only=True)

    class Meta:
        model = Payslip
        fields = ["id", "employee", "employee_name", "month", "days_in_month", "paid_days", "gross", "advance_deduction",
                  "net", "status"]


class PayslipViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    module = "hr"
    permission_classes = [ModulePermission]
    serializer_class = SlipSer
    queryset = Payslip.objects.select_related("employee")
    filterset_fields = ["month", "status", "employee"]
    perm_map = {"generate": "create", "pay": "approve"}

    def get_queryset(self):
        return super().get_queryset().filter(company_id=self.request.user.company_id)

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def generate(self, request):
        """Body: {month: 'YYYY-MM'}. Salary = base x paid days / days in month. Existing slips are kept."""
        u, m = request.user, str(request.data.get("month", ""))
        if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", m):
            raise ValidationError("month must be YYYY-MM")
        y, mo = int(m[:4]), int(m[5:])
        dim = calendar.monthrange(y, mo)[1]
        made = 0
        for e in Employee.objects.filter(company=u.company, is_active=True):
            if Payslip.objects.filter(employee=e, month=m).exists():
                continue
            att = {a.status: 0 for a in []}
            for a in e.attendance.filter(date__year=y, date__month=mo):
                att[a.status] = att.get(a.status, 0) + 1
            paid = D(att.get("present", 0)) + D(att.get("leave", 0)) + D("0.5") * att.get("half", 0)
            gross = J.q2(e.base_salary * paid / D(dim))
            out = sum((a.amount - a.recovered for a in e.advances.all()), D(0))
            ded = min(out, gross)
            Payslip.objects.create(company=u.company, branch=u.branch, created_by=u, employee=e, month=m, days_in_month=dim,
                                   paid_days=paid, gross=gross, advance_deduction=ded, net=gross - ded)
            made += 1
        audit(u, "payroll", None, f"Generated {made} payslips for {m}", model="hr.Payslip")
        return Response({"generated": made})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def pay(self, request, pk=None):
        u = request.user
        p = Payslip.objects.select_for_update().select_related("employee").get(pk=self.get_object().pk)
        if p.status == "paid":
            raise ValidationError("Already paid")
        method = request.data.get("method", "bank")
        if method not in ("cash", "bank", "upi"):
            raise ValidationError("Invalid method")
        left = p.advance_deduction
        for a in p.employee.advances.select_for_update().order_by("date"):
            if left <= 0:
                break
            take = min(a.amount - a.recovered, left)
            if take > 0:
                a.recovered += take
                a.save(update_fields=["recovered", "updated_at"])
                left -= take
        if left > 0:
            raise ValidationError("Advance balance changed since payslip generation; regenerate")
        # Salary expense = gross; advance already expensed when given, so credit it back.
        lines = [("5300", p.net, 0), (acc.METHOD_ACCOUNT[method], 0, p.net)] if p.advance_deduction == 0 else \
                [("5300", p.gross - p.advance_deduction, 0), (acc.METHOD_ACCOUNT[method], 0, p.net)]
        if p.net > 0:
            acc.post(company=p.company, branch=p.branch, user=u, kind="payment", reference=f"SAL-{p.month}-{p.employee.code}",
                     narration=f"Salary {p.employee.name} {p.month}", lines=lines)
        p.status = "paid"
        p.save(update_fields=["status", "updated_at"])
        audit(u, "pay", p)
        return Response(SlipSer(p).data)
