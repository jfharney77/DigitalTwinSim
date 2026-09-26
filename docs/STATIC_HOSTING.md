# Static hosting: the twins with no backend

The whole tutorial — root `index.html`, `Learn/`, `CustomerSetup/`, and every
twin frontend — can be served as plain files from GitLab or GitHub Pages.
No uvicorn, no vite, no server code.

    scripts/build_site.sh            # assembles site/ (gitignored)
    scripts/smoke_static.sh          # serves site/ with python -m http.server, runs the smoke manifests

Piloted on `DellPowerStore` (narrative, GET-only) and `PhysicsME5`
(scenario-driven, `POST /api/simulate`); **all 43 components now follow the
recipe below and build**, `compose` included. A component that has not been
through the recipe is skipped by `build_site.sh` and hosted pages disable links
to it rather than breaking them, so adding the 44th changes nothing here.

What the hosted build cannot do — the GPU live tab, `compose`'s custom chains —
is listed under "Degraded on the hosted site" at the end of this file.

## How it works

One shared mechanism, two ways a request gets answered.

**`apiFetch`** (`packages/twin-ui/src/staticApi.ts`) replaces `fetch` in a
twin's `api.ts`. In a normal build it is `fetch`. In a static build
(`VITE_STATIC=1`) a request to `/api/...` never leaves the page's own origin:

| Request | Answered by |
|---|---|
| `GET /api/poweron?level=3&scenario=x` | `api-static/poweron/level-3__scenario-x.json`, written at build time |
| `POST /api/simulate` with a body known at build time | `api-static/_post/simulate/<key>.json` |
| `POST /api/simulate` with any other body | the component's real `engine.py`, run in the browser by Pyodide |

**Snapshots** come from `scripts/build_static.py <Component>`. It re-executes
under the component's `.venv`, imports `app.main`, and walks every `GET` route
under `/api`: each query parameter is either enumerated (`level` → 1–5;
`scenario` → the ids `GET /api/scenarios` lists; anything in `static.json`) or
left at its default, and every combination — including "parameter omitted" —
is written. Root-absolute asset paths in payloads (`/powerstore1.webp`) that
name a file in `frontend/public/` are made relative, because the site lives
under a sub-path.

**The in-browser engine.** Engines are pure Python, so the physics apps do not
fall back to a pre-computed grid: they run the same `engine.py`, validation and
leveling the backend runs. Any app with a `POST` route gets `py/bundle.zip`
(`backend/app/` + `twinkit/`, no tests). On the first request no snapshot can
answer, a web worker loads Pyodide from its CDN (pydantic ships with it),
unpacks the bundle, and answers through `twinkit.static_dispatch`. A small note
at the bottom of the page reports progress. Measured in the pilot: about 2.5 s
cold to the first answer, then milliseconds; answers are byte-identical to the
native engine (`e2e/static_engine.check.mjs` asserts it). Results are cached by
request body, since a pure engine cannot answer the same body differently.

Two pieces in `twinkit/` make that possible, and both are covered by
`twinkit/tests/test_static_dispatch.py`:

- `static_dispatch.py` calls route functions directly — find the route, coerce
  and bound-check the query, validate the body model, dump by alias. FastAPI's
  own request path runs sync endpoints in a thread pool, and Pyodide has no
  threads, so the ASGI app cannot be driven in the browser. `build_static.py`
  uses the same dispatcher natively (`--verify` diffs it against FastAPI's
  `TestClient`), so a snapshot is what the backend would have said.
- `fastapi_stub.py` stands in for `fastapi` under Pyodide. A `main.py` only
  uses FastAPI to *declare* routes; the stub remembers the declarations. This
  avoids a PyPI install on every first visit.

**Prebaked POSTs.** The builder looks inside the GET snapshots for objects that
validate as the POST body model under a key named `scenario` (the guided
scenarios) and answers them ahead of time, so opening a guided scenario is
instant and needs no Pyodide. Browser and builder agree on the file through
`bodyKey` — FNV-1a over key-sorted JSON — implemented in both
`staticApi.ts` and `static_dispatch.py` and pinned to the same value in the
tests. A miss is never an error; it falls through to the engine.

**Sub-path hosting.** Static builds use `vite build --base=./`, passed on the
command line — no `vite.config.ts` edit. A relative base makes the bundle
relocatable: `/<Component>/` on GitLab Pages, `/<repo>/<Component>/` on GitHub
Pages, same files. Hash routes are untouched. Everything the shim fetches is
resolved against `document.baseURI`.

**Links between things.** One resolver per side:

- In twin code, `hostedHref(directory, devPort, hash)` from twin-ui gives
  `http://localhost:<port>/<hash>` in dev and `../<Directory>/<hash>` hosted.
