# Handoff: My Accountant — Liquid Glass accounting control room

## Overview
Multi-tenant AI-assisted accounting operations platform. Six agents (Financial Controller + AP, Treasury, Fixed Assets, General Ledger, Tax) prepare work under human supervision; nothing ever posts to the ERP without a human. The centerpiece workflow is the **supplier payment campaign**: AP selects eligible invoices on configurable campaign days → structured handoff to Treasury → Treasury review → Financial Controller approval → draft (unposted) batch in Odoo.

## About the Design Files
The files in this bundle are **design references created in HTML** — working prototypes showing intended look and behavior, NOT production code to copy directly. The task is to **recreate these designs in the target codebase** (e.g. React + TypeScript; if no codebase exists, a sensible default is Next.js or Vite + React, TanStack Table/Query, i18next) using its established patterns. All data in the prototype is an in-memory fixture; replace with real APIs.

- `My Accountant.dc.html` — source prototype (readable: an HTML template + a JS class named `Component` holding all state, data, i18n and the campaign engine).
- `My Accountant.html` — self-contained bundled version; open in any browser to click through the live behavior.

## Fidelity
**High-fidelity** for: visual language (glass surfaces, tokens below), Control Room, Financial Controller, Policies, AP selection, Treasury, Payment Campaigns (calendar/list/detail), ERP/Odoo wizard, display/accessibility drawer, navigation (desktop sidebar, <900px bottom nav + drawer). Recreate closely.
**Medium-fidelity** for: Agent overview, Fixed Assets, GL, Tax, Journal Centre, Approvals, Documents, Audit Trail, Reports, Notifications, Tenant Settings — these use a shared "tiles + table + note" layout in the prototype; keep the pattern, deepen content per the product brief.
**Not designed yet**: Sign-in, tenant onboarding, legal-entity onboarding.

## Design Tokens

### Color
- Ink text: `#0b1524` (primary), `#213247`, `#48586c` (secondary), `#5b6b80` (metadata — minimum grey allowed on white, ≈5.4:1)
- App background: `linear-gradient(180deg,#eef2f7,#e7ecf3)` + two soft radial tints: `rgba(45,212,191,.16)` at 12%/-8%, `rgba(123,108,217,.14)` at 92%/4%
- Navy foundation (nav surfaces): `rgba(11,21,36,α)`; nav text `rgba(214,228,242,.72–.80)`, white for active
- Teal accent (primary actions): gradient `#12a294 → #0c7c71`; light chip `rgba(15,155,142,.14)` / text `#0a6b62`
- Odoo/ERP violet: text `#5244a8`, bg `rgba(123,108,217,.15)`, border `rgba(123,108,217,.30)`
- Status: ok `#166b44` on `rgba(31,122,77,.13)`; warn `#8a5606` on `rgba(196,138,26,.16)`; risk `#a3241a` on `rgba(176,48,32,.12)`; info `#17538f` on `rgba(29,95,181,.12)`; neutral `#40506a` on `rgba(11,21,36,.06)`
- Every status chip pairs color with a symbol (✔ ▲ ■ ● ◆ –) — never color alone.
- Links: `#0d6f8f`, hover `#0a5570` underline. Focus ring: `2px solid #0d7d74`, offset 2px.

### Glass levels (CSS custom properties, set per density mode)
| Level | Use | Balanced default |
|---|---|---|
| `--nav` | sidebar/top bar/bottom nav | `rgba(11,21,36,.87)` + blur 18px sat 160% |
| `--work` | workspace panels | `rgba(255,255,255,.70)` + blur 18px |
| `--card` | KPI/agent cards | `rgba(255,255,255,.60)` + blur 18px |
| Opaque data surface | ALL financial tables | solid `#fff`, border `rgba(11,21,36,.10)` |

Density modes: **airy** (work .46 / card .38 / nav .74 / blur 26px), **balanced** (above), **solid** (.93/.90/.96/7px). **Reduced transparency** mode: all 1.0/blur 0. Always ship `background-color` fallback for no `backdrop-filter` support. Glass borders `1px rgba(255,255,255,.55–.60)` + inset top highlight `0 1px 0 rgba(255,255,255,.85)`; shadows `0 10–12px 28–34px rgba(11,21,36,.09–.10)`.

