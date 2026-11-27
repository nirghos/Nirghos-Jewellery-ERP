from decimal import Decimal
from django.db import models
from apps.core.models import TenantScoped


class Karigar(TenantScoped):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    skill = models.CharField(max_length=80, blank=True)
    allowed_wastage_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1.50"))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class JobCard(TenantScoped):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    number = models.CharField(max_length=30)
    karigar = models.ForeignKey(Karigar, on_delete=models.PROTECT, related_name="jobcards")
    description = models.CharField(max_length=300)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    labour_charge = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    issued_fine = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    returned_fine = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    wastage_fine = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    allowed_wastage = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    excess_wastage = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("company", "number")]
        ordering = ["-created_at"]


class MetalTxn(TenantScoped):
    class Kind(models.TextChoices):
        ISSUE = "issue", "Metal issued"
        RETURN = "return", "Metal returned"
        SCRAP = "scrap", "Scrap returned"
        FINISHED = "finished", "Finished jewellery received"

    karigar = models.ForeignKey(Karigar, on_delete=models.PROTECT, related_name="txns")
    jobcard = models.ForeignKey(JobCard, on_delete=models.PROTECT, related_name="txns")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    metal = models.CharField(max_length=20, default="gold")
    purity = models.DecimalField(max_digits=5, decimal_places=3)
    gross_weight = models.DecimalField(max_digits=12, decimal_places=3)
    fine_weight = models.DecimalField(max_digits=12, decimal_places=3)
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    approved_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-created_at"]


class KarigarPayment(TenantScoped):
    karigar = models.ForeignKey(Karigar, on_delete=models.PROTECT, related_name="payments")
    date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=10, choices=[("cash", "Cash"), ("bank", "Bank"), ("upi", "UPI")])
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-date", "-created_at"]
