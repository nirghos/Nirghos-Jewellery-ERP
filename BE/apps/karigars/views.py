from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounting import services as acc
from apps.accounts.permissions import ModulePermission
from apps.core import jewellery as J
from apps.core.crud import serializer_for, viewset_for
from apps.core.models import audit, next_number
from apps.products.models import Product, StockMovement
from apps.products.services import post_metal
from .models import JobCard, Karigar, KarigarPayment, MetalTxn

D = Decimal


def holdings(company, karigar=None):
    """Fine metal currently with each karigar = issued - (returned + scrap + finished)."""
    qs = MetalTxn.objects.filter(company=company, jobcard__status="open")
    if karigar:
        qs = qs.filter(karigar=karigar)
    out = {}
    for t in qs:
        sign = 1 if t.kind == "issue" else -1
        out[t.karigar_id] = out.get(t.karigar_id, D(0)) + sign * t.fine_weight
    return out


KarigarViewSet = viewset_for(Karigar, "karigars", search=["name", "phone"], filters=["is_active"], branch_scoped=False)


class KarigarVS(KarigarViewSet):
    @action(detail=False, methods=["get"])
    def balances(self, request):
        h = holdings(request.user.company)
        rows = [{"karigar_id": k.id, "name": k.name, "fine_with_karigar": h.get(k.id, D(0))}
                for k in self.get_queryset().filter(is_active=True)]
        return Response({"rows": rows, "total": sum((r["fine_with_karigar"] for r in rows), D(0))})

    @action(detail=True, methods=["get"])
    def ledger(self, request, pk=None):
        k = self.get_object()
        run, rows = D(0), []
        for t in MetalTxn.objects.filter(karigar=k).order_by("created_at").select_related("jobcard"):
            run += t.fine_weight if t.kind == "issue" else -t.fine_weight
            rows.append({"date": t.created_at, "job": t.jobcard.number, "kind": t.kind, "gross": t.gross_weight,
                         "fine": t.fine_weight, "balance": run, "note": t.note})
        paid = k.payments.aggregate(s=Sum("amount"))["s"] or D(0)
        labour = k.jobcards.aggregate(s=Sum("labour_charge"))["s"] or D(0)
        return Response({"karigar": k.name, "rows": rows, "metal_balance_fine": run,
                         "labour_charges": labour, "labour_paid": paid, "labour_due": labour - paid})


class JobSer(serializers.ModelSerializer):
    karigar_name = serializers.CharField(source="karigar.name", read_only=True)

    class Meta:
        model = JobCard
        fields = ["id", "number", "karigar", "karigar_name", "description", "due_date", "status", "labour_charge",
                  "issued_fine", "returned_fine", "wastage_fine", "allowed_wastage", "excess_wastage", "closed_at", "created_at"]
        read_only_fields = ["id", "number", "status", "issued_fine", "returned_fine", "wastage_fine", "allowed_wastage",
                            "excess_wastage", "closed_at", "created_at"]


class TxnSer(serializers.ModelSerializer):
    karigar_name = serializers.CharField(source="karigar.name", read_only=True)
    job = serializers.CharField(source="jobcard.number", read_only=True)

    class Meta:
        model = MetalTxn
        fields = ["id", "karigar", "karigar_name", "jobcard", "job", "kind", "metal", "purity", "gross_weight",
                  "fine_weight", "note", "created_at"]


class TxnIn(serializers.Serializer):
    jobcard = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=["issue", "return", "scrap", "finished"])
    metal = serializers.ChoiceField(choices=["gold", "silver", "platinum"], default="gold")
    purity = serializers.DecimalField(max_digits=5, decimal_places=3, min_value=D("0.001"), max_value=1)
    gross_weight = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=D("0.001"))
    note = serializers.CharField(required=False, allow_blank=True, default="")
    # finished jewellery only
    sku = serializers.CharField(required=False)
    barcode = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    stone_weight = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=0, default=0)
    making_type = serializers.ChoiceField(choices=["per_gram", "percent", "fixed"], default="per_gram")
    making_value = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, default=0)
    wastage_percent = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, default=0)


