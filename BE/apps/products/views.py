from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.permissions import can_see_cost
from apps.core.views import TenantViewSet
from .models import Category, MetalRate, Product, StockMovement


class ProductSer(serializers.ModelSerializer):
    class Meta:
        model = Product
        exclude = ["company", "created_by"]
        read_only_fields = ["id", "net_weight", "fine_weight", "status", "created_at", "updated_at"]

    def validate(self, a):
        g = a.get("gross_weight", getattr(self.instance, "gross_weight", None))
        s = a.get("stone_weight", getattr(self.instance, "stone_weight", 0))
        if g is not None and s > g:
            raise serializers.ValidationError("Stone weight cannot exceed gross weight")
        p = a.get("purity")
        if p is not None and not (0 < p <= 1):
            raise serializers.ValidationError({"purity": "Must be between 0 and 1 (e.g. 0.916)"})
        return a

    def to_representation(self, obj):
        data = super().to_representation(obj)
        if not can_see_cost(self.context["request"].user):
            data.pop("purchase_cost", None)
            data.pop("supplier", None)
        return data


class CategorySer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class RateSer(serializers.ModelSerializer):
    class Meta:
        model = MetalRate
        fields = ["id", "metal", "purity", "rate_per_gram", "created_at"]
        read_only_fields = ["id", "created_at"]


class MovementSer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = ["id", "kind", "reference", "gross_weight", "fine_weight", "direction", "created_at"]


class ProductViewSet(TenantViewSet):
    module = "products"
    queryset = Product.objects.select_related("category")
    serializer_class = ProductSer
    search_fields = ["name", "sku", "barcode", "huid"]
    filterset_fields = ["metal", "status", "category", "branch"]
    ordering_fields = ["created_at", "net_weight", "name"]

    @action(detail=False, methods=["get"], url_path=r"scan/(?P<code>[^/]+)")
    def scan(self, request, code=None):
        p = self.get_queryset().filter(barcode=code).first()
        if not p:
            return Response({"detail": "Barcode not found"}, status=404)
        return Response(ProductSer(p, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        return Response(MovementSer(self.get_object().movements.all(), many=True).data)


class CategoryViewSet(TenantViewSet):
    module = "products"
    branch_scoped = False
    queryset = Category.objects.all()
    serializer_class = CategorySer
    pagination_class = None


class RateViewSet(TenantViewSet):
    module = "products"
    branch_scoped = False
    queryset = MetalRate.objects.all()
    serializer_class = RateSer
    filterset_fields = ["metal"]
