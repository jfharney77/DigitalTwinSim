// Hosted-site check for the pages that are not twins: root index, Learn,
// CustomerSetup. Run by scripts/smoke_static.sh against a plain static server.
// Asserts that no link still points at localhost, that hosted twins' links land
// on a sibling path that answers 200, and that liveness chips read "hosted".
import { chromium } from "@playwright/test";
import { existsSync } from "node:fs";

const site = process.env.SITE_URL ?? "http://127.0.0.1:6170";
const hosted = await (await fetch(site + "/hosted.json")).json();
const pages = ["/", "/Learn/", "/CustomerSetup/", "/CustomerSetup/McLarenRacing/setup.html", "/CustomerSetup/RHB-Bank/setup.html"];

let exe;
try { exe = chromium.executablePath(); } catch { exe = ""; }
const browser = await chromium.launch(
  exe && existsSync(exe) ? {} : existsSync("/usr/bin/google-chrome") ? { executablePath: "/usr/bin/google-chrome" } : {},
);
const problems = [];
for (const p of pages) {
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const res = await page.goto(site + p, { waitUntil: "load" });
  if (!res || res.status() !== 200) { problems.push(`${p}: HTTP ${res && res.status()}`); continue; }
  await page.waitForTimeout(2500); // chips ping with a 2 s timeout
  const local = await page.locator('a[href^="http://localhost"], a[href^="http://127.0.0.1"]').count();
  if (local) problems.push(`${p}: ${local} link(s) still point at localhost`);
  const hrefs = await page.locator("a[href]").evaluateAll((as) => as.map((a) => a.href));
  const twinLinks = [...new Set(hrefs.map((h) => h.split("#")[0]))].filter((h) =>
    hosted.built.some((d) => h.endsWith("/" + d + "/")));
  for (const h of twinLinks) {
    const r = await fetch(h);
    if (r.status !== 200) problems.push(`${p}: ${h} -> ${r.status}`);
  }
  const chips = await page.locator(".chip").allInnerTexts();
  if (chips.some((c) => /^(running|not running|checking)/.test(c))) problems.push(`${p}: chip still says ${JSON.stringify(chips)}`);
  if (errors.length) problems.push(`${p}: ${errors.join("; ")}`);
  console.log(`${p}: ${twinLinks.length} hosted twin link(s), chips: ${[...new Set(chips)].join(" | ") || "none"}`);
  await page.close();
}
await browser.close();
if (problems.length) { console.error(problems.join("\n")); process.exit(1); }
console.log("static pages ok");
