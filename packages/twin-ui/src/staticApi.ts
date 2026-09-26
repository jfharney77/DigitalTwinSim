/**
 * staticApi — the fetch shim that lets a twin run with no backend.
 *
 * A twin's api.ts calls `apiFetch` where it called `fetch`. In a normal build
 * that *is* `fetch`. In a static build (`VITE_STATIC=1 vite build --base=./`,
 * see docs/STATIC_HOSTING.md) requests to `/api/...` are answered from what
 * scripts/build_static.py wrote beside the bundle:
 *
 *   GET  /api/poweron?level=3&scenario=x -> api-static/poweron/level-3__scenario-x.json
 *   POST /api/simulate {body}            -> api-static/_post/simulate/<key>.json when the
 *                                           body was prebaked, otherwise the component's
 *                                           real engine.py, run in a Pyodide web worker
 *
 * The naming (`safe`, `queryName`, `bodyKey`) mirrors scripts/build_static.py
 * and twinkit/static_dispatch.py. Change one side, change the other.
 *
 * `hostedHref` is the cross-twin link resolver: localhost ports in dev,
 * sibling paths on the hosted site.
 */

const env = ((import.meta as unknown as { env?: Record<string, string | undefined> }).env ?? {});

/** True in a build made for static hosting. */
export const isStatic: boolean = env.VITE_STATIC === "1" || env.VITE_STATIC === "true";

const PYODIDE_URL: string = env.VITE_PYODIDE_URL ?? "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/";

function siteUrl(rel: string): string {
  return new URL(rel, document.baseURI).href;
}

function safe(value: string): string {
  return value.replace(/[^A-Za-z0-9._-]/g, "_");
}

function queryName(query: Record<string, string>): string {
  const keys = Object.keys(query).sort();
  if (keys.length === 0) return "_";
  return keys.map((k) => `${safe(k)}-${safe(query[k])}`).join("__");
}

function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    const src = value as Record<string, unknown>;
    const out: Record<string, unknown> = {};
    for (const k of Object.keys(src).sort()) if (src[k] !== undefined) out[k] = canonical(src[k]);
    return out;
  }
  return value;
}

/** FNV-1a 32-bit over the canonical JSON's UTF-16 code units. */
export function bodyKey(body: unknown): string {
  const text = JSON.stringify(canonical(body));
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(16).padStart(8, "0");
}

type StaticIndex = {
  get: Record<string, string[]>;
  post: Record<string, string[]>;
  engine: boolean;
};

let indexPromise: Promise<StaticIndex> | null = null;
function loadIndex(): Promise<StaticIndex> {
  indexPromise ??= fetch(siteUrl("api-static/index.json")).then((r) => {
    if (!r.ok) throw new Error(`api-static/index.json ${r.status} — was scripts/build_static.py run?`);
    return r.json();
  });
  return indexPromise;
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// ---- the in-browser engine --------------------------------------------------

// A classic worker built from a string: it loads Pyodide with importScripts,
// so no bundler worker configuration is needed in any of the twins.
const WORKER_SOURCE = `
let ready = null;
async function boot(cfg) {
  importScripts(cfg.pyodideUrl + "pyodide.js");
  postMessage({ progress: "Starting Python" });
  const pyodide = await loadPyodide({ indexURL: cfg.pyodideUrl });
  postMessage({ progress: "Loading pydantic" });
  await pyodide.loadPackage(["pydantic"]);
  postMessage({ progress: "Loading the simulator engine" });
  const zip = await (await fetch(cfg.bundleUrl)).arrayBuffer();
  pyodide.unpackArchive(zip, "zip", { extractDir: "/twin" });
  pyodide.runPython(
    "import sys\\n" +
    "sys.path.insert(0, '/twin')\\n" +
    "from twinkit.fastapi_stub import install\\n" +
    "install()\\n" +
    "from twinkit.static_dispatch import dispatch_json\\n" +
    "from app.main import app as _app\\n" +
    "def _handle(method, path, query, body):\\n" +
    "    return dispatch_json(_app, method, path, query, body)\\n"
  );
  return pyodide.globals.get("_handle");
}
onmessage = async (e) => {
  const m = e.data;
  try {
    if (!ready) ready = boot(m.cfg);
    const handle = await ready;
    const out = handle(m.method, m.path, m.query, m.body === null ? undefined : m.body);
    postMessage({ id: m.id, result: out });
  } catch (err) {
    postMessage({ id: m.id, error: String(err && err.message ? err.message : err) });
  }
};
`;

let worker: Worker | null = null;
let nextId = 1;
const pending = new Map<number, { resolve: (s: string) => void; reject: (e: Error) => void }>();
let engineReady = false;

function notice(text: string | null): void {
  const id = "twin-static-engine-note";
  let el = document.getElementById(id);
  if (text === null) {
    el?.remove();
    return;
  }
  if (!el) {
    el = document.createElement("div");
    el.id = id;
    el.setAttribute("role", "status");
    el.style.cssText =
      "position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:1000;" +
      "background:#fff;color:#0e0e0e;border:1px solid #c8c9c7;border-radius:4px;" +
      "padding:10px 16px;font:14px Roboto,Arial,sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.15)";
    document.body.appendChild(el);
  }
  el.textContent = text;
}

function engineCall(method: string, path: string, query: Record<string, string>, body: string | null): Promise<string> {
  if (!worker) {
    const blob = new Blob([WORKER_SOURCE], { type: "text/javascript" });
    worker = new Worker(URL.createObjectURL(blob));
    worker.onmessage = (e: MessageEvent) => {
      const m = e.data as { id?: number; result?: string; error?: string; progress?: string };
      if (m.progress) {
        if (!engineReady) {
          notice(`${m.progress} — the simulator runs in your browser on this site. One-time download, about 15 MB.`);
        }
        return;
      }
      engineReady = true;
      notice(null);
      const p = pending.get(m.id!);
      if (!p) return;
      pending.delete(m.id!);
      if (m.error !== undefined) p.reject(new Error(m.error));
      else p.resolve(m.result!);
    };
    worker.onerror = (e) => {
      notice("The in-browser simulator could not start. Check the network connection and reload.");
      for (const p of pending.values()) p.reject(new Error(e.message || "engine worker failed"));
      pending.clear();
    };
  }
  const id = nextId++;
  const cfg = { pyodideUrl: PYODIDE_URL, bundleUrl: siteUrl("py/bundle.zip") };
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    worker!.postMessage({ id, cfg, method, path, query: JSON.stringify(query), body });
  });
}

