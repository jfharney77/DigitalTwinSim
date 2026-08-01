"""Component catalog: what an Exascale Storage deployment is built from.

Same pattern as the other twins: categories map onto platform regions via
``region_ids`` (ids from anatomy.py; an empty list means the item is not a
drawn part of the data path — services, validated designs). Written for a
technically skilled reader new to parallel storage; jargon (pNFS, layout,
stripe, OneFS, GPUDirect, RDMA, MDS, ...) is spelled out on first use.
Figures are product-literature numbers from Dell's 2025–26 AI Data Platform
announcements, not benchmarks.
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
        limits="~6 TB/s per Exascale rack; engines scale independently",
        region_ids=[],
        options=[
            CatalogOption(
                id="plat-exascale",
                name="Dell Exascale Storage (unified rack)",
                summary="Block, file, parallel file, and object consolidated in one footprint.",
                details=(
                    "Announced at Dell Technologies World 2026, Exascale "
                    "Storage combines PowerFlex (block), PowerScale and "
                    "Lightning (file and parallel file), and ObjectScale "
                    "(object) on current PowerEdge hardware, delivering on "
                    "the order of 6 TB/s per rack. The motivation is "
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
                summary="Classic scale-out NAS — add Lightning later on the same OneFS.",
                details=(
                    "The conventional entry point: a PowerScale all-flash "
                    "cluster (F710/F910 class) serving NFS and SMB from one "
                    "namespace that grows node by node. Because Lightning "
                    "is built on the same OneFS foundation, an estate can "
                    "start here for ordinary file workloads and add the "
                    "parallel path when AI training arrives — without "
                    "migrating the data into a different system."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="parallel",
        name="Lightning parallel file system",
        blurb=(
            "The parallel path — and the reason this twin exists. Its "
            "defining move is architectural: get the metadata server out of "
            "the data path."
        ),
        limits="pNFS + Flex Files; parallel NFS globally available in 2026",
        region_ids=["metadata", "fanout"],
        options=[
            CatalogOption(
                id="par-lightning",
                name="Lightning File System",
                summary="Parallel NFS on OneFS: up to 6× large-file performance.",
                details=(
                    "Lightning is the production form of Project Lightning, "
                    "an 18-month effort to add parallel IO to PowerScale's "
                    "OneFS. It uses pNFS — parallel NFS, the standard "
                    "extension that lets one client stream from many "
                    "servers at once — with a metadata server handing out "
                    "Flex Files layouts. Dell reports up to 6× faster "
                    "large-file performance than the prior NFS stack and "
                    "positions it as the fastest parallel file system "
                    "available. Because it is standards-based pNFS, clients "
                    "need no proprietary driver."
                ),
            ),
            CatalogOption(
                id="par-mds",
                name="Metadata server + Flex Files layouts",
                summary="Answers 'where are the stripes?' once, then leaves the path.",
                details=(
                    "The metadata server (MDS) holds the namespace and the "
                    "layout map. A client asks once, receives a delegation "
                    "describing which data servers hold which stripes, and "
                    "then transfers data directly — the MDS is not "
                    "consulted again for that transfer and could be "
                    "restarted without interrupting it. That separation is "
                    "why metadata never becomes the bottleneck as GPU "
                    "counts rise, and it is the invariant this twin's "
                    "engine tests enforce."
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
            "The engine that lets an AI storage rack also be ordinary "
            "enterprise infrastructure."
        ),
        limits="Software-defined; scales with the rack",
        region_ids=["protocol-block"],
        options=[
            CatalogOption(
                id="blk-powerflex",
                name="Dell PowerFlex",
                summary="Software-defined block storage inside the same rack.",
                details=(
                    "PowerFlex pools server-local media into software-"
                    "defined block volumes with independent compute and "
                    "capacity scaling. Its inclusion is what makes "
                    "PowerRack-for-storage and Exascale useful beyond AI: "
                    "the demanding conventional databases next to the "
                    "training job get first-class block storage from the "
                    "same footprint, instead of a separate array."
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
        limits="pNFS, NFS/SMB, S3; RDMA and GPUDirect where supported",
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
                    "what lets a rack's 6 TB/s actually reach the "
                    "accelerators."
                ),
            ),
            CatalogOption(
                id="cli-pnfs",
                name="pNFS client (standards-based)",
                summary="Parallel access using the in-tree NFS client — no proprietary driver.",
                details=(
                    "Because Lightning speaks pNFS rather than a "
                    "proprietary protocol, standard Linux clients can mount "
                    "it with the in-tree NFS client and get parallel "
                    "access. That is an underrated operational property: "
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
            "One control plane over four engines — and the place the "
            "question 'is storage why the GPUs are idle?' gets answered."
        ),
        limits="Unified provisioning + AIOps telemetry",
        region_ids=["mgmt"],
        options=[
            CatalogOption(
                id="mgmt-unified",
                name="Unified Exascale management",
                summary="Provision block, file, parallel file, and object from one place.",
                details=(
                    "Consolidation's operational payoff: one console for "
                    "capacity, performance, and provisioning across all "
                    "four engines. Without it, a unified rack would just be "
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
