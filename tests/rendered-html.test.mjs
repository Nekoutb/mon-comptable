import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(new Request("http://localhost/", { headers: { accept: "text/html" } }), { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } }, { waitUntil() {}, passThroughOnException() {} });
}

test("server renders bilingual product metadata with English as the default", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /Mon Comptable/);
  assert.match(html, /My Accountant/);
  assert.match(html, /AI accounting team/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape|react-loading-skeleton/i);
});

test("keeps all six accounting agents as separate modules", async () => {
  const i18n = await readFile(new URL("../app/lib/i18n.ts", import.meta.url), "utf8");
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  for (const name of ["Financial Controller", "AP Accountant", "Treasury Accountant", "Fixed Assets Accountant", "General Ledger Accountant", "Tax Accountant"])
    assert.match(i18n, new RegExp(name));
  for (const id of ["controller", "ap", "treasury", "assets", "gl", "tax"])
    assert.match(page, new RegExp(`id:\"${id}\"`));
});

test("includes a typed API boundary", async () => {
  const api = await readFile(new URL("../app/lib/api.ts", import.meta.url), "utf8");
  assert.match(api, /NEXT_PUBLIC_API_URL/);
  assert.match(api, /Authorization: `Bearer/);
  assert.match(api, /getApiHealth/);
});

test("AP workspace contains invoice intake, email capture and Odoo draft controls", async () => {
  const ap = await readFile(new URL("../app/ap-operations.tsx", import.meta.url), "utf8");
  for (const control of ["unpostedApJournals", "apAgeing", "uploadInvoicePack", "emailInvoices", "purchaseOrderCheck", "deliveryNoteCheck", "vendorIdentification", "accountingProposal", "pushApDraft"])
    assert.match(ap, new RegExp(control));
  assert.doesNotMatch(ap, /AFR-2026-0842|BANK-REC-0731|CLOSE-2026-07/);
});
