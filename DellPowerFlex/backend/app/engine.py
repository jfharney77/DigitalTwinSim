"""Pure cluster engine for the PowerFlex software-defined storage twin.

``simulate()`` returns the deterministic trace of a pool being built, put
under load, losing a server, and recovering — which is the only part of a
storage system's life that reveals its architecture. Same purity rule as
every other twin in this repo: no FastAPI, no IO, no timers — the frontend
owns the playback clock, and each ``ClusterState`` is plain data the
renderer consumes.

The idea this twin exists to teach: **there is no controller.**

PowerStore and PowerMax, twinned elsewhere here, are controller
architectures. Every byte a host writes crosses a controller, so the
controller is at once the performance ceiling and the failure domain, and
the design's real work is making that centrality survivable — dual nodes,
mirrored cache, vault-on-power-loss, active-active failover.

PowerFlex deletes the centre instead. Servers contribute local NVMe;
volumes are chopped into chunks and scattered, redundantly, across every
node; clients hold the map and talk straight to whichever nodes hold what
they want. The metadata manager referees but carries nothing.

The payoff shows up at the failure. In a controller array, one surviving
controller performs the rebuild — a single device reading, a single device
writing, hours at reduced protection. Here the lost node's data lives in
fragments on every other node, so every survivor rebuilds a sliver at once,
reading from every other survivor. Recovery therefore gets faster as the
cluster grows, which is the reverse of how storage systems normally age.

Two counters carry it. ``rebuild_participants`` equals ``nodes_online``
during the rebuild — never a subset. And ``cycle_cost`` deliberately peaks
on *building* the pool rather than on recovering it, inverting this repo's
usual pattern: in the other twins the recovery-ish stage is the long one,
and here it is not, because that is the claim.

Capacities and timings are illustrative but plausible; favor a correct
mental model over measured numbers (project scope guardrail).
"""

from __future__ import annotations

from .leveling import L
from .models import ClusterState

# Six drawn nodes. A real pool runs from three to past two thousand, which
# is the scale at which many-to-many rebuild stops being a nicety.
ALL_NODES = [f"node-{i}" for i in range(1, 7)]

# The node that dies mid-trace. Nothing about it is special, which is the
# point — any of the six would do.
FAILED_NODE = "node-6"

SURVIVORS = [n for n in ALL_NODES if n != FAILED_NODE]

# Phases in which clients are actually doing I/O.
IO_PHASES = {"io", "failure", "rebuild", "rebalanced", "steady"}

# Phases where the pool is at its normal, uneventful working state. The
# coordinator must be absent from these — see
# test_the_coordinator_is_absent_from_the_steady_data_path.
STEADY_PHASES = {"io", "rebalanced", "steady"}


