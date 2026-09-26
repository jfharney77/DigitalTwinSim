# DellAlienware — gaming-laptop power-path twin

A digital twin of the Alienware m18's AC power path: what happens inside when
the adapter goes in. Pure FastAPI engine (`backend/app/engine.py`), React/Vite
frontend that owns the playback clock. The full design is in
`initial_spec.md`.

- Run: `./scripts/start_all.sh` (backend :8003, frontend :5176). Stop: `./scripts/stop_all.sh`.
- Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
- Frontend build: `cd frontend && npm run build`
- Browser smoke: `scripts/smoke.sh DellAlienware` from the repo root.

## Failure scenario: charging diagnostics

`/#scenario=charge-taper-diagnostics` plays a second trace beside the plug-in
path. It models the support genre "it stopped charging at 80%" and "it charges
slowly": one complaint with four causes, only one of which is a fault.

| Phase | What the owner sees | What it is | Recovery |
|---|---|---|---|
| `cap` | Stuck at 80%, AC Adapter line correct | BIOS charge mode (Primarily AC Use) | Switch to Standard, if full capacity is wanted |
| `taper` | Slow past 80%, cool brick | Constant-voltage taper: the cells set the pace | None; it is normal |
| `heat` | Not charging after gaming, below full | Pack over its charge-temperature limit | Airflow and time; charge resumes unprompted a few degrees under the limit |
| `swap` | Not charging, machine slow, AC Adapter: Unknown | PSID handshake failed | Reseat, check the centre pin, use the Dell adapter |

Each state carries what the owner could read off the machine (`adapterReadout`,
`batteryReadout`, `chargeMode`, `packTempC`) and the diagnosis, `chargeLimiter`,
which is the hero readout on the sim page. Parts that are stopping the charge
(`failedRegions`: the pack while too hot, the DC-in jack while the handshake
fails) are drawn in the error colour. The charge cap and the taper draw nothing
as failed, because nothing has.

How it is served:

- `POST /api/simulate?scenario=charge-taper-diagnostics` returns the walk. With
  no `scenario` parameter (or `plug-in`) the endpoint returns the plug-in trace
  byte for byte as before. `GET /api/scenarios` lists both.
- The walk lives in `backend/app/diagnostics.py`, pure under the same AST rules
  as the engine. Every charge decision goes through one gate (`_Walk.charge`),
  which checks in a technician's order: adapter trusted, pack cool enough,
  limit reached, budget left, then what the cells accept.
- It is a fixed script. Laptop and adapter selections apply (a USB-C or
  unrecognized selection falls back to the default barrel adapter, since the
  walk needs a PSID handshake that works before one that fails); start level,
  thermal mode and workload do not.
- Deep links compose: `#scenario=charge-taper-diagnostics&phase=heat`,
  `&step=16`. Choosing a trace resets the playback cursor.

Invariants, in `backend/tests/test_diagnostics.py`: the energy identity on every
state; charge power never rises once the pack is on the constant-voltage leg,
including across the heat pause and the adapter swap; zero charge while the pack
is over its limit, with adapter headroom proven to exist; the thermal inhibit
holds until the re-arm temperature (hysteresis), with a state shown inside the
band; the battery status line reads the same "Not charging" for three different
limiters; an unrecognized
adapter powers the system and never charges; no state charges and discharges at
once; and a digest pinning the plug-in trace's numbers to what they were before
the walk existed.

Sourced: the charge modes and the BIOS AC Adapter line (Dell KB 000123069,
000125125), hybrid power (KB 000143915), the constant-current/constant-voltage
shape with 3-5% termination (Battery University BU-409), and the 0-45 °C
lithium-ion charge window (BU-410). Dell does not publish this machine's
firmware thresholds, so the 80% knee, the 45 °C trip, the 42 °C re-arm, and
every watt and percentage are illustrative. Dell's wording for an unidentified
adapter is that the battery may not charge or may charge slowly; the walk
models the no-charge case, as the plug-in trace already did. The guided tour still narrates the plug-in trace
only.
