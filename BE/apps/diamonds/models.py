from django.db import models
from apps.core.models import TenantScoped


class Stone(TenantScoped):
    """Diamonds and gemstones are tracked in carats, never mixed with metal grams."""
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        ISSUED = "issued", "Issued to karigar"
        SET = "set", "Set in jewellery"
        SOLD = "sold", "Sold"

    kind = models.CharField(max_length=10, choices=[("diamond", "Diamond"), ("gemstone", "Gemstone")], default="diamond")
    stock_no = models.CharField(max_length=40)
    name = models.CharField(max_length=80, blank=True)          # e.g. Ruby, Emerald (gemstones)
    shape = models.CharField(max_length=30, blank=True)
    carat = models.DecimalField(max_digits=8, decimal_places=3)
    color = models.CharField(max_length=10, blank=True)
    clarity = models.CharField(max_length=10, blank=True)
    cut = models.CharField(max_length=20, blank=True)
    cert_no = models.CharField(max_length=40, blank=True)
    lab = models.CharField(max_length=40, blank=True)           # GIA, IGI, ...
    dimensions = models.CharField(max_length=60, blank=True)
    lot_no = models.CharField(max_length=40, blank=True)
    purchase_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.AVAILABLE)
    karigar = models.ForeignKey("karigars.Karigar", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    product = models.ForeignKey("products.Product", on_delete=models.SET_NULL, null=True, blank=True, related_name="stones")

    class Meta:
        unique_together = [("company", "stock_no")]
        ordering = ["-created_at"]
