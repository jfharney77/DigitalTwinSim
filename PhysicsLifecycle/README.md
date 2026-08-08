# PhysicsLifecycle — telecom & sustainability simulator

Eighth and final app of the physics suite
(`physics_specs/08-telecom-and-sustainability.md`, plan in
`physics_specs/BUILD_PLAN.md`). Tick = one sim-day.

- **Telecom Infrastructure Blocks** — the integration-effort model is
  the product: DIY pays 10 h/site of compatibility-matrix validation
  and hits a deterministic mismatch every 12th site (16 h + an outage
  each); Blocks pays 1.5 h/site for a tested bundle. The 48 °C heatwave
  drops ~30% of a standard-temp fleet and none of an XR-class one
  (envelope figures labeled to verify); coverage counts subscribers;
  updates with N+1 spares keep it — maintenance, not failure, is where
  the nines leak.
- **Circular Design** — four design checkboxes, then eight accounted
  years: scheduled crises (port day ~912, battery ~1278, RAM ~1642)
  resolve as parts (6–12 kgCO2e) or whole devices (~246–280 kg
  embodied, again); refurb success = f(disassembly minutes) decides the
  second life. The ledger **closes every tick** (total = embodied +
  use, asserted) and the headline is carbon per useful-year — sealed
  runs ≥3 devices and ~2× the serviceable figure. **Spec 08's honesty
  rule is test-enforced**: every carbon constant is a labeled estimate,
  and Dell's per-product PCF reports are named as the calibration
  source on every surface.

## Run

```
./scripts/start_all.sh     # backend :8038 background, frontend :5211 foreground
./scripts/stop_all.sh
```

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

## Companions

`DellNativeEdge/` (:5187) — telecom is its most extreme fleet;
`PhysicsFleet/`'s NativeEdge personality is the shared engine.
`DellCircularDesign/initial_spec.md` is the narrated-twin spec the
sustainability half descends from (LOOP_LOG's strongest unbuilt
candidate — this app is its physics-first sibling, not its
replacement).
