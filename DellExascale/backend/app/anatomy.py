"""Platform anatomy data: the Exascale + Lightning data path, annotated.

Like the other twins, the layout is *data*, not code: regions placed in a
normalized coordinate space the frontend renders as SVG. Geometry is
stylized — favor a correct mental model over rack accuracy (project scope
guardrail).

The view is a left→right data path (the convention the CloudIQ and
PowerProtect twins use): GPU clients on the left, the scale-out fabric,
then the split that defines a parallel file system — the metadata server
sitting *above* the path on its own, and the four data servers carrying the
actual bytes straight through the middle. The multi-protocol engines and
NVMe media sit behind the data servers, with the management plane along the
bottom.

The metadata server is drawn deliberately off the horizontal centerline and
smaller than the data servers: it is architecturally beside the data path,
not on it, and it is the one component whose *absence* from most of the
trace is the lesson.
"""

from __future__ import annotations

from .leveling import L
from .models import Photo, PlatformAnatomy, PlatformRegion, SourceLink, Stat

# The only shipped visual is a self-contained schematic drawn for this
# project — not a Dell product image — with an honest credit line.
PATH_ILLO = Photo(
    url="/exascale-path.svg",
    caption=(
        "The parallel data path: clients ask the metadata server once for a "
        "layout, then stream stripes straight from every data server at "
        "the same time — the metadata server out of the path entirely."
    ),
    credit="Schematic illustration by this project — not a Dell product image",
)

_DATA_DESC = (
    "A data server — one of the many nodes that actually hold and serve "
    "the file's stripes. Under pNFS Flex Files, the client talks to these "
    "directly and simultaneously once it holds a layout, so aggregate "
    "throughput is the sum of the servers rather than the ceiling of any "
    "controller. This is the architectural difference from the block twins "
    "in this repo: PowerStore and PowerMax route every byte through a "
    "director or node pair; here, adding servers adds bandwidth, which is "
    "how a rack reaches multiple terabytes per second."
)

_MEDIA_DESC = (
    "The NVMe flash behind a data server. Capacity matters less here than "
    "concurrency: an AI read pattern is thousands of GPUs pulling different "
    "stripes of different files at once, so the media is chosen for "
    "parallel small-and-large mixed IO, and the data servers stripe across "
    "it so no single device becomes a hot spot."
)


def _data_server(idx: int, y0: float) -> list[PlatformRegion]:
    d = f"ds{idx}"
    return [
        PlatformRegion(
            id=f"data-{d}", kind="dataserver", label=f"Data server {idx}",
            x=44, y=y0, w=22, h=10, description=_DATA_DESC,
        ),
        PlatformRegion(
            id=f"media-{d}", kind="media", label="NVMe",
            x=68, y=y0, w=12, h=10, description=_MEDIA_DESC,
        ),
    ]


