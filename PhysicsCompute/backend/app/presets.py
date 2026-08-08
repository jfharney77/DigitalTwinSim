"""Presets and the teaching layer for the AI-compute simulator — config
presets, workload presets, guided scenarios (spec 01's key scenarios),
and Explain-mode entries, with reading levels on the prose.
"""

from __future__ import annotations

from .leveling import L
from .models import (
    ConfigPreset,
    Environment,
    Explain,
    GuidedScenario,
    Scenario,
    SimEvent,
    SystemConfig,
    Workload,
    WorkloadPreset,
)

# --- Config presets --------------------------------------------------------

XE7745_8GPU = SystemConfig(
    product="xe7745", cpu_tdp_w=350, pcie_gpus=8, pcie_gpu_tdp_w=600,
    psu_capacity_w=2800,
)

XE7745_4GPU = SystemConfig(
    product="xe7745", cpu_tdp_w=350, pcie_gpus=4, pcie_gpu_tdp_w=450,
    psu_capacity_w=2400,
)

XE9680_H100 = SystemConfig(product="xe9680", cpu_tdp_w=350, sxm_gpu_tdp_w=700, nics=8)
XE9680_B200 = SystemConfig(product="xe9680", cpu_tdp_w=350, sxm_gpu_tdp_w=1000, nics=8)

XE9712_FULL = SystemConfig(
    product="xe9712", trays=18, shelf_capacity_kw=132,
    manifold_capacity_lpm=200, coolant_supply_c=25, coolant_flow_lpm=120,
)

CONFIG_PRESETS = [
    ConfigPreset(id="xe7745-8", name="XE7745 · 8× 600 W", config=XE7745_8GPU,
                 blurb="Max PCIe density — the positional-inequality machine."),
    ConfigPreset(id="xe7745-4", name="XE7745 · 4× 450 W", config=XE7745_4GPU,
                 blurb="The moderate build — margin everywhere."),
    ConfigPreset(id="xe9680-h100", name="XE9680 · H100", config=XE9680_H100,
                 blurb="8× 700 W SXM — the flagship air-cooled trainer."),
    ConfigPreset(id="xe9680-b200", name="XE9680 · B200", config=XE9680_B200,
                 blurb="8× 1000 W SXM — air cooling near its ceiling."),
    ConfigPreset(id="xe9712", name="XE9712 rack (72 GPUs)", config=XE9712_FULL,
                 blurb="The liquid-cooled rack — heat leaves in water."),
]

# --- Workload presets ------------------------------------------------------

IDLE = Workload()
TRAINING = Workload(gpu_pct=100, cpu_pct=50, data_feed_pct=100)
STARVED = Workload(gpu_pct=100, cpu_pct=50, data_feed_pct=30)
INFERENCE = Workload(gpu_pct=60, cpu_pct=30, data_feed_pct=100)

WORKLOAD_PRESETS = [
    WorkloadPreset(id="idle", name="Idle", workload=IDLE),
    WorkloadPreset(id="training", name="Training (fed)", workload=TRAINING),
    WorkloadPreset(id="starved", name="Training (starved)", workload=STARVED),
    WorkloadPreset(id="inference", name="Inference", workload=INFERENCE),
]

# --- Guided scenarios ------------------------------------------------------

