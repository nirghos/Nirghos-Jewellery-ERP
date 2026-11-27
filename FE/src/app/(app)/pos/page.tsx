"use client";
import { useEffect, useRef, useState } from "react";
import { Trash2 } from "lucide-react";
import { api, money, Page } from "@/lib/api";

type Product = { id: string; name: string; sku: string; net_weight: string; purity: string; metal: string; barcode: string };
type Customer = { id: string; name: string };
type OG = { id: string; number: string; value: string; fine_weight: string; payout: string };
type Invoice = {
  id: string; number: string; metal_total: string; making_total: string; stone_total: string; hallmark_total: string;
  discount: string; taxable_value: string; gst_rate: string; gst_amount: string; grand_total: string; paid: string;
};

export default function POS() {
  const [code, setCode] = useState("");
  const [cart, setCart] = useState<Product[]>([]);
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

  useEffect(() => {
    api<Page<Customer>>("/customers/").then((d) => setCustomers(d.results)).catch(() => {});
    api<Page<OG>>("/old-gold/?status=received&payout=exchange").then((d) => setOgs(d.results)).catch(() => {});
  }, [done]);

  async function scan(e: React.FormEvent) {
    e.preventDefault();
    const c = code.trim();
    if (!c) return;
    try {
      let p: Product;
      try {
        p = await api<Product>(`/products/scan/${encodeURIComponent(c)}/`);
      } catch {
        const r = await api<Page<Product>>(`/products/?search=${encodeURIComponent(c)}&status=available`);
        if (!r.results.length) throw new Error("Item not found");
        p = r.results[0];
      }
      if ((p as Product & { status?: string }).status && (p as Product & { status?: string }).status !== "available") throw new Error("Item is not available");
      if (cart.some((x) => x.id === p.id)) throw new Error("Already in bill");
      setCart([...cart, p]);
      setMsg(null);
      setCode("");
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "Scan failed" });
    }
    ref.current?.focus();
  }

  async function complete() {
    if (!confirm(`Complete sale of ${cart.length} item(s)?`)) return;
    setBusy(true);
    try {
      const inv = await api<Invoice>("/sales/invoices/", {
        method: "POST",
        body: {
          customer: customer || null, product_ids: cart.map((c) => c.id), discount: discount || "0",
          include_hallmark: hallmark, old_gold_ids: ogSel, payments: amount ? [{ method, amount }] : [],
        },
      });
      setDone(inv);
      setCart([]); setAmount(""); setDiscount("0"); setOgSel([]);
      setMsg({ ok: true, text: `Invoice ${inv.number} created` });
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "Failed" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="lg:col-span-2 space-y-4">
        <h1 className="text-xl font-bold">POS Billing</h1>
        <form onSubmit={scan}>
          <input ref={ref} autoFocus className="input" placeholder="Scan barcode or search SKU / name / HUID, press Enter"
            value={code} onChange={(e) => setCode(e.target.value)} />
        </form>
        {msg && <div className={`card p-3 text-sm ${msg.ok ? "text-green-600" : "text-red-600"}`}>{msg.text}</div>}
        <div className="card divide-y divide-line">
          {cart.length === 0 && <div className="p-4 text-muted text-sm">Scan items to start a bill.</div>}
          {cart.map((p) => (
            <div key={p.id} className="p-3 flex items-center justify-between text-sm">
              <div><b>{p.name}</b><div className="text-muted">{p.sku} · {p.metal} {p.purity} · {p.net_weight} g net</div></div>
              <button aria-label="Remove" onClick={() => setCart(cart.filter((x) => x.id !== p.id))}><Trash2 size={16} /></button>
            </div>
          ))}
        </div>
      </div>

      <div className="card p-4 space-y-3 h-fit">
        <h2 className="font-semibold">Checkout</h2>
        <select className="input" value={customer} onChange={(e) => setCustomer(e.target.value)}>
          <option value="">Walk-in customer</option>
          {customers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <label className="text-sm block">Discount (₹)<input className="input" type="number" min="0" value={discount} onChange={(e) => setDiscount(e.target.value)} /></label>
        <label className="text-sm flex items-center gap-2"><input type="checkbox" checked={hallmark} onChange={(e) => setHallmark(e.target.checked)} /> Add hallmarking charge</label>
        {ogs.length > 0 && (
          <div className="text-sm space-y-1"><div className="text-muted">Old gold exchange</div>
            {ogs.map((o) => (
              <label key={o.id} className="flex items-center gap-2"><input type="checkbox" checked={ogSel.includes(o.id)} onChange={(e) => setOgSel(e.target.checked ? [...ogSel, o.id] : ogSel.filter((x) => x !== o.id))} />
                {o.number} · {o.fine_weight} g fine · {money(o.value)}</label>
            ))}</div>
        )}
        <div className="flex gap-2">
          <select className="input w-28" value={method} onChange={(e) => setMethod(e.target.value)}>
            {["cash", "upi", "card", "bank"].map((m) => <option key={m}>{m}</option>)}
          </select>
          <input className="input" type="number" min="0" placeholder="Amount paid" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </div>
        <p className="text-xs text-muted">Prices, making charges and GST are calculated by the server when you complete the sale.</p>
        <button className="btn w-full justify-center" disabled={!cart.length || busy} onClick={complete}>{busy ? "Processing…" : "Complete sale"}</button>
        {done && (
          <div className="text-sm border-t border-line pt-3 space-y-1">
            <div className="font-semibold">{done.number}</div>
            <div className="flex justify-between"><span>Metal</span><span>{money(done.metal_total)}</span></div>
            <div className="flex justify-between"><span>Making</span><span>{money(done.making_total)}</span></div>
            <div className="flex justify-between"><span>Stone</span><span>{money(done.stone_total)}</span></div>
            <div className="flex justify-between"><span>Discount</span><span>-{money(done.discount)}</span></div>
            <div className="flex justify-between"><span>GST ({done.gst_rate}%)</span><span>{money(done.gst_amount)}</span></div>
            <div className="flex justify-between font-bold"><span>Total</span><span>{money(done.grand_total)}</span></div>
            <div className="flex justify-between"><span>Paid</span><span>{money(done.paid)}</span></div>
            <button className="btn btn-ghost w-full justify-center" onClick={() => window.print()}>Print</button>
          </div>
        )}
      </div>
    </div>
  );
}
