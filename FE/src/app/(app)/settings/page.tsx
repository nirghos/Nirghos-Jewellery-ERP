"use client";
import { useEffect, useState } from "react";
import { api, money } from "@/lib/api";
import { CrudPage } from "@/components/crud";
import { can, useMe } from "@/components/shell";
import { DataTable, Tabs, useFetch } from "@/components/ui";

type Company = { name: string; gstin: string; pan: string; address: string; phone: string; state: string; gst_rate: string; hallmark_charge: string; hsn_code: string };
type Rate = { id: string; metal: string; purity: string; rate_per_gram: string; created_at: string };
type U = { id: string; username: string; first_name: string; last_name: string; role: string; branch: string | null; is_active: boolean; last_login: string | null };
const ROLES = ["owner", "branch_manager", "accountant", "sales_manager", "sales_staff", "stock_manager", "purchase_manager", "karigar_manager", "hr_manager", "auditor"];

function CompanyForm() {
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
      <input className="input" type={type} step="0.01" disabled={!edit} value={c[k] ?? ""} onChange={(e) => setC({ ...c, [k]: e.target.value })} /></label>);
  return (
    <form onSubmit={save} className="card p-5 space-y-3 max-w-2xl">
      <div className="grid sm:grid-cols-2 gap-3">{f("name", "Company name")}{f("phone", "Phone")}{f("gstin", "GSTIN")}{f("pan", "PAN")}{f("state", "State")}{f("hsn_code", "HSN code")}
        {f("gst_rate", "GST rate % (confirm with your CA)", "number")}{f("hallmark_charge", "Hallmark charge per piece", "number")}</div>
      {f("address", "Address")}{msg && <p className="text-sm text-muted">{msg}</p>}{edit && <button className="btn">Save</button>}
    </form>
  );
}

function Audit() {
  const { data } = useFetch<{ when: string; user: string; action: string; model: string; summary: string }[]>("/settings/audit-logs/");
  return <DataTable columns={["When", "User", "Action", "Record", "Summary"]} rows={(data ?? []).map((a) => [new Date(a.when).toLocaleString(), a.user, a.action, a.model, a.summary])} />;
}

export default function Settings() {
  const me = useMe();
  const tabs = [
    { label: "Company", content: <CompanyForm /> },
    { label: "Gold / metal rates", content: (
      <CrudPage<Rate> bare title="Rate" endpoint="/products/rates" module="products" search={false} canEdit={false} addLabel="Set new rate"
        columns={[{ label: "Metal", render: (r) => r.metal }, { label: "Purity", render: (r) => r.purity }, { label: "Rate / g", render: (r) => money(r.rate_per_gram) }, { label: "Set on", render: (r) => new Date(r.created_at).toLocaleString() }]}
        fields={[{ name: "metal", label: "Metal", type: "select", required: true, default: "gold", options: ["gold", "silver", "platinum"].map((m) => ({ value: m, label: m })) },
          { name: "purity", label: "Purity (0.916 = 22K)", type: "number", step: "0.001", required: true }, { name: "rate_per_gram", label: "Rate per gram (₹)", type: "number", step: "0.01", required: true }]} />) },
    { label: "Branches", content: (
      <CrudPage<{ id: string; name: string; code: string; address: string; is_active: boolean }> bare title="Branch" endpoint="/branches" module="company" search={false}
        columns={[{ label: "Name", render: (r) => r.name }, { label: "Code", render: (r) => r.code }, { label: "Address", render: (r) => r.address }, { label: "Active", render: (r) => (r.is_active ? "Yes" : "No") }]}
        fields={[{ name: "name", label: "Name", required: true }, { name: "code", label: "Code", required: true }, { name: "address", label: "Address", type: "textarea" }, { name: "is_active", label: "Active", type: "checkbox", default: true }]} />) },
  ];
  if (can(me, "users", "view")) {
    tabs.push({ label: "Users & roles", content: (
      <CrudPage<U> bare title="User" endpoint="/users" module="users"
        columns={[{ label: "Username", render: (r) => r.username }, { label: "Name", render: (r) => `${r.first_name} ${r.last_name}` }, { label: "Role", render: (r) => r.role.replace("_", " ") }, { label: "Active", render: (r) => (r.is_active ? "Yes" : "No") }, { label: "Last login", render: (r) => (r.last_login ? new Date(r.last_login).toLocaleString() : "-") }]}
        fields={[{ name: "username", label: "Username", required: true }, { name: "first_name", label: "First name" }, { name: "last_name", label: "Last name" }, { name: "email", label: "Email" }, { name: "phone", label: "Phone" },
          { name: "role", label: "Role", type: "select", required: true, default: "sales_staff", options: ROLES.map((r) => ({ value: r, label: r.replace("_", " ") })) },
          { name: "branch", label: "Branch", type: "select", from: { endpoint: "/branches/", label: (b) => b.name } }, { name: "password", label: "Password (min 8; leave blank to keep)", type: "password" }, { name: "is_active", label: "Active", type: "checkbox", default: true }]} />) });
    tabs.push({ label: "Audit log", content: <Audit /> });
  }
  return <div className="space-y-4"><h1 className="text-xl font-bold">Settings & administration</h1><Tabs tabs={tabs} /></div>;
}
