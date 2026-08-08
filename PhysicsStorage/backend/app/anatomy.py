"""Product maps for the storage simulator — six compact architecture
diagrams, painted by *load* (utilization / fill / hit rate) rather than
temperature. Each map's region ids key the engine's ``region_load``.
The geometry carries each product's argument: controllers on top of the
media for the arrays, a flat node band for scale-out, the network as a
first-class block for PowerFlex, four partitioned pools for Exascale.
"""

from __future__ import annotations

from .leveling import L
from .models import MapRegion, ProductMap


def _clients(w: float = 96) -> MapRegion:
    return MapRegion(
        id="clients", kind="client", label="Hosts / clients",
        x=2, y=1, w=w, h=8,
        description=(
            "The demand side — the workload generator's dials live "
            "here. Everything below exists to answer these hosts "
            "inside their latency budget."
        ),
    )


POWERSTORE = ProductMap(
    id="powerstore",
    name="PowerStore · dual-controller all-NVMe array",
    vendor="Dell Technologies",
    form_factor="2U appliance — architecture view",
    generation="PowerStore T/Q class",
    year=2024,
    width=100,
    height=52,
    overview=L(
        novice=(
            "A classic storage array: two controller computers share one "
            "shelf of NVMe drives, and every byte passes through one of "
            "them. That pair is the machine's ceiling — as demand "
            "approaches what the controllers can do, response time "
            "climbs a curve that starts gentle and ends vertical (the "
            "'knee'). Lose one controller and the survivor carries "
            "everything: the array stays up, but the knee arrives at "
            "half the demand. Finding that knee, and moving it, is most "
            "of what storage sizing means."
        ),
        standard=(
            "The mid-range reference architecture: an active/active "
            "controller pair over a shared NVMe shelf, inline "
            "dedupe/compression always on. The knee — service latency "
            "× 1/(1−ρ) — is the core instrument; controller failover "
            "halves front-end capability and visibly moves the knee "
            "left at unchanged demand. Contrast with PowerScale/"
            "PowerFlex, where the ceiling is a sum instead of a pair. "
            "The narrated companion is the DellPowerStore twin (:5175)."
        ),
        expert=(
            "Dual-controller ceiling; ρ = demand/pair. Failover → "
            "frontend ×0.5 → knee at half demand. Inline DRR in the "
            "effective-capacity line. The scale-out apps argue with "
            "this diagram."
        ),
    ),
    regions=[
        _clients(),
        MapRegion(
            id="ctrl-a", kind="controller", label="Controller A",
            x=2, y=12, w=46, h=12,
            description=(
                "One of the active/active pair. Its utilization is the ρ "
                "in the latency curve; the knee is where this block's "
                "color goes hot."
            ),
        ),
        MapRegion(
            id="ctrl-b", kind="controller", label="Controller B",
            x=52, y=12, w=46, h=12,
            description=(
                "The partner controller. Fail it (event) and this block "
                "goes dark while A carries everything — service "
                "continues, the knee moves left."
            ),
        ),
        MapRegion(
            id="cache", kind="cache", label="DRAM / NVRAM cache",
            x=2, y=27, w=96, h=8,
            description=(
                "The cache the working-set slider fills. Hits cost "
                "~0.05 ms; misses pay the media. Its color is the hit "
                "rate."
            ),
        ),
        MapRegion(
            id="media", kind="media", label="NVMe drive shelf",
            x=2, y=38, w=96, h=12,
            description=(
                "25 NVMe slots, dual-ported to both controllers. Colored "
                "by capacity fill — the snapshot-bill scenario is "
                "watched here."
            ),
        ),
    ],
    sources=[
        {"label": "physics_specs/02-storage-platforms.md (this repo)",
         "url": "../physics_specs/02-storage-platforms.md"},
        {"label": "DellPowerStore twin — the same array's power-on story",
         "url": "http://localhost:5175/"},
    ],
)


