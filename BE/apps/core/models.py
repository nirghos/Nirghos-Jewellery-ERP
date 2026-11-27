import uuid
from django.conf import settings
from django.db import models


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