### Typography
- UI: `IBM Plex Sans` (400/500/600/700). Numbers/code/money: `IBM Plex Mono` with `font-variant-numeric: tabular-nums`, right-aligned in tables.
- Scale: page title 26/600/-.02em; section h2 15/600; body 13–13.5; table cells 13 (mono 12.5); metadata 11.5–12; overline labels 10–11 uppercase +.07–.10em tracking; KPI value 21–23 mono.
- Minimum text 10.5px (bottom-nav labels only); table/metadata never below 11.5px.

### Shape, spacing, motion
- Radius: 8–9 chips/small buttons, 10–11 inputs/buttons, 13–16 cards/panels. Spacing on a 4px base; card padding 14–16px; page gap 18px; max content width 1560px centered.
- Motion: 120–240ms, `cubic-bezier(.22,1,.36,1)` ease-out entries, exits faster; transform/opacity only; honor `prefers-reduced-motion` (prototype zeroes durations globally).
- Breakpoint used by the prototype: **<900px = narrow** (bottom nav + nav drawer, main padding 16/14/96). Tables become horizontally scrollable (`overflow-x:auto`, inner min-width 780–960px). All card grids use `repeat(auto-fit, minmax(min(Xpx,100%),1fr))` so nothing overflows at 320px.

## Information Architecture
Sidebar groups: **Command** (Control Room, Financial Controller, Policies) · **Accounting agents** (Overview, AP, Treasury, Fixed Assets, GL, Tax) · **Operations** (Payment Campaigns, Journal Centre, Approvals, Documents) · **System** (ERP Connections, Audit Trail, Reports, Tenant Settings). Badge counts on items with pending work.
Top bar (sticky, glass nav level): brand · tenant select · legal-entity select · role select · EN/FR segmented toggle · display-settings button (◐) · notifications with count. Second row of context chips: ERP connected + database, last sync, period + accounting date, close status (amber).
Mobile: burger opens glass nav drawer (fixed left, `rgba(11,21,36,.96)`, scrim `rgba(6,14,26,.48)`); bottom nav with 5 destinations (Control, Controller, AP, Treasury, Campaigns), 52px targets, safe-area padding.

## The Campaign Engine (business logic — do not hard-code)
Policy (per tenant+entity, versioned, editable on Policies screen):
- `campaignDays`: list of days-of-month, default `[13, 25]`
- `horizonDays`: default `4`
- `weekendRule`: `prev` (move to previous business day) | `next` | `exec` (keep date, shift execution date)

Selection for a campaign on date D with horizon H: **all approved supplier invoices already overdue** + **due on D** + **due in (D, D+H]**. Example: campaign of the 13th covers overdue + due 13th + due 14–17; the 25th covers overdue + due 25th + 26–29.
Next campaign date = first configured day ≥ today (scan up to 3 months); apply weekend rule; horizon end = adjusted date + H.
Exclude and label (blocked, unselectable, reason shown): draft/unapproved, disputed, on payment hold, duplicate suspect, missing supplier bank details, unresolved tax exception. Flag but allow: related party (controller review). Policy edits recompute the open campaign immediately and bump the policy version (audited).

## Campaign statuses (18, exact order)
Scheduled · AP selection in progress · Awaiting AP review · Sent to Treasury · Treasury review in progress · Information requested · Awaiting Financial Controller approval · Approved for ERP preparation · Submitted to ERP · ERP draft created · Awaiting manual bank/ERP approval · Paid · Partially paid · Rejected · Cancelled · Failed · Reconciliation pending · Reconciled.
Never mark Paid on transmission alone. Campaign detail shows this as a vertical checklist (done ✔ `#40506a`, current ● teal pill `rgba(15,155,142,.13)`, pending ○ `#5b6b80`).

## Screens (hifi set)

