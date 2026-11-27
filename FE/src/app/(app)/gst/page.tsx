"use client";
import { useState } from "react";
import { money } from "@/lib/api";
import { DataTable, DateRange, Err, Stat, Tabs, qs, useFetch } from "@/components/ui";

type Row = Record<string, string>;

function Section({ path, children }: { path: string; children: (d: any) => React.ReactNode }) { // eslint-disable-line @typescript-eslint/no-explicit-any
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const { data, error } = useFetch<any>(`${path}${qs({ from, to })}`); // eslint-disable-line @typescript-eslint/no-explicit-any
  return <div className="space-y-3"><DateRange from={from} to={to} setFrom={setFrom} setTo={setTo} /><Err>{error}</Err>{data && children(data)}</div>;
}

export default function Gst() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">GST & compliance</h1>
      <p className="text-sm text-muted">Working reports to help your CA. Nothing here files returns. GST rate and HSN are company settings. E-invoice and e-way bill need government portal access and are not integrated.</p>
      <Tabs tabs={[
        { label: "GSTR-3B working", content: <Section path="/gst/gstr3b/">{(d) => <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3">
          <Stat label="Outward taxable" value={money(d.outward_taxable)} /><Stat label="Output tax" value={money(d.output_tax)} /><Stat label="Input tax credit" value={money(d.input_tax_credit)} /><Stat label="Net payable" value={money(d.net_tax_payable)} sub={d.note} /></div>}</Section> },
        { label: "Sales register", content: <Section path="/gst/sales-register/">{(d) => <><DataTable columns={["Invoice", "Date", "Customer", "GSTIN", "Taxable", "Rate %", "CGST", "SGST", "IGST", "Total"]} money={[4, 6, 7, 8, 9]}
          rows={d.rows.map((r: Row) => [r.number, r.date, r.customer, r.gstin, r.taxable, r.gst_rate, r.cgst, r.sgst, r.igst, r.total])} /><p className="text-xs text-muted">{d.note}</p></>}</Section> },
        { label: "Purchase register", content: <Section path="/gst/purchase-register/">{(d) => <DataTable columns={["Bill", "Date", "Supplier", "GSTIN", "Supplier bill", "Taxable", "GST", "Total"]} money={[5, 6, 7]}
          rows={d.rows.map((r: Row) => [r.number, r.date, r.supplier, r.gstin, r.supplier_invoice, r.taxable, r.gst, r.total])} />}</Section> },
        { label: "HSN summary", content: <Section path="/gst/hsn-summary/">{(d) => <DataTable columns={["HSN", "Description", "Invoices", "Net weight g", "Taxable", "GST", "Total"]} money={[4, 5, 6]}
          rows={d.rows.map((r: Row) => [r.hsn, r.description, r.invoices, r.net_weight_g, r.taxable, r.gst, r.total])} />}</Section> },
        { label: "GSTR-1 summary", content: <Section path="/gst/gstr1/">{(d) => <><DataTable columns={["GSTIN", "Invoice", "Date", "Taxable", "GST", "Total"]} money={[3, 4, 5]} rows={d.b2b.map((r: Row) => [r.gstin, r.invoice, r.date, r.taxable, r.gst, r.total])} />
          <div className="grid sm:grid-cols-3 gap-3"><Stat label="B2C invoices" value={d.b2c.invoices} /><Stat label="B2C taxable" value={money(d.b2c.taxable)} /><Stat label="B2C GST" value={money(d.b2c.gst)} /></div>
          <DataTable columns={["Cancelled invoice", "Date", "Taxable", "GST"]} money={[2, 3]} rows={d.cancelled_invoices.map((r: Row) => [r.invoice, r.date, r.taxable, r.gst])} /></>}</Section> },
        { label: "Reconciliation", content: <Section path="/gst/reconciliation/">{(d) => <div className="grid sm:grid-cols-3 gap-3"><Stat label="GST on invoices" value={money(d.invoice_gst)} /><Stat label="Output GST in ledger" value={money(d.ledger_output_gst)} /><Stat label="Difference" value={money(d.difference)} sub="Should be 0.00" /></div>}</Section> },
      ]} />
    </div>
  );
}
