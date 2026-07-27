"""Rack-as-loop anatomy data: an IR7000 with PowerCool cooling, annotated.

Like the other twins, the layout is *data*, not code: regions placed in a
normalized coordinate space the frontend renders as SVG. Geometry is
stylized — favor a correct mental model over exact rack units (project
scope guardrail).

The view is a front elevation of the rack drawn as a cooling system: four
generic IT bays (the heat source — whatever dense payload the site racks)
between a supply manifold on the left and a return manifold on the right,
the enclosed rear-door heat exchanger drawn as the far-right strip, and the
plant row along the bottom — CDU, facility water connection, and the
leak/flow instrumentation. The power shelf across the top feeds the load
whose heat the loop exists to remove.
"""

from __future__ import annotations

from .leveling import L
from .models import Photo, RackAnatomy, RackRegion, SourceLink, Stat

# The only shipped visual is a self-contained schematic drawn for this
# project — not a Dell product image — with an honest credit line.
LOOP_ILLO = Photo(
    url="/ir7000-loop.svg",
    caption=(
        "The IR7000 as a cooling loop, schematically: the CDU pumps treated "
        "coolant up the supply manifold, through cold plates in every IT "
        "bay, and back down the return; the rear-door heat exchanger "
        "catches the air-side remainder; and all of it leaves as warm "
        "facility water."
    ),
    credit="Schematic illustration by this project — not a Dell product image",
)


_BAY_DESC = (
    "An IT bay — the loop's heat source. Whatever dense payload the site "
    "racks here (GB200 NVL72 trays, XE9685L GPU nodes, dense CPU sleds), "
    "its processors sit under cold plates: machined copper blocks with "
    "coolant channels, clamped where a heatsink would go. Each bay taps "
    "the manifolds through blind-mate quick disconnects — dry-break "
    "fittings that seal both halves the instant a sled is pulled — so "
    "service never means draining the loop. To the cooling system a bay is "
    "simply a resistance that turns electricity into hot coolant."
)


def _bay(idx: int, y0: float) -> RackRegion:
    b = f"b{idx}"
    return RackRegion(
        id=f"coldplate-{b}", kind="coldplate", label=f"IT bay {idx} · cold plates",
        x=14, y=y0, w=60, h=14, description=_BAY_DESC,
    )


