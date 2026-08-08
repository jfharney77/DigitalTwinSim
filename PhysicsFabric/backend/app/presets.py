"""Presets and the teaching layer for the fabric simulator."""

from __future__ import annotations

from .leveling import L
from .models import (
    ConfigPreset,
    Explain,
    FabricConfig,
    GuidedScenario,
    Scenario,
    SimEvent,
    Workload,
    WorkloadPreset,
)

# --- Config presets --------------------------------------------------------

CAMPUS = FabricConfig(
    product="e3200", spines=1, leaves=4, endpoints_per_leaf=48,
    downlink_gbps=1, uplink_gbps=10,
    poe_aps=16, poe_cameras=10, poe_phones=31, poe_budget_w=740,
)

SN6000_STATIC = FabricConfig(
    product="sn6000", spines=4, leaves=8, endpoints_per_leaf=16,
    downlink_gbps=400, uplink_gbps=800,
    adaptive_routing=False, lossless_roce=True, cpo_optics=False,
)

SN6000_ADAPTIVE = SN6000_STATIC.model_copy(update={"adaptive_routing": True})

X800_FABRIC = FabricConfig(
    product="x800", spines=4, leaves=8, endpoints_per_leaf=16,
    downlink_gbps=400, uplink_gbps=800, sharp=True,
)

CONFIG_PRESETS = [
    ConfigPreset(id="campus", name="E3200 campus floor", config=CAMPUS,
                 blurb="4 access switches, 57 PoE devices — the human-scale fabric."),
    ConfigPreset(id="sn6000-static", name="SN6000 · static ECMP", config=SN6000_STATIC,
                 blurb="RoCE lossless, hashing left alone — collisions included."),
    ConfigPreset(id="sn6000-adaptive", name="SN6000 · adaptive", config=SN6000_ADAPTIVE,
                 blurb="Spectrum-X adaptive routing on — the before/after."),
    ConfigPreset(id="x800", name="Quantum-X800 + SHARP", config=X800_FABRIC,
                 blurb="Credit-lossless InfiniBand with in-network collectives."),
]

# --- Workload presets ------------------------------------------------------

STEADY = Workload(demand_gbps=8000, pattern="uniform", collective_pct=0)
ALLREDUCE = Workload(demand_gbps=16000, pattern="alltoall", collective_pct=70)
INCAST = Workload(demand_gbps=12000, pattern="incast", collective_pct=0)
ELEPHANTS = Workload(demand_gbps=10000, pattern="elephant", collective_pct=0)
CAMPUS_DAY = Workload(demand_gbps=24, pattern="uniform", collective_pct=0)

WORKLOAD_PRESETS = [
    WorkloadPreset(id="steady", name="Steady uniform", workload=STEADY),
    WorkloadPreset(id="allreduce", name="Training all-reduce", workload=ALLREDUCE),
    WorkloadPreset(id="incast", name="Storage incast", workload=INCAST),
    WorkloadPreset(id="elephants", name="Elephant flows", workload=ELEPHANTS),
    WorkloadPreset(id="campus-day", name="Campus 9 a.m.", workload=CAMPUS_DAY),
]

# --- Guided scenarios ------------------------------------------------------

