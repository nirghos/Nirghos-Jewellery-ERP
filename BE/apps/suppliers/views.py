from rest_framework import serializers
from apps.core.views import TenantViewSet
from .models import Supplier


class SupplierSer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        exclude = ["company", "branch", "created_by"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SupplierViewSet(TenantViewSet):
    module = "suppliers"
    branch_scoped = False
    queryset = Supplier.objects.all()
    serializer_class = SupplierSer
    search_fields = ["name", "phone", "gstin"]
