# DellCloudIQ — spec

## 1. Purpose & scope

Teach a technically skilled reader who is *new to the product* what **CloudIQ**
is: Dell's cloud-native **AIOps observability SaaS** (rebranded **Dell AIOps**
and folded into APEX AIOps in 2024). What it monitors, how telemetry gets from
on-prem Dell systems to Dell's cloud (one-way, through the Secure Connect
Gateway), what the machine learning does with it (health scoring, anomaly
detection, capacity forecasting, cybersecurity, sustainability), how the
generative-AI AIOps Assistant fits, and what real workflows look like.

The twist versus the hardware twins: **CloudIQ is software, not a box.** There
is no chassis and no power-on. So, following the precedent set by the iDRAC
twin (functional block diagram + firmware bring-up) and the PowerSwitch twin
(boot trace):

- the shared **"anatomy" is a platform architecture diagram** — the
  telemetry-to-insight pipeline, laid out left (telemetry in) to right
  (insights out); and
- the **"power-on trace" is the lifecycle of a batch of telemetry becoming an
  actionable insight**, with the signature **Health Score** as the metric that
  moves.

Guardrails (mirror the repo's spirit):

- **Not a simulator of Dell's actual cloud.** Timings, data-point counts, and
  the Health Score are illustrative — the goal is a correct *mental model* of
  the pipeline, not measured behavior. CloudIQ collects on intervals and runs
  analytics periodically, not second-by-second.
- **The diagram is stylized**, a mental model of Dell's published AIOps
  architecture placed in a normalized 100×58 space. Not an internal system
  diagram.
- Content follows Dell's public AIOps material, written for someone with
  infrastructure background but no observability vocabulary — telemetry,
  Secure Connect Gateway, Health Score, anomaly detection, ITSM, RPO, and the
  AIOps Assistant are spelled out where they appear.

## 2. Architecture

Same split as the rest of the repo: a **pure FastAPI backend engine** and a
**React/Vite frontend** in the Dell clean-design skin.

- The backend emits the whole pipeline as a deterministic `PipelineState[]`
  trace — plain data, no timers, no IO in `engine.py`.
- The frontend fetches the trace and **owns the playback clock**
  (`setInterval` in `App.tsx`, never in the engine). Run/Step/Reset/Speed work
  exactly like the hardware twins; the heavy ML `analyze` stage has
  `cycleCost > 1` so the UI dwells on it.
- The platform architecture diagram, the capability catalog, and the use cases
  are **backend data** (`anatomy.py`, `catalog.py`, `usecases.py`), not
  frontend code. The SVG renderer (`PlatformView.tsx`) draws whatever it is
  sent.

```
backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
frontend/  src/{api,types}.ts, App.tsx (pipeline page + clock), components/
scripts/   start_backend.sh (:8007), start_frontend.sh (:5180), start_all.sh, stop_all.sh
```

Endpoints: `GET /api/health`, `/api/anatomy` (single `PlatformMap`),
`/api/pipeline` (`{trace: PipelineState[]}` — renamed from the hardware twins'
`/api/poweron`), `/api/catalog` (`CatalogCategory[]`), `/api/usecases`
(`UseCase[]`). Ports (8007/5180) are offset from the other twins so all can run
at once.

## 3. Data models (all camelCase over the wire, `CamelModel` base)

Renamed for the SaaS domain (like the iDRAC twin's `SubsystemMap`/`Block`), but
wire-compatible with the hardware twins so the frontend and its tests carry
over:

- `PlatformMap` (was `ChassisAnatomy`) — the architecture diagram container.
- `PlatformRegion` (was `ChassisRegion`) — one functional block.
- `PipelineState` (was `PowerOnState`) — one pipeline step. Replaces the
  hardware twins' `powerWatts`/`fanPercent` with the CloudIQ metrics:
  `progressPercent` (0→100), `healthScore` (0–100), and `dataPoints`.
- `PipelineResponse`, and unchanged `CatalogCategory`/`CatalogOption`/`UseCase`.

Enums:

- `PlatformRegion.kind` ∈ `source · gateway · ingest · analytics · security ·
  insight · assistant · action`.
- `PipelineState.phase` ∈ `idle · collect · transmit · ingest · analyze ·
  detect · surface · assist · notify`.

## 4. Pipeline sequence & invariants

Phase order, never regressing:

```
idle → collect → transmit → ingest → analyze → detect → surface → assist → notify
```

1. **idle** — systems connected and healthy; Health Score 100.
2. **collect** — telemetry gathered on the monitored systems (SupportAssist /
   OME plugin / AIOps Collector).
3. **transmit** — the Secure Connect Gateway sends it one-way (outbound TLS,
   port 443) to Dell's cloud.
4. **ingest** — the cloud parses, normalizes, and lands it in the data lake
   against a fleet-wide baseline.
5. **analyze** — the ML engine scores health, detects anomalies, and forecasts
   capacity — the heaviest stage, largest `cycleCost`.
6. **detect** — a risk crosses threshold (latency anomaly + capacity forecast +
   cybersecurity drift); the Health Score drops.
7. **surface** — the insight appears in the CloudIQ / AIOps app.
8. **assist** — the generative-AI AIOps Assistant explains it and recommends a
   fix (Infrastructure Context Awareness).
9. **notify** — email/mobile alerts, an ITSM ticket, and webhooks fire;
   remediation begins and the Health Score recovers.

Enforced by `backend/tests/test_engine.py` (keep green):

- Steps sequential from 0; `elapsedSeconds` strictly increases.
- Phase order monotonic through the sequence above; all 9 phases appear.
- `progressPercent` in [0,100], monotonic non-decreasing, starts 0, ends 100.
- `healthScore` in [0,100]; **idle == 100**; a dip below 100 occurs at/after
  `detect`; the final step recovers (above the low-water mark, below 100) —
  the signature Health-Score behavior.
- The **ML `analyze` stage is the single longest** (`cycleCost` max, unique).
- **Telemetry flows one way:** the first `transmit` step precedes the first
  `surface` step.
- Every `activeRegions` id exists in the map; `engine.py` imports nothing
  beyond `models` (AST-checked) — pure data.

`tests/test_anatomy.py` holds the diagram invariants (unique ids, in-bounds, no
overlaps, every `RegionKind` exercised, exactly one `gateway` and one
`assistant`, ≥2 `source` families, credited photos when present);
`tests/test_catalog.py` keeps the catalog and use cases resolvable.

## 5. Pages

1. **Pipeline** (`/`) — the architecture diagram lit block-by-block as the
   trace plays; controls, the Health-Score / progress / data-point counters,
   and a per-step explanation.
2. **Architecture** (`#architecture`) — hover/click the diagram for per-block
   descriptions, facts, and Dell sources.
3. **Capabilities** (`#capabilities`) — the capability menu (monitored systems,
   connectivity, health, capacity, performance, cybersecurity, sustainability,
   AIOps Assistant, integrations, access & licensing), each mapped to where it
   runs in the diagram.
4. **Use cases** (`#usecases`) — prevent a capacity shortfall, find a
   performance anomaly (noisy neighbor), and watch cybersecurity posture —
   each listing the capabilities it leans on (no bill of materials; CloudIQ is
   enabled, not assembled).

## 6. Roadmap ideas

- Alternate traces: a "clean run" where analysis finds nothing (Health Score
  stays 100), or a cybersecurity-only path; a multi-system fleet view.
- A live-feeling Health-Score gauge and sparkline instead of a number.
- Onboarding walkthrough: the concrete steps to connect a PowerStore or a
  PowerEdge (SupportAssist vs collector vs OME plugin), as its own trace.
- Sustainability page: energy/carbon trends as a first-class view.
- Real screenshots/illustrations once a credited, self-contained asset set is
  available (the `photo` field is already optional and rendered when present).
- More components as sibling top-level directories per the repo pattern.
