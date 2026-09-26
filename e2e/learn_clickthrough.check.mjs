// Learn click-through against the hosted site: no backend, no vite, just the
// files scripts/build_site.sh wrote. Run by scripts/smoke_static.sh, or on its
// own:
//
//   python3 -m http.server 6170 --directory site &
//   SITE_URL=http://127.0.0.1:6170 node e2e/learn_clickthrough.check.mjs
//
// What it asserts, module page by module page:
//   - the page loads with no page error and renders its prediction,
//   - every lab stop renders and its "#lab=<id>" link resolves to a hosted
//     twin page that answers 200 (or is disabled, if that twin is not hosted),
//   - the Labs track lists exactly the modules that carry a lab, and a labs
//     stop can be marked passed (the reader's own progress, in localStorage),
//   - the capstone's coupled chain renders with its chain and seam links,
//   - the "What goes wrong" track still renders its failure stops.
//
// The course's own integrity (ids, ports, quoted numbers) is pinned by
// pytest Learn. This file only asks whether a reader can actually click it.
import { chromium } from "@playwright/test";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const site = process.env.SITE_URL ?? "http://127.0.0.1:6170";
const repo = join(dirname(fileURLToPath(import.meta.url)), "..");
const hosted = await (await fetch(site + "/hosted.json")).json();

const courseJs = readFileSync(join(repo, "Learn", "course.js"), "utf8");
const course = JSON.parse(courseJs.slice(courseJs.indexOf("window.COURSE = ") + 16).trim().replace(/;$/, ""));
const labModules = course.modules.filter((m) => m.lab);
const capstone = course.modules.filter((m) => m.core).at(-1);

let exe;
try { exe = chromium.executablePath(); } catch { exe = ""; }
const browser = await chromium.launch(
  exe && existsSync(exe) ? {} : existsSync("/usr/bin/google-chrome") ? { executablePath: "/usr/bin/google-chrome" } : {},
);
const problems = [];
const seen = new Map(); // resolved href -> status, so each twin page is fetched once

async function open(path) {
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => { if (m.type() === "error") errors.push("console: " + m.text()); });
  const res = await page.goto(site + path, { waitUntil: "load" });
  if (!res || res.status() !== 200) problems.push(`${path}: HTTP ${res && res.status()}`);
  await page.waitForTimeout(300);
  return { page, errors };
}

async function checkResolved(where, page) {
  // twin-hosted.js rewrites localhost links; anything left is a bug in the
  // resolver or a link the builder could not place.
  const stillLocal = await page.locator('a[href^="http://localhost"]').count();
  if (stillLocal) problems.push(`${where}: ${stillLocal} link(s) still point at localhost`);
  const hrefs = await page.locator("a[href]").evaluateAll((as) => as.map((a) => a.href));
  for (const h of [...new Set(hrefs)]) {
    const base = h.split("#")[0];
    if (!hosted.built.some((d) => base.endsWith("/" + d + "/"))) continue;
    if (!seen.has(base)) seen.set(base, (await fetch(base)).status);
    if (seen.get(base) !== 200) problems.push(`${where}: ${base} -> ${seen.get(base)}`);
  }
}

// ---- the home page, and every track it offers ------------------------------
{
  const { page, errors } = await open("/Learn/");
  const tracks = await page.locator("a.track").count();
  if (tracks !== course.tracks.length) problems.push(`home: ${tracks} track cards, course.js has ${course.tracks.length}`);
  await checkResolved("home", page);
  if (errors.length) problems.push(`home: ${errors.join("; ")}`);
  await page.close();
}

// ---- the Labs track: its home listing, then every stop ---------------------
{
  const { page, errors } = await open("/Learn/index.html#track=labs");
  const listed = await page.locator("ul.modules li.module a").allInnerTexts();
  const want = labModules.map((m) => m.title);
  if (JSON.stringify(listed) !== JSON.stringify(want)) {
    problems.push(`labs track lists ${JSON.stringify(listed)}, expected ${JSON.stringify(want)}`);
  }
  if (errors.length) problems.push(`labs home: ${errors.join("; ")}`);
  await page.close();
}