POWERMAX = ProductMap(
    id="powermax",
    name="PowerMax · high-end enterprise array",
    vendor="Dell Technologies",
    form_factor="Rack-scale — architecture view",
    generation="PowerMax 2500/8500",
    year=2024,
    width=100,
    height=52,
    overview=L(
        novice=(
            "The bank-vault tier of storage. Many director computers "
            "share the work, so a component failing causes a brief "
            "stumble in response time rather than an outage — kill "
            "things repeatedly and watch it degrade without going down. "
            "Its second lesson is about distance: if every write must "
            "also land at a second site before it counts, light itself "
            "becomes the delay — a hundredth of a millisecond per "
            "kilometer, doubled for the round trip. That is why "
            "synchronous disaster protection has a radius."
        ),
        standard=(
            "The extreme-availability personality: component failures "
            "produce decaying latency blips, never zeros — the "
            "six-nines mindset as a trace. The replication physics is "
            "the star: sync SRDF adds distance × 0.01 ms/km × 2 to "
            "every write (a speed-of-light fact, not an estimate), so "
            "the distance slider turns geography into latency; async "
            "mode trades that for an RPO that grows whenever write "
            "bursts outrun the link. The DellPowerMax twin (:5178) "
            "narrates the same machine's bring-up."
        ),
        expert=(
            "Blip-not-outage failure model. Sync: +d×0.01×2 ms on "
            "writes — c in fiber, non-negotiable. Async: RPO = "
            "backlog/link, grows under bursts. Geography is the "
            "config."
        ),
    ),
    regions=[
        _clients(),
        MapRegion(
            id="directors", kind="controller", label="Director complex",
            x=2, y=12, w=62, h=12,
            description=(
                "Many directors sharing front-end work — the reason a "
                "failure is a blip here and a halving on PowerStore."
            ),
        ),
        MapRegion(
            id="srdf", kind="replication", label="SRDF link",
            x=68, y=12, w=30, h=12,
            description=(
                "The replication port to the partner array. Sync mode "
                "puts the site distance inside every write's latency; "
                "async mode buffers here and pays in RPO."
            ),
        ),
        MapRegion(
            id="gmem", kind="cache", label="Global memory",
            x=2, y=27, w=96, h=8,
            description="The shared cache every director reads through.",
        ),
        MapRegion(
            id="media", kind="media", label="NVMe DMEs",
            x=2, y=38, w=96, h=12,
            description="Drive enclosures behind the directors, colored by fill.",
        ),
    ],
    sources=[
        {"label": "physics_specs/02-storage-platforms.md (this repo)",
         "url": "../physics_specs/02-storage-platforms.md"},
        {"label": "DellPowerMax twin", "url": "http://localhost:5178/"},
    ],
)


def _scaleout_map(
    map_id: str, name: str, gen: str, node_desc: str, ns_desc: str,
    overview: str, extra_sources: list[dict[str, str]],
) -> ProductMap:
    return ProductMap(
        id=map_id,
        name=name,
        vendor="Dell Technologies",
        form_factor="Scale-out cluster — architecture view",
        generation=gen,
        year=2025,
        width=100,
        height=52,
        overview=overview,
        regions=[
            _clients(),
            MapRegion(
                id="namespace", kind="namespace", label=(
                    "One namespace" if map_id == "powerscale" else "Buckets (S3)"
                ),
                x=2, y=12, w=96, h=7,
                description=ns_desc,
            ),
            MapRegion(
                id="network", kind="network", label="Cluster network",
                x=2, y=22, w=96, h=6,
                description=(
                    "The east-west fabric the nodes coordinate and "
                    "rebuild across."
                ),
            ),
            MapRegion(
                id="nodes", kind="node", label="Node band (identical nodes)",
                x=2, y=31, w=96, h=10,
                description=node_desc,
            ),
            MapRegion(
                id="media", kind="media", label="Per-node media",
                x=2, y=44, w=96, h=7,
                description="Every node's local drives — capacity and performance arrive together.",
            ),
        ],
        sources=[
            {"label": "physics_specs/02-storage-platforms.md (this repo)",
             "url": "../physics_specs/02-storage-platforms.md"},
            *extra_sources,
        ],
    )


POWERSCALE = _scaleout_map(
    "powerscale",
    "PowerScale · scale-out NAS",
    "OneFS F/H/A series",
    (
        "Identical nodes, each adding capacity AND performance — the "
        "anti-monolith. More nodes also mean faster rebuilds, the "
        "exact opposite of a controller array."
    ),
    (
        "One file system across every node — no volumes to plan, no "
        "migration when a node joins. The DellPowerScale twin's whole "
        "argument, as a load-painted strip."
    ),
    L(
        novice=(
            "Storage built like a chorus instead of a soloist: every "
            "node is identical, and adding one adds both space and "
            "speed. When a drive dies, the whole cluster rebuilds it "
            "together — so a bigger cluster heals faster, which is "
            "exactly backwards from a traditional array and the best "
            "reason to build this way. All the nodes present one "
            "shared file system, so growth never means reorganizing."
        ),
        standard=(
            "Scale-OUT: per-node contribution × node count, minus a "
            "small coordination tax (~2%/node beyond 10) — near-linear "
            "to dozens of nodes. Rebuilds are cluster-wide and speed "
            "up with membership (rate × surviving nodes), inverting "
            "the controller-array story; the protection-level choice "
            "(EC 8+2 vs 16+4) trades overhead for survivable "
            "failures. Companion: DellPowerScale (:5196), whose "
            "namespace invariant this map borrows."
        ),
        expert=(
            "cap = n·per-node·(1−tax(n)); rebuild rate ∝ survivors — "
            "the inversion. EC width trades overhead vs survives-N. "
            "Namespace count stays 1; that's the other app's test."
        ),
    ),
    [{"label": "DellPowerScale twin", "url": "http://localhost:5196/"}],
)

