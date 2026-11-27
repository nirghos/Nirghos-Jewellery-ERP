from django.db.models import ProtectedError
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from apps.accounts.permissions import ModulePermission


class TenantViewSet(viewsets.ModelViewSet):
    """Scopes every query to the user's company and (when restricted) branch."""
    permission_classes = [ModulePermission]
    module = ""
    branch_scoped = True

    def get_queryset(self):
        u = self.request.user
        qs = super().get_queryset().filter(company_id=u.company_id)
        if self.branch_scoped and not u.all_branches:
            qs = qs.filter(branch_id=u.branch_id)
        return qs

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError("Cannot delete: this record is used by other transactions.")

    def perform_create(self, serializer):
        u = self.request.user
        extra = {"company_id": u.company_id, "created_by": u}
        if self.branch_scoped and not u.all_branches:
            extra["branch_id"] = u.branch_id
        serializer.save(**extra)