class JobCardViewSet(viewset_for(JobCard, "karigars", search=["number", "description", "karigar__name"],
                                 filters=["status", "karigar"], select=["karigar"], ser=JobSer, no_delete=True)):
    perm_map = {"close": "approve", "cancel": "approve"}

    def perform_create(self, s):
        u = self.request.user
        if s.validated_data["karigar"].company_id != u.company_id:
            raise ValidationError({"karigar": "Not found"})
        obj = s.save(company=u.company, branch=u.branch, created_by=u, number=next_number(u.company, "job", "JOB"))
        audit(u, "create", obj)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def close(self, request, pk=None):
        job = JobCard.objects.select_for_update().get(pk=self.get_object().pk)
        if job.status != "open":
            raise ValidationError("Job card is not open")
        issued = job.txns.filter(kind="issue").aggregate(s=Sum("fine_weight"))["s"] or D(0)
        back = job.txns.exclude(kind="issue").aggregate(s=Sum("fine_weight"))["s"] or D(0)
        if issued == 0:
            raise ValidationError("No metal was issued on this job")
        waste = issued - back
        if waste < 0:
            raise ValidationError(f"Returned fine ({back}) exceeds issued fine ({issued}); check entries")
        allowed = J.q3(issued * job.karigar.allowed_wastage_percent / D(100))
        job.issued_fine, job.returned_fine, job.wastage_fine = issued, back, waste
        job.allowed_wastage, job.excess_wastage = allowed, max(waste - allowed, D(0))
        if "labour_charge" in request.data:
            try:
                job.labour_charge = J.q2(request.data["labour_charge"])
            except Exception:
                raise ValidationError({"labour_charge": "Invalid amount"})
        job.status, job.closed_at = "closed", timezone.now()
        job.save()
        audit(request.user, "close", job)
        return Response(JobSer(job).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        job = self.get_object()
        if job.txns.exists():
            raise ValidationError("Job has metal transactions; close it instead")
        job.status = "cancelled"
        job.save(update_fields=["status", "updated_at"])
        return Response(JobSer(job).data)


class TxnViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Issue / return / scrap / finished-jewellery receipts. Append-only."""
    module = "karigars"
    permission_classes = [ModulePermission]
    serializer_class = TxnSer
    queryset = MetalTxn.objects.select_related("karigar", "jobcard")
    filterset_fields = ["karigar", "jobcard", "kind"]
    search_fields = ["jobcard__number", "karigar__name"]

    def get_queryset(self):
        return super().get_queryset().filter(company_id=self.request.user.company_id)

    @transaction.atomic
    def create(self, request):
        s = TxnIn(data=request.data)
        s.is_valid(raise_exception=True)
        d, u = s.validated_data, request.user
        job = JobCard.objects.select_for_update().filter(pk=d["jobcard"], company=u.company).select_related("karigar").first()
        if not job:
            raise ValidationError({"jobcard": "Not found"})
        if job.status != "open":
            raise ValidationError("Job card is not open")
        gross, purity = J.q3(d["gross_weight"]), d["purity"]
        fine = J.fine_weight(gross, purity)
        product = None
        branch = u.branch
        if d["kind"] == "issue":
            post_metal(company=u.company, branch=branch, user=u, metal=d["metal"], purity=purity, kind="karigar_issue",
                       gross=gross, reference=job.number, direction=-1)
        elif d["kind"] in ("return", "scrap"):
            post_metal(company=u.company, branch=branch, user=u, metal=d["metal"], purity=purity, kind="karigar_return",
                       gross=gross, reference=job.number)
        else:
            if not d.get("sku") or not d.get("barcode"):
                raise ValidationError("Finished jewellery needs sku and barcode")
            if Product.objects.filter(company=u.company, sku=d["sku"]).exists() or \
               Product.objects.filter(company=u.company, barcode=d["barcode"]).exists():
                raise ValidationError("SKU/barcode already exists")
            try:
                product = Product.objects.create(
                    company=u.company, branch=branch, created_by=u, name=d.get("name") or d["sku"], sku=d["sku"],
                    barcode=d["barcode"], metal=d["metal"], purity=purity, gross_weight=gross, stone_weight=d["stone_weight"],
                    making_type=d["making_type"], making_value=d["making_value"], wastage_percent=d["wastage_percent"])
            except ValueError as e:
                raise ValidationError(str(e))
            fine = product.fine_weight
            StockMovement.objects.create(company=u.company, branch=branch, product=product, kind="production",
                                         reference=job.number, gross_weight=gross, fine_weight=fine, direction=1, created_by=u)
        t = MetalTxn.objects.create(company=u.company, branch=branch, created_by=u, approved_by=u, karigar=job.karigar,
                                    jobcard=job, kind=d["kind"], metal=d["metal"], purity=purity, gross_weight=gross,
                                    fine_weight=fine, product=product, note=d["note"])
        audit(u, d["kind"], t)
        return Response(TxnSer(t).data, status=201)


class PaymentSer(serializers.ModelSerializer):
    karigar_name = serializers.CharField(source="karigar.name", read_only=True)

    class Meta:
        model = KarigarPayment
        fields = ["id", "karigar", "karigar_name", "date", "amount", "method", "note", "created_at"]
        read_only_fields = ["id", "created_at"]


class PaymentViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    module = "karigars"
    permission_classes = [ModulePermission]
    serializer_class = PaymentSer
    queryset = KarigarPayment.objects.select_related("karigar")
    filterset_fields = ["karigar"]

    def get_queryset(self):
        return super().get_queryset().filter(company_id=self.request.user.company_id)

    @transaction.atomic
    def perform_create(self, s):
        u, d = self.request.user, s.validated_data
        if d["karigar"].company_id != u.company_id:
            raise ValidationError({"karigar": "Not found"})
        if d["amount"] <= 0:
            raise ValidationError({"amount": "Must be positive"})
        obj = s.save(company=u.company, branch=u.branch, created_by=u)
        acc.post(company=u.company, branch=u.branch, user=u, kind="payment", reference=f"KP-{str(obj.id)[:8]}",
                 narration=f"Karigar payment {d['karigar'].name}",
                 lines=[("5100", d["amount"], 0), (acc.METHOD_ACCOUNT[d["method"]], 0, d["amount"])])
        audit(u, "create", obj)
