"""Pure namespace engine for the PowerScale scale-out NAS twin.

``simulate()`` returns the deterministic trace of a cluster being formed,
striped, put to work, outgrown, expanded, and rebalanced — which is the
part of a NAS system's life that reveals its architecture. Same purity rule
as every other twin in this repo: no FastAPI, no IO, no timers — the
frontend owns the playback clock, and each ``NamespaceState`` is plain data
the renderer consumes.

The idea this twin exists to teach: **there are no volumes.**

Conventional NAS makes you carve capacity into fixed containers — volumes
— before you know what you will need. Reality diverges from the guess, and
the system's remaining life is spent on the consequences: one volume 95%
full while another sits empty, and moving capacity between them meaning a
migration, a maintenance window, and a conversation with whoever owns the
data. The administrative work is not caused by the storage being full; it
is caused by capacity having been partitioned into containers that cannot
be resized as fast as the world changes.

OneFS — the operating system every PowerScale node runs — declines to
partition. One file system spans every node. Capacity is added by adding a
node, at which point the single volume simply becomes larger and the
cluster redistributes data onto the new hardware while clients keep
reading. So this trace deliberately *lacks* the steps a conventional NAS
trace would need: there is no "provision a volume" step, no "volume full"
step, and no "migrate data" step. There is an ``addnode`` step and nothing
else, and the tests assert that ``namespaces`` stays at 1 and
``migrations_required`` stays at 0 no matter how much the cluster grows.

The sibling refusal in this repo is DellPowerFlex: it removed the
controller from block storage; OneFS removed the volume from file storage.
Both let a system's shape change while it is running. Capacities and
timings are illustrative but plausible; favor a correct mental model over
measured numbers (project scope guardrail).
"""

from __future__ import annotations

from .models import NamespaceState

# Six drawn nodes. A real cluster runs from three nodes to 252, and the
# namespace is one file system at every size in between.
ALL_NODES = [f"node-{i}" for i in range(1, 7)]

# The cluster starts life with four nodes; five and six arrive mid-trace.
INITIAL_NODES = ALL_NODES[:4]
ADDED_NODES = ALL_NODES[4:]

INITIAL_MEDIA = [f"media-{i}" for i in range(1, 5)]
ALL_MEDIA = [f"media-{i}" for i in range(1, 7)]

# Every protocol region is reachable from every node — no node is the
# "NFS node" or the "SMB head", which is what makes the single namespace
# usable rather than merely true.
PROTOCOLS = ["proto-nfs", "proto-smb", "proto-s3", "proto-hdfs"]

# Phases in which clients are actively being served. Note that this set
# includes the expansion and the rebalance: growth is a background task
# here, not an outage.
SERVING_PHASES = {"serve", "fill", "addnode", "rebalance", "served"}


