from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounting import services as acc
from apps.accounts.permissions import ModulePermission
from apps.customers.models import Customer
from apps.karigars.views import holdings
from apps.products.models import Product
from apps.repairs.models import RepairJob
from apps.sales.models import Invoice

D = Decimal


class OverviewView(APIView):
    module = "dashboard"
    permission_classes = [ModulePermission]

    def get(self, request):
        u = request.user
        inv = Invoice.objects.filter(company_id=u.company_id, status="posted")
        prod = Product.objects.filter(company_id=u.company_id, status="available")
        if not u.all_branches:
            inv, prod = inv.filter(branch_id=u.branch_id), prod.filter(branch_id=u.branch_id)
        now = timezone.localtime()
        today = inv.filter(created_at__date=now.date())
        month = inv.filter(created_at__year=now.year, created_at__month=now.month)

        def tot(q, f="grand_total"):
            return q.aggregate(s=Sum(f))["s"] or 0

        stock = {r["metal"]: {"pieces": r["n"], "gross": r["g"], "net": r["nw"], "fine": r["f"]}
                 for r in prod.values("metal").annotate(
                     n=Count("id"), g=Sum("gross_weight"), nw=Sum("net_weight"), f=Sum("fine_weight"))}
        trend = list(inv.filter(created_at__date__gte=now.date() - timedelta(days=13))
                     .annotate(d=TruncDate("created_at")).values("d").annotate(t=Sum("grand_total")).order_by("d"))
        data = {
            "sales_today": tot(today), "sales_month": tot(month), "invoices_today": today.count(),
            "customer_due": tot(inv) - tot(inv, "paid"),
            "customers": Customer.objects.filter(company_id=u.company_id).count(),
            "stock": stock, "trend": trend,
            "recent": list(inv.order_by("-created_at").values("number", "grand_total", "created_at", "customer__name")[:8]),
        }
        # finance widgets only for roles allowed to see accounting
        from apps.accounts.permissions import MATRIX
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
