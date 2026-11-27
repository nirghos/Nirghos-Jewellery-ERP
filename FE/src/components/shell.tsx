"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle, BadgeCheck, BarChart3, Bell, Boxes, ChevronDown, ChevronsLeft, ChevronsRight, Coins, Diamond, Factory, FileText,
  Hammer, Landmark, LayoutDashboard, LineChart, LogOut, Menu, Moon, PiggyBank, Plus, Receipt, ScanLine, Search, Settings, ShoppingCart,
  Sun, Truck, UserCog, Users, Wrench, X,
} from "lucide-react";
import { api, tokens } from "@/lib/api";
import { JewelleryImage, Logo } from "./art";

export type Me = {
  username: string; name: string; role: string; company: string | null;
  branch: { id: string; name: string } | null; can_see_cost: boolean; all_branches?: boolean;
  permissions: Record<string, string[]>;
};
const MeCtx = createContext<Me | null>(null);
export const useMe = () => useContext(MeCtx)!;
export const can = (me: Me, module: string, action: string) => me.permissions[module]?.includes(action);

type Item = { href: string; label: string; icon: typeof BarChart3; module: string; need?: string };
const GROUPS: { label: string; items: Item[] }[] = [
  { label: "Overview", items: [{ href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, module: "dashboard" }] },
  { label: "Sales", items: [
    { href: "/pos", label: "POS Billing", icon: ScanLine, module: "sales", need: "create" },
    { href: "/invoices", label: "Invoices", icon: Receipt, module: "sales" },
    { href: "/customers", label: "Customers", icon: Users, module: "customers" },
    { href: "/schemes", label: "Gold Schemes", icon: PiggyBank, module: "schemes" },
  ] },
  { label: "Stock & Purchase", items: [
    { href: "/products", label: "Inventory", icon: Boxes, module: "products" },
    { href: "/purchases", label: "Purchases", icon: ShoppingCart, module: "purchases" },
    { href: "/suppliers", label: "Suppliers", icon: Truck, module: "suppliers" },
    { href: "/stones", label: "Diamond & Stones", icon: Diamond, module: "diamonds" },
    { href: "/old-gold", label: "Old Gold", icon: Coins, module: "old_gold" },
    { href: "/hallmark", label: "Hallmark & HUID", icon: BadgeCheck, module: "hallmark" },
  ] },
  { label: "Production", items: [
    { href: "/karigars", label: "Karigars", icon: Hammer, module: "karigars" },
    { href: "/manufacturing", label: "Manufacturing", icon: Factory, module: "manufacturing" },
    { href: "/repairs", label: "Repairs & Custom", icon: Wrench, module: "repairs" },
  ] },
  { label: "Finance & Admin", items: [
    { href: "/accounting", label: "Accounting", icon: Landmark, module: "accounting" },
    { href: "/gst", label: "GST & Tax", icon: FileText, module: "gst" },
    { href: "/hr", label: "HR & Payroll", icon: UserCog, module: "hr" },
    { href: "/reports", label: "Reports", icon: LineChart, module: "reports" },
    { href: "/settings", label: "Settings", icon: Settings, module: "company" },
  ] },
];
const ALL = GROUPS.flatMap((g) => g.items);
const QUICK = [
  { label: "New POS bill", href: "/pos", module: "sales" }, { label: "New purchase", href: "/purchases?new=1", module: "purchases" },
  { label: "Add product", href: "/products?add=1", module: "products" }, { label: "Add customer", href: "/customers?add=1", module: "customers" },
  { label: "New repair job", href: "/repairs?add=1", module: "repairs" }, { label: "Add expense / voucher", href: "/accounting?new=1", module: "accounting" },
];

function useOutside(ref: React.RefObject<HTMLElement | null>, close: () => void) {
  useEffect(() => {
    const h = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && close();
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  });
}

