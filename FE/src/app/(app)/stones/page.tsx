"use client";
import { money } from "@/lib/api";
import { CrudPage } from "@/components/crud";
import { useMe } from "@/components/shell";

type S = { id: string; kind: string; stock_no: string; name: string; shape: string; carat: string; color: string; clarity: string; cut: string; cert_no: string; lab: string; lot_no: string; purchase_price?: string; selling_price: string; status: string };

export default function Stones() {
  const me = useMe();
  return (
    <CrudPage<S> title="Diamonds & gemstones" endpoint="/stones" module="diamonds" canEdit
      filters={[{ name: "kind", label: "All kinds", options: [{ value: "diamond", label: "Diamond" }, { value: "gemstone", label: "Gemstone" }] },
        { name: "status", label: "All status", options: ["available", "issued", "set", "sold"].map((s) => ({ value: s, label: s })) }]}
      fields={[{ name: "kind", label: "Kind", type: "select", required: true, default: "diamond", options: [{ value: "diamond", label: "Diamond" }, { value: "gemstone", label: "Gemstone" }] },
        { name: "stock_no", label: "Stock no.", required: true }, { name: "name", label: "Stone name (gemstone)" }, { name: "shape", label: "Shape" },
        { name: "carat", label: "Carat", type: "number", step: "0.001", required: true }, { name: "color", label: "Colour" }, { name: "clarity", label: "Clarity" }, { name: "cut", label: "Cut" },
        { name: "cert_no", label: "Certificate no." }, { name: "lab", label: "Lab (GIA / IGI ...)" }, { name: "dimensions", label: "Dimensions" }, { name: "lot_no", label: "Parcel / lot no." },
        ...(me.can_see_cost ? [{ name: "purchase_price", label: "Purchase price (₹)", type: "number" as const, step: "0.01", default: "0" }] : []),
        { name: "selling_price", label: "Selling price (₹)", type: "number", step: "0.01", default: "0" }]}
      columns={[{ label: "Stock no.", render: (r) => r.stock_no }, { label: "Kind", render: (r) => `${r.kind}${r.name ? " · " + r.name : ""}` }, { label: "Shape", render: (r) => r.shape }, { label: "Carat", render: (r) => r.carat },
        { label: "Colour/Clarity", render: (r) => `${r.color} ${r.clarity}` }, { label: "Cert", render: (r) => `${r.lab} ${r.cert_no}` }, { label: "Lot", render: (r) => r.lot_no },
        ...(me.can_see_cost ? [{ label: "Cost", render: (r: S) => money(r.purchase_price) }] : []), { label: "Price", render: (r) => money(r.selling_price) }, { label: "Status", render: (r) => r.status }]}
      rowActions={[
        { label: "Issue", when: (r) => r.status === "available", endpoint: (r) => `/stones/${r.id}/issue/`, fields: [{ name: "karigar", label: "Karigar", type: "select", required: true, from: { endpoint: "/karigars/", label: (k) => k.name } }] },
        { label: "Return", when: (r) => r.status === "issued", endpoint: (r) => `/stones/${r.id}/return/`, confirm: "Mark stone as returned?" },
        { label: "Set in piece", when: (r) => r.status === "issued" || r.status === "available", endpoint: (r) => `/stones/${r.id}/set/`, fields: [{ name: "product", label: "Jewellery piece", type: "select", required: true, from: { endpoint: "/products/", label: (p) => `${p.sku} · ${p.name}` } }] },
        { label: "Sell", perm: "approve", when: (r) => r.status === "available", endpoint: (r) => `/stones/${r.id}/sell/`, confirm: "Mark this loose stone as sold?" }]} />
  );
}
