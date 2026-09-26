"""The couplings and the preset chains, as data the page renders.

Prose carries reading levels 1/3/5 through the shared ``L(...)`` mechanism;
resolution happens in the server, never here.
"""

from __future__ import annotations

from pydantic import Field

from twinkit.models import CamelModel

from .leveling import L
from .presets import CHAINS


class CouplingInfo(CamelModel):
    id: str
    title: str
    source: str
    target: str
    source_fields: list[str]
    target_inputs: list[str]
    units: str
    time_base: str
    identity: str
    tolerance: str
    test: str
    closed_with: str | None = None
    blurb: str


class EngineRef(CamelModel):
    component: str
    label: str
    frontend_port: int


class ChainInfo(CamelModel):
    id: str
    title: str
    couplings: list[str]
    closed: bool
    engines: list[EngineRef]
    blurb: str
    watch: str
    default_chain: dict = Field(default_factory=dict)


FRONTEND_PORTS = {
    "PhysicsCompute": 5205, "PhysicsCDU": 5216, "PhysicsStorage": 5206, "PhysicsFabric": 5207,
    "PhysicsAIFactory": 5219, "PhysicsRackPower": 5217, "PhysicsResilience": 5209,
    "PhysicsDataDomain": 5215, "PhysicsXR": 5213, "PhysicsFleet": 5208,
    "DellPowerEdgeR760Thermal": 5203,
}
ENGINE_LABELS = {
    "PhysicsCompute": "AI compute", "PhysicsCDU": "PowerCool CDU", "PhysicsStorage": "Storage",
    "PhysicsFabric": "Fabric", "PhysicsAIFactory": "AI factory", "PhysicsRackPower": "Rack power",
    "PhysicsResilience": "Resilience", "PhysicsDataDomain": "Data Domain", "PhysicsXR": "Rugged edge",
    "PhysicsFleet": "Fleet operations", "DellPowerEdgeR760Thermal": "R760 thermal",
}

