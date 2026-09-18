"""The narrated tour of the PowerStore appliance — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: eight beats that
move a camera across the enclosure, peel it from the serviceable outside to
the link between the two controller nodes, pin the power-on trace at the
moments that carry the story, and narrate each one. The frontend player owns
the clock; nothing here knows about time, IO or the web (AST-checked in
``tests/test_tour.py``, the same rule as ``engine.py``).

The storyboard is ACTIVE_TWIN_SPEC.md section 8's PowerStore row, and the
signature beat is ``mirrored-ack``: a write exists in two places before the
host is told it is safe. Every claim the scripts make is one the engine and
the anatomy already make — the trace indices named in each beat are the
steps whose descriptions say the same thing.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``ChassisAnatomy`` is unchanged:

    0  what you can see and touch: drive bay, NVRAM slots, PSUs, ports, modules
    1  inside each node canister: fans, battery, CPU, DRAM, system board
    2  the link between the two canisters
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
from .models import ChassisAnatomy

#: The step the tests pin: the product's one idea lives here.
SIGNATURE_STEP_ID = "mirrored-ack"

_OUTSIDE = 0
_CANISTER = 1
_LINK = 2


def layer_map(anatomy: ChassisAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    inside = {"cooling", "battery", "cpu", "memory"}
    layers: dict[str, int] = {}
    for region in anatomy.regions:
        if region.id == "interconnect":
            layers[region.id] = _LINK
        elif region.kind in inside or region.id.startswith("board-"):
            layers[region.id] = _CANISTER
        else:
            layers[region.id] = _OUTSIDE
    return layers


def _photos() -> list[TourPhoto]:
    credit = "Dell Technologies product image"
    return [
        TourPhoto(
            id="front",
            url="/powerstore2.webp",
            caption="The base enclosure from the front: 25 hot-swap NVMe slots.",
            credit=credit,
        ),
        TourPhoto(
            id="io-module",
            url="/powerstore3.webp",
            caption="A 100 GbE I/O module mid-service; orange marks what can be swapped live.",
            credit=credit,
        ),
    ]


def build_tour(anatomy: ChassisAnatomy) -> Tour:
    """The PowerStore tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 3.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    steps = [
        TourStep(
            id="front-bezel",
            title="Twenty-five slots, all NVMe",
            script=L(
                novice=(
                    "This is a Dell PowerStore, a storage array: a box whose whole "
                    "job is to hold data for other computers. We are looking down "
                    "on it from above, with the front on the left. Those slots at "
                    "the front hold 25 flash drives, and every one of them speaks "
                    "NVMe, short for Non-Volatile Memory Express, the fast way for "
                    "flash to talk directly to a processor. Twenty-one of them hold "
                    "your data. The bottom four are something special, which we "
                    "will come back to. The cords are in, and the box is still dark."
                ),
                standard=(
                    "This is a Dell PowerStore, an all-NVMe midrange storage array, "
                    "seen from above with the front on the left. The front holds 25 "
                    "hot-swap slots, and every one speaks NVMe (Non-Volatile Memory "
                    "Express) straight to a processor over PCIe. Twenty-one hold "
                    "capacity SSDs; the bottom four hold NVRAM, the write cache this "
                    "tour comes back to. Both cords are in and the enclosure is dark."
                ),
                expert=(
                    "PowerStore base enclosure, top-down, front left. 25 NVMe slots: "
                    "21 capacity SSDs, 4 NVRAM. AC present, enclosure dark."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["drive-bay", "nvram"],
            layer_reveal=_OUTSIDE,
            trace_cursor=0,
            duration_ms=26_000,
            photo_id="front",
        ),
        TourStep(
            id="no-power-button",
            title="No power button, and a battery that is not a UPS",
            script=L(
                novice=(
                    "There is no power button. The moment electricity arrives, each "
                    "half of the box powers itself on, because an array is expected "
                    "to come back by itself after any outage with nobody there. We "
                    "have lifted the lid now, and the first thing each half checks "
                    "is its battery. That battery cannot keep the array running. "
                    "Its only job is to keep things alive for a few seconds after a "
                    "power cut, long enough to save anything still in memory onto "
                    "flash. Until both halves know that works, the array will not "
                    "accept a single write."
                ),
                standard=(
                    "There is no power button: applying AC is the power-on, because "
                    "an array must return to service unattended after any outage. "
                    "With the lid peeled back, the first check each node makes is "
                    "its battery backup unit (BBU). The BBU is not a UPS and cannot "
                    "keep the array running; it exists for vaulting, powering the "
                    "node for the seconds it takes to flush cached writes to "
                    "non-volatile media. Until both nodes pass, no write is accepted."
                ),
                expert=(
                    "AC is the power-on. First gate: BBU self-test on both nodes. "
                    "BBU funds the vault flush only, not ride-through. No writes "
                    "until both pass."
                ),
            ),
            # Close on node A's canister; node B, below, is its mirror image.
            # (The map is 100 x 46, so any frame that holds both halves is
            # nearly the whole map — a real zoom has to pick one half.)
            camera=CameraTarget(x=8, y=0, w=50, h=23),
            region_ids=["bbu-a", "bbu-b"],
            layer_reveal=_CANISTER,
            trace_cursor=2,
            duration_ms=28_000,
        ),
        TourStep(
            id="two-computers",
            title="Two computers in one box",
            script=L(
                novice=(
                    "Look at the top half and the bottom half. They are mirror "
                    "images, because they are two separate computers, called nodes, "
                    "sharing one box. Each has its own processor, its own memory and "
                    "its own power supply, and each starts up on its own without "
                    "waiting for the other. They are loading the array's operating "
                    "system, PowerStoreOS, which runs every storage feature as a "
                    "separate container, a small packaged program. This is the "
                    "slowest part of the whole start-up, so the timeline lingers "
                    "here."
                ),
                standard=(
                    "The top and bottom halves are mirror images because they are "
                    "two complete x86 computers: controller nodes A and B, each with "
                    "its own Xeon, DRAM, fans and power supply. They boot "
                    "independently, assuming the partner may not be there. Here both "
                    "load PowerStoreOS, an embedded Linux that runs the storage "
                    "stack as containers. It is the longest stage in the trace, "
                    "which is why playback dwells on it."
                ),
                expert=(
                    "Nodes A and B: independent x86 controllers, independent boot. "
                    "PowerStoreOS container stack loading on both; longest stage, "
                    "max dwell."
                ),
            ),
            camera=frame("cpu-a", "cpu-b", "dimm-a", "dimm-b", pad=2.0),
            region_ids=["cpu-a", "cpu-b", "dimm-a", "dimm-b"],
            layer_reveal=_CANISTER,
            trace_cursor=5,
            duration_ms=28_000,
        ),
        TourStep(
            id="dual-ported-drives",
            title="Every drive has two doors",
            script=L(
                novice=(
                    "Now both computers look for the drives, and both find all of "
                    "them. That is because every drive has two separate "
                    "connections, one wired to each computer. There is no middleman "
                    "in between. This is why losing one computer is not a crisis: "
                    "the other one does not have to take the drives over, because "
                    "it was already connected to every one of them the whole time."
                ),
                standard=(
                    "Both nodes now enumerate the drive bay, and both see every "
                    "slot. Each drive is dual-ported: two independent PCIe "
                    "connections, one to each node, with no SAS expanders or "
                    "protocol bridges in between. That is the physical reason "
                    "failover is fast. The surviving node does not take the drives "
                    "over; it already owns a path to every one of them."
                ),
                expert=(
                    "Dual-ported NVMe: one PCIe path per node, no expanders. "
                    "Failover needs no drive takeover; both paths always exist."
                ),
            ),
            camera=frame("drive-bay", "nvram", "cpu-a", "cpu-b", pad=2.0),
            region_ids=["drive-bay", "board-a", "board-b"],
            layer_reveal=_CANISTER,
            trace_cursor=6,
            duration_ms=26_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="Two copies before the answer",
            script=L(
                novice=(
                    "This is the most important moment in the tour. The four special "
                    "drives at the front wake up as the write cache, called NVRAM: "
                    "fast storage that keeps its contents without power. Here is "
                    "what happens to every piece of data a computer sends from now "
                    "on. It arrives at one half of the box, is copied across the "
                    "link in the middle to the other half, and is held in that "
                    "cache, reachable from both halves. Only then does the array "
                    "answer, yes, your data is safe. Because two copies exist "
                    "before that answer, losing a whole half of the box, or losing "
                    "power, cannot lose anything the array has already promised to "
                    "keep. Moving the data onto the main drives happens later, "
                    "while nobody is waiting."
                ),
                standard=(
                    "The four NVRAM drives come up as the write cache, and this is "
                    "the idea the whole appliance is built around. A host write "
                    "arrives at one node, is mirrored across the interconnect to "
                    "its partner, and lands in non-volatile NVRAM that both nodes "
                    "can reach. Only then is the host acknowledged. Because the "
                    "write exists twice before the acknowledgement, an "
                    "acknowledged write survives a node failure and a power loss "
                    "both. Destaging to the capacity SSDs happens later, off the "
                    "path the host is waiting on."
                ),
                expert=(
                    "Signature: mirrored acknowledgement. Write mirrored node to "
                    "node, landed in non-volatile NVRAM, then acked. Survives node "
                    "loss and power loss. Destage async."
                ),
            ),
            camera=frame("nvram", "dimm-a", "dimm-b", "interconnect", pad=2.0),
            region_ids=["nvram", "dimm-a", "dimm-b", "interconnect"],
            layer_reveal=_LINK,
            trace_cursor=7,
            duration_ms=40_000,
        ),
        TourStep(
            id="nodes-converge",
            title="The two boots converge",
            script=L(
                novice=(
                    "Until now the two halves have ignored each other. Here they "
                    "finally meet over the internal link. They start sending each "
                    "other a regular I-am-alive signal, called a heartbeat, and "
                    "agree to work at the same time rather than one waiting as a "
                    "spare. From now on each one watches the other, and if one "
                    "stops answering, its partner takes over all of its "
                    "connections within seconds."
                ),
                standard=(
                    "The two independent boots converge over the internal "
                    "interconnect. The nodes exchange heartbeats, establish the "
                    "cache-mirroring path, and negotiate active/active operation: "
                    "both own volumes and serve I/O at once, rather than one idling "
                    "as a spare. Each now watches the other, and if a node stops "
                    "answering, its partner takes over every host path in seconds."
                ),
                expert=(
                    "Boots converge: heartbeat, mirror path, active/active. Mutual "
                    "watch; path takeover in seconds."
                ),
            ),
            camera=frame("interconnect", pad=6.0),
            region_ids=["interconnect", "board-a", "board-b"],
            layer_reveal=_LINK,
            trace_cursor=8,
            duration_ms=24_000,
        ),
        TourStep(
            id="every-path-twice",
            title="Every host path exists twice",
            script=L(
                novice=(
                    "Meanwhile the storage pool has been built and the data "
                    "features have started, including shrinking every write as it "
                    "arrives. Now the ports at the back come alive, the sockets "
                    "other computers plug into. The swappable cards, called I/O "
                    "modules, decide what kinds of cable the array speaks, such as "
                    "Fibre Channel or Ethernet. Both halves carry matching cards, "
                    "so every connection a computer uses exists twice, once on each "
                    "half."
                ),
                standard=(
                    "By now the storage pool has assembled and inline deduplication "
                    "and compression are running. The front-end ports come online: "
                    "the embedded mezzanine ports and the hot-swap I/O modules "
                    "present Fibre Channel, iSCSI, NVMe-oF (NVMe over Fabrics) and "
                    "file shares to hosts. Both nodes carry matching modules, so "
                    "every host path exists twice, once per node."
                ),
                expert=(
                    "Pool assembled, inline reduction on. Front-end up: FC, iSCSI, "
                    "NVMe-oF, NFS/SMB, matched modules per node, every path doubled."
                ),
            ),
            # The rear of node A; node B carries the same modules below it.
            camera=CameraTarget(x=36, y=0, w=50, h=23),
            region_ids=[
                "embedded-a", "embedded-b",
                "iomod-a1", "iomod-a2", "iomod-b1", "iomod-b2",
            ],
            layer_reveal=_LINK,
            trace_cursor=11,
            duration_ms=26_000,
            photo_id="io-module",
        ),
        TourStep(
            id="reassemble",
            title="Serving, with nobody touching it",
            script=L(
                novice=(
                    "The lid goes back on. The array is now serving data, and both "
                    "halves share the work. New data is copied into the cache on "
                    "both sides before it is confirmed, and it reaches the main "
                    "drives later. From plugging in the cords to serving data took "
                    "a few minutes in this illustrative timeline, and at no point "
                    "did anyone need to touch the box. Press play on the power-on "
                    "page to walk the same sequence step by step."
                ),
                standard=(
                    "Reassembled and online. Both nodes serve host I/O and share "
                    "the load; writes mirror through NVRAM, reads come off the NVMe "
                    "pool, and data reduction runs inline on every write. Cords-in "
                    "to serving took minutes on this illustrative timeline, with no "
                    "one touching the box. The power-on page walks the same trace "
                    "one step at a time."
                ),
                expert=(
                    "Online, active/active. NVRAM-mirrored writes, NVMe reads, "
                    "inline reduction. Cords-in to serving in minutes, unattended."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[],
            layer_reveal=_OUTSIDE,
            trace_cursor=13,
            duration_ms=26_000,
        ),
    ]

    return Tour(
        id="powerstore-tour",
        title="Inside a PowerStore, as it wakes",
        intro=L(
            novice=(
                "A guided walk through the appliance as it starts up, narrated beat "
                "by beat. Sit back and watch, or pause and click anything to look "
                "closer; the tour waits for you."
            ),
            standard=(
                "A narrated walk through the appliance while it powers on. Watch it "
                "play, or pause and explore; Resume tour brings the camera back."
            ),
            expert="Narrated power-on walk-through. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=_photos(),
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: ChassisAnatomy) -> TourResponse:
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
