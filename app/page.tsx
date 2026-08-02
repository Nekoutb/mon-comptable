"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "./modules.css";
import { AccountingApi, getApiHealth, login, type ApiDashboard, type ApiInvoice, type ApiMode, type ApiStatement, type SessionUser } from "./lib/api";
import { makeT, type Lang, type TKey } from "./lib/i18n";

type View = "overview" | "invoices" | "treasury" | "integrations";
type T = (key: TKey) => string;
type Session = { api: AccountingApi; user: SessionUser };
type Row = { id: string; supplier: string; number: string; date: string; amount: number; currency: string; status: string; confidence: number };
type Filter = "all" | "review" | "approve" | "ready" | "posted";

const demoInvoices: Row[] = [
  { id: "demo-0842", supplier: "Africa Office SARL", number: "FAC-2026-0842", date: "2026-07-30", amount: 1428750, currency: "XAF", status: "pending_approval", confidence: 96 },
  { id: "demo-0841", supplier: "CamTel Business", number: "FAC-2026-0841", date: "2026-07-29", amount: 486000, currency: "XAF", status: "approved", confidence: 98 },
  { id: "demo-0839", supplier: "Clean & Care Services", number: "FAC-2026-0839", date: "2026-07-29", amount: 219500, currency: "XAF", status: "review", confidence: 74 },
  { id: "demo-0838", supplier: "Bureau Plus SA", number: "FAC-2026-0838", date: "2026-07-28", amount: 842300, currency: "XAF", status: "posted", confidence: 99 },
];

const invoiceTone: Record<string, string> = { received: "blue", ocr_pending: "blue", review: "violet", supplier_not_found: "amber", duplicate: "amber", pending_approval: "amber", approved: "blue", erp_draft: "blue", posted: "green", failed: "amber" };
const statementTone: Record<string, string> = { received: "violet", parsed: "amber", validated: "blue", imported: "green", duplicate: "amber", failed: "amber" };
const FILTERS: Record<Filter, string[]> = {
  all: [],
  review: ["received", "ocr_pending", "review", "supplier_not_found", "duplicate", "failed"],
  approve: ["pending_approval"],
  ready: ["approved", "erp_draft"],
  posted: ["posted"],
};

const locale = (lang: Lang) => (lang === "FR" ? "fr-FR" : "en-GB");
const formatAmount = (value: number | string, lang: Lang) => new Intl.NumberFormat(locale(lang), { maximumFractionDigits: 0 }).format(Number(value));
const formatDate = (value: string, lang: Lang) => {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat(locale(lang), { day: "numeric", month: "short", year: "numeric" }).format(parsed);
};
const sumStatuses = (counts: Record<string, number> | undefined, keys: string[]) => keys.reduce((total, key) => total + (counts?.[key] ?? 0), 0);

