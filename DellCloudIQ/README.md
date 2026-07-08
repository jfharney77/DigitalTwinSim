# CloudIQ / Dell AIOps — inside the platform

A digital-twin web app for **CloudIQ** (rebranded **Dell AIOps**, part of APEX
AIOps) — Dell's cloud-native AIOps observability SaaS. It follows the same
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
  at 100, drops when a risk is detected, and recovers as remediation begins.

Written for a technically skilled reader new to AIOps: what CloudIQ observes,
how telemetry reaches Dell's cloud (one-way, via the Secure Connect Gateway),
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
  Score drop when a risk is detected and recover after remediation.
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

See `initial_spec.md` for architecture, data models, and invariants. Content
is grounded in Dell's AIOps product page and support docs, cited in the
Architecture page's sources.
