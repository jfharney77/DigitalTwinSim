"""Failure scenario: a running array loses node A.

A second pure trace over the same chassis map as ``engine.simulate()``. It
does not start from AC: step 0 is the power-on trace's last step, an array
already serving I/O from both nodes. Then node A stops, node B carries every
volume alone, node A reboots and rejoins, and the volumes move back.

Same purity rule as the engine (AST-checked in ``tests/test_failover.py``):
no FastAPI, no IO, no timers, no randomness. The frontend owns the clock.

What is sourced and what is not. The behaviour follows two Dell white papers,
"Clustering and High Availability" (H18157) and "Introduction to the
Platform" (H18149), both listed in ``SCENARIO.sources``:

* the NVRAM drives are dual-ported and reachable from both nodes; host data
  is written to them from node DRAM before the host is acknowledged, and
  H18149 says the design lets PowerStore "acknowledge the host without
  mirroring data to the peer node" — the peer is not in the write path, so
  losing it cannot force a write-through fallback;
* the BBU in node A powers drive slots 21 and 23, the BBU in node B powers
  slots 22 and 24, and the NVRAM drives are mirrored as 23 with 24 (and 21
  with 22 on the four-drive models), so both BBUs power each mirrored pair
  "ensuring that there is no single point of failure" (H18149);
* hosts reach a volume over active/optimized paths on its owning node and
  active/non-optimized paths on the other (ALUA for SCSI, ANA for NVMe-oF),
  and I/O arriving on either kind is committed locally with no redirection;
  when every optimized path to a volume goes away, H18157 has the surviving
  node processing that I/O on the non-optimized paths — the paths are not
  relabelled, which is why the optimized share stays at 50% while A is out;
* a lost node's storage resources and OS containers fail over to its peer;
  NAS servers generally move within 30 seconds;
* when the node returns, block resources fail back automatically, NAS servers
  must be failed back by hand, and management services rebalance after five
  minutes;
* a node that cannot boot places itself in service mode.

Every number — seconds, watts, percentages — is illustrative. Dell says
failover time depends on utilization and resource count and publishes no
figure for block. The ``resync`` step is this twin's reading of the public
documents, which do not describe how a returning node rebuilds its in-memory
state; the prose says so.
"""

from __future__ import annotations

from .leveling import L
from .models import FailoverState, ScenarioInfo, SourceLink

SCENARIO_ID = "node-loss-failover"

PHASE_ORDER = [
    "online", "fault", "failover", "degraded",
    "rejoin", "resync", "rebalance", "restored",
]

# Node A's canister, split by what the fault takes away. The PSU, BBU and fan
# pack are left out of both lists on purpose: a node that crashes or reboots
# still has AC, and its BBU still backs its NVRAM slots.
_A_COMPUTE = ["cpu-a", "dimm-a", "board-a"]
_A_PORTS = ["embedded-a", "iomod-a1", "iomod-a2", "mgmt-a"]
NODE_A = _A_COMPUTE + _A_PORTS

_B_COMPUTE = ["cpu-b", "dimm-b", "board-b"]
_B_PORTS = ["embedded-b", "iomod-b1", "iomod-b2", "mgmt-b"]
_B_ALL = _B_COMPUTE + _B_PORTS + ["fans-b"]
_SHARED = ["drive-bay", "nvram"]
# Exactly what the power-on trace's last step lights: the serving array.
_ONLINE = [
    "drive-bay", "nvram", "interconnect",
    "cpu-a", "cpu-b", "dimm-a", "dimm-b", "embedded-a", "embedded-b",
    "iomod-a1", "iomod-a2", "iomod-b1", "iomod-b2",
    "mgmt-a", "mgmt-b", "fans-a", "fans-b",
]

