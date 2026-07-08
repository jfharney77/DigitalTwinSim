# DellPowerMax — spec

## 1. Purpose & scope

Teach a technically skilled reader who is *new to the product* what a Dell
PowerMax is: Dell's flagship, mission-critical, end-to-end NVMe **scale-out**
storage array, built from modular **node pairs** (two compute directors each)
joined by an **InfiniBand Dynamic Fabric**, with drives living separately in
**Dynamic Media Enclosures (DMEs)** reached over that fabric. What sits inside
the box, what actually happens between connecting AC and serving I/O (there is
no power button — applying AC *is* the power-on), what can be configured, and
what real deployments look like.

Guardrails (mirror the GPU app's spirit, and the PowerStore app's):

- **Not a firmware/PowerMaxOS simulator.** Timings, wattages, and fan
  percentages are illustrative — the goal is a correct *mental model* of the
  bring-up sequence, not second-accurate behavior.
- **The floorplan is stylized**, traced from Dell's PowerMax 2500/8500 spec
  sheet and product imagery, placed in a normalized 100×52 coordinate space.
  It shows **one node pair engine plus one DME**; a real array is 1–8 node
  pairs and many DMEs across one or more cabinets. Not mm²-accurate.
- Catalog content follows Dell's public PowerMax spec sheet, written for
  someone with infrastructure background but no enterprise-storage vocabulary
  — DME, SRDF, SnapVX, FICON, zHyperLink, vault-to-flash, memory config,
  Flexible RAID, and service levels are spelled out where they appear.

The subject is a **rack-scale, scale-out array**, which is the twist versus
the 2U PowerStore: the "chassis anatomy" is a single node-pair *engine* (the
scale-out building block) plus its drive enclosure, and the bring-up trace
gains a **fabric** phase — the drives are not on either director's bus, so the
InfiniBand fabric must come up before drive discovery.

## 2. Architecture

Same split as `GPU/`, `DellPowerEdgeR760/`, and `DellPowerStore/`: a **pure
FastAPI backend engine** and a **React/Vite frontend** in the Dell
clean-design skin.

- The backend emits the whole bring-up sequence as a deterministic
  `PowerOnState[]` trace — plain data, no timers, no IO in `engine.py`.
- The frontend fetches the trace and **owns the playback clock**
  (`setInterval` in `App.tsx`, never in the engine). Run/Step/Reset/Speed work
  exactly like the GPU simulator; states with `cycleCost > 1` (PowerMaxOS
  boot, pool assembly) get UI dwell so slow stages *feel* slow.
- The node-pair anatomy, the component catalog, and the use cases are
  **backend data** (`anatomy.py`, `catalog.py`, `usecases.py`), not frontend
  code. New regions/options/use cases are data edits; the SVG renderer
  (`ChassisView.tsx`) draws whatever it is sent.

```
backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
frontend/  src/{api,types}.ts, App.tsx (power-on page + clock), components/
scripts/   start_backend.sh (:8005), start_frontend.sh (:5178), start_all.sh, stop_all.sh
```

Endpoints: `GET /api/health`, `/api/anatomy` (single `ChassisAnatomy`),
`/api/poweron` (`{trace: PowerOnState[]}`), `/api/catalog`
(`CatalogCategory[]`), `/api/usecases` (`UseCase[]`).

Ports are offset from the GPU app (8000/5173), the R760 (8001/5174),
PowerStore (8002/5175), Alienware (8003/5176), and iDRAC (8004/5177) so all
apps can run at once.

## 3. Data models (all camelCase over the wire, `CamelModel` base)

Same shapes as `DellPowerStore/`, with a PowerMax-specific enum vocabulary:

- `ChassisRegion.kind` ∈ `storage · vault · cache · cpu · fabric · io ·
  power · cooling · battery · management · board`.
  - `vault` — NVMe SED vault-to-flash modules (cache is dumped here on power
    loss), distinct from the `battery` standby power supply (SPS).
  - `cache` — the per-node DRAM PowerMax calls "cache"/global memory.
  - `fabric` — InfiniBand Dynamic Fabric adapters + the shared interconnect.
- `PowerOnState.phase` ∈ `off · power · vault · boot · fabric · drives ·
  pool · services · online`.

The floorplan's defining feature is **A/B symmetry**: every per-node region id
ends in `-a` or `-b` (`cpu-a`/`cpu-b`, `vault-a`/`vault-b`, `fabric-a`/
`fabric-b`, ...), because a node pair holds two mirror-image directors. The
shared `fabric-bus` region (the Dynamic Fabric) carries no node suffix, and
`dme` (the drive enclosure) is a single shared region.