export default function Home() {
  const [view, setView] = useState<View>("overview");
  const [lang, setLang] = useState<Lang>("FR");
  const [notice, setNotice] = useState("");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [apiMode, setApiMode] = useState<ApiMode>("checking");
  const [session, setSession] = useState<Session | null>(null);
  const [loginOpen, setLoginOpen] = useState(false);
  const [invoices, setInvoices] = useState<ApiInvoice[]>([]);
  const [statements, setStatements] = useState<ApiStatement[]>([]);
  const [dashboard, setDashboard] = useState<ApiDashboard | null>(null);
  const [suppliers, setSuppliers] = useState<Record<string, string>>({});
  const t = useMemo(() => makeT(lang), [lang]);

  const flash = (message: string) => { setNotice(message); setTimeout(() => setNotice(""), 3400); };

  useEffect(() => {
    const controller = new AbortController();
    getApiHealth(controller.signal).then((health) => setApiMode(health ? "connected" : "demo")).catch(() => setApiMode("demo"));
    return () => controller.abort();
  }, []);

  useEffect(() => { document.documentElement.lang = lang === "FR" ? "fr" : "en"; }, [lang]);

  const refresh = useCallback(async (active: Session) => {
    const [dash, invoiceRows, statementRows, supplierRows] = await Promise.all([
      active.api.dashboard(), active.api.invoices(), active.api.statements(), active.api.suppliers(),
    ]);
    setDashboard(dash); setInvoices(invoiceRows); setStatements(statementRows);
    setSuppliers(Object.fromEntries(supplierRows.map((row) => [row.id, row.name])));
  }, []);

  useEffect(() => {
    if (!session) return;
    const id = setTimeout(() => { refresh(session).catch(() => undefined); }, 0);
    return () => clearTimeout(id);
  }, [view, session, refresh]);

  const handleLogin = async (email: string, password: string, tenant: string) => {
    const api = new AccountingApi(await login(email, password, tenant || undefined));
    const active = { api, user: await api.me() };
    setSession(active); setLoginOpen(false);
    await refresh(active);
    flash(t("toast.loginOk"));
  };

  const signOut = () => { setSession(null); setInvoices([]); setStatements([]); setDashboard(null); flash(t("toast.logout")); };

  const rows: Row[] = session
    ? invoices.map((invoice) => ({
        id: invoice.id,
        supplier: (invoice.supplier_id && suppliers[invoice.supplier_id]) || "—",
        number: invoice.invoice_number ?? invoice.id.slice(0, 8),
        date: invoice.invoice_date ?? invoice.created_at,
        amount: Number(invoice.gross_amount),
        currency: invoice.currency,
        status: invoice.status,
        confidence: Math.round(Number(invoice.ocr_confidence ?? 0)),
      }))
    : demoInvoices;
  const filtered = rows.filter((row) => `${row.number} ${row.supplier}`.toLowerCase().includes(query.toLowerCase()) && (filter === "all" || FILTERS[filter].includes(row.status)));
  const counts = (bucket: Filter) => (bucket === "all" ? rows.length : rows.filter((row) => FILTERS[bucket].includes(row.status)).length);
  const approvals = counts("approve");

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">M</span><span><b>Mon Comptable</b><small>{t("brand.subtitle")}</small></span></div>
        <div className="company-switch"><span className="company-avatar">{session ? session.user.name.slice(0, 2).toUpperCase() : "AK"}</span><span><b>{session ? "Akwa Consulting" : "Akwa Consulting"}</b><small>{t("company.entity")}</small></span><span className="chevron">⌄</span></div>
        <nav>
          <p className="nav-label">{t("nav.modules")}</p>
          {([
            { id: "overview" as View, label: t("nav.overview"), icon: "⌂" },
            { id: "invoices" as View, label: t("nav.ap"), icon: "▤" },
            { id: "treasury" as View, label: t("nav.treasury"), icon: "⇄" },
            { id: "integrations" as View, label: t("nav.integrations"), icon: "⌁" },
          ]).map((item) => <button key={item.id} className={view === item.id ? "nav-item active" : "nav-item"} onClick={() => setView(item.id)}><span>{item.icon}</span>{item.label}{item.id === "invoices" && rows.length > 0 && <em>{rows.length}</em>}</button>)}
          <p className="nav-label">{t("nav.management")}</p>
          <button className="nav-item" onClick={() => { setView("invoices"); setFilter("approve"); }}><span>✓</span>{t("nav.approvals")}{approvals > 0 && <em>{approvals}</em>}</button>
          <button className="nav-item" onClick={() => flash(t("toast.notAvailable"))}><span>◷</span>{t("nav.audit")}</button>
          <button className="nav-item" onClick={() => flash(t("toast.notAvailable"))}><span>⚙</span>{t("nav.settings")}</button>
        </nav>
        <div className="sidebar-foot">
          <div className="sync"><span className="pulse" /><span><b>{t("sidebar.adapters.title")}</b><small>{apiMode === "connected" ? t("sidebar.adapters.connected") : t("sidebar.adapters.offline")}</small></span></div>
          <div className="profile">
            <span>{session ? session.user.name.slice(0, 2).toUpperCase() : "?"}</span>
            <div><b>{session ? session.user.name : t("sidebar.demoUser")}</b><small>{session ? session.user.role : t("sidebar.demoRole")}</small></div>
            {apiMode === "connected" && (session
              ? <button onClick={signOut} title={t("sidebar.signout")}>⎋</button>
              : <button onClick={() => setLoginOpen(true)} title={t("sidebar.signin")}>→</button>)}
          </div>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="mobile-brand"><span className="brand-mark">M</span><b>Mon Comptable</b></div>
          <label className="search">⌕<input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("search.placeholder")} /><kbd>⌘ K</kbd></label>
          <div className="top-actions"><button className="lang" onClick={() => setLang(lang === "FR" ? "EN" : "FR")}>{lang}⌄</button><button className="icon-button">?</button></div>
        </header>

        {apiMode === "connected" && !session && <div className="session-banner"><span>ⓘ</span>{t("banner.connectPrompt")}<button onClick={() => setLoginOpen(true)}>{t("sidebar.signin")}</button></div>}

        {view === "overview" && <Overview setView={setView} t={t} session={session} dashboard={dashboard} statements={statements} />}
        {view === "invoices" && <Invoices items={filtered} t={t} lang={lang} session={session} filter={filter} setFilter={setFilter} counts={counts} flash={flash} refresh={() => session && refresh(session)} />}
        {view === "treasury" && <Treasury t={t} lang={lang} session={session} statements={statements} flash={flash} />}
        {view === "integrations" && <Integrations t={t} flash={flash} apiMode={apiMode} />}
      </section>

      {loginOpen && <LoginPanel t={t} onClose={() => setLoginOpen(false)} onSubmit={handleLogin} />}
      {notice && <div className="toast"><span>✓</span>{notice}</div>}
    </main>
  );
}

