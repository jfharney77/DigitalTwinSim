# PhysicsCDU — PowerCool CDU C7000 · PowerRack · Integrated Rack Controller

An interactive physics simulator of the facility layer under a
liquid-cooled AI rack: the **coolant distribution unit** as the star.
Product #5 of `physics_specs/10-additional-products.md`, built on the
`DellPowerEdgeR760Thermal/` template (scenario → deterministic trace,
pure engine, playback clock in the frontend).

**The one idea:** a CDU is a wall between two loops, and one chain of
temperatures runs through it —

```
facility supply  +  approach (Q / UA·flowfactor)   =  coolant supply
coolant supply   +  loop rise (Q / ṁ·cp)           =  coolant return
coolant supply   +  ½·rise + cold-plate R_th·q     =  silicon
```

Both loops carry the same heat on every tick (`ṁ·cp·ΔT` primary =
IT heat = `ṁ·cp·ΔT` secondary) — asserted in the tests, the IR7000
twin's identity with two liquids instead of air. Above the loop sits
the **Integrated Rack Controller** and the twin's real argument: on a
warm-water day, a coordinated policy caps every tray bank a little,
together (zero trips), while uncoordinated tray-level panic becomes a
staggered cascade that sheds more compute than the physics required —
the loop's 60 s thermal lag keeps survivors hot after the first trip,
so the cascade overshoots. Delivered kilowatt-hours, compared across
the two runs, is the IRC's reason to exist.

Also modeled: pump hydraulics (parallel pumps add flow like k^0.65;
power goes with speed³; N+1 vs N priced by one A/B), the heat
exchanger's approach temperature, and the **dew-point floor** — the
mixing valve holds coolant supply ≥ dew point + 2 K on every tick,
because condensation on a live cold plate is a worse day than warm
silicon. On a humid afternoon the room, not the operator, owns the
bottom of the loop.

## Run

```
./PhysicsCDU/scripts/start_all.sh    # backend :8043 background, frontend :5216 foreground
./PhysicsCDU/scripts/stop_all.sh
```

- Backend tests: `cd PhysicsCDU/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend build: `cd PhysicsCDU/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8043`. Trace endpoint:
  `POST /api/simulate` (Scenario in, Validation[] + SimState[] +
  LogEntry[] + Summary out); `GET /api/simulate` runs the default.
  Other endpoints: `/api/anatomy`, `/api/constants`,
  `/api/presets/{configs,workloads}`, `/api/scenarios`, `/api/explain`,
  `/api/levels`.

## Guided scenarios

Size the CDU (add banks until the heat exchanger binds — near the
220 kW nameplate) · Warm water day, coordinated (graceful shed) · Warm
water day, panic (the trip cascade) · One pump down on N+1 (a boring
failure) · No spare pump (the derate) · The dew-point floor (the room
sets your supply temperature).

## Companions in this repo

- **`DellIR7000/`** (:8009/:5182) — the same loop's commissioning story
  and the rack-side heat-balance identity this twin inherits.
- **`DellPowerEdgeXE9712/`** (:8008/:5181) — the trays making the heat;
  its power-on pauses at "liquid before silicon", and this twin is what
  it waits for, one layer further out.

## Honesty

The C7000 (4U, 19-inch, 220+ kW class, Vera Rubin NVL72), PowerRack,
and the IRC were announced at Dell Technologies World in May 2026 and
ship from Q3 2026 — public detail is press-release depth. The one
sourced figure is the 220 kW capacity class; nearly every physics
constant (UA, pump curves, cold-plate resistance, time constants,
trip thresholds) is an **estimate and labeled so** in
`backend/app/constants.py`, each with units and a source field, served
over `/api/constants` so the UI can badge estimate-derived readouts.

**What we don't model:** NTU heat-exchanger integration, pump heat into
the coolant, filter fouling, glycol aging, water-side economizer
dynamics, leak events (the IRC's headline feature is leak detection in
seconds — a story about sensing, not thermodynamics), and CFD anywhere.
Correct relationships and orders of magnitude, not a P&ID.
