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
step of this trace, including at the peak of the incast — and
``tests/test_engine.py`` asserts exactly that.

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
                    "silicon rated to 409.6 Tb/s of switching capacity with 1.6 "
                    "Tb/s ports. No link is up and no packet has moved."
                ),
                standard=(
                    "The SN6000s power up and boot their network operating "
                    "system, the same disaggregated open-networking path the "
                    "E3200 twin walks through in detail: hardware init, then a "
                    "NOS loaded independently of the switch vendor. Each system "
                    "carries NVIDIA Spectrum-6 silicon rated to 409.6 Tb/s of "
                    "switching capacity with 1.6 Tb/s ports. No link is up yet "
                    "and no packet has moved."
                ),
                technical=(
                    "Power-on and NOS boot over the disaggregated open-networking "
                    "path detailed in the E3200 twin. Spectrum-6 silicon: 409.6 "
                    "Tb/s switching capacity, 1.6 Tb/s ports. No links up, no "
                    "forwarding."
                ),
                expert=(
                    "Power-on, disaggregated NOS boot. Spectrum-6: 409.6 Tb/s "
                    "capacity, 1.6 Tb/s ports. No links, no forwarding."
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
                    "correction, lane alignment, at 1.6 Tb/s per port. This is "
                    "where the optics choice shows up — pluggable transceivers or "
                    "co-packaged optics, where the optical engine sits on the "
                    "switch package itself, cutting the electrical distance and "
                    "with it a great deal of power. At these rates the network is "
                    "as much an analogue problem as a digital one."
                ),
                standard=(
                    "The long stage. Every leaf-to-spine and leaf-to-endpoint "
                    "link negotiates and tunes: signal equalization, forward "
                    "error correction, lane alignment, at 1.6 Tb/s per port. "
                    "This is where the optics choice shows up — pluggable "
                    "transceivers or co-packaged optics, where the optical "
                    "engine sits on the switch package itself, cutting the "
                    "electrical distance the signal travels and with it a "
                    "great deal of power. At these rates the network is as much "
                    "an analog engineering problem as a digital one."
                ),
                technical=(
                    "Max-dwell stage. Every leaf-spine and leaf-endpoint link "
                    "trains: equalization, FEC, lane alignment at 1.6 Tb/s per "
                    "port. The optics decision surfaces here — pluggable "
                    "transceivers versus co-packaged optics, where the optical "
                    "engine moves onto the switch package, shortening the "
                    "electrical path and cutting both loss and power."
                ),
                expert=(
                    "Max dwell: link training — equalization, FEC, lane alignment "
                    "at 1.6 Tb/s/port. CPO versus pluggable shows up here; CPO "
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
            label="All-reduce — every GPU exchanging gradients at once",
            description=L(
                novice=(
                    "A training step ends and the whole fleet performs a shared "
                    "calculation: every processor contributes its results and every "
                    "one must receive the combined answer before the next step can "
                    "start. This is the least forgiving traffic pattern networks "
                    "face — synchronized, everyone-to-everyone, and bursty — and it "
                    "repeats thousands of times an hour. Because it is a shared "
                    "calculation, the clock that matters is not the average speed "
                    "but when the *last* processor finishes."
                ),
                plain=(
                    "A training step ends and the fleet performs an all-reduce: "
                    "every GPU contributes its gradients and every GPU must receive "
                    "the summed result before the next step may begin. The traffic "
                    "pattern is the least forgiving networks face — synchronized, "
                    "all-to-all, and bursty — and it repeats thousands of times an "
                    "hour. The fabric carries 18 Tb/s comfortably, and because it "
                    "is a collective, the clock that matters is when the *last* GPU "
                    "finishes."
                ),
                standard=(
                    "A training step ends and the fleet performs an all-reduce: "
                    "every GPU contributes its gradients and every GPU must "
                    "receive the summed result before the next step may begin. "
                    "The traffic pattern is the least forgiving one networks "
                    "face — synchronized, all-to-all, and bursty — and it "
                    "repeats thousands of times an hour. The fabric carries "
                    "18 Tb/s comfortably, and because it is a collective, the "
                    "clock that matters is not average throughput but when the "
                    "*last* GPU finishes."
                ),
                technical=(
                    "All-reduce: every GPU contributes gradients and must receive "
                    "the reduction before the next step. Synchronized, all-to-all, "
                    "bursty — the least forgiving pattern in networking, repeating "
                    "thousands of times hourly. 18 Tb/s carried comfortably. "
                    "Completion time is set by the slowest participant, not by mean "
                    "throughput."
                ),
                expert=(
                    "All-reduce: synchronized all-to-all, 18 Tb/s. Completion "
                    "bounded by slowest participant, not mean throughput."
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
            label="Incast — many senders, one receiver, buffers filling",
            description=L(
                novice=(
                    "The hard moment. Traffic converges many-to-one — a save "
                    "operation landing on the storage network, or a calculation "
                    "collapsing toward one participant — and a single connection "
                    "hits 98% with data queuing up behind it. This is where an "
                    "ordinary network would start throwing traffic away. This one "
                    "does not: it marks packets so senders slow down before the "
                    "queues overflow, and it pauses one class of traffic rather "
                    "than discarding it. Watch the dropped counter stay at zero — "
                    "that single number is the entire product claim, because a "
                    "retransmission here would stall not one connection but every "
                    "processor in the job."
                ),
                plain=(
                    "The hard moment. Traffic converges many-to-one — a checkpoint "
                    "landing on the storage fabric, or a reduction collapsing "
                    "toward one rank — and a single link hits 98% with buffers "
                    "filling behind it. This is incast, and it is where ordinary "
                    "Ethernet would start discarding frames. The SN6000 does not: "
                    "explicit congestion notification marks packets so senders slow "
                    "before buffers overflow, and priority flow control pauses a "
                    "traffic class rather than dropping it. Watch the dropped "
                    "counter stay at zero."
                ),
                standard=(
                    "The hard moment. Traffic converges many-to-one — a "
                    "checkpoint landing on the storage fabric, or a reduction "
                    "collapsing toward one rank — and a single link hits 98% "
                    "with buffers filling behind it. This is called incast, and "
                    "it is where ordinary Ethernet would start discarding "
                    "frames. The SN6000 does not: explicit congestion "
                    "notification (ECN) marks packets so senders slow down "
                    "before buffers overflow, and priority flow control (PFC) "
                    "pauses a specific traffic class rather than dropping it. "
                    "Watch the dropped-packet counter stay at zero — that "
                    "single number is the entire product claim, because a "
                    "retransmission here would stall not one flow but every "
                    "GPU in the job."
                ),
                technical=(
                    "Incast: many-to-one convergence — checkpoint landing on the "
                    "storage fabric, or a reduction collapsing toward one rank — "
                    "driving a single link to 98% with buffers filling. Ordinary "
                    "Ethernet discards here. ECN marks before overflow and PFC "
                    "pauses a class rather than dropping. Zero drops asserted, and "
                    "the ≥95% utilization is asserted too, so losslessness is "
                    "proven under stress rather than at idle."
                ),
                expert=(
                    "Incast to 98% on one link, buffers filling. ECN marks "
                    "pre-overflow, PFC pauses the class. Zero drops asserted at "
                    "≥95% utilization — proven under stress, not at idle."
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
        ),
        FabricState(
            step=7,
            phase="reroute",
            label="Adaptive routing spreads the flows — congestion clears",
            description=L(
                novice=(
                    "Information from the congested link feeds the network's "
                    "adaptive routing, which moves traffic onto the alternative "
                    "paths the design has been holding in reserve since routing "
                    "settled. The busy link relaxes from 98% to 71% while the "
                    "*total* throughput rises — the work did not shrink, it spread "
                    "out. This is the difference from a generic network, where a "
                    "connection is pinned to one path for its lifetime, so an "
                    "unlucky collision stays unlucky for the whole job."
                ),
                plain=(
                    "Telemetry from the congested link feeds adaptive routing, "
                    "which moves flows onto the alternate equal-cost paths the "
                    "topology has held in reserve since routing converged. The hot "
                    "link relaxes from 98% to 71% while *total* throughput rises to "
                    "31 Tb/s — the work did not shrink, it spread. This is the "
                    "difference from generic Ethernet: conventional hashing pins a "
                    "flow to one path for its lifetime, so an unlucky collision "
                    "stays unlucky for the whole job."
                ),
                standard=(
                    "Telemetry from the congested link feeds the fabric's "
                    "adaptive routing, which moves flows onto the alternate "
                    "equal-cost paths the leaf/spine topology has been holding "
                    "in reserve since routing converged. The hot link relaxes "
                    "from 98% to 71% while *total* throughput rises to 31 Tb/s "
                    "— the work did not shrink, it spread. This is the "
                    "difference between Spectrum-X and generic Ethernet: "
                    "conventional hashing pins a flow to one path for its "
                    "lifetime, so an unlucky collision stays unlucky for the "
                    "whole job."
                ),
                technical=(
                    "Congestion telemetry drives adaptive routing onto the reserved "
                    "ECMP set. Hot link 98% → 71% while aggregate rises 24 → 31 "
                    "Tb/s: the work spread rather than shrank, and the engine "
                    "asserts both halves. Conventional flow hashing pins a flow for "
                    "its lifetime, so a collision persists for the job's duration."
                ),
                expert=(
                    "Adaptive routing onto the reserved ECMP set: 98%@24 Tb/s → "
                    "71%@31 Tb/s. Both halves asserted. Static hashing pins flows "
                    "and persists collisions."
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
        ),
        FabricState(
            step=8,
            phase="steady",
            label="Steady state — the training loop's heartbeat",
            description=L(
                novice=(
                    "The sustained pattern of the next several weeks: compute, "
                    "share results, save state, repeat, with the network absorbing "
                    "each burst and never throwing anything away. It has become "
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
                    "fabric is invisibility. Completes the quartet — compute "
                    "(XE9712), cooling (IR7000), data (Exascale), fabric (this)."
                ),
                expert=(
                    "Steady: compute, all-reduce, checkpoint, repeat. Zero drops "
                    "throughout. Success condition is invisibility. Completes the "
                    "quartet."
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
