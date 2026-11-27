from decimal import Decimal as D

from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.companies.models import Branch, Company
from apps.customers.models import Customer
from apps.products.models import Product
from apps.purchases.tests import FlowBase

API = "/api/v1"


class KarigarFlow(FlowBase):
    def test_issue_return_close(self):
        self.c.post(f"{API}/purchases/invoices/", {"supplier": str(self.sup.id), "items": [
            {"kind": "metal", "metal": "gold", "purity": "0.995", "gross_weight": "200", "rate_per_gram": "6500"}]}, format="json")
        k = self.c.post(f"{API}/karigars/", {"name": "Ravi", "allowed_wastage_percent": "1.5"}, format="json").data
        job = self.c.post(f"{API}/karigars/jobcards/", {"karigar": k["id"], "description": "10 rings"}, format="json")
        self.assertEqual(job.status_code, 201, job.content)
        jid = job.data["id"]
        over = self.c.post(f"{API}/karigars/transactions/", {"jobcard": jid, "kind": "issue", "purity": "0.995", "gross_weight": "500"}, format="json")
        self.assertEqual(over.status_code, 400)  # more than stock
        ok = self.c.post(f"{API}/karigars/transactions/", {"jobcard": jid, "kind": "issue", "purity": "0.995", "gross_weight": "100"}, format="json")
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertEqual(D(ok.data["fine_weight"]), D("99.500"))
        bal = self.c.get(f"{API}/karigars/balances/").data
        self.assertEqual(D(bal["total"]), D("99.500"))
        fin = self.c.post(f"{API}/karigars/transactions/", {"jobcard": jid, "kind": "finished", "purity": "0.995", "gross_weight": "96",
                          "sku": "F1", "barcode": "F1", "name": "Ring"}, format="json")
        self.assertEqual(fin.status_code, 201, fin.content)
        self.assertTrue(Product.objects.filter(sku="F1", status="available").exists())
        self.c.post(f"{API}/karigars/transactions/", {"jobcard": jid, "kind": "scrap", "purity": "0.995", "gross_weight": "2"}, format="json")
        cl = self.c.post(f"{API}/karigars/jobcards/{jid}/close/", {"labour_charge": "5000"}, format="json")
        self.assertEqual(cl.status_code, 200, cl.content)
        self.assertEqual(D(cl.data["wastage_fine"]), D("1.990"))   # 99.5 - 96*0.995 - 2*0.995 = 1.99
        self.assertEqual(D(cl.data["allowed_wastage"]), D("1.493"))
        self.assertEqual(D(cl.data["excess_wastage"]), D("0.497"))
        pay = self.c.post(f"{API}/karigars/payments/", {"karigar": k["id"], "date": "2026-01-01", "amount": "2000", "method": "cash"}, format="json")
        self.assertEqual(pay.status_code, 201, pay.content)
        led = self.c.get(f"{API}/karigars/{k['id']}/ledger/").data
        self.assertEqual(D(led["labour_due"]), D("3000.00"))
        self.tb()


