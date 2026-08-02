import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("../app/lib/i18n.ts", import.meta.url), "utf8");
const enBlock = source.match(/en:\s*\{([\s\S]*?)\n\s*\},\n\s*fr:/)?.[1] ?? "";
const frBlock = source.match(/fr:\s*\{([\s\S]*?)\n\s*\},\n\} as const/)?.[1] ?? "";
const keys = block => [...block.matchAll(/(?:^|,\s*)([A-Za-z][A-Za-z0-9]*):/g)].map(match => match[1]);

test("English and French dictionaries have identical, non-empty keys", () => {
  const enKeys = keys(enBlock);
  const frKeys = keys(frBlock);
  assert.ok(enKeys.length > 100, "expected comprehensive translation coverage");
  assert.deepEqual([...enKeys].sort(), [...frKeys].sort());
  assert.equal(/:\s*"\s*"/.test(enBlock + frBlock), false);
});

test("agent names are fully localised", () => {
  for (const english of ["Financial Controller","AP Accountant","Treasury Accountant","Fixed Assets Accountant","General Ledger Accountant","Tax Accountant"])
    assert.equal(frBlock.includes(english), false, `French dictionary contains ${english}`);
  for (const french of ["Comptable fournisseurs","Comptable trésorerie","Comptable immobilisations","Comptable général","Comptable fiscaliste"])
    assert.equal(enBlock.includes(french), false, `English dictionary contains ${french}`);
});

test("page components use the central translation dictionary", () => {
  const page = readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");
  for (const forbidden of ["AP Accountant","Comptable fournisseurs","Treasury Accountant","Comptable trésorerie","Submit draft to ERP","Transmettre l’écriture"])
    assert.equal(page.includes(forbidden), false, `hard-coded interface string: ${forbidden}`);
});
