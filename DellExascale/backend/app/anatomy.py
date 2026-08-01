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
    "throughput is the *sum* of the servers rather than the ceiling of any "
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
            x=44, y=y0, w=22, h=11, description=_DATA_DESC,
        ),
        PlatformRegion(
            id=f"media-{d}", kind="media", label="NVMe",
            x=68, y=y0, w=12, h=11, description=_MEDIA_DESC,
        ),
    ]


ANATOMY = PlatformAnatomy(
    id="exascale",
    name="Exascale Storage + Lightning File System",
    vendor="Dell Technologies",
    form_factor="Unified storage rack — block, file, parallel file, object",
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
            "Dell Exascale Storage with the Lightning File System: parallel NFS "
            "on PowerScale's OneFS, with a metadata server and Flex Files "
            "layouts, unifying block, file, and object in one rack at roughly 6 "
            "TB/s. The contrast with PowerStore and PowerMax is the point — "
            "those move every byte through a controller, and that controller's "
            "ceiling is the system's. Here the client asks the metadata server "
            "once where the stripes live, then reads straight from every data "
            "server at once. The metadata server never appears in the bulk data "
            "phases, which the tests assert, and the geometry puts it above the "
            "data band rather than within it."
        ),
        standard=(
            "Dell's Lightning File System is the production form of Project "
            "Lightning: a parallel file system built on PowerScale's OneFS, "
            "using pNFS (parallel NFS) with a metadata server and Flex Files "
            "layouts, which Dell positions as the fastest parallel file system "
            "available — up to 6× the large-file performance of the previous "
            "NFS stack. Exascale Storage is the rack that unifies the engines: "
            "PowerFlex for block, PowerScale and Lightning for file, "
            "ObjectScale for object, in one footprint delivering on the order "
            "of 6 TB/s. The architecture's central move is visible on this map. "
            "A client asks the metadata server exactly one question — where do "
            "this file's stripes live? — and from then on reads straight from "
            "every data server at once, with the metadata server out of the "
            "path. Throughput becomes the sum of the servers instead of the "
            "ceiling of a controller, which is the only way to keep thousands "
            "of GPUs fed. The layout is a stylized mental model; a real rack "
            "holds many more data servers than the four drawn."
        ),
        technical=(
            "Exascale with Lightning File System — pNFS on OneFS, MDS plus Flex "
            "Files layouts; block (PowerFlex), file, and object (ObjectScale) "
            "unified per rack at ~6 TB/s. Phase order mount → layout → stripe → "
            "feed → checkpoint → tier → steady. Asserted: the metadata region "
            "is active in exactly {mount, layout} and absent from every bulk "
            "phase — the twin's reason for existing; layout precedes data and "
            "is never lost mid-job; nonzero throughput implies all four data "
            "servers streaming; peak ≥48,000 Gbps; checkpoint burst holds max "
            "dwell. Geometry pins the MDS above the data-server band."
        ),
        expert=(
            "pNFS over OneFS with MDS and Flex Files layouts; ~6 TB/s per rack, "
            "block/file/object unified. Metadata active in exactly {mount, "
            "layout}, absent from all bulk phases — asserted, and pinned "
            "geometrically above the data band. Throughput requires full "
            "four-way fan-out. Checkpoint burst holds max dwell."
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
            id="metadata", kind="metadata", label="Lightning metadata server",
            x=33, y=1, w=42, h=10,
            description=(
                "The metadata server — and the twin's central lesson. It "
                "answers one question per file set: where do the stripes "
                "live? It hands the client a Flex Files layout and then "
                "leaves the conversation; the bulk transfer that follows "
                "never touches it. That is why it is drawn above the data "
                "path rather than on it, and why it stays dark through "
                "every bulk phase of the trace. It could be restarted "
                "mid-read without interrupting a transfer. Contrast the "
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
        *_data_server(2, 26),
        *_data_server(3, 38),
        *_data_server(4, 50),
        PlatformRegion(
            id="protocol-file", kind="protocol", label="File — PowerScale / Lightning",
            x=1, y=51, w=30, h=8,
            description=(
                "The file engines. PowerScale's OneFS provides the "
                "conventional NFS and SMB namespace an enterprise already "
                "knows; Lightning adds the parallel pNFS path on the same "
                "foundation for the AI read pattern. Sharing a foundation "
                "matters: data prepared through the ordinary file interface "
                "is immediately readable at parallel speed without being "
                "copied into a second system."
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
                "*arrive* as objects; keeping the object tier in the same "
                "rack as the file tier means the first step of every "
                "pipeline stops being a petabyte-scale copy."
            ),
        ),
        PlatformRegion(
            id="protocol-block", kind="protocol", label="Block — PowerFlex",
            x=33, y=61, w=30, h=8,
            description=(
                "The block engine: PowerFlex, software-defined block "
                "storage, which is why an Exascale rack serves demanding "
                "conventional enterprise workloads as well as AI. Its "
                "presence is what turns a specialist AI appliance into "
                "consolidated infrastructure — the databases beside the "
                "training job get first-class storage from the same rack."
            ),
        ),
        PlatformRegion(
            id="mgmt", kind="management", label="Management & telemetry",
            x=65, y=61, w=34, h=8,
            description=(
                "The control plane over the unified rack: provisioning "
                "across all four engines, capacity and performance "
                "telemetry, and the AIOps feed this repo's CloudIQ twin "
                "consumes. Consolidation's real payoff shows here — one "
                "place to answer 'is storage the reason the GPUs are "
                "idle?', a question that is genuinely hard when block, "
                "file, and object live in three separate products."
            ),
        ),
    ],
    stats=[
        Stat(label="Throughput", value="~6 TB/s per Exascale rack"),
        Stat(label="Parallel path", value="pNFS + Flex Files layouts (Lightning FS)"),
        Stat(label="Lightning gain", value="Up to 6× large-file vs prior NFS stack"),
        Stat(label="Engines in one rack", value="Block, file, parallel file, object"),
        Stat(label="Block", value="PowerFlex (software-defined)"),
        Stat(label="File", value="PowerScale OneFS + Lightning parallel"),
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
            label="Dell Technologies World 2026 announcements",
            url="https://www.dell.com/en-us/blog/dell-technologies-world-2026-enterprise-ai-announcements-this-week/",
        ),
    ],
)
