"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { Printer, ScanLine, Trash2 } from "lucide-react";
import { api, money, Page } from "@/lib/api";
import { JewelleryImage } from "@/components/art";
import { PageHeader } from "@/components/ui";

type Product = { id: string; name: string; sku: string; net_weight: string; fine_weight: string; purity: string; metal: string; barcode: string; category_name: string; status: string; huid: string; image: string | null };
type Customer = { id: string; name: string };
type OG = { id: string; number: string; value: string; fine_weight: string };
type Invoice = {
  id: string; number: string; metal_total: string; making_total: string; stone_total: string; hallmark_total: string;
  discount: string; old_gold_adjustment: string; taxable_value: string; gst_rate: string; gst_amount: string; grand_total: string; paid: string; balance: string;
};

export default function POS() {
  const [code, setCode] = useState("");
  const [cart, setCart] = useState<Product[]>([]);
  const [catalog, setCatalog] = useState<Product[]>([]);
  const [cq, setCq] = useState("");
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customer, setCustomer] = useState("");
  const [ogs, setOgs] = useState<OG[]>([]);
  const [ogSel, setOgSel] = useState<string[]>([]);
  const [discount, setDiscount] = useState("0");
  const [method, setMethod] = useState("cash");
  const [amount, setAmount] = useState("");
  const [hallmark, setHallmark] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [done, setDone] = useState<Invoice | null>(null);
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLInputElement>(null);

  const loadCatalog = useCallback(() => {
    api<Page<Product>>(`/products/?status=available&search=${encodeURIComponent(cq)}`).then((d) => setCatalog(d.results)).catch(() => {});
  }, [cq]);
  useEffect(() => { const t = setTimeout(loadCatalog, 250); return () => clearTimeout(t); }, [loadCatalog, done]);
  useEffect(() => {
    api<Page<Customer>>("/customers/").then((d) => setCustomers(d.results)).catch(() => {});
    api<Page<OG>>("/old-gold/?status=received&payout=exchange").then((d) => setOgs(d.results)).catch(() => {});
  }, [done]);

  function add(p: Product) {
    if (p.status !== "available") return setMsg({ ok: false, text: "Item is not available" });
    if (cart.some((x) => x.id === p.id)) return setMsg({ ok: false, text: "Already in bill" });
    setCart((c) => [...c, p]); setMsg(null);
  }

  async function scan(e: React.FormEvent) {
    e.preventDefault();
    const c = code.trim();
    if (!c) return;
    try {
      let p: Product;
      try { p = await api<Product>(`/products/scan/${encodeURIComponent(c)}/`); } catch {
        const r = await api<Page<Product>>(`/products/?search=${encodeURIComponent(c)}&status=available`);
        if (!r.results.length) throw new Error("Item not found");
        p = r.results[0];
      }
      add(p); setCode("");
    } catch (e) { setMsg({ ok: false, text: e instanceof Error ? e.message : "Scan failed" }); }
    ref.current?.focus();
  }

  async function complete() {
    if (!confirm(`Complete sale of ${cart.length} item(s)?`)) return;
    setBusy(true);
    try {
      const inv = await api<Invoice>("/sales/invoices/", {
        method: "POST",
        body: { customer: customer || null, product_ids: cart.map((c) => c.id), discount: discount || "0", include_hallmark: hallmark, old_gold_ids: ogSel, payments: amount ? [{ method, amount }] : [] },
      });
      setDone(inv); setCart([]); setAmount(""); setDiscount("0"); setOgSel([]);
      setMsg({ ok: true, text: `Invoice ${inv.number} created` });
    } catch (e) { setMsg({ ok: false, text: e instanceof Error ? e.message : "Failed" }); } finally { setBusy(false); }
  }

  const inCart = new Set(cart.map((c) => c.id));
  return (
    <div className="space-y-4">
      <PageHeader title="POS Billing" subtitle="Scan a barcode or tap a piece. Prices, making charges and GST are calculated by the server." />
      <div className="grid gap-4 xl:grid-cols-[1fr_380px]">
        <div className="space-y-4 min-w-0">
          <form onSubmit={scan} className="relative">
            <ScanLine size={18} className="absolute left-3.5 top-3 text-gold" />
            <input ref={ref} autoFocus className="input !pl-10 !py-2.5" placeholder="Scan barcode or search SKU / name / HUID, press Enter" value={code} onChange={(e) => setCode(e.target.value)} />
          </form>
          {msg && <div className={`card p-3 text-sm ${msg.ok ? "text-success" : "text-danger"}`}>{msg.text}</div>}

          <div className="card">
            <div className="flex items-center justify-between px-4 py-3 border-b border-line"><h2 className="font-semibold">Current bill <span className="text-muted font-normal">({cart.length})</span></h2>
              {cart.length > 0 && <button className="text-sm text-danger" onClick={() => setCart([])}>Clear</button>}</div>
            {cart.length === 0 && <div className="p-8 text-center text-muted text-sm">No items yet. Scan or pick from the catalogue below.</div>}
            <div className="divide-y divide-line">
              {cart.map((p) => (
                <div key={p.id} className="p-3 flex items-center gap-3 text-sm">
                  <JewelleryImage name={p.name} category={p.category_name} metal={p.metal} src={p.image} className="w-12 h-12 rounded-lg" />
                  <div className="flex-1 min-w-0"><div className="font-semibold truncate">{p.name}</div><div className="text-xs text-muted">{p.sku} · {p.metal} {p.purity} · net {p.net_weight} g · fine {p.fine_weight} g{p.huid ? ` · HUID ${p.huid}` : ""}</div></div>
                  <button aria-label="Remove" className="text-muted hover:text-danger" onClick={() => setCart(cart.filter((x) => x.id !== p.id))}><Trash2 size={16} /></button>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="flex items-center gap-3 mb-3"><h2 className="font-semibold flex-1">Catalogue</h2><input className="input !w-56" placeholder="Filter pieces…" value={cq} onChange={(e) => setCq(e.target.value)} /></div>
            <div className="grid gap-3 grid-cols-2 md:grid-cols-3 2xl:grid-cols-4">
              {catalog.map((p) => (
                <button key={p.id} onClick={() => add(p)} disabled={inCart.has(p.id)} className={`card overflow-hidden text-left transition hover:border-gold hover:shadow-md ${inCart.has(p.id) ? "opacity-50" : ""}`}>
                  <JewelleryImage name={p.name} category={p.category_name} metal={p.metal} src={p.image} className="h-28 w-full" />
                  <div className="p-3"><div className="text-sm font-semibold truncate">{p.name}</div><div className="text-xs text-muted">{p.sku} · {p.net_weight} g</div></div>
                </button>
              ))}
              {catalog.length === 0 && <div className="text-sm text-muted col-span-full">No available pieces match.</div>}
            </div>
          </div>
        </div>

        <div className="card p-5 space-y-3 h-fit xl:sticky xl:top-24">
          <h2 className="font-semibold">Checkout</h2>
          <select className="input" value={customer} onChange={(e) => setCustomer(e.target.value)}>
            <option value="">Walk-in customer</option>
            {customers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <label className="text-sm block"><span className="text-muted">Discount (₹)</span><input className="input mt-1" type="number" min="0" value={discount} onChange={(e) => setDiscount(e.target.value)} /></label>
          <label className="text-sm flex items-center gap-2"><input type="checkbox" checked={hallmark} onChange={(e) => setHallmark(e.target.checked)} /> Add hallmarking charge</label>
          {ogs.length > 0 && (
            <div className="text-sm space-y-1 rounded-xl bg-soft p-3"><div className="th">Old gold exchange</div>
              {ogs.map((o) => (
                <label key={o.id} className="flex items-center gap-2"><input type="checkbox" checked={ogSel.includes(o.id)} onChange={(e) => setOgSel(e.target.checked ? [...ogSel, o.id] : ogSel.filter((x) => x !== o.id))} />
                  {o.number} · {o.fine_weight} g fine · {money(o.value)}</label>
              ))}</div>
          )}
          <div className="flex gap-2">
            <select className="input !w-28" value={method} onChange={(e) => setMethod(e.target.value)}>{["cash", "upi", "card", "bank"].map((m) => <option key={m}>{m}</option>)}</select>
            <input className="input" type="number" min="0" placeholder="Amount paid" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </div>
          <button className="btn btn-gold w-full !py-3 !text-base" disabled={!cart.length || busy} onClick={complete}>{busy ? "Processing…" : "Complete sale"}</button>
          {done && (
            <div className="text-sm border-t border-line pt-3 space-y-1">
              <div className="font-semibold text-base">{done.number}</div>
              {([["Metal (incl. wastage)", done.metal_total], ["Making", done.making_total], ["Stone", done.stone_total], ["Hallmark", done.hallmark_total]] as const).map(([l, v]) => <div key={l} className="flex justify-between"><span className="text-muted">{l}</span><span>{money(v)}</span></div>)}
              <div className="flex justify-between"><span className="text-muted">Discount</span><span>-{money(done.discount)}</span></div>
              <div className="flex justify-between"><span className="text-muted">Old gold</span><span>-{money(done.old_gold_adjustment)}</span></div>
              <div className="flex justify-between"><span className="text-muted">GST ({done.gst_rate}%)</span><span>{money(done.gst_amount)}</span></div>
              <div className="flex justify-between font-bold text-base rounded-lg bg-gold-light/40 dark:bg-white/5 px-2 py-1.5"><span>Total</span><span>{money(done.grand_total)}</span></div>
              <div className="flex justify-between"><span className="text-muted">Paid</span><span>{money(done.paid)}</span></div>
              <div className="flex justify-between"><span className="text-muted">Balance</span><span>{money(done.balance)}</span></div>
              <button className="btn btn-ghost w-full" onClick={() => window.print()}><Printer size={15} /> Print</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
