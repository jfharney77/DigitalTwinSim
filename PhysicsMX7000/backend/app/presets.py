"""Presets and the teaching layer — backend data.

Config presets, workload presets, guided scenarios (scripted walkthroughs
that set the scenario and narrate what to watch), and Explain-mode entries
(the equation behind each key readout, with live-value substitution in the
frontend). Explain and scenario prose carries reading levels — the natural
authoring surface in a twin whose trace states are numbers.
"""

from __future__ import annotations

from .leveling import L
from .models import (
    ChassisConfig,
    ConfigPreset,
    Environment,
    Explain,
    GuidedScenario,
    Scenario,
    SimEvent,
    SledConfig,
    SledLoad,
    Workload,
    WorkloadPreset,
)

# --- Config presets ---------------------------------------------------------

def _compute(tdp: int = 205, dimms: int = 16, drives: int = 2) -> SledConfig:
    return SledConfig(kind="compute", cpu_tdp_w=tdp, dimms=dimms, drives=drives)


def _storage(owner: int) -> SledConfig:
    return SledConfig(kind="storage", owner_slot=owner)


EIGHT_COMPUTE = ChassisConfig(
    sleds=[_compute() for _ in range(8)],
    psu_count=6, redundancy="grid",
)

MIXED = ChassisConfig(
    sleds=[*[_compute() for _ in range(6)], _storage(1), _storage(2)],
    psu_count=6, redundancy="grid",
)

HOT_HALF = ChassisConfig(
    sleds=[
        _compute(350, 32, 4), _compute(350, 32, 4),
        _compute(350, 32, 4), _compute(350, 32, 4),
        SledConfig(kind="empty"), SledConfig(kind="empty"),
        SledConfig(kind="empty"), SledConfig(kind="empty"),
    ],
    psu_count=6, redundancy="grid",
)

NPLUS1 = ChassisConfig(
    sleds=[_compute() for _ in range(8)],
    psu_count=4, redundancy="n+1",
)

CONFIG_PRESETS = [
    ConfigPreset(id="eight-compute", name="Eight compute", config=EIGHT_COMPUTE,
                 blurb="8× dual-205 W sleds, 6 PSUs on grid redundancy — the full house."),
    ConfigPreset(id="mixed", name="Compute + storage", config=MIXED,
                 blurb="6 compute sleds plus 2 storage sleds owned by sleds 1 and 2 — the composability build."),
    ConfigPreset(id="hot-half", name="Hot half", config=HOT_HALF,
                 blurb="4× dual-350 W sleds and 4 empty bays — density without a full chassis."),
    ConfigPreset(id="nplus1", name="N+1 pool", config=NPLUS1,
                 blurb="8 compute sleds on 4 PSUs, N+1 — covered against a PSU dying, not a feed dying."),
]

# --- Workload presets --------------------------------------------------------

def _all(load: SledLoad) -> Workload:
    return Workload(loads=[load.model_copy() for _ in range(8)])


IDLE = _all(SledLoad())
STEADY = _all(SledLoad(cpu_pct=50, mem_pct=40, storage_pct=30))
FULL = _all(SledLoad(cpu_pct=100, mem_pct=80, storage_pct=60))
ONE_HOT = Workload(loads=[
    SledLoad(cpu_pct=100, mem_pct=80, storage_pct=60),
    *[SledLoad() for _ in range(7)],
])

WORKLOAD_PRESETS = [
    WorkloadPreset(id="idle", name="All idle", workload=IDLE),
    WorkloadPreset(id="steady", name="All steady", workload=STEADY),
    WorkloadPreset(id="one-hot", name="One hot neighbor", workload=ONE_HOT),
    WorkloadPreset(id="full", name="All out", workload=FULL),
]

# --- Guided scenarios ----------------------------------------------------------

