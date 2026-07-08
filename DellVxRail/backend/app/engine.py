"""Pure cluster first-run engine for VxRail.

``simulate()`` returns the deterministic trace of what happens across a fresh
VxRail cluster from the moment the nodes are powered on until they serve
virtual machines. Same purity rule as every other twin in this repo: no
FastAPI, no IO, no timers — the frontend owns the playback clock, and each
``FirstRunState`` is plain data the renderer consumes. ``cycle_cost`` marks
the long stages (ESXi boot, the VxRail Manager cluster build) so the UI
dwells on them.

The storytelling beat that makes HCI different from a single box: nothing
here is one machine booting. Several complete PowerEdge nodes come up *in
lockstep*, discover each other over a private network, and then one of them
— the node with the lowest serial number — wins an election and powers up
the VxRail Manager VM (the "blue house" the first-run UI draws on it). That
node drives the rest: it validates the configuration, builds the vSphere
cluster, and fuses every node's local NVMe drives into a single shared vSAN
datastore. Timing and wattage are illustrative but plausible for a small
four-node all-NVMe cluster; favor a correct mental model over measured
numbers (project scope guardrail).
"""

from __future__ import annotations

from .models import FirstRunState

# A minimum-viable cluster in this twin: four nodes brought up together.
NODES = ["n1", "n2", "n3", "n4"]
FABRIC = ["tor-a", "tor-b"]


def _all(prefix: str) -> list[str]:
    """Region ids for `prefix` on every node, e.g. compute-n1 … compute-n4."""
    return [f"{prefix}-{n}" for n in NODES]