for (const m of labModules) {
  const path = `/Learn/modules/${m.id.toLowerCase()}.html#track=labs`;
  const { page, errors } = await open(path);
  const lab = page.locator("section.lab");
  if ((await lab.count()) !== 1) problems.push(`${m.id}: the labs stop renders ${await lab.count()} lab sections`);
  else {
    const href = await lab.locator("a.entry-link").first().getAttribute("href");
    const disabled = await lab.locator("a[data-twin-unhosted], [data-twin-unhosted]").count();
    if (href) {
      if (!href.includes(`#lab=${m.lab.id}`)) problems.push(`${m.id}: lab link is ${href}, expected #lab=${m.lab.id}`);
    } else if (!disabled) {
      problems.push(`${m.id}: lab link has no href and is not marked unhosted`);
    }
    // Mark it passed: the stop must then report itself finished.
    await lab.locator("button", { hasText: /I passed this lab|Passed/ }).first().click();
    const done = await page.locator("p.done-line").first().innerText();
    if (!/finished/i.test(done)) problems.push(`${m.id}: marking the lab passed left "${done}"`);
  }
  await checkResolved(m.id + " (labs)", page);
  if (errors.length) problems.push(`${m.id} (labs): ${errors.join("; ")}`);
  await page.close();
}

// ---- the whole course: every module page, on its own track -----------------
for (const m of course.modules) {
  const path = `/Learn/modules/${m.id.toLowerCase()}.html`;
  const { page, errors } = await open(path);
  // The module's own prediction, not a failure stop (which reuses the class).
  const predict = page.locator("section.predict:not(.failure)").first();
  if ((await predict.count()) < 1) problems.push(`${m.id}: no prediction rendered`);
  const options = await predict.locator(".option").count();
  if (options < 3) problems.push(`${m.id}: ${options} prediction options`);
  // Commit an answer: that is what unlocks the twin links for a reader.
  await predict.locator(".option").first().click();
  await predict.locator("button.primary").click();
  // Only the "Play it" links unlock here: a failure stop keeps its own link
  // shut until the reader commits to that stop's question.
  const locked = await page.locator("section.play a.entry-link.locked").count();
  if (locked) problems.push(`${m.id}: ${locked} twin link(s) still locked after committing`);
  if (m.lab && (await page.locator("section.lab").count()) !== 1) problems.push(`${m.id}: lab section missing from the whole module`);
  if (m.couplings) {
    const chain = page.locator("section.coupling a.entry-link");
    if ((await chain.count()) < 2) problems.push(`${m.id}: the coupled chain needs a chain link and a seam link`);
    const hrefs = await chain.evaluateAll((as) => as.map((a) => a.getAttribute("href") || ""));
    const unhosted = await page.locator("section.coupling [data-twin-unhosted]").count();
    if (!unhosted && !hrefs.some((h) => h.includes(`#chain=${m.couplings.chain}`))) {
      problems.push(`${m.id}: no link to #chain=${m.couplings.chain} (got ${JSON.stringify(hrefs)})`);
    }
  }
  await checkResolved(m.id, page);
  if (errors.length) problems.push(`${m.id}: ${errors.join("; ")}`);
  await page.close();
}

// ---- the failure track still works ----------------------------------------
{
  const wgw = course.tracks.find((t) => t.failuresOnly);
  const first = wgw.steps[0].module.toLowerCase();
  const { page, errors } = await open(`/Learn/modules/${first}.html#track=${wgw.id}`);
  if ((await page.locator("section.failure").count()) < 1) problems.push(`${first}: no failure stop on the ${wgw.id} track`);
  if (errors.length) problems.push(`${first} (${wgw.id}): ${errors.join("; ")}`);
  await page.close();
}

await browser.close();
if (problems.length) {
  console.error(problems.join("\n"));
  process.exit(1);
}
console.log(`learn click-through ok: ${course.modules.length} module pages, ${labModules.length} lab stops, ` +
            `capstone ${capstone.id} coupled chain, ${seen.size} hosted twin page(s) fetched`);
