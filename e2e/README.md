# Browser smoke tests

One generic Playwright spec (`smoke.spec.ts`) loads every route a component
lists in its `<Component>/frontend/smoke.json` and fails the route when the
page is broken. A component opts in by adding that file; it writes no test code.

## Running

```
scripts/smoke.sh GPU                 # start backend + frontend, run the spec, stop both
scripts/smoke.sh GPU --keep          # same, then leave the servers up to poke at
scripts/smoke.sh --all               # every reference/built/partial component, then a table
npm run smoke -- DellPowerEdgeR760   # the same script through npm
```

`smoke.sh` reads the ports from `components.json`, starts the backend with
`.venv/bin/python -m uvicorn app.main:app` (creating the venv from
`requirements.txt` if it has none) and the frontend with
`npx vite --port <frontendPort> --strictPort` with `API_TARGET` aimed at the
backend. It waits for `/api/health` and the Vite index, runs the spec with
`COMPONENT` and `BASE_URL` set, and kills both process trees on exit.

If something unrelated already holds a registry port, the run stops with
"port N is already in use". For a single component you can move it aside:

```
SMOKE_BACKEND_PORT=8090 SMOKE_FRONTEND_PORT=5290 scripts/smoke.sh GPU
```

With both servers already running (for example from `scripts/dev.sh`), you
can run the spec on its own:

```
COMPONENT=GPU BASE_URL=http://localhost:5173 npx playwright test -c e2e/playwright.config.ts
```

`SMOKE_MANIFEST=path/to/other.json` swaps in a different manifest, and
`SMOKE_CHROME=/usr/bin/google-chrome` forces a browser binary.
`@playwright/test` is pinned to 1.63.0 because that release uses the
`chromium-1243` build cached in `~/.cache/ms-playwright`. If that build is
missing, the config falls back to `/usr/bin/google-chrome`.

## Output

- `e2e/artifacts/<Component>/<route>.png`: a screenshot of each route. The
  viewport is grown to the tallest scrolling container first, because twin
  pages scroll inside the layout rather than the document.
- `e2e/artifacts/<Component>/backend.log`, `frontend.log`: server output.
  Read these first after a startup failure.
- `e2e/test-results/<Component>/`: Playwright traces for failed tests. Open
  one with `npx playwright show-trace e2e/test-results/<Component>/<dir>/trace.zip`.

Playwright empties its output directory at the start of every run, so each
component gets its own. Runs for different components can therefore overlap
(several agents or CI shards on one machine) without deleting each other's
trace files. Before this, overlapping runs failed passing tests at
`browserContext.close` with `ENOENT ... .playwright-artifacts-N/traces/...`;
if you see that error, something is still sharing a directory.
`SMOKE_OUTPUT=<dir>` picks the directory explicitly, `SMOKE_TRACE=off` turns
traces off, and anything after `--` goes straight to `playwright test`:

```
scripts/smoke.sh DellPowerStore -- --grep tour
```

All three directories are gitignored.

## What fails a route

Every route is checked for:

- an uncaught page error (`pageerror`)
- any `console.error`, which includes React key warnings and failed resource loads
- any `/api/...` response with status >= 400, or an `/api/` request that fails
  outright (aborted streams are not counted)
- a visible `.an-error` line (every twin renders one when a fetch fails) or
  ErrorBoundary text ("... view hit an error", "something went wrong")
- a body with fewer than 20 characters of text

The manifest can add more checks per route (below). Problems are gathered over
the whole test and reported together at the end, one per line, for example
`api 500: GET http://127.0.0.1:5174/api/poweron` or
`console.error: Warning: Each child in a list ... (at http://.../App.tsx)`.

## Manifest schema: `<Component>/frontend/smoke.json`

```json
{
  "routes": [
    {
      "hash": "",
      "name": "poweron",
      "svg": true,
      "visible": [".phase"],
      "text": ["Telemetry"],
      "play": { "click": "button:text-is('Step')", "watch": ".phase", "times": 2 },
      "ignoreConsole": []
    },
    { "hash": "#anatomy", "name": "anatomy", "svg": true, "text": ["Overview"] }
  ],
  "ignoreConsole": [],
  "ignoreApi": []
}
```

| Field | Required | Meaning |
|---|---|---|
| `routes` | yes | Non-empty list. Each route becomes one test, loaded fresh at `BASE_URL/` + `hash`. |
| `routes[].hash` | yes | `""` for the landing page, otherwise the hash with its `#` (`"#anatomy"`, `"#usecases"`, `"#live/tour"`). |
| `routes[].name` | no | Screenshot file name. Defaults to the hash with unsafe characters replaced, or `root`. |
| `routes[].svg` | no | `true` requires at least one visible `<svg>` of at least 100×80 px, so a diagram and not just an icon. Set it on diagram pages. |
| `routes[].visible` | no | CSS/Playwright selectors, each of which must match a visible element. These are also the "page has rendered" wait, with a 15 s limit per item. |
| `routes[].text` | no | Strings that must appear visibly on the page (substring match, first match used). Use headings that only exist once data has loaded. |
| `routes[].play` | no | Interaction check. Reads the text of `watch`, clicks `click` `times` times (default 1, 150 ms apart), then requires `watch`'s text to change. |
| `routes[].ignoreConsole` | no | Regexes; a problem line matching one is ignored for this route. |
| `ignoreConsole` | no | The same, for every route. The match runs against the whole problem line, including its `(at <url>)` suffix. |
| `ignoreApi` | no | Regexes matched against the URL of a failing `/api` request; matches are not reported. |

Add every `ignore*` entry with a comment in your report explaining why. They
exist for failures outside the app, like a hotlinked image host that is
unreachable offline, and should not be used to hide app bugs.

## Writing a manifest: what works

- Playback controls come from the shared `ControlPanel` in `packages/twin-ui`.
  Every trace twin therefore has a `button:text-is('Step')` and a `.phase` status line,
  so the `play` block above works unchanged on most twins. Physics apps have
  their own controls. Check their markup before copying it.
- `text` and `visible` are the waits. Without them the checks run once the
  `load` event fires, plus up to 5 s of network idle, and a page that fetches
  late could pass while still empty. Name something that only renders after
  the fetch returns.
- Pages holding an SSE stream (GPU `#live`) never reach network idle. The spec
  gives up after 5 s and carries on, which is expected.
- One route takes 1–2 s once the servers are up. Startup takes 5–15 s when the
  venv exists, and a minute or more when it has to be built.
- Anchor only on content every checkout has. Anything built from gitignored
  runtime data (GPU's `#live` recordings list, read from `backend/sessions/`)
  is empty on a fresh clone or a CI runner.
- `text` uses the first match, and an SVG `<title>` tooltip counts as a match
  that is never visible. Pick strings that do not also appear in a diagram's
  hover titles.
- Each test's title is the hash plus the route's `name`, so two routes on the
  same hash need different `name`s.
- `--all` treats a component without a manifest as "no manifest", not a failure.
  A startup failure is reported as "FAIL (startup)", separate from a test failure.
- Several agents running smoke at once should keep their own scratch files
  (explore scripts, logs, screenshots) in a per-component directory; the
  harness's own output is already per component.
- Stop `--keep` with Ctrl-C in the foreground, or with `kill -TERM <smoke.sh pid>`.
  Find the pid with `pgrep -f '[s]moke.sh DellPowerStore'`; a plain
  `pkill -f 'smoke.sh DellPowerStore'` also matches, and kills, the shell running it.
  SIGINT sent to a background job is ignored by bash. If `smoke.sh` is killed with
  SIGKILL, its servers are left running on the component's ports.
