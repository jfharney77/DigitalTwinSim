"""Pure lifecycle engine for the circular-design twin.

``simulate()`` returns the deterministic trace of one device cohort's life
and afterlife: material assembled, devices built, shipped, deployed,
served, repaired, stretched past the no-repair baseline, taken back,
sorted three ways, and — the step no other twin has — reborn as the input
to the next cycle. Same purity rule as every other twin in this repo: no
FastAPI, no IO, no timers — the frontend owns the playback clock, and each
``MaterialState`` is plain data the renderer consumes.

The idea this twin exists to teach: **mass in equals mass out.**

The DellIR7000 twin asserts ``liquid_watts + air_watts == it_load_watts``
with no tolerance, because the whole point of a cooling loop is that heat
does not vanish. This engine asserts the same thing about matter, for the
same reason: from the recovery step onward,
``reused_kg + reclaimed_kg + lost_kg == mass_kg`` — exactly, no tolerance.
That is the IR7000's heat balance applied to matter, and it is what keeps
this twin from being a brochure. A lifecycle story that only shows the
virtuous paths is marketing; the honest version measures the leak, and
the leak here is not zero. About 4.5% of the cohort's mass does not come
back — shredder fines, mixed-plastic fractions with no buyer, the cobalt
that stayed dissolved in someone's slag. The fraction lost is the honest
measure of how circular the design actually is.

Three more things the trace is careful to say plainly. First, the
expensive step is manufacture, which is why the ``repair`` and ``extend``
phases matter: each repair defers an entire manufacturing cycle, and
service-life extension — not recycling — is the largest lever in the whole
arithmetic. Second, refurbishment is preferred to reclamation: a device
broken down for materials that could have been resold whole is a loss even
though the mass balances. Third, the loop genuinely closes: the reborn
step's recycled-input percentage is strictly higher than the first
step's, because the output of one cycle is the input of the next.

Masses, percentages, and timings are illustrative but plausible; favor a
correct mental model over measured numbers (project scope guardrail).
"""

from __future__ import annotations

from .models import MaterialState

# One cohort: 5,000 corporate laptops at roughly 2 kg each.
COHORT_DEVICES = 5_000
COHORT_MASS_KG = 10_000

# Recycled/renewable share of the input material, first pass. Nonzero from
# step 0: recycled cobalt, copper, steel, and plastics are inputs from the
# beginning, not an aspiration for later.
FIRST_PASS_RECYCLED_PERCENT = 34

# Second pass, after this cohort's reclaimed material re-enters the pool.
# Strictly higher than the first — the loop's thesis in one comparison.
SECOND_PASS_RECYCLED_PERCENT = 46

# The no-repair baseline: with a glued-in battery and no spare parts, the
# cohort would have been refreshed when the batteries faded — around year
# four. The trace's repair and extend steps exist to beat this number, and
# tests/test_engine.py::test_repair_extends_service_life checks the trace
# demonstrates the deferral against this constant rather than asserting it.
UNREPAIRED_SERVICE_YEARS = 4

# What the cohort actually reached, with two repair passes.
REPAIRED_SERVICE_YEARS = 7

# The three destinations at end of life. They sum to COHORT_MASS_KG
# exactly — no tolerance — and reuse outweighs reclamation, because a
# refurbished device defers a manufacturing cycle and shredded material
# does not. The loss is stated, not hidden: 450 kg does not come back.
REUSED_KG = 6_200
RECLAIMED_KG = 3_350
LOST_KG = 450

assert REUSED_KG + RECLAIMED_KG + LOST_KG == COHORT_MASS_KG

# Phases in which the end-of-life accounting is open: from recover onward,
# the three destinations must sum to the cohort mass exactly.
ACCOUNTED_PHASES = {"recover", "sort", "reborn"}


