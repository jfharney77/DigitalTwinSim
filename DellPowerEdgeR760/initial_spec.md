# DellPowerEdgeR760 — spec

## 1. Purpose & scope

Teach a technically skilled reader who is *new to the product* what a Dell
PowerEdge R760 is: what sits inside the 2U chassis, what actually happens when
you plug it in and press the power button, what components and options can be
configured into it, and what real deployments look like.

Guardrails (mirror the GPU app's spirit):

- **Not a BIOS/firmware simulator.** Timings, wattages, and fan percentages are
  illustrative — the goal is a correct *mental model* of the power-on sequence,
  not cycle- or second-accurate behavior.
- **The floorplan is stylized**, traced from Dell's own top-down interior
  photo (`frontend/public/r760-interior.webp`), placed in a normalized
  100×46 coordinate space. Not mm²-accurate.
- Catalog content follows Dell's public R760 spec sheet, written for someone
  with hardware background but no Dell vocabulary — iDRAC, PERC, BOSS-N1 and
  OCP 3.0 are spelled out where they appear.

## 2. Architecture

Same split as `GPU/`: a **pure FastAPI backend engine** and a **React/Vite
frontend** in the Dell clean-design skin.

- The backend emits the whole power-on sequence as a deterministic
  `PowerOnState[]` trace — plain data, no timers, no IO in `engine.py`.
- The frontend fetches the trace and **owns the playback clock**
  (`setInterval` in `App.tsx`, never in the engine). Run/Step/Reset/Speed work
  exactly like the GPU simulator; states with `cycleCost > 1` (memory
  training, drive spin-up) get UI dwell so slow stages *feel* slow.
- Chassis anatomy, the component catalog, and the use cases are **backend
  data** (`anatomy.py`, `catalog.py`, `usecases.py`), not frontend code. New
  regions/options/use cases are data edits; the SVG renderer
  (`ChassisView.tsx`) draws whatever it is sent.

```
backend/   app/{models,anatomy,engine,catalog,usecases,main}.py + tests/
frontend/  src/{api,types}.ts, App.tsx (power-on page + clock), components/
scripts/   start_backend.sh (:8001), start_frontend.sh (:5174), start_all.sh, stop_all.sh
```

Endpoints: `GET /api/health`, `/api/anatomy` (single `ChassisAnatomy`),
`/api/poweron` (`{trace: PowerOnState[]}`), `/api/catalog`
(`CatalogCategory[]`), `/api/usecases` (`UseCase[]`).

## 3. Data models (all camelCase over the wire, `CamelModel` base)

- `ChassisAnatomy` — id, name, vendor, formFactor, generation, year,
  width/height (viewBox), `regions: ChassisRegion[]`, stats, sources,
  overview, photo.
- `ChassisRegion` — id, `kind` (one of `storage · cooling · cpu · memory ·
  power · expansion · management · board`), label, x/y/w/h, description,
  optional photo.
- `PowerOnState` — step, phase, label, description,
  `activeRegions: string[]` (region ids lit in the floorplan), powerWatts,
  fanPercent, elapsedSeconds, cycleCost.
- `CatalogCategory` — id, name, blurb, limits, `regionIds` (where in the
  chassis the category lives), `options: CatalogOption[]` (id, name, summary,
  details).
- `UseCase` — id, title, summary, narrative paragraphs,
  `config: UseCaseItem[]` (categoryId/optionId/qty/rationale — a resolvable
  bill of materials), outcomes.

## 4. Power-on sequence & invariants

Phase order, never regressing:

```
off → standby → bmc → poweron → post → boot → os
```

1. **off** — AC connected, 0 W.
2. **standby** — PSUs raise the 12 V standby rail.
3. **bmc** — iDRAC9 boots its embedded Linux and inventories the hardware
   before the host powers on; the server is reachable while "off".
4. **poweron** — main rails enable, fans spike to 100 % ("jet engine"
   moment), voltage regulators sequence the CPU sockets.
5. **post** — CPUs out of reset, UEFI from SPI flash (cache-as-RAM), DDR5
   memory training (longest stage, largest `cycleCost`), PCIe Gen5
   enumeration, staggered drive spin-up, fans settle.
6. **boot** — UEFI boot manager hands off to the BOSS-N1 mirrored M.2 pair.
7. **os** — steady state; iDRAC keeps watching out-of-band.

Enforced by `backend/tests/test_engine.py` (keep green):

- Steps are sequential from 0; `elapsedSeconds` strictly increases.
- Phase order is monotonic through the sequence above; all 7 phases appear.
- `powerWatts >= 0` (0 at "off", > 0 at "os"); `fanPercent` in [0, 100].
- Every `activeRegions` id exists in the anatomy; `cycleCost >= 1`, and
  memory training has the largest cycle cost.
- `engine.py` imports nothing beyond `models` — the trace is pure data.

`tests/test_anatomy.py` holds the geometry invariants (unique ids, in-bounds,
no overlaps, exactly six fans); `tests/test_catalog.py` guarantees the catalog
and use cases stay resolvable (unique option ids, real region ids, every use
case config points at a real category + option).

## 5. Pages

1. **Power-on** (`/`) — the chassis floorplan lit region-by-region as the
   trace plays; controls, watts/fan/elapsed counters, per-step explanation.
2. **Inside the chassis** (`#anatomy`) — hover/click the floorplan for
   per-region descriptions, specs, sources, and the real interior photo.
3. **Components & options** (`#components`) — the configuration menu, each
   category tied to its home region in the chassis.
4. **Use cases** (`#usecases`) — deployment stories with a resolvable build
   sheet and outcomes.

## 6. Roadmap ideas

- Thermal/airflow view: animate front-to-rear airflow, fan zones responding to
  a simulated CPU load slider.
- Failure scenarios: pull a PSU (redundancy event), fail a DIMM (POST maps it
  out), pull a fan (thermal ramp) — each as an alternate trace.
- Config → power-budget calculator: pick catalog options, get estimated draw
  and the PSU size the configurator would require.
- More components as sibling top-level directories per the repo pattern.
