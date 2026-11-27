"""GST working reports derived from posted invoices/purchases. These are *working* reports to assist a CA;
nothing here files returns. E-invoice / e-way bill need government (IRP / NIC) API access and are not integrated."""
from decimal import Decimal

from django.db.models import Count, Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounting import services as acc
from apps.accounts.permissions import ModulePermission
from apps.purchases.models import PurchaseInvoice
from apps.sales.models import Invoice, InvoiceItem

D = Decimal
Z = D(0)


class _G(APIView):
    module = "gst"
    permission_classes = [ModulePermission]

    def inv(self, request):
        u, p = request.user, request.query_params
        qs = Invoice.objects.filter(company_id=u.company_id)
        if not u.all_branches:
            qs = qs.filter(branch_id=u.branch_id)
        if p.get("from"):
            qs = qs.filter(created_at__date__gte=p["from"])
        if p.get("to"):
            qs = qs.filter(created_at__date__lte=p["to"])
        return qs

    def pur(self, request):
        u, p = request.user, request.query_params
        qs = PurchaseInvoice.objects.filter(company_id=u.company_id, status="posted")
        if not u.all_branches:
            qs = qs.filter(branch_id=u.branch_id)
        if p.get("from"):
            qs = qs.filter(date__gte=p["from"])
        if p.get("to"):
            qs = qs.filter(date__lte=p["to"])
        return qs

    @staticmethod
    def split(gst, intra=True):
        return ({"cgst": gst / 2, "sgst": gst / 2, "igst": Z} if intra else {"cgst": Z, "sgst": Z, "igst": gst})


class SalesRegister(_G):
    def get(self, request):
        intra = request.query_params.get("intra_state", "1") != "0"
        rows = []
        for i in self.inv(request).filter(status="posted").select_related("customer").order_by("created_at"):
            rows.append({"number": i.number, "date": i.created_at.date(), "customer": i.customer.name if i.customer else "Walk-in",
                         "gstin": i.customer.gstin if i.customer else "", "taxable": i.taxable_value, "gst_rate": i.gst_rate,
                         "gst": i.gst_amount, **self.split(i.gst_amount, intra), "total": i.grand_total})
        return Response({"rows": rows, "taxable": sum((r["taxable"] for r in rows), Z), "gst": sum((r["gst"] for r in rows), Z),
                         "note": "CGST/SGST vs IGST split depends on place of supply; toggle intra_state=0 for inter-state."})


class PurchaseRegister(_G):
    def get(self, request):
        rows = [{"number": p.number, "date": p.date, "supplier": p.supplier.name, "gstin": p.supplier.gstin,
                 "supplier_invoice": p.supplier_invoice_no, "taxable": p.subtotal, "gst": p.gst_amount, "total": p.total}
                for p in self.pur(request).select_related("supplier").order_by("date")]
        return Response({"rows": rows, "taxable": sum((r["taxable"] for r in rows), Z), "gst": sum((r["gst"] for r in rows), Z)})


class HsnSummary(_G):
    def get(self, request):
        hsn = request.user.company.hsn_code
        inv = self.inv(request).filter(status="posted")
        agg = inv.aggregate(n=Count("id"), t=Sum("taxable_value"), g=Sum("gst_amount"), v=Sum("grand_total"))
        w = InvoiceItem.objects.filter(invoice__in=inv).aggregate(w=Sum("net_weight"))["w"] or Z
        return Response({"rows": [{"hsn": hsn, "description": "Jewellery", "invoices": agg["n"], "net_weight_g": w,
                                   "taxable": agg["t"] or Z, "gst": agg["g"] or Z, "total": agg["v"] or Z}]})


class Gstr1(_G):
    """B2B (customers with GSTIN) vs B2C summary, plus credit notes (cancelled invoices)."""
    def get(self, request):
        posted = self.inv(request).filter(status="posted").select_related("customer")
        b2b = [{"gstin": i.customer.gstin, "invoice": i.number, "date": i.created_at.date(), "taxable": i.taxable_value,
                "gst": i.gst_amount, "total": i.grand_total} for i in posted if i.customer and i.customer.gstin]
        rest = [i for i in posted if not (i.customer and i.customer.gstin)]
        a = {"n": len(rest), "t": sum((i.taxable_value for i in rest), Z), "g": sum((i.gst_amount for i in rest), Z)}
        cn = [{"invoice": i.number, "date": i.created_at.date(), "taxable": i.taxable_value, "gst": i.gst_amount}
              for i in self.inv(request).filter(status="cancelled")]
        return Response({"b2b": b2b, "b2c": {"invoices": a["n"], "taxable": a["t"], "gst": a["g"]},
                         "cancelled_invoices": cn})


class Gstr3b(_G):
    def get(self, request):
        out = self.inv(request).filter(status="posted").aggregate(t=Sum("taxable_value"), g=Sum("gst_amount"))
        inn = self.pur(request).aggregate(t=Sum("subtotal"), g=Sum("gst_amount"))
        og, ig = out["g"] or Z, inn["g"] or Z
        return Response({"outward_taxable": out["t"] or Z, "output_tax": og, "inward_taxable": inn["t"] or Z,
                         "input_tax_credit": ig, "net_tax_payable": og - ig,
                         "note": "Working figures only. Verify ITC eligibility with your CA before filing."})


class Reconciliation(_G):
    """Compares GST on invoices with the Output GST ledger (account 2100)."""
    def get(self, request):
        company = request.user.company
        acc.ensure_accounts(company)
        p = request.query_params
        bal = acc.balances(company, None if request.user.all_branches else request.user.branch,
                           upto=p.get("to") or None, since=p.get("from") or None)
        a = acc.Account.objects.get(company=company, code="2100")
        d, c = bal.get(a.id, (Z, Z))
        ledger = c - d
        inv = self.inv(request).filter(status="posted").aggregate(g=Sum("gst_amount"))["g"] or Z
        return Response({"invoice_gst": inv, "ledger_output_gst": ledger, "difference": inv - ledger})
