import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";

const worker=await readFile(new URL("../worker/index.ts",import.meta.url),"utf8");
const page=await readFile(new URL("../app/page.tsx",import.meta.url),"utf8");

test("every Odoo read carries a single selected-company context",()=>{
 assert.match(worker,/allowed_company_ids:\[row\.company_id\]/);
 assert.match(worker,/\["company_id","=",row\.company_id\]/);
});

test("saved company is verified against companies accessible to the API user",()=>{
 assert.match(worker,/verified\.companies\?\.find\(company=>company\.id===body\.company_id\)/);
});

test("ERP screen uses the company-selection wizard",()=>{
 assert.match(page,/<CompanyErpWizard t=\{t\}/);
});

test("AP extraction uses the server-side Anthropic connector",()=>{
 assert.match(worker,/ANTHROPIC_API_KEY/);
 assert.match(worker,/https:\/\/api\.anthropic\.com\/v1\/messages/);
 assert.match(worker,/const AP_MODEL="claude-sonnet-5"/);
 assert.doesNotMatch(worker,/api\.moonshot\.ai/);
 assert.doesNotMatch(worker,/api\.openai\.com/);
});

test("AP queue excludes legacy providers and failed Claude documents can be retried",()=>{
 assert.match(worker,/r\.model=\?/);
 assert.match(worker,/existing&&existing\.status!=="failed"/);
 assert.doesNotMatch(worker,/confidence:\{type:"number",minimum:/);
});

test("AP agent performs controlled Odoo matching and only creates drafts after review",()=>{
 for(const model of ["res.partner","purchase.order","stock.picking","account.move","account.journal","purchase.order.line","ir.attachment"]) assert.match(worker,new RegExp(model.replace(".","\\.")));
 assert.match(worker,/readyForDraft/);
 assert.match(worker,/odoo_draft_created/);
 assert.match(worker,/move_type:"in_invoice"/);
 assert.doesNotMatch(worker,/action_post/);
});
