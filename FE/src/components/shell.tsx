"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { BadgeCheck, BarChart3, Boxes, Coins, Diamond, Factory, FileText, Gem, Hammer, Landmark, LineChart, LogOut, Menu, Moon, PiggyBank, Receipt, ScanLine, Settings, ShoppingCart, Sun, Truck, UserCog, Users, Wrench } from "lucide-react";
import { api, tokens } from "@/lib/api";

export type Me = {
  username: string; name: string; role: string; company: string | null;
  branch: { id: string; name: string } | null; can_see_cost: boolean;
  permissions: Record<string, string[]>;
};
const MeCtx = createContext<Me | null>(null);
export const useMe = () => useContext(MeCtx)!;
export const can = (me: Me, module: string, action: string) => me.permissions[module]?.includes(action);

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: BarChart3, module: "dashboard" },
  { href: "/pos", label: "POS Billing", icon: ScanLine, module: "sales" },
  { href: "/invoices", label: "Invoices", icon: Receipt, module: "sales" },
  { href: "/products", label: "Inventory", icon: Boxes, module: "products" },
  { href: "/purchases", label: "Purchases", icon: ShoppingCart, module: "purchases" },
  { href: "/customers", label: "Customers", icon: Users, module: "customers" },
  { href: "/suppliers", label: "Suppliers", icon: Truck, module: "suppliers" },
  { href: "/karigars", label: "Karigars", icon: Hammer, module: "karigars" },
  { href: "/manufacturing", label: "Manufacturing", icon: Factory, module: "manufacturing" },
  { href: "/repairs", label: "Repairs & Custom", icon: Wrench, module: "repairs" },
  { href: "/old-gold", label: "Old Gold", icon: Coins, module: "old_gold" },
  { href: "/stones", label: "Diamond & Stones", icon: Diamond, module: "diamonds" },
  { href: "/hallmark", label: "Hallmark & HUID", icon: BadgeCheck, module: "hallmark" },
  { href: "/schemes", label: "Gold Schemes", icon: PiggyBank, module: "schemes" },
  { href: "/accounting", label: "Accounting", icon: Landmark, module: "accounting" },
  { href: "/gst", label: "GST", icon: FileText, module: "gst" },
  { href: "/hr", label: "HR & Payroll", icon: UserCog, module: "hr" },
  { href: "/reports", label: "Reports", icon: LineChart, module: "reports" },
  { href: "/settings", label: "Settings", icon: Settings, module: "company" },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [me, setMe] = useState<Me | null>(null);
  const [open, setOpen] = useState(false);
  const [dark, setDark] = useState(false);

  useEffect(() => {
    if (!tokens.get()) { location.href = "/login"; return; }
    api<Me>("/auth/me/").then(setMe).catch(() => {});
    const d = localStorage.getItem("nirghos_dark") === "1";
    setDark(d);
    document.documentElement.classList.toggle("dark", d);
  }, []);

  function toggleDark() {
    const d = !dark;
    setDark(d);
    localStorage.setItem("nirghos_dark", d ? "1" : "0");
    document.documentElement.classList.toggle("dark", d);
  }

  if (!me) return <div className="min-h-screen grid place-items-center text-muted">Loading…</div>;
  const items = NAV.filter((n) => can(me, n.module, "view"));

  return (
    <MeCtx.Provider value={me}>
      <div className="min-h-screen lg:flex">
        <aside className={`${open ? "block" : "hidden"} lg:block lg:w-60 shrink-0 bg-navy text-white p-4 lg:sticky lg:top-0 lg:h-screen overflow-y-auto`}>
          <div className="flex items-center gap-2 text-gold font-bold text-lg mb-6"><Gem size={20} /> NIRGHOS</div>
          <nav className="space-y-1">
            {items.map((n) => (
              <Link key={n.href} href={n.href} onClick={() => setOpen(false)}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm ${path.startsWith(n.href) ? "bg-white/15 text-gold" : "text-white/80 hover:bg-white/10"}`}>
                <n.icon size={18} /> {n.label}
              </Link>
            ))}
          </nav>
        </aside>
        <div className="flex-1 min-w-0">
          <header className="flex items-center gap-3 px-4 py-3 border-b border-line bg-card sticky top-0 z-10">
            <button className="lg:hidden" onClick={() => setOpen(!open)} aria-label="Menu"><Menu /></button>
            <div className="text-sm text-muted flex-1">{me.company} · {me.branch?.name ?? "All branches"}</div>
            <button onClick={toggleDark} aria-label="Toggle theme">{dark ? <Sun size={18} /> : <Moon size={18} />}</button>
            <span className="text-sm">{me.name} <span className="text-muted">({me.role.replace("_", " ")})</span></span>
            <button aria-label="Logout" onClick={() => { tokens.clear(); location.href = "/login"; }}><LogOut size={18} /></button>
          </header>
          <main className="p-4 lg:p-6">{children}</main>
        </div>
      </div>
    </MeCtx.Provider>
  );
}