def simulate() -> list[NamespaceState]:
    """A cluster's life: formed, striped, serving, outgrown, expanded,
    rebalanced, and serving again at larger scale — one namespace
    throughout."""
    return [
        NamespaceState(
            step=0,
            phase="off",
            label="Four nodes racked, drives unjoined",
            description=(
                "Four PowerScale nodes in a rack, each carrying its own "
                "compute, memory, networking, and drives — about 400 TB of "
                "raw capacity between them, none of it yet part of "
                "anything. Worth noticing before the software starts: "
                "nobody is drawing a partition map. On a conventional NAS "
                "this is where an administrator would begin carving "
                "capacity into volumes — fixed containers sized against a "
                "guess about the future. Here that step simply never "
                "happens. The number of file systems this cluster will "
                "ever present is one, and it holds at one from this step "
                "to the last."
            ),
            active_regions=[],
            elapsed_seconds=0,
            nodes=0,
            namespaces=1,
            capacity_tb=400,
            used_percent=0,
            migrations_required=0,
        ),
        NamespaceState(
            step=1,
            phase="form",
            label="Nodes join — OneFS forms one cluster",
            description=(
                "The nodes find each other over the back-end interconnect "
                "— a private network reserved for traffic between nodes — "
                "and OneFS, the operating system every PowerScale node "
                "runs, joins them into a single cluster. There is no "
                "controller among them and no head unit: every node runs "
                "the same software, holds a share of the same file system, "
                "and will answer clients directly. The cluster that forms "
                "here is the unit of everything that follows — capacity, "
                "performance, and protection all belong to it as a whole, "
                "not to any box inside it."
            ),
            active_regions=[*INITIAL_NODES, "interconnect", "mgmt"],
            elapsed_seconds=45,
            cycle_cost=2,
            nodes=4,
            namespaces=1,
            capacity_tb=400,
            used_percent=0,
            migrations_required=0,
        ),
        NamespaceState(
            step=2,
            phase="stripe",
            label="One file system striped across every node",
            description=(
                "OneFS lays out the single file system across all four "
                "nodes at once. Every file is cut into stripes and spread "
                "over the cluster with erasure coding — mathematical "
                "parity stored alongside the data, from which any lost "
                "stripe can be recomputed — so protection is a property of "
                "the file, not of a RAID group inside one box. No node "
                "holds a whole file; every node holds part of every file. "
                "This is what it means for there to be no volumes: the "
                "file system's boundary is the cluster's boundary, and "
                "nothing smaller than the cluster exists to fill up."
            ),
            active_regions=[
                *INITIAL_NODES, *INITIAL_MEDIA, "interconnect", "namespace",
            ],
            elapsed_seconds=240,
            cycle_cost=4,
            nodes=4,
            namespaces=1,
            capacity_tb=400,
            used_percent=0,
            migrations_required=0,
        ),
        NamespaceState(
            step=3,
            phase="serve",
            label="All protocols up, on every node",
            description=(
                "The access layer comes up: NFS (the Network File System "
                "used by Unix and Linux clients), SMB (Server Message "
                "Block, the Windows file-sharing protocol), S3 (the "
                "HTTP-based object protocol), and HDFS (the Hadoop "
                "Distributed File System interface used by analytics "
                "platforms). All four reach the same files, and — the part "
                "that matters — all four are served by every node. There "
                "is no 'NFS node' and no 'SMB head'; a client can mount "
                "the namespace through any node in the cluster and see "
                "the same single file system, which is what makes one "
                "namespace usable rather than merely true."
            ),
            active_regions=[
                *INITIAL_NODES, *INITIAL_MEDIA, "interconnect",
                "namespace", *PROTOCOLS,
            ],
            elapsed_seconds=300,
            nodes=4,
            namespaces=1,
            capacity_tb=400,
            used_percent=18,
            migrations_required=0,
        ),
        NamespaceState(
            step=4,
            phase="fill",
            label="The namespace fills — and there is no volume to be full",
            description=(
                "Months compressed into a step: data pours in and the one "
                "namespace climbs past 80% used. On a conventional NAS "
                "this is where the pathology starts — not because the "
                "system is full, but because some *volume* is. One "
                "container hits 95% while another sits half empty, and "
                "fixing that means a migration, a maintenance window, and "
                "a negotiation with whoever owns the data. Here there is "
                "no container to hit 95%. The whole cluster is filling, "
                "evenly, and the only decision approaching is the simple "
                "one: add hardware. Note the counter that has not moved — "
                "migrations required is zero, and it stays there."
            ),
            active_regions=[
                *INITIAL_NODES, *INITIAL_MEDIA, "interconnect",
                "namespace", *PROTOCOLS,
            ],
            elapsed_seconds=900,
            cycle_cost=2,
            nodes=4,
            namespaces=1,
            capacity_tb=400,
            used_percent=81,
            migrations_required=0,
        ),
        NamespaceState(
            step=5,
            phase="addnode",
            label="Two nodes join — the volume simply becomes larger",
            description=(
                "Nodes five and six are cabled to the interconnect and "
                "join the cluster; OneFS absorbs them in about a minute. "
                "Watch the counters do the whole argument: capacity jumps "
                "from 400 TB to 600 TB, used falls from 81% to 54% — and "
                "namespaces stays at one, because the existing file system "
                "*became larger* rather than gaining a sibling. Nothing "
                "was provisioned, nothing was carved, and no data moved "
                "yet. On a conventional NAS this moment is a planning "
                "exercise: size the new volumes, decide what migrates "
                "onto them, book the windows. Here it is a purchase and "
                "two cables."
            ),
            active_regions=[
                *ALL_NODES, *ALL_MEDIA, "interconnect",
                "namespace", *PROTOCOLS, "mgmt",
            ],
            elapsed_seconds=960,
            cycle_cost=2,
            nodes=6,
            namespaces=1,
            capacity_tb=600,
            used_percent=54,
            migrations_required=0,
        ),
        NamespaceState(
            step=6,
            phase="rebalance",
            label="Data redistributes onto the new nodes — live",
            description=(
                "AutoBalance — the OneFS job that keeps data spread evenly "
                "— restripes files onto the new nodes in the background, "
                "and this is deliberately the longest stage in the trace. "
                "Moving a share of everything onto new hardware is "
                "genuinely slow, and it is the price of never having to "
                "migrate: the work a conventional NAS spreads across "
                "years of volume shuffling happens here, once, invisibly. "
                "The word invisibly is load-bearing. Every protocol is "
                "still up on every node, clients keep reading and writing "
                "the same paths, and nothing above the cluster knows the "
                "layout underneath is changing. Expansion is a background "
                "task, not an outage."
            ),
            active_regions=[
                *ALL_NODES, *ALL_MEDIA, "interconnect",
                "namespace", *PROTOCOLS,
            ],
            elapsed_seconds=1200,
            cycle_cost=6,
            nodes=6,
            namespaces=1,
            capacity_tb=600,
            used_percent=54,
            migrations_required=0,
            rebalancing=True,
        ),
        NamespaceState(
            step=7,
            phase="served",
            label="Serving at six nodes — same single namespace",
            description=(
                "Steady state at larger scale. Six nodes now serve the "
                "one file system, every stripe is balanced across all of "
                "them, and the two new nodes carry their full share of "
                "reads, writes, and protection. Add up what the expansion "
                "cost in administrative terms: no volume was provisioned, "
                "no data was migrated by hand, no client remounted "
                "anything, and no capacity-planning ritual was booked for "
                "next quarter. In this repo, DellPowerFlex shows what "
                "block storage gains by deleting the controller. This "
                "twin is the same refusal aimed at file storage: OneFS "
                "deleted the volume, and this step is what growth looks "
                "like without it."
            ),
            active_regions=[
                *ALL_NODES, *ALL_MEDIA, "interconnect",
                "namespace", *PROTOCOLS, "mgmt",
            ],
            elapsed_seconds=1800,
            nodes=6,
            namespaces=1,
            capacity_tb=600,
            used_percent=57,
            migrations_required=0,
        ),
    ]
