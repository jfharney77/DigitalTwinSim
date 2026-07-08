"""Chassis-anatomy data: one PowerMax node-pair engine and its drive
enclosure, annotated.

Like the GPU app's die anatomies and the PowerStore floorplan, the enclosure
is *data*, not code: regions placed in a normalized coordinate space the
frontend renders as SVG. Geometry is stylized, traced from Dell's PowerMax
2500/8500 spec sheet and product imagery — favor a correct mental model over
exact millimetres (project scope guardrail).

What's drawn: a single **node pair** — the modular building block of a
PowerMax array. Two compute nodes (directors), Node A on top and Node B
below, connected by the InfiniBand Dynamic Fabric down the middle, plus the
48-slot Dynamic Media Enclosure (DME) that holds the NVMe drives at the
front. A PowerMax 2500 is 1–2 of these node pairs; an 8500 scales to 8. Top-
down view: front of the rack (the DME) at x=0, rear (I/O modules and PSUs)
at x=100.
"""

from __future__ import annotations

from .models import ChassisAnatomy, ChassisRegion, SourceLink, Stat

# --- Per-node region descriptions (shared A/B text) --------------------------

_FAN_DESC = (
    "The node's fan pack. Airflow runs front to rear: in over the DME "
    "drives, through the director, out past the power supply. Cooling is per "
    "node, and PowerMax runs its CPUs continuously in turbo, so the fans and "
    "the Adaptive Cooling algorithm work harder at high ambient temperature — "
    "which is why the spec sheet quotes two power figures, one below 26 °C "
    "and a higher one above 35 °C."
)

_VAULT_DESC = (
    "Vault-to-flash module: an NVMe SED (self-encrypting drive) flash device. "
    "PowerMax's write cache lives in DRAM, which is volatile — on AC loss the "
    "standby power supply keeps the node alive just long enough to 'vault', "
    "copying the entire cache to these flash modules so no acknowledged write "
    "is ever lost. On the next boot the array validates the vault and, if the "
    "shutdown was dirty, restores cache before serving I/O. Two to four "
    "modules per node pair."
)

_SPS_DESC = (
    "Standby power supply (SPS): the battery behind vault-to-flash. It is not "
    "a UPS — it cannot keep the array serving I/O. Its single job is to power "
    "the node through the seconds it takes to flush DRAM cache to the vault "
    "flash modules when line power disappears. It self-tests before the array "
    "will accept a single write."
)

_CACHE_DESC = (
    "The node's DRAM — PowerMax calls it 'cache' or global memory. Reads and "
    "writes are served from here at memory speed, metadata lives here, and "
    "every dirty write is mirrored to the partner node over the fabric before "
    "the host is acknowledged. Cache scales from 896 GB to 7.68 TB per node "
    "pair; the amount is what most separates the memory-configuration tiers."
)

_CPU_DESC = (
    "The director's Intel Xeon Scalable processors. Each node is a complete "
    "multi-socket x86 compute complex; PowerMaxOS 10, all data services "
    "(global inline data reduction, SnapVX, SRDF), and the RAID math run "
    "here. Higher memory-configuration tiers ship faster Xeons with more "
    "cores — up to 20 cores per CPU on the 8500's top tier."
)

_FABRIC_DESC = (
    "InfiniBand Dynamic Fabric adapter: PowerMax's scale-out interconnect at "
    "100 Gb/s per port. It carries cache mirroring and heartbeat between the "
    "two nodes of this pair and — on the 8500 — connects every node pair to "
    "every other over a dual redundant fabric, so any director can reach any "
    "drive in any DME. This is what lets nodes and capacity grow "
    "independently. The 2500 uses a direct fabric connection; the 8500 a dual "
    "redundant fabric."
)

