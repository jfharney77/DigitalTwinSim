"""Loop map for the CDU twin — the rack drawn as a cooling circuit.

Left to right: the facility water plant, its supply/return pipes, the
heat exchanger inside the 4U CDU (pumps below, the Integrated Rack
Controller above), then the vertical supply/return manifolds bracketing
six tray banks. Regions are thermal zones keyed to the engine's
``region_temps`` dict; the frontend paints them on a fixed 10–80 °C
scale. Stylized — a mental model of a coolant loop, not a P&ID.
"""

from __future__ import annotations

from .leveling import L
from .models import LoopMap, LoopRegion


def _pump(i: int) -> LoopRegion:
    return LoopRegion(
        id=f"pump-{i}", kind="pump", label=f"Pump {i + 1}",
        x=28 + i * 9.5, y=44, w=8, h=7,
        description=(
            "One of the CDU's redundant secondary-loop pumps. Parallel "
            "pumps share a system curve, so two pumps deliver about 1.6× "
            "one pump's flow — not 2× — and losing one costs less flow "
            "than you'd guess. Pump power follows the cube of speed. "
            "Click to fail this pump and watch the survivors ramp."
        ),
    )


def _tray(i: int) -> LoopRegion:
    return LoopRegion(
        id=f"tray-{i}", kind="tray", label=f"Tray bank {i + 1}",
        x=74, y=2 + i * 9, w=19, h=8,
        description=(
            "One bank of liquid-cooled compute trays (~40 kW at full "
            "tilt — about six GB200-class trays behind cold plates). To "
            "the loop, a bank is just heat: its silicon rides the "
            "supply temperature plus the loop's rise plus the cold "
            "plate's own resistance. The IRC can cap it; its own "
            "firmware can trip it. The difference between those two "
            "endings is this twin's whole argument."
        ),
    )


