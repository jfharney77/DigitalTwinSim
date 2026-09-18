"""The narrated tour of the Quantum-X800 InfiniBand fabric — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: nine beats that
move a camera across the fat tree, peel it down to the optics and cooling
plant under the switches, pin the fabric trace at the moments that carry the
story, and narrate each one. The frontend player owns the clock; nothing here
knows about time, IO or the web (AST-checked in ``tests/test_tour.py``, the
same rule as ``engine.py``).

The signature beat is ``credits-before-bytes``: a receiver grants buffer
credits before any sender may transmit, so ``packets_sent_without_credit``
is zero by construction. Every claim the scripts make is one the engine and
the anatomy already make — each beat's ``trace_cursor`` is the trace step
whose description says the same thing.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``FabricAnatomy`` is unchanged:

    0  the topology as drawn: subnet manager, spines, leaves, GPU racks
    1  the physical plant beneath it: OSFP optics and fibre, liquid cooling
"""

from __future__ import annotations

from twinkit.tour import (
    CameraTarget,
    Tour,
    TourResponse,
    TourSource,
    TourStep,
    camera_around,
    whole_map,
)

from .leveling import L
from .models import FabricAnatomy

#: The step the tests pin: the product's one idea lives here.
SIGNATURE_STEP_ID = "credits-before-bytes"

_TOPOLOGY = 0
_PLANT = 1

SPINES = ["spine-s1", "spine-s2"]
LEAVES = ["leaf-l1", "leaf-l2", "leaf-l3", "leaf-l4"]
RACKS = ["endpoint-e1", "endpoint-e2", "endpoint-e3", "endpoint-e4"]


