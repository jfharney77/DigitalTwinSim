"""The narrated tour of the SN6000 AI fabric — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: eight beats that
move a camera across the leaf/spine map, peel it from the switches you can
rack and cable down to the optics between them and the control plant under
them, pin the fabric trace at the moments that carry the story, and narrate
each one. The frontend player owns the clock; nothing here knows about time,
IO or the web (AST-checked in ``tests/test_tour.py``, the same rule as
``engine.py``).

The signature beat is ``zero-drops-under-stress``: the congestion step, where
the busiest link is driven to 98% and ``dropped_packets`` still reads zero.
Every claim the scripts make is one ``engine.py``, ``anatomy.py`` and
``tests/test_engine.py`` already make; the trace index each beat pins is the
step whose description says the same thing.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``FabricAnatomy`` is unchanged:

    0  the boxes you rack and cable: spines, leaves, GPU racks
    1  the optics layer the links run through
    2  the plant beneath the fabric: congestion control & telemetry,
       liquid cooling, fabric management
"""

from __future__ import annotations

from twinkit.tour import (
    CameraTarget,
    Tour,
    TourPhoto,
    TourResponse,
    TourSource,
    TourStep,
    camera_around,
    whole_map,
)

from .leveling import L
from .models import FabricAnatomy

#: The step the tests pin: the fabric's one idea lives here.
SIGNATURE_STEP_ID = "zero-drops-under-stress"

_SWITCHES = 0
_OPTICS = 1
_PLANT = 2