ANATOMY = LoopMap(
    id="powercool-cdu",
    name="PowerCool CDU C7000 · rack cooling loop",
    vendor="Dell Technologies",
    form_factor="4U in-rack coolant distribution unit + tray banks",
    generation="PowerRack era (announced Dell Technologies World 2026)",
    year=2026,
    width=100,
    height=60,
    overview=L(
        novice=(
            "This is a map of how heat leaves a modern AI rack. The "
            "computers on the right make heat — a lot of it, more than "
            "air could ever carry. Cold liquid is pumped through metal "
            "plates pressed against the chips, picks the heat up, and "
            "carries it to the box in the middle: the CDU, a heat "
            "exchanger with pumps. There the rack's liquid hands its "
            "heat across a metal wall to the building's water on the "
            "left, without the two liquids ever mixing. Two rules run "
            "everything you'll watch: the rack's liquid can never be "
            "colder than the building's water plus a little, and it "
            "must never be so cold that water condenses on the pipes. "
            "When the building's water runs warm, the whole chain "
            "shifts up — and something has to give. The controller at "
            "the top decides what: slow every computer down a little, "
            "together, or let each one panic on its own."
        ),
        standard=(
            "The rack drawn as a cooling circuit. Facility water (left) "
            "crosses a plate heat exchanger in the 4U CDU (center) and "
            "never mixes with the treated coolant the pumps push out to "
            "the tray banks (right). The physics is a chain of three "
            "temperatures: secondary supply = facility supply + the "
            "heat exchanger's approach (Q ÷ UA, worse at low flow); "
            "loop rise = Q ÷ (ṁ·cp); silicon = supply + half the rise "
            "+ the cold plate's resistance. Both loops carry the same "
            "heat on every tick — that identity is asserted in the "
            "tests. Above it all sits the Integrated Rack Controller: "
            "in coordinated mode it sheds load gracefully (uniform "
            "power caps, silicon held at target); uncoordinated, each "
            "tray bank self-protects and a warm-water day becomes a "
            "staggered cascade of trips. The dew-point floor is the "
            "constraint people forget: the mixing valve will not let "
            "supply coolant below dew point + margin, because "
            "condensation on a cold plate is a worse day than warm "
            "silicon."
        ),
        expert=(
            "Primary ↔ plate HX ↔ secondary; approach = Q/(UA·ff), "
            "ff = (flow/nom)^0.6; ΔT = Q/(ṁcp); chip = supply + ΔT/2 "
            "+ R_th·q. Pumps: Q(k) ∝ k^0.65, P ∝ s³. Supply floored at "
            "max(setpoint, dew+2). IRC: coordinated = uniform caps to "
            "target; uncoordinated = staggered firmware trips. Both "
            "loops carry equal Q per tick, asserted."
        ),
    ),
    regions=[
        LoopRegion(
            id="facility-plant", kind="facility", label="Facility water",
            x=1, y=16, w=10, h=22,
            description=(
                "The building's technology cooling system — chillers, "
                "dry coolers, or a warm-water loop. Its supply "
                "temperature is the floor under everything downstream: "
                "no heat exchanger can deliver coolant colder than the "
                "water on its other side. ASHRAE's W-classes (W32, W45) "
                "are bands for this number."
            ),
        ),
        LoopRegion(
            id="pipe-fac-supply", kind="pipe", label="Facility supply",
            x=12, y=18, w=15, h=5,
            description=(
                "Facility water in. The CDU's primary-side valve "
                "modulates this flow to hold a ~6 K design rise — more "
                "heat, more water."
            ),
        ),
        LoopRegion(
            id="pipe-fac-return", kind="pipe", label="Facility return",
            x=12, y=31, w=15, h=5,
            description=(
                "Facility water out, carrying every watt the rack made. "
                "Return = supply + Q ÷ (ṁ·cp): the identity the IR7000 "
                "twin enforces for a whole rack, here measured at the "
                "building wall. Warm enough to be worth reusing."
            ),
        ),
        LoopRegion(
            id="hx", kind="hx", label="Heat exchanger",
            x=28, y=14, w=14, h=26,
            description=(
                "The plate heat exchanger at the CDU's core — two loops "
                "pressed together across metal, never mixing. Its "
                "conductance (UA) sets the approach temperature: the "
                "unavoidable gap between facility supply and rack "
                "supply, which grows with heat and shrinks with flow. "
                "When people say a CDU 'moves 220 kW', this is the part "
                "they mean."
            ),
        ),
        LoopRegion(
            id="irc", kind="controller", label="Integrated Rack Controller",
            x=28, y=2, w=18, h=8,
            description=(
                "Dell's rack-scope management plane — iDRAC's idea, "
                "grown to rack scale. It reads the loop's sensors "
                "(leak detection in seconds, per Dell's announcement) "
                "and owns the policy this twin exists to compare: on a "
                "warm-water day, cap every tray bank a little, "
                "together — or let each bank discover the problem "
                "alone and trip."
            ),
        ),
        *[_pump(i) for i in range(3)],
        LoopRegion(
            id="pipe-sec-supply", kind="pipe", label="Coolant supply",
            x=43, y=16, w=24, h=5,
            description=(
                "Treated coolant (PG25) leaving the CDU for the rack. "
                "Its temperature is the chain's middle link: facility "
                "supply + approach, but never below the dew-point "
                "floor — the mixing valve sees to that."
            ),
        ),
        LoopRegion(
            id="pipe-sec-return", kind="pipe", label="Coolant return",
            x=56.5, y=45, w=11, h=5,
            description=(
                "Hot coolant back from the tray banks, headed for the "
                "pumps and the heat exchanger. Return − supply is the "
                "loop rise, Q ÷ (ṁ·cp): the number that says whether "
                "the flow matches the heat."
            ),
        ),
        LoopRegion(
            id="manifold-supply", kind="manifold", label="Supply manifold",
            x=68, y=2, w=4, h=54,
            description=(
                "The vertical supply manifold feeding every tray bank "
                "through dry-break quick disconnects — the same part "
                "the IR7000 twin draws, seen from the CDU's side of "
                "the story."
            ),
        ),
        *[_tray(i) for i in range(6)],
        LoopRegion(
            id="manifold-return", kind="manifold", label="Return manifold",
            x=95, y=2, w=4, h=54,
            description=(
                "The return manifold collecting hot coolant from every "
                "bank. Everything the silicon made passes through here "
                "on its way back to the heat exchanger."
            ),
        ),
    ],
    sources=[
        {"label": "Dell announcement coverage — PowerRack, PowerCool CDU "
                  "C7000, Integrated Rack Controller (DCD)",
         "url": "https://www.datacenterdynamics.com/en/news/dell-launches-powerrack-a-turnkey-compute-storage-and-networking-solution-updates-nvidia-ai-factory-platform/"},
        {"label": "Dell Technologies DTW 2026 press release",
         "url": "https://www.businesswire.com/news/home/20260518066830/en/Dell-Technologies-Closes-the-Gap-Between-AI-Ambition-and-AI-Outcomes"},
        {"label": "ASHRAE liquid-cooling guidelines (W-classes, dew point)",
         "url": "https://www.ashrae.org/technical-resources/bookstore/datacom-series"},
    ],
)