class OtherModules(FlowBase):
    def test_manufacturing(self):
        d = self.c.post(f"{API}/manufacturing/designs/", {"code": "D1", "name": "Ring A", "purity": "0.916", "bom": [
            {"material": "Gold", "weight": "5"}]}, format="json")
        self.assertEqual(d.status_code, 201, d.content)
        o = self.c.post(f"{API}/manufacturing/orders/", {"design": d.data["id"], "quantity": 1}, format="json").data
        early = self.c.post(f"{API}/manufacturing/orders/{o['id']}/complete/", {"sku": "M1", "barcode": "M1", "gross_weight": "5"}, format="json")
        self.assertEqual(early.status_code, 400)
        self.c.post(f"{API}/manufacturing/orders/{o['id']}/advance/", {"stage": "quality_check"}, format="json")
        done = self.c.post(f"{API}/manufacturing/orders/{o['id']}/complete/", {"sku": "M1", "barcode": "M1", "gross_weight": "5"}, format="json")
        self.assertEqual(done.status_code, 200, done.content)
        self.assertTrue(Product.objects.filter(sku="M1").exists())

    def test_repair_flow(self):
        r = self.c.post(f"{API}/repairs/", {"customer": str(self.cust.id), "item_description": "Chain", "problem": "broken"}, format="json").data
        skip = self.c.post(f"{API}/repairs/{r['id']}/set-status/", {"status": "ready"}, format="json")
        self.assertEqual(skip.status_code, 400)
        self.c.post(f"{API}/repairs/{r['id']}/estimate/", {"amount": "500"}, format="json")
        self.c.post(f"{API}/repairs/{r['id']}/advance/", {"amount": "200", "method": "cash"}, format="json")
        for st in ["approved", "in_progress", "quality_check", "ready"]:
            x = self.c.post(f"{API}/repairs/{r['id']}/set-status/", {"status": st}, format="json")
            self.assertEqual(x.status_code, 200, x.content)
        dl = self.c.post(f"{API}/repairs/{r['id']}/deliver/", {"amount_paid": "300", "method": "upi"}, format="json")
        self.assertEqual(dl.status_code, 200, dl.content)
        self.assertEqual(dl.data["status"], "delivered")
        self.tb()

    def test_hallmark_and_huid(self):
        p = Product.objects.create(company=self.co, branch=self.br, name="R", sku="H1", barcode="H1", gross_weight=D("5"))
        ahc = self.c.post(f"{API}/hallmark/centres/", {"name": "AHC1", "charge_per_piece": "45"}, format="json").data
        rq = self.c.post(f"{API}/hallmark/requests/", {"centre": ahc["id"], "product_ids": [str(p.id)]}, format="json")
        self.assertEqual(rq.status_code, 201, rq.content)
        self.c.post(f"{API}/hallmark/requests/{rq.data['id']}/dispatch/")
        bad = self.c.post(f"{API}/hallmark/requests/{rq.data['id']}/receive/", {"results": [{"item": rq.data["items"][0]["id"], "result": "pass", "huid": "AB"}]}, format="json")
        self.assertEqual(bad.status_code, 400)
        ok = self.c.post(f"{API}/hallmark/requests/{rq.data['id']}/receive/", {"results": [{"item": rq.data["items"][0]["id"], "result": "pass", "huid": "ab12cd"}]}, format="json")
        self.assertEqual(ok.status_code, 200, ok.content)
        p.refresh_from_db()
        self.assertEqual(p.huid, "AB12CD")
        self.assertEqual(len(self.c.get(f"{API}/hallmark/huid/?q=ab12").data), 1)

    def test_scheme(self):
        plan = self.c.post(f"{API}/schemes/plans/", {"name": "P", "months": 2, "monthly_amount": "1000", "bonus_amount": "500"}, format="json").data
        m = self.c.post(f"{API}/schemes/members/", {"plan": plan["id"], "customer": str(self.cust.id), "start_date": "2026-01-01"}, format="json")
        self.assertEqual(m.status_code, 201, m.content)
        mid = m.data["id"]
        self.assertEqual(self.c.post(f"{API}/schemes/members/{mid}/pay/", {"amount": "999"}, format="json").status_code, 400)
        self.assertEqual(self.c.post(f"{API}/schemes/members/{mid}/redeem/").status_code, 400)  # not matured
        for _ in range(2):
            self.assertEqual(self.c.post(f"{API}/schemes/members/{mid}/pay/", {"method": "upi"}, format="json").status_code, 200)
        self.assertEqual(self.c.post(f"{API}/schemes/members/{mid}/pay/", {}, format="json").status_code, 400)
        r = self.c.post(f"{API}/schemes/members/{mid}/redeem/")
        self.assertEqual(D(r.data["redeemed_value"]), D("2500.00"))
        self.tb()

    def test_stones_carat_validation_and_state(self):
        s = self.c.post(f"{API}/stones/", {"kind": "diamond", "stock_no": "D1", "carat": "0.500", "clarity": "VS1"}, format="json")
        self.assertEqual(s.status_code, 201, s.content)
        self.assertEqual(self.c.post(f"{API}/stones/", {"stock_no": "D1", "carat": "1"}, format="json").status_code, 400)
        self.assertEqual(self.c.post(f"{API}/stones/", {"stock_no": "D2", "carat": "-1"}, format="json").status_code, 400)
        self.assertEqual(self.c.post(f"{API}/stones/{s.data['id']}/return/").status_code, 400)

    def test_hr_payroll(self):
        e = self.c.post(f"{API}/hr/employees/", {"code": "E1", "name": "Amit", "base_salary": "31000"}, format="json").data
        for day in range(1, 11):
            self.c.post(f"{API}/hr/attendance/", {"employee": e["id"], "date": f"2026-03-{day:02d}", "status": "present"}, format="json")
        self.c.post(f"{API}/hr/attendance/", {"employee": e["id"], "date": "2026-03-01", "status": "half"}, format="json")  # update, not dup
        self.c.post(f"{API}/hr/advances/", {"employee": e["id"], "date": "2026-03-02", "amount": "1000"}, format="json")
        g = self.c.post(f"{API}/hr/payslips/generate/", {"month": "2026-03"}, format="json")
        self.assertEqual(g.data["generated"], 1)
        slip = self.c.get(f"{API}/hr/payslips/").data["results"][0]
        self.assertEqual(D(slip["paid_days"]), D("9.5"))
        self.assertEqual(D(slip["gross"]), D("9500.00"))      # 31000 * 9.5 / 31
        self.assertEqual(D(slip["net"]), D("8500.00"))
        self.assertEqual(self.c.post(f"{API}/hr/payslips/{slip['id']}/pay/", {"method": "bank"}, format="json").status_code, 200)
        self.assertEqual(self.c.post(f"{API}/hr/payslips/{slip['id']}/pay/", {"method": "bank"}, format="json").status_code, 400)
        self.tb()

    def test_gst_and_reports(self):
        p = Product.objects.create(company=self.co, branch=self.br, name="R", sku="G1", barcode="G1", gross_weight=D("8"),
                                   making_type="fixed", making_value=D("1000"))
        self.c.post(f"{API}/sales/invoices/", {"product_ids": [str(p.id)]}, format="json")
        self.c.post(f"{API}/purchases/invoices/", {"supplier": str(self.sup.id), "items": [
            {"kind": "metal", "purity": "0.995", "gross_weight": "10", "rate_per_gram": "6000"}]}, format="json")
        r3 = self.c.get(f"{API}/gst/gstr3b/").data
        self.assertEqual(D(r3["output_tax"]), D("1470.00"))
        self.assertEqual(D(r3["input_tax_credit"]), D("1800.00"))
        self.assertEqual(D(self.c.get(f"{API}/gst/reconciliation/").data["difference"]), D("0"))
        self.assertEqual(len(self.c.get(f"{API}/gst/sales-register/").data["rows"]), 1)
        for name in ["sales-daily", "sales-category", "sales-employee", "purchases-supplier", "inventory-metal", "raw-metal-stock",
                     "inventory-ageing", "gold-summary", "karigar-balance", "customer-top", "customer-outstanding",
                     "supplier-payable", "branch-performance", "repair-status", "scheme-summary"]:
            r = self.c.get(f"{API}/reports/{name}/")
            self.assertEqual(r.status_code, 200, f"{name}: {r.content[:200]}")
            self.assertEqual(self.c.get(f"{API}/reports/{name}/?export=csv").status_code, 200, name)
        self.assertEqual(self.c.get(f"{API}/reports/nope/").status_code, 404)
        self.assertEqual(self.c.get(f"{API}/dashboard/overview/").status_code, 200)

    def test_users_and_audit(self):
        u = self.c.post(f"{API}/users/", {"username": "s1", "password": "Str0ng#Pass1", "role": "sales_staff", "branch": str(self.br.id)}, format="json")
        self.assertEqual(u.status_code, 201, u.content)
        self.assertNotIn("password", u.data)
        self.assertEqual(self.c.post(f"{API}/users/", {"username": "s2", "password": "short", "role": "sales_staff"}, format="json").status_code, 400)
        other = Company.objects.create(name="X")
        ob = Branch.objects.create(company=other, name="ob", code="O")
        self.assertEqual(self.c.post(f"{API}/users/", {"username": "s3", "password": "Str0ng#Pass1", "role": "sales_staff", "branch": str(ob.id)}, format="json").status_code, 400)
        self.assertEqual(self.c.patch(f"{API}/users/{self.owner.id}/", {"role": "sales_staff"}, format="json").status_code, 400)
        self.assertGreater(len(self.c.get(f"{API}/settings/audit-logs/").data), 0)


