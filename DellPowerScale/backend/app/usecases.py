"""Use cases: three PowerScale clusters, as backend data.

Each is a build sheet whose category and option ids must resolve against
``catalog.py`` — enforced in ``tests/test_catalog.py``. The narratives are
written for a reader who understands file storage but has always had to
carve it into volumes.

All three lean on the same property from different angles: one namespace
that grows by addition. What differs is which consequence is being bought
— an archive that never pauses, one dataset behind four protocols, or the
file tier under an AI rack.
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="media-archive",
        title="A media archive that grows unpredictably and can never pause",
        summary=(
            "Decades of footage in one namespace, where growth is a node "
            "joining the cluster rather than a migration project."
        ),
        narrative=[
            "Media archives have the least forgiving growth pattern in "
            "storage: nobody can say which acquisition, remaster, or news "
            "cycle will add half a petabyte, and the archive can never be "
            "taken offline, because the point of keeping footage is that "
            "an editor might ask for any of it tomorrow. On volume-based "
            "NAS this becomes a permanent planning burden — capacity "
            "carved against guesses, volumes filling unevenly, and every "
            "correction a migration negotiated around production "
            "schedules.",
            "One namespace removes the object the planning attaches to. "
            "There is no volume to outgrow: when the cluster runs short, "
            "an archive-tier node joins it, the single file system "
            "becomes larger, and AutoBalance spreads data onto the new "
            "hardware while editors keep pulling footage. The trace in "
            "this twin is exactly this story — usage climbing past 80%, "
            "two nodes joining, and the migrations-required counter "
            "sitting at zero throughout.",
            "Tiering does the second half of the work. New ingest lands "
            "on flash-cached hybrid nodes; footage ages onto high-density "
            "archive nodes by policy, without changing path, so a "
            "twenty-year-old asset is still exactly where its catalog "
            "entry says it is. The alternative — a separate archive "
            "system with its own namespace — is a second guess to "
            "maintain and a retrieval ceremony this design never asks "
            "for.",
        ],
        config=[
            UseCaseItem(
                category_id="node-tiers", option_id="hybrid", qty=4,
                rationale=(
                    "Ingest and active editing stream large files; "
                    "flash-cached disk is the right price for that shape."
                ),
            ),
            UseCaseItem(
                category_id="node-tiers", option_id="archive", qty=8,
                rationale=(
                    "The bulk of the archive is cold but must stay "
                    "online at its original path."
                ),
            ),
            UseCaseItem(
                category_id="onefs", option_id="single-namespace", qty=1,
                rationale=(
                    "The property being purchased: growth without a "
                    "migration, forever."
                ),
            ),
            UseCaseItem(
                category_id="protocols", option_id="file-protocols", qty=1,
                rationale=(
                    "Edit bays mount over SMB; render farms read the "
                    "same assets over NFS."
                ),
            ),
            UseCaseItem(
                category_id="tiering", option_id="smartpools", qty=1,
                rationale=(
                    "Footage ages from hybrid to archive nodes by rule, "
                    "without changing path."
                ),
            ),
            UseCaseItem(
                category_id="protection", option_id="protection-levels", qty=1,
                rationale=(
                    "An archive this size holds masters; higher "
                    "protection is a policy change, not a rebuild."
                ),
            ),
            UseCaseItem(
                category_id="replication", option_id="synciq", qty=1,
                rationale=(
                    "The catalog is replaceable; the footage is not — a "
                    "second cluster at a second site."
                ),
            ),
            UseCaseItem(
                category_id="management", option_id="cluster-mgmt", qty=1,
                rationale=(
                    "Growth events should be minutes of work, because "
                    "they will happen often and unpredictably."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Namespaces", value="One, at every size"),
            Stat(label="Growth increment", value="One node"),
            Stat(label="Migrations to expand", value="Zero"),
            Stat(label="Archive downtime", value="None — expansion is a background task"),
        ],
    ),
    UseCase(
        id="genomics-multiprotocol",
        title="Genomics data written, read, and published — one copy, four doors",
        summary=(
            "Sequencers write over SMB, pipelines read over NFS, results "
            "publish over S3 — the same files, never copied between silos."
        ),
        narrative=[
            "A sequencing lab's data takes a fixed journey: an instrument "
            "on a Windows workstation writes raw output, a Linux compute "
            "cluster runs the analysis pipeline, and results are shared "
            "with collaborators over the web. On conventional "
            "infrastructure each leg has its own storage — an SMB share "
            "by the instrument, an NFS scratch system by the cluster, an "
            "object store for publication — and the data is copied "
            "between them, which costs time, capacity, and eventually the "
            "certainty about which copy is authoritative.",
            "Multi-protocol access to one namespace collapses the "
            "journey. The instrument writes over SMB (Server Message "
            "Block, the Windows file protocol); the pipeline reads the "
            "same files over NFS (the Network File System Linux mounts); "
            "an analytics platform can read them again over HDFS; and "
            "the results directory is published over S3 without anything "
            "being copied anywhere. There is one copy of the genome, and "
            "the protocols are doors into it rather than rooms of their "
            "own.",
            "The practical consequence is provenance. When a result is "
            "questioned two years later, the raw data is at the path the "
            "pipeline log recorded, on the archive tier it aged to by "
            "policy, still behind all four doors. Nobody has to "
            "reconstruct which of three silos held the true version, "
            "because there was never more than one.",
        ],
        config=[
            UseCaseItem(
                category_id="node-tiers", option_id="all-flash", qty=4,
                rationale=(
                    "Pipeline runs hammer the active flowcells; flash "
                    "keeps analysis wall-clock short."
                ),
            ),
            UseCaseItem(
                category_id="node-tiers", option_id="archive", qty=4,
                rationale=(
                    "Completed runs are kept for years and rarely "
                    "reread — until they must be, at the same path."
                ),
            ),
            UseCaseItem(
                category_id="protocols", option_id="file-protocols", qty=1,
                rationale=(
                    "The instrument writes SMB; the pipeline reads NFS; "
                    "one namespace serves both."
                ),
            ),
            UseCaseItem(
                category_id="protocols", option_id="object-analytics", qty=1,
                rationale=(
                    "Results publish over S3 and feed analytics over "
                    "HDFS without an export step."
                ),
            ),
            UseCaseItem(
                category_id="tiering", option_id="smartpools", qty=1,
                rationale=(
                    "Runs age from flash to archive automatically at "
                    "the pace sequencers dictate."
                ),
            ),
            UseCaseItem(
                category_id="security", option_id="smartlock", qty=1,
                rationale=(
                    "Regulated studies need retention the storage "
                    "enforces, per directory, inside the same namespace."
                ),
            ),
            UseCaseItem(
                category_id="replication", option_id="snapshots", qty=1,
                rationale=(
                    "Per-directory snapshots protect active runs "
                    "without snapshotting the whole estate."
                ),
            ),
            UseCaseItem(
                category_id="scale", option_id="node-pools", qty=1,
                rationale=(
                    "Flash and archive hardware organized as pools, "
                    "with the namespace still undivided."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Copies of the data", value="One"),
            Stat(label="Protocols reaching it", value="SMB, NFS, S3, HDFS"),
            Stat(label="Export steps between stages", value="None"),
            Stat(label="Authoritative version disputes", value="Nothing to dispute"),
        ],
    ),
    UseCase(
        id="ai-corpus",
        title="The file tier under an AI factory's training corpus",
        summary=(
            "The namespace beneath the Exascale rack's parallel file "
            "system — a corpus that grows for years without ever being "
            "reorganized."
        ),
        narrative=[
            "A training corpus is an archive with a violent read "
            "pattern. It accumulates for years — crawls, licensed "
            "datasets, generated data — and then, during a training run, "
            "must be streamed to GPUs at rates that would saturate any "
            "single controller. This repo splits the problem across two "
            "twins: DellExascale covers the throughput half, where the "
            "Lightning File System hands clients a layout and lets them "
            "read from every data server at once. This twin covers the "
            "half underneath — Lightning runs on OneFS, and the "
            "namespace it parallelizes is the single file system "
            "described here.",
            "The namespace half matters because a corpus's enemy is "
            "reorganization. Datasets that move break the manifests, "
            "loaders, and provenance records that point at them; a "
            "corpus partitioned into volumes gets reorganized every time "
            "a volume fills. One namespace that grows by node addition "
            "never forces that: the path a manifest recorded in year one "
            "is the path in year five, with the cluster several times "
            "larger and the data rebalanced underneath — while training "
            "reads continue, as this twin's rebalance step insists.",
            "The fan-out matters even at this layer. Every node serves "
            "the whole namespace, so preprocessing jobs, tokenizers, and "
            "the parallel file system above are never queued behind one "
            "head — the same refusal of a choke point that DellPowerFlex "
            "makes for block storage and the SN6000 twin's fabric makes "
            "for the network between them.",
        ],
        config=[
            UseCaseItem(
                category_id="node-tiers", option_id="all-flash", qty=12,
                rationale=(
                    "Training streams are read-heavy and merciless; the "
                    "corpus's hot tier is flash end to end."
                ),
            ),
            UseCaseItem(
                category_id="onefs", option_id="onefs-os", qty=1,
                rationale=(
                    "Lightning parallelizes OneFS — this namespace is "
                    "the layer that twin's layouts point into."
                ),
            ),
            UseCaseItem(
                category_id="onefs", option_id="single-namespace", qty=1,
                rationale=(
                    "Manifests recorded in year one must resolve in "
                    "year five; the namespace never reorganizes."
                ),
            ),
            UseCaseItem(
                category_id="networking", option_id="backend-fabric", qty=1,
                rationale=(
                    "Restriping a growing corpus is interconnect work; "
                    "undersizing it slows every expansion."
                ),
            ),
            UseCaseItem(
                category_id="networking", option_id="frontend-pools", qty=1,
                rationale=(
                    "Hundreds of loader clients spread across every "
                    "node with no per-client configuration."
                ),
            ),
            UseCaseItem(
                category_id="scale", option_id="cluster-scale", qty=1,
                rationale=(
                    "The corpus will grow for the model program's "
                    "lifetime; the ceiling should be far away."
                ),
            ),
            UseCaseItem(
                category_id="protection", option_id="erasure-coding", qty=1,
                rationale=(
                    "Re-crawling a corpus is possible and miserable; "
                    "per-file parity makes it unnecessary."
                ),
            ),
            UseCaseItem(
                category_id="management", option_id="aiops", qty=1,
                rationale=(
                    "Capacity trajectory is the decision input for the "
                    "next node purchase; CloudIQ watches it."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Corpus reorganizations", value="Zero, by construction"),
            Stat(label="Namespace under Lightning", value="This one"),
            Stat(label="Growth during training", value="Non-disruptive"),
            Stat(label="Paths broken by expansion", value="None"),
        ],
    ),
]
