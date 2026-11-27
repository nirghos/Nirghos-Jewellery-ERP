from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import Role

# module -> role -> allowed actions. Enforced server-side.
FULL = {"view", "create", "edit", "delete", "approve", "export"}
RW = {"view", "create", "edit", "export"}
RO = {"view", "export"}
MATRIX = {
    "customers": {Role.OWNER: FULL, Role.BRANCH_MANAGER: RW, Role.SALES_MANAGER: RW, Role.SALES_STAFF: {"view", "create"}, Role.ACCOUNTANT: RO, Role.AUDITOR: RO},
    "suppliers": {Role.OWNER: FULL, Role.BRANCH_MANAGER: RW, Role.PURCHASE_MANAGER: RW, Role.ACCOUNTANT: RO, Role.AUDITOR: RO},
    "products": {Role.OWNER: FULL, Role.BRANCH_MANAGER: RW, Role.STOCK_MANAGER: RW, Role.PURCHASE_MANAGER: RW,
                 Role.SALES_MANAGER: RO, Role.SALES_STAFF: {"view"}, Role.ACCOUNTANT: RO, Role.AUDITOR: RO},
    "sales": {Role.OWNER: FULL, Role.BRANCH_MANAGER: RW | {"approve"}, Role.SALES_MANAGER: RW, Role.SALES_STAFF: {"view", "create"},
              Role.ACCOUNTANT: RO, Role.AUDITOR: RO},
    "company": {Role.OWNER: FULL, Role.BRANCH_MANAGER: RO, Role.ACCOUNTANT: RO, Role.AUDITOR: RO},
    "dashboard": {Role.OWNER: FULL, Role.BRANCH_MANAGER: RO, Role.ACCOUNTANT: RO, Role.SALES_MANAGER: RO,
                  Role.SALES_STAFF: RO, Role.STOCK_MANAGER: RO, Role.AUDITOR: RO},
}
SENSITIVE_FIELDS_ROLES = {Role.SUPER_ADMIN, Role.OWNER, Role.ACCOUNTANT, Role.BRANCH_MANAGER, Role.PURCHASE_MANAGER, Role.AUDITOR}


def can_see_cost(user):
    return user.is_superuser or user.role in SENSITIVE_FIELDS_ROLES


def action_for(request, view):
    if request.method in SAFE_METHODS:
        return "view"
    if request.method == "POST":
        return getattr(view, "action_name", None) or "create"
    if request.method == "DELETE":
        return "delete"
    return "edit"


class ModulePermission(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        if not u.is_authenticated:
            return False
        if u.is_superuser or u.role == Role.SUPER_ADMIN:
            return True
        allowed = MATRIX.get(getattr(view, "module", ""), {}).get(u.role, set())
        return action_for(request, view) in allowed
