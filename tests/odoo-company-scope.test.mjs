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

test("AP extraction uses the server-side Kimi connector",()=>{
 assert.match(worker,/KIMI_API_KEY/);
 assert.match(worker,/https:\/\/api\.moonshot\.ai\/v1\/chat\/completions/);
 assert.match(worker,/const AP_MODEL="kimi-k3"/);
 assert.doesNotMatch(worker,/api\.openai\.com/);
});