/** Start the engine download before the first uncached request needs it. */
export function warmEngine(): void {
  if (!isStatic) return;
  loadIndex().then((ix) => {
    if (ix.engine) engineCall("GET", "/api/health", {}, null).catch(() => {});
  }).catch(() => {});
}

// Engines are pure: the same body always gets the same answer.
const engineCache = new Map<string, string>();
const ENGINE_CACHE_MAX = 24;

async function staticFetch(input: string, init?: RequestInit): Promise<Response> {
  const u = new URL(input, "http://twin.invalid");
  const path = u.pathname;
  const query: Record<string, string> = {};
  u.searchParams.forEach((v, k) => { query[k] = v; });
  const method = (init?.method ?? "GET").toUpperCase();
  const index = await loadIndex();

  if (method === "GET") {
    const accepted = index.get[path];
    if (accepted) {
      // Drop parameters the route never declared, as the backend would.
      const kept: Record<string, string> = {};
      for (const k of accepted) if (k in query) kept[k] = query[k];
      const rel = path.slice("/api/".length) || "_root";
      const r = await fetch(siteUrl(`api-static/${rel}/${queryName(kept)}.json`));
      if (r.ok) return r;
      return jsonResponse(404, { detail: `no static snapshot for ${input}` });
    }
  }

  const bodyText = typeof init?.body === "string" ? init.body : null;
  if (method === "POST" && bodyText !== null) {
    const keys = index.post[path] ?? [];
    const key = bodyKey(JSON.parse(bodyText));
    if (keys.includes(key)) {
      const r = await fetch(siteUrl(`api-static/_post/${path.slice("/api/".length)}/${key}.json`));
      if (r.ok) return r;
    }
  }
  if (!index.engine) return jsonResponse(404, { detail: `${method} ${path} is not available on the hosted site` });

  const cacheKey = `${method} ${path} ${JSON.stringify(query)} ${bodyText ?? ""}`;
  let raw = engineCache.get(cacheKey);
  if (raw === undefined) {
    raw = await engineCall(method, path, query, bodyText);
    if (engineCache.size >= ENGINE_CACHE_MAX) engineCache.delete(engineCache.keys().next().value as string);
    engineCache.set(cacheKey, raw);
  }
  const parsed = JSON.parse(raw) as { status: number; body: unknown };
  return jsonResponse(parsed.status, parsed.body);
}

/**
 * Drop-in for `fetch` in a twin's api.ts. Anything that is not a same-origin
 * `/api/` request, and everything in a normal build, goes to `fetch` untouched.
 */
export function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  if (!isStatic || !input.startsWith("/api/")) return fetch(input, init);
  return staticFetch(input, init);
}

/**
 * A public-folder asset ("/photo.webp") addressed so it also works under a
 * sub-path. API payloads are already rewritten by build_static.py; this is for
 * paths written in frontend code.
 */
export function assetUrl(path: string): string {
  if (!isStatic || !path.startsWith("/") || path.startsWith("//")) return path;
  return siteUrl(path.slice(1));
}

/**
 * Link to another twin: `http://localhost:<port>/<hash>` in dev, the sibling
 * directory on the hosted site (`../<Directory>/<hash>`).
 */
export function hostedHref(directory: string, devPort: number, hash = ""): string {
  if (isStatic) return siteUrl(`../${directory}/${hash}`);
  return `http://localhost:${devPort}/${hash}`;
}

// A handle for checks and the console on the hosted site
// (e2e/static_engine.check.mjs posts a body through it). Static builds only.
if (isStatic && typeof window !== "undefined") {
  (window as unknown as { __twinStatic?: unknown }).__twinStatic = { apiFetch, bodyKey };
}
