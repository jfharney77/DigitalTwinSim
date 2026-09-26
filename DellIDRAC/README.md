# iDRAC9 Inside

Interactive web app that visualizes the **iDRAC9 baseboard management
controller** — the always-on service processor embedded in every PowerEdge
server — as a digital twin. It shows what wakes up *before* the server does:
iDRAC's own firmware bring-up, its internal architecture, its licensed
capabilities, and the management scenarios it enables. The fifth component in
the DigitalTwinSim family, alongside the GPU, PowerEdge R760, PowerStore, and
Alienware twins, and the natural companion to the R760 power-on twin (iDRAC is
the "brain" that orchestrates that boot).

## Architecture

Same as the R760 twin: a Python/FastAPI backend owns the **deterministic
bring-up engine** and all content as data; the React frontend fetches the
`BringUpState[]` trace and animates it on its own clock (the UI owns the
clock — a core spec invariant).

```
backend/   FastAPI + pure engine
  app/
    models.py    SubsystemMap, Block, BringUpState (pydantic; camelCase JSON)
    anatomy.py   the iDRAC9 block diagram (blocks in a normalized space)
    engine.py    pure simulate() -> BringUpState[]  (AC → ready controller)
    catalog.py   license tiers + capabilities (Basic/Express/Enterprise/Datacenter)
    usecases.py  management scenarios (lights-out deploy, fleet, telemetry)
    main.py      FastAPI: /api/health, /api/anatomy, /api/bringup, /api/catalog, /api/usecases
  tests/         trace + geometry + catalog invariant tests

frontend/  React + Vite + TypeScript, Dell clean-design skin
  src/
    api.ts, types.ts
    components/  BlockView (SVG), AnatomyPage, CatalogPage, UseCasePage,
                 BringUpControls, BringUpCounters
    App.tsx      composition root; owns the playback clock

scripts/   start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh
```

## Run it

```bash
./scripts/start_all.sh      # backend :8004 (background) + frontend :5177 (foreground)
./scripts/stop_all.sh       # stop both
```

Open http://localhost:5177. Vite proxies `/api` to the backend on :8004.
Ports are offset from the other twins (GPU 8000/5173, R760 8001/5174,
PowerStore 8002/5175, Alienware 8003/5176) so all five run together.

## Develop

```bash
cd backend && . .venv/bin/activate && python -m pytest -q   # backend tests
cd frontend && npm run build                                 # typecheck / build
```

## Pages

- **Bring-up** — iDRAC's own boot from AC standby to a ready, watching
  controller, animated over the block diagram (the host stays powered off).
- **Inside the controller** — the annotated block diagram: SoC, memory/flash,
  sideband buses, management NIC, remote-presence engines, Root of Trust.
- **Capabilities & options** — the license tiers and what each unlocks.
- **Use cases** — lights-out OS deployment, zero-touch fleet provisioning,
  predictive telemetry at scale.

Content is grounded in Dell's iDRAC9 documentation (see the Sources panel on
the anatomy page); timings and wattages are illustrative, not measured.

## Failure scenario: a firmware update that rolls back

Both traces stamp `elapsedSeconds` at the end of each step, so a step's length
is its stamp minus the one before it. The Telemetry panel shows that length and
names the longest step (Lifecycle Controller init in the bring-up, the flash
write in the rollback). The picker lists this scenario as "Firmware rollback".

The sim page has a scenario picker. The second trace is the iDRAC firmware
update lifecycle and its failure, the loudest iDRAC theme in the community
threads collected in `RESEARCH_ASSETS.md`: upload, signature verification,
staging to the inactive flash partition, the iDRAC restart, a failed boot check
on the new image, automatic rollback to the previous partition, and iDRAC back
on the old version with a Lifecycle log entry. The host is powered on and
running on every step. Management is lost for a while; the workload is not.

- Deep link: `/#scenario=firmware-update-rollback`, which composes with the
  existing links (`/#scenario=firmware-update-rollback&phase=bootcheck`,
  `&step=7`). Phases: `ready → upload → verify → stage → reboot → bootcheck →
  rollback → restored`.
- API: `GET /api/bringup?scenario=firmware-update-rollback` serves it on the
  same route and the same `BringUpState` model, extended with optional fields
  (`hostPowered`, `activePartition`, `runningVersion`, `writingPartition`,
  `signatureVerified`, `bootableImages`, `managementReachable`,
  `managementOutageSeconds`, `failedRegions`, `logEntry`). The bring-up never
  sets them and the route drops unset fields, so `GET /api/bringup` returns
  what it always did. `GET /api/scenarios` lists the traces with their sources.
- Engine: `simulate_firmware_rollback()` in `app/engine.py`, pure like
  `simulate()`. Scenario metadata and sources live in `app/scenarios.py`.
- Invariants (`tests/test_firmware_rollback.py`): the host power state never
  changes; nothing is written before the signature verifies, and never to the
  running partition; there is always at least one bootable image, and the trace
  reaches that floor twice (during the write, and after the rejected image);
  the management outage is real, tracks the clock, and stays under
  `MAX_MANAGEMENT_OUTAGE_S`; the failed flash block stays marked to the end,
  because a rollback leaves one good image until the administrator re-stages
  the update; and the bring-up trace is pinned unchanged.
- The hero counter is **management outage** in seconds. The block holding the
  rejected image is drawn dashed in the error colour (`--dell-error`).

What is sourced: Dell signs firmware packages with SHA-256 hashing and
2048-bit RSA and aborts one that fails validation with a Lifecycle Controller
log error; iDRAC keeps two operating-system images "to ensure a bootable
iDRAC"; an iDRAC update or rollback needs no server reboot, and an iDRAC reset
does not affect the running operating system (KB 000126703); SD card or TFTP
recovery is the documented last resort. Sourced with a qualification: RED007,
unable to verify update package signature, is published in an iDRAC7 and
iDRAC8 article, and the SUP0516, RAC0182, SUP0520 sequence is published in
KB 000343194, which describes an iDRAC10 case on 17G servers — the message
identifiers are Dell's, the generations are not this twin's, and the prose
says so at both steps. What is inferred: that the switch to the other image is
automatic. Dell's two-image KB implies it and does not describe the mechanics.
Reported rather than documented: the fans ramping up while iDRAC is away. Dell
documents a full-speed ramp as a sign of a hard iDRAC reset, not of an update,
so the reboot step calls it reported behaviour. What is illustrative: every
timing, the version strings, the partition letters, the cause of the failed
boot check (a staged copy damaged in the flash write), the single boot
attempt, and the RAC0182 reason text. Real failures do not always end this
cleanly: KB 000343194 includes a case that needed AC power removed, and the
last step of the trace says so. The guided tour still
narrates the bring-up only; opening it switches the scenario back.
