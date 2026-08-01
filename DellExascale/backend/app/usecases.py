"""Worked use cases: what Exascale + Lightning actually gets deployed for.

Each use case is a narrative plus a build sheet whose category/option ids
must resolve against catalog.py (enforced in tests/test_catalog.py).
Written for a technically skilled reader new to parallel storage.
Quantities count the unit named (racks, clusters, engines).
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="feedthefactory",
        title="Feeding an eight-rack AI factory",
        summary=(
            "576 GPUs read their corpus in parallel and checkpoint in "
            "bursts; Lightning's fan-out keeps them fed at ~6 TB/s while "
            "the metadata server stays out of the way."
        ),
        narrative=[
            (
                "The workload: the eight-rack GB200 NVL72 training cluster "
                "from the XE9712 twin — 576 GPUs on one job for weeks. "
                "Storage sees two utterly different patterns from the same "
                "job. Continuous reads stream the corpus batch after batch, "
                "and periodically everything stops to write a checkpoint "
                "measured in terabytes. Both must be fast, for different "
                "reasons: slow reads starve the GPUs, and slow checkpoints "
                "either pause the fleet too long or push the team to "
                "checkpoint less often, which raises the cost of every "
                "failure."
            ),
            (
                "Why Lightning fits: the read pattern is exactly what "
                "parallel access is for. Each client fetches a layout once "
                "and then pulls stripes from every data server at the same "
                "time, so aggregate bandwidth is the sum of the servers — "
                "roughly 6 TB/s per rack — rather than any controller's "
                "ceiling, and the metadata server never becomes the "
                "chokepoint no matter how many clients mount. GPUDirect "
                "puts the bytes in GPU memory without a host-CPU bounce. "
                "For checkpoints the same striping runs in reverse: "
                "thousands of writers landing simultaneously across all "
                "servers, which is why the checkpoint pause is minutes "
                "instead of an hour."
            ),
            (
                "The corpus itself lives on ObjectScale in the same rack "
                "and ages back to it between epochs, so the pipeline's "
                "first step stops being a petabyte-scale copy between "
                "systems. Run this twin with the XE9712, IR7000, and SN6000 "
                "twins for the complete factory — compute, cooling, data, "
                "and fabric are four views of the same machine."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="plat-exascale", qty=2,
                rationale=(
                    "Two unified racks feed 576 GPUs and hold the corpus "
                    "and checkpoints in one namespace."
                ),
            ),
            UseCaseItem(
                category_id="parallel", option_id="par-lightning", qty=1,
                rationale="Parallel reads are the difference between fed GPUs and idle ones.",
            ),
            UseCaseItem(
                category_id="dataservers", option_id="ds-node", qty=32,
                rationale="Bandwidth scales with data servers — these are the throughput.",
            ),
            UseCaseItem(
                category_id="client", option_id="cli-gpudirect", qty=1,
                rationale="Bytes into GPU memory without a host-CPU bounce.",
            ),
            UseCaseItem(
                category_id="object", option_id="obj-objectscale", qty=1,
                rationale="The corpus arrives and ages here, inside the same rack.",
            ),
            UseCaseItem(
                category_id="fabric", option_id="fab-spectrumx", qty=1,
                rationale="Fan-out reads are incast by design; adaptive routing absorbs it.",
            ),
            UseCaseItem(
                category_id="services", option_id="svc-aidataplatform", qty=1,
                rationale="Sized against GPU count and checkpoint cadence, not terabytes.",
            ),
        ],
        outcomes=[
            Stat(label="Read bandwidth", value="~6 TB/s per rack, aggregate"),
            Stat(label="Metadata in path", value="Once per layout — then never"),
            Stat(label="Checkpoint", value="Parallel writes across every server"),
            Stat(label="Corpus staging", value="None — object tier is in the rack"),
        ],
    ),
    UseCase(
        id="hpc",
        title="HPC centre replacing a legacy parallel file system",
        summary=(
            "A research site swaps an aging Lustre-style deployment for "
            "Lightning — standards-based pNFS means no proprietary client "
            "module chasing every kernel upgrade."
        ),
        narrative=[
            (
                "The workload: a university HPC centre running simulation "
                "and, increasingly, AI on the same machine. It has operated "
                "a traditional parallel file system for a decade and knows "
                "the costs intimately: a proprietary client module pinned "
                "to specific kernel versions, so every OS upgrade becomes a "
                "storage project; specialist staff to keep it healthy; and "
                "a metadata server that has become the system's political "
                "bottleneck, since one badly-behaved job doing millions of "
                "small file operations can slow the whole cluster."
            ),
            (
                "Why Lightning fits: it delivers parallel performance "
                "through pNFS, a standard, so ordinary Linux clients mount "
                "it with the in-tree NFS client — no module to rebuild, no "
                "kernel version matrix. The parallel path is the same one "
                "the AI groups need, and the conventional NFS and SMB "
                "namespace on the same OneFS foundation serves the "
                "traditional users who just want a home directory. One "
                "system, two access personalities, and no migration between "
                "them because it is the same data."
            ),
            (
                "The operational argument closed it: the centre's staff "
                "already know OneFS from an existing PowerScale cluster, so "
                "the parallel capability arrives as a capability rather "
                "than a new product to learn. Adding data servers adds "
                "bandwidth, which gives the centre a growth path measured "
                "in nodes instead of forklifts."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="plat-powerscale", qty=1,
                rationale=(
                    "Start from the familiar OneFS cluster; the parallel "
                    "path is added, not migrated to."
                ),
            ),
            UseCaseItem(
                category_id="parallel", option_id="par-lightning", qty=1,
                rationale="Parallel throughput for simulation and AI on the same data.",
            ),
            UseCaseItem(
                category_id="client", option_id="cli-pnfs", qty=1,
                rationale=(
                    "Standards-based clients end the kernel-version chase "
                    "that defined the old system."
                ),
            ),
            UseCaseItem(
                category_id="parallel", option_id="par-mds", qty=1,
                rationale="Metadata off the data path — one bad job no longer stalls everyone.",
            ),
            UseCaseItem(
                category_id="dataservers", option_id="ds-node", qty=16,
                rationale="Growth path measured in nodes; each one adds bandwidth.",
            ),
            UseCaseItem(
                category_id="fabric", option_id="fab-infiniband", qty=1,
                rationale="The centre already runs InfiniBand for compute; extend it.",
            ),
            UseCaseItem(
                category_id="management", option_id="mgmt-unified", qty=1,
                rationale="Existing OneFS skills transfer; no new product to staff.",
            ),
        ],
        outcomes=[
            Stat(label="Client software", value="In-tree NFS — no proprietary module"),
            Stat(label="Access modes", value="Parallel pNFS + conventional NFS/SMB"),
            Stat(label="Migration", value="None — same data, added capability"),
            Stat(label="Scaling", value="Add nodes for bandwidth, not forklifts"),
        ],
    ),
    UseCase(
        id="consolidate",
        title="Consolidating three storage silos into one rack",
        summary=(
            "An enterprise collapses a block array, a NAS, and an object "
            "store into a single Exascale rack — and stops copying "
            "petabytes between them to start any AI project."
        ),
        narrative=[
            (
                "The workload: an enterprise with the usual archaeology — a "
                "block array under the databases, a NAS for shared files, "
                "and an object store bolted on when the data-science team "
                "arrived. Three products, three consoles, three support "
                "contracts, three capacity forecasts, and a data-science "
                "pipeline whose first step is always copying a few hundred "
                "terabytes from the object store into the NAS so a training "
                "job can read it at a tolerable speed."
            ),
            (
                "Why Exascale fits: it puts all four access patterns — "
                "PowerFlex block, PowerScale and Lightning file, "
                "ObjectScale object — in one rack with one control plane. "
                "The databases keep their block volumes, the shared "
                "namespace keeps working, and the corpus becomes readable "
                "at parallel speed *where it already sits*. That deleted "
                "copy step is usually the single biggest schedule win, "
                "because it was measured in days and repeated for every "
                "experiment."
            ),
            (
                "Floor space and power made the finance case — a "
                "consolidated rack replaces three partly-empty ones — but "
                "the operational case was the capacity question. Across "
                "three silos, 'how much room do we have?' had three answers "
                "and no way to move space between them. In one rack with "
                "AIOps telemetry, it has one answer and a forecast."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="plat-exascale", qty=1,
                rationale="One rack, one control plane, replacing three silos.",
            ),
            UseCaseItem(
                category_id="block", option_id="blk-powerflex", qty=1,
                rationale="The databases keep first-class block storage in the same footprint.",
            ),
            UseCaseItem(
                category_id="object", option_id="obj-objectscale", qty=1,
                rationale="The corpus stays put and becomes readable in place.",
            ),
            UseCaseItem(
                category_id="parallel", option_id="par-lightning", qty=1,
                rationale="Parallel reads on the existing data — no staging copy.",
            ),
            UseCaseItem(
                category_id="media", option_id="media-nvme", qty=1,
                rationale="All-NVMe sized for concurrency across every workload at once.",
            ),
            UseCaseItem(
                category_id="management", option_id="mgmt-aiops", qty=1,
                rationale="One capacity forecast instead of three that cannot lend to each other.",
            ),
            UseCaseItem(
                category_id="services", option_id="svc-residency", qty=1,
                rationale="Pipeline and tiering policy work so the data is genuinely ready.",
            ),
        ],
        outcomes=[
            Stat(label="Silos replaced", value="Block + NAS + object → one rack"),
            Stat(label="Pipeline staging copy", value="Eliminated"),
            Stat(label="Capacity view", value="One forecast across all engines"),
            Stat(label="Footprint", value="Three partly-empty racks → one"),
        ],
    ),
]
