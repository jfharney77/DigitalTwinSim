# DellAlienware — spec

## 1. Purpose & scope

Teach a technically skilled reader who is *new to the product* what happens
inside an Alienware m18 when you plug it in: how the adapter announces itself
over the center ID pin, how the embedded controller decides a power budget,
how the battery charges (and why it sometimes discharges while plugged in),
and where each of those events physically happens on the motherboard.

Guardrails (mirror the GPU app's spirit):

- **Not an EC/firmware simulator.** Wattages, charge rates, fan percentages,
  and stage timings are illustrative — the goal is a correct *mental model*
  of the AC power path, not measured behavior. The numbers are anchored to
  Dell's public KB articles and the m18 owner's manuals (280 W / 360 W
  adapters at 19.5 V, 97 Wh 6-cell battery, 175 W GPU TGP, ~5%/h hybrid
  drain, 94–100% hold band, <20% hybrid cutoff) — sources are listed in the
  research notes and carried into the API's `sources` fields.
- **The floorplan is stylized**, traced from the real service photo
  (`frontend/public/alienware-interior.jpg` — laptop opened from below) and
  placed in a normalized 100×62 coordinate space. Not mm²-accurate.
- Content is written for someone with hardware background but no Dell
  vocabulary — EC, PSID, ExpressCharge, TGP, AWCC, and hybrid power are
  spelled out where they appear.

## 2. Architecture

Same split as `GPU/`: a **pure FastAPI backend engine** and a **React/Vite
frontend** in the Dell clean-design skin.

- The backend emits the whole plug-in sequence as a deterministic
  `PowerState[]` trace — plain data, no timers, no IO in `engine.py`.
- The frontend fetches the trace and **owns the playback clock**
  (`setInterval` in `App.tsx`, never in the engine). Run/Step/Reset/Speed
  work exactly like the GPU simulator; states with `cycleCost > 1` (the
  1-Wire PSID handshake, the constant-current charge bulk) get UI dwell so
  slow stages *feel* slow.
- The laptop catalog, the interior anatomy, and the use cases are **backend
  data** (`catalog.py`, `anatomy.py`, `usecases.py`), not frontend code. New
  laptops, adapters, regions, or walkthroughs are data edits; the SVG
  renderer (`AnatomyView.tsx` / `PowerPathView.tsx`) draws whatever it is
  sent.

```
backend/   app/{models,catalog,anatomy,engine,usecases,main}.py + tests/
frontend/  src/{api,types}.ts, App.tsx (power page + clock), components/
scripts/   start_backend.sh (:8003), start_frontend.sh (:5176), start_all.sh, stop_all.sh
```

Endpoints: `GET /api/health`, `/api/catalog` (`LaptopProfile[]`),
`/api/catalog/default`, `/api/anatomy` (`Anatomy[]`),
`/api/anatomy/{id}` (404 if unknown), `/api/usecases` (`UseCase[]`),
`POST /api/simulate` (`SimulateRequest` → `SimulateResponse`; 422 for an
unknown `profileId`/`adapterId`).

## 3. Data models (all camelCase over the wire, `CamelModel` base)

- `LaptopProfile` — id, name, family, cpu/`cpuMaxW`, gpu/`gpuTgpW`,
  `battery` (`wh`, `cells`, `voltage`, `expressCharge`), `adapters:
  AdapterOption[]`, `defaultAdapterId`, `idleW`, `anatomyId` (ties the
  profile to its floorplan), description.
- `AdapterOption` — id, name, watts, `connector` (`barrel | usbc`), voltage,
  amps, `recognized` (false models a failed PSID handshake / damaged ID
  pin), description. Every profile carries at least one unrecognized option
  so the throttled path is always reachable.
- `Scenario` — `profileId`, `adapterId`, `startBatteryPct` (0–100),
  `thermalMode` (`quiet | balanced | performance | fullSpeed`), `workload`
  (`idle | gaming | fullLoad`).
- `PowerState` — one trace entry: cycle (== index), phase, `stageId`
  (stable kebab-case, from the research stage machine S0–S10), label,
  description, `activeRegions: string[]` (region ids lit on the floorplan),
  the power split (`acW`, `systemW`, `chargeW`, `batteryW`, `cpuW`, `gpuW`),
  `batteryPct`, `chargeStage` (`idle | precharge | cc | cv | full`),
  `fanPct`, `hybrid`, `stalled`, `cycleCost`.
- `Summary` — `adapterW`, `peakSystemW`, `peakHybridW`, `hybridUsed`,
  `endBatteryPct`, `regime` (`adapter-limited | within-budget | throttled`),
  `minutesTo80Pct` (illustrative ExpressCharge estimate, null when not
  charging), notes.
- `Anatomy` / `Region` — mirror the R760/GPU anatomy shape: normalized
  100×62 canvas, regions with `kind` (`board · power · battery · cooling ·
  memory · storage · io · display · wireless`), stats, sources, overview,
  and a `Photo` (url/caption/credit — the credit line is always rendered).
  Region ids include at least `dc-in`, `ec`, `charger`, `battery`, `cpu`,
  `gpu`, `vram`, `dimm`, `fan-left`, `fan-right`, `heatpipes`, `ssd`,
  `io-left`, `io-right`, `wlan` — these are what `activeRegions` references.
- `UseCase` — id, title, summary, persona, `steps: UseCaseStep[]`
  (title/body/`regionIds`, each id resolvable against the anatomy), outcome,
  sources.

## 4. Phase machine & invariants

Phase order, never regressing:

```
off → detect → handshake → budget → charge → boot → load → steady
```

1. **off** — on battery; the EC idles on standby power (`s0-unplugged`).
2. **detect** — the adapter rectifies mains to 19.5 VDC and the barrel seats
   in the DC-in jack; the EC senses voltage on the rail (`s1-ac-convert`,
   `s2-plug-detect`).
3. **handshake** — the EC reads the adapter's 1-Wire PSID EEPROM over the
   center pin (`s3-psid-handshake`, the dwell stage). A broken ID pin or a
   third-party brick reads as "Unknown".
4. **budget** — the EC and BIOS set the power policy: full performance for a
   recognized full-wattage adapter, capped CPU/GPU and no charging for an
   unknown one; the charger IC switches the system load from battery to the
   adapter rail (`s4-power-budget`, `s5-power-path`).
5. **charge** — Li-ion ramp: precharge → constant-current bulk (the
   ExpressCharge regime, largest `cycleCost`) → constant-voltage taper; a
   full battery enters the 94–100% hold band instead, and an unrecognized
   adapter emits `s6-charge-disabled`.
6. **boot** — power button: rails sequence, fans blip audibly (working as
   designed), POST, Windows + AWCC restore the thermal profile.
7. **load** — the workload ramps in under the chosen thermal mode; when
   CPU+GPU demand exceeds the adapter budget the battery supplements it
   (`s9-hybrid`) instead of throttling — unless the pack is below 20%, where
   hybrid disables and the system throttles.
8. **steady** — equilibrium: the trace ends with the sustained power split
   and fan duty for the scenario.

Enforced by `backend/tests/test_engine.py` (keep green):

- `cycle == index`; phase order is monotonic through the sequence above and
  every trace ends at `steady`.
- **Energy conservation in every state**: `acW + batteryW == systemW +
  chargeW` (±0.5 W); never `chargeW > 0` and `batteryW > 0` at once;
  `hybrid` is true exactly when the battery supplements the adapter.
- `acW <= adapter.watts` always; `batteryPct` stays in [0, 100] and moves in
  the direction of `chargeW`/`batteryW`; `fanPct` in [0, 100];
  `cycleCost >= 1` with the handshake stage `stalled` and dwelled.
- Every `activeRegions` id exists in the profile's anatomy.
- Unrecognized adapter → `regime == "throttled"`, `chargeW == 0` throughout,
  capped `cpuW + gpuW`, and the phase machine still completes.
- `engine.py` imports nothing beyond `models` — `simulate()` is pure and
  deterministic (same scenario, same trace).

`tests/test_anatomy.py` holds the geometry invariants (unique ids, in-bounds,
no overlaps, the contract's required region ids, photo credit present,
camelCase wire format); `tests/test_catalog.py` guarantees the catalog and
use cases stay resolvable (default adapter exists, every profile has an
unrecognized adapter option, adapter physics sane, `anatomyId` resolves,
every use-case `regionIds` entry is a real region).

## 5. Pages

1. **Power path** (`/`) — the plug-in sequence played over a power-path
   diagram; scenario controls (laptop, adapter, start charge, thermal mode,
   workload), live watt counters, per-stage explanation, and the summary
   read-out (regime, peak hybrid supplement, minutes to 80%).
2. **Inside the m18** (`#anatomy`, deep link `#anatomy/<id>`) — the annotated
   interior floorplan; hover/click regions for descriptions and the real
   service photo with its credit line.
3. **Use cases** (`#usecases`, deep link `#usecases/<id>`) — walkthroughs:
   setting up an m18 R2 for a sustained GPU run (adapter recognition, AWCC
   thermal modes, expected hybrid drain), and diagnosing "plugged in, not
   charging" via LED codes and ePSA diagnostics. Each step lights its
   regions on the floorplan.

## 6. Roadmap ideas

- USB-C PD path: model the x14's 130 W Type-C contract negotiation as an
  alternate handshake branch.
- Fault traces: UVP shutdown after running a weak adapter flat, the RTC-reset
  recovery sequence, LED blink-code explorer.
- Charge-mode policies: Primarily AC Use / Adaptive / ExpressCharge Boost as
  scenario options changing the charge phase.
- Thermal view: TCC offset slider and thermal-mode fan curves over time.
- More components as sibling top-level directories per the repo pattern.
