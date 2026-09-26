# PhysicsDisplay — Dell UltraSharp display physics simulator

Product #7 of `physics_specs/10-additional-products.md` (Archetype A-lite
+ F), deliberately the smallest app in the physics suite — the spec calls
the display "a small module, not a full sim", and this app takes that at
its word: one page, one panel, one idea.

**The one idea:** panel power = maximum backlight × brightness × lit
fraction — and whether the *lit fraction* matters at all is a hardware
question. An edge-lit strip (U2723QE-class, "edge-27") lights the whole
field no matter what the picture shows; a mini-LED array (UP3221Q-class,
"miniled-32", 2,000 local-dimming zones) lights only what the content
needs. Dark mode saves real watts on one and almost none on the other.
The tests pin both halves.

Around that sit three honest satellites:

- **The hub is most of the nameplate.** The "220 W maximum" monitor is a
  display of a few tens of watts (Dell lists 25.9 W on-mode; the model
  reaches ~38 W at full brightness) plus a 90 W USB-C laptop charger
  with conversion loss.
  Delivered watts leave over the cable: `heat = DC − delivered`, asserted
  per tick alongside the suite's power-balance identity
  (`electronics + backlight + delivered + loss = DC`, `AC = DC ÷ η`).
- **Acoustics = silence.** No fans, no pumps, nothing moving — the M12
  module's degenerate case, shipped as one sentence and a pinned test
  (`test_there_is_no_cooling_region`), not a gauge.
- **The lifetime-carbon ledger.** Embodied carbon from Dell's PCF
  datasheets (27″ and 32″ class proxies), use-phase computed from the
  scenario's duty cycle and grid intensity, with the Circular Design
  closure rule as pytest: embodied + use = lifetime, shares sum to 100.
  The instructive contrast with a laptop (use-phase 12% of lifetime,
  per Dell's Latitude E7440 PCF whitepaper) is also a test: at desk duty the
  monitor's use share must exceed it. The portfolio version of this
  ledger is `DellCircularDesign/initial_spec.md`.

## Run

```
./PhysicsDisplay/scripts/start_all.sh   # backend :8045 background, frontend :5218 foreground
./PhysicsDisplay/scripts/stop_all.sh
```

- Backend tests: `cd PhysicsDisplay/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend build: `cd PhysicsDisplay/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8045` (`API_TARGET` overrides).
- `POST /api/simulate` takes a Scenario (panel config + lifecycle
  assumptions + timed events); `GET /api/simulate` runs the default.
  Other endpoints: `/api/anatomy`, `/api/constants`, `/api/presets/models`,
  `/api/scenarios`, `/api/explain`, `/api/levels`, `/api/health`.

## Architecture

The R760Thermal template, scaled down: pure engine
(`backend/app/engine.py`, AST-checked — no fastapi/time/random/IO),
constants with units + source and estimates flagged through to the UI
(`constants.py`), validation rules with citations (`validation.py`), a
panel map as backend data (`anatomy.py` — the screen must dominate the
geometry, pinned), guided scenarios + Explain mode (`presets.py`), and
the repo-shared reading-level mechanism (`leveling.py`, byte-for-byte;
levels 1/3/5 authored on the teaching prose). The frontend owns only the
playback clock; mid-run actions (sleep, dock a laptop) become timed
events, keeping every run reproducible.

The mini-LED zone grid in the UI draws 200 cells for the 2,000 real zones
(10× scale, labeled on the drawing) with a deterministic hash pattern —
no randomness on either side of the wire.

## What we don't model

Panel aging and LED lumen depreciation, ambient-light sensors, per-zone
halo/blooming optics, pixel-level content (four content profiles stand in
for real frames), power-factor behavior at the wall, and disposal
logistics beyond the PCF end-of-life figure. Backlight maxima are
estimates sized against Dell's published figures (U2723QE 25.9 W on-mode,
220 W max, 0.3 W standby; UP3221Q 68.3 W on-mode, 380 W max) — the model's
~38 W full-brightness figure for the 27-inch class is its own estimate, as
is the ~400 cd/m² SDR ceiling behind the HDR boost. Embodied carbon uses
the nearest published PCF class as a proxy, not a per-SKU figure: the
S2722QC (27-inch 4K) and the P3424WE (a 34-inch curved ultrawide standing
in for the 32-inch mini-LED, which has no published PCF). Both classes are
modeled as fanless; the UP3221Q's internal cooling was not verified
against a Dell document. Every constant carries a source tag; readouts that
derive from estimates are badged in the UI.

## Sources

- Dell U2723QE product page (25.9 W on-mode, 220 W max, 0.3 W standby,
  90 W USB-C PD)
- Dell UP3221Q product page (2,000 mini-LED zones, DisplayHDR 1000) and
  user's guide (68.3 W on-mode, 380 W max)
- Dell Product Carbon Footprint datasheets: S2722QC (638 kgCO2e, use
  33.8%), P3424WE (777 kgCO2e, use 33.6%); Latitude 7490 datasheet
  (241 kgCO2e) and Latitude E7440 whitepaper (use 12%) for the laptop
  contrast
