from django.db import models
from apps.core.models import TenantScoped, TimeStamped

FLOW = ["received", "inspection", "estimated", "approved", "in_progress", "quality_check", "ready", "delivered"]


class RepairJob(TenantScoped):
    number = models.CharField(max_length=30)
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    kind = models.CharField(max_length=10, choices=[("repair", "Repair"), ("custom", "Custom order")], default="repair")
    item_description = models.CharField(max_length=300)
    weight_in = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    problem = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=15, default="received")
    estimate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    advance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    final_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    karigar = models.ForeignKey("karigars.Karigar", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    due_date = models.DateField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        unique_together = [("company", "number")]
        ordering = ["-created_at"]


class RepairLog(TimeStamped):
    job = models.ForeignKey(RepairJob, on_delete=models.CASCADE, related_name="logs")
    status = models.CharField(max_length=15)
    note = models.CharField(max_length=300, blank=True)
    by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        ordering = ["created_at"]
