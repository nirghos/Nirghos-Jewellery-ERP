from decimal import Decimal as D
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.companies.models import Branch, Company
from apps.customers.models import Customer
from apps.products.models import MetalRate, Product
from apps.suppliers.models import Supplier


class FlowBase(TestCase):
    def setUp(self):
        self.co = Company.objects.create(name="T", gst_rate=D("3.00"))
        self.br = Branch.objects.create(company=self.co, name="B", code="B1")
        self.owner = User.objects.create_user("o", password="x", company=self.co, branch=self.br, role="owner")
        self.c = APIClient()
        self.c.force_authenticate(self.owner)
        MetalRate.objects.create(company=self.co, metal="gold", purity=D("0.916"), rate_per_gram=D("6000"))
        self.sup = Supplier.objects.create(company=self.co, name="S")
        self.cust = Customer.objects.create(company=self.co, name="C")

    def tb(self):
        r = self.c.get("/api/v1/accounting/trial-balance/").data
        self.assertEqual(r["total_debit"], r["total_credit"])
        return r


class PurchaseFlow(FlowBase):
    def test_purchase_adds_stock_and_posts_ledger_and_cancels(self):
        r = self.c.post("/api/v1/purchases/invoices/", {"supplier": str(self.sup.id), "paid": "1000", "items": [
            {"kind": "piece", "sku": "P1", "barcode": "P1", "name": "Ring", "purity": "0.916", "gross_weight": "10",
             "stone_weight": "1", "rate_per_gram": "6000"},
            {"kind": "metal", "metal": "gold", "purity": "0.995", "gross_weight": "50", "rate_per_gram": "6500"},
        ]}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        # 9*6000=54000 + 50*6500=325000 => 379000, GST 3% = 11370
        self.assertEqual(D(r.data["subtotal"]), D("379000.00"))
        self.assertEqual(D(r.data["total"]), D("390370.00"))
        p = Product.objects.get(sku="P1")
        self.assertEqual((p.net_weight, p.status), (D("9.000"), "available"))
        self.tb()
        led = self.c.get(f"/api/v1/purchases/ledger/?supplier={self.sup.id}").data
        self.assertEqual(D(led["outstanding"]), D("389370.00"))
        pay = self.c.post("/api/v1/purchases/payments/", {"supplier": str(self.sup.id), "amount": "9370", "method": "bank",
                                                          "date": "2026-01-01"}, format="json")
        self.assertEqual(pay.status_code, 201, pay.content)
        parties = self.c.get("/api/v1/accounting/parties/?kind=payable").data
        self.assertEqual(D(parties["total"]), D("380000.00"))
        c = self.c.post(f"/api/v1/purchases/invoices/{r.data['id']}/cancel/", {"reason": "x"}, format="json")
        self.assertEqual(c.status_code, 200, c.content)
        p.refresh_from_db()
        self.assertEqual(p.status, "void")
        self.tb()

    def test_duplicate_sku_rejected_atomically(self):
        Product.objects.create(company=self.co, branch=self.br, name="x", sku="P1", barcode="Z", gross_weight=D("1"))
        r = self.c.post("/api/v1/purchases/invoices/", {"supplier": str(self.sup.id), "items": [
            {"kind": "metal", "purity": "0.995", "gross_weight": "5", "rate_per_gram": "6000"},
            {"kind": "piece", "sku": "P1", "barcode": "N", "purity": "0.916", "gross_weight": "5", "rate_per_gram": "1"}]},
            format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.c.get("/api/v1/purchases/invoices/").data["count"], 0)

    def test_other_company_supplier_rejected(self):
        co2 = Company.objects.create(name="Other")
        s2 = Supplier.objects.create(company=co2, name="X")
        r = self.c.post("/api/v1/purchases/invoices/", {"supplier": str(s2.id), "items": []}, format="json")
        self.assertEqual(r.status_code, 400)


class OldGoldAndSale(FlowBase):
    def test_exchange_flow(self):
        og = self.c.post("/api/v1/old-gold/", {"customer": str(self.cust.id), "gross_weight": "10", "stone_weight": "0",
                                                "touch": "0.750", "rate_per_gram": "6500", "deduction_percent": "2"}, format="json")
        self.assertEqual(og.status_code, 201, og.content)
        self.assertEqual(D(og.data["fine_weight"]), D("7.500"))
        self.assertEqual(D(og.data["value"]), D("47775.00"))  # 7.5*6500*0.98
        p = Product.objects.create(company=self.co, branch=self.br, name="R", sku="R", barcode="R",
                                   gross_weight=D("8"), making_type="fixed", making_value=D("1000"))
        inv = self.c.post("/api/v1/sales/invoices/", {"product_ids": [str(p.id)], "old_gold_ids": [og.data["id"]]}, format="json")
        self.assertEqual(inv.status_code, 201, inv.content)
        # metal 8*6000=48000 + making 1000 = 49000, gst 1470, grand = 50470 - 47775 = 2695
        self.assertEqual(D(inv.data["grand_total"]), D("2695.00"))
        self.tb()
        again = self.c.post("/api/v1/sales/invoices/", {"product_ids": [str(p.id)], "old_gold_ids": [og.data["id"]]}, format="json")
        self.assertEqual(again.status_code, 400)
        pay = self.c.post(f"/api/v1/sales/invoices/{inv.data['id']}/pay/", {"amount": "2695", "method": "cash"}, format="json")
        self.assertEqual(pay.status_code, 200, pay.content)
        self.assertEqual(D(pay.data["balance"]), D("0.00"))
        self.tb()
        cx = self.c.post(f"/api/v1/sales/invoices/{inv.data['id']}/cancel/", {"reason": "t"}, format="json")
        self.assertEqual(cx.status_code, 200)
        self.tb()
        self.assertEqual(self.c.get(f"/api/v1/old-gold/{og.data['id']}/").data["status"], "received")
        pl = self.c.get("/api/v1/accounting/profit-loss/").data
        self.assertEqual(D(pl["net_profit"]), D("0"))
        bs = self.c.get("/api/v1/accounting/balance-sheet/").data
        self.assertTrue(bs["balanced"])

    def test_melting(self):
        og = self.c.post("/api/v1/old-gold/", {"gross_weight": "10", "touch": "0.750", "rate_per_gram": "6500",
                                                "customer_name": "Walk"}, format="json").data
        r = self.c.post("/api/v1/old-gold/melt/", {"receipt_ids": [og["id"]], "recovered_gross": "7.6",
                                                    "recovered_purity": "0.980"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(D(r.data["loss_fine"]), D("0.052"))
