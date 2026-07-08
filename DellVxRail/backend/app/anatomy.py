"""Cluster-anatomy data: a four-node VxRail cluster, annotated.

Like the other twins, the layout is *data*, not code: regions placed in a
normalized coordinate space the frontend renders as SVG. Geometry is
stylized — favor a correct mental model over exact rack units (project scope
guardrail).

The view is a front-of-rack elevation with four identical HCI nodes stacked
top to bottom, joined by a redundant top-of-rack switch pair across the top.
Within each node the front (the NVMe drive bay) is at x=0 and the rear (NIC
and power) is at x=100 — the same front-to-rear convention the chassis twins
use. Every node is the same building block; the cluster's power comes from
having several of them, not from any one being special. (During first run
exactly one node is temporarily special — it wins the primary election and
runs VxRail Manager — but that is a role, not different hardware.)
"""

from __future__ import annotations

from .models import ClusterAnatomy, ClusterRegion, Photo, SourceLink, Stat

# The only shipped visual is a self-contained schematic drawn for this
# project — not a Dell product image — with an honest credit line.
CLUSTER_ILLO = Photo(
    url="/vxrail-cluster.svg",
    caption=(
        "A four-node VxRail cluster: identical PowerEdge-based HCI nodes "
        "joined by a redundant top-of-rack switch pair. Each node's local "
        "NVMe drives are pooled into one shared vSAN datastore, and one node "
        "runs the VxRail Manager VM (the blue house)."
    ),
    credit="Schematic illustration by this project — not a Dell product image",
)


# --- Per-node region descriptions (shared across all four nodes) -------------

_STORAGE_DESC = (
    "The node's front NVMe drive bay. These are the capacity drives, and "
    "they are the raw material of storage: VxRail pools every node's local "
    "NVMe into one cluster-wide vSAN datastore rather than attaching an "
    "external array. On the Express Storage Architecture (ESA) they are all "
    "NVMe TLC and every drive serves both cache and capacity — there is no "
    "separate cache tier as there was on the older Original Storage "
    "Architecture (OSA)."
)

_BOOT_DESC = (
    "The node's BOSS-N1 boot device (Boot Optimized Storage Solution): a "
    "small mirrored pair of M.2 SSDs that holds only the ESXi hypervisor and "
    "the VxRail factory image. Keeping the OS here, off the data drives, "
    "means every NVMe capacity drive is free for vSAN and a boot-device "
    "failure never touches cluster data."
)

_MEMORY_DESC = (
    "The node's DDR5 DIMM banks. Memory does double duty in HCI: it runs the "
    "guest virtual machines and it backs the vSAN data path, so VxRail nodes "
    "are configured with more memory than a compute-only server of the same "
    "size — a common build is hundreds of gigabytes to multiple terabytes "
    "per node."
)

_COMPUTE_DESC = (
    "The node's CPU socket(s) — Intel Xeon Scalable or AMD EPYC. In a "
    "hyperconverged node the processor runs both the virtual machines and "
    "the storage stack (vSAN) at the same time; ESA is deliberately designed "
    "to spread its work across many cores, which is why VxRail requires a "
    "minimum core count and memory per node before a node may join a vSAN "
    "ESA cluster."
)

_NETWORK_DESC = (
    "The node's network adapter — OCP/NDC ports, typically 25 or 100 GbE. "
    "This is the cluster's nervous system: it carries VM traffic, vMotion "
    "(live migration of running VMs between nodes), and the vSAN storage "
    "traffic that mirrors every write across nodes. ESA clusters lean on "
    "RoCE (RDMA over Converged Ethernet) for low-latency storage, which is "
    "why the switch pair and NICs are chosen together."
)

_MGMT_DESC = (
    "The node's iDRAC — the integrated Dell Remote Access Controller, the "
    "always-on service processor (see the iDRAC twin). It powers up on "
    "standby before the host does, and VxRail uses it for hardware health, "
    "remote console, and lifecycle operations. During first run the nodes "
    "reach one another over the management network the iDRAC and OS share."
)

_POWER_DESC = (
    "The node's redundant hot-swap power supplies. Each node powers itself; "
    "fed from separate rails, a node rides through a circuit outage. Because "
    "the cluster keeps a copy of data on other nodes, losing a whole node — "
    "power and all — degrades capacity but never loses committed writes."
)