GUIDED_SCENARIOS = [
    GuidedScenario(
        id="positional",
        title="8 GPUs at 30 °C inlet",
        narration=[
            L(
                novice=(
                    "Eight identical graphics cards share one river of "
                    "air in a warm room. The air picks up heat as it "
                    "flows, so each card breathes slightly hotter air "
                    "than the one before it — and under full load, the "
                    "card in the worst seat crosses its limit first and "
                    "slows down while its siblings keep running. Watch "
                    "the gap between the hottest and coolest card grow. "
                    "Nothing is wrong with that card; it just lives "
                    "downstream. Inside every air-cooled machine there "
                    "is a worst seat."
                ),
                standard=(
                    "The full XE7745 (8× 600 W) at 30 °C inlet, full "
                    "training load. Per-slot inlet preheat accumulates "
                    "down the riser row, so the hottest-GPU and "
                    "coolest-GPU readouts diverge, and the throttle "
                    "count rises one position at a time — the worst "
                    "airflow seat first. Meanwhile the fan wall climbs "
                    "toward its cubic ceiling: check the cooling-"
                    "overhead instrument when the fans peak. Positional "
                    "thermal inequality is the whole scenario."
                ),
                expert=(
                    "8× 600 W @ 30 °C: per-slot preheat → staggered "
                    "throttle, hot/cool spread is the readout. Fan wall "
                    "→ rpm³ overhead in the hundreds of watts."
                ),
            ),
        ],
        question="Which slot throttles first, and how many watts is the fan wall drawing when it does?",
        scenario=Scenario(
            config=XE7745_8GPU, workload=TRAINING,
            environment=Environment(inlet_c=30),
            duration_s=900,
        ),
    ),
    GuidedScenario(
        id="power-plant",
        title="Why AI servers are power-plant problems",
        narration=[
            L(
                novice=(
                    "The machine idles for two minutes, then training "
                    "starts. Watch the power number: it leaps from "
                    "about one kilowatt to more than ten, in seconds. "
                    "One rack of these swings by the demand of a small "
                    "neighborhood every time a job starts or stops. "
                    "This is why building an AI data center is mostly "
                    "an electricity project — the computers are the "
                    "easy part."
                ),
                standard=(
                    "The B200-class XE9680 idles at roughly a kilowatt "
                    "— idle GPUs still hold ~10% of TDP — and training "
                    "lands at t=120 s, stepping the box to ~10.5 kW DC. "
                    "The swing, not the peak, is the story: grid-facing "
                    "infrastructure must absorb megawatt-scale steps "
                    "when a cluster of these starts a job. Note the NIC "
                    "bank's steady ~240 W — plumbing that never idles."
                ),
                expert=(
                    "~1 kW idle → ~10.5 kW at t=120. The step function "
                    "is the grid problem; NICs are a constant 240 W "
                    "floor term."
                ),
            ),
        ],
        question="How many kilowatts did the step add, and over how many seconds?",
        scenario=Scenario(
            config=XE9680_B200, workload=IDLE, environment=Environment(),
            duration_s=600,
            events=[SimEvent(at_s=120, action="set-workload", workload=TRAINING)],
        ),
    ),
    GuidedScenario(
        id="starved",
        title="Starved GPUs",
        narration=[
            L(
                novice=(
                    "Training runs healthily for five minutes; then the "
                    "storage system starts delivering data at only a "
                    "third of the rate the GPUs can consume. Watch two "
                    "numbers separate: power barely falls — a waiting "
                    "GPU still burns most of its electricity — but the "
                    "useful-output number collapses, and a counter "
                    "starts adding up wasted GPU-hours. This is the "
                    "most expensive way to save money on storage."
                ),
                standard=(
                    "At t=300 s the data-feed slider drops to 30%: "
                    "effective utilization is capped by delivery, so "
                    "tokens/s falls to less than a third while DC power "
                    "drops only modestly (the idle floor plus hold "
                    "power). The GPU-hours-wasted ledger accumulates "
                    "the difference between demanded and delivered "
                    "utilization — the number a capacity planner should "
                    "be shown before trimming the storage budget. The "
                    "storage suite (PhysicsStorage) is the other end of "
                    "this slider."
                ),
                expert=(
                    "feed 100→30 at t=300: tok/s ∝ feed, P falls ~20%. "
                    "Wasted-GPU-hours ledger = ∫(demand − delivered). "
                    "Storage's bill, paid in compute."
                ),
            ),
        ],
        question="After starvation, what fraction of the power buys what fraction of the tokens?",
        scenario=Scenario(
            config=XE9680_H100, workload=TRAINING, environment=Environment(),
            duration_s=900,
            events=[SimEvent(at_s=300, action="set-data-feed", value=30)],
        ),
    ),
    GuidedScenario(
        id="air-vs-liquid",
        title="Air vs liquid",
        narration=[
            L(
                novice=(
                    "This is the whole rack — seventy-two GPUs, the "
                    "same count as nine of the air-cooled boxes — at "
                    "full training load. Notice what is missing: fan "
                    "noise. Nearly all the heat leaves in water, the "
                    "pumps that move it draw far less than nine fan "
                    "walls would, and the temperature rise of the "
                    "water obeys simple arithmetic the instruments "
                    "show live. Air cooling was never wrong; it just "
                    "stops scaling around a kilowatt per chip. This "
                    "rack is what comes after."
                ),
                standard=(
                    "The XE9712 at full load: ~120 kW DC, ~88% leaving "
                    "in the liquid loop, ΔT = Q/(ṁ·cp) on display. "
                    "Compare cooling overhead with the XE9680 run: nine "
                    "fan walls at full bore versus one pump pair — the "
                    "spec calls this the best cross-product lesson in "
                    "the suite, and the overhead instrument is where it "
                    "lands. The residual ~12% still heats the room; the "
                    "IR7000's rear-door option exists for exactly that "
                    "remainder."
                ),
                expert=(
                    "72 GPUs ≈ 9× XE9680. ~120 kW, 88% liquid, ΔT = "
                    "Q/ṁcp live. Pump ~1.5 kW vs 9 fan walls — the "
                    "overhead instrument is the lesson."
                ),
            ),
        ],
        question="Compare cooling overhead here with the XE9680 preset at full load — which is smaller, and by how much?",
        scenario=Scenario(
            config=XE9712_FULL, workload=TRAINING, environment=Environment(),
            duration_s=900,
        ),
    ),
    GuidedScenario(
        id="populate",
        title="Populate the rack",
        narration=[
            L(
                novice=(
                    "This rack has room for eighteen compute drawers, "
                    "but its power shelves were sized for a smaller "
                    "build. The validation panel is the exercise: try "
                    "raising the tray count and watch the rules trip — "
                    "first power, then coolant capacity, with a weight "
                    "advisory along the way. At rack scale, the budgets "
                    "run out before the space does. Empty slots in a "
                    "real AI data center are usually a power decision, "
                    "not a shortage of hardware."
                ),
                standard=(
                    "Eighteen trays against a 66 kW shelf: the shelf "
                    "rule errors at once (≈ 124 kW of demand), and the "
                    "run demonstrates the consequence — sustained "
                    "overcurrent trips the shelves mid-run. Fix it in "
                    "the build panel: fewer trays, or the 132/198 kW "
                    "shelf options. Then watch the manifold rule as "
                    "tray count rises. The IR7000 section of the spec "
                    "says it plainly: at rack scale the validation "
                    "rules are the product."
                ),
                expert=(
                    "18 trays vs 66 kW shelf: rule errors, then the "
                    "trip proves it. Power binds, then coolant, then "
                    "weight — space never does."
                ),
            ),
        ],
        question="How many trays does the 66 kW shelf actually support, per the rules?",
        scenario=Scenario(
            config=XE9712_FULL.model_copy(update={"shelf_capacity_kw": 66}),
            workload=TRAINING, environment=Environment(),
            duration_s=300,
        ),
    ),
    GuidedScenario(
        id="warm-water",
        title="Warm water day",
        narration=[
            L(
                novice=(
                    "Halfway through this run, the building's cooling "
                    "plant has a bad afternoon and the water arriving "
                    "at the rack warms from 25 to 42 degrees. The rack "
                    "keeps working — warm-water cooling is a real and "
                    "efficient design — but watch the margin: the "
                    "return water creeps toward the temperature where "
                    "the drawers must slow down to protect themselves. "
                    "Every degree the facility saves on chillers is a "
                    "degree of headroom the rack gives up."
                ),
                standard=(
                    "A CDU supply excursion at t=300 s: 25 → 42 °C. "
                    "ΔT is unchanged (same heat, same flow), so the "
                    "whole loop translates upward and the return "
                    "approaches the 65 °C throttle line — return-side "
                    "trays first. Warm-water economization trades "
                    "chiller energy for exactly this margin; the "
                    "validation panel's warm-water warning is this "
                    "scenario in rule form."
                ),
                expert=(
                    "Supply +17 K, ΔT const → return +17 K toward the "
                    "65 °C line. Economization = margin sold for "
                    "chiller savings."
                ),
            ),
        ],
        question="How close does the return get to the throttle line after the excursion?",
        scenario=Scenario(
            config=XE9712_FULL, workload=TRAINING, environment=Environment(),
            duration_s=900,
            events=[SimEvent(at_s=300, action="set-coolant-supply", value=42)],
        ),
    ),
    GuidedScenario(
        id="pump-down",
        title="One pump down",
        narration=[
            L(
                novice=(
                    "At five minutes, the rack loses three-quarters of "
                    "its coolant flow — a pump failure. The same heat "
                    "now rides a quarter of the water, so the water "
                    "comes back far hotter, and the drawers nearest the "
                    "end of the loop "
                    "feel it first. The rack protects itself by "
                    "slowing down rather than dying. In a liquid "
                    "world, the pump is the new fan wall: the quiet "
                    "component everything depends on."
                ),
                standard=(
                    "Pump degradation at t=300 s cuts flow to a "
                    "quarter: ΔT quadruples by arithmetic (same Q, "
                    "quarter ṁ), the "
                    "return crosses the 65 °C throttle line, and the "
                    "loop-level protection steps every tray down "
                    "together until heat and flow rebalance. Compare "
                    "with the XE7745's fan failure: same physics role, "
                    "different fluid — and note the trip line at 75 °C "
                    "this run should stay under once throttled."
                ),
                expert=(
                    "Flow ×0.25 at t=300 → ΔT ×4 → return > 65 → "
                    "loop-wide clamp, rebalance under the 75 °C trip. "
                    "The pump is the fan wall now."
                ),
            ),
        ],
        question="After the loop settles, what fraction of full performance survived the pump?",
        scenario=Scenario(
            config=XE9712_FULL, workload=TRAINING, environment=Environment(),
            duration_s=1200,
            events=[SimEvent(at_s=300, action="degrade-pump", value=0.75)],
        ),
    ),
]

