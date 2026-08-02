"use client";

import {useState} from "react";
import {formatDate,formatMoney,type Lang,type Translation} from "./lib/i18n";
import {campaignWindow,type CampaignStatus,type PaymentPolicy,type VendorInvoice} from "./lib/payment-campaign";

type Props={t:Translation;lang:Lang;policy:PaymentPolicy;campaignDate:Date;invoices:VendorInvoice[];status:CampaignStatus;send:()=>void};

function statusLabel(t:Translation,status:CampaignStatus){return {scheduled:t.campaignScheduled,sent_to_treasury:t.campaignSentTreasury,awaiting_controller:t.campaignAwaitingController,approved:t.campaignApprovedStatus}[status]}

export function ApOperationsWorkspace({t,lang,policy,campaignDate,invoices,status,send}:Props){
  const [source,setSource]=useState("");
  const [stage,setStage]=useState(0);
  const [comment,setComment]=useState("");
  const window=campaignWindow(campaignDate,policy);
  const emailItems: {id:string;sender:string;subject:string;state:string}[]=[];
  const workflow=[[t.purchaseOrderCheck,t.purchaseOrderCheckDetail],[t.amountMatch,t.amountMatchDetail],[t.deliveryNoteCheck,t.deliveryNoteCheckDetail],[t.vendorIdentification,t.vendorIdentificationDetail],[t.accountingProposal,t.accountingProposalDetail],[t.odooDraftPreparation,t.odooDraftPreparationDetail]];
  const total=invoices.reduce((sum,item)=>sum+item.amount,0);
  return <div className="content inner"><div className="page-heading"><div><p>{t.paymentReadiness}</p><h1>{t.apName}</h1><p className="subtitle">{t.apMission}</p></div></div>
    <div className="ap-kpis"><section className="panel ap-kpi"><small>{t.unpostedApJournals}</small><b>—</b><p>{t.noConnections}</p></section><section className="panel ageing-panel"><div className="panel-head"><h2>{t.apAgeing}</h2></div><div className="empty-connection"><p>{t.noConnections}</p></div></section></div>
    <div className="invoice-intake-grid"><section className="panel invoice-intake"><div className="panel-head"><div><h2>{t.processNewInvoice}</h2><p>{t.manualUpload}</p></div></div><label className="drop-zone compact-upload"><input type="file" accept=".pdf,.png,.jpg,.jpeg,.zip" onChange={e=>{const file=e.target.files?.[0];if(file){setSource(file.name);setStage(0)}}}/><span>＋</span><b>{t.uploadInvoicePack}</b><small>{t.invoicePackFormats}</small></label></section><section className="panel"><div className="panel-head"><div><h2>{t.emailInvoices}</h2><p>{t.emailInboxNote}</p></div></div>{emailItems.length===0?<div className="empty-connection"><p>{t.noConnections}</p></div>:emailItems.map(item=><div className="email-invoice" key={item.id}><div><b>{item.subject}</b><small>{item.sender} · {item.state}</small></div><button className="outline" onClick={()=>{setSource(item.id);setStage(0)}}>{t.processInvoice}</button></div>)}</section></div>
    <section className="panel invoice-workflow"><div className="panel-head"><div><h2>{t.invoiceTreatment}</h2><p>{source?`${t.sourceDocument}: ${source}`:t.noInvoiceSelected}</p></div></div>{workflow.map(([title,detail],index)=><div className={`workflow-step ${stage>index?"done":""}`} key={title}><span>{stage>index?"✓":index+1}</span><div><b>{title}</b><small>{detail}</small></div><em>{stage>index?t.completedCheck:t.notStarted}</em></div>)}<div className="workflow-actions"><button className="outline" disabled={!source} onClick={()=>setStage(5)}>{t.startProcessing}</button></div></section>
    {stage>=5&&<div className="ap-draft"><section className="panel"><div className="panel-head"><h2>{t.proposedApJournal}</h2></div><div className="empty-connection"><p>{t.noConnections}</p></div></section><section className="panel"><div className="panel-head"><h2>{t.supportingDocuments}</h2></div><div className="supporting-pack"><p>{source}</p><label>{t.reviewerComments}<textarea value={comment} onChange={e=>setComment(e.target.value)} placeholder={t.commentPlaceholder}/></label></div><div className="workflow-actions"><button className="primary" disabled>{t.pushApDraft}</button></div></section></div>}
    <section className="panel campaign-panel"><div className="panel-head"><div><h2>{t.paymentProposal}</h2><p>{t.apEligibilityNote}</p></div><button className="primary" disabled={status!=="scheduled"} onClick={send}>→ {t.sendToTreasury}</button></div><div className="campaign-summary"><article><small>{t.campaignDate}</small><b>{formatDate(campaignDate,lang)}</b></article><article><small>{t.selectionHorizon}</small><b>{formatDate(window.end,lang)}</b></article><article><small>{t.eligibleInvoices}</small><b>{invoices.length}</b></article><article><small>{t.campaignTotal}</small><b>{formatMoney(total,lang)}</b></article><article><small>{t.campaignStatus}</small><b>{statusLabel(t,status)}</b></article></div></section>
  </div>
}
