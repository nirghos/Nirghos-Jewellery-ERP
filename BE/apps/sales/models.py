from django.db import models
from apps.core.models import TenantScoped, TimeStamped


class Invoice(TenantScoped):
    class Status(models.TextChoices):
        POSTED = "posted", "Posted"
        CANCELLED = "cancelled", "Cancelled"

    number = models.CharField(max_length=30)
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.POSTED)
    metal_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    making_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    stone_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    hallmark_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    old_gold_adjustment = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    taxable_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cancel_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = [("company", "number")]
        ordering = ["-created_at"]

    @property
    def balance(self):
        return self.grand_total - self.paid


class InvoiceItem(TimeStamped):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT)
    rate_per_gram = models.DecimalField(max_digits=12, decimal_places=2)
    net_weight = models.DecimalField(max_digits=10, decimal_places=3)
    metal_value = models.DecimalField(max_digits=14, decimal_places=2)
    wastage_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    making_value = models.DecimalField(max_digits=14, decimal_places=2)
    stone_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=14, decimal_places=2)


class Payment(TimeStamped):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    method = models.CharField(max_length=10, choices=[("cash", "Cash"), ("upi", "UPI"), ("card", "Card"), ("bank", "Bank")])
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reference = models.CharField(max_length=60, blank=True)
