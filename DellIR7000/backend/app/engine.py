"""Pure thermal bring-up engine for the IR7000 + PowerCool loop.

``simulate()`` returns the deterministic trace of commissioning a
liquid-cooled rack from a dry loop to full design load. Same purity rule as
every other twin in this repo: no FastAPI, no IO, no timers — the frontend
owns the playback clock, and each ``ThermalState`` is plain data the
renderer consumes. ``cycle_cost`` marks the long stages (the leak/flow
verification) so the UI dwells on them.

The storytelling beat that makes a thermal twin different from every
compute twin: nothing here boots. The plot is physics — heat is conserved,
so every watt the IT payload dissipates must leave through the liquid loop
or through the rear-door air coil, and the trace's defining invariant is
that the books balance on every single step
(``liquid_watts + air_watts == it_load_watts``). The loop is proven *empty*
first — fill, pump, leak-check — because the one unrecoverable failure in
liquid cooling is discovering a bad fitting after 264 kW of silicon is
already running above it. Numbers are illustrative but plausible for an
IR7000-class rack; favor a correct mental model over measured numbers
(project scope guardrail).
"""

from __future__ import annotations

from .models import ThermalState

# The four IT bays whose cold plates are the loop's heat source. A real
# IR7000 hosts whatever dense payload the site deploys (an NVL72, XE9685L
# nodes, ...); the bays are drawn generic on purpose.
BAYS = ["b1", "b2", "b3", "b4"]
MANIFOLDS = ["manifold-supply", "manifold-return"]


def _bays() -> list[str]:
    return [f"coldplate-{b}" for b in BAYS]


