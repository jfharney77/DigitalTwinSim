# PhysicsXR — PowerEdge XR rugged-edge physics simulator

Product #2 of `physics_specs/10-additional-products.md`: the Dell
PowerEdge XR-series (XR8000 sled-based, XR4000 stackable) as an
interactive physics model. Built on the `DellPowerEdgeR760Thermal/`
template — deliberately, because that is the product story:

**The one idea: the R760's thermal engine with the environment sliders
unlocked to hostile ranges.** A data-hall server's inlet slider stops at
45 °C; this one runs −25…65 °C, accumulates dust on a front filter over
sim-months (raising the airflow resistance the fan wall must overcome, so
the same cooling costs more rpm and rpm costs its cube in watts), exposes
a vibration class that taxes spinning drives and spares SSDs, and hangs
off a single-phase site feed that browns out — where ride-through is
arithmetic (I = P/V against the PSU input limit), so the same sag idles
through at 2 A and trips at full load.

## Run

```
./PhysicsXR/scripts/start_all.sh    # backend :8040 background, frontend :5213 foreground
./PhysicsXR/scripts/stop_all.sh
```

- Backend tests: `cd PhysicsXR/backend && . .venv/bin/activate && python -m pytest -q`
- Frontend build: `cd PhysicsXR/frontend && npm run build`
- Vite proxies `/api` → `http://localhost:8040` (`API_TARGET` overrides).

`POST /api/simulate` takes a Scenario (config + workload dials +
environment + timed events) and returns Validation[] + SimState[] trace +
LogEntry[] + Summary; `GET /api/simulate` runs the default (cell-site
build, RAN workload). Other endpoints: `/api/anatomy`, `/api/constants`,
`/api/presets/{configs,workloads}`, `/api/scenarios`, `/api/explain`,
`/api/levels`. The engine is pure (AST-checked: no fastapi/time/random/
IO); the playback clock lives in the frontend.

## Invariants (pytest, house style)

- **Power balance every tick**: component powers sum to DC; AC = DC ÷
  η(load) on the Titanium-class curve.
- **Heat balance at steady state**: ΔT = DC/(ṁ·cp) — the IR7000 identity
  inside one short-depth box.
- **Phoenix throttles where Fargo idles its fans** — one config, two
  climates (the spec's headline scenario).
- **The fouled filter throttles where a clean one survives** the same
  heat wave; fouling costs fan power at constant work.
- **The same brownout rides through at idle and trips at full load**;
  deep sags are lights-out regardless.
- **Vibration taxes HDDs and spares SSDs** — a performance tax, not a
  failure event.
- The rated envelopes (−5…55 °C standard, −20…65 °C select extended) are
  pinned as *documented, not estimated* constants — as are the XR8000's
  205 W CPU ceiling (195 W in the 65 °C classes), its eight DIMM slots,
  and the altitude derating (from 900 m; 1 °C per 80 m in the −5…55 °C
  class, 1 °C per 58 m in the extended class).

## Honesty

Sourced facts (fact-checked 2026-09 against the Dell XR-Series spec sheet,
Jan 2026 Rev. A01, the XR8000 spec sheet, and the XR8000r/XR8610t/XR8620t
Technical Guide — all cited in `/api/anatomy` sources): the −5…55 °C
standard envelope; the −20…65 °C extended envelope, which Dell offers only
on the 2U XR8620t sled with CPUs to 195 W, dual extended-temperature PSUs,
and the Heater Manager option for cold starts; "MIL-STD tested and NEBS
Level 3" positioning (Dell's wording — the XR8000 guide itself lists only
the telco standards); the 205 W CPU maximum and its 125/150/185/205 W SKU
classes; eight DDR5 slots per XR8000 sled and four DDR4 per XR4000 sled;
four fans in the 1U sled; altitude derating from 900 m. Everything else —
fouling rates, vibration derates, fan curves, PSU input margins, XR4000 CPU
wattage classes — is an estimate and is labeled as such in
`backend/app/constants.py`, through to the UI.

**Where the model is a composite, not a Dell sled:** the real XR8000 and
XR4000 take M.2 flash only, so the HDD build is a thought experiment; the
XR8000's dust filter is an optional chassis bezel (otherwise Dell asks the
cabinet to filter); its two PSUs live in the chassis and feed up to four
sleds; and its AC supplies are 1400 W (1050 W at 100–120 V) and 1800 W
(200–240 V only) — the 800 W and 1100 W units are −48 V DC. The sim keeps
one sled, one AC feed, and PSU sizes as classes.

**What we don't model:** CFD; per-core DVFS; cold starts (Dell's guide
gives the CPU, chipset, and DIMMs 0 °C minimums and forbids a cold start
below +5 °C without Heater Manager — the real reason the lower rating
exists); condensation;
corrosion; filter media chemistry; the −48 V DC telecom feed (the sag
model is single-phase AC); acoustics. Correct relationships and orders
of magnitude, not a service manual.

## Companions

- `DellPowerEdgeR760Thermal/` — the template engine, in its native
  data hall (8030/5203).
- `DellPowerEdgeR760/` — what happens when a server like this turns on.
- `DellNativeEdge/` — who manages a thousand of these without visiting
  any of them.
- `DellTelecomBlocks/initial_spec.md` — the unbuilt narrative twin whose
  cell-site story this app gives physics to.
