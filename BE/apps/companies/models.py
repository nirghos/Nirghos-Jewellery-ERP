from decimal import Decimal
from django.db import models
from apps.core.models import TimeStamped


class Company(TimeStamped):
    name = models.CharField(max_length=200)
    gstin = models.CharField(max_length=15, blank=True)
    pan = models.CharField(max_length=10, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    # GST is configuration, not hardcoded. Defaults must be confirmed by a CA.
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("3.00"))
    hsn_code = models.CharField(max_length=10, default="7113")
    state = models.CharField(max_length=40, blank=True)
    hallmark_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))

    class Meta:
        verbose_name_plural = "companies"

    def __str__(self): return self.name


class Branch(TimeStamped):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=10)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("company", "code")]
        verbose_name_plural = "branches"

    def __str__(self): return f"{self.name} ({self.code})"
