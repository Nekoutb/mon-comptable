# Mon Comptable

AI-powered bilingual (FR/EN) accounting assistant for **Accounts Payable** and
**Treasury**, built for multi-tenant use. The interface is a vinext (Next.js
compatible) app; the API is FastAPI + SQLAlchemy with PostgreSQL in production
and SQLite for local development.

> Assistant comptable IA bilingue (FR/EN) pour les comptes fournisseurs et la
> trésorerie. La documentation détaillée en français se trouve dans [`docs/`](docs/).

## Modules

- **Accounts Payable** — invoice intake (upload or inbound email webhook), OCR
  extraction (background job), supplier matching, duplicate detection
  (exact + probable), deterministic accounting proposal, four-eyes approval,
  ERP draft and posting with tenant-scoped idempotency keys.
- **Treasury** — bank statement upload (CSV, MT940, CAMT.053), parsing, line
  duplicate control, opening/closing balance validation, ERP import.
- **Foundation** — JWT auth with tenant-scoped roles (`accountant`, `approver`,
  `poster`, `tenant_admin`), tenant isolation on every query, document storage,
  append-only audit log with request correlation IDs, background job tracking.

All ERP/OCR/email integrations are **mock adapters** — responses say so
explicitly and no external service is ever contacted. See
[docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md).

## Quick start (Docker)

```bash
cp .env.example .env   # then replace the placeholder secrets
docker compose up --build
```

- Frontend: http://localhost:3000
- API + OpenAPI docs: http://localhost:8000/api/docs
- The api service runs `alembic upgrade head` before starting.

Seed the demo tenant (one-off):

```bash
docker compose exec api python -m app.seed
```

## Quick start (local, no Docker)

Backend (Python 3.13):

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate  # or source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --port 8000
```

Frontend (Node >= 22.13):

```bash
echo NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 > .env
npm install
npm run dev
```

Without `NEXT_PUBLIC_API_URL` (or with the API down) the UI runs in a clearly
labelled demo mode; once the API is reachable, sign in to load live data.

## Demo accounts

Seeded by `python -m app.seed`, tenant code `akwa`, password `DemoPass2026!`:

| Email | Role |
| --- | --- |
| nadia@akwa.example | accountant |
| approver@akwa.example | approver |
| poster@akwa.example | poster |
| admin@akwa.example | tenant_admin |

## Tests

```bash
cd backend && python -m pytest      # API, workflow, isolation and parser tests
npm test                            # builds the frontend and checks rendered output
npm run lint
```

## Background jobs

`MC_BACKGROUND_MODE=inline` (default) executes jobs synchronously — invoice OCR
completes before the upload response returns. `MC_BACKGROUND_MODE=rq` defers
jobs to the Redis/RQ worker (`python -m app.worker`, included in
docker-compose); uploads then return `ocr_pending` until the worker finishes.

## Repository layout

- `app/` — vinext frontend (UI, i18n dictionary, typed API client)
- `backend/app/` — FastAPI application (models, services, jobs, adapters, parsers)
- `backend/migrations/` — Alembic migrations
- `backend/tests/` — pytest suite
- `docs/` — architecture, security notes and known limitations (French)
- `worker/`, `build/`, `examples/` — vinext starter scaffolding kept for the
  hosting platform; `.openai/hosting.json` is optional deployment metadata and
  the build falls back to no bindings when it is absent

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — technical architecture (FR)
- [docs/SECURITY.md](docs/SECURITY.md) — security notes and deployment checklist (FR)
- [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) — current limitations (FR)
