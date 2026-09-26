"""Pure day-2 engine: adding a fifth node, refused on a version mismatch.

``simulate_node_add()`` is the repo's first day-2 trace. The first-run engine
(``engine.py``) ends with a four-node cluster serving virtual machines; this
trace starts there. A fifth node is racked and discovered, VxRail Manager's
compatibility check finds the node's factory image older than the cluster
supports adding, and the add is refused before the node touches vSAN. The
admin re-images the node to the cluster's version, the retry passes, the host
joins, vSAN claims its drives and rebalances.

Same purity rule as ``engine.py``: no FastAPI, no IO, no timers, no
randomness — the frontend owns the clock. Same ``FirstRunState`` model,
extended only with optional fields the first-run trace leaves unset.

How the real product behaves, and where this trace simplifies (sources in
``SOURCES`` below):

* The VxRail administration guide's "expand a cluster" page states it plainly:
  "All nodes in the cluster must be running the same VxRail software version."
  The Node Addition Matrix (KB 000012298) is where a given pair is looked up —
  the KB itself only says to "check this document to ensure the version of
  VxRail on the node is supported for node addition with the version running
  on the cluster", and the matrix PDF answers 403 to automated fetches, so
  this module sends the reader to it rather than quoting cells from it.
  Whether a supported-but-older node is leveled up during expansion or has to
  be re-imaged first is what the matrix decides; this trace models a pair far
  enough apart that re-imaging is the only route (a 7.0.x factory image
  against an 8.0.x cluster, a whole ESXi major release apart), because that is
  the case that stops people.
* The check runs inside the Add VxRail Hosts wizard in vCenter. KB 000193250
  is cited for the precheck's name and place in the wizard, not for this
  failure: the causes it documents are different faults (a missing VMK0, a
  stale Radar tool, an ADC version, an interrupted upgrade). The wizard
  configures nothing until the admin clicks Finish, so any refusal inside it
  precedes every change. A refused node has been discovered and nothing else:
  no management IP from the cluster's pool, no membership of the vSphere
  cluster, no vSAN disk claim.
* Re-imaging uses RASR (Rapid Appliance Self Recovery) — "a factory reset
  and/or a complete upgrade of a VxRail Node (incl. ESXi, iDRAC, BIOS,
  Firmware...)" — often driven by the Node Image Management tool, with an
  image from Dell Support. One public write-up reports seven nodes re-imaged
  in nearly three hours.
* vSAN's automatic rebalance is a cluster setting that is off unless someone
  turns it on; without it vSAN moves existing data only reactively, when a
  capacity device fills up. The ``rebalance`` step says so, and says this
  cluster has it switched on. No fetchable source pins the reactive
  threshold, so no number is quoted for it.
* The other classic failure is one step earlier: the node never appears.
  Discovery uses the VMware Loudmouth service over IPv6 multicast on the
  internal management VLAN (3939 by default), so a switch port that is
  missing that VLAN or filters the multicast hides the node completely. It is
  covered in the ``found`` step's prose rather than as a second trace.

Version numbers, watts, terabytes, VM counts and timings are illustrative.
"""

from __future__ import annotations

from .engine import FABRIC, NODES
from .leveling import L
from .models import FirstRunState, Scenario, SourceLink

SCENARIO_ID = "node-add-mismatch"

NEW_NODE = "n5"
CLUSTER_VERSION = "8.0.300"
FACTORY_VERSION = "7.0.370"

# Illustrative estate: ~30 TB of raw NVMe per node, 96 running VMs.
TB_PER_NODE = 30
VMS = 96

PHASE_ORDER = [
    "serving", "racked", "found", "check", "refused",
    "reimage", "recheck", "join", "rebalance", "expanded",
]

_KINDS = ["storage", "boot", "mgmt", "memory", "compute", "network", "power"]


def _on(node: str, *kinds: str) -> list[str]:
    return [f"{k}-{node}" for k in kinds]


