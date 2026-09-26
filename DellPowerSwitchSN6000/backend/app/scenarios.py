"""Failure scenarios for the SN6000 fabric twin — pure traces beside the
happy path.

``engine.simulate()`` is the fabric working. This module holds what happens
when part of it stops working, under the same rules: no FastAPI, no IO, no
timers, no randomness, and the same ``FabricState`` model (extended only with
fields that default to "nothing is wrong"). ``tests/test_gray_link.py`` runs
the engine's purity check against this module too.

The one scenario so far is the **gray link**. The happy path proves the
fabric never discards a packet for want of buffer. A gray failure attacks
from the other side: one leaf-to-spine optic degrades, its bit errors outrun
forward error correction, and frames start arriving corrupt. The receiving
port discards them at the frame check and the sending NIC sends them again.
Nothing is lost for good, no buffer ever overflowed, so ``dropped_packets``
is still zero — and the link never goes down, so every status page is green
while the all-reduce takes nearly twice as long. The cure is not congestion
control. It is per-link error counters, and then taking a link that reports
"up" out of service on purpose.

How the behaviour here is grounded (sources ride on the scenario):

- NVIDIA's Spectrum-X telemetry write-up describes exactly this hunt on the
  Israel-1 system: NIC counters showed RoCE retransmissions, switch telemetry
  "pinpointed symbol errors on a specific port" of a spine, and "after
  disabling the faulty port, bandwidth usage fully recovered". That account
  goes straight to disabling the port. This trace splits the recovery in
  two — withdraw routing from the link first, shut the port second — which
  is ordinary operator practice (RFC 8326 is the BGP form of it), not
  something the NVIDIA write-up describes.
- NVIDIA's fabric-resiliency write-up is the reason a few corrupt frames
  matter: NCCL has no heavy error recovery, so small loss stalls the step.
- SprayCheck (Krebs, Amir, Landau Feibish, Silberstein) is the reason
  adaptive routing does not save you unaided: per-packet spraying puts every
  flow across the sick link, which spreads the damage instead of containing
  it. NVIDIA's Cumulus Linux documentation says adaptive routing chooses by
  queue occupancy and port utilization, and a corrupting link is not
  congested.

Three honest limits. Each drawn uplink is a bundle of eight 800 Gb/s links
(the healthy trace's own reading of the map), so the gray optic is one member
of leaf 2's bundle to spine 1. The damage is the same — per-packet spraying
puts every flow that crosses the bundle across the bad member — but the
recovery here drains the whole drawn uplink, where an operator would shut the
one erring port and lose an eighth of it. The capacity dip from the steer step
on is therefore a worst case, and the step-0 text says so.

A link that errs badly enough does take itself down: the
Ethernet physical layer declares a fault above a symbol-error threshold. The
gray window is the band between "FEC no longer repairs everything" and that
threshold, and this trace sits inside it. And turning adaptive routing off on
one port would not move traffic off it (the port would still be an
equal-cost next hop), which is why the steer step withdraws routing instead.

Rates, times and error counts are illustrative. The ordering is the content.
PhysicsFabric's gray-failure toggle is the same lesson with a dial on it.
"""

from __future__ import annotations

from .engine import _endpoints, _leaves, _spines, simulate
from .leveling import L
from .models import FabricState, Scenario, SourceLink

HEALTHY = "healthy"
GRAY_LINK = "gray-link"

# The link that goes gray: leaf 2's uplink to spine 1.
SICK_LEAF = "leaf-l2"
SICK_SPINE = "spine-s1"
SICK_LINK = f"{SICK_LEAF}:{SICK_SPINE}"
# Leaf 2's other uplink, which carries the work of two while routing is
# withdrawn from the sick one. It runs hot (92%) and ECN keeps it lossless.
SURVIVOR_LINK = f"{SICK_LEAF}:spine-s2"

# The happy path's sustained rate and its all-reduce time at that rate.
HEALTHY_STEADY_TBPS = 29
HEALTHY_COLLECTIVE_MS = 120

GRAY_LINK_PHASES = [
    "steady", "degrade", "blind", "telemetry",
    "steer", "drain", "replace", "restored",
]

# Phases in which the sick link is carrying job traffic and nobody knows.
BLIND_PHASES = {"blind"}