# --- Explain-mode entries --------------------------------------------------

EXPLAINS = [
    Explain(
        id="liquid-balance",
        title="The liquid heat balance",
        equation="ΔT = Q_liquid / (ṁ × cp_water);  Q_liquid + Q_air = P_dc exactly",
        inputs=["DC power", "liquid share", "flow", "ΔT", "return temp"],
        explanation=L(
            novice=(
                "Water carries the rack's heat away, and the "
                "bookkeeping is exact: the temperature rise of the "
                "water equals the heat put in, divided by how much "
                "water flows and how much heat water can hold. Less "
                "flow or more heat means hotter water back — there is "
                "nowhere else for the energy to go, and the simulator "
                "enforces that to the watt."
            ),
            standard=(
                "The rack's split is asserted every tick: liquid plus "
                "air equals DC power exactly, with ~88% in the loop. "
                "The loop obeys ΔT = Q/(ṁ·cp) with water's 4186 "
                "J/(kg·K) — four thousand times air's volumetric "
                "capacity is why one pipe pair replaces nine fan "
                "walls. Every failure scenario in this app is a "
                "manipulation of one variable in this equation."
            ),
            expert=(
                "liquid + air = DC, exact; ΔT = Q/ṁcp, cp = 4186. "
                "Pump loss halves ṁ → doubles ΔT; supply excursion "
                "translates the loop. One equation, every scenario."
            ),
        ),
    ),
    Explain(
        id="starvation",
        title="Data starvation",
        equation="util_eff = util_demand × min(1, feed);  tokens ∝ util_eff, power ⊅",
        inputs=["data feed", "effective util", "tokens/s", "DC power", "wasted GPU-hours"],
        explanation=L(
            novice=(
                "A graphics chip waiting for data is like an idling "
                "truck: barely moving, still burning fuel. When the "
                "storage system cannot keep up, output falls in "
                "proportion — but power hardly falls at all, because "
                "staying ready is itself expensive. The wasted-hours "
                "counter turns that gap into a number you can put in "
                "a budget meeting."
            ),
            standard=(
                "The feed slider caps effective utilization; tokens/s "
                "scales with it linearly while power keeps its idle-"
                "plus-hold floor (~10% of TDP plus the demand curve's "
                "flat bottom). The wasted-GPU-hours ledger integrates "
                "demanded-minus-delivered utilization across all GPUs "
                "— the cross-link the storage and data-platform apps "
                "pick up from the other side."
            ),
            expert=(
                "tok ∝ eff-util; P has idle floor → starved GPUs are "
                "max-cost/min-output. ∫(demand − delivered)·N dt = the "
                "storage architect's bill."
            ),
        ),
    ),
    Explain(
        id="positional",
        title="Positional preheat",
        equation="T_inlet(slot i) = T_room + i × preheat;  worst slot throttles first",
        inputs=["slot position", "inlet preheat", "GPU temp spread", "throttle order"],
        explanation=L(
            novice=(
                "Air warms as it crosses the machine, so every card "
                "breathes the exhaust of the parts before it. The "
                "cards are identical; their seats are not. The one in "
                "the hottest seat slows down first, every time — a "
                "fact worth knowing before blaming the card."
            ),
            standard=(
                "Each XE7745 riser slot adds ~1 °C of inlet preheat "
                "over the one before it; at 600 W per card the spread "
                "between best and worst seats is enough to stagger "
                "the throttle order deterministically. The XE9680 "
                "deliberately erases this: one baseboard, one zone, "
                "shared fate — a simplification the spec footnotes."
            ),
            expert=(
                "Σ preheat down the row → deterministic throttle "
                "order. 9680 collapses the vector to one zone (stated "
                "simplification); 9712's analog is loop position."
            ),
        ),
    ),
    Explain(
        id="cooling-overhead",
        title="Cooling overhead",
        equation="overhead = (P_fans + P_pumps) / P_IT",
        inputs=["fan power", "pump power", "IT power", "overhead %"],
        explanation=L(
            novice=(
                "Some of the electricity a machine draws does no "
                "computing at all — it just moves the coolant, air or "
                "water. This instrument shows that share. Sixteen "
                "fans at full speed cost hundreds of watts; the "
                "rack's pumps cost about as much while moving "
                "seventy-two GPUs' heat. That ratio is most of the "
                "argument for liquid."
            ),
            standard=(
                "Fan and pump watts over IT watts — a chassis-scale "
                "PUE. The XE7745's wall at full bore runs ~5% "
                "overhead; the XE9712's pumps run ~1% for 9× the "
                "GPUs. The same ratio at facility scale is the PUE "
                "number the IR7000 twin argues about."
            ),
            expert=(
                "(fans + pumps)/IT: ~5% air at full bore vs ~1% "
                "liquid at 9× density. Chassis-scale PUE."
            ),
        ),
    ),
    Explain(
        id="redfish",
        title="From sim to twin (Redfish)",
        equation="GET /redfish/v1/Chassis/…/Thermal → this SimState, reshaped",
        inputs=["SimState", "Redfish JSON", "a real iDRAC", "a digital twin"],
        explanation=L(
            novice=(
                "Every Dell server carries a small always-on manager "
                "(the iDRAC) that answers questions like 'how hot is "
                "the processor?' over a standard web protocol called "
                "Redfish. The iDRAC tab shows this simulator "
                "answering in exactly that format. That is the whole "
                "trick of a digital twin: keep the questions, swap "
                "the answerer from a model to a machine."
            ),
            standard=(
                "The iDRAC tab reshapes the live SimState into the "
                "Redfish Thermal resource an iDRAC serves, with an "
                "Oem.Dell.Simulated flag telling the truth about the "
                "source. Point the same poller at real hardware and "
                "the simulator becomes the twin's offline half — the "
                "loop the whole physics suite was motivated by."
            ),
            expert=(
                "SimState → Thermal.v1 JSON, Oem.Simulated = true. "
                "Same schema against hardware = the twin. QED."
            ),
        ),
    ),
]
