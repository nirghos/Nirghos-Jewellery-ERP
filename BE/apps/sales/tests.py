from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.companies.models import Branch, Company
from apps.core import jewellery as J
from apps.products.models import MetalRate, Product


class JewelleryMath(TestCase):
    def test_22k_fine_weight(self):
        net = J.net_weight("8.500", "0.500")
        self.assertEqual(net, Decimal("8.000"))
        self.assertEqual(J.fine_weight(net, "0.916"), Decimal("7.328"))

    def test_stone_exceeds_gross(self):
        with self.assertRaises(ValueError):
            J.net_weight("1", "2")


class BillingTests(TestCase):
    def setUp(self):
        self.co = Company.objects.create(name="T", gst_rate=Decimal("3.00"))
        self.br = Branch.objects.create(company=self.co, name="B", code="B1")
        self.other = Branch.objects.create(company=self.co, name="O", code="B2")
        self.user = User.objects.create_user("u", password="x", company=self.co, branch=self.br, role="sales_staff")
        MetalRate.objects.create(company=self.co, metal="gold", purity=Decimal("0.916"), rate_per_gram=Decimal("6000"))
        self.p = Product.objects.create(company=self.co, branch=self.br, name="Ring", sku="R1", barcode="B1",
                                        gross_weight=Decimal("8.5"), stone_weight=Decimal("0.5"),
                                        making_type="per_gram", making_value=Decimal("500"))
        self.c = APIClient()
        self.c.force_authenticate(self.user)

    def test_sale_calculates_on_backend_and_blocks_double_sale(self):
        r = self.c.post("/api/v1/sales/invoices/", {"product_ids": [str(self.p.id)], "payments": [
            {"method": "cash", "amount": "1000"}], "total": "1"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        # metal 8.000*6000=48000, making 8*500=4000 -> taxable 52000, gst 1560
        self.assertEqual(Decimal(r.data["taxable_value"]), Decimal("52000.00"))
        self.assertEqual(Decimal(r.data["gst_amount"]), Decimal("1560.00"))
        self.assertEqual(Decimal(r.data["grand_total"]), Decimal("53560.00"))
        self.p.refresh_from_db()
        self.assertEqual(self.p.status, "sold")
        r2 = self.c.post("/api/v1/sales/invoices/", {"product_ids": [str(self.p.id)]}, format="json")
        self.assertEqual(r2.status_code, 400)

    def test_cancel_restores_stock(self):
        r = self.c.post("/api/v1/sales/invoices/", {"product_ids": [str(self.p.id)]}, format="json")
        owner = User.objects.create_user("o", password="x", company=self.co, branch=self.br, role="owner")
        self.c.force_authenticate(owner)
        r = self.c.post(f"/api/v1/sales/invoices/{r.data['id']}/cancel/", {"reason": "test"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.p.refresh_from_db()
        self.assertEqual(self.p.status, "available")

    def test_sales_staff_cannot_cancel_or_see_cost(self):
        r = self.c.post("/api/v1/sales/invoices/", {"product_ids": [str(self.p.id)]}, format="json")
        self.assertEqual(self.c.post(f"/api/v1/sales/invoices/{r.data['id']}/cancel/").status_code, 403)
        self.p.status = "available"
        self.p.save()
        data = self.c.get("/api/v1/products/").data["results"][0]
        self.assertNotIn("purchase_cost", data)

    def test_branch_isolation(self):
        Product.objects.create(company=self.co, branch=self.other, name="X", sku="X1", barcode="X1",
                               gross_weight=Decimal("1"))
        skus = [p["sku"] for p in self.c.get("/api/v1/products/").data["results"]]
        self.assertEqual(skus, ["R1"])
