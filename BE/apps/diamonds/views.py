from django.db import transaction
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.permissions import can_see_cost
from apps.core.crud import serializer_for, viewset_for
from apps.core.models import audit
from apps.karigars.models import Karigar
from apps.products.models import Product
from .models import Stone


class StoneSer(serializers.ModelSerializer):
    class Meta:
        model = Stone
        exclude = ["company", "created_by"]
        read_only_fields = ["id", "status", "karigar", "product", "created_at", "updated_at"]

    def validate_carat(self, v):
        if v <= 0:
            raise serializers.ValidationError("Carat must be positive")
        return v

    def validate_stock_no(self, v):
        qs = Stone.objects.filter(company_id=self.context["request"].user.company_id, stock_no=v)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Stock number already exists")
        return v

    def to_representation(self, o):
        d = super().to_representation(o)
        if not can_see_cost(self.context["request"].user):
            d.pop("purchase_price", None)
            d.pop("supplier", None)
        return d


class StoneViewSet(viewset_for(Stone, "diamonds", search=["stock_no", "name", "cert_no", "lot_no", "shape"],
                               filters=["kind", "status", "lab", "clarity", "color"], ser=StoneSer, no_delete=True)):
    perm_map = {"issue": "edit", "return_stone": "edit", "set_in": "edit", "sell": "approve"}

    def _lock(self):
        return Stone.objects.select_for_update().get(pk=self.get_object().pk)

    def _done(self, s, request, act):
        audit(request.user, act, s)
        return Response(StoneSer(s, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def issue(self, request, pk=None):
        s = self._lock()
        k = Karigar.objects.filter(pk=request.data.get("karigar"), company=request.user.company).first()
        if s.status != "available" or not k:
            raise ValidationError("Stone must be available and karigar valid")
        s.status, s.karigar = "issued", k
        s.save(update_fields=["status", "karigar", "updated_at"])
        return self._done(s, request, "issue")

    @action(detail=True, methods=["post"], url_path="return")
    @transaction.atomic
    def return_stone(self, request, pk=None):
        s = self._lock()
        if s.status != "issued":
            raise ValidationError("Stone is not issued")
        s.status, s.karigar = "available", None
        s.save(update_fields=["status", "karigar", "updated_at"])
        return self._done(s, request, "return")

    @action(detail=True, methods=["post"], url_path="set")
    @transaction.atomic
    def set_in(self, request, pk=None):
        s = self._lock()
        p = Product.objects.filter(pk=request.data.get("product"), company=request.user.company).first()
        if s.status not in ("issued", "available") or not p:
            raise ValidationError("Stone must be issued/available and product valid")
        s.status, s.product = "set", p
        s.save(update_fields=["status", "product", "updated_at"])
        return self._done(s, request, "set")

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def sell(self, request, pk=None):
        s = self._lock()
        if s.status != "available":
            raise ValidationError("Only available loose stones can be sold")
        s.status = "sold"
        s.save(update_fields=["status", "updated_at"])
        return self._done(s, request, "sell")
