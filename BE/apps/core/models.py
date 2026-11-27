import uuid
from django.conf import settings
from django.db import models, transaction


class TimeStamped(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantScoped(TimeStamped):
    """Every business record carries company + branch context and an author."""
    company = models.ForeignKey("companies.Company", on_delete=models.PROTECT, related_name="+")
    branch = models.ForeignKey("companies.Branch", on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        abstract = True


class Sequence(models.Model):
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="+")
    key = models.CharField(max_length=30)
    value = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("company", "key")]


def next_number(company, key, prefix=None):
    """Race-safe document numbering (call inside transaction.atomic)."""
    with transaction.atomic():
        s, _ = Sequence.objects.select_for_update().get_or_create(company=company, key=key)
        s.value += 1
        s.save(update_fields=["value"])
    return f"{prefix or key.upper()}-{s.value:05d}"


class AuditLog(TimeStamped):
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="+")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    action = models.CharField(max_length=20)
    model = models.CharField(max_length=60)
    object_id = models.CharField(max_length=64, blank=True)
    summary = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]


def audit(user, action, obj=None, summary="", model=None):
    AuditLog.objects.create(
        company_id=user.company_id, user=user, action=action,
        model=model or (obj._meta.label if obj is not None else ""),
        object_id=str(getattr(obj, "pk", "") or ""), summary=(summary or (str(obj) if obj is not None else ""))[:300])
