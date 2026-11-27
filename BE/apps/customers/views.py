from rest_framework import serializers
from apps.core.views import TenantViewSet
from .models import Customer


class CustomerSer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        exclude = ["company", "branch", "created_by"]
        read_only_fields = ["id", "created_at", "updated_at", "loyalty_points"]


class CustomerViewSet(TenantViewSet):
    module = "customers"
    branch_scoped = False
    queryset = Customer.objects.all()
    serializer_class = CustomerSer
    search_fields = ["name", "phone", "email", "gstin"]
    filterset_fields = ["is_vip"]
