"""Component catalog: what an Exascale Storage deployment is built from.

Same pattern as the other twins: categories map onto platform regions via
``region_ids`` (ids from anatomy.py; an empty list means the item is not a
drawn part of the data path — services, validated designs). Written for a
technically skilled reader new to parallel storage; jargon (pNFS, layout,
stripe, OneFS, GPUDirect, RDMA, MDS, ...) is spelled out on first use.
Figures are product-literature numbers from Dell's 2025–26 AI Data Platform
announcements, not benchmarks; performance figures are labeled as Dell's
claims in the served text.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

_DATA_REGIONS = [f"data-ds{i}" for i in (1, 2, 3, 4)]
_MEDIA_REGIONS = [f"media-ds{i}" for i in (1, 2, 3, 4)]

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="platform",
        name="Storage platform",
        blurb=(
            "The rack itself. Dell's AI Data Platform puts several storage "
            "engines under one roof; how much of that you buy at once is "
            "the first decision."
        ),
        limits="Up to 6 TB/s reads per rack (Dell's claim); capacity moves between engines",
        region_ids=[],
        options=[
            CatalogOption(
                id="plat-exascale",
                name="Dell Exascale Storage (unified rack)",
                summary="File, parallel file, and object on common servers; block planned for 2027.",
                details=(
                    "Announced in March 2026, Exascale Storage runs "
                    "PowerScale (file), Lightning (parallel file), and "
                    "ObjectScale (object) as software personalities on "
                    "qualified PowerEdge servers, beginning with the "
                    "R7725xd, at up to 800 GbE per node. Dell targets "
                    "PowerFlex (block) for the first half of 2027, and "
                    "quotes up to 6 TB/s of reads per rack running the "
                    "Lightning personality. One license covers every "
                    "personality, so capacity can be moved between them. "
                    "The motivation is "
                    "spatial and operational as much as technical: an AI "
                    "corpus arrives as objects, is prepared as files, and "
                    "must be read in parallel, and doing that across three "
                    "separate products means copying petabytes between "
                    "them for every stage."
                ),
            ),
            CatalogOption(
                id="plat-powerscale",
                name="PowerScale cluster (file only)",
                summary="Classic scale-out NAS — turn on parallel NFS in the same OneFS.",
                details=(
                    "The conventional entry point: a PowerScale all-flash "
                    "cluster (F710/F910 class) serving NFS and SMB from one "
                    "namespace that grows node by node. OneFS 9.15 adds "
                    "parallel NFS to that same namespace, so an estate can "
                    "start here for ordinary file workloads and turn on the "
                    "parallel path when AI training arrives — without "
                    "migrating the data into a different system. The "
                    "Lightning File System is a separate, faster engine."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="parallel",
        name="Parallel file systems",
        blurb=(
            "The parallel paths — and the reason this twin exists. The "
            "defining move is architectural: get metadata out of the data "
            "path."
        ),
        limits="Lightning FS from April 2026; PowerScale pNFS in OneFS 9.15",
        region_ids=["metadata", "fanout"],
        options=[
            CatalogOption(
                id="par-lightning",
                name="Lightning File System",
                summary="Dell's own parallel file system: up to 150 GB/s per rack unit, by Dell's claim.",
                details=(
                    "The Lightning File System grew out of Project "
                    "Lightning and became available in April 2026. It is "
                    "a separate file system, not OneFS: Dell describes "
                    "clients that turn file requests into direct reads and "
                    "writes against NVMe, metadata distributed across the "
                    "system, and its own client software. Dell calls it "
                    "the world's fastest parallel file system, on its own "
                    "internal analysis, and quotes up to 150 GB/s per rack "
                    "unit, which is where the 6 TB/s per rack comes from. "
                    "Dell aims it at short-lived, high-speed training and "
                    "inference data, beside PowerScale and ObjectScale "
                    "rather than in place of them."
                ),
            ),
            CatalogOption(
                id="par-pnfs",
                name="PowerScale parallel NFS (pNFS)",
                summary="The open-standard parallel path, inside OneFS.",
                details=(
                    "The other result of Project Lightning: OneFS 9.15 "
                    "adds pNFS — parallel NFS, the standard extension that "
                    "lets one client stream from many servers at once — "
                    "with a metadata server handing out Flex Files "
                    "layouts. Dell claims up to 6× faster large-file "
                    "performance than NFSv3. This is the path the twin's "
                    "trace narrates, because the protocol is public and "
                    "names its parts."
                ),
            ),
            CatalogOption(
                id="par-mds",
                name="Metadata server + Flex Files layouts",
                summary="Answers 'where are the stripes?' once, then leaves the path.",
                details=(
                    "In pNFS, the metadata server (MDS) holds the namespace and the "
                    "layout map. A client asks once, receives a layout "
                    "describing which data servers hold which stripes, and "
                    "then transfers data directly — the MDS is not "
                    "consulted again for that transfer and could be "
                    "restarted without interrupting it. That separation is "
                    "why metadata never becomes the bottleneck as GPU "
                    "counts rise, and it is the invariant this twin's "
                    "engine tests enforce. In OneFS any node can take the "
                    "metadata role; Lightning spreads metadata across the "
                    "system instead."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="dataservers",
        name="Data servers",
        blurb=(
            "Where the bytes actually live and stream from. Throughput is "
            "the sum of these, which is why capacity planning here is "
            "really bandwidth planning."
        ),
        limits="Scale out for bandwidth; each adds throughput, not just space",
        region_ids=_DATA_REGIONS,
        options=[
            CatalogOption(
                id="ds-node",
                name="Exascale data server node",
                summary="PowerEdge-based node serving stripes directly to clients.",
                details=(
                    "Each data server holds a subset of every striped "
                    "file's segments and serves them straight to clients "
                    "that hold a layout. The scaling property is the "
                    "important one: adding a node adds bandwidth as well as "
                    "capacity, because clients simply widen their fan-out "
                    "to include it. Compare the block twins in this repo, "
                    "where adding drives adds capacity but the controllers "
                    "still set the ceiling."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="media",
        name="Media",
        blurb=(
            "Flash chosen for concurrency rather than raw capacity — an AI "
            "read pattern is thousands of GPUs pulling different stripes at "
            "once."
        ),
        limits="All-NVMe; sized for parallel mixed IO",
        region_ids=_MEDIA_REGIONS,
        options=[
            CatalogOption(
                id="media-nvme",
                name="All-NVMe flash",
                summary="Dense TLC NVMe striped so no device becomes a hot spot.",
                details=(
                    "The media tier is all-NVMe and deliberately striped "
                    "wide: a training job's access pattern is highly "
                    "concurrent and only semi-predictable, so the design "
                    "goal is that no single device or server ever becomes "
                    "the queue everyone waits in. Capacity per rack "
                    "matters, but sustained concurrent bandwidth is what "
                    "the GPUs actually experience."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="object",
        name="Object tier",
        blurb=(
            "Where the corpus arrives and the archive tail lives. Keeping "
            "it in the same rack removes the copy that starts every "
            "pipeline."
        ),
        limits="Multi-petabyte; S3 with RDMA acceleration",
        region_ids=["protocol-object"],
        options=[
            CatalogOption(
                id="obj-objectscale",
                name="Dell ObjectScale",
                summary="Software-defined S3 at multi-petabyte scale, with S3 over RDMA.",
                details=(
                    "ObjectScale serves the S3 object protocol on dense "
                    "PowerEdge nodes and scales to multi-petabyte data "
                    "lakes. S3 over RDMA pairs object storage with the "
                    "low-latency network protocol so object data can feed "
                    "preprocessing and training directly rather than being "
                    "staged to file first — which, at corpus scale, is the "
                    "difference between hours and days before a job can "
                    "start."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="block",
        name="Block tier",
        blurb=(
            "The engine that would let an AI storage rack also be ordinary "
            "enterprise infrastructure. Planned, not yet shipping in Exascale."
        ),
        limits="Targeted by Dell for 1H 2027 as an Exascale personality",
        region_ids=["protocol-block"],
        options=[
            CatalogOption(
                id="blk-powerflex",
                name="Dell PowerFlex",
                summary="Software-defined block storage, planned as the fourth personality.",
                details=(
                    "PowerFlex pools server-local media into software-"
                    "defined block volumes with independent compute and "
                    "capacity scaling. It is a shipping product on its "
                    "own; as an Exascale personality Dell targets the "
                    "first half of 2027. Its inclusion is what would make "
                    "Exascale useful beyond AI: the demanding conventional "
                    "databases next to the training job get first-class "
                    "block storage from the same footprint, instead of a "
                    "separate array."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="client",
        name="Client access paths",
        blurb=(
            "How the GPUs actually reach the data — and how little of the "
            "host CPU gets involved."
        ),
        limits="Lightning client, pNFS, NFS/SMB, S3; RDMA and GPUDirect where supported",
        region_ids=["clients", "fabric"],
        options=[
            CatalogOption(
                id="cli-gpudirect",
                name="GPUDirect Storage",
                summary="Data lands in GPU memory without a host-CPU bounce.",
                details=(
                    "GPUDirect Storage gives the network adapter a direct "
                    "path into GPU memory, skipping the usual copy into "
                    "host memory and back. At AI-factory bandwidth the "
                    "saved copies are not a micro-optimization: host memory "
                    "bandwidth and CPU cycles become a real ceiling long "
                    "before the storage does, and removing the bounce is "
                    "what lets a rack's claimed 6 TB/s actually reach the "
                    "accelerators."
                ),
            ),
            CatalogOption(
                id="cli-pnfs",
                name="pNFS client (standards-based)",
                summary="Parallel access using the in-tree NFS client — no proprietary driver.",
                details=(
                    "Because PowerScale's parallel path is pNFS rather "
                    "than a proprietary protocol, standard Linux clients "
                    "mount it with the in-tree NFS client and get parallel "
                    "access; Dell says no special software or custom "
                    "driver is needed. The Lightning File System is the "
                    "other trade: more speed, with Dell's own client "
                    "software. The standard client is an underrated "
                    "operational property: "
                    "competing parallel file systems often require a "
                    "kernel module matched to the OS version, which turns "
                    "every client upgrade into a storage project."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="fabric",
        name="Storage fabric",
        blurb=(
            "A parallel file system generates many-to-one traffic by "
            "design, so the network's congestion behavior is part of the "
            "storage design."
        ),
        limits="400–800 Gb/s class per client; Ethernet or InfiniBand",
        region_ids=["fabric", "fanout"],
        options=[
            CatalogOption(
                id="fab-spectrumx",
                name="Spectrum-X Ethernet (PowerSwitch SN-series)",
                summary="AI-tuned Ethernet — the subject of this repo's SN6000 twin.",
                details=(
                    "Fan-out reads are incast by construction: many data "
                    "servers answering one client at once, all arriving at "
                    "the same switch port. Spectrum-X's adaptive routing "
                    "and telemetry-driven congestion control exist for "
                    "exactly this, which is why the storage and network "
                    "designs are made together rather than in sequence."
                ),
            ),
            CatalogOption(
                id="fab-infiniband",
                name="Quantum InfiniBand",
                summary="The HPC-heritage alternative: lossless, lowest jitter.",
                details=(
                    "Sites with HPC heritage often already run InfiniBand "
                    "for the compute fabric and extend it to storage. "
                    "Lossless delivery and low jitter suit checkpoint "
                    "bursts, where thousands of clients write "
                    "simultaneously and the slowest stream sets the "
                    "duration of the whole pause."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="management",
        name="Management & observability",
        blurb=(
            "One control plane over every engine — and the place the "
            "question 'is storage why the GPUs are idle?' gets answered."
        ),
        limits="Unified provisioning + AIOps telemetry",
        region_ids=["mgmt"],
        options=[
            CatalogOption(
                id="mgmt-unified",
                name="Unified Exascale management",
                summary="Provision file, parallel file, and object from one place.",
                details=(
                    "Consolidation's operational payoff: one console for "
                    "capacity, performance, and provisioning across "
                    "every engine. Without it, a unified rack would just be "
                    "three products sharing a floor tile — the "
                    "single control plane is what makes it one system."
                ),
            ),
            CatalogOption(
                id="mgmt-aiops",
                name="CloudIQ / Dell AIOps",
                summary="Capacity forecasting and anomaly detection across the fleet.",
                details=(
                    "The storage fleet reports into Dell's AIOps platform "
                    "(this repo's CloudIQ twin): capacity forecasting says "
                    "when the corpus outgrows the rack, and performance "
                    "anomaly detection catches the noisy-neighbor job that "
                    "is quietly starving a training run of bandwidth."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="services",
        name="Validated designs & services",
        blurb=(
            "Storage for an AI factory is sized against GPU count and "
            "checkpoint policy, not against terabytes — which is a "
            "different skill."
        ),
        limits="Sized per AI Factory design; residencies available",
        region_ids=[],
        options=[
            CatalogOption(
                id="svc-aidataplatform",
                name="Dell AI Data Platform validated designs",
                summary="Storage sized and tested against the compute it feeds.",
                details=(
                    "Dell's AI Data Platform designs size the storage tier "
                    "against a specific GPU fleet and checkpoint cadence, "
                    "with the compute, fabric, and storage integration "
                    "tested before delivery. The sizing question is "
                    "unfamiliar to most storage teams: not 'how many "
                    "petabytes' but 'how many GB/s per GPU, and how long "
                    "may a checkpoint pause the fleet?'"
                ),
            ),
            CatalogOption(
                id="svc-residency",
                name="Data engineering residency",
                summary="Help getting the corpus into shape before the GPUs wait on it.",
                details=(
                    "Most AI projects lose more time to data preparation "
                    "than to training. Residency services cover the "
                    "pipeline work — ingest, curation, format conversion, "
                    "tiering policy — so the expensive compute arrives to "
                    "find data that is actually ready to be read at speed."
                ),
            ),
        ],
    ),
]
