"""Component catalog: what you actually choose when you build a PowerScale
cluster, as backend data.

Written for a technically skilled reader new to scale-out NAS: OneFS, the
protocols (NFS, SMB, S3, HDFS), erasure coding, and node pools are spelled
out on first use. Categories map to the cluster regions in ``anatomy.py``
via ``region_ids``, and ``tests/test_catalog.py`` enforces that every id
resolves.

The ordering says something. There is no "volumes" category, because there
are no volumes — the first decision is which *nodes* to buy, and every
later decision is a policy applied to the one namespace those nodes form.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

_ALL_NODE_IDS = [f"node-{i}" for i in range(1, 7)]
_ALL_MEDIA_IDS = [f"media-{i}" for i in range(1, 7)]
_PROTO_IDS = ["proto-nfs", "proto-smb", "proto-s3", "proto-hdfs"]

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="node-tiers",
        name="Node tiers",
        blurb=(
            "The one hardware decision: which class of node to add. "
            "Everything a node brings — flash, disk, compute — joins the "
            "same single namespace."
        ),
        limits="All-flash, hybrid, and archive tiers; mixable in one cluster",
        region_ids=[*_ALL_NODE_IDS, *_ALL_MEDIA_IDS],
        options=[
            CatalogOption(
                id="all-flash",
                name="All-flash nodes (F-series)",
                summary=(
                    "NVMe flash nodes for the performance tier of the "
                    "namespace."
                ),
                details=(
                    "All-flash nodes carry NVMe drives and the strongest "
                    "compute, and form the tier where hot data lives — "
                    "active projects, scratch space, training data being "
                    "read right now. The important mental adjustment for "
                    "someone arriving from conventional NAS is that "
                    "buying these does not create a new share or a new "
                    "mount point. They join the same file system as every "
                    "other node, and placement onto them is policy, not "
                    "partitioning."
                ),
            ),
            CatalogOption(
                id="hybrid",
                name="Hybrid nodes (H-series)",
                summary=(
                    "Flash-cached disk nodes balancing capacity against "
                    "throughput."
                ),
                details=(
                    "Hybrid nodes pair spinning disk capacity with flash "
                    "caching, for workloads that stream large files "
                    "rather than hammering small ones — media assets, "
                    "instrument output, backup targets. In a mixed "
                    "cluster they form the middle tier, and files age "
                    "onto them from the flash tier by policy without "
                    "changing path or protocol."
                ),
            ),
            CatalogOption(
                id="archive",
                name="Archive nodes (A-series)",
                summary=(
                    "High-density disk nodes for the cold end of the "
                    "namespace."
                ),
                details=(
                    "Archive nodes maximize terabytes per rack unit and "
                    "watt, for data that must remain online and reachable "
                    "but is rarely touched. Because they join the same "
                    "namespace as the flash tier, an archived file is "
                    "still at the same path it was written to years "
                    "earlier — cold storage without the retrieval "
                    "ceremony that a separate archive system imposes."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="onefs",
        name="OneFS operating system",
        blurb=(
            "The software that joins the nodes into one cluster and "
            "presents one file system — the product, really; the nodes "
            "are its hardware."
        ),
        limits="One file system, one volume, one namespace — at any scale",
        region_ids=["namespace", *_ALL_NODE_IDS],
        options=[
            CatalogOption(
                id="onefs-os",
                name="OneFS",
                summary=(
                    "Every node runs the same operating system; the "
                    "cluster is the machine."
                ),
                details=(
                    "OneFS is the distributed operating system every "
                    "PowerScale node runs. It combines the roles that "
                    "conventional storage splits across RAID controllers, "
                    "volume managers, and file servers into one layer "
                    "that spans the cluster: it stripes every file across "
                    "the nodes, protects each with erasure coding, and "
                    "serves the result over every protocol from every "
                    "node. There is no controller node and no metadata "
                    "master — the cluster is symmetric, which is what "
                    "lets it grow by simple addition."
                ),
            ),
            CatalogOption(
                id="single-namespace",
                name="The single namespace",
                summary=(
                    "One file system rooted at /ifs, with no volume layer "
                    "beneath it."
                ),
                details=(
                    "The design decision the rest of the system follows "
                    "from. There is exactly one file system, and capacity "
                    "is never carved into fixed containers, so the "
                    "administrative work that containers generate — "
                    "sizing them, watching them fill unevenly, migrating "
                    "data between them — has nothing to attach to. "
                    "Directory quotas exist for governance, but a quota "
                    "is a policy on the one namespace, adjustable in "
                    "seconds, not a container with a fixed size. This "
                    "twin's trace is the argument played out: the "
                    "namespace count is one on every step."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="protocols",
        name="Protocols",
        blurb=(
            "How clients reach the one namespace: every protocol, on "
            "every node, to the same files."
        ),
        limits="NFS, SMB, S3, and HDFS — served cluster-wide, no protocol heads",
        region_ids=_PROTO_IDS,
        options=[
            CatalogOption(
                id="file-protocols",
                name="NFS and SMB",
                summary=(
                    "The two classic file protocols, served by every node "
                    "at once."
                ),
                details=(
                    "NFS (the Network File System, mounted by Unix and "
                    "Linux clients) and SMB (Server Message Block, the "
                    "Windows file-sharing protocol) both reach the same "
                    "files with permissions mapped between the two "
                    "worlds. Neither has a dedicated head: any node "
                    "serves either protocol, and a cluster-wide address "
                    "pool spreads client connections across all of them. "
                    "A failed node's clients reconnect to a survivor and "
                    "find the same namespace there, because every node "
                    "has all of it."
                ),
            ),
            CatalogOption(
                id="object-analytics",
                name="S3 and HDFS",
                summary=(
                    "Object and analytics access to the same data — "
                    "nothing is copied to be shared."
                ),
                details=(
                    "S3 is the HTTP-based object protocol in the style of "
                    "cloud storage; HDFS is the Hadoop Distributed File "
                    "System interface analytics platforms speak. On "
                    "PowerScale both are views onto the namespace rather "
                    "than separate silos: a file an instrument wrote over "
                    "SMB can be read by a pipeline over NFS, crunched by "
                    "an analytics farm over HDFS, and published to a "
                    "partner over S3 — one copy, four doors. For the full "
                    "object-native version of the trade, this repo's "
                    "DellObjectScale spec is the counterpart: it gave up "
                    "the directory tree, where OneFS kept the tree and "
                    "gave up the volume."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="protection",
        name="Data protection",
        blurb=(
            "How the cluster survives losing drives and nodes — per file, "
            "across nodes, with no RAID groups anywhere."
        ),
        limits="Erasure coding up to quadruple failure tolerance; per-file policy",
        region_ids=["namespace", "interconnect"],
        options=[
            CatalogOption(
                id="erasure-coding",
                name="Per-file erasure coding",
                summary=(
                    "Every file carries its own parity, striped across "
                    "nodes."
                ),
                details=(
                    "Erasure coding stores mathematical parity alongside "
                    "data, from which lost stripes can be recomputed — "
                    "the generalization of RAID parity, applied per file "
                    "across nodes rather than per disk group inside one "
                    "box. Because protection is a property of the file, "
                    "different directories in the same namespace can "
                    "carry different protection levels, and a rebuild "
                    "reconstructs only actual data, spread across the "
                    "whole cluster's drives rather than hammering one "
                    "spare."
                ),
            ),
            CatalogOption(
                id="protection-levels",
                name="Configurable protection levels",
                summary=(
                    "From single-failure to quadruple-failure tolerance, "
                    "chosen by policy."
                ),
                details=(
                    "OneFS expresses protection as how many simultaneous "
                    "failures — of drives or of whole nodes — a file must "
                    "survive. Raising it is a policy change on the "
                    "namespace, not a rebuild of a RAID group: the "
                    "cluster restripes affected files in the background. "
                    "Larger clusters can afford higher protection at "
                    "lower overhead, because parity is spread across more "
                    "nodes — one of several ways this architecture gets "
                    "better, not worse, as it grows."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="tiering",
        name="Tiering and placement",
        blurb=(
            "Policy-driven placement across node tiers — files move "
            "between hardware classes without changing path."
        ),
        limits="Policy-based tiering across pools; optional cloud tier",
        region_ids=["namespace", "mgmt"],
        options=[
            CatalogOption(
                id="smartpools",
                name="Policy-driven tiering (SmartPools)",
                summary=(
                    "Files age from flash to disk to archive by rule, "
                    "invisibly."
                ),
                details=(
                    "SmartPools watches file age, size, and access "
                    "pattern and moves files between node pools — the "
                    "flash tier, the hybrid tier, the archive tier — "
                    "according to policy. The move is invisible to "
                    "clients because the path never changes; only the "
                    "hardware underneath the file does. This is what "
                    "replaces the conventional practice of provisioning "
                    "separate 'fast' and 'cheap' volumes and making users "
                    "know which is which."
                ),
            ),
            CatalogOption(
                id="cloudpools",
                name="Cloud tier (CloudPools)",
                summary=(
                    "The coldest data spills to object storage, still at "
                    "the same path."
                ),
                details=(
                    "CloudPools extends the tiering ladder past the "
                    "cluster: files matching policy are stubbed out to "
                    "object storage — a public cloud or an on-premises "
                    "object store — while remaining visible at their "
                    "original path in the namespace. Reads recall them "
                    "transparently. The namespace stays one thing even "
                    "when its coldest bytes are no longer in the room."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="networking",
        name="Cluster networking",
        blurb=(
            "Two networks with two jobs: a front end clients see, and a "
            "back-end interconnect the cluster stripes over."
        ),
        limits="Ethernet front end; dedicated back-end fabric between nodes",
        region_ids=["interconnect"],
        options=[
            CatalogOption(
                id="backend-fabric",
                name="Back-end interconnect",
                summary=(
                    "The private fabric every stripe, parity block, and "
                    "rebalance crosses."
                ),
                details=(
                    "The back-end interconnect is a private network "
                    "reserved for node-to-node traffic — historically "
                    "InfiniBand, now typically high-speed Ethernet. It is "
                    "what lets a client talk to one node and receive a "
                    "file striped across all of them, and it is the path "
                    "every post-expansion rebalance runs over. Clients "
                    "never see it; sizing it is sizing how fast the "
                    "cluster can be one machine."
                ),
            ),
            CatalogOption(
                id="frontend-pools",
                name="Front-end address pools",
                summary=(
                    "Cluster-wide addressing that spreads clients across "
                    "every node."
                ),
                details=(
                    "Client connections land on the cluster through "
                    "pooled addresses that distribute load across all "
                    "nodes and shift automatically when a node leaves or "
                    "joins. The effect is that the cluster has one "
                    "front door with many receptionists: no client is "
                    "configured against a particular box, so growing or "
                    "shrinking the cluster never means touching client "
                    "mount configuration."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="scale",
        name="Scale and node pools",
        blurb=(
            "How far one namespace stretches, and how unlike hardware "
            "coexists inside it."
        ),
        limits="3 to 252 nodes; multiple node pools in one namespace",
        region_ids=[*_ALL_NODE_IDS, "namespace"],
        options=[
            CatalogOption(
                id="cluster-scale",
                name="Three nodes to 252",
                summary=(
                    "The namespace is one file system at every size in "
                    "that range."
                ),
                details=(
                    "A cluster starts at three nodes and grows one node "
                    "at a time to 252, with capacity and performance "
                    "scaling together because every node brings compute "
                    "and network alongside its drives. The number that "
                    "does not change across that entire range is the "
                    "namespace count: growth never adds a second file "
                    "system, so the administrative model at 252 nodes is "
                    "the same as at three."
                ),
            ),
            CatalogOption(
                id="node-pools",
                name="Node pools",
                summary=(
                    "Groups of like nodes, managed as tiers of the one "
                    "namespace."
                ),
                details=(
                    "A node pool is a group of identical nodes — the "
                    "unit OneFS stripes within, so parity math runs over "
                    "matching hardware. A cluster with flash, hybrid, and "
                    "archive nodes has three pools, but still one "
                    "namespace: pools are how tiering policy names its "
                    "targets, not partitions a user can see. This is the "
                    "difference between structure and fragmentation — "
                    "the hardware is organized, the namespace is not "
                    "divided."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="replication",
        name="Snapshots and replication",
        blurb=(
            "Point-in-time copies within the namespace, and copies of it "
            "elsewhere."
        ),
        limits="Directory-level snapshots; async replication between clusters",
        region_ids=["namespace", "mgmt"],
        options=[
            CatalogOption(
                id="snapshots",
                name="Snapshots (SnapshotIQ)",
                summary=(
                    "Per-directory point-in-time copies — no volume to "
                    "snapshot, so the granularity is yours."
                ),
                details=(
                    "Because there is no volume layer, snapshots apply to "
                    "directories: any subtree of the namespace can have "
                    "its own schedule and retention. Conventional NAS "
                    "snapshots the container, which forces everything "
                    "sharing a volume to share a snapshot policy; here "
                    "the policy boundary is wherever you point it."
                ),
            ),
            CatalogOption(
                id="synciq",
                name="Replication (SyncIQ)",
                summary=(
                    "Asynchronous replication of any subtree to another "
                    "cluster."
                ),
                details=(
                    "SyncIQ replicates directories to a second cluster, "
                    "typically at another site, with every node on both "
                    "sides participating in the transfer — replication is "
                    "parallel for the same reason everything else here "
                    "is. Pair it with this repo's PowerProtect twin for "
                    "the distinction that matters: replication protects "
                    "against a site being destroyed, and an immutable "
                    "vault protects against a site being corrupted. "
                    "Replication faithfully copies ransomware to your "
                    "second site, which is why it is not a backup."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="security",
        name="Security and immutability",
        blurb=(
            "Locking parts of the one namespace against change — "
            "compliance retention without a separate compliance silo."
        ),
        limits="Directory-level WORM; encryption at rest; ransomware defense",
        region_ids=["namespace", "mgmt"],
        options=[
            CatalogOption(
                id="smartlock",
                name="Immutability (SmartLock)",
                summary=(
                    "WORM retention applied per directory, inside the "
                    "same namespace."
                ),
                details=(
                    "SmartLock makes directories write-once-read-many "
                    "(WORM): files committed there cannot be modified or "
                    "deleted until their retention clock expires, up to a "
                    "compliance mode aimed at regulated records. As with "
                    "snapshots, the policy attaches to a subtree rather "
                    "than a volume, so immutable and ordinary data live "
                    "in one namespace instead of forcing a separate "
                    "compliance system."
                ),
            ),
            CatalogOption(
                id="encryption",
                name="Encryption and hardening",
                summary=(
                    "Self-encrypting drives and audited, hardened access "
                    "paths."
                ),
                details=(
                    "Data at rest is protected by self-encrypting drives; "
                    "access is auditable per protocol; and API-driven "
                    "detection can watch for the write patterns "
                    "ransomware produces. For the deeper questions this "
                    "repo splits across twins: DellCyberDetect asks "
                    "whether a copy is intact, DellPowerProtect asks "
                    "whether a copy survives, and DellFortZero asks who "
                    "may reach the data at all."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="management",
        name="Management and AIOps",
        blurb=(
            "One cluster, one management surface — and fleet-scale "
            "telemetry for the parts nobody watches by hand."
        ),
        limits="Single-pane cluster management; cloud-based fleet observability",
        region_ids=["mgmt"],
        options=[
            CatalogOption(
                id="cluster-mgmt",
                name="Cluster management",
                summary=(
                    "Administering one namespace, however many nodes hold "
                    "it."
                ),
                details=(
                    "The management surface matches the architecture: one "
                    "cluster, one file system, one place to run the jobs "
                    "— tiering, snapshots, replication, rebalance — that "
                    "keep it healthy. Adding a node is minutes of guided "
                    "work rather than a provisioning project, because "
                    "there is nothing to provision: the node joins, the "
                    "namespace grows, and AutoBalance handles the rest in "
                    "the background."
                ),
            ),
            CatalogOption(
                id="aiops",
                name="Fleet observability (APEX AIOps / CloudIQ)",
                summary=(
                    "Cloud-based analytics across every cluster you run."
                ),
                details=(
                    "Telemetry from the cluster feeds Dell's cloud-based "
                    "observability — twinned separately in this repo as "
                    "DellCloudIQ — which watches capacity trajectories, "
                    "performance anomalies, and component health across a "
                    "fleet. In a system built from interchangeable nodes, "
                    "no single component's decline is dramatic enough to "
                    "notice by hand; a slowly failing drive in one node "
                    "of many is a statistical anomaly, which is exactly "
                    "the shape of problem AIOps exists to catch."
                ),
            ),
        ],
    ),
]
