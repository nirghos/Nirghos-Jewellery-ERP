"use client";
import { money } from "@/lib/api";
import { CrudPage } from "@/components/crud";
import { DataTable, Tabs, useFetch } from "@/components/ui";

type O = { id: string; number: string; customer_name: string; gross_weight: string; net_weight: string; touch: string; fine_weight: string; rate_per_gram: string; value: string; payout: string; status: string };

function Melting() {
  const { data } = useFetch<{ results: Record<string, string>[] }>("/old-gold/melting/");
  return <DataTable columns={["Batch", "Date", "Input gross g", "Input fine g", "Recovered gross g", "Purity", "Recovered fine g", "Loss fine g"]}
    rows={(data?.results ?? []).map((b) => [b.number, b.date, b.input_gross, b.input_fine, b.recovered_gross, b.recovered_purity, b.recovered_fine, b.loss_fine])} />;
}

export default function OldGold() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Old gold purchase & exchange</h1>
      <Tabs tabs={[
        { label: "Old gold register", content: (
          <CrudPage<O> bare title="Old gold receipt" endpoint="/old-gold" module="old_gold" canEdit={false} addLabel="New old gold"
            filters={[{ name: "status", label: "All status", options: ["received", "exchanged", "melted", "cancelled"].map((s) => ({ value: s, label: s })) }]}
            fields={[{ name: "customer", label: "Customer", type: "select", from: { endpoint: "/customers/", label: (r) => r.name } }, { name: "customer_name", label: "Or walk-in name" },
              { name: "gross_weight", label: "Gross weight (g)", type: "number", step: "0.001", required: true }, { name: "stone_weight", label: "Stone / dirt weight (g)", type: "number", step: "0.001", default: "0" },
              { name: "touch", label: "Tested purity (0.750 = 18K)", type: "number", step: "0.001", required: true },
              { name: "test_method", label: "Test method", type: "select", required: true, default: "touchstone", options: ["touchstone", "xrf", "fire_assay"].map((m) => ({ value: m, label: m })) },
              { name: "rate_per_gram", label: "24K rate / g (blank = today's gold rate)", type: "number", step: "0.01" }, { name: "deduction_percent", label: "Deduction %", type: "number", step: "0.01", default: "0" },
              { name: "payout", label: "Payout", type: "select", required: true, default: "exchange", options: [{ value: "exchange", label: "Exchange against new jewellery" }, { value: "cash", label: "Cash purchase" }] },
              { name: "kyc_id_type", label: "KYC ID type" }, { name: "kyc_id_number", label: "KYC ID number" }, { name: "notes", label: "Notes" }]}
            columns={[{ label: "No.", render: (r) => r.number }, { label: "Customer", render: (r) => r.customer_name }, { label: "Gross g", render: (r) => r.gross_weight }, { label: "Net g", render: (r) => r.net_weight },
              { label: "Touch", render: (r) => r.touch }, { label: "Fine g", render: (r) => r.fine_weight }, { label: "24K rate", render: (r) => money(r.rate_per_gram) }, { label: "Value", render: (r) => <b>{money(r.value)}</b> }, { label: "Payout", render: (r) => r.payout }, { label: "Status", render: (r) => r.status }]}
            rowActions={[
              { label: "Melt", perm: "approve", when: (r) => r.status === "received" || r.status === "exchanged", endpoint: () => "/old-gold/melt/", extra: (r) => ({ receipt_ids: [r.id] }),
                intro: "Melt this receipt into a bar. Loss = input fine - recovered fine.",
                fields: [{ name: "recovered_gross", label: "Recovered gross (g)", type: "number", step: "0.001", required: true }, { name: "recovered_purity", label: "Recovered purity (e.g. 0.995)", type: "number", step: "0.001", required: true }] },
              { label: "Cancel", perm: "approve", danger: true, when: (r) => r.status === "received", endpoint: (r) => `/old-gold/${r.id}/cancel/`, confirm: "Cancel this receipt and reverse stock/payment?" }]} />) },
        { label: "Melting batches", content: <Melting /> },
      ]} />
      <p className="text-xs text-muted">Value = net weight x touch x 24K rate x (1 - deduction %). To exchange against a new piece, select the receipt in POS Billing.</p>
    </div>
  );
}