COUPLINGS: list[CouplingInfo] = [
    CouplingInfo(
        id="c1", title="Rack heat becomes the CDU's load",
        source="PhysicsCompute", target="PhysicsCDU",
        source_fields=["liquid_watts"], target_inputs=["config.tray_groups", "set-util events"],
        units="W → kW", time_base="1 s → 1 s",
        identity="racks × liquid_watts / 1000 == it_load_kw on every uncapped tick; energy within 0.5% over the run",
        tolerance="0.5 × (1 − idle) × banks × 40 kW / 100 + 0.05 kW per tick",
        test="compose/tests/test_c1.py::test_heat_out_equals_heat_in_across_the_seam",
        closed_with="c2",
        blurb=L(
            standard=(
                "The XE9712 rack reports how many watts leave through its cold plates. The CDU "
                "simulator has no heat input: its load is a bank count and a utilization dial. "
                "The adapter inverts the CDU's own bank formula, so the heat the rack sheds is "
                "the heat the CDU carries. Utilization is a whole percent, which costs up to "
                "1.1 kW of rounding at six banks; the seam states that error and tests against it."
            ),
            novice=(
                "A rack of AI computers turns electricity into heat, and most of that heat leaves "
                "in water pipes. The cooling unit next to the rack has to carry it away. These "
                "two simulators were built separately: one knows how much heat the rack makes, "
                "the other knows how a cooling unit behaves. This link hands the first one's "
                "heat to the second, second by second, and then checks that no heat was lost or "
                "invented on the way. The cooling simulator only accepts whole-percent settings, "
                "so the hand-off is off by a small, known amount, and the check allows exactly "
                "that much."
            ),
            expert=(
                "liquid_watts → tray_groups = ⌈peak/40 kW⌉ and set-util = round(100·((q/(g·40)) − "
                "0.08)/0.92). Per-tick bound 0.5·0.92·g·40/100 + 0.05 kW; ∫ within 0.5%. Capped, "
                "tripped and sub-idle-floor ticks are excluded and counted. air_watts stays upstream."
            ),
        ),
    ),
    CouplingInfo(
        id="c2", title="The CDU's limits come back as throttling",
        source="PhysicsCDU", target="PhysicsCompute",
        source_fields=["sec_supply_c", "cap_pct", "sec_flow_lpm", "bank_status"],
        target_inputs=["set-coolant-supply", "set-workload (gpu_pct × cap)", "degrade-pump", "restrict-tray"],
        units="°C → °C; % → %; L/min → fraction", time_base="1 s → 1 s",
        identity="at the fixed point C1 holds, supply temperatures match within the 0.25 °C deadband, and coupled tokens never exceed the open-loop run",
        tolerance="0.25 °C + rounding + what the loop still moved on its last iteration",
        test="compose/tests/test_c2.py::test_closed_loop_converges_and_is_deterministic",
        closed_with="c1",
        blurb=L(
            standard=(
                "What the CDU does about the heat comes back to the rack: the coolant temperature "
                "it can actually supply, the power cap its controller asks for, lost pump flow, "
                "and any tray bank that tripped. With C1 this closes a loop, so the two engines "
                "are run in turn until the numbers stop moving. Each pass moves the carried cap "
                "half way to the new value, stops within the iteration cap, and uses no randomness, "
                "so the same inputs always settle the same way. The compute simulator has no "
                "power-cap input, so the cap is applied as reduced GPU demand."
            ),
            novice=(
                "Cooling pushes back. If the building's water runs warm, the cooling unit cannot "
                "keep the chips cool at full speed, so its controller tells the computers to slow "
                "down. Slower computers make less heat, which changes what the cooling unit "
                "needs to ask for. That is a loop, and a loop needs settling. This link runs the "
                "rack simulator, then the cooling simulator, then the rack again with the "
                "slowdown applied, and repeats until two passes in a row agree. It always takes "
                "the same steps in the same order, so you get the same answer every time. The "
                "price shows up as fewer tokens, the units of work an AI model produces."
            ),
            expert=(
                "Fixed point over whole runs; loop variable E = ∫liquid_watts dt. carried_k = "
                "0.5·carried·cap + 0.5·carried. Stops when both |ΔE|/E and the heat the CDU still "
                "refuses fall under 0.5%, or at fixed_point_max_iter. Cap applied as gpu_pct × cap (no power-cap "
                "event). Latched trips pin the later iteration's trip set. Transients under the "
                "CDU's 60 s loop lag are not resolved."
            ),
        ),
    ),
    CouplingInfo(
        id="c3", title="Storage delivery becomes the GPUs' data feed",
        source="PhysicsStorage", target="PhysicsCompute",
        source_fields=["gpu_idle_due_to_data_pct", "iops_delivered_k", "iops_demand_k"],
        target_inputs=["workload.data_feed_pct", "set-data-feed events"],
        units="ratio → %", time_base="1 h → 1 s, one 600 s window per distinct operating point",
        identity="100 − gpu_idle_due_to_data_pct == effective GPU utilization ÷ demanded, within 1 point",
        tolerance="1.0 point (integer data_feed_pct accounts for 0.5)",
        test="compose/tests/test_c3.py::test_the_two_idle_gauges_are_the_same_number",
        blurb=L(
            standard=(
                "The storage simulator has a gauge for GPUs idle because data was late. The "
                "compute simulator has a slider for how well fed the GPUs are. They are the same "
                "quantity read from opposite ends. Storage ticks in hours and compute in seconds, "
                "so the storage run is reduced to its distinct operating points and the compute "
                "run visits each for ten minutes. The seam checks that both engines report the "
                "same fed fraction, and that a starved GPU still draws most of its power."
            ),
            novice=(
                "A GPU can only work as fast as its data arrives. When storage falls behind, "
                "expensive processors sit waiting. One simulator measures that from the storage "
                "side, another from the processor side. This link feeds the storage result into "
                "the processor simulator and checks that both tell the same story. One simulator "
                "counts in hours and the other in seconds, so the link picks out each different "
                "situation the storage went through and gives the processors ten minutes in each."
            ),
            expert=(
                "feed = round(100 − gpu_idle_due_to_data_pct); operating points deduplicated in "
                "first-seen order, ≤ 12 windows. Identity on the last 20% of each window; "
                "Δgpu_hours_wasted within 2%. Exascale's pool view reads configured units, so a "
                "node loss does not move the gauge; demand and checkpoint bursts do."
            ),
        ),
    ),
    CouplingInfo(
        id="c4", title="A gray link becomes lost tokens",
        source="PhysicsFabric", target="PhysicsAIFactory",
        source_fields=["fct_ms", "status_all_green", "goodput_penalty_pct"],
        target_inputs=["job.tokens_per_gpu_s × tokens_scale, per fabric regime"],
        units="ms ratio → dimensionless", time_base="1 s → 1 h, traces spliced per regime",
        identity="factory tokens/s (gray ÷ healthy) == 1 / ((1 − 0.25) + 0.25 × fct_gray / fct_healthy), within 0.5%; status stays green on every gray tick",
        tolerance="0.5% of the scale",
        test="compose/tests/test_c4.py::test_gray_failure_is_green_in_the_fabric_and_red_in_the_tokens",
        blurb=L(
            standard=(
                "A gray failure is a link that loses a little traffic while every status light "
                "stays green. The fabric simulator shows it as a longer flow-completion time. A "
                "training step is part compute and part collective communication; only the "
                "collective part stretches. The adapter turns the stretch into a scale on the "
                "factory's tokens per GPU. The quarter of a step assumed to be communication is "
                "an estimate and is labeled as one. The seam asserts both halves: green in the "
                "fabric, slower in the tokens."
            ),
            novice=(
                "Sometimes a network cable goes slightly bad. Nothing reports a fault, every "
                "light stays green, and yet everything that crosses it arrives late. An AI "
                "training job spends part of every step waiting for its processors to swap "
                "results over the network, so a slow link slows the whole job. This link "
                "measures how much later traffic arrives and works out how many fewer tokens, "
                "the units of work, the factory produces. It then checks two things at once: "
                "the network still says it is healthy, and the factory is making less."
            ),
            expert=(
                "stretch = 0.75 + 0.25·fct/fct₀ (comm_fraction estimated); tokens_scale = 1/stretch. "
                "No degrade-fabric event in PhysicsAIFactory, so one factory run per regime, "
                "spliced with cumulative tokens and cost restamped. PhysicsFabric's fct proxy is "
                "product-independent under incast, so Ethernet and InfiniBand stretch alike here."
            ),
        ),
    ),
    CouplingInfo(
        id="c5", title="Server wall watts load the rack's phases",
        source="DellPowerEdgeR760Thermal", target="PhysicsRackPower",
        source_fields=["ac_power_w", "alive_psus"],
        target_inputs=["config.loads[i].power_w", "set-load events"],
        units="W → W", time_base="1 s → 1 s",
        identity="Σ ac_power_w == pdu_input_w within 10 W per load on every tick; energy within 0.2%",
        tolerance="10 W deadband × loads, plus output rounding",
        test="compose/tests/test_c5.py::test_wall_watts_are_conserved_across_the_seam",
        blurb=L(
            standard=(
                "Each server simulator reports what it draws at the wall. The rack power "
                "simulator takes loads per outlet. The adapter plugs up to eight servers into "
                "the rack's A, B and C phases and replays their draw as it changes. A failed fan "
                "upstream raises fan power, which raises wall power, which moves a phase meter "
                "downstream. A rack slot carries at most 2000 W: a larger server is split across "
                "its power supplies, and refused if one supply still exceeds the slot."
            ),
            novice=(
                "Every server plugs into a power strip in its rack, and the strip's circuit "
                "breakers only allow so much. One simulator knows how much power a server pulls "
                "as it works harder or loses a fan. Another knows how a rack's power strips and "
                "breakers behave. This link plugs the first into the second and checks that the "
                "watts going into the rack equal the watts the servers asked for. A server too "
                "big for one socket is shared across several, and one too big even for that is "
                "turned away instead of being quietly shrunk."
            ),
            expert=(
                "ac_power_w → RackLoad.power_w + set-load (10 W deadband, ≤ 240 events). Over "
                "2000 W: one slot per PSU feed at ac/alive_psus; refused, not clamped, above "
                "2000 W per feed. XE9712 excluded (busbar). Identity skips ticks with a tripped phase."
            ),
        ),
    ),
    CouplingInfo(
        id="c6", title="An attack, read from the backup appliance",
        source="PhysicsResilience", target="PhysicsDataDomain",
        source_fields=["corrupted_tb", "contained", "estate_tb", "change_gb_day"],
        target_inputs=["dataset.full_tb", "dataset.daily_change_pct", "ransomware-start", "ransomware-stop"],
        units="GB/h → %/day; h → day", time_base="1 h → 1 d, then back",
        identity="encrypted TB agrees on both sides within one day of spread; the restore-time law is unchanged",
        tolerance="one day of spread",
        test="compose/tests/test_c6.py::test_both_engines_agree_how_much_is_encrypted",
        blurb=L(
            standard=(
                "The resilience simulator scripts an abstract incident: a corruption rate and a "
                "start time. The Data Domain simulator sees the same event from the ingest side, "
                "as a share of the dataset turning to high-entropy data each day. Two passes. "
                "The first carries the incident into the appliance and checks both engines agree "
                "how much is encrypted. The second carries the appliance's entropy alarm back as "
                "detection timing, and checks that earlier detection shrinks the damage while the "
                "restore-time law stays the same. Only rates, sizes and times cross this seam."
            ),
            novice=(
                "When data is being quietly scrambled, the backup system is often the first "
                "place it shows: scrambled data looks random, and random data stands out. One "
                "simulator plays out the damage hour by hour. The other is the backup appliance, "
                "which takes one reading a day. This link tells the appliance how fast the damage "
                "spreads, checks that both simulators agree on how much is scrambled, and then "
                "hands the appliance's early warning back so the first simulator can respond "
                "sooner. It deals only in amounts and times. Nothing about how an attack is "
                "carried out appears on either side."
            ),
            expert=(
                "value = 100·(GB/h·24/1000)/estate_TB; at_day = ⌊t_h/24⌋, not before day 2. "
                "Return leg: alarm latency → the integer sensitivity whose detect_threshold_base_h "
                "/ sensitivity does not beat it. RTO = decide_h + TB·1000/(GB/s·3600) asserted "
                "unchanged. Scope boundary inherited and re-tested over the adapter source."
            ),
        ),
    ),
    CouplingInfo(
        id="c7", title="A hostile edge site becomes admin hours",
        source="PhysicsXR", target="PhysicsFleet",
        source_fields=["summary.shutdown", "summary.throttle_seconds"],
        target_inputs=["node-fault events", "config.sites"],
        units="s of one hostile day → faults per site-year → events in days", time_base="1 s → 1 d",
        identity="extra faults_cum == faults injected, exactly; extra admin hours == count × per-fault hours within 1%",
        tolerance="0 faults; 1% of the hours",
        test="compose/tests/test_c7.py::test_injected_faults_are_all_accounted_for",
        blurb=L(
            standard=(
                "One run of the rugged-edge simulator is a hostile day at one class of site: a "
                "heat wave on a fouled filter, a brownout at a cell site. A day that ends in a "
                "shutdown, or is mostly spent throttled, raises a service fault each time it "
                "comes round. The adapter multiplies by the number of such sites and schedules "
                "the faults into the fleet simulator evenly, by division instead of dice. The "
                "seam closes the ledger: every extra fault and every extra admin hour traces back "
                "to a site the first simulator ran."
            ),
            novice=(
                "A server on a hot rooftop with a clogged air filter has bad days. Multiply that "
                "by sixty rooftops and somebody has to deal with it. One simulator shows what a "
                "bad day does to one machine. Another counts the hours an operations team spends "
                "keeping hundreds of sites running. This link turns bad days into service calls, "
                "spreads them evenly over the months, and checks that every extra call and every "
                "extra hour in the second simulator can be traced to the first."
            ),
            expert=(
                "n = round(sites × days/365 × heatwave_days_per_year), estimated at 12; at_d = "
                "⌊(i + 0.5)·0.9·D/n⌋. Fault if shutdown or throttled ≥ 50% of the run. Per-fault "
                "hours from PhysicsFleet constants (+ truck_roll_h when manual at the edge). Use "
                "automated ops for the hours identity: a saturated manual backlog does not drain."
            ),
        ),
    ),
    CouplingInfo(
        id="c8", title="The AI factory, fed by real engines",
        source="PhysicsStorage + PhysicsFabric + PhysicsCompute ⇄ PhysicsCDU", target="PhysicsAIFactory",
        source_fields=["iops_capacity_k", "gpu_idle_due_to_data_pct", "fct_ms", "gpu_power_w", "pump_power_kw", "cap_pct"],
        target_inputs=["data.storage_gbps", "degrade-storage", "compute.gpu_peak_w", "warm-day", "job.tokens_per_gpu_s"],
        units="mixed", time_base="mixed → 1 h",
        identity="steady-state tokens/s within 5%, facility MW within 8%, idle within 2 points, PUE within 0.05 — or the gap names its cause",
        tolerance="per instrument, above",
        test="compose/tests/test_c8.py::test_fed_and_aggregate_agree_when_nothing_is_wrong",
        blurb=L(
            standard=(
                "The AI Factory simulator describes each subsystem with one number. Here those "
                "numbers come from the detailed engines instead: storage throughput from the "
                "Exascale model, watts per GPU from the XE9712 model, PUE from the CDU's pump "
                "power, tokens per GPU scaled by the fabric and by the closed cooling loop. The "
                "factory engine itself is unchanged. The seam compares the two modes at steady "
                "state. Where they differ by more than the tolerance, the chain must name the "
                "cause from a fixed list, or the test fails."
            ),
            novice=(
                "The factory simulator is a summary: one number for storage, one for cooling, one "
                "for the network. The other simulators are the detail behind each number. This "
                "link swaps the summary numbers for ones worked out by the detailed simulators "
                "and runs the same factory again. Then it compares the two runs. Mostly they "
                "agree. Where they do not, the link has to say why in plain terms, for example "
                "that the detailed rack model draws more watts per GPU than the summary assumed."
            ),
            expert=(
                "storage_gbps from iops_capacity_k; shortfalls as hourly degrade-storage; gpu_peak_w "
                "= steady gpu_power_w / GPUs; PUE = 1 + pump/IT + 0.12 (estimate), injected as a "
                "warm-day offset; tokens_per_gpu_s × C4 scale × C2 cap, spliced. Causes: stall_power, "
                "hourly_rounding, cap_vs_shed, checkpoint_burst, gpu_tier_vs_detailed, gray_fabric. "
                "The cap scales tokens only; fed-mode MW is not reduced under a cap."
            ),
        ),
    ),
]

