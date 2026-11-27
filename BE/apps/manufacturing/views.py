from decimal import Decimal

from django.db import transaction
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.crud import serializer_for, viewset_for
from apps.core.models import audit, next_number
from apps.core import jewellery as J
from apps.products.models import Product, StockMovement
from .models import STAGES, BOMItem, Design, ProductionOrder, StageLog

D = Decimal


class BOMSer(serializers.ModelSerializer):
    class Meta:
        model = BOMItem
        fields = ["id", "material", "metal", "purity", "weight", "unit", "note"]


class DesignSer(serializers.ModelSerializer):
    bom = BOMSer(many=True, required=False)

    class Meta:
        model = Design
        fields = ["id", "code", "name", "category", "description", "metal", "purity", "expected_weight", "image",
                  "is_active", "bom"]
        read_only_fields = ["id"]

    def validate_code(self, v):
        qs = Design.objects.filter(company_id=self.context["request"].user.company_id, code=v)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Design code already exists")
        return v

    @transaction.atomic
    def create(self, vd):
        bom = vd.pop("bom", [])
        d = super().create(vd)
        BOMItem.objects.bulk_create([BOMItem(design=d, **b) for b in bom])
        return d

    @transaction.atomic
    def update(self, inst, vd):
        bom = vd.pop("bom", None)
        d = super().update(inst, vd)
        if bom is not None:
            inst.bom.all().delete()
            BOMItem.objects.bulk_create([BOMItem(design=d, **b) for b in bom])
        return d


class DesignViewSet(viewset_for(Design, "manufacturing", search=["code", "name", "category"], filters=["is_active"],
                                branch_scoped=False, ser=DesignSer)):
    pass


class LogSer(serializers.ModelSerializer):
    class Meta:
        model = StageLog
        fields = ["id", "stage", "weight_in", "weight_out", "note", "created_at"]


class OrderSer(serializers.ModelSerializer):
    design_name = serializers.CharField(source="design.name", read_only=True)
    karigar_name = serializers.CharField(source="karigar.name", read_only=True, default="")
    logs = LogSer(many=True, read_only=True)

    class Meta:
        model = ProductionOrder
        fields = ["id", "number", "design", "design_name", "quantity", "karigar", "karigar_name", "jobcard", "stage",
                  "due_date", "notes", "production_cost", "logs", "created_at"]
        read_only_fields = ["id", "number", "stage", "production_cost", "logs", "created_at"]


class OrderViewSet(viewset_for(ProductionOrder, "manufacturing", search=["number", "design__name"],
                               filters=["stage", "karigar"], select=["design", "karigar"], ser=OrderSer, no_delete=True)):
    perm_map = {"advance": "edit", "complete": "approve"}

    def perform_create(self, s):
        u = self.request.user
        self._check_refs(s)
        o = s.save(company=u.company, branch=u.branch, created_by=u, number=next_number(u.company, "prod", "PRD"))
        StageLog.objects.create(order=o, stage="planned", note="Order created", by=u)
        audit(u, "create", o)

    @action(detail=True, methods=["post"])
    def advance(self, request, pk=None):
        o = self.get_object()
        stage = request.data.get("stage")
        if o.stage == "completed":
            raise ValidationError("Order already completed")
        if stage not in STAGES or stage == "completed":
            raise ValidationError(f"stage must be one of {STAGES[:-1]} (use complete to finish)")
        wi, wo = request.data.get("weight_in"), request.data.get("weight_out")
        StageLog.objects.create(order=o, stage=stage, note=str(request.data.get("note", ""))[:300], by=request.user,
                                weight_in=J.q3(wi) if wi not in (None, "") else None,
                                weight_out=J.q3(wo) if wo not in (None, "") else None)
        o.stage = stage
        o.save(update_fields=["stage", "updated_at"])
        return Response(OrderSer(o).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def complete(self, request, pk=None):
        """Finish production: creates the finished piece in stock. Requires quality_check stage first."""
        o = ProductionOrder.objects.select_for_update().select_related("design").get(pk=self.get_object().pk)
        if o.stage != "quality_check":
            raise ValidationError("Order must pass quality_check before completion")
        d, u = request.data, request.user
        for k in ("sku", "barcode", "gross_weight"):
            if not d.get(k):
                raise ValidationError({k: "required"})
        if Product.objects.filter(company=u.company, sku=d["sku"]).exists() or \
           Product.objects.filter(company=u.company, barcode=d["barcode"]).exists():
            raise ValidationError("SKU/barcode already exists")
        try:
            p = Product.objects.create(
                company=u.company, branch=u.branch, created_by=u, name=d.get("name") or o.design.name, sku=d["sku"],
                barcode=d["barcode"], metal=o.design.metal, purity=o.design.purity, gross_weight=J.q3(d["gross_weight"]),
                stone_weight=J.q3(d.get("stone_weight") or 0), making_type=d.get("making_type", "per_gram"),
                making_value=d.get("making_value") or 0, purchase_cost=J.q2(d.get("production_cost") or 0))
        except (ValueError, ArithmeticError) as e:
            raise ValidationError(str(e))
        StockMovement.objects.create(company=u.company, branch=u.branch, product=p, kind="production", reference=o.number,
                                     gross_weight=p.gross_weight, fine_weight=p.fine_weight, direction=1, created_by=u)
        o.stage, o.product, o.production_cost = "completed", p, p.purchase_cost
        o.save()
        StageLog.objects.create(order=o, stage="completed", weight_out=p.gross_weight, note="Added to stock", by=u)
        audit(u, "complete", o)
        return Response(OrderSer(o).data)
