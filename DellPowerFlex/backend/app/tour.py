"""The narrated tour of a PowerFlex pool — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: eight beats that
move a camera across the pool map, peel it from the hardware to the software
that coordinates it, pin the cluster trace at the moments that carry the
story, and narrate each one. The frontend player owns the clock; nothing here
knows about time, IO or the web (AST-checked in ``tests/test_tour.py``, the
same rule as ``engine.py``).

The storyboard is ACTIVE_TWIN_SPEC.md section 8's PowerFlex row, and the
signature beat is ``no-controller``: the camera pans the empty band between
the fabric and the servers, where a controller row would sit in any other
array, while the trace sits on the step that elects a metadata *manager* —
the one piece of coordination the pool has, drawn small and off to one side.
Every claim the scripts make is one the engine, the anatomy and the tests
already make.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``ClusterAnatomy`` is unchanged:

    0  the hardware in the data path: clients, the IP fabric, the six nodes
    1  the software that coordinates it: metadata manager, protection and
       rebuild engine, lifecycle and telemetry
"""

from __future__ import annotations

from twinkit.tour import (
    CameraTarget,
    Tour,
    TourPhoto,
    TourResponse,
    TourSource,
    TourStep,
    whole_map,
)

from .leveling import L
from .models import ClusterAnatomy

#: The step the tests pin: the product's one idea lives here.
SIGNATURE_STEP_ID = "no-controller"

_HARDWARE = 0
_SOFTWARE = 1

_NODES = [f"node-{i}" for i in range(1, 7)]
# Node 6 is the one the engine fails; nothing about it is special.
_SURVIVORS = [n for n in _NODES if n != "node-6"]


