# Nirghos Jewellery ERP

- `BE/` — Django REST Framework API (`/api/v1/`, docs at `/api/docs/`)
- `FE/` — Next.js (App Router, TypeScript, Tailwind) frontend

## Run locally
Backend: `cd BE && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt && cp .env.example .env && python manage.py migrate && python manage.py seed_demo --password <pw> && python manage.py runserver`
Frontend: `cd FE && npm i && cp .env.example .env.local && npm run dev`

## Implemented (Phase 1 + core slice)
JWT auth, role-based permissions (server-enforced), company/branches, products (piece-wise, net/fine weight),
metal rates, customers, suppliers, POS billing engine (backend-calculated, row-locked, cancel with stock reversal),
dashboard, stock movement ledger. Remaining modules from the blueprint are planned, not yet built.

GST rate is a company setting — confirm with a CA before production use.
