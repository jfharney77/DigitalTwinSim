# DellQuantumX800 — InfiniBand-fabric digital twin

Same architecture as the other twins in this repo, applied to the **NVIDIA
Quantum-X800 InfiniBand platform** (800 Gb/s XDR: Q3400 spine switches,
ConnectX-8 SuperNICs, SHARP v4) as Dell delivers it in IRSS racks — the
interconnect named in the **TACC Horizon** announcement (4,000 GPUs, one
million CPU cores, 300 PF).

The deliberate counterpart to `DellPowerSwitchSN6000/`. That twin's
Ethernet fabric must *prove* it never drops a packet — Ethernet drops by
default, so Spectrum-X earns losslessness with ECN, PFC, and adaptive
routing reacting in time, and the twin drives a congestion step to show
zero drops under stress. This twin inverts the premise: **lossless by
construction, not by vigilance.** A sender may not transmit until the
receiver has granted buffer credits, so `packetsSentWithoutCredit` is zero
not because the fabric caught itself but because the link layer cannot
express the violation. Two more architectural facts complete the story:
one **centralized subnet manager** maps the fabric and installs every
route before a byte moves — then leaves the data path — and **SHARP**
moves the all-reduce arithmetic into the switch ASICs, so raw traffic
falls while effective collective throughput rises.

```
backend/   app/{models,anatomy,engine,catalog,usecases,leveling,main}.py + tests/
frontend/  src/{api,types,level}.ts, App.tsx, components/{FabricView,AnatomyPage,
           CatalogPage,UseCasePage,FabricControls,FabricCounters,LevelControl}.tsx
scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

- Run: `./scripts/start_all.sh` (backend :8029 background, frontend :5202
  foreground). Stop: `./scripts/stop_all.sh`.
- Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
- Frontend typecheck/build: `cd frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8029`. Trace endpoint is
  `GET /api/fabric` returning `FabricResponse` (SN6000-twin style).

Key invariants (enforced in `backend/tests/`):

- **No packet is ever sent without a credit** — zero on every step, stated
  in the constructive form the Ethernet twin cannot claim.
- **The burst stalls senders instead of losing work** — the incast drives
  the hot link ≥95% and `stallMicrosPerSec` goes nonzero (the honest cost),
  on exactly that one step, while the collective keeps progressing.
- **The manager programs the fabric, then leaves the data path** — active
  in exactly the `discover` and `routes` phases, absent from every traffic
  step (the Exascale-MDS / PowerFlex-coordinator move).
- **Routes are installed before any traffic** — programmed, not converged.
- **SHARP moves the math into the fabric** — `fabricTbps` strictly falls
  while `allreduceGbps` strictly rises when the switches start computing.
- **Route computation is the longest stage** (unique max `cycleCost`).
- **Geometry carries the lesson** — tiers vertically ordered; the subnet
  manager drawn smaller than every fabric block and strictly beside the
  tree, because no data ever passes through it.

Referenced by `CustomerSetup/TACC-Horizon/` as the sourced fabric block
(previously stood in for by the SN6000's catalog InfiniBand option).
Cross-references: `DellPowerSwitchSN6000/` (the Ethernet fork of the same
decision), `DellPowerEdgeXE9712/`/`DellPowerEdgeXE9680/` (the NVLink
domains this fabric joins), `DellIR7000/` (the liquid loop the Q3400
plugs into), and `DellExascale/` (the other central-brain-off-the-data-path
architecture in this repo).
