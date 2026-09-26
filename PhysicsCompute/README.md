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

## Sourced facts

Checked against public documents in September 2026; everything else in
`constants.py` is a labeled estimate.

- XE7745: dual AMD EPYC 9005 (not Xeon), up to 8× 600 W double-wide
  GPUs, 24 DIMMs, eight 3200 W Titanium PSUs (2900 W on 200–220 V),
  twelve front fans plus four dual-fan mid-tray modules — Dell spec
  sheet, July 2025. The model budgets four PSUs (a 4+4 bank); that
  split is this app's assumption.
- XE9680: two Xeon Scalable sockets, 32 DIMMs, six PSUs, six mid-tray
  plus ten rear fans — Dell Installation and Service Manual.
- XE9712: 2 Grace + 4 GPUs per 1U sled, 33 kW power shelves, 30 kg
  sled, 1,590 kg cabinet wet weight, eight dual-rotor fans per sled
  (not modeled) — Dell spec sheet, April 2026, which now describes the
  GB300 generation on the IR9048 rack. The first GB200 racks shipped in
  IR7000 racks in late 2024 (Dell press release). Nine NVLink switch
  trays — NVIDIA technical blog.

## Companions

- `DellPowerEdgeXE9680/` (:5201) and `DellPowerEdgeXE9712/` (:5181) —
  the same machines' power-on narratives.
- `DellIR7000/` (:5182) — the cooling loop as its own subject; this
  app's verify-phase heat balance is that twin's identity, live.
- `DellIDRAC/` (:5177) — the controller behind the Redfish tab.
- `PhysicsStorage/` (when built) — the other end of the data-feed
  slider.
