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
            description=(
                "Six ordinary servers, each with local NVMe drives that "
                "belong to it alone. At this moment there is no shared "
                "storage here at all — just six machines with disks in "
                "them, which is exactly what they would be in any rack. "
                "Everything that follows is software deciding to treat "
                "those separate drives as one pool, with no additional "
                "hardware and no storage-area network involved."
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
            description=(
                "The servers find each other over ordinary IP and form a "
                "cluster, electing a metadata manager to hold the map of "
                "what will live where. Note the word: manager, not "
                "controller. It will decide placement and referee "
                "failures, and it will never have a byte of client data "
                "pass through it. That distinction is the architecture in "
                "miniature, and it is why the block is drawn small and off "
                "to one side in the map."
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
            description=(
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
            description=(
                "Volumes are created and presented to the consuming "
                "servers. Each client receives the chunk map, which is "
                "what lets it address nodes directly rather than sending "
                "requests somewhere to be forwarded. From the "
                "application's point of view it has just been given an "
                "ordinary block device; from the pool's point of view it "
                "has just acquired a peer that knows where everything is."
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
            description=(
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
            description=(
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
            description=(
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
            description=(
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
            description=(
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
            active_regions=[*SURVIVORS, "clients", "fabric", "mgmt"],
            nodes_online=5,
            rebuild_participants=0,
            iops_thousands=1800,
            protected_percent=100,
            elapsed_seconds=600,
        ),
    ]
