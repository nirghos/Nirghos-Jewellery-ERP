from django.db import models
from apps.core.models import TenantScoped, TimeStamped


class PurchaseInvoice(TenantScoped):
    class Status(models.TextChoices):
        POSTED = "posted", "Posted"
        CANCELLED = "cancelled", "Cancelled"

    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.PROTECT, related_name="purchases")
    number = models.CharField(max_length=30)
    supplier_invoice_no = models.CharField(max_length=40, blank=True)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.POSTED)
    subtotal = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    paid = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        unique_together = [("company", "number")]
        ordering = ["-date", "-created_at"]

    @property
    def balance(self):
        return self.total - self.paid


class PurchaseItem(TimeStamped):
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name="items")
    kind = models.CharField(max_length=6, choices=[("piece", "Jewellery piece"), ("metal", "Raw metal")])
    metal = models.CharField(max_length=20, default="gold")
    purity = models.DecimalField(max_digits=5, decimal_places=3)
    gross_weight = models.DecimalField(max_digits=12, decimal_places=3)
    stone_weight = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    net_weight = models.DecimalField(max_digits=12, decimal_places=3)
    fine_weight = models.DecimalField(max_digits=12, decimal_places=3)
    rate_per_gram = models.DecimalField(max_digits=12, decimal_places=2)
    extra_charges = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    name = models.CharField(max_length=200, blank=True)
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, null=True, blank=True, related_name="+")


class SupplierPayment(TenantScoped):
    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.PROTECT, related_name="payments")
    date = models.DateField()
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    method = models.CharField(max_length=10, choices=[("cash", "Cash"), ("upi", "UPI"), ("bank", "Bank"), ("card", "Card")])
    reference = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["-date", "-created_at"]
