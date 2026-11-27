export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

const A = "nirghos_access";
const R = "nirghos_refresh";

export const tokens = {
  get: () => (typeof window === "undefined" ? null : localStorage.getItem(A)),
  set: (a: string, r?: string) => {
    localStorage.setItem(A, a);
    if (r) localStorage.setItem(R, r);
  },
  clear: () => {
    localStorage.removeItem(A);
    localStorage.removeItem(R);
  },
};

export class ApiError extends Error {
  constructor(public status: number, public data: unknown) {
    super(formatError(data) || `Request failed (${status})`);
  }
}

export function formatError(d: unknown): string {
  if (!d) return "";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map(formatError).join(" ");
  if (typeof d === "object") {
    return Object.entries(d as Record<string, unknown>)
      .map(([k, v]) => (k === "detail" || k === "non_field_errors" ? formatError(v) : `${k}: ${formatError(v)}`))
      .join(" · ");
  }
  return String(d);
}

async function refresh(): Promise<boolean> {
  const r = localStorage.getItem(R);
  if (!r) return false;
  const res = await fetch(`${API_URL}/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: r }),
  });
  if (!res.ok) return false;
  const d = await res.json();
  tokens.set(d.access, d.refresh);
  return true;
}

export async function api<T = unknown>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const go = () =>
    fetch(`${API_URL}${path}`, {
      method: opts.method || "GET",
      headers: {
        "Content-Type": "application/json",
        ...(tokens.get() ? { Authorization: `Bearer ${tokens.get()}` } : {}),
      },
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
  let res = await go();
  if (res.status === 401 && (await refresh())) res = await go();
  if (res.status === 401) {
    tokens.clear();
    if (typeof window !== "undefined" && !location.pathname.startsWith("/login")) location.href = "/login";
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

export type Page<T> = { count: number; results: T[] };
export const money = (v: string | number | null | undefined) =>
  "₹" + Number(v || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const moneyInt = (v: string | number | null | undefined) =>
  "₹" + Math.round(Number(v || 0)).toLocaleString("en-IN");
export const compact = (v: number) =>
  v >= 1e7 ? `${(v / 1e7).toFixed(2)} Cr` : v >= 1e5 ? `${(v / 1e5).toFixed(2)} L` : v >= 1e3 ? `${(v / 1e3).toFixed(1)}k` : String(Math.round(v));
