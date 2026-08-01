import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(new Request("http://localhost/", { headers: { accept: "text/html" } }), { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } }, { waitUntil() {}, passThroughOnException() {} });
}

test("server renders Mon Comptable product metadata", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /Mon Comptable/);
  assert.match(html, /Assistant comptable IA/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape|react-loading-skeleton/i);
});

test("keeps Accounts Payable and Treasury as separate modules", async () => {
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  assert.match(page, /Accounts Payable/);
  assert.match(page, /Treasury/);
  assert.match(page, /setView\("invoices"\)/);
  assert.match(page, /setView\("treasury"\)/);
});

test("includes a typed API boundary", async () => {
  const api = await readFile(new URL("../app/lib/api.ts", import.meta.url), "utf8");
  assert.match(api, /NEXT_PUBLIC_API_URL/);
  assert.match(api, /Authorization: `Bearer/);
  assert.match(api, /getApiHealth/);
});
