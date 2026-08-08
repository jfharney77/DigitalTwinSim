# physics_specs — build plan

Decided 2026-08-07 (owner-confirmed): the physics suite is built as **eight apps,
one per spec file**, with products as selectable personalities inside each app —
not one directory per product. The specs' shared-engine instruction ("build ONE
engine, parameterize per product") and the flagship cross-product A/B scenarios
(SN6000 vs X800 on identical traffic, sealed vs serviceable laptop) require the
products to live in one process.

## Apps, ports, spec files

| App | Spec file | Products (build order within app) | Backend | Frontend |
|---|---|---|---|---|
| `PhysicsClient/` | 07 | Alienware → Pro Max Plus | 8031 | 5204 |
| `PhysicsCompute/` | 01 | XE7745 → XE9680 → XE9712+IR7000 (one rack model) → iDRAC console panel | 8032 | 5205 |
| `PhysicsStorage/` | 02 | PowerStore → PowerMax → PowerScale → ObjectScale → PowerFlex → Exascale meta-sim | 8033 | 5206 |
| `PhysicsFabric/` | 03 | E3200 → SN6000 → Quantum-X800 → Ethernet-vs-IB A/B | 8034 | 5207 |
| `PhysicsFleet/` | 04 | VxRail → Private Cloud → APEX → NativeEdge/DPC → Automation Studio | 8035 | 5208 |
| `PhysicsResilience/` | 05 | PowerProtect → Cyber Detect → MDR → Fort Zero | 8036 | 5209 |
| `PhysicsData/` | 06 | AI Data Platform → CloudIQ/APEX AIOps console | 8037 | 5210 |
| `PhysicsLifecycle/` | 08 | Telecom Blocks → Circular Design | 8038 | 5211 |

Ports continue from the last built twin (R760Thermal, 8030/5203). The eight
unbuilt `initial_spec.md` twins keep their reservations (8015, 8017–8018,
8020–8021, 8026–8027 / 5188, 5190–5191, 5193–5194, 5199–5200) — a physics
treatment of a product does **not** consume its narrative-twin reservation.

## Cross-app build order

1. **PhysicsClient** — smallest delta from R760Thermal (battery, PL1/PL2,
   skin temp, acoustics); proves the engine generalizes (spec 07's own words).
2. **PhysicsCompute** — the suite's anchor; defines the data-starvation slider
   consumed conceptually by 02 and 06, and the coolant-loop instruments reused
   by 03.
3. **PhysicsStorage** — shared B engine, Exascale meta-sim last (spec's rule).
4. **PhysicsFabric** — E3200 first ("good first networking sim"), X800 last.
5. **PhysicsFleet** — Automation Studio last (the integrator).
6. **PhysicsResilience** — Fort Zero last (different UI shape: access graph).
7. **PhysicsData** — observes concepts from 1–4; CloudIQ console is the
   suite-closing lesson.
8. **PhysicsLifecycle** — Telecom reuses the fleet engine; Circular Design
   reuses the client laptop model.

## Architectural rules (all eight apps)

- **Template is `DellPowerEdgeR760Thermal/`**: `POST /api/simulate` takes a
  Scenario (product/config + workload dials + environment + timed events),
  returns Validation[] + SimState[] trace + LogEntry[] + Summary. GET runs the
  default scenario. Pure engine, AST-checked (no fastapi/time/random/IO);
  the playback clock lives in the frontend.
- **Engine sharing by copy, not import.** Each app is self-contained (own
  `.venv`, own tests) like every twin. Copying + adapting the R760Thermal
  engine is the repo's accepted idiom; a shared package would break the
  per-app purity story for marginal savings.
- **Companion apps, not replacements.** Existing narrative twins stay
  untouched except for a cross-link; each physics app links the corresponding
  twin(s) and vice versa (the R760 ↔ R760Thermal precedent).
- **Constants discipline**: every constant carries units + `source`; figures
  the specs flag `verify` get a research pass at build time, and anything
  unresolved ships labeled `estimate` — never silently promoted to fact.
  Circular Design additionally: no invented sustainability numbers (test-
  enforced label/citation on every carbon constant).
- **House invariants as pytest**: per-tick conservation identities (power
  balance; ṁ·cp·ΔT; capacity arithmetic raw→usable→effective; flow
  conservation across the fabric; carbon accounting closure), presets pass
  their own validation rules, each spec's key scenarios become acceptance
  tests, and spec 05's scope-boundary footer is asserted present.
- **Reading levels** on teaching prose (overview + explain/scenario text,
  levels 1/3/5 authored) via the shared `leveling.py` mechanism.
- **Dell clean-design skin**; the instrument panels/diagrams stay dark.
- Each app lands as: backend green → frontend builds → `ports.json` entry →
  CLAUDE.md section → cross-links into companion twins →
  `CustomerSetup/tests/test_links.py` still green.