def simulate() -> list[MaterialState]:
    """One cohort's life and afterlife: built, used, repaired, stretched,
    taken back, sorted three ways, and fed into the next cycle."""
    return [
        MaterialState(
            step=0,
            phase="materials",
            label="Material assembled — a third of it has been here before",
            description=(
                "Ten tonnes of input for a cohort of 5,000 laptops: "
                "aluminium and steel for chassis, copper for windings and "
                "boards, cobalt and lithium for batteries, plastics for "
                "everything else. About a third of it, by mass, is "
                "recovered material — closed-loop aluminium and steel, "
                "recycled cobalt from returned battery packs, "
                "post-consumer plastics — because circular design starts "
                "at procurement, not at the recycling bin. Worth being "
                "precise about what that third is made of, though: the "
                "recycled share is easiest in steel and plastics, where "
                "recovery chains are old and the chemistry is forgiving, "
                "and hardest in exactly the rare elements that matter "
                "most. Nobody should read 34% recycled input as 34% of "
                "the cobalt."
            ),
            active_regions=["materials"],
            elapsed_months=0,
            mass_kg=COHORT_MASS_KG,
            recycled_input_percent=FIRST_PASS_RECYCLED_PERCENT,
            reused_kg=0,
            reclaimed_kg=0,
            lost_kg=0,
            years_in_service=0,
            repairs=0,
        ),
        MaterialState(
            step=1,
            phase="manufacture",
            label="Fabrication and assembly — the expensive step",
            description=(
                "Boards fabricated, batteries formed, chassis machined, "
                "5,000 devices assembled and imaged. This is deliberately "
                "the longest stage in the trace, because it is the "
                "expensive one — most of a laptop's lifetime energy, "
                "water, and emissions are spent here, before it computes "
                "anything. That is called embodied carbon, and it is the "
                "reason the repair steps later in this trace matter more "
                "than the recycling steps: every repair that keeps a "
                "device in service defers repeating *this* step, and "
                "nothing recovered at end of life pays back what "
                "manufacture already spent. The same arithmetic runs at "
                "rack scale in this repo's DellPowerEdgeXE9712 twin, "
                "where a refresh is tonnes of material, not kilograms."
            ),
            active_regions=["materials", "manufacture"],
            elapsed_months=1,
            cycle_cost=6,
            mass_kg=COHORT_MASS_KG,
            recycled_input_percent=FIRST_PASS_RECYCLED_PERCENT,
            reused_kg=0,
            reclaimed_kg=0,
            lost_kg=0,
            years_in_service=0,
            repairs=0,
        ),
        MaterialState(
            step=2,
            phase="ship",
            label="Packed and shipped — the packaging is the easy win",
            description=(
                "The cohort is boxed and freighted. Dell's packaging is "
                "the genuinely solved corner of this picture — about 97% "
                "of it from recycled or renewable material, and honestly "
                "so, because cardboard and moulded fibre are the easiest "
                "materials on Earth to recycle. It is worth enjoying the "
                "win and keeping its size in perspective: packaging is a "
                "few hundred grams per device against two kilograms of "
                "electronics, and recycled cardboard does not offset a "
                "virgin cobalt supply chain. The hard problems are all "
                "inside the box."
            ),
            active_regions=["manufacture", "packaging", "deployment"],
            elapsed_months=2,
            mass_kg=COHORT_MASS_KG,
            recycled_input_percent=FIRST_PASS_RECYCLED_PERCENT,
            reused_kg=0,
            reclaimed_kg=0,
            lost_kg=0,
            years_in_service=0,
            repairs=0,
        ),
        MaterialState(
            step=3,
            phase="deploy",
            label="5,000 devices in users' hands",
            description=(
                "Deployment: imaged, enrolled, and issued. From the "
                "material ledger's point of view nothing happens here — "
                "ten tonnes sits distributed across office desks and "
                "backpacks instead of a warehouse — but this is where "
                "every other twin in this repo lives, and where they all "
                "stop. The R760 boots and reaches 'os'; the SN6000 "
                "fabric reaches 'steady'; this repo's DellProMaxPlus and "
                "DellAlienware twins end with the machine working. This "
                "trace keeps going, because the machine working is the "
                "middle of the story, not the end."
            ),
            active_regions=["deployment"],
            elapsed_months=3,
            mass_kg=COHORT_MASS_KG,
            recycled_input_percent=FIRST_PASS_RECYCLED_PERCENT,
            reused_kg=0,
            reclaimed_kg=0,
            lost_kg=0,
            years_in_service=0,
            repairs=0,
        ),
        MaterialState(
            step=4,
            phase="serve",
            label="Three years of service",
            description=(
                "Three years compressed into a step. Batteries fade "
                "toward 80% of their design capacity, hinges loosen, a "
                "few percent of the fleet dies outright and is triaged "
                "early. This is the point at which the no-repair path "
                "and the repair path diverge: with a glued-in battery "
                "and no spare parts, the sensible corporate decision at "
                "year four is a full refresh — 5,000 new devices, and "
                "another run through the expensive manufacture step. "
                "The next two steps are what circular design does "
                "instead, and they are the largest lever in this whole "
                "trace — bigger than the recycling that gets the "
                "publicity."
            ),
            active_regions=["deployment"],
            elapsed_months=39,
            cycle_cost=2,
            mass_kg=COHORT_MASS_KG,
            recycled_input_percent=FIRST_PASS_RECYCLED_PERCENT,
            reused_kg=0,
            reclaimed_kg=0,
            lost_kg=0,
            years_in_service=3,
            repairs=0,
        ),
        MaterialState(
            step=5,
            phase="repair",
            label="Battery swap — a repair defers a manufacturing cycle",
            description=(
                "The fleet gets new batteries. Because the pack is "
                "customer-replaceable — a design decision made years "
                "earlier, at the CAD stage — this is a ten-minute "
                "procedure with a spudger, guided by a repair tutorial "
                "or the AR (augmented reality) assistant, not a "
                "depot-return program. The arithmetic is the point: a "
                "300-gram battery pack postpones the replacement of a "
                "2,000-gram device, which means it postpones repeating "
                "the manufacture step that dominates the cohort's "
                "lifetime footprint. Repairability is not a sentimental "
                "feature. It is the cheapest tonne of material in this "
                "entire diagram — the one that never gets processed."
            ),
            active_regions=["deployment", "service"],
            elapsed_months=40,
            mass_kg=COHORT_MASS_KG,
            recycled_input_percent=FIRST_PASS_RECYCLED_PERCENT,
            reused_kg=0,
            reclaimed_kg=0,
            lost_kg=0,
            years_in_service=3,
            repairs=1,
        ),
        MaterialState(
            step=6,
            phase="extend",
            label="Refresh deferred — service life stretched past the baseline",
            description=(
                "Year six, second service pass: keyboards, fans, a round "
                "of SSD swaps. The refresh that would have happened at "
                "year four — the no-repair baseline — has now been "
                "deferred twice, and the cohort is on course for seven "
                "years of service instead of four. Honesty requires "
                "naming the tension here: every deferred refresh is a "
                "sale Dell did not make, and refurbishment and repair "
                "compete directly with the commercial incentive to sell "
                "new units. Take-back programs and repair support exist "
                "where that tension has been resolved in the customer's "
                "favor — or where regulation, procurement rules, or the "
                "resale market resolved it regardless. The design "
                "decisions were still real; so is the tension."
            ),
            active_regions=["deployment", "service"],
            elapsed_months=76,
            cycle_cost=2,
            mass_kg=COHORT_MASS_KG,
            recycled_input_percent=FIRST_PASS_RECYCLED_PERCENT,
            reused_kg=0,
            reclaimed_kg=0,
            lost_kg=0,
            years_in_service=6,
            repairs=2,
        ),
        MaterialState(
            step=7,
            phase="recover",
            label="Take-back at year seven — the mass accounting opens",
            description=(
                "The cohort is retired through asset recovery: collected, "
                "inventoried, and every drive cryptographically sanitized "
                "with a certificate per device — the step that makes "
                "enterprises willing to hand hardware back at all rather "
                "than shelving it in a store-room forever. Triage begins, "
                "and refurbishment is assessed *first*, deliberately: a "
                "device broken down for materials that could have been "
                "resold whole is a loss even though the mass balances. "
                "From this step onward the ledger must close exactly — "
                "6,200 kg fit for a second life, 3,350 kg bound for "
                "material reclamation, and 450 kg that will not come "
                "back. Reused plus reclaimed plus lost equals ten tonnes, "
                "to the kilogram, on this step and every step after."
            ),
            active_regions=["deployment", "recovery", "refurbish"],
            elapsed_months=84,
            cycle_cost=3,
            mass_kg=COHORT_MASS_KG,
            recycled_input_percent=FIRST_PASS_RECYCLED_PERCENT,
            reused_kg=REUSED_KG,
            reclaimed_kg=RECLAIMED_KG,
            lost_kg=LOST_KG,
            years_in_service=REPAIRED_SERVICE_YEARS,
            repairs=2,
        ),
        MaterialState(
            step=8,
            phase="sort",
            label="Three destinations — and one of them is a leak",
            description=(
                "The sort completes. The inner return: 6,200 kg of "
                "devices refurbished — retested, re-batteried, resold or "
                "redeployed — each one deferring another manufacturing "
                "cycle somewhere. The outer return: 3,350 kg shredded and "
                "separated, steel and aluminium to closed-loop smelting, "
                "boards to precious-metal recovery, battery packs to "
                "cobalt and lithium reclamation. And the leak: 450 kg "
                "that does not come back — shredder fines too small to "
                "sort, mixed-plastic fractions no process wants, cobalt "
                "left dissolved in slag. The loss region is drawn on this "
                "map for the same reason the IR7000 twin meters the heat "
                "leaving its rack: a diagram that only shows the "
                "virtuous paths is marketing. 4.5% of this cohort, by "
                "mass, is gone, and that number — not the recycling rate "
                "— is the honest measure of how circular the design is."
            ),
            active_regions=["recovery", "refurbish", "reclaim", "loss"],
            elapsed_months=85,
            cycle_cost=2,
            mass_kg=COHORT_MASS_KG,
            recycled_input_percent=FIRST_PASS_RECYCLED_PERCENT,
            reused_kg=REUSED_KG,
            reclaimed_kg=RECLAIMED_KG,
            lost_kg=LOST_KG,
            years_in_service=REPAIRED_SERVICE_YEARS,
            repairs=2,
        ),
        MaterialState(
            step=9,
            phase="reborn",
            label="The loop closes — the next cohort starts richer",
            description=(
                "Reclaimed steel, aluminium, copper, cobalt, and plastics "
                "re-enter the materials pool, and the next cohort's input "
                "is 46% recovered material where this one's was 34% — "
                "the output of one cycle is the input of the next, which "
                "is the entire thesis, demonstrated rather than asserted. "
                "Every other trace in this repo ends with a machine in "
                "steady state; this one ends where it began, one turn "
                "further on. The honest caveats travel with it: the leak "
                "does not close, the recycled share of the rare elements "
                "lags the recycled share of the steel, and the biggest "
                "single contribution to that 46% was not any recycling "
                "process — it was the three extra years of service that "
                "meant this material was demanded once instead of twice. "
                "The reporting side of this loop — provenance, carbon "
                "per device, end-of-life outcomes — is the same "
                "telemetry-to-insight shape as this repo's DellCloudIQ "
                "twin."
            ),
            active_regions=["reclaim", "materials"],
            elapsed_months=86,
            mass_kg=COHORT_MASS_KG,
            recycled_input_percent=SECOND_PASS_RECYCLED_PERCENT,
            reused_kg=REUSED_KG,
            reclaimed_kg=RECLAIMED_KG,
            lost_kg=LOST_KG,
            years_in_service=REPAIRED_SERVICE_YEARS,
            repairs=2,
        ),
    ]