# What a serving cluster keeps lit on every step: each original node's CPU,
# memory, NVMe, NIC and power supplies, and both switches. The trace's first invariant is that
# this set never goes dark — a node add, failed or not, is not an outage.
SERVING = [
    rid
    for n in NODES
    for rid in _on(n, "compute", "memory", "storage", "network", "power")
] + FABRIC

# VxRail Manager runs as a VM on the elected primary (node 1 in the first-run
# trace). Lit whenever the manager is doing the work.
MANAGER = ["mgmt-n1"]

NEW_NODE_REGIONS = _on(NEW_NODE, *_KINDS)

SOURCES = [
    SourceLink(
        label="Dell community: can a 7.0.370 node join a 7.0.452 cluster? (an admin asking; unanswered)",
        url="https://www.dell.com/community/en/conversations/vxrail/adding-new-node-vxrail-software-70370-to-existing-cluster-higher-node-version-70452/65a525b0f5f55c66d376db2e",
    ),
    SourceLink(
        label="Dell KB 000012298: VxRail Node Addition Matrix",
        url="https://www.dell.com/support/kbdoc/en-uk/000012298/vxrail-vxrail-node-addition-matrix",
    ),
    SourceLink(
        label="Dell VxRail Node Addition Matrix (PDF)",
        url="https://dl.dell.com/content/manual29314685-vxrail-node-addition-matrix.pdf?language=en-us",
    ),
    SourceLink(
        label="VxRail 7.0.x Administration Guide: expand a cluster",
        url="https://www.dell.com/support/manuals/en-us/vxrail-software/vxr_p_vxrail-70x_admin-guide/expand-a-cluster?guid=guid-6f3b67ad-1445-4e6d-af86-7fdcd9a4f3de&lang=en-us",
    ),
    SourceLink(
        label="Dell KB 000193250: Add VxRail Hosts precheck, 'Failed to check Node compatibility'",
        url="https://www.dell.com/support/kbdoc/en-us/000193250/dell-emc-vxrail-add-vxrail-hosts-precheck-failed-with-error-failed-to-check-node-compatibility",
    ),
    SourceLink(
        label="VxRail 8 cluster expansion walkthrough (Victor Wu)",
        url="https://wuchikin.wordpress.com/2023/06/13/vxrail-8-cluster-expansion/",
    ),
    SourceLink(
        label="VxRail Node Image Management tool and RASR (make-it-work.net)",
        url="https://make-it-work.net/2022/01/vxrail-node-image-management-nim-tool/",
    ),
    SourceLink(
        label="VxRail Network Planning Guide: multicast for the internal management network",
        url="https://www.dell.com/support/manuals/en-us/vxrail-appliance-series/vxrail_planning_guide/configure-multicast-for-the-vxrail-internal-management-network?guid=guid-37401a04-6fdf-4b82-8b63-4aefc5395d5d&lang=en-us",
    ),
    SourceLink(
        label="VxRail Network Planning Guide: node discovery and the Ethernet switch",
        url="https://www.dell.com/support/manuals/en-us/vxrail-appliance-series/vxrail_planning_guide/vxrail-node-discovery-and-the-ethernet-switch?guid=guid-41425c8d-482d-4c8a-b7f4-cd1a9c717286&lang=en-us",
    ),
    SourceLink(
        label="Dell community: VxRail Manager unable to discover a new node",
        url="https://www.dell.com/community/VxRail/VxRail-Manager-unable-to-discovery-quot-NEW-quot-node-for/td-p/7160989",
    ),
]

FIRST_RUN = Scenario(
    id="first-run",
    title="First run",
    kind="happy",
    summary=(
        "Four nodes power on together, elect a primary, and fuse their NVMe "
        "into one vSAN datastore."
    ),
    hero="Build progress, 0 to 100%.",
    phases=[
        "off", "power", "esxi", "discovery", "primary", "cluster", "vsan", "online",
    ],
)

