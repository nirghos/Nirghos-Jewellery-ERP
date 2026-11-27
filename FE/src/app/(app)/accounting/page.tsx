"use client";
import { useState } from "react";
import { money } from "@/lib/api";
import { CrudPage } from "@/components/crud";
import { can, useMe } from "@/components/shell";
import { ActionModal, DataTable, DateRange, Err, Stat, Tabs, downloadCsv, qs, useFetch } from "@/components/ui";

type E = { id: string; number: string; date: string; kind: string; narration: string; reversed: boolean; reverses: string | null; lines: { account_name: string; debit: string; credit: string }[] };
type Row = Record<string, string>;

function useRange() {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  return { from, to, setFrom, setTo, q: qs({ from, to }) };
}

function Trial() {
  const r = useRange();
  const { data, error } = useFetch<{ rows: Row[]; total_debit: string; total_credit: string }>(`/accounting/trial-balance/${r.q}`);
  return <div className="space-y-3"><DateRange {...r} /><Err>{error}</Err>
    {data && <><DataTable columns={["Code", "Account", "Type", "Debit", "Credit"]} money={[3, 4]} rows={data.rows.map((x) => [x.code, x.name, x.type, x.debit, x.credit])} />
      <div className="font-bold">Total: {money(data.total_debit)} / {money(data.total_credit)} {data.total_debit === data.total_credit ? "✓ balanced" : "✗ NOT BALANCED"}</div></>}</div>;
}

function PL() {
  const r = useRange();
  const { data, error } = useFetch<{ income: Row[]; expenses: Row[]; total_income: string; total_expense: string; net_profit: string }>(`/accounting/profit-loss/${r.q}`);
  return <div className="space-y-3"><DateRange {...r} /><Err>{error}</Err>
    {data && <><div className="grid sm:grid-cols-3 gap-3"><Stat label="Income" value={money(data.total_income)} /><Stat label="Expenses" value={money(data.total_expense)} /><Stat label="Net profit" value={money(data.net_profit)} /></div>
      <DataTable columns={["Income", "Amount"]} money={[1]} rows={data.income.map((x) => [x.name, x.amount])} />
      <DataTable columns={["Expense", "Amount"]} money={[1]} rows={data.expenses.map((x) => [x.name, x.amount])} /></>}
    <p className="text-xs text-muted">Sales are shown at invoice value; cost of goods sold is not auto-posted yet, so profit here is revenue less booked expenses.</p></div>;
}

function BS() {
  const { data, error } = useFetch<{ asset: Row[]; liability: Row[]; equity: Row[]; total_assets: string; total_liabilities_equity: string; balanced: boolean }>("/accounting/balance-sheet/");
  return <div className="space-y-3"><Err>{error}</Err>{data && <>
    <DataTable columns={["Assets", "Amount"]} money={[1]} rows={data.asset.map((x) => [x.name, x.amount])} />
    <DataTable columns={["Liabilities & equity", "Amount"]} money={[1]} rows={[...data.liability, ...data.equity].map((x) => [x.name, x.amount])} />
    <div className="font-bold">Assets {money(data.total_assets)} · Liabilities + equity {money(data.total_liabilities_equity)} {data.balanced ? "✓" : "✗"}</div></>}</div>;
}

function Ledger() {
  const r = useRange();
  const [code, setCode] = useState("1000");
  const { data: accts } = useFetch<Row[]>("/accounting/accounts/");
  const { data, error } = useFetch<{ account: string; rows: Row[]; closing: string }>(`/accounting/ledger/${qs({ code, from: r.from, to: r.to })}`, [code]);
  return <div className="space-y-3"><div className="flex flex-wrap gap-3"><select className="input w-64" value={code} onChange={(e) => setCode(e.target.value)}>{accts?.map((a) => <option key={a.code} value={a.code}>{a.code} · {a.name}</option>)}</select><DateRange {...r} /></div>
    <p className="text-xs text-muted">Cashbook = 1000, Bankbook = 1010.</p><Err>{error}</Err>
    {data && <><DataTable columns={["Date", "Voucher", "Narration", "Debit", "Credit", "Balance"]} money={[3, 4, 5]} rows={data.rows.map((x) => [x.date, x.number, x.narration, x.debit, x.credit, x.balance])} /><div className="font-bold">Closing: {money(data.closing)}</div></>}</div>;
}

function Parties({ kind }: { kind: "receivable" | "payable" }) {
  const { data, error } = useFetch<{ rows: Row[]; total: string }>(`/accounting/parties/?kind=${kind}`);
  return <div className="space-y-3"><Err>{error}</Err>{data && <><DataTable columns={[kind === "receivable" ? "Customer" : "Supplier", "Outstanding"]} money={[1]} rows={data.rows.map((x) => [x.name, x.outstanding])} /><div className="font-bold">Total: {money(data.total)}</div></>}</div>;
}