ANATOMY = RackAnatomy(
    id="ir7000",
    name="Integrated Rack 7000 + PowerCool loop",
    vendor="Dell Technologies",
    form_factor="ORv3 21-inch rack · in-rack CDU · rear-door heat exchanger",
    generation="Dell IR7000 / PowerCool (OCP 2024)",
    year=2024,
    width=100,
    height=84,
    overview=L(
        novice=(
            "Nothing in this twin boots. The subject is not a computer but the "
            "plumbing that keeps computers cool — and at the power levels "
            "modern AI hardware reaches, moving air over it is no longer "
            "enough, so the heat is carried away by liquid instead. The diagram "
            "is the rack drawn as a loop: cool liquid goes up one side, passes "
            "over metal plates pressed against the hot chips, comes back warmer "
            "down the other side, and gives its heat to the building's water "
            "supply. The single most important idea here is that heat does not "
            "disappear. Every watt of electricity that goes into the equipment "
            "comes back out as heat that has to go somewhere, and the whole "
            "design is an argument about where. Watch the two heat figures: "
            "added together, they always equal exactly what the equipment is "
            "drawing."
        ),
        plain=(
            "The Integrated Rack 7000 with PowerCool liquid cooling, at 33 to "
            "264 kW per rack. The subject is a thermal system rather than a "
            "computer, so nothing boots: the map is the rack drawn as a cooling "
            "loop — coolant distribution unit, supply and return manifolds, "
            "cold plates over four generic IT bays, an enclosed rear-door heat "
            "exchanger, facility water, and leak and flow sensors — and the "
            "trace is commissioning and thermal ramp. The governing idea is "
            "conservation: the liquid and air heat figures always sum exactly "
            "to the IT load, because heat does not vanish. Flow is established "
            "before any heat arrives."
        ),
        standard=(
            "The Integrated Rack 7000 is Dell's Open Compute ORv3-based rack "
            "for extreme-density AI and HPC — 33 to 264 kW per rack today, with "
            "a roadmap toward 480 kW — and PowerCool is the liquid-cooling "
            "family that makes such density survivable. This twin draws the "
            "rack as what it thermally is: a closed coolant loop. An in-rack "
            "coolant distribution unit (CDU) pumps treated coolant up a supply "
            "manifold, through cold plates on every processor in every IT bay, "
            "and back down a return manifold to a heat exchanger that hands the "
            "heat to facility water; an enclosed rear-door heat exchanger "
            "(eRDHx) catches the ten-or-so percent that still leaves by air, "
            "making the rack room-neutral. Heat is conserved: every watt the "
            "payload draws through the power shelf leaves through one of those "
            "two paths, and the trace on the first page shows the books "
            "balancing at every step. The layout is a stylized mental model, "
            "not a rack-accurate drawing."
        ),
        technical=(
            "IR7000 with PowerCool, 33–264 kW/rack, roadmap to 480 kW. A "
            "thermal system, not a compute one — the anatomy is the loop: RCDU, "
            "supply/return manifolds, cold plates over four generic bays, "
            "eRDHx, facility water, instrumentation. Phase order fill → pump → "
            "verify → airdoor → load → balance → steady. Asserted with no "
            "tolerance: `liquidWatts + airWatts == itLoadWatts` on every step; "
            "liquid share ≥85% under load; flow strictly precedes the first "
            "watt and is monotonic; per-branch leak and flow verification holds "
            "max dwell. Bays are drawn generic because to the loop any payload "
            "is heat."
        ),
        expert=(
            "Thermal loop, 33–264 kW/rack. `liquidWatts + airWatts == "
            "itLoadWatts` asserted exactly, no tolerance — the twin's reason "
            "for existing. Liquid share ≥85% under load; flow strictly precedes "
            "heat and is monotonic; leak/flow verification holds max dwell. "
            "Payload drawn generic: to the loop it is heat."
        ),
    ),
    regions=[
        RackRegion(
            id="power-shelf", kind="power", label="Power shelf → busbar",
            x=2, y=1, w=92, h=6,
            description=(
                "The ORv3 power shelf and DC busbar feeding the IT bays — "
                "the same centralized-rectification design the XE9712 twin "
                "describes. In this twin it matters as the *input* side of "
                "the energy balance: the wattage flowing through this "
                "busbar is exactly the heat the loop below must remove. "
                "Cooling capacity and power capacity are two views of one "
                "number, which is why Dell sizes IR7000 power and PowerCool "
                "cooling as a matched pair."
            ),
        ),
        _bay(1, 9),
        _bay(2, 25),
        _bay(3, 41),
        _bay(4, 57),
        RackRegion(
            id="manifold-supply", kind="manifold", label="Supply",
            x=2, y=9, w=9, h=62,
            description=(
                "The vertical supply manifold: cool coolant from the CDU "
                "rises here and branches into every IT bay through "
                "blind-mate quick disconnects. Manifolds are sized "
                "generously — hundreds of liters per minute at full load — "
                "because pressure drop is pump energy, and pump energy is "
                "overhead the facility pays forever."
            ),
        ),
        RackRegion(
            id="manifold-return", kind="manifold", label="Return",
            x=77, y=9, w=9, h=62,
            description=(
                "The vertical return manifold: coolant leaves each bay a "
                "few degrees warmer and collects here on its way back to "
                "the CDU's heat exchanger. The supply-to-return temperature "
                "rise is the loop's most honest gauge — flow times "
                "temperature rise *is* the heat being carried, and the CDU "
                "modulates its pumps to hold that rise steady as load "
                "changes."
            ),
        ),
        RackRegion(
            id="door", kind="airdoor", label="eRDHx",
            x=88, y=9, w=10, h=62,
            description=(
                "The enclosed rear-door heat exchanger (eRDHx): a water "
                "coil and fan wall built into the rack's rear door. "
                "Components without cold plates — DIMMs, NICs, drives, the "
                "power shelves — still heat the air inside the rack; the "
                "door captures that exhaust heat and returns it to the "
                "liquid loop instead of the room. Dell quotes up to 60% "
                "cooling-energy savings versus conventional room cooling, "
                "and the practical effect is that a 264 kW rack is "
                "room-neutral: the aisle behind it stays office-warm."
            ),
        ),
        RackRegion(
            id="cdu", kind="cdu", label="PowerCool CDU — pumps + heat exchanger",
            x=2, y=75, w=44, h=8,
            description=(
                "The in-rack coolant distribution unit, Dell's PowerCool "
                "RCDU family: redundant pumps, a plate heat exchanger, and "
                "the loop's control brain. It keeps the rack loop and the "
                "facility water hydraulically separate — they exchange heat "
                "through the plate exchanger but never mix, so a facility "
                "water-quality problem cannot corrode a cold plate. Rated "
                "on the order of 160 kW per unit; extreme racks pair units "
                "or step up to row-scale CDUs."
            ),
        ),
        RackRegion(
            id="facility", kind="facility", label="Facility water",
            x=48, y=75, w=28, h=8,
            description=(
                "The facility water connection — where every watt "
                "ultimately goes. Warm water leaving here is the rack's "
                "true output, and modern sites treat it as a resource: at "
                "the elevated temperatures direct liquid cooling allows, "
                "the return loop can feed heat-reuse systems or dry "
                "coolers that spend a fraction of a chiller's energy. The "
                "twin ends the story here on purpose: the heat does not "
                "disappear, it just becomes someone else's warm water."
            ),
        ),
        RackRegion(
            id="sensors", kind="sensor", label="Leak / flow / temp",
            x=78, y=75, w=20, h=8,
            description=(
                "The loop's instrumentation: rope-style leak sensors along "
                "the manifolds, drip trays under quick disconnects, and "
                "flow and temperature probes on every branch. This is what "
                "the verify phase exercises branch by branch, and what the "
                "management plane watches forever after — the XE9712 twin's "
                "'liquid before silicon' interlock is, concretely, these "
                "sensors saying yes."
            ),
        ),
    ],
    stats=[
        Stat(label="Rack standard", value="OCP ORv3 · 21-inch open rack"),
        Stat(label="Power envelope", value="33–264 kW today · 480 kW roadmap"),
        Stat(label="CDU", value="PowerCool RCDU — ~160 kW class, redundant pumps"),
        Stat(label="Air-side catch", value="eRDHx rear door · up to 60% cooling-energy savings"),
        Stat(label="Heat split at load", value="~90% liquid · ~10% air (door-captured)"),
        Stat(label="Coolant", value="Treated propylene-glycol mix (e.g. PG25)"),
        Stat(label="Service", value="Blind-mate dry-break quick disconnects per bay"),
    ],
    photo=LOOP_ILLO,
    sources=[
        SourceLink(
            label="Dell announcement — IR7000, PowerCool at OCP 2024",
            url="https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2024~10~dell-servers-storage-at-ocp.htm",
        ),
        SourceLink(
            label="Dell — cooling and computing innovations (eRDHx, RCDU)",
            url="https://www.dell.com/en-us/blog/power-future-ai-dell-cooling-servers/",
        ),
        SourceLink(
            label="Dell Integrated Rack Scalable Systems",
            url="https://www.dell.com/en-us/shop/storage-servers-and-networking-for-business/sf/integrated-rack-scalable-systems",
        ),
        SourceLink(
            label="Open Compute Project — Open Rack v3",
            url="https://www.opencompute.org/projects/rack-and-power",
        ),
    ],
)
