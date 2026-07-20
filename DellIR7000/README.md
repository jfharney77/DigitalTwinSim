# DellIR7000 — liquid-cooling digital twin (eleventh component)

A digital twin of the **Dell Integrated Rack 7000 (IR7000)** and the
**PowerCool** liquid-cooling family that makes extreme density survivable:
an Open Compute ORv3 rack rated 33–264 kW today (roadmap to 480 kW), with
an in-rack coolant distribution unit (CDU), vertical manifolds, cold plates
on the payload, and an enclosed rear-door heat exchanger (eRDHx).

The repo's first **thermal** twin — nothing here boots. Same architecture as
the other twins: a pure-engine FastAPI `backend/`, a React/Vite `frontend/`
in the Dell clean-design skin, and `scripts/` to run both.

## What it shows

- **Thermal bring-up** (`/`) — commissioning a liquid-cooled rack: fill and
  degas, start pumps, per-branch leak and flow verification, rear door
  online, then IT load arrives and ramps to 264 kW. The signature invariant
  is **heat balance**: liquid + air heat removal equals the IT load exactly,
  on every step.
- **Inside the loop** (`/#anatomy`) — the rack drawn as a cooling loop: CDU,
  supply/return manifolds, four generic IT bays, rear-door heat exchanger,
  facility water, and the leak/flow instrumentation.
- **Components & options** (`/#components`) — rack platform (IR7000/IR5000),
  CDUs, rear-door options, cold plates, manifolds and quick disconnects,
  instrumentation, power, facility integration, payload, management.
- **Use cases** (`/#usecases`) — cooling a GB200 NVL72 row, retrofitting
  density into a legacy air-cooled building, and max-density HPC with heat
  reuse.

## Run

```
./DellIR7000/scripts/start_all.sh   # backend :8009, frontend :5182
./DellIR7000/scripts/stop_all.sh
```

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

## Key invariants (backend/tests/)

- Engine purity (AST-checked); the playback clock lives in `App.tsx`.
- Phase order `off→fill→pump→verify→airdoor→load→balance→steady` never
  regresses.
- **Heat balance**: `liquidWatts + airWatts == itLoadWatts` on every step,
  no tolerance; liquid carries ≥85% whenever there is load.
- **Flow before heat**: coolant flows strictly before the first watt of IT
  load; flow and load are both monotonic through the ramp.
- Per-branch leak/flow verification is the single longest stage (max
  `cycleCost`); the four IT bays always light together.

This twin is the other side of the XE9712 twin's cold plate — that twin's
power-on pauses at "liquid before silicon", and this twin's verify phase is
what it waits for. Wattages, flows, and timings are illustrative, anchored
to Dell's OCP-2024 announcement and PowerCool material (see anatomy
`sources`).
