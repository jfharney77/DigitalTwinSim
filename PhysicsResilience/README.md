# PhysicsResilience — security & resilience timeline simulator

Sixth app of the physics suite (`physics_specs/05-security-resilience.md`,
plan in `physics_specs/BUILD_PLAN.md`). One Archetype-E timeline engine
(tick = one sim-hour, the scrubber is the UI's centre) with four
defensive personalities.

**Hard scope boundary (spec 05, test-enforced):** these simulators teach
defensive architecture only. The "attack" is an abstract scripted event
— a corruption rate and a timestamp. No exploit content, no technique
detail, no offensive realism. `test_scope_boundary_is_stated_and_abstract`
and `test_scenarios_stay_inside_the_scope_boundary` keep it that way.

- **PowerProtect** — the incident corrupts every repository copy and no
  vault copy (the air gap holds, asserted); RTO = decision hours +
  TB ÷ restore-throughput — 200 TB at 1 GB/s is a days-scale affair,
  computed by the validation panel before anything goes wrong.
- **Cyber Detect** — the ROC knob: latency = base ÷ sensitivity, false
  alarms ∝ sensitivity at 3 h each. Detection names the last clean
  point; blindness restores the newest (corrupt) copy first and roughly
  doubles RTO — both branches compared in tests.
- **MDR** — blast radius = rate × time-to-contain. The 2 a.m. Saturday
  incident waits ~54 h for an in-house desk and ~15 min for a 24/7
  SOC; alert fatigue is the 1/(1−ρ) queue wearing a SIEM's clothes.
- **Fort Zero** — the access-graph mode: a perimeter compromise floods
  ~90% of assets, zero trust caps it at grants ÷ segments; friction is
  priced (9 vs 1 checks/session) and least privilege decays without
  reviews.

## Run

```
./scripts/start_all.sh     # backend :8036 background, frontend :5209 foreground
./scripts/stop_all.sh
```

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

## Companions

Narrated twins: `DellPowerProtect/` (:5183), `DellCyberDetect/`
(:5192), `DellFortZero/` (:5195). ObjectScale's WORM bucket in
`PhysicsStorage/` is this app's vault substrate; the sensitivity knob
rhymes with `PhysicsData/`'s anomaly detector on purpose.
