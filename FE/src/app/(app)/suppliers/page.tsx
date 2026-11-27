"use client";
import { CrudPage } from "@/components/crud";

type Supplier = { id: string; name: string; phone: string; email: string; gstin: string };

export default function Suppliers() {
  return (
    <CrudPage<Supplier>
      title="Suppliers" endpoint="/suppliers" module="suppliers"
      columns={[
        { label: "Name", render: (r) => r.name },
        { label: "Phone", render: (r) => r.phone },
        { label: "Email", render: (r) => r.email },
        { label: "GSTIN", render: (r) => r.gstin },
      ]}
      fields={[
        { name: "name", label: "Name", required: true },
        { name: "phone", label: "Phone" },
        { name: "email", label: "Email" },
        { name: "gstin", label: "GSTIN" },
        { name: "address", label: "Address", type: "textarea" },
      ]}
    />
  );
}
