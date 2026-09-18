"""The narrated tour of a PowerMax node pair and its drive enclosure — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: nine beats that
move a camera across the floorplan, peel it from the serviceable outside to
the fabric that joins everything, pin the power-on trace at the moments that
carry the story, and narrate each one. The frontend player owns the clock;
nothing here knows about time, IO or the web (AST-checked in
``tests/test_tour.py``, the same rule as ``engine.py``).

The storyboard: the array from outside -> the node-pair engine -> directors
A and B -> global memory (DRAM cache) -> vault-to-flash -> PowerMaxOS, the
long stage -> the InfiniBand fabric -> drives that are not on a director's
bus -> online. The signature beat is ``vault-to-flash``: the write cache is
volatile DRAM, the standby power supply carries a flush of it to flash on a
power loss, and the array validates that vault before it boots its storage
stack (the trace's ``vault`` phase). Every claim a script makes is one the
engine or the anatomy already makes; the trace index each beat pins is the
step whose description says the same thing.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``ChassisAnatomy`` is unchanged:

    0  what you see and service from outside: DME, PSUs, I/O modules, mgmt
    1  inside each director: fans, SPS, vault flash, cache, CPUs, board
    2  the InfiniBand Dynamic Fabric that joins directors and drives
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
from .models import ChassisAnatomy

#: The step the tests pin: the product's one idea lives here.
SIGNATURE_STEP_ID = "vault-to-flash"

_OUTSIDE = 0
_DIRECTOR = 1
_FABRIC = 2


def layer_map(anatomy: ChassisAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    inside = {"cooling", "battery", "vault", "cache", "cpu", "board"}
    layers: dict[str, int] = {}
    for region in anatomy.regions:
        if region.kind == "fabric":
            layers[region.id] = _FABRIC
        elif region.kind in inside:
            layers[region.id] = _DIRECTOR
        else:
            layers[region.id] = _OUTSIDE
    return layers


def build_tour(anatomy: ChassisAnatomy) -> Tour:
    """The PowerMax tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 3.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    steps = [
        TourStep(
            id="rack-elevation",
            title="A node pair and a shelf of drives",
            script=L(
                novice=(
                    "This is a Dell PowerMax, the storage array for the big "
                    "databases and mainframes that are never allowed to stop. We are "
                    "looking down on one building block of it from above. On the "
                    "left, standing on its own, is a shelf of flash drives called "
                    "a Dynamic Media Enclosure, or DME for short, with room for 48 "
                    "drives that speak NVMe, a fast way for flash to talk to a "
                    "processor. Everything to its right is the engine that runs "
                    "the array. The power cords have just gone in, and the whole "
                    "thing is still dark."
                ),
                standard=(
                    "This is Dell PowerMax, the flagship array for workloads that "
                    "cannot go down, seen from above with the front on the left. "
                    "The strip on the left is a Dynamic Media Enclosure (DME): a "
                    "separate shelf of up to 48 dual-ported NVMe flash drives. "
                    "Everything to its right is one node-pair engine. Line cords "
                    "are in at the intelligent PDUs (power distribution units) and "
                    "the array is dark."
                ),
                expert=(
                    "PowerMax: one node-pair engine plus one 48-slot NVMe DME, "
                    "top-down, front left. AC present at the PDUs; array dark."
                ),
            ),
            camera=whole_map(anatomy),
            # Only the DME: the PSUs belong to the engine and are still dark
            # (trace step 0 lights nothing), so lighting them here would
            # contradict the narration.
            region_ids=["dme"],
            layer_reveal=_OUTSIDE,
            trace_cursor=0,
            duration_ms=24_000,
        ),
        TourStep(
            id="node-pair-engine",
            title="The engine is two computers",
            script=L(
                novice=(
                    "Now we lift the lid on the engine. It is really two complete "
                    "computers, one on top and one on the bottom, and PowerMax calls "
                    "each one a director. Together they make a node pair. A small "
                    "PowerMax 2500 has one or two of these pairs, and the big "
                    "PowerMax 8500 can have up to eight, all joined together. "
                    "There is no power button anywhere: an array must come back by "
                    "itself after an outage, with nobody there to press anything, "
                    "so plugging it in is what turns it on."
                ),
                standard=(
                    "With the lid peeled back, the engine is a node pair: two "
                    "compute nodes, called directors, drawn as mirror images top "
                    "and bottom, each with its own CPUs, DRAM cache, vault flash "
                    "and front-end I/O. A PowerMax 2500 is one or two node pairs; "
                    "an 8500 scales to eight. There is no power button. An array "
                    "must return to service unattended after an outage, so "
                    "applying AC is the power-on."
                ),
                expert=(
                    "Node-pair engine: two directors, each a full compute node. "
                    "2500 = 1-2 pairs, 8500 = up to 8. No power button; AC is "
                    "power-on."
                ),
            ),
            camera=CameraTarget(x=8, y=0, w=92, h=52),
            region_ids=[
                "cpu-a", "cpu-b", "cache-a", "cache-b",
                "board-a", "board-b",
            ],
            layer_reveal=_DIRECTOR,
            trace_cursor=0,
            duration_ms=26_000,
        ),
        TourStep(
            id="directors-a-b",
            title="Everything happens twice",
            script=L(
                novice=(
                    "We have moved in close on the top director, called A. "
                    "Director B, below it, is an exact copy. Both directors' power "
                    "supplies switch on together, and from here until the end, "
                    "everything happens twice, once in each director. Neither one "
                    "waits for the other. Each starts up as if its partner might "
                    "not be there at all, because staying up when one half fails "
                    "is the whole point of having two. Each director's processors "
                    "are Intel Xeon chips, and they will run the storage software "
                    "and all its features."
                ),
                standard=(
                    "A close-up of director A; director B below is its mirror. "
                    "Both directors' power supplies bring their rails up in "
                    "parallel, and from here on everything happens twice, once per "
                    "director, because redundancy starts from the assumption that "
                    "the partner might not be there. Each director is a complete "
                    "multi-socket x86 compute complex whose Intel Xeon processors "
                    "will run PowerMaxOS and every data service."
                ),
                expert=(
                    "Director A close-up; B mirrors it. PSUs up on both in "
                    "parallel; every stage now runs per director. Multi-socket "
                    "Xeon complex per node."
                ),
            ),
            # Close on director A's rear half, where its power supplies (the
            # regions trace step 1 lights), processors and board sit; director
            # B, below, is its mirror image. The map is 100 x 52, so any frame
            # that holds both halves is nearly the whole map — a real zoom has
            # to pick one half.
            camera=frame("cpu-a", "board-a", "psu-a", pad=1.5),
            region_ids=["psu-a", "psu-b", "cpu-a", "cpu-b", "board-a", "board-b"],
            layer_reveal=_DIRECTOR,
            trace_cursor=1,
            duration_ms=26_000,
        ),
        TourStep(
            id="global-memory",
            title="The write cache is ordinary memory",
            script=L(
                novice=(
                    "Next to the processors sits each director's memory, which "
                    "PowerMax calls cache or global memory. Data that computers "
                    "read and write is handled here first, at memory speed, "
                    "which is far quicker than any drive. But this is ordinary memory: "
                    "switch off the power and it forgets everything. So before the "
                    "array will accept a single write, each director tests its "
                    "standby power supply, a battery drawn just beside the cache. "
                    "It is not there to keep the array running. Its one job comes "
                    "in the next beat."
                ),
                standard=(
                    "Beside the Xeons is each director's DRAM, which PowerMax calls "
                    "cache or global memory. Reads and writes are served from it at "
                    "memory speed, and metadata lives there too. DRAM is volatile, "
                    "so each node now self-tests its standby power supply (SPS). "
                    "The SPS is not a UPS and cannot keep the array serving. Until "
                    "both nodes know a power loss is survivable, the array will not "
                    "accept a single write."
                ),
                expert=(
                    "DRAM cache = global memory: reads, writes, metadata at memory "
                    "speed. Volatile, so SPS self-test on both nodes gates writes. "
                    "SPS is not a UPS."
                ),
            ),
            # Director A's SPS, cache and the Xeons beside it; director B
            # carries the same below.
            camera=frame("sps-a", "cache-a", "cpu-a", pad=2.0),
            region_ids=["cache-a", "cache-b", "sps-a", "sps-b"],
            layer_reveal=_DIRECTOR,
            trace_cursor=2,
            duration_ms=26_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="The flush that makes memory safe",
            script=L(
                novice=(
                    "This is the most important moment in the tour. Here is the "
                    "problem: the array tells a computer its data is safe while "
                    "that data is still only in memory, which forgets everything "
                    "when the power goes. The answer is these small flash modules, "
                    "called the vault. If the power ever fails, the standby battery "
                    "keeps each director alive for just a few seconds, long enough "
                    "to copy everything in memory onto the vault's flash, which "
                    "keeps its contents with no power at all. Director B, below, "
                    "has the same three parts. So now, before the "
                    "storage software even starts, each director checks its vault. "
                    "If the last shutdown was sudden, it copies the saved data back "
                    "into memory first. That is how the array is designed to keep "
                    "its promise: nothing it said was safe is lost to a power cut. The "
                    "smaller PowerStore twin solves the same problem a different "
                    "way, with special drives that hold the cache."
                ),
                standard=(
                    "This is the idea the array's cache is built around. Writes "
                    "are acknowledged from DRAM, which is volatile, so each "
                    "director carries vault-to-flash modules: NVMe self-encrypting "
                    "flash, shown here on director A with B's mirror below. On a "
                    "power loss the SPS powers the director for the "
                    "seconds it takes to flush the whole cache into the vault. Now, "
                    "before PowerMaxOS boots, each node validates its vault, and "
                    "if the last shutdown was dirty, restores cache from flash "
                    "first. The design goal is that no acknowledged write is ever "
                    "lost across a power event. The PowerStore twin makes the same promise "
                    "with dedicated NVRAM drives instead."
                ),
                expert=(
                    "Signature: vault-to-flash. DRAM-acked writes; SPS funds a "
                    "full cache flush to NVMe SED vault on AC loss. Vault "
                    "validated, dirty cache restored, before OS boot. Zero "
                    "acknowledged-write loss. Contrast PowerStore's NVRAM."
                ),
            ),
            # Director A's vault, SPS and cache, the three parts of the idea.
            # Framing both directors' copies would need the whole map (they
            # stack top and bottom), which is no zoom at all; B's copies stay
            # lit and the narration says they mirror A.
            camera=frame("vault-a", "sps-a", "cache-a", pad=2.0),
            region_ids=["vault-a", "vault-b", "sps-a", "sps-b", "cache-a", "cache-b"],
            layer_reveal=_DIRECTOR,
            trace_cursor=4,
            duration_ms=40_000,
        ),
        TourStep(
            id="powermaxos-boots",
            title="The longest wait",
            script=L(
                novice=(
                    "With the vault known to be good, both directors start the "
                    "array's own operating system, PowerMaxOS 10. It runs "
                    "everything the array does: shrinking data so it takes less "
                    "space, taking snapshots, copying data to a second array far "
                    "away, and speaking the different languages computers use to "
                    "reach storage, including the one IBM mainframes use. This is "
                    "the slowest part of the whole start-up, taking minutes rather "
                    "than seconds on this illustrative timeline, so the playback "
                    "lingers here."
                ),
                standard=(
                    "With the vault validated, each director boots PowerMaxOS 10, "
                    "the operating environment for the whole storage stack: global "
                    "memory management, data reduction, SnapVX snapshots, SRDF "
                    "replication, and the front-end emulations that let one array "
                    "speak Fibre Channel, iSCSI, NVMe and mainframe FICON at once. "
                    "It is the longest single stage in the trace, minutes rather "
                    "than seconds (illustrative), so playback dwells on it."
                ),
                expert=(
                    "PowerMaxOS 10 boot on both directors: global memory, "
                    "reduction, SnapVX, SRDF, FC/iSCSI/NVMe/FICON emulations. "
                    "Longest stage, max dwell."
                ),
            ),
            camera=frame("cache-a", "cpu-a", pad=2.0),
            region_ids=["cpu-a", "cpu-b", "cache-a", "cache-b"],
            layer_reveal=_DIRECTOR,
            trace_cursor=6,
            duration_ms=28_000,
        ),
        TourStep(
            id="dynamic-fabric",
            title="The fabric joins the pair",
            script=L(
                novice=(
                    "Until now the two directors have ignored each other. Here "
                    "they finally meet, over a very fast network called "
                    "InfiniBand, which PowerMax calls the Dynamic Fabric. It is "
                    "drawn as the thin line between the two halves. From now on "
                    "each director copies every new write to its partner across "
                    "this link before telling the computer it is safe, and each "
                    "watches the other, ready to take over at once if it stops. On "
                    "the big 8500 this same network joins every pair to every "
                    "other pair."
                ),
                standard=(
                    "The InfiniBand Dynamic Fabric initializes at 100 Gb/s per "
                    "port, and the two directors find each other over it. Cache "
                    "mirroring and heartbeat now cross the fabric: every dirty "
                    "write is copied to the partner before it is acknowledged, "
                    "and each node watches the other for instant failover. On a "
                    "PowerMax 8500 the same fabric is a dual redundant mesh "
                    "joining every node pair; on the 2500 it is a direct "
                    "connection between the pair."
                ),
                expert=(
                    "Dynamic Fabric up, 100 Gb/s InfiniBand per port. Cache "
                    "mirror and heartbeat across it; ack after partner copy. 8500: "
                    "dual redundant mesh; 2500: direct link."
                ),
            ),
            # Director A's InfiniBand adapter and the thin bus between the
            # halves; the top of director B's adapter shows below the bus.
            camera=frame("fabric-a", "fabric-bus", pad=2.0),
            region_ids=["fabric-a", "fabric-b", "fabric-bus"],
            layer_reveal=_FABRIC,
            trace_cursor=7,
            duration_ms=28_000,
        ),
        TourStep(
            id="drives-on-the-fabric",
            title="The drives belong to no director",
            script=L(
                novice=(
                    "Now the directors look for the drives, and notice where they "
                    "find them. The drive shelf is not plugged into either "
                    "director's own circuit board. It hangs off the fabric, and "
                    "every drive has two separate connections, so any director, in "
                    "any node pair, can reach any drive. That is why PowerMax can "
                    "grow two different ways: add node pairs when you need more "
                    "speed, add drives when you need more space, and neither "
                    "forces you to buy the other. In the smaller PowerStore twin, "
                    "the drives sit inside the same box as the two computers."
                ),
                standard=(
                    "The directors enumerate the DME over the fabric, not over "
                    "their own PCIe buses. Every NVMe drive is dual-ported and "
                    "reached across the InfiniBand fabric, so any director in any "
                    "node pair has a path to any drive. That is the physical "
                    "reason PowerMax scales out: compute and capacity are separate "
                    "modules joined by the fabric, and either can grow without the "
                    "other. PowerStore, by contrast, keeps its drives in the same "
                    "enclosure as its two nodes."
                ),
                expert=(
                    "DME discovery over the fabric, not a director PCIe bus. "
                    "Dual-ported NVMe, any director to any drive. Compute and "
                    "capacity scale independently."
                ),
            ),
            camera=frame("dme", "fabric-a", "fabric-b", "fabric-bus", pad=2.0),
            region_ids=["dme", "fabric-a", "fabric-b", "fabric-bus"],
            layer_reveal=_FABRIC,
            trace_cursor=8,
            duration_ms=30_000,
        ),
        TourStep(
            id="online",
            title="Serving, with nobody touching it",
            script=L(
                novice=(
                    "The lid goes back on and the array is serving data, with both "
                    "directors sharing the work. New writes are copied into both "
                    "directors' memory and protected by the vault; reads come off "
                    "the drives; data is shrunk as it arrives. The whole pair plus "
                    "its drive shelf draws roughly what one electric kettle does "
                    "while it boils, an illustrative figure. It also sends health "
                    "reports to Dell's CloudIQ service, and it can copy data to a "
                    "PowerProtect vault for cyber recovery. From cords in to "
                    "serving took minutes, and nobody touched it."
                ),
                standard=(
                    "Reassembled and online. Both directors serve host I/O and "
                    "share the load across the fabric; writes mirror through cache "
                    "and are protected by vault-to-flash, reads come off the NVMe "
                    "pool, and data reduction runs inline on every write. Steady "
                    "draw for one node pair and one DME is around two kilovolt-"
                    "amperes (illustrative), telemetry flows to CloudIQ, and the "
                    "PowerProtect twin shows the cyber vault behind it. Cords-in "
                    "to serving: minutes, unattended."
                ),
                expert=(
                    "Online, both directors active. Cache-mirrored, vault-"
                    "protected writes; NVMe pool reads; inline reduction. ~2 kVA "
                    "(illustrative). CloudIQ telemetry. Unattended."
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
        id="powermax-tour",
        title="Inside a PowerMax, as it wakes",
        intro=L(
            novice=(
                "A guided walk through the array as it starts up, narrated beat by "
                "beat. Sit back and watch, or pause and click anything to look "
                "closer; the tour waits for you."
            ),
            standard=(
                "A narrated walk through the node pair and its drive enclosure "
                "while they power on. Watch it play, or pause and explore; Resume "
                "tour brings the camera back."
            ),
            expert="Narrated node-pair power-on. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=[],
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
