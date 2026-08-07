# DellPowerEdgeR760Thermal — interactive power & thermal simulator

The R760's **second twin**: same machine as `DellPowerEdgeR760/`, the other
question. That twin shows what happens when the server turns on; this one
shows what happens while it runs — an interactive, simplified physics model
of the causal chain **configuration → load → power → heat → fan response →
feedback**. Built from the spec at
`DellPowerEdgeR760/r760-interactive-simulator-spec.md` (with the repo
adaptations recorded in its §11).

Not CFD and not a telemetry-fed digital twin: a "flight simulator" for
understanding the platform, where correct *relationships and orders of
magnitude* matter more than exact numbers. Every model constant lives in
`backend/app/constants.py` with units and a `source` field; estimates are
flagged and surfaced in the UI, per the repo's no-invented-specs rule.

The architectural twist versus the fixed-trace twins: `POST /api/simulate`
takes a **Scenario** — server configuration, workload dials, environment,
and a list of timed events (kill fan 3 at t=180, raise the inlet to 40 °C)
— and the pure engine returns the whole deterministic trace, which the
frontend animates at ×1/×10/×60. This is the `DellAlienware/` twin's
scenario→trace pattern generalized; interactive mid-run actions become
events at the current cursor, so the engine stays pure and reproducible.

```
backend/   app/{models,constants,engine,validation,anatomy,presets,leveling,main}.py + tests/
frontend/  src/{api,types,level}.ts, App.tsx, components/{ThermalChassisView,BuildPanel,
           Instruments,StripCharts,LevelControl}.tsx
scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./scripts/start_all.sh` (backend :8030 background, frontend :5203
  foreground). Stop: `./scripts/stop_all.sh`.
- Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8030`. `POST /api/simulate` runs
  a scenario; `GET /api/simulate` runs the default one (for zero-click
  first paint and the CustomerSetup chip enrichment, which expects a GET).

Key invariants (enforced in `backend/tests/` — the spec's §9 acceptance
criteria as pytest, plus the house-style conservation identities):

- **Power balance, every tick** — CPU + GPU + DIMM + drives + I/O +
  platform + fans equals total DC exactly, and wall AC = DC ÷ efficiency
  at the load point. The fan-feedback loop is an asserted fact.
- **Heat balance at steady state** — exhaust ΔT = DC ÷ (ṁ·cp), the
  IR7000 twin's identity from inside one server.
- **Acceptance §9.1–9.3** — modest config idles at 90–140 W wall with
  fans at the floor; the max config peaks in the 1.2–1.9 kW band and
  holds below throttle at 22 °C; raising inlet to 40 °C at full load
  produces fan ramp, then higher wall power, then throttling — in that
  order, with lag.
- **Protective behaviors** — throttling clamps power in steps and is
  logged; sustained overtemp or hot inlet powers the server off; a killed
  fan makes the survivors ramp; a killed PSU in 1+1 shifts the survivor's
  efficiency point, in 1+0 it is lights-out; sustained overcurrent trips.
- **Constants honesty** — every constant carries a source; the
  estimate-flag and the source text must agree.
- **Validation rules** (spec §6) — heatsink and Gold-fan requirements
  error, ambient/altitude/PSU-oversubscription warn; presets must pass
  their own hard rules.
- **Engine ↔ anatomy contract** — the engine's `regionTemps` keys equal
  the chassis map's region ids (geometry reused from the R760 power-on
  twin, temperature-painted on a fixed 20–110 °C scale).

Teaching layer: Explain mode renders each key readout's governing equation
with live values substituted; seven guided scenarios (idle-to-full, the
fan-power feedback loop, kill-a-fan, the 350 W problem, the recirculation
death spiral, the PSU sweet spot, altitude) set the scenario and narrate
what to watch, each ending in a question the simulator can answer. The
Explain and scenario prose is authored at reading levels 1/3/5.

Cross-references: `DellPowerEdgeR760/` (the same chassis's bring-up — and
the floorplan this twin repaints), `DellIR7000/` (this server's heat, seen
from the facility side), `DellAlienware/` (the scenario→trace and
energy-identity precedents), `GPU/` (the roofline behind the AI-training
preset), `DellIDRAC/` (the controller whose policies the fan loop and
protective behaviors model).
