"use client";
import { CrudPage } from "@/components/crud";

type Customer = { id: string; name: string; phone: string; email: string; gstin: string; is_vip: boolean; loyalty_points: number };

export default function Customers() {
  return (
    <CrudPage<Customer>
      title="Customers" endpoint="/customers" module="customers"
      columns={[
        { label: "Name", render: (r) => <>{r.name} {r.is_vip && <span className="text-gold">★ VIP</span>}</> },
        { label: "Phone", render: (r) => r.phone },
        { label: "Email", render: (r) => r.email },
        { label: "GSTIN", render: (r) => r.gstin },
        { label: "Loyalty", render: (r) => r.loyalty_points },
      ]}
      fields={[
        { name: "name", label: "Name", required: true },
        { name: "phone", label: "Phone" },
        { name: "email", label: "Email" },
        { name: "gstin", label: "GSTIN" },
        { name: "birthday", label: "Birthday", type: "date" },
        { name: "anniversary", label: "Anniversary", type: "date" },
        { name: "address", label: "Address", type: "textarea" },
        { name: "is_vip", label: "VIP customer", type: "checkbox" },
      ]}
    />
  );
}