function DataChip({ live, t }: { live: boolean; t: T }) {
  return <span className={live ? "data-chip live" : "data-chip"}>{live ? t("banner.liveData") : t("banner.demoData")}</span>;
}

function Overview({ setView, t, session, dashboard, statements }: { setView: (v: View) => void; t: T; session: Session | null; dashboard: ApiDashboard | null; statements: ApiStatement[] }) {
  const ap = dashboard?.accounts_payable;
  const live = Boolean(session);
  const apStats: [string | number, TKey][] = live
    ? [[sumStatuses(ap, FILTERS.review), "overview.stats.toProcess"], [sumStatuses(ap, FILTERS.approve), "overview.stats.toApprove"], [sumStatuses(ap, FILTERS.ready), "overview.stats.ready"]]
    : [[8, "overview.stats.toProcess"], [3, "overview.stats.toApprove"], [5, "overview.stats.ready"]];
  const trStats: [string | number, TKey][] = live
    ? [[statements.length, "overview.stats.statements"], [statements.filter((s) => ["received", "parsed"].includes(s.status)).length, "overview.stats.toValidate"], [statements.filter((s) => s.status === "imported").length, "overview.stats.imported"]]
    : [[2, "overview.stats.statements"], [1, "overview.stats.toValidate"], [1, "overview.stats.imported"]];
  return <div className="content">
    <div className="module-heading"><p>{t("overview.eyebrow")}</p><h1>{session ? `${t("overview.greeting")} ${session.user.name.split(" ")[0]}. ` : ""}{t("overview.title")}</h1><span>{t("overview.subtitle")} <DataChip live={live} t={t} /></span></div>
    <div className="module-grid">
      <button className="module-card ap" onClick={() => setView("invoices")}><div className="module-top"><span className="module-icon">▤</span><em>{t("overview.module")} 01</em></div><div><h2>Accounts Payable</h2><p>{t("overview.ap.description")}</p></div><div className="module-stats">{apStats.map(([value, label]) => <span key={label}><b>{value}</b><small>{t(label)}</small></span>)}</div><footer><span>{t("overview.ap.open")}</span><b>→</b></footer></button>
      <button className="module-card cash" onClick={() => setView("treasury")}><div className="module-top"><span className="module-icon">⇄</span><em>{t("overview.module")} 02</em></div><div><h2>Treasury</h2><p>{t("overview.treasury.description")}</p></div><div className="module-stats">{trStats.map(([value, label]) => <span key={label}><b>{value}</b><small>{t(label)}</small></span>)}</div><footer><span>{t("overview.treasury.open")}</span><b>→</b></footer></button>
    </div>
    <section className="module-security"><span>✓</span><div><b>{t("overview.security.title")}</b><p>{t("overview.security.body")}</p></div><button onClick={() => setView("integrations")}>{t("overview.security.link")}</button></section>
  </div>;
}

