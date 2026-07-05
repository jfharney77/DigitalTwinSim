# DellPowerStore — spec

## 1. Purpose & scope

Teach a technically skilled reader who is *new to the product* what a Dell
PowerStore is: an all-NVMe unified block + file storage appliance with **two
active-active controller nodes** in one 2U enclosure. What sits inside the
box, what actually happens between connecting AC and serving I/O (there is no
power button — applying AC *is* the power-on), what components and options can
be configured, and what real deployments look like.

Guardrails (mirror the GPU app's spirit):

- **Not a firmware/PowerStoreOS simulator.** Timings, wattages, and fan
  percentages are illustrative — the goal is a correct *mental model* of the
  bring-up sequence, not second-accurate behavior.
- **The floorplan is stylized**, composed from Dell's product photos
  (`frontend/public/powerstore1..4.webp`) and public documentation, placed in
  a normalized 100×46 coordinate space. Not mm²-accurate.
- Catalog content follows Dell's public PowerStore spec sheet, written for
  someone with infrastructure background but no storage-array vocabulary —
  NVRAM, vaulting, active/active, NVMe-oF, and Metro Volume are spelled out
  where they appear.

## 2. Architecture

Same split as `GPU/` and `DellPowerEdgeR760/`: a **pure FastAPI backend
engine** and a **React/Vite frontend** in the Dell clean-design skin.

- The backend emits the whole bring-up sequence as a deterministic
  `PowerOnState[]` trace — plain data, no timers, no IO in `engine.py`.
- The frontend fetches the trace and **owns the playback clock**
  (`setInterval` in `App.tsx`, never in the engine). Run/Step/Reset/Speed work
  exactly like the GPU simulator; states with `cycleCost > 1` (PowerStoreOS
  container boot, pool assembly) get UI dwell so slow stages *feel* slow.
- Chassis anatomy, the component catalog, and the use cases are **backend
  data** (`anatomy.py`, `catalog.py`, `usecases.py`), not frontend code. New
  regions/options/use cases are data edits; the SVG renderer
  (`ChassisView.tsx`) draws whatever it is sent.

```
backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
frontend/  src/{api,types}.ts, App.tsx (power-on page + clock), components/
scripts/   start_backend.sh (:8002), start_frontend.sh (:5175), start_all.sh, stop_all.sh
```

Endpoints: `GET /api/health`, `/api/anatomy` (single `ChassisAnatomy`),
`/api/poweron` (`{trace: PowerOnState[]}`), `/api/catalog`
(`CatalogCategory[]`), `/api/usecases` (`UseCase[]`).

## 3. Data models (all camelCase over the wire, `CamelModel` base)

Same shapes as `DellPowerEdgeR760/`, with two PowerStore-specific enums:

- `ChassisRegion.kind` ∈ `storage · nvram · cpu · memory · io · power ·
  cooling · battery · management · board`.
- `PowerOnState.phase` ∈ `off · power · boot · drives · cluster · services ·
  online`.

The floorplan's defining feature is **A/B symmetry**: every per-node region id
ends in `-a` or `-b` (`cpu-a`/`cpu-b`, `bbu-a`/`bbu-b`, `iomod-a1`/`iomod-b1`,
...), because the enclosure holds two mirror-image node canisters that share
the 25-slot dual-ported NVMe drive bay and the 4-slot NVRAM write cache.

## 4. Bring-up sequence & invariants

Phase order, never regressing:

```
off → power → boot → drives → cluster → services → online
```

1. **off** — AC connected to both PSUs, 0 W.
2. **power** — PSUs energize (no power button), BBUs self-test (the array
   won't accept writes until it knows cached data can be vaulted through a
   power loss), fans spike then settle.
3. **boot** — both nodes' firmware starts independently; PowerStoreOS (an
   embedded Linux running the storage stack as containers) boots on each —
   the longest single stage, largest `cycleCost`.
4. **drives** — each node enumerates all 25 dual-ported NVMe drives (both
   nodes see every drive — why failover is instant); the NVRAM drives come up
   as the mirrored write cache.
5. **cluster** — the nodes handshake over the internal interconnect
   (heartbeat + cache mirroring), then the dynamic resiliency engine
   assembles the storage pool from drive slices.
6. **services** — data-service containers (always-on inline dedup +
   compression, snapshots, thin provisioning), front-end ports (FC / iSCSI /
   NVMe-oF / NFS / SMB), PowerStore Manager on the cluster IP.
7. **online** — serving I/O active-active from both nodes.

Enforced by `backend/tests/test_engine.py` (keep green):

- Steps are sequential from 0; `elapsedSeconds` strictly increases.
- Phase order is monotonic through the sequence above; all 7 phases appear.
- `powerWatts >= 0` (0 at "off", > 0 at "online"); `fanPercent` in [0, 100].
- Every `activeRegions` id exists in the anatomy; `cycleCost >= 1`, and the
  PowerStoreOS boot step has the largest cycle cost.
- **Dual-node symmetry:** in the `power` and `boot` phases, every lit `-a`
  region lights its `-b` twin — the nodes bring up in lockstep.
- `engine.py` imports nothing beyond `models` (AST-checked) — the trace is
  pure data.

`tests/test_anatomy.py` holds the geometry invariants (unique ids, in-bounds,
no overlaps, A/B twins share kind and size, exactly one NVRAM region, photos
only from the local `/powerstore*.webp` set); `tests/test_catalog.py`
guarantees the catalog and use cases stay resolvable (unique option ids, real
region ids, every use-case config points at a real category + option).

## 5. Pages

1. **Power-on** (`/`) — the enclosure floorplan lit region-by-region as the
   trace plays; controls, watts/fan/elapsed counters, per-step explanation.
2. **Inside the chassis** (`#anatomy`) — hover/click the floorplan for
   per-region descriptions, specs, sources, and the real product photos.
3. **Components & options** (`#components`) — the configuration menu
   (appliance tiers, drives, NVRAM, expansion, clustering, I/O modules,
   mezzanine, power, software, management, protection, rack), each category
   tied to its home region in the enclosure.
4. **Use cases** (`#usecases`) — VMware consolidation, database
   consolidation, edge block + file — each with a resolvable build sheet and
   outcomes.

## 6. Roadmap ideas

- Failure scenarios as alternate traces: pull a node (the survivor takes all
  volumes over the shared drive bay), pull a PSU, fail a drive (the dynamic
  resiliency engine rebuilds from every remaining drive at once).
- Metro Volume view: two appliances active-active across sites, zero-RPO
  writes acknowledged at both.
- Capacity / data-reduction calculator: pick drives + the 4:1 reduction
  guarantee, get effective capacity; scale-up (ENS24) vs scale-out compare.
- More components as sibling top-level directories per the repo pattern.
