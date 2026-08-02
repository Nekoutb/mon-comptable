# My Accountant Admin Platform — implementation prompt

Build a production-grade, responsive **Admin** workspace inside My Accountant. It must use the existing bilingual design system and application shell, support English and French without mixed-language strings, and preserve strict tenant isolation.

## Security and access

- Use the platform’s authenticated identity and role-based access control. Only platform administrators may create tenants; tenant administrators may manage only their own tenant.
- For local development only, a bootstrap account may initially be named `admin` with password `admin`, but force a password change at first sign-in, never deploy that password publicly, never store it in source control, and rate-limit login attempts.
- Encrypt ERP API keys at rest, never return secrets to the browser, mask saved credentials, record all administrative changes in an immutable audit trail, and require re-authentication for security-sensitive changes.

## Information architecture

Create top-level sections for Dashboard, Companies, Users, Agent Provisioning, ERP Connections, Roles & Permissions, Audit Trail, and Platform Settings. Every list supports search, filtering, pagination, responsive tables/cards, loading states, validated empty states, and error recovery. Never insert demonstration companies, users, transactions, or metrics.

## Company onboarding wizard

Implement a resumable wizard with: legal identity; tenant code and domains; country, currency, time zone and languages; fiscal calendar; OHADA/SYSCOHADA accounting framework; tax profile; Odoo or other ERP connection; company/entity mapping; chart-of-accounts and journal synchronisation; user invitations; agent provisioning; review and activation. Save drafts server-side. Validate uniqueness and show a completion checklist.

## User administration

Allow authorised administrators to invite, suspend, reactivate, and assign users to tenants and legal entities. Provide platform administrator, tenant administrator, CFO, Financial Controller, Financial Planning Manager, accountant/analyst, reviewer, and read-only roles. Enforce least privilege and separation of duties. Invitation links expire and are single-use.

## Agent organisation and provisioning

Render the hierarchy clearly:

- CFO: finance strategy, capital allocation, financing, governance, executive reporting, and final accountability.
  - Financial Controller: close, reporting, accounting policy, internal controls, review, and supervision of Financial Reporting Agents.
    - AP Accountant: vendor invoices, three-way match, coding, AP ageing, payment proposals, and draft AP journals.
    - AR Accountant: billing, receipts, credit control, collections, AR ageing, and draft AR journals.
    - Treasury Accountant: cash, bank journals, reconciliation, liquidity forecasts, and payment campaigns.
    - Fixed Assets Accountant: asset register, capitalisation, depreciation, disposals, and reconciliation.
    - General Ledger Accountant: ledger integrity, close, account reconciliations, journals, and financial statements.
    - Tax Accountant: tax determination, VAT and withholding, filings, reconciliations, and exceptions.
  - Financial Planning Manager: budgets, forecasts, scenarios, performance management, and supervision of Financial Planning Agents.
    - Financial Planning Analyst: budgets, forecasts, variance analysis, models, and dashboards.
    - Pricing Analyst: pricing models, margins, elasticity, proposals, and approvals.
    - Value for Money Analyst: cost-benefit assessment, procurement value, benchmarks, and realised savings.

Administrators can provision any subset by tenant/entity, configure responsibility boundaries and approval limits, activate/deactivate agents, and view configuration status. Provisioning must be idempotent and auditable.

## ERP and synchronisation

Support multiple saved ERP connections per tenant, prioritising Odoo JSON-2 for Odoo 19+ and JSON-RPC/XML-RPC for older versions. Provide Test, Save, Refresh, and Sync entire application actions. Persist connections server-side, show last successful/failed sync, retain the prior valid configuration on failure, and refresh only verified ERP data. Provide per-domain sync status for accounts, journals, partners, taxes, invoices, payments, bank statements, fixed assets, and balances. Draft journal submission must be idempotent and require manual ERP posting.

## UX and quality

Use the supplied My Accountant interface exactly: established tokens, navigation, typography, glass surfaces, spacing, focus treatment, and responsive behaviour. Meet WCAG 2.2 AA, full keyboard navigation, 44px touch targets, semantic landmarks, clear destructive-action confirmations, reduced-motion support, and layouts for 320px mobile through wide desktop. Every action needs pending, success, validation, permission, network-error, and empty states. Add unit tests for permissions and agent provisioning, integration tests for tenant isolation and encrypted connectors, and end-to-end tests for onboarding, invitation, provisioning, and Odoo connection persistence.
