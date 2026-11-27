"use client";
import { useEffect, useState } from "react";
import { api, money, Page } from "@/lib/api";
import { CrudPage } from "@/components/crud";
import { can, useMe } from "@/components/shell";

type Company = { name: string; gstin: string; pan: string; address: string; phone: string; gst_rate: string; hallmark_charge: string };
type Rate = { id: string; metal: string; purity: string; rate_per_gram: string; created_at: string };

export default function Settings() {
  const me = useMe();
  const [c, setC] = useState<Company | null>(null);
  const [msg, setMsg] = useState("");
  useEffect(() => { api<Company>("/company/").then(setC).catch((e) => setMsg(e.message)); }, []);
  const edit = can(me, "company", "edit");

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try { setC(await api<Company>("/company/", { method: "PATCH", body: c })); setMsg("Saved"); } catch (e) { setMsg(e instanceof Error ? e.message : "Failed"); }
  }
  if (!c) return <div className="text-muted">{msg || "Loading…"}</div>;
  const f = (k: keyof Company, label: string, type = "text") => (
    <label className="text-sm space-y-1 block"><span className="text-muted">{label}</span>
      <input className="input" type={type} step="0.01" disabled={!edit} value={c[k] ?? ""} onChange={(e) => setC({ ...c, [k]: e.target.value })} /></label>
  );
  return (
    <div className="space-y-8">
      <form onSubmit={save} className="card p-5 space-y-3 max-w-2xl">
        <h1 className="text-xl font-bold">Company settings</h1>
        <div className="grid sm:grid-cols-2 gap-3">
          {f("name", "Company name")}{f("phone", "Phone")}{f("gstin", "GSTIN")}{f("pan", "PAN")}
          {f("gst_rate", "GST rate % (confirm with your CA)", "number")}{f("hallmark_charge", "Hallmark charge per piece", "number")}
        </div>
        {f("address", "Address")}
        {msg && <p className="text-sm text-muted">{msg}</p>}
        {edit && <button className="btn">Save</button>}
      </form>
      <CrudPage<Rate>
        title="Gold / metal rates" endpoint="/products/rates" module="products" search={false}
        columns={[
          { label: "Metal", render: (r) => r.metal }, { label: "Purity", render: (r) => r.purity },
          { label: "Rate / g", render: (r) => money(r.rate_per_gram) }, { label: "Set on", render: (r) => new Date(r.created_at).toLocaleString() },
        ]}
        fields={[
          { name: "metal", label: "Metal", type: "select", required: true, default: "gold", options: ["gold", "silver", "platinum"].map((m) => ({ value: m, label: m })) },
          { name: "purity", label: "Purity (0.916 = 22K)", type: "number", step: "0.001", required: true },
          { name: "rate_per_gram", label: "Rate per gram (₹)", type: "number", step: "0.01", required: true },
        ]}
      />
    </div>
  );
}