def _node(idx: int, y0: float) -> list[ClusterRegion]:
    """One HCI node as a horizontal slice; front (drives) left, rear right."""
    s = f"n{idx}"
    tag = f"Node {idx}"
    h = 12.0
    return [
        ClusterRegion(
            id=f"storage-{s}", kind="storage", label="NVMe",
            x=0, y=y0, w=11, h=h, description=_STORAGE_DESC,
        ),
        ClusterRegion(
            id=f"boot-{s}", kind="boot", label="BOSS",
            x=12, y=y0, w=10, h=5.5, description=_BOOT_DESC,
        ),
        ClusterRegion(
            id=f"mgmt-{s}", kind="management", label="iDRAC",
            x=12, y=y0 + 6.5, w=10, h=5.5, description=_MGMT_DESC,
        ),
        ClusterRegion(
            id=f"memory-{s}", kind="memory", label="DIMMs",
            x=23, y=y0, w=14, h=h, description=_MEMORY_DESC,
        ),
        ClusterRegion(
            id=f"compute-{s}", kind="compute", label=f"CPU · {tag}",
            x=38, y=y0, w=18, h=h, description=_COMPUTE_DESC,
        ),
        ClusterRegion(
            id=f"network-{s}", kind="network", label="NIC",
            x=57, y=y0, w=18, h=h, description=_NETWORK_DESC,
        ),
        ClusterRegion(
            id=f"power-{s}", kind="power", label=f"PSU · {tag}",
            x=76, y=y0, w=22, h=h, description=_POWER_DESC,
        ),
    ]


ANATOMY = ClusterAnatomy(
    id="vxrail",
    name="VxRail four-node cluster",
    vendor="Dell Technologies + VMware",
    form_factor="4× 1U/2U HCI nodes + redundant top-of-rack fabric",
    generation="VxRail (16G PowerEdge · vSAN ESA)",
    year=2024,
    width=100,
    height=64,
    overview=(
        "VxRail is Dell's hyperconverged infrastructure (HCI) system, "
        "jointly engineered with VMware. Instead of separate servers and a "
        "storage array, it is built from identical nodes — each a Dell "
        "PowerEdge server running VMware ESXi — whose local NVMe drives are "
        "pooled by VMware vSAN into one shared datastore that spans the "
        "cluster. VxRail Manager, unique to VxRail, automates the whole life "
        "cycle: it builds the cluster on first run and keeps hardware, "
        "hypervisor, and vSAN upgrades in lockstep afterward. A cluster "
        "starts at two nodes and grows one node at a time to sixty-four, "
        "adding compute, memory, and storage together each time. This "
        "floorplan shows four nodes joined by a redundant switch pair; the "
        "layout is a stylized mental model, not a rack-accurate drawing."
    ),
    regions=[
        ClusterRegion(
            id="tor-a", kind="fabric", label="Top-of-rack switch A",
            x=6, y=1, w=43, h=6,
            description=(
                "One of a redundant pair of top-of-rack switches — the "
                "cluster network. Every node connects to both switches, so a "
                "switch failure never partitions the cluster. This fabric "
                "carries three logical networks over the same wires: VM "
                "traffic, vMotion (live VM migration), and vSAN storage "
                "replication. On ESA clusters it is tuned for RoCE (RDMA over "
                "Converged Ethernet) to keep storage latency low."
            ),
        ),
        ClusterRegion(
            id="tor-b", kind="fabric", label="Top-of-rack switch B",
            x=51, y=1, w=43, h=6,
            description=(
                "The second top-of-rack switch. VxRail can drive the switch "
                "pair itself through SmartFabric Services on Dell PowerSwitch "
                "hardware — the cluster programs its own VLANs — or connect to "
                "customer-managed switches. Either way the redundant pair is "
                "what lets vSAN safely mirror writes between nodes: lose one "
                "switch and every node still has a path to every other."
            ),
        ),
        *_node(1, 9),
        *_node(2, 23),
        *_node(3, 37),
        *_node(4, 51),
    ],
    stats=[
        Stat(label="Nodes per cluster", value="2–64 (grow one at a time)"),
        Stat(label="Node platform", value="Dell PowerEdge (Intel Xeon / AMD EPYC)"),
        Stat(label="Hypervisor", value="VMware ESXi on every node"),
        Stat(label="Storage", value="VMware vSAN — ESA all-NVMe or OSA"),
        Stat(label="Management", value="VxRail Manager + vCenter Server"),
        Stat(label="Cluster network", value="25 / 100 GbE redundant top-of-rack pair"),
        Stat(label="Minimum cluster", value="2 nodes + a witness (ROBO/edge)"),
    ],
    photo=CLUSTER_ILLO,
    sources=[
        SourceLink(
            label="Dell VxRail product page",
            url="https://www.dell.com/en-us/shop/storage-servers-and-networking-for-business/sf/vxrail-hci",
        ),
        SourceLink(
            label="Dell VxRail spec sheet (H16763)",
            url="https://www.delltechnologies.com/asset/en-us/products/converged-infrastructure/technical-support/h16763-vxrail-spec-sheet.pdf",
        ),
        SourceLink(
            label="Dell VxRail with vSAN ESA (Info Hub)",
            url="https://infohub.delltechnologies.com/p/vxrail-with-vsan-express-storage-architecture-esa/",
        ),
        SourceLink(
            label="VxRail Architecture Overview (Dell docs)",
            url="https://www.dell.com/support/manuals/en-us/vxrail-d-series-nodes/vxrail_architecture_guide/features",
        ),
    ],
)
