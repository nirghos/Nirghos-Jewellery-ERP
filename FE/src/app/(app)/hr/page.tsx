"use client";
import { useState } from "react";
import { api, money } from "@/lib/api";
import { CrudPage } from "@/components/crud";
import { can, useMe } from "@/components/shell";
import { ActionModal, Tabs } from "@/components/ui";

type E = { id: string; code: string; name: string; designation: string; department: string; base_salary: string; is_active: boolean };
type S = { id: string; employee_name: string; month: string; paid_days: string; days_in_month: number; gross: string; advance_deduction: string; net: string; status: string };
const emp = { endpoint: "/hr/employees/?is_active=true", label: (e: { code: string; name: string }) => `${e.code} · ${e.name}` };
const thisMonth = new Date().toISOString().slice(0, 7);

export default function HR() {
  const me = useMe();
  const [gen, setGen] = useState(false);
  const [n, setN] = useState(0);
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3"><h1 className="text-xl font-bold flex-1">HR & payroll</h1>
        {can(me, "hr", "create") && <button className="btn" onClick={() => setGen(true)}>Generate payroll</button>}</div>
      <Tabs tabs={[
        { label: "Employees", content: (
          <CrudPage<E> bare title="Employee" endpoint="/hr/employees" module="hr"
            fields={[{ name: "code", label: "Employee code", required: true }, { name: "name", label: "Name", required: true }, { name: "phone", label: "Phone" }, { name: "designation", label: "Designation" }, { name: "department", label: "Department" },
              { name: "joining_date", label: "Joining date", type: "date" }, { name: "base_salary", label: "Monthly salary (₹)", type: "number", step: "0.01", default: "0" }, { name: "is_active", label: "Active", type: "checkbox", default: true }]}
            columns={[{ label: "Code", render: (r) => r.code }, { label: "Name", render: (r) => r.name }, { label: "Designation", render: (r) => r.designation }, { label: "Department", render: (r) => r.department }, { label: "Salary", render: (r) => money(r.base_salary) }, { label: "Active", render: (r) => (r.is_active ? "Yes" : "No") }]} />) },
        { label: "Attendance", content: (
          <CrudPage<{ id: string; employee_name: string; date: string; status: string }> bare title="Attendance" endpoint="/hr/attendance" module="hr" canEdit={false} search={false} addLabel="Mark attendance"
            fields={[{ name: "employee", label: "Employee", type: "select", required: true, from: emp }, { name: "date", label: "Date", type: "date", required: true },
              { name: "status", label: "Status", type: "select", required: true, default: "present", options: [{ value: "present", label: "Present" }, { value: "half", label: "Half day" }, { value: "leave", label: "Paid leave" }, { value: "absent", label: "Absent" }] }]}
            columns={[{ label: "Date", render: (r) => r.date }, { label: "Employee", render: (r) => r.employee_name }, { label: "Status", render: (r) => r.status }]} />) },
        { label: "Leave", content: (
          <CrudPage<{ id: string; employee_name: string; from_date: string; to_date: string; kind: string; reason: string; status: string }> bare title="Leave" endpoint="/hr/leaves" module="hr" canEdit={false} search={false} addLabel="Apply leave"
            filters={[{ name: "status", label: "All", options: ["pending", "approved", "rejected"].map((s) => ({ value: s, label: s })) }]}
            fields={[{ name: "employee", label: "Employee", type: "select", required: true, from: emp }, { name: "from_date", label: "From", type: "date", required: true }, { name: "to_date", label: "To", type: "date", required: true }, { name: "kind", label: "Type", default: "casual" }, { name: "reason", label: "Reason" }]}
            columns={[{ label: "Employee", render: (r) => r.employee_name }, { label: "From", render: (r) => r.from_date }, { label: "To", render: (r) => r.to_date }, { label: "Type", render: (r) => r.kind }, { label: "Reason", render: (r) => r.reason }, { label: "Status", render: (r) => r.status }]}
            rowActions={[{ label: "Decide", perm: "approve", when: (r) => r.status === "pending", endpoint: (r) => `/hr/leaves/${r.id}/decide/`, fields: [{ name: "status", label: "Decision", type: "select", required: true, options: [{ value: "approved", label: "Approve" }, { value: "rejected", label: "Reject" }] }] }]} />) },
        { label: "Advances", content: (
          <CrudPage<{ id: string; employee_name: string; date: string; amount: string; recovered: string; outstanding: string }> bare title="Advance" endpoint="/hr/advances" module="hr" canEdit={false} search={false} addLabel="Give advance"
            fields={[{ name: "employee", label: "Employee", type: "select", required: true, from: emp }, { name: "date", label: "Date", type: "date", required: true }, { name: "amount", label: "Amount (₹)", type: "number", step: "0.01", required: true }]}
            columns={[{ label: "Date", render: (r) => r.date }, { label: "Employee", render: (r) => r.employee_name }, { label: "Amount", render: (r) => money(r.amount) }, { label: "Recovered", render: (r) => money(r.recovered) }, { label: "Outstanding", render: (r) => money(r.outstanding) }]} />) },
        { label: "Payslips", content: (
          <CrudPage<S> key={n} bare title="Payslip" endpoint="/hr/payslips" module="hr" canAdd={false} canEdit={false} fields={[]}
            filters={[{ name: "status", label: "All", options: [{ value: "generated", label: "generated" }, { value: "paid", label: "paid" }] }]}
            columns={[{ label: "Month", render: (r) => r.month }, { label: "Employee", render: (r) => r.employee_name }, { label: "Paid days", render: (r) => `${r.paid_days}/${r.days_in_month}` }, { label: "Gross", render: (r) => money(r.gross) },
              { label: "Advance ded.", render: (r) => money(r.advance_deduction) }, { label: "Net", render: (r) => <b>{money(r.net)}</b> }, { label: "Status", render: (r) => r.status }]}
            rowActions={[{ label: "Pay", perm: "approve", when: (r) => r.status === "generated", endpoint: (r) => `/hr/payslips/${r.id}/pay/`, fields: [{ name: "method", label: "Method", type: "select", required: true, default: "bank", options: ["cash", "bank", "upi"].map((m) => ({ value: m, label: m })) }] }]} />) },
      ]} />
      {gen && <ActionModal title="Generate payroll" endpoint="/hr/payslips/generate/" intro="Salary = monthly salary x paid days / days in month. Existing payslips are not changed. Outstanding advances are deducted."
        fields={[{ name: "month", label: "Month (YYYY-MM)", required: true, default: thisMonth }]} onClose={() => setGen(false)} onDone={(r) => { setGen(false); setN(n + 1); alert(`${(r as { generated: number }).generated} payslip(s) generated`); }} />}
    </div>
  );
}
