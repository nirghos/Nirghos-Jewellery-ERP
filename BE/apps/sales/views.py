from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import ModulePermission
from apps.customers.models import Customer
from .models import Invoice, InvoiceItem, Payment
from . import services


class ItemSer(serializers.ModelSerializer):
    sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = InvoiceItem
        fields = ["id", "sku", "product_name", "rate_per_gram", "net_weight", "metal_value", "wastage_value",
                  "making_value", "stone_value", "line_total"]


class PaymentSer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "method", "amount", "reference"]


class InvoiceSer(serializers.ModelSerializer):
    items = ItemSer(many=True, read_only=True)
    payments = PaymentSer(many=True, read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True, default="")
    balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = ["id", "number", "customer", "customer_name", "status", "metal_total", "making_total", "stone_total",
                  "hallmark_total", "discount", "old_gold_adjustment", "taxable_value", "gst_rate", "gst_amount",
                  "grand_total", "paid", "balance", "items", "payments", "created_at"]
        read_only_fields = fields


class PaymentIn(serializers.Serializer):
    method = serializers.ChoiceField(choices=["cash", "upi", "card", "bank"])
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0)
    reference = serializers.CharField(required=False, allow_blank=True)


class InvoiceIn(serializers.Serializer):
    customer = serializers.UUIDField(required=False, allow_null=True)
    product_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)
    payments = PaymentIn(many=True, required=False)
    discount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0, default=0)
    old_gold_adjustment = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0, default=0)
    include_hallmark = serializers.BooleanField(default=False)


class InvoiceViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Invoices are created via the billing engine and never hard-deleted; cancellation reverses stock."""
    module = "sales"
    permission_classes = [ModulePermission]
    serializer_class = InvoiceSer
    queryset = Invoice.objects.select_related("customer").prefetch_related("items__product", "payments")
    search_fields = ["number", "customer__name"]
    filterset_fields = ["status", "branch"]

    def get_queryset(self):
        u = self.request.user
        qs = super().get_queryset().filter(company_id=u.company_id)
        return qs if u.all_branches else qs.filter(branch_id=u.branch_id)

    def create(self, request):
        s = InvoiceIn(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        customer = None
        if d.get("customer"):
            customer = Customer.objects.filter(pk=d["customer"], company_id=request.user.company_id).first()
            if not customer:
                raise serializers.ValidationError({"customer": "Not found"})
        branch = request.user.branch
        if branch is None:
            raise serializers.ValidationError("Your user has no branch assigned")
        inv = services.create_invoice(
            user=request.user, branch=branch, customer=customer, product_ids=d["product_ids"],
            payments=d.get("payments", []), discount=d["discount"],
            old_gold_adjustment=d["old_gold_adjustment"], include_hallmark=d["include_hallmark"])
        return Response(InvoiceSer(inv).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        self.action_name = "approve"
        inv = services.cancel_invoice(user=request.user, invoice=self.get_object(),
                                      reason=request.data.get("reason", "")[:200])
        return Response(InvoiceSer(inv).data)

    def check_permissions(self, request):
        if getattr(self, "action", None) == "cancel":
            self.action_name = "approve"
        super().check_permissions(request)
