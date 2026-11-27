from decimal import Decimal
from django.conf import settings
from django.db import models
from apps.core import jewellery as J
from apps.core.models import TenantScoped, TimeStamped


class Metal(models.TextChoices):
    GOLD = "gold", "Gold"
    SILVER = "silver", "Silver"
    PLATINUM = "platinum", "Platinum"
    DIAMOND = "diamond", "Diamond"
    GEMSTONE = "gemstone", "Gemstone"


class Category(TenantScoped):
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = [("company", "name")]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class MetalRate(TenantScoped):
    """Rate per gram for a metal at a purity (fineness)."""
    metal = models.CharField(max_length=20, choices=Metal.choices)
    purity = models.DecimalField(max_digits=5, decimal_places=3)
    rate_per_gram = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["-created_at"]


class Product(TenantScoped):
    """One row per individual article (piece-wise tracking)."""

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        SOLD = "sold", "Sold"
        RESERVED = "reserved", "Reserved"
        DAMAGED = "damaged", "Damaged"
        IN_TRANSIT = "in_transit", "In transit"
        VOID = "void", "Void"

    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50)
    barcode = models.CharField(max_length=60)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, null=True, blank=True, related_name="products")
    metal = models.CharField(max_length=20, choices=Metal.choices, default=Metal.GOLD)
    purity = models.DecimalField(max_digits=5, decimal_places=3, default=Decimal("0.916"))
    gross_weight = models.DecimalField(max_digits=10, decimal_places=3)
    stone_weight = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    net_weight = models.DecimalField(max_digits=10, decimal_places=3, editable=False)
    fine_weight = models.DecimalField(max_digits=10, decimal_places=3, editable=False)
    making_type = models.CharField(
        max_length=10, default="per_gram",
        choices=[("per_gram", "Per gram"), ("percent", "Percent"), ("fixed", "Fixed")])
    making_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    wastage_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    stone_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    huid = models.CharField(max_length=6, blank=True)
    purchase_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.SET_NULL, null=True, blank=True)
    rack = models.CharField(max_length=30, blank=True)
    image = models.ImageField(upload_to="products/", blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.AVAILABLE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["company", "sku"], name="uniq_sku_company"),
            models.UniqueConstraint(fields=["company", "barcode"], name="uniq_barcode_company"),
        ]
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.net_weight = J.net_weight(self.gross_weight, self.stone_weight)
        self.fine_weight = J.fine_weight(self.net_weight, self.purity)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sku} {self.name}"


class StockMovement(TimeStamped):
    """Permanent, append-only stock history."""
    company = models.ForeignKey("companies.Company", on_delete=models.PROTECT, related_name="+")
    branch = models.ForeignKey("companies.Branch", on_delete=models.PROTECT, null=True, related_name="+")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="movements")
    kind = models.CharField(max_length=20)  # purchase, sale, sale_reversal, adjustment, transfer
    reference = models.CharField(max_length=60, blank=True)
    gross_weight = models.DecimalField(max_digits=10, decimal_places=3)
    fine_weight = models.DecimalField(max_digits=10, decimal_places=3)
    direction = models.SmallIntegerField()  # +1 in, -1 out
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        ordering = ["-created_at"]


class MetalLedger(TimeStamped):
    """Raw metal (bar/scrap/old gold) stock ledger. Signed weights; append-only."""
    company = models.ForeignKey("companies.Company", on_delete=models.PROTECT, related_name="+")
    branch = models.ForeignKey("companies.Branch", on_delete=models.PROTECT, null=True, related_name="+")
    metal = models.CharField(max_length=20, choices=Metal.choices)
    purity = models.DecimalField(max_digits=5, decimal_places=3)
    kind = models.CharField(max_length=20)  # purchase, karigar_issue, karigar_return, old_gold, melting, adjustment
    reference = models.CharField(max_length=60, blank=True)
    gross_weight = models.DecimalField(max_digits=12, decimal_places=3)
    fine_weight = models.DecimalField(max_digits=12, decimal_places=3)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        ordering = ["-created_at"]
