"use client";
import { useEffect, useState } from "react";
import { api, money } from "@/lib/api";

type Overview = {
  cash_in_hand?: string; bank_balance?: string; supplier_due?: string; karigar_fine_pending: string; pending_repairs: number; trend: { d: string; t: string }[];
  sales_today: string; sales_month: string; invoices_today: number; customer_due: string; customers: number;
  stock: Record<string, { pieces: number; gross: string; net: string; fine: string }>;
  recent: { number: string; grand_total: string; created_at: string; customer__name: string | null }[];
};

export default function Dashboard() {
  const [d, setD] = useState<Overview | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api<Overview>("/dashboard/overview/").then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return <div className="card p-4 text-red-600">{err}</div>;
  if (!d) return <div className="text-muted">Loading…</div>;

  const tiles = [
    ["Sales today", money(d.sales_today)], ["Sales this month", money(d.sales_month)],
    ["Invoices today", String(d.invoices_today)], ["Customer due", money(d.customer_due)],
    ["Customers", String(d.customers)], ["Pending repairs", String(d.pending_repairs)], ["Fine gold with karigars", `${d.karigar_fine_pending} g`],
    ...(d.cash_in_hand !== undefined ? [["Cash in hand", money(d.cash_in_hand)], ["Bank balance", money(d.bank_balance)], ["Supplier due", money(d.supplier_due)]] : []),
  ];
  const max = Math.max(1, ...d.trend.map((x) => Number(x.t)));
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Dashboard</h1>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {tiles.map(([l, v]) => (
          <div key={l} className="card p-4"><div className="text-sm text-muted">{l}</div><div className="text-2xl font-bold mt-1">{v}</div></div>
        ))}
      </div>
      <div className="card p-4">
        <h2 className="font-semibold mb-3">Sales - last 14 days</h2>
        {d.trend.length === 0 ? <div className="text-sm text-muted">No sales yet.</div> : (
          <div className="flex items-end gap-2 h-32">
            {d.trend.map((x) => (<div key={x.d} className="flex-1 flex flex-col items-center gap-1" title={`${x.d}: ${money(x.t)}`}>
              <div className="w-full bg-gold rounded-t" style={{ height: `${(Number(x.t) / max) * 100}%` }} /><span className="text-[10px] text-muted">{x.d.slice(8)}</span></div>))}
          </div>)}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card p-4">
          <h2 className="font-semibold mb-3">Stock on hand</h2>
          <table className="w-full text-sm">
            <thead className="text-muted text-left"><tr><th>Metal</th><th>Pieces</th><th>Gross g</th><th>Net g</th><th>Fine g</th></tr></thead>
            <tbody>
              {Object.entries(d.stock).map(([m, s]) => (
                <tr key={m} className="border-t border-line"><td className="py-2 capitalize">{m}</td><td>{s.pieces}</td><td>{s.gross}</td><td>{s.net}</td><td>{s.fine}</td></tr>
              ))}
              {Object.keys(d.stock).length === 0 && <tr><td colSpan={5} className="py-3 text-muted">No stock yet.</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="card p-4">
          <h2 className="font-semibold mb-3">Recent invoices</h2>
          <ul className="text-sm divide-y divide-line">
            {d.recent.map((r) => (
              <li key={r.number} className="py-2 flex justify-between"><span>{r.number} · {r.customer__name || "Walk-in"}</span><b>{money(r.grand_total)}</b></li>
            ))}
            {d.recent.length === 0 && <li className="py-2 text-muted">No invoices yet.</li>}
          </ul>
        </div>
      </div>
    </div>
  );
}
