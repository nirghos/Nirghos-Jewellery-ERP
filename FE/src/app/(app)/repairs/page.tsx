"use client";
import { money } from "@/lib/api";
import { CrudPage } from "@/components/crud";

type R = { id: string; number: string; kind: string; customer_name: string; customer_phone: string; item_description: string; status: string; estimate: string; advance: string; final_charges: string; due_date: string };
const FLOW = ["received", "inspection", "estimated", "approved", "in_progress", "quality_check", "ready", "delivered"];
const next = (s: string) => FLOW[FLOW.indexOf(s) + 1];
const METHODS = ["cash", "upi", "card", "bank"].map((m) => ({ value: m, label: m }));

export default function Repairs() {
  return (
    <div className="space-y-4">
      <CrudPage<R> title="Repairs & custom orders" endpoint="/repairs" module="repairs" canEdit={false} addLabel="New job"
        filters={[{ name: "status", label: "All status", options: [...FLOW, "cancelled"].map((s) => ({ value: s, label: s })) }, { name: "kind", label: "All kinds", options: [{ value: "repair", label: "repair" }, { value: "custom", label: "custom" }] }]}
        fields={[{ name: "kind", label: "Kind", type: "select", required: true, default: "repair", options: [{ value: "repair", label: "Repair" }, { value: "custom", label: "Custom order" }] },
          { name: "customer", label: "Customer (optional)", type: "select", from: { endpoint: "/customers/", label: (r) => r.name } }, { name: "customer_name", label: "Customer name" }, { name: "customer_phone", label: "Phone" },
          { name: "item_description", label: "Item", required: true }, { name: "weight_in", label: "Weight received (g)", type: "number", step: "0.001", default: "0" }, { name: "problem", label: "Problem / requirement" },
          { name: "karigar", label: "Assign karigar", type: "select", from: { endpoint: "/karigars/", label: (r) => r.name } }, { name: "due_date", label: "Due date", type: "date" }]}
        columns={[{ label: "No.", render: (r) => r.number }, { label: "Kind", render: (r) => r.kind }, { label: "Customer", render: (r) => `${r.customer_name} ${r.customer_phone}` }, { label: "Item", render: (r) => r.item_description },
          { label: "Status", render: (r) => <b>{r.status.replace("_", " ")}</b> }, { label: "Estimate", render: (r) => money(r.estimate) }, { label: "Advance", render: (r) => money(r.advance) }, { label: "Final", render: (r) => money(r.final_charges) }, { label: "Due", render: (r) => r.due_date }]}
        rowActions={[
          { label: "Estimate", when: (r) => ["received", "inspection", "estimated"].includes(r.status), endpoint: (r) => `/repairs/${r.id}/estimate/`, fields: [{ name: "amount", label: "Estimated charges (₹)", type: "number", step: "0.01", required: true }] },
          { label: "Advance", perm: "create", when: (r) => !["delivered", "cancelled"].includes(r.status), endpoint: (r) => `/repairs/${r.id}/advance/`,
            fields: [{ name: "amount", label: "Advance (₹)", type: "number", step: "0.01", required: true }, { name: "method", label: "Method", type: "select", required: true, default: "cash", options: METHODS }] },
          { label: "Next status", when: (r) => !["ready", "delivered", "cancelled"].includes(r.status), endpoint: (r) => `/repairs/${r.id}/set-status/`,
            fields: [{ name: "status", label: "Move to", type: "select", required: true, options: FLOW.slice(1, 7).map((s) => ({ value: s, label: s })) }, { name: "note", label: "Note" }],
            initial: (r) => ({ status: next(r.status) }) },
          { label: "Deliver", perm: "approve", when: (r) => r.status === "ready", endpoint: (r) => `/repairs/${r.id}/deliver/`, intro: "Balance after advance is collected now or booked as customer due (needs a linked customer).",
            fields: [{ name: "final_charges", label: "Final charges (₹)", type: "number", step: "0.01" }, { name: "amount_paid", label: "Paid now (₹)", type: "number", step: "0.01", default: "0" }, { name: "method", label: "Method", type: "select", required: true, default: "cash", options: METHODS }],
            initial: (r) => ({ final_charges: r.estimate }) },
        ]} />
    </div>
  );
}