GRAY_LINK_SOURCES = [
    SourceLink(
        label=(
            "NVIDIA — Next-generation AI factory telemetry with Spectrum-X "
            "Ethernet (symbol errors on one spine port; disabling the port "
            "restored bandwidth)"
        ),
        url=(
            "https://developer.nvidia.com/blog/next-generation-ai-factory-"
            "telemetry-with-nvidia-spectrum-x-ethernet/"
        ),
    ),
    SourceLink(
        label=(
            "NVIDIA — AI fabric resiliency and why network convergence "
            "matters (NCCL has no heavy error recovery; small loss stalls "
            "training)"
        ),
        url=(
            "https://developer.nvidia.com/blog/ai-fabric-resiliency-and-why-"
            "network-convergence-matters/"
        ),
    ),
    SourceLink(
        label=(
            "Krebs, Amir, Landau Feibish, Silberstein — SprayCheck: finding "
            "gray failures in adaptive routing networks (arXiv 2605.03702)"
        ),
        url="https://arxiv.org/abs/2605.03702",
    ),
    SourceLink(
        label=(
            "NVIDIA Cumulus Linux — Equal cost multipath and adaptive "
            "routing (paths chosen by queue occupancy and port utilization)"
        ),
        url=(
            "https://docs.nvidia.com/networking-ethernet-software/"
            "cumulus-linux-514/Layer-3/Routing/"
            "Equal-Cost-Multipath-Load-Sharing/"
        ),
    ),
    SourceLink(
        label=(
            "IETF RFC 8326 — Graceful BGP session shutdown (move traffic "
            "off a link before taking it down)"
        ),
        url="https://www.rfc-editor.org/rfc/rfc8326",
    ),
]


def _fabric() -> list[str]:
    return _spines() + _leaves() + _endpoints()


