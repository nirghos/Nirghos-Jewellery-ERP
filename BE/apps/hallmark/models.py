from django.db import models
from apps.core.models import TenantScoped, TimeStamped


class AHCCentre(TenantScoped):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    charge_per_piece = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["name"]
        verbose_name = "AHC centre"

    def __str__(self):
        return self.name


class HallmarkRequest(TenantScoped):
    number = models.CharField(max_length=30)
    centre = models.ForeignKey(AHCCentre, on_delete=models.PROTECT, related_name="requests")
    status = models.CharField(max_length=12, default="created")  # created, dispatched, received
    dispatched_on = models.DateField(null=True, blank=True)
    received_on = models.DateField(null=True, blank=True)
    total_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        unique_together = [("company", "number")]
        ordering = ["-created_at"]


class HallmarkItem(TimeStamped):
    request = models.ForeignKey(HallmarkRequest, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="+")
    huid = models.CharField(max_length=6, blank=True)
    result = models.CharField(max_length=8, default="pending")  # pending, pass, fail
    remarks = models.CharField(max_length=200, blank=True)
