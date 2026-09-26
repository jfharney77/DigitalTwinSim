# CloudIQ / Dell AIOps — inside the platform

A digital-twin web app for **CloudIQ** (renamed APEX AIOps Infrastructure Observability in 2024,
then **Dell AIOps** in 2025) — Dell's cloud-native AIOps observability SaaS. It follows the same
pattern as the hardware twins in this repo (`GPU/`, `DellPowerStore/`, ...): a
pure FastAPI engine that emits a deterministic trace as data, and a React/Vite
frontend (Dell clean-design skin) that plays it back.

The twist: CloudIQ is **software, not a box**, so the metaphors are adapted the
way the iDRAC and PowerSwitch twins adapted theirs:

- The **"anatomy"** is the platform **architecture diagram** — the
  telemetry-to-insight pipeline, drawn left (telemetry in) to right (insights
  out): monitored Dell systems → Secure Connect Gateway → cloud ingest → ML
  analytics + cybersecurity → insights, AIOps Assistant, and notifications.
- The **"power-on trace"** is the **lifecycle of telemetry becoming an
  actionable insight** (`idle → collect → transmit → ingest → analyze →
  detect → surface → assist → notify`). The signature **Health Score** starts
  at 100, drops when a risk is detected, and recovers only when a later
  collection shows the issue cleared (the final step's clock jumps about an hour;
  a ticket does not move the score).

Written for a technically skilled reader new to AIOps: what CloudIQ observes,
how telemetry reaches Dell's cloud (one-way, over an outbound-initiated
Secure Connect Gateway connection),
what the machine learning does with it, and what real workflows look like.

## Run

```bash
./DellCloudIQ/scripts/start_all.sh    # backend :8007 (background) + frontend :5180 (foreground)
./DellCloudIQ/scripts/stop_all.sh     # stop both
```

Backend tests: `cd DellCloudIQ/backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd DellCloudIQ/frontend && npm run build`

Vite proxies `/api` → `http://localhost:8007`, so open http://localhost:5180.
Ports are offset from the other twins so they can run alongside. If :8007 is
taken, run the backend elsewhere and point Vite at it:
`API_TARGET=http://localhost:8017 npm run dev`.

## Pages

- **Pipeline** — play the telemetry-to-insight trace; the architecture blocks
  light up per step (collect → Secure Connect Gateway → cloud ingest → ML
  analyze → detect → surface → AIOps Assistant → notify). Watch the Health
  Score drop when a risk is detected and recover at a later collection, after
  the fix.
- **Architecture** (`#architecture`) — the annotated platform diagram;
  hover/click each block (monitored systems, gateway, ingest, ML analytics,
  cybersecurity, insights & app, AIOps Assistant, notify & integrate).
- **Capabilities** (`#capabilities`) — the capability menu: monitored systems,
  connectivity, health monitoring, capacity analytics, performance analytics,
  cybersecurity, sustainability, the AIOps Assistant, integrations &
  notifications, access & licensing.
- **Use cases** (`#usecases`) — predict/prevent a capacity shortfall, find and
  fix a performance anomaly (noisy neighbor), and watch cybersecurity posture
  across the fleet — each with the capabilities it leans on.

## Failure scenario: connected, but no data

The onboarding failure people report most (see the Dell Community thread "OME
not updating anything to APEX AIOps" in `RESEARCH_ASSETS.md`): the system says
connected and nothing arrives. Pick it from the Scenario menu on the Pipeline
page, or deep-link it. The link composes with the phase and step links:
`/#scenario=connected-no-data`, `/#scenario=connected-no-data&phase=stale`,
`/#scenario=connected-no-data&step=3`.

The trace (`backend/app/scenarios.py`, pure and AST-checked like the engine):
`register → handshake → collect → blocked → starved → stale → repair → backfill
→ analyze → resume`. A new array is registered, the Secure Connect Gateway
passes its own connection test, and the customer's outbound proxy refuses the
telemetry upload (Dell's connectivity uses more than one port and destination;
which one is refused here is illustrative). Failing blocks are
drawn dashed in the error colour. The counter to watch is **minutes without
data**.

What it copies from the real product, with sources served by
`GET /api/scenarios` and shown under the counters:

- A system with no delivered telemetry has no Health Score. CloudIQ draws a
  grey dash, and a grey number means "connectivity issue, uncertain score".
  It is never green (CloudIQ detailed review, H15691).
- CloudIQ's Connectivity view defines Connected as successfully sending data,
  a stricter claim than the gateway's own status. A system that has never sent
  sits under Not Set Up, known from the install-base record; Lost Connection
  is for systems that were sending and stopped (same paper). The cloud does
  not infer this failure from missed sends. The stale step dwells because
  onboarding can take up to an hour (KB 000181685), so a grey dash is a fault
  only after that, and the listing is passive: someone has to look.
- The causes and the fix are on the customer side: blocked outbound 443, a
  proxy rule, DNS, or collection disabled on the array (Dell KB 000181685; a
  gateway port change does the same to the Collector, KB 000196110). Dell's
  cloud has no inbound path, so it cannot repair this itself.

Invariants (`backend/tests/test_scenarios.py`): analytics, cybersecurity, the
Assistant and notifications never run while the cloud holds no data from the
system; the score state is `no-data` and never in the green band until a score
has been computed from delivered telemetry; the stale step is the unique
longest stage and lights only the app; collected = delivered + backlog on
every step; the repair step lights only customer-side blocks; and the healthy
trace is byte-identical in every original field (pinned by hash).

Illustrative: every count and timing, and the full backfill in particular.
How much a system or gateway retains while egress is blocked varies by
product, and a long real outage can leave a gap in the charts.

API: `GET /api/pipeline?scenario=connected-no-data` (no parameter returns the
healthy trace, as before; an unknown id is a 404) and `GET /api/scenarios`.
The guided tour narrates the healthy trace only.

See `initial_spec.md` for architecture, data models, and invariants. Content
is grounded in Dell's AIOps product page and support docs, cited in the
Architecture page's sources.
