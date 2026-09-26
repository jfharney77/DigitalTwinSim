# PhysicsClient — client-device power & thermal simulator

First app of the physics suite (`physics_specs/07-client-devices.md`,
plan in `physics_specs/BUILD_PLAN.md`): the R760 thermal twin's engine
generalized to the machines that sit on desks and laps. Two product
personalities in one app — **Alienware** (laptop or desktop tower) and
the **Dell Pro Max Plus** mobile workstation with its optional discrete
NPU (the Qualcomm AI 100 PC Inference Card). On the shipping Dell Pro Max
16 Plus that card takes the discrete GPU's slot; the simulator keeps both so
the GPU-vs-NPU comparison runs on one chassis, and says so in the UI. The
promax presets use the real machine's 96 Wh pack and 280 W adapter.

The mechanics servers never meet, each asserted in the tests:

- **PL2 → PL1 burst-then-fade** (τ ≈ 28 s boost window) — the shape that
  defines laptop benchmarks; `fps_minute_1 > fps_minute_15` is a test.
- **The shared thermal budget** — laptop CPU/GPU/NPU share heat pipes;
  the allocator favors the GPU under game load and clips the CPU. The
  desktop tower is the control group: separate coolers, no budget state.
- **The skin cap** — a slow (τ ≈ 120 s) chassis zone with a hard 46 °C
  contact limit that overrides fan logic entirely.
- **Battery arithmetic** — runtime = Wh × health × 0.92 ÷ W, verified
  against the readout; the undersized charger drains the pack while
  plugged in, and the tick-level supply identity
  (adapter + discharge = system + charge) holds in every regime.
- **Tokens per joule** — the LLM preset runs on CPU, GPU, or NPU;
  rate ranks GPU > NPU > CPU, efficiency ranks NPU > GPU > CPU.

## Run

```
./scripts/start_all.sh     # backend :8031 background, frontend :5204 foreground
./scripts/stop_all.sh
```

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

## Brand-map page (`#brands`)

The static explainer from `physics_specs/10-additional-products.md` §8:
Dell's January 2025 client rebrand — **Dell** (consumer, absorbing
XPS/Inspiron), **Dell Pro** (née Latitude/OptiPlex), **Dell Pro Max** (née
Precision), each with Base/Plus/Premium tiers, Alienware left unchanged —
the scheme that names both of this app's products ("Pro Max Plus" = the
workstation brand's Plus tier). Served leveled from `GET /api/brandmap`,
so the reading-level control applies to it like everything else. The 2026
course corrections are labeled by sourcing strength: the XPS revival
(CES 2026) and the return of Precision as "Dell Pro Precision" (Dell's
March 25, 2026 release, which also numbered the business notebooks Dell
Pro 3/5/7) are confirmed by Dell; the model-by-model mapping and any
retirement of the Pro Max name are marked *reported* — `tests/test_brandmap.py` enforces the labeling, the tier
ladder, the placement of "Pro Max Plus", and the twin cross-links.

## Graded labs (`#labs`, `#lab=<id>`)

Three labs on the `docs/LAB_PATTERN.md` recipe (`backend/app/labs.py`, pure;
`GET /api/labs`, `POST /api/labs/{id}/grade`; `tests/test_labs.py`). Every
constraint is a criterion measured from the trace, delivered work is a rate
averaged over the whole run (dark seconds count as zero), and the reference
solutions stay server-side. Work proxies and scores are illustrative. On the
static site the same `labs.py` grades in the browser under Pyodide.

| Lab | Difficulty | The lesson |
|---|---|---|
| `charge-while-you-play` | 1 | The pack only gets the charger's surplus over the system, and the opening PL2/GPU boost sets the peak the charger must cover. |
| `hour-of-tokens` | 2 | The battery divides by system watts, not engine watts: remove the passengers (idle GPU, spare RAM, background CPU), then run the NPU flat out. |
| `warm-lap-no-clamp` | 3 | On a lap the skin cap limits total internal heat, and a tenth of the charge power is heat: a right-sized charger hands watts back to the chips. |

## Companions

- `DellAlienware/` (:5176) — the same laptop's AC power path as a
  narrated trace (PSID handshake, hybrid power). This app is the
  continuous-physics side of that story.
- `DellProMaxPlus/` (:5186) — the NPU's data path (weights cross PCIe
  once, host idle during decode). This app prices the same inference in
  watts, dB(A), and tokens per joule.
- `DellPowerEdgeR760Thermal/` (:5203) — the engine this one extends.
