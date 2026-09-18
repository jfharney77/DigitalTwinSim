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

from .leveling import L
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
            description=L(
                standard=(
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
                novice=(
                    "This step gathers ten tonnes of raw material to build "
                    "5,000 laptops. Aluminium and steel make the case, copper "
                    "makes the wires and circuit boards, cobalt and lithium "
                    "go into the batteries, and plastic covers the rest. "
                    "About a third of that material has been used before: "
                    "metal melted down from old products, cobalt taken out of "
                    "returned batteries, plastic from things people threw "
                    "away. Using old material is where a circular design "
                    "begins, before anything is built. One warning: steel and "
                    "plastic are easy to recycle, but the rare metals are "
                    "hard. So 34% recycled material overall does not mean 34% "
                    "of the cobalt is recycled."
                ),
                plain=(
                    "Ten tonnes of material go into 5,000 laptops: aluminium "
                    "and steel for the cases, copper for wiring and circuit "
                    "boards, cobalt and lithium for the batteries, and plastic "
                    "for most of the rest. About a third of it by weight has "
                    "been used before, as remelted metal, cobalt from returned "
                    "batteries and recycled plastic. Circular design starts "
                    "here, when the materials are bought. Be careful with that "
                    "third, though. Steel and plastic are easy to recycle and "
                    "rare metals are hard, so 34% recycled overall does not "
                    "mean 34% of the cobalt."
                ),
                technical=(
                    "10,000 kg of input for 5,000 units: aluminium and steel "
                    "chassis, copper conductors and boards, cobalt/lithium "
                    "cells, engineering polymers. Roughly 34% by mass is "
                    "recovered content (closed-loop aluminium and steel, "
                    "recycled cobalt from returned packs, post-consumer resin), "
                    "so circularity begins at procurement. The share is not "
                    "uniform: recovery chains for steel and plastics are "
                    "mature, and those for the critical elements are not. A 34% "
                    "recycled-content figure says little about the cobalt."
                ),
                expert=(
                    "10 t input, 5,000 units: Al/steel chassis, Cu, Co/Li "
                    "cells, polymers. 34% recovered content by mass, weighted "
                    "heavily toward steel and post-consumer plastics; "
                    "recovered Co share is far lower. Circularity is a "
                    "procurement decision first."
                ),
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
            description=L(
                standard=(
                    "Boards fabricated, batteries formed, chassis machined, "
                    "5,000 devices assembled and imaged. This is deliberately "
                    "the longest stage in the trace, because it is the "
                    "expensive one — most of a laptop's lifetime energy, "
                    "water, and emissions are spent here, before it computes "
                    "anything. That is called embodied carbon, and it is the "
                    "reason the repair steps later in this trace matter more "
                    "than the recycling steps: every repair that keeps a "
                    "device in service defers repeating this step, and "
                    "nothing recovered at end of life pays back what "
                    "manufacture already spent. The same arithmetic runs at "
                    "rack scale in this repo's DellPowerEdgeXE9712 twin, "
                    "where a refresh is tonnes of material, not kilograms."
                ),
                novice=(
                    "The factory makes the circuit boards, the batteries and "
                    "the cases, then puts together all 5,000 laptops. This "
                    "step takes the longest in the trace on purpose, because "
                    "it costs the most. Most of the energy, water and "
                    "pollution a laptop will ever cause is spent here, before "
                    "anyone turns it on. People call this embodied carbon. "
                    "That is why fixing a laptop later matters more than "
                    "recycling it: every repair means one less new laptop has "
                    "to be built, and nothing saved at the end of its life "
                    "gives back what the factory already used. The "
                    "DellPowerEdgeXE9712 twin shows the same idea for a whole "
                    "rack of servers, where replacing it means tonnes of "
                    "material."
                ),
                plain=(
                    "The factory makes the boards, forms the batteries, "
                    "machines the cases and assembles all 5,000 laptops. It is "
                    "the longest step in the trace because it is the most "
                    "costly: most of the energy, water and emissions a laptop "
                    "will ever cause are spent here, before it is switched on. "
                    "That is called embodied carbon. It is why repair matters "
                    "more than recycling later on. Each repair that keeps a "
                    "laptop working puts off doing this step again, and nothing "
                    "recovered at the end pays back what was spent here. The "
                    "DellPowerEdgeXE9712 twin shows the same sum for a rack, "
                    "where a replacement is tonnes of material."
                ),
                technical=(
                    "Board fabrication, cell formation, chassis machining, "
                    "assembly and imaging for 5,000 units. The trace's longest "
                    "stage by design, because it carries most of the "
                    "lifecycle's energy, water and emissions: embodied carbon, "
                    "committed before first power-on. That makes the later "
                    "repair steps worth more than the recycling steps. Each "
                    "repair that keeps a unit in service defers a repeat of "
                    "this stage, and end-of-life recovery cannot recoup what it "
                    "spent. The DellPowerEdgeXE9712 twin runs the same "
                    "arithmetic at rack scale, in tonnes."
                ),
                expert=(
                    "Fab, cell formation, assembly, imaging. Longest stage: "
                    "manufacture dominates lifecycle embodied carbon, so each "
                    "repair that defers a refresh avoids a full repeat of "
                    "this step. End-of-life recovery cannot repay it. See "
                    "DellPowerEdgeXE9712 for the rack-scale version."
                ),
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
            description=L(
                standard=(
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
                novice=(
                    "The laptops are put in boxes and sent out. Packaging is "
                    "the part Dell has mostly solved: about 97% of it comes "
                    "from recycled or renewable material, because cardboard "
                    "and pressed paper fibre are very easy to recycle. That "
                    "is good news, but it is small. The box weighs a few "
                    "hundred grams, and the laptop inside weighs two "
                    "kilograms. Recycled cardboard does nothing about the "
                    "cobalt mined for the battery. The hard problems are "
                    "inside the box."
                ),
                plain=(
                    "The laptops are boxed and shipped. Packaging is the part "
                    "that is largely solved: about 97% of Dell's packaging is "
                    "recycled or renewable material, because cardboard and "
                    "moulded paper fibre are about the easiest things there are "
                    "to recycle. It is a real win, but a small one. A box "
                    "weighs a few hundred grams and the laptop weighs two "
                    "kilograms, and recycled cardboard does nothing about new "
                    "cobalt being mined. The hard problems are inside the box."
                ),
                technical=(
                    "Cohort boxed and freighted. Packaging is the solved part: "
                    "roughly 97% recycled or renewable content, credibly, since "
                    "corrugated board and moulded fibre are the most recyclable "
                    "material class there is. Keep the scale in view: a few "
                    "hundred grams of packaging per 2 kg device, and recycled "
                    "fibre offsets nothing in a virgin cobalt supply chain. The "
                    "hard problems are inside the box."
                ),
                expert=(
                    "Boxed and freighted. ~97% recycled/renewable packaging, "
                    "a solved problem: fibre recycles trivially. At a few "
                    "hundred grams against 2 kg of electronics it does not "
                    "offset virgin Co supply."
                ),
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
            description=L(
                standard=(
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
                novice=(
                    "The laptops are set up and handed to the people who will "
                    "use them. On the material ledger nothing changes: the "
                    "same ten tonnes now sit on desks and in backpacks "
                    "instead of in a warehouse. Most other twins in this repo "
                    "stop at this point, with the machine switched on and "
                    "working. The R760 server reaches its operating system, "
                    "the SN6000 network reaches a steady state, and the "
                    "DellProMaxPlus and DellAlienware laptops end up running. "
                    "This trace keeps going, because a working machine is the "
                    "middle of its story, not the end."
                ),
                plain=(
                    "The laptops are set up, enrolled and handed out. On the "
                    "material ledger nothing happens: the same ten tonnes now "
                    "sit on desks and in bags rather than in a warehouse. This "
                    "is where every other twin in this repo lives, and where "
                    "they all stop. The R760 server reaches its operating "
                    "system, the SN6000 network reaches steady running, and the "
                    "DellProMaxPlus and DellAlienware twins end with the laptop "
                    "working. This trace carries on, because a working machine "
                    "is the middle of the story, not the end."
                ),
                technical=(
                    "Deployment: imaged, enrolled, issued. The ledger does not "
                    "move; ten tonnes is redistributed from warehouse to desks, "
                    "not consumed. This is the state every other twin's trace "
                    "terminates in: the R760 at 'os', the SN6000 fabric at "
                    "'steady', DellProMaxPlus and DellAlienware with the "
                    "machine running. This trace continues, because an "
                    "operating machine is mid-lifecycle, not end-of-lifecycle."
                ),
                expert=(
                    "Imaged, enrolled, issued. Ledger unchanged; mass is "
                    "distributed, not consumed. The point where every other "
                    "twin's trace terminates (R760 'os', SN6000 'steady')."
                ),
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
            description=L(
                standard=(
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
                novice=(
                    "Three years pass in one step. The batteries wear down "
                    "until they hold about 80% of their original charge, "
                    "hinges get loose, and a few laptops break completely and "
                    "are pulled out early. Here the story can go two ways. If "
                    "the battery is glued in and there are no spare parts, a "
                    "company will sensibly replace every laptop around year "
                    "four. That means 5,000 new laptops and another trip "
                    "through the costly factory step. The next two steps show "
                    "what circular design does instead. They make the biggest "
                    "difference in this whole trace, more than recycling, "
                    "even though recycling gets more attention."
                ),
                plain=(
                    "Three years go by in a single step. Batteries fade to "
                    "about 80% of the charge they held when new, hinges loosen, "
                    "and a few percent of the laptops fail and are pulled out "
                    "early. This is where two paths split. With a glued-in "
                    "battery and no spare parts, the sensible company decision "
                    "at year four is to replace every laptop: 5,000 new ones, "
                    "and another trip through the costly factory step. The next "
                    "two steps show what circular design does instead, and they "
                    "are the biggest lever in this trace, bigger than the "
                    "recycling that gets the attention."
                ),
                technical=(
                    "Three years in one step. Cells fade toward 80% of design "
                    "capacity, hinges wear, a few percent of the fleet fails "
                    "and is triaged early. This is where the no-repair and "
                    "repair paths diverge: with bonded cells and no spares, the "
                    "rational call at year four is a full refresh, 5,000 new "
                    "units and a second manufacture pass. The next two steps "
                    "are the circular alternative, and life extension is the "
                    "largest lever in the trace, larger than the recycling that "
                    "gets the attention."
                ),
                expert=(
                    "Three years: cells at ~80% SoH, mechanical wear, early "
                    "failures triaged. Divergence point: without "
                    "field-replaceable cells the rational call is a year-four "
                    "refresh and a second manufacture pass. Life extension is "
                    "the dominant lever."
                ),
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
            description=L(
                standard=(
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
                novice=(
                    "Every laptop gets a new battery. The battery was "
                    "designed years ago so that the owner can replace it, so "
                    "the swap takes about ten minutes with a plastic prying "
                    "tool and a repair guide, or with the AR (augmented "
                    "reality) assistant that shows the steps on screen. "
                    "Nothing has to be shipped back to a repair centre. The "
                    "numbers are what matter: a 300-gram battery keeps a "
                    "2,000-gram laptop in use, and so it puts off building a "
                    "new one in the factory, the step that costs the most. "
                    "Being easy to repair is not a nice extra. It saves more "
                    "material than anything else on this map, because that "
                    "material never has to be processed at all."
                ),
                plain=(
                    "Every laptop gets a new battery. The battery was designed "
                    "years earlier so the owner can replace it, so the job "
                    "takes about ten minutes with a plastic prying tool (a "
                    "spudger) and a repair guide, or with the AR (augmented "
                    "reality) assistant that shows the steps on screen. Nothing "
                    "goes back to a repair depot. The sum is the point: a "
                    "300-gram battery keeps a 2,000-gram laptop working, which "
                    "puts off building a new one in the factory, the most "
                    "costly step. Being easy to repair is not a nice extra. It "
                    "saves the cheapest tonne of material on this map, the one "
                    "that never needs processing."
                ),
                technical=(
                    "Fleet-wide battery replacement. The pack is "
                    "customer-replaceable, a decision taken at the CAD stage, "
                    "so the swap is roughly ten minutes with a spudger and a "
                    "repair tutorial or the AR (augmented reality) assistant, "
                    "with no depot return. A 300 g pack postpones replacing a "
                    "2,000 g device and therefore postpones the manufacture "
                    "stage that dominates the lifetime footprint. Repairability "
                    "is the lowest-cost tonne in the diagram: the one never "
                    "processed."
                ),
                expert=(
                    "Fleet-wide cell swap: user-replaceable pack, ~10 min, no "
                    "depot return. 300 g of parts defers 2 kg of device and a "
                    "manufacture pass. Repairability is the lowest-cost tonne "
                    "in the loop."
                ),
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
            description=L(
                standard=(
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
                novice=(
                    "In year six the laptops get a second round of repairs: "
                    "new keyboards, new fans, some new storage drives. "
                    "Without repairs they would have been replaced in year "
                    "four. Now that replacement has been put off twice, and "
                    "the laptops are on track to last seven years instead of "
                    "four. There is a conflict worth saying out loud. Every "
                    "laptop that is repaired instead of replaced is a laptop "
                    "Dell did not sell, so repair works against the wish to "
                    "sell new machines. Take-back and repair programs exist "
                    "where that conflict was settled in the customer's "
                    "favour, or where laws, buying rules or the second-hand "
                    "market settled it anyway. The design choices still "
                    "count, and so does the conflict."
                ),
                plain=(
                    "Year six brings a second round of repairs: keyboards, fans "
                    "and some storage drives. The refresh that would have come "
                    "at year four without repairs has now been put off twice, "
                    "and the laptops are heading for seven years of use instead "
                    "of four. One conflict should be said plainly. Each laptop "
                    "repaired rather than replaced is a sale Dell did not make, "
                    "so repair works against the business of selling new "
                    "machines. Take-back and repair programs exist where that "
                    "conflict was settled in the customer's favour, or where "
                    "laws, buying rules or the resale market settled it anyway. "
                    "The design choices were real, and so is the conflict."
                ),
                technical=(
                    "Year six, second service pass: keyboards, fans, some SSD "
                    "replacements. The year-four refresh of the no-repair "
                    "baseline has been deferred twice, and the cohort is "
                    "tracking seven service years against four. The tension "
                    "deserves naming: each deferred refresh is a forgone unit "
                    "sale, so repair and refurbishment compete with the "
                    "incentive to ship new hardware. Take-back and repair "
                    "support exist where that was resolved for the customer, or "
                    "where regulation, procurement rules or resale value "
                    "resolved it anyway. Both the design decisions and the "
                    "tension are real."
                ),
                expert=(
                    "Second service pass (keyboards, fans, SSDs); refresh "
                    "deferred twice, seven-year life against a four-year "
                    "baseline. Every deferral is a forgone unit sale, so "
                    "repair support exists where regulation, procurement or "
                    "resale value enforces it."
                ),
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
            description=L(
                standard=(
                    "The cohort is retired through asset recovery: collected, "
                    "inventoried, and every drive cryptographically sanitized "
                    "with a certificate per device — the step that makes "
                    "enterprises willing to hand hardware back at all rather "
                    "than shelving it in a store-room forever. Triage begins, "
                    "and refurbishment is assessed first, deliberately: a "
                    "device broken down for materials that could have been "
                    "resold whole is a loss even though the mass balances. "
                    "From this step onward the ledger must close exactly — "
                    "6,200 kg fit for a second life, 3,350 kg bound for "
                    "material reclamation, and 450 kg that will not come "
                    "back. Reused plus reclaimed plus lost equals ten tonnes, "
                    "to the kilogram, on this step and every step after."
                ),
                novice=(
                    "At year seven the laptops are collected and returned. "
                    "Each one is counted, and every storage drive is wiped so "
                    "securely that the data cannot be recovered, with a "
                    "certificate for each laptop. That certificate is what "
                    "makes companies willing to give their old machines back "
                    "instead of locking them in a cupboard. Then sorting "
                    "begins, and the first question is whether a laptop can "
                    "be fixed up and used again, because taking apart a "
                    "laptop that could have been sold whole wastes it, even "
                    "if every gram is counted. From here on the ledger has to "
                    "add up exactly: 6,200 kg can be used again, 3,350 kg "
                    "will be broken down for materials, and 450 kg will not "
                    "come back. Those three add up to ten tonnes, to the "
                    "kilogram, on this step and every step after it."
                ),
                plain=(
                    "At year seven the laptops are taken back through asset "
                    "recovery. They are collected and counted, and every drive "
                    "is wiped with a method that cannot be undone, with a "
                    "certificate for each laptop. That certificate is what "
                    "makes companies willing to hand old machines back instead "
                    "of locking them in a cupboard. Sorting starts, and the "
                    "first question is whether a laptop can be refurbished, "
                    "because taking apart a laptop that could have been resold "
                    "whole is a loss even when every gram is counted. From here "
                    "the ledger has to add up exactly: 6,200 kg for reuse, "
                    "3,350 kg for material recovery and 450 kg that will not "
                    "come back. Together that is ten tonnes, to the kilogram, "
                    "on this step and every one after."
                ),
                technical=(
                    "Retirement through asset recovery: collection, inventory, "
                    "and cryptographic sanitization of every drive with a "
                    "per-device certificate, the control that gets enterprises "
                    "to return hardware at all. Triage assesses refurbishment "
                    "first, since dismantling a resaleable device is a loss "
                    "even when the mass balances. The ledger now closes "
                    "exactly: 6,200 kg to reuse, 3,350 kg to material "
                    "reclamation, 450 kg lost. Reused + reclaimed + lost = "
                    "10,000 kg, to the kilogram, on this and every later step."
                ),
                expert=(
                    "Asset recovery: collection, inventory, per-device "
                    "certified crypto sanitization. Refurbish triage precedes "
                    "reclamation. Ledger closes exactly from here: 6,200 "
                    "reused + 3,350 reclaimed + 450 lost = 10,000 kg."
                ),
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
            description=L(
                standard=(
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
                novice=(
                    "The sorting is finished, and the material goes three "
                    "ways. The inner loop: 6,200 kg of laptops are fixed up, "
                    "tested, given new batteries and sold or handed out "
                    "again, so each one saves a new laptop from being built. "
                    "The outer loop: 3,350 kg are shredded and separated. "
                    "Steel and aluminium are melted down, circuit boards give "
                    "up their gold and silver, and batteries give back cobalt "
                    "and lithium. And the leak: 450 kg does not come back. "
                    "That is dust too fine to sort, mixed plastics nobody can "
                    "use, and cobalt stuck in furnace waste. The map draws "
                    "that loss on purpose, the same way the IR7000 twin "
                    "measures the heat leaving its rack, because a picture "
                    "that shows only the good paths is an advert. 4.5% of "
                    "this batch, by weight, is gone, and that number tells "
                    "you more about how circular the design really is than "
                    "the recycling rate does."
                ),
                plain=(
                    "Sorting finishes, and the material goes three ways. The "
                    "inner return: 6,200 kg of laptops are retested, given new "
                    "batteries and sold or reissued, and each one saves another "
                    "laptop from being built. The outer return: 3,350 kg are "
                    "shredded and separated. Steel and aluminium go to be "
                    "remelted, circuit boards to precious-metal recovery, "
                    "batteries to cobalt and lithium recovery. And the leak: "
                    "450 kg does not come back, as dust too fine to sort, mixed "
                    "plastic no process wants, and cobalt left in furnace "
                    "waste. The map draws that loss on purpose, as the IR7000 "
                    "twin measures the heat leaving its rack, because a picture "
                    "of only the good paths is an advert. 4.5% of the batch by "
                    "weight is gone, and that figure says more about how "
                    "circular the design is than the recycling rate."
                ),
                technical=(
                    "Sort complete. Inner return: 6,200 kg refurbished "
                    "(retested, re-celled, resold or redeployed), each unit "
                    "deferring a manufacture cycle. Outer return: 3,350 kg "
                    "shredded and separated, ferrous and aluminium to "
                    "closed-loop smelting, boards to precious-metal recovery, "
                    "packs to cobalt and lithium reclamation. The leak: 450 kg "
                    "of shredder fines, unmarketable mixed polymer, and cobalt "
                    "lost to slag. The loss region is drawn for the reason the "
                    "IR7000 twin meters rejected heat. At 4.5% of cohort mass, "
                    "the loss fraction, not the recycling rate, is the honest "
                    "circularity metric."
                ),
                expert=(
                    "Inner return: 6,200 kg refurbished and redeployed. Outer "
                    "return: 3,350 kg shredded, separated, smelted, Co/Li "
                    "recovered. Leak: 450 kg of fines, unmarketable mixed "
                    "polymer, Co in slag. 4.5% loss is the real circularity "
                    "metric."
                ),
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
            description=L(
                standard=(
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
                novice=(
                    "The recovered steel, aluminium, copper, cobalt and "
                    "plastic go back into the pool of raw material. The next "
                    "batch of laptops starts with 46% used material, up from "
                    "34% for this batch. What comes out of one round goes "
                    "into the next, and here you can see it happen. Every "
                    "other trace in this repo ends with a machine running; "
                    "this one ends where it started, one lap further on. Some "
                    "honest limits come along: the leak never closes, rare "
                    "metals are still recycled much less than steel, and the "
                    "biggest reason for the jump to 46% was not recycling at "
                    "all. It was the three extra years of use, which meant "
                    "this material was needed once instead of twice. Tracking "
                    "where the material came from, how much carbon each "
                    "laptop cost and what happened to it at the end works "
                    "like the data pipeline in the DellCloudIQ twin."
                ),
                plain=(
                    "The recovered steel, aluminium, copper, cobalt and plastic "
                    "go back into the materials pool, and the next batch starts "
                    "at 46% recycled material, up from 34% for this one. What "
                    "comes out of one cycle goes into the next, and here it "
                    "happens rather than being claimed. Every other trace in "
                    "this repo ends with a machine running; this one ends where "
                    "it started, one lap on. Some honest limits come along. The "
                    "leak does not close, rare metals are still recycled far "
                    "less than steel, and the biggest single reason for the "
                    "rise to 46% was not recycling: it was three extra years of "
                    "use, so this material was needed once instead of twice. "
                    "Reporting on the loop (where material came from, carbon "
                    "per laptop, what happened at the end) follows the same "
                    "data-to-insight shape as the DellCloudIQ twin."
                ),
                technical=(
                    "Reclaimed steel, aluminium, copper, cobalt and polymer "
                    "re-enter the pool, and the next cohort's input is 46% "
                    "recovered content against this one's 34%: the output of "
                    "one cycle is the input of the next, demonstrated. Every "
                    "other trace here ends in steady state; this one ends at "
                    "its own start, one revolution on. The caveats persist: the "
                    "leak stays open, critical-element recovery lags steel, and "
                    "most of the gain came from three extra service years "
                    "halving demand rather than from reclamation. Provenance, "
                    "per-device carbon and end-of-life reporting follow the "
                    "DellCloudIQ twin's telemetry-to-insight pipeline."
                ),
                expert=(
                    "Reclaimed fractions re-enter the pool: next cohort at "
                    "46% recovered content versus 34%. Loop closed, leak "
                    "open, rare-element recovery lagging. Most of the gain "
                    "came from life extension halving demand, not from "
                    "reclamation. Reporting mirrors DellCloudIQ."
                ),
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