def layer_map(anatomy: FabricAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    outside = {"spine", "leaf", "endpoint"}
    layers: dict[str, int] = {}
    for region in anatomy.regions:
        if region.kind in outside:
            layers[region.id] = _SWITCHES
        elif region.kind == "optics":
            layers[region.id] = _OPTICS
        else:
            layers[region.id] = _PLANT
    return layers


def _ids(anatomy: FabricAnatomy, *kinds: str) -> list[str]:
    return [r.id for r in anatomy.regions if r.kind in kinds]


def _photos() -> list[TourPhoto]:
    return [
        TourPhoto(
            id="fabric",
            url="/sn6000-fabric.svg",
            caption=(
                "A leaf/spine AI fabric: every leaf connects to every spine, so "
                "any GPU rack reaches any other in two hops."
            ),
            credit="Schematic illustration by this project — not a Dell product image",
        ),
    ]


def build_tour(anatomy: FabricAnatomy) -> Tour:
    """The SN6000 tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 2.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    switches = _ids(anatomy, "spine", "leaf")
    racks = _ids(anatomy, "endpoint")
    mesh = switches + racks

    steps = [
        TourStep(
            id="mesh-from-above",
            title="Every leaf reaches every spine",
            script=L(
                novice=(
                    "This is not one switch but a small network built from "
                    "several of them, seen from above. A switch is the box that "
                    "passes data between computers. Along the top are two spine "
                    "switches. In the middle are four leaf switches, one on top "
                    "of each rack of GPUs, the graphics processors that train AI "
                    "models. Every leaf is cabled to every spine. That shape, "
                    "called leaf/spine, means any rack can reach any other rack "
                    "in exactly two hops. Equal distance matters because the "
                    "GPUs work in lockstep, and the whole team waits for the "
                    "slowest one. Everything is cabled, and still dark."
                ),
                standard=(
                    "This twin draws not one switch but the fabric several of "
                    "them form: two spines across the top, four leaf switches "
                    "below them, and under each leaf the GPU rack it serves. "
                    "Every leaf connects to every spine, so any rack reaches any "
                    "other in exactly two hops. That uniform distance is the "
                    "point of leaf/spine: a collective operation finishes only "
                    "when its slowest participant does. The switches are racked, "
                    "cabled and dark."
                ),
                expert=(
                    "Two-tier leaf/spine: 2 spines, 4 leaves, 4 GPU racks, full "
                    "leaf-to-spine mesh. Any pair in two hops. Dark."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=mesh,
            layer_reveal=_SWITCHES,
            trace_cursor=0,
            duration_ms=26_000,
            photo_id="fabric",
        ),
        TourStep(
            id="one-sn6000",
            title="One SN6000, and the optics beside it",
            script=L(
                novice=(
                    "Up close, one of the six switches. All six, the two spines "
                    "and the four leaves, are the same model: a Dell PowerSwitch "
                    "SN6000. According to Dell's spec sheet, each has ports that move "
                    "1.6 terabits per second, and a chip, NVIDIA Spectrum-6, that "
                    "can switch up to 409.6 terabits per second in total. They "
                    "are switching on now and loading their network operating "
                    "system, the software that runs a switch; the E3200 twin "
                    "walks through that start-up in detail. We have also peeled "
                    "back a layer to show the optics, the parts that turn "
                    "electrical signals into light for the cables. They come two "
                    "ways: pluggable modules you slide into each port, or "
                    "co-packaged optics, built onto the switch chip itself, "
                    "which saves a great deal of power. No cable carries data "
                    "yet."
                ),
                standard=(
                    "Up close, one of the six switches; spines and leaves are "
                    "the same model, a Dell PowerSwitch SN6000: NVIDIA Spectrum-6 "
                    "silicon, 1.6 Tb/s ports and up to 409.6 Tb/s of switching "
                    "capacity, per Dell's spec sheet. Here they power on and boot "
                    "their network operating system (NOS), the open-networking "
                    "path the E3200 twin walks through in detail. The peeled "
                    "layer is the optics: pluggable transceivers, or co-packaged "
                    "optics (CPO), where the optical engine sits on the switch "
                    "package itself, shortening the electrical path and cutting "
                    "power. No link is up yet."
                ),
                expert=(
                    "Spine 1 close-up. SN6000: Spectrum-6, 1.6 Tb/s ports, "
                    "409.6 Tb/s (spec sheet). "
                    "NOS booting. Optics: pluggable or CPO. No links up."
                ),
            ),
            # Close on spine 1 and the optics under it; spine 2 mirrors it,
            # and the narration says it is looking at one of six.
            camera=CameraTarget(x=0, y=0, w=58, h=36),
            region_ids=["spine-s1", "spine-s2", "optics"],
            layer_reveal=_OPTICS,
            trace_cursor=1,
            duration_ms=30_000,
        ),
        TourStep(
            id="link-training",
            title="Every link trains, the longest stage",
            script=L(
                novice=(
                    "Now every cable wakes up, spine to leaf and leaf to rack. "
                    "At 1.6 terabits per second, a link cannot simply switch on. "
                    "Each end tunes its signal, adds error correction so damaged "
                    "bits can be repaired, and lines up its lanes with the other "
                    "end. This is the slowest part of bringing the network up, "
                    "so the timeline lingers here. It is also where the choice "
                    "of optics matters: at these speeds a network is as much an "
                    "analog engineering problem as a digital one."
                ),
                standard=(
                    "Every leaf-to-spine and leaf-to-rack link negotiates and "
                    "tunes: signal equalization, forward error correction (FEC), "
                    "lane alignment, at 1.6 Tb/s per port. This is the longest "
                    "stage in the trace, which is why playback dwells on it, and "
                    "it is where the optics choice shows up. At these rates the "
                    "network is as much an analog engineering problem as a "
                    "digital one."
                ),
                expert=(
                    "Link training on every port: equalization, FEC, lane "
                    "alignment at 1.6 Tb/s. Longest stage, max dwell."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=mesh + ["optics"],
            layer_reveal=_OPTICS,
            trace_cursor=2,
            duration_ms=30_000,
        ),
        TourStep(
            id="one-fabric",
            title="Six switches become one fabric",
            script=L(
                novice=(
                    "With the cables up, the switches find each other and agree "
                    "on routes. Each leaf learns it has more than one equally "
                    "good way to reach every other leaf: one through each spine. "
                    "Those spare routes are not only there in case something "
                    "breaks. Later, the network will use them to spread out "
                    "traffic that piles up in one place. From here on, six "
                    "separate boxes behave like one network with one set of "
                    "rules."
                ),
                standard=(
                    "The switches discover each other and routing converges. "
                    "Each leaf learns it has multiple equal-cost paths to every "
                    "other leaf, one through each spine. Those redundant paths "
                    "are not merely failover; they are the raw material adaptive "
                    "routing will use later to spread a congested flow. Six "
                    "independent switches start behaving like one fabric with a "
                    "single forwarding policy."
                ),
                expert=(
                    "Routing converges: equal-cost paths via each spine. Six "
                    "switches, one forwarding policy."
                ),
            ),
            camera=frame(*switches, "mgmt", "telemetry"),
            region_ids=switches + ["mgmt", "telemetry"],
            layer_reveal=_PLANT,
            trace_cursor=3,
            duration_ms=26_000,
        ),
        TourStep(
            id="all-reduce",
            title="Every GPU exchanging at once",
            script=L(
                novice=(
                    "A training step ends, and every GPU in every rack shares "
                    "what it has learned with all the others at the same moment. "
                    "This is called an all-reduce: each GPU adds its piece, and "
                    "each must receive the combined result before anyone can "
                    "start the next step. We are looking at two racks here; the "
                    "other two do exactly the same. The network carries about 18 "
                    "terabits per second, an illustrative figure, and it copes "
                    "easily. What matters is not the average speed but when the "
                    "last GPU finishes."
                ),
                standard=(
                    "A training step ends and the fleet performs an all-reduce, "
                    "a collective operation: every GPU contributes its gradients "
                    "and every GPU must receive the summed result before the "
                    "next step may begin. The pattern is synchronized, "
                    "all-to-all and bursty, and it repeats thousands of times an "
                    "hour. Two of the four racks are in view; the other two do "
                    "the same. The fabric carries 18 Tb/s comfortably "
                    "(illustrative). "
                    "The clock that matters is when the last GPU finishes."
                ),
                expert=(
                    "All-reduce, racks 1-2 shown: synchronized, all-to-all, "
                    "bursty. ~18 Tb/s (illustrative). Tail latency governs."
                ),
            ),
            # Close on racks 1 and 2 and their leaves; racks 3 and 4 mirror
            # them. x+w stops short of leaf 3 (x=50) once the renderer's
            # 2.5-unit margin is added, so no block is cut in half.
            camera=CameraTarget(x=0, y=18, w=46, h=28.5),
            region_ids=mesh,
            layer_reveal=_PLANT,
            trace_cursor=5,
            duration_ms=28_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="98% on one link, and nothing dropped",
            script=L(
                novice=(
                    "This is the moment the whole network exists for. Traffic "
                    "piles up many-to-one, the way it does when a checkpoint "
                    "lands on storage, and one link fills to 98 percent, an "
                    "illustrative figure, with "
                    "its buffers, the waiting space inside the switch, filling "
                    "behind it. This pile-up is called incast. An ordinary "
                    "network would start throwing data away here and ask for it "
                    "again later, and every GPU in the job would sit waiting for "
                    "that one late piece. The SN6000 is built not to throw "
                    "anything away. It marks passing data so the senders slow down "
                    "early, called explicit congestion notification, and it can "
                    "pause one kind of traffic for a moment instead of dropping "
                    "it, called priority flow control. Watch the dropped-packet "
                    "counter. In this twin it stays at zero, even at the worst "
                    "moment, and that one number is the whole promise."
                ),
                standard=(
                    "The hard moment. Traffic converges many-to-one, a checkpoint "
                    "landing on the storage fabric or a reduction collapsing "
                    "toward one rank, and a "
                    "single link hits 98% (illustrative) with buffers filling "
                    "behind it. This is incast, where ordinary Ethernet would "
                    "start discarding frames. The SN6000 is designed not to: explicit "
                    "congestion notification (ECN) marks packets so senders slow "
                    "before buffers overflow, and priority flow control (PFC) "
                    "pauses one traffic class instead of dropping it. The "
                    "In this twin the dropped-packet counter stays at zero under "
                    "genuine stress. "
                    "That single number is the product claim, because one "
                    "retransmission would stall every GPU in the job."
                ),
                expert=(
                    "Incast drives the hot link to 98%; ECN marks, PFC "
                    "pauses, drops stay 0. Lossless proven under stress, not at "
                    "idle."
                ),
            ),
            # The whole two-hop path plus the reflexes acting on it: that is
            # the whole map (a padded frame only clipped its right border).
            camera=whole_map(anatomy),
            region_ids=mesh + ["telemetry"],
            layer_reveal=_PLANT,
            trace_cursor=6,
            duration_ms=42_000,
        ),
        TourStep(
            id="adaptive-reroute",
            title="The work spreads instead of shrinking",
            script=L(
                novice=(
                    "Now the network fixes the pile-up without losing anything. "
                    "Sensors on the busy link report the crowding, and the "
                    "switches move some of the traffic onto the spare routes "
                    "through the other spine, the ones they found earlier. This "
                    "is called adaptive routing. The busy link cools from 98 to "
                    "71 percent, while the total amount the network carries "
                    "goes up, to 31 terabits per second, again illustrative. "
                    "The work did not shrink. It spread out. Ordinary networks "
                    "tie each flow of data to one route for its whole life, so "
                    "an unlucky collision stays unlucky."
                ),
                standard=(
                    "Telemetry from the congested link feeds adaptive routing, "
                    "which moves flows onto the alternate equal-cost paths the "
                    "topology has held in reserve since routing converged. The "
                    "hot link relaxes from 98% to 71% while total throughput "
                    "rises to 31 Tb/s (illustrative): the work did not shrink, "
                    "it spread. Conventional hashing pins a flow to one path for "
                    "its lifetime, so an unlucky collision stays unlucky for the "
                    "whole job."
                ),
                expert=(
                    "Adaptive routing: hot link 98% to 71%, fabric 24 to 31 Tb/s "
                    "(illustrative). Load-aware, not static ECMP hashing."
                ),
            ),
            camera=frame(*switches, "telemetry", "mgmt"),
            region_ids=switches + ["telemetry", "mgmt"],
            layer_reveal=_PLANT,
            trace_cursor=7,
            duration_ms=30_000,
        ),
        TourStep(
            id="reassemble",
            title="The training loop's heartbeat",
            script=L(
                novice=(
                    "The layers go back on. From here the job settles into a "
                    "rhythm that runs for weeks: compute, share results, save a "
                    "checkpoint, repeat. The network soaks up every burst and "
                    "never drops a packet, and nobody notices it at all, which "
                    "is the best thing anyone says about a network. The GPU "
                    "racks themselves are the XE9712 twin, the IR7000 twin "
                    "cools them, and Quantum-X800 is the same job done with "
                    "InfiniBand instead of Ethernet."
                ),
                standard=(
                    "Reassembled and in steady state: compute, all-reduce, "
                    "checkpoint, repeat, with the fabric absorbing each burst and "
                    "never dropping a packet. With the XE9712 racks at its edge "
                    "(NVLink stops at their wall; this fabric carries traffic "
                    "past it), the IR7000 loop cooling them, and the Exascale "
                    "storage feeding them, it completes the AI factory. The "
                    "Quantum-X800 twin makes the InfiniBand counterargument."
                ),
                expert=(
                    "Steady state: compute, all-reduce, checkpoint; zero drops "
                    "throughout. See XE9712, IR7000, Exascale, Quantum-X800."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[],
            layer_reveal=_SWITCHES,
            trace_cursor=8,
            duration_ms=24_000,
        ),
    ]

    return Tour(
        id="sn6000-tour",
        title="An AI fabric that refuses to drop",
        intro=L(
            novice=(
                "A guided walk through the network as it comes up and carries "
                "its first training step, narrated beat by beat. Sit back and "
                "watch, or pause and click anything to look closer; the tour "
                "waits for you."
            ),
            standard=(
                "A narrated walk through the fabric as it comes up and carries a "
                "training step's collective. Watch it play, or pause and "
                "explore; Resume tour brings the camera back."
            ),
            expert="Narrated fabric bring-up and collective. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=_photos(),
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
