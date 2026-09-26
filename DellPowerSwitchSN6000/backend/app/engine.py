"""Pure fabric engine for the PowerSwitch SN6000 leaf/spine AI fabric.

``simulate()`` returns the deterministic trace of an AI fabric coming up and
then carrying a training step's collective — including the congestion that
collective provokes and the adaptive routing that clears it. Same purity
rule as every other twin in this repo: no FastAPI, no IO, no timers — the
frontend owns the playback clock, and each ``FabricState`` is plain data the
renderer consumes. ``cycle_cost`` marks the long stages (link training) so
the UI dwells on them.

The idea this twin exists to teach: **an AI fabric's product is what it
refuses to do.** Ordinary Ethernet drops packets when a buffer fills; the
sender notices a gap, backs off, and retransmits, and the network keeps
working. That bargain is catastrophic for distributed training, where every
GPU must finish the same all-reduce before any of them can start the next
step — one retransmitted packet stalls not one flow but the entire fleet.
So the fabric is built never to drop: it signals congestion early (ECN),
pauses selectively (PFC), and spreads flows across alternate equal-cost
paths (adaptive routing). ``dropped_packets`` is therefore zero on every
step of this trace, including at the peak of the congestion — and
``tests/test_engine.py`` asserts exactly that. Zero drops is not free, so the
trace also carries what it cost: ``ecn_marked_percent`` and
``pfc_pauses_per_sec``, nonzero where the fabric is under stress.

The hotspot is a spine downlink, not a rack's last hop. Many-to-one traffic
overloads spine 1's link to leaf 2 while spine 2's has room; the sending
leaves' adaptive routing judges local queues and cannot see it until
telemetry tells them. A last-hop incast has no alternate path and only
congestion control relieves it; the reroute step says so.

Capacities and timings are illustrative but plausible for an SN6000-class
fabric; favor a correct mental model over measured numbers (project scope
guardrail).
"""

from __future__ import annotations

from .leveling import L
from .models import FabricState

SPINES = ["s1", "s2"]
LEAVES = ["l1", "l2", "l3", "l4"]
ENDPOINTS = ["e1", "e2", "e3", "e4"]

# Phases in which traffic is actually crossing the fabric.
TRAFFIC_PHASES = {"collective", "congestion", "reroute", "steady"}

# The link the congestion step saturates: spine 1's link down to leaf 2. It is
# a leaf-spine link on purpose. Adaptive routing can only relieve a hotspot
# that has an alternate path, and the last hop into a rack has none.
HOT_LINK = "leaf-l2:spine-s1"


def _spines() -> list[str]:
    return [f"spine-{s}" for s in SPINES]


def _leaves() -> list[str]:
    return [f"leaf-{l}" for l in LEAVES]


def _endpoints() -> list[str]:
    return [f"endpoint-{e}" for e in ENDPOINTS]


