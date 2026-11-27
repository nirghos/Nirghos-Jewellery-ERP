"use client";
import { useCallback, useEffect, useState } from "react";
import { X } from "lucide-react";
import { api, ApiError, API_URL, money, tokens } from "@/lib/api";

export type Opt = { value: string; label: string };
export type Field = {
  name: string; label: string; type?: "text" | "number" | "date" | "select" | "checkbox" | "textarea" | "password";
  options?: Opt[]; from?: { endpoint: string; label: (r: any) => string }; // eslint-disable-line @typescript-eslint/no-explicit-any
  required?: boolean; step?: string; default?: string | boolean; hint?: string;
};

export function useFetch<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!path) return;
    let live = true;
    setLoading(true);
    api<T>(path).then((d) => { if (live) { setData(d); setError(""); } })
      .catch((e) => live && setError(e.message)).finally(() => live && setLoading(false));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, tick, ...deps]);
  return { data, error, loading, reload: useCallback(() => setTick((t) => t + 1), []) };
}

export function Tabs({ tabs }: { tabs: { label: string; content: React.ReactNode }[] }) {
  const [i, setI] = useState(0);
  return (
    <div className="space-y-4">
      <div className="flex gap-1 overflow-x-auto border-b border-line">
        {tabs.map((t, k) => (
          <button key={t.label} onClick={() => setI(k)}
            className={`px-4 py-2 text-sm whitespace-nowrap border-b-2 -mb-px ${k === i ? "border-gold font-semibold" : "border-transparent text-muted"}`}>{t.label}</button>
        ))}
      </div>
      <div key={i}>{tabs[i].content}</div>
    </div>
  );
}

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/50 grid place-items-center p-4 overflow-y-auto">
      <div className="card w-full max-w-2xl p-6 space-y-4">
        <div className="flex items-center justify-between"><h2 className="font-bold">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close"><X /></button></div>
        {children}
      </div>
    </div>
  );
}