def layer_map(anatomy: ClusterAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    hardware = {"client", "network", "node"}
    return {
        r.id: _HARDWARE if r.kind in hardware else _SOFTWARE
        for r in anatomy.regions
    }


def _photos() -> list[TourPhoto]:
    return [
        TourPhoto(
            id="pool",
            url="/powerflex-pool.svg",
            caption=(
                "A pool with no middle: chunks mirrored across every server, "
                "clients reading straight from the nodes that hold them."
            ),
            credit="Schematic illustration by this project — not a Dell product image",
        ),
    ]


def build_tour(anatomy: ClusterAnatomy) -> Tour:
    """The PowerFlex tour, framed against ``anatomy``."""
    W, H = float(anatomy.width), float(anatomy.height)

    # The node band and the software row beneath it (y 22..55), full width.
    node_band = CameraTarget(x=0, y=22, w=W, h=H - 22)

    steps = [
        TourStep(
            id="six-servers",
            title="Six ordinary servers",
            script=L(
                novice=(
                    "This is Dell PowerFlex, a way of building shared storage out "
                    "of ordinary servers. Across the top are the clients, the "
                    "computers that will use the storage. Below them is the "
                    "network, and below that six plain servers, each with its own "
                    "fast flash drives inside, called NVMe, short for Non-Volatile "
                    "Memory Express. Right now there is no shared storage here at "
                    "all, just six machines with disks in them. Everything that "
                    "follows is software, with no extra hardware bought and no "
                    "special storage network."
                ),
                standard=(
                    "This is Dell PowerFlex, software-defined block storage built "
                    "from ordinary servers. Clients across the top, the IP fabric "
                    "beneath them, and a band of six identical servers, each with "
                    "local NVMe (Non-Volatile Memory Express) drives that belong "
                    "to it alone. At this moment there is no shared storage at "
                    "all. Everything that follows is software turning those "
                    "separate drives into one pool, with no added hardware and no "
                    "storage-area network (SAN)."
                ),
                expert=(
                    "PowerFlex pool map: clients, IP fabric, six commodity nodes "
                    "with local NVMe. No shared storage yet; pool formation is "
                    "software-only, no SAN."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=list(_NODES),
            layer_reveal=_HARDWARE,
            trace_cursor=0,
            duration_ms=26_000,
            photo_id="pool",
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="The row where the controller isn't",
            script=L(
                novice=(
                    "Look at the gap between the network and the servers. In most "
                    "storage systems, including the PowerStore and PowerMax "
                    "machines shown elsewhere in this collection, a row of "
                    "special computers called controllers would sit right there, "
                    "and every piece of data would have to pass through them. "
                    "Here that row is empty, and it stays empty. The servers "
                    "find each other over the ordinary network and choose one "
                    "small helper, the metadata manager, to keep the map of what "
                    "is stored where. It is a manager, not a controller: it "
                    "decides where things go and settles arguments when a machine "
                    "stops answering, but none of your actual data ever passes "
                    "through it. That is why it is drawn small, down in the "
                    "corner."
                ),
                standard=(
                    "The camera is on the gap between the fabric and the "
                    "servers. In a controller array, like the PowerStore and "
                    "PowerMax twins elsewhere here, a controller row sits here and "
                    "every byte crosses it. In PowerFlex the row is empty. "
                    "The nodes find each other over IP and elect a metadata "
                    "manager (MDM) to hold the map of what will live where. "
                    "Manager, not controller: it decides placement and referees "
                    "failures, and no byte of client data ever passes through "
                    "it. That is why it is drawn smaller than any node, off in "
                    "the corner."
                ),
                expert=(
                    "Signature: no controller tier. The band a controller array "
                    "fills is empty by construction. Nodes cluster over IP and "
                    "elect an MDM: control plane only, never in the data path."
                ),
            ),
            # Fabric, the empty band, the nodes, and the MDM beneath them.
            camera=CameraTarget(x=0, y=10, w=W, h=H - 10),
            region_ids=[*_NODES, "fabric", "mdm"],
            layer_reveal=_SOFTWARE,
            trace_cursor=1,
            duration_ms=40_000,
        ),
        TourStep(
            id="chunk-scatter",
            title="Scattering the chunks, slowly on purpose",
            script=L(
                novice=(
                    "This is the longest stage in the whole timeline, and that is "
                    "deliberate. Each server hands its drives to one shared pool. "
                    "The software cuts that pool into small pieces, called chunks, "
                    "and spreads them across all six servers, keeping a second "
                    "copy of every chunk on a different server. No server ends up "
                    "holding a whole volume, which is the storage equivalent of a "
                    "disk; every server holds a piece of every volume. It takes "
                    "time, and it pays off later: because the data is already "
                    "everywhere, nothing has to be moved there in a hurry when "
                    "something breaks."
                ),
                standard=(
                    "The longest stage in the trace, on purpose. Each node's "
                    "drives are contributed to a shared pool, and the software "
                    "chops the capacity into chunks and scatters them, mirrored, "
                    "across all six nodes. No node holds a whole volume; every "
                    "node holds a piece of every volume. The protection engine "
                    "lights because the redundant copies are being laid down. "
                    "The scatter is slow so that the repair later can be fast: "
                    "it is the prepayment."
                ),
                expert=(
                    "Longest stage by design: capacity chunked and mirrored across all "
                    "nodes; no node holds a whole volume. The scatter prepays the "
                    "rebuild."
                ),
            ),
            camera=node_band,
            region_ids=[*_NODES, "protection"],
            layer_reveal=_SOFTWARE,
            trace_cursor=2,
            duration_ms=30_000,
        ),
        TourStep(
            id="coordinator-dark",
            title="Steady reads and writes, with the manager dark",
            script=L(
                novice=(
                    "Now real work arrives — reading and writing, which storage "
                    "people call I/O, short for input and output. Each client "
                    "was handed the map of "
                    "where the chunks live, so it talks straight to the servers "
                    "that hold its data, all of them at once, with nothing in "
                    "between. There is no queue in front of one special machine, "
                    "so the total speed is the sum of what the servers can do. "
                    "In this illustrative timeline each server handles about 300 "
                    "thousand operations per second, so this small pool of six "
                    "runs about 1.8 million; Dell quotes up to 240 million "
                    "for a very large one. Now look at the corner: the metadata "
                    "manager has gone dark. It handed out the map and stepped out "
                    "of the way."
                ),
                standard=(
                    "Load arrives. Each client holds the chunk map, so it "
                    "addresses every node directly and at once; there is no "
                    "controller queue and no shared path, and aggregate "
                    "throughput is simply the sum of the servers. Six nodes at "
                    "300 thousand each make this pool's "
                    "about 1.8 million IOPS (input/output operations per second, "
                    "illustrative); Dell's published ceiling for a large pool is "
                    "240 million. Notice the corner: the metadata manager is dark "
                    "during steady I/O, because a coordinator in the data path "
                    "would be a controller by another name."
                ),
                expert=(
                    "Steady I/O: full client-to-node fan-out, throughput sums "
                    "across nodes (6 x 300k = ~1.8M IOPS illustrative; Dell quotes 240M at scale). MDM "
                    "dark, out of the data path."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[*_NODES, "clients", "fabric"],
            layer_reveal=_SOFTWARE,
            trace_cursor=4,
            duration_ms=28_000,
        ),
        TourStep(
            id="a-node-dies",
            title="A node dies, and the clients carry on",
            script=L(
                novice=(
                    "Node 6 stops answering: a failed power supply, a dead "
                    "motherboard, somebody pulling the wrong cable. In a "
                    "controller-based system this is the dramatic moment, when "
                    "work switches over to a partner and the applications can "
                    "feel a pause. Here the clients simply stop talking to one "
                    "address and carry on with the other five, because a second "
                    "copy of everything node 6 held was already on those five. "
                    "Requests that were on their way to node 6 wait a few seconds "
                    "and go to the other copy instead. Speed falls by the lost "
                    "server's share, one sixth, to 1.5 million operations per "
                    "second in this illustrative timeline, and never reaches "
                    "zero. Protection has really fallen, "
                    "though: some chunks now have only one copy, and a second "
                    "failure before the repair would lose data."
                ),
                standard=(
                    "Node 6 stops answering. In a controller array this is "
                    "failover, with path renegotiation and a pause applications "
                    "feel. Here the clients drop one address and keep going "
                    "against the other five, because the second copy of "
                    "everything node 6 held was already resident there. "
                    "Requests in flight to node 6 wait out a timeout of a few "
                    "seconds and are retried against the other copy. Throughput "
                    "dips by the lost node's share, one sixth, to 1.5 million "
                    "IOPS in this illustrative trace, and never reaches zero. "
                    "Protection has "
                    "genuinely fallen: chunks that had two copies now have one, "
                    "so the metadata manager and the protection engine wake to "
                    "decide the repair."
                ),
                expert=(
                    "Node loss: no controller failover; I/O to the dead node's "
                    "chunks stalls for a timeout (seconds) until the MDM cluster "
                    "remaps, below this trace's resolution. IOPS 5/6 (1.5M), never "
                    "zero. Redundancy single-copy; MDM and protection engine "
                    "engage."
                ),
            ),
            # Whole map: the clients carrying on are half of this beat.
            camera=whole_map(anatomy),
            region_ids=[*_SURVIVORS, "clients", "mdm", "protection"],
            layer_reveal=_SOFTWARE,
            trace_cursor=5,
            duration_ms=28_000,
        ),
        TourStep(
            id="every-survivor-rebuilds",
            title="Every survivor rebuilds at once",
            script=L(
                novice=(
                    "This is the reason the design exists. Node 6's data was never "
                    "kept on one partner machine; it was in fragments spread "
                    "across all five survivors. So the repair is many-to-many: "
                    "each of the five rebuilds a fifth of what was lost, reading "
                    "from the other four, all at the same time. The web of lines "
                    "between the servers is that repair. Every server helps and "
                    "none just watches, and the count of servers rebuilding always "
                    "equals the count still running. Meanwhile the clients keep "
                    "working at well over two-thirds of full speed."
                ),
                standard=(
                    "The reason this architecture exists. Node 6's data was not "
                    "on one partner device; it was in fragments across all five "
                    "survivors. So the rebuild is many-to-many: each survivor "
                    "reconstructs a fifth of the loss, reading from the other "
                    "four, simultaneously. The mesh drawn between the nodes is "
                    "that traffic. The rebuild-participants counter shows it: "
                    "nodes rebuilding equals nodes online, never a subset. A "
                    "controller array also spreads a drive rebuild over many "
                    "drives, but all of it runs through one controller pair, "
                    "and that pair's fixed budget caps the rate at any scale. "
                    "Here the budget grows with the survivors. Client I/O "
                    "gives a little to the rebuild load and stays above 70 "
                    "percent of steady throughout."
                ),
                expert=(
                    "Many-to-many rebuild: rebuild participants == nodes online "
                    "(5/5), each reconstructing 1/n from the rest. Client I/O "
                    "held above 0.7x steady."
                ),
            ),
            camera=node_band,
            region_ids=[*_SURVIVORS, "protection"],
            layer_reveal=_SOFTWARE,
            trace_cursor=6,
            duration_ms=36_000,
        ),
        TourStep(
            id="faster-with-scale",
            title="Faster as the pool grows",
            script=L(
                novice=(
                    "Every chunk has its full protection again, now spread over "
                    "five servers instead of six. Nothing came back from a backup, "
                    "no spare drive was swapped in, and nobody was woken in the "
                    "night. The new copies went into empty space the pool keeps "
                    "in reserve, about one server's worth; a pool filled past "
                    "that reserve would stay under-protected until space was "
                    "added. Now run the arithmetic forward. In a hundred-server "
                    "pool about a hundred survivors would each rebuild a "
                    "hundredth of the lost machine. That is twenty times more "
                    "helpers than the five here, so the repair would be roughly "
                    "twenty times faster. Recovery "
                    "gets quicker as the system grows, the reverse of how storage "
                    "normally ages. That is also why building the pool, not "
                    "repairing it, was the long stage. The arithmetic does not go "
                    "on forever, though: in a real pool the repair is deliberately "
                    "held back so it does not eat the speed the clients are still "
                    "using, and past a certain size the network, not the number of "
                    "helpers, decides how fast it can go."
                ),
                standard=(
                    "Full protection is back, redistributed across five nodes "
                    "instead of six: no backup restored, no spare drive swapped "
                    "in, no one paged. The rebuild landed in spare capacity the "
                    "pool keeps reserved, about one node's worth; a pool filled "
                    "past that reserve stays degraded until capacity is added. "
                    "Now scale the arithmetic. In a hundred-node pool about a "
                    "hundred survivors share the same job, so recovery is "
                    "roughly twenty times faster than with the five survivors "
                    "here. "
                    "Rebuild time falls as the pool grows, the reverse of how "
                    "storage usually ages, and it is why the scatter, not the "
                    "repair, was the longest stage. The one-over-n arithmetic "
                    "holds until something else binds: PowerFlex throttles "
                    "rebuild and rebalance traffic on purpose so the repair does "
                    "not eat the front-end I/O — the dip to 1,380k a step ago is "
                    "that throttle at work — and at large scale the fabric and "
                    "the spare capacity's write bandwidth bind before the count "
                    "of participants does. Dell has quoted mirrored "
                    "pools from three nodes to past two thousand."
                ),
                expert=(
                    "Redundancy restored on n-1 into reserved spare capacity (~one "
                    "node's worth; without it, degraded until capacity is added). "
                    "MTTR scales ~1/n: 100 nodes rebuild ~20x faster than 5 — "
                    "until the rebuild QoS throttle or the fabric binds (the "
                    "throttle is the 1,380k dip), and spare-capacity write "
                    "bandwidth caps it at scale. "
                    "Scatter, not repair, is the longest stage. Dell-quoted: 3 to 2,000+ nodes."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[*_SURVIVORS, "clients", "fabric"],
            layer_reveal=_SOFTWARE,
            trace_cursor=7,
            duration_ms=30_000,
        ),
        TourStep(
            id="reassemble",
            title="One fewer server, no drama",
            script=L(
                novice=(
                    "Back to ordinary work, one server short. Losing a machine "
                    "cost that machine's share of the speed, which comes back when "
                    "a replacement is added, and needed nobody's attention. The same trick handles the pleasant version of "
                    "the story: to replace ageing hardware, add new servers, let "
                    "the pool spread onto them, then take the old ones out, with "
                    "everything running the whole time. The health data flows to "
                    "Dell's CloudIQ monitoring service, another twin here. The "
                    "SN6000 twin tells the same story from the network's side: "
                    "the network is part of the storage design. Press play on the Pool in motion page to walk the "
                    "same sequence step by step."
                ),
                standard=(
                    "Steady again, one server short. The episode cost one "
                    "node's share of the throughput, which returns when a "
                    "replacement is added, and no one's attention. The "
                    "same rebalance machinery turns a hardware refresh into a "
                    "background task: add nodes, let the pool rebalance, remove "
                    "the old ones, hosts running throughout. Telemetry feeds the "
                    "CloudIQ twin, and because the pool runs over the IP fabric, "
                    "fabric design is a storage decision; the SN6000 twin "
                    "makes that case from the network's side. PowerStore and PowerMax show "
                    "what it takes to make a controller safe; this design "
                    "removes it. Pool in motion walks the same trace step by step."
                ),
                expert=(
                    "Steady on n-1 at 5/6 throughput. Refresh via add, rebalance, drain, remove; "
                    "no host-visible events. Telemetry to CloudIQ. The controller "
                    "twins harden the centre; this deletes it."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[*_SURVIVORS, "clients", "fabric", "mgmt"],
            layer_reveal=_HARDWARE,
            trace_cursor=8,
            duration_ms=28_000,
        ),
    ]

    return Tour(
        id="powerflex-tour",
        title="A storage pool with no middle",
        intro=L(
            novice=(
                "A guided walk through a PowerFlex pool as it is built, loaded, "
                "loses a server and heals, narrated beat by beat. Sit back and "
                "watch, or pause and click anything to look closer; the tour "
                "waits for you."
            ),
            standard=(
                "A narrated walk through a PowerFlex pool: built, loaded, "
                "wounded and healed. Watch it play, or pause and explore; Resume "
                "tour brings the camera back."
            ),
            expert="Narrated build, load, failure and rebuild. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=_photos(),
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: ClusterAnatomy) -> TourResponse:
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
