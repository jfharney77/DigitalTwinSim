# DellCircularDesign — product-lifecycle digital twin (spec)

Status: **spec only.** Chosen in loop iteration 4 as one of the top three
untwinned Dell products; Project Fort Zero was built first. Build this one
by following the pattern in `DellIR7000/` (conservation invariant) and
`DellPowerProtect/` (left-to-right lifecycle map).

## Subject

**Dell's circular design and Asset Recovery Services** — recycled cobalt,
copper, steel and plastics in new products (more than 95 million pounds of
recycled and renewable materials in a year; 97% of packaging from 100%
recycled or renewable material), modular and serviceable designs with
customer-replaceable batteries and an AR repair assistant, and end-of-life
take-back that refurbishes what can be reused and reclaims materials from
what cannot.

## The one idea

**Every twin in this repo ends at "steady". This one doesn't end.**

Look at the traces already in the repository. The R760 boots and reaches
`os`. The SN6000 fabric reaches `steady`. The XE9712 reaches `ready`. The
Pro Max Plus reaches `offline`. In all seventeen, the final state is the
machine working, and the implicit claim is that working forever is what
machines do.

They don't. Every device in this repo will be decommissioned, and what
happens next is not nothing — it is either landfill or it is the material
input to the next generation. Circular design is the claim that the second
option can be engineered rather than hoped for, and it changes what the
*shape* of a product's trace is: not a line ending in steady state, but a
loop that returns to its own beginning.

That makes this the only twin whose trace closes. And it hands the design a
conservation invariant that is the exact analogue of the IR7000's heat
balance, applied to matter instead of energy:

> **mass in equals mass out.** Every kilogram entering the loop is
> accounted for at the end as reused, reclaimed, or genuinely lost — and
> the fraction lost is the honest measure of how circular the design
> actually is.

The IR7000 twin asserts `liquid_watts + air_watts == it_load_watts` with no
tolerance, because the whole point of a cooling loop is that heat does not
vanish. This twin should assert the same thing about material, for the same
reason, and it should be honest that the lost fraction is not zero.

## Metaphor mapping

- **"Anatomy"** → a **closed loop**, drawn as a cycle rather than a
  left-to-right path: materials → manufacture → deployment → service and
  repair → refresh → recovery → refurbish (back to deployment) or reclaim
  (back to materials). Two return paths, at different radii, because reuse
  and recycling are not the same thing and reuse is strictly better.
  Geometry test: `test_the_loop_closes` — the recovery region has a path
  back to both `materials` and `deployment`, and no region is a terminus.
- **"Power-on trace"** → the life and afterlife of one device.

## Proposed model shapes

`LifecycleMap` / `LifecycleRegion` / **`MaterialState`**.

```
RegionKind = materials | manufacture | packaging | deployment
           | service | recovery | refurbish | reclaim | loss
```

Note the `loss` kind. It has to be in the model and drawn in the diagram,
because a lifecycle map that shows only the virtuous paths is marketing. The
honest version draws the leak and measures it.

`MaterialState` carries:

- `mass_kg: int` — total in the cohort being traced
- `recycled_input_percent: int` — how much of the input was already
  recovered material
- `reused_kg` / `reclaimed_kg` / `lost_kg` — the three destinations
- `years_in_service: int`
- `repairs: int` — each one deferring the recovery step
- plus the standard `step / phase / label / description / active_regions /
  elapsed_seconds (or elapsed_months) / cycle_cost`

## Proposed phases

`materials → manufacture → ship → deploy → serve → repair → extend → recover → sort → reborn`

- `repair` and `extend` are the phases most lifecycle stories skip. A
  customer-replaceable battery and an AR repair guide are not sentimental
  features; each repair postpones an entire manufacturing cycle, which
  dominates the arithmetic.
- `reborn` returns material to `materials`, closing the loop.

## Signature invariants to enforce (backend/tests/test_engine.py)

1. **`test_mass_is_conserved`** — THE invariant, and the direct analogue of
   the IR7000's heat balance: at every step from `recover` onward,
   `reused_kg + reclaimed_kg + lost_kg == mass_kg`, exactly, no tolerance.