OBJECTSCALE = _scaleout_map(
    "objectscale",
    "ObjectScale · S3-compatible object storage",
    "ObjectScale X-series class",
    (
        "Dense nodes tuned for throughput and capacity; latency is "
        "measured in milliseconds and mostly nobody cares — object "
        "workloads are streams, not transactions."
    ),
    (
        "S3 buckets. With object lock (WORM) on, deletes bounce — try "
        "the attempt-delete event and read the log."
    ),
    L(
        novice=(
            "Storage that speaks the web's language: objects in "
            "buckets, reached by name over HTTP. It gives up "
            "split-second response times — nobody streams a backup "
            "byte by byte — and wins enormous capacity and "
            "throughput. Two habits matter: millions of tiny objects "
            "waste most of the machinery on bookkeeping (the "
            "small-object tax), and a locked bucket refuses deletion "
            "no matter who asks — the write-once property that makes "
            "it a favorite target for backup vaults."
        ),
        standard=(
            "The throughput/capacity personality: ms-class latency "
            "floor accepted by design, per-node contribution scaled "
            "by the erasure scheme, and two teaching mechanics — the "
            "small-object tax (metadata ops dominate below ~100 KB; "
            "the toggle costs ~45% of throughput) and object lock, "
            "where the attempt-delete event bounces with a WORM log "
            "line. Ties to the resilience suite as the immutable "
            "backup target."
        ),
        expert=(
            "ms floor by contract; small-object toggle −45% "
            "throughput (metadata-bound); WORM bounce is a log line, "
            "not an error. The vault's favorite substrate."
        ),
    ),
    [],
)


POWERFLEX = ProductMap(
    id="powerflex",
    name="PowerFlex · software-defined block storage",
    vendor="Dell Technologies",
    form_factor="Scale-out cluster — architecture view",
    generation="PowerFlex 5.x",
    year=2025,
    width=100,
    height=52,
    overview=L(
        novice=(
            "Ordinary servers pooled into one storage system, joined "
            "by nothing but their network cards — which is the whole "
            "story: the network IS the array. Give the nodes slow "
            "network ports and no amount of fast drives helps; give "
            "them fast ones and a hundred nodes answer as one. "
            "Because every node holds a slice of everything, a failed "
            "drive is rebuilt by everyone at once — in about a "
            "minute, not hours. And growing the system is just "
            "plugging in more servers while it runs."
        ),
        standard=(
            "The SDS personality: aggregate IOPS = min(Σ node "
            "ceilings, Σ NIC bandwidth ÷ block size) — the NIC term "
            "usually binds, so the nic-speed dial moves the aggregate "
            "ceiling (10 vs 100 GbE is the scenario). Rebuilds are "
            "massively parallel (rate × survivors at ~4× the NAS "
            "figure): the 15 TB drive comes back in minutes — the "
            "'60-second rebuild' against PowerStore's hours. Add-nodes "
            "is a live event with a brief rebalance penalty. "
            "Companion: DellPowerFlex (:5189)."
        ),
        expert=(
            "cap = min(n·node, n·NIC/2/blk). NIC binds → the network "
            "is the array. Rebuild ∝ survivors at SDS rates: minutes. "
            "Elastic add-nodes mid-run."
        ),
    ),
    regions=[
        _clients(),
        MapRegion(
            id="network", kind="network", label="IP fabric — the array's backplane",
            x=2, y=12, w=96, h=9,
            description=(
                "The NICs and switches every byte crosses. Its color is "
                "demand against the network ceiling — when this block "
                "saturates, drive speed is irrelevant."
            ),
        ),
        MapRegion(
            id="nodes", kind="node", label="Server nodes with local NVMe",
            x=2, y=25, w=96, h=13,
            description=(
                "Ordinary servers whose local drives are sliced across "
                "the pool. Everyone serves, everyone rebuilds."
            ),
        ),
        MapRegion(
            id="media", kind="media", label="Pooled media (mesh-mirrored)",
            x=2, y=42, w=96, h=8,
            description="The logical pool the slices form, colored by fill.",
        ),
    ],
    sources=[
        {"label": "physics_specs/02-storage-platforms.md (this repo)",
         "url": "../physics_specs/02-storage-platforms.md"},
        {"label": "DellPowerFlex twin", "url": "http://localhost:5189/"},
    ],
)


