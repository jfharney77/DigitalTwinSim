"""The narrated tour of the circular-design loop — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: eight beats
that follow one laptop cohort's material ledger around the loop, peel the
map from the forward line everyone draws to the afterlife almost nobody
draws, pin the lifecycle trace at the moments that carry the story, and
narrate each one. The frontend player owns the clock; nothing here knows
about time, IO or the web (AST-checked in ``tests/test_tour.py``, the same
rule as ``engine.py``).

The storyboard is ACTIVE_TWIN_SPEC.md section 8's DellCircularDesign row —
the product whole, disassembly, material streams out, back into a new
product — told with what this twin's engine actually models. The engine
has no per-device fastener count, so the tour does not invent one: the
disassembly beat narrates what the anatomy and trace do say (screws rather
than glue, a battery that lifts out, certified wipe, refurbish-first
triage) and pins the step where the mass ledger opens. The signature beat
is ``disassembly``: from that trace step on, reused + reclaimed + lost ==
mass, to the kilogram (``tests/test_engine.py::test_mass_is_conserved``).

Layers (region id -> layer) ride with the tour rather than on the
``LifecycleMap`` model, so the anatomy is unchanged. For a loop the
"outside" is the part of the story every brochure already shows:

    0  the forward line: materials, packaging, manufacture, deployment
    1  the service loop that keeps devices in use
    2  the afterlife: recovery and its three exits (refurbish, reclaim, loss)
"""

from __future__ import annotations

from twinkit.tour import (
    CameraTarget,
    Tour,
    TourResponse,
    TourSource,
    TourStep,
    camera_around,
    whole_map,
)

from .leveling import L
from .models import LifecycleMap

#: The step the tests pin: the product's one idea lives here.
SIGNATURE_STEP_ID = "disassembly"

_FORWARD = 0
_SERVICE = 1
_AFTERLIFE = 2

_KIND_LAYER = {
    "materials": _FORWARD,
    "packaging": _FORWARD,
    "manufacture": _FORWARD,
    "deployment": _FORWARD,
    "service": _SERVICE,
    "recovery": _AFTERLIFE,
    "refurbish": _AFTERLIFE,
    "reclaim": _AFTERLIFE,
    "loss": _AFTERLIFE,
}


