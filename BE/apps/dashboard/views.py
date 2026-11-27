from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.accounts.permissions import ModulePermission
from apps.customers.models import Customer
from apps.products.models import Product
from apps.sales.models import Invoice


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
        return Response({
            "sales_today": tot(today), "sales_month": tot(month),
            "invoices_today": today.count(),
            "customer_due": tot(inv) - tot(inv, "paid"),
            "customers": Customer.objects.filter(company_id=u.company_id).count(),
            "stock": stock,
            "recent": list(inv.order_by("-created_at").values(
                "number", "grand_total", "created_at", "customer__name")[:8]),
        })
