# DellPowerEdgeXE9712 — rack-scale AI digital twin (tenth component)

A digital twin of the **Dell PowerEdge XE9712**, Dell's rack-scale AI system
built around **NVIDIA GB200 NVL72**: one integrated, liquid-cooled rack of
18 compute trays (36 Grace CPUs + 72 Blackwell GPUs) and 9 NVLink switch
trays that fuse every GPU into a single NVLink domain — software sees
something close to one giant GPU.

Same architecture as the repo's other twins: a pure-engine FastAPI
`backend/`, a React/Vite `frontend/` in the Dell clean-design skin, and
`scripts/` to run both.

## What it shows

- **Power-on** (`/`) — the rack's bring-up from dark to accepting jobs,
  with two beats no earlier twin has: **liquid before silicon** (the
  coolant loop must prime before any GPU may power on) and the **fuse**
  (the GPUs-in-domain counter sits at 0 through the whole bring-up, then
  snaps to 72 when the NVLink fabric fuses).
- **Inside the rack** (`/#anatomy`) — annotated front-of-rack elevation:
  power shelves and busbar, GB200 compute trays, mid-rack NVLink switch
  trays, the CDU and coolant manifolds.
- **Components & options** (`/#components`) — rack platform (GB200/GB300),
  trays, GPUs, Grace, the NVLink fabric, scale-out networking, PowerCool
  liquid cooling, power, management, external storage, software, delivery.
- **Use cases** (`/#usecases`) — foundation-model training (8 racks),
  real-time trillion-parameter inference (1 GB300 rack), and a sovereign
  AI factory.

## Failure scenario: coolant fault

`GET /api/poweron?scenario=coolant-fault` serves a second pure trace (15 steps)
beside the nominal one; `GET /api/scenarios` lists both with their sources.
On the power-on page it is the Scenario picker, and it deep-links as
`#scenario=coolant-fault`, composing with `&phase=<name>` or `&step=N`
(for example `#scenario=coolant-fault&phase=leak`). The guided tour always
plays the nominal trace.

Liquid before silicon, tested twice:

- **Before any GPU has power** (`flowfault → isolate → repair → reverify`):
  one tray branch reads low flow and its leak sensor is wet. That tray's
  GPUs get no power without verified flow. The modelled site runs the rack as
  one 72-GPU machine, so it holds every GPU off and does not bring up 68. That
  hold is a site policy and the prose says so: real hardware can boot 17 trays
  into a smaller partition. The tray is held off the busbar automatically; its
  branch seals when a technician unseats it: its quick disconnects close as
  they part, and this twin models no automatic per-tray liquid shut-off (the
  automatic one NVIDIA documents is rack-level, through the building
  management system). The technician reseats it,
  all 18 branches re-verify, and the nominal bring-up then replays unchanged,
  about ninety minutes late.
- **Under full load** (`leak → traydown → held`): a cold-plate leak sensor
  trips and the tray's BMC cuts its power on a timer rather than on a
  temperature reading, so rack power falls on that step and the hottest GPU
  never gets hotter. NVIDIA's fault table gives the BMC a shutdown timer and
  no duration; the one published figure nearby is a ten-minute going-down
  timeout for a large leak, so compressing the response into a single step is
  this twin's simplification, and the step's prose says so. The 72-GPU domain
  ends (72 → 0 with 68 GPUs still powered) and the rack waits for service.
  Re-forming a smaller partition from the survivors is a real fabric-manager
  capability and is not modelled.

Invariants (`backend/tests/test_scenarios.py`): no GPU draws power without
verified flow on its branch (`gpusPowered <= 4 × branchesVerified`, both
scenarios); `gpusInDomain` is only ever 0 or 72; power drops before temperature
rises; faulted regions are never lit; the recovered bring-up equals the nominal
one except for the clock; and the nominal trace's numbers are pinned by a
SHA-256 over step, phase, label, regions, watts, domain count, clock and dwell,
so the happy path cannot drift unnoticed. The hash deliberately excludes the
leveled prose, which the reading-level tests own. `PowerOnState` grew four defaulted fields for this
(`failedRegions`, `branchesVerified`, `gpusPowered`, `gpuTempC`).

The behaviour follows NVIDIA's Mission Control leak-detection and
building-management-integration guides for GB200 NVL72 (tray BMC detects over
Redfish and runs a shutdown timer; rack-level leaks escalate to breakers and
valves), Dell's iDRAC default-action power-off leak events (whose recommended
action is to remove power and disconnect the hoses from the manifold), and
NVIDIA's IMEX guide for what a lost node does to a running job. The links ride in the scenario data. Timings, watts and
temperatures are illustrative. Read it with `DellIR7000/` (the same loop from
the plumbing side, whose verify phase is the check that fails here) and
`PhysicsCDU/` (what the CDU does when a branch closes or load falls away).

## Run

```
./DellPowerEdgeXE9712/scripts/start_all.sh   # backend :8008, frontend :5181
./DellPowerEdgeXE9712/scripts/stop_all.sh
```

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

## Key invariants (backend/tests/)

- Engine purity (AST-checked): no FastAPI/IO/timers in `engine.py`; the
  playback clock lives in `App.tsx`.
- Phase order `off→power→coolant→trayboot→gpuinit→fabric→fused→ready`
  never regresses; the first `coolant` step precedes the first `trayboot`
  step (liquid before silicon).
- Power draw is monotonic to ~120 kW and its single biggest jump is GPU
  init; NVLink fabric training is the single longest stage (max
  `cycleCost`).
- `gpusInDomain` is 0 until the `fused` step and exactly 72 from then on —
  there is no partial domain; the fuse step lights every GPU region.
- Trays boot in lockstep (`-t1..-t4` suffix twins); four-tray symmetry in
  the anatomy; catalog/use-case ids resolve.

Counts, watts, and timings are illustrative, anchored to Dell's XE9712 and
NVIDIA's GB200 NVL72 product pages (see anatomy `sources`). The floorplan
draws 4 of 18 compute trays and 2 blocks for 9 switch trays — a stylized
mental model, not a rack-accurate drawing.
