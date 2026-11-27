import re
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import ModulePermission
from apps.core.crud import viewset_for
from apps.core.models import audit, next_number
from apps.products.models import Product
from .models import AHCCentre, HallmarkItem, HallmarkRequest

HUID_RE = re.compile(r"^[A-Z0-9]{6}$")

CentreViewSet = viewset_for(AHCCentre, "hallmark", search=["name", "code"], branch_scoped=False)


class ItemSer(serializers.ModelSerializer):
    sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = HallmarkItem
        fields = ["id", "product", "sku", "product_name", "huid", "result", "remarks"]


class RequestSer(serializers.ModelSerializer):
    items = ItemSer(many=True, read_only=True)
    centre_name = serializers.CharField(source="centre.name", read_only=True)

    class Meta:
        model = HallmarkRequest
        fields = ["id", "number", "centre", "centre_name", "status", "dispatched_on", "received_on", "total_charges",
                  "notes", "items", "created_at"]


class RequestViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    module = "hallmark"
    permission_classes = [ModulePermission]
    serializer_class = RequestSer
    queryset = HallmarkRequest.objects.select_related("centre").prefetch_related("items__product")
    filterset_fields = ["status", "centre"]
    search_fields = ["number", "centre__name"]
    perm_map = {"dispatch_request": "edit", "receive": "edit"}

    def get_queryset(self):
        u = self.request.user
        qs = super().get_queryset().filter(company_id=u.company_id)
        return qs if u.all_branches else qs.filter(branch_id=u.branch_id)

    @transaction.atomic
    def create(self, request):
        u = request.user
        centre = AHCCentre.objects.filter(pk=request.data.get("centre"), company=u.company).first()
        ids = request.data.get("product_ids") or []
        if not centre or not ids:
            raise ValidationError("centre and product_ids are required")
        prods = list(Product.objects.select_for_update().filter(pk__in=ids, company=u.company, status="available"))
        if len(prods) != len(set(ids)):
            raise ValidationError("Some products are missing or not available")
        busy = HallmarkItem.objects.filter(product__in=prods, result="pending").select_related("product")
        if busy.exists():
            raise ValidationError(f"{busy[0].product.sku} is already in a pending hallmark request")
        r = HallmarkRequest.objects.create(company=u.company, branch=u.branch, created_by=u, centre=centre,
                                           number=next_number(u.company, "hm", "HM"),
                                           total_charges=centre.charge_per_piece * len(prods), notes=str(request.data.get("notes", ""))[:300])
        HallmarkItem.objects.bulk_create([HallmarkItem(request=r, product=p) for p in prods])
        audit(u, "create", r)
        return Response(RequestSer(r).data, status=201)

    @action(detail=True, methods=["post"], url_path="dispatch")
    def dispatch_request(self, request, pk=None):
        r = self.get_object()
        if r.status != "created":
            raise ValidationError("Request already dispatched")
        r.status, r.dispatched_on = "dispatched", timezone.localdate()
        r.save(update_fields=["status", "dispatched_on", "updated_at"])
        return Response(RequestSer(r).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def receive(self, request, pk=None):
        """Body: results = [{item, result: pass|fail, huid}]. Passing items get their HUID stored on the product."""
        r = HallmarkRequest.objects.select_for_update().get(pk=self.get_object().pk)
        if r.status != "dispatched":
            raise ValidationError("Dispatch the request first")
        items = {str(i.id): i for i in r.items.select_related("product")}
        res = request.data.get("results") or []
        if {str(x.get("item")) for x in res} != set(items):
            raise ValidationError("Provide a result for every item")
        for x in res:
            it, result = items[str(x["item"])], x.get("result")
            if result not in ("pass", "fail"):
                raise ValidationError("result must be pass or fail")
            if result == "pass":
                huid = str(x.get("huid", "")).upper()
                if not HUID_RE.match(huid):
                    raise ValidationError(f"HUID must be 6 alphanumeric characters ({it.product.sku})")
                if Product.objects.filter(company=r.company, huid=huid).exclude(pk=it.product_id).exists():
                    raise ValidationError(f"HUID {huid} is already assigned to another piece")
                it.huid = huid
                it.product.huid = huid
                it.product.save(update_fields=["huid", "updated_at"])
            it.result, it.remarks = result, str(x.get("remarks", ""))[:200]
            it.save()
        r.status, r.received_on = "received", timezone.localdate()
        r.save(update_fields=["status", "received_on", "updated_at"])
        audit(request.user, "receive", r)
        return Response(RequestSer(r).data)


class HuidSearch(APIView):
    module = "hallmark"
    permission_classes = [ModulePermission]

    def get(self, request):
        q = (request.query_params.get("q") or "").strip().upper()
        if len(q) < 3:
            raise ValidationError("Enter at least 3 characters")
        qs = Product.objects.filter(company=request.user.company, huid__icontains=q)
        if not request.user.all_branches:
            qs = qs.filter(branch=request.user.branch)
        return Response([{"huid": p.huid, "sku": p.sku, "name": p.name, "purity": p.purity, "net_weight": p.net_weight,
                          "status": p.status} for p in qs[:50]])
