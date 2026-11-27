from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.models import audit
from apps.accounts.permissions import ModulePermission
from .models import Role, User
from .permissions import MATRIX, can_see_cost


@api_view(["GET"])
def me(request):
    u = request.user
    full = u.is_superuser or u.role == "super_admin"
    perms = {m: sorted({"view", "create", "edit", "delete", "approve", "export"} if full else r.get(u.role, set()))
             for m, r in MATRIX.items()}
    return Response({
        "id": u.id, "username": u.username, "name": u.get_full_name() or u.username, "role": u.role,
        "company": u.company.name if u.company else None,
        "branch": {"id": u.branch_id, "name": u.branch.name} if u.branch else None,
        "all_branches": u.all_branches, "can_see_cost": can_see_cost(u), "permissions": perms,
    })


class UserSer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "phone", "role", "branch", "is_active", "password", "last_login"]
        read_only_fields = ["id", "last_login"]

    def validate_role(self, v):
        if v == Role.SUPER_ADMIN and not self.context["request"].user.is_superuser:
            raise serializers.ValidationError("Only a super admin can assign this role")
        return v

    def validate_branch(self, b):
        if b and b.company_id != self.context["request"].user.company_id:
            raise serializers.ValidationError("Invalid branch")
        return b

    def validate(self, a):
        req = self.context["request"].user
        if self.instance and self.instance.pk == req.pk:
            if "role" in a and a["role"] != req.role:
                raise serializers.ValidationError("You cannot change your own role")
            if a.get("is_active") is False:
                raise serializers.ValidationError("You cannot deactivate yourself")
        if not self.instance and not a.get("password"):
            raise serializers.ValidationError({"password": "Password is required"})
        if a.get("password"):
            validate_password(a["password"])
        role = a.get("role", getattr(self.instance, "role", None))
        if role not in (Role.OWNER, Role.SUPER_ADMIN, Role.ACCOUNTANT, Role.AUDITOR) and not a.get("branch", getattr(self.instance, "branch", None)):
            raise serializers.ValidationError({"branch": "A branch is required for this role"})
        return a

    def create(self, vd):
        pw = vd.pop("password")
        u = User(**vd, company=self.context["request"].user.company)
        u.set_password(pw)
        u.save()
        return u

    def update(self, inst, vd):
        pw = vd.pop("password", None)
        for k, v in vd.items():
            setattr(inst, k, v)
        if pw:
            inst.set_password(pw)
        inst.save()
        return inst


class UserViewSet(viewsets.ModelViewSet):
    module = "users"
    permission_classes = [ModulePermission]
    serializer_class = UserSer
    queryset = User.objects.all()
    search_fields = ["username", "first_name", "last_name", "email"]
    filterset_fields = ["role", "is_active", "branch"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return super().get_queryset().filter(company_id=self.request.user.company_id)

    def perform_create(self, s):
        audit(self.request.user, "create", s.save())

    def perform_update(self, s):
        audit(self.request.user, "update", s.save())
