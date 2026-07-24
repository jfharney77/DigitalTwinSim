"""Pool anatomy data: a PowerFlex storage pool, annotated.

Like the other twins, the layout is *data*, not code: regions placed in a
normalized coordinate space the frontend renders as SVG. Geometry is
stylized — favor a correct mental model over rack accuracy (project scope
guardrail).

The drawing is organized to make an absence visible. Clients across the
top, the IP fabric beneath them, then a band of identical servers — and
that is the whole data path. There is no controller row, because there is
no controller. Every server in the band is the same as every other, holds
its share of every volume, and answers clients directly.

The metadata manager is in the diagram, but deliberately small and off in a
corner, and ``tests/test_anatomy.py`` pins it that way: it must be smaller
than any single storage node. It maps chunks to nodes and referees
failures; it does not carry data. Drawing it large would tell the reader
exactly the wrong thing about where the bytes go.

Six nodes are drawn. A real pool starts at three and runs past two
thousand, which is the scale at which the rebuild property below stops
being a nicety and becomes the reason to buy it.
"""

from __future__ import annotations

from .models import ClusterAnatomy, ClusterRegion, Photo, SourceLink, Stat

# The only shipped visual is a self-contained schematic drawn for this
# project — not a Dell product image — with an honest credit line.
POOL_ILLO = Photo(
    url="/powerflex-pool.svg",
    caption=(
        "A pool with no middle. Volumes are chopped into chunks and "
        "mirrored across every server, so a client reads straight from the "
        "nodes holding its data — and when a server dies, every survivor "
        "rebuilds a sliver at the same time."
    ),
    credit="Schematic illustration by this project — not a Dell product image",
)

_NODE_DESC = (
    "A server contributing its local NVMe drives to the pool. Every node "
    "in the band is identical in role: it stores a share of every volume, "
    "serves reads and writes to clients directly, and takes part in any "
    "rebuild. None of them is a controller and none is a spare. That "
    "uniformity is what makes the arithmetic work — adding a server adds "
    "capacity, adds throughput, and adds one more participant to every "
    "future recovery, all at once. In a hyperconverged deployment this same "
    "server also runs the applications consuming the storage; in a "
    "two-layer deployment it does nothing else."
)

_NODE_X = [2, 18, 34, 50, 66, 82]


def _node(idx: int, x0: float) -> ClusterRegion:
    return ClusterRegion(
        id=f"node-{idx}", kind="node", label=f"Node {idx}",
        x=x0, y=24, w=15, h=18, description=_NODE_DESC,
    )


