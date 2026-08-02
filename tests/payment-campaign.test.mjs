import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

async function loadCampaignModule(){
  const source=await readFile(new URL("../app/lib/payment-campaign.ts",import.meta.url),"utf8");
  const output=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(output).toString("base64")}`);
}

test("13th campaign includes overdue invoices and invoices due through the 17th",async()=>{
  const mod=await loadCampaignModule();
  const selected=mod.selectCampaignInvoices(mod.sampleVendorInvoices,new Date("2026-08-13T00:00:00Z"),{campaignDays:[13,25],horizonDays:4});
  assert.deepEqual(selected.map(invoice=>invoice.id),["INV-2026-0811","INV-2026-0818","INV-2026-0820","INV-2026-0822"]);
});

test("payment holds, missing approvals and missing bank details are excluded",async()=>{
  const mod=await loadCampaignModule();
  const selected=mod.selectCampaignInvoices(mod.sampleVendorInvoices,new Date("2026-08-13T00:00:00Z"),{campaignDays:[13,25],horizonDays:4});
  for(const blocked of ["INV-2026-0827","INV-2026-0829","INV-2026-0831"])
    assert.equal(selected.some(invoice=>invoice.id===blocked),false);
});

test("campaign dates and forward-looking horizon remain configurable",async()=>{
  const mod=await loadCampaignModule();
  const next=mod.nextCampaignDate(new Date("2026-08-18T00:00:00Z"),{campaignDays:[13,25],horizonDays:6});
  assert.equal(next.toISOString(),"2026-08-25T00:00:00.000Z");
  assert.equal(mod.campaignWindow(next,{campaignDays:[13,25],horizonDays:6}).end.toISOString(),"2026-08-31T00:00:00.000Z");
});
