# PhysicsCompute — AI-compute power & thermal simulator

Second app of the physics suite (`physics_specs/01-gpu-compute-and-management.md`,
plan in `physics_specs/BUILD_PLAN.md`). Three system personalities on one
engine, plus the iDRAC closer:

- **XE7745** (4U, PCIe): positional thermal inequality — per-slot inlet
  preheat means the worst seat throttles first, and the 16-fan wall's
  cubic overhead runs to hundreds of watts.
- **XE9680** (6U, HGX): the shared-fate baseboard (all 8 SXM GPUs
  throttle together — `gpus_throttled ∈ {0, 8}` is a test) and the
  **data-starvation slider**: a starved GPU busy-waits at most of its fed
  power while tokens/s collapses; the wasted-GPU-hours ledger integrates
  the gap. Idle→full swing ~1 → 10+ kW.
- **XE9712 + IR7000** (one model, rack as the unit): the heat-split
  identity (liquid + air = DC, exact, ≥85% liquid), ΔT = Q/(ṁ·cp) with
  water's cp, pump/CDU/tray failure events, and the IR7000's
  budget-validation rules (shelf kW, manifold L/min, weight advisory) —
  at rack scale the rules are the product.
- **iDRAC tab**: the live SimState reshaped as the Redfish
  `/Chassis/…/Thermal` payload (`Oem.Dell.Simulated: true`) — swap the
  simulator for hardware behind the same query and you have the twin.

## Run

```
./scripts/start_all.sh     # backend :8032 background, frontend :5205 foreground
./scripts/stop_all.sh
```

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

## Companions

- `DellPowerEdgeXE9680/` (:5201) and `DellPowerEdgeXE9712/` (:5181) —
  the same machines' power-on narratives.
- `DellIR7000/` (:5182) — the cooling loop as its own subject; this
  app's verify-phase heat balance is that twin's identity, live.
- `DellIDRAC/` (:5177) — the controller behind the Redfish tab.
- `PhysicsStorage/` (when built) — the other end of the data-feed
  slider.