GUIDED_SCENARIOS = [
    GuidedScenario(
        id="wire-a-floor",
        title="Wire a floor",
        narration=[
            L(
                novice=(
                    "Four wiring-closet switches power a floor's Wi-Fi "
                    "points, cameras, and desk phones through their "
                    "network cables. The validation panel already "
                    "warned you: the electrical budget is nearly "
                    "spent while most ports are still free. At three "
                    "minutes a power supply dies, the budget halves, "
                    "and the switch sheds devices in priority order — "
                    "phones first, cameras next, Wi-Fi last. Choosing "
                    "that order is a real configuration decision that "
                    "someone in every building has quietly made for "
                    "you."
                ),
                standard=(
                    "The campus preset: 57 PoE devices ≈ 90% of the "
                    "740 W budget (the rule that binds before port "
                    "count — spec 03's E3200 headline). At t=180 s a "
                    "PSU fails: budget halves, and the shed order "
                    "(phones → cameras → APs) executes. Watch "
                    "devices-powered against devices-total; then "
                    "reread the validation panel, which predicted the "
                    "whole run."
                ),
                expert=(
                    "ΣPoE ≈ 0.9× budget; PSU loss → ×0.5 → priority "
                    "shed. The budget, not the ports, is the "
                    "constraint. Validation predicted it."
                ),
            ),
        ],
        question="How many devices survived the PSU loss, and which class went first?",
        scenario=Scenario(
            config=CAMPUS, workload=CAMPUS_DAY, duration_s=600,
            events=[SimEvent(at_s=180, action="kill-psu")],
        ),
    ),
    GuidedScenario(
        id="uplink-down",
        title="One uplink down at 9 a.m.",
        narration=[
            L(
                novice=(
                    "Morning traffic is flowing when one of an access "
                    "switch's two uplink wires fails. For about two "
                    "seconds the floor goes dark while the switches "
                    "agree on the new path — then everything returns, "
                    "but the surviving wire now carries both wires' "
                    "load. Watch the utilization double and the "
                    "latency curve bend. Nothing is broken anymore; "
                    "there is simply half the road."
                ),
                standard=(
                    "A LAG member fails at t=180 s: a ~2 s STP-class "
                    "outage (delivered drops to zero — the log admits "
                    "it), then the survivor at doubled utilization. "
                    "At the 9 a.m. demand level that lands the link "
                    "near the queue-onset knee: same 1/(1−ρ) curve as "
                    "the 800G fabrics, at 10G scale. The campus is "
                    "the rehearsal room."
                ),
                expert=(
                    "LAG −1 at t=180: 2 s dark, then ρ ×2 → knee. "
                    "Identical curve, smaller wire."
                ),
            ),
        ],
        question="How long was the outage, and where did the survivor's utilization settle?",
        scenario=Scenario(
            config=CAMPUS,
            workload=CAMPUS_DAY.model_copy(update={"demand_gbps": 60}),
            duration_s=600,
            events=[SimEvent(at_s=180, action="kill-uplink")],
        ),
    ),
    GuidedScenario(
        id="hash-collision",
        title="Hash collision",
        narration=[
            L(
                novice=(
                    "Traffic spreads across four parallel spine paths "
                    "by hashing — like assigning cars to lanes by "
                    "license plate. Usually fair; today, a handful of "
                    "enormous flows hash onto the same lane. Watch "
                    "the worst-link strip burn while the average "
                    "stays modest — the average is a liar. At five "
                    "minutes, adaptive routing switches on and "
                    "watches the actual lanes instead of the plates: "
                    "the hot strip cools, and delivered bandwidth "
                    "rises without one new cable."
                ),
                standard=(
                    "Elephant flows on static ECMP: the worst link "
                    "runs +85% over fair share while the mean sits "
                    "low — the worst-link strip vs the spine tier, "
                    "side by side. At t=300 s adaptive routing "
                    "engages (Spectrum-X's pitch made tangible): "
                    "residual skew ~15% of static, the hot strip "
                    "cools, FCT and delivered improve with zero "
                    "hardware change. Toggle it off again live and "
                    "watch the skew return."
                ),
                expert=(
                    "Elephants: worst = fair × 1.85 static → ×1.13 "
                    "adaptive. Mean is a liar; the strip is the "
                    "truth. Software, not cables."
                ),
            ),
        ],
        question="What did the worst link read before and after adaptive routing engaged?",
        scenario=Scenario(
            config=SN6000_STATIC,
            workload=ELEPHANTS.model_copy(update={"demand_gbps": 18000}),
            duration_s=600,
            events=[SimEvent(at_s=300, action="toggle-adaptive")],
        ),
    ),
    GuidedScenario(
        id="lossless-vs-drop",
        title="Lossless under incast",
        narration=[
            L(
                novice=(
                    "Many machines answer one asker at once — the "
                    "storage world's classic pile-up — and the "
                    "receiving link is offered more than it can "
                    "carry. On ordinary Ethernet the excess would "
                    "simply be discarded and re-sent. This fabric "
                    "instead sends 'pause' messages upstream: nothing "
                    "is lost, but the congestion spreads backward "
                    "like brake lights on a highway. Zero drops, "
                    "wider slowdown — that is the trade, and you are "
                    "watching both halves of it."
                ),
                standard=(
                    "Incast at 4× concentration on the hot leaf, RoCE "
                    "lossless on: the drop counter holds zero while "
                    "the pause counter climbs and the latency "
                    "multiplier spreads (head-of-line, ×1.5 modeled). "
                    "Rerun with lossless off — drops appear, pauses "
                    "vanish, and the affected radius shrinks. "
                    "Losslessness is not free; it relocates the "
                    "damage. PhysicsStorage's fan-out reads are where "
                    "this pattern comes from."
                ),
                expert=(
                    "Incast ×4: PFC → drops 0, pauses > 0, HoL "
                    "spread ×1.5 on latency. Drop mode inverts it. "
                    "Losslessness relocates, never removes."
                ),
            ),
        ],
        question="With PFC on, what do the drop and pause counters read — and what happened to latency's radius?",
        scenario=Scenario(
            config=SN6000_ADAPTIVE,
            workload=INCAST.model_copy(update={"demand_gbps": 40000}),
            duration_s=600,
        ),
    ),
    GuidedScenario(
        id="ib-vs-ethernet",
        title="Ethernet vs InfiniBand, same topology",
        narration=[
            L(
                novice=(
                    "This is the InfiniBand personality under the "
                    "same training traffic you can run on the "
                    "Ethernet preset — same switches, same cables, "
                    "different constitution. Here a sender may not "
                    "transmit until the receiver has granted it "
                    "room, so the drop counter cannot move: watch "
                    "the stall gauge instead, which counts the "
                    "microseconds senders spend waiting. Run the "
                    "SN6000 preset with the same load afterward and "
                    "compare which costs you more where. This A/B is "
                    "the suite's networking exam."
                ),
                standard=(
                    "The X800 under the all-reduce profile: drops "
                    "structurally zero (credit-based flow control — "
                    "the violation is unexpressible at the link "
                    "layer), congestion visible only as stall-µs/s. "
                    "Against the SN6000 on identical traffic: "
                    "reactive losslessness (PFC pauses in time) vs "
                    "constructive (credits before transmission) — the "
                    "DellQuantumX800 twin's architectural contrast, "
                    "priced live. The spec calls this the suite's "
                    "best A/B lesson; run both and disagree with your "
                    "own priors."
                ),
                expert=(
                    "Credits: drops unexpressible, stalls the cost. "
                    "vs PFC: reactive-in-time vs constructive. Same "
                    "topology, different constitution — run the A/B."
                ),
            ),
        ],
        question="Where does the congestion cost surface on each fabric — and which one can even express a drop?",
        scenario=Scenario(
            config=X800_FABRIC.model_copy(update={"sharp": False}),
            workload=ALLREDUCE.model_copy(update={"demand_gbps": 40000}),
            duration_s=600,
        ),
    ),
    GuidedScenario(
        id="sharp",
        title="Collectives in the network",
        narration=[
            L(
                novice=(
                    "Training thousands of GPUs means constantly "
                    "adding everyone's results together. Normally "
                    "every number crosses the fabric several times. "
                    "At five minutes the switches themselves start "
                    "doing the addition as data passes through: the "
                    "wires suddenly carry half as much, while the "
                    "effective speed of the addition nearly doubles. "
                    "Two gauges cross in opposite directions — less "
                    "traffic, more math. The network became a "
                    "calculator."
                ),
                standard=(
                    "All-reduce at 70% of traffic; SHARP engages at "
                    "t=300 s (toggle in the preset): bytes crossing "
                    "links fall by half of the collective share while "
                    "effective all-reduce rate rises ×1.8 — fabric "
                    "throughput down, work rate up, the counters "
                    "crossing exactly as the DellQuantumX800 twin "
                    "pins in its trace. In-network computing is the "
                    "rare feature whose success shows as *less* "
                    "traffic."
                ),
                expert=(
                    "SHARP: link bytes ×(1−0.5·coll), allreduce "
                    "×1.8. Counters cross; success = less traffic. "
                    "The twin's invariant, continuous."
                ),
            ),
        ],
        question="Which counter fell and which rose when SHARP engaged — and by how much each?",
        scenario=Scenario(
            config=X800_FABRIC.model_copy(update={"sharp": False}),
            workload=ALLREDUCE, duration_s=600,
            events=[SimEvent(at_s=300, action="toggle-sharp")],
        ),
    ),
    GuidedScenario(
        id="gray-failure",
        title="Gray failure",
        narration=[
            L(
                novice=(
                    "At three minutes, one link begins silently "
                    "losing one packet in a thousand. No alarm "
                    "sounds. Every status light stays green — look at "
                    "the status readout, it will not budge. But the "
                    "flows crossing that link slow to a crawl as "
                    "they endlessly re-send, and the flow-completion "
                    "gauge quietly triples. This is the failure mode "
                    "that ruins weeks: nothing is down, and "
                    "something is very wrong. Only trend-watching "
                    "telemetry catches it — which is the whole "
                    "argument for the observability app next door."
                ),
                standard=(
                    "The gray-failure toggle at t=180 s: 0.1% silent "
                    "loss on one link. status-all-green stays true "
                    "for the rest of the run — asserted in the tests, "
                    "adversarial-twin style — while goodput on "
                    "affected flows collapses ~35% (retransmit "
                    "arithmetic) and FCT multiplies. The device's "
                    "self-report and the user's experience have "
                    "parted company; PhysicsData's anomaly feed "
                    "exists to reunite them. Note even the event log "
                    "only admits what happened in parentheses."
                ),
                expert=(
                    "0.1% loss: green ∧ goodput −35% ∧ FCT ×3+ — "
                    "both asserted. Telemetry-or-nothing. The "
                    "observability app's opening argument."
                ),
            ),
        ],
        question="What does the status light say at t=400 — and what does the FCT gauge say?",
        scenario=Scenario(
            config=SN6000_ADAPTIVE, workload=STEADY, duration_s=600,
            events=[SimEvent(at_s=180, action="gray-failure")],
        ),
    ),
]

