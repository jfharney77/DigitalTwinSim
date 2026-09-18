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
node, at which point the single namespace simply becomes larger and the
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

from .leveling import L
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
            description=L(
                novice=(
                    'Four storage computers, called nodes, sit in a rack. Each one '
                    'has its own processor, memory, network connections, and disk '
                    'drives, and together they hold about 400 terabytes — enough '
                    'for tens of millions of photos. Right now they are separate '
                    'machines that are not yet working together. On most file '
                    'storage systems, this is the moment someone would sit down and'
                    ' divide the space into fixed chunks called volumes, guessing '
                    'how big each one needs to be for years ahead. Here nobody does'
                    ' that, and nobody ever will. The cluster will offer exactly '
                    'one shared file system, from the first step to the last.'
                ),
                plain=(
                    'Four PowerScale nodes sit in a rack. Each has its own '
                    'processor, memory, networking, and drives, about 400 TB raw '
                    'between them, but none of it belongs to anything yet. On a '
                    'conventional NAS an administrator would now split that space '
                    'into volumes, fixed containers sized against a guess about the'
                    ' future. That step never happens here. This cluster will '
                    'present one file system, and the count stays at one for the '
                    'whole trace.'
                ),
                standard=(
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
                technical=(
                    'Four nodes racked, each a self-contained compute, memory, '
                    'network, and drive unit — ~400 TB raw in aggregate, not yet '
                    'clustered. The step a conventional NAS would perform next, '
                    'provisioning volumes or aggregates against a capacity '
                    'forecast, is absent from this trace by design. The namespace '
                    'count is 1 here and is invariant through the final step.'
                ),
                expert=(
                    'Four unjoined nodes, ~400 TB raw. No volume or aggregate '
                    'provisioning follows — none exists in OneFS. Namespace count: '
                    '1, invariant for the trace.'
                ),
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
            description=L(
                novice=(
                    'The nodes find each other over a private network cable that '
                    'only they use, called the back-end interconnect. Each node '
                    'runs the same software, OneFS, and that software joins them '
                    'into one team, called a cluster. There is no boss machine in '
                    'charge of the others: every node does the same work, keeps '
                    "part of the same data, and can answer requests from people's "
                    'computers by itself. From now on, the storage space, the '
                    'speed, and the safety of the data all belong to the whole '
                    'cluster, not to any one box.'
                ),
                plain=(
                    'The nodes find each other over the back-end interconnect, a '
                    'private network used only for traffic between them, and OneFS '
                    'joins them into one cluster. No node is in charge: there is no'
                    ' controller and no head unit. Every node runs the same '
                    'software, holds part of the same file system, and answers '
                    'clients directly. Capacity, performance, and protection now '
                    'belong to the cluster as a whole.'
                ),
                standard=(
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
                technical=(
                    'Nodes discover each other over the back-end interconnect and '
                    'OneFS forms a single cluster with symmetric membership — no '
                    'controller, no head node, no metadata server. Every node runs '
                    'the same OS, owns a share of the file system, and serves '
                    'clients directly. Capacity, throughput, and protection are '
                    'cluster-level properties from here on.'
                ),
                expert=(
                    'Cluster formation over the back-end network. Symmetric '
                    'membership — no controller, head, or dedicated MDS; capacity, '
                    'performance, and protection are cluster-scoped.'
                ),
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
            description=L(
                novice=(
                    'OneFS now sets up a single file system that stretches across '
                    'all four nodes at once. Every file gets cut into pieces, and '
                    'the pieces are spread over all the nodes. Along with the '
                    'pieces, OneFS stores some extra math, called parity, so that '
                    'if a piece is ever lost it can be rebuilt from the others — a '
                    'bit like being able to work out a missing number in a sum if '
                    'you know the total. No single node holds a whole file; every '
                    "node holds a slice of every file. That is what 'no volumes' "
                    'means in practice: the only edge the file system has is the '
                    'edge of the whole cluster, so there is no smaller box that '
                    'could fill up on its own.'
                ),
                plain=(
                    'OneFS lays the single file system out across all four nodes at'
                    ' once. Every file is cut into stripes and spread over the '
                    'cluster with erasure coding: extra parity data stored next to '
                    'the data, from which a lost stripe can be recalculated. '
                    'Protection belongs to the file, not to a RAID group in one '
                    'box. No node holds a whole file, and every node holds part of '
                    'every file. The file system ends where the cluster ends, so '
                    'nothing smaller than the cluster exists to fill up.'
                ),
                standard=(
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
                technical=(
                    'OneFS stripes the file system across all four nodes. Each file'
                    ' is split into stripe units and protected with Reed-Solomon '
                    'erasure coding at a per-file protection level, so protection '
                    'is a file attribute rather than a property of a RAID group '
                    'bound to one enclosure. No node holds a complete file. The '
                    'file-system boundary equals the cluster boundary; there is no '
                    'sub-cluster container to exhaust.'
                ),
                expert=(
                    'Per-file striping across all nodes with Reed-Solomon FEC; '
                    'protection is a file attribute, not a disk-group one. File-'
                    'system boundary equals cluster boundary.'
                ),
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
            description=L(
                novice=(
                    'Now the cluster opens its doors to the computers that will use'
                    ' it. It speaks four languages for sharing files: NFS, used by '
                    'Linux and Unix computers; SMB, used by Windows; S3, the web-'
                    'style way of storing objects used by many cloud apps; and '
                    'HDFS, used by big data analysis tools. All four languages '
                    'reach the very same files. Even better, every node speaks all '
                    'four. There is no special node just for Windows or just for '
                    'Linux, so a computer can connect through any node and see '
                    'exactly the same single file system. That is what makes one '
                    'shared namespace easy to use, not just true on paper.'
                ),
                plain=(
                    'The access layer comes up: NFS for Unix and Linux clients, SMB'
                    ' for Windows file sharing, S3 for object access over HTTP, and'
                    ' HDFS for analytics platforms such as Hadoop. All four reach '
                    'the same files, and every node serves all four. There is no '
                    'NFS node and no SMB head, so a client can mount through any '
                    'node and see the same single file system. That is what makes '
                    'one namespace usable rather than merely true.'
                ),
                standard=(
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
                technical=(
                    'Protocol services start on every node: NFSv3/v4, SMB, S3, and '
                    'HDFS, all addressing the same /ifs tree. Protocol service is '
                    'symmetric — no protocol is pinned to a subset of nodes — so a '
                    'client can connect through any node and resolve the same '
                    'paths. Symmetric multiprotocol access is what makes a single '
                    'namespace operationally useful rather than a nominal property.'
                ),
                expert=(
                    'NFS, SMB, S3, and HDFS up on every node against one /ifs tree.'
                    ' Symmetric multiprotocol service — no protocol-specific heads.'
                ),
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
            description=L(
                novice=(
                    'Imagine months passing in one step: data pours in, and the '
                    'shared space climbs past 80% full. On most file storage, this '
                    'is where trouble starts. The problem is not that the whole '
                    'system is full — it is that one of the fixed chunks, one '
                    'volume, is full, while another sits half empty. Fixing that '
                    'means copying data from one chunk to another, planning a time '
                    'when nobody can use it, and asking the people who own the data'
                    ' for permission. Here there are no chunks to get stuck in. The'
                    ' whole cluster fills up evenly, and the only choice coming up '
                    'is an easy one: buy more hardware. Look at the migrations '
                    'counter — it still reads zero, and it will stay at zero.'
                ),
                plain=(
                    'Months pass in one step: data pours in and the one namespace '
                    'climbs past 80% used. On a conventional NAS the trouble starts'
                    ' here, not because the system is full but because one volume '
                    'is. One container hits 95% while another sits half empty, and '
                    'fixing that takes a migration, a maintenance window, and a '
                    "negotiation with the data's owner. Here there is no container "
                    'to hit 95%. The whole cluster fills evenly, and the only '
                    'decision coming is to add hardware. Migrations required stays '
                    'at zero.'
                ),
                standard=(
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
                technical=(
                    'Utilisation climbs past 80% across the single namespace. On '
                    'volume-based NAS the failure mode at this point is local '
                    'exhaustion — one volume at 95% while others are underused — '
                    'resolved only by migration and a maintenance window. With no '
                    'sub-cluster containers, utilisation here is uniform across the'
                    ' cluster, and the only pending action is capacity expansion. '
                    'migrationsRequired remains 0.'
                ),
                expert=(
                    '81% used, uniform across the namespace. No per-volume '
                    'exhaustion is possible; the only pending action is a node add.'
                    ' migrationsRequired = 0.'
                ),
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
            label="Two nodes join — the namespace simply becomes larger",
            description=L(
                novice=(
                    'Two new nodes, number five and number six, are plugged into '
                    'the private network and join the team in about a minute. Now '
                    'look at the numbers: the total space jumps from 400 to 600 '
                    'terabytes, and the used share drops from 81% to 54%. But the '
                    'count of namespaces stays at one. The existing shared file '
                    'system simply grew bigger — nobody created a second one next '
                    'to it. Nothing had to be set up, nothing had to be divided, '
                    'and no data has moved yet. On other file storage, this moment '
                    'would mean a planning project: deciding how big the new chunks'
                    ' should be, what data should move into them, and when the '
                    'system could be taken offline. Here it is just a purchase and '
                    'two cables.'
                ),
                plain=(
                    'Nodes five and six are cabled to the interconnect and join the'
                    ' cluster in about a minute. Capacity jumps from 400 TB to 600 '
                    'TB and used falls from 81% to 54%, while namespaces stays at '
                    'one: the existing file system grew instead of gaining a '
                    'sibling. Nothing was provisioned or carved, and no data has '
                    'moved yet. On a conventional NAS this is a planning exercise: '
                    'size new volumes, decide what migrates, book the windows. Here'
                    ' it is a purchase and two cables.'
                ),
                standard=(
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
                technical=(
                    'Nodes 5 and 6 join over the back-end network; OneFS admits '
                    'them in roughly a minute. Capacity rises 400 → 600 TB and '
                    'utilisation falls 81% → 54% with namespace count unchanged — '
                    'the existing file system is extended, not supplemented. No '
                    'provisioning, no carving, and no data movement yet. The '
                    'volume-based equivalent requires sizing new volumes, planning '
                    'migrations, and scheduling windows.'
                ),
                expert=(
                    'Nodes 5–6 join (~1 min). 400 → 600 TB, 81% → 54%, namespaces '
                    'still 1. No provisioning; data movement deferred to '
                    'AutoBalance.'
                ),
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
            description=L(
                novice=(
                    'Now OneFS starts a background job called AutoBalance. It moves'
                    ' a share of the existing data onto the two new nodes, so all '
                    'six carry an even load. This is on purpose the slowest step in'
                    ' the whole story: copying part of everything onto new machines'
                    ' really does take time. That time is the price of never having'
                    ' to do a big planned move later. The work other systems spread'
                    ' over years of shuffling data between chunks happens here, '
                    'once, quietly. And it really is quiet: people can still open, '
                    'save, and read their files the whole time, through any node, '
                    'using the same folder paths as before. Nobody outside the '
                    'cluster can even tell the data is being rearranged. Growing '
                    'the system is a background job, not a shutdown.'
                ),
                plain=(
                    'AutoBalance, the OneFS job that keeps data spread evenly, '
                    'restripes files onto the new nodes in the background, and this'
                    ' is on purpose the longest stage in the trace. Moving a share '
                    'of everything onto new hardware is slow, and that is the price'
                    ' of never migrating: the work a conventional NAS spreads over '
                    'years of volume shuffling happens here, once. It is also '
                    'invisible to clients. Every protocol stays up on every node, '
                    'clients keep reading and writing the same paths, and nothing '
                    'above the cluster sees the layout change. Expansion is a '
                    'background task, not an outage.'
                ),
                standard=(
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
                technical=(
                    'AutoBalance restripes existing data onto the new nodes as a '
                    'background job — the longest stage in the trace by design. '
                    'Restriping a proportional share of all data is I/O-bound and '
                    'slow; it is the amortised cost of never running a migration. '
                    'Protocol service continues on every node throughout, client '
                    'paths are unchanged, and the relayout is invisible above the '
                    'file system. Expansion is an online operation.'
                ),
                expert=(
                    'AutoBalance restripe onto the new nodes — longest stage, '
                    'I/O-bound, online. Protocols up on all nodes; paths unchanged.'
                    ' Expansion without an outage.'
                ),
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
            description=L(
                novice=(
                    'Everything has settled at the bigger size. Six nodes now share'
                    ' the one file system, the data is spread evenly across all of '
                    'them, and the two new nodes do their full share of the work of'
                    ' reading, writing, and protecting data. Count up what growing '
                    'the system cost the people running it: no new chunk of storage'
                    " was set up, nobody moved data by hand, nobody's computer had "
                    'to reconnect, and no planning meeting had to be booked for '
                    'next quarter. Another twin in this collection, DellPowerFlex, '
                    'shows what block storage gains by getting rid of the '
                    'controller box. This twin makes the same kind of move for file'
                    ' storage: OneFS got rid of the volume, and this step shows '
                    'what growing looks like without one.'
                ),
                plain=(
                    'Steady state at the larger size. Six nodes serve the one file '
                    'system, every stripe is balanced across them, and the two new '
                    'nodes carry their full share of reads, writes, and protection.'
                    ' The expansion cost nothing administrative: no volume '
                    'provisioned, no data migrated by hand, no client remounted, no'
                    ' capacity-planning meeting booked. DellPowerFlex, elsewhere in'
                    ' this repo, shows what block storage gains by removing the '
                    'controller. This twin makes the same refusal for file storage:'
                    ' OneFS removed the volume, and this step is growth without it.'
                ),
                standard=(
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
                technical=(
                    'Steady state at six nodes. Stripes are balanced cluster-wide '
                    'and the new nodes carry a proportional share of I/O and '
                    'protection. Administrative cost of the expansion: zero volumes'
                    ' provisioned, zero manual migrations, zero client remounts, no'
                    ' capacity-planning cycle. DellPowerFlex is the block-storage '
                    'counterpart (the controller removed); this twin removes the '
                    'volume for file storage.'
                ),
                expert=(
                    'Balanced at six nodes. Zero provisioning, migration, or '
                    'remount. Counterpart: DellPowerFlex (no controller) — here, no'
                    ' volume.'
                ),
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
