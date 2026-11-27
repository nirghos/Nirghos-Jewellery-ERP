"use client";
import { useState } from "react";
import { api, money } from "@/lib/api";
import { CrudPage } from "@/components/crud";
import { can, useMe } from "@/components/shell";
import { ActionModal, DataTable, Err, Field, Tabs, useFetch } from "@/components/ui";

type K = { id: string; name: string; phone: string; skill: string; allowed_wastage_percent: string; is_active: boolean };
type J = { id: string; number: string; karigar_name: string; description: string; status: string; due_date: string; issued_fine: string; returned_fine: string; wastage_fine: string; allowed_wastage: string; excess_wastage: string; labour_charge: string };
type T = { id: string; karigar_name: string; job: string; kind: string; metal: string; purity: string; gross_weight: string; fine_weight: string; created_at: string };

const jobSel = { endpoint: "/karigars/jobcards/?status=open", label: (r: { number: string; karigar_name: string }) => `${r.number} · ${r.karigar_name}` };
const txnFields: Field[] = [
  { name: "jobcard", label: "Job card", type: "select", required: true, from: jobSel },
  { name: "kind", label: "Type", type: "select", required: true, default: "issue", options: [
    { value: "issue", label: "Issue metal to karigar" }, { value: "return", label: "Metal returned" }, { value: "scrap", label: "Scrap / filings returned" }, { value: "finished", label: "Finished jewellery received" }] },
  { name: "metal", label: "Metal", type: "select", required: true, default: "gold", options: ["gold", "silver", "platinum"].map((m) => ({ value: m, label: m })) },
  { name: "purity", label: "Purity (0.995 / 0.916)", type: "number", step: "0.001", required: true },
  { name: "gross_weight", label: "Gross weight (g)", type: "number", step: "0.001", required: true },
  { name: "note", label: "Note" },
  { name: "name", label: "Piece name (finished only)" }, { name: "sku", label: "SKU (finished only)" }, { name: "barcode", label: "Barcode (finished only)" },
  { name: "stone_weight", label: "Stone weight g (finished only)", type: "number", step: "0.001", default: "0" },
  { name: "making_value", label: "Making charge value (finished only)", type: "number", step: "0.01", default: "0" },
];

function Balances() {
  const { data, error } = useFetch<{ rows: { name: string; fine_with_karigar: string }[]; total: string }>("/karigars/balances/");
  return <div className="space-y-3"><Err>{error}</Err>{data && <><DataTable columns={["Karigar", "Fine metal with karigar (g)"]} rows={data.rows.map((r) => [r.name, r.fine_with_karigar])} /><div className="font-bold">Total with karigars: {data.total} g fine</div></>}</div>;
}

