"""Tiny factory so simple masters/registers need no boilerplate."""
from rest_framework import serializers
from rest_framework.routers import DefaultRouter
from .views import TenantViewSet

_RO = ["id", "created_at", "updated_at"]


def serializer_for(model, *, readonly=(), exclude=(), branch_scoped=True, extra=None, validators=None):
    ex = ["company", "created_by", *exclude]
    if not branch_scoped and "branch" not in ex:
        ex.append("branch")
    meta = type("Meta", (), {"model": model, "exclude": ex, "read_only_fields": [*_RO, *readonly]})
    attrs = {"Meta": meta, **(extra or {})}
    attrs.update(validators or {})
    return type(f"{model.__name__}Ser", (serializers.ModelSerializer,), attrs)


def viewset_for(model, module, *, search=(), filters=(), ordering=None, branch_scoped=True, readonly=(),
                exclude=(), select=(), ser=None, no_delete=False, **extra):
    attrs = {
        "module": module, "branch_scoped": branch_scoped,
        "queryset": model.objects.select_related(*select) if select else model.objects.all(),
        "serializer_class": ser or serializer_for(model, readonly=readonly, exclude=exclude, branch_scoped=branch_scoped),
        "search_fields": list(search), "filterset_fields": list(filters),
    }
    if ordering:
        attrs["ordering"] = ordering
    if no_delete:
        attrs["http_method_names"] = ["get", "post", "put", "patch", "head", "options"]
    attrs.update(extra)
    return type(f"{model.__name__}ViewSet", (TenantViewSet,), attrs)


def router_for(*regs):
    r = DefaultRouter()
    for prefix, vs in regs:
        r.register(prefix, vs, basename=prefix.replace("/", "-"))
    return r.urls
