"use client";
import { useState } from "react";
import { Gem } from "lucide-react";
import { API_URL, tokens } from "@/lib/api";

export default function Login() {
  const [username, setU] = useState("");
  const [password, setP] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const res = await fetch(`${API_URL}/auth/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const d = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(d.detail || "Login failed");
      tokens.set(d.access, d.refresh);
      location.href = "/dashboard";
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen grid place-items-center bg-navy p-4">
      <form onSubmit={submit} className="card w-full max-w-sm p-8 space-y-4">
        <div className="flex items-center gap-2 text-navy dark:text-gold">
          <Gem /> <span className="text-xl font-bold tracking-wide">NIRGHOS</span>
        </div>
        <p className="text-sm text-muted">Jewellery ERP — sign in to continue</p>
        <input className="input" placeholder="Username" value={username} onChange={(e) => setU(e.target.value)} required autoFocus />
        <input className="input" type="password" placeholder="Password" value={password} onChange={(e) => setP(e.target.value)} required />
        {err && <p className="text-sm text-red-600">{err}</p>}
        <button className="btn w-full justify-center" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </main>
  );
}