## 4. Bring-up sequence & invariants

Phase order, never regressing:

```
off → power → vault → boot → fabric → drives → pool → services → online
```

1. **off** — AC present at the cabinet's intelligent PDUs, 0 W.
2. **power** — PSUs energize (no power button), SPS self-tests (the array
   won't accept writes until it knows cache can be vaulted through a power
   loss), fans spike then settle. Both directors wake in parallel.
3. **vault** — each director validates its vault-to-flash modules and, if the
   last shutdown was dirty, restores cache from flash before serving I/O.
4. **boot** — each director boots PowerMaxOS 10 (Xeons power, DRAM cache
   tested) — the longest single stage, largest `cycleCost`.
5. **fabric** — the InfiniBand Dynamic Fabric comes up and the two directors
   find each other; cache mirroring and heartbeat now cross the fabric.
6. **drives** — the DME's dual-ported NVMe drives are discovered *over the
   fabric* (both directors, and on the 8500 every node pair, reach every
   drive — why the fabric phase must precede this one).
7. **pool** — Flexible RAID assembles the storage resource pool from drive
   slices with distributed spare capacity.
8. **services** — data-service engines (global inline data reduction, SnapVX,
   SRDF), front-end ports (FC / FC-NVMe / iSCSI / NVMe-TCP / FICON /
   zHyperLink), Unisphere for PowerMax.
9. **online** — serving block / file / mainframe I/O.

Enforced by `backend/tests/test_engine.py` (keep green):

- Steps are sequential from 0; `elapsedSeconds` strictly increases.
- Phase order is monotonic through the sequence above; all 9 phases appear.
- `powerWatts >= 0` (0 at "off", > 0 at "online"); `fanPercent` in [0, 100].
- Every `activeRegions` id exists in the anatomy; `cycleCost >= 1`, and the
  PowerMaxOS boot step has the strictly-largest cycle cost.
- **Fabric before drives:** the first `fabric`-phase step precedes the first
  `drives`-phase step (the drives hang off the fabric).
- **Dual-node symmetry:** in the `power`, `vault`, and `boot` phases, every
  lit `-a` region lights its `-b` twin — the directors bring up in lockstep.
- `engine.py` imports nothing beyond `models` (AST-checked) — pure data.

`tests/test_anatomy.py` holds the geometry invariants (unique ids, in-bounds,
no overlaps, A/B twins share kind and size, exactly one `storage`/DME region,
every `RegionKind` exercised, credited photos when present);
`tests/test_catalog.py` guarantees the catalog and use cases stay resolvable
(unique option ids, real region ids, every use-case config points at a real
category + option).

## 5. Pages

1. **Power-on** (`/`) — the node-pair floorplan lit region-by-region as the
   trace plays; controls, watts/fan/elapsed counters, per-step explanation.
2. **Inside the engine** (`#anatomy`) — hover/click the floorplan for
   per-region descriptions, specs, and sources.
3. **Components & options** (`#components`) — the configuration menu (array
   family, node pairs, director CPUs/memory config, cache, drives, DME,
   Flexible RAID, Dynamic Fabric, front-end I/O, vault & standby power,
   PowerMaxOS software, management, power & PDUs, cabinet & dispersion), each
   category tied to its home region in the engine.
4. **Use cases** (`#usecases`) — mainframe + open-systems consolidation,
   mission-critical database with zero-RPO SRDF/Metro, cyber-resiliency vault
   — each with a resolvable build sheet and outcomes.

## 6. Roadmap ideas

- Scale-out view: animate adding node pairs (1→8) and DMEs, showing the
  Dynamic Fabric fan out and effective capacity / core count grow.
- Failure scenarios as alternate traces: pull a director (the partner carries
  the array over the fabric), pull a PSU, fail a drive (Flexible RAID rebuilds
  from every remaining drive at once), lose AC (watch the SPS drive a
  vault-to-flash flush).
- SRDF/Metro view: two arrays active/active across sites, zero-RPO writes
  acknowledged at both.
- Capacity / data-reduction calculator: pick drives + RAID + the 5:1 (open) /
  3:1 (mainframe) guarantee, get effective capacity; 2500 vs 8500 compare.
- Product photos: add credited local images (as PowerStore does) once a
  licensed set is available; the anatomy already renders `photo` when present.
- More components as sibling top-level directories per the repo pattern.
