import csv
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounting import services as acc
from apps.accounting.models import Account
from apps.accounts.permissions import ModulePermission, can_see_cost
from apps.karigars.models import JobCard, Karigar
from apps.karigars.views import holdings
from apps.products.models import MetalLedger, Product
from apps.purchases.models import PurchaseInvoice
from apps.repairs.models import RepairJob
from apps.sales.models import Invoice, InvoiceItem
from apps.schemes.models import SchemeMember

D = Decimal


def _scope(request, qs, branch_field="branch_id", date_field=None):
    u, p = request.user, request.query_params
    qs = qs.filter(company_id=u.company_id)
    if not u.all_branches:
        qs = qs.filter(**{branch_field: u.branch_id})
    elif p.get("branch"):
        qs = qs.filter(**{branch_field: p["branch"]})
    if date_field:
        if p.get("from"):
            qs = qs.filter(**{f"{date_field}__date__gte" if "created" in date_field else f"{date_field}__gte": p["from"]})
        if p.get("to"):
            qs = qs.filter(**{f"{date_field}__date__lte" if "created" in date_field else f"{date_field}__lte": p["to"]})
    return qs


# each report returns (columns, rows); rows are lists aligned with columns
def sales_daily(r):
    q = _scope(r, Invoice.objects.filter(status="posted"), date_field="created_at")
    from django.db.models.functions import TruncDate
    rows = q.annotate(d=TruncDate("created_at")).values("d").annotate(n=Count("id"), t=Sum("taxable_value"), g=Sum("gst_amount"),
                                                                    tot=Sum("grand_total")).order_by("d")
    return ["Date", "Invoices", "Taxable", "GST", "Total"], [[x["d"], x["n"], x["t"], x["g"], x["tot"]] for x in rows]


def sales_category(r):
    q = InvoiceItem.objects.filter(invoice__status="posted", invoice__company_id=r.user.company_id)
    if not r.user.all_branches:
        q = q.filter(invoice__branch_id=r.user.branch_id)
    p = r.query_params
    if p.get("from"):
        q = q.filter(invoice__created_at__date__gte=p["from"])
    if p.get("to"):
        q = q.filter(invoice__created_at__date__lte=p["to"])
    rows = q.values("product__category__name", "product__metal").annotate(n=Count("id"), w=Sum("net_weight"), v=Sum("line_total")).order_by("-v")
    return ["Category", "Metal", "Pieces", "Net weight g", "Sales value"], [[x["product__category__name"] or "Uncategorised", x["product__metal"], x["n"], x["w"], x["v"]] for x in rows]


def sales_employee(r):
    q = _scope(r, Invoice.objects.filter(status="posted"), date_field="created_at")
    rows = q.values("created_by__username").annotate(n=Count("id"), tot=Sum("grand_total")).order_by("-tot")
    return ["Employee", "Invoices", "Total"], [[x["created_by__username"] or "-", x["n"], x["tot"]] for x in rows]


def purchases_supplier(r):
    q = _scope(r, PurchaseInvoice.objects.filter(status="posted"), date_field="date")
    rows = q.values("supplier__name").annotate(n=Count("id"), sub=Sum("subtotal"), g=Sum("gst_amount"), tot=Sum("total"),
                                               paid=Sum("paid")).order_by("-tot")
    return ["Supplier", "Bills", "Subtotal", "GST", "Total", "Paid at purchase"], [[x["supplier__name"], x["n"], x["sub"], x["g"], x["tot"], x["paid"]] for x in rows]


def inventory_metal(r):
    q = _scope(r, Product.objects.filter(status="available"))
    rows = q.values("metal", "purity").annotate(n=Count("id"), g=Sum("gross_weight"), nw=Sum("net_weight"), f=Sum("fine_weight")).order_by("metal", "-purity")
    return ["Metal", "Purity", "Pieces", "Gross g", "Net g", "Fine g"], [[x["metal"], x["purity"], x["n"], x["g"], x["nw"], x["f"]] for x in rows]


def raw_metal(r):
    q = _scope(r, MetalLedger.objects.all())
    rows = q.values("metal", "purity").annotate(g=Sum("gross_weight"), f=Sum("fine_weight")).order_by("metal", "-purity")
    return ["Metal", "Purity", "Gross g", "Fine g"], [[x["metal"], x["purity"], x["g"], x["f"]] for x in rows if x["g"]]


def inventory_ageing(r):
    q = _scope(r, Product.objects.filter(status="available"))
    now, buckets = timezone.now(), {"0-30 days": [0, D(0)], "31-90 days": [0, D(0)], "91-180 days": [0, D(0)], "180+ days": [0, D(0)]}
    for p in q:
        age = (now - p.created_at).days
        k = "0-30 days" if age <= 30 else "31-90 days" if age <= 90 else "91-180 days" if age <= 180 else "180+ days"
        buckets[k][0] += 1
        buckets[k][1] += p.fine_weight
    return ["Age", "Pieces", "Fine g"], [[k, v[0], v[1]] for k, v in buckets.items()]


