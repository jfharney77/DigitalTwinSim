// Proves the in-browser engine: on the hosted build of a scenario-driven app,
// change a control so the request body is one build_static.py never prebaked,
// and compare what the Pyodide worker answers with the native engine's answer
// for the same body (EXPECT_JSON = scripts/static/native_answer.py output).
//   SITE_URL=http://127.0.0.1:6170 COMPONENT=PhysicsME5 BODY='{"durationMin":33}' EXPECT_JSON=/path node e2e/static_engine.check.mjs
import { chromium } from "@playwright/test";
import { existsSync, readFileSync } from "node:fs";

const site = process.env.SITE_URL ?? "http://127.0.0.1:6170";
const comp = process.env.COMPONENT ?? "PhysicsME5";
const body = process.env.BODY ?? '{"durationMin":33}';
const expected = JSON.parse(readFileSync(process.env.EXPECT_JSON, "utf8"));

let exe; try { exe = chromium.executablePath(); } catch { exe = ""; }
const browser = await chromium.launch(
  exe && existsSync(exe) ? {} : existsSync("/usr/bin/google-chrome") ? { executablePath: "/usr/bin/google-chrome" } : {});
const page = await browser.newPage();
const requests = [];
page.on("request", (r) => requests.push(r.url()));
await page.goto(`${site}/${comp}/`, { waitUntil: "load" });
const t0 = Date.now();
const got = await page.evaluate(async (b) => {
  const r = await window.__twinStatic.apiFetch("/api/simulate", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: b });
  return { status: r.status, json: await r.json() };
}, body);
await browser.close();
if (got.error) { console.error(got.error); process.exit(2); }
const usedPyodide = requests.some((u) => u.includes("pyodide"));
const same = got.status === expected.status && JSON.stringify(got.json) === JSON.stringify(expected.body);
console.log(`status ${got.status}, pyodide loaded: ${usedPyodide}, identical to native engine: ${same}, ${Date.now() - t0} ms`);
process.exit(usedPyodide && same ? 0 : 1);
