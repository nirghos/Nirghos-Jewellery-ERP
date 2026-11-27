"use client";
import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { api, money } from "@/lib/api";
import { CrudPage } from "@/components/crud";
import { can, useMe } from "@/components/shell";
import { ActionModal, DataTable, Err, Field, Modal, Tabs, useFetch } from "@/components/ui";

type Inv = { id: string; number: string; supplier_name: string; supplier_invoice_no: string; date: string; status: string; subtotal: string; gst_amount: string; total: string; paid: string; balance: string };
type Item = Record<string, string>;
const emptyItem = (): Item => ({ kind: "metal", metal: "gold", purity: "0.916", gross_weight: "", stone_weight: "0", rate_per_gram: "", extra_charges: "0", name: "", sku: "", barcode: "", making_type: "per_gram", making_value: "0" });

function PurchaseForm({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { data: sups } = useFetch<{ results: { id: string; name: string }[] }>("/suppliers/");
  const [h, setH] = useState({ supplier: "", date: "", supplier_invoice_no: "", paid: "0", method: "cash", gst_rate: "" });
  const [items, setItems] = useState<Item[]>([emptyItem()]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const upd = (i: number, k: string, v: string) => setItems(items.map((x, j) => (j === i ? { ...x, [k]: v } : x)));

  async function save(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setErr("");
    try {
      const body = {
        ...Object.fromEntries(Object.entries(h).filter(([, v]) => v !== "")),
        items: items.map((x) => Object.fromEntries(Object.entries(x).filter(([k, v]) => v !== "" && (x.kind === "piece" || !["sku", "barcode", "name", "making_type", "making_value"].includes(k))))),
      };
      await api("/purchases/invoices/", { method: "POST", body });
      onDone();
    } catch (e) { setErr(e instanceof Error ? e.message : "Failed"); } finally { setBusy(false); }
  }
  return (
    <Modal title="New purchase" onClose={onClose}>
      <form onSubmit={save} className="space-y-4">
        <div className="grid sm:grid-cols-3 gap-3 text-sm">
          <label className="space-y-1"><span className="text-muted">Supplier *</span>
            <select className="input" required value={h.supplier} onChange={(e) => setH({ ...h, supplier: e.target.value })}>
              <option value="">Select…</option>{sups?.results.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
          <label className="space-y-1"><span className="text-muted">Date</span><input type="date" className="input" value={h.date} onChange={(e) => setH({ ...h, date: e.target.value })} /></label>
          <label className="space-y-1"><span className="text-muted">Supplier invoice no.</span><input className="input" value={h.supplier_invoice_no} onChange={(e) => setH({ ...h, supplier_invoice_no: e.target.value })} /></label>
          <label className="space-y-1"><span className="text-muted">GST % (blank = company default)</span><input type="number" step="0.01" className="input" value={h.gst_rate} onChange={(e) => setH({ ...h, gst_rate: e.target.value })} /></label>
          <label className="space-y-1"><span className="text-muted">Paid now (₹)</span><input type="number" min="0" step="0.01" className="input" value={h.paid} onChange={(e) => setH({ ...h, paid: e.target.value })} /></label>
          <label className="space-y-1"><span className="text-muted">Pay by</span>
            <select className="input" value={h.method} onChange={(e) => setH({ ...h, method: e.target.value })}>{["cash", "upi", "bank", "card"].map((m) => <option key={m}>{m}</option>)}</select></label>
        </div>
        {items.map((x, i) => (
          <div key={i} className="border border-line rounded-xl p-3 space-y-2">
            <div className="flex gap-2 items-center">
              <select className="input w-44" value={x.kind} onChange={(e) => upd(i, "kind", e.target.value)}>
                <option value="metal">Raw metal (bar/scrap)</option><option value="piece">Jewellery piece</option></select>
              <select className="input w-32" value={x.metal} onChange={(e) => upd(i, "metal", e.target.value)}>{["gold", "silver", "platinum"].map((m) => <option key={m}>{m}</option>)}</select>
              <div className="flex-1" />
              {items.length > 1 && <button type="button" aria-label="Remove item" onClick={() => setItems(items.filter((_, j) => j !== i))}><Trash2 size={16} /></button>}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-sm">
              {([["purity", "Purity (0.916)"], ["gross_weight", "Gross g"], ["stone_weight", "Stone g"], ["rate_per_gram", "Rate / g"], ["extra_charges", "Extra ₹"]] as const).map(([k, l]) => (
                <label key={k} className="space-y-1"><span className="text-muted">{l}</span>
                  <input className="input" type="number" step="0.001" required={k !== "stone_weight" && k !== "extra_charges"} value={x[k]} onChange={(e) => upd(i, k, e.target.value)} /></label>
              ))}
            </div>
            {x.kind === "piece" && (
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-sm">
                {([["name", "Name"], ["sku", "SKU *"], ["barcode", "Barcode *"], ["making_value", "Selling making value"]] as const).map(([k, l]) => (
                  <label key={k} className="space-y-1"><span className="text-muted">{l}</span>
                    <input className="input" required={k === "sku" || k === "barcode"} type={k === "making_value" ? "number" : "text"} value={x[k]} onChange={(e) => upd(i, k, e.target.value)} /></label>
                ))}
                <label className="space-y-1"><span className="text-muted">Making type</span>
                  <select className="input" value={x.making_type} onChange={(e) => upd(i, "making_type", e.target.value)}>
                    <option value="per_gram">per gram</option><option value="percent">percent</option><option value="fixed">fixed</option></select></label>
              </div>
            )}
          </div>
        ))}
        <button type="button" className="btn btn-ghost" onClick={() => setItems([...items, emptyItem()])}><Plus size={16} /> Add item</button>
        <p className="text-xs text-muted">Net/fine weight, amounts and GST are calculated by the server. Pieces go into stock; raw metal goes to the metal stock ledger.</p>
        {err && <p className="text-sm text-red-600">{err}</p>}
        <div className="flex justify-end gap-2"><button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button><button className="btn" disabled={busy}>{busy ? "Saving…" : "Save purchase"}</button></div>
      </form>
    </Modal>
  );
}

function Ledger() {
  const [sup, setSup] = useState("");
  const { data: sups } = useFetch<{ results: { id: string; name: string }[] }>("/suppliers/");
  const { data, error } = useFetch<{ rows: Record<string, string>[]; outstanding: string }>(sup ? `/purchases/ledger/?supplier=${sup}` : null, [sup]);
  return (
    <div className="space-y-3">
      <select className="input w-64" value={sup} onChange={(e) => setSup(e.target.value)}><option value="">Select supplier…</option>{sups?.results.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>
      <Err>{error}</Err>
      {data && <><DataTable columns={["Date", "Description", "Purchase", "Paid", "Balance"]} money={[2, 3, 4]} rows={data.rows.map((r) => [r.date, r.description, r.purchase, r.paid, r.balance])} />
        <div className="font-bold">Outstanding: {money(data.outstanding)}</div></>}
    </div>
  );
}

export default function Purchases() {
  const me = useMe();
  const [form, setForm] = useState(false);
  const [pay, setPay] = useState(false);
  const [n, setN] = useState(0);
  const payFields: Field[] = [
    { name: "supplier", label: "Supplier", type: "select", required: true, from: { endpoint: "/suppliers/", label: (r) => r.name } },
    { name: "amount", label: "Amount (₹)", type: "number", step: "0.01", required: true },
    { name: "method", label: "Method", type: "select", required: true, default: "bank", options: ["cash", "upi", "bank", "card"].map((m) => ({ value: m, label: m })) },
    { name: "date", label: "Date", type: "date" }, { name: "reference", label: "Reference" },
  ];
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3"><h1 className="text-xl font-bold flex-1">Purchases</h1>
        {can(me, "purchases", "create") && <><button className="btn btn-ghost" onClick={() => setPay(true)}>Pay supplier</button><button className="btn" onClick={() => setForm(true)}><Plus size={16} /> New purchase</button></>}</div>
      <Tabs tabs={[
        { label: "Purchase invoices", content: (
          <CrudPage<Inv> key={n} bare title="Purchase" endpoint="/purchases/invoices" module="purchases" canAdd={false} canEdit={false} fields={[]}
            filters={[{ name: "status", label: "All status", options: [{ value: "posted", label: "posted" }, { value: "cancelled", label: "cancelled" }] }]}
            columns={[{ label: "No.", render: (r) => r.number }, { label: "Date", render: (r) => r.date }, { label: "Supplier", render: (r) => r.supplier_name },
              { label: "Bill no.", render: (r) => r.supplier_invoice_no }, { label: "Subtotal", render: (r) => money(r.subtotal) }, { label: "GST", render: (r) => money(r.gst_amount) },
              { label: "Total", render: (r) => money(r.total) }, { label: "Paid", render: (r) => money(r.paid) }, { label: "Status", render: (r) => r.status }]}
            rowActions={[{ label: "Cancel", perm: "approve", danger: true, when: (r) => r.status === "posted", endpoint: (r) => `/purchases/invoices/${r.id}/cancel/`,
              fields: [{ name: "reason", label: "Reason", required: true }], intro: "Cancelling reverses stock and accounting entries." }]} />) },
        { label: "Supplier payments", content: <CrudPage<{ id: string; supplier_name: string; date: string; amount: string; method: string; reference: string }> key={"p" + n} bare title="Payment" endpoint="/purchases/payments" module="purchases" canAdd={false} canEdit={false} fields={[]}
            columns={[{ label: "Date", render: (r) => r.date }, { label: "Supplier", render: (r) => r.supplier_name }, { label: "Amount", render: (r) => money(r.amount) }, { label: "Method", render: (r) => r.method }, { label: "Ref", render: (r) => r.reference }]} /> },
        { label: "Supplier ledger", content: <Ledger /> },
      ]} />
      {form && <PurchaseForm onClose={() => setForm(false)} onDone={() => { setForm(false); setN(n + 1); }} />}
      {pay && <ActionModal title="Pay supplier" endpoint="/purchases/payments/" fields={payFields} onClose={() => setPay(false)} onDone={() => { setPay(false); setN(n + 1); }} />}
    </div>
  );
}