function InvoiceTable({ items, t, lang }: { items: Row[]; t: T; lang: Lang }) {
  if (!items.length) return <p className="empty-note">{t("invoices.empty")}</p>;
  return <div className="table"><div className="thead"><span>{t("invoices.table.supplier")}</span><span>{t("invoices.table.date")}</span><span>{t("invoices.table.amount")}</span><span>{t("invoices.table.status")}</span><span>{t("invoices.table.confidence")}</span></div>{items.map((row) => <button className="trow" key={row.id}><span className="supplier"><i>{row.supplier.slice(0, 2).toUpperCase()}</i><span><b>{row.supplier}</b><small>{row.number}</small></span></span><span>{formatDate(row.date, lang)}</span><b>{formatAmount(row.amount, lang)}<small> {row.currency}</small></b><span><em className={`status ${invoiceTone[row.status] ?? "blue"}`}>● {t(`status.${row.status}` as TKey)}</em></span><span className="confidence"><i style={{ width: `${row.confidence}%` }} /><small>{row.confidence}%</small></span></button>)}</div>;
}

function Invoices({ items, t, lang, session, filter, setFilter, counts, flash, refresh }: { items: Row[]; t: T; lang: Lang; session: Session | null; filter: Filter; setFilter: (f: Filter) => void; counts: (f: Filter) => number; flash: (s: string) => void; refresh: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const onFile = async (file: File | undefined) => {
    if (!file || !session) return;
    try {
      const invoice = await session.api.uploadInvoice(file);
      flash(invoice.status === "ocr_pending" ? t("toast.uploadPending") : `${t("toast.uploadOk")} ${t(`status.${invoice.status}` as TKey)}`);
      refresh();
    } catch (error) {
      flash(`${t("toast.uploadError")} ${error instanceof Error ? error.message : String(error)}`);
    }
  };
  const filterDefs: [Filter, TKey][] = [["all", "invoices.filter.all"], ["review", "invoices.filter.review"], ["approve", "invoices.filter.approve"], ["ready", "invoices.filter.ready"], ["posted", "invoices.filter.posted"]];
  return <div className="content inner">
    <div className="page-heading"><div><p>{t("invoices.eyebrow")}</p><h1>{t("invoices.title")} <DataChip live={Boolean(session)} t={t} /></h1><p className="subtitle">{t("invoices.subtitle")}</p></div>
      <input ref={fileRef} type="file" accept=".pdf,.png,.jpg,.jpeg,.tiff" hidden onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ""; }} />
      <button className="primary" onClick={() => session ? fileRef.current?.click() : flash(t("toast.demoImport"))}>{t("invoices.import")}</button></div>
    <div className="filter-row">{filterDefs.map(([id, label]) => <button key={id} className={filter === id ? "filter active" : "filter"} onClick={() => setFilter(id)}>{t(label)} {counts(id) > 0 && <b>{counts(id)}</b>}</button>)}<button className="outline" onClick={() => flash(t("toast.notAvailable"))}>{t("invoices.filter.more")}</button></div>
    <section className="panel invoice-panel"><InvoiceTable items={items} t={t} lang={lang} /></section>
    <div className="ai-note"><span>✦</span><div><b>{t("invoices.ai.title")}</b><p>{t("invoices.ai.body")}</p></div></div>
  </div>;
}

function Treasury({ t, lang, session, statements, flash }: { t: T; lang: Lang; session: Session | null; statements: ApiStatement[]; flash: (s: string) => void }) {
  const live = Boolean(session);
  return <div className="content inner">
    <div className="page-heading"><div><p>{t("treasury.eyebrow")}</p><h1>{t("treasury.title")} <DataChip live={live} t={t} /></h1><p className="subtitle">{t("treasury.subtitle")}</p></div><button className="primary" onClick={() => flash(t("toast.statementHint"))}>{t("treasury.import")}</button></div>
    {!live && <div className="bank-cards"><article className="bank-card featured"><div><span className="bank-logo">A</span><p><b>Afriland First Bank</b><small>{t("banner.demoData")} · •••• 2841</small></p></div><h3>18 245 900 <small>XAF</small></h3><footer><span>{t("banner.demoData")}</span><em>—</em></footer></article><article className="bank-card"><div><span className="bank-logo blue">S</span><p><b>Société Générale</b><small>{t("banner.demoData")} · •••• 6712</small></p></div><h3>4 812 640 <small>XAF</small></h3><footer><span>{t("banner.demoData")}</span><em>—</em></footer></article></div>}
    <section className="panel"><div className="panel-head"><div><h2>{t("treasury.recent.title")}</h2><p>{t("treasury.recent.subtitle")}</p></div></div>
      {live
        ? (statements.length
          ? statements.map((statement) => <div className="statement-row" key={statement.id}><span className="file">{statement.format === "camt053" ? "XML" : statement.format === "mt940" ? "MT" : "CSV"}</span><div><b>{statement.reference}</b><small>{t("treasury.opening")} {formatAmount(statement.opening_balance, lang)} → {t("treasury.closing")} {formatAmount(statement.closing_balance, lang)} {statement.currency}</small></div><span>{formatDate(statement.created_at, lang)}</span><b>{formatAmount(statement.closing_balance, lang)} {statement.currency}</b><em className={`status ${statementTone[statement.status] ?? "blue"}`}>● {t(`stmt.${statement.status}` as TKey)}</em></div>)
          : <p className="empty-note">{t("treasury.empty")}</p>)
        : <><div className="statement-row"><span className="file">CSV</span><div><b>AFB_JUILLET_2026.csv</b><small>42 {t("treasury.operations")} · BQ-AFB ({t("banner.demoData")})</small></div><span>{formatDate("2026-07-31", lang)}</span><b>12 847 500 XAF</b><em className="status green">● {t("stmt.imported")}</em></div><div className="statement-row"><span className="file">MT</span><div><b>SGC_2026_W31.mt940</b><small>18 {t("treasury.operations")} · BQ-SGC ({t("banner.demoData")})</small></div><span>{formatDate("2026-07-29", lang)}</span><b>3 210 400 XAF</b><em className="status amber">● {t("stmt.parsed")}</em></div></>}
    </section>
  </div>;
}

