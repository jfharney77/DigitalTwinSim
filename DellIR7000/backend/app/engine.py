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

from .leveling import L
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
            description=L(
                novice=(
                    "The rack stands connected to the building's power and water, "
                    "with equipment installed and cooling plates plumbed in — but "
                    "the pipes are dry and nothing is running. What follows is not "
                    "a startup sequence. Nothing here boots. It is a commissioning "
                    "procedure: the careful, methodical process of proving a "
                    "cooling system works before you trust expensive equipment to "
                    "it."
                ),
                plain=(
                    "The IR7000 stands connected to facility power and water, its "
                    "payload racked and its cold plates plumbed — but the loop is "
                    "dry and nothing runs. This is Dell's Open Compute ORv3-based "
                    "rack, a 21-inch open standard that trades the classic 19-inch "
                    "frame for more payload width, a shared DC busbar, and native "
                    "liquid-cooling provisions. What follows is not a boot "
                    "sequence; it is commissioning."
                ),
                standard=(
                    "The IR7000 stands connected to facility power and facility "
                    "water, its payload racked and its cold plates plumbed — but "
                    "the loop is dry and nothing runs. The IR7000 is Dell's Open "
                    "Compute ORv3-based rack (a 21-inch open standard that trades "
                    "the classic 19-inch frame for more payload width, a shared "
                    "DC busbar, and native liquid-cooling provisions). What "
                    "follows is not a boot sequence; it is the commissioning of "
                    "a small hydraulic plant."
                ),
                technical=(
                    "Connected to facility power and water, payload racked, cold "
                    "plates plumbed, loop dry. ORv3-based 21-inch frame: wider "
                    "payload, shared DC busbar, native liquid provisions. What "
                    "follows is commissioning, not bring-up — nothing in this twin "
                    "boots."
                ),
                expert=(
                    "ORv3 rack, plumbed and connected, loop dry. Commissioning "
                    "sequence, not a boot sequence."
                ),
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
            description=L(
                novice=(
                    "The loop is filled from the cooling unit with treated coolant "
                    "— usually a glycol mix with corrosion inhibitors rather than "
                    "plain water — and the dissolved air is drawn out. Bubbles are "
                    "the quiet enemy of liquid cooling: air trapped in a cooling "
                    "plate makes an insulating pocket exactly where the heat needs "
                    "to escape, and air in a pump makes it cavitate and wear out."
                ),
                plain=(
                    "The technician fills the rack loop from the CDU with treated "
                    "coolant — typically a propylene-glycol mix such as PG25 with "
                    "corrosion inhibitors, not plain water — and pulls the "
                    "dissolved air out. Bubbles are the quiet enemy of liquid "
                    "cooling: air in a cold plate makes an insulating pocket "
                    "exactly where the heat is, and air in a pump cavitates it."
                ),
                standard=(
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
                technical=(
                    "Loop filled from the CDU with treated coolant — PG25-class "
                    "glycol with corrosion inhibitors, not water — then degassed. "
                    "Entrained air is the failure mode: an insulating pocket at the "
                    "cold plate is precisely where it must not be, and gas in the "
                    "pump cavitates."
                ),
                expert=(
                    "Fill with inhibited PG25, then degas. Entrained air insulates "
                    "at the cold plate and cavitates the pump."
                ),
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
            description=L(
                novice=(
                    "The cooling unit's pumps spin up and the vertical supply pipe "
                    "pressurizes, pushing coolant up the rack, through every "
                    "branch, and back down the return pipe. Flow settles at around "
                    "300 litres per minute with no heat to carry yet — the loop is "
                    "proving it can move liquid before it is asked to move heat. "
                    "Either pump can carry the whole load alone."
                ),
                plain=(
                    "The CDU's redundant pumps spin up and the vertical supply "
                    "manifold pressurizes, pushing coolant up the rack, through "
                    "every branch, and back down the return manifold. Flow settles "
                    "near 300 litres per minute with no heat to carry yet — the "
                    "loop runs open, proving it can move coolant before it is asked "
                    "to move heat. Each pump can carry the load alone."
                ),
                standard=(
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
                technical=(
                    "Redundant CDU pumps up; supply manifold pressurizes, coolant "
                    "circulates every branch and returns. ~300 L/min with zero "
                    "thermal load — flow is established and proven before heat is "
                    "admitted, which the engine asserts. N+1 pump redundancy."
                ),
                expert=(
                    "Pumps up, manifolds pressurized, ~300 L/min at zero load. "
                    "Flow-before-heat asserted. N+1 pumps."
                ),
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
            description=L(
                novice=(
                    "The long, careful stage — deliberately the longest here. Leak "
                    "sensors along the pipes and trays under every connector are "
                    "armed, and flow and temperature sensors on each branch confirm "
                    "that every cooling plate in every bay is actually getting its "
                    "share. This matters more than it sounds: a blocked branch "
                    "would still pass a whole-rack flow check and quietly cook one "
                    "server."
                ),
                plain=(
                    "The long, careful stage, and deliberately the longest in this "
                    "trace. Rope-style leak sensors along the manifolds and drip "
                    "trays under every quick disconnect are armed; flow and "
                    "temperature sensors on each branch confirm that every cold "
                    "plate in every bay actually receives its share of coolant. A "
                    "blocked branch would pass a whole-rack flow check and still "
                    "cook one server."
                ),
                standard=(
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
                technical=(
                    "Max-dwell stage. Rope leak detection along the manifolds and "
                    "drip trays under every quick disconnect armed; per-branch flow "
                    "and temperature verified so each cold plate is confirmed to "
                    "receive its share. Whole-rack flow is insufficient — a blocked "
                    "branch passes aggregate and destroys one server."
                ),
                expert=(
                    "Max dwell: rope leak detection armed, per-branch "
                    "flow/temperature verified. Aggregate flow is insufficient — a "
                    "blocked branch passes it and cooks one bay."
                ),
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
            description=L(
                novice=(
                    "Not everything wears a cooling plate — memory modules, network "
                    "cards, power units, and drives still shed their heat into the "
                    "air. The rear door of the rack catches that remainder: it "
                    "holds a water coil and a wall of fans that capture the exhaust "
                    "air's heat and hand it to the same loop. With that door "
                    "running, the rack becomes neutral to the room — the aisle "
                    "behind it stays at room temperature."
                ),
                plain=(
                    "Not every component wears a cold plate — DIMMs, NICs, power "
                    "shelves, and drives still shed heat to air. The enclosed "
                    "rear-door heat exchanger is the catch for that remainder: a "
                    "water coil and fan wall in the rack's rear door that captures "
                    "the exhaust air's heat and hands it to the same liquid loop. "
                    "With the door online the rack becomes room-neutral — the aisle "
                    "behind it stays at room temperature."
                ),
                standard=(
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
                technical=(
                    "Air-cooled remainder — DIMMs, NICs, power shelves, drives — is "
                    "captured by the enclosed rear-door heat exchanger: water coil "
                    "plus fan wall handing exhaust heat to the same loop. Rack "
                    "becomes room-neutral, so the aisle carries no thermal load and "
                    "the room's air handling is not sized against this rack."
                ),
                expert=(
                    "eRDHx captures the air-cooled remainder into the same loop. "
                    "Rack goes room-neutral; aisle carries no load."
                ),
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
            description=L(
                novice=(
                    "Only now is the equipment allowed to power on, and with it the "
                    "twin's real subject arrives: heat. The first tranche of load "
                    "dissipates 60 kilowatts, and conservation of energy — not a "
                    "design goal but a law — dictates that all 60 must leave the "
                    "rack. Here 55 go through the cooling plates into the liquid "
                    "and 5 through the air into the rear door. Add the two figures "
                    "and you always get exactly the input."
                ),
                plain=(
                    "Only now is the payload allowed to power on, and with it the "
                    "twin's real subject arrives: heat. The first tranche "
                    "dissipates 60 kW, and energy conservation — not a design goal "
                    "but a law — dictates that all 60 kW must leave the rack: 55 kW "
                    "through the cold plates into the liquid loop and 5 kW through "
                    "air into the rear door. The two figures always sum exactly to "
                    "the input."
                ),
                standard=(
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
                technical=(
                    "Payload energized; heat appears. 60 kW dissipated, and "
                    "conservation dictates all of it leaves: 55 kW liquid via cold "
                    "plates, 5 kW air via the rear door. liquidWatts + airWatts == "
                    "itLoadWatts is asserted exactly, no tolerance — the twin's "
                    "reason for existing."
                ),
                expert=(
                    "60 kW load: 55 kW liquid, 5 kW air. liquid + air == load "
                    "asserted exactly, zero tolerance."
                ),
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
            description=L(
                novice=(
                    "The load climbs toward the design point and the loop chases "
                    "it: the cooling unit raises pump speed to hold the temperature "
                    "difference steady, and the door's fans track the exhaust. This "
                    "is the cooling twin's version of the tuning stages the "
                    "computing twins go through — a control system hunting briefly "
                    "before it settles. Through every adjustment the books still "
                    "balance exactly."
                ),
                plain=(
                    "The load steps up toward design point and the loop chases it: "
                    "the CDU raises pump speed to hold the supply-return "
                    "temperature difference steady, and the door's fans track the "
                    "exhaust. This is the thermal twin's version of the compute "
                    "twins' training stages — a control system hunting briefly "
                    "before it settles. Through every adjustment the books still "
                    "balance: 150 kW in, 137 kW out by liquid, 13 kW by air."
                ),
                standard=(
                    "The load steps up toward design point and the loop chases "
                    "it: the CDU raises pump speed to hold the supply-return "
                    "temperature difference steady, and the door's fans track "
                    "the exhaust. This is the thermal twin's version of the "
                    "compute twins' 'training' stages — a control system "
                    "hunting briefly before it settles. Through every "
                    "adjustment the books still balance: 150 kW in, 137 kW out "
                    "by liquid, 13 kW out by air, not a watt unaccounted for."
                ),
                technical=(
                    "Load steps toward design point; the CDU modulates pump speed "
                    "to hold delta-T and the door fans track exhaust. A control "
                    "loop settling, analogous to the compute twins' training "
                    "stages. The balance holds through every intermediate state: "
                    "150 kW in, 137 kW liquid, 13 kW air."
                ),
                expert=(
                    "Load ramps; CDU modulates on delta-T, door fans track exhaust. "
                    "Balance holds through transients: 150 kW in, 137 liquid / 13 "
                    "air."
                ),
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
            description=L(
                novice=(
                    "Steady state at 264 kilowatts — the rack's current limit, with "
                    "the roadmap pointing toward nearly double that. About "
                    "ninety-one percent of the heat leaves through the liquid and "
                    "the rest through the rear door, and at the building connection "
                    "all of it becomes warm water. A modern site treats that as a "
                    "product rather than a waste stream, feeding it into heat-reuse "
                    "loops or into dry coolers that use a fraction of the energy a "
                    "chiller would."
                ),
                plain=(
                    "Steady state at 264 kW — the IR7000's current per-rack "
                    "envelope, with Dell's roadmap pointing toward 480 kW. About "
                    "ninety-one percent of the heat leaves through the liquid loop "
                    "and the rest through the rear door, and at the facility "
                    "connection all of it becomes warm water — which a modern site "
                    "treats as a product rather than a waste stream, feeding "
                    "heat-reuse loops or dry coolers that cost a fraction of a "
                    "chiller."
                ),
                standard=(
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
                technical=(
                    "Steady at 264 kW, roadmap to 480 kW. ~91% liquid fraction, "
                    "remainder via the rear door; all of it presented at the "
                    "facility connection as warm water. Warm-water operation "
                    "permits economization or heat reuse rather than compressor "
                    "cooling, which is where the operating-cost argument actually "
                    "lives."
                ),
                expert=(
                    "Steady 264 kW (roadmap 480 kW), ~91% liquid. Facility-side "
                    "output is warm water — economization or heat reuse rather than "
                    "compressor cooling."
                ),
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
