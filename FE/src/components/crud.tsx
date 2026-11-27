"use client";
import { useCallback, useEffect, useState } from "react";
import { Plus, Search, X } from "lucide-react";
import { api, ApiError, Page } from "@/lib/api";
import { can, useMe } from "./shell";

export type Field = {
  name: string; label: string; type?: "text" | "number" | "date" | "select" | "checkbox" | "textarea";
  options?: { value: string; label: string }[]; required?: boolean; step?: string; default?: string | boolean;
};
export type Col<T> = { label: string; render: (r: T) => React.ReactNode };

export function CrudPage<T extends { id: string }>({
  title, endpoint, module, columns, fields, search = true, filters,
}: {
  title: string; endpoint: string; module: string; columns: Col<T>[]; fields: Field[]; search?: boolean;
  filters?: { name: string; label: string; options: { value: string; label: string }[] }[];
}) {
  const me = useMe();
  const [rows, setRows] = useState<T[]>([]);
  const [count, setCount] = useState(0);
  const [q, setQ] = useState("");
  const [fv, setFv] = useState<Record<string, string>>({});
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<Partial<T> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const p = new URLSearchParams({ page: String(page) });
      if (q) p.set("search", q);
      Object.entries(fv).forEach(([k, v]) => v && p.set(k, v));
      const d = await api<Page<T>>(`${endpoint}/?${p}`);
      setRows(d.results);
      setCount(d.count);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [endpoint, q, fv, page]);

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-bold flex-1">{title}</h1>
        {search && (
          <div className="relative">
            <Search size={16} className="absolute left-3 top-2.5 text-muted" />
            <input className="input pl-9 w-56" placeholder="Search…" value={q} onChange={(e) => { setPage(1); setQ(e.target.value); }} />
          </div>
        )}
        {filters?.map((f) => (
          <select key={f.name} className="input w-36" value={fv[f.name] || ""} onChange={(e) => { setPage(1); setFv({ ...fv, [f.name]: e.target.value }); }}>
            <option value="">{f.label}</option>
            {f.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        ))}
        {can(me, module, "create") && <button className="btn" onClick={() => setEditing({})}><Plus size={16} /> Add</button>}
      </div>

      {error && <div className="card p-3 text-sm text-red-600">{error}</div>}
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-muted border-b border-line">
            <tr>{columns.map((c) => <th key={c.label} className="px-4 py-3 font-medium whitespace-nowrap">{c.label}</th>)}<th /></tr>
          </thead>
          <tbody>
            {loading && <tr><td className="px-4 py-6 text-muted" colSpan={columns.length + 1}>Loading…</td></tr>}
            {!loading && rows.length === 0 && <tr><td className="px-4 py-6 text-muted" colSpan={columns.length + 1}>No records yet.</td></tr>}
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-line last:border-0">
                {columns.map((c) => <td key={c.label} className="px-4 py-3 whitespace-nowrap">{c.render(r)}</td>)}
                <td className="px-4 py-3 text-right">
                  {can(me, module, "edit") && <button className="text-gold font-semibold" onClick={() => setEditing(r)}>Edit</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between text-sm text-muted">
        <span>{count} records</span>
        <div className="flex gap-2">
          <button className="btn btn-ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>Prev</button>
          <button className="btn btn-ghost" disabled={page * 25 >= count} onClick={() => setPage(page + 1)}>Next</button>
        </div>
      </div>

      {editing && (
        <FormModal<T> title={title} endpoint={endpoint} fields={fields} initial={editing}
          onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />
      )}
    </div>
  );
}

function FormModal<T extends { id: string }>({ title, endpoint, fields, initial, onClose, onSaved }: {
  title: string; endpoint: string; fields: Field[]; initial: Partial<T>; onClose: () => void; onSaved: () => void;
}) {
  const [v, setV] = useState<Record<string, unknown>>(() => {
    const o: Record<string, unknown> = {};
    fields.forEach((f) => { o[f.name] = (initial as Record<string, unknown>)[f.name] ?? f.default ?? (f.type === "checkbox" ? false : ""); });
    return o;
  });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const id = (initial as { id?: string }).id;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    const body: Record<string, unknown> = {};
    fields.forEach((f) => {
      const x = v[f.name];
      if (x === "" && f.type !== "text" && f.type !== "textarea") return; // omit empty non-text -> server default
      body[f.name] = x;
    });
    try {
      await api(id ? `${endpoint}/${id}/` : `${endpoint}/`, { method: id ? "PATCH" : "POST", body });
      onSaved();
    } catch (e) {
      setErr(e instanceof ApiError || e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 grid place-items-center p-4 overflow-y-auto">
      <form onSubmit={save} className="card w-full max-w-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-bold">{id ? "Edit" : "New"} {title}</h2>
          <button type="button" onClick={onClose} aria-label="Close"><X /></button>
        </div>
        <div className="grid sm:grid-cols-2 gap-3">
          {fields.map((f) => (
            <label key={f.name} className={`text-sm space-y-1 ${f.type === "textarea" ? "sm:col-span-2" : ""}`}>
              <span className="text-muted">{f.label}{f.required && " *"}</span>
              {f.type === "select" ? (
                <select className="input" value={String(v[f.name])} required={f.required} onChange={(e) => setV({ ...v, [f.name]: e.target.value })}>
                  {!f.required && <option value="">—</option>}
                  {f.options!.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              ) : f.type === "checkbox" ? (
                <input type="checkbox" className="block" checked={!!v[f.name]} onChange={(e) => setV({ ...v, [f.name]: e.target.checked })} />
              ) : f.type === "textarea" ? (
                <textarea className="input" rows={2} value={String(v[f.name] ?? "")} onChange={(e) => setV({ ...v, [f.name]: e.target.value })} />
              ) : (
                <input className="input" type={f.type || "text"} step={f.step} required={f.required}
                  value={String(v[f.name] ?? "")} onChange={(e) => setV({ ...v, [f.name]: e.target.value })} />
              )}
            </label>
          ))}
        </div>
        {err && <p className="text-sm text-red-600">{err}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn" disabled={busy}>{busy ? "Saving…" : "Save"}</button>
        </div>
      </form>
    </div>
  );
}
