"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowDownRight, ArrowUpRight, Boxes, FileText, Gem, ShoppingCart, Users, Wallet, BarChart3, ScanLine, Wrench } from "lucide-react";
import { compact, money, moneyInt } from "@/lib/api";
import { HeroArt, JewelleryImage } from "@/components/art";
import { can, useMe } from "@/components/shell";
import { Err, useFetch } from "@/components/ui";

type Pt = { d?: string; date?: string; t: string };
type Overview = {
  sales_today: string; sales_month: string; sales_prev_month: string; invoices_today: number; customer_due: string; customers: number; new_customers_month: number;
  stock: Record<string, { pieces: number; gross: string; net: string; fine: string }>; trend: Pt[]; purchase_trend?: Pt[];
  sales_by_category: { name: string; value: string }[]; top_products: { name: string; category: string; value: string; pieces: number }[];
  low_stock: { name: string; pieces: number }[]; recent_transactions: { type: string; ref: string; amount: string; at: string }[];
  branch_performance?: { name: string; sales: string; purchase: string }[];
  stones: { n: number; ct: string | null }; karigar_fine_pending: string; pending_repairs: number;
  purchases_month?: string; gross_profit_month?: string; stock_value?: string; cash_in_hand?: string; bank_balance?: string; supplier_due?: string;
};
const PALETTE = ["#101B35", "#C9A45C", "#B7BECB", "#E8D7B1", "#4B5D8A", "#8E6D2B", "#7C8596"];

