"use client";
import { CrudPage } from "@/components/crud";
import { useMe } from "@/components/shell";
import { JewelleryImage } from "@/components/art";
import { Badge } from "@/components/ui";

type Product = {
  id: string; name: string; sku: string; barcode: string; metal: string; purity: string; gross_weight: string;
  stone_weight: string; net_weight: string; fine_weight: string; huid: string; status: string; purchase_cost?: string; category_name: string; rack: string; image: string | null;
};

const METALS = ["gold", "silver", "platinum", "diamond", "gemstone"].map((m) => ({ value: m, label: m[0].toUpperCase() + m.slice(1) }));

export default function Products() {
  const me = useMe();
  return (
    <CrudPage<Product>
      title="Inventory" subtitle="Every piece tracked by weight, purity, barcode and HUID" endpoint="/products" module="products" addLabel="Add product"
      card={(r, actions) => (
        <div className="card overflow-hidden group hover:shadow-md hover:border-gold/60 transition">
          <div className="relative"><JewelleryImage name={r.name} category={r.category_name} metal={r.metal} src={r.image} className="h-44 w-full" />
            <span className="absolute top-3 left-3"><Badge value={r.status} /></span>
            {r.huid && <span className="absolute top-3 right-3 text-[11px] font-semibold rounded-full bg-navy text-gold px-2 py-0.5">HUID {r.huid}</span>}</div>
          <div className="p-4 space-y-2">
            <div><div className="font-semibold truncate">{r.name}</div><div className="text-xs text-muted">{r.sku} · {r.category_name || "Uncategorised"}{r.rack ? ` · Rack ${r.rack}` : ""}</div></div>
            <div className="grid grid-cols-3 gap-2 text-center text-xs bg-soft rounded-lg py-2">
              <div><div className="text-muted">Gross</div><div className="font-semibold">{r.gross_weight} g</div></div>
              <div><div className="text-muted">Net</div><div className="font-semibold">{r.net_weight} g</div></div>
              <div><div className="text-muted">Fine</div><div className="font-semibold">{r.fine_weight} g</div></div>
            </div>
            <div className="flex items-center justify-between text-xs"><span className="capitalize text-muted">{r.metal} · {r.purity}</span><span className="space-x-3">{actions}</span></div>
          </div>
        </div>
      )}
      filters={[
        { name: "metal", label: "All metals", options: METALS },
        { name: "status", label: "All status", options: ["available", "sold", "reserved", "damaged"].map((s) => ({ value: s, label: s })) },
      ]}
      columns={[
        { label: "SKU", render: (r) => r.sku },
        { label: "Piece", render: (r) => <span className="flex items-center gap-2.5"><JewelleryImage name={r.name} category={r.category_name} metal={r.metal} src={r.image} className="w-9 h-9 rounded-lg" />{r.name}</span> },
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
