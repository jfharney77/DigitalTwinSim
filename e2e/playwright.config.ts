import { defineConfig, chromium } from "@playwright/test";
import { existsSync } from "node:fs";

// Browser smoke tests for one component at a time. scripts/smoke.sh starts the
// component's backend + frontend and sets COMPONENT and BASE_URL; running this
// config directly works too if both servers are already up:
//   COMPONENT=GPU BASE_URL=http://localhost:5173 npx playwright test -c e2e
//
// The pinned @playwright/test (1.63.0) matches the cached chromium-1243 build in
// ~/.cache/ms-playwright. If that build is missing (a fresh machine that never
// ran `npx playwright install chromium`), fall back to the system Chrome.
function launchOptions() {
  const forced = process.env.SMOKE_CHROME;
  if (forced) return { executablePath: forced };
  let bundled = "";
  try {
    bundled = chromium.executablePath();
  } catch {
    bundled = "";
  }
  if (bundled && existsSync(bundled)) return {};
  if (existsSync("/usr/bin/google-chrome")) return { executablePath: "/usr/bin/google-chrome" };
  return {};
}

// Playwright empties outputDir when a run starts. One shared directory meant
// concurrent runs (several components smoke-tested at once) deleted each
// other's in-flight trace files, and passing tests failed at
// browserContext.close with ENOENT. Each component now gets its own directory;
// SMOKE_OUTPUT overrides it (smoke.sh passes its per-component path).
const outputDir =
  process.env.SMOKE_OUTPUT ?? `test-results/${process.env.COMPONENT ?? "unnamed"}`;

// SMOKE_TRACE=off|on|retain-on-failure (default) — traces are written only on
// failure, but an operator can switch them off entirely.
type TraceMode = "off" | "on" | "retain-on-failure" | "on-first-retry";
const trace = (process.env.SMOKE_TRACE as TraceMode | undefined) ?? "retain-on-failure";

export default defineConfig({
  testDir: ".",
  testMatch: "smoke.spec.ts",
  outputDir,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:5173",
    viewport: { width: 1440, height: 900 },
    launchOptions: launchOptions(),
    trace,
  },
});
