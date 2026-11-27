from django.db.models import ProtectedError
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from apps.accounts.permissions import ModulePermission
from .models import audit


class TenantViewSet(viewsets.ModelViewSet):
    """Scopes every query to the user's company and (when restricted) branch.
    Rejects references to records of another company and audits every write."""
    permission_classes = [ModulePermission]
    module = ""
    branch_scoped = True

    def get_queryset(self):
        u = self.request.user
        qs = super().get_queryset().filter(company_id=u.company_id)
        if self.branch_scoped and not u.all_branches:
            qs = qs.filter(branch_id=u.branch_id)
        return qs

    def _check_refs(self, serializer):
        cid = self.request.user.company_id
        for k, v in serializer.validated_data.items():
            if hasattr(v, "_meta") and getattr(v, "company_id", cid) != cid:
                raise ValidationError({k: "Invalid reference"})

    def perform_create(self, serializer):
        u = self.request.user
        self._check_refs(serializer)
        extra = {"company_id": u.company_id, "created_by": u}
        if self.branch_scoped:
            if not u.all_branches:
                extra["branch_id"] = u.branch_id
            elif "branch" not in serializer.validated_data and u.branch_id:
                extra["branch_id"] = u.branch_id
        obj = serializer.save(**extra)
        audit(u, "create", obj)

    def perform_update(self, serializer):
        u = self.request.user
        self._check_refs(serializer)
        extra = {}
        if self.branch_scoped and not u.all_branches:
            extra["branch_id"] = u.branch_id
        obj = serializer.save(**extra)
        audit(u, "update", obj)

    def perform_destroy(self, instance):
        try:
            audit(self.request.user, "delete", instance)
            instance.delete()
        except ProtectedError:
            raise ValidationError("Cannot delete: this record is used by other transactions.")
