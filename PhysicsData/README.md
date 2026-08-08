# PhysicsData — data pipeline & observability simulator

Seventh app of the physics suite (`physics_specs/06-data-and-observability.md`,
plan in `physics_specs/BUILD_PLAN.md`). Two halves of one loop, tick =
one sim-hour, deterministic throughout (noise is a fixed sinusoid mix).

- **Dell AI Data Platform** — theory of constraints as a sim:
  throughput = min(stage rates), backlog piles up ahead of the
  constraint, freshness lag = backlog ÷ throughput (Little's law in the
  explain tab), and fixing the bottleneck relocates it (×6 GPU toggle,
  labeled a claim to verify). The KV-cache offload trades a ~12% token
  tax for ×4 long-context sessions; GPU-idle-due-to-data is the north
  star — PhysicsCompute's feed slider and PhysicsStorage's Exascale
  gauge, unified.
- **CloudIQ / APEX AIOps** — the meta-instrument, graded: injected
  issues are ground truth, so the anomaly k-knob earns
  precision/recall/MTTD scores (same ROC trade as PhysicsResilience's
  sensitivity slider — the rhyme is deliberate). The days-to-full
  forecast converges on steady slopes and is confidently wrong for one
  window after every change; acting on it averts the outage the
  no-action run records. The gray failure stays status-green for the
  whole trace while the trend catches it — both halves asserted.

## Run

```
./scripts/start_all.sh     # backend :8037 background, frontend :5210 foreground
./scripts/stop_all.sh
```

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

## Companions

`DellCloudIQ/` (:5180) narrates the telemetry-to-insight pipeline;
`DellExascale/` (:5184) and `PhysicsStorage/`'s Exascale meta-sim are
the storage under this pipeline; `PhysicsFabric/`'s gray-failure toggle
is the wound this app's console diagnoses. Dashboards are the data
layer a digital twin binds to — the suite's closing loop.
