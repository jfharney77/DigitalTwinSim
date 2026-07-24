# DellPowerFlex — software-defined storage digital twin (sixteenth component)

A digital twin of **Dell PowerFlex** (5.0 Ultra — scalable availability
engine, erasure coding): shared block storage assembled out of ordinary
servers' local NVMe, running over ordinary IP, scaling from three nodes to
more than two thousand and past 240 million IOPS.

The third storage twin in this repo, and the one that argues with the other
two. PowerStore and PowerMax are controller architectures; this is what
happens when you delete the controller.

## The one idea

**There is no controller.**

PowerStore has two active-active controller nodes. PowerMax has directors in
node pairs. In both, every byte a host writes crosses a controller, so the
controller is simultaneously the performance ceiling and the failure domain
— and most of the engineering in those designs goes into making that
centrality survivable: mirrored cache, vault-on-power-loss, active-active
failover.

PowerFlex removes the centre instead. Servers contribute local NVMe; volumes
are chopped into chunks scattered redundantly across every node; clients
hold the map and address nodes directly. The metadata manager referees and
carries nothing.

The payoff arrives when a node dies. In a controller array the surviving
controller performs the rebuild — one device reading, one device writing,
hours at reduced protection. Here the lost node's data lives in fragments on
every other node, so **every survivor rebuilds a sliver simultaneously**,
reading from every other survivor. In a hundred-node pool, a hundred nodes
each rebuild a hundredth. Rebuild time *falls* as the cluster grows, which
is the reverse of how storage systems normally age.

`rebuildParticipants == nodesOnline` during a rebuild, and
`test_engine.py` asserts it.

## What it shows

- **Pool in motion** (`/`) — a pool assembled, loaded, wounded, and healed:
  nodes joining, chunks scattered, volumes presented, steady I/O, a node
  dying, the many-to-many rebuild, and full protection restored on a smaller
  cluster.
- **Inside the pool** (`/#anatomy`) — clients above, IP fabric, then a band
  of six identical servers, with the metadata manager drawn deliberately
  small in a corner. The lesson is an absence: there is no controller row.
- **Components & options** (`/#components`) — storage nodes, deployment
  topology (two-layer / hyperconverged / mixed in one pool), protection
  (mesh mirroring, erasure coding, fault sets), fabric, client access,
  metadata management, data services, lifecycle, platform integration.
- **Use cases** (`/#usecases`) — consolidating a database estate that cannot
  pause, a container platform that grows a node at a time, and replacing
  every server in the pool without a migration project.

## Run

```
./DellPowerFlex/scripts/start_all.sh   # backend :8016, frontend :5189
./DellPowerFlex/scripts/stop_all.sh
```

`start_all.sh` creates the backend venv, installs dependencies, starts
uvicorn in the background (logs to `logs/backend.log`), and runs Vite in the
foreground — Ctrl-C stops both. Then open <http://localhost:5189>.

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

Vite proxies `/api` → `http://localhost:8016`. If that port is taken,
run the backend elsewhere and point Vite at it:
`API_TARGET=http://localhost:8116 npm run dev`.

Trace endpoint is `GET /api/cluster`, returning `ClusterResponse`;
`/api/anatomy`, `/api/catalog`, and `/api/usecases` follow the same shape as
the other twins.

## Key invariants (backend/tests/)

- Engine purity (AST-checked); the playback clock lives in `App.tsx`.
- Phase order
  `off→cluster→pool→volumes→io→failure→rebuild→rebalanced→steady` never
  regresses.
- **Every surviving node rebuilds** — `rebuildParticipants == nodesOnline`
  during the rebuild, never a subset. The defining property.
- **No node is privileged** — in every step the lit node set is empty, all
  six, or all five survivors. Never an arbitrary subset, never one node
  working for the others.
- **The failed node never comes back** — recovery is redistribution onto
  survivors, not waiting for a replacement.
- **Service survives the failure** — I/O never stops and never falls below
  70% of steady. A controller array's failover would show a gap here.
- **Protection dips and fully returns** — it may fall when hardware is lost,
  and may not settle anywhere but 100.
- **The coordinator is absent from the steady data path** — the metadata
  manager is dark during ordinary I/O; it hands out the map and steps aside.
- **Building the pool is the longest stage, not repairing it** — this twin
  deliberately inverts the repo's usual pattern (R760 memory training,
  SN6000 link training, Pro Max Plus model load). The scatter is slow so the
  repair can be fast, and `cycleCost` is pinned to say so.
- Geometry carries the lesson: nodes are drawn identically, the coordinator
  must be smaller than any node, and nothing may sit between the client band
  and the node band except the fabric
  (`test_anatomy.py::test_there_is_no_tier_between_clients_and_nodes`).

## Honesty notes

- Six nodes are drawn; a real pool runs from three to past two thousand,
  which is the scale at which many-to-many rebuild stops being a nicety.
  Layout is a stylized mental model.
- IOPS, protection percentages, and timings are illustrative but plausible;
  favor a correct mental model over measured numbers (project scope
  guardrail).
- The only shipped visual is `frontend/public/powerflex-pool.svg`, a
  self-contained schematic drawn for this project with an honest credit line
  — not a Dell product image.

## Sources

- [Dell PowerFlex — software-defined infrastructure](https://www.dell.com/en-us/shop/powerflex/sf/powerflex)
- [Dell PowerFlex technical overview — rebuild](https://www.dell.com/support/manuals/en-us/scaleio/flex-software-to-45x/rebuild)
- [Introducing Dell PowerFlex 5.0 Ultra (WWT)](https://www.wwt.com/blog/introducing-dell-powerflex-5-dot-0-ultra-a-new-era-in-software-defined-storage)
- [Dell Technologies reimagines the modern data center for the AI era (May 2026)](https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2026~05~dell-technologies-reimagines-the-modern-data-center-for-the-ai-era.htm)
