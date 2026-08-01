"use client";

import { useMemo, useState } from "react";
import "./modules.css";

type View = "overview" | "invoices" | "treasury" | "integrations";

const invoices = [
  { id: "FAC-2026-0842", supplier: "Africa Office SARL", date: "30 juil. 2026", amount: "1 428 750", status: "À approuver", tone: "amber", confidence: 96 },
  { id: "FAC-2026-0841", supplier: "CamTel Business", date: "29 juil. 2026", amount: "486 000", status: "Prête à comptabiliser", tone: "blue", confidence: 98 },
  { id: "FAC-2026-0839", supplier: "Clean & Care Services", date: "29 juil. 2026", amount: "219 500", status: "À vérifier", tone: "violet", confidence: 74 },
  { id: "FAC-2026-0838", supplier: "Bureau Plus SA", date: "28 juil. 2026", amount: "842 300", status: "Comptabilisée", tone: "green", confidence: 99 },
];

const nav: { id: View; label: string; icon: string }[] = [
  { id: "overview", label: "Choisir un module", icon: "⌂" },
  { id: "invoices", label: "Accounts Payable", icon: "▤" },
  { id: "treasury", label: "Trésorerie", icon: "⇄" },
  { id: "integrations", label: "Intégrations", icon: "⌁" },
];

export default function Home() {
  const [view, setView] = useState<View>("overview");
  const [lang, setLang] = useState<"FR" | "EN">("FR");
  const [notice, setNotice] = useState("");
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => invoices.filter((i) => `${i.id} ${i.supplier}`.toLowerCase().includes(query.toLowerCase())), [query]);

  const flash = (message: string) => { setNotice(message); setTimeout(() => setNotice(""), 2800); };

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">M</span><span><b>Mon Comptable</b><small>Assistant comptable IA</small></span></div>
        <div className="company-switch"><span className="company-avatar">AK</span><span><b>Akwa Consulting</b><small>Entité principale</small></span><span className="chevron">⌄</span></div>
        <nav>
          <p className="nav-label">MODULES</p>
          {nav.map((item) => <button key={item.id} className={view === item.id ? "nav-item active" : "nav-item"} onClick={() => setView(item.id)}><span>{item.icon}</span>{item.label}{item.id === "invoices" && <em>8</em>}</button>)}
          <p className="nav-label">GESTION</p>
          <button className="nav-item" onClick={() => flash("Centre de contrôle ouvert en mode démonstration")}><span>✓</span>Approbations<em>3</em></button>
          <button className="nav-item" onClick={() => flash("Journal d’audit : 248 événements protégés")}><span>◷</span>Journal d’audit</button>
          <button className="nav-item" onClick={() => flash("Les paramètres société sont synchronisés") }><span>⚙</span>Paramètres</button>
        </nav>
        <div className="sidebar-foot"><div className="sync"><span className="pulse"/><span><b>ERP synchronisé</b><small>Il y a 12 minutes</small></span></div><div className="profile"><span>NS</span><div><b>Nadia Simo</b><small>Comptable senior</small></div><button>•••</button></div></div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="mobile-brand"><span className="brand-mark">M</span><b>Mon Comptable</b></div>
          <label className="search">⌕<input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Rechercher une facture, un fournisseur…"/><kbd>⌘ K</kbd></label>
          <div className="top-actions"><button className="lang" onClick={() => setLang(lang === "FR" ? "EN" : "FR")}>{lang}⌄</button><button className="icon-button">?</button><button className="icon-button notification">♢<i>3</i></button></div>
        </header>

        {view === "overview" && <Overview setView={setView} flash={flash} />}
        {view === "invoices" && <Invoices items={filtered} flash={flash} />}
        {view === "treasury" && <Treasury flash={flash} />}
        {view === "integrations" && <Integrations flash={flash} />}
      </section>
      {notice && <div className="toast"><span>✓</span>{notice}</div>}
    </main>
  );
}

function Overview({ setView }: { setView: (v: View) => void; flash: (s: string) => void }) {
  return <div className="content">
    <div className="module-heading"><p>MON COMPTABLE</p><h1>Bonjour Nadia. Quel module souhaitez-vous ouvrir ?</h1><span>Chaque espace possède ses propres processus, contrôles et tableaux de bord.</span></div>
    <div className="module-grid">
      <button className="module-card ap" onClick={() => setView("invoices")}><div className="module-top"><span className="module-icon">▤</span><em>MODULE 01</em></div><div><h2>Accounts Payable</h2><p>Gérez le cycle complet des factures fournisseurs, de la réception à la comptabilisation ERP.</p></div><div className="module-stats"><span><b>8</b><small>À traiter</small></span><span><b>3</b><small>À approuver</small></span><span><b>5</b><small>Prêtes</small></span></div><footer><span>Ouvrir Accounts Payable</span><b>→</b></footer></button>
      <button className="module-card cash" onClick={() => setView("treasury")}><div className="module-top"><span className="module-icon">⇄</span><em>MODULE 02</em></div><div><h2>Treasury</h2><p>Importez, validez et transférez les relevés et transactions bancaires vers votre ERP.</p></div><div className="module-stats"><span><b>2</b><small>Comptes</small></span><span><b>1</b><small>À valider</small></span><span><b>60</b><small>Opérations</small></span></div><footer><span>Ouvrir Treasury</span><b>→</b></footer></button>
    </div>
    <section className="module-security"><span>✓</span><div><b>Deux modules, un même niveau de contrôle</b><p>Isolation des données, droits par rôle, traçabilité et validation humaine restent actifs dans chaque espace.</p></div><button onClick={() => setView("integrations")}>État des intégrations →</button></section>
  </div>;
}

