from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounting import services as acc
from apps.accounts.permissions import ModulePermission
from apps.core import jewellery as J
from apps.core.models import audit, next_number
from apps.customers.models import Customer
from apps.products.models import MetalRate
from apps.products.services import post_metal
from .models import MeltingBatch, OldGoldReceipt

D = Decimal


class ReceiptSer(serializers.ModelSerializer):
    class Meta:
        model = OldGoldReceipt
        fields = ["id", "number", "customer", "customer_name", "gross_weight", "stone_weight", "net_weight", "touch",
                  "fine_weight", "test_method", "rate_per_gram", "deduction_percent", "value", "payout", "kyc_id_type",
                  "kyc_id_number", "status", "exchange_invoice", "notes", "created_at"]
        read_only_fields = ["id", "number", "net_weight", "fine_weight", "value", "status", "exchange_invoice", "created_at"]
        extra_kwargs = {"rate_per_gram": {"required": False}}

    def validate_touch(self, v):
        if not (0 < v <= 1):
            raise serializers.ValidationError("Touch must be between 0 and 1 (e.g. 0.750)")
        return v


class ReceiptViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    module = "old_gold"
    permission_classes = [ModulePermission]
    serializer_class = ReceiptSer
    queryset = OldGoldReceipt.objects.select_related("customer")
    search_fields = ["number", "customer_name", "customer__name"]
    filterset_fields = ["status", "payout"]
    perm_map = {"cancel": "approve", "melt": "approve"}

    def get_queryset(self):
        u = self.request.user
        qs = super().get_queryset().filter(company_id=u.company_id)
        return qs if u.all_branches else qs.filter(branch_id=u.branch_id)

    @transaction.atomic
    def perform_create(self, s):
        u, d = self.request.user, s.validated_data
        if d.get("customer") and d["customer"].company_id != u.company_id:
            raise ValidationError({"customer": "Not found"})
        try:
            net = J.net_weight(d["gross_weight"], d.get("stone_weight", 0))
            fine = J.fine_weight(net, d["touch"])
        except ValueError as e:
            raise ValidationError(str(e))
        rate = d.get("rate_per_gram")
        if not rate:
            r = MetalRate.objects.filter(company=u.company, metal="gold").first()
            if not r:
                raise ValidationError("Set a gold rate first or enter the 24K rate")
            rate = J.q2(r.rate_per_gram / r.purity)
        value = J.q2(fine * rate * (D(100) - d.get("deduction_percent", 0)) / D(100))
        if not u.branch:
            raise ValidationError("Your user has no branch assigned")
        obj = s.save(company=u.company, branch=u.branch, created_by=u, number=next_number(u.company, "og", "OG"),
                     net_weight=net, fine_weight=fine, rate_per_gram=rate, value=value)
        post_metal(company=u.company, branch=u.branch, user=u, metal="gold", purity=obj.touch, kind="old_gold",
                   gross=obj.gross_weight, reference=obj.number)
        if obj.payout == "cash":
            acc.post(company=u.company, branch=u.branch, user=u, kind="payment", reference=obj.number,
                     narration=f"Old gold purchase {obj.number}", lines=[("1200", value, 0), ("1000", 0, value)])
        audit(u, "create", obj)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def cancel(self, request, pk=None):
        o = OldGoldReceipt.objects.select_for_update().get(pk=self.get_object().pk)
        if o.status != "received":
            raise ValidationError("Only received (not exchanged/melted) old gold can be cancelled")
        post_metal(company=o.company, branch=o.branch, user=request.user, metal="gold", purity=o.touch,
                   kind="old_gold_reversal", gross=o.gross_weight, reference=o.number, direction=-1)
        acc.reverse_by_reference(o.company, ["payment"], o.number, request.user)
        o.status = "cancelled"
        o.save(update_fields=["status", "updated_at"])
        audit(request.user, "cancel", o)
        return Response(ReceiptSer(o).data)

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def melt(self, request):
        """Melt selected receipts into a bar. Body: receipt_ids, recovered_gross, recovered_purity."""
        u = request.user
        ids = request.data.get("receipt_ids") or []
        try:
            rg, rp = J.q3(request.data["recovered_gross"]), D(str(request.data["recovered_purity"]))
        except Exception:
            raise ValidationError("recovered_gross and recovered_purity are required")
        recs = list(OldGoldReceipt.objects.select_for_update().filter(
            pk__in=ids, company=u.company, melting_batch__isnull=True, status__in=["received", "exchanged"]))
        if not recs or len(recs) != len(ids):
            raise ValidationError("Select valid, un-melted receipts")
        inp_g = sum((r.gross_weight for r in recs), D(0))
        inp_f = sum((r.fine_weight for r in recs), D(0))
        rf = J.fine_weight(rg, rp)
        if rf > inp_f + D("0.001"):
            raise ValidationError("Recovered fine gold cannot exceed input fine gold")
        b = MeltingBatch.objects.create(company=u.company, branch=u.branch, created_by=u,
                                        number=next_number(u.company, "melt", "MLT"), date=timezone.localdate(),
                                        input_gross=inp_g, input_fine=inp_f, recovered_gross=rg, recovered_purity=rp,
                                        recovered_fine=rf, loss_fine=inp_f - rf)
        for r in recs:
            post_metal(company=u.company, branch=u.branch, user=u, metal="gold", purity=r.touch, kind="melting",
                       gross=r.gross_weight, reference=b.number, direction=-1)
            r.melting_batch = b
            r.status = "melted"
            r.save(update_fields=["melting_batch", "status", "updated_at"])
        post_metal(company=u.company, branch=u.branch, user=u, metal="gold", purity=rp, kind="melting", gross=rg, reference=b.number)
        audit(u, "melt", b)
        return Response({"batch": b.number, "input_fine": b.input_fine, "recovered_fine": b.recovered_fine, "loss_fine": b.loss_fine})


class BatchSer(serializers.ModelSerializer):
    class Meta:
        model = MeltingBatch
        fields = ["id", "number", "date", "input_gross", "input_fine", "recovered_gross", "recovered_purity",
                  "recovered_fine", "loss_fine"]


class BatchViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    module = "old_gold"
    permission_classes = [ModulePermission]
    serializer_class = BatchSer
    queryset = MeltingBatch.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(company_id=self.request.user.company_id)
