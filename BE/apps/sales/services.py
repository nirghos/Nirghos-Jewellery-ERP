"""Billing engine. All money/weight maths happens here, on the backend."""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core import jewellery as J
from apps.products.models import MetalRate, Product, StockMovement
from .models import Invoice, InvoiceItem, Payment

D = Decimal


def _next_number(company):
    n = Invoice.objects.filter(company=company).count() + 1
    return f"INV-{timezone.now():%y%m}-{n:05d}"


def _rate_for(company, product):
    r = (MetalRate.objects.filter(company=company, metal=product.metal, purity=product.purity).first()
         or MetalRate.objects.filter(company=company, metal=product.metal).first())
    if not r:
        raise ValidationError(f"No rate configured for {product.metal} {product.purity}")
    return r.rate_per_gram if r.purity == product.purity else J.q2(r.rate_per_gram / r.purity * product.purity)


@transaction.atomic
def create_invoice(*, user, branch, customer, product_ids, payments, discount=0, old_gold_adjustment=0, include_hallmark=False):
    company = user.company
    if not product_ids or len(set(product_ids)) != len(product_ids):
        raise ValidationError("Select at least one unique item")

    # Row-lock the pieces so concurrent POS sessions cannot sell the same article twice.
    products = list(Product.objects.select_for_update().filter(id__in=product_ids, company=company))
    if len(products) != len(product_ids):
        raise ValidationError("Some items were not found")
    for p in products:
        if p.status != Product.Status.AVAILABLE:
            raise ValidationError(f"{p.sku} is not available ({p.status})")
        if not user.all_branches and p.branch_id != user.branch_id:
            raise ValidationError(f"{p.sku} belongs to another branch")

    inv = Invoice(company=company, branch=branch, customer=customer, created_by=user, number=_next_number(company))
    metal = making = stone = D(0)
    items = []
    for p in products:
        rate = _rate_for(company, p)
        mv = J.q2(rate * p.net_weight)
        wv = J.q2(mv * p.wastage_percent / D(100))
        mk = J.making_charge(p.making_type, p.making_value, p.net_weight, mv)
        sv = J.q2(p.stone_price)
        items.append(InvoiceItem(product=p, rate_per_gram=rate, net_weight=p.net_weight, metal_value=mv,
                                 wastage_value=wv, making_value=mk, stone_value=sv, line_total=mv + wv + mk + sv))
        metal += mv + wv
        making += mk
        stone += sv

    discount, old_gold = J.q2(discount), J.q2(old_gold_adjustment)
    hallmark = J.q2(company.hallmark_charge * len(products)) if include_hallmark else D(0)
    taxable = metal + making + stone + hallmark - discount
    if taxable < 0:
        raise ValidationError("Discount exceeds invoice value")
    gst = J.q2(taxable * company.gst_rate / D(100))
    grand = taxable + gst - old_gold
    paid = sum((J.q2(x["amount"]) for x in payments), D(0))
    if paid > grand:
        raise ValidationError("Payments exceed grand total")

    inv.metal_total, inv.making_total, inv.stone_total, inv.hallmark_total = metal, making, stone, hallmark
    inv.discount, inv.old_gold_adjustment, inv.taxable_value = discount, old_gold, taxable
    inv.gst_rate, inv.gst_amount, inv.grand_total, inv.paid = company.gst_rate, gst, grand, paid
    inv.save()
    for it in items:
        it.invoice = inv
    InvoiceItem.objects.bulk_create(items)
    Payment.objects.bulk_create([Payment(invoice=inv, method=x["method"], amount=J.q2(x["amount"]),
                                         reference=x.get("reference", "")) for x in payments])
    for p in products:
        p.status = Product.Status.SOLD
        p.save(update_fields=["status", "updated_at"])
        StockMovement.objects.create(company=company, branch=p.branch, product=p, kind="sale", reference=inv.number,
                                     gross_weight=p.gross_weight, fine_weight=p.fine_weight, direction=-1, created_by=user)
    return inv


@transaction.atomic
def cancel_invoice(*, user, invoice, reason):
    inv = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if inv.status == Invoice.Status.CANCELLED:
        raise ValidationError("Already cancelled")
    for it in inv.items.select_related("product"):
        p = Product.objects.select_for_update().get(pk=it.product_id)
        p.status = Product.Status.AVAILABLE
        p.save(update_fields=["status", "updated_at"])
        StockMovement.objects.create(company=inv.company, branch=p.branch, product=p, kind="sale_reversal",
                                     reference=inv.number, gross_weight=p.gross_weight, fine_weight=p.fine_weight,
                                     direction=1, created_by=user)
    inv.status = Invoice.Status.CANCELLED
    inv.cancel_reason = reason
    inv.save(update_fields=["status", "cancel_reason", "updated_at"])
    return inv