def simulate() -> list[FirstRunState]:
    """The cluster's journey from powered-on nodes to serving VMs, as pure data."""
    return [
        FirstRunState(
            step=0,
            phase="off",
            label="Nodes racked, AC connected",
            description=(
                "Four VxRail nodes are racked and cabled — each a complete "
                "Dell PowerEdge server — with their NIC ports patched into a "
                "redundant pair of top-of-rack switches. Power is connected "
                "but the nodes are dark. A VxRail cluster is not one machine; "
                "it is these identical building blocks about to fuse into a "
                "single hyperconverged (HCI) system where compute, storage, "
                "and virtualization live together on every node."
            ),
            active_regions=[],
            power_watts=0,
            progress_percent=0,
            elapsed_seconds=0,
        ),
        FirstRunState(
            step=1,
            phase="power",
            label="PSUs energize — iDRAC wakes on every node",
            description=(
                "Each node's power supplies bring their rails up and the "
                "iDRAC — the PowerEdge baseboard management controller — "
                "wakes on standby power, exactly as in the R760 twin. Every "
                "node does this at once and independently; at this moment "
                "they know nothing of each other. Redundancy in HCI starts "
                "from the assumption that any one node may be absent."
            ),
            active_regions=_all("power") + _all("mgmt"),
            power_watts=200,
            progress_percent=0,
            elapsed_seconds=6,
        ),
        FirstRunState(
            step=2,
            phase="power",
            label="Full power and POST — in lockstep",
            description=(
                "The nodes power on fully: CPUs sequence up, DDR5 memory "
                "trains, fans run to full then settle, and each node runs its "
                "power-on self-test. Nothing is coordinated yet — four "
                "servers simply boot in parallel. For a first run you power "
                "on the first three or four nodes together and leave the rest "
                "off until the cluster exists."
            ),
            active_regions=_all("power") + _all("compute") + _all("memory") + _all("mgmt"),
            power_watts=900,
            progress_percent=0,
            elapsed_seconds=30,
            cycle_cost=2,
        ),
        FirstRunState(
            step=3,
            phase="esxi",
            label="ESXi boots from BOSS on every node",
            description=(
                "Each node loads VMware ESXi — the hypervisor — from its BOSS "
                "device (Boot Optimized Storage Solution: a small mirrored "
                "pair of M.2 SSDs used only for the OS, kept off the data "
                "drives). Booting a hypervisor with its factory VxRail image "
                "and integrity checks takes minutes, and it happens on all "
                "nodes at once. Crucially, the node's NVMe capacity drives "
                "are left untouched — they belong to vSAN, not to ESXi."
            ),
            active_regions=_all("boot") + _all("compute") + _all("memory"),
            power_watts=1400,
            progress_percent=5,
            elapsed_seconds=140,
            cycle_cost=3,
        ),
        FirstRunState(
            step=4,
            phase="discovery",
            label="Nodes discover each other on the private VLAN",
            description=(
                "Now the nodes stop being strangers. Over the top-of-rack "
                "switches, each freshly imaged node announces itself on the "
                "private VxRail management VLAN using IPv6 multicast, and "
                "every node hears the others. This is the moment four servers "
                "become candidates to form one cluster — no IP addresses "
                "assigned yet, just mutual discovery over the fabric."
            ),
            active_regions=_all("network") + FABRIC,
            power_watts=1450,
            progress_percent=15,
            elapsed_seconds=200,
            cycle_cost=2,
        ),
        FirstRunState(
            step=5,
            phase="primary",
            label="Primary-node election — VxRail Manager powers up",
            description=(
                "The nodes hold an election, and by default the node with the "
                "lowest serial number wins. The first-run UI marks it with a "
                "blue house icon. Only that node powers up the VxRail Manager "
                "VM — the appliance that will orchestrate the whole build — "
                "so from here the story is deliberately asymmetric: one node "
                "leads, the others wait to be configured. VxRail Manager is "
                "the single pane of glass for the cluster's entire life, from "
                "this first run through every future upgrade."
            ),
            active_regions=["compute-n1", "memory-n1", "mgmt-n1"],
            power_watts=1500,
            progress_percent=25,
            elapsed_seconds=260,
            cycle_cost=2,
        ),
        FirstRunState(
            step=6,
            phase="cluster",
            label="VxRail Manager builds the cluster",
            description=(
                "This is the long stage — Dell quotes roughly 25–40 minutes. "
                "You hand VxRail Manager one JSON configuration (hostnames, "
                "IPs, VLANs, passwords); it validates every input, then drives "
                "the build: it assigns management IPs to all nodes, deploys or "
                "attaches vCenter Server (the VMware management plane), and "
                "joins every node into one vSphere cluster with High "
                "Availability and Distributed Resource Scheduler configured. "
                "A progress bar climbs while the primary orchestrates the "
                "others; the console is otherwise silent."
            ),
            active_regions=_all("compute") + _all("memory") + FABRIC + ["mgmt-n1"],
            power_watts=1700,
            progress_percent=60,
            elapsed_seconds=900,
            cycle_cost=5,
        ),
        FirstRunState(
            step=7,
            phase="vsan",
            label="vSAN datastore assembles across every node's NVMe",
            description=(
                "The defining HCI step: each node's local NVMe drives are "
                "claimed and pooled into a single shared vSAN datastore that "
                "spans the whole cluster. On the current Express Storage "
                "Architecture (ESA) this is a single tier of all-NVMe drives "
                "— every drive serves both cache and capacity, and writes are "
                "mirrored across nodes over the fabric, so a whole node can "
                "fail without data loss. There is no separate storage array; "
                "the servers *are* the storage."
            ),
            active_regions=_all("storage") + _all("compute") + FABRIC,
            power_watts=1850,
            progress_percent=85,
            elapsed_seconds=1500,
            cycle_cost=4,
        ),
        FirstRunState(
            step=8,
            phase="online",
            label="Cluster online — serving virtual machines",
            description=(
                "The cluster is up. vCenter shows one cluster of four hosts "
                "backed by one vSAN datastore, VxRail Manager watches the "
                "hardware and owns lifecycle upgrades, and virtual machines "
                "can be created and moved live between nodes with vMotion. "
                "From here growth is non-disruptive: add a node and its CPU, "
                "memory, and NVMe all join the running cluster at once — the "
                "reason HCI scales 'a node at a time' from two nodes up to "
                "sixty-four."
            ),
            active_regions=(
                _all("storage") + _all("compute") + _all("memory")
                + _all("network") + _all("boot") + _all("mgmt") + _all("power")
                + FABRIC
            ),
            power_watts=1900,
            progress_percent=100,
            elapsed_seconds=1800,
        ),
    ]
