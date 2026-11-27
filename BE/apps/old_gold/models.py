from django.db import models
from apps.core.models import TenantScoped


class MeltingBatch(TenantScoped):
    number = models.CharField(max_length=30)
    date = models.DateField()
    input_gross = models.DecimalField(max_digits=12, decimal_places=3)
    input_fine = models.DecimalField(max_digits=12, decimal_places=3)
    recovered_gross = models.DecimalField(max_digits=12, decimal_places=3)
    recovered_purity = models.DecimalField(max_digits=5, decimal_places=3)
    recovered_fine = models.DecimalField(max_digits=12, decimal_places=3)
    loss_fine = models.DecimalField(max_digits=12, decimal_places=3)

    class Meta:
        unique_together = [("company", "number")]
        ordering = ["-date", "-created_at"]


class OldGoldReceipt(TenantScoped):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        EXCHANGED = "exchanged", "Exchanged"
        MELTED = "melted", "Melted"
        CANCELLED = "cancelled", "Cancelled"

    number = models.CharField(max_length=30)
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, null=True, blank=True)
    customer_name = models.CharField(max_length=200, blank=True)
    gross_weight = models.DecimalField(max_digits=12, decimal_places=3)
    stone_weight = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    net_weight = models.DecimalField(max_digits=12, decimal_places=3)
    touch = models.DecimalField(max_digits=5, decimal_places=3)           # tested purity (fineness)
    fine_weight = models.DecimalField(max_digits=12, decimal_places=3)
    test_method = models.CharField(max_length=20, default="touchstone")  # touchstone / xrf / fire_assay
    rate_per_gram = models.DecimalField(max_digits=12, decimal_places=2)  # rate of 24K fine gold
    deduction_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    value = models.DecimalField(max_digits=14, decimal_places=2)
    payout = models.CharField(max_length=10, choices=[("exchange", "Exchange"), ("cash", "Cash")], default="exchange")
    kyc_id_type = models.CharField(max_length=20, blank=True)
    kyc_id_number = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RECEIVED)
    exchange_invoice = models.ForeignKey("sales.Invoice", on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name="old_gold_receipts")
    melting_batch = models.ForeignKey(MeltingBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name="receipts")
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        unique_together = [("company", "number")]
        ordering = ["-created_at"]
