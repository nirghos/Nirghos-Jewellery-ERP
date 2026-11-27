from django.db import models
from apps.core.models import TenantScoped


class Employee(TenantScoped):
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    designation = models.CharField(max_length=80, blank=True)
    department = models.CharField(max_length=80, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("company", "code")]
        ordering = ["name"]


class Attendance(TenantScoped):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance")
    date = models.DateField()
    status = models.CharField(max_length=8, choices=[("present", "Present"), ("absent", "Absent"), ("half", "Half day"), ("leave", "Paid leave")])

    class Meta:
        unique_together = [("employee", "date")]
        ordering = ["-date"]


class Leave(TenantScoped):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leaves")
    from_date = models.DateField()
    to_date = models.DateField()
    kind = models.CharField(max_length=20, default="casual")
    reason = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, default="pending")  # pending, approved, rejected

    class Meta:
        ordering = ["-from_date"]


class Advance(TenantScoped):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="advances")
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    recovered = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["-date"]


class Payslip(TenantScoped):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="payslips")
    month = models.CharField(max_length=7)  # YYYY-MM
    days_in_month = models.PositiveSmallIntegerField()
    paid_days = models.DecimalField(max_digits=5, decimal_places=1)
    gross = models.DecimalField(max_digits=12, decimal_places=2)
    advance_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, default="generated")  # generated, paid

    class Meta:
        unique_together = [("employee", "month")]
        ordering = ["-month", "employee__name"]
