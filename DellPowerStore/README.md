# Dell PowerStore — inside the box

A digital-twin web app for the Dell PowerStore all-NVMe storage appliance,
following the same pattern as `GPU/` and `DellPowerEdgeR760/`: a pure FastAPI
engine that emits the bring-up sequence as data, and a React/Vite frontend
(Dell clean-design skin) that plays it back.

Written for a technically skilled reader who is new to the product: what's
inside the 2U enclosure (two active-active controller nodes sharing a 25-slot
NVMe drive bay), what happens between connecting AC and serving I/O — there is
no power button — what can be configured into it, and what real deployments
look like.

## Run

```bash
./DellPowerStore/scripts/start_all.sh    # backend :8002 (background) + frontend :5175 (foreground)
./DellPowerStore/scripts/stop_all.sh     # stop both
```

Backend tests: `cd DellPowerStore/backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd DellPowerStore/frontend && npm run build`

Vite proxies `/api` → `http://localhost:8002`, so open http://localhost:5175.
Ports are offset from the GPU app (8000/5173) and the R760 app (8001/5174) so
all three can run at once.

## Pages

- **Power-on** — play the AC-to-serving-I/O trace; enclosure regions light up
  per step (PSUs → BBU vault self-test → both nodes boot PowerStoreOS →
  NVMe/NVRAM discovery → cluster handshake → data services → online).
- **Inside the chassis** (`#anatomy`) — annotated top-down floorplan of the
  base enclosure with real product photos; hover/click for what each block
  does (drive bay, NVRAM, the mirror-image Node A / Node B canisters).
- **Components & options** (`#components`) — the configuration menu:
  appliance tiers (500T–9200T), NVMe drives, NVRAM, expansion shelves,
  clustering, I/O modules, mezzanine cards, power, PowerStoreOS software,
  management, protection, rack hardware.
- **Use cases** (`#usecases`) — VMware storage consolidation, database
  consolidation, edge block + file, each with a resolvable build sheet.

## Failure scenario: node A fails

The sim page has a scenario picker. `#scenario=node-loss-failover` plays a
second pure trace (`backend/app/failover.py`) that starts from a serving
array, not from AC, and composes with the other deep links
(`#scenario=node-loss-failover&phase=degraded`). It is served by the same
endpoint, `GET /api/poweron?scenario=node-loss-failover`; `GET /api/scenarios`
lists the traces. With no `scenario` the power-on response is byte-identical
to before, and `tests/test_failover.py` pins that.

Phases: `online → fault → failover → degraded → rejoin → resync → rebalance →
restored`. Node A stops; hosts retry on their active/non-optimized paths to
node B (ALUA for SCSI, ANA for NVMe-oF); node B takes over node A's resources
and serves every volume at roughly double its load; node A reboots (the
longest stage), rejoins over the interconnect, catches up, and block volumes
fail back by themselves.

What the tests assert because the failure happened:

- **Zero acknowledged writes lost**, on every step. The hero counter exists to
  be zero, and the failure is checked to be real (all of node A's compute and
  ports down, one node serving) so the zero means something.
- **Writes stay mirrored while single-node.** The write cache is a mirrored
  pair of NVRAM drives in the shared, dual-ported front bay, not memory inside
  a node. Node B still commits every write to two devices before it
  acknowledges, with no fallback to write-through, and each BBU powers one
  drive of every pair, so vaulting on AC loss is still covered. This is the
  1000-through-9200 design; the PowerStore 500 has no NVRAM drives (it caches
  writes in node DRAM and vaults to the M.2 boot module) and the trace does
  not model it. The scenario's `basis` and the degraded step say so.
- **I/O never stops**: a bounded dip at the fault, back to the full rate
  before the degraded phase, paid for in node B's headroom.
- **Rejoin precedes rebalance**: node A is a member again and caught up
  strictly before any volume moves back.

Behaviour follows Dell's white papers H18157 (Clustering and High
Availability) and H18149 (Introduction to the Platform), cited in the scenario
data. Every second, watt and percentage is illustrative: Dell publishes no
block failover time. The `resync` step is this twin's reading of the public
documents, and its prose says so. Down regions are drawn in the shared error
colour with a dashed outline. The guided tour stays on the power-on trace.

See `initial_spec.md` for architecture, data models, and invariants.