ANATOMY = PlatformAnatomy(
    id="exascale",
    name="Exascale Storage + Lightning File System",
    vendor="Dell Technologies",
    form_factor="Unified storage rack — file, parallel file, object (block planned)",
    generation="Dell AI Data Platform (Lightning FS · Exascale Storage)",
    year=2026,
    width=100,
    height=72,
    overview=L(
        novice=(
            "Ordinary storage systems have a bottleneck built into them: every "
            "piece of data travels through one controller, so that controller's "
            "speed becomes the whole system's speed. A parallel file system "
            "refuses that arrangement. A client asks a single dedicated server "
            "one question — where are the pieces of this file? — and then reads "
            "directly from every storage server at once, all of them feeding it "
            "simultaneously. The server that answered the first question does "
            "not carry any of the data itself, which is why it is drawn above "
            "the others rather than in the middle of them. Watch the throughput "
            "figure and notice it is only ever high when all four storage "
            "servers are streaming together. One server alone cannot produce "
            "it."
        ),
        plain=(
            "Dell Exascale Storage runs PowerScale file, ObjectScale object, "
            "and the Lightning File System as software on the same PowerEdge "
            "servers; Dell quotes up to 6 TB/s of reads per rack, and plans to "
            "add PowerFlex block in 2027. The trace follows parallel NFS, the "
            "open standard PowerScale's OneFS ships, with a metadata server "
            "and Flex Files layouts; Lightning applies the same split with its "
            "own client. The contrast with PowerStore and PowerMax is the point — "
            "those move every byte through a controller, and that controller's "
            "ceiling is the system's. Here the client asks the metadata server "
            "once where the stripes live, then reads straight from every data "
            "server at once. The metadata server never appears in the bulk data "
            "phases, which the tests assert, and the geometry puts it above the "
            "data band rather than within it."
        ),
        standard=(
            "Dell Exascale Storage, announced in March 2026, runs three "
            "storage engines as software personalities on the same PowerEdge "
            "servers: PowerScale for file, ObjectScale for object, and the "
            "Lightning File System for parallel file. Dell targets PowerFlex "
            "block for the first half of 2027. Two parallel paths came out of "
            "Project Lightning. PowerScale's OneFS gained pNFS (parallel NFS) "
            "with a metadata server and Flex Files layouts, which Dell says "
            "reads large files up to 6× faster than NFSv3. The Lightning File "
            "System is a separate file system, not OneFS, with its own client "
            "software, metadata distributed across the system, and direct "
            "access to NVMe; Dell calls it the world's fastest parallel file "
            "system on its own internal analysis and quotes up to 6 TB/s of "
            "reads per rack. This twin narrates the pNFS form, because that "
            "protocol is public and names its parts, and both paths make the "
            "same central move, visible on this map. "
            "A client asks the metadata server exactly one question — where do "
            "this file's stripes live? — and from then on reads straight from "
            "every data server at once, with the metadata server out of the "
            "path. Throughput becomes the sum of the servers instead of the "
            "ceiling of a controller, which is the only way to keep thousands "
            "of GPUs fed. The layout is a stylized mental model; a real rack "
            "holds many more data servers than the four drawn."
        ),
        technical=(
            "Exascale: PowerScale, ObjectScale, and Lightning FS personalities "
            "on common PowerEdge nodes (PowerFlex block targeted 1H CY2027); "
            "Dell claims up to 6 TB/s reads per rack on the Lightning "
            "personality. The trace narrates the pNFS form OneFS ships — MDS "
            "plus Flex Files layouts; Lightning FS is a separate file system "
            "with its own client and distributed metadata, same off-path "
            "principle. Phase order mount → layout → stripe → "
            "feed → checkpoint → tier → steady. Asserted: the metadata region "
            "is active in exactly {mount, layout} and absent from every bulk "
            "phase — the twin's reason for existing; layout precedes data and "
            "is never lost mid-job; nonzero throughput implies all four data "
            "servers streaming; peak ≥48,000 Gbps; checkpoint burst holds max "
            "dwell. Geometry pins the MDS above the data-server band. The four "
            "data servers drawn stand in for the ~40 1U units Dell describes in "
            "a rack, so 6 TB/s is the rack figure, not four servers at 1.5 TB/s "
            "each."
        ),
        expert=(
            "Narrated as pNFS (MDS, Flex Files layouts, as in OneFS); "
            "Lightning FS is separate, own client. ~6 TB/s per rack is Dell's "
            "claim; file/object/parallel file unified, block planned 2027. "
            "Metadata active in exactly {mount, "
            "layout}, absent from all bulk phases — asserted, and pinned "
            "geometrically above the data band. Throughput requires full "
            "four-way fan-out — a property of the drawing, not the product: the "
            "4 servers drawn stand for ~40 1U units, so 6 TB/s is the rack "
            "figure, not 4 × 1.5 TB/s. Checkpoint burst holds max dwell."
        ),
    ),
    regions=[
        PlatformRegion(
            id="clients", kind="client", label="GPU compute racks",
            x=1, y=14, w=16, h=34,
            description=(
                "The readers: racks of GPUs — XE9712 systems in this repo's "
                "AI Factory — whose appetite defines the entire design. A "
                "training job reads batches continuously and writes "
                "checkpoints in bursts, and any second a GPU spends waiting "
                "on storage is a second of the most expensive hardware in "
                "the building doing nothing. With GPUDirect paths, data "
                "lands in GPU memory without a detour through host CPUs."
            ),
        ),
        PlatformRegion(
            id="fabric", kind="fabric", label="Scale-out fabric",
            x=19, y=14, w=12, h=34,
            description=(
                "The network between compute and storage — Spectrum-X "
                "Ethernet or InfiniBand, the subject of this repo's SN6000 "
                "twin. A parallel file system leans on it hard: because the "
                "client opens simultaneous streams to every data server, "
                "the read pattern is many-to-one by design, exactly the "
                "incast the fabric's congestion control exists to absorb. "
                "RDMA keeps the transfers off host CPUs."
            ),
        ),
        PlatformRegion(
            id="metadata", kind="metadata", label="Metadata server",
            x=33, y=1, w=42, h=10,
            description=(
                "The metadata server — and the twin's central lesson. It "
                "answers one question per file set: where do the stripes "
                "live? It hands the client a Flex Files layout and then "
                "leaves the conversation; the bulk transfer that follows "
                "never touches it. That is why it is drawn above the data "
                "path rather than on it, and why it stays dark through "
                "every bulk phase of the trace. It could be restarted "
                "mid-read without interrupting a transfer. One box is a "
                "simplification: in PowerScale's pNFS any node can take the "
                "metadata role, and the Lightning File System spreads "
                "metadata across the system. Contrast the "
                "block twins, where every byte crosses a controller: here, "
                "scaling reads means adding data servers, not a bigger "
                "brain."
            ),
        ),
        PlatformRegion(
            id="fanout", kind="fabric", label="Parallel stripe fan-out",
            x=33, y=14, w=9, h=34,
            description=(
                "The fan-out itself: one client request becoming "
                "simultaneous streams to every data server holding a stripe "
                "of the file. Striping is what makes a single large file "
                "readable at aggregate speed — no one server holds enough "
                "of it to be asked for all of it. The width of this "
                "fan-out, not the speed of any single component, is what "
                "sets the rack's throughput."
            ),
        ),
        *_data_server(1, 14),
        *_data_server(2, 25),
        *_data_server(3, 36),
        *_data_server(4, 47),
        PlatformRegion(
            id="protocol-file", kind="protocol", label="File — PowerScale / Lightning",
            x=1, y=51, w=30, h=8,
            description=(
                "The file engines. PowerScale's OneFS provides the "
                "conventional NFS and SMB namespace an enterprise already "
                "knows, and since OneFS 9.15 a parallel pNFS path to the "
                "same files. The Lightning File System is a separate "
                "engine, not OneFS: Dell positions it as the fastest tier, "
                "for short-lived training and inference data, with its own "
                "client software and direct access to NVMe. Both run as "
                "software on the same servers, so capacity can move "
                "between them as the work changes."
            ),
        ),
        PlatformRegion(
            id="protocol-object", kind="protocol", label="Object — ObjectScale",
            x=1, y=61, w=30, h=8,
            description=(
                "The object engine: S3-compatible storage for the raw "
                "corpus and the archive tail, scaling to multiple "
                "petabytes, with S3-over-RDMA paths so object data can feed "
                "preprocessing and training directly. Most AI corpora "
                "arrive as objects; keeping the object tier in the same "
                "rack as the file tier means the first step of every "
                "pipeline stops being a petabyte-scale copy."
            ),
        ),
        PlatformRegion(
            id="protocol-block", kind="protocol", label="Block — PowerFlex (planned)",
            x=33, y=61, w=30, h=8,
            description=(
                "The block engine: PowerFlex, software-defined block "
                "storage. Exascale launched without it; Dell targets "
                "PowerFlex as a fourth personality in the first half of "
                "2027, which is why this block never lights in the trace. "
                "Its arrival is what would turn a specialist AI rack into "
                "consolidated infrastructure, with the databases beside "
                "the training job served from the same hardware."
            ),
        ),
        PlatformRegion(
            id="mgmt", kind="management", label="Management & telemetry",
            x=65, y=61, w=34, h=8,
            description=(
                "The control plane over the unified rack: provisioning "
                "across every engine, capacity and performance "
                "telemetry, and the AIOps feed this repo's CloudIQ twin "
                "consumes. Consolidation's real payoff shows here — one "
                "place to answer 'is storage the reason the GPUs are "
                "idle?', a question that is genuinely hard when block, "
                "file, and object live in three separate products."
            ),
        ),
    ],
    stats=[
        Stat(label="Throughput", value="Up to 6 TB/s reads per rack (Dell's claim, Lightning personality)"),
        Stat(label="Path narrated here", value="pNFS + Flex Files layouts (PowerScale OneFS 9.15)"),
        Stat(label="PowerScale pNFS gain", value="Up to 6× on large files vs NFSv3 (Dell's claim)"),
        Stat(label="Lightning File System", value="Separate file system, own client; up to 150 GB/s per rack unit (Dell's claim)"),
        Stat(label="Engines in one rack", value="File, parallel file, object; block planned"),
        Stat(label="Block", value="PowerFlex — targeted 1H 2027"),
        Stat(label="Hardware", value="PowerEdge R7725xd first; up to 800 GbE per node"),
        Stat(label="File", value="PowerScale OneFS, NFS/SMB + pNFS"),
        Stat(label="Object", value="ObjectScale, S3 (with S3-over-RDMA)"),
        Stat(label="Client path", value="RDMA / GPUDirect — bypasses host CPUs"),
    ],
    photo=PATH_ILLO,
    sources=[
        SourceLink(
            label="Dell — Lightning: a new performance layer for AI infrastructure",
            url="https://www.dell.com/en-us/blog/lightning-a-new-performance-layer-for-ai-infrastructure/",
        ),
        SourceLink(
            label="Blocks & Files — PowerScale goes parallel (Project Lightning)",
            url="https://www.blocksandfiles.com/ai-ml/2025/11/17/dell-powerscale-gets-struck-by-lightning-and-goes-parallel/1711291",
        ),
        SourceLink(
            label="StorageReview — Lightning File System and Exascale Storage (GTC 2026)",
            url="https://www.storagereview.com/news/dell-expands-ai-factory-with-nvidia-at-gtc-2026-new-data-engines-lightning-file-system-and-exascale-storage",
        ),
        SourceLink(
            label="Dell press release, 16 March 2026 — Lightning FS, Exascale Storage, PowerScale pNFS claims and dates",
            url="https://www.prnewswire.com/news-releases/dell-ai-data-platform-with-nvidia-supercharges-enterprise-ai-with-breakthrough-data-orchestration-and-storage-innovations-302715096.html",
        ),
        SourceLink(
            label="Dell — Exascale 4-in-1 storage: personalities, R7725xd, 800 GbE, PowerFlex in 1H 2027",
            url="https://www.dell.com/en-us/blog/dell-ai-data-platform-introduces-only-4-in-1-storage-for-ai/",
        ),
        SourceLink(
            label="Blocks & Files — Lightning is not OneFS; 150 GB/s per 1U, 40 to a rack (March 2026)",
            url="https://www.blocksandfiles.com/ai-ml/2026/03/16/dells-ai-story-electrified-by-lightning/5209387",
        ),
        SourceLink(
            label="Unstructured Data Quick Tips (Dell engineer's blog) — pNFS generally available in OneFS 9.15",
            url="http://www.unstructureddatatips.com/powerscale-onefs-9-15/",
        ),
        SourceLink(
            label="Dell — PowerScale with pNFS: standard Linux clients, no custom driver",
            url="https://www.dell.com/en-us/blog/dell-powerscale-with-pnfs-parallel-performance-for-ai/",
        ),
    ],
)
