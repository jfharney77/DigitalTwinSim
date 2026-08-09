# PhysicsRackPower — rack PDUs & UPS, the power layer under every rack

Product #6 of `physics_specs/10-additional-products.md` (Archetype A/F):
Dell-branded rack power accessories — today, resold APC NetShelter
metered/switched PDUs plus rack UPS units — as an interactive physics
simulator in the `DellPowerEdgeR760Thermal/` mold: **`POST /api/simulate`**
takes a Scenario (eight rack loads assigned to three phase feeds, per-phase
breaker ratings, a UPS battery with a chemistry and an age, timed events)
and returns Validation[] + a deterministic SimState[] trace + LogEntry[] +
Summary. The engine is pure (AST-checked); the playback clock lives in the
frontend.

## The one idea

Three lessons share one rack:

1. **Balance the phases.** Three feeds share the load only if you assign
   it evenly. Moving a server between phases never creates or destroys a
   watt — conservation is asserted per tick — but it converts a stranded
   breaker limit into headroom.
2. **Breaker math.** The NEC 80% continuous-load rule is drawn on every
   meter; ignore it and a simplified thermal-magnetic I²t curve trips the
   breaker on a delay proportional to the overload — taking every load on
   the phase down at once. Warn, don't block; then simulate the consequence.
3. **The battery truth gap.** UPS runtime = usable Wh × inverter η ÷ load W
   — but the front panel computes it from *nameplate* Wh until a self-test
   measures the fade that age and room temperature inflicted (VRLA ~6%/yr,
   aging ~2× per +10 °C; lithium far gentler — all labeled estimates). The
   engine discharges the *faded* Wh, so predicted/actual runtime differ by
   exactly the capacity fraction. The gap is the hero instrument, and the
   classic outage post-mortem, simulated.

## Run

```
./scripts/start_all.sh     # backend :8044 background, frontend :5217 foreground
./scripts/stop_all.sh
```

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
(41 tests). Frontend: `cd frontend && npm run build`.

## What we don't model

Transfer-time gaps (the ~4 ms line-interactive switchover), harmonics and
true three-phase vector math (phases are treated as three independent
230 V feeds), PDU metering electronics (~5 W), battery internal resistance
and depth-of-discharge limits, generator interaction, and per-outlet
switching sequences. Fade rates and trip curves are estimates — every
constant in `backend/app/constants.py` carries units and a source, and the
UI badges estimate-derived readouts.

## Sources

- Dell's rack power lineup is resold APC NetShelter Rack PDU Advanced
  (switched, metered-by-outlet; 1- and 3-phase) — dell.com listings,
  checked 2026-08.
- NEC 210.19/210.20 — the 80% continuous-load rule.
- IEEE 1188 / IEEE 535 practice — the VRLA aging rule of thumb (applied
  as an exact doubling per +10 °C; labeled estimate).
