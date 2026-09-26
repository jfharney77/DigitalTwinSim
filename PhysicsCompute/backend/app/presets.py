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
    Intro,
    Scenario,
    SimEvent,
    SystemConfig,
    Workload,
    WorkloadPreset,
)

# --- Page intro --------------------------------------------------------------

INTRO = Intro(
    title="From one hot slot to a hundred-kilowatt rack",
    text=L(
        novice=(
            "Three AI machines, one simulator. Watch how much power they "
            "draw, how hot they get, and how the heat leaves: by air in "
            "the two servers (the XE7745 and the XE9680), by water in "
            "the XE9712 rack. Pick a guided scenario on the left to "
            "start; each one tells you what to watch. The iDRAC tab "
            "shows the same readings in the format a real Dell server "
            "reports them."
        ),
        standard=(
            "Three machines on one engine. In the XE7745, eight "
            "identical GPUs sit in unequal seats, and the one breathing "
            "the warmest air throttles first. In the XE9680, eight GPUs "
            "on one baseboard heat up and throttle together, and starve "
            "together when the data pipeline lags. In the XE9712 rack "
            "the heat leaves in water, and the arithmetic is enforced "
            "to the watt: liquid heat plus air heat equals DC power, "
            "and the water's temperature rise is ΔT = Q/(ṁ·cp). The "
            "iDRAC tab serves the simulator's state as the Redfish JSON "
            "a digital twin would read from real hardware."
        ),
        expert=(
            "One engine, three personalities: XE7745 per-slot preheat, "
            "XE9680 one-zone HGX with a data-feed cap, XE9712 liquid "
            "loop (liquid + air = DC exact; ΔT = Q/(ṁ·cp)). iDRAC tab: "
            "SimState as Redfish Thermal JSON."
        ),
    ),
)

# --- Config presets --------------------------------------------------------

XE7745_8GPU = SystemConfig(
    product="xe7745", cpu_tdp_w=350, pcie_gpus=8, pcie_gpu_tdp_w=600,
    psu_capacity_w=3200,
)

XE7745_4GPU = SystemConfig(
    product="xe7745", cpu_tdp_w=350, pcie_gpus=4, pcie_gpu_tdp_w=450,
    psu_capacity_w=2900,
)

XE9680_H100 = SystemConfig(product="xe9680", cpu_tdp_w=350, sxm_gpu_tdp_w=700, nics=8)
XE9680_B200 = SystemConfig(product="xe9680", cpu_tdp_w=350, sxm_gpu_tdp_w=1000, nics=8)

XE9712_FULL = SystemConfig(
    product="xe9712", trays=18, shelf_capacity_kw=132,
    manifold_capacity_lpm=200, coolant_supply_c=25, coolant_flow_lpm=120,
)