def _collective_ms(tbps: int) -> int:
    """All-reduce time scales inversely with what the fabric delivers: the
    same gradients, moved at a lower rate. Integer arithmetic, no clock."""
    return (HEALTHY_COLLECTIVE_MS * HEALTHY_STEADY_TBPS + tbps // 2) // tbps


def simulate_gray_link() -> list[FabricState]:
    """One leaf-spine link degrades while staying up; telemetry finds it."""
    return [
        FabricState(
            step=0,
            phase="steady",
            label="Steady state — eight clean uplinks",
            description=L(
                novice=(
                    "The network is days into a training job and everything "
                    "is working. Four lower switches (leaves) each have a "
                    "cable to both upper switches (spines), so there are "
                    "eight of these up-cables in the picture, which the panel "
                    "calls uplinks, and the job's traffic is shared across "
                    "all of them. Each line on the map is really a bundle of "
                    "eight cables, which is how so small a drawing carries so "
                    "much traffic, and the part that goes bad here is one "
                    "cable inside one bundle. The drawing cannot show that, "
                    "so it takes the whole bundle out of service later; a "
                    "real repair takes out the one bad cable and costs less. "
                    "One round of the "
                    "processors swapping their results, called an all-reduce, "
                    "takes about 120 milliseconds; it is the top row of the "
                    "panel. "
                    "That number is what the people running the job watch, "
                    "and it is the number this scenario is about. All the "
                    "figures here are illustrative."
                ),
                standard=(
                    "The fabric is days into a training job, in the same "
                    "steady state the healthy trace ends on: 29 Tb/s, "
                    "busiest link 68%, nothing dropped. Four leaves times "
                    "two spines gives eight uplinks, and adaptive routing "
                    "sprays the job's packets across all of them. Each drawn "
                    "uplink stands for a bundle of eight 800 Gb/s links, as "
                    "the healthy trace's note says, and the optic that goes "
                    "gray here is one member of leaf 2's bundle to spine 1. "
                    "Per-packet spraying puts every flow that crosses the "
                    "bundle across that member, so the damage below is what "
                    "it would be; the recovery is drawn coarser than a real "
                    "one, withdrawing and shutting the whole uplink where an "
                    "operator shuts the one erring port and loses an eighth "
                    "of it. The capacity dip late in this trace is therefore "
                    "a worst case. The ordering is the content. One "
                    "all-reduce — every GPU exchanging gradients — completes "
                    "in about 120 ms. That completion time is what the "
                    "training team feels, and it is this scenario's hero "
                    "number. Figures are illustrative."
                ),
                expert=(
                    "Steady: 29 Tb/s, 68% peak, zero drops, eight drawn "
                    "uplinks of 8x 800G under per-packet AR. The gray optic "
                    "is one member of leaf 2's bundle to spine 1; the "
                    "recovery below drains the whole uplink, so its capacity "
                    "cost is a worst case. All-reduce ≈120 ms "
                    "(illustrative) — the hero number."
                ),
            ),
            active_regions=_fabric() + ["optics", "telemetry", "cooling", "mgmt"],
            fabric_tbps=HEALTHY_STEADY_TBPS,
            peak_link_percent=68,
            elapsed_seconds=0,
            sick_link=SICK_LINK,
            sick_link_status="up",
            collective_ms=_collective_ms(HEALTHY_STEADY_TBPS),
        ),
        FabricState(
            step=1,
            phase="degrade",
            label="One optic starts to err — error correction hides it",
            description=L(
                novice=(
                    "The optical part at one end of the cable between lower "
                    "switch 2 and upper switch 1 (leaf 2 and spine 1 on the "
                    "map) starts to wear out, or has "
                    "a speck of dust on its connector. Some bits now arrive "
                    "wrong. Links this fast expect that: every link carries "
                    "extra check bits so the receiver can repair a few wrong "
                    "bits by itself, which is called forward error "
                    "correction. For now it repairs all of them. The job "
                    "runs at full speed and nothing looks different. The "
                    "only trace is a counter of damaged bits, which engineers "
                    "call symbol errors, creeping upward on one port, and "
                    "nobody is looking at it. The panel's symbol errors row "
                    "says so: not on any dashboard."
                ),
                standard=(
                    "The optic on leaf 2's uplink to spine 1 begins to "
                    "degrade — an ageing laser, a dirty connector, a lane "
                    "running marginal. Raw bit errors rise. At these speeds "
                    "every link runs forward error correction (FEC): "
                    "redundant bits that let the receiver repair a bounded "
                    "number of errors without asking for anything again. For "
                    "now FEC repairs all of them, so throughput and "
                    "all-reduce time are unchanged. The only evidence is a "
                    "symbol-error counter on one port climbing from zero, "
                    "which is the early warning a fleet with tens of "
                    "thousands of optics has to be watching for."
                ),
                expert=(
                    "Optic on leaf-2↔spine-1 goes marginal. Pre-FEC BER "
                    "rises, FEC corrects everything, goodput unchanged. "
                    "Symbol-error counter on one port leaves zero — the "
                    "only signal, and an early one."
                ),
            ),
            active_regions=_fabric() + ["optics"],
            fabric_tbps=HEALTHY_STEADY_TBPS,
            peak_link_percent=68,
            elapsed_seconds=3600,
            sick_link=SICK_LINK,
            sick_link_status="up",
            symbol_errors_per_sec=40,
            collective_ms=_collective_ms(HEALTHY_STEADY_TBPS),
        ),
        FabricState(
            step=2,
            phase="blind",
            label="Errors outrun correction — the link stays up, the job slows",
            description=L(
                novice=(
                    "The wrong bits now come in bursts too large to repair. "
                    "A damaged message fails its checksum at the receiving "
                    "port and is thrown away there, and the sending network "
                    "card (a NIC) has to notice and send it again; the "
                    "panel's NIC retransmits row counts those. Nothing is lost "
                    "for good, and no switch ever ran out of room, so the "
                    "dropped-packet counter still reads zero. But a round of "
                    "result-swapping finishes only when its slowest message "
                    "arrives, and every round now contains some re-sent "
                    "messages. The round takes 205 ms instead of 120. The "
                    "network spreads each conversation across all the "
                    "up-cables, so every conversation through lower switch 2 "
                    "touches the bad cable. A cable that got much worse "
                    "than this would switch itself off, and the network "
                    "would route around it. This one is not bad enough for "
                    "that, so it still reports that it is up."
                ),
                standard=(
                    "Error bursts now exceed what FEC can repair. A frame "
                    "that arrives corrupt fails its frame check at the "
                    "receiving port and is discarded there; the sending NIC "
                    "detects the gap and retransmits. Nothing is lost for "
                    "good and no buffer overflowed, so dropped packets — "
                    "congestion loss — is still zero. But the collective "
                    "library has no heavy error recovery, and an all-reduce "
                    "completes at the pace of its slowest message: 120 ms "
                    "becomes 205 ms and the fabric delivers 17 Tb/s instead "
                    "of 29. Adaptive routing makes this worse, not better. "
                    "It picks paths by queue depth and port utilization, "
                    "the sick link is not congested, and per-packet spraying "
                    "puts every flow through leaf 2 across it. A link that "
                    "errs badly enough is taken down by its own physical "
                    "layer, and a down link is easy. This one sits below "
                    "that threshold: its state is up and it has not flapped "
                    "once."
                ),
                expert=(
                    "Uncorrectable bursts: corrupt frames fail FCS at "
                    "ingress, NICs retransmit. Congestion loss still zero. "
                    "All-reduce 120 → 205 ms, 29 → 17 Tb/s. Per-packet AR "
                    "selects on queue occupancy and utilization, so it "
                    "sprays every leaf-2 flow across the erring link. Error "
                    "rate is under the PHY's own link-fault threshold: oper "
                    "state up, no flap."
                ),
            ),
            active_regions=_fabric() + ["optics"],
            fabric_tbps=17,
            peak_link_percent=41,
            elapsed_seconds=10800,
            cycle_cost=2,
            sick_link=SICK_LINK,
            sick_link_status="up",
            symbol_errors_per_sec=9000,
            retransmits_per_sec=1400,
            collective_ms=_collective_ms(17),
        ),
        FabricState(
            step=3,
            phase="blind",
            label="Every dashboard is green — the hunt starts in the wrong place",
            description=L(
                novice=(
                    "The training team reports that each step of the job "
                    "takes almost twice as long. The network team checks "
                    "what network teams check first. All eight up-cables "
                    "report up. No switch has logged a cable going down and "
                    "coming back. No cable is anywhere near full; the "
                    "busiest sits at 41%, lower than before, because the "
                    "stalled job is offering less traffic. A test message "
                    "between any two racks gets through. Every sign says the "
                    "network is healthy, so the search moves to the "
                    "processors, the storage and the software, where there "
                    "is nothing to find. This is the longest stage, and the "
                    "map shows the bad cable exactly like the good ones, "
                    "because that is all anyone can see."
                ),
                standard=(
                    "The training team reports step time nearly doubled. "
                    "The network team checks the usual things. All eight "
                    "uplinks report up. There are no link-flap events in any "
                    "log. No link is saturated — the busiest reads 41%, "
                    "lower than before, because a stalled job offers less "
                    "load. A ping between any two racks succeeds. Every "
                    "coarse signal says the fabric is healthy, so the hunt "
                    "moves to GPUs, storage and the framework, where there "
                    "is nothing to find. This is the longest stage of the "
                    "failure, and the map draws the sick link exactly like "
                    "the other seven on purpose: that is the operator's "
                    "actual position."
                ),
                expert=(
                    "Step time ≈2×. Link state 8/8 up, no flap events, peak "
                    "41% (offered load fell), reachability fine. Coarse "
                    "health is green, so the hunt goes to GPUs, storage and "
                    "framework. Longest stage. The map draws the sick link "
                    "as healthy — deliberately."
                ),
            ),
            active_regions=_fabric() + ["optics"],
            fabric_tbps=17,
            peak_link_percent=41,
            elapsed_seconds=21600,
            cycle_cost=5,
            sick_link=SICK_LINK,
            sick_link_status="up",
            symbol_errors_per_sec=9000,
            retransmits_per_sec=1400,
            collective_ms=_collective_ms(17),
        ),
        FabricState(
            step=4,
            phase="telemetry",
            label="Per-link error counters name the port",
            description=L(
                novice=(
                    "The answer is in counters nobody had on a dashboard. "
                    "The network cards in the racks count how often they "
                    "re-send, and the cards in rack 2 are re-sending "
                    "constantly (the NIC retransmits row). The switches count "
                    "damaged bits on each port (the symbol errors row), and "
                    "one port on upper switch 1 — the one facing "
                    "lower switch 2 — shows thousands per second while the "
                    "other seven show none. The two counters point at the "
                    "same cable. It is now drawn in the warning colour. It "
                    "still reports up, and the job is still slow: knowing "
                    "which cable is bad has not yet fixed anything."
                ),
                standard=(
                    "The answer is in per-link counters, not link state. "
                    "NIC telemetry shows RoCE retransmission counters "
                    "climbing on the hosts behind leaf 2. Switch telemetry, "
                    "streamed at high frequency per port, shows symbol "
                    "errors and uncorrectable FEC blocks on one spine-1 port "
                    "— the one facing leaf 2 — and zero on the other seven "
                    "uplinks. The two ends agree, and the link is located. "
                    "From here the map draws it in the error colour. Its "
                    "state is still up and the job is still slow: locating "
                    "the fault has not yet moved a single packet."
                ),
                expert=(
                    "NIC RoCE retransmit counters high behind leaf 2; "
                    "per-port switch telemetry shows symbol errors and "
                    "uncorrectable FEC on one spine-1 port, zero on the "
                    "other seven. Located. Still oper-up, still 17 Tb/s."
                ),
            ),
            active_regions=_fabric() + ["optics", "telemetry", "mgmt"],
            fabric_tbps=17,
            peak_link_percent=41,
            elapsed_seconds=25200,
            cycle_cost=2,
            sick_link=SICK_LINK,
            sick_link_status="up",
            sick_link_located=True,
            symbol_errors_per_sec=9000,
            retransmits_per_sec=1400,
            collective_ms=_collective_ms(17),
        ),
        FabricState(
            step=5,
            phase="steer",
            label="Routing is withdrawn from the sick link while it is still up",
            description=L(
                novice=(
                    "An operator tells the two switches to stop offering "
                    "the bad cable as a path. It stays plugged in and still "
                    "reports up, but no job traffic is sent over it, and "
                    "traffic for rack 2 now reaches it only through upper "
                    "switch 2. The network did not do this unprompted: it "
                    "chooses paths by how busy they are, and the bad cable "
                    "never looked busy. Re-sending stops at once and a "
                    "round of result-swapping drops from 205 ms to 134 ms. "
                    "It does not return to 120, because lower switch 2 now "
                    "has one up-cable doing the work of two, and that cable "
                    "runs at 92%. The job got its speed back only at this "
                    "step — not when the fault was found, but when traffic "
                    "stopped crossing it. The cable still counts damaged "
                    "bits, because a fast link sends filler even when idle."
                ),
                standard=(
                    "An operator withdraws routing from the link: the "
                    "routing session that runs over it is shut down (or "
                    "signalled for graceful shutdown), so neither switch "
                    "offers it as a next hop and it leaves the equal-cost "
                    "group that adaptive routing sprays across. The link "
                    "itself stays up. Turning adaptive routing off on the "
                    "port would not have done this; the port would still be "
                    "a valid path. Other leaves now reach rack 2 only "
                    "through spine 2. Retransmissions stop immediately and "
                    "the all-reduce falls from 205 ms to 134 ms, the fabric "
                    "back to 26 Tb/s. It is not 29, because leaf 2 now has "
                    "one uplink doing the work of two, and that survivor "
                    "runs at 92%, drawn in amber — the healthy trace's "
                    "congestion machinery is what keeps it lossless there, "
                    "with a few percent of its packets ECN-marked. Throughput recovered "
                    "at this step and not before: finding the link changed "
                    "nothing, moving traffic off it changed everything. The "
                    "link still counts symbol errors, since an idle "
                    "high-speed link keeps signalling."
                ),
                expert=(
                    "Routing session on the link shut (or graceful-shutdown): "
                    "next hop leaves the ECMP/AR group, link stays oper-up "
                    "and idle; rack 2 reachable via spine 2 only. Disabling "
                    "AR on the port would not drain it. Retransmits → 0, "
                    "all-reduce 205 → 134 ms, 26 Tb/s. Not 29: leaf 2 is on "
                    "one uplink at 92%, held lossless by ECN/PFC. Recovery "
                    "happens here, not at detection."
                ),
            ),
            active_regions=_fabric() + ["telemetry", "mgmt"],
            fabric_tbps=26,
            peak_link_percent=92,
            hot_link=SURVIVOR_LINK,
            ecn_marked_percent=4,
            elapsed_seconds=25500,
            sick_link=SICK_LINK,
            sick_link_status="up",
            sick_link_located=True,
            traffic_steered=True,
            symbol_errors_per_sec=9000,
            collective_ms=_collective_ms(26),
        ),
        FabricState(
            step=6,
            phase="drain",
            label="The port is shut down on purpose",
            description=L(
                novice=(
                    "An operator switches the port off from the management "
                    "software. This is the first moment in the whole story "
                    "that the cable reports anything other than up, and a "
                    "person did it, not the hardware. Because no traffic was "
                    "using the cable any more, switching it off interrupts "
                    "nothing. A cable that is cleanly off is much better "
                    "than one that is half-working: the network plans "
                    "around what it knows is gone, and cannot plan around "
                    "what claims to be fine."
                ),
                standard=(
                    "An operator administratively disables the port from "
                    "fabric management. This is the first time in the "
                    "scenario that the link reports anything but up, and a "
                    "person did it, not the hardware. Because traffic had "
                    "already moved, the shutdown interrupts nothing — no "
                    "packets in flight on the link, no reconvergence under "
                    "load, no stalled collective. A link that is cleanly "
                    "down is better than one that is half up: routing plans "
                    "around what it knows is gone, and cannot plan around "
                    "what claims to be healthy. NVIDIA's account of this "
                    "fault on its own Israel-1 system goes straight here: "
                    "disable the faulty port, and bandwidth returns. Moving "
                    "traffic first is the more careful version of the same "
                    "cure."
                ),
                expert=(
                    "Port admin-down from fabric management — first "
                    "non-up state in the trace, and operator-initiated. "
                    "Traffic already moved, so nothing in flight and no "
                    "reconvergence under load. Clean-down beats half-up. "
                    "NVIDIA's Israel-1 account skips the prior step and "
                    "disables the port directly."
                ),
            ),
            active_regions=_fabric() + ["mgmt"],
            fabric_tbps=26,
            peak_link_percent=92,
            hot_link=SURVIVOR_LINK,
            ecn_marked_percent=4,
            elapsed_seconds=26100,
            sick_link=SICK_LINK,
            sick_link_status="admin-down",
            sick_link_located=True,
            traffic_steered=True,
            collective_ms=_collective_ms(26),
        ),
        FabricState(
            step=7,
            phase="replace",
            label="The optic is replaced and the link retrains",
            description=L(
                novice=(
                    "A technician cleans the connector and swaps the "
                    "optical part, which on a switch with plug-in optics is "
                    "a job done from the front panel with the switch "
                    "running. The two ends then tune themselves to the new "
                    "part, the same training every cable went through when "
                    "the network was first powered on. The cable is held "
                    "out of use until its damaged-bit counter has stayed at "
                    "zero for a while, so a marginal repair is caught here "
                    "and not by the job. The job keeps running on seven "
                    "up-cables throughout."
                ),
                standard=(
                    "A technician cleans the connector and replaces the "
                    "transceiver — on a switch with pluggable optics, a "
                    "front-panel job with the switch in service. With "
                    "co-packaged optics the engine is part of the switch "
                    "package, and the field-replaceable pieces are the "
                    "fibre and the external laser source, which is one "
                    "reason that option's reliability figures matter. The "
                    "link retrains, exactly as in the healthy trace's link "
                    "training, and routing stays withdrawn until its error "
                    "counters have stayed at zero. The job runs on seven "
                    "uplinks throughout."
                ),
                expert=(
                    "Connector cleaned, transceiver swapped hot (CPO: fibre "
                    "or external laser source instead). Link retrains, soaks "
                    "at zero errors before routing is restored. Job "
                    "continues on seven uplinks."
                ),
            ),
            active_regions=_fabric() + ["optics", "mgmt"],
            fabric_tbps=26,
            peak_link_percent=92,
            hot_link=SURVIVOR_LINK,
            ecn_marked_percent=4,
            elapsed_seconds=28800,
            cycle_cost=3,
            sick_link=SICK_LINK,
            sick_link_status="training",
            sick_link_located=True,
            traffic_steered=True,
            collective_ms=_collective_ms(26),
        ),
        FabricState(
            step=8,
            phase="restored",
            label="Eight clean uplinks — back to 120 ms",
            description=L(
                novice=(
                    "The repaired cable is offered as a path again. "
                    "Traffic spreads across all eight "
                    "up-cables again, the busiest drops back to 68%, and a "
                    "round of result-swapping is back to 120 ms. Through "
                    "the whole episode the network never threw a packet "
                    "away for lack of room, and no cable ever failed by "
                    "itself. What it lost was hours of training time, "
                    "during which every status light was green. The lesson "
                    "is to watch the per-cable error counters, not the "
                    "lights. The PhysicsFabric simulator in this repo has "
                    "the same fault as a switch you can flip."
                ),
                standard=(
                    "Routing is restored on the link and it rejoins the "
                    "group adaptive routing sprays across. Traffic "
                    "spreads across eight uplinks, the busiest falls back "
                    "to 68%, and the all-reduce is back to 120 ms at "
                    "29 Tb/s. Across the whole episode the fabric never "
                    "discarded a packet for want of buffer and no link ever "
                    "went down by itself. What was lost was hours of "
                    "training time, during which link state was green. "
                    "Lossless under congestion and healthy under corruption "
                    "are different guarantees with different instruments, "
                    "and the second one is per-link error telemetry. "
                    "PhysicsFabric's gray-failure toggle is this same fault "
                    "with a dial on it."
                ),
                expert=(
                    "Routing restored, link back in the ECMP/AR group: "
                    "29 Tb/s, 68%, 120 ms. Zero "
                    "congestion drops and zero unplanned link-down events "
                    "end to end; the cost was hours at 17 Tb/s behind green "
                    "link state. See PhysicsFabric's gray-failure toggle."
                ),
            ),
            active_regions=_fabric() + ["optics", "telemetry", "cooling", "mgmt"],
            fabric_tbps=HEALTHY_STEADY_TBPS,
            peak_link_percent=68,
            elapsed_seconds=30600,
            sick_link=SICK_LINK,
            sick_link_status="up",
            sick_link_located=True,
            collective_ms=_collective_ms(HEALTHY_STEADY_TBPS),
        ),
    ]


SCENARIOS: list[Scenario] = [
    Scenario(
        id=HEALTHY,
        name="Healthy bring-up",
        summary=L(
            novice=(
                "The network powers on, its cables tune themselves, and it "
                "carries a training job through a traffic jam without "
                "throwing anything away."
            ),
            standard=(
                "The fabric comes up, trains its links, and carries a "
                "collective through an incast without dropping a packet."
            ),
            expert="Bring-up, then a collective through incast. Zero drops.",
        ),
        hero_field="droppedPackets",
        hero_label="dropped packets",
        intro=L(
            novice=(
                "Data crosses a network in small pieces called packets. When "
                "a switch, the box that passes packets between computers, runs "
                "out of waiting space (its buffer), an ordinary network throws "
                "packets away, and the sender notices and sends them again. "
                "For most uses that is fine. It is very bad for training an AI "
                "model, where many processors (GPUs) work as one team: after "
                "every step they all swap results, called an all-reduce, and "
                "nobody can start the next step until everyone has finished. "
                "One re-sent packet makes the whole team wait. This network, "
                "four lower switches called leaves each cabled to two upper "
                "switches called spines, is built never to throw a packet "
                "away. It warns senders early, pauses traffic for an instant, "
                "and moves traffic onto a second route. Play the trace and "
                "watch the dropped packets row stay at zero while the busiest "
                "link reaches 98%. Figures are illustrative."
            ),
            standard=(
                "Ordinary Ethernet drops packets when a buffer fills: the "
                "sender notices, backs off, retransmits, and the network keeps "
                "working. That bargain is catastrophic for distributed "
                "training, where every GPU must finish the same all-reduce "
                "before any of them can start the next step, so one "
                "retransmission stalls the entire fleet. This fabric is built "
                "never to drop: it signals congestion early, pauses "
                "selectively, and moves flows onto the alternate paths "
                "leaf/spine provides. Play the trace and watch the "
                "dropped-packet counter stay at zero while the busiest link "
                "hits 98%, and watch what that costs in the marks and pauses "
                "rows. Figures are illustrative."
            ),
            expert=(
                "Lossy Ethernet plus a synchronous collective means one "
                "retransmit stalls every rank. This fabric trades drops for "
                "ECN marks, PFC pauses and adaptive routing. Watch drops hold "
                "at zero with the busiest link at 98%, and the mark and pause "
                "rows that pay for it. Illustrative."
            ),
        ),
        telemetry_note=L(
            novice=(
                "The dropped packets row is the whole promise, so watch it on "
                "the congestion step: the busiest link reaches 98% and the "
                "row still reads zero. An ordinary network would be throwing "
                "packets away there, and every re-send would hold up every "
                "GPU in the job. The two rows under it are the price. Marked "
                "packets tell senders to slow down, and a pause stops one "
                "kind of traffic for an instant, innocent traffic behind it "
                "included. Each line on the map stands for a bundle of eight "
                "800 gigabit cables, and throughput adds up the traffic "
                "climbing from the leaves to the spines. Values are "
                "illustrative."
            ),
            standard=(
                "The dropped-packet row is the product claim, so watch it "
                "during the congestion step: the busiest link hits 98% and the "
                "counter still reads zero. The two rows under it are what "
                "that costs. ECN marks slow the senders, and each PFC pause "
                "stops a whole traffic class on the link behind it, "
                "uncongested flows included. Each drawn leaf-to-spine line "
                "stands for a bundle of eight 800 Gb/s links (6.4 Tb/s), and "
                "fabric throughput is leaf-to-spine traffic summed over the "
                "eight bundles. Values are illustrative, meant to show shape "
                "and order of magnitude."
            ),
            expert=(
                "Drops stay 0 at 98%. Cost rows: ECN-marked share and PFC "
                "pause frames/s on the hot port. Each drawn uplink is 8x 800G; "
                "throughput is summed leaf-to-spine (51.2 Tb/s capacity). "
                "Illustrative."
            ),
        ),
        playback_hint=L(
            novice=(
                "The sequence is worked out in advance by the backend, and Run "
                "only plays it back. Step moves one event at a time. The "
                "slowest real-world stage, tuning every cable at 800 gigabits "
                "per second, stays on screen longer."
            ),
            standard=(
                "The fabric sequence is a fixed trace computed by the backend; "
                "Run only plays it back. Step walks one event at a time. The "
                "longest real-world stage (training every link at 800 Gb/s) "
                "dwells on screen longer."
            ),
            expert="Fixed backend trace; Run replays it. Link training holds the longest dwell.",
        ),
        phases=[
            "off", "power", "linktrain", "topology", "ready",
            "collective", "congestion", "reroute", "steady",
        ],
    ),
    Scenario(
        id=GRAY_LINK,
        name="Gray link failure",
        summary=L(
            novice=(
                "One cable goes bad without going down. Every status light "
                "stays green, and per-cable error counters are the only place "
                "the fault shows. The training job takes nearly twice as long "
                "and stays that way until a person moves traffic off the cable."
            ),
            standard=(
                "One leaf-spine link degrades but stays up. Link state stays "
                "green and per-link error counters are the only place the "
                "fault shows. The all-reduce stretches from 120 ms to 205 ms "
                "and stays there until an operator steers traffic off the link."
            ),
            expert=(
                "One uplink errs past FEC while oper-up. Link state green; "
                "per-port counters are the only signal. All-reduce "
                "120 → 205 ms until routing is withdrawn from the link."
            ),
        ),
        hero_field="collectiveMs",
        hero_label="all-reduce time",
        intro=L(
            novice=(
                "A training job is many processors (GPUs) working as one team. "
                "After every step they all swap results, called an all-reduce, "
                "and nobody starts the next step until everyone has finished. "
                "Their data crosses the network in small pieces called "
                "packets. Here the optical part at one end of one cable, the "
                "part that turns electrical signals into light, starts to "
                "fail. Some bits arrive damaged. Every link carries spare "
                "check bits that repair a few damaged bits, called forward "
                "error correction, but these come too fast to repair. A "
                "damaged packet is thrown away where it arrives, and the "
                "sending network card (a NIC) sends it again. No switch ran "
                "out of room, so the dropped packets row still reads zero, "
                "and the cable never reports down, so every status light is "
                "green while each all-reduce takes nearly twice as long. Play "
                "the trace and watch the all-reduce time. It recovers when a "
                "person moves traffic off the cable, not when the cable is "
                "found. Until the counters name it, the map draws the bad "
                "cable like the other seven, which is all anyone can see. "
                "Figures are illustrative."
            ),
            standard=(
                "One leaf-to-spine optic degrades. Its errors outrun forward "
                "error correction, corrupt frames are discarded at the "
                "receiving port, and the NICs send them again. No buffer "
                "overflowed, so the dropped-packet counter still reads zero, "
                "and the link never goes down, so every status page is green "
                "while the all-reduce takes nearly twice as long. Play the "
                "trace and watch the all-reduce time: it recovers when an "
                "operator moves traffic off the link, not when the link is "
                "found, and adaptive routing does not move it unprompted. "
                "Until telemetry names it, the map draws the sick link like "
                "the other seven, which is all the operator can see either. "
                "Figures are illustrative."
            ),
            expert=(
                "One uplink optic errs past FEC while oper-up: FCS discards, "
                "NIC retransmits, zero congestion drops, green link state, "
                "all-reduce near 2x. Recovery comes when routing is "
                "withdrawn, not at detection; AR selects on load and will not avoid it. The "
                "link is drawn healthy until located. Illustrative."
            ),
        ),
        telemetry_note=L(
            novice=(
                "Dropped packets counts packets thrown away because a switch "
                "ran out of room, and it stays at zero here too. Damaged "
                "packets are a different loss. The receiving port checks each "
                "one, throws away any that arrive damaged, and the sending "
                "network card (NIC) sends them again. That shows up in the "
                "NIC retransmits row and in the all-reduce time. Symbol "
                "errors are the damaged bits themselves, counted per cable. "
                "Watch where the time recovers: when a person moves traffic "
                "off the cable, not when the counters find it. Values are "
                "illustrative."
            ),
            standard=(
                "Dropped packets counts frames discarded for want of buffer, "
                "and it stays at zero here too. Corrupt frames are a "
                "different loss: the receiving port discards them at the "
                "frame check and the NIC sends them again, which shows up as "
                "retransmits and as all-reduce time. Watch where the time "
                "recovers: when an operator moves traffic off the link, not "
                "when telemetry finds it. Values are illustrative."
            ),
            expert=(
                "Drops = congestion loss, still 0. Corruption loss shows as "
                "NIC retransmits and all-reduce time. Recovery when routing "
                "is withdrawn, not at detection. Illustrative."
            ),
        ),
        playback_hint=L(
            novice=(
                "The sequence is worked out in advance by the backend, and Run "
                "only plays it back. Step moves one event at a time. The "
                "longest stage here, the hunt while every light is green, "
                "stays on screen longer."
            ),
            standard=(
                "The failure sequence is a fixed trace computed by the "
                "backend; Run only plays it back. Step walks one event at a "
                "time. The longest stage (the hunt while every dashboard is "
                "green) dwells on screen longer."
            ),
            expert="Fixed backend trace; Run replays it. The blind hunt holds the longest dwell.",
        ),
        phases=GRAY_LINK_PHASES,
        sources=GRAY_LINK_SOURCES,
    ),
]

TRACES = {
    HEALTHY: simulate,
    GRAY_LINK: simulate_gray_link,
}