def simulate() -> list[ClusterState]:
    """A pool's life: assembled, loaded, wounded, and healed."""
    return [
        ClusterState(
            step=0,
            phase="off",
            label="Servers racked, drives unpooled",
            description=L(
                novice=(
                    "Six ordinary servers, each with its own drives inside. Right "
                    "now there is no shared storage here at all — just six machines "
                    "with disks in them, which is what they would be in any "
                    "equipment rack. Everything that follows is software deciding "
                    "to treat all those separate drives as one pool, with no extra "
                    "hardware bought and no dedicated storage network involved."
                ),
                plain=(
                    "Six ordinary servers, each with local NVMe drives belonging to "
                    "it alone. At this point there is no shared storage — just six "
                    "machines with disks. Everything that follows is software "
                    "treating those separate drives as one pool, with no additional "
                    "hardware and no storage-area network."
                ),
                standard=(
                    "Six ordinary servers, each with local NVMe drives that "
                    "belong to it alone. At this moment there is no shared "
                    "storage here at all — just six machines with disks in "
                    "them, which is exactly what they would be in any rack. "
                    "Everything that follows is software deciding to treat "
                    "those separate drives as one pool, with no additional "
                    "hardware and no storage-area network involved."
                ),
                technical=(
                    "Six commodity servers with local NVMe. No shared storage yet. "
                    "What follows is entirely software: the pool is formed without "
                    "additional hardware and without a dedicated SAN."
                ),
                expert=(
                    "Six commodity nodes, local NVMe, no shared storage. Pool "
                    "formation is software-only — no SAN, no added hardware."
                ),
            ),
            active_regions=[],
            nodes_online=0,
            rebuild_participants=0,
            iops_thousands=0,
            protected_percent=0,
            elapsed_seconds=0,
        ),
        ClusterState(
            step=1,
            phase="cluster",
            label="Nodes join — a metadata manager is elected",
            description=L(
                novice=(
                    "The servers find each other over the ordinary office network "
                    "and form a group, choosing one component to keep the map of "
                    "what will be stored where. Note the word: it is a *manager*, "
                    "not a controller. It will decide where things go and settle "
                    "arguments when a machine stops responding, and it will never "
                    "have any of your actual data pass through it. That distinction "
                    "is the whole design in miniature, and it is why the block is "
                    "drawn small and off to one side."
                ),
                plain=(
                    "The servers find each other over ordinary IP and form a "
                    "cluster, electing a metadata manager to hold the map of what "
                    "lives where. Note the word: manager, not controller. It "
                    "decides placement and referees failures, and no byte of client "
                    "data ever passes through it. That distinction is the "
                    "architecture in miniature, and it is why the block is drawn "
                    "small and off to one side."
                ),
                standard=(
                    "The servers find each other over ordinary IP and form a "
                    "cluster, electing a metadata manager to hold the map of "
                    "what will live where. Note the word: manager, not "
                    "controller. It will decide placement and referee "
                    "failures, and it will never have a byte of client data "
                    "pass through it. That distinction is the architecture in "
                    "miniature, and it is why the block is drawn small and off "
                    "to one side in the map."
                ),
                technical=(
                    "Cluster forms over IP; a metadata manager is elected to hold "
                    "the chunk map. Manager, not controller — it handles placement "
                    "and failure arbitration and carries no client data. The "
                    "distinction is the architecture, and the geometry reflects it."
                ),
                expert=(
                    "Cluster forms over IP; MDM elected for placement and failure "
                    "arbitration. Control plane, not data plane — reflected in the "
                    "geometry."
                ),
            ),
            active_regions=[*ALL_NODES, "fabric", "mdm"],
            nodes_online=6,
            rebuild_participants=0,
            iops_thousands=0,
            protected_percent=0,
            elapsed_seconds=30,
            cycle_cost=2,
        ),
        ClusterState(
            step=2,
            phase="pool",
            label="Chunks scattered and mirrored across every node",
            description=L(
                novice=(
                    "The long stage, and the one that pays for everything later. "
                    "Each server's drives are handed to a shared pool, and the "
                    "software cuts the total capacity into small pieces which it "
                    "spreads — with duplicates — across all six machines. No single "
                    "server holds a whole volume; every server holds a piece of "
                    "every volume. Building that arrangement genuinely takes time, "
                    "and it is deliberately the slowest step here. Watch what it "
                    "buys: because the data is already everywhere, nothing later "
                    "has to move it there in a hurry."
                ),
                plain=(
                    "The long stage, and the one that earns everything later. Each "
                    "server's drives join a shared pool, and the software chops the "
                    "capacity into chunks distributed — redundantly — across all "
                    "six nodes. No node holds a whole volume; every node holds a "
                    "piece of every volume. Building this takes real time and is "
                    "deliberately the slowest stage in the trace. Watch what that "
                    "buys: because the data is already everywhere, nothing later "
                    "has to move it there in a hurry."
                ),
                standard=(
                    "The long stage, and the one that earns everything later. "
                    "Each server's drives are contributed to a shared pool, "
                    "and the software chops the pool's capacity into small "
                    "chunks which it distributes — redundantly — across all "
                    "six nodes. No node holds a whole volume; every node holds "
                    "a piece of every volume. Building this arrangement takes "
                    "real time, and it is deliberately the slowest stage in "
                    "this trace. Watch what that buys: because the data is "
                    "already everywhere, nothing later in the pool's life has "
                    "to move it there in a hurry."
                ),
                technical=(
                    "The long stage, and the one that earns the rest. Drives are "
                    "contributed to a shared pool; capacity is chunked and "
                    "distributed redundantly across all six nodes, so no node holds "
                    "a whole volume and every node holds part of each. Deliberately "
                    "the max-dwell stage — the scatter is the prepayment that makes "
                    "later recovery short."
                ),
                expert=(
                    "Chunked, redundantly scattered across all nodes; no node holds "
                    "a whole volume. Max dwell by design — the scatter prepays the "
                    "rebuild."
                ),
            ),
            active_regions=[*ALL_NODES, "fabric", "mdm", "protection"],
            nodes_online=6,
            rebuild_participants=0,
            iops_thousands=0,
            protected_percent=100,
            elapsed_seconds=180,
            cycle_cost=6,
        ),
        ClusterState(
            step=3,
            phase="volumes",
            label="Volumes presented — clients receive the map",
            description=L(
                novice=(
                    "Volumes are created and offered to the servers that will use "
                    "them. Each of those receives the map of where the pieces live, "
                    "which is what lets it contact the right machines directly "
                    "instead of sending requests somewhere to be passed along. From "
                    "the application's point of view it has just been handed an "
                    "ordinary disk; from the pool's point of view it has just "
                    "gained a participant that knows where everything is."
                ),
                plain=(
                    "Volumes are created and presented to the consuming servers. "
                    "Each client receives the chunk map, which is what lets it "
                    "address nodes directly rather than sending requests somewhere "
                    "to be forwarded. To the application it is an ordinary block "
                    "device; to the pool it is a peer that knows where everything "
                    "is."
                ),
                standard=(
                    "Volumes are created and presented to the consuming "
                    "servers. Each client receives the chunk map, which is "
                    "what lets it address nodes directly rather than sending "
                    "requests somewhere to be forwarded. From the "
                    "application's point of view it has just been given an "
                    "ordinary block device; from the pool's point of view it "
                    "has just acquired a peer that knows where everything is."
                ),
                technical=(
                    "Volumes presented; clients receive the chunk map, enabling "
                    "direct addressing rather than forwarding. Ordinary block "
                    "device upstream, map-aware peer downstream."
                ),
                expert=(
                    "Volumes presented, chunk map distributed to clients. Direct "
                    "addressing, no forwarding tier."
                ),
            ),
            active_regions=[*ALL_NODES, "clients", "fabric", "mdm"],
            nodes_online=6,
            rebuild_participants=0,
            iops_thousands=0,
            protected_percent=100,
            elapsed_seconds=200,
        ),
        ClusterState(
            step=4,
            phase="io",
            label="Steady I/O — every client talking to every node",
            description=L(
                novice=(
                    "Real work arrives, and the traffic pattern is the whole "
                    "argument. Every client is talking to every server at once, "
                    "because its data is on every server at once. There is no queue "
                    "in front of a special machine and no path that all requests "
                    "have to share, so the total speed is simply the sum of what "
                    "the servers can do — which is why very large systems of this "
                    "kind are rated in the hundreds of millions of operations per "
                    "second. Notice which block is dark: the manager. It handed out "
                    "the map and got out of the way."
                ),
                plain=(
                    "Load arrives, and the traffic pattern is the argument. Every "
                    "client talks to every node at once, because its data is on "
                    "every node at once. There is no queue in front of a controller "
                    "and no shared path, so aggregate throughput is the sum of what "
                    "the servers can do — which is why a large pool is rated past "
                    "240 million operations per second. Notice which block is dark: "
                    "the metadata manager. It handed out the map and stepped out of "
                    "the way."
                ),
                standard=(
                    "Load arrives, and the traffic pattern is the whole "
                    "argument. Every client is talking to every node at once, "
                    "because its data is on every node at once. There is no "
                    "queue in front of a controller and no path that all "
                    "requests share, so aggregate throughput is simply the sum "
                    "of what the servers can do — which is why the published "
                    "ceiling for a large pool runs to 240 million operations "
                    "per second. Notice which block is dark: the metadata "
                    "manager. It handed out the map and stepped out of the "
                    "way."
                ),
                technical=(
                    "Steady I/O. Every client addresses every node, because its "
                    "data is on every node — no controller queue, no shared path, "
                    "so aggregate throughput sums across nodes; hence the 240M IOPS "
                    "ceiling for a large pool. The MDM is dark: map distributed, "
                    "control plane out of the path."
                ),
                expert=(
                    "Full client-to-node fan-out; no shared path, throughput sums "
                    "across nodes (240M IOPS at scale). MDM dark — out of the data "
                    "path."
                ),
            ),
            active_regions=[*ALL_NODES, "clients", "fabric"],
            nodes_online=6,
            rebuild_participants=0,
            iops_thousands=1800,
            protected_percent=100,
            elapsed_seconds=240,
            cycle_cost=2,
        ),
        ClusterState(
            step=5,
            phase="failure",
            label="A node dies — and the clients barely notice",
            description=L(
                novice=(
                    "Node 6 stops responding: a power supply, a motherboard, "
                    "somebody pulling the wrong cable. On a conventional storage "
                    "system this is the dramatic moment — switching over, "
                    "renegotiating paths, a pause the applications can feel. Here "
                    "the clients simply stop talking to one address and carry on "
                    "with the other five, because a second copy of everything node "
                    "6 held is already sitting on those five and always was. "
                    "Throughput drops by roughly the share of the system that "
                    "vanished, and nothing else happens. Protection, though, has "
                    "genuinely fallen: something that had two copies now has one, "
                    "and until that is fixed a second failure would be a real loss."
                ),
                plain=(
                    "Node 6 stops answering. In a controller array this is the "
                    "dramatic moment — failover, path renegotiation, a pause the "
                    "applications feel. Here the clients stop sending to one "
                    "address and keep sending to the other five, because a second "
                    "copy of everything node 6 held is already on those five and "
                    "always was. Throughput dips by roughly the share of the "
                    "cluster that vanished, and nothing else happens. Protection "
                    "has genuinely fallen, though: a chunk with two copies now has "
                    "one, and until that is fixed a second failure would be a real "
                    "loss."
                ),
                standard=(
                    "Node 6 stops answering: a power supply, a motherboard, "
                    "someone pulling the wrong cable. In a controller array "
                    "this is the dramatic moment — failover, path "
                    "renegotiation, a pause the applications can feel. Here "
                    "the clients simply stop sending to one address and keep "
                    "sending to the other five, because a second copy of "
                    "everything node 6 held is already sitting on those five "
                    "and always was. Throughput dips by roughly the share of "
                    "the cluster that just vanished, and nothing else happens. "
                    "Protection, though, has genuinely fallen: a chunk that "
                    "had two copies now has one, and until that is fixed a "
                    "second failure would be a real loss."
                ),
                technical=(
                    "Node loss. In a controller array this is failover — path "
                    "renegotiation and an application-visible pause. Here clients "
                    "drop one address and continue against the remaining five, "
                    "since the redundant copies were already resident there. "
                    "Throughput falls by the lost node's share; nothing else "
                    "changes. Protection is genuinely degraded until rebuild — "
                    "single-copy chunks would not survive a second loss."
                ),
                expert=(
                    "Node loss: no failover event, clients simply drop an address. "
                    "Throughput -1/n; redundancy degraded to single-copy until "
                    "rebuild completes."
                ),
            ),
            active_regions=[*SURVIVORS, "clients", "fabric", "mdm", "protection"],
            nodes_online=5,
            rebuild_participants=0,
            iops_thousands=1620,
            protected_percent=68,
            elapsed_seconds=246,
        ),
        ClusterState(
            step=6,
            phase="rebuild",
            label="Every surviving node rebuilds a sliver, all at once",
            description=L(
                novice=(
                    "The reason this design exists. The lost machine's data was not "
                    "kept on one partner device — it was in fragments spread across "
                    "all five survivors. So the repair is many-to-many: each of the "
                    "five rebuilds a fifth of what was lost, reading from the other "
                    "four, all at the same time. Every machine helps; none watches. "
                    "Run that forward and the striking property appears — in a "
                    "hundred-machine pool, a hundred machines each rebuild a "
                    "hundredth, so the repair is about twenty times faster than it "
                    "is here in a cluster twenty times smaller. Recovery gets "
                    "quicker as the system grows, which is the reverse of how "
                    "storage normally ages."
                ),
                plain=(
                    "The reason this architecture exists. The lost node's data was "
                    "not on one partner device — it was in fragments across all "
                    "five survivors. So the rebuild is many-to-many: each of the "
                    "five reconstructs a fifth of what was lost, reading from the "
                    "other four, simultaneously. Every node participates; none "
                    "spectates. Run it forward and the striking property appears — "
                    "in a hundred-node pool, a hundred nodes each rebuild a "
                    "hundredth, roughly twenty times faster than here. Rebuild time "
                    "falls as the system grows, which is why this stage is not the "
                    "longest in the trace."
                ),
                standard=(
                    "The reason this architecture exists. The lost node's data "
                    "was not stored on one partner device — it was in "
                    "fragments spread across all five survivors. So the "
                    "rebuild is many-to-many: each of the five reconstructs a "
                    "fifth of what was lost, reading from the other four, "
                    "simultaneously. Every node is a participant; none is a "
                    "spectator. Run the arithmetic forward and the striking "
                    "property appears — in a hundred-node pool, a hundred "
                    "nodes each rebuild a hundredth, so the recovery is "
                    "roughly twenty times faster than it is here, in a cluster "
                    "twenty times smaller. Rebuild time falls as the system "
                    "grows. That is the reverse of how storage normally ages, "
                    "and it is why this stage is not the longest one in the "
                    "trace: building the pool took six times as long as "
                    "repairing it."
                ),
                technical=(
                    "The architecture's justification. The lost node's data was "
                    "fragmented across all survivors, so rebuild is many-to-many: "
                    "each of five reconstructs a fifth concurrently, reading from "
                    "the other four. Every node participates. Scaled out, an n-node "
                    "pool rebuilds 1/n each, so MTTR falls as n rises — the reverse "
                    "of controller-array behaviour, and why the scatter rather than "
                    "the repair holds max dwell."
                ),
                expert=(
                    "Many-to-many rebuild: each survivor reconstructs 1/n "
                    "concurrently. MTTR inversely proportional to node count — the "
                    "inverse of controller-array scaling. Scatter, not repair, "
                    "holds max dwell."
                ),
            ),
            active_regions=[*SURVIVORS, "clients", "fabric", "mdm", "protection"],
            nodes_online=5,
            rebuild_participants=5,
            iops_thousands=1500,
            protected_percent=89,
            elapsed_seconds=300,
            cycle_cost=3,
        ),
        ClusterState(
            step=7,
            phase="rebalanced",
            label="Full protection restored on a smaller cluster",
            description=L(
                novice=(
                    "Everything has its full protection again, now spread across "
                    "five machines instead of six. Nothing was restored from a "
                    "backup, no spare drive was used up, and nobody was woken in "
                    "the night — the pool simply used capacity it already had. The "
                    "cluster is genuinely smaller now and behaves that way: a "
                    "little less space, a little less speed, and complete "
                    "protection. Replacing the failed machine later is an addition "
                    "rather than a repair, and the pool will spread onto it the "
                    "same way."
                ),
                plain=(
                    "Every chunk has full protection again, redistributed across "
                    "five nodes instead of six. Nothing was restored from backup, "
                    "no spare drive was consumed, and no administrator was paged — "
                    "the pool used capacity it already had. The cluster is "
                    "genuinely smaller and behaves accordingly: slightly less "
                    "capacity, slightly less throughput, complete protection. "
                    "Replacing node 6 later is an addition, not a repair."
                ),
                standard=(
                    "Every chunk has its full protection again, redistributed "
                    "across five nodes instead of six. Nothing was restored "
                    "from a backup, no spare drive was consumed, and no "
                    "administrator was paged — the pool simply used the "
                    "capacity it already had. The cluster is now genuinely "
                    "smaller and behaves accordingly: slightly less capacity, "
                    "slightly less throughput, and complete protection. "
                    "Replacing node 6 later is an addition, not a repair, and "
                    "the pool will rebalance onto it the same way."
                ),
                technical=(
                    "Full protection restored across five nodes. No backup restore, "
                    "no spare consumed, no page raised — redistribution used "
                    "existing capacity. The cluster is smaller and behaves so: "
                    "reduced capacity and throughput, full redundancy. Replacement "
                    "is an addition, not a repair."
                ),
                expert=(
                    "Redundancy restored on n-1 nodes from existing capacity. No "
                    "spare, no restore, no page. Replacement is an add, not a "
                    "repair."
                ),
            ),
            active_regions=[*SURVIVORS, "clients", "fabric"],
            nodes_online=5,
            rebuild_participants=0,
            iops_thousands=1780,
            protected_percent=100,
            elapsed_seconds=420,
        ),
        ClusterState(
            step=8,
            phase="steady",
            label="Steady state — one fewer server, no drama",
            description=L(
                novice=(
                    "Back to ordinary operation. The whole episode cost a little "
                    "speed for a few minutes and required nobody's attention, which "
                    "is an unusual way to describe losing a machine from a storage "
                    "system. The same mechanism handles the pleasant version of the "
                    "story too: to replace ageing hardware, add new machines, let "
                    "the pool spread onto them, then remove the old ones — with "
                    "everything still running and no interruption at all."
                ),
                plain=(
                    "Back to ordinary operation. The episode cost some throughput "
                    "for a few minutes and required nobody's attention, which is an "
                    "unusual description of losing a server from a storage system. "
                    "The same mechanism handles the pleasant version: to refresh "
                    "hardware, add new nodes, let the pool rebalance onto them, "
                    "then remove the old ones — hosts running throughout, without "
                    "so much as a dropped path."
                ),
                standard=(
                    "Back to ordinary operation. The episode cost some "
                    "throughput for a few minutes and required nobody's "
                    "attention, which is an unusual description of losing a "
                    "server from a storage system. The same mechanism handles "
                    "the pleasant version of the story too: to refresh "
                    "hardware, add new nodes, let the pool rebalance onto "
                    "them, then remove the old ones — hosts running "
                    "throughout, without so much as a dropped path. In this "
                    "repo, PowerStore and PowerMax show what it costs to make "
                    "a controller safe enough to sit in the middle of "
                    "everything. This twin is the answer that removes the "
                    "middle."
                ),
                technical=(
                    "Steady state on n-1. The incident cost minutes of throughput "
                    "and no operator attention. The same rebalance machinery drives "
                    "hardware refresh: add, rebalance, drain, remove — hosts up "
                    "throughout, no path events. PowerStore and PowerMax show what "
                    "it costs to make a controller safe enough to sit in the "
                    "middle; this removes the middle."
                ),
                expert=(
                    "Steady on n-1. Same rebalance path drives refresh: add, "
                    "rebalance, drain, remove — no host-visible events. The "
                    "controller twins harden the centre; this deletes it."
                ),
            ),
            active_regions=[*SURVIVORS, "clients", "fabric", "mgmt"],
            nodes_online=5,
            rebuild_participants=0,
            iops_thousands=1800,
            protected_percent=100,
            elapsed_seconds=600,
        ),
    ]