_HA = SourceLink(
    label="Dell PowerStore: Clustering and High Availability (white paper H18157)",
    url=(
        "https://www.delltechnologies.com/asset/en-us/products/storage/"
        "industry-market/h18157-dell-powerstore-clustering-high-availability.pdf"
    ),
)
_PLATFORM = SourceLink(
    label="Dell PowerStore: Introduction to the Platform (white paper H18149)",
    url=(
        "https://www.delltechnologies.com/asset/en-us/products/storage/"
        "industry-market/h18149-dell-powerstore-platform-introduction.pdf"
    ),
)

POWER_ON = ScenarioInfo(
    id="power-on",
    name="Power-on",
    summary="AC arrives and both nodes come up in step until the array serves I/O.",
    hero_metric="elapsed time to serving I/O",
    basis=(
        "Order of events follows Dell's platform white paper. Watts and "
        "timings are illustrative."
    ),
    sources=[_PLATFORM],
)

SCENARIO = ScenarioInfo(
    id=SCENARIO_ID,
    name="Node A fails",
    summary=(
        "A serving array loses one controller node. Node B carries every "
        "volume, node A reboots and rejoins, and the volumes move back."
    ),
    hero_metric="acknowledged writes lost",
    basis=(
        "What fails over, what protects the writes and what fails back by "
        "itself follow Dell's high-availability and platform white papers. "
        "The trace is a model with NVRAM drives (1000 through 9200); the "
        "PowerStore 500 caches writes in node DRAM and is not modeled. "
        "Seconds, watts and percentages are illustrative: Dell publishes no "
        "block failover time, and says it depends on load and resource count."
    ),
    sources=[_HA, _PLATFORM],
)

SCENARIOS = [POWER_ON, SCENARIO]


