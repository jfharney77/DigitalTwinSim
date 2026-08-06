"""Pure fabric engine for the Quantum-X800 InfiniBand leaf/spine fabric.

``simulate()`` returns the deterministic trace of an InfiniBand fabric being
programmed into existence and then carrying a training step's collective —
including the SHARP offload that moves the arithmetic into the switches and
the incast burst that credit-based flow control absorbs without loss. Same
purity rule as every other twin in this repo: no FastAPI, no IO, no timers —
the frontend owns the playback clock, and each ``FabricState`` is plain data
the renderer consumes. ``cycle_cost`` marks the long stage (central route
computation) so the UI dwells on it.

The idea this twin exists to teach: **lossless by construction, not by
vigilance.** The SN6000 Ethernet twin proves its fabric never drops by
driving it into congestion and watching the counter stay at zero — Ethernet
drops by default, so losslessness there is an achievement of ECN, PFC, and
adaptive routing reacting fast enough. InfiniBand inverts the premise: a
sender may not put a packet on the wire until the receiver has granted it
buffer credits, so there is never a packet in flight without a reserved
place to land. ``packets_sent_without_credit`` is zero on every step not
because the fabric caught itself in time but because the link layer cannot
express the violation. The honest cost appears in a different column:
under incast, senders *wait* (``stall_micros_per_sec``), and waiting
briefly is precisely the bargain distributed training wants, because a
stalled flow resumes in microseconds while a dropped packet stalls every
GPU in the job. Capacities and timings are illustrative but plausible for
a Quantum-X800-class fabric; favor a correct mental model over measured
numbers (project scope guardrail).
"""

from __future__ import annotations

from .leveling import L
from .models import FabricState

SPINES = ["s1", "s2"]
LEAVES = ["l1", "l2", "l3", "l4"]
ENDPOINTS = ["e1", "e2", "e3", "e4"]

# Phases in which traffic is actually crossing the fabric.
TRAFFIC_PHASES = {"collective", "sharp", "burst", "steady"}
# Phases in which the subnet manager is at work — and the only ones: the
# brain programs the fabric, then leaves the data path.
MANAGER_PHASES = {"discover", "routes"}


def _spines() -> list[str]:
    return [f"spine-{s}" for s in SPINES]


def _leaves() -> list[str]:
    return [f"leaf-{l}" for l in LEAVES]


def _endpoints() -> list[str]:
    return [f"endpoint-{e}" for e in ENDPOINTS]