**Control Room** — 6 KPI glass cards (label + status chip, mono value, meta): approvals awaiting, draft journals in ERP, overdue supplier total, cash position, unreconciled lines, open anomalies. Then 2-col: "Today's priorities" (opaque list: title, agent · entity · document ref, state + next approver, risk chip, due date, Open button) | right column "Recent agent handoffs" (time, From → To, subject ref, reason, confidence 0.xx, status chip; caption: none of these is a human approval) + "Recent ERP submissions" (erp ref mono, type · journal · time, status chip incl. a Failed example). Bottom: 6 agent cards (name, subtitle, status chip, queue/exceptions counts, last action, Open workspace).

**AP Accountant** — Glass strip stating the selection rule in prose with computed dates + chips (campaign day, horizon → end date, execution date) and proposal total + select-all/clear. 4 stat cards (overdue selected, due within horizon, blocked by controls, in scope/open items). Selection table (opaque): checkbox (18px, accent `#0c7c71`; disabled for blocked/deferred rows) · supplier + ERP partner id · invoice ref + ERP id (mono) · due date · window chip (Overdue N d / Due on campaign day / Within horizon) · open balance (mono right) · control chip (Ready / block reason / Related party) · Defer button. Row tints: blocked `rgba(176,48,32,.045)`, deferred 72% opacity, selected `rgba(15,155,142,.05)`. Sticky footer row: total + count. Action bar: **Send proposal to Treasury** (primary; disabled unless role AP/Admin and ≥1 selected) + Recompute from policy + footnote describing the structured handoff payload. EUR note: fixed parity 655.957 XAF for totals only.

**Treasury** — 4 stat cards (available cash, campaign total, cash after payment, unreconciled). Received-proposal table (same columns, read-only + Defer) with paying-journal select (BNK-SGC / BNK-AFB / CAI-KAI) and status chip; actions **Submit for controller approval** (primary, gated), **Return to AP** (danger). Bank journals list (name, code + masked IBAN, balance, reconciliation chip). Statement upload dropzone (CSV/OFX/MT940/XLSX) + a balance-mismatch example routed to GL as a handoff.

**Financial Controller** — same KPI row; approval panel for the campaign: totals grid (total, overdue, cash after, threshold), amber "above threshold — second approver required" banner when total > threshold, exception list (bank-detail change, related party, over threshold, tax block) each with chip; actions Approve (gated to Controller/Admin) / Reject / Create draft in Odoo. Right: supervised-agents list (queue/exceptions mono, status chip, Open).

**Policies** — form (glass panel): campaign days text input (comma list), horizon number input, weekend rule select; changes apply live and show "Policy v7 · changed date by user". Read-only panel restating the computed rule + next dates.

**Payment Campaigns** — month calendar (Mon-first; campaign day = teal cell with total, horizon days = blue tint, weekends muted, today ring) + campaign list table (id, date, entity, invoices, suppliers, total, overdue, bank, status chip + owner, Open).

**Campaign detail** — 4 stat cards; workflow checklist (18 statuses); audit history (opaque: date/time mono gutter, action bold, detail, actor) — seeded by agent events, appended by every user action; action buttons repeat here.

**ERP Connections / Odoo wizard** — two radio cards: **Simulator** vs **Connect live Odoo** (violet selection). Simulator: credential fields hidden, blue panel explaining why (no credentials needed, records marked "simulated", how to switch). Live: 6 fields with field-level guidance (connection name; server URL "address you sign in with, without /web"; database via Settings → Developer; login = dedicated technical user with read+draft rights only; API key via Preferences → Account security → API keys, entered once never redisplayed; company matching `res.company`). Test connection reports version, database and the 4 verified rights, explicitly "no posting right requested". Recent submissions list below.

**Display drawer** (◐, right-side glass overlay, dialog): glass density radio (Airy/Balanced/Solid) + Reduce transparency switch + reduced-motion note.

