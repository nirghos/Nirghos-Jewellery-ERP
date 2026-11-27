"use client";
import { money } from "@/lib/api";
import { CrudPage } from "@/components/crud";
import { Tabs } from "@/components/ui";

type P = { id: string; name: string; months: number; monthly_amount: string; flexible: boolean; bonus_amount: string; is_active: boolean };
type M = { id: string; number: string; plan_name: string; customer_name: string; start_date: string; status: string; paid_total: string; paid_count: number; matured: boolean; maturity_value: string; missed: number; redeemed_value: string };
const METHODS = ["cash", "upi", "card", "bank"].map((m) => ({ value: m, label: m }));

export default function Schemes() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Gold saving schemes</h1>
      <Tabs tabs={[
        { label: "Members", content: (
          <CrudPage<M> bare title="Scheme member" endpoint="/schemes/members" module="schemes" canEdit={false} addLabel="Enrol member"
            filters={[{ name: "status", label: "All status", options: ["active", "redeemed", "refunded"].map((s) => ({ value: s, label: s })) }]}
            fields={[{ name: "plan", label: "Plan", type: "select", required: true, from: { endpoint: "/schemes/plans/?is_active=true", label: (p) => `${p.name} (${p.months} months)` } },
              { name: "customer", label: "Customer", type: "select", required: true, from: { endpoint: "/customers/", label: (c) => `${c.name} ${c.phone}` } }, { name: "start_date", label: "Start date", type: "date", required: true }]}
            columns={[{ label: "No.", render: (r) => r.number }, { label: "Customer", render: (r) => r.customer_name }, { label: "Plan", render: (r) => r.plan_name }, { label: "Paid", render: (r) => `${r.paid_count} (${money(r.paid_total)})` },
              { label: "Missed", render: (r) => <span className={r.missed > 0 ? "text-red-600 font-semibold" : ""}>{r.missed}</span> }, { label: "Maturity value", render: (r) => money(r.maturity_value) },
              { label: "Status", render: (r) => (r.status === "active" && r.matured ? "matured" : r.status) }]}
            rowActions={[
              { label: "Collect", perm: "create", when: (r) => r.status === "active" && !r.matured, endpoint: (r) => `/schemes/members/${r.id}/pay/`, fields: [{ name: "amount", label: "Amount (blank = plan amount)", type: "number", step: "0.01" }, { name: "method", label: "Method", type: "select", required: true, default: "cash", options: METHODS }] },
              { label: "Redeem", perm: "approve", when: (r) => r.status === "active" && r.matured, endpoint: (r) => `/schemes/members/${r.id}/redeem/`, confirm: "Redeem this matured scheme? Apply the value to jewellery at billing." },
              { label: "Refund", perm: "approve", danger: true, when: (r) => r.status === "active", endpoint: (r) => `/schemes/members/${r.id}/refund/`, confirm: "Close early and refund the amount paid in cash (no bonus)?" }]} />) },
        { label: "Plans", content: (
          <CrudPage<P> bare title="Scheme plan" endpoint="/schemes/plans" module="schemes"
            fields={[{ name: "name", label: "Plan name", required: true }, { name: "months", label: "Number of months", type: "number", required: true, default: "11" }, { name: "monthly_amount", label: "Monthly amount (₹)", type: "number", step: "0.01", default: "0" },
              { name: "flexible", label: "Flexible amount each month", type: "checkbox" }, { name: "bonus_amount", label: "Bonus on maturity (₹)", type: "number", step: "0.01", default: "0" }, { name: "terms", label: "Terms", type: "textarea" }, { name: "is_active", label: "Active", type: "checkbox", default: true }]}
            columns={[{ label: "Plan", render: (r) => r.name }, { label: "Months", render: (r) => r.months }, { label: "Monthly", render: (r) => (r.flexible ? "Flexible" : money(r.monthly_amount)) }, { label: "Bonus", render: (r) => money(r.bonus_amount) }, { label: "Active", render: (r) => (r.is_active ? "Yes" : "No") }]} />) },
      ]} />
    </div>
  );
}