NODE_ADD_MISMATCH = Scenario(
    id=SCENARIO_ID,
    title="Node add refused: version mismatch",
    kind="failure",
    summary=L(
        novice=(
            "Months after the first run, a fifth server is added to the running "
            "cluster. It arrives with older software than the cluster runs, so "
            "the management software refuses it before it can touch the shared "
            "storage. The admin reinstalls the server's software at the right "
            "version and tries again, and this time it joins. The four original "
            "servers keep working the whole time."
        ),
        standard=(
            "A day-2 expansion. A fifth node is racked and discovered, the "
            "VxRail Manager compatibility check finds its factory image older "
            "than the cluster can take, and the add is refused before the node "
            "touches vSAN. The admin re-images the node, the retry passes, and "
            "vSAN rebalances across five. The running cluster is untouched "
            "throughout."
        ),
        expert=(
            "Day-2 node add. Factory image outside the Node Addition Matrix, "
            "refused at the wizard's compatibility check, pre-vSAN. RASR "
            "re-image, retry, join, rebalance. Zero impact on the serving "
            "cluster."
        ),
    ),
    hero=(
        "Nodes in vSAN: 4 until the retry succeeds, then 5. Mismatched nodes "
        "in vSAN: 0 on every step."
    ),
    phases=PHASE_ORDER,
    sources=SOURCES,
)

SCENARIOS = [FIRST_RUN, NODE_ADD_MISMATCH]