def simulate() -> list[FabricState]:
    """The fabric's journey from dark to sustained collective traffic."""
    return [
        FabricState(
            step=0,
            phase="off",
            label="Switches racked and cabled, fabric dark",
            description=L(
                novice=(
                    "Two upper-tier switches, four lower-tier switches, and the "
                    "racks of processors they serve — cabled into the standard "
                    "two-layer arrangement and powered down. Practically every "
                    "large AI cluster takes this shape for one reason: every lower "
                    "switch connects to every upper switch, so any rack reaches any "
                    "other rack in the same two steps. Equal distance matters more "
                    "here than raw speed, because a shared calculation finishes "
                    "only when its slowest participant does."
                ),
                plain=(
                    "Two spine switches, four leaf switches, and the GPU racks they "
                    "serve — cabled into a leaf/spine topology and powered down. "
                    "Leaf/spine is the shape practically every AI cluster takes, "
                    "for one reason: every leaf connects to every spine, so any "
                    "endpoint reaches any other in the same two hops. Uniform "
                    "distance matters more than raw speed, because a collective "
                    "finishes only when its slowest participant does."
                ),
                standard=(
                    "Two spine switches, four leaf switches, and the GPU racks "
                    "they serve — cabled into a leaf/spine topology and powered "
                    "down. Leaf/spine is the shape practically every AI cluster "
                    "takes, for one reason: every leaf connects to every spine, "
                    "so any endpoint reaches any other endpoint in the same two "
                    "hops. Uniform distance matters more here than raw speed, "
                    "because a collective operation finishes only when its "
                    "slowest participant does, and unequal path lengths would "
                    "make some GPU pairs permanently slower than others."
                ),
                technical=(
                    "Two spines, four leaves, four endpoint racks, cabled "
                    "leaf/spine and dark. Full leaf-to-spine mesh gives uniform "
                    "two-hop reachability between any endpoint pair. Path "
                    "uniformity dominates link speed because a collective completes "
                    "at the rate of its slowest participant."
                ),
                expert=(
                    "Leaf/spine, dark. Full mesh gives uniform two-hop "
                    "reachability; path uniformity dominates link rate under "
                    "collectives."
                ),
            ),
            active_regions=[],
            fabric_tbps=0,
            peak_link_percent=0,
            dropped_packets=0,
            elapsed_seconds=0,
        ),
        FabricState(
            step=1,
            phase="power",
            label="Switches power on — the network OS boots",
            description=L(
                novice=(
                    "The switches power up and load their operating system — the "
                    "same separated approach the campus switch twin covers in "
                    "detail, where the hardware and the software are bought "
                    "independently. Each system carries silicon rated for enormous "
                    "switching capacity. No connection is up yet and no traffic has "
                    "moved."
                ),
                plain=(
                    "The SN6000s power up and boot their network operating system, "
                    "the same disaggregated open-networking path the E3200 twin "
                    "walks through: hardware init, then a NOS loaded independently "
                    "of the switch vendor. Each system carries NVIDIA Spectrum-6 "
                    "silicon, 800 Gb/s ports and, in the largest four-chip model, up "
                    "to 409.6 Tb/s of switching capacity. No link is up and no "
                    "packet has moved."
                ),
                standard=(
                    "The SN6000s power up and boot their network operating "
                    "system, the same disaggregated open-networking path the "
                    "E3200 twin walks through in detail: hardware init, then a "
                    "NOS loaded independently of the switch vendor. Each system "
                    "carries NVIDIA Spectrum-6 silicon: 800 Gb/s ports, 102.4 Tb/s "
                    "per chip, and up to 409.6 Tb/s in the four-chip SN6800. No "
                    "link is up yet and no packet has moved."
                ),
                technical=(
                    "Power-on and NOS boot over the disaggregated open-networking "
                    "path detailed in the E3200 twin. Spectrum-6 silicon: 102.4 "
                    "Tb/s per ASIC (409.6 Tb/s in the 4-ASIC SN6800), 800 Gb/s "
                    "ports on 8x 200G PAM4 lanes. No links up, no forwarding."
                ),
                expert=(
                    "Power-on, disaggregated NOS boot. Spectrum-6: 102.4 Tb/s/ASIC, "
                    "up to 409.6 Tb/s, 800G ports. No links, no forwarding."
                ),
            ),
            active_regions=_spines() + _leaves() + ["mgmt"],
            fabric_tbps=0,
            peak_link_percent=0,
            dropped_packets=0,
            elapsed_seconds=20,
        ),
        FabricState(
            step=2,
            phase="linktrain",
            label="Every link trains — leaf to spine, leaf to endpoint",
            description=L(
                novice=(
                    "The long stage. Every connection negotiates and tunes itself: "
                    "signal shaping, error correction, lane alignment, at very high "
                    "rates per port. This is where the choice of optics shows up — "
                    "either pluggable modules or optics built onto the switch "
                    "package itself, which shortens the electrical distance the "
                    "signal travels and saves a great deal of power. At these rates "
                    "networking is as much an analogue engineering problem as a "
                    "digital one."
                ),
                plain=(
                    "The long stage. Every leaf-to-spine and leaf-to-endpoint link "
                    "negotiates and tunes: signal equalization, forward error "
                    "correction, lane alignment, at 800 Gb/s per port. This is "
                    "where the optics choice shows up — pluggable transceivers or "
                    "co-packaged optics, where the optical engine sits on the "
                    "switch package itself, cutting the electrical distance and "
                    "with it a great deal of power. At these rates the network is "
                    "as much an analogue problem as a digital one."
                ),
                standard=(
                    "The long stage. Every leaf-to-spine and leaf-to-endpoint "
                    "link negotiates and tunes: signal equalization, forward "
                    "error correction, lane alignment, at 800 Gb/s per port. "
                    "This is where the optics choice shows up — pluggable "
                    "transceivers or co-packaged optics, where the optical "
                    "engine sits on the switch package itself, cutting the "
                    "electrical distance the signal travels and with it a "
                    "great deal of power. At these rates the network is as much "
                    "an analog engineering problem as a digital one."
                ),
                technical=(
                    "Max-dwell stage. Every leaf-spine and leaf-endpoint link "
                    "trains: equalization, FEC, lane alignment at 800 Gb/s per "
                    "port (8x 200G PAM4). The optics decision surfaces here — pluggable "
                    "transceivers versus co-packaged optics, where the optical "
                    "engine moves onto the switch package, shortening the "
                    "electrical path and cutting both loss and power."
                ),
                expert=(
                    "Max dwell: link training — equalization, FEC, lane alignment "
                    "at 800 Gb/s/port. CPO versus pluggable shows up here; CPO "
                    "shortens the electrical path, cutting loss and power."
                ),
            ),
            active_regions=_spines() + _leaves() + _endpoints() + ["optics"],
            fabric_tbps=0,
            peak_link_percent=0,
            dropped_packets=0,
            elapsed_seconds=90,
            cycle_cost=5,
        ),
        FabricState(
            step=3,
            phase="topology",
            label="Routing converges — six switches become one fabric",
            description=L(
                novice=(
                    "The switches discover each other and routing settles, so each "
                    "lower switch learns it has several equally good paths to every "
                    "other one — one through each upper switch. Those spare paths "
                    "are not just there for failures; they are the raw material "
                    "that will later be used to spread out congested traffic. At "
                    "this moment six independent boxes stop behaving like six "
                    "devices and start behaving like one network."
                ),
                plain=(
                    "The switches discover each other and routing converges, so "
                    "each leaf learns it has multiple equal-cost paths to every "
                    "other leaf — one through each spine. Those redundant paths are "
                    "not merely failover; they are the raw material adaptive "
                    "routing will use to spread a congested flow. At this moment "
                    "six independent switches stop behaving like six devices and "
                    "start behaving like one fabric with a single forwarding "
                    "policy."
                ),
                standard=(
                    "The switches discover each other and routing converges, "
                    "so each leaf learns it has multiple equal-cost paths to "
                    "every other leaf — one through each spine. Those "
                    "redundant paths are not merely failover; they are the raw "
                    "material adaptive routing will use later to spread a "
                    "congested flow. At this moment six independent switches "
                    "stop behaving like six devices and start behaving like one "
                    "fabric with a single forwarding policy."
                ),
                technical=(
                    "Routing converges; each leaf resolves multiple equal-cost "
                    "paths to every other leaf, one per spine. The ECMP set is not "
                    "merely failover capacity — it is the substrate adaptive "
                    "routing consumes later. Six switches become one forwarding "
                    "domain with a single policy."
                ),
                expert=(
                    "Routing converges: per-leaf ECMP set, one path per spine. Not "
                    "failover capacity — the substrate adaptive routing consumes. "
                    "Six devices, one forwarding domain."
                ),
            ),
            active_regions=_spines() + _leaves() + ["mgmt", "telemetry"],
            fabric_tbps=0,
            peak_link_percent=0,
            dropped_packets=0,
            elapsed_seconds=120,
            cycle_cost=2,
        ),
        FabricState(
            step=4,
            phase="ready",
            label="Fabric ready — idle, cool, waiting for a job",
            description=L(
                novice=(
                    "The network is up and idle. The liquid cooling is already "
                    "running: this silicon at this capacity is hot enough that "
                    "liquid cooling is an option here for the same reason it is "
                    "mandatory on the processors — the cooling loop serves the "
                    "switches as well as the compute. Nothing is flowing yet and "
                    "every counter that matters reads zero."
                ),
                plain=(
                    "The fabric is converged and idle. Its liquid-cooling loop is "
                    "already running, because Spectrum-6 silicon at this capacity "
                    "runs hot enough that liquid cooling is offered on the SN6000 "
                    "for the same reason it is required on the GPUs — the IR7000 "
                    "twin's loop cools the switches as well as the compute. No "
                    "traffic is flowing, and every counter that matters reads zero."
                ),
                standard=(
                    "The fabric is up and idle. The liquid-cooling loop is "
                    "already running: Spectrum-6 silicon at this capacity is "
                    "hot enough that liquid cooling is an option on the SN6000 "
                    "for the same reason it is mandatory on the GPUs — the "
                    "IR7000 twin's loop serves the switches as well as the "
                    "compute. Nothing is flowing yet, and every counter that "
                    "matters reads zero."
                ),
                technical=(
                    "Fabric converged and idle, liquid loop already running. "
                    "Spectrum-6 at this capacity is a kilowatt-class thermal load, "
                    "so it shares the same cooling infrastructure as the compute — "
                    "a reminder that the network is not a low-power accessory in an "
                    "AI factory. All traffic counters zero."
                ),
                expert=(
                    "Converged, idle, liquid loop running. Spectrum-6 is a "
                    "kilowatt-class thermal load sharing the compute's cooling. "
                    "Counters zero."
                ),
            ),
            active_regions=_spines() + _leaves() + ["cooling", "telemetry"],
            fabric_tbps=0,
            peak_link_percent=0,
            dropped_packets=0,
            elapsed_seconds=140,
        ),
        FabricState(
            step=5,
            phase="collective",
            label=L(
                novice="All-reduce — every GPU sharing its results at once",
                standard="All-reduce — every GPU exchanging gradients at once",
            ),
            description=L(
                novice=(
                    "A training step ends and the whole fleet performs a shared "
                    "calculation called an all-reduce: every processor contributes "
                    "its results and every one must receive the combined answer "
                    "before the next step can start. Data crosses a network in "
                    "small pieces called packets, and this is the least forgiving "
                    "traffic networks face — everyone at the same instant, every "
                    "processor taking part, in sudden bursts — repeated thousands "
                    "of times an hour. The network carries 18 terabits per second "
                    "comfortably. Each line on the map stands for a bundle of "
                    "eight cables, which is how so small a drawing carries so "
                    "much. Because it is a shared calculation, the clock that "
                    "matters is not the average speed but when the last processor "
                    "finishes."
                ),
                plain=(
                    "A training step ends and the fleet performs an all-reduce: "
                    "every GPU contributes its gradients, the numbers that say how "
                    "the model should change, and every GPU must receive the "
                    "summed result before the next step may begin. The traffic "
                    "pattern is the least forgiving networks face — synchronized, "
                    "every GPU taking part, and bursty — and it repeats thousands "
                    "of times an hour. The fabric carries 18 Tb/s comfortably; "
                    "each line on the map stands for a bundle of eight 800 Gb/s "
                    "links. Because it is a collective, the clock that matters is "
                    "when the last GPU finishes."
                ),
                standard=(
                    "A training step ends and the fleet performs an all-reduce: "
                    "every GPU contributes its gradients and every GPU must "
                    "receive the summed result before the next step may begin. "
                    "The traffic pattern is the least forgiving one networks "
                    "face — synchronized, every rank participating, and bursty — "
                    "and it repeats thousands of times an hour. The fabric "
                    "carries 18 Tb/s comfortably. Each leaf-to-spine line on the "
                    "map stands for a bundle of eight 800 Gb/s links, and fabric "
                    "throughput is the leaf-to-spine traffic summed over all "
                    "eight bundles. Because this is a collective, the clock that "
                    "matters is not average throughput but when the last GPU "
                    "finishes."
                ),
                technical=(
                    "All-reduce, in practice a reduce-scatter followed by an "
                    "all-gather over a ring or tree: every rank contributes "
                    "gradients and must receive the reduction before the next "
                    "step. Synchronized, every rank participating, bursty, "
                    "thousands of times hourly. 18 Tb/s carried comfortably, "
                    "measured leaf-to-spine and summed over the eight drawn "
                    "uplinks; each stands for 8x 800G (6.4 Tb/s), so 51.2 Tb/s of "
                    "uplink capacity. Completion time is set by the slowest "
                    "participant, not by mean throughput."
                ),
                expert=(
                    "All-reduce (reduce-scatter + all-gather), every rank in "
                    "lockstep. 18 Tb/s leaf-to-spine over 8 drawn uplinks of 8x "
                    "800G each (51.2 Tb/s). Completion bounded by slowest "
                    "participant, not mean throughput."
                ),
            ),
            active_regions=(
                _spines() + _leaves() + _endpoints() + ["telemetry", "cooling"]
            ),
            fabric_tbps=18,
            peak_link_percent=62,
            dropped_packets=0,
            elapsed_seconds=180,
            cycle_cost=2,
        ),
        FabricState(
            step=6,
            phase="congestion",
            label="Congestion — many senders converge on one spine link, buffers filling",
            description=L(
                novice=(
                    "The hard moment. Many senders aim at one place at once — the "
                    "job saving its progress (a checkpoint) to storage, or a "
                    "calculation collapsing toward one participant — and too much "
                    "of the traffic for rack 2 goes by way of upper switch 1. Its "
                    "link down to lower switch 2 (leaf 2) hits 98%, with data "
                    "queuing in the switch's buffer, its waiting space. The other "
                    "route, through upper switch 2, still has room, but no sender "
                    "can see that from where it sits. This is where an ordinary "
                    "network would start throwing packets away. This one does "
                    "not: it marks packets so senders slow down before the queue "
                    "overflows, written ECN on the panel, and it can pause one "
                    "class of traffic for an instant rather than discard it, "
                    "written PFC. Neither is free. A pause also holds up "
                    "innocent traffic waiting behind it, which is why the panel "
                    "counts both — the marked-packets row and the pauses row. "
                    "Watch the dropped packets row stay at zero — that single "
                    "number is the entire "
                    "product claim, because re-sending one packet here would "
                    "stall not one connection but every processor in the job."
                ),
                plain=(
                    "The hard moment. Traffic converges many-to-one — a checkpoint "
                    "(the job saving its progress) landing on the storage fabric, "
                    "or a reduction collapsing toward one GPU — and too many of "
                    "the flows for rack 2 cross spine 1. Its link down to leaf 2 "
                    "hits 98% with buffers filling behind it, while the path "
                    "through spine 2 has room that no sender can see yet. "
                    "Many-to-one traffic is called incast, and this is where "
                    "ordinary Ethernet would start discarding frames. The SN6000 "
                    "does not: explicit congestion notification (ECN) marks "
                    "packets so senders slow before buffers overflow, and "
                    "priority flow control (PFC) pauses a traffic class rather "
                    "than dropping it. A pause has a price: it also stops "
                    "innocent flows of that class on the link behind it. Watch "
                    "the dropped counter stay at zero while the marked-packets "
                    "and pauses rows move."
                ),
                standard=(
                    "The hard moment. Traffic converges many-to-one — a "
                    "checkpoint landing on the storage fabric, or a reduction "
                    "collapsing toward one rank — and too many of the flows "
                    "bound for rack 2 cross spine 1. Its link down to leaf 2 "
                    "hits 98% with buffers filling behind it, while the path "
                    "through spine 2 has room. Each sending leaf picked its "
                    "spine from its own uplink queues, and those looked fine; "
                    "the pile-up is one hop further on, where no sender can see "
                    "it. Many-to-one traffic like this is called incast, and it "
                    "is where ordinary Ethernet would start discarding frames. "
                    "The SN6000 does not: explicit congestion notification (ECN) "
                    "marks packets so senders slow down before buffers overflow, "
                    "and priority flow control (PFC) pauses a specific traffic "
                    "class rather than dropping it. Neither is free. A pause "
                    "stops every flow of that class on the link behind it, "
                    "including flows bound somewhere uncongested, and pauses can "
                    "spread upstream hop by hop; the telemetry panel counts "
                    "marks and pauses for that reason. Watch the dropped-packet "
                    "counter stay at zero — that single number is the entire "
                    "product claim, because a retransmission here would stall "
                    "not one flow but every GPU in the job."
                ),
                technical=(
                    "Many-to-one convergence — a checkpoint landing on the "
                    "storage fabric, or a reduction collapsing toward one rank — "
                    "overloads the spine-1 downlink to leaf 2: 98% with buffers "
                    "filling, spine 2's downlink underused. Leaf-local adaptive "
                    "routing chose on its own egress queues and cannot see a "
                    "queue one hop away. Ordinary Ethernet discards here. ECN "
                    "marks before overflow (12% of packets on the hot link) and "
                    "PFC pauses the class upstream (40 pause frames/s), which "
                    "costs head-of-line blocking for victim flows and can "
                    "propagate. Zero drops with the link at or above 95%, so "
                    "losslessness is shown under stress rather than at idle. "
                    "Figures illustrative."
                ),
                expert=(
                    "Many-to-one traffic overloads spine-1 to leaf-2: 98%, "
                    "buffers filling; remote to the sending leaves, so local AR "
                    "did not avoid it. ECN marks pre-overflow (12%), PFC pauses "
                    "the class (40/s) at the cost of head-of-line blocking "
                    "upstream. Zero drops at ≥95% utilization (illustrative)."
                ),
            ),
            active_regions=(
                _spines() + _leaves() + _endpoints() + ["telemetry"]
            ),
            fabric_tbps=24,
            peak_link_percent=98,
            dropped_packets=0,
            elapsed_seconds=186,
            cycle_cost=3,
            hot_link=HOT_LINK,
            ecn_marked_percent=12,
            pfc_pauses_per_sec=40,
        ),
        FabricState(
            step=7,
            phase="reroute",
            label="Adaptive routing spreads the flows — congestion clears",
            description=L(
                novice=(
                    "News of the crowded link reaches the lower switches that are "
                    "sending into it. The network's adaptive routing had been "
                    "choosing routes all along, but each switch could only judge "
                    "by its own cables. Now that they know, they move part of the "
                    "traffic for rack 2 onto the other route, through upper "
                    "switch 2, which had room the whole time. The busy link "
                    "relaxes from 98% to 71%, the pauses stop, and the total the "
                    "network carries rises from 24 to 31 terabits per second — "
                    "the work did not shrink, it spread out. A generic network "
                    "pins each conversation to one route for its whole life, so "
                    "an unlucky pile-up stays unlucky for the whole job. One "
                    "limit: the last cable into a rack has no second route, and "
                    "a pile-up there eases only when the senders slow down."
                ),
                plain=(
                    "Telemetry from the congested link reaches the leaves sending "
                    "into it. Adaptive routing was on all along, but each leaf "
                    "could judge only its own uplinks; now it moves flows for "
                    "rack 2 onto the equal-cost path through spine 2, which had "
                    "room. The hot link relaxes from 98% to 71%, pauses stop, and "
                    "total throughput rises from 24 to 31 Tb/s — the work did "
                    "not shrink, it spread. Generic Ethernet hashes a flow onto "
                    "one path for its lifetime, so an unlucky collision stays "
                    "unlucky for the whole job. The last link into a rack has no "
                    "alternate path; congestion there eases only when senders "
                    "slow."
                ),
                standard=(
                    "Telemetry from the congested link reaches the leaves that "
                    "are sending into it. Adaptive routing has been choosing "
                    "paths since routing converged, but only on what each leaf "
                    "could see locally; with the remote queue now visible, it "
                    "moves flows for rack 2 onto the alternate equal-cost path "
                    "through spine 2. The hot link relaxes from 98% to 71%, the "
                    "pauses stop, and total throughput rises from 24 to 31 Tb/s "
                    "— the work did not shrink, it spread. This is the "
                    "difference between Spectrum-X and generic Ethernet: "
                    "conventional hashing pins a flow to one path for its "
                    "lifetime, so an unlucky collision stays unlucky for the "
                    "whole job. Routing can only help where a second path "
                    "exists. The last link into a rack has none, and congestion "
                    "there is relieved only by ECN slowing the senders."
                ),
                technical=(
                    "Congestion telemetry from the spine-1 downlink reaches the "
                    "sending leaves, and adaptive routing (load-aware all along, "
                    "but leaf-local) shifts rack-2 flows onto the alternate "
                    "equal-cost path via spine 2. Hot link 98% → 71%, PFC pauses "
                    "to zero, ECN marks to 1%, aggregate 24 → 31 Tb/s: the work "
                    "spread rather than shrank. Static flow hashing pins a flow "
                    "for its lifetime, so a collision persists for the job. "
                    "Path diversity ends at the leaf: a last-hop incast is "
                    "relieved by congestion control alone."
                ),
                expert=(
                    "Remote congestion signal reaches the sending leaves; AR "
                    "shifts rack-2 flows to the alternate equal-cost path via "
                    "spine 2: 98%@24 Tb/s → 71%@31 Tb/s, pauses 0. Static "
                    "hashing pins flows and persists collisions. Last-hop "
                    "incast has no alternate path; only congestion control "
                    "relieves it."
                ),
            ),
            active_regions=(
                _spines() + _leaves() + _endpoints() + ["telemetry", "mgmt"]
            ),
            fabric_tbps=31,
            peak_link_percent=71,
            dropped_packets=0,
            elapsed_seconds=190,
            cycle_cost=2,
            ecn_marked_percent=1,
        ),
        FabricState(
            step=8,
            phase="steady",
            label="Steady state — the training loop's heartbeat",
            description=L(
                novice=(
                    "The sustained pattern of the next several weeks: compute, "
                    "share results, save progress (a checkpoint), repeat, with the "
                    "network absorbing each burst and never throwing a packet away. It has become "
                    "invisible in the good way, which is the only review a network "
                    "ever gets. Together with the compute racks, the cooling loop, "
                    "and the storage that feeds them, this completes the picture."
                ),
                plain=(
                    "The sustained pattern of the next several weeks: compute, "
                    "all-reduce, checkpoint, repeat, with the fabric absorbing each "
                    "burst and never dropping a packet. The fabric has become "
                    "invisible in the good way, which is the only review a network "
                    "gets. Together with the XE9712 racks, the IR7000 loop that "
                    "cools them, and the Exascale storage that feeds them, this "
                    "completes the AI factory."
                ),
                standard=(
                    "The sustained pattern of the next several weeks: compute, "
                    "all-reduce, checkpoint, repeat, with the fabric absorbing "
                    "each burst and never dropping a packet. The fabric has "
                    "become invisible in the good way, which is the only "
                    "review a network gets. Together with the XE9712 racks, "
                    "the IR7000 loop that cools them, and the Exascale storage "
                    "that feeds them, this completes the AI factory: compute, "
                    "cooling, data, and the fabric that ties them into one "
                    "machine."
                ),
                technical=(
                    "Steady state: compute, all-reduce, checkpoint, repeat, with "
                    "every burst absorbed and no drops. The success condition for a "
                    "fabric is invisibility. Fourth of this project's four AI "
                    "factory twins — compute (XE9712), cooling (IR7000), data "
                    "(Exascale), fabric (this)."
                ),
                expert=(
                    "Steady: compute, all-reduce, checkpoint, repeat. Zero drops "
                    "throughout. Success condition is invisibility. Companion "
                    "twins: XE9712, IR7000, Exascale."
                ),
            ),
            active_regions=(
                _spines() + _leaves() + _endpoints()
                + ["optics", "telemetry", "cooling", "mgmt"]
            ),
            fabric_tbps=29,
            peak_link_percent=68,
            dropped_packets=0,
            elapsed_seconds=240,
        ),
    ]