EXASCALE = ProductMap(
    id="exascale",
    name="Exascale Storage · the AI Data Platform's engine room",
    vendor="Dell Technologies",
    form_factor="Rack-scale software-defined — architecture view",
    generation="Dell AI Data Platform (2026)",
    year=2026,
    width=100,
    height=52,
    overview=L(
        novice=(
            "One rack of storage servers, divided by software into "
            "four specialist teams: a parallel file system for "
            "feeding GPU training (the sprinter), general file "
            "storage, object storage for the big archive, and block "
            "storage for databases. You choose the split. The "
            "scoreboard is unusual: not this rack's speed, but the "
            "percentage of time the GPUs elsewhere sit idle waiting "
            "for data. Partition badly and million-dollar computers "
            "wait; partition well and the idle number goes to zero."
        ),
        standard=(
            "The meta-simulator: one node pool partitioned among "
            "Lightning (parallel FS), file, object, and block "
            "personalities, serving a single AI demand profile with "
            "fixed shares. Per-pool utilization is the diagnostic; "
            "the north-star instrument is GPU-idle-due-to-data — "
            "PhysicsCompute's data-feed slider, seen from the supply "
            "side. Checkpoint stampedes fire automatically every six "
            "hours (write demand ×6) and each pool absorbs them "
            "differently. Built last, per the spec: it composes the "
            "other five. Companion: DellExascale (:5184)."
        ),
        expert=(
            "Partitioned pool → per-pool ρ; north star = GPU idle % "
            "(the compute app's feed slider, inverted). Auto "
            "checkpoint ×6 every 6 h. The capstone: right-size the "
            "mix until idle ≈ 0."
        ),
    ),
    regions=[
        MapRegion(
            id="clients", kind="client", label="GPU cluster (the customer)",
            x=2, y=1, w=96, h=8,
            description=(
                "PhysicsCompute's XE9680s. Their idle-due-to-data "
                "percentage is this rack's real report card, and this "
                "block's color."
            ),
        ),
        MapRegion(
            id="network", kind="network", label="800GbE storage fabric",
            x=2, y=12, w=96, h=6,
            description="The fabric between the GPUs and the pools.",
        ),
        MapRegion(
            id="pool-lightning", kind="pool", label="Lightning (parallel FS)",
            x=2, y=22, w=46, h=13,
            description=(
                "The training feed — sequential-optimized parallel FS "
                "carrying 60% of AI demand. Undersize this pool and "
                "the GPU-idle number says so within the hour."
            ),
        ),
        MapRegion(
            id="pool-file", kind="pool", label="File (PowerScale)",
            x=52, y=22, w=46, h=13,
            description="General file serving — 20% of the demand profile.",
        ),
        MapRegion(
            id="pool-object", kind="pool", label="Object (ObjectScale)",
            x=2, y=39, w=46, h=11,
            description="The dataset archive — 15% of demand, capacity-heavy.",
        ),
        MapRegion(
            id="pool-block", kind="pool", label="Block (PowerFlex, roadmap)",
            x=52, y=39, w=46, h=11,
            description=(
                "Database/block duty — 5% of demand. Flagged roadmap "
                "1H 2027 in Dell's materials; drawn solid here because "
                "the physics doesn't care about ship dates."
            ),
        ),
    ],
    sources=[
        {"label": "physics_specs/02-storage-platforms.md (this repo)",
         "url": "../physics_specs/02-storage-platforms.md"},
        {"label": "DellExascale twin", "url": "http://localhost:5184/"},
    ],
)


MAPS: dict[str, ProductMap] = {
    "powerstore": POWERSTORE,
    "powermax": POWERMAX,
    "powerscale": POWERSCALE,
    "objectscale": OBJECTSCALE,
    "powerflex": POWERFLEX,
    "exascale": EXASCALE,
}
