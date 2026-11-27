from decimal import Decimal
from django.db import models
from apps.core.models import TenantScoped, TimeStamped


class Account(TenantScoped):
    class Type(models.TextChoices):
        ASSET = "asset", "Asset"
        LIABILITY = "liability", "Liability"
        EQUITY = "equity", "Equity"
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"

    code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=Type.choices)
    is_system = models.BooleanField(default=False)

    class Meta:
        unique_together = [("company", "code")]
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"


class JournalEntry(TenantScoped):
    number = models.CharField(max_length=30)
    date = models.DateField()
    kind = models.CharField(max_length=20, default="journal")  # journal/receipt/payment/contra/expense/income/sale/purchase...
    narration = models.CharField(max_length=300, blank=True)
    reference = models.CharField(max_length=60, blank=True)
    reverses = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversed_by")

    class Meta:
        unique_together = [("company", "number")]
        ordering = ["-date", "-created_at"]
        verbose_name_plural = "journal entries"


class JournalLine(TimeStamped):
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="lines")
    debit = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    credit = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    party = models.CharField(max_length=80, blank=True)  # e.g. "customer:<id>" for sub-ledgers

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(debit__gte=0) & models.Q(credit__gte=0), name="nonneg_dc")]
