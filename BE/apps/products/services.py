from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from apps.companies.models import Company
from apps.core import jewellery as J
from .models import MetalLedger


def metal_balance(company, metal, purity, branch=None):
    qs = MetalLedger.objects.filter(company=company, metal=metal, purity=purity)
    if branch:
        qs = qs.filter(branch=branch)
    r = qs.aggregate(g=Sum("gross_weight"), f=Sum("fine_weight"))
    return r["g"] or Decimal(0), r["f"] or Decimal(0)


@transaction.atomic
def post_metal(*, company, branch, user, metal, purity, kind, gross, reference="", direction=1):
    """direction=+1 adds raw metal stock, -1 removes it (never below zero)."""
    purity, gross = Decimal(purity), J.q3(gross)
    if gross <= 0:
        raise ValidationError("Weight must be greater than zero")
    fine = J.fine_weight(gross, purity)
    if direction < 0:
        Company.objects.select_for_update().get(pk=company.pk)  # serialise stock-out per company
        g, f = metal_balance(company, metal, purity, branch)
        if g < gross:
            raise ValidationError(f"Insufficient {metal} {purity} stock: have {g} g, need {gross} g")
    return MetalLedger.objects.create(
        company=company, branch=branch, metal=metal, purity=purity, kind=kind, reference=reference,
        gross_weight=gross * direction, fine_weight=fine * direction, created_by=user)