- The static pages (`index.html`, `Learn/`, `CustomerSetup/`) are *not edited*.
  `build_site.sh` copies them into `site/` and injects
  `scripts/static/twin-hosted.js` plus a `window.TWIN_HOSTED` map (from
  `components.json`). That script rewrites every `http://localhost:<port>/…`
  link — including ones `learn.js` and `index.html` create later — to the
  sibling path, answers the pages' liveness pings from the hosted files, and
  relabels chips: `running` → `hosted` (the step-count enrichment still works,
  read from the snapshot), `not running` → `not hosted`, start-command hints
  removed. Links to twins that are not static-ready lose their `href` and gain
  a tooltip.

## Per-component recipe

For one component `<C>`. Touch only `<C>/frontend/src/api.ts` and, if needed,
a new `<C>/frontend/static.json`. Do not edit shared files.

1. **api.ts**: add `import { apiFetch } from "@twinsim/twin-ui";` and replace
   every `fetch(` that targets `/api/...` with `apiFetch(`. Nothing else
   changes — `apiFetch` has `fetch`'s signature and returns a `Response`.
   `build_site.sh` detects readiness by grepping `api.ts` for `apiFetch`.
2. **Find fetches outside api.ts**: `grep -rn "fetch(\|EventSource\|/api/" <C>/frontend/src`.
   Route them through `apiFetch` too. `EventSource`/streaming cannot be served
   statically (see gotchas).
3. **Find absolute asset paths in frontend code**:
   `grep -rn "src=\"/\|url(/\|href=\"/" <C>/frontend/src <C>/frontend/index.html`.
   Paths inside API payloads are fixed by the builder; paths written in TSX
   need `assetUrl("/x.svg")` from twin-ui. Paths in `index.html` and CSS are
   handled by vite's `--base=./`.
4. **Find cross-twin links**: `grep -rn "localhost:" <C>/frontend/src`. Replace
   each with `hostedHref("<Directory>", <port>, "#hash")`.
5. **Snapshot and verify**:
   `python3 scripts/build_static.py <C> --verify --out /tmp/<C>-static`
   Read the `note:` lines. A query parameter it could not enumerate needs
   `<C>/frontend/static.json`:
   `{"params": {"product": ["alienware", "promax"], "formFactor": ["laptop", "tower"]}}`.
   `--verify` fails loudly if the dispatcher and FastAPI ever disagree.
6. **Build and check**:
   `scripts/build_site.sh <C>` then `scripts/smoke_static.sh <C>`
   (one port, 6170; `STATIC_PORT` overrides). The component's existing
   `frontend/smoke.json` is the test — it must pass unchanged with no backend.
   For an app with a POST route the script also runs the engine-parity check.
7. **Physics apps only**: open the hosted page, move a control, and confirm the
   progress note appears once and the instruments update. If the default
   first-paint body is not prebaked (first paint waits ~2.5 s for Pyodide),
   add it to `static.json` as `{"postBodies": {"/api/simulate": [{...}]}}` —
   copy the body the UI sends from the network tab of a dev run.

Done means: `build_static.py --verify` clean, `smoke_static.sh <C>` green,
`npm run build` in `<C>/frontend` still green, backend tests untouched.

## Gotchas

- **Generated output is never committed.** `dist-static/` and `/site/` are in
  `.gitignore`. CI builds them: `scripts/build_site.sh && mv site public`
  (GitLab Pages), or upload `site/` as the Pages artifact (GitHub). The job
  needs each built component's backend `.venv` (or `pip install -r
  requirements.txt` into one) and the root `npm ci`. `site/.nojekyll` is
  written so GitHub does not drop `_post/` and other underscore paths.
- **The file-naming contract has three copies**: `safe`/`queryName`/`bodyKey`
  in `staticApi.ts`, `safe`/`query_name` in `build_static.py`, `canonical`/
  `body_key` in `static_dispatch.py`. Query values are sanitized to
  `[A-Za-z0-9._-]`; two values differing only in other characters would
  collide. Scenario ids are kebab-case everywhere, so this has not bitten.
- **Parameters the route did not declare are dropped** by the shim, as the
  backend ignores them — api.ts files that append `?level=` to everything are
  fine. A value that was not enumerated (`?level=7`, an unknown scenario) gets
  a 404 JSON response, which the pages already render as their `.an-error`.
- **Path parameters are not snapshotted** (`/api/thing/{id}`); the builder
  prints a note. Prefer a query parameter, or list the ids in `static.json`
  once someone needs it — the builder has the hook but no pilot exercised it.
- **What the stub covers**: `FastAPI`, `get/post/put/delete/patch`, `Query`/
  `Path`/`Body`, `HTTPException`, `add_middleware`, the CORS import. A
  `main.py` that imports `Request`, `StreamingResponse`, `UploadFile`,
  `APIRouter`, or uses `Depends` will fail to import under Pyodide — extend
  `twinkit/fastapi_stub.py` (small, additive) or keep that route out of the
  static build with `static.json` `"skip"`. **GPU's live tab (SSE, session
  CRUD, file import) cannot be static**; its simulator, anatomy and tour tabs
  can, with the live routes skipped and the tab labeled.
- **Async endpoints** work for snapshots but not in the browser
  (`asyncio.run` inside Pyodide's loop). Every physics `main.py` checked so far
  is sync.
- **Anything an engine reads from disk at import** must live under
  `backend/app/` to be bundled (`.py`, `.json`, `.txt`, `.csv`, `.md`).
- **The first Pyodide load needs the network** (jsdelivr, ~15 MB, cached by the
  browser afterwards). `VITE_PYODIDE_URL` at build time points the worker at a
  self-hosted copy for air-gapped sites. `smoke_static.sh` therefore needs
  network for physics apps; the narrative twins do not.
- **Shared ports** (PowerMax and E3200 on 5178): the hosted resolver prefers a
  link's `data-twin-start` directory, then whichever of the two is hosted. A
  bare `http://localhost:5178/` link with no `data-twin-start` is ambiguous —
  add the attribute in the source page when you hit one.