def gold_summary(r):
    q = _scope(r, Product.objects.filter(status="available", metal="gold"))
    a = q.aggregate(g=Sum("gross_weight"), n=Sum("net_weight"), f=Sum("fine_weight"))
    raw = _scope(r, MetalLedger.objects.filter(metal="gold")).aggregate(g=Sum("gross_weight"), f=Sum("fine_weight"))
    held = sum(holdings(r.user.company).values(), D(0))
    waste = JobCard.objects.filter(company=r.user.company, status="closed").aggregate(w=Sum("wastage_fine"), e=Sum("excess_wastage"))
    z = D(0)
    return ["Item", "Gross g", "Fine g"], [
        ["Jewellery in stock (gross/net/fine)", a["g"] or z, a["f"] or z], ["Raw / old gold stock", raw["g"] or z, raw["f"] or z],
        ["With karigars (fine)", "", held], ["Karigar wastage to date (fine)", "", waste["w"] or z],
        ["Of which excess over allowed (fine)", "", waste["e"] or z]]


def karigar_balance(r):
    h = holdings(r.user.company)
    return ["Karigar", "Fine metal with karigar g"], [[k.name, h.get(k.id, D(0))] for k in Karigar.objects.filter(company=r.user.company, is_active=True)]


def customer_top(r):
    q = _scope(r, Invoice.objects.filter(status="posted"), date_field="created_at")
    rows = q.values("customer__name").annotate(n=Count("id"), t=Sum("grand_total"), p=Sum("paid")).order_by("-t")[:100]
    return ["Customer", "Invoices", "Purchases", "Paid", "Outstanding"], [[x["customer__name"] or "Walk-in", x["n"], x["t"], x["p"], x["t"] - x["p"]] for x in rows]


def branch_performance(r):
    q = Invoice.objects.filter(company=r.user.company, status="posted")
    if not r.user.all_branches:
        q = q.filter(branch=r.user.branch)
    p = r.query_params
    if p.get("from"):
        q = q.filter(created_at__date__gte=p["from"])
    if p.get("to"):
        q = q.filter(created_at__date__lte=p["to"])
    rows = q.values("branch__name").annotate(n=Count("id"), t=Sum("grand_total")).order_by("-t")
    return ["Branch", "Invoices", "Sales"], [[x["branch__name"], x["n"], x["t"]] for x in rows]


def repair_status(r):
    q = _scope(r, RepairJob.objects.all())
    rows = q.values("status").annotate(n=Count("id"), e=Sum("estimate"), c=Sum("final_charges"))
    return ["Status", "Jobs", "Estimated", "Final charges"], [[x["status"], x["n"], x["e"], x["c"]] for x in rows]


def scheme_summary(r):
    q = _scope(r, SchemeMember.objects.all())
    rows = q.values("status", "plan__name").annotate(n=Count("id"), paid=Sum("installments__amount"))
    return ["Status", "Plan", "Members", "Collected"], [[x["status"], x["plan__name"], x["n"], x["paid"] or 0] for x in rows]


def receivables(r):
    return _parties(r, "receivable")


def payables(r):
    return _parties(r, "payable")


def _parties(r, kind):
    from apps.accounting.views import Parties
    v = Parties()
    v.request = r
    data = v.get(r).data
    return ["Party", "Outstanding"], [[x["name"], x["outstanding"]] for x in data["rows"]]


REPORTS = {
    "sales-daily": ("sales", sales_daily), "sales-category": ("sales", sales_category), "sales-employee": ("sales", sales_employee),
    "purchases-supplier": ("purchases", purchases_supplier), "inventory-metal": ("inventory", inventory_metal),
    "raw-metal-stock": ("inventory", raw_metal), "inventory-ageing": ("inventory", inventory_ageing),
    "gold-summary": ("gold", gold_summary), "karigar-balance": ("karigar", karigar_balance),
    "customer-top": ("customer", customer_top), "customer-outstanding": ("customer", receivables),
    "supplier-payable": ("supplier", payables), "branch-performance": ("branch", branch_performance),
    "repair-status": ("repair", repair_status), "scheme-summary": ("scheme", scheme_summary),
}


class ReportList(APIView):
    module = "reports"
    permission_classes = [ModulePermission]

    def get(self, request):
        return Response([{"key": k, "group": g} for k, (g, _) in REPORTS.items()])


class ReportView(APIView):
    module = "reports"
    permission_classes = [ModulePermission]

    def get(self, request, name):
        if name not in REPORTS:
            raise NotFound("Unknown report")
        cols, rows = REPORTS[name][1](request)
        if request.query_params.get("export") == "csv":
            resp = HttpResponse(content_type="text/csv")
            resp["Content-Disposition"] = f'attachment; filename="{name}.csv"'
            w = csv.writer(resp)
            w.writerow(cols)
            for row in rows:
                # neutralise spreadsheet formula injection
                w.writerow([("'" + str(c)) if isinstance(c, str) and c[:1] in "=+-@" else c for c in row])
            return resp
        return Response({"report": name, "columns": cols, "rows": rows})