def layer_map(anatomy: LifecycleMap) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here (unknown kinds count as
    afterlife: anything new on this map is most likely an exit)."""
    return {r.id: _KIND_LAYER.get(r.kind, _AFTERLIFE) for r in anatomy.regions}


def build_tour(anatomy: LifecycleMap) -> Tour:
    """The circular-design tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 3.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    steps = [
        TourStep(
            id="the-product-whole",
            title="Ten tonnes, a third of it used before",
            script=L(
                novice=(
                    "This map is not a machine. It is the life of the material "
                    "inside a batch of 5,000 laptops, drawn as a loop. The "
                    "numbers in this tour are illustrative, but chosen to be "
                    "plausible. The batch starts as about ten tonnes of "
                    "material: aluminium and steel for the cases, copper for "
                    "wires and circuit boards, cobalt and lithium for the "
                    "batteries, and plastic. About a third of it, 34% by "
                    "weight, has been used before. Only the materials box is "
                    "lit for now. Most stories about a product stop at the "
                    "Deployment box, where the laptops reach the people who "
                    "use them. This one follows the material all the way "
                    "around the loop."
                ),
                standard=(
                    "This map is a lifecycle, not a machine: the material "
                    "inside a cohort of 5,000 laptops, drawn as a loop. The "
                    "figures are illustrative. The cohort begins as ten tonnes "
                    "in the materials pool, aluminium, steel, copper, cobalt, "
                    "lithium and plastics, and 34% of it by mass is already "
                    "recovered material. That share is easiest in steel and "
                    "plastics and hardest in the rare elements, so 34% "
                    "overall is not 34% of the cobalt. Only the materials "
                    "pool is lit; the loop around it is what the rest of the "
                    "tour follows."
                ),
                expert=(
                    "Lifecycle map, 5,000-unit cohort, 10 t input, 34% "
                    "recovered content by mass (steel/polymer weighted). "
                    "Illustrative figures. Recovered Co share far below the "
                    "average."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["materials"],
            layer_reveal=_FORWARD,
            trace_cursor=0,
            duration_ms=26_000,
        ),
        TourStep(
            id="built-once",
            title="The expensive step",
            script=L(
                novice=(
                    "The factory builds the circuit boards, forms the "
                    "batteries, makes the cases and assembles all 5,000 "
                    "laptops. It is the longest stop on the timeline because "
                    "it costs the most. Most of the energy, water and "
                    "pollution a laptop will ever cause is spent here, before "
                    "anyone switches it on. That is called embodied carbon. "
                    "Keep it in mind, because the rest of the tour is about "
                    "not having to repeat this step. The XE9712 rack twin "
                    "makes the same point in tonnes instead of kilograms."
                ),
                standard=(
                    "Manufacture is the trace's longest stage, and the "
                    "expensive one. Most of a laptop's lifetime energy, water "
                    "and emissions are committed here before it computes "
                    "anything; that is embodied carbon. Every later decision "
                    "on this map is judged against it, because a repair "
                    "defers repeating this step, and nothing recovered at end "
                    "of life pays back what manufacture already spent. The "
                    "DellPowerEdgeXE9712 twin runs the "
                    "same arithmetic at rack scale."
                ),
                expert=(
                    "Manufacture: unique max dwell. Embodied carbon dominates "
                    "the lifecycle; deferral beats recovery. See XE9712 for "
                    "rack scale."
                ),
            ),
            camera=frame("materials", "packaging", "manufacture", pad=2.0),
            region_ids=["materials", "manufacture"],
            layer_reveal=_FORWARD,
            trace_cursor=1,
            duration_ms=28_000,
        ),
        TourStep(
            id="where-other-twins-stop",
            title="Where every other twin stops",
            script=L(
                novice=(
                    "The laptops are shipped, set up and handed to the people "
                    "who will use them. On the material ledger, the running "
                    "count of where every kilogram is, nothing changes: the "
                    "same ten tonnes sit on desks instead of in a warehouse. "
                    "This is where almost every other twin in this collection "
                    "ends. The R760 server reaches its operating system, the "
                    "SN6000 network reaches a steady state, and the Pro Max "
                    "Plus and Alienware laptop twins end with the machine "
                    "running. This one keeps going."
                ),
                standard=(
                    "Shipped, imaged and issued. The material ledger does not "
                    "move here: ten tonnes is redistributed onto desks, not "
                    "consumed. This is the state every other twin's trace ends "
                    "in, the R760 at its operating system, the SN6000 fabric "
                    "at steady, the DellProMaxPlus and DellAlienware clients "
                    "running. The devices on this map are those clients, and "
                    "their final state is the middle of this story."
                ),
                expert=(
                    "Deployed; ledger static. The terminal state of every "
                    "other trace (R760 'os', SN6000 'steady') is mid-loop "
                    "here."
                ),
            ),
            camera=frame("manufacture", "deployment", pad=3.0),
            region_ids=["deployment"],
            layer_reveal=_FORWARD,
            trace_cursor=3,
            duration_ms=24_000,
        ),
        TourStep(
            id="repair-not-replace",
            title="Repair defers a factory run",
            script=L(
                novice=(
                    "Three years in, the batteries hold about 80% of their "
                    "first charge. With a glued-in battery, a company would "
                    "sensibly replace every laptop at year four, and the "
                    "factory step would run again. These batteries were "
                    "designed so the owner can swap them in about ten "
                    "minutes. A 300-gram battery keeps a 2,000-gram laptop "
                    "working. A second round of repairs at year six, "
                    "keyboards, fans and drives, stretches the batch to "
                    "seven years instead of four. That, not recycling, is "
                    "the biggest saving on the map. It also means fewer new "
                    "laptops sold, a conflict the twin names openly."
                ),
                standard=(
                    "The service loop is the largest lever on the map. At "
                    "year three the cells are near 80% of design capacity, "
                    "and without replaceable parts the rational call is a "
                    "year-four refresh and a second manufacture pass. "
                    "Instead, a ten-minute battery swap, 300 grams of part "
                    "keeping two kilograms of device in use, and a second "
                    "service pass at year six carry the cohort to seven "
                    "years against a four-year baseline. Every deferred "
                    "refresh is also a sale not made, and the twin says so."
                ),
                expert=(
                    "Two service passes: user-replaceable cells, then "
                    "keyboards/fans/SSDs. Seven years versus the four-year "
                    "no-repair baseline; each deferral skips a manufacture "
                    "pass and a sale."
                ),
            ),
            camera=frame("deployment", "service", pad=3.0),
            region_ids=["deployment", "service"],
            layer_reveal=_SERVICE,
            trace_cursor=6,
            duration_ms=30_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="Taken back, and every kilogram counted",
            script=L(
                novice=(
                    "At year seven the batch comes back. This is asset "
                    "recovery: every laptop is collected and counted, and "
                    "every drive is wiped so the data cannot be recovered, "
                    "with a certificate per laptop, which is what makes "
                    "companies willing to hand machines back at all. Then the "
                    "laptops are sorted, and the first question is always "
                    "whether one can be fixed up and used again. What the "
                    "sorters can do was decided years earlier, when the "
                    "laptop was designed: screws instead of glue, a battery "
                    "that lifts out. And from this moment the ledger must add up "
                    "exactly. 6,200 kilograms will be reused, 3,350 "
                    "kilograms broken down into materials, and 450 "
                    "kilograms lost. Together that is 10,000 kilograms, to "
                    "the kilogram, with no rounding allowed. It is the same "
                    "rule the IR7000 cooling twin applies to heat, applied "
                    "here to matter. This is the twin's one idea: mass in "
                    "equals mass out."
                ),
                standard=(
                    "The cohort returns through asset recovery: collected, "
                    "inventoried, every drive cryptographically sanitized "
                    "with a certificate per device. Triage tries "
                    "refurbishment first, because dismantling a device that "
                    "could have been resold whole is a loss even when the "
                    "mass balances, and what triage can do was fixed years "
                    "earlier at the design stage, by screws rather than glue "
                    "and a battery that lifts out. From this step the ledger closes "
                    "exactly: 6,200 kg reused, 3,350 kg reclaimed, 450 kg "
                    "lost, 10,000 kg in all, with no tolerance. It is the "
                    "IR7000's heat balance applied to matter: mass in "
                    "equals mass out."
                ),
                expert=(
                    "Signature: the ledger opens. Certified sanitization, "
                    "refurbish-first triage. Reused + reclaimed + lost = "
                    "6,200 + 3,350 + 450 = 10,000 kg, exact, on every step "
                    "from here."
                ),
            ),
            camera=frame("recovery", "refurbish", "reclaim", "loss", pad=2.0),
            region_ids=["recovery", "refurbish", "reclaim", "loss"],
            layer_reveal=_AFTERLIFE,
            trace_cursor=7,
            duration_ms=42_000,
        ),
        TourStep(
            id="material-streams",
            title="Two returns, at two radii",
            script=L(
                novice=(
                    "The sorted material leaves by two roads home. The short "
                    "road is refurbishment: 6,200 kilograms of laptops are "
                    "tested, given new batteries and sold or handed out "
                    "again, and each one saves a new laptop from being "
                    "built. The long road is reclamation: 3,350 kilograms "
                    "are shredded and separated by magnets and other "
                    "sorting machines, the metals are melted down, and "
                    "cobalt and lithium are pulled out of the batteries with "
                    "chemicals. The map draws the short road as a tighter "
                    "curve on purpose, because reusing a laptop beats "
                    "recycling it."
                ),
                standard=(
                    "The sort completes, and two returns leave recovery. The "
                    "inner return, refurbishment, carries 6,200 kg of whole "
                    "devices back to deployment, each deferring a "
                    "manufacturing cycle. The outer return, reclamation, "
                    "carries 3,350 kg through shredding, magnetic and "
                    "eddy-current separation, and hydrometallurgy, chemical "
                    "leaching of cobalt and lithium, back to the materials "
                    "pool. The map draws them at two radii because reuse "
                    "is the tighter, better circle."
                ),
                expert=(
                    "Inner return 6,200 kg (refurbish to deployment); outer "
                    "return 3,350 kg (shred, separate, smelt, leach Co/Li). "
                    "Reuse outranks reclaim."
                ),
            ),
            # The two roads end at deployment and at the materials pool, so
            # both ends are lit and framed: on this map an edge fades with its
            # fainter end, and ghosting either end would erase the very
            # returns the beat is about.
            camera=frame(
                "recovery", "refurbish", "reclaim", "deployment", "materials",
                pad=2.0,
            ),
            region_ids=["recovery", "refurbish", "reclaim", "deployment", "materials"],
            layer_reveal=_AFTERLIFE,
            trace_cursor=8,
            duration_ms=30_000,
        ),
        TourStep(
            id="the-leak",
            title="The leak is drawn",
            script=L(
                novice=(
                    "Now the box most lifecycle diagrams leave out. 450 "
                    "kilograms does not come back: dust from the shredder "
                    "too fine to sort, mixed plastics nobody can use, and "
                    "cobalt stuck in furnace waste. That is 4.5% of the "
                    "batch by weight. This box has no arrow leaving it, "
                    "because that is what a leak is. The twin's tests fail "
                    "if the batch ends with nothing lost, because no real "
                    "supply chain loses nothing. The IR7000 cooling twin measures "
                    "the heat leaving its rack for the same reason."
                ),
                standard=(
                    "The third exit is the leak, drawn at full size with no "
                    "outgoing edge: 450 kg of shredder fines, unmarketable "
                    "mixed plastics, and cobalt left in slag, 4.5% of the "
                    "cohort's mass. The twin's tests require it to be "
                    "nonzero and lit during the sort, because a map of only "
                    "the virtuous paths is marketing. The loss fraction, not "
                    "the recycling rate, is the honest measure of how "
                    "circular the design is, just as the IR7000 twin meters "
                    "the heat leaving its rack."
                ),
                expert=(
                    "Loss: 450 kg, 4.5%, sole terminus. Tested nonzero and "
                    "monotonic. The circularity figure of merit, as metered "
                    "heat is for IR7000."
                ),
            ),
            camera=frame("loss", "reclaim", pad=3.0),
            region_ids=["loss"],
            layer_reveal=_AFTERLIFE,
            trace_cursor=8,
            duration_ms=26_000,
        ),
        TourStep(
            id="the-ledger-closes",
            title="Back into a new product",
            script=L(
                novice=(
                    "The recovered metal and plastic go back into the "
                    "materials pool where the tour started, and the next "
                    "batch of laptops begins with 46% used material instead "
                    "of 34%. What comes out of one cycle goes into the next. "
                    "Every other trace in this collection ends with a machine "
                    "running; this one ends where it began, one lap further "
                    "on. The leak stays open, and the biggest reason for the "
                    "rise was not recycling at all. It was the three extra "
                    "years of use, so this material was needed once instead "
                    "of twice. Press play on the first page to walk the same "
                    "ledger step by step."
                ),
                standard=(
                    "Reclaimed material re-enters the pool, and the next "
                    "cohort starts at 46% recovered content against this "
                    "one's 34%: the output of one cycle is the input of the "
                    "next. Every other trace here ends in steady state; this "
                    "one ends at its own beginning, one turn further on. The "
                    "caveats travel with it: the leak stays open, and most "
                    "of the gain came from three extra years of service, not "
                    "from reclamation. The reporting side follows the "
                    "DellCloudIQ twin's pipeline."
                ),
                expert=(
                    "Loop closed: next cohort at 46% recovered content versus "
                    "34%. Leak open; life extension, not reclamation, drove "
                    "the gain."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["reclaim", "materials"],
            layer_reveal=_FORWARD,
            trace_cursor=9,
            duration_ms=30_000,
        ),
    ]

    return Tour(
        id="circular-design-tour",
        title="One cohort, all the way around",
        intro=L(
            novice=(
                "A guided walk around the loop, following the material in "
                "5,000 laptops from the factory to the next batch, narrated "
                "beat by beat. Watch it play, or pause and click any block "
                "to read about it; the tour waits for you."
            ),
            standard=(
                "A narrated walk around the material loop, from input to the "
                "next cohort. Watch it play, or pause and explore; Resume "
                "tour brings the camera back."
            ),
            expert="Narrated walk around the loop. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=[],
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: LifecycleMap) -> TourResponse:
    """The ``GET /api/tour`` payload: the tour plus the layer map and bounds."""
    return TourResponse(
        tour=build_tour(anatomy),
        layers=layer_map(anatomy),
        map_width=anatomy.width,
        map_height=anatomy.height,
    )


# Built once at import, like ANATOMY: importing the module registers the
# narration's reading-level variants, which tests/test_leveling.py relies on.
from .anatomy import ANATOMY  # noqa: E402  (after the builders it feeds)

TOUR_RESPONSE = build_response(ANATOMY)