GUIDED_SCENARIOS = [
    GuidedScenario(
        id="noisy-neighbor",
        title="The noisy neighbor, thermally",
        narration=[
            L(
                novice=(
                    "Eight sleds sit idle, and two minutes in, one of them "
                    "goes to full power while the other seven do nothing. "
                    "Watch the fan speed and the fan wattage: they climb "
                    "for the whole chassis, because the fans belong to the "
                    "box, not to any sled, and they spin to keep the "
                    "hottest one happy. The seven idle sleds did not "
                    "change at all — check their power readouts — yet the "
                    "chassis's cooling bill went up around them. That is "
                    "what sharing infrastructure means: one busy neighbor, "
                    "everyone's fans."
                ),
                standard=(
                    "From all-idle, sled 1 goes to 100% at t=120 s while "
                    "sleds 2–8 stay idle. The shared controller targets "
                    "the hottest sled, so the whole nine-fan wall ramps — "
                    "and fan power (cubic in rpm) is billed to the "
                    "chassis. Compare the per-sled power list before and "
                    "after: seven entries unchanged, one climbing, and a "
                    "fan-power line that rose for everyone. The pain is "
                    "real and it is allocated to nobody — the classic "
                    "shared-infrastructure tax."
                ),
                expert=(
                    "Sled 1 → 100% at t=120, rest idle. Controller on "
                    "max(T): rpm and rpm³ watts are chassis-scoped. Seven "
                    "sled powers flat, fan line up. The commons, taxed."
                ),
            ),
        ],
        question="How many watts did the fan wall add, and which sled's power readout explains it?",
        scenario=Scenario(
            config=EIGHT_COMPUTE, workload=IDLE, environment=Environment(),
            duration_s=600,
            events=[SimEvent(
                at_s=120, action="set-sled-load", index=0,
                load=SledLoad(cpu_pct=100, mem_pct=80, storage_pct=60),
            )],
        ),
    ),
    GuidedScenario(
        id="grid-feed-loss",
        title="Pooled redundancy: grid survives a feed",
        narration=[
            L(
                novice=(
                    "This chassis has six power supplies split across two "
                    "separate wall feeds — three on feed A, three on feed "
                    "B. Five minutes in, feed A dies entirely, taking its "
                    "three supplies with it. The chassis keeps running: "
                    "the three survivors on feed B carry the whole load, "
                    "working harder but within their limit. That is what "
                    "'grid redundancy' buys — protection against losing a "
                    "whole electrical feed, not just one supply."
                ),
                standard=(
                    "Six PSUs on grid redundancy, alternated across feeds "
                    "A and B. At t=300 s feed A is lost — three PSUs go "
                    "dark at once. The surviving trio's load fraction "
                    "jumps (watch the PSU load and efficiency readouts "
                    "move along the curve), and the chassis rides through. "
                    "Now re-run the N+1 scenario next to this one: same "
                    "chassis, same event, opposite outcome. Redundancy is "
                    "a policy about *which* failure you are covered for."
                ),
                expert=(
                    "Grid 3+3; feed A lost at t=300. Pool halves, load "
                    "point doubles, η shifts, chassis rides. N+1 under the "
                    "same event: dark. Policy = covered failure class."
                ),
            ),
        ],
        question="After the feed loss, what fraction of the surviving pool's capacity is the chassis using?",
        scenario=Scenario(
            config=EIGHT_COMPUTE, workload=STEADY, environment=Environment(),
            duration_s=600,
            events=[SimEvent(at_s=300, action="lose-feed", index=0)],
        ),
    ),
    GuidedScenario(
        id="nplus1-feed-loss",
        title="Pooled redundancy: N+1 doesn't",
        narration=[
            L(
                novice=(
                    "Same chassis, same feed failure — but this time the "
                    "power policy is 'N+1', which keeps one spare supply "
                    "in case a supply breaks. The catch: all the supplies "
                    "share one wall feed. When that feed dies at five "
                    "minutes, every supply dies with it, spare included, "
                    "and the chassis goes dark instantly. N+1 answered a "
                    "different question than the one this failure asked."
                ),
                standard=(
                    "The same feed-loss event against the N+1 preset: "
                    "four PSUs, one spare, all on feed A. At t=300 s the "
                    "feed goes and the pool goes with it — the spare "
                    "covered a PSU failure, and this was not a PSU "
                    "failure. The log line says it plainly; the grid "
                    "scenario beside this one is the control group. "
                    "Redundancy math is set arithmetic: what matters is "
                    "which failure modes leave a non-empty pool."
                ),
                expert=(
                    "N+1, single feed. Feed loss ⇒ pool → ∅ ⇒ dark. The "
                    "spare covered {PSU fails}, not {feed fails}. Compare "
                    "the grid run: same event, disjoint outcome."
                ),
            ),
        ],
        question="What would this chassis have needed — more PSUs, or the same PSUs arranged differently?",
        scenario=Scenario(
            config=NPLUS1, workload=STEADY, environment=Environment(),
            duration_s=600,
            events=[SimEvent(at_s=300, action="lose-feed", index=0)],
        ),
    ),
    GuidedScenario(
        id="composability",
        title="Reassign the storage sled",
        narration=[
            L(
                novice=(
                    "Bay 7 holds a storage sled — sixteen drives and no "
                    "computer. It does whatever the compute sled that "
                    "owns it asks. It starts owned by sled 1, which is "
                    "hammering its drives, so the storage sled runs hot "
                    "and busy. Five minutes in, ownership moves to sled 2, "
                    "which is barely using storage — and the storage "
                    "sled's power drops at once, though nobody touched a "
                    "cable. Reassigning drives between servers as a "
                    "settings change is the 'composable' part of a "
                    "composable chassis."
                ),
                standard=(
                    "The mixed build: storage sled 7 is owned by compute "
                    "sled 1, whose storage dial sits at 90%; compute sled "
                    "2 idles. At t=300 s ownership is reassigned to sled "
                    "2 — a timed config event, the software equivalent of "
                    "moving sixteen drives between servers. Watch bay 7's "
                    "power fall to idle as its activity follows its new "
                    "owner. The drives didn't move; the mapping did. "
                    "That mapping being a first-class, runtime-changeable "
                    "object is what 'composable infrastructure' means."
                ),
                expert=(
                    "Storage sled slaved to owner's storage dial. Owner "
                    "1@90% → owner 2@idle at t=300: bay-7 watts fall on "
                    "the reassignment tick. Drives static, mapping moved. "
                    "Composability in one event."
                ),
            ),
        ],
        question="How many watts did bay 7 shed when its owner changed — and where did the workload actually go?",
        scenario=Scenario(
            config=MIXED,
            workload=Workload(loads=[
                SledLoad(cpu_pct=60, mem_pct=40, storage_pct=90),
                SledLoad(cpu_pct=10, mem_pct=10, storage_pct=5),
                *[SledLoad(cpu_pct=30, mem_pct=20, storage_pct=10) for _ in range(4)],
                SledLoad(), SledLoad(),
            ]),
            environment=Environment(),
            duration_s=600,
            events=[SimEvent(at_s=300, action="reassign-storage", index=6, value=2)],
        ),
    ),
    GuidedScenario(
        id="power-cap",
        title="The chassis power budget",
        narration=[
            L(
                novice=(
                    "The chassis can be given a power budget — a ceiling "
                    "it must not cross, perhaps because the rack's "
                    "electrical circuit is smaller than the hardware's "
                    "appetite. Here eight sleds all run flat out into a "
                    "budget that cannot hold them, and the management "
                    "module responds by slowing *every* compute sled "
                    "together until the total fits. Watch the 'capped' "
                    "flag and the power line flatten below the ceiling: "
                    "shared budget, shared haircut."
                ),
                standard=(
                    "Eight sleds at 100% against a 4000 W chassis cap. "
                    "The budget is enforced chassis-wide: a global clamp "
                    "walks every compute sled down together until DC fits "
                    "under the ceiling, then holds. This is the modular "
                    "version of a rack power cap — the fair-share haircut "
                    "a shared budget implies, and the reason capacity "
                    "planners care about worst-case draw rather than "
                    "typical."
                ),
                expert=(
                    "8×full vs 4000 W cap: global clamp steps until "
                    "DC ≤ cap, capped flag latched. Shared budget ⇒ "
                    "shared haircut; plan on worst-case, not typical."
                ),
            ),
        ],
        question="Where does the power line settle relative to the 4000 W budget, and what did each sled give up?",
        scenario=Scenario(
            config=EIGHT_COMPUTE.model_copy(update={"power_cap_w": 4000}),
            workload=FULL, environment=Environment(),
            duration_s=600,
        ),
    ),
]