## Interactions & State
- State: `lang, role, route, density, reduceT, tenant, entity, navOpen, displayOpen, selected{}, deferred{}, status (1–18), audit[], erpMode, erpTest, toast, w (viewport)`.
- Role gates actions (Admin unlocks all): AP → send proposal; Treasury → submit/return; Controller → approve/reject. Disabled = grey `rgba(11,21,36,.05)` / `#8494a8`, not hidden.
- Transitions wired in the prototype: send→status 4; return→3; submit→7; approve→8; reject→14; ERP draft→10. Each writes an audit entry {timestamp, actor "Role · Name", action, detail} and fires a toast (glass, bottom-right, aria-live=polite, manual dismiss).
- Defer moves an invoice out of totals with a toast + audit note; selection persists across AP/Treasury/detail views.
- ERP submissions must be idempotent (campaign-scoped key); drafts remain unposted until a human posts in Odoo.

## Localisation
Full EN/FR dictionaries; no mixed-language UI. Keep untranslated: ERP identifiers (`account.move,88651`, `res.partner,4412`), account/journal codes (ACH-KAI, BNK-SGC, OD-KLO), document refs, company data. Locale formatting via `Intl` (en-GB / fr-FR): dates, currency (XAF 0 decimals shown as FCFA, EUR 2 decimals), separators (fr uses narrow-space thousands + comma decimals). Professional accounting register in both languages (see dictionaries in the source for approved FR terms, e.g. "retenue à la source", "rapprochement", "écriture brouillon", "piste d'audit").

## Accessibility
WCAG 2.2 AA. Semantic landmarks (banner/nav/main), skip link, one h1 per page + h2 sections, `role=table/row/columnheader/cell` on grid tables, labeled selects/inputs, `aria-current` nav, `role=radiogroup/radio` + `role=switch` with `aria-checked`, dialogs `aria-modal`, toast `aria-live`. Focus-visible ring everywhere. Touch targets ≥44px (32px inline table buttons are the floor; enlarge on touch if possible). Text on white ≥ `#5b6b80`. Status = color + symbol + text. Reduced-motion and reduced-transparency both honored.

## Fixture Data
Tenant **Groupe Kribi Holdings SA**; entities Kribi Agro-Industries SARL (XAF), Kribi Logistique SA (XAF), Kribi Europe SAS (EUR). Simulated accounting date **11 Aug 2026** → next campaign Thu **13 Aug 2026**, horizon → 17 Aug. 22 supplier invoices (6 overdue, 4 due on the 13th, 4 in horizon, 4 later, 6 blocked with distinct reasons + 1 related-party flag). Cash 412 500 000 XAF; approval threshold 50 000 000 XAF. SYSCOHADA + Cameroon tax flavor (TVA 19.25%, RAS 5.5%, TSR; filing deadline the 15th).

## Assets
No raster assets. Fonts: IBM Plex Sans + IBM Plex Mono (Google Fonts). Icons are unicode glyphs in the prototype — swap for a real icon set (e.g. Lucide/Phosphor) in production.

## Suggested Claude Code prompt
"Read design_handoff_my_accountant/README.md and the prototype `My Accountant.dc.html` (template + `class Component` logic at the bottom: i18n dictionaries, invoice fixtures, campaign engine `nextCampaign`/`classify`/`pool`, status machine). Recreate in [your stack] following the README's tokens and behavior exactly. Start with: app shell + tokens + i18n; then the campaign engine as a pure, unit-tested module; then Control Room, AP selection, Treasury, Controller approval, Policies, Campaigns, ERP wizard. Financial tables always opaque; agents never post."

## Build checklist (acceptance)
1. Campaign days/horizon/weekend rule configurable, never hard-coded; 13th campaign = overdue + due-13 + 14–17.
2. AP → Treasury structured handoff; Treasury can return to AP; Controller approves/rejects.
3. ERP records stay draft/unposted until a human posts; no "Paid" on transmission.
4. Complete audit trail of every action; policy changes versioned.
5. EN has no FR text and vice versa.
6. Works at 320px; tables scroll, totals and approval actions stay visible.
7. WCAG 2.2 AA incl. reduced-motion and reduced-transparency modes.
