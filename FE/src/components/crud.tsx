"use client";
import { useCallback, useEffect, useState } from "react";
import { Plus, Search } from "lucide-react";
import { api, Page } from "@/lib/api";
import { can, useMe } from "./shell";
import { ActionModal, Err, Field, Opt } from "./ui";

export type { Field };
export type Col<T> = { label: string; render: (r: T) => React.ReactNode };
export type RowAction<T> = {
  label: string; when?: (r: T) => boolean; endpoint: (r: T) => string; fields?: Field[]; intro?: string;
  perm?: string; danger?: boolean; confirm?: string; initial?: (r: T) => Record<string, unknown>; extra?: (r: T) => Record<string, unknown>;
};

export function CrudPage<T extends { id: string }>({
  title, endpoint, module, columns, fields, search = true, filters, rowActions = [], canEdit = true, canAdd = true,
  bare = false, query = "", addLabel = "Add", createFields, transformCreate,
}: {
  title: string; endpoint: string; module: string; columns: Col<T>[]; fields: Field[]; search?: boolean;
  filters?: { name: string; label: string; options: Opt[] }[]; rowActions?: RowAction<T>[]; canEdit?: boolean; canAdd?: boolean;
  bare?: boolean; query?: string; addLabel?: string; createFields?: Field[];
  transformCreate?: (b: Record<string, unknown>) => Record<string, unknown>;
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
  const [acting, setActing] = useState<{ a: RowAction<T>; r: T } | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const p = new URLSearchParams(query);
      p.set("page", String(page));
      if (q) p.set("search", q);
      Object.entries(fv).forEach(([k, v]) => v && p.set(k, v));
      const d = await api<Page<T> | T[]>(`${endpoint}/?${p}`);
      const list = Array.isArray(d) ? d : d.results;
      setRows(list); setCount(Array.isArray(d) ? d.length : d.count);
    } catch (e) { setError(e instanceof Error ? e.message : "Failed to load"); } finally { setLoading(false); }
  }, [endpoint, q, fv, page, query]);

  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); }, [load]);

  async function runAction(a: RowAction<T>, r: T) {
    if (a.fields?.length) { setActing({ a, r }); return; }
    if (a.confirm && !confirm(a.confirm)) return;
    try { await api(a.endpoint(r), { method: "POST", body: a.extra?.(r) ?? {} }); load(); } catch (e) { alert(e instanceof Error ? e.message : "Failed"); }
  }

  const colspan = columns.length + 1;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        {bare ? <div className="flex-1" /> : <h1 className="text-xl font-bold flex-1">{title}</h1>}
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
        {canAdd && can(me, module, "create") && <button className="btn" onClick={() => setEditing({})}><Plus size={16} /> {addLabel}</button>}
      </div>

      <Err>{error}</Err>
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-muted border-b border-line">
            <tr>{columns.map((c) => <th key={c.label} className="px-4 py-3 font-medium whitespace-nowrap">{c.label}</th>)}<th /></tr>
          </thead>
          <tbody>
            {loading && <tr><td className="px-4 py-6 text-muted" colSpan={colspan}>Loading…</td></tr>}
            {!loading && rows.length === 0 && <tr><td className="px-4 py-6 text-muted" colSpan={colspan}>No records yet.</td></tr>}
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-line last:border-0">
                {columns.map((c) => <td key={c.label} className="px-4 py-3 whitespace-nowrap">{c.render(r)}</td>)}
                <td className="px-4 py-3 text-right whitespace-nowrap space-x-3">
                  {rowActions.filter((a) => (!a.when || a.when(r)) && can(me, module, a.perm || "edit")).map((a) => (
                    <button key={a.label} className={`font-semibold ${a.danger ? "text-red-600" : "text-gold"}`} onClick={() => runAction(a, r)}>{a.label}</button>
                  ))}
                  {canEdit && can(me, module, "edit") && <button className="text-muted" onClick={() => setEditing(r)}>Edit</button>}
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
        <ActionModal title={`${(editing as { id?: string }).id ? "Edit" : "New"} ${title}`}
          endpoint={(editing as { id?: string }).id ? `${endpoint}/${(editing as { id: string }).id}/` : `${endpoint}/`}
          method={(editing as { id?: string }).id ? "PATCH" : "POST"}
          fields={!(editing as { id?: string }).id && createFields ? createFields : fields}
          initial={editing as Record<string, unknown>} submitLabel="Save"
          transform={!(editing as { id?: string }).id ? transformCreate : undefined}
          onClose={() => setEditing(null)} onDone={() => { setEditing(null); load(); }} />
      )}
      {acting && (
        <ActionModal title={acting.a.label} endpoint={acting.a.endpoint(acting.r)} fields={acting.a.fields!} intro={acting.a.intro}
          initial={acting.a.initial?.(acting.r)} transform={(b) => ({ ...b, ...(acting.a.extra?.(acting.r) ?? {}) })} onClose={() => setActing(null)} onDone={() => { setActing(null); load(); }} />
      )}
    </div>
  );
}