def simulate() -> list[FabricState]:
    """The fabric's journey from dark to a SHARP-accelerated training loop."""
    return [
        FabricState(
            step=0,
            phase="off",
            label="Switches racked and cabled, fabric dark",
            description=L(
                novice=(
                    "The network switches sit in their racks with every cable "
                    "already run — thick fibre bundles from each computer rack "
                    "up to the top-of-rack switches, and from those up to the "
                    "core switches every rack shares. Nothing is on. This is a "
                    "different kind of network from the office sort: it exists "
                    "to let thousands of processors swap partial results "
                    "mid-calculation, where a single lost message would make "
                    "everyone wait. The design that prevents that loss starts "
                    "powered off, like everything else."
                ),
                plain=(
                    "The Quantum-X800 switches sit racked with the fibre plant "
                    "already run: each GPU rack to its leaf switch, every leaf "
                    "to every spine. Nothing is energized. This is an "
                    "InfiniBand fabric — a supercomputer interconnect, not a "
                    "general-purpose network — and its defining property, "
                    "losslessness by construction, is wired into the link "
                    "layer it will bring up in a few steps."
                ),
                standard=(
                    "The Quantum-X800 switches sit racked and cabled, dark: "
                    "each GPU rack wired to its leaf (top-of-rack) switch, "
                    "every leaf wired to every spine, the OSFP transceivers "
                    "seated. This is an InfiniBand fabric — the "
                    "supercomputer interconnect lineage, distinct from "
                    "Ethernet — and the difference is architectural, not a "
                    "speed grade: InfiniBand's link layer will not let a "
                    "sender transmit until the receiver has granted it "
                    "buffer space, and a central subnet manager will program "
                    "every route before a byte moves. Both mechanisms are "
                    "still switched off, like everything else."
                ),
                technical=(
                    "Racked and cabled: leaf per GPU rack, full leaf-to-spine "
                    "mesh, OSFP plant seated. InfiniBand end to end — "
                    "credit-based link layer and centralized subnet "
                    "management, both inert until bring-up. Dark."
                ),
                expert=(
                    "Cabled fat tree, OSFP plant in. IB link layer + central "
                    "SM, both down. Dark."
                ),
            ),
            active_regions=[],
            fabric_tbps=0,
            peak_link_percent=0,
            allreduce_gbps=0,
            elapsed_seconds=0,
        ),
        FabricState(
            step=1,
            phase="power",
            label="Switches energize — the liquid loop takes their heat",
            description=L(
                novice=(
                    "Power is applied and the switch chips come alive. Each "
                    "core switch moves so much data that it is cooled with "
                    "liquid rather than fans — the same plumbing story as the "
                    "GPU racks it serves, told at smaller scale. The switches "
                    "boot their firmware and start watching their ports, but "
                    "no connections exist yet: at this moment the network is "
                    "a collection of powered boxes that do not yet know each "
                    "other."
                ),
                plain=(
                    "Power is applied: the spine and leaf switches boot their "
                    "firmware, and the liquid loop takes the switch ASICs' "
                    "heat — at 800 Gb/s per port the silicon is dense enough "
                    "that the Q3400 chassis is liquid-cooled like the GPU "
                    "racks it joins (the IR7000 twin's loop, at smaller "
                    "scale). Ports see light on the fibre but no links are "
                    "up: the boxes do not yet know each other."
                ),
                standard=(
                    "Power is applied. The spine and leaf switches boot "
                    "their firmware and the cold plates start pulling heat "
                    "into the liquid loop — at 800 Gb/s per port the switch "
                    "ASICs are dense enough that the Quantum-X800 chassis "
                    "is liquid-cooled just like the GPU racks it joins, a "
                    "small echo of the IR7000 twin's whole story. Each port "
                    "sees light on its fibre and trains its lanes, but the "
                    "fabric does not exist yet: nothing knows the topology, "
                    "no route is installed, and InfiniBand will not forward "
                    "a packet on a link the subnet manager has not blessed."
                ),
                technical=(
                    "Switches boot; cold plates on the loop. Lanes train "
                    "per-port, but no forwarding: unconfigured IB ports pass "
                    "only subnet-management packets until the SM programs "
                    "them. The fabric is boxes, not yet a fabric."
                ),
                expert=(
                    "Power + lane training. SMP-only until the SM programs "
                    "ports. Liquid-cooled ASICs. No fabric yet."
                ),
            ),
            active_regions=_spines() + _leaves() + ["cooling"],
            fabric_tbps=0,
            peak_link_percent=0,
            allreduce_gbps=0,
            elapsed_seconds=20,
        ),
        FabricState(
            step=2,
            phase="discover",
            label="The subnet manager sweeps the fabric — one brain, whole map",
            description=L(
                novice=(
                    "Now the network's brain wakes up. One machine — the "
                    "subnet manager — walks the entire network, hop by hop, "
                    "and builds a complete map: every switch, every computer, "
                    "every cable between them. This is the deep difference "
                    "from ordinary networking, where every switch figures "
                    "things out for itself by gossiping with its neighbours. "
                    "Here, exactly one authority knows the whole picture, "
                    "and everything that happens next follows from its map. "
                    "The office-network approach heals itself when things "
                    "change; this approach knows precisely what it has, "
                    "which is what a machine built to run one giant "
                    "calculation wants."
                ),
                plain=(
                    "The subnet manager — UFM, running beside the fabric — "
                    "sweeps the network hop by hop and builds the complete "
                    "map: every switch, every ConnectX adapter, every cable, "
                    "each given a fabric-local address. This is InfiniBand's "
                    "deep difference from Ethernet: no distributed protocol "
                    "converging by gossip, but one authority that knows the "
                    "whole graph. Distributed healing versus central "
                    "knowledge is a real trade — and a machine built to run "
                    "one job wants the second."
                ),
                standard=(
                    "The fabric's brain goes to work. The subnet manager "
                    "(SM — here NVIDIA UFM, running on a host beside the "
                    "fabric) sweeps the network hop by hop using the only "
                    "packets unconfigured InfiniBand ports will pass, and "
                    "builds a complete map: every switch, every ConnectX "
                    "adapter, every cable between them, each assigned a "
                    "fabric-local address. This centralization is "
                    "InfiniBand's deep architectural difference from "
                    "Ethernet, where every switch runs distributed "
                    "protocols and the topology is something the network "
                    "discovers about itself by gossip. Here one authority "
                    "holds the whole graph — which is exactly what you "
                    "want for a machine whose purpose is running a single "
                    "job across every node at once."
                ),
                technical=(
                    "SM sweep (UFM): directed-route SMPs walk the graph, "
                    "assign LIDs, inventory switches, HCAs, and links. "
                    "Centralized topology authority versus Ethernet's "
                    "distributed convergence — the architectural fork all "
                    "of IB's determinism descends from."
                ),
                expert=(
                    "UFM sweep: DR SMPs, LID assignment, full graph "
                    "inventory. Central authority, no convergence."
                ),
            ),
            active_regions=["manager"] + _spines() + _leaves() + _endpoints() + ["optics"],
            fabric_tbps=0,
            peak_link_percent=0,
            allreduce_gbps=0,
            elapsed_seconds=60,
            cycle_cost=2,
        ),
        FabricState(
            step=3,
            phase="routes",
            label="Every forwarding table computed centrally, then installed",
            description=L(
                novice=(
                    "The longest stage, and the most distinctive. With the "
                    "map complete, the subnet manager sits and computes the "
                    "path every possible conversation will take — every "
                    "computer to every other computer, spread evenly so no "
                    "cable becomes a bottleneck — and then writes those "
                    "routing tables into every switch. Only after the last "
                    "table lands is the network allowed to carry data. An "
                    "ordinary network figures out routes as it goes and "
                    "adjusts when things change; this one is programmed "
                    "like a machine, before use, by something that can see "
                    "all of it. The waiting is the price of the certainty."
                ),
                plain=(
                    "The longest stage. With the map complete, the subnet "
                    "manager computes routes for every source-destination "
                    "pair — balanced across the spine layer so no link "
                    "carries more than its share — and installs the "
                    "forwarding tables into every switch. Ethernet "
                    "converges: switches exchange protocol messages until "
                    "routing settles. InfiniBand is programmed: nothing "
                    "forwards until the central computation lands, and the "
                    "trace dwells here because for a Horizon-scale fabric "
                    "that computation is genuinely the slow part."
                ),
                standard=(
                    "The single longest stage, and InfiniBand's most "
                    "distinctive moment. With the map complete, the subnet "
                    "manager computes the forwarding table for every "
                    "switch — every source-to-destination pair assigned a "
                    "path, balanced across the spines so the fat tree's "
                    "full cross-section is used — and pushes the tables "
                    "into the hardware. Where the SN6000 twin's fabric "
                    "*converges* (distributed protocols negotiating until "
                    "routing settles), this fabric is *programmed*: no "
                    "data packet moves until the central computation is "
                    "installed, and for a fabric the size of TACC's "
                    "Horizon that computation is genuinely the slow part "
                    "of bring-up. The UI dwells here for the same reason "
                    "the R760 twin dwells on memory training — the wait "
                    "is the work."
                ),
                technical=(
                    "Max-dwell stage. SM computes per-switch linear "
                    "forwarding tables — all pairs, spine-balanced (fat-tree "
                    "routing) — and installs them. Programmed, not "
                    "converged: zero forwarding until tables land. Route "
                    "computation scales with fabric size; at Horizon scale "
                    "it dominates bring-up."
                ),
                expert=(
                    "Max dwell: SM computes + installs LFTs, spine-balanced, "
                    "all pairs. No forwarding until installed. Programmed, "
                    "not converged."
                ),
            ),
            active_regions=["manager"] + _spines() + _leaves(),
            fabric_tbps=0,
            peak_link_percent=0,
            allreduce_gbps=0,
            elapsed_seconds=150,
            cycle_cost=5,
        ),
        FabricState(
            step=4,
            phase="credits",
            label="Receivers grant buffer credits — losslessness switches on",
            description=L(
                novice=(
                    "Now the network's defining rule takes effect. On every "
                    "link, the receiving end tells the sending end exactly "
                    "how much buffer space it has free, and the sender is "
                    "not allowed to transmit more than that. Permission "
                    "before transmission, on every link, always. This is "
                    "why this network cannot lose data the way an ordinary "
                    "one can: an ordinary network sends first and discards "
                    "what does not fit, while this one never sends what "
                    "does not fit in the first place. Nothing dramatic "
                    "shows on screen — a rule this deep just switches on."
                ),
                plain=(
                    "The defining mechanism arms. On every link, the "
                    "receiver advertises its free buffer space as credits, "
                    "and the sender may transmit only against credits it "
                    "holds — permission before transmission, per link, "
                    "always. Ethernet transmits first and drops what "
                    "overflows; InfiniBand never sends what has no landing "
                    "place. The packetsSentWithoutCredit counter starts "
                    "here and will read zero forever — not vigilance, "
                    "construction."
                ),
                standard=(
                    "The mechanism this twin exists for arms itself. On "
                    "every link, the receiving end advertises how much "
                    "buffer space it has free — its *credits* — and the "
                    "sending end may transmit only against credits it "
                    "holds, returning them as the receiver drains. "
                    "Permission precedes transmission, on every link, "
                    "always. This is credit-based flow control, and it is "
                    "why the packets-sent-without-credit counter on the "
                    "right will read zero for the rest of the trace: not "
                    "because the fabric reacts quickly when buffers fill — "
                    "the SN6000 twin's Ethernet story — but because the "
                    "link layer has no way to transmit into a full buffer "
                    "at all. The cost will appear later, in a different "
                    "column: when credits run short, senders wait."
                ),
                technical=(
                    "Per-link, per-VL credit initialization: receivers "
                    "advertise buffer capacity, senders transmit strictly "
                    "against held credits. Loss is unexpressible at the "
                    "link layer — the zero counter is structural, not "
                    "reactive. The cost surfaces as sender stalls under "
                    "credit exhaustion, visible later at the burst step."
                ),
                expert=(
                    "Per-VL credit init. Tx strictly against credits; loss "
                    "unexpressible. Cost = stalls, shown at burst."
                ),
            ),
            active_regions=_spines() + _leaves() + _endpoints() + ["optics"],
            fabric_tbps=0,
            peak_link_percent=0,
            allreduce_gbps=0,
            elapsed_seconds=180,
            cycle_cost=2,
        ),
        FabricState(
            step=5,
            phase="ready",
            label="Fabric programmed and idle — the manager steps aside",
            description=L(
                novice=(
                    "The network is complete: mapped, programmed, and "
                    "governed by the credit rule — and idle, because the "
                    "computers have not started work. Notice what is no "
                    "longer lit: the brain. The subnet manager wrote the "
                    "map and the routes, and then stepped out of the way — "
                    "data never passes through it, and if it crashed right "
                    "now, traffic would keep flowing on the routes it "
                    "installed. The planner is not a bottleneck, because "
                    "the plan is already in the switches."
                ),
                plain=(
                    "The fabric is programmed and idle — and the manager "
                    "region has gone dark. UFM computed the map and the "
                    "routes, installed them, and stepped off the data "
                    "path: packets flow switch to switch on the tables it "
                    "wrote, and an SM outage stops management, not "
                    "traffic. Same architectural move as the Exascale "
                    "twin's metadata server and the PowerFlex "
                    "coordinator: the brain plans, then leaves."
                ),
                standard=(
                    "The fabric is up: mapped, programmed, credit-armed, "
                    "idle. Notice what is *not* lit anymore — the subnet "
                    "manager. It computed the topology and the routes, "
                    "installed them into the switches, and stepped aside; "
                    "data packets flow switch-to-switch on the tables it "
                    "wrote and never pass through the manager itself. If "
                    "UFM crashed right now, traffic would continue "
                    "unbothered on the installed routes. This is the same "
                    "architectural move the Exascale twin makes with its "
                    "metadata server and PowerFlex makes with its "
                    "coordinator: the brain is central to *planning* and "
                    "absent from *doing* — centralized control, "
                    "distributed data."
                ),
                technical=(
                    "Programmed and idle. SM off the data path: forwarding "
                    "runs on installed LFTs, SM loss degrades management "
                    "(no re-sweeps, no reprogramming) but not traffic. "
                    "Central control plane, distributed data plane — the "
                    "Exascale-MDS/PowerFlex-MDM move, asserted in the "
                    "tests."
                ),
                expert=(
                    "Idle, programmed. SM off the data path (asserted); "
                    "LFTs carry traffic, SM loss ≠ traffic loss."
                ),
            ),
            active_regions=_spines() + _leaves() + ["cooling"],
            fabric_tbps=0,
            peak_link_percent=0,
            allreduce_gbps=0,
            elapsed_seconds=210,
        ),
        FabricState(
            step=6,
            phase="collective",
            label="An all-reduce runs — gradients cross the fabric",
            description=L(
                novice=(
                    "The computers go to work, and the network fills. In "
                    "distributed training, every processor computes its "
                    "own correction to the shared model, and then all of "
                    "them must combine their corrections — everyone "
                    "averaging with everyone — before any of them may "
                    "take the next step. That combining operation floods "
                    "every layer of the network at once, and its speed "
                    "sets the pace of the whole machine: the calculation "
                    "cannot outrun the averaging. Watch the busiest-link "
                    "number — the whole game is keeping every cable "
                    "evenly loaded."
                ),
                plain=(
                    "Training starts and the all-reduce fills the fabric: "
                    "every GPU's gradients combined with every other's, "
                    "racks exchanging partial sums through leaves and "
                    "spines, the routes' spine-balancing keeping links "
                    "within a few percent of each other. The job cannot "
                    "start its next step until the collective completes — "
                    "the fabric's speed is the machine's speed, the beat "
                    "the SN6000 twin also carries."
                ),
                standard=(
                    "Training begins, and the fabric fills with its "
                    "defining traffic pattern: the all-reduce. Every GPU "
                    "has computed gradients that every other GPU needs "
                    "combined — an all-to-all exchange of partial sums, "
                    "racks trading data through leaves and spines with "
                    "the spine-balanced routes keeping every link within "
                    "a few percent of every other. No GPU may begin the "
                    "next training step until the collective completes, "
                    "so the fabric's speed is literally the machine's "
                    "speed. So far this is the classical version: the "
                    "switches carry the numbers and the endpoints do all "
                    "the arithmetic. The next step retires that "
                    "assumption."
                ),
                technical=(
                    "All-reduce at line rate: all-to-all partial-sum "
                    "exchange, two hops, spine-balanced within a few "
                    "percent. Collective completion gates the training "
                    "step. Classical mode — endpoints do the arithmetic, "
                    "switches move bytes; SHARP retires this next step."
                ),
                expert=(
                    "Classical allreduce: all-to-all partial sums, "
                    "balanced fat tree, completion-gated. Switches move "
                    "bytes only — for one more step."
                ),
            ),
            active_regions=_spines() + _leaves() + _endpoints() + ["optics", "cooling"],
            fabric_tbps=36,
            peak_link_percent=64,
            allreduce_gbps=1600,
            elapsed_seconds=240,
            cycle_cost=2,
        ),
        FabricState(
            step=7,
            phase="sharp",
            label="SHARP moves the arithmetic into the switches",
            description=L(
                novice=(
                    "Now the network does something an ordinary network "
                    "cannot: it starts doing the mathematics itself. "
                    "Instead of every processor sending its numbers to be "
                    "added elsewhere, the switches add the numbers as "
                    "they pass through, and send onward only the sums. "
                    "Look at the two meters move in opposite directions: "
                    "traffic crossing the network drops, because sums are "
                    "smaller than the numbers that made them, while the "
                    "speed of useful work rises. The network stopped "
                    "being a road and became part of the calculator."
                ),
                plain=(
                    "The fabric starts computing. SHARP — in-network "
                    "aggregation in the switch ASICs — adds the gradient "
                    "streams as they pass through, forwarding only "
                    "partial sums up the tree and the result back down. "
                    "The two counters cross: raw fabric traffic falls "
                    "(sums are smaller than their inputs, data crosses "
                    "once instead of twice) while effective all-reduce "
                    "throughput rises. The switch stopped moving the "
                    "numbers and started adding them."
                ),
                standard=(
                    "The fabric begins doing arithmetic. SHARP (Scalable "
                    "Hierarchical Aggregation and Reduction Protocol) "
                    "puts reduction engines in the switch ASICs "
                    "themselves: as gradient streams pass through a "
                    "leaf, the switch *adds them together* and forwards "
                    "only the partial sum up the tree; the spines "
                    "combine partial sums and send the single result "
                    "back down. Watch the two counters move in opposite "
                    "directions — raw fabric traffic falls, because "
                    "sums are smaller than their inputs and the data "
                    "crosses the fabric once instead of twice, while "
                    "the effective all-reduce rate the job observes "
                    "rises. This is the capability InfiniBand holds "
                    "that no amount of Ethernet speed matches in kind: "
                    "the network stopped carrying the computation and "
                    "joined it."
                ),
                technical=(
                    "SHARP v4: reduction trees in the switch ASICs — "
                    "leaves aggregate member streams, spines merge "
                    "partial sums, one result multicast down. "
                    "fabric_tbps falls while allreduce_gbps rises "
                    "(asserted): single traversal, in-fabric add. The "
                    "qualitative capability Ethernet fabrics lack."
                ),
                expert=(
                    "SHARP: in-ASIC reduction trees. Tbps down, "
                    "effective allreduce up (asserted). One traversal. "
                    "Not a speed grade — a capability."
                ),
            ),
            active_regions=_spines() + _leaves() + _endpoints(),
            fabric_tbps=22,
            peak_link_percent=55,
            allreduce_gbps=2900,
            elapsed_seconds=270,
            cycle_cost=2,
        ),
        FabricState(
            step=8,
            phase="burst",
            label="Incast burst — senders wait for credits, nothing is lost",
            description=L(
                novice=(
                    "The stress test. A moment comes when many computers "
                    "all need to send to the same place at once — far "
                    "more data than the receiving link can take. An "
                    "ordinary network would overflow and throw data "
                    "away, then spend a long time retransmitting. Here, "
                    "the receiver simply stops granting permission, and "
                    "the senders pause — for microseconds — until space "
                    "opens. The waiting meter is the honest part of this "
                    "story: this network does make senders wait. But "
                    "the lost-data meter stays at zero, because losing "
                    "was never possible, and a brief pause is vastly "
                    "cheaper than a single loss that stalls every "
                    "processor in the machine."
                ),
                plain=(
                    "The stress test: an incast — many senders, one "
                    "receiver, more offered data than the link can take. "
                    "Ethernet's failure mode is overflow, drop, "
                    "retransmit; here the receiver simply stops granting "
                    "credits and the senders pause for microseconds "
                    "until buffers drain. The stall counter goes nonzero "
                    "— the honest price, and the only step where it does "
                    "— while packets-sent-without-credit stays zero, "
                    "because the link layer cannot express the "
                    "violation. Waiting is recoverable in microseconds; "
                    "a drop stalls every GPU in the job."
                ),
                standard=(
                    "The stress test arrives: an incast, many senders "
                    "converging on one receiver at once, offering more "
                    "data than its link can accept. This is the moment "
                    "the SN6000 twin meets with ECN marks and priority "
                    "pauses — Ethernet reacting fast enough to avoid "
                    "the drop its nature defaults to. Here the "
                    "mechanics are almost anticlimactic: the receiver "
                    "stops granting credits, so the senders stop "
                    "sending, hold their data for some microseconds, "
                    "and resume as buffers drain. The stall counter "
                    "goes nonzero — the only step in the trace where "
                    "it does, and the honest cost of the design — "
                    "while the packets-sent-without-credit counter "
                    "stays at zero, not survived but structurally "
                    "incapable of moving. A microsecond stall is "
                    "recoverable noise; one dropped packet would stall "
                    "every GPU in the job through a retransmission "
                    "timeout."
                ),
                technical=(
                    "Incast: offered load exceeds the hot receiver's "
                    "link. Credits exhaust; senders stall (the only "
                    "nonzero stall_micros_per_sec step — asserted) and "
                    "resume as buffers drain. packets_sent_without_credit "
                    "stays 0 structurally. Peak link ≥95% (asserted): "
                    "the claim is exercised under stress, not at idle. "
                    "Contrast: reactive ECN/PFC vs constructive "
                    "credits."
                ),
                expert=(
                    "Incast: credits exhaust, senders stall (only "
                    "nonzero-stall step), zero uncredited tx. Peak ≥95%. "
                    "Constructive, not reactive."
                ),
            ),
            active_regions=_spines() + _leaves() + _endpoints() + ["optics"],
            fabric_tbps=38,
            peak_link_percent=97,
            stall_micros_per_sec=1800,
            allreduce_gbps=2600,
            elapsed_seconds=300,
            cycle_cost=2,
        ),
        FabricState(
            step=9,
            phase="steady",
            label="The training loop settles — programmed, lossless, computing",
            description=L(
                novice=(
                    "The machine finds its rhythm: compute, combine, "
                    "step, again — thousands of times an hour, for "
                    "weeks. The burst has passed, the waiting meter is "
                    "back to zero, the switches are still doing part of "
                    "the arithmetic, and the lost-data meter has never "
                    "moved. Step back and the shape of this network is "
                    "visible: mapped and programmed by one brain that "
                    "then got out of the way, forbidden by construction "
                    "from losing anything, and doing some of the "
                    "mathematics itself. That is what a network built "
                    "for one enormous calculation looks like."
                ),
                plain=(
                    "The training loop settles: compute, all-reduce, "
                    "step, repeat — for weeks. Stalls back to zero, "
                    "SHARP still adding in-fabric, the uncredited-send "
                    "counter never moved. The architecture in one "
                    "sentence: programmed by a central brain that left "
                    "the data path, lossless by construction rather "
                    "than by vigilance, and computing as it carries — "
                    "the fabric TACC's Horizon names, delivered in "
                    "Dell's IRSS racks."
                ),
                standard=(
                    "The training loop settles into its rhythm: "
                    "compute, all-reduce, step, repeat — thousands of "
                    "iterations a day for weeks. The burst has drained, "
                    "the stall counter is back at zero, SHARP is still "
                    "doing the arithmetic in the switches, and the "
                    "packets-sent-without-credit counter has never "
                    "moved. Step back and read the whole architecture "
                    "at once: a fabric mapped and programmed by one "
                    "central brain that then left the data path, "
                    "lossless because permission precedes transmission "
                    "on every link, computing as it carries. That is "
                    "the interconnect TACC's Horizon names — "
                    "Quantum-X800 joining Dell IRSS racks of Grace "
                    "Blackwell nodes — and the reason academic HPC "
                    "never left InfiniBand: the machine is one job, "
                    "and this is what a network shaped like one job "
                    "looks like."
                ),
                technical=(
                    "Steady state: collective-dominated load, stalls 0, "
                    "SHARP resident, uncredited sends 0 for the whole "
                    "trace. Architecture summary: central SM (off data "
                    "path), constructive losslessness, in-network "
                    "compute. The Horizon interconnect: Quantum-X800 "
                    "over Dell IRSS Grace Blackwell racks."
                ),
                expert=(
                    "Steady: stalls 0, SHARP resident, uncredited 0 "
                    "throughout. Central SM off-path, constructive "
                    "lossless, in-net compute. Horizon's fabric."
                ),
            ),
            active_regions=_spines() + _leaves() + _endpoints() + ["optics", "cooling"],
            fabric_tbps=30,
            peak_link_percent=62,
            allreduce_gbps=2900,
            elapsed_seconds=360,
        ),
    ]