# --- Explain-mode entries -------------------------------------------------------

EXPLAINS = [
    Explain(
        id="sled-power",
        title="Compute sled power",
        equation="P_sled = 2 × (P_idle + (TDP − P_idle) × util^1.4) + DIMMs + drives + base",
        inputs=["sled util", "sled power", "sled heat", "hottest sled", "fan rpm"],
        explanation=L(
            novice=(
                "Each compute sled holds two processors, and a processor "
                "never drops to zero watts — idle costs about fifteen "
                "percent of its maximum. From there power rises with "
                "load, and faster than a straight line: the last stretch "
                "to 100% costs the most. Memory sticks, drives, and the "
                "sled's own circuit board add their share on top."
            ),
            standard=(
                "Per-sled power interpolates each socket from an idle "
                "floor (~15% of TDP) to full TDP along util^1.4 — "
                "superlinear because higher utilization brings higher "
                "clocks and voltages. DIMMs, local drives, and a fixed "
                "sled base ride on top. Eight of these curves, summed, "
                "are what the shared pool has to carry."
            ),
            expert=(
                "2 × (idle + (TDP−idle)·util^1.4) + DIMM + drives + base, "
                "× throttle clamps. Eight curves, one pool."
            ),
        ),
    ),
    Explain(
        id="fan-tax",
        title="The shared fan tax",
        equation="rpm ← rpm + k × (max(T_sled) − target);  P_fan = N × P_max × (rpm%)³",
        inputs=["hottest sled", "fan rpm", "fan power", "total power"],
        explanation=L(
            novice=(
                "The nine fans belong to the chassis, and they spin fast "
                "enough to keep the single hottest sled at a safe "
                "temperature — they cannot cool one bay more than "
                "another. Fan electricity grows with the cube of speed, "
                "so one hard-working sled can multiply the whole box's "
                "cooling bill while its neighbors do nothing. That bill "
                "lands on the chassis, not on the sled that caused it."
            ),
            standard=(
                "The controller is proportional on the *maximum* sled "
                "temperature — the defining line of shared cooling. One "
                "sled at 100% sets the error term, the wall ramps, and "
                "cubic fan power is billed chassis-wide. The noisy-"
                "neighbor scenario is this equation run twice: same "
                "seven idle sleds, very different fan line."
            ),
            expert=(
                "P-control on max(T)−target; P ∝ rpm³, chassis-scoped. "
                "One argmax sets everyone's bill. The commons, in two "
                "terms."
            ),
        ),
    ),
    Explain(
        id="wall-power",
        title="Wall (AC) power",
        equation="P_wall = P_dc / η(load ÷ pool capacity)",
        inputs=["total DC power", "alive PSUs", "PSU load point", "efficiency", "wall power"],
        explanation=L(
            novice=(
                "The power supplies convert wall electricity and lose a "
                "few percent doing it — least efficient when barely "
                "loaded, best near half load. Because they work as one "
                "pool, losing supplies moves the survivors to a "
                "different point on that curve: the wall wattage changes "
                "even when the computers' work does not."
            ),
            standard=(
                "Wall power is DC over efficiency at the pool's load "
                "fraction — DC divided by (alive PSUs × 3000 W), read "
                "off a Titanium-class curve. Feed losses and PSU kills "
                "change the denominator, so the same DC lands on a "
                "different efficiency point. The gap between the DC and "
                "AC readouts is the conversion loss, live."
            ),
            expert=(
                "AC = DC/η(DC ÷ N_alive·3 kW). Events move N_alive; the "
                "η point and the AC line move with it. Loss = AC − DC."
            ),
        ),
    ),
    Explain(
        id="redundancy",
        title="Pooled redundancy math",
        equation="survives(failure) ⇔ capacity(pool − failure) ≥ P_dc",
        inputs=["redundancy policy", "alive PSUs", "feed A", "feed B", "total power"],
        explanation=L(
            novice=(
                "Redundancy is a promise about which failures the box "
                "can shrug off. 'N+1' keeps one spare supply — enough "
                "if a supply breaks, useless if the wall feed powering "
                "all of them dies. 'Grid' splits the supplies across two "
                "independent feeds, so even a whole feed going dark "
                "leaves half of them running. Same supplies, different "
                "arrangement, different promise."
            ),
            standard=(
                "Every policy is the same inequality with a different "
                "failure subtracted. N+1: capacity(N−1 PSUs) ≥ DC — "
                "covered against one PSU. Grid: capacity(smaller feed's "
                "PSUs) ≥ DC — covered against a whole AC feed, because "
                "the pool alternates feeds. The two feed-loss scenarios "
                "run the same event against each policy; only the "
                "subtraction differs, and so does the outcome."
            ),
            expert=(
                "survives(F) ⇔ cap(pool∖F) ≥ DC. N+1: F = one PSU. "
                "Grid: F = a feed = half the pool. Same event, different "
                "F coverage, opposite outcomes."
            ),
        ),
    ),
    Explain(
        id="heat-balance",
        title="Chassis heat balance",
        equation="T_exhaust = T_inlet + P_dc / (ṁ × cp)",
        inputs=["total power", "airflow", "inlet temp", "exhaust temp"],
        explanation=L(
            novice=(
                "Every watt the chassis draws becomes heat the airflow "
                "must carry out the back. The exhaust temperature is the "
                "inlet plus a knowable rise: total power divided by how "
                "much air passes and how much heat air can hold. More "
                "watts or less airflow means hotter exhaust — a rule "
                "with no exceptions."
            ),
            standard=(
                "The whole-box identity: exhaust = inlet + DC/(ṁ·cp), "
                "with ṁ from the fan wall's CFM. It is the IR7000 twin's "
                "rack-scale heat balance applied to one 7U enclosure, "
                "and the tests assert it at steady state — the chassis "
                "cannot cheat thermodynamics, whatever the sleds do."
            ),
            expert=(
                "ΔT = DC/ṁcp, asserted. Same identity as IR7000, one "
                "enclosure down the hierarchy."
            ),
        ),
    ),
]