function Integrations({ t, flash, apiMode }: { t: T; flash: (s: string) => void; apiMode: ApiMode }) {
  const connected = apiMode === "connected";
  const entries: [string, string, string][] = [
    ["API", connected ? t("integrations.api.connected") : t("integrations.api.offline"), connected ? t("integrations.api.stateOk") : t("integrations.api.stateDemo")],
    ["ERP", t("integrations.erp"), t("integrations.simulated")],
    ["OCR", t("integrations.ocr"), t("integrations.simulated")],
    ["✉", t("integrations.email"), t("integrations.testMode")],
  ];
  return <div className="content inner">
    <div className="page-heading"><div><p>{t("integrations.eyebrow")}</p><h1>{t("integrations.title")}</h1><p className="subtitle">{t("integrations.subtitle")}</p></div><button className="outline" onClick={() => flash(t("toast.refreshOk"))}>{t("integrations.checkAll")}</button></div>
    <div className="integration-grid">{entries.map((entry, index) => <article className="integration" key={entry[1]}><span>{entry[0]}</span><div><b>{entry[1]}</b><small>{t("integrations.state")} {entry[2]}</small></div><em className={index > 0 || !connected ? "test" : ""}>● {index === 0 && connected ? t("integrations.connected") : t("integrations.test")}</em><button onClick={() => flash(`${entry[1]} : ${entry[2]}`)}>{t("integrations.check")}</button></article>)}</div>
    <div className="mock-banner"><span>i</span><div><b>{connected ? t("integrations.banner.connected") : t("integrations.banner.demo")}</b><p>{t("integrations.banner.body")}</p></div></div>
  </div>;
}

function LoginPanel({ t, onClose, onSubmit }: { t: T; onClose: () => void; onSubmit: (email: string, password: string, tenant: string) => Promise<void> }) {
  const [email, setEmail] = useState("nadia@akwa.example");
  const [password, setPassword] = useState("");
  const [tenant, setTenant] = useState("akwa");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true); setError("");
    try { await onSubmit(email, password, tenant); } catch (err) { setError(err instanceof Error ? err.message : String(err)); } finally { setBusy(false); }
  };
  return <div className="login-overlay" onClick={onClose}>
    <form className="login-card" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
      <h2>{t("login.title")}</h2>
      <p>{t("login.subtitle")}</p>
      <label className="field"><span>{t("login.email")}</span><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus /></label>
      <label className="field"><span>{t("login.password")}</span><input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} /></label>
      <label className="field"><span>{t("login.tenant")}</span><input value={tenant} onChange={(e) => setTenant(e.target.value)} /></label>
      {error && <p className="login-error">{t("login.error")} {error}</p>}
      <div className="login-actions"><button type="button" className="outline" onClick={onClose}>{t("login.cancel")}</button><button type="submit" className="primary" disabled={busy}>{t("login.submit")}</button></div>
    </form>
  </div>;
}
