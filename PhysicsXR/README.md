# PhysicsXR — PowerEdge XR rugged-edge physics simulator

Product #2 of `physics_specs/10-additional-products.md`: the Dell
PowerEdge XR-series (XR8000 sled-based, XR4000 stackable) as an
interactive physics model. Built on the `DellPowerEdgeR760Thermal/`
template — deliberately, because that is the product story:

**The one idea: the R760's thermal engine with the environment sliders
unlocked to hostile ranges.** A data-hall server's inlet slider stops at
45 °C; this one runs −25…65 °C, accumulates dust on a front filter over
sim-months (raising the airflow resistance the fan wall must overcome, so
the same cooling costs more rpm and rpm costs its cube in watts), exposes
a vibration class that taxes spinning drives and spares SSDs, and hangs
off a single-phase site feed that browns out — where ride-through is
arithmetic (I = P/V against the PSU input limit), so the same sag idles
through at 2 A and trips at full load.

## Run

```
./PhysicsXR/scripts/start_all.sh    # backend :8040 background, frontend :5213 foreground
./PhysicsXR/scripts/stop_all.sh
```

- Backend tests: `cd PhysicsXR/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend build: `cd PhysicsXR/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8040` (`API_TARGET` overrides).

`POST /api/simulate` takes a Scenario (config + workload dials +
environment + timed events) and returns Validation[] + SimState[] trace +
LogEntry[] + Summary; `GET /api/simulate` runs the default (cell-site
build, RAN workload). Other endpoints: `/api/anatomy`, `/api/constants`,
`/api/presets/{configs,workloads}`, `/api/scenarios`, `/api/explain`,
`/api/levels`. The engine is pure (AST-checked: no fastapi/time/random/
IO); the playback clock lives in the frontend.

## Invariants (pytest, house style)

- **Power balance every tick**: component powers sum to DC; AC = DC ÷
  η(load) on the Titanium-class curve.
- **Heat balance at steady state**: ΔT = DC/(ṁ·cp) — the IR7000 identity
  inside one short-depth box.
- **Phoenix throttles where Fargo idles its fans** — one config, two
  climates (the spec's headline scenario).
- **The fouled filter throttles where a clean one survives** the same
  heat wave; fouling costs fan power at constant work.
- **The same brownout rides through at idle and trips at full load**;
  deep sags are lights-out regardless.
- **Vibration taxes HDDs and spares SSDs** — a performance tax, not a
  failure event.
- The rated envelopes (−5…55 °C standard, −20…65 °C select extended) are
  pinned as *documented, not estimated* constants.

## Honesty

Sourced facts: the −5…55 °C standard and −20…65 °C extended envelopes,
NEBS Level 3 / MIL-STD-810H positioning, the altitude derating note
(Dell XR spec sheet, XR8000 Technical Guide, Dell Info Hub thermal
article — cited in `/api/anatomy` sources). Everything else — fouling
rates, vibration derates, fan curves, PSU input margins — is an estimate
and is labeled as such in `backend/app/constants.py`, through to the UI.

**What we don't model:** CFD; per-core DVFS; condensation and material
brittleness at the cold end (the real reasons the lower rating exists);
corrosion; filter media chemistry; the −48 V DC telecom feed (the sag
model is single-phase AC); acoustics. Correct relationships and orders
of magnitude, not a service manual.

## Companions

- `DellPowerEdgeR760Thermal/` — the template engine, in its native
  data hall (8030/5203).
- `DellPowerEdgeR760/` — what happens when a server like this turns on.
- `DellNativeEdge/` — who manages a thousand of these without visiting
  any of them.
- `DellTelecomBlocks/initial_spec.md` — the unbuilt narrative twin whose
  cell-site story this app gives physics to.
