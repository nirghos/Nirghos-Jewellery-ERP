"use client";
import { CrudPage } from "@/components/crud";
import { Tabs } from "@/components/ui";

type D = { id: string; code: string; name: string; category: string; metal: string; purity: string; expected_weight: string; bom: { material: string; weight: string; unit: string }[] };
type O = { id: string; number: string; design_name: string; quantity: number; karigar_name: string; stage: string; due_date: string; production_cost: string };
const STAGES = ["planned", "melting", "casting", "cutting", "filing", "stone_setting", "polishing", "finishing", "quality_check"];

export default function Manufacturing() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Manufacturing</h1>
      <Tabs tabs={[
        { label: "Production orders", content: (
          <CrudPage<O> bare title="Production order" endpoint="/manufacturing/orders" module="manufacturing" canEdit={false}
            filters={[{ name: "stage", label: "All stages", options: [...STAGES, "completed"].map((s) => ({ value: s, label: s })) }]}
            fields={[{ name: "design", label: "Design", type: "select", required: true, from: { endpoint: "/manufacturing/designs/", label: (r) => `${r.code} · ${r.name}` } },
              { name: "quantity", label: "Quantity", type: "number", default: "1" }, { name: "karigar", label: "Karigar", type: "select", from: { endpoint: "/karigars/", label: (r) => r.name } },
              { name: "due_date", label: "Due date", type: "date" }, { name: "notes", label: "Notes" }]}
            columns={[{ label: "Order", render: (r) => r.number }, { label: "Design", render: (r) => r.design_name }, { label: "Qty", render: (r) => r.quantity }, { label: "Karigar", render: (r) => r.karigar_name },
              { label: "Stage", render: (r) => <b>{r.stage.replace("_", " ")}</b> }, { label: "Due", render: (r) => r.due_date }]}
            rowActions={[
              { label: "Move stage", when: (r) => r.stage !== "completed", endpoint: (r) => `/manufacturing/orders/${r.id}/advance/`,
                fields: [{ name: "stage", label: "New stage", type: "select", required: true, options: STAGES.map((s) => ({ value: s, label: s })) },
                  { name: "weight_in", label: "Weight in (g)", type: "number", step: "0.001" }, { name: "weight_out", label: "Weight out (g)", type: "number", step: "0.001" }, { name: "note", label: "Note" }] },
              { label: "Complete → stock", perm: "approve", when: (r) => r.stage === "quality_check", endpoint: (r) => `/manufacturing/orders/${r.id}/complete/`,
                intro: "Creates the finished piece in inventory (design metal & purity).",
                fields: [{ name: "sku", label: "SKU", required: true }, { name: "barcode", label: "Barcode", required: true }, { name: "name", label: "Name" },
                  { name: "gross_weight", label: "Final gross weight (g)", type: "number", step: "0.001", required: true }, { name: "stone_weight", label: "Stone weight (g)", type: "number", step: "0.001", default: "0" },
                  { name: "production_cost", label: "Production cost (₹)", type: "number", step: "0.01" }, { name: "making_value", label: "Selling making charge / g", type: "number", step: "0.01" }] }]} />) },
        { label: "Designs & BOM", content: (
          <CrudPage<D> bare title="Design" endpoint="/manufacturing/designs" module="manufacturing"
            fields={[{ name: "code", label: "Design code", required: true }, { name: "name", label: "Name", required: true }, { name: "category", label: "Category" },
              { name: "metal", label: "Metal", type: "select", required: true, default: "gold", options: ["gold", "silver", "platinum"].map((m) => ({ value: m, label: m })) },
              { name: "purity", label: "Purity", type: "number", step: "0.001", default: "0.916" }, { name: "expected_weight", label: "Expected weight (g)", type: "number", step: "0.001", default: "0" },
              { name: "description", label: "Description", type: "textarea" }]}
            columns={[{ label: "Code", render: (r) => r.code }, { label: "Name", render: (r) => r.name }, { label: "Category", render: (r) => r.category }, { label: "Metal", render: (r) => `${r.metal} ${r.purity}` },
              { label: "Expected g", render: (r) => r.expected_weight }, { label: "BOM lines", render: (r) => r.bom.length }]} />) },
      ]} />
      <p className="text-xs text-muted">BOM lines can be managed through the API (<code>bom</code> array on a design); a visual BOM editor is planned.</p>
    </div>
  );
}
