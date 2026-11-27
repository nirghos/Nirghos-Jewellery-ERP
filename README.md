# Nirghos Jewellery ERP

- `BE/` — Django REST Framework API (`/api/v1/`, docs at `/api/docs/`)
- `FE/` — Next.js (App Router, TypeScript, Tailwind) frontend

## Run locally
Backend: `cd BE && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt && cp .env.example .env && python manage.py migrate && python manage.py seed_demo --password <pw> && python manage.py runserver`
Frontend: `cd FE && npm i && cp .env.example .env.local && npm run dev`

## Implemented modules (backend API + frontend pages)
Auth/roles/audit log, company & branches, users, products (piece-wise, net/fine weight), metal rates, customers, suppliers,
POS billing (server-calculated, row-locked, old-gold exchange, cancel with reversal), purchases (piece + raw metal, supplier ledger/payments),
karigar (job cards, metal issue/return, wastage, labour), manufacturing (designs/BOM/stage tracking), repairs & custom orders,
old gold (testing, valuation, melting), diamonds & gemstones (carats), hallmark/HUID, gold schemes, double-entry accounting
(auto-posting, trial balance, P&L, balance sheet, ledgers, daybook), GST working reports, HR/payroll, 15 reports with CSV export, dashboard.

## Not implemented
E-invoice / e-way bill (need government API access), WhatsApp/email sending, AI assistant, bank reconciliation, barcode label printing,
multi-language UI, product image upload UI, PDF invoices (use browser print), 2FA. GST rate/HSN are settings - confirm with a CA.

## Tests
`cd BE && python manage.py test apps` (23 tests: calculations, double-entry balance, role boundaries, tenant isolation, all module flows).
