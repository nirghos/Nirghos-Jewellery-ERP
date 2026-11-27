"use client";
import { useState } from "react";
import { api, money } from "@/lib/api";
import { CrudPage } from "@/components/crud";
import { can, useMe } from "@/components/shell";
import { ActionModal, DataTable, Err, Modal, Tabs } from "@/components/ui";

type Item = { id: string; sku: string; product_name: string; huid: string; result: string };
type R = { id: string; number: string; centre_name: string; status: string; dispatched_on: string; received_on: string; total_charges: string; items: Item[] };

function Receive({ r, onClose, onDone }: { r: R; onClose: () => void; onDone: () => void }) {
  const [res, setRes] = useState<Record<string, { result: string; huid: string }>>(Object.fromEntries(r.items.map((i) => [i.id, { result: "pass", huid: "" }])));
  const [err, setErr] = useState("");
  async function save() {
    setErr("");
    try { await api(`/hallmark/requests/${r.id}/receive/`, { method: "POST", body: { results: r.items.map((i) => ({ item: i.id, ...res[i.id] })) } }); onDone(); } catch (e) { setErr(e instanceof Error ? e.message : "Failed"); }
  }
  return (
    <Modal title={`Receive ${r.number}`} onClose={onClose}>
      <div className="space-y-2">
        {r.items.map((i) => (
          <div key={i.id} className="flex gap-2 items-center text-sm">
            <span className="flex-1">{i.sku} · {i.product_name}</span>
            <select className="input w-24" value={res[i.id].result} onChange={(e) => setRes({ ...res, [i.id]: { ...res[i.id], result: e.target.value } })}><option>pass</option><option>fail</option></select>
            <input className="input w-28 uppercase" maxLength={6} placeholder="HUID" disabled={res[i.id].result !== "pass"} value={res[i.id].huid} onChange={(e) => setRes({ ...res, [i.id]: { ...res[i.id], huid: e.target.value.toUpperCase() } })} />
          </div>
        ))}
      </div>
      <Err>{err}</Err>
      <div className="flex justify-end gap-2"><button className="btn btn-ghost" onClick={onClose}>Cancel</button><button className="btn" onClick={save}>Save results</button></div>
    </Modal>
  );
}

function Huid() {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<Record<string, string>[]>([]);
  const [err, setErr] = useState("");
  async function go(e: React.FormEvent) { e.preventDefault(); setErr(""); try { setRows(await api(`/hallmark/huid/?q=${encodeURIComponent(q)}`)); } catch (x) { setErr(x instanceof Error ? x.message : "Failed"); } }
  return <div className="space-y-3"><form onSubmit={go} className="flex gap-2"><input className="input w-64 uppercase" placeholder="HUID (min 3 chars)" value={q} onChange={(e) => setQ(e.target.value)} /><button className="btn">Search</button></form><Err>{err}</Err>
    <DataTable columns={["HUID", "SKU", "Name", "Purity", "Net g", "Status"]} rows={rows.map((r) => [r.huid, r.sku, r.name, r.purity, r.net_weight, r.status])} /></div>;
}

export default function Hallmark() {
  const me = useMe();
  const [make, setMake] = useState(false);
  const [recv, setRecv] = useState<R | null>(null);
  const [n, setN] = useState(0);
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3"><h1 className="text-xl font-bold flex-1">Hallmark & HUID</h1>
        {can(me, "hallmark", "create") && <button className="btn" onClick={() => setMake(true)}>New hallmark request</button>}</div>
      <Tabs tabs={[
        { label: "Requests", content: (
          <CrudPage<R> key={n} bare title="Request" endpoint="/hallmark/requests" module="hallmark" canAdd={false} canEdit={false} fields={[]}
            columns={[{ label: "No.", render: (r) => r.number }, { label: "Centre", render: (r) => r.centre_name }, { label: "Pieces", render: (r) => r.items.length }, { label: "Charges", render: (r) => money(r.total_charges) },
              { label: "Status", render: (r) => r.status }, { label: "Dispatched", render: (r) => r.dispatched_on }, { label: "Received", render: (r) => r.received_on },
              { label: "Passed / failed", render: (r) => `${r.items.filter((i) => i.result === "pass").length} / ${r.items.filter((i) => i.result === "fail").length}` }]}
            rowActions={[{ label: "Dispatch", when: (r) => r.status === "created", endpoint: (r) => `/hallmark/requests/${r.id}/dispatch/`, confirm: "Mark as dispatched to AHC?" }]} />) },
        { label: "Receive results", content: (
          <CrudPage<R> key={"r" + n} bare title="Dispatched" endpoint="/hallmark/requests" module="hallmark" query="status=dispatched" canAdd={false} canEdit={false} search={false} fields={[]}
            columns={[{ label: "No.", render: (r) => r.number }, { label: "Centre", render: (r) => r.centre_name }, { label: "Pieces", render: (r) => r.items.length }, { label: "Dispatched", render: (r) => r.dispatched_on },
              { label: "", render: (r) => <button className="text-gold font-semibold" onClick={() => setRecv(r)}>Enter results</button> }]} />) },
        { label: "HUID search", content: <Huid /> },
        { label: "AHC centres", content: (
          <CrudPage<{ id: string; name: string; code: string; phone: string; charge_per_piece: string }> bare title="AHC centre" endpoint="/hallmark/centres" module="hallmark"
            fields={[{ name: "name", label: "Name", required: true }, { name: "code", label: "Code" }, { name: "phone", label: "Phone" }, { name: "charge_per_piece", label: "Charge per piece (₹)", type: "number", step: "0.01", default: "0" }, { name: "address", label: "Address", type: "textarea" }]}
            columns={[{ label: "Name", render: (r) => r.name }, { label: "Code", render: (r) => r.code }, { label: "Phone", render: (r) => r.phone }, { label: "Charge / piece", render: (r) => money(r.charge_per_piece) }]} />) },
      ]} />
      {make && <ActionModal title="New hallmark request" endpoint="/hallmark/requests/" intro="Enter SKUs/barcodes of available pieces, comma separated."
        fields={[{ name: "centre", label: "AHC centre", type: "select", required: true, from: { endpoint: "/hallmark/centres/", label: (c) => c.name } }, { name: "skus", label: "SKUs (comma separated)", required: true }, { name: "notes", label: "Notes" }]}
        onClose={() => setMake(false)} onDone={() => { setMake(false); setN(n + 1); }} />}
      {recv && <Receive r={recv} onClose={() => setRecv(null)} onDone={() => { setRecv(null); setN(n + 1); }} />}
    </div>
  );
}
