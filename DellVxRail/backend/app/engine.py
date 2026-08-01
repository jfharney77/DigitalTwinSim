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

from .leveling import L
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
            description=L(
                novice=(
                    "Four servers are installed in a rack and cabled, with their "
                    "network ports connected to a redundant pair of switches at the "
                    "top. Power is plugged in but nothing is switched on. The thing "
                    "to understand before anything else: this is not one machine. "
                    "It is four identical machines that are about to merge into a "
                    "single system where the computing, the storage, and the "
                    "software that runs virtual machines all live together on the "
                    "same boxes."
                ),
                plain=(
                    "Four VxRail nodes are racked and cabled — each a complete Dell "
                    "PowerEdge server — with their network ports patched into a "
                    "redundant pair of top-of-rack switches. Power is connected but "
                    "the nodes are dark. A VxRail cluster is not one machine: it is "
                    "these identical building blocks about to fuse into a single "
                    "hyperconverged system, where compute, storage, and "
                    "virtualization share the same hardware."
                ),
                standard=(
                    "Four VxRail nodes are racked and cabled — each a complete "
                    "Dell PowerEdge server — with their NIC ports patched into a "
                    "redundant pair of top-of-rack switches. Power is connected "
                    "but the nodes are dark. A VxRail cluster is not one machine; "
                    "it is these identical building blocks about to fuse into a "
                    "single hyperconverged (HCI) system where compute, storage, "
                    "and virtualization live together on every node."
                ),
                technical=(
                    "Four PowerEdge-based nodes racked, cabled into a redundant ToR "
                    "pair, AC connected, dark. The subject is a cluster, not a "
                    "chassis — identical building blocks about to fuse into one HCI "
                    "system with compute, storage, and virtualization co-resident."
                ),
                expert=(
                    "Four identical nodes, redundant ToR, AC connected, dark. "
                    "Subject is the cluster; compute, storage, and virtualization "
                    "co-resident by design."
                ),
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
            description=L(
                novice=(
                    "Each server's power supplies come up, and a small always-on "
                    "management controller wakes on standby power — the same "
                    "component the rack-server twin in this repo covers in detail. "
                    "Every server does this at the same time and completely "
                    "independently; at this moment none of them knows the others "
                    "exist. Redundancy in this kind of system starts from the "
                    "assumption that any one of them might be missing."
                ),
                plain=(
                    "Each node's power supplies bring their rails up and the iDRAC "
                    "— the PowerEdge management controller — wakes on standby "
                    "power, exactly as in the R760 twin. Every node does this at "
                    "once and independently; at this moment they know nothing of "
                    "each other. Redundancy here starts from the assumption that "
                    "any one node may be absent."
                ),
                standard=(
                    "Each node's power supplies bring their rails up and the "
                    "iDRAC — the PowerEdge baseboard management controller — "
                    "wakes on standby power, exactly as in the R760 twin. Every "
                    "node does this at once and independently; at this moment "
                    "they know nothing of each other. Redundancy in HCI starts "
                    "from the assumption that any one node may be absent."
                ),
                technical=(
                    "PSU rails up; iDRAC wakes on standby on every node, as "
                    "detailed in the R760 twin. Independent and concurrent — no "
                    "inter-node state exists yet. The redundancy model assumes any "
                    "single node may be absent from the outset."
                ),
                expert=(
                    "PSU rails up, iDRAC on standby per node. Concurrent, "
                    "independent, no shared state. Redundancy assumes any node may "
                    "be absent."
                ),
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
            description=L(
                novice=(
                    "The servers power on fully: processors sequence up, memory is "
                    "tested and tuned, fans spin to full and then settle, and each "
                    "machine runs its own start-up self-test. Nothing is "
                    "coordinated yet — four servers are simply starting in "
                    "parallel. For a first installation you power on the first "
                    "three or four together and leave any others switched off until "
                    "the cluster actually exists."
                ),
                plain=(
                    "The nodes power on fully: CPUs sequence up, DDR5 memory "
                    "trains, fans run to full then settle, and each runs its "
                    "power-on self-test. Nothing is coordinated yet — four servers "
                    "booting in parallel. For a first run you power on the first "
                    "three or four together and leave the rest off until the "
                    "cluster exists."
                ),
                standard=(
                    "The nodes power on fully: CPUs sequence up, DDR5 memory "
                    "trains, fans run to full then settle, and each node runs its "
                    "power-on self-test. Nothing is coordinated yet — four "
                    "servers simply boot in parallel. For a first run you power "
                    "on the first three or four nodes together and leave the rest "
                    "off until the cluster exists."
                ),
                technical=(
                    "Full power: CPU sequencing, DDR5 training, fan ramp and "
                    "settle, POST per node. Uncoordinated parallel boot. First-run "
                    "practice is to power the initial three or four and hold the "
                    "remainder until the cluster exists."
                ),
                expert=(
                    "Full power, DDR5 training, POST — parallel and uncoordinated. "
                    "First run powers the initial three or four only."
                ),
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
            description=L(
                novice=(
                    "Each server loads its virtualization software from a small "
                    "dedicated pair of mirrored drives kept separate from the ones "
                    "that hold data. Loading that software with its factory image "
                    "and integrity checks takes minutes, and it happens on all the "
                    "servers at once. Importantly, the fast data drives are left "
                    "completely untouched — they are not part of anything yet."
                ),
                plain=(
                    "Each node loads VMware ESXi — the hypervisor — from its BOSS "
                    "device, a small mirrored pair of M.2 SSDs used only for the "
                    "operating system and kept off the data drives. Booting a "
                    "hypervisor with its factory image and integrity checks takes "
                    "minutes, and happens on all nodes at once. The NVMe capacity "
                    "drives are left untouched — they belong to nothing yet."
                ),
                standard=(
                    "Each node loads VMware ESXi — the hypervisor — from its BOSS "
                    "device (Boot Optimized Storage Solution: a small mirrored "
                    "pair of M.2 SSDs used only for the OS, kept off the data "
                    "drives). Booting a hypervisor with its factory VxRail image "
                    "and integrity checks takes minutes, and it happens on all "
                    "nodes at once. Crucially, the node's NVMe capacity drives "
                    "are left untouched — they belong to vSAN, not to ESXi."
                ),
                technical=(
                    "ESXi boots from BOSS — a mirrored M.2 pair carrying only the "
                    "hypervisor, deliberately isolated from the capacity tier. "
                    "Factory image plus integrity verification takes minutes, "
                    "concurrent across nodes. NVMe capacity drives remain "
                    "unclaimed."
                ),
                expert=(
                    "ESXi from BOSS (mirrored M.2, OS-only). Concurrent across "
                    "nodes. Capacity NVMe unclaimed."
                ),
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
            description=L(
                novice=(
                    "Now the servers stop being strangers. Through the switches "
                    "above them, each freshly imaged machine announces itself on a "
                    "private management network and every other machine hears it. "
                    "This is the moment four separate servers become candidates to "
                    "form one cluster — no addresses assigned yet, just mutual "
                    "discovery."
                ),
                plain=(
                    "The nodes stop being strangers. Through the switches above "
                    "them, each freshly imaged node announces itself on the private "
                    "VxRail management VLAN by IPv6 multicast, and every other node "
                    "hears it. Four servers have just become candidates to form one "
                    "cluster — no addresses handed out yet, only mutual discovery "
                    "across the fabric."
                ),
                standard=(
                    "Now the nodes stop being strangers. Over the top-of-rack "
                    "switches, each freshly imaged node announces itself on the "
                    "private VxRail management VLAN using IPv6 multicast, and "
                    "every node hears the others. This is the moment four servers "
                    "become candidates to form one cluster — no IP addresses "
                    "assigned yet, just mutual discovery over the fabric."
                ),
                technical=(
                    "Discovery over the ToR pair: each imaged node announces on the "
                    "private management VLAN via IPv6 multicast and hears its "
                    "peers. Candidacy established, no addressing yet — the "
                    "transition from four independent hosts to a prospective "
                    "cluster."
                ),
                expert=(
                    "IPv6 multicast discovery on the private management VLAN. "
                    "Candidacy established, no addressing."
                ),
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
            description=L(
                novice=(
                    "The servers hold an election, and by default the one with the "
                    "lowest serial number wins. Only that machine starts up the "
                    "management software that will orchestrate the whole build — so "
                    "from here the story is deliberately lopsided: one leads, the "
                    "others wait to be configured. This is the only step where the "
                    "four are not identical, and it is worth pausing on."
                ),
                plain=(
                    "The nodes hold an election, and by default the node with the "
                    "lowest serial number wins; the first-run interface marks it "
                    "with a blue house icon. Only that node powers up the VxRail "
                    "Manager virtual machine — the appliance that orchestrates the "
                    "whole build — so from here the story is deliberately "
                    "asymmetric: one node leads, the others wait to be configured."
                ),
                standard=(
                    "The nodes hold an election, and by default the node with the "
                    "lowest serial number wins. The first-run UI marks it with a "
                    "blue house icon. Only that node powers up the VxRail Manager "
                    "VM — the appliance that will orchestrate the whole build — "
                    "so from here the story is deliberately asymmetric: one node "
                    "leads, the others wait to be configured. VxRail Manager is "
                    "the single pane of glass for the cluster's entire life, from "
                    "this first run through every future upgrade."
                ),
                technical=(
                    "Primary election, defaulting to lowest serial. Only the "
                    "elected node instantiates the VxRail Manager VM that drives "
                    "the build, so the trace becomes deliberately asymmetric here. "
                    "The engine asserts the active suffix set is exactly {n1} at "
                    "this step — the single break in an otherwise lockstep "
                    "sequence."
                ),
                expert=(
                    "Primary election (lowest serial); only the winner instantiates "
                    "VxRail Manager. Active suffix set exactly {n1} — the sole "
                    "lockstep break, asserted."
                ),
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
            description=L(
                novice=(
                    "The long stage — Dell quotes roughly 25 to 40 minutes. You "
                    "hand the management software one configuration file with "
                    "names, addresses, network identifiers, and passwords; it "
                    "checks every input, then drives the build: it assigns "
                    "addresses to all the servers, sets up the central management "
                    "system, and joins every server into one cluster with automatic "
                    "failover and workload balancing switched on."
                ),
                plain=(
                    "The long stage — Dell quotes roughly 25 to 40 minutes. You "
                    "hand VxRail Manager one JSON configuration file (hostnames, "
                    "IPs, VLANs, passwords); it validates every input, then drives "
                    "the build: assigning management IPs to all nodes, deploying or "
                    "attaching vCenter Server, and joining every node into one "
                    "vSphere cluster with High Availability and Distributed "
                    "Resource Scheduler enabled."
                ),
                standard=(
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
                technical=(
                    "Max-dwell stage, ~25–40 minutes. A single JSON configuration "
                    "is validated, then drives the build: management IP assignment "
                    "across nodes, vCenter deployment or attachment, and cluster "
                    "formation with HA and DRS enabled. Declarative input, "
                    "orchestrated execution."
                ),
                expert=(
                    "Max dwell (~25–40 min): JSON validated, then IP assignment, "
                    "vCenter deploy/attach, cluster formation with HA and DRS."
                ),
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
            description=L(
                novice=(
                    "The defining step. Each server's local fast drives are claimed "
                    "and pooled into a single shared storage area that spans the "
                    "whole cluster. On the current design there is one tier of "
                    "all-flash drives — every drive serves both as fast cache and "
                    "as capacity — and writes are copied across servers over the "
                    "network, so an entire server can fail without losing anything."
                ),
                plain=(
                    "The defining hyperconverged step: each node's local NVMe "
                    "drives are claimed and pooled into a single shared vSAN "
                    "datastore spanning the whole cluster. On the current Express "
                    "Storage Architecture this is one tier of all-NVMe drives — "
                    "every drive serves both cache and capacity — and writes are "
                    "mirrored across nodes over the fabric, so a whole node can "
                    "fail without data loss."
                ),
                standard=(
                    "The defining HCI step: each node's local NVMe drives are "
                    "claimed and pooled into a single shared vSAN datastore that "
                    "spans the whole cluster. On the current Express Storage "
                    "Architecture (ESA) this is a single tier of all-NVMe drives "
                    "— every drive serves both cache and capacity, and writes are "
                    "mirrored across nodes over the fabric, so a whole node can "
                    "fail without data loss. There is no separate storage array; "
                    "the servers *are* the storage."
                ),
                technical=(
                    "The defining HCI step: local NVMe claimed and pooled into one "
                    "cluster-wide vSAN datastore. ESA presents a single all-NVMe "
                    "tier where every device serves both cache and capacity, with "
                    "writes mirrored across nodes over the fabric — node-level "
                    "fault tolerance without a separate array."
                ),
                expert=(
                    "vSAN claims local NVMe into one cluster-wide datastore. ESA: "
                    "single all-NVMe tier, cache and capacity unified, writes "
                    "mirrored cross-node."
                ),
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
            description=L(
                novice=(
                    "The cluster is up. The management console shows one cluster of "
                    "four hosts backed by one shared storage area, the management "
                    "software watches the hardware and owns future upgrades, and "
                    "virtual machines can be created and moved between servers "
                    "while still running. Growth from here is non-disruptive: add a "
                    "server and its processing, memory, and storage all join the "
                    "running cluster at once — which is exactly what people mean "
                    "when they say this kind of system scales a node at a time."
                ),
                plain=(
                    "The cluster is up. vCenter shows one cluster of four hosts "
                    "backed by one vSAN datastore, VxRail Manager watches the "
                    "hardware and owns lifecycle upgrades, and virtual machines can "
                    "be created and moved live between nodes with vMotion. Growth "
                    "is non-disruptive: add a node and its CPU, memory, and NVMe "
                    "all join the running cluster at once — the reason HCI is "
                    "described as scaling a node at a time."
                ),
                standard=(
                    "The cluster is up. vCenter shows one cluster of four hosts "
                    "backed by one vSAN datastore, VxRail Manager watches the "
                    "hardware and owns lifecycle upgrades, and virtual machines "
                    "can be created and moved live between nodes with vMotion. "
                    "From here growth is non-disruptive: add a node and its CPU, "
                    "memory, and NVMe all join the running cluster at once — the "
                    "reason HCI scales 'a node at a time' from two nodes up to "
                    "sixty-four."
                ),
                technical=(
                    "Online: one vSphere cluster of four hosts on one vSAN "
                    "datastore, VxRail Manager owning hardware monitoring and "
                    "lifecycle, live migration available. Growth is non-disruptive "
                    "and fixed-ratio — a node contributes CPU, memory, and capacity "
                    "together, which is the coupling the PrivateCloud twin exists "
                    "to argue with."
                ),
                expert=(
                    "Online: four hosts, one vSAN datastore, lifecycle owned by "
                    "VxRail Manager, vMotion available. Growth is non-disruptive "
                    "but fixed-ratio — the coupling PrivateCloud argues against."
                ),
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