_IOMOD_DESC = (
    "Front-end I/O module slot. Field-replaceable cards set which fabrics "
    "hosts connect over: 32/64 Gb Fibre Channel and FC-NVMe, 100/25/10 GbE "
    "for iSCSI and NVMe/TCP, FICON and zHyperlink for IBM mainframe, and SRDF "
    "replication ports. Up to eight modules per node pair (four per node), and "
    "both nodes carry matching modules so every host path exists twice."
)

_MGMT_DESC = (
    "Management and control ports. PowerMax is administered from Unisphere for "
    "PowerMax and driven over a REST API; the management network is kept off "
    "the data path. On the array these ports also reach the embedded "
    "management module used for call-home and remote support."
)

_BOARD_DESC = (
    "The director system board and its slice of the midplane: the PCIe fabric "
    "that fans out from the Xeons to the fabric adapters, the front-end I/O "
    "modules, and the vault flash. The drives themselves are not on this "
    "board — they live in the DME and are reached over the InfiniBand fabric."
)

_PSU_DESC = (
    "The node's power supply. Each director has redundant, hot-swap supplies "
    "fed from two power zones; PowerMax racks take single- or three-phase "
    "input (Delta or Wye) and ship with intelligent PDUs that report power, "
    "voltage, current, temperature, and humidity as real-time telemetry."
)


def _node(suffix: str, y0: float) -> list[ChassisRegion]:
    """One director node; Node A at y0=1, Node B mirrored at y0=27."""
    up = suffix.upper()
    return [
        ChassisRegion(
            id=f"fans-{suffix}", kind="cooling", label=f"Fans {up}",
            x=10.5, y=y0, w=6, h=24, description=_FAN_DESC,
        ),
        ChassisRegion(
            id=f"vault-{suffix}", kind="vault", label="Vault flash",
            x=17, y=y0, w=8, h=11, description=_VAULT_DESC,
        ),
        ChassisRegion(
            id=f"sps-{suffix}", kind="battery", label=f"SPS {up}",
            x=17, y=y0 + 12, w=8, h=12, description=_SPS_DESC,
        ),
        ChassisRegion(
            id=f"cache-{suffix}", kind="cache", label="Cache (DRAM)",
            x=26, y=y0, w=9, h=24, description=_CACHE_DESC,
        ),
        ChassisRegion(
            id=f"cpu-{suffix}", kind="cpu", label=f"Xeon · Node {up}",
            x=36, y=y0, w=12, h=24, description=_CPU_DESC,
        ),
        ChassisRegion(
            id=f"fabric-{suffix}", kind="fabric", label="InfiniBand",
            x=49, y=y0, w=10, h=24, description=_FABRIC_DESC,
        ),
        ChassisRegion(
            id=f"iomod-{suffix}1", kind="io", label="FE I/O 0",
            x=60, y=y0, w=11, h=11.5, description=_IOMOD_DESC,
        ),
        ChassisRegion(
            id=f"iomod-{suffix}2", kind="io", label="FE I/O 1",
            x=60, y=y0 + 12.5, w=11, h=11.5, description=_IOMOD_DESC,
        ),
        ChassisRegion(
            id=f"mgmt-{suffix}", kind="management", label="Mgmt",
            x=72, y=y0, w=10, h=11, description=_MGMT_DESC,
        ),
        ChassisRegion(
            id=f"board-{suffix}", kind="board", label=f"Node {up} board",
            x=72, y=y0 + 12, w=10, h=12, description=_BOARD_DESC,
        ),
        ChassisRegion(
            id=f"psu-{suffix}", kind="power", label=f"PSU {up}",
            x=83, y=y0, w=16, h=24, description=_PSU_DESC,
        ),
    ]


