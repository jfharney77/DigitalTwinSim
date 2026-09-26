import { test, expect, type Page } from "@playwright/test";
import { readFileSync, mkdirSync } from "node:fs";
import { join, resolve } from "node:path";

// Generic, data-driven browser smoke test. Everything component-specific lives
// in <Component>/frontend/smoke.json; the schema is documented in e2e/README.md.

type Play = { click: string; watch: string; times?: number };
type Route = {
  hash: string;
  name?: string;
  svg?: boolean;
  visible?: string[];
  text?: string[];
  play?: Play;
  ignoreConsole?: string[];
};
type Manifest = { routes: Route[]; ignoreConsole?: string[]; ignoreApi?: string[] };

// Playwright transpiles specs as CommonJS here (the root package.json has no
// "type": "module"), so __dirname is the e2e/ directory.
const here = __dirname;
const repo = resolve(here, "..");
const component = process.env.COMPONENT;
if (!component) throw new Error("set COMPONENT=<Dir> (scripts/smoke.sh does this)");
const manifestPath = process.env.SMOKE_MANIFEST
  ? resolve(process.env.SMOKE_MANIFEST)
  : join(repo, component, "frontend", "smoke.json");
const manifest: Manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
if (!Array.isArray(manifest.routes) || manifest.routes.length === 0) {
  throw new Error(`${manifestPath}: "routes" must be a non-empty array`);
}

// Text that only appears when a page has fallen over: the ErrorBoundary card
// (GPU) and the `.an-error` line every twin page renders when a fetch fails.
const FALLBACK_TEXT = /view hit an error|something went wrong/i;
const FALLBACK_SELECTOR = ".an-error";

function routeName(r: Route): string {
  if (r.name) return r.name;
  const h = r.hash.replace(/^#/, "").replace(/[^A-Za-z0-9_-]+/g, "_");
  return h || "root";
}

function collect(page: Page, ignoreApi: RegExp[]) {
  const problems: string[] = [];
  page.on("pageerror", (err) => problems.push(`uncaught page error: ${err.message}`));
  page.on("console", (msg) => {
    // The source URL rides along so ignoreConsole can target e.g. a hotlinked
    // image host that is unreachable offline ("Failed to load resource" alone
    // does not name the resource).
    const at = msg.location()?.url;
    if (msg.type() === "error") problems.push(`console.error: ${msg.text()}${at ? ` (at ${at})` : ""}`);
  });
  const isApi = (url: string) => /^(\/[^/]+)?\/api(-static)?\//.test(new URL(url).pathname);
  page.on("response", (res) => {
    const url = res.url();
    if (isApi(url) && res.status() >= 400 && !ignoreApi.some((re) => re.test(url))) {
      problems.push(`api ${res.status()}: ${res.request().method()} ${url}`);
    }
  });
  page.on("requestfailed", (req) => {
    const url = req.url();
    const why = req.failure()?.errorText ?? "failed";
    // Aborts happen when a test ends with an open stream (SSE); not a fault.
    if (isApi(url) && !/ERR_ABORTED|aborted/i.test(why) && !ignoreApi.some((re) => re.test(url))) {
      problems.push(`api request failed (${why}): ${req.method()} ${url}`);
    }
  });
  return problems;
}

for (const route of manifest.routes) {
  const name = routeName(route);
  // The title carries the route's name when it has one, so two routes on the
  // same hash (two checks of the landing page) do not collide as duplicates.
  const title = `${component} ${route.hash || "/"}${route.name ? ` (${route.name})` : ""}`;
  test(title, async ({ page }) => {
    const ignoreApi = (manifest.ignoreApi ?? []).map((s) => new RegExp(s));
    // The skin's webfont is hotlinked from Google Fonts. On a machine with no
    // internet the stylesheet fails and the page renders in the fallback font —
    // a fact about the network, not about the twin, so it is not a smoke failure.
    const ignoreConsole = ["fonts\\.googleapis\\.com", ...(manifest.ignoreConsole ?? []),
                           ...(route.ignoreConsole ?? [])].map(
      (s) => new RegExp(s),
    );
    const problems = collect(page, ignoreApi);

    // SMOKE_PATH: the sub-path a statically hosted twin lives under (scripts/smoke_static.sh).
    await page.goto((process.env.SMOKE_PATH ?? "/") + route.hash, { waitUntil: "load" });

    // Wait for the manifest's anchors first: they are the "page has rendered" signal.
    for (const sel of route.visible ?? []) {
      await expect(page.locator(sel).first(), `visible: ${sel}`).toBeVisible();
    }
    for (const t of route.text ?? []) {
      await expect(page.getByText(t, { exact: false }).first(), `text: ${t}`).toBeVisible();
    }
    // Let in-flight fetches settle; SSE-backed pages never go idle, so cap it.
    await page.waitForLoadState("networkidle", { timeout: 5_000 }).catch(() => {});
    await page.waitForTimeout(300);

    const bodyText = (await page.locator("body").innerText()).trim();
    expect(bodyText.length, "page body is empty").toBeGreaterThan(20);

    await expect(page.getByText(FALLBACK_TEXT), "error fallback is showing").toHaveCount(0);
    const visibleErrors = await page.locator(FALLBACK_SELECTOR).filter({ visible: true }).allInnerTexts();
    expect(visibleErrors, `${FALLBACK_SELECTOR} is showing`).toEqual([]);

    if (route.svg) {
      // A diagram, not an icon: at least one visible <svg> of real size.
      const big = await page.locator("svg").evaluateAll((els) =>
        els.some((el) => {
          const r = el.getBoundingClientRect();
          return r.width >= 100 && r.height >= 80;
        }),
      );
      expect(big, "expected a diagram <svg> (>=100x80) on this page").toBe(true);
    }

    if (route.play) {
      const watch = page.locator(route.play.watch).first();
      await expect(watch, `play.watch: ${route.play.watch}`).toBeVisible();
      const before = await watch.innerText();
      const click = page.locator(route.play.click).first();
      for (let i = 0; i < (route.play.times ?? 1); i++) {
        await click.click();
        await page.waitForTimeout(150);
      }
      await expect
        .poll(() => watch.innerText(), { message: `play: "${route.play.watch}" never changed from "${before}"` })
        .not.toBe(before);
    }

    const out = process.env.SMOKE_ARTIFACTS ?? join(here, "artifacts", component!);
    mkdirSync(out, { recursive: true });
    // Twin pages scroll inside a container rather than the document, which
    // fullPage cannot see — so grow the viewport to the tallest scroller first.
    const tall = await page.evaluate(() => {
      let h = document.documentElement.scrollHeight;
      for (const el of Array.from(document.querySelectorAll<HTMLElement>("body *"))) {
        const o = getComputedStyle(el).overflowY;
        if ((o === "auto" || o === "scroll") && el.scrollHeight > el.clientHeight) {
          h = Math.max(h, el.scrollHeight + el.getBoundingClientRect().top);
        }
      }
      return Math.ceil(h);
    });
    const vp = page.viewportSize()!;
    if (tall > vp.height) await page.setViewportSize({ width: vp.width, height: Math.min(tall, 8000) });
    await page.screenshot({ path: join(out, `${name}.png`), fullPage: true });

    const real = problems.filter((p) => !ignoreConsole.some((re) => re.test(p)));
    expect(real, "page errors / console errors / failed /api requests").toEqual([]);
  });
}
