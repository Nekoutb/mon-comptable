# AP agent layer — gap report and prerequisite tickets

## Blockers before any L0 agent

1. **Choose the authoritative runtime.** The live Sites Worker and dormant FastAPI AP domain are disconnected. Adopt one AP store and API boundary; do not duplicate invoices or agent state across D1 and PostgreSQL.
2. **Add the Agent Contract schema.** Persist `AgentDefinition`, `AgentRun`, tool calls, prompt/model versions, input hash, structured output, field confidence, guards, latency/cost and later human verdict.
3. **Add sourced extraction fields.** Replace aggregate `ocr_output` with typed fields carrying page, bounding box/text span, language, confidence and source document version.
4. **Add document-pack structure.** Persist document type, pages, split boundaries, parent pack, classification result and quarantine status.
5. **Build a real secure document pipeline.** Object storage, malware scanning, size/type validation, PDF/image normalisation, hashing and retention controls are required before production invoices enter an agent.
6. **Build the golden corpus and evaluation harness.** No anonymised labelled production documents are present. L0 cannot begin until the corpus, labels, metrics and CI regression gate exist.
7. **Build tenant-safe tool endpoints.** Agents need minimal read tools for invoice pages, supplier candidates, tenant chart, PO/GRN, tax-rule verdicts and historical coding. Tenant/entity context must come from authenticated execution context, not prompt text.
8. **Implement deterministic services.** Amount arithmetic, tax computation, duplicate detection, PO/GRN tolerances, currency rules and referential validation must be services, not prompts.
9. **Build the prompt registry.** Prompts must be versioned artefacts promoted through evaluation environments; remove prompt-version labels that do not resolve to an immutable artefact.
10. **Build human review and feedback.** One review queue with accept/edit/reject, field deltas, reason codes, SLA, reminders and timeout handling.

## State-machine gaps

- No explicit transitions from `duplicate`, `supplier_not_found` or `failed` after resolution/retry.
- No persisted PO, GRN, contract, invoice-line or matching-result models.
- No document classification state or multi-document split state.
- No observation/reconciliation that changes `erp_draft` to `posted` based on Odoo.
- No cancellation, credit-note linkage, dispute, payment hold or write-off prohibition state.
- No transition policy object specifying allowed actor, guard set and idempotency semantics.

## Safety and governance gaps

- No capability-scoped credentials or tool permission classes (read, propose, draft, forbidden).
- No enforcement model for T0/T1/T2/T3 tiers.
- No structured refusal schema or guard-failure persistence.
- No prompt-injection red-team corpus or tool-containment tests.
- Bank-detail divergence is not modelled as a security incident with freeze and out-of-band verification.
- Audit is application append-only but not immutable/WORM-backed.
- FastAPI defaults include development secrets and local storage; production configuration must fail closed.
- The live Worker associates an ERP connection with owner plus a literal default tenant, not a provisioned tenant/entity identifier.

## Observability and resilience gaps

- Background jobs do not execute domain work; they only change status.
- No stable idempotency key for agent runs, resumable checkpoints or dependency graph.
- No cost/token/latency budgets, traces, calibration dashboard or drift alerts.
- No prompt/model shadow version comparison.
- No per-field human verdict capture and no acceptance/edit/rejection trend.

## Proposed prerequisite ticket order

1. ADR: choose authoritative AP runtime and tenant boundary.
2. Migration: agent contracts, runs, sourced fields, document pack, verdicts and prompt registry.
3. Tool gateway: authenticated tenant/entity context plus capability permissions.
4. Deterministic AP rules package and guard service.
5. Secure document pipeline and hostile-content boundary.
6. HITL review bus and feedback capture.
7. Evaluation harness plus anonymisation workflow.
8. L0 Classifier specification and shadow implementation.
9. L0 Extractor specification and shadow implementation.

## Not silently implemented

No model provider was selected, no production document was copied, no tax rule was guessed, and no agent was granted write access. These require the decisions and evidence requested in the review gate.