CONFIG_PRESETS = [
    ConfigPreset(id="xe7745-8", compare_preset_id="xe7745-4", name="XE7745 · 8× 600 W", config=XE7745_8GPU,
                 blurb="Max PCIe density — the positional-inequality machine."),
    ConfigPreset(id="xe7745-4", name="XE7745 · 4× 450 W", config=XE7745_4GPU,
                 blurb="The moderate build — margin everywhere."),
    ConfigPreset(id="xe9680-h100", name="XE9680 · H100", config=XE9680_H100,
                 blurb="8× 700 W SXM — the flagship air-cooled trainer."),
    ConfigPreset(id="xe9680-b200", compare_preset_id="xe9712", name="XE9680 · B200", config=XE9680_B200,
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
                    "about one and a half kilowatts to about eleven, "
                    "in seconds. "
                    "One rack of these swings by the demand of a small "
                    "neighborhood every time a job starts or stops. "
                    "This is why building an AI data center is mostly "
                    "an electricity project — the computers are the "
                    "easy part."
                ),
                standard=(
                    "The B200-class XE9680 idles near 1.5 kW "
                    "— idle GPUs still hold ~10% of TDP — and training "
                    "lands at t=120 s, stepping the box to ~9.7 kW DC "
                    "at once and ~11 kW once the fans reach full speed. "
                    "The swing, not the peak, is the story: grid-facing "
                    "infrastructure must absorb megawatt-scale steps "
                    "when a cluster of these starts a job. Note the NIC "
                    "bank's steady ~240 W — plumbing that never idles."
                ),
                expert=(
                    "~1.5 kW idle → ~11 kW from t=120. The step function "
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
                    "numbers separate. Power falls by less than a "
                    "third, because a waiting GPU still burns most of "
                    "its electricity. The training throughput number "
                    "falls by more than two thirds, and a counter "
                    "starts adding up wasted GPU-hours. The Data feed "
                    "slider on the right shows the live value next to "
                    "its starting one. This is the "
                    "most expensive way to save money on storage."
                ),
                standard=(
                    "At t=300 s a timed event drops the data feed to "
                    "30%; the slider keeps its starting value and shows "
                    "the live one beside it. Effective utilization is "
                    "capped by delivery, so tokens/s falls by 70% while "
                    "DC power drops about 28%, from 7.6 to 5.5 kW (the "
                    "idle floor plus hold power). The GPU-hours-wasted "
                    "ledger accumulates "
                    "the difference between demanded and delivered "
                    "utilization — the number a capacity planner should "
                    "be shown before trimming the storage budget. The "
                    "storage suite (PhysicsStorage) is the other end of "
                    "this slider."
                ),
                expert=(
                    "feed 100→30 at t=300: tok/s ∝ feed, P falls ~28%. "
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
                    "This is the whole rack at full training load: "
                    "seventy-two GPUs, the same count as nine of the "
                    "air-cooled XE9680 servers. Notice what has "
                    "shrunk: the fans. Each drawer keeps a few small "
                    "ones for leftover heat, but nearly all the heat "
                    "leaves in water. Watch cooling overhead. It is "
                    "the share of electricity spent on fans and pumps "
                    "rather than on computing. For this rack it is "
                    "about 1.4%. The A/B panel above the instruments "
                    "runs one XE9680 with 1,000 W GPUs alongside, and "
                    "its fans take about 15%. The water's temperature "
                    "rise obeys simple arithmetic, but give it time: "
                    "the return temperature needs several minutes to "
                    "settle at about 12 °C above the supply. Air "
                    "cooling was never wrong; it just stops scaling "
                    "around a kilowatt per chip. This rack is what "
                    "comes after."
                ),
                standard=(
                    "The XE9712 at full load: ~116 kW DC, ~88% leaving "
                    "in the liquid loop, ΔT = Q/(ṁ·cp) on display. The "
                    "return temperature lags (τ = 60 s), so the "
                    "measured rise reaches the settled 12 °C after "
                    "several minutes. This scenario opens the A/B "
                    "panel against the XE9680 · B200: its sixteen fans "
                    "pinned at full speed cost ~15% of IT power (the "
                    "700 W H100 build, fans near two-thirds speed, "
                    "costs ~5%), while the rack's pumps plus tray fans "
                    "cost ~1.4% for 72 GPUs. That is nine XE9680s' "
                    "worth of fan walls against one pump pair. The "
                    "residual ~12% still heats the room; the IR7000's "
                    "rear-door option exists for exactly that "
                    "remainder."
                ),
                expert=(
                    "72 GPUs ≈ 9× XE9680. ~116 kW, 88% liquid, ΔT = "
                    "Q/ṁcp (return lags, τ 60 s). Overhead ~1.4% "
                    "(pump 0.75 kW + tray fans 0.8 kW) vs ~15% for "
                    "the B200 box in the A/B read-out."
                ),
            ),
        ],
        question="Once both runs settle, read the cooling overhead row in the A/B panel: which machine spends the smaller share on cooling, and by what factor?",
        scenario=Scenario(
            config=XE9712_FULL, workload=TRAINING, environment=Environment(),
            duration_s=900,
        ),
        compare_preset_id="xe9680-b200",
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
                    "rule errors at once (≈ 122 kW of demand), and the "
                    "run demonstrates the consequence — sustained "
                    "overcurrent trips the shelves mid-run. Fix it in "
                    "the build panel: fewer trays, or the 132/198 kW "
                    "shelf options. Then watch the manifold rule as "
                    "tray count rises. At rack scale the validation "
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
        equation="util_eff = util_demand × min(1, feed);  tokens ∝ util_eff;  power falls far less",
        inputs=["data feed", "effective util", "tokens/s", "DC power", "wasted GPU-hours"],
        explanation=L(
            novice=(
                "A graphics chip waiting for data is like an idling "
                "truck: barely moving, still burning fuel. When the "
                "storage system cannot keep up, output falls in "
                "proportion, but power falls far less, because "
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
                "shared fate, which is a stated simplification."
            ),
            expert=(
                "Σ preheat down the row → deterministic throttle "
                "order. 9680 collapses the vector to one zone (stated "
                "simplification); 9712's analog is loop position."
            ),
        ),
    ),
    Explain(
        id="power-chain",
        title="DC power, wall power, GPU power",
        equation="P_dc = P_gpu + P_cpu + P_nic + P_base + P_fans + P_pumps;  P_wall = P_dc / η_psu",
        inputs=["GPU power", "the other parts", "DC power", "PSU efficiency", "wall power"],
        explanation=L(
            novice=(
                "Three power readings, and they are not the same "
                "number. GPU power is what the graphics chips alone "
                "draw — usually most of the total. DC power is what "
                "every part inside draws added up: chips, memory, "
                "network cards, fans and pumps. 'DC' means direct "
                "current, the steady kind of electricity the parts "
                "run on. Wall power is what the electricity meter "
                "sees, and it is always the larger number, because "
                "converting the building's alternating current into "
                "direct current wastes a few percent as heat. In the "
                "liquid rack the same job is done by a busbar — a "
                "thick metal bar running down the back of the rack "
                "that every tray clips onto instead of having its own "
                "cord. Starve the GPUs and watch these three fall far "
                "less than the tokens do."
            ),
            standard=(
                "The power chain, inside out: GPU watts are the "
                "largest single term; DC power is the sum the engine "
                "asserts every tick (components must add up exactly); "
                "wall power is DC divided by PSU efficiency — a "
                "load-dependent curve for the air servers, a single "
                "0.97 busbar-shelf point for the rack. The gap "
                "between DC and wall is conversion loss, and it is "
                "worst at low load, which is why an oversized PSU "
                "bank costs money at idle."
            ),
            expert=(
                "ΣP_components = P_dc, asserted per tick; P_ac = "
                "P_dc/η(load). η curve for PSUs, 0.97 flat for the "
                "busbar shelf. Conversion loss peaks at low load."
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
                "computing at all. It just moves the coolant, air or "
                "water. This instrument shows that share. The "
                "XE9680's sixteen fans at full speed draw about "
                "1.4 kW to cool eight GPUs. The rack's pumps and "
                "small drawer fans draw about 1.6 kW to cool "
                "seventy-two. That ratio is most of the argument "
                "for liquid. The wattages are estimates."
            ),
            standard=(
                "Fan and pump watts over IT watts — a chassis-scale "
                "PUE. At full bore the XE7745's wall runs ~9% and "
                "the B200-class XE9680's ~15%; the XE9712's pumps "
                "plus tray fans run ~1.4% for 9× the GPUs. Fan "
                "wattages are estimates. The same ratio at facility "
                "scale is the PUE number the IR7000 twin argues "
                "about."
            ),
            expert=(
                "(fans + pumps)/IT: ~9–15% air at full bore vs "
                "~1.4% liquid at 9× density. Chassis-scale PUE."
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