function Metric({ label, value, detail, tone, icon }: {label:string;value:string;detail:string;tone:string;icon:string}) { return <article className="metric"><div className={`metric-icon ${tone}`}>{icon}</div><div><p>{label}</p><b>{value}</b><small>{detail}</small></div></article> }

function InvoiceTable({ items }: { items: typeof invoices }) { return <div className="table"><div className="thead"><span>FOURNISSEUR</span><span>DATE</span><span>MONTANT</span><span>STATUT</span><span>CONFIANCE</span></div>{items.map((row) => <button className="trow" key={row.id}><span className="supplier"><i>{row.supplier.slice(0,2).toUpperCase()}</i><span><b>{row.supplier}</b><small>{row.id}</small></span></span><span>{row.date}</span><b>{row.amount}<small> XAF</small></b><span><em className={`status ${row.tone}`}>● {row.status}</em></span><span className="confidence"><i style={{width:`${row.confidence}%`}}/><small>{row.confidence}%</small></span></button>)}</div> }

function Invoices({ items, flash }: {items: typeof invoices; flash:(s:string)=>void}) { return <div className="content inner"><div className="page-heading"><div><p>COMPTES FOURNISSEURS</p><h1>Factures fournisseurs</h1><p className="subtitle">Contrôlez, approuvez et comptabilisez chaque pièce en toute confiance.</p></div><button className="primary" onClick={()=>flash("Import lancé — analyse OCR en arrière-plan")}>＋ Importer une facture</button></div><div className="filter-row"><button className="filter active">Toutes <b>8</b></button><button className="filter">À vérifier <b>2</b></button><button className="filter">À approuver <b>3</b></button><button className="filter">Prêtes <b>5</b></button><button className="filter">Comptabilisées</button><button className="outline">☷ Filtres</button></div><section className="panel invoice-panel"><InvoiceTable items={items}/></section><div className="ai-note"><span>✦</span><div><b>Contrôles déterministes actifs</b><p>Équilibre débit/crédit, fournisseur ERP, période ouverte, TVA et doublons sont vérifiés avant toute comptabilisation.</p></div></div></div> }

function Treasury({ flash }: {flash:(s:string)=>void}) { return <div className="content inner"><div className="page-heading"><div><p>TRÉSORERIE</p><h1>Relevés bancaires</h1><p className="subtitle">Importez et validez vos opérations avant transfert vers l’ERP.</p></div><button className="primary" onClick={()=>flash("Import prêt — formats CSV, MT940 et CAMT.053")}>＋ Importer un relevé</button></div><div className="bank-cards"><article className="bank-card featured"><div><span className="bank-logo">A</span><p><b>Afriland First Bank</b><small>Compte courant · •••• 2841</small></p></div><h3>18 245 900 <small>XAF</small></h3><footer><span>Dernier import : 31 juil.</span><em>À jour</em></footer></article><article className="bank-card"><div><span className="bank-logo blue">S</span><p><b>Société Générale</b><small>Compte dépenses · •••• 6712</small></p></div><h3>4 812 640 <small>XAF</small></h3><footer><span>Dernier import : 29 juil.</span><em className="warning">2 jours</em></footer></article></div><section className="panel"><div className="panel-head"><div><h2>Imports récents</h2><p>Suivi des validations et transferts ERP</p></div></div><div className="statement-row"><span className="file">CSV</span><div><b>AFB_JUILLET_2026.csv</b><small>42 opérations · Journal BQ-AFB</small></div><span>31 juil. 2026</span><b>12 847 500 XAF</b><em className="status green">● Importé</em></div><div className="statement-row"><span className="file">MT</span><div><b>SGC_2026_W31.mt940</b><small>18 opérations · Journal BQ-SGC</small></div><span>29 juil. 2026</span><b>3 210 400 XAF</b><em className="status amber">● À valider</em></div></section></div> }

function Integrations({ flash }: {flash:(s:string)=>void}) { return <div className="content inner"><div className="page-heading"><div><p>ADMINISTRATION</p><h1>Intégrations</h1><p className="subtitle">État des services et des synchronisations de données.</p></div><button className="outline" onClick={()=>flash("Tous les contrôles de santé ont été relancés")}>↻ Tout vérifier</button></div><div className="integration-grid">{[["ERP","ERP SYSCOHADA (démo)","12 min"],["OCR","Moteur OCR simulé","Opérationnel"],["ST","Stockage documentaire","Opérationnel"],["✉","Réception e-mail","Mode test"]].map((x,i)=><article className="integration" key={x[1]}><span>{x[0]}</span><div><b>{x[1]}</b><small>Dernière activité : {x[2]}</small></div><em className={i===3?"test":""}>● {i===3?"Test":"Connecté"}</em><button onClick={()=>flash(`${x[1]} : connexion vérifiée`)}>Vérifier</button></article>)}</div><div className="mock-banner"><span>i</span><div><b>Environnement de démonstration sécurisé</b><p>Les adaptateurs ERP, OCR, e-mail et stockage utilisent actuellement des réponses simulées. Aucune connexion externe n’est présentée comme active.</p></div></div></div> }