function Daybook() {
  const [d, setD] = useState("");
  const { data, error } = useFetch<{ date: string; entries: E[] }>(`/accounting/daybook/${qs({ date: d })}`);
  return <div className="space-y-3"><input type="date" className="input w-44" value={d} onChange={(e) => setD(e.target.value)} /><Err>{error}</Err>
    {data && <DataTable columns={["Voucher", "Type", "Narration", "Debit", "Credit"]} money={[3, 4]} rows={data.entries.map((e) => [e.number, e.kind, e.narration, e.lines.reduce((a, l) => a + Number(l.debit), 0).toFixed(2), e.lines.reduce((a, l) => a + Number(l.credit), 0).toFixed(2)])} />}</div>;
}

export default function Accounting() {
  const me = useMe();
  const [v, setV] = useState(false);
  const [n, setN] = useState(0);
  const acct = { endpoint: "/accounting/accounts/", label: (a: { code: string; name: string }) => `${a.code} · ${a.name}` };
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3"><h1 className="text-xl font-bold flex-1">Accounting & finance</h1>
        {can(me, "accounting", "create") && <button className="btn" onClick={() => setV(true)}>New voucher</button>}
        <button className="btn btn-ghost" onClick={() => downloadCsv("/reports/customer-outstanding/?export=csv", "outstanding.csv").catch((e) => alert(e.message))}>Export dues CSV</button></div>
      <Tabs tabs={[
        { label: "Vouchers", content: (
          <CrudPage<E> key={n} bare title="Voucher" endpoint="/accounting/entries" module="accounting" canAdd={false} canEdit={false} fields={[]}
            filters={[{ name: "kind", label: "All types", options: ["sale", "purchase", "receipt", "payment", "expense", "income", "contra", "journal", "repair", "reversal"].map((k) => ({ value: k, label: k })) }]}
            columns={[{ label: "No.", render: (r) => r.number }, { label: "Date", render: (r) => r.date }, { label: "Type", render: (r) => r.kind }, { label: "Narration", render: (r) => r.narration },
              { label: "Amount", render: (r) => money(r.lines.reduce((a, l) => a + Number(l.debit), 0)) }, { label: "Status", render: (r) => (r.reverses ? "reversal" : r.reversed ? "reversed" : "posted") }]}
            rowActions={[{ label: "Reverse", perm: "approve", danger: true, when: (r) => !r.reversed && !r.reverses, endpoint: (r) => `/accounting/entries/${r.id}/reverse/`, fields: [{ name: "reason", label: "Reason" }], intro: "Posted entries are never edited or deleted; a reversing entry is created." }]} />) },
        { label: "Daybook", content: <Daybook /> }, { label: "Ledger / Cashbook", content: <Ledger /> },
        { label: "Trial balance", content: <Trial /> }, { label: "Profit & loss", content: <PL /> }, { label: "Balance sheet", content: <BS /> },
        { label: "Receivables", content: <Parties kind="receivable" /> }, { label: "Payables", content: <Parties kind="payable" /> },
        { label: "Chart of accounts", content: (
          <CrudPage<{ id: string; code: string; name: string; type: string; is_system: boolean }> bare title="Account" endpoint="/accounting/accounts" module="accounting" canEdit={false}
            fields={[{ name: "code", label: "Code", required: true }, { name: "name", label: "Name", required: true }, { name: "type", label: "Type", type: "select", required: true, options: ["asset", "liability", "equity", "income", "expense"].map((t) => ({ value: t, label: t })) }]}
            columns={[{ label: "Code", render: (r) => r.code }, { label: "Name", render: (r) => r.name }, { label: "Type", render: (r) => r.type }, { label: "System", render: (r) => (r.is_system ? "Yes" : "") }]} />) },
      ]} />
      {v && <ActionModal title="New voucher" endpoint="/accounting/entries/" intro="Receipt/income: money in. Payment/expense: money out. Contra: move money between cash and bank (choose the destination account, e.g. Bank, and 'via' = source)."
        fields={[{ name: "type", label: "Type", type: "select", required: true, default: "expense", options: ["receipt", "payment", "expense", "income", "contra"].map((t) => ({ value: t, label: t })) },
          { name: "date", label: "Date", type: "date" }, { name: "amount", label: "Amount (₹)", type: "number", step: "0.01", required: true },
          { name: "account", label: "Account", type: "select", required: true, from: acct }, { name: "via", label: "Via", type: "select", required: true, default: "cash", options: [{ value: "cash", label: "Cash" }, { value: "bank", label: "Bank" }] },
          { name: "narration", label: "Narration", type: "textarea" }]} onClose={() => setV(false)} onDone={() => { setV(false); setN(n + 1); }} />}
    </div>
  );
}
