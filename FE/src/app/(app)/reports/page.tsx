"use client";
import { useState } from "react";
import { Download, Printer } from "lucide-react";
import { DataTable, DateRange, Err, downloadCsv, qs, useFetch } from "@/components/ui";

const REPORTS: [string, string][] = [
  ["sales-daily", "Sales - daily"], ["sales-category", "Sales - category / metal"], ["sales-employee", "Sales - employee"], ["branch-performance", "Branch performance"],
  ["purchases-supplier", "Purchases - supplier"], ["inventory-metal", "Inventory - metal & purity"], ["raw-metal-stock", "Raw metal / old gold stock"], ["inventory-ageing", "Stock ageing"],
  ["gold-summary", "Gold - gross / fine / wastage"], ["karigar-balance", "Karigar - metal pending"], ["customer-top", "Customers - purchases & dues"], ["customer-outstanding", "Customer outstanding"],
  ["supplier-payable", "Supplier payable"], ["repair-status", "Repairs by status"], ["scheme-summary", "Gold scheme summary"],
];
const MONEY = /value|total|taxable|gst|paid|outstanding|sales|purchases|subtotal|estimated|charges|collected/i;

export default function Reports() {
  const [name, setName] = useState(REPORTS[0][0]);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const q = qs({ from, to });
  const { data, error, loading } = useFetch<{ columns: string[]; rows: unknown[][] }>(`/reports/${name}/${q}`);
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Reports & analytics</h1>
      <div className="flex flex-wrap items-center gap-3">
        <select className="input w-72" value={name} onChange={(e) => setName(e.target.value)}>{REPORTS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
        <DateRange from={from} to={to} setFrom={setFrom} setTo={setTo} />
        <button className="btn btn-ghost" onClick={() => downloadCsv(`/reports/${name}/${qs({ from, to, export: "csv" })}`, `${name}.csv`).catch((e) => alert(e.message))}><Download size={16} /> CSV</button>
        <button className="btn btn-ghost" onClick={() => window.print()}><Printer size={16} /> Print / PDF</button>
      </div>
      <Err>{error}</Err>
      {loading && <div className="text-muted text-sm">Loading…</div>}
      {data && <DataTable columns={data.columns} rows={data.rows} money={data.columns.map((c, i) => (MONEY.test(c) && !/g$|weight/i.test(c) ? i : -1)).filter((i) => i >= 0)} />}
    </div>
  );
}
