"use client";
import { useState } from "react";
import { Eye, EyeOff, Lock, User } from "lucide-react";
import { API_URL, tokens } from "@/lib/api";
import { HeroArt, JewelleryArt, Logo } from "@/components/art";

export default function Login() {
  const [username, setU] = useState("");
  const [password, setP] = useState("");
  const [show, setShow] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const res = await fetch(`${API_URL}/auth/login/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }) });
      const d = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(d.detail || "Login failed");
      tokens.set(d.access, d.refresh);
      location.href = "/dashboard";
    } catch (e) { setErr(e instanceof Error ? e.message : "Login failed"); } finally { setBusy(false); }
  }

  return (
    <main className="min-h-screen grid lg:grid-cols-2 bg-bg">
      <section className="relative hidden lg:flex flex-col justify-between overflow-hidden bg-navy text-white p-12">
        <div className="absolute inset-0 grid place-items-center"><HeroArt bare className="w-[170%] max-w-none h-auto opacity-95" /></div>
        <div className="absolute inset-0 bg-gradient-to-t from-navy via-transparent to-navy/60" />
        <div className="relative flex items-center gap-3"><Logo size={44} /><div><div className="font-serif text-3xl gold-text">NIRGHOS</div><div className="text-[11px] tracking-[0.3em] text-white/60">JEWELLERY ERP</div></div></div>
        <div className="relative max-w-md">
          <h2 className="font-serif text-4xl leading-tight gold-text">Manage. Grow. Shine.</h2>
          <p className="mt-4 text-white/70">Stock, billing, karigar, hallmark, schemes and accounts — one premium system for your showroom.</p>
          <div className="mt-8 flex gap-3">{(["ring", "necklace", "earrings", "bangle"] as const).map((k) => <div key={k} className="w-16 h-16 rounded-xl bg-white/5 border border-white/10 grid place-items-center"><JewelleryArt kind={k} className="w-11 h-11" /></div>)}</div>
        </div>
      </section>
      <section className="grid place-items-center p-6">
        <form onSubmit={submit} className="card w-full max-w-md p-8 space-y-5">
          <div className="lg:hidden flex items-center gap-2"><Logo size={32} /><span className="font-serif text-2xl text-navy dark:text-gold">NIRGHOS</span></div>
          <div><h1 className="text-2xl font-semibold">Welcome back</h1><p className="text-sm text-muted mt-1">Sign in to your account</p></div>
          <label className="block text-sm space-y-1"><span className="text-muted">Username</span>
            <div className="relative"><User size={16} className="absolute left-3 top-3 text-muted" /><input className="input !pl-9" placeholder="Username" autoComplete="username" value={username} onChange={(e) => setU(e.target.value)} required autoFocus /></div></label>
          <label className="block text-sm space-y-1"><span className="text-muted">Password</span>
            <div className="relative"><Lock size={16} className="absolute left-3 top-3 text-muted" />
              <input className="input !pl-9 !pr-10" type={show ? "text" : "password"} placeholder="Password" autoComplete="current-password" value={password} onChange={(e) => setP(e.target.value)} required />
              <button type="button" className="absolute right-3 top-2.5 text-muted" onClick={() => setShow(!show)} aria-label="Show password">{show ? <EyeOff size={16} /> : <Eye size={16} />}</button></div></label>
          {err && <p className="text-sm text-danger">{err}</p>}
          <button className="btn btn-gold w-full !py-2.5" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
          <p className="text-xs text-muted text-center">© {new Date().getFullYear()} Nirghos Jewellers · All rights reserved</p>
        </form>
      </section>
    </main>
  );
}
