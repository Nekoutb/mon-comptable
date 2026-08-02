"use client";
import {useEffect,useState} from "react";

type ApDocument={id:string;filename:string;status:string;created_at:string;error_message?:string|null;extraction?:Record<string,unknown>|null};
type AiStatus={ok?:boolean;message?:string;model?:string};

export default function InvoiceIntake(){
 const [documents,setDocuments]=useState<ApDocument[]>([]);
 const [file,setFile]=useState<File|null>(null);
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState("");
 const [aiStatus,setAiStatus]=useState<AiStatus|null>(null);
 const load=async()=>{try{const response=await fetch("/api/ap/documents",{cache:"no-store"}),body=await response.json() as {documents?:ApDocument[]};setDocuments(body.documents||[])}catch{setDocuments([])}};
 const loadAiStatus=async()=>{try{const response=await fetch("/api/ai/status",{cache:"no-store"});setAiStatus(await response.json() as AiStatus)}catch{setAiStatus({ok:false,message:"Kimi status unavailable."})}};
 useEffect(()=>{void load();void loadAiStatus()},[]);
 const submit=async()=>{if(!file)return;setBusy(true);setMessage("");const form=new FormData();form.set("invoice",file);try{const response=await fetch("/api/ap/invoices/extract",{method:"POST",body:form}),body=await response.json() as {ok?:boolean;message?:string};setMessage(body.message||`HTTP ${response.status}`);if(body.ok){setFile(null);await load()}}catch{setMessage("The invoice could not be submitted.")}finally{setBusy(false)}};
 return <section className="panel"><header><h2>New invoice transactions</h2></header><div className="invoice-intake"><div className={`connection-banner ${aiStatus?.ok?"connected":"saved"}`}><b>{aiStatus?.ok?"● Kimi connected":"◐ Kimi unavailable"}</b><span>{aiStatus?.message||"Checking Kimi connection…"}{aiStatus?.model?` · ${aiStatus.model}`:""}</span><button onClick={loadAiStatus}>Test Kimi</button></div><div className="info security"><b>Human-reviewed AP agent · evaluation limited</b> Kimi extracts visible facts only. It never calculates tax, posts entries, changes vendor bank details, or invents missing evidence.</div><div className="upload-row"><label>Supplier invoice pack<input type="file" accept="application/pdf,image/png,image/jpeg,image/webp" onChange={event=>setFile(event.target.files?.[0]||null)}/></label><button className="primary" disabled={!file||busy||!aiStatus?.ok} onClick={submit}>{busy?"Reading invoice…":"Extract with Kimi"}</button><button disabled={busy} onClick={load}>Refresh queue</button></div>{message&&<div className="result" role="status">{message}</div>}<div className="invoice-queue">{documents.length===0?<div className="empty"><b>No invoice documents received</b><p>Upload a real invoice pack; no examples are displayed.</p></div>:documents.map(document=><article className="review-card" key={document.id}><header><div><b>{document.filename}</b><small>{new Date(document.created_at).toLocaleString()}</small></div><span className={`chip ${document.status==="extracted"?"ok":"neutral"}`}>{document.status.replaceAll("_"," ")}</span></header>{document.error_message&&<p className="error-text">{document.error_message}</p>}{document.extraction&&<dl>{Object.entries(document.extraction).filter(([key,value])=>value!==null&&value!==""&&!Array.isArray(value)&&key!=="confidence").map(([key,value])=><div key={key}><dt>{key.replaceAll("_"," ")}</dt><dd>{String(value)}</dd></div>)}</dl>}<p className="review-note">Review required before any accounting proposal or Odoo draft can be created.</p></article>)}</div></div></section>
}