def simulate_node_add() -> list[FirstRunState]:
    """A fifth node's two attempts to join a running cluster, as pure data."""

    def state(
        step: int,
        phase: str,
        label: str,
        description: str,
        new_node: list[str],
        *,
        manager: bool = False,
        failed: list[str] | None = None,
        watts: int,
        progress: int,
        elapsed: int,
        vsan_nodes: int = len(NODES),
        node_version: str = FACTORY_VERSION,
        cycle_cost: int = 1,
    ) -> FirstRunState:
        return FirstRunState(
            step=step,
            phase=phase,
            label=label,
            description=description,
            # The serving cluster is lit on every step, first in the list.
            active_regions=SERVING + (MANAGER if manager else []) + new_node,
            failed_regions=failed or [],
            power_watts=watts,
            progress_percent=progress,
            elapsed_seconds=elapsed,
            cycle_cost=cycle_cost,
            vsan_nodes=vsan_nodes,
            # Derived, not asserted: a host counted by vSAN while its version
            # differs from the cluster's. Exists to be zero.
            mismatched_nodes_in_vsan=(
                vsan_nodes - len(NODES) if node_version != CLUSTER_VERSION else 0
            ),
            datastore_tb=vsan_nodes * TB_PER_NODE,
            vms_running=VMS,
            cluster_version=CLUSTER_VERSION,
            node_version=node_version,
        )

    return [
        state(
            0,
            "serving",
            "Four nodes serving virtual machines",
            L(
                novice=(
                    "This trace starts where the first-run trace ends, months "
                    "later. Four servers act as one system, running 96 virtual "
                    "machines on one shared pool of storage. All four run the "
                    "same version of the VxRail software, 8.0.300, because the "
                    "cluster is upgraded as a unit. The storage is filling up, "
                    "so a fifth server has been ordered. Every number on this "
                    "page is illustrative."
                ),
                standard=(
                    "Day 2. The four-node cluster from the first-run trace has "
                    "been in production for months: 96 virtual machines on one "
                    "120 TB vSAN datastore, every node on VxRail 8.0.300. Dell's "
                    "administration guide requires all nodes in a cluster to run "
                    "the same VxRail version, and lifecycle upgrades keep it "
                    "that way. Capacity is running short, so a fifth node is on "
                    "order. VM count, terabytes and version numbers here are "
                    "illustrative."
                ),
                expert=(
                    "Day 2: four hosts, one 120 TB vSAN datastore, 96 VMs, all "
                    "at 8.0.300. Single-version cluster is a stated requirement. "
                    "Fifth node on order. Figures illustrative."
                ),
            ),
            [],
            watts=1900,
            progress=0,
            elapsed=0,
        ),
        state(
            1,
            "racked",
            "Fifth node racked, cabled and powered on",
            L(
                novice=(
                    "The new server is bolted into the rack under the other "
                    "four, its network ports are cabled to both switches, and "
                    "it is switched on. It starts up the same way the first "
                    "four did: its small management controller wakes, the "
                    "machine tests itself, and it loads its virtualization "
                    "software from its own pair of boot drives. That software "
                    "was installed at the factory and is version 7.0.370, "
                    "older than the cluster's. Nobody has noticed yet. The new "
                    "server's data drives are untouched."
                ),
                standard=(
                    "The new node is racked below the others, patched into both "
                    "top-of-rack switches, and powered on. It boots like any "
                    "first-run node: iDRAC (the management controller) wakes, "
                    "POST (power-on self-test) runs, and ESXi loads from the "
                    "BOSS boot device. The image on that device was written at "
                    "the factory and is VxRail 7.0.370. The cluster has been "
                    "upgraded since the order was placed and runs 8.0.300. The "
                    "node's NVMe capacity drives are unclaimed."
                ),
                expert=(
                    "Node 5 racked, dual-homed to the ToR pair, booted from "
                    "BOSS on its factory image: 7.0.370 against a cluster at "
                    "8.0.300. Capacity NVMe unclaimed."
                ),
            ),
            _on(NEW_NODE, "power", "mgmt", "compute", "memory", "boot"),
            watts=2250,
            progress=0,
            elapsed=600,
            cycle_cost=2,
        ),
        state(
            2,
            "found",
            "VxRail Manager discovers the new node",
            L(
                novice=(
                    "The new server announces itself on a private network that "
                    "only VxRail servers use, and the management software on "
                    "server 1 hears it and lists it as available. This step has "
                    "its own well-known way of failing, separate from the one "
                    "this trace follows. The announcement is a broadcast-style "
                    "message, and network switches are often set up to block "
                    "those. If the switch ports for the new server are missing "
                    "that private network, or block its announcements, the "
                    "server never shows up in the list at all. Nothing is "
                    "damaged and the cluster carries on. The fix is on the "
                    "switch, or the admin adds the server by hand instead."
                ),
                standard=(
                    "The node advertises itself with the VMware Loudmouth "
                    "service, a zero-configuration discovery protocol that uses "
                    "IPv6 multicast on the internal management VLAN (3939 by "
                    "default). VxRail Manager, running on node 1, hears it and "
                    "lists the host under Add VxRail Hosts in vCenter. This is "
                    "the other classic place a node add stops. If the new "
                    "switch ports do not carry that VLAN, or IPv6 multicast is "
                    "filtered (MLD snooping, the switch feature that prunes "
                    "multicast, enabled with no querier is a common cause), the "
                    "node never appears. Nothing fails loudly and the cluster "
                    "is unaffected. The recovery is a switch change, or manual "
                    "discovery, which does not need multicast."
                ),
                expert=(
                    "Loudmouth advertisement over IPv6 multicast on the "
                    "internal management VLAN (default 3939); VxRail Manager "
                    "lists the host. The other classic stop: VLAN absent on the "
                    "new ports, or MLD snooping without a querier, so the node "
                    "is never discovered. Silent, harmless to the cluster. Fix "
                    "the switch or use manual discovery."
                ),
            ),
            _on(NEW_NODE, "network", "mgmt"),
            manager=True,
            watts=2300,
            progress=0,
            elapsed=720,
        ),
        state(
            3,
            "check",
            "Add VxRail Hosts: the compatibility check runs",
            L(
                novice=(
                    "The admin picks the new server in the management console "
                    "and clicks Add. Before asking for any names or addresses, "
                    "the management software compares the software version on "
                    "the new server with the version the cluster runs. Dell "
                    "publishes a table of which combinations are allowed. This "
                    "check reads the new server's version and nothing else. It "
                    "does not change anything on either side."
                ),
                standard=(
                    "The admin selects the discovered host and starts the Add "
                    "VxRail Hosts wizard. Before it configures anything, the "
                    "wizard runs a node compatibility precheck: VxRail Manager "
                    "reads the node's VxRail version and "
                    "compares it with the cluster's, against the rules Dell "
                    "publishes as the Node Addition Matrix. The check is "
                    "read-only, and the wizard applies nothing until Finish. "
                    "The node has no cluster IP address, is not in "
                    "the vSphere cluster, and its drives are still unclaimed."
                ),
                expert=(
                    "Add VxRail Hosts wizard, compatibility precheck: node "
                    "version against cluster version per the Node Addition "
                    "Matrix. Read-only; no addressing, no cluster membership, "
                    "no disk claim."
                ),
            ),
            _on(NEW_NODE, "boot", "network"),
            manager=True,
            watts=2300,
            progress=10,
            elapsed=900,
        ),
        state(
            4,
            "refused",
            "Refused: node 7.0.370, cluster 8.0.300",
            L(
                novice=(
                    "The check fails. The console marks the new server as "
                    "incompatible and will not continue. This is the system "
                    "protecting itself. Servers in one cluster share storage "
                    "and pass running virtual machines between each other, and "
                    "that only works safely when they all run the same "
                    "software. So the refusal comes before the new server gets "
                    "anywhere near the shared storage. Count what has changed "
                    "on the running cluster: nothing. Four servers in the "
                    "storage pool, 96 virtual machines, 120 TB. Dell publishes a "
                    "table of which version pairs may be added at all, and "
                    "which are close enough to be brought up to the cluster's "
                    "version during the add instead of being reinstalled. This "
                    "trace assumes the new server is too far behind for that."
                ),
                standard=(
                    "The wizard reports the host as incompatible and stops. "
                    "What protects the data is where the check sits: ahead of "
                    "every step that would change the cluster. The refused node "
                    "has been discovered and nothing more, so there is nothing "
                    "to roll back. vSAN still has four hosts, the datastore is "
                    "still 120 TB, and the 96 VMs never noticed. One "
                    "qualification: whether a given pair may be added at all, "
                    "and whether a close-enough node is leveled up during "
                    "expansion rather than re-imaged, is what the Node Addition "
                    "Matrix (Dell KB 000012298) decides. This trace models a "
                    "pair far enough apart that re-imaging is the only route: a "
                    "7.0.x image against an 8.0.x cluster, a whole ESXi major "
                    "release apart. The version pair is illustrative, so check "
                    "the matrix for a real one."
                ),
                expert=(
                    "Precheck fails: host incompatible, wizard blocked. The "
                    "gate precedes every mutating step, so there is no "
                    "rollback. vSAN membership 4, 120 TB, 96 VMs unchanged. "
                    "Level-up-during-expansion versus re-image is the Node "
                    "Addition Matrix's call (KB 000012298); this pair, 7.0.x "
                    "into 8.0.x, is assumed re-image-only. Illustrative "
                    "versions."
                ),
            ),
            [],
            manager=True,
            failed=NEW_NODE_REGIONS,
            watts=2300,
            progress=0,
            elapsed=960,
        ),
        state(
            5,
            "reimage",
            "The admin re-images the node to 8.0.300",
            L(
                novice=(
                    "The fix is to reinstall the new server's software at the "
                    "cluster's version. VxRail servers carry a built-in "
                    "factory-reset tool for this. The admin gets the matching "
                    "software image from Dell Support, starts the reset, and "
                    "waits while the server rewrites its boot drives and brings "
                    "its built-in firmware up to the matching level. This is "
                    "the longest step in the trace, an hour or more, and most "
                    "of the delay in real life is getting the image. The "
                    "cluster is not involved and keeps serving."
                ),
                standard=(
                    "Recovery is to level-set the node. The admin obtains the "
                    "8.0.300 image from Dell Support and runs RASR (Rapid "
                    "Appliance Self Recovery, the node's factory-reset "
                    "mechanism), often through the Node Image Management "
                    "tool. RASR rewrites ESXi on the BOSS device and brings "
                    "BIOS, iDRAC and device firmware to the levels that VxRail "
                    "version expects. It is the longest stage here: one public "
                    "write-up reports nearly three hours for seven nodes in "
                    "parallel, and this trace allows roughly an hour and a half "
                    "for one. All of it happens on node 5 alone."
                ),
                expert=(
                    "Level-set via RASR, often driven by NIM, with the "
                    "8.0.300 image from Dell Support: ESXi on BOSS rewritten, "
                    "BIOS, iDRAC and firmware aligned. Max dwell. Node-local; "
                    "the cluster is not a participant."
                ),
            ),
            _on(NEW_NODE, "boot", "mgmt", "compute", "memory", "power"),
            watts=2300,
            progress=0,
            elapsed=1080,
            cycle_cost=5,
        ),
        state(
            6,
            "recheck",
            "Rediscovered, and the check passes",
            L(
                novice=(
                    "The reset server starts up, announces itself again, and "
                    "reappears in the list. The admin clicks Add a second time. "
                    "The same check runs, and now both sides read 8.0.300, so "
                    "the wizard moves on and asks for the new server's name, "
                    "addresses and passwords."
                ),
                standard=(
                    "The re-imaged node boots, advertises itself again, and is "
                    "rediscovered. The admin restarts the wizard. The same "
                    "compatibility check now reads 8.0.300 on both sides and "
                    "passes, and the wizard continues to what it would have "
                    "asked the first time: vCenter credentials, NIC (network "
                    "adapter) layout, hostname, and management, vSAN and "
                    "vMotion IP addresses for the new host."
                ),
                expert=(
                    "Node rediscovered at 8.0.300; precheck passes; wizard "
                    "proceeds to credentials, NIC layout, hostname, and "
                    "management, vSAN and vMotion addressing."
                ),
            ),
            _on(NEW_NODE, "boot", "network", "mgmt"),
            manager=True,
            watts=2300,
            progress=15,
            elapsed=6480,
            node_version=CLUSTER_VERSION,
        ),
        state(
            7,
            "join",
            "Validated and added to the vSphere cluster",
            L(
                novice=(
                    "The management software checks the admin's entries, which "
                    "takes a few minutes, and then configures the new server "
                    "and adds it to the cluster as a fifth host. It can now run "
                    "virtual machines. Its drives are not part of the shared "
                    "storage yet, so the pool is still four servers and 120 TB."
                ),
                standard=(
                    "The wizard's Validate step runs for a few minutes, then "
                    "VxRail Manager configures the host: addresses, virtual "
                    "switch uplinks, and membership of the vSphere cluster. The "
                    "wizard offers to leave the new host in maintenance mode so "
                    "the admin can inspect it before it takes work. Compute has "
                    "joined. Storage has not: vSAN still counts four hosts and "
                    "120 TB."
                ),
                expert=(
                    "Validate (minutes), then host configuration: addressing, "
                    "VDS uplinks, vSphere cluster membership, optional "
                    "maintenance mode. vSAN membership still 4."
                ),
            ),
            _on(NEW_NODE, "compute", "memory", "network", "mgmt"),
            manager=True,
            watts=2330,
            progress=50,
            elapsed=6780,
            node_version=CLUSTER_VERSION,
            cycle_cost=2,
        ),
        state(
            8,
            "join",
            "vSAN claims the fifth node's NVMe",
            L(
                novice=(
                    "Now the new server's data drives are added to the shared "
                    "storage pool. This is the first moment in the whole trace "
                    "that the storage changes, and it only happens after the "
                    "version check has passed. The pool grows from four servers "
                    "to five and from 120 TB to 150 TB."
                ),
                standard=(
                    "vSAN claims the new host's NVMe drives and the datastore "
                    "grows from 120 TB to 150 TB. This is the first step in the "
                    "trace that changes the datastore, and it sits behind the "
                    "check that passed two steps ago. vSAN membership goes from "
                    "four to five, and every member is on 8.0.300."
                ),
                expert=(
                    "vSAN disk claim on host 5: membership 4 to 5, raw 120 to "
                    "150 TB. First datastore mutation in the trace, gated by "
                    "the passed precheck. Zero mixed-version members."
                ),
            ),
            _on(NEW_NODE, "storage", "compute", "network"),
            manager=True,
            watts=2360,
            progress=75,
            elapsed=7380,
            vsan_nodes=5,
            node_version=CLUSTER_VERSION,
        ),
        state(
            9,
            "rebalance",
            "vSAN rebalances across five nodes",
            L(
                novice=(
                    "The new drives start empty while the old ones are nearly "
                    "full. This cluster has the storage software's automatic "
                    "rebalance setting switched on, so it moves some existing "
                    "data onto the new server in the background until all five "
                    "carry a similar share. That setting is off unless an "
                    "admin enables it. With it off, existing data moves only "
                    "when a drive fills up, and in the meantime new virtual "
                    "machines simply land on the emptier server. The move runs over the network at a "
                    "limited pace so the virtual machines are not slowed much. "
                    "It can take hours on a full cluster. Nothing is switched "
                    "off for it."
                ),
                standard=(
                    "The new drives are empty and the old ones are not. vSAN's "
                    "automatic rebalance is off unless it is switched on, and "
                    "without it existing data moves only when a capacity "
                    "device fills up (reactive rebalance). This cluster has automatic "
                    "rebalance enabled, so vSAN moves existing components onto "
                    "host 5 until the five hosts carry a similar share. The "
                    "resync crosses the "
                    "top-of-rack fabric as background traffic, throttled so VM "
                    "latency stays acceptable, and on a full cluster it runs "
                    "for hours. It is a background task on a serving cluster: "
                    "all 96 VMs stay up."
                ),
                expert=(
                    "Automatic rebalance (off unless enabled; on here, else "
                    "reactive only, once a device fills): components resync onto "
                    "host 5 over the ToR fabric, throttled, background. Hours on a full "
                    "datastore. No service interruption."
                ),
            ),
            _on(NEW_NODE, "storage", "network", "compute"),
            watts=2420,
            progress=90,
            elapsed=7680,
            vsan_nodes=5,
            node_version=CLUSTER_VERSION,
            cycle_cost=4,
        ),
        state(
            10,
            "expanded",
            "Five nodes, one larger datastore",
            L(
                novice=(
                    "The cluster is now five servers and 150 TB, all on the "
                    "same software version, still running the same 96 virtual "
                    "machines. The first attempt cost an afternoon and nothing "
                    "else. The lesson for next time: before the new server "
                    "arrives, compare its factory version with the cluster's "
                    "and have the matching image ready."
                ),
                standard=(
                    "Five hosts, one 150 TB datastore, every node on 8.0.300, "
                    "96 VMs that ran throughout. The refused attempt cost time "
                    "and nothing else. The practical lesson is to check the "
                    "Node Addition Matrix when the node ships: clusters get "
                    "upgraded between the order and the delivery, and factory "
                    "images do not."
                ),
                expert=(
                    "Five hosts, 150 TB, uniform 8.0.300, 96 VMs uninterrupted. "
                    "Cost of the refusal: elapsed time only. Check the matrix "
                    "at ship time."
                ),
            ),
            NEW_NODE_REGIONS + _on("n1", "boot")
            + [
                rid
                for n in NODES[1:]
                for rid in _on(n, "boot", "mgmt")
            ],
            manager=True,
            watts=2375,
            progress=100,
            elapsed=11280,
            vsan_nodes=5,
            node_version=CLUSTER_VERSION,
        ),
    ]

