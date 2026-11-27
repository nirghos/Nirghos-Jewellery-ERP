from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounting import services as acc
from apps.accounts.permissions import MATRIX, ModulePermission, can_see_cost
from apps.customers.models import Customer
from apps.diamonds.models import Stone
from apps.karigars.views import holdings
from apps.products.models import Product
from apps.purchases.models import PurchaseInvoice, SupplierPayment
from apps.repairs.models import RepairJob
from apps.sales.models import Invoice, InvoiceItem

D = Decimal


def _sum(q, f):
    return q.aggregate(s=Sum(f))["s"] or D(0)


class OverviewView(APIView):
    module = "dashboard"
    permission_classes = [ModulePermission]

    def get(self, request):
        u = request.user
        cost = can_see_cost(u)
        inv = Invoice.objects.filter(company_id=u.company_id, status="posted")
        prod = Product.objects.filter(company_id=u.company_id)
        pur = PurchaseInvoice.objects.filter(company_id=u.company_id, status="posted")
        if not u.all_branches:
            inv, prod, pur = inv.filter(branch_id=u.branch_id), prod.filter(branch_id=u.branch_id), pur.filter(branch_id=u.branch_id)
        avail = prod.filter(status="available")
        now = timezone.localtime()
        today = inv.filter(created_at__date=now.date())
        month = inv.filter(created_at__year=now.year, created_at__month=now.month)
        prev_end = now.replace(day=1) - timedelta(days=1)
        prev_month = inv.filter(created_at__year=prev_end.year, created_at__month=prev_end.month)
        since = now.date() - timedelta(days=29)

        stock = {r["metal"]: {"pieces": r["n"], "gross": r["g"], "net": r["nw"], "fine": r["f"]}
                 for r in avail.values("metal").annotate(
                     n=Count("id"), g=Sum("gross_weight"), nw=Sum("net_weight"), f=Sum("fine_weight"))}
        trend = list(inv.filter(created_at__date__gte=since).annotate(d=TruncDate("created_at"))
                     .values("d").annotate(t=Sum("grand_total")).order_by("d"))
        items = InvoiceItem.objects.filter(invoice__in=month)
        by_cat = [{"name": r["product__category__name"] or "Other", "value": r["v"]}
                  for r in items.values("product__category__name").annotate(v=Sum("line_total")).order_by("-v")]
        top = [{"name": r["product__name"], "category": r["product__category__name"] or "", "value": r["v"], "pieces": r["n"]}
               for r in items.values("product__name", "product__category__name")
               .annotate(v=Sum("line_total"), n=Count("id")).order_by("-v")[:5]]

        # categories running low (2 or fewer pieces available)
        cats = {}
        for p in prod.values("category__name", "status"):
            c = cats.setdefault(p["category__name"] or "Uncategorised", {"total": 0, "available": 0})
            c["total"] += 1
            c["available"] += p["status"] == "available"
        low = sorted(({"name": k, "pieces": v["available"]} for k, v in cats.items() if v["available"] <= 2 and v["total"] > 0),
                     key=lambda x: x["pieces"])[:6]

        tx = [{"type": "Sale", "ref": i.number, "amount": i.grand_total, "at": i.created_at} for i in inv.order_by("-created_at")[:6]]
        tx += [{"type": "Purchase", "ref": p.number, "amount": p.total, "at": p.created_at} for p in pur.order_by("-created_at")[:6]]
        tx += [{"type": "Payment", "ref": p.reference or f"PAY-{str(p.id)[:6].upper()}", "amount": p.amount, "at": p.created_at}
               for p in SupplierPayment.objects.filter(company_id=u.company_id).order_by("-created_at")[:4]]
        tx.sort(key=lambda x: x["at"], reverse=True)

        data = {
            "sales_today": _sum(today, "grand_total"), "sales_month": _sum(month, "grand_total"),
            "sales_prev_month": _sum(prev_month, "grand_total"), "invoices_today": today.count(),
            "customer_due": _sum(inv, "grand_total") - _sum(inv, "paid"),
            "customers": Customer.objects.filter(company_id=u.company_id).count(),
            "new_customers_month": Customer.objects.filter(company_id=u.company_id, created_at__year=now.year,
                                                           created_at__month=now.month).count(),
            "stock": stock, "trend": trend, "sales_by_category": by_cat, "top_products": top, "low_stock": low,
            "recent_transactions": tx[:8],
            "stones": Stone.objects.filter(company_id=u.company_id, status="available").aggregate(n=Count("id"), ct=Sum("carat")),
            "recent": list(inv.order_by("-created_at").values("number", "grand_total", "created_at", "customer__name")[:8]),
        }
        if cost:
            gp = sum((it.line_total - it.product.purchase_cost for it in items.select_related("product")), D(0)) - _sum(month, "discount")
            data.update({
                "purchases_month": _sum(pur.filter(date__year=now.year, date__month=now.month), "total"),
                "gross_profit_month": gp,
                "stock_value": _sum(avail, "purchase_cost"),
                "purchase_trend": list(pur.filter(date__gte=since).values("date").annotate(t=Sum("total")).order_by("date")),
            })
        if u.all_branches:
            sales_b = {r["branch__name"]: r["t"] for r in month.values("branch__name").annotate(t=Sum("grand_total"))}
            pur_b = {}
            if cost:
                pur_b = {r["branch__name"]: r["t"] for r in
                         pur.filter(date__year=now.year, date__month=now.month).values("branch__name").annotate(t=Sum("total"))}
            data["branch_performance"] = [{"name": n, "sales": sales_b.get(n, 0), "purchase": pur_b.get(n, 0)}
                                          for n in sorted(set(sales_b) | set(pur_b))]
        if u.is_superuser or "view" in MATRIX["accounting"].get(u.role, set()):
            acc.ensure_accounts(u.company)
            b = acc.balances(u.company, None if u.all_branches else u.branch)
            ids = {a.code: a.id for a in acc.Account.objects.filter(company=u.company, code__in=["1000", "1010", "2000"])}

            def net(code, sign=1):
                d, c = b.get(ids.get(code), (D(0), D(0)))
                return sign * (d - c)
            data.update({"cash_in_hand": net("1000"), "bank_balance": net("1010"), "supplier_due": net("2000", -1)})
        data["karigar_fine_pending"] = sum(holdings(u.company).values(), D(0))
        data["pending_repairs"] = RepairJob.objects.filter(company_id=u.company_id).exclude(status__in=["delivered", "cancelled"]).count()
        return Response(data)