- **`window.__twinStatic`** exists only in static builds: `{ apiFetch,
  bodyKey }`, for the parity check and for debugging from the console.
- **The smoke spec gained three env hooks**, all defaulting to the old
  behavior: `SMOKE_PATH` (sub-path to open), `SMOKE_ARTIFACTS` (screenshots go
  to `e2e/artifacts/static/<C>/`, so static runs do not overwrite live ones),
  and the failed-API detector now also watches `/<C>/api-static/`.

## Files

| File | Role |
|---|---|
| `packages/twin-ui/src/staticApi.ts` | `apiFetch`, `assetUrl`, `hostedHref`, `warmEngine`, the Pyodide worker |
| `twinkit/static_dispatch.py` | call routes as functions; `canonical`/`body_key` |
| `twinkit/fastapi_stub.py` | declaration-only `fastapi` for Pyodide |
| `scripts/build_static.py` | snapshot GETs, prebake POSTs, bundle the engine |
| `scripts/build_site.sh` | build each ready twin, assemble `site/`, inject the link resolver |
| `scripts/static/twin-hosted.js` | hosted link/chip resolver for the static pages |
| `scripts/static/native_answer.py` | native engine answer, for the parity check |
| `scripts/smoke_static.sh` | static server + smoke manifests + engine parity + pages check |
| `e2e/static_engine.check.mjs`, `e2e/static_pages.check.mjs` | the two extra checks |
| `e2e/learn_clickthrough.check.mjs` | the course clicked through on the hosted build: every module page, every lab stop, the Labs track, the capstone's coupled chain |

## Degraded on the hosted site

Everything else is the same page with the same numbers. These are the places
where a hosted visitor gets less than a local `scripts/dev.sh` run, verified on
the full 43-component build:

| Feature | Hosted behaviour |
|---|---|
| **GPU live co-browse** (`/api/live`, skipped in `GPU/frontend/static.json`) | No SSE stream, no session CRUD, no import, no `measurement` ingest — those need the local backend and a CUDA GPU. The tab still opens: it says so in as many words, the connection badge reads *Recorded only*, and the shipped lesson recordings and guided tours replay through the same pure fold. |
| **`compose` custom chains** (`POST /api/run/custom`, skipped) | The preset chains all run from snapshots. `postChain()` exists in `compose/frontend/src/api.ts` and nothing calls it yet, so today this costs a hosted reader nothing; wire an editor to it and the editor needs a backend or a Pyodide bundle. |
| **Path-parameter routes** | `GET /api/anatomy/{id}` (GPU, DellAlienware, PhysicsClient) and `GET /api/tour/recordings/{lesson_id}` (GPU) are not snapshotted; the builder prints a note. Every frontend deliberately reads the same payload out of the list endpoint instead, so no page depends on them. |
| **The first engine answer** | A body nobody prebaked waits for Pyodide: ~2.5 s cold, from the jsdelivr CDN, so the first such answer needs network. Guided scenarios and the labs' start scenarios are prebaked and instant; the answer is then byte-identical to the native engine and cached per body. `VITE_PYODIDE_URL` points the worker at a self-hosted copy for an air-gapped site. |
| **Grading a lab** | Same path as any other `POST`: the reference-quality bodies a learner builds are not prebaked, so the first *Run and grade* pays the Pyodide load once. The grade itself is the app's own pure `grade_scenario`, unchanged. |
| **Liveness chips on the static pages** | `running` → `hosted`, `not running` → `not hosted`, start-command hints removed. The step-count enrichment still works, read from the snapshot rather than a live trace. |
