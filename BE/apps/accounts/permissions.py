from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import Role as R

# module -> role -> allowed actions. Enforced server-side.
FULL = {"view", "create", "edit", "delete", "approve", "export"}
RW = {"view", "create", "edit", "export"}
RWA = RW | {"approve"}
RO = {"view", "export"}
VC = {"view", "create"}


def _m(**kw):
    return {R(k): v for k, v in kw.items()}


MATRIX = {
    "customers": _m(owner=FULL, branch_manager=RW, sales_manager=RW, sales_staff=VC, accountant=RO, auditor=RO),
    "suppliers": _m(owner=FULL, branch_manager=RW, purchase_manager=RW, accountant=RO, auditor=RO),
    "products": _m(owner=FULL, branch_manager=RW, stock_manager=RW, purchase_manager=RW, sales_manager=RO,
                   sales_staff={"view"}, accountant=RO, auditor=RO),
    "sales": _m(owner=FULL, branch_manager=RWA, sales_manager=RW, sales_staff=VC, accountant=RO, auditor=RO),
    "purchases": _m(owner=FULL, branch_manager=RW, purchase_manager=RWA, stock_manager=RO, accountant=RO, auditor=RO),
    "karigars": _m(owner=FULL, branch_manager=RW, karigar_manager=RWA, stock_manager=RO, accountant=RO, auditor=RO),
    "manufacturing": _m(owner=FULL, branch_manager=RW, karigar_manager=RWA, stock_manager=RO, auditor=RO),
    "repairs": _m(owner=FULL, branch_manager=RW, sales_manager=RW, sales_staff=VC | {"edit"}, karigar_manager=RW, auditor=RO),
    "old_gold": _m(owner=FULL, branch_manager=RWA, sales_manager=RW, sales_staff=VC, accountant=RO, auditor=RO),
    "diamonds": _m(owner=FULL, branch_manager=RW, stock_manager=RW, sales_manager=RO, sales_staff={"view"}, auditor=RO),
    "hallmark": _m(owner=FULL, branch_manager=RW, stock_manager=RW, auditor=RO),
    "schemes": _m(owner=FULL, branch_manager=RW, sales_manager=RW, sales_staff=VC, accountant=RO, auditor=RO),
    "accounting": _m(owner=FULL, accountant=FULL, branch_manager=RO, auditor=RO),
    "gst": _m(owner=FULL, accountant=FULL, auditor=RO),
    "hr": _m(owner=FULL, hr_manager=FULL, branch_manager=RO, auditor=RO),
    "reports": _m(owner=FULL, branch_manager=RO, accountant=RO, auditor=RO, sales_manager=RO, stock_manager=RO),
    "company": _m(owner=FULL, branch_manager=RO, accountant=RO, auditor=RO),
    "users": _m(owner=FULL, hr_manager=RO, auditor=RO),
    "dashboard": _m(owner=FULL, branch_manager=RO, accountant=RO, sales_manager=RO, sales_staff=RO,
                    stock_manager=RO, purchase_manager=RO, karigar_manager=RO, hr_manager=RO, auditor=RO),
}
SENSITIVE_FIELDS_ROLES = {R.SUPER_ADMIN, R.OWNER, R.ACCOUNTANT, R.BRANCH_MANAGER, R.PURCHASE_MANAGER, R.AUDITOR}


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
        if u.is_superuser or u.role == R.SUPER_ADMIN:
            return True
        allowed = MATRIX.get(getattr(view, "module", ""), {}).get(u.role, set())
        act = action_for(request, view)
        # views may declare per-action overrides, e.g. {"cancel": "approve"}
        act = getattr(view, "perm_map", {}).get(getattr(view, "action", None), act)
        return act in allowed
