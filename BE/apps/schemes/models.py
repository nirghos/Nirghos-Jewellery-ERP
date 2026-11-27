from django.db import models
from apps.core.models import TenantScoped, TimeStamped


class SchemePlan(TenantScoped):
    name = models.CharField(max_length=120)
    months = models.PositiveIntegerField(default=11)
    monthly_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    flexible = models.BooleanField(default=False)  # any amount each month
    bonus_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # added by the shop on maturity
    terms = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]


class SchemeMember(TenantScoped):
    number = models.CharField(max_length=30)
    plan = models.ForeignKey(SchemePlan, on_delete=models.PROTECT, related_name="members")
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="schemes")
    start_date = models.DateField()
    status = models.CharField(max_length=10, default="active")  # active, redeemed, refunded
    redeemed_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    closed_on = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = [("company", "number")]
        ordering = ["-created_at"]


class Installment(TimeStamped):
    member = models.ForeignKey(SchemeMember, on_delete=models.CASCADE, related_name="installments")
    seq = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_on = models.DateField()
    method = models.CharField(max_length=10, default="cash")
    receipt_no = models.CharField(max_length=30)

    class Meta:
        ordering = ["seq"]
        unique_together = [("member", "seq")]
