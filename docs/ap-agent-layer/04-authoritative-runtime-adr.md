# ADR-001 — authoritative AP runtime

Status: accepted provisionally on 2026-08-02 following instruction to proceed.

## Decision

The live Sites application remains the user interface and Odoo connection surface. The FastAPI/PostgreSQL service becomes the authoritative AP transaction, document, approval, audit and agent-runtime domain. The browser must never write AP business state directly to D1. D1 remains limited to Sites-owned connection/configuration concerns until a server-to-server integration boundary is implemented.

## Consequences

- Every agent tool call is implemented behind the authenticated FastAPI boundary and tenant/entity context is derived from the signed identity.
- Odoo credentials remain server-side; the AP backend receives capability-scoped Odoo operations, never raw credentials.
- The existing mock ERP/OCR adapters cannot be used in production or reported as live.
- A signed service-to-service contract between the Sites Worker and FastAPI is a prerequisite for live agent execution.
- Agent L0 output may be stored only in the authoritative AP database and remains invisible to users until evaluation permits L1.

## Rejected alternative

Duplicating invoice and agent state into the current D1 database was rejected because it creates conflicting sources of truth, weakens tenant isolation and breaks audit reconstruction.