def layer_map(anatomy: FabricAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    plant = {"optics", "cooling"}
    return {
        r.id: (_PLANT if r.kind in plant else _TOPOLOGY) for r in anatomy.regions
    }


def build_tour(anatomy: FabricAnatomy) -> Tour:
    """The Quantum-X800 tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 3.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    steps = [
        TourStep(
            id="fat-tree-from-above",
            title="A fat tree, and a small box beside it",
            script=L(
                novice=(
                    "This is an InfiniBand network, the kind of network "
                    "supercomputers use to join thousands of graphics "
                    "processors (GPUs) into one machine. At the bottom are four "
                    "racks of GPUs. Each rack plugs into a switch above it, "
                    "called a leaf, and every leaf is wired to both switches at "
                    "the top, called spines. That shape is a fat tree: any two "
                    "racks are exactly two hops apart. Now look at the small "
                    "box at the top left. It is the subnet manager, the "
                    "network's planner. It is drawn small and off to the side "
                    "on purpose, and by the end of the tour you will see why. "
                    "Everything is cabled, and everything is still dark."
                ),
                standard=(
                    "This is an NVIDIA Quantum-X800 InfiniBand fabric, the "
                    "interconnect TACC's Horizon names, drawn as a two-tier fat "
                    "tree. Four GPU racks sit at the bottom, each wired to its "
                    "leaf (top-of-rack) switch; every leaf is wired to both "
                    "spines, so any two racks are two hops apart. The small box "
                    "beside the spines is the subnet manager (SM), the fabric's "
                    "central brain, drawn small and off to one side because "
                    "data never passes through it. The fabric is cabled and dark."
                ),
                expert=(
                    "Quantum-X800 XDR fat tree: 2 spines, 4 leaves, 4 GPU racks, "
                    "two hops any-to-any. SM beside the spine tier, off the data "
                    "path. Cabled, dark."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["manager", *SPINES],
            layer_reveal=_TOPOLOGY,
            trace_cursor=0,
            duration_ms=26_000,
        ),
        TourStep(
            id="one-brain-whole-map",
            title="One brain sweeps the whole fabric",
            script=L(
                novice=(
                    "The switches have power now, and a liquid cooling loop is "
                    "carrying their heat away. We have peeled back to show the "
                    "cables and the cooling underneath. The subnet manager wakes "
                    "up and walks the network one hop at a time, finding every "
                    "switch, every network card and every cable, and giving each "
                    "one an address. In an ordinary Ethernet network, every "
                    "switch works this out for itself by chatting with its "
                    "neighbours. Here, one planner holds the complete map."
                ),
                standard=(
                    "Power is on and the switches' cold plates feed the liquid "
                    "loop. With the optics and cooling plant revealed, the "
                    "subnet manager, here NVIDIA UFM (Unified Fabric Manager), "
                    "sweeps the fabric hop by hop and builds a complete map: "
                    "every switch, every ConnectX adapter, every cable, each "
                    "given a fabric-local address. Ethernet discovers its "
                    "topology by distributed gossip; InfiniBand hands the whole "
                    "graph to one authority."
                ),
                expert=(
                    "SM (UFM) sweep: full topology discovery, fabric-local "
                    "addressing. Centralized graph, not distributed protocol "
                    "convergence."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["manager", *SPINES, *LEAVES, *RACKS, "optics"],
            layer_reveal=_PLANT,
            trace_cursor=2,
            duration_ms=26_000,
        ),
        TourStep(
            id="routes-computed-centrally",
            title="Every route computed before a byte moves",
            script=L(
                novice=(
                    "This is the slowest part of starting up, so the timeline "
                    "lingers here. With the map finished, the subnet manager "
                    "works out a route for every possible pair of GPU "
                    "network ports, spreading them across both spines so no single path gets "
                    "crowded. Then it writes those routes into every switch. No "
                    "data moves until this is done. Ethernet settles its routes "
                    "gradually while it runs; InfiniBand plans them all first "
                    "and then programs the switches."
                ),
                standard=(
                    "The longest stage of bring-up, so playback dwells here. "
                    "The subnet manager computes the forwarding table for every "
                    "switch, each source-destination pair given a path and "
                    "balanced across the spines so the fat tree's full "
                    "cross-section is used, then installs the tables in "
                    "hardware. Where the SN6000 Ethernet fabric converges, this "
                    "fabric is programmed: no data packet moves until the "
                    "central computation is in place."
                ),
                expert=(
                    "Central route computation, spine-balanced, installed "
                    "before any traffic. Longest stage (max cycle cost). "
                    "Programmed, not converged."
                ),
            ),
            camera=frame("manager", *SPINES, *LEAVES, pad=2.0),
            region_ids=["manager", *SPINES, *LEAVES],
            layer_reveal=_PLANT,
            trace_cursor=3,
            duration_ms=28_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="No packet without a credit",
            script=L(
                novice=(
                    "This is the most important moment in the tour. On every "
                    "cable, the switch or card at the receiving end tells the "
                    "sender how much free space it has to hold incoming data. "
                    "Each unit of that space is called a credit. A sender may "
                    "only send data it holds credits for, and gets them back as "
                    "the receiver empties its space. Permission always comes "
                    "before sending. So the counter of packets sent without a "
                    "credit will stay at zero for the rest of the tour. That is "
                    "not because the network reacts quickly when things get "
                    "busy. It is because there is simply no way to send data "
                    "into a full space. The price shows up later, somewhere "
                    "else: when credits run short, senders have to wait."
                ),
                standard=(
                    "The mechanism this twin exists for arms itself. On every "
                    "link, the receiver advertises its free buffer space as "
                    "credits, and the sender may transmit only against credits "
                    "it holds, getting them back as the receiver drains. This "
                    "is credit-based flow control: permission precedes "
                    "transmission, on every link, always. The "
                    "sent-without-credit counter reads zero from here to the "
                    "end, not because the fabric reacts in time, the SN6000 "
                    "Ethernet story, but because the link layer cannot express "
                    "a send into a full buffer. The cost will show up in a "
                    "different column: senders wait."
                ),
                expert=(
                    "Credit-based link-level flow control. Receiver "
                    "grants buffer credits; sender transmits only against held "
                    "credits. Sent-without-credit is zero by construction, not "
                    "by reaction. Cost: sender stall."
                ),
            ),
            camera=frame(*SPINES, *LEAVES, *RACKS, "optics", pad=2.0),
            region_ids=[*SPINES, *LEAVES, *RACKS, "optics"],
            layer_reveal=_PLANT,
            trace_cursor=4,
            duration_ms=40_000,
        ),
        TourStep(
            id="manager-steps-aside",
            title="The brain leaves the data path",
            script=L(
                novice=(
                    "The network is ready: mapped, programmed and armed with "
                    "credits, but not yet busy. Look at the small box at the "
                    "top left. It has gone dark. The subnet manager did its "
                    "planning and then stepped aside. Data moves from switch to "
                    "switch using the routes it wrote, and never passes through "
                    "the manager itself. If it crashed right now, the traffic "
                    "would keep flowing. The Exascale storage twin and the "
                    "PowerFlex twin make the same move: the planner is central "
                    "to planning and absent from the actual work."
                ),
                standard=(
                    "The fabric is up and idle, and the subnet manager is no "
                    "longer lit. It mapped the topology, installed the routes "
                    "and stepped aside; data packets flow switch to switch on "
                    "the tables it wrote and never pass through it. If UFM "
                    "crashed now, traffic would continue on the installed "
                    "routes. It is the move the Exascale twin makes with its "
                    "metadata server and PowerFlex with its coordinator: "
                    "centralized control, distributed data."
                ),
                expert=(
                    "Fabric ready, idle. SM dark: absent from every traffic "
                    "step. SM loss does not stop forwarding. Centralized "
                    "control, distributed data."
                ),
            ),
            # Close on the top-left corner: the dark manager beside spine 1,
            # with the lit leaves it programmed framed whole below it.
            camera=frame("manager", "spine-s1", "leaf-l1", "leaf-l2", pad=3.0),
            region_ids=["spine-s1", "leaf-l1", "leaf-l2"],
            layer_reveal=_PLANT,
            trace_cursor=5,
            duration_ms=26_000,
        ),
        TourStep(
            id="the-all-reduce",
            title="Gradients cross the fabric",
            script=L(
                novice=(
                    "Training starts. Each GPU has worked out its share of the "
                    "answer, and every GPU needs everyone's shares added "
                    "together. That exchange is called an all-reduce. Data "
                    "flows up through the leaves and spines and back down to "
                    "every rack. No GPU can start its next step until the "
                    "exchange finishes, so the network's speed is the machine's "
                    "speed. For now, the switches only carry the numbers and "
                    "the GPUs do all the adding. On this illustrative timeline "
                    "the fabric carries about 36 terabits per second."
                ),
                standard=(
                    "Training begins with the fabric's defining traffic "
                    "pattern, the all-reduce: every GPU's partial gradients "
                    "combined and returned to every GPU, racks trading data "
                    "through leaves and spines on the balanced routes. No GPU "
                    "starts the next step until the collective completes, so "
                    "the fabric's speed is the machine's speed. So far the "
                    "switches carry the numbers and the endpoints do the "
                    "arithmetic, about 36 Tb/s of fabric traffic on this "
                    "illustrative trace."
                ),
                expert=(
                    "All-reduce over the fat tree, host-side reduction. "
                    "Illustrative: 36 Tb/s fabric, 1,600 Gb/s effective "
                    "collective, peak link 64%."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[*SPINES, *LEAVES, *RACKS, "optics"],
            layer_reveal=_PLANT,
            trace_cursor=6,
            duration_ms=26_000,
        ),
        TourStep(
            id="sharp-counters-cross",
            title="The switches start doing the arithmetic",
            script=L(
                novice=(
                    "Now the switches join in the maths. A feature called "
                    "SHARP (Scalable Hierarchical Aggregation and Reduction "
                    "Protocol) lets each leaf add up the numbers from its rack "
                    "as they pass through, and send only the total upward. The "
                    "spines add those totals and send one answer back down. "
                    "Watch two numbers move in opposite directions: the traffic "
                    "on the network falls, from about 36 to 22 terabits per "
                    "second in this illustration, while the speed the training "
                    "job actually sees rises, from 1,600 to 2,900 gigabits per "
                    "second."
                ),
                standard=(
                    "SHARP (Scalable Hierarchical Aggregation and Reduction "
                    "Protocol) puts adding engines in the switch ASICs, the "
                    "switches' own chips. A "
                    "leaf adds its rack's gradient streams and forwards only "
                    "the partial sum; the spines combine the partial sums and "
                    "send one result down. The counters cross: fabric traffic "
                    "falls, 36 to 22 Tb/s here, because sums are smaller than "
                    "their inputs, while the effective all-reduce rate rises, "
                    "1,600 to 2,900 Gb/s. Both figures are illustrative."
                ),
                expert=(
                    "SHARP in-network reduction: leaf partial sums, spine "
                    "combine. Fabric 36 to 22 Tb/s, all-reduce 1,600 to 2,900 "
                    "Gb/s (illustrative). Counters cross."
                ),
            ),
            camera=frame(*SPINES, *LEAVES, *RACKS, pad=2.0),
            region_ids=[*SPINES, *LEAVES, *RACKS],
            layer_reveal=_PLANT,
            trace_cursor=7,
            duration_ms=28_000,
        ),
        TourStep(
            id="incast-senders-wait",
            title="An incast burst: senders wait, nothing drops",
            script=L(
                novice=(
                    "Here is the stress test. Many senders all aim at one "
                    "receiver at once, more data than its cable can take. This "
                    "is called an incast. The Ethernet twin, the SN6000, "
                    "handles this moment by reacting fast enough, with warning "
                    "marks and pause signals, to avoid throwing data away. "
                    "Here, the receiver simply stops handing out credits, so "
                    "the senders stop and hold their data for a few millionths "
                    "of a second, then carry on. The busiest link hits 97 "
                    "percent and the waiting counter goes above zero for the "
                    "only time in the tour. The counter of packets sent without "
                    "a credit stays at zero. A short wait is harmless; one lost "
                    "packet would hold up every GPU in the job."
                ),
                standard=(
                    "The stress test: an incast, many senders converging on one "
                    "receiver faster than its link can accept. The SN6000 "
                    "Ethernet twin meets this with ECN (Explicit Congestion "
                    "Notification) marks and priority pauses, reacting in time to avoid a drop. Here the "
                    "receiver stops granting credits, senders hold their data "
                    "for microseconds, and resume as buffers drain. The busiest "
                    "link reaches 97% and the stall counter goes nonzero, the "
                    "only step where it does, while sent-without-credit stays "
                    "at zero and the collective keeps progressing."
                ),
                expert=(
                    "Incast: peak link 97%, stall about 1,800 µs/s "
                    "(illustrative), only nonzero stall step. Credits withheld, "
                    "zero sent without credit, collective progresses. Contrast "
                    "SN6000 ECN/PFC."
                ),
            ),
            camera=frame(*SPINES, *LEAVES, *RACKS, "optics", pad=2.0),
            region_ids=[*SPINES, *LEAVES, *RACKS, "optics"],
            layer_reveal=_PLANT,
            trace_cursor=8,
            duration_ms=30_000,
        ),
        TourStep(
            id="programmed-lossless-computing",
            title="Programmed, lossless, computing",
            script=L(
                novice=(
                    "The plant goes back under the switches. The training job "
                    "settles into its rhythm: compute, combine, step, repeat, "
                    "for weeks. The burst has drained and the waiting counter "
                    "is back at zero. Put it all together: one planner mapped "
                    "and programmed the network and then stepped out of the "
                    "way, no data is ever sent without permission, and the "
                    "switches help with the maths as they carry it. The Fabric "
                    "in motion page plays the same timeline step by step."
                ),
                standard=(
                    "Reassembled, and the training loop settles: compute, "
                    "all-reduce, step, repeat. The burst has drained, stalls "
                    "are back at zero, SHARP is still doing the arithmetic, and "
                    "the sent-without-credit counter never moved. The whole "
                    "architecture at once: a fabric mapped and programmed by "
                    "one central brain that then left the data path, lossless "
                    "because permission precedes transmission, computing as it "
                    "carries. The Fabric in motion page plays the same trace "
                    "step by step."
                ),
                expert=(
                    "Steady state: stalls zero, SHARP on, sent-without-credit "
                    "never moved. Programmed by the SM, lossless by credits, "
                    "computing in-network."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[],
            layer_reveal=_TOPOLOGY,
            trace_cursor=9,
            duration_ms=26_000,
        ),
    ]

    return Tour(
        id="quantum-x800-tour",
        title="Inside a Quantum-X800 fabric, as it comes up",
        intro=L(
            novice=(
                "A guided walk through the InfiniBand fabric as it is switched "
                "on, programmed and put to work, narrated beat by beat. Sit "
                "back and watch, or pause and click anything to look closer; "
                "the tour waits for you."
            ),
            standard=(
                "A narrated walk through the fabric from dark switches to a "
                "running training job. Watch it play, or pause and explore; "
                "Resume tour brings the camera back."
            ),
            expert="Narrated bring-up and workload walk-through. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=[],
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: FabricAnatomy) -> TourResponse:
    """The ``GET /api/tour`` payload: the tour plus the layer map and bounds."""
    return TourResponse(
        tour=build_tour(anatomy),
        layers=layer_map(anatomy),
        map_width=anatomy.width,
        map_height=anatomy.height,
    )


# Built once at import, like ANATOMY: importing the module registers the
# narration's reading-level variants, which tests/test_leveling.py relies on.
from .anatomy import ANATOMY  # noqa: E402  (after the builders it feeds)

TOUR_RESPONSE = build_response(ANATOMY)