_CHAIN_PROSE: dict[str, tuple[str, str]] = {
    "heat-to-cdu": (
        L(standard="Two XE9712 racks ramp from idle to full load on one CDU. Open seam: heat goes one way.",
          novice="Two racks of AI computers go from resting to flat out, and one cooling unit has to carry the heat away.",
          expert="C1 open; racks = 2 → six banks; idle→100% step at t = 60 s."),
        L(standard="Watch the two heat curves lie on top of each other, a rounding step apart.",
          novice="Watch the rack's heat line and the cooling unit's load line: they should sit on top of each other.",
          expert="Per-tick error stays under 1.15 kW; the air share never crosses."),
    ),
    "closed-loop": (
        L(standard="The same ramp, but the building's water turns 12 °C warmer at 200 s. The CDU caps the racks, the racks make less heat, and the loop is iterated until it settles.",
          novice="The same two racks, but partway through the building's cooling water turns warm. The cooling unit asks the computers to slow down, which changes the heat, which changes what it asks for. The loop repeats until it settles.",
          expert="C1 + C2 closed; facility supply 17 → 29 °C at t = 200 s; damping 0.5, tol 0.5%; settles in five passes."),
        L(standard="Step through the iterations: the cap the CDU still asks for shrinks toward zero as the racks absorb it.",
          novice="Use the iteration control to step through the passes and watch the two simulators come to agree.",
          expert="Residuals halve per pass; tokens integral drops about 10% against open loop."),
    ),
    "storage-feed": (
        L(standard="An Exascale rack serves an AI read workload for three days, with checkpoint bursts every six hours and a demand surge at hour 40.",
          novice="A storage system feeds a rack of AI processors for three days. Every six hours the processors save their work, and later the demand for data jumps.",
          expert="C3; 3000k → 5000k IOPS at h 40 against a 3480k ceiling; four operating points."),
        L(standard="Watch the storage-side and compute-side fed fractions track each other through every regime.",
          novice="Watch both 'how well fed' lines move together: one is measured at the storage, one at the processors.",
          expert="Worst gauge gap 0.4 points; stall power keeps DC at ×0.84 while tokens fall to ×0.53."),
    ),
    "gray-fabric": (
        L(standard="One link in the fabric turns gray for the middle third of a month-long training run, then clears.",
          novice="For the middle part of a month-long job, one network link goes slightly bad without anyone being told.",
          expert="C4; gray-failure at 200–400 s of 600 maps to the middle third of the training span."),
        L(standard="The fabric's status line stays at 1 while the factory's token ratio drops to the predicted scale.",
          novice="The 'all green' line never moves, and the factory's output drops anyway.",
          expert="fct ×2.63 → stretch 1.41 → scale 0.710; ratio matches to 1e-6."),
    ),
    "wall-watts": (
        L(standard="Three R760 servers on one rack PDU. Two ramp to full load; one loses a fan at 200 s.",
          novice="Three servers share one rack's power strips. Two get busy; one loses a cooling fan.",
          expert="C5; three R760Thermal runs → slots 0–2 on phases A/B/C; kill-fan index 2 at 200 s."),
        L(standard="Watch the summed wall watts and the PDU input track within the deadband, and phase B rise after the fan fails.",
          novice="Watch what happens to the second phase's current after the fan dies: the remaining fans work harder, and that costs power.",
          expert="Fan feedback visible as a phase-B current step; energy conserved to 0.2%."),
    ),
    "attack-to-appliance": (
        L(standard="A slow incident corrupts 100 GB an hour from day 10 of a 60-day run; nobody contains it until day 40.",
          novice="Data starts being quietly scrambled on day 10. With nobody watching, it runs for a month.",
          expert="C6; slow-incident 100 GB/h at h 240, contain at h 960, restore ordered at h 984."),
        L(standard="The appliance's entropy alarm fires within a day. Pass 2 uses it, and the corrupted curve flattens almost at once.",
          novice="The backup appliance notices within a day. The dashed line shows how little is lost when someone acts on that warning.",
          expert="Blast radius 72,000 GB → 3,800 GB; RTO law unchanged at 61.6 h."),
    ),
    "hostile-sites": (
        L(standard="Two hundred edge sites: sixty rooftops with filters six months overdue, twenty cell sites on a weak feed, and the rest in conditioned closets.",
          novice="Two hundred small remote sites. Some sit on hot rooftops with clogged filters, some have unreliable power, most are fine.",
          expert="C7; site mix 60/20/120; 180 days; automated NativeEdge ops."),
        L(standard="Every extra fault and admin hour in the fleet ledger traces back to a hostile site.",
          novice="The gap between the two fleet lines is what the bad sites cost, in hours of somebody's time.",
          expert="473 faults injected, 473 counted; 473 h at 1 h per fault."),
    ),
    "factory-fed": (
        L(standard="An eight-rack factory on a design day, run twice: once on its own aggregate numbers, once with inputs from the detailed engines.",
          novice="The same AI factory run twice: once using its own rough numbers, once using numbers worked out by the detailed simulators.",
          expert="C8 healthy: exascale sized from factory demand, healthy fabric, design-day closed loop."),
        L(standard="Tokens, idle time and PUE agree. Facility power does not, and the chain says why: 1400 W per GPU in the detailed model against a 1200 W tier.",
          novice="Three of the four headline numbers agree. The power number does not, and the page says why.",
          expert="facility_mw +18%, named gpu_tier_vs_detailed."),
    ),
    "factory-fed-bad-day": (
        L(standard="The same factory with a gray link and a warm-water afternoon in the last week of the run.",
          novice="The same factory on a bad week: a slightly faulty network link and warm cooling water.",
          expert="C8 with gray-failure from 60% of the fabric run and facility supply 29 °C over h 480–720."),
        L(standard="The aggregate model sees none of it. The fed run loses about forty percent of its tokens and names the fabric and the cooling cap as the causes.",
          novice="The rough model notices nothing. The detailed one shows a large loss and says which two things caused it.",
          expert="tokens −38%, named gray_fabric with the cap noted; MW still gpu_tier_vs_detailed."),
    ),
}


def _engines(chain_id: str) -> list[EngineRef]:
    chain = CHAINS[chain_id]
    seen: list[str] = []
    for link in chain.links:
        for component in (link.source, link.target):
            if component not in seen:
                seen.append(component)
    return [EngineRef(component=c, label=ENGINE_LABELS[c], frontend_port=FRONTEND_PORTS[c]) for c in seen]


def _chain_json(chain_id: str) -> dict:
    c = CHAINS[chain_id]
    return {
        "id": c.id, "title": c.title, "scenarios": c.scenarios, "closed": c.closed,
        "maxIter": c.max_iter, "damping": c.damping, "tol": c.tol,
        "links": [{"coupling": l.coupling, "source": l.source, "target": l.target, "params": l.params}
                  for l in c.links],
    }


CHAIN_INFOS: list[ChainInfo] = [
    ChainInfo(
        id=cid, title=CHAINS[cid].title,
        couplings=sorted({l.coupling for l in CHAINS[cid].links}),
        closed=CHAINS[cid].closed, engines=_engines(cid),
        blurb=_CHAIN_PROSE[cid][0], watch=_CHAIN_PROSE[cid][1],
        default_chain=_chain_json(cid),
    )
    for cid in CHAINS
]
