"""The narrated tour of the PowerEdge XE9680 — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: nine beats that
move a camera across the 6U chassis from the front (left) to the rear
(right), peel it from the parts you can reach from outside to the HGX
baseboard and, last, the NVSwitch strip in the middle of it, pin the
power-on trace at the moments that carry the story, and narrate each one.
The frontend player owns the clock; nothing here knows about time, IO or the
web (AST-checked in ``tests/test_tour.py``, the same rule as ``engine.py``).

The signature beat is ``domain-stops-at-eight``: the NVSwitch fuse snaps the
NVLink domain from zero to eight GPUs at once, and nothing that follows ever
grows it. Every claim the scripts make is one the engine, the anatomy or
``tests/test_engine.py`` already makes — the trace index named in each beat
is the step whose description says the same thing.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``ServerAnatomy`` is unchanged:

    0  what you reach from outside: NVMe bay and fan wall at the front,
       NICs, iDRAC and PSUs at the rear
    1  under the lid: the HGX field of eight SXM GPUs and the x86 host
    2  the NVSwitch strip on the baseboard, between the GPUs and the NICs
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
from .models import ServerAnatomy

#: The step the tests pin: the product's one idea lives here.
SIGNATURE_STEP_ID = "domain-stops-at-eight"

_OUTSIDE = 0
_LID_OFF = 1
_SWITCH = 2

_GPUS = [f"gpu-g{i}" for i in range(1, 9)]
_NICS = [f"nic-g{i}" for i in range(1, 9)]
_FANS = ["fan-bank-a", "fan-bank-b"]


def layer_map(anatomy: ServerAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    layers: dict[str, int] = {}
    for region in anatomy.regions:
        if region.kind == "nvswitch":
            layers[region.id] = _SWITCH
        elif region.kind in {"gpu", "compute"}:
            layers[region.id] = _LID_OFF
        else:
            layers[region.id] = _OUTSIDE
    return layers


def build_tour(anatomy: ServerAnatomy) -> Tour:
    """The XE9680 tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 2.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    steps = [
        TourStep(
            id="six-u-from-above",
            title="A big server, but still a server",
            script=L(
                novice=(
                    "This is a Dell PowerEdge XE9680, a server built to train "
                    "artificial intelligence. We are looking down on it from "
                    "above, with the front on the left and the back on the "
                    "right. It is tall for a server, six rack units, and heavy, "
                    "but it still slides into an ordinary rack and runs on "
                    "ordinary power, with no water pipes. That ordinariness is "
                    "the plan: the fast connections between its processors stay "
                    "inside this one box, so installing a thousand of them is "
                    "just a thousand everyday rack jobs. It is cabled in, and "
                    "still dark."
                ),
                standard=(
                    "This is the Dell PowerEdge XE9680, an 8-GPU AI training "
                    "server, seen from above with the front on the left. It is "
                    "six rack units (6U) tall and heavy, but it is still a server: it takes a "
                    "standard rack and ordinary facility power, with no "
                    "factory-built cabinet and no building water. That is the "
                    "strategy. Its fast GPU fabric stays inside the chassis, so "
                    "installing a thousand of them is a thousand ordinary rack "
                    "jobs. It is racked, cabled, and dark."
                ),
                expert=(
                    "XE9680, 6U, top-down, front left. Standard rack, facility "
                    "power, no liquid. Scale-up fabric contained in the chassis. "
                    "Racked and dark."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[],
            layer_reveal=_OUTSIDE,
            trace_cursor=0,
            duration_ms=26_000,
        ),
        TourStep(
            id="fan-wall-and-nvme",
            title="Drives in front, a wall of fans behind them",
            script=L(
                novice=(
                    "We lift the lid and look at the front. On the far left is "
                    "a bay of up to eight NVMe drives. NVMe, short for "
                    "Non-Volatile Memory Express, is the fast way for flash "
                    "storage to talk to a processor. Training data waits here "
                    "on its way in, and saved progress lands here on its way "
                    "out. Just behind the drives stands a wall of powerful "
                    "fans, drawn as two banks, top and bottom. There is no "
                    "liquid cooling in this model: moving air alone has to "
                    "carry away the heat of eight very hungry chips."
                ),
                standard=(
                    "With the lid off, the front of the chassis holds two "
                    "things. On the far left, a bay of up to eight hot-swap NVMe "
                    "(Non-Volatile Memory Express) SSDs, where training data "
                    "stages and checkpoints land. Behind it, the fan wall: two "
                    "redundant banks of high-static-pressure, counter-rotating "
                    "fans that pull air through the bay and over the GPU "
                    "heatsinks. This is the air-cooled answer to a question the "
                    "XE9712 rack answers with building water."
                ),
                expert=(
                    "Front: up to 8 NVMe SSDs (staging, checkpoints), then two "
                    "redundant high-static-pressure fan banks. Air-cooled; the "
                    "XE9712 uses facility liquid."
                ),
            ),
            # Close on the upper front: the NVMe bay and fan bank A with their
            # labels, and the top of bank B below. (The map is 100 x 56, so
            # any frame holding both banks' full height is the whole map; a
            # real zoom keeps the labels, which sit at the top of each block.)
            camera=CameraTarget(x=0, y=2, w=60, h=33.6),
            region_ids=["nvme-bay", *_FANS],
            layer_reveal=_LID_OFF,
            trace_cursor=0,
            duration_ms=26_000,
        ),
        TourStep(
            id="hgx-field",
            title="Eight GPUs on one baseboard",
            script=L(
                novice=(
                    "The middle of the box belongs to eight GPUs, the chips "
                    "that do the actual AI arithmetic. They sit on one shared "
                    "circuit board from NVIDIA called HGX, four in the top row "
                    "and four more below. Each one is an SXM module: instead of "
                    "a plug-in card, it is bolted straight onto the board under "
                    "a tall metal heatsink, which lets it draw roughly 700 "
                    "watts, several times what an ordinary card may use. Each "
                    "carries its own very fast memory, called HBM. Power has "
                    "just reached the box and its small management computer is "
                    "awake, but these eight, outlined here, have no power yet."
                ),
                standard=(
                    "The middle of the chassis is the HGX field: eight SXM GPUs "
                    "on one NVIDIA HGX baseboard, four per row. SXM is the "
                    "socketed, high-power form factor, with no card edge and no "
                    "power cable; each module bolts to the board under a tall "
                    "heatsink and can draw on the order of 700 W. Each carries "
                    "its own stacks of HBM (high-bandwidth memory). The power "
                    "supplies have just brought up standby power and the iDRAC "
                    "(the built-in management controller) is awake, but the "
                    "GPUs, outlined here, are still unpowered."
                ),
                expert=(
                    "HGX baseboard: 8 SXM GPUs, ~700 W class each, HBM on "
                    "package. Standby power up, iDRAC awake; GPUs unpowered."
                ),
            ),
            # The top row whole and the labelled top of the bottom row, so
            # all eight GPUs are on screen and every label reads.
            camera=CameraTarget(x=12, y=0, w=64, h=35.84),
            region_ids=_GPUS,
            layer_reveal=_LID_OFF,
            trace_cursor=1,
            duration_ms=28_000,
        ),
        TourStep(
            id="nvswitch-strip",
            title="The switch between the GPUs and the rear",
            script=L(
                novice=(
                    "Now look at the narrow strip just to the right of the "
                    "GPUs. That is the NVSwitch: switching chips on the same "
                    "board that connect every GPU to every other one, one "
                    "switch hop apart, through NVIDIA's own link, called NVLink. Its position "
                    "tells the story of the box. On its left are the GPUs. On "
                    "its right, at the back, are eight network cards that lead "
                    "outside. Conversation between the eight GPUs stays on the "
                    "left of that strip; anything bound for the wider world "
                    "leaves through the right."
                ),
                standard=(
                    "The narrow strip at the right edge of the GPU field is the "
                    "NVSwitch complex, switch silicon on the HGX baseboard that "
                    "cross-connects all eight GPUs over NVLink, NVIDIA's "
                    "GPU-to-GPU link, so any one can read or write any other's "
                    "HBM, at 900 GB/s per GPU on H100 and H200 boards. Its "
                    "placement is the traffic hierarchy drawn in space: GPUs on "
                    "its left, the eight scale-out network cards (NICs) at the "
                    "rear on its right. The "
                    "XE9712 rack gives the same role to nine switch trays, "
                    "built on a newer generation of the switch chip; here "
                    "it is a strip of chips on one board."
                ),
                expert=(
                    "NVSwitch strip: all-to-all NVLink, 900 GB/s/GPU (H100/H200). Sits "
                    "between the GPU field and the NICs. XE9712 moves the same "
                    "role, a generation newer, into nine switch trays."
                ),
            ),
            # The upper half around the strip; the lower half mirrors it.
            camera=CameraTarget(x=40, y=0, w=60, h=33.6),
            region_ids=["nvswitch"],
            layer_reveal=_SWITCH,
            trace_cursor=1,
            duration_ms=26_000,
        ),
        TourStep(
            id="host-boots-first",
            title="The host boots before any GPU",
            script=L(
                novice=(
                    "Before any GPU wakes, an ordinary computer inside the box "
                    "starts up: two Intel Xeon processors and 32 memory sticks. "
                    "It runs its power-on self-test, called POST, tunes its "
                    "memory timing, which is the slow part of any server "
                    "start-up, and takes a roll call of everything attached. "
                    "To this computer, the eight GPUs are, for now, just eight "
                    "more devices on the list, like the drives. Everything the "
                    "GPUs will ever be fed passes through it first. A GPU "
                    "server is still a server."
                ),
                standard=(
                    "The x86 host boots first: two Intel Xeon processors and 32 "
                    "DDR5 DIMMs run POST (power-on self-test), train their "
                    "memory, the same slow stage the R760 twin dwells on, and "
                    "enumerate PCIe, the internal expansion bus. At this moment the eight GPUs are just "
                    "eight PCIe endpoints, no different from the NVMe drives. "
                    "Everything the accelerators consume passes through this "
                    "host, but here the host exists to feed them. A GPU server "
                    "is still a server."
                ),
                expert=(
                    "Host first: 2x Xeon, 32 DDR5 DIMMs, POST, memory training, "
                    "PCIe enumeration. GPUs are plain endpoints until they init."
                ),
            ),
            # Only the host is lit and framed: the trace also lights the NVMe
            # bay and iDRAC here, but they sit at opposite ends of the map and
            # the narration only uses the drives as a comparison.
            camera=frame("host-cpus"),
            region_ids=["host-cpus"],
            layer_reveal=_SWITCH,
            trace_cursor=2,
            duration_ms=26_000,
        ),
        TourStep(
            id="gpu-init",
            title="Eight GPUs wake, and the fans roar",
            script=L(
                novice=(
                    "Now the eight GPUs wake, all at once, and this is the "
                    "slowest step of the whole start-up, so the timeline "
                    "lingers here. Each GPU loads its own software and then "
                    "tunes the connection to its fast memory, thousands of tiny "
                    "adjustments, much as the host tuned its memory a moment "
                    "ago, but eight times over. The power drawn by the box "
                    "jumps from about one kilowatt to about nine in this "
                    "illustrative timeline, and the fans speed up toward full "
                    "roar. Once GPUs draw power, the fans never stop again."
                ),
                standard=(
                    "The eight GPUs come out of reset in lockstep. Firmware "
                    "loads, then HBM training: each GPU tunes the interface to "
                    "its memory stacks, thousands of per-lane adjustments, the "
                    "accelerator's version of DIMM training times eight. It is "
                    "the longest stage in the trace, so playback dwells on it. "
                    "Draw jumps from about 1 kW to about 9 kW (illustrative), "
                    "and the fan wall ramps; from here to the end, the fans run "
                    "on every step. The GPUs are awake, and still eight "
                    "separate devices."
                ),
                expert=(
                    "GPU init, lockstep: firmware, HBM training x8. Longest "
                    "stage. ~1 to ~9 kW (illustrative). Fans on from here to "
                    "the end. Eight separate devices."
                ),
            ),
            camera=frame(*_GPUS, *_FANS),
            region_ids=[*_GPUS, *_FANS],
            layer_reveal=_SWITCH,
            trace_cursor=3,
            duration_ms=30_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="The domain snaps to eight, and stops",
            script=L(
                novice=(
                    "This is the most important moment in the tour. The switch "
                    "chips join the eight GPUs into one group, called an NVLink "
                    "domain. From now on, any GPU can reach straight into any "
                    "other GPU's memory, far faster than an ordinary connection "
                    "allows, and software can treat the eight almost like one "
                    "giant chip. Watch the counter of GPUs in the domain. It "
                    "jumps from zero straight to eight in a single step; there "
                    "is never a group of three or five. And eight is where it "
                    "stops for good. The links are copper traces on one board, "
                    "and they end at the metal wall of this box. Nothing that "
                    "happens next, not even joining a cluster of a hundred "
                    "thousand GPUs, will ever add a ninth."
                ),
                standard=(
                    "This is the idea the machine is built around. The NVSwitch "
                    "chips fuse the eight GPUs into one NVLink domain: every GPU "
                    "can read and write every other's HBM directly (900 GB/s "
                    "per GPU on H100 and H200 boards), and software sees something close to one large "
                    "accelerator. The GPUs-in-domain counter snaps from zero to "
                    "eight atomically, so a partial domain never exists, and it "
                    "never grows again. The fuse runs over copper traces on one "
                    "baseboard, with none of the XE9712's cable training, and "
                    "it ends at the chassis wall. NVLink stops here. Scale does not."
                ),
                expert=(
                    "NVSwitch fuse: gpusInDomain 0 to 8 atomically, never "
                    "partial, never above 8. Board-trace NVLink (900 GB/s/GPU "
                    "on H100/H200), bounded by the chassis."
                ),
            ),
            camera=frame(*_GPUS, "nvswitch"),
            region_ids=[*_GPUS, "nvswitch"],
            layer_reveal=_SWITCH,
            trace_cursor=4,
            duration_ms=40_000,
        ),
        TourStep(
            id="one-nic-per-gpu",
            title=L(
                standard="One NIC per GPU, past the wall",
                novice="One network card (NIC) per GPU, leading outside",
            ),
            script=L(
                novice=(
                    "Now the box reaches outward. At the back, eight network "
                    "cards, called NICs, come online, one for each GPU, and "
                    "connect to the switch at the top of the rack. That "
                    "switch is the edge of the fabric, meaning the "
                    "data-center network that joins thousands of servers. "
                    "Each GPU gets its "
                    "own private road out, so it never waits in line behind "
                    "the other seven. Watch the NICs-up counter climb to "
                    "eight. That road out is much narrower than the wiring "
                    "inside the box — leaving the box always costs speed, "
                    "which is why the eight GPUs in here are joined so "
                    "tightly in the first place. The tour shows this after "
                    "the fuse to keep inside and outside apart; on a real "
                    "server neither waits for the other. So inside the box, "
                    "the GPUs talk over NVLink; beyond it, they talk over "
                    "Ethernet, the same kind of networking the rest of the "
                    "building uses."
                ),
                standard=(
                    "Now the box reaches outward. Eight "
                    "ConnectX-class NICs, one dedicated to each GPU, train "
                    "400 GbE links to the leaf switch, and the NICs-up counter "
                    "reaches eight. Each GPU has a private on-ramp: remote GPUs "
                    "do RDMA (remote direct memory access) into its memory "
                    "without the host CPU and without queueing behind seven "
                    "siblings. NVLink inside the box, Ethernet beyond it, and "
                    "the units change with it: NVLink's 900 GB/s (H100 and "
                    "H200 boards) is bytes, "
                    "both directions summed, while 400 Gb/s is bits, about "
                    "50 GB/s each way. Past the wall a GPU has roughly one "
                    "ninth of what it has inside. The trace places this beat "
                    "after the fuse to show that hierarchy, not because one "
                    "gates the other; real NIC links train when the host "
                    "loads their drivers. The "
                    "XE9712 moves that wall out to a 72-GPU rack; here the "
                    "SN6000 twin's fabric takes over at the sheet metal."
                ),
                expert=(
                    "Fabric: 8 NICs, 1:1 with GPUs, 400 GbE each, RDMA. "
                    "100 GB/s bidir out vs 900 in (H100/H200), ~9:1. Order after the fuse "
                    "is illustrative. NVLink in-chassis, Ethernet out. Contrast "
                    "XE9712's 72-GPU domain; SN6000 carries scale-out."
                ),
            ),
            camera=frame(*_NICS, "nvswitch"),
            region_ids=[*_NICS, "nvswitch"],
            layer_reveal=_SWITCH,
            trace_cursor=5,
            duration_ms=30_000,
        ),
        TourStep(
            id="buy-the-box-again",
            title="Scale by buying the box again",
            script=L(
                novice=(
                    "The lid goes back on. The server passes its health checks "
                    "and joins a cluster, drawing roughly 11 kilowatts at full "
                    "load in this illustrative timeline, about as much as a "
                    "whole rack of ordinary servers. Look at the two counters "
                    "one last time: eight network cards up, and still eight "
                    "GPUs in the domain. Joining a huge cluster did not add a "
                    "single GPU to it. The group is the box, the cluster is the "
                    "network, and you grow by buying the box again. xAI's "
                    "Colossus was first built this way: a reported 100,000 GPUs "
                    "in eight-GPU servers from Dell and Supermicro, which works "
                    "out to about 12,500 boxes, in liquid-cooled racks rather "
                    "than this air-cooled version."
                ),
                standard=(
                    "Reassembled and in service. Burn-in exercises every GPU, "
                    "NVLink path, NIC and HBM stack, then the server registers "
                    "with the cluster scheduler, drawing on the order of 11 kW "
                    "at full load (illustrative). Both counters read eight: "
                    "joining the cluster did not grow the NVLink domain by a "
                    "single GPU. The domain is the box, the cluster is the "
                    "fabric, and you scale by buying the box again. xAI's "
                    "Colossus was first built that way: a reported 100,000 GPUs "
                    "in 8-GPU HGX servers from Dell and Supermicro, about "
                    "12,500 boxes, liquid-cooled rather than this air-cooled "
                    "6U."
                ),
                expert=(
                    "Burn-in, scheduler registration, ~11 kW (illustrative). "
                    "Domain 8, NICs 8. Domain = box, cluster = fabric; "
                    "Colossus: ~12,500 8-GPU HGX boxes (Dell + Supermicro, DLC)."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[],
            layer_reveal=_OUTSIDE,
            trace_cursor=6,
            duration_ms=28_000,
        ),
    ]

    return Tour(
        id="xe9680-tour",
        title="Inside an XE9680, as it wakes",
        intro=L(
            novice=(
                "A guided walk through the server as it starts up, narrated "
                "beat by beat. Sit back and watch, or pause and click anything "
                "to look closer; the tour waits for you."
            ),
            standard=(
                "A narrated walk through the 8-GPU server while it powers on. "
                "Watch it play, or pause and explore; Resume tour brings the "
                "camera back."
            ),
            expert="Narrated power-on walk-through. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=[],
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: ServerAnatomy) -> TourResponse:
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