2. **`test_the_loss_is_stated_not_hidden`** — `lost_kg > 0` at the end. A
   twin claiming a perfectly closed loop would be lying, and the test should
   make lying impossible.
3. **`test_reuse_is_preferred_to_reclaim`** — `reused_kg > 0` and the trace
   must attempt refurbishment before material reclamation; a device broken
   down for materials that could have been refurbished is a loss even though
   the mass balances.
4. **`test_repair_extends_service_life`** — `years_in_service` at `recover`
   is strictly greater when `repairs > 0`; the trace should demonstrate the
   deferral rather than assert it.
5. **`test_the_loop_closes`** — the final phase's active regions include
   `materials`, and `recycled_input_percent` in a second pass is strictly
   higher than in the first. The output of one cycle is the input of the
   next, which is the entire thesis.
6. **`test_recycled_input_is_never_zero`** — the cohort does not start from
   virgin material; recycled cobalt, copper, steel and plastics are inputs
   from the beginning.
7. **`test_manufacture_is_the_longest_stage`** — unique max `cycle_cost`,
   and the reason repair matters: the expensive step is the one repair
   avoids repeating.
8. Standard: phase order, active regions exist, engine purity (AST-checked).

## Catalog (~9 categories, backend data)

Material inputs (recycled cobalt, copper, steel, plastics; bio-based
alternatives), packaging (97% recycled/renewable), design for repair
(modularity, customer-replaceable batteries, simplified cabling), repair
support (spare parts, tutorials, the AR Assistant app), service life
extension, asset recovery services (secure retirement, data sanitization),
refurbishment and second life, materials reclamation, lifecycle reporting
(product carbon footprint data, the Sustainable Data Dashboard).

## Use cases (3)

1. An enterprise refreshing 5,000 laptops that wants residual value and
   certified data destruction rather than a skip.
2. A datacenter operator accounting for embodied carbon in a hardware
   refresh — where the interesting finding is usually that extending
   service life beats replacing with something more efficient.
3. A manufacturer under regulatory pressure to report material provenance
   and end-of-life outcomes.

## Cross-references to keep intact

- **DellIR7000** — the conservation invariant is deliberately modelled on
  that twin's heat balance. Both twins exist to say that something does not
  vanish just because it left the diagram. Say so explicitly in both.
- **DellProMaxPlus** and **DellAlienware** — the client devices whose
  afterlife this twin models.
- **DellPowerEdgeXE9712** — the embodied-carbon argument is sharpest at
  rack scale, where a refresh is tonnes of material.
- **DellCloudIQ** — lifecycle reporting and the Sustainable Data Dashboard
  are the same telemetry-to-insight shape.

## A note on tone

This is the twin most at risk of reading as a brochure. The guard is the
`loss` region and the invariant that goes with it: the trace must show
material that does not come back, and the copy must say plainly what the
limits are — that refurbishment competes with the commercial incentive to
sell new units, that recycled content is easier in steel and plastics than
in the rare elements that matter most, and that the largest lever by far is
not recycling at all but keeping the device in service longer. Write it the
way the rest of the repo writes: skeptical, specific, and willing to name
the trade.

## Ports

Backend **:8024**, frontend **:5197** (after DellPowerScale's 8023/5196).
Trace endpoint `GET /api/lifecycle` returning `MaterialResponse` — note
`/api/lifecycle` collides in name with the PowerProtect twin's endpoint but
the apps are independent and on different ports.

## Sources

- <https://www.dell.com/en-us/lp/dt/circular-economy>
- <https://www.dell.com/en-us/blog/circular-economy-in-action-leading-the-fight-against-e-waste/>
- <https://www.dell.com/en-us/blog/from-vision-to-reality-circular-design-ai-pcs/>
- <https://www.dell.com/en-us/lp/dt/sustainable-devices>
- <https://www.dell.com/en-in/blog/repair-reuse-recycle-the-circular-economy-in-action/>