function Palette({ me, onClose }: { me: Me; onClose: () => void }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [res, setRes] = useState<{ label: string; sub: string; href: string; art?: { name: string; category: string; metal: string } }[]>([]);
  const pages = useMemo(() => ALL.filter((i) => can(me, i.module, "view") && i.label.toLowerCase().includes(q.toLowerCase())).slice(0, 5), [me, q]);
  useEffect(() => {
    if (q.trim().length < 2) { setRes([]); return; }
    const t = setTimeout(async () => {
      const out: typeof res = [];
      try {
        if (can(me, "products", "view")) {
          const p = await api<{ results: { sku: string; name: string; category_name: string; metal: string; net_weight: string }[] }>(`/products/?search=${encodeURIComponent(q)}`);
          p.results.slice(0, 5).forEach((x) => out.push({ label: x.name, sub: `${x.sku} · ${x.net_weight} g net`, href: `/products?q=${encodeURIComponent(x.sku)}`, art: { name: x.name, category: x.category_name, metal: x.metal } }));
        }
        if (can(me, "customers", "view")) {
          const c = await api<{ results: { name: string; phone: string }[] }>(`/customers/?search=${encodeURIComponent(q)}`);
          c.results.slice(0, 4).forEach((x) => out.push({ label: x.name, sub: `Customer · ${x.phone}`, href: `/customers?q=${encodeURIComponent(x.name)}` }));
        }
      } catch { /* ignore */ }
      setRes(out);
    }, 300);
    return () => clearTimeout(t);
  }, [q, me]);
  const go = (href: string) => { onClose(); router.push(href); };
  return (
    <div className="fixed inset-0 z-[60] bg-black/50 grid place-items-start justify-center pt-24 px-4" onClick={onClose}>
      <div className="card w-full max-w-xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 px-4 border-b border-line">
          <Search size={18} className="text-muted" />
          <input autoFocus className="flex-1 bg-transparent py-4 outline-none text-sm" placeholder="Search pages, SKU, barcode, product, customer…" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Escape" && onClose()} />
          <kbd className="text-xs text-muted border border-line rounded px-1.5 py-0.5">Esc</kbd>
        </div>
        <div className="max-h-96 overflow-y-auto p-2 text-sm">
          {pages.length > 0 && <div className="px-2 py-1 th">Pages</div>}
          {pages.map((p) => <button key={p.href} className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-soft text-left" onClick={() => go(p.href)}><p.icon size={16} className="text-gold" />{p.label}</button>)}
          {res.length > 0 && <div className="px-2 py-1 th mt-2">Records</div>}
          {res.map((r, i) => (
            <button key={i} className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-soft text-left" onClick={() => go(r.href)}>
              {r.art ? <JewelleryImage {...r.art} className="w-9 h-9 rounded-lg" /> : <Users size={16} className="text-gold" />}
              <span><span className="block font-medium">{r.label}</span><span className="text-xs text-muted">{r.sub}</span></span>
            </button>
          ))}
          {q.length >= 2 && pages.length === 0 && res.length === 0 && <div className="p-4 text-muted">No results.</div>}
        </div>
      </div>
    </div>
  );
}

type Notif = { low_stock: { name: string; pieces: number }[]; pending_repairs: number; customer_due: string };

function Bell_({ me }: { me: Me }) {
  const [open, setOpen] = useState(false);
  const [n, setN] = useState<Notif | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  useOutside(ref, () => setOpen(false));
  useEffect(() => { if (can(me, "dashboard", "view")) api<Notif>("/dashboard/overview/").then(setN).catch(() => {}); }, [me]);
  const items: { text: string; href: string }[] = [];
  n?.low_stock.forEach((l) => items.push({ text: `Low stock: ${l.name} (${l.pieces} pcs left)`, href: "/products" }));
  if (n && n.pending_repairs > 0) items.push({ text: `${n.pending_repairs} repair / custom jobs pending`, href: "/repairs" });
  if (n && Number(n.customer_due) > 0) items.push({ text: `Customer dues ₹${Number(n.customer_due).toLocaleString("en-IN")}`, href: "/invoices" });
  return (
    <div className="relative" ref={ref}>
      <button aria-label="Notifications" className="relative p-2 rounded-full hover:bg-soft" onClick={() => setOpen(!open)}>
        <Bell size={18} />{items.length > 0 && <span className="absolute top-0.5 right-0.5 min-w-4 h-4 px-1 rounded-full bg-danger text-white text-[10px] grid place-items-center">{items.length}</span>}
      </button>
      {open && (
        <div className="card absolute right-0 mt-2 w-80 p-2 z-40 text-sm">
          <div className="px-2 py-1 th">Alerts</div>
          {items.length === 0 && <div className="p-3 text-muted">Everything looks good.</div>}
          {items.map((i, k) => <Link key={k} href={i.href} onClick={() => setOpen(false)} className="flex gap-2 items-start px-2 py-2 rounded-lg hover:bg-soft"><AlertTriangle size={15} className="text-warning mt-0.5 shrink-0" />{i.text}</Link>)}
        </div>
      )}
    </div>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [drawer, setDrawer] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [dark, setDark] = useState(false);
  const [palette, setPalette] = useState(false);
  const [quick, setQuick] = useState(false);
  const [profile, setProfile] = useState(false);
  const [closed, setClosed] = useState<Record<string, boolean>>({});
  const [now, setNow] = useState<Date | null>(null);
  const qRef = useRef<HTMLDivElement>(null), pRef = useRef<HTMLDivElement>(null);
  useOutside(qRef, () => setQuick(false));
  useOutside(pRef, () => setProfile(false));

  useEffect(() => {
    if (!tokens.get()) { location.href = "/login"; return; }
    api<Me>("/auth/me/").then(setMe).catch(() => {});
    const d = localStorage.getItem("nirghos_dark") === "1";
    setDark(d); document.documentElement.classList.toggle("dark", d);
    setCollapsed(localStorage.getItem("nirghos_collapsed") === "1");
    setNow(new Date());
    const t = setInterval(() => setNow(new Date()), 30000);
    const k = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPalette(true); } };
    window.addEventListener("keydown", k);
    return () => { clearInterval(t); window.removeEventListener("keydown", k); };
  }, []);
  useEffect(() => setDrawer(false), [path]);

  const toggleDark = () => { const d = !dark; setDark(d); localStorage.setItem("nirghos_dark", d ? "1" : "0"); document.documentElement.classList.toggle("dark", d); };
  const toggleCollapse = () => { const c = !collapsed; setCollapsed(c); localStorage.setItem("nirghos_collapsed", c ? "1" : "0"); };

  if (!me) return <div className="min-h-screen grid place-items-center bg-navy"><Logo size={56} className="animate-pulse" /></div>;
  const current = ALL.find((i) => path.startsWith(i.href));
  const narrow = collapsed && !drawer;

  const sidebar = (
    <aside className={`${drawer ? "fixed inset-y-0 left-0 z-50 w-72" : "hidden lg:flex lg:sticky lg:top-0 lg:h-screen"} ${narrow ? "lg:w-[76px]" : "lg:w-64"} shrink-0 flex-col bg-navy text-white transition-[width] duration-200`}>
      <div className={`flex items-center gap-3 px-4 h-[72px] border-b border-white/10 ${narrow ? "justify-center" : ""}`}>
        <Logo size={34} />
        {!narrow && <div className="leading-tight"><div className="font-serif text-xl tracking-wide gold-text">NIRGHOS</div><div className="text-[10px] tracking-[0.25em] text-white/60">JEWELLERY ERP</div></div>}
        {drawer && <button className="ml-auto" onClick={() => setDrawer(false)} aria-label="Close menu"><X size={20} /></button>}
      </div>
      <nav className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        {GROUPS.map((g) => {
          const items = g.items.filter((i) => can(me, i.module, i.need || "view"));
          if (!items.length) return null;
          const shut = closed[g.label] && !items.some((i) => path.startsWith(i.href));
          return (
            <div key={g.label}>
              {!narrow && g.label !== "Overview" && (
                <button className="w-full flex items-center justify-between px-3 py-1 text-[11px] uppercase tracking-wider text-white/45 hover:text-white/70" onClick={() => setClosed({ ...closed, [g.label]: !closed[g.label] })}>
                  {g.label}<ChevronDown size={13} className={shut ? "-rotate-90" : ""} />
                </button>
              )}
              {!shut && items.map((n) => {
                const active = path.startsWith(n.href);
                return (
                  <Link key={n.href} href={n.href} className={`group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm my-0.5 transition ${active ? "bg-white/10 text-gold" : "text-white/75 hover:bg-white/5 hover:text-white"} ${narrow ? "justify-center" : ""}`}>
                    {active && <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r bg-gold" />}
                    <n.icon size={18} />
                    {!narrow && n.label}
                    {narrow && <span className="pointer-events-none absolute left-full ml-3 z-50 whitespace-nowrap rounded-md bg-navy-2 border border-white/10 px-2.5 py-1 text-xs opacity-0 group-hover:opacity-100 shadow-lg">{n.label}</span>}
                  </Link>
                );
              })}
            </div>
          );
        })}
      </nav>
      {!narrow && (
        <div className="m-3 rounded-2xl overflow-hidden relative border border-white/10 bg-navy-2">
          <JewelleryImage name="Gold Necklace" category="Necklace" className="absolute right-[-6px] top-1 w-16 h-16 opacity-90 bg-transparent" />
          <div className="relative p-3 pr-16 text-xs"><div className="text-gold font-semibold">Crafting Trust</div><div className="text-white/70">Building Excellence</div></div>
        </div>
      )}
      <button className="hidden lg:flex items-center justify-center gap-2 h-11 border-t border-white/10 text-white/60 hover:text-white text-xs" onClick={toggleCollapse}>
        {collapsed ? <ChevronsRight size={16} /> : <><ChevronsLeft size={16} /> Collapse</>}
      </button>
    </aside>
  );

  return (
    <MeCtx.Provider value={me}>
      <div className="min-h-screen lg:flex">
        {drawer && <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={() => setDrawer(false)} />}
        {sidebar}
        <div className="flex-1 min-w-0">
          <header className="flex items-center gap-3 px-4 lg:px-6 h-[72px] border-b border-line bg-card/90 backdrop-blur sticky top-0 z-30">
            <button className="lg:hidden p-2 -ml-2" onClick={() => setDrawer(true)} aria-label="Menu"><Menu /></button>
            <div className="hidden md:block text-sm min-w-0">
              <div className="text-muted truncate">Home <span className="mx-1">/</span> <span className="text-ink font-medium">{current?.label ?? "Page"}</span></div>
            </div>
            <button onClick={() => setPalette(true)} className="flex-1 max-w-xl mx-auto flex items-center gap-2 rounded-full border border-line bg-soft px-4 py-2 text-sm text-muted hover:border-gold">
              <Search size={16} /><span className="truncate">Search anything…</span><kbd className="ml-auto hidden sm:block text-[11px] border border-line rounded px-1.5">Ctrl K</kbd>
            </button>
            <div className="hidden xl:block text-right text-xs text-muted leading-tight">
              <div>{now?.toLocaleDateString("en-IN", { weekday: "short", day: "2-digit", month: "short", year: "numeric" })}</div>
              <div className="text-ink font-semibold text-sm">{now?.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}</div>
            </div>
            <div className="hidden md:block rounded-full border border-line px-3 py-1.5 text-xs bg-soft" title="Your branch scope">{me.branch?.name ?? "All branches"}</div>
            <div className="relative" ref={qRef}>
              <button className="btn btn-gold !rounded-full" onClick={() => setQuick(!quick)}><Plus size={16} /><span className="hidden sm:inline">Quick create</span></button>
              {quick && (
                <div className="card absolute right-0 mt-2 w-56 p-1.5 z-40 text-sm">
                  {QUICK.filter((q) => can(me, q.module, "create")).map((q) => <button key={q.href} className="w-full text-left px-3 py-2 rounded-lg hover:bg-soft" onClick={() => { setQuick(false); router.push(q.href); }}>{q.label}</button>)}
                </div>
              )}
            </div>
            <Bell_ me={me} />
            <button onClick={toggleDark} aria-label="Toggle theme" className="p-2 rounded-full hover:bg-soft">{dark ? <Sun size={18} /> : <Moon size={18} />}</button>
            <div className="relative" ref={pRef}>
              <button className="flex items-center gap-2" onClick={() => setProfile(!profile)}>
                <span className="w-9 h-9 rounded-full bg-navy text-gold grid place-items-center font-semibold">{me.name.slice(0, 1).toUpperCase()}</span>
                <span className="hidden md:block text-left leading-tight"><span className="block text-sm font-semibold">{me.name}</span><span className="block text-xs text-muted capitalize">{me.role.replace("_", " ")}</span></span>
                <ChevronDown size={14} className="hidden md:block text-muted" />
              </button>
              {profile && (
                <div className="card absolute right-0 mt-2 w-56 p-1.5 z-40 text-sm">
                  <div className="px-3 py-2 border-b border-line mb-1"><div className="font-semibold">{me.name}</div><div className="text-xs text-muted">{me.company}</div></div>
                  <button className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-soft text-danger" onClick={() => { tokens.clear(); location.href = "/login"; }}><LogOut size={15} /> Log out</button>
                </div>
              )}
            </div>
          </header>
          <main className="p-4 lg:p-6 max-w-[1600px]">{children}</main>
        </div>
      </div>
      {palette && <Palette me={me} onClose={() => setPalette(false)} />}
    </MeCtx.Provider>
  );
}