def simulate_node_loss() -> list[FailoverState]:
    """Node A is lost from a serving array and comes back, as pure data."""
    return [
        FailoverState(
            step=0,
            phase="online",
            label="Serving I/O from both nodes",
            description=L(
                novice=(
                    "This story starts where the power-on story ends. The array is "
                    "running, and its two controller nodes — two computers in one box, "
                    "called node A and node B — are each serving about half of the "
                    "volumes (a volume is a disk the array presents to a server). Each "
                    "node is a little under half busy. That spare room matters in a "
                    "moment. Each server has several routes into the array, and for "
                    "each volume it prefers the routes into the node that owns it. The "
                    "array calls those optimized paths, and right now every volume is "
                    "on one. A write a server sends arrives in the memory of the node "
                    "that took it, but the array does not answer 'done' until the "
                    "write is on a mirrored pair of small, fast NVRAM drives in the "
                    "front bay. Those drives belong to the shared bay, not to either "
                    "node, and both nodes can read them."
                ),
                standard=(
                    "The array is online and active/active: each node owns about half "
                    "of the volumes and runs a little under half busy. Every host has "
                    "paths to both nodes. The paths to a volume's owning node are "
                    "marked active/optimized and carry its I/O; the paths to the other "
                    "node are active/non-optimized and sit ready. A write lands first "
                    "in the DRAM of the node that took it, and is acknowledged only "
                    "once it is on a mirrored pair of dual-ported NVRAM drives in the "
                    "shared front bay, which both nodes can reach."
                ),
                expert=(
                    "Online, active/active, about 45% per node. ALUA/ANA: optimized "
                    "paths on the owning node, non-optimized on the peer. Write ack "
                    "follows commit from node DRAM to the mirrored dual-ported NVRAM "
                    "pair in the shared bay."
                ),
            ),
            active_regions=_ONLINE,
            power_watts=680,
            fan_percent=30,
            elapsed_seconds=0,
            io_percent=100,
            nodes_serving=2,
            node_b_load_percent=45,
            optimized_paths_percent=100,
        ),
        FailoverState(
            step=1,
            phase="fault",
            label="Node A stops responding",
            description=L(
                novice=(
                    "Node A stops. Here the cause is a software fault that makes the "
                    "node restart, but the array reacts the same way to a hardware "
                    "fault, to someone powering the node off, or to a planned reboot "
                    "during an upgrade. Node B notices because the two nodes check on "
                    "each other constantly over an internal link, and node A has gone "
                    "quiet. Servers using node B carry on untouched. Requests that were "
                    "on their way to node A get no answer, so for a few seconds about "
                    "half the traffic waits. The counter 'volumes on optimized paths' "
                    "drops to 50%, because node A's volumes have lost their preferred "
                    "routes. Nothing already answered 'done' is at risk: those writes "
                    "are on the NVRAM drives in the front bay, and node A's failure did "
                    "not touch them."
                ),
                standard=(
                    "Node A stops — here a software fault that forces a reboot; Dell "
                    "lists node reboot, hardware or software fault, service mode and "
                    "power-off as the events that trigger the same response. Node B "
                    "sees the heartbeat over the node interconnect go silent. I/O on "
                    "node B's optimized paths is unaffected; I/O in flight to node A is "
                    "unanswered and the hosts will retry it. Every write node A had "
                    "acknowledged is already on the mirrored NVRAM drives in the shared "
                    "bay, so the node took no acknowledged data with it. The dip shown "
                    "is illustrative."
                ),
                expert=(
                    "Node A down (software fault, reboot). Heartbeat lost on the "
                    "interconnect. B's optimized paths unaffected; A's in-flight I/O "
                    "unanswered, pending host retry. Acknowledged writes are on shared "
                    "mirrored NVRAM, outside the failed node."
                ),
            ),
            active_regions=_SHARED + _B_ALL,
            failed_regions=NODE_A + ["interconnect"],
            power_watts=540,
            fan_percent=35,
            elapsed_seconds=2,
            io_percent=55,
            nodes_serving=1,
            node_b_load_percent=45,
            optimized_paths_percent=50,
            node_a_joined=False,
        ),
        FailoverState(
            step=2,
            phase="failover",
            label="Hosts retry on node B's paths",
            description=L(
                novice=(
                    "Each server runs multipathing software, which keeps several routes "
                    "to the array and knows which are preferred. It sees that the "
                    "routes into node A are dead and resends the waiting requests down "
                    "its routes into node B. Node B does not have to forward them "
                    "anywhere or wait to take anything over first. Both nodes share one "
                    "map of where every block of data lives, so node B can complete a "
                    "request for any volume by itself. Those routes are not the "
                    "preferred ones, which is why 'volumes on optimized paths' stays at "
                    "50% until node A is back. This is why the routes to node B had to "
                    "be cabled and configured before today: a server with routes to "
                    "node A only would now be cut off. How long the resend takes is set "
                    "by the server's own timeout, not by the array, and the figure "
                    "shown here is illustrative."
                ),
                standard=(
                    "Host multipathing software (Dell PowerPath, Linux device-mapper "
                    "multipath, VMware's native multipathing) marks node A's paths dead "
                    "and reissues the outstanding I/O on the active/non-optimized paths "
                    "to node B. PowerStore commits I/O locally on whichever path it "
                    "arrives, with no redirection to the owning node, so there is no "
                    "ownership transfer (a 'trespass' on older Dell EMC arrays) to wait "
                    "for. Dell's guidance is to cable and zone every host to both "
                    "nodes, so each host already holds a path into node B. A host zoned "
                    "or cabled to one node only loses access here. How long the retry "
                    "takes is the host's path timeout, not the array's; the figure "
                    "shown is illustrative."
                ),
                expert=(
                    "Host MPIO fails A's paths and reissues on B's non-optimized paths. "
                    "I/O commits locally on any path, no redirection, no ownership move "
                    "(trespass) to wait for. Hosts must be zoned to both nodes; "
                    "single-node-zoned hosts lose access. Retry time is the host's path "
                    "timeout."
                ),
            ),
            active_regions=_SHARED + _B_ALL,
            failed_regions=NODE_A + ["interconnect"],
            power_watts=560,
            fan_percent=40,
            elapsed_seconds=10,
            io_percent=85,
            nodes_serving=1,
            node_b_load_percent=75,
            optimized_paths_percent=50,
            node_a_joined=False,
            cycle_cost=2,
        ),
        FailoverState(
            step=3,
            phase="failover",
            label="Node B takes over node A's resources",
            description=L(
                novice=(
                    "Node B now formally takes charge of everything node A was "
                    "running: its volumes, its file servers (the parts that "
                    "serve shared folders), and the management software behind "
                    "the web console. Dell says file servers generally move "
                    "within 30 seconds so that connected computers do not give "
                    "up. An administrator who had the console open may see "
                    "'connection lost' for a few minutes, then it comes back, "
                    "now running on node B. The array raises alerts and, if it "
                    "is set up to, reports the fault to Dell by itself."
                ),
                standard=(
                    "Node A's resources — volume ownership and the PowerStoreOS "
                    "containers that ran there — fail over to node B. NAS "
                    "servers move too, which Dell says generally completes "
                    "within 30 seconds to stay inside client timeouts. The "
                    "management services that ran on node A restart on node B, "
                    "after host access, which has priority: PowerStore Manager may show a lost connection for "
                    "several minutes and then returns on the same cluster "
                    "address. The array raises alerts for the node and sends "
                    "call-home if support connectivity is configured. Dell "
                    "publishes no block failover time; it depends on load and on "
                    "how many resources move."
                ),
                expert=(
                    "A's storage resources and OS containers fail over to B. NAS "
                    "servers within about 30 s (Dell's figure). Management "
                    "services restart on B; PowerStore Manager drops for "
                    "minutes. Alerts and call-home raised. No published block "
                    "failover time."
                ),
            ),
            active_regions=_SHARED + _B_ALL,
            failed_regions=NODE_A + ["interconnect"],
            power_watts=580,
            fan_percent=45,
            elapsed_seconds=40,
            io_percent=100,
            nodes_serving=1,
            node_b_load_percent=90,
            optimized_paths_percent=50,
            node_a_joined=False,
            cycle_cost=3,
        ),
        FailoverState(
            step=4,
            phase="degraded",
            label="One node serves every volume",
            description=L(
                novice=(
                    "Node B is now doing the work of two, and writes are as safe as "
                    "they were. Each one still lands on the pair of NVRAM drives before "
                    "the array answers, because those drives sit in the shared front "
                    "bay, outside both nodes, and both are still there. Node A was "
                    "never a step in that journey — Dell's platform paper says the "
                    "array answers the server without copying the write to the other "
                    "node — so losing node A does not push the array into the slower "
                    "way of writing that some arrays fall back on when they lose half "
                    "their cache. Servers get the same "
                    "amount of work done as before, but node B is about 90% busy where "
                    "it was 45%, and a node that busy answers each request more slowly. "
                    "This trace does not model that delay. It is the reason to keep "
                    "each node under half busy on a normal day: an array that runs both "
                    "nodes at 80% has nowhere to put the load when one stops. What the "
                    "array has lost is its spare. If node B stopped as well, service "
                    "would stop until a node came back, though the stored data would "
                    "still be intact.\n\n"
                    "If the mains failed now, the batteries would keep the NVRAM drives "
                    "powered while they save their contents to their own built-in "
                    "flash, which is called vaulting. Node A's battery still works: the "
                    "node's software stopped, but its half of the box still has mains "
                    "power. The wiring is Dell's, not this twin's guess: node A's "
                    "battery powers drive slots 21 and 23, node B's powers 22 and 24, "
                    "and the drives are mirrored 23 with 24. Each pair is therefore "
                    "powered by both batteries, which Dell says leaves no single point "
                    "of failure — even a node pulled out for service, taking its "
                    "battery with it, leaves a powered drive holding a full copy of "
                    "every write. "
                    "The entry model, the PowerStore 500, has no NVRAM drives and keeps "
                    "its write cache in node memory, so this story is about the 1000 to "
                    "9200 models."
                ),
                standard=(
                    "Node B serves every volume, and write protection is unchanged. The "
                    "reason is physical: the copy that makes an acknowledgement safe is "
                    "not memory inside a node. A write passes through the taking node's "
                    "DRAM, but it is acknowledged from a mirrored pair of dual-ported "
                    "NVRAM drives in the shared front bay, and Dell's platform paper "
                    "says that design lets the array acknowledge a host without "
                    "mirroring the data to the peer node. The peer was never in the "
                    "write path, so its loss cannot force the fallback to write-through "
                    "that an array caching writes in a peer's memory has to make. Node "
                    "B commits to the same mirrored pair it always did. "
                    "Host I/O is back to its earlier rate, but node B runs near 90% "
                    "where it ran at 45%. Same rate is not same response time: at 90% "
                    "busy a controller is well up the queueing curve, and this trace "
                    "does not model latency. That is the arithmetic behind the sizing "
                    "rule to keep each node under about half load, since an array "
                    "running both nodes hot cannot absorb this. What is gone is "
                    "controller redundancy: a second node failure now is an outage, "
                    "though not a loss of acknowledged data. Percentages are "
                    "illustrative.\n\n"
                    "Vaulting (each NVRAM drive saving its contents to its own flash on "
                    "AC loss) is still covered. Node A's software is down but its "
                    "canister still has AC, so its BBU still works. The wiring is "
                    "documented, not inferred: BBU A powers drive slots 21 and 23, BBU "
                    "B powers 22 and 24, and the NVRAM drives are mirrored as 23 with "
                    "24 (and 21 with 22 on the four-drive models), so both BBUs power "
                    "each mirrored pair — Dell's phrase is that this ensures no single "
                    "point of failure. A canister pulled for service, taking its BBU "
                    "with it, still leaves a powered drive holding a full copy of every "
                    "write. This holds for the models with NVRAM "
                    "drives, the 1000 through 9200; the PowerStore 500 caches writes in "
                    "node DRAM instead, and this trace does not model it."
                ),
                expert=(
                    "B owns all volumes at about 90% (was 45%); same rate, latency up "
                    "the queueing curve and not modelled — hence the "
                    "under-half-per-node sizing rule. Write path unchanged: DRAM to the "
                    "shared mirrored NVRAM pair, then ack. Dell: the design acks "
                    "without mirroring to the peer, so the peer's loss forces no "
                    "write-through fallback. Controller redundancy is what is lost.\n\n"
                    "Vaulting: A's canister still has AC, so BBU A is live. Dell wires "
                    "BBU A to slots 21/23 and BBU B to 22/24, mirroring 23 with 24, so "
                    "both BBUs power each pair — no single point of failure. NVRAM "
                    "models only, not the 500."
                ),
            ),
            active_regions=_SHARED + _B_ALL + ["bbu-a", "bbu-b"],
            failed_regions=NODE_A + ["interconnect"],
            power_watts=600,
            fan_percent=50,
            elapsed_seconds=90,
            io_percent=100,
            nodes_serving=1,
            node_b_load_percent=90,
            optimized_paths_percent=50,
            node_a_joined=False,
            cycle_cost=3,
        ),
        FailoverState(
            step=5,
            phase="rejoin",
            label="Node A reboots",
            description=L(
                novice=(
                    "Node A restarts by itself, going through the same start-up "
                    "as in the power-on story: its firmware checks the hardware, "
                    "then PowerStoreOS — the array's operating system — loads. "
                    "This is the longest wait in the whole sequence, several "
                    "minutes, and node B carries everything throughout. Nobody "
                    "has to do anything. If node A could not start, because a "
                    "part had truly failed, it would put itself into service "
                    "mode: a safe state where it stays out of the way and waits "
                    "for an engineer. Node B would keep serving until the part "
                    "or the whole node was swapped, which can be done with the "
                    "array running."
                ),
                standard=(
                    "Node A reboots unattended: firmware, then PowerStoreOS and "
                    "its containers, the same sequence as the power-on trace and "
                    "again the longest stage. Node B serves throughout. The "
                    "recovery action for the administrator is usually to watch "
                    "the alerts and wait. If the node cannot boot because of a "
                    "hardware or software problem, it places itself in service "
                    "mode and stays out of the pair; clearing that is a Dell "
                    "support task done with a service script, not something "
                    "PowerStore Manager, the REST API or the CLI offers. A node "
                    "with failed hardware is replaced with the array online."
                ),
                expert=(
                    "A reboots unattended: firmware, PowerStoreOS, containers. "
                    "Longest stage. Boot failure drops the node into service "
                    "mode; exit is by service script with Dell support. Node "
                    "replacement is an online procedure."
                ),
            ),
            active_regions=_SHARED + _B_ALL + _A_COMPUTE + ["fans-a"],
            failed_regions=_A_PORTS + ["interconnect"],
            power_watts=660,
            fan_percent=55,
            elapsed_seconds=330,
            io_percent=100,
            nodes_serving=1,
            node_b_load_percent=90,
            optimized_paths_percent=50,
            node_a_joined=False,
            cycle_cost=6,
        ),
        FailoverState(
            step=6,
            phase="rejoin",
            label="Node A rejoins the pair",
            description=L(
                novice=(
                    "Node A is running again and the two nodes are back in "
                    "contact over their internal link. Node B accepts node A "
                    "back as its partner. Node A's network ports come up, so "
                    "servers see their routes to it return. But node A owns no "
                    "volumes yet and node B keeps serving them all. The array "
                    "will not hand work to a node that has only just come back "
                    "and has not yet caught up."
                ),
                standard=(
                    "PowerStoreOS is up on node A, the heartbeat returns over "
                    "the interconnect, and node A is a member of the pair again. "
                    "Its front-end ports come online, so hosts see their paths "
                    "to node A return — as active/non-optimized, because node B "
                    "still owns every volume. Rejoining and taking back work are "
                    "separate events, in that order."
                ),
                expert=(
                    "A up; heartbeat restored; pair membership re-formed. A's "
                    "ports return as non-optimized paths. B still owns all "
                    "volumes. Rejoin precedes failback."
                ),
            ),
            active_regions=(
                _SHARED + ["interconnect"] + _B_ALL + _A_COMPUTE + _A_PORTS
                + ["fans-a"]
            ),
            power_watts=690,
            fan_percent=45,
            elapsed_seconds=360,
            io_percent=100,
            nodes_serving=1,
            node_b_load_percent=90,
            optimized_paths_percent=50,
        ),
        FailoverState(
            step=7,
            phase="resync",
            label="Node A catches up",
            description=L(
                novice=(
                    "Node A was away for several minutes, and thousands of "
                    "writes happened without it. It has to catch up before it "
                    "can be trusted with volumes again. The writes themselves "
                    "need no copying: they went to the NVRAM drives and the main "
                    "drives in the front bay, which node A can read directly. "
                    "What node A lost is what it held in its own memory — its "
                    "working copy of the map of where data lives, and its cache "
                    "of recently used data. It rebuilds that from the shared "
                    "drives and from node B over the internal link. Dell's "
                    "public papers do not spell this step out, so treat this "
                    "account as the twin's own reading."
                ),
                standard=(
                    "Node A rebuilds the state a reboot erased. No acknowledged "
                    "write has to be copied back to it: the write log lives on "
                    "the shared NVRAM drives and the data on the shared SSDs, "
                    "and node A reads both directly. What it lacks is in-memory "
                    "state — mapping metadata and cache contents held in DRAM — "
                    "which it brings level with node B over the interconnect. "
                    "Dell's public white papers do not describe this step; it is "
                    "this twin's reading of the architecture, and the duration "
                    "is illustrative."
                ),
                expert=(
                    "A rebuilds DRAM-resident state (mapping metadata, cache) "
                    "against the shared NVRAM log, the SSDs and B over the "
                    "interconnect. No acknowledged write needs copying back. Not "
                    "described in Dell's public papers; the twin's reading."
                ),
            ),
            active_regions=(
                _SHARED + ["interconnect", "dimm-a", "dimm-b", "cpu-a", "cpu-b",
                           "board-a", "board-b"]
                + _B_PORTS + ["fans-a", "fans-b"]
            ),
            power_watts=700,
            fan_percent=45,
            elapsed_seconds=420,
            io_percent=100,
            nodes_serving=1,
            node_b_load_percent=90,
            optimized_paths_percent=50,
            cycle_cost=3,
        ),
        FailoverState(
            step=8,
            phase="rebalance",
            label="Block volumes fail back to node A",
            description=L(
                novice=(
                    "With node A caught up, the array gives it back the volumes "
                    "it used to own. For block volumes — the kind servers use as "
                    "disks — this happens by itself. The servers' multipathing "
                    "software sees the preferred routes to node A return and "
                    "moves traffic back, and node B drops to a normal load. Two "
                    "things do not return by themselves. File servers stay on "
                    "node B until an administrator moves them back in the "
                    "console. And the management software waits five minutes "
                    "before it spreads out again, which can disconnect the "
                    "console for up to three minutes."
                ),
                standard=(
                    "Block storage resources fail back to their owning node "
                    "automatically. Node A's paths for those volumes return to "
                    "active/optimized, host multipathing moves the I/O back, and "
                    "node B's load falls to where it started. Two things do not "
                    "follow by themselves. NAS servers must be failed back by an "
                    "administrator in PowerStore Manager. Management services "
                    "rebalance five minutes after the node recovers, and "
                    "PowerStore Manager may drop for up to three minutes while "
                    "they do; the primary-node role can stay with node B until "
                    "the next reboot or failover. Those rules are Dell's; the "
                    "timings shown are illustrative."
                ),
                expert=(
                    "Block resources fail back automatically; A's paths return "
                    "to optimized and MPIO follows. NAS servers need manual "
                    "failback. Management services rebalance after five minutes "
                    "(console drop up to three). Primary role may stay on B."
                ),
            ),
            active_regions=_ONLINE,
            power_watts=690,
            fan_percent=35,
            elapsed_seconds=720,
            io_percent=100,
            nodes_serving=2,
            node_b_load_percent=55,
            optimized_paths_percent=90,
            cycle_cost=2,
        ),
        FailoverState(
            step=9,
            phase="restored",
            label="Active/active again",
            description=L(
                novice=(
                    "Both nodes are serving again, each about as busy as before, "
                    "and the alerts clear. Look at what the servers went "
                    "through: a few seconds of waiting on about half their "
                    "requests, then normal service for the rest of the thirteen "
                    "minutes. The count of acknowledged writes lost stayed at "
                    "zero on every step. That was decided long before the fault, "
                    "by where the write cache was put: in the shared bay, "
                    "outside both nodes, mirrored. One job is left, and it is "
                    "the administrator's: the file servers are still running on "
                    "node B and stay there until someone moves them back. All "
                    "times here are illustrative, not measured."
                ),
                standard=(
                    "Both nodes serve their own volumes on optimized paths, node "
                    "B is back to about 45%, and the node alerts clear. Hosts "
                    "saw a pause of seconds on about half their I/O and then full "
                    "service; acknowledged writes lost held at zero on every "
                    "step. That number was decided by placement, not by "
                    "recovery logic: the write cache sits in the shared bay, "
                    "mirrored, outside the failure domain of either node. "
                    "Block is where it started; the NAS servers are not, and "
                    "will not be until an administrator fails them back. "
                    "Timings are illustrative."
                ),
                expert=(
                    "Active/active restored, optimized paths on both nodes, "
                    "about 45% each, alerts cleared. Zero acknowledged writes "
                    "lost — a consequence of cache placement outside either "
                    "node's failure domain. NAS servers still await a manual "
                    "failback."
                ),
            ),
            active_regions=_ONLINE,
            power_watts=680,
            fan_percent=30,
            elapsed_seconds=780,
            io_percent=100,
            nodes_serving=2,
            node_b_load_percent=45,
            optimized_paths_percent=100,
        ),
    ]