export default function Karigars() {
  const me = useMe();
  const [txn, setTxn] = useState(false);
  const [n, setN] = useState(0);
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3"><h1 className="text-xl font-bold flex-1">Karigar management</h1>
        {can(me, "karigars", "create") && <button className="btn" onClick={() => setTxn(true)}>Metal issue / return</button>}</div>
      <Tabs tabs={[
        { label: "Job cards", content: (
          <CrudPage<J> key={"j" + n} bare title="Job card" endpoint="/karigars/jobcards" module="karigars" canEdit={false}
            filters={[{ name: "status", label: "All", options: ["open", "closed", "cancelled"].map((s) => ({ value: s, label: s })) }]}
            fields={[{ name: "karigar", label: "Karigar", type: "select", required: true, from: { endpoint: "/karigars/?is_active=true", label: (r) => r.name } },
              { name: "description", label: "Work description", required: true }, { name: "due_date", label: "Due date", type: "date" }]}
            columns={[{ label: "Job", render: (r) => r.number }, { label: "Karigar", render: (r) => r.karigar_name }, { label: "Work", render: (r) => r.description },
              { label: "Issued fine", render: (r) => r.issued_fine }, { label: "Returned fine", render: (r) => r.returned_fine }, { label: "Wastage", render: (r) => r.wastage_fine },
              { label: "Excess", render: (r) => <span className={Number(r.excess_wastage) > 0 ? "text-red-600" : ""}>{r.excess_wastage}</span> }, { label: "Labour", render: (r) => money(r.labour_charge) }, { label: "Status", render: (r) => r.status }]}
            rowActions={[{ label: "Close job", perm: "approve", when: (r) => r.status === "open", endpoint: (r) => `/karigars/jobcards/${r.id}/close/`,
              intro: "Closing computes wastage = issued fine − returned fine. This cannot be undone.", fields: [{ name: "labour_charge", label: "Labour charge (₹)", type: "number", step: "0.01" }] },
              { label: "Cancel", perm: "approve", danger: true, when: (r) => r.status === "open" && Number(r.issued_fine) === 0, endpoint: (r) => `/karigars/jobcards/${r.id}/cancel/`, confirm: "Cancel this job card?" }]} />) },
        { label: "Metal register", content: (
          <CrudPage<T> key={"t" + n} bare title="Transaction" endpoint="/karigars/transactions" module="karigars" canAdd={false} canEdit={false} fields={[]}
            filters={[{ name: "kind", label: "All types", options: ["issue", "return", "scrap", "finished"].map((s) => ({ value: s, label: s })) }]}
            columns={[{ label: "Date", render: (r) => new Date(r.created_at).toLocaleString() }, { label: "Karigar", render: (r) => r.karigar_name }, { label: "Job", render: (r) => r.job },
              { label: "Type", render: (r) => r.kind }, { label: "Metal", render: (r) => `${r.metal} ${r.purity}` }, { label: "Gross g", render: (r) => r.gross_weight }, { label: "Fine g", render: (r) => r.fine_weight }]} />) },
        { label: "Pending metal", content: <Balances key={n} /> },
        { label: "Karigars", content: (
          <CrudPage<K> bare title="Karigar" endpoint="/karigars" module="karigars"
            columns={[{ label: "Name", render: (r) => r.name }, { label: "Phone", render: (r) => r.phone }, { label: "Skill", render: (r) => r.skill }, { label: "Allowed wastage %", render: (r) => r.allowed_wastage_percent }, { label: "Active", render: (r) => (r.is_active ? "Yes" : "No") }]}
            fields={[{ name: "name", label: "Name", required: true }, { name: "phone", label: "Phone" }, { name: "skill", label: "Skill" },
              { name: "allowed_wastage_percent", label: "Allowed wastage %", type: "number", step: "0.01", default: "1.5" }, { name: "address", label: "Address", type: "textarea" }, { name: "is_active", label: "Active", type: "checkbox", default: true }]} />) },
        { label: "Labour payments", content: (
          <CrudPage<{ id: string; karigar_name: string; date: string; amount: string; method: string; note: string }> key={"p" + n} bare title="Payment" endpoint="/karigars/payments" module="karigars" canEdit={false} addLabel="Pay karigar"
            fields={[{ name: "karigar", label: "Karigar", type: "select", required: true, from: { endpoint: "/karigars/", label: (r) => r.name } }, { name: "date", label: "Date", type: "date", required: true },
              { name: "amount", label: "Amount (₹)", type: "number", step: "0.01", required: true }, { name: "method", label: "Method", type: "select", required: true, default: "cash", options: ["cash", "bank", "upi"].map((m) => ({ value: m, label: m })) }, { name: "note", label: "Note" }]}
            columns={[{ label: "Date", render: (r) => r.date }, { label: "Karigar", render: (r) => r.karigar_name }, { label: "Amount", render: (r) => money(r.amount) }, { label: "Method", render: (r) => r.method }, { label: "Note", render: (r) => r.note }]} />) },
      ]} />
      {txn && <ActionModal title="Metal issue / return" endpoint="/karigars/transactions/" fields={txnFields} intro="Issue deducts from raw metal stock; return/scrap add back; finished creates a jewellery piece in stock." onClose={() => setTxn(false)} onDone={() => { setTxn(false); setN(n + 1); }} />}
    </div>
  );
}
