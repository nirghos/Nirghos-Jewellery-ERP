from django.db import models
from apps.core.models import TenantScoped, TimeStamped

STAGES = ["planned", "melting", "casting", "cutting", "filing", "stone_setting", "polishing", "finishing",
          "quality_check", "completed"]


class Design(TenantScoped):
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    metal = models.CharField(max_length=20, default="gold")
    purity = models.DecimalField(max_digits=5, decimal_places=3, default=0.916)
    expected_weight = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    image = models.ImageField(upload_to="designs/", blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("company", "code")]
        ordering = ["code"]


class BOMItem(TimeStamped):
    design = models.ForeignKey(Design, on_delete=models.CASCADE, related_name="bom")
    material = models.CharField(max_length=120)
    metal = models.CharField(max_length=20, blank=True)
    purity = models.DecimalField(max_digits=5, decimal_places=3, default=0)
    weight = models.DecimalField(max_digits=10, decimal_places=3)
    unit = models.CharField(max_length=10, default="g")  # g for metal, ct for stones
    note = models.CharField(max_length=200, blank=True)


class ProductionOrder(TenantScoped):
    number = models.CharField(max_length=30)
    design = models.ForeignKey(Design, on_delete=models.PROTECT, related_name="orders")
    quantity = models.PositiveIntegerField(default=1)
    karigar = models.ForeignKey("karigars.Karigar", on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    jobcard = models.ForeignKey("karigars.JobCard", on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    stage = models.CharField(max_length=20, default="planned")
    due_date = models.DateField(null=True, blank=True)
    notes = models.CharField(max_length=300, blank=True)
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    production_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        unique_together = [("company", "number")]
        ordering = ["-created_at"]


class StageLog(TimeStamped):
    order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE, related_name="logs")
    stage = models.CharField(max_length=20)
    weight_in = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    weight_out = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)
    by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        ordering = ["created_at"]