class Security(FlowBase):
    def client_for(self, role):
        u = User.objects.create_user(f"u_{role}", password="x", company=self.co, branch=self.br, role=role)
        c = APIClient()
        c.force_authenticate(u)
        return c

    def test_role_boundaries(self):
        staff = self.client_for("sales_staff")
        for path in ["/accounting/trial-balance/", "/hr/employees/", "/purchases/invoices/", "/karigars/", "/gst/gstr3b/",
                     "/reports/sales-daily/", "/users/", "/settings/audit-logs/"]:
            self.assertEqual(staff.get(API + path).status_code, 403, path)
        self.assertEqual(self.client_for("auditor").post(f"{API}/customers/", {"name": "x"}, format="json").status_code, 403)
        hr = self.client_for("hr_manager")
        self.assertEqual(hr.get(f"{API}/hr/employees/").status_code, 200)
        self.assertEqual(hr.get(f"{API}/accounting/trial-balance/").status_code, 403)
        acct = self.client_for("accountant")
        self.assertEqual(acct.get(f"{API}/accounting/trial-balance/").status_code, 200)
        self.assertEqual(acct.get(f"{API}/hr/employees/").status_code, 403)

    def test_cross_company_isolation(self):
        other = Company.objects.create(name="Other")
        ob = Branch.objects.create(company=other, name="ob", code="O")
        Customer.objects.create(company=other, name="Secret")
        self.assertEqual(self.c.get(f"{API}/customers/").data["count"], 1)
        r = self.c.post(f"{API}/products/", {"name": "x", "sku": "Z", "barcode": "Z", "gross_weight": "1", "branch": str(ob.id)}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_journal_must_balance_and_reverse(self):
        accts = {a["code"]: a["id"] for a in self.c.get(f"{API}/accounting/accounts/").data}
        bad = self.c.post(f"{API}/accounting/entries/", {"type": "journal", "lines": [
            {"account": accts["1000"], "debit": "100"}, {"account": accts["4000"], "credit": "90"}]}, format="json")
        self.assertEqual(bad.status_code, 400)
        e = self.c.post(f"{API}/accounting/entries/", {"type": "expense", "amount": "250", "account": accts["5200"], "narration": "tea"}, format="json")
        self.assertEqual(e.status_code, 201, e.content)
        rv = self.c.post(f"{API}/accounting/entries/{e.data['id']}/reverse/", {}, format="json")
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(self.c.post(f"{API}/accounting/entries/{e.data['id']}/reverse/", {}, format="json").status_code, 400)
        self.assertEqual(D(self.c.get(f"{API}/accounting/profit-loss/").data["net_profit"]), D("0"))
