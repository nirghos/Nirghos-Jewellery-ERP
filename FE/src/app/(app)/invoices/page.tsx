"use client";
import { Fragment, useCallback, useEffect, useState } from "react";
import { api, money, Page } from "@/lib/api";
import { can, useMe } from "@/components/shell";
import { ActionModal } from "@/components/ui";

type Inv = {
  id: string; number: string; customer_name: string; status: string; grand_total: string; paid: string; balance: string;
  created_at: string; items: { sku: string; product_name: string; net_weight: string; line_total: string }[];
};

export default function Invoices() {
  const me = useMe();
  const [rows, setRows] = useState<Inv[]>([]);
  const [q, setQ] = useState("");
  const [err, setErr] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const [paying, setPaying] = useState<Inv | null>(null);

  const load = useCallback(() => {
    api<Page<Inv>>(`/sales/invoices/?search=${encodeURIComponent(q)}`).then((d) => setRows(d.results)).catch((e) => setErr(e.message));
  }, [q]);
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); }, [load]);

  async function cancel(i: Inv) {
    const reason = prompt(`Cancel ${i.number}? Enter a reason (stock will be restored):`);
    if (!reason) return;
    try { await api(`/sales/invoices/${i.id}/cancel/`, { method: "POST", body: { reason } }); load(); } catch (e) { alert(e instanceof Error ? e.message : "Failed"); }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3"><h1 className="text-xl font-bold flex-1">Invoices</h1>
        <input className="input w-56" placeholder="Search number / customer" value={q} onChange={(e) => setQ(e.target.value)} /></div>
      {err && <div className="card p-3 text-red-600 text-sm">{err}</div>}
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-muted border-b border-line"><tr>{["Number", "Customer", "Total", "Paid", "Due", "Status", ""].map((h) => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}</tr></thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={7} className="px-4 py-6 text-muted">No invoices.</td></tr>}
            {rows.map((i) => (
              <Fragment key={i.id}>
                <tr className="border-b border-line">
                  <td className="px-4 py-3"><button className="text-gold font-semibold" onClick={() => setOpen(open === i.id ? null : i.id)}>{i.number}</button></td>
                  <td className="px-4 py-3">{i.customer_name || "Walk-in"}</td>
                  <td className="px-4 py-3">{money(i.grand_total)}</td><td className="px-4 py-3">{money(i.paid)}</td><td className="px-4 py-3">{money(i.balance)}</td>
                  <td className="px-4 py-3">{i.status}</td>
                  <td className="px-4 py-3 text-right space-x-3">
                    {i.status === "posted" && Number(i.balance) > 0 && can(me, "sales", "create") && <button className="text-gold font-semibold" onClick={() => setPaying(i)}>Receive payment</button>}
                    {i.status === "posted" && can(me, "sales", "approve") && <button className="text-red-600" onClick={() => cancel(i)}>Cancel</button>}</td>
                </tr>
                {open === i.id && <tr><td colSpan={7} className="px-4 py-3 bg-bg text-muted">
                  {i.items.map((x) => <div key={x.sku}>{x.sku} · {x.product_name} · {x.net_weight} g · {money(x.line_total)}</div>)}</td></tr>}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
      {paying && <ActionModal title={`Receive payment - ${paying.number}`} endpoint={`/sales/invoices/${paying.id}/pay/`} intro={`Balance due: ${money(paying.balance)}`}
        fields={[{ name: "amount", label: "Amount (₹)", type: "number", step: "0.01", required: true, default: paying.balance }, { name: "method", label: "Method", type: "select", required: true, default: "cash", options: ["cash", "upi", "card", "bank"].map((m) => ({ value: m, label: m })) }, { name: "reference", label: "Reference" }]}
        onClose={() => setPaying(null)} onDone={() => { setPaying(null); load(); }} />}
    </div>
  );
}