function Spark({ data, color = "#C9A45C" }: { data: number[]; color?: string }) {
  const pts = data.map((v, i) => ({ i, v }));
  return (
    <ResponsiveContainer width="100%" height={44}>
      <AreaChart data={pts} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
        <defs><linearGradient id={`s${color.slice(1)}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={color} stopOpacity={0.35} /><stop offset="1" stopColor={color} stopOpacity={0} /></linearGradient></defs>
        <Area type="monotone" dataKey="v" stroke={color} strokeWidth={2} fill={`url(#s${color.slice(1)})`} isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function Kpi({ icon: Icon, label, value, delta, spark, sub }: { icon: typeof Wallet; label: string; value: string; delta?: number | null; spark?: number[]; sub?: string }) {
  return (
    <div className="card p-4 overflow-hidden">
      <div className="flex items-center gap-3">
        <span className="w-11 h-11 rounded-full bg-navy text-gold grid place-items-center shrink-0"><Icon size={20} /></span>
        <div className="min-w-0">
          <div className="text-sm text-muted">{label}</div>
          <div className="text-2xl font-semibold tracking-tight truncate">{value}</div>
        </div>
      </div>
      <div className="flex items-end justify-between mt-2">
        <div className="text-xs">
          {delta !== null && delta !== undefined ? (
            <span className={`inline-flex items-center gap-0.5 font-semibold ${delta >= 0 ? "text-success" : "text-danger"}`}>{delta >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}{Math.abs(delta).toFixed(1)}% <span className="text-muted font-normal ml-1">vs last month</span></span>
          ) : <span className="text-muted">{sub ?? "this month"}</span>}
        </div>
        {spark && spark.length > 1 && <div className="w-28 -mb-1"><Spark data={spark} /></div>}
      </div>
    </div>
  );
}

function fill30(trend: Pt[] = []) {
  const m = new Map(trend.map((p) => [(p.d ?? p.date)!, Number(p.t)]));
  const out: { day: string; v: number }[] = [];
  for (let i = 29; i >= 0; i--) {
    const d = new Date(); d.setDate(d.getDate() - i);
    const k = d.toLocaleDateString("en-CA");
    out.push({ day: k, v: m.get(k) ?? 0 });
  }
  return out;
}

export default function Dashboard() {
  const me = useMe();
  const { data: d, error } = useFetch<Overview>("/dashboard/overview/");
  const [series, setSeries] = useState<"sales" | "purchase">("sales");
  const sales30 = useMemo(() => fill30(d?.trend), [d]);
  const pur30 = useMemo(() => fill30(d?.purchase_trend), [d]);
  const cat = useMemo(() => (d?.sales_by_category ?? []).map((c) => ({ name: c.name, value: Number(c.value) })), [d]);
  const catTotal = cat.reduce((a, c) => a + c.value, 0);

  if (error) return <Err>{error}</Err>;
  if (!d) return (
    <div className="space-y-4"><div className="skeleton h-44 !rounded-2xl" /><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[0, 1, 2, 3].map((i) => <div key={i} className="skeleton h-28 !rounded-2xl" />)}</div><div className="skeleton h-72 !rounded-2xl" /></div>
  );
  const sm = Number(d.sales_month), pm = Number(d.sales_prev_month);
  const delta = pm > 0 ? ((sm - pm) / pm) * 100 : null;
  const costView = d.purchases_month !== undefined;
  const quick = [
    { label: "New POS Bill", href: "/pos", icon: ScanLine, m: "sales" }, { label: "New Purchase", href: "/purchases?new=1", icon: ShoppingCart, m: "purchases" },
    { label: "Add Product", href: "/products?add=1", icon: Gem, m: "products" }, { label: "Add Customer", href: "/customers?add=1", icon: Users, m: "customers" },
    { label: "New Repair", href: "/repairs?add=1", icon: Wrench, m: "repairs" }, { label: "Reports", href: "/reports", icon: BarChart3, m: "reports" },
  ].filter((q) => can(me, q.m, q.m === "reports" ? "view" : "create"));
  const series30 = series === "sales" ? sales30 : pur30;
  const total30 = series30.reduce((a, p) => a + p.v, 0);
  const hour = new Date().getHours();
  const greet = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <div className="space-y-5">
      <section className="relative overflow-hidden rounded-2xl bg-navy text-white min-h-[150px]">
        <HeroArt className="absolute inset-y-0 right-0 h-full w-full md:w-3/5 opacity-90" />
        <div className="absolute inset-0 bg-gradient-to-r from-navy via-navy/90 to-transparent" />
        <div className="relative p-6 md:p-8 max-w-xl">
          <h1 className="font-serif text-3xl md:text-4xl gold-text">{greet}, {me.name}!</h1>
          <p className="text-white/75 mt-2 text-sm md:text-base">Here&apos;s what&apos;s happening with your jewellery business today.</p>
          <div className="flex gap-6 mt-4 text-sm">
            <div><div className="text-white/50 text-xs">Sales today</div><div className="text-lg font-semibold">{moneyInt(d.sales_today)}</div></div>
            <div><div className="text-white/50 text-xs">Invoices today</div><div className="text-lg font-semibold">{d.invoices_today}</div></div>
            <div><div className="text-white/50 text-xs">Pending repairs</div><div className="text-lg font-semibold">{d.pending_repairs}</div></div>
          </div>
        </div>
      </section>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi icon={Wallet} label="Total Sales (month)" value={moneyInt(d.sales_month)} delta={delta} spark={sales30.map((p) => p.v)} />
        {costView ? <Kpi icon={ShoppingCart} label="Total Purchase (month)" value={moneyInt(d.purchases_month)} spark={pur30.map((p) => p.v)} />
          : <Kpi icon={FileText} label="Customer Due" value={moneyInt(d.customer_due)} sub="outstanding" />}
        {costView ? <Kpi icon={BarChart3} label="Gross Profit (month)" value={moneyInt(d.gross_profit_month)} sub="sales value − item cost − discounts" />
          : <Kpi icon={Boxes} label="Gold in stock" value={`${d.stock.gold?.fine ?? 0} g`} sub="fine weight" />}
        {costView ? <Kpi icon={Boxes} label="Stock Value (cost)" value={moneyInt(d.stock_value)} sub={`${Object.values(d.stock).reduce((a, s) => a + s.pieces, 0)} pieces`} />
          : <Kpi icon={Users} label="Customers" value={String(d.customers)} sub={`${d.new_customers_month} new this month`} />}
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <div className="card p-5 xl:col-span-2">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <h2 className="font-semibold flex items-center gap-2"><BarChart3 size={18} className="text-gold" /> {series === "sales" ? "Sales" : "Purchase"} Analytics</h2>
            {costView && <div className="flex rounded-lg border border-line text-xs overflow-hidden">{(["sales", "purchase"] as const).map((s) => <button key={s} onClick={() => setSeries(s)} className={`px-3 py-1.5 capitalize ${series === s ? "bg-navy text-white dark:bg-gold dark:text-navy" : ""}`}>{s}</button>)}</div>}
          </div>
          <div className="mt-2 flex items-baseline gap-3"><span className="text-3xl font-semibold">{moneyInt(total30)}</span><span className="text-sm text-muted">last 30 days</span></div>
          <div className="h-64 mt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={series30} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
                <defs><linearGradient id="ga" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#C9A45C" stopOpacity={0.35} /><stop offset="1" stopColor="#C9A45C" stopOpacity={0} /></linearGradient></defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
                <XAxis dataKey="day" tickFormatter={(v: string) => v.slice(8)} tick={{ fontSize: 11, fill: "#788292" }} axisLine={false} tickLine={false} interval={3} />
                <YAxis tickFormatter={(v: number) => compact(v)} tick={{ fontSize: 11, fill: "#788292" }} axisLine={false} tickLine={false} />
                <Tooltip formatter={(v) => [money(Number(v)), series]} labelFormatter={(l) => String(l)} contentStyle={{ borderRadius: 10, border: "1px solid var(--line)", background: "var(--card)" }} />
                <Area type="monotone" dataKey="v" stroke="#101B35" strokeWidth={2.5} fill="url(#ga)" dot={false} activeDot={{ r: 5, fill: "#C9A45C" }} className="dark:[&_path]:stroke-[#C9A45C]" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card p-5">
          <h2 className="font-semibold flex items-center gap-2"><Gem size={18} className="text-gold" /> Sales by Category</h2>
          {cat.length === 0 ? <div className="text-sm text-muted py-16 text-center">No sales this month.</div> : (
            <>
              <div className="h-52 relative">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart><Pie data={cat} dataKey="value" nameKey="name" innerRadius={58} outerRadius={84} paddingAngle={2} stroke="none">{cat.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}</Pie>
                    <Tooltip formatter={(v) => money(Number(v))} contentStyle={{ borderRadius: 10, border: "1px solid var(--line)", background: "var(--card)" }} /></PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 grid place-items-center pointer-events-none text-center"><div><div className="text-lg font-semibold">₹{compact(catTotal)}</div><div className="text-xs text-muted">This month</div></div></div>
              </div>
              <ul className="text-sm space-y-1.5 mt-2">
                {cat.slice(0, 5).map((c, i) => <li key={c.name} className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full" style={{ background: PALETTE[i % PALETTE.length] }} /><span className="flex-1 truncate">{c.name}</span><span className="text-muted">{((c.value / catTotal) * 100).toFixed(0)}%</span></li>)}
              </ul>
            </>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="card p-5">
          <div className="flex items-center justify-between"><h2 className="font-semibold">Quick Actions</h2></div>
          <div className="grid grid-cols-3 gap-2.5 mt-3">
            {quick.map((q) => (
              <Link key={q.label} href={q.href} className="rounded-xl border border-line bg-soft hover:border-gold hover:shadow-sm transition p-3 text-center text-xs font-medium">
                <q.icon size={22} className="mx-auto mb-1.5 text-navy dark:text-gold" />{q.label}
              </Link>
            ))}
          </div>
          <h3 className="font-semibold mt-5 mb-2 text-sm">Stock on hand</h3>
          <div className="space-y-2">
            {Object.entries(d.stock).map(([m, s]) => (
              <div key={m} className="flex items-center gap-3 rounded-xl bg-soft p-2.5">
                <JewelleryImage name={m === "silver" ? "Silver Coin" : "Gold Coin"} category="coin" metal={m} className="w-11 h-11 rounded-lg" />
                <div className="flex-1 text-sm"><div className="font-medium capitalize">{m}</div><div className="text-xs text-muted">{s.pieces} pcs · gross {s.gross} g</div></div>
                <div className="text-right text-sm"><div className="font-semibold">{s.fine} g</div><div className="text-xs text-muted">fine</div></div>
              </div>
            ))}
            <div className="flex items-center gap-3 rounded-xl bg-soft p-2.5">
              <JewelleryImage name="Diamond" category="diamond" className="w-11 h-11 rounded-lg" />
              <div className="flex-1 text-sm"><div className="font-medium">Diamonds & gemstones</div><div className="text-xs text-muted">{d.stones.n} stones available</div></div>
              <div className="text-right text-sm"><div className="font-semibold">{d.stones.ct ? Number(d.stones.ct).toFixed(2) : "0.00"} ct</div></div>
            </div>
          </div>
        </div>

        <div className="card p-5">
          <h2 className="font-semibold">Low Stock Alerts</h2>
          {d.low_stock.length === 0 ? <div className="text-sm text-muted py-6">No low-stock categories.</div> : (
            <table className="w-full text-sm mt-3"><thead><tr className="th text-left"><th className="py-1">Category</th><th>Pieces left</th><th /></tr></thead><tbody>
              {d.low_stock.map((l) => <tr key={l.name} className="border-t border-line"><td className="py-2.5 flex items-center gap-2"><JewelleryImage name={l.name} category={l.name} className="w-8 h-8 rounded-lg" />{l.name}</td><td>{l.pieces}</td><td className="text-right"><span className="badge badge-danger">Low stock</span></td></tr>)}
            </tbody></table>
          )}
          <h2 className="font-semibold mt-6">Top Selling (month)</h2>
          {d.top_products.length === 0 ? <div className="text-sm text-muted py-4">No sales this month.</div> : (
            <ul className="mt-2 divide-y divide-line text-sm">
              {d.top_products.map((p) => <li key={p.name} className="flex items-center gap-3 py-2"><JewelleryImage name={p.name} category={p.category} className="w-10 h-10 rounded-lg" /><span className="flex-1 min-w-0"><span className="block truncate font-medium">{p.name}</span><span className="text-xs text-muted">{p.category}</span></span><b>{moneyInt(p.value)}</b></li>)}
            </ul>
          )}
        </div>

        <div className="space-y-4">
          <div className="card p-5">
            <h2 className="font-semibold">Recent Transactions</h2>
            <table className="w-full text-sm mt-3"><thead><tr className="th text-left"><th className="py-1">Type</th><th>ID</th><th className="text-right">Amount</th></tr></thead><tbody>
              {d.recent_transactions.map((t, i) => (
                <tr key={i} className="border-t border-line"><td className="py-2"><span className={`badge ${t.type === "Sale" ? "badge-success" : t.type === "Purchase" ? "badge-info" : "badge-warning"}`}>{t.type}</span></td>
                  <td className="text-muted">{t.ref}</td><td className="text-right font-medium">{moneyInt(t.amount)}</td></tr>
              ))}
              {d.recent_transactions.length === 0 && <tr><td colSpan={3} className="py-4 text-muted">No transactions yet.</td></tr>}
            </tbody></table>
          </div>
          {d.branch_performance && d.branch_performance.length > 0 && (
            <div className="card p-5">
              <h2 className="font-semibold">Branch Performance</h2>
              <div className="h-44 mt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={d.branch_performance.map((b) => ({ name: b.name.replace(/ (Main )?Showroom/, ""), Sales: Number(b.sales), Purchase: Number(b.purchase) }))} margin={{ top: 8, right: 0, bottom: 0, left: -14 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#788292" }} axisLine={false} tickLine={false} />
                    <YAxis tickFormatter={(v: number) => compact(v)} tick={{ fontSize: 11, fill: "#788292" }} axisLine={false} tickLine={false} />
                    <Tooltip formatter={(v) => money(Number(v))} contentStyle={{ borderRadius: 10, border: "1px solid var(--line)", background: "var(--card)" }} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="Sales" fill="#101B35" radius={[4, 4, 0, 0]} /><Bar dataKey="Purchase" fill="#C9A45C" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      </div>

      {d.cash_in_hand !== undefined && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {[["Cash in hand", moneyInt(d.cash_in_hand)], ["Bank balance", moneyInt(d.bank_balance)], ["Supplier due", moneyInt(d.supplier_due)], ["Customer due", moneyInt(d.customer_due)], ["Fine gold with karigars", `${d.karigar_fine_pending} g`]].map(([l, v]) => (
            <div key={l} className="card p-4"><div className="text-sm text-muted">{l}</div><div className="text-xl font-semibold mt-1">{v}</div></div>
          ))}
        </div>
      )}
    </div>
  );
}
