"""The narrated tour of the IR7000 + PowerCool loop — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: eight beats that
walk the rack as plumbing, from the outside in to the CDU and the manifolds,
down onto the cold plates, and out through the rear door and the facility
water. Each beat pins the thermal trace at the step whose description makes
the same claim. The frontend player owns the clock; nothing here knows about
time, IO or the web (AST-checked in ``tests/test_tour.py``, the same rule as
``engine.py``).

The signature beat is ``heat-balance``: the first step where IT load exists,
and so the first step where ``liquid_watts + air_watts == it_load_watts`` is
more than 0 + 0 = 0. Every claim the scripts make is one the engine, the
anatomy or ``tests/test_engine.py`` already makes.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``RackAnatomy`` is unchanged:

    0  the rack's skin and trim: power shelf, rear door, instrumentation
    1  what the loop serves and feeds: the IT bays and the facility water
    2  the loop itself: the CDU and the supply/return manifolds
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
from .models import RackAnatomy

#: The step the tests pin: the twin's one idea lives here.
SIGNATURE_STEP_ID = "heat-balance"

_SKIN = 0
_SERVED = 1
_LOOP = 2

_LAYER_BY_KIND = {
    "power": _SKIN,
    "airdoor": _SKIN,
    "sensor": _SKIN,
    "coldplate": _SERVED,
    "facility": _SERVED,
    "cdu": _LOOP,
    "manifold": _LOOP,
}


def layer_map(anatomy: RackAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    return {r.id: _LAYER_BY_KIND.get(r.kind, _SKIN) for r in anatomy.regions}


def build_tour(anatomy: RackAnatomy) -> Tour:
    """The IR7000 tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 2.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    bays = sorted(r.id for r in anatomy.regions if r.kind == "coldplate")
    manifolds = ["manifold-supply", "manifold-return"]
    balance_ids = ["power-shelf", *bays, *manifolds, "cdu", "door"]

    steps = [
        TourStep(
            id="rack-as-plumbing",
            title="A rack drawn as plumbing",
            script=L(
                novice=(
                    "This is a Dell Integrated Rack 7000, or IR7000, drawn the way "
                    "a plumber would see it rather than the way a computer buyer "
                    "would. Across the top is the power shelf, which feeds "
                    "electricity to the computers. The four wide bays in the middle "
                    "hold those computers, drawn plain on purpose, because to the "
                    "cooling system they are simply heaters. Along the bottom sits "
                    "the equipment that moves liquid and carries heat out of the "
                    "building. The pipes are connected, but they are still dry, and "
                    "nothing is running yet. Nothing in this twin boots up. It is "
                    "commissioned, the way you would bring a small water plant into "
                    "service."
                ),
                standard=(
                    "This is the Dell Integrated Rack 7000 (IR7000), a 21-inch "
                    "rack built on the Open Compute Project's Open Rack v3 "
                    "(ORv3) standard, drawn as a cooling system "
                    "rather than a computer. The power shelf across the top feeds "
                    "the load; the four IT bays in the middle are drawn generic, "
                    "because to the loop any payload is just heat; the plant row "
                    "along the bottom moves the coolant and hands the heat to the "
                    "building. Power and water are connected, the loop is dry, and "
                    "nothing runs. What follows is commissioning, not a boot."
                ),
                expert=(
                    "IR7000, ORv3 21-inch, drawn as a loop. Power shelf on top, "
                    "four generic bays, plant row below. Plumbed, dry, "
                    "commissioning rather than bring-up."
                ),
            ),
            camera=whole_map(anatomy),
            # The script names three things: the power shelf on top, the four
            # bays, and the plant row along the bottom.
            region_ids=["power-shelf", *bays, "cdu", "facility", "sensors"],
            layer_reveal=_SKIN,
            trace_cursor=0,
            duration_ms=26_000,
        ),
        TourStep(
            id="cdu-internals",
            title="The CDU keeps two waters apart",
            script=L(
                novice=(
                    "We have peeled the outer trim away and moved to the bottom "
                    "left. This box is the CDU, short for coolant distribution "
                    "unit: Dell calls this one PowerCool. It holds more than one pump, "
                    "and any one of them can do the whole job alone. It also holds a heat "
                    "exchanger, a stack of thin metal plates where warm rack "
                    "coolant passes the building's water without the two ever "
                    "mixing. Right now it is filling the rack's own loop with "
                    "treated coolant, a glycol mix with anti-corrosion additives "
                    "rather than plain water, and then pulling out the air, "
                    "because a bubble in the wrong place blocks heat and wears out "
                    "a pump."
                ),
                standard=(
                    "With the trim peeled back, the camera drops to the CDU "
                    "(coolant distribution unit), Dell's in-rack PowerCool "
                    "RCDU: "
                    "redundant pumps, a plate heat exchanger, and the loop's "
                    "control logic. It keeps rack coolant and facility water "
                    "hydraulically separate, so they trade heat but never mix. "
                    "Here it fills the rack loop with treated coolant, a "
                    "propylene-glycol mix such as PG25 rather than plain water, "
                    "then degasses it: air in a cold plate insulates exactly where "
                    "the heat is, and air in a pump cavitates it."
                ),
                expert=(
                    "PowerCool RCDU: N+1 pumps, plate HX, controls; rack and "
                    "facility loops isolated. Fill with inhibited PG25, degas."
                ),
            ),
            # The bottom-left corner: the CDU and the foot of the supply
            # manifold. The map is 100 x 84, so a frame holding the whole
            # plant row would be nearly the whole map.
            camera=CameraTarget(x=0, y=42, w=50, h=42),
            region_ids=["cdu"],
            layer_reveal=_SERVED,
            trace_cursor=1,
            duration_ms=30_000,
        ),
        TourStep(
            id="supply-and-return",
            title="Up the left, down the right",
            script=L(
                novice=(
                    "Now only the plumbing is left in view. The pumps have started, "
                    "and the tall pipe on the left, the supply manifold, fills with "
                    "cool liquid and pushes it up the rack and into every bay. The "
                    "tall pipe on the right, the return manifold, collects the "
                    "liquid on its way back down to the CDU. About 80 litres a "
                    "minute is moving in this illustrative run, and there is still "
                    "no heat at all. The loop proves it can move liquid before "
                    "anyone asks it to move heat."
                ),
                standard=(
                    "Only the loop itself remains. The CDU's pumps start and the "
                    "supply manifold on the left pressurizes, pushing coolant up "
                    "the rack and into every bay through blind-mate quick "
                    "disconnects; the return manifold on the right carries it back "
                    "down to the heat exchanger. Flow settles near 80 litres per "
                    "minute (illustrative) with zero heat to carry. The order is "
                    "the rule: coolant flows strictly before the first watt of IT "
                    "load, on every run."
                ),
                expert=(
                    "Pumps up; supply manifold left, return right, ~80 L/min "
                    "(illustrative) at zero load. Flow strictly precedes heat."
                ),
            ),
            camera=frame(*manifolds, pad=1.0),
            region_ids=manifolds,
            layer_reveal=_LOOP,
            trace_cursor=2,
            duration_ms=26_000,
        ),
        TourStep(
            id="cold-plates",
            title="Cold plates over generic heat",
            script=L(
                novice=(
                    "Inside each bay, the hottest chips wear a cold plate instead "
                    "of a fan-cooled heatsink: a copper block with channels cut "
                    "through it for the liquid to run. Each bay connects to the "
                    "pipes through dry-break fittings, which seal both sides the "
                    "moment a server is pulled out, so nobody has to drain the "
                    "loop. This is the slowest, most careful stage of all. Leak "
                    "sensors are switched on, and every single branch is checked to "
                    "prove its cold plate gets its share of liquid, because one "
                    "blocked branch could pass a whole-rack check and still cook "
                    "one server. The GPU rack in the XE9712 twin waits for exactly "
                    "this check before it may power on."
                ),
                standard=(
                    "In each bay, processors sit under cold plates: machined "
                    "copper blocks with coolant channels, clamped where a heatsink "
                    "would go, tapped into the manifolds through dry-break quick "
                    "disconnects that seal both halves when a sled is pulled. This "
                    "is the longest stage in the trace. Leak sensors along the "
                    "manifolds are armed, and flow and temperature are verified "
                    "branch by branch, because a blocked branch would pass a "
                    "whole-rack flow check and still cook one server. It is the "
                    "rule the XE9712 twin waits on: liquid before silicon."
                ),
                expert=(
                    "Copper cold plates, dry-break QDs per bay. Max-dwell stage: "
                    "leak detection armed, per-branch flow and temperature "
                    "verified. The XE9712's liquid-before-silicon interlock."
                ),
            ),
            # The verify step exercises the bays' branches, the leak sensors
            # along both manifolds and the instrumentation block, so all of
            # them are lit and all of them are framed.
            camera=frame(*bays, *manifolds, "sensors", pad=1.0),
            region_ids=[*bays, *manifolds, "sensors"],
            layer_reveal=_LOOP,
            trace_cursor=3,
            duration_ms=32_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="Liquid plus air equals the load",
            script=L(
                novice=(
                    "This is the most important moment in the tour. Only now are "
                    "the computers allowed to switch on, and heat finally appears. "
                    "In this illustrative run the first batch of load gives off "
                    "60 kilowatts. Energy cannot vanish, so every one of those "
                    "kilowatts has to leave the rack: 55 go into the liquid "
                    "through the cold plates, and 5 go into the air, where the "
                    "rear door catches them. Add those two numbers and you get "
                    "exactly 60, not roughly 60. The twin checks this on every "
                    "step of the run, with no margin for error allowed, and it "
                    "always balances. Heat is not managed here. It is simply "
                    "accounted for, like money in a ledger that must add up."
                ),
                standard=(
                    "The payload is allowed to power on, and the twin's real "
                    "subject arrives: heat. The first tranche of IT load "
                    "dissipates 60 kW (illustrative), and energy conservation "
                    "dictates that all of it leaves the rack: 55 kW through the "
                    "cold plates into the liquid, 5 kW through air into the rear "
                    "door. Liquid plus air equals IT load, exactly, on every step "
                    "of the trace, with no tolerance. At "
                    "least 85% leaves as liquid whenever there is load; here it is "
                    "about 92%. The busbar, the coolant's temperature rise and the "
                    "door's coil are three meters on one fact."
                ),
                expert=(
                    "Signature: heat balance. 60 kW in (illustrative) = 55 kW "
                    "liquid + 5 kW air. liquid + air == load on every step, zero "
                    "tolerance; liquid share >= 85% under load."
                ),
            ),
            camera=frame(*balance_ids, pad=1.0),
            region_ids=balance_ids,
            layer_reveal=_LOOP,
            trace_cursor=5,
            duration_ms=42_000,
        ),
        TourStep(
            id="rear-door",
            title="The rear door catches the rest",
            script=L(
                novice=(
                    "Not every part wears a cold plate. Memory sticks, network "
                    "cards, drives and the power shelf still warm the air inside "
                    "the rack. The strip on the far right is the rear door, called "
                    "an eRDHx, short for enclosed rear-door heat exchanger. It "
                    "holds a coil of water pipe and a wall of fans that pull the "
                    "warm air through the coil and hand its heat to the same "
                    "liquid loop. As the load climbs to 150 kilowatts in this "
                    "illustrative run, the door carries 13 of them and its fans "
                    "speed up to follow. The pumps speed up too, in step with the "
                    "load, so the liquid comes back about as warm as it did "
                    "before. The aisle behind the rack stays at room temperature."
                ),
                standard=(
                    "Not everything wears a cold plate: DIMMs, NICs, drives and "
                    "the power shelves still heat the air. The enclosed rear-door "
                    "heat exchanger (eRDHx) on the right is the catch for that "
                    "remainder, a water coil and fan wall in the rack's rear door "
                    "that hands exhaust heat to the same loop. As load climbs to "
                    "150 kW, the CDU speeds its pumps in proportion, so the "
                    "coolant's temperature rise holds near 10 K, and the door's "
                    "fans track the exhaust: 137 kW by cold plate, 13 kW by air "
                    "(illustrative). The rack stays room-neutral, meaning its "
                    "exhaust leaves at room temperature. Dell quotes up to 60% "
                    "cooling-energy savings against what it calls standard "
                    "solutions, a baseline this twin's sources do not define."
                ),
                expert=(
                    "eRDHx captures the air-side remainder into the loop. 150 kW: "
                    "137 liquid, 13 air (illustrative); pumps modulate on "
                    "delta-T, door fans track exhaust. Room-neutral."
                ),
            ),
            camera=frame("door", pad=3.0),
            region_ids=["door", "manifold-return"],
            layer_reveal=_LOOP,
            trace_cursor=6,
            duration_ms=30_000,
        ),
        TourStep(
            id="facility-water",
            title="The heat becomes warm water",
            script=L(
                novice=(
                    "At full load the rack gives off 264 kilowatts in this "
                    "illustrative run, the most an IR7000 is rated for today, and "
                    "Dell plans to go almost twice as high. About 91 percent "
                    "leaves through the cold plates and the rest through the rear "
                    "door, and all of it ends up in the same place: the building's "
                    "water, which leaves warm. The heat does not disappear. A "
                    "modern site can use that warm water to heat other spaces, or "
                    "cool it with simple outdoor radiators that use far less "
                    "energy than an air conditioner."
                ),
                standard=(
                    "At full design load, 264 kW, the IR7000's per-rack envelope "
                    "today, with Dell's roadmap pointing at 480 kW. About 91% "
                    "leaves through the liquid (240 kW) and 24 kW through the "
                    "door, and at the facility connection all of it becomes warm "
                    "water. The heat is not destroyed; it becomes someone else's "
                    "warm water, which a modern site treats as a product: it can "
                    "feed heat-reuse loops or dry coolers that spend a fraction of "
                    "a chiller's energy (numbers illustrative)."
                ),
                expert=(
                    "Steady 264 kW (roadmap 480 kW): 240 liquid, 24 air, ~91%. "
                    "All of it exits as warm facility water, suited to heat reuse "
                    "or dry-cooler economization (illustrative)."
                ),
            ),
            # The plant row: the CDU's heat exchanger handing the heat to the
            # facility water. Both lit regions sit wholly inside the frame.
            camera=frame("cdu", "facility"),
            region_ids=["facility", "cdu"],
            layer_reveal=_LOOP,
            trace_cursor=7,
            duration_ms=28_000,
        ),
        TourStep(
            id="reassemble",
            title="Balanced, and staying that way",
            script=L(
                novice=(
                    "The trim goes back on. From a dry rack to full load took "
                    "about seventy minutes in this illustrative timeline, and the "
                    "order never changed: liquid first, then checks, then heat. "
                    "From here the books balance for as long as the rack runs. "
                    "This rack is one of four twins that show one Dell AI factory "
                    "from four sides: the XE9712 makes the heat, the Exascale "
                    "storage feeds it data, and the SN6000 switches carry its "
                    "traffic. The thermal bring-up page walks the same run one "
                    "step at a time."
                ),
                standard=(
                    "Reassembled at steady state. Dry to design load took about "
                    "seventy minutes on this illustrative timeline, always in the "
                    "same order: flow, verification, then heat, and from then on "
                    "liquid plus air equals load. This is the cooling pillar of "
                    "the AI Factory quartet: the XE9712 makes the heat, Exascale "
                    "feeds the data and the SN6000 carries the traffic. The "
                    "thermal bring-up page steps through the same trace."
                ),
                expert=(
                    "Steady state, ~70 min dry to design load (illustrative). "
                    "Flow, verify, heat; balance holds thereafter. Cooling pillar "
                    "beside XE9712, Exascale, SN6000."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[],
            layer_reveal=_SKIN,
            trace_cursor=7,
            duration_ms=24_000,
        ),
    ]

    return Tour(
        id="ir7000-tour",
        title="Inside an IR7000, as the loop comes alive",
        intro=L(
            novice=(
                "A guided walk through the rack's cooling loop as it is brought "
                "into service, narrated beat by beat. Sit back and watch, or pause "
                "and click anything to look closer; the tour waits for you."
            ),
            standard=(
                "A narrated walk through the cooling loop while it is "
                "commissioned. Watch it play, or pause and explore; Resume tour "
                "brings the camera back."
            ),
            expert="Narrated commissioning walk-through. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=[],
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: RackAnatomy) -> TourResponse:
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
