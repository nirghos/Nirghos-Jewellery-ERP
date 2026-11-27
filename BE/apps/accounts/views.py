from rest_framework.decorators import api_view
from rest_framework.response import Response
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