export function useOptions(f: Field): Opt[] {
  const [opts, setOpts] = useState<Opt[]>(f.options || []);
  useEffect(() => {
    if (!f.from) return;
    api<any>(f.from.endpoint).then((d) => { // eslint-disable-line @typescript-eslint/no-explicit-any
      const list = Array.isArray(d) ? d : d.results;
      setOpts(list.map((r: any) => ({ value: r.id, label: f.from!.label(r) }))); // eslint-disable-line @typescript-eslint/no-explicit-any
    }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [f.from?.endpoint]);
  return opts;
}

export function FieldInput({ f, v, set }: { f: Field; v: unknown; set: (x: unknown) => void }) {
  const opts = useOptions(f);
  if (f.type === "select")
    return (
      <select className="input" value={String(v ?? "")} required={f.required} onChange={(e) => set(e.target.value)}>
        {!f.required && <option value="">—</option>}
        {f.required && !v && <option value="">Select…</option>}
        {opts.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    );
  if (f.type === "checkbox") return <input type="checkbox" className="block" checked={!!v} onChange={(e) => set(e.target.checked)} />;
  if (f.type === "textarea") return <textarea className="input" rows={2} value={String(v ?? "")} onChange={(e) => set(e.target.value)} />;
  return <input className="input" type={f.type || "text"} step={f.step} required={f.required} value={String(v ?? "")} onChange={(e) => set(e.target.value)} />;
}

export function initialValues(fields: Field[], src: Record<string, unknown> = {}) {
  const o: Record<string, unknown> = {};
  fields.forEach((f) => { o[f.name] = src[f.name] ?? f.default ?? (f.type === "checkbox" ? false : ""); });
  return o;
}

export function buildBody(fields: Field[], v: Record<string, unknown>) {
  const b: Record<string, unknown> = {};
  fields.forEach((f) => {
    const x = v[f.name];
    if (x === "" && f.type !== "text" && f.type !== "textarea") return;
    if (x === "" && f.type === "password") return;
    b[f.name] = x;
  });
  return b;
}

/** Modal form that POSTs/PATCHes to an endpoint. */
export function ActionModal({ title, endpoint, method = "POST", fields, initial, intro, onClose, onDone, submitLabel = "Submit", transform }: {
  title: string; endpoint: string; method?: string; fields: Field[]; initial?: Record<string, unknown>; intro?: string;
  onClose: () => void; onDone: (r: unknown) => void; submitLabel?: string; transform?: (b: Record<string, unknown>) => Record<string, unknown>;
}) {
  const [v, setV] = useState(() => initialValues(fields, initial));
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  async function go(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      let body = buildBody(fields, v);
      if (transform) body = transform(body);
      onDone(await api(endpoint, { method, body }));
    } catch (e) { setErr(e instanceof Error ? e.message : "Failed"); } finally { setBusy(false); }
  }
  return (
    <Modal title={title} onClose={onClose}>
      <form onSubmit={go} className="space-y-4">
        {intro && <p className="text-sm text-muted">{intro}</p>}
        <div className="grid sm:grid-cols-2 gap-3">
          {fields.map((f) => (
            <label key={f.name} className={`text-sm space-y-1 ${f.type === "textarea" ? "sm:col-span-2" : ""}`}>
              <span className="text-muted">{f.label}{f.required && " *"}</span>
              <FieldInput f={f} v={v[f.name]} set={(x) => setV({ ...v, [f.name]: x })} />
              {f.hint && <span className="text-xs text-muted block">{f.hint}</span>}
            </label>
          ))}
        </div>
        {err && <p className="text-sm text-red-600">{err}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn" disabled={busy}>{busy ? "Working…" : submitLabel}</button>
        </div>
      </form>
    </Modal>
  );
}

export const fmt = (v: unknown): string => {
  if (v === null || v === undefined || v === "") return "";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  return String(v);
};
const isNum = (v: unknown) => typeof v === "string" && /^-?\d+\.\d+$/.test(v);

/** Renders {columns, rows} (reports) – or any array of objects when `cols` is given. */
export function DataTable({ columns, rows, money: moneyCols = [] }: { columns: string[]; rows: unknown[][]; money?: number[] }) {
  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-muted border-b border-line"><tr>{columns.map((c) => <th key={c} className="px-4 py-3 font-medium whitespace-nowrap">{c}</th>)}</tr></thead>
        <tbody>
          {rows.length === 0 && <tr><td colSpan={columns.length} className="px-4 py-6 text-muted">No data.</td></tr>}
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-line last:border-0">
              {r.map((c, j) => <td key={j} className={`px-4 py-2.5 whitespace-nowrap ${isNum(c) ? "tabular-nums" : ""}`}>{moneyCols.includes(j) ? money(c as string) : fmt(c)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DateRange({ from, to, setFrom, setTo }: { from: string; to: string; setFrom: (s: string) => void; setTo: (s: string) => void }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <input type="date" className="input w-40" value={from} onChange={(e) => setFrom(e.target.value)} aria-label="From" />
      <span className="text-muted">to</span>
      <input type="date" className="input w-40" value={to} onChange={(e) => setTo(e.target.value)} aria-label="To" />
    </div>
  );
}

export function qs(o: Record<string, string>) {
  const p = new URLSearchParams();
  Object.entries(o).forEach(([k, v]) => v && p.set(k, v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

export async function downloadCsv(path: string, name: string) {
  const res = await fetch(`${API_URL}${path}`, { headers: { Authorization: `Bearer ${tokens.get()}` } });
  if (!res.ok) throw new ApiError(res.status, await res.json().catch(() => null));
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url; a.download = name; a.click();
  URL.revokeObjectURL(url);
}

export function Stat({ label, value, sub }: { label: string; value: React.ReactNode; sub?: string }) {
  return <div className="card p-4"><div className="text-sm text-muted">{label}</div><div className="text-2xl font-bold mt-1">{value}</div>{sub && <div className="text-xs text-muted">{sub}</div>}</div>;
}

export function Err({ children }: { children: React.ReactNode }) {
  return children ? <div className="card p-3 text-sm text-red-600">{children}</div> : null;
}
