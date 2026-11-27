"use client";
import { CrudPage } from "@/components/crud";
import { useMe } from "@/components/shell";

type Product = {
  id: string; name: string; sku: string; barcode: string; metal: string; purity: string; gross_weight: string;
  stone_weight: string; net_weight: string; fine_weight: string; huid: string; status: string; purchase_cost?: string;
};

const METALS = ["gold", "silver", "platinum", "diamond", "gemstone"].map((m) => ({ value: m, label: m[0].toUpperCase() + m.slice(1) }));

export default function Products() {
  const me = useMe();
  return (
    <CrudPage<Product>
      title="Products" endpoint="/products" module="products"
      filters={[
        { name: "metal", label: "All metals", options: METALS },
        { name: "status", label: "All status", options: ["available", "sold", "reserved", "damaged"].map((s) => ({ value: s, label: s })) },
      ]}
      columns={[
        { label: "SKU", render: (r) => r.sku },
        { label: "Name", render: (r) => r.name },
        { label: "Metal", render: (r) => `${r.metal} ${r.purity}` },
        { label: "Gross g", render: (r) => r.gross_weight },
        { label: "Net g", render: (r) => r.net_weight },
        { label: "Fine g", render: (r) => r.fine_weight },
        { label: "Barcode", render: (r) => r.barcode },
        { label: "HUID", render: (r) => r.huid },
        ...(me.can_see_cost ? [{ label: "Cost", render: (r: Product) => r.purchase_cost }] : []),
        { label: "Status", render: (r) => r.status },
      ]}
      fields={[
        { name: "name", label: "Product name", required: true },
        { name: "sku", label: "SKU", required: true },
        { name: "barcode", label: "Barcode", required: true },
        { name: "metal", label: "Metal", type: "select", options: METALS, required: true, default: "gold" },
        { name: "purity", label: "Purity (fineness, 22K = 0.916)", type: "number", step: "0.001", default: "0.916" },
        { name: "gross_weight", label: "Gross weight (g)", type: "number", step: "0.001", required: true },
        { name: "stone_weight", label: "Stone weight (g)", type: "number", step: "0.001", default: "0" },
        { name: "making_type", label: "Making charge type", type: "select", required: true, default: "per_gram",
          options: [{ value: "per_gram", label: "Per gram" }, { value: "percent", label: "Percent" }, { value: "fixed", label: "Fixed" }] },
        { name: "making_value", label: "Making charge value", type: "number", step: "0.01", default: "0" },
        { name: "wastage_percent", label: "Wastage %", type: "number", step: "0.01", default: "0" },
        { name: "stone_price", label: "Stone price", type: "number", step: "0.01", default: "0" },
        { name: "huid", label: "HUID (6 chars)" },
        { name: "rack", label: "Rack" },
        ...(me.can_see_cost ? [{ name: "purchase_cost", label: "Purchase cost", type: "number" as const, step: "0.01", default: "0" }] : []),
      ]}
    />
  );
}
