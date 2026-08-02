# AP agent layer — codebase capability map

Date: 2026-08-02  
Status: prerequisite audit; no agent is authorised to operate yet.

## Runtime reality

The repository contains two materially different application paths:

1. The deployed Sites application is `app/page.tsx` plus `worker/index.ts`, backed by Sites D1. It authenticates with the Sites identity header, stores one encrypted Odoo connection for the signed-in owner and reads live Odoo data. It has no invoice-document persistence, approvals, agent-run records or prompt/model runtime.
2. `backend/app/**` is a more complete FastAPI/PostgreSQL design with invoices, documents, suppliers, proposals, approvals, audit and background jobs. It is not wired to the deployed Sites application. Its ERP and OCR implementations are explicitly mock adapters.

This split is the primary architectural constraint. The agent layer must not write shadow state into D1 while the invoice workflow remains in an unconnected FastAPI service. A single authoritative runtime must be selected before L0 agents run.

## Current AP state machine

Canonical states are declared by `InvoiceStatus` in `backend/app/models.py`:

| State | Entry trigger | Exit/transition | Actor |
|---|---|---|---|
| `received` | Upload or inbound document intake | `ocr_pending` | Human/API |
| `ocr_pending` | Accepted document queued for extraction | `review` or `failed` | Background extraction worker |
| `review` | Extraction completed, supplier matched, or approver rejected | `supplier_not_found`, `duplicate`, `pending_approval` | Automation then accountant |
| `supplier_not_found` | Resolver has no candidate above threshold | `review` after human correction/match | Resolver/human |
| `duplicate` | Deterministic duplicate check finds an exact match | Human resolution required; transition not explicitly implemented | Deterministic service/human |
| `pending_approval` | Accountant submits a validated proposal | `approved` or `review` | Accountant then approver |
| `approved` | Four-eyes approval succeeds | `erp_draft` | Approver then ERP draft action |
| `erp_draft` | Idempotent draft request accepted | `posted` is modelled but direct posting is prohibited by the current API | ERP adapter/human in Odoo |
| `posted` | Expected external ERP observation | No implemented reconciliation transition | External ERP/manual posting |
| `failed` | Extraction/integration failure | Retry or human recovery is implied but not modelled as a state transition | Worker/human |

Guards already present include tenant-filtered queries, role checks, validated-proposal requirement, four-eyes approval, idempotency key for ERP drafts, and rejection back to review. Missing transitions are listed in the gap report.

## Human judgement and data-entry insertion points

| Insertion point | Current human action | Existing surface | Candidate capability |
|---|---|---|---|
| Invoice intake | Select/upload invoice pack and identify source | `app/ap-operations.tsx`; `POST /api/v1/invoices/upload` | Classifier, Extractor |
| Document classification/splitting | Determine invoice, credit note, statement, receipt or noise; split packs | Not implemented | Classifier |
| Field correction | Correct invoice number, dates, currency and amounts | `PATCH /api/v1/invoices/{id}` | Extractor suggestion + human verdict |
| Supplier resolution | Select supplier when deterministic score is insufficient | `/match-supplier`; `services.match_supplier` | Vendor Resolver |
| Duplicate resolution | Decide whether a flagged item is a true duplicate | `/check-duplicate`; `services.duplicate_check` | Validator/Exception Triage |
| PO/GRN matching | Find PO, delivery evidence and explain variances | UI copy exists; no persisted model/tool | Matcher |
| Accounting coding | Select journal, expense account, tax code and explanation | `/generate-proposal`; `AccountingProposal` | Coder, permanently T1 |
| Validation interpretation | Understand deterministic guard failures and choose correction | Proposal validation exists in service code; no unified review object | Validator |
| Submission | Decide that evidence and proposal are complete | `/submit` | Human remains accountable |
| Approval/rejection | Approve or return with a reason | `/approve`, `/reject` | Human only; agents may summarise |
| ERP draft creation | Trigger draft after approval | `/record-draft` | T1 preparation with human action |
| Email handling | Review inbound attachments, link documents, draft response | `/inbound-email/webhook`, `/exceptions` | Correspondent; never sends |
| Payment selection | Review eligible invoices and hand to Treasury | payment campaign library/UI | Payment Planner; preparation only |

## Existing data model

- Tenant and identity: `Tenant`, `LegalEntity`, `User`; tenant filtering is derived from authenticated identity in FastAPI.
- Supplier master: `Supplier`, including ERP ID, tax ID, blocked status and bank last four digits. Full bank data is not stored.
- Accounting master: `Account`, `TaxCode`, `Journal`, all tenant/entity scoped.
- Documents: `Document` stores immutable metadata, SHA-256, source and a storage key. Production object storage, malware scanning, page structure and extracted text spans are absent.
- Invoices: `Invoice` stores header fields, amounts, status, raw `ocr_output`, aggregate OCR confidence and duplicate level.
- Proposals and approvals: `AccountingProposal`, `ApprovalAction`, `ERPPosting`.
- Operations: `InboundEmail`, `Notification`, `BackgroundJob`.
- Audit: `AuditLog` stores before/after JSON, actor, origin and correlation ID; it is application append-only, not WORM-enforced.
- Deployed D1: only ERP connections and initial admin/provisioning tables; it does not contain the FastAPI AP domain.

## Current model and prompt inventory

No production model call exists. `MockOCRAdapter` returns hard-coded supplier and amount data and identifies itself as a mock. `generate_proposal` is deterministic/mock-labelled. Prompt versions such as `ap-v1` are stored on proposals, but there is no prompt registry and no prompt artefact to version, diff, evaluate or promote. Therefore the current model inventory is empty:

| Capability | Provider/model | Prompt | Production status |
|---|---|---|---|
| OCR/extraction | `MockOCRAdapter` | None | Mock only |
| Supplier resolution | Deterministic scoring | None | Backend-only |
| Duplicate check | Deterministic exact match | None | Backend-only |
| Coding proposal | Deterministic/mock | No registered prompt | Backend-only |

## Write paths and guards

- Invoice field writes require `accountant` or `tenant_admin`, tenant-filter the invoice, increment version and emit audit.
- Supplier match and duplicate checks tenant-filter candidates and emit automation audit.
- Submission requires an existing validated proposal.
- Approval requires `approver`/`tenant_admin` and blocks self-approval.
- ERP action accepts only `record-draft`, requires `poster`/`tenant_admin` and an idempotency key. Direct posting is rejected.
- Inbound email uses a shared webhook secret and resolves tenant from the recipient address.
- Deployed Odoo reads are authenticated server-side and credentials are encrypted; however the deployed worker has no AP write endpoint.

## Provisional conclusion

The safest first build target is not an LLM agent. It is the shared runtime and evidence model that joins the deployed Odoo connector to one authoritative AP domain. The first agent after that should be the Classifier or Extractor in L0 shadow, but only after a labelled corpus exists.