# --- Explain-mode entries --------------------------------------------------

EXPLAINS = [
    Explain(
        id="oversub",
        title="Oversubscription",
        equation="ratio = Σ downlink capacity ÷ Σ uplink capacity, per leaf",
        inputs=["downlinks", "uplinks", "ratio", "congestion location"],
        explanation=L(
            novice=(
                "Count the bandwidth entering a switch from below and "
                "the bandwidth leaving it upward. If three times as "
                "much can arrive as can leave, the ratio is 3:1, and "
                "when everyone talks at once the traffic jam forms "
                "exactly at that switch's uplinks — predictably, "
                "before any packet is sent. AI fabrics are built 1:1 "
                "because GPUs do all talk at once."
            ),
            standard=(
                "The first-class ratio (spec 03 lesson #1): "
                "endpoints × downlink over spines × uplink, shown "
                "before any traffic runs. Congestion appears exactly "
                "where the ratio predicts because it is arithmetic, "
                "not weather. Campus trees run 4:1–20:1 and mostly "
                "get away with it; training fabrics run 1:1 because "
                "all-to-all traffic offers no statistical mercy."
            ),
            expert=(
                "Σdown/Σup per leaf. Campus: statistical multiplexing "
                "forgives 10:1. All-to-all: forgives nothing → 1:1."
            ),
        ),
    ),
    Explain(
        id="queue-delay",
        title="The queue-delay curve",
        equation="latency = hops × base × 1/(1−ρ) past ~90% utilization",
        inputs=["worst link ρ", "queue multiplier", "latency", "FCT"],
        explanation=L(
            novice=(
                "A link at 80% full is fine; at 95% it is a parking "
                "lot. Waiting time explodes as a link approaches "
                "full, on the same curve the storage simulator uses "
                "for disks — one law for every queue in this repo. "
                "The last 10% of a link's capacity is bought with "
                "unbounded patience."
            ),
            standard=(
                "The same 1/(1−ρ) shape as PhysicsStorage's knee, "
                "applied per link past the ~90% onset (spec 03 "
                "points out the rhyme deliberately). The worst link "
                "— not the mean — sets tail latency and FCT, which "
                "is why the map gives it its own strip and why "
                "adaptive routing is worth a switch generation."
            ),
            expert=(
                "Same curve as storage, per-link; onset ~0.9. Tail "
                "= f(worst link). Mean is marketing."
            ),
        ),
    ),
    Explain(
        id="ecmp",
        title="ECMP & adaptive routing",
        equation="worst link = fair share × (1 + imbalance);  adaptive ⇒ imbalance × 0.15",
        inputs=["flows", "hash", "imbalance", "worst link", "delivered"],
        explanation=L(
            novice=(
                "Spreading traffic by hashing flow labels is fair "
                "only on average. A few giant flows can land on one "
                "path and jam it while parallel paths sit idle — bad "
                "luck, industrialized. Adaptive routing watches "
                "actual queues and moves flows away from the heat; "
                "in this model it removes about 85% of the unfairness."
            ),
            standard=(
                "Static ECMP's collision skew is modeled per "
                "pattern: +25% (uniform), +50% (all-to-all), +85% "
                "(elephants) over fair share on the worst link. "
                "Adaptive routing leaves 15% residual. The delivered-"
                "bandwidth delta between the two presets is "
                "Spectrum-X's sales pitch, reproduced as arithmetic."
            ),
            expert=(
                "Skew {.25,.5,.85} by pattern; AR ×0.15. The delta "
                "is the product."
            ),
        ),
    ),
    Explain(
        id="lossless",
        title="Three answers to congestion",
        equation="Ethernet: drop · RoCE: pause upstream · InfiniBand: stall the sender",
        inputs=["excess demand", "personality", "drops / pauses / stalls", "radius"],
        explanation=L(
            novice=(
                "When more arrives than a link can carry, something "
                "must give. Plain Ethernet throws the excess away "
                "and lets endpoints re-send. Lossless Ethernet "
                "shouts 'pause' upstream — nothing lost, but the "
                "jam spreads backward. InfiniBand never lets the "
                "excess leave the sender at all: permission comes "
                "before transmission. Three philosophies; this app "
                "prices all three."
            ),
            standard=(
                "Drop mode: excess → drops (counted in pps), "
                "delivered = capacity, radius small. PFC: drops "
                "structurally zero, pauses spread the slowdown "
                "(HoL ×1.5 on latency radius). Credit-based IB: the "
                "violation is unexpressible — excess waits at the "
                "source as stall-µs. Note what is conserved in all "
                "three: demand = delivered + (lost | waiting). Flow "
                "conservation is this app's power-balance identity."
            ),
            expert=(
                "drop | pause | stall — damage relocated, never "
                "destroyed. Conservation: D = delivered + lost + "
                "deferred, asserted."
            ),
        ),
    ),
    Explain(
        id="optics-power",
        title="The optics ledger",
        equation="P_optics = ports × (18 W pluggable | 6 W CPO);  compare P_asic",
        inputs=["ports", "optic type", "optics W", "ASIC W", "fabric W"],
        explanation=L(
            novice=(
                "Every port's fiber plug contains a tiny laser "
                "transceiver drawing real power. One is trivial; "
                "hundreds rival the switch's own processor. "
                "Co-packaged optics move the lasers inside the chip "
                "package, cutting that by two-thirds — at hundreds "
                "of thousands of ports, that is a building's worth "
                "of electricity."
            ),
            standard=(
                "~18 W per 800G pluggable × hundreds of ports ≈ the "
                "ASIC's own draw — the toggle makes the fabric-power "
                "instrument jump, which is the whole lesson. CPO "
                "(~6 W/port) is why the SN6000 generation offers it, "
                "and why the liquid-cooling option follows: the "
                "power you save still has to not-exist somewhere."
            ),
            expert=(
                "128×18 ≈ ASIC. CPO ×⅓. At cluster scale the "
                "optics line item is a substation."
            ),
        ),
    ),
]
