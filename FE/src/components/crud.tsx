"use client";
import { useCallback, useEffect, useState } from "react";
import { Download, LayoutGrid, List, Plus, Search } from "lucide-react";
import { api, Page } from "@/lib/api";
import { can, useMe } from "./shell";
import { ActionModal, Badge, Err, Field, Opt, PageHeader, Skeleton, isStatusCol } from "./ui";

export type { Field };
export type Col<T> = { label: string; render: (r: T) => React.ReactNode };
export type RowAction<T> = {
  label: string; when?: (r: T) => boolean; endpoint: (r: T) => string; fields?: Field[]; intro?: string;
  perm?: string; danger?: boolean; confirm?: string; initial?: (r: T) => Record<string, unknown>; extra?: (r: T) => Record<string, unknown>;
};

function text(n: React.ReactNode): string {
  if (n === null || n === undefined || typeof n === "boolean") return "";
  if (typeof n === "string" || typeof n === "number") return String(n);
  if (Array.isArray(n)) return n.map(text).join("");
  if (typeof n === "object" && "props" in n) return text((n as { props: { children?: React.ReactNode } }).props.children);
  return "";
}

export function CrudPage<T extends { id: string }>({
  title, endpoint, module, columns, fields, search = true, filters, rowActions = [], canEdit = true, canAdd = true,
  bare = false, query = "", addLabel = "Add", createFields, transformCreate, subtitle, card,
}: {
  title: string; endpoint: string; module: string; columns: Col<T>[]; fields: Field[]; search?: boolean;
  filters?: { name: string; label: string; options: Opt[] }[]; rowActions?: RowAction<T>[]; canEdit?: boolean; canAdd?: boolean;
  bare?: boolean; query?: string; addLabel?: string; createFields?: Field[]; subtitle?: string;
  transformCreate?: (b: Record<string, unknown>) => Record<string, unknown>;
  card?: (r: T, actions: React.ReactNode) => React.ReactNode;
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
  const [view, setView] = useState<"table" | "cards">(card ? "cards" : "table");

  // deep links: ?q=<search>  and  ?add=1
  useEffect(() => {
    if (bare) return;
    const p = new URLSearchParams(window.location.search);
    if (p.get("q")) setQ(p.get("q")!);
    if (p.get("add") === "1" && canAdd && can(me, module, "create")) setEditing({});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  function exportCsv() {
    const esc = (s: string) => `"${(/^[=+\-@]/.test(s) ? "'" + s : s).replace(/"/g, '""')}"`;
    const csv = [columns.map((c) => esc(c.label)).join(","), ...rows.map((r) => columns.map((c) => esc(text(c.render(r)))).join(","))].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = `${title.toLowerCase().replace(/\W+/g, "-")}.csv`;
    a.click();
  }

  const actions = (r: T) => (
    <>
      {rowActions.filter((a) => (!a.when || a.when(r)) && can(me, module, a.perm || "edit")).map((a) => (
        <button key={a.label} className={`font-semibold hover:underline ${a.danger ? "text-danger" : "text-gold"}`} onClick={() => runAction(a, r)}>{a.label}</button>
      ))}
      {canEdit && can(me, module, "edit") && <button className="text-muted hover:text-ink" onClick={() => setEditing(r)}>Edit</button>}
    </>
  );
  const colspan = columns.length + 1;
  const cell = (c: Col<T>, r: T) => {
    const v = c.render(r);
    return isStatusCol(c.label) && typeof v === "string" && v ? <Badge value={v} /> : v;
  };

  return (
    <div className="space-y-4">
      {!bare && <PageHeader title={title} subtitle={subtitle} />}
      <div className="flex flex-wrap items-center gap-2.5">
        {search && (
          <div className="relative">
            <Search size={16} className="absolute left-3 top-2.5 text-muted" />
            <input className="input pl-9 w-60" placeholder="Search…" value={q} onChange={(e) => { setPage(1); setQ(e.target.value); }} />
          </div>
        )}
        {filters?.map((f) => (
          <select key={f.name} className="input !w-40" value={fv[f.name] || ""} onChange={(e) => { setPage(1); setFv({ ...fv, [f.name]: e.target.value }); }}>
            <option value="">{f.label}</option>
            {f.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        ))}
        <div className="flex-1" />
        {card && (
          <div className="flex rounded-lg border border-line overflow-hidden">
            <button className={`p-2 ${view === "cards" ? "bg-navy text-white dark:bg-gold dark:text-navy" : ""}`} onClick={() => setView("cards")} aria-label="Card view"><LayoutGrid size={16} /></button>
            <button className={`p-2 ${view === "table" ? "bg-navy text-white dark:bg-gold dark:text-navy" : ""}`} onClick={() => setView("table")} aria-label="Table view"><List size={16} /></button>
          </div>
        )}
        <button className="btn btn-ghost" onClick={exportCsv} disabled={!rows.length}><Download size={15} /> Export</button>
        {canAdd && can(me, module, "create") && <button className="btn" onClick={() => setEditing({})}><Plus size={16} /> {addLabel}</button>}
      </div>

      <Err>{error}</Err>
      {view === "cards" && card ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {loading && Array.from({ length: 8 }).map((_, i) => <div key={i} className="card overflow-hidden"><div className="skeleton h-44 !rounded-none" /><div className="p-4 space-y-2"><div className="skeleton h-4 w-3/4" /><div className="skeleton h-3 w-1/2" /></div></div>)}
          {!loading && rows.length === 0 && <div className="card p-10 text-center text-muted col-span-full">No records yet.</div>}
          {!loading && rows.map((r) => <div key={r.id}>{card(r, actions(r))}</div>)}
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left border-b border-line bg-soft">
              <tr>{columns.map((c) => <th key={c.label} className="px-4 py-3 th whitespace-nowrap">{c.label}</th>)}<th /></tr>
            </thead>
            <tbody>
              {loading && <Skeleton rows={6} cols={colspan} />}
              {!loading && rows.length === 0 && <tr><td className="px-4 py-12 text-center text-muted" colSpan={colspan}>No records yet.</td></tr>}
              {!loading && rows.map((r) => (
                <tr key={r.id} className="border-b border-line last:border-0 hover:bg-soft/70 transition-colors">
                  {columns.map((c) => <td key={c.label} className="px-4 py-3 whitespace-nowrap">{cell(c, r)}</td>)}
                  <td className="px-4 py-3 text-right whitespace-nowrap space-x-3">{actions(r)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
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
