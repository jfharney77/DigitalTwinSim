# PhysicsClient — client-device power & thermal simulator

First app of the physics suite (`physics_specs/07-client-devices.md`,
plan in `physics_specs/BUILD_PLAN.md`): the R760 thermal twin's engine
generalized to the machines that sit on desks and laps. Two product
personalities in one app — **Alienware** (laptop or desktop tower) and
the **Dell Pro Max Plus** mobile workstation with its optional discrete
NPU (Qualcomm AI-100-class).

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
(CES 2026) is confirmed; the reported "Pro Max" → "Dell Pro Precision"
workstation rename is marked *reported*, per the spec's `verify`
discipline — `tests/test_brandmap.py` enforces the labeling, the tier
ladder, the placement of "Pro Max Plus", and the twin cross-links.

## Companions

- `DellAlienware/` (:5176) — the same laptop's AC power path as a
  narrated trace (PSID handshake, hybrid power). This app is the
  continuous-physics side of that story.
- `DellProMaxPlus/` (:5186) — the NPU's data path (weights cross PCIe
  once, host idle during decode). This app prices the same inference in
  watts, dB(A), and tokens per joule.
- `DellPowerEdgeR760Thermal/` (:5203) — the engine this one extends.
