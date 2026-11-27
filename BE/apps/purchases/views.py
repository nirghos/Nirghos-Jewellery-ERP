from decimal import Decimal

from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import ModulePermission
from apps.core.crud import serializer_for, viewset_for
from apps.core.models import audit
from apps.suppliers.models import Supplier
from . import services
from .models import PurchaseInvoice, PurchaseItem, SupplierPayment


class ItemSer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseItem
        fields = ["id", "kind", "name", "metal", "purity", "gross_weight", "stone_weight", "net_weight", "fine_weight",
                  "rate_per_gram", "extra_charges", "amount"]


class PurchaseSer(serializers.ModelSerializer):
    items = ItemSer(many=True, read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    balance = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseInvoice
        fields = ["id", "number", "supplier", "supplier_name", "supplier_invoice_no", "date", "status", "subtotal",
                  "gst_rate", "gst_amount", "total", "paid", "balance", "notes", "items", "created_at"]


class ItemIn(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["piece", "metal"])
    metal = serializers.ChoiceField(choices=["gold", "silver", "platinum"], default="gold")
    purity = serializers.DecimalField(max_digits=5, decimal_places=3, min_value=Decimal("0.001"), max_value=1)
    gross_weight = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
    stone_weight = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=0, default=0)
    rate_per_gram = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    extra_charges = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0, default=0)
    name = serializers.CharField(required=False, allow_blank=True)
    sku = serializers.CharField(required=False)
    barcode = serializers.CharField(required=False)
    huid = serializers.CharField(required=False, allow_blank=True, max_length=6)
    making_type = serializers.ChoiceField(choices=["per_gram", "percent", "fixed"], default="per_gram")
    making_value = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, default=0)
    wastage_percent = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, default=0)
    stone_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, default=0)


class PurchaseIn(serializers.Serializer):
    supplier = serializers.UUIDField()
    date = serializers.DateField(required=False)
    supplier_invoice_no = serializers.CharField(required=False, allow_blank=True)
    gst_rate = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=28, required=False)
    paid = serializers.DecimalField(max_digits=16, decimal_places=2, min_value=0, default=0)
    method = serializers.ChoiceField(choices=["cash", "upi", "bank", "card"], default="cash")
    notes = serializers.CharField(required=False, allow_blank=True)
    items = ItemIn(many=True)


class PurchaseViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    module = "purchases"
    permission_classes = [ModulePermission]
    serializer_class = PurchaseSer
    queryset = PurchaseInvoice.objects.select_related("supplier").prefetch_related("items")
    search_fields = ["number", "supplier__name", "supplier_invoice_no"]
    filterset_fields = ["status", "supplier"]
    perm_map = {"cancel": "approve"}

    def get_queryset(self):
        u = self.request.user
        qs = super().get_queryset().filter(company_id=u.company_id)
        return qs if u.all_branches else qs.filter(branch_id=u.branch_id)

    def create(self, request):
        s = PurchaseIn(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        sup = Supplier.objects.filter(pk=d["supplier"], company_id=request.user.company_id).first()
        if not sup:
            raise ValidationError({"supplier": "Not found"})
        if not request.user.branch:
            raise ValidationError("Your user has no branch assigned")
        inv = services.create_purchase(
            user=request.user, branch=request.user.branch, supplier=sup, items=d["items"], date=d.get("date"),
            supplier_invoice_no=d.get("supplier_invoice_no", ""), gst_rate=d.get("gst_rate"), paid=d["paid"],
            method=d["method"], notes=d.get("notes", ""))
        audit(request.user, "create", inv)
        return Response(PurchaseSer(inv).data, status=201)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        inv = services.cancel_purchase(user=request.user, invoice=self.get_object(), reason=request.data.get("reason", "")[:100])
        audit(request.user, "cancel", inv)
        return Response(PurchaseSer(inv).data)


class PaymentSer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)

    class Meta:
        model = SupplierPayment
        fields = ["id", "supplier", "supplier_name", "date", "amount", "method", "reference", "created_at"]
        read_only_fields = ["id", "created_at"]


class SupplierPaymentViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    module = "purchases"
    permission_classes = [ModulePermission]
    serializer_class = PaymentSer
    queryset = SupplierPayment.objects.select_related("supplier")
    filterset_fields = ["supplier"]
    search_fields = ["supplier__name", "reference"]

    def get_queryset(self):
        return super().get_queryset().filter(company_id=self.request.user.company_id)

    def create(self, request):
        s = PaymentSer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        if d["supplier"].company_id != request.user.company_id:
            raise ValidationError({"supplier": "Not found"})
        p = services.pay_supplier(user=request.user, branch=request.user.branch, supplier=d["supplier"],
                                  amount=d["amount"], method=d["method"], date=d.get("date"), reference=d.get("reference", ""))
        audit(request.user, "create", p)
        return Response(PaymentSer(p).data, status=201)


class SupplierLedger(APIView):
    module = "purchases"
    permission_classes = [ModulePermission]

    def get(self, request):
        sup = Supplier.objects.filter(pk=request.query_params.get("supplier"), company_id=request.user.company_id).first()
        if not sup:
            raise ValidationError("supplier is required")
        ev = [(i.date, i.created_at, f"Purchase {i.number}", i.total, Decimal(0))
              for i in sup.purchases.filter(status="posted")]
        ev += [(p.date, p.created_at, f"Payment {p.method} {p.reference}", Decimal(0), p.amount) for p in sup.payments.all()]
        # payments made at time of purchase are inside invoice.paid; show them as credits too
        ev += [(i.date, i.created_at, f"Paid on {i.number}", Decimal(0), i.paid) for i in sup.purchases.filter(status="posted", paid__gt=0)]
        ev.sort(key=lambda x: (x[0], x[1]))
        bal, rows = Decimal(0), []
        for d, _, t, cr, dr in ev:
            bal += cr - dr
            rows.append({"date": d, "description": t, "purchase": cr, "paid": dr, "balance": bal})
        return Response({"supplier": sup.name, "rows": rows, "outstanding": bal})
