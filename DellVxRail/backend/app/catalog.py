"""The components-and-options menu for a VxRail cluster.

Like the cluster anatomy, the catalog is data, not code. ``region_ids`` tie
each category to the floorplan regions it slots into (all four nodes, since
a VxRail cluster is built from identical nodes), so the UI can light up
"where it lives". ``details`` are written for a technically skilled reader
new to HCI — Dell and VMware jargon is spelled out on first use. Figures
follow Dell's VxRail spec sheet; treat them as product-literature numbers,
not benchmarks.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

# Every per-node category lights all four nodes on the floorplan.
_COMPUTE = ["compute-n1", "compute-n2", "compute-n3", "compute-n4"]
_MEMORY = ["memory-n1", "memory-n2", "memory-n3", "memory-n4"]
_STORAGE = ["storage-n1", "storage-n2", "storage-n3", "storage-n4"]
_BOOT = ["boot-n1", "boot-n2", "boot-n3", "boot-n4"]
_NETWORK = ["network-n1", "network-n2", "network-n3", "network-n4"]
_MGMT = ["mgmt-n1", "mgmt-n2", "mgmt-n3", "mgmt-n4"]
_POWER = ["power-n1", "power-n2", "power-n3", "power-n4"]
_FABRIC = ["tor-a", "tor-b"]

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="platform",
        name="Node platform",
        blurb=(
            "Every VxRail cluster is built from one node type, repeated. The "
            "platform sets the chassis, the processor family, and how much "
            "compute, memory, storage, and GPU each node can hold. Names "
            "encode role: VE = compute-dense 1U, VP = performance 2U, VS = "
            "storage-dense, VD = ruggedized/edge. All run the same VxRail HCI "
            "System Software."
        ),
        limits="One platform per cluster; all nodes in a cluster match",
        region_ids=_COMPUTE,
        options=[
            CatalogOption(
                id="plat-ve660",
                name="VxRail VE-660",
                summary="Compact 1U Intel node — the mainstream general-purpose building block.",
                details=(
                    "A 1U node on the PowerEdge R660 chassis with single or "
                    "dual Intel Xeon Scalable processors. The volume choice "
                    "for consolidating virtual machines where rack density "
                    "and core count matter more than GPUs or bulk capacity. "
                    "Its 1U height limits drive slots and add-in cards, which "
                    "is the trade for fitting twice as many nodes per rack "
                    "unit as a 2U platform."
                ),
            ),
            CatalogOption(
                id="plat-vp760",
                name="VxRail VP-760",
                summary="Performance 2U Intel node with room for up to six GPUs.",
                details=(
                    "A 2U node on the R760 chassis (the same server the R760 "
                    "twin models) with dual Intel Xeon Scalable CPUs, the most "
                    "memory and NVMe per node, and space for up to six GPUs. "
                    "The platform for demanding workloads: virtual desktops "
                    "(VDI), AI/ML inference, and databases that want both "
                    "cores and capacity in one node."
                ),
            ),
            CatalogOption(
                id="plat-vs760",
                name="VxRail VS-760",
                summary="Storage-dense 2U node for capacity-led clusters.",
                details=(
                    "A 2U node configured for maximum drive count per node, "
                    "for clusters where the sizing constraint is terabytes "
                    "rather than cores or GPUs — file services, backup "
                    "targets, and content repositories. Fewer, larger clusters "
                    "of these hold a lot of vSAN capacity behind modest "
                    "compute."
                ),
            ),
            CatalogOption(
                id="plat-vd4000",
                name="VxRail VD-4000",
                summary="Ruggedized short-depth node for the edge and harsh sites.",
                details=(
                    "A compact, short-depth, ruggedized node (available in "
                    "sled and standalone forms) built for edge locations — "
                    "factory floors, vehicles, telco cabinets — where depth, "
                    "temperature, shock, and dust rule out a normal rack "
                    "server. Small VD clusters, often two nodes plus a "
                    "witness, put full VxRail lifecycle automation where no "
                    "IT staff sit."
                ),
            ),
            CatalogOption(
                id="plat-vp7625",
                name="VxRail VP-7625 (AMD)",
                summary="AMD EPYC 2U performance node — highest core counts per socket.",
                details=(
                    "A 2U node built on AMD EPYC processors, offering very "
                    "high core counts and memory bandwidth per socket with up "
                    "to hundreds of terabytes of NVMe per node. Chosen where "
                    "per-node consolidation ratio (VMs per node) or "
                    "memory-bandwidth-bound analytics favor EPYC over Xeon."
                ),
            ),
            CatalogOption(
                id="plat-ve6615",
                name="VxRail VE-6615 (AMD)",
                summary="Compact 1U AMD EPYC node for dense general-purpose clusters.",
                details=(
                    "The 1U AMD counterpart to the VE-660: single-socket EPYC "
                    "with high core density in minimal rack space. A "
                    "cost-per-core play for large fleets of general-purpose "
                    "VMs where the workload scales with cores rather than "
                    "GPUs or capacity."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="processor",
        name="Processor",
        blurb=(
            "Each node runs its virtual machines and the vSAN storage stack "
            "on the same CPUs. Because storage steals cores, VxRail sets a "
            "minimum core count per node — vSAN ESA in particular is designed "
            "to spread work across many cores."
        ),
        limits="Minimum 16 cores + 128 GB memory per node for vSAN ESA",
        region_ids=_COMPUTE,
        options=[
            CatalogOption(
                id="cpu-xeon-4g",
                name="Intel Xeon Scalable (4th Gen)",
                summary="Sapphire Rapids — broad core range with built-in accelerators.",
                details=(
                    "The 4th-generation Intel Xeon Scalable family used across "
                    "the 16G VxRail Intel platforms, up to the mid-60s in core "
                    "count per socket. On-die accelerators and AVX-512 help "
                    "both mixed VM workloads and the data-reduction math vSAN "
                    "runs inline."
                ),
            ),
            CatalogOption(
                id="cpu-xeon-5g",
                name="Intel Xeon Scalable (5th Gen)",
                summary="Emerald Rapids — more cache and clocks on the same platform.",
                details=(
                    "A drop-in generational step with more L3 cache and higher "
                    "clocks, lifting per-core throughput for latency-sensitive "
                    "databases and denser VM consolidation without changing "
                    "the node platform."
                ),
            ),
            CatalogOption(
                id="cpu-epyc-4g",
                name="AMD EPYC (4th Gen)",
                summary="Genoa — up to 96 cores and eight memory channels per socket.",
                details=(
                    "The AMD option on VP-7625 / VE-6615 nodes: very high core "
                    "counts and memory bandwidth from a single socket, which "
                    "can raise VMs-per-node and suit bandwidth-bound analytics. "
                    "A single EPYC socket often replaces a dual-Xeon node for "
                    "core-scaled workloads, saving licensing that is counted "
                    "per core."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="memory",
        name="Memory",
        blurb=(
            "DDR5 DIMMs per node. In HCI, memory runs the guest VMs and backs "
            "the vSAN data path, so VxRail nodes carry more memory than a "
            "compute-only server of the same class."
        ),
        limits="Up to ~4 TB (Intel) per node depending on platform",
        region_ids=_MEMORY,
        options=[
            CatalogOption(
                id="mem-256",
                name="256 GB per node",
                summary="Entry point for edge and light general-purpose clusters.",
                details=(
                    "Enough for a modest VM count per node plus the vSAN "
                    "overhead. Common on VD edge clusters and small VE "
                    "clusters where the workload is bounded and predictable. "
                    "All nodes in a cluster should be memory-matched so vSphere "
                    "HA can restart any node's VMs anywhere."
                ),
            ),
            CatalogOption(
                id="mem-1024",
                name="1 TB per node",
                summary="The mainstream consolidation sweet spot.",
                details=(
                    "A terabyte per node comfortably runs dozens of "
                    "general-purpose VMs with headroom for vSAN and for a "
                    "failed node's VMs to restart on survivors. The usual "
                    "default for VE-660 / VP-760 consolidation clusters."
                ),
            ),
            CatalogOption(
                id="mem-2048",
                name="2 TB per node",
                summary="For memory-hungry workloads — VDI, in-memory databases.",
                details=(
                    "Virtual desktops and in-memory databases are gated by "
                    "RAM long before cores. Two terabytes per node keeps the "
                    "cluster VM-dense without memory becoming the bottleneck; "
                    "typically paired with the VP performance platform."
                ),
            ),
            CatalogOption(
                id="mem-4096",
                name="4 TB per node (max)",
                summary="Maximum memory for the largest VMs and densest hosts.",
                details=(
                    "The ceiling on the 2U Intel platforms, for monster VMs "
                    "or the highest consolidation ratios. Populating every "
                    "channel also maximizes memory bandwidth, which vSAN ESA "
                    "and analytics both reward."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="storage-arch",
        name="vSAN storage architecture",
        blurb=(
            "vSAN is VMware's software that pools every node's local drives "
            "into one shared datastore — it is what makes the cluster "
            "hyperconverged. The architecture you pick decides how those "
            "drives are organized."
        ),
        limits="ESA is all-NVMe single-tier; OSA supports hybrid/legacy layouts",
        region_ids=_STORAGE,
        options=[
            CatalogOption(
                id="arch-esa",
                name="vSAN ESA (Express Storage Architecture)",
                summary="Single tier of all-NVMe drives — every drive is both cache and capacity.",
                details=(
                    "The current architecture: one pool of NVMe TLC drives per "
                    "node with no separate cache tier. Every drive serves "
                    "cache and capacity, writes are logged and mirrored across "
                    "nodes, and ESA delivers RAID-6 space efficiency at RAID-1 "
                    "performance — you stop trading resilience against "
                    "capacity. It needs NVMe drives, higher core counts, and "
                    "a fast (RoCE) network, which is why it is the default on "
                    "new all-NVMe VxRail clusters."
                ),
            ),
            CatalogOption(
                id="arch-osa",
                name="vSAN OSA (Original Storage Architecture)",
                summary="Classic disk groups: a dedicated cache tier in front of capacity.",
                details=(
                    "The older model, still supported: drives are organized "
                    "into disk groups, each a fast cache device fronting "
                    "several capacity devices, and it can be all-flash or "
                    "hybrid (flash cache over spinning capacity). Chosen for "
                    "capacity-led builds, existing OSA estates, or where "
                    "spinning disks are still required for cost."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="drives",
        name="Capacity drives",
        blurb=(
            "The NVMe drives in each node's front bay. Their total across all "
            "nodes, minus the resilience overhead vSAN reserves, is the "
            "cluster's usable datastore. Drives are added per node so nodes "
            "stay matched."
        ),
        limits="All-NVMe TLC for ESA; keep drive counts matched across nodes",
        region_ids=_STORAGE,
        options=[
            CatalogOption(
                id="drive-3_84",
                name="3.84 TB NVMe TLC",
                summary="Balanced capacity point for general-purpose clusters.",
                details=(
                    "Triple-level-cell (TLC) NAND — the mainstream enterprise "
                    "flash grade. A good default: enough capacity per drive to "
                    "grow into, small enough that more drives per node means "
                    "more parallelism for vSAN. Populate the same count in "
                    "every node."
                ),
            ),
            CatalogOption(
                id="drive-7_68",
                name="7.68 TB NVMe TLC",
                summary="Capacity-per-slot sweet spot for consolidation.",
                details=(
                    "Doubles capacity per drive; a handful per node across "
                    "four nodes builds a datastore in the hundreds of "
                    "terabytes. The common pick when consolidating storage "
                    "for many VMs onto one cluster."
                ),
            ),
            CatalogOption(
                id="drive-15_36",
                name="15.36 TB NVMe TLC",
                summary="Maximum density for capacity-led VS clusters.",
                details=(
                    "The densest option, for storage-dense builds where "
                    "terabytes-per-rack-unit dominate. Fewer, larger drives "
                    "mean less parallelism per node, so these suit "
                    "capacity-heavy, throughput-moderate workloads like file "
                    "shares and backup landing zones."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="boot",
        name="Boot device (BOSS-N1)",
        blurb=(
            "Where each node's ESXi hypervisor lives — deliberately separate "
            "from the vSAN data drives, so the OS and the data never compete "
            "and a boot failure never risks cluster data."
        ),
        limits="One BOSS-N1 per node; mirrored M.2 pair",
        region_ids=_BOOT,
        options=[
            CatalogOption(
                id="boot-bossn1",
                name="BOSS-N1 mirrored M.2",
                summary="A hardware-mirrored pair of M.2 NVMe SSDs dedicated to ESXi.",
                details=(
                    "BOSS (Boot Optimized Storage Solution) is a small "
                    "RAID-1 pair of M.2 SSDs on its own controller, used only "
                    "for the hypervisor and VxRail image. It is the device "
                    "ESXi boots from during first run. Because it is mirrored "
                    "and isolated from the NVMe capacity drives, a boot SSD "
                    "can fail and be replaced with the node — and the cluster "
                    "— fully online."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="network",
        name="Node networking (NIC)",
        blurb=(
            "Each node's NIC carries three networks over the same ports: VM "
            "traffic, vMotion (live migration), and the vSAN storage traffic "
            "that mirrors writes between nodes. On ESA this network is on the "
            "critical path for storage latency."
        ),
        limits="Ports per node must match the top-of-rack fabric speed",
        region_ids=_NETWORK,
        options=[
            CatalogOption(
                id="nic-25gbe",
                name="25 GbE (OCP / NDC)",
                summary="The mainstream cluster interconnect for general-purpose builds.",
                details=(
                    "Dual or quad 25 GbE ports per node on an OCP 3.0 or "
                    "PowerEdge NDC (Network Daughter Card) form factor — the "
                    "same cabling plant as 10 GbE with far more bandwidth. "
                    "Ample for VE/VS consolidation clusters; each node "
                    "connects to both top-of-rack switches for redundancy."
                ),
            ),
            CatalogOption(
                id="nic-100gbe",
                name="100 GbE with RoCE",
                summary="Low-latency storage fabric for vSAN ESA performance clusters.",
                details=(
                    "100 GbE ports supporting RoCE (RDMA over Converged "
                    "Ethernet), which lets one node write into another node's "
                    "memory with minimal CPU involvement — the low-latency "
                    "path vSAN ESA is built for. The right choice for VP "
                    "performance clusters, VDI, and databases, and it needs a "
                    "switch pair configured to match."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="fabric",
        name="Top-of-rack fabric",
        blurb=(
            "The redundant switch pair every node plugs into. It is not "
            "optional plumbing: vSAN mirrors writes across nodes over this "
            "fabric, so its redundancy is part of the cluster's data "
            "resilience."
        ),
        limits="Redundant pair required; SmartFabric needs Dell PowerSwitch",
        region_ids=_FABRIC,
        options=[
            CatalogOption(
                id="fab-smartfabric",
                name="Dell PowerSwitch + SmartFabric Services",
                summary="VxRail programs its own switches — the network configures itself.",
                details=(
                    "On Dell PowerSwitch top-of-rack switches, VxRail can "
                    "drive SmartFabric Services: the cluster automatically "
                    "creates and maintains the VLANs and settings its own "
                    "networks need, so adding a node does not mean a switch "
                    "ticket. The tightest integration, and the least "
                    "network-engineering effort at the edge."
                ),
            ),
            CatalogOption(
                id="fab-customer",
                name="Customer-managed switches",
                summary="Bring your own switches to a documented configuration.",
                details=(
                    "VxRail also runs on existing customer-managed switches, "
                    "configured by hand to Dell's network guide (VLANs, MTU, "
                    "multicast/unicast, and — for ESA — RoCE lossless "
                    "settings). More flexible for standardized data-center "
                    "fabrics, at the cost of doing the network setup yourself."
                ),
            ),
            CatalogOption(
                id="fab-dynamic-nodes",
                name="Dynamic Node Networking",
                summary="Separate the cluster network from external/storage traffic.",
                details=(
                    "Advanced topologies let VxRail split the networks it "
                    "carries — for example, dedicating ports to vSAN so "
                    "storage traffic never contends with VMs, or attaching "
                    "external storage. Useful for large clusters and for "
                    "Dynamic Nodes (compute-only nodes that use external "
                    "storage instead of vSAN)."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="gpu",
        name="GPU acceleration",
        blurb=(
            "Optional accelerators in the 2U performance nodes, for workloads "
            "the CPU cannot serve alone — graphics for virtual desktops and "
            "matrix math for AI. GPUs live in the compute node, so a "
            "GPU-heavy cluster is a VP cluster."
        ),
        limits="Up to 6 GPUs per VP-760 node; none on 1U VE nodes",
        region_ids=_COMPUTE,
        options=[
            CatalogOption(
                id="gpu-none",
                name="No GPU (CPU-only)",
                summary="Most clusters — general-purpose VMs need no accelerator.",
                details=(
                    "The default. General server consolidation, databases, "
                    "and file services run entirely on CPU; adding GPUs would "
                    "spend power and slots for nothing. Leaves the node's "
                    "slots for more NVMe or networking."
                ),
            ),
            CatalogOption(
                id="gpu-vdi",
                name="GPUs for VDI (graphics)",
                summary="Shared GPUs so many virtual desktops get hardware graphics.",
                details=(
                    "Data-center GPUs partitioned across many virtual "
                    "desktops (vGPU), so each user gets smooth graphics — CAD, "
                    "video, modern OS compositing — from a VM. Sized by users "
                    "per GPU and paired with high memory per node; the classic "
                    "VP-760 VDI build."
                ),
            ),
            CatalogOption(
                id="gpu-ai",
                name="GPUs for AI / ML inference",
                summary="Accelerators for inference and light training at the data's location.",
                details=(
                    "Higher-end GPUs for running AI inference (and modest "
                    "fine-tuning) next to the data already living on the "
                    "cluster, avoiding a separate AI silo. Up to six per "
                    "VP-760 node; capacity and networking are sized to keep "
                    "the accelerators fed."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="topology",
        name="Cluster topology",
        blurb=(
            "How the nodes are arranged. VxRail is not only 'a rack of "
            "identical nodes' — the same software supports tiny two-node edge "
            "clusters and site-spanning stretched clusters."
        ),
        limits="2–64 nodes; 2-node and stretched clusters need a witness",
        region_ids=_FABRIC,
        options=[
            CatalogOption(
                id="topo-standard",
                name="Standard cluster (3–64 nodes)",
                summary="The common shape: three or more nodes in one rack/site.",
                details=(
                    "Three nodes is the smallest fully self-protecting "
                    "cluster (data has somewhere to rebuild after a node "
                    "loss); it grows one node at a time to sixty-four. This is "
                    "the topology the first-run trace on the home page builds."
                ),
            ),
            CatalogOption(
                id="topo-2node",
                name="2-node ROBO cluster + witness",
                summary="The minimum cluster for edge/remote-office sites.",
                details=(
                    "Two nodes back each other up, with a lightweight witness "
                    "appliance (often a VM at a central site) casting the "
                    "tie-breaking vote so the survivor knows it is the "
                    "survivor. The economical way to put a self-managing, "
                    "fully-redundant cluster in a remote office or branch "
                    "office (ROBO) with no local IT."
                ),
            ),
            CatalogOption(
                id="topo-stretched",
                name="Stretched cluster across two sites",
                summary="One cluster split across two rooms/sites for zero-RPO availability.",
                details=(
                    "Half the nodes sit in each of two sites with synchronous "
                    "vSAN mirroring between them and a witness at a third "
                    "location. A whole site can fail and VMs restart on the "
                    "other with no data loss (zero RPO — recovery point "
                    "objective). Needs low-latency links between sites."
                ),
            ),
            CatalogOption(
                id="topo-dynamic",
                name="Dynamic Nodes (compute-only)",
                summary="Nodes with no local storage that use an external array instead.",
                details=(
                    "Dynamic Nodes run VxRail's lifecycle automation but keep "
                    "no vSAN datastore of their own — they consume storage "
                    "from an external Dell array (PowerStore, PowerMax, Unity "
                    "XT) over the fabric. The way to scale compute independent "
                    "of storage while keeping one VxRail management model."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="vxrail-software",
        name="VxRail HCI System Software",
        blurb=(
            "The layer that makes this a VxRail and not just servers running "
            "vSphere. It is what Dell adds on top of VMware: automation, "
            "lifecycle management, and support integration."
        ),
        limits="Included with every VxRail; not sold separately",
        region_ids=[],
        options=[
            CatalogOption(
                id="sw-manager",
                name="VxRail Manager",
                summary="The single pane of glass that builds the cluster and runs its life cycle.",
                details=(
                    "The appliance elected onto the primary node during first "
                    "run. It automates the initial build and, day-to-day, "
                    "presents cluster health and drives the defining VxRail "
                    "feature: one-click full-stack lifecycle management. It "
                    "upgrades firmware, ESXi, and vSAN together as a tested, "
                    "Dell-validated bundle — the thing customers buy VxRail "
                    "for instead of assembling their own vSAN cluster."
                ),
            ),
            CatalogOption(
                id="sw-lcm",
                name="Continuously validated states (LCM)",
                summary="Upgrades are pre-tested combinations, not a matrix you validate yourself.",
                details=(
                    "Dell tests each combination of firmware, hypervisor, and "
                    "vSAN as a 'continuously validated state' and ships it as "
                    "one bundle. Lifecycle management (LCM) applies it "
                    "node-by-node with VMs migrating out of the way, so the "
                    "cluster upgrades without downtime and without the "
                    "operator hand-checking a compatibility matrix."
                ),
            ),
            CatalogOption(
                id="sw-support",
                name="SolVe / Secure Connect Gateway support integration",
                summary="Phone-home telemetry and guided, hardware-aware support.",
                details=(
                    "VxRail integrates hardware and software support into one "
                    "channel: the cluster phones home health and logs, and a "
                    "single Dell case covers a failed drive and a hypervisor "
                    "bug alike. It is the operational payoff of a "
                    "single-vendor, jointly-engineered stack."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="vmware-software",
        name="VMware software & licensing",
        blurb=(
            "VxRail runs VMware's stack — the hypervisor, the storage, and "
            "the management plane. The edition you license sets which "
            "features are available and whether the cluster is part of a "
            "private cloud."
        ),
        limits="vSphere + vSAN required; VCF for full private cloud",
        region_ids=[],
        options=[
            CatalogOption(
                id="vmw-vsphere",
                name="vSphere + vSAN",
                summary="The baseline: ESXi hypervisor, vCenter management, and vSAN storage.",
                details=(
                    "Every VxRail needs vSphere (ESXi on each node plus "
                    "vCenter Server to manage them) and vSAN (the software "
                    "that pools local drives). This is the minimum stack — a "
                    "self-contained virtualization cluster with shared "
                    "storage, managed from vCenter, with no external SAN."
                ),
            ),
            CatalogOption(
                id="vmw-vcf",
                name="VMware Cloud Foundation (VCF)",
                summary="Full private cloud: adds automated networking, and lifecycle across clusters.",
                details=(
                    "VCF layers a full software-defined data center on top — "
                    "software-defined networking, and fleet-wide lifecycle via "
                    "SDDC Manager. VxRail was the first HCI system with full "
                    "VCF integration, so SDDC Manager and VxRail Manager "
                    "coordinate upgrades. The choice when the goal is a "
                    "private cloud with self-service and Kubernetes, not just "
                    "a virtualization cluster."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="management",
        name="Management & monitoring",
        blurb=(
            "Beyond VxRail Manager and vCenter, the per-node service "
            "processors and Dell's cloud service give hardware-level and "
            "fleet-level visibility."
        ),
        limits="iDRAC per node; CloudIQ is cloud-hosted and read-only",
        region_ids=_MGMT,
        options=[
            CatalogOption(
                id="mgmt-idrac",
                name="iDRAC (per node)",
                summary="The always-on service processor in every node, as in the R760/iDRAC twins.",
                details=(
                    "Each node's integrated Dell Remote Access Controller "
                    "gives out-of-band hardware health, remote console, and "
                    "power control independent of ESXi. VxRail Manager reads "
                    "the iDRACs for hardware status, so a failing part is "
                    "flagged in the same UI that manages the VMs."
                ),
            ),
            CatalogOption(
                id="mgmt-cloudiq",
                name="CloudIQ / APEX AIOps",
                summary="Dell's cloud monitoring: fleet health, capacity forecasting, anomaly alerts.",
                details=(
                    "The cluster streams telemetry to Dell's cloud service, "
                    "which trends capacity, forecasts exhaustion, scores "
                    "health, and flags anomalies across every VxRail (and "
                    "other Dell systems) you own. Read-only by design — "
                    "control stays on-prem in VxRail Manager and vCenter."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="power",
        name="Power supplies",
        blurb=(
            "Redundant hot-swap PSUs per node. Because vSAN keeps copies of "
            "data on other nodes, cluster resilience is layered: redundant "
            "supplies protect a node, and the cluster protects against losing "
            "the whole node."
        ),
        limits="Redundant PSUs per node; feed from separate rails",
        region_ids=_POWER,
        options=[
            CatalogOption(
                id="psu-redundant",
                name="Redundant hot-swap PSUs (per node)",
                summary="Two supplies per node, either one able to carry it, hot-swappable.",
                details=(
                    "Standard PowerEdge redundant supplies: fed from separate "
                    "rails, a node survives a circuit outage, and a failed "
                    "supply swaps with the node online. Titanium-class "
                    "efficiency options reduce draw across a cluster of many "
                    "nodes, where power and cooling are a real running cost."
                ),
            ),
        ],
    ),
]