ANATOMY = ChassisAnatomy(
    id="powermax",
    name="PowerMax 2500 node pair + DME",
    vendor="Dell Technologies",
    form_factor="3U node-pair engine + 48-slot DME",
    generation="PowerMax (PowerMaxOS 10)",
    year=2025,
    width=100,
    height=52,
    overview=(
        "PowerMax is Dell's flagship mission-critical storage array: an "
        "end-to-end NVMe scale-out system for the workloads that cannot go "
        "down — large databases, SAP, VMware at scale, and IBM mainframe. It "
        "is built from modular node pairs. Each node pair is two compute nodes "
        "(directors) with their own CPUs, DRAM cache, vault flash, and "
        "front-end connectivity, joined by a 100 Gb/s InfiniBand Dynamic "
        "Fabric. Drives live separately in 48-slot Dynamic Media Enclosures "
        "(DMEs) reached over that same fabric, so compute and capacity scale "
        "independently — add node pairs for performance, add drives one at a "
        "time for capacity. A PowerMax 2500 is 1–2 node pairs; a PowerMax 8500 "
        "scales to 8 node pairs and 18 PBe. PowerMaxOS 10 runs global inline "
        "data reduction (guaranteed 5:1 open systems, 3:1 mainframe), SnapVX "
        "snapshots, SRDF replication, and hardware-rooted cyber resiliency, at "
        "six-nines availability. This floorplan shows one node pair engine and "
        "one DME."
    ),
    regions=[
        ChassisRegion(
            id="dme", kind="storage", label="48× NVMe DME",
            x=0, y=0, w=9, h=51,
            description=(
                "Dynamic Media Enclosure (DME): the drive shelf, holding up to "
                "48 dual-ported 2.5″ NVMe flash drives (3.84–30.72 TB, TLC or "
                "QLC). 'Dual-ported' means each drive has two independent "
                "channels, so both directors — and, through the fabric, every "
                "node pair — reach every drive directly, with automatic "
                "failover if one path fails. The DME is a separate module from "
                "the compute node pair and attaches over the InfiniBand "
                "Dynamic Fabric: that separation is what lets capacity grow "
                "without adding controllers. A PowerMax 2500 holds up to 96 "
                "drives; an 8500 up to 384."
            ),
        ),
        *_node("a", 1),
        ChassisRegion(
            id="fabric-bus", kind="fabric", label="Dynamic Fabric",
            x=26, y=25.2, w=45, h=1.6,
            description=(
                "The InfiniBand Dynamic Fabric that ties the pair together — "
                "and, on the 8500, ties every node pair to every other. Cache "
                "mirroring and heartbeat cross here at 100 Gb/s per port: each "
                "dirty write is copied to the partner node before it is "
                "acknowledged, and each node watches the other so the survivor "
                "takes over instantly on a failure. Because drives hang off "
                "this fabric rather than off one node's PCIe bus, any director "
                "can reach any drive — the architectural reason PowerMax "
                "scales out instead of up."
            ),
        ),
        *_node("b", 27),
    ],
    stats=[
        Stat(label="Building block", value="Node pair · 2 directors · 3U"),
        Stat(label="Scale-out", value="1–2 node pairs (2500) · 1–8 (8500)"),
        Stat(label="Fabric", value="InfiniBand Dynamic Fabric · 100 Gb/s"),
        Stat(label="Cache per node pair", value="896 GB – 7.68 TB DRAM"),
        Stat(label="Drives", value="Up to 96 (2500) / 384 (8500) NVMe"),
        Stat(label="Max effective capacity", value="8 PBe (2500) / 18 PBe (8500)"),
        Stat(label="Data reduction", value="5:1 open · 3:1 mainframe (guaranteed)"),
        Stat(label="Hosts", value="Open systems · IBM mainframe · file"),
    ],
    sources=[
        SourceLink(
            label="Dell PowerMax 2500 & 8500 spec sheet",
            url="https://www.delltechnologies.com/asset/en-us/products/storage/technical-support/powermax-2500-8500-spec-sheet.pdf",
        ),
        SourceLink(
            label="Dell PowerMax product page",
            url="https://www.dell.com/en-us/shop/dell-powermax-nvme-storage/sf/powermax",
        ),
    ],
)
