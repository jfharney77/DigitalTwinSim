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
