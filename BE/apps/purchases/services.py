from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounting import services as acc
from apps.core import jewellery as J
from apps.core.models import next_number
from apps.products.models import Product, StockMovement
from apps.products.services import post_metal
from .models import PurchaseInvoice, PurchaseItem, SupplierPayment

D = Decimal


@transaction.atomic
def create_purchase(*, user, branch, supplier, items, date=None, supplier_invoice_no="", gst_rate=None, paid=0,
                    method="cash", notes=""):
    company = user.company
    if not items:
        raise ValidationError("Add at least one item")
    gst_rate = D(company.gst_rate if gst_rate is None else gst_rate)
    inv = PurchaseInvoice(company=company, branch=branch, supplier=supplier, created_by=user,
                          number=next_number(company, "pur", "PUR"), supplier_invoice_no=supplier_invoice_no,
                          date=date or timezone.localdate(), notes=notes, gst_rate=gst_rate)
    inv.save()
    subtotal = D(0)
    for it in items:
        try:
            gross, stone = J.q3(it["gross_weight"]), J.q3(it.get("stone_weight") or 0)
            net = J.net_weight(gross, stone)
            purity = D(str(it["purity"]))
            fine = J.fine_weight(net, purity)
        except ValueError as e:
            raise ValidationError(str(e))
        rate, extra = J.q2(it["rate_per_gram"]), J.q2(it.get("extra_charges") or 0)
        amount = J.q2(net * rate) + extra
        product = None
        if it["kind"] == "piece":
            if not it.get("sku") or not it.get("barcode"):
                raise ValidationError("Piece items need sku and barcode")
            if Product.objects.filter(company=company, sku=it["sku"]).exists() or \
               Product.objects.filter(company=company, barcode=it["barcode"]).exists():
                raise ValidationError(f"SKU/barcode already exists: {it['sku']}")
            product = Product.objects.create(
                company=company, branch=branch, created_by=user, name=it.get("name") or it["sku"], sku=it["sku"],
                barcode=it["barcode"], metal=it.get("metal", "gold"), purity=purity, gross_weight=gross,
                stone_weight=stone, making_type=it.get("making_type", "per_gram"),
                making_value=it.get("making_value", 0), wastage_percent=it.get("wastage_percent", 0),
                stone_price=it.get("stone_price", 0), huid=it.get("huid", ""), purchase_cost=amount, supplier=supplier)
            StockMovement.objects.create(company=company, branch=branch, product=product, kind="purchase",
                                         reference=inv.number, gross_weight=gross, fine_weight=product.fine_weight,
                                         direction=1, created_by=user)
        else:
            post_metal(company=company, branch=branch, user=user, metal=it.get("metal", "gold"), purity=purity,
                       kind="purchase", gross=gross, reference=inv.number)
        PurchaseItem.objects.create(invoice=inv, kind=it["kind"], metal=it.get("metal", "gold"), purity=purity,
                                    gross_weight=gross, stone_weight=stone, net_weight=net, fine_weight=fine,
                                    rate_per_gram=rate, extra_charges=extra, amount=amount, name=it.get("name", ""),
                                    product=product)
        subtotal += amount
    inv.subtotal = subtotal
    inv.gst_amount = J.q2(subtotal * gst_rate / D(100))
    inv.total = inv.subtotal + inv.gst_amount
    paid = J.q2(paid or 0)
    if paid > inv.total:
        raise ValidationError("Payment exceeds invoice total")
    inv.paid = paid
    inv.save()
    acc.post_purchase(inv, user)
    if paid > 0:
        _post_payment(company, branch, user, supplier, paid, method, inv.number)
    return inv


def _post_payment(company, branch, user, supplier, amount, method, ref):
    acc.post(company=company, branch=branch, user=user, kind="payment", reference=ref,
             narration=f"Supplier payment {supplier.name}",
             lines=[("2000", amount, 0, f"supplier:{supplier.id}"), (acc.METHOD_ACCOUNT[method], 0, amount)])


@transaction.atomic
def pay_supplier(*, user, branch, supplier, amount, method, date=None, reference=""):
    amount = J.q2(amount)
    if amount <= 0:
        raise ValidationError("Amount must be positive")
    p = SupplierPayment.objects.create(company=user.company, branch=branch, created_by=user, supplier=supplier,
                                       date=date or timezone.localdate(), amount=amount, method=method, reference=reference)
    _post_payment(user.company, branch, user, supplier, amount, method, reference or f"PAY-{str(p.id)[:8]}")
    return p


@transaction.atomic
def cancel_purchase(*, user, invoice, reason=""):
    inv = PurchaseInvoice.objects.select_for_update().get(pk=invoice.pk)
    if inv.status == "cancelled":
        raise ValidationError("Already cancelled")
    for it in inv.items.select_related("product"):
        if it.kind == "piece":
            p = Product.objects.select_for_update().get(pk=it.product_id)
            if p.status != Product.Status.AVAILABLE:
                raise ValidationError(f"{p.sku} is {p.status}; cannot cancel this purchase")
            p.status = Product.Status.VOID
            p.save(update_fields=["status", "updated_at"])
            StockMovement.objects.create(company=inv.company, branch=p.branch, product=p, kind="purchase_reversal",
                                         reference=inv.number, gross_weight=p.gross_weight, fine_weight=p.fine_weight,
                                         direction=-1, created_by=user)
        else:
            post_metal(company=inv.company, branch=inv.branch, user=user, metal=it.metal, purity=it.purity,
                       kind="purchase_reversal", gross=it.gross_weight, reference=inv.number, direction=-1)
    acc.reverse_by_reference(inv.company, ["purchase"], inv.number, user, f"Cancelled {inv.number}: {reason}")
    inv.status = "cancelled"
    inv.notes = (inv.notes + f" | cancelled: {reason}")[:300]
    inv.save(update_fields=["status", "notes", "updated_at"])
    return inv