ANATOMY = ClusterAnatomy(
    id="powerflex",
    name="Dell PowerFlex — software-defined block storage pool",
    vendor="Dell Technologies",
    form_factor="Server-based block storage over an IP fabric",
    generation="PowerFlex 5.0 Ultra — scalable availability engine, erasure coding",
    year=2026,
    width=100,
    height=55,
    overview=(
        "PowerFlex turns a set of ordinary servers into shared block "
        "storage: each contributes its local NVMe, the software chops every "
        "volume into chunks and scatters them — mirrored — across all of "
        "them, and clients read and write straight to the servers holding "
        "the chunks they want. Scale runs from three nodes to more than two "
        "thousand, and past 240 million operations per second. What is "
        "worth noticing in this diagram is what is not in it. There is no "
        "controller row. PowerStore and PowerMax, both twinned elsewhere in "
        "this repo, are built around controllers that every byte passes "
        "through, and most of their engineering goes into making that "
        "centrality safe. Here the centre was removed instead. The payoff "
        "arrives when a server dies: rather than one surviving controller "
        "grinding through a rebuild for hours, every remaining node "
        "reconstructs a sliver simultaneously, reading from every other "
        "node. Recovery therefore gets *faster* as the cluster grows, which "
        "is the opposite of how storage systems usually age. Six nodes are "
        "drawn; the layout is a stylized mental model."
    ),
    regions=[
        ClusterRegion(
            id="clients", kind="client", label="Storage data clients",
            x=2, y=2, w=96, h=9,
            description=(
                "The servers consuming storage. Each runs a lightweight "
                "client that presents pool volumes as ordinary block "
                "devices to whatever is above — a hypervisor, a database, "
                "a container platform. The important thing about this "
                "client is what it knows: it holds the map of which nodes "
                "hold which chunks, so it issues each read and write "
                "straight to the servers that can answer it. No request is "
                "forwarded through an intermediary. That is the mechanical "
                "reason there is no controller bottleneck here — not that "
                "the controller is fast, but that the client never talks "
                "to one."
            ),
        ),
        ClusterRegion(
            id="fabric", kind="network", label="IP fabric",
            x=2, y=14, w=96, h=7,
            description=(
                "Ordinary IP networking, and the substitution that defines "
                "the product category. A traditional storage array needs a "
                "storage-area network — dedicated switches, dedicated "
                "adapters, a separate skill set. PowerFlex runs its pool "
                "over the same Ethernet the servers already use. The "
                "consequence is that the network stops being plumbing and "
                "becomes part of the storage system's performance "
                "envelope: every read that crosses the fabric competes "
                "with everything else on it, so the fabric design is a "
                "storage design decision. This repo's SN6000 twin is the "
                "same lesson from the network's side."
            ),
        ),
        *[_node(i + 1, x) for i, x in enumerate(_NODE_X)],
        ClusterRegion(
            id="mdm", kind="coordinator", label="Metadata manager",
            x=2, y=45, w=12, h=8,
            description=(
                "The referee, drawn small on purpose. The metadata manager "
                "keeps the map of which chunks live on which nodes, hands "
                "that map to clients, notices when a node stops answering, "
                "and decides what the cluster does about it. What it never "
                "does is carry data. A read does not pass through it, a "
                "write does not wait on it, and its throughput is not part "
                "of anyone's performance calculation. It is genuinely a "
                "control plane rather than a controller, and the difference "
                "between those two words is the entire architecture. If "
                "this block were drawn as large as a node, the diagram "
                "would be telling you something false."
            ),
        ),
        ClusterRegion(
            id="protection", kind="protection", label="Protection & rebuild engine",
            x=17, y=45, w=40, h=8,
            description=(
                "How the pool survives losing hardware. Every chunk exists "
                "in more than one place — classically as a mirror, and in "
                "PowerFlex 5.0 Ultra also via erasure coding, which stores "
                "mathematical parity instead of a full second copy and so "
                "costs far less capacity for comparable protection. The "
                "part worth watching is the rebuild. Because the lost "
                "node's data lives in fragments spread over every other "
                "node, the reconstruction is many-to-many: in a hundred-"
                "node cluster, a hundred nodes each rebuild a hundredth of "
                "the loss, in parallel, reading from each other. Compare a "
                "controller array, where one device reads and one device "
                "writes for hours while the system sits at reduced "
                "protection. Fault sets let you tell the software which "
                "nodes share a rack or a power feed, so it never places "
                "both copies of anything in the same thing that can fail."
            ),
        ),
        ClusterRegion(
            id="mgmt", kind="management", label="Lifecycle & telemetry",
            x=60, y=45, w=38, h=8,
            description=(
                "Lifecycle management for a system whose parts are "
                "ordinary servers. The operation this architecture is "
                "unusually good at is replacement: add new nodes, let the "
                "pool rebalance onto them, then remove the old ones — all "
                "while hosts keep running, without so much as a dropped "
                "path. A hardware refresh stops being a migration project "
                "and becomes a background task. Telemetry feeds this "
                "repo's CloudIQ twin, which is where a slowly failing "
                "drive in one of two thousand nodes actually gets noticed."
            ),
        ),
    ],
    stats=[
        Stat(label="Architecture", value="Server-based; no controller tier"),
        Stat(label="Scale", value="3 to 2,000+ nodes"),
        Stat(label="Performance", value="Up to 240 million IOPS"),
        Stat(label="Transport", value="IP fabric — no dedicated storage network"),
        Stat(label="Protection", value="Mesh mirroring and erasure coding"),
        Stat(label="Rebuild", value="Many-to-many; every surviving node takes part"),
        Stat(label="Deployment", value="Two-layer or hyperconverged"),
        Stat(label="Release", value="PowerFlex 5.0 Ultra — scalable availability engine"),
    ],
    photo=POOL_ILLO,
    sources=[
        SourceLink(
            label="Dell PowerFlex — software-defined infrastructure",
            url="https://www.dell.com/en-us/shop/powerflex/sf/powerflex",
        ),
        SourceLink(
            label="Dell PowerFlex technical overview — rebuild",
            url="https://www.dell.com/support/manuals/en-us/scaleio/flex-software-to-45x/rebuild",
        ),
        SourceLink(
            label="Introducing Dell PowerFlex 5.0 Ultra (WWT)",
            url="https://www.wwt.com/blog/introducing-dell-powerflex-5-dot-0-ultra-a-new-era-in-software-defined-storage",
        ),
        SourceLink(
            label="Dell Technologies reimagines the modern data center for the AI era (May 2026)",
            url="https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2026~05~dell-technologies-reimagines-the-modern-data-center-for-the-ai-era.htm",
        ),
    ],
)