def simulate() -> list[ThermalState]:
    """The loop's journey from dry to full-load heat balance, as pure data."""
    return [
        ThermalState(
            step=0,
            phase="off",
            label="Rack integrated, loop dry",
            description=(
                "The IR7000 stands connected to facility power and facility "
                "water, its payload racked and its cold plates plumbed — but "
                "the loop is dry and nothing runs. The IR7000 is Dell's Open "
                "Compute ORv3-based rack (a 21-inch open standard that trades "
                "the classic 19-inch frame for more payload width, a shared "
                "DC busbar, and native liquid-cooling provisions). What "
                "follows is not a boot sequence; it is the commissioning of "
                "a small hydraulic plant."
            ),
            active_regions=[],
            it_load_watts=0,
            liquid_watts=0,
            air_watts=0,
            flow_lpm=0,
            elapsed_seconds=0,
        ),
        ThermalState(
            step=1,
            phase="fill",
            label="Loop fills with treated coolant, then degasses",
            description=(
                "The technician fills the rack loop from the CDU (coolant "
                "distribution unit) with treated coolant — typically a "
                "propylene-glycol mix such as PG25 with corrosion "
                "inhibitors, not plain water — and pulls the dissolved air "
                "out. Bubbles are the quiet enemy of liquid cooling: air in "
                "a cold plate makes an insulating pocket exactly where the "
                "heat is, and air in a pump cavitates it. The facility "
                "connection stays isolated behind the CDU's heat exchanger; "
                "rack coolant and facility water will never mix."
            ),
            active_regions=["cdu", "facility"] + MANIFOLDS,
            it_load_watts=0,
            liquid_watts=0,
            air_watts=0,
            flow_lpm=0,
            elapsed_seconds=600,
            cycle_cost=2,
        ),
        ThermalState(
            step=2,
            phase="pump",
            label="CDU pumps start — manifolds pressurize",
            description=(
                "The CDU's redundant pumps spin up and the vertical supply "
                "manifold pressurizes, pushing coolant up the rack, through "
                "every branch, and back down the return manifold. Flow "
                "settles near 300 liters per minute with no heat to carry "
                "yet — the loop is running open-loop, proving it can move "
                "coolant before it is asked to move heat. Each pump can "
                "carry the load alone; like the power shelves on the "
                "compute twins, the redundancy is in parallel units, not a "
                "spare on a shelf."
            ),
            active_regions=["cdu"] + MANIFOLDS,
            it_load_watts=0,
            liquid_watts=0,
            air_watts=0,
            flow_lpm=300,
            elapsed_seconds=900,
        ),
        ThermalState(
            step=3,
            phase="verify",
            label="Leak check and per-branch flow verification",
            description=(
                "The long, careful stage — and deliberately the longest in "
                "this trace. Rope-style leak sensors along the manifolds and "
                "drip trays under every quick disconnect are armed; flow and "
                "temperature sensors on each branch confirm that every cold "
                "plate in every bay actually receives its share of coolant. "
                "A blocked branch would pass a whole-rack flow check and "
                "still cook one server, so commissioning verifies branch by "
                "branch. This is the step that earns the rule the compute "
                "twins inherit: liquid before silicon — the XE9712 twin's "
                "GPUs are interlocked on precisely this verification."
            ),
            active_regions=["sensors"] + MANIFOLDS + _bays(),
            it_load_watts=0,
            liquid_watts=0,
            air_watts=0,
            flow_lpm=300,
            elapsed_seconds=2400,
            cycle_cost=5,
        ),
        ThermalState(
            step=4,
            phase="airdoor",
            label="Rear-door heat exchanger comes online",
            description=(
                "Not every component wears a cold plate — DIMMs, NICs, "
                "power shelves, and drives still shed heat to air. The "
                "enclosed rear-door heat exchanger (eRDHx) is the catch for "
                "that remainder: a water coil and fan wall built into the "
                "rack's rear door that captures the exhaust air's heat and "
                "hands it to the same liquid loop. With the door online, "
                "the rack becomes room-neutral — the aisle behind it stays "
                "at room temperature, and the building's air conditioning "
                "never learns that a quarter-megawatt neighbor moved in."
            ),
            active_regions=["door", "cdu"],
            it_load_watts=0,
            liquid_watts=0,
            air_watts=0,
            flow_lpm=300,
            elapsed_seconds=2700,
        ),
        ThermalState(
            step=5,
            phase="load",
            label="IT load arrives — heat appears on the cold plates",
            description=(
                "Only now is the payload allowed to power on, and with it "
                "the twin's real subject arrives: heat. The first tranche "
                "of IT load dissipates 60 kW, and energy conservation — not "
                "a design goal but a law — dictates that all 60 kW must "
                "leave the rack: here 55 kW through the cold plates into "
                "the liquid loop and 5 kW through air into the rear door. "
                "The busbar current, the coolant's temperature rise, and "
                "the door's coil load are three meters reading the same "
                "physical fact."
            ),
            active_regions=_bays() + ["power-shelf"],
            it_load_watts=60000,
            liquid_watts=55000,
            air_watts=5000,
            flow_lpm=450,
            elapsed_seconds=3000,
        ),
        ThermalState(
            step=6,
            phase="balance",
            label="Pumps and fans modulate as the load climbs",
            description=(
                "The load steps up toward design point and the loop chases "
                "it: the CDU raises pump speed to hold the supply-return "
                "temperature difference steady, and the door's fans track "
                "the exhaust. This is the thermal twin's version of the "
                "compute twins' 'training' stages — a control system "
                "hunting briefly before it settles. Through every "
                "adjustment the books still balance: 150 kW in, 137 kW out "
                "by liquid, 13 kW out by air, not a watt unaccounted for."
            ),
            active_regions=["cdu", "door"] + _bays(),
            it_load_watts=150000,
            liquid_watts=137000,
            air_watts=13000,
            flow_lpm=650,
            elapsed_seconds=3600,
            cycle_cost=2,
        ),
        ThermalState(
            step=7,
            phase="steady",
            label="Full design load — the heat balance holds",
            description=(
                "Steady state at 264 kW — the IR7000's current per-rack "
                "envelope, with Dell's roadmap pointing toward 480 kW. "
                "About ninety-one percent of the heat leaves through the "
                "liquid loop and the rest through the rear door, and at the "
                "facility connection all of it becomes warm water — which a "
                "modern site treats as a product, not a waste stream, "
                "feeding heat-reuse loops or dry coolers that spend a "
                "fraction of a chiller's energy. The rack will hold this "
                "balance for years; the trace ends, the physics does not."
            ),
            active_regions=(
                ["cdu", "door", "power-shelf", "facility", "sensors"]
                + MANIFOLDS + _bays()
            ),
            it_load_watts=264000,
            liquid_watts=240000,
            air_watts=24000,
            flow_lpm=900,
            elapsed_seconds=4200,
        ),
    ]
