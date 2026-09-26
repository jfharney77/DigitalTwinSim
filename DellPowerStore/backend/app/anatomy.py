"""Chassis-anatomy data: the PowerStore base enclosure, annotated.

Like the GPU app's die anatomies and the R760's chassis floorplan, the
enclosure is *data*, not code: regions placed in a normalized coordinate
space the frontend renders as SVG. Geometry is stylized, traced from Dell's
own product photos and the PowerStore hardware guide — favor a correct
mental model over exact millimetres (project scope guardrail).

Top-down view: front of the enclosure (the 25 NVMe drive slots) at x=0,
rear (I/O modules and PSUs) at x=100. Node A is the top half, Node B the
bottom half — two mirror-image controller canisters in one 2U box. That
side-by-side layout is a drawing convention: in the real chassis the two 1U
nodes stack vertically, Node A on the bottom and Node B inverted on top
(Dell's "Introduction to the Platform" white paper, H18149).
"""

from __future__ import annotations

from .leveling import L
from .models import ChassisAnatomy, ChassisRegion, Photo, SourceLink, Stat

# --- Product photographs (local files served from frontend/public) ----------

_CREDIT = "Dell Technologies product image"

P_FRONT = Photo(
    url="/powerstore2.webp",
    caption=("The base enclosure from the front: 25 hot-swap 2.5″ NVMe "
             "slots — there are no spinning disks or SAS SSDs in the data "
             "path, every slot speaks PCIe."),
    credit=_CREDIT,
)

P_REAR = Photo(
    url="/powerstore4.webp",
    caption=("Front bezel and rear view of the appliance. The rear is two "
             "stacked 1U controller canisters — Node B on top, inverted, "
             "above Node A — each a complete x86 computer with its own power "
             "supply. The floorplan here lays them side by side instead."),
    credit=_CREDIT,
)

P_NODES = Photo(
    url="/powerstore1.webp",
    caption=("Rear port map: each node exposes an embedded module (mezz "
             "ports, management and service ports) plus two slots for "
             "hot-swap I/O modules."),
    credit=_CREDIT,
)

P_IOMOD = Photo(
    url="/powerstore3.webp",
    caption=("A 100 GbE I/O module mid-service. The orange touch-points mark "
             "everything that can be swapped in the field without powering "
             "the appliance down."),
    credit=_CREDIT,
)


# --- Per-node region descriptions (shared A/B text) --------------------------

_FAN_DESC = (
    "The node's internal fan pack: seven redundant fan modules, of which "
    "the node can lose one and keep running. Airflow runs front to rear: in "
    "over the NVMe drives, through the node canister, out past the PSU. "
    "Cooling is per node — losing one node's fans never takes down the other."
)

_BBU_DESC = (
    "Battery backup unit. On AC loss it does not keep the array running — "
    "it powers the NVRAM drive slots and the node's management controller "
    "just long enough for the NVRAM drives to 'vault': copy their volatile "
    "contents into flash inside the same drive, so no acknowledged write "
    "is ever lost. Each node's BBU backs half of the NVRAM slots. Think "
    "brief ride-through, not minutes of UPS."
)

_CPU_DESC = (
    "The node's Intel Xeon Scalable processors. Each controller node is a "
    "complete x86 server in a canister — dual-socket on the 1200T through "
    "9200T, single-socket on the entry 500T — and the model tiers differ "
    "mainly in core count and DRAM. Dell's spec sheet lists the 5200T at "
    "four CPUs, 96 cores and 1,152 GB of memory per appliance. All data "
    "services — deduplication, compression, RAID math — run here."
)

_DIMM_DESC = (
    "The node's DRAM bank. Used for the operating system, metadata, and "
    "read caching. It is not where a write is made safe: before the host "
    "gets an acknowledgement the write is committed to a mirrored pair of "
    "NVRAM drives in the shared front bay, so a node failure never loses an "
    "acknowledged write. (The PowerStore 500 has no NVRAM drives and caches "
    "writes in node DRAM; this map is the 5200T.)"
)

_EMBEDDED_DESC = (
    "Embedded module: the node's built-in connectivity — a 4-port mezzanine "
    "card (used for the intra-cluster network on multi-appliance setups and "
    "for host traffic) that doesn't consume either I/O module slot."
)

_MGMT_DESC = (
    "Management and service ports, both 1 GbE copper. The management port "
    "carries the PowerStore Manager web UI and REST API; the service port "
    "is a direct-attach path for initial configuration and on-site support. "
    "On the real hardware both sit on the embedded module; they are drawn "
    "as their own block here because management traffic is kept off the "
    "data path entirely."
)

_IOMOD_DESC = (
    "Hot-swap I/O module slot. Field-replaceable cards — 32 Gb Fibre "
    "Channel, 10/25 GbE, or 100 GbE — set the array's front-end personality. "
    "Both nodes must carry matching modules so either node can serve any "
    "host path. Orange handles mark it as customer-serviceable while the "
    "array is online."
)

_BOARD_DESC = (
    "Node system board: the PCIe fabric that fans out from the CPU to the "
    "25 dual-ported NVMe drives, the I/O modules, and the embedded module. "
    "Also hosts the node's boot devices, separate from the data drives: a "
    "pair of internal M.2 SATA modules, a 240 GB primary that holds the "
    "operating system and a 120 GB secondary kept for recovery."
)

_PSU_DESC = (
    "The node's power supply unit, an 1800 W or 2100 W part depending on "
    "model. Each node has its own hot-swap PSU and the pair is redundant: "
    "feed them from separate power rails and the appliance survives a full "
    "rail outage on the surviving supply."
)


def _node(suffix: str, y0: float) -> list[ChassisRegion]:
    """One controller canister; Node A at y0=1, Node B mirrored at y0=25."""
    up = suffix.upper()
    return [
        ChassisRegion(
            id=f"fans-{suffix}", kind="cooling", label=f"Fans {up}",
            x=10.5, y=y0, w=6, h=20, description=_FAN_DESC,
        ),
        ChassisRegion(
            id=f"bbu-{suffix}", kind="battery", label=f"BBU {up}",
            x=17.5, y=y0, w=9, h=9, description=_BBU_DESC,
        ),
        ChassisRegion(
            id=f"dimm-{suffix}", kind="memory", label="DRAM",
            x=17.5, y=y0 + 10, w=9, h=10, description=_DIMM_DESC,
        ),
        ChassisRegion(
            id=f"cpu-{suffix}", kind="cpu", label=f"Xeon · Node {up}",
            x=27.5, y=y0, w=11, h=12, description=_CPU_DESC,
        ),
        ChassisRegion(
            id=f"embedded-{suffix}", kind="io", label="Embedded module",
            x=39.5, y=y0, w=14, h=9, description=_EMBEDDED_DESC,
            photo=P_NODES,
        ),
        ChassisRegion(
            id=f"mgmt-{suffix}", kind="management", label="Mgmt · service",
            x=39.5, y=y0 + 10, w=14, h=10, description=_MGMT_DESC,
            photo=P_NODES,
        ),
        ChassisRegion(
            id=f"iomod-{suffix}1", kind="io", label="I/O module 0",
            x=55.5, y=y0, w=10, h=9.5, description=_IOMOD_DESC,
            photo=P_IOMOD,
        ),
        ChassisRegion(
            id=f"iomod-{suffix}2", kind="io", label="I/O module 1",
            x=55.5, y=y0 + 10.5, w=10, h=9.5, description=_IOMOD_DESC,
            photo=P_IOMOD,
        ),
        ChassisRegion(
            id=f"board-{suffix}", kind="board", label=f"Node {up} board",
            x=67.5, y=y0, w=16, h=20, description=_BOARD_DESC,
        ),
        ChassisRegion(
            id=f"psu-{suffix}", kind="power", label=f"PSU {up}",
            x=85, y=y0, w=14, h=20, description=_PSU_DESC,
        ),
    ]


ANATOMY = ChassisAnatomy(
    id="powerstore",
    name="PowerStore 5200T base enclosure",
    vendor="Dell Technologies",
    form_factor="2U base appliance",
    generation="PowerStore T",
    year=2022,
    width=100,
    height=46,
    overview=L(
        novice=(
            "A storage array is a box whose whole job is to hold data for other "
            "computers. This one has two independent controller units inside, "
            "and both are working at the same time rather than one sitting idle "
            "as a spare. They share the same set of drives, and each drive is "
            "wired to both of them, so if one controller fails the other simply "
            "carries on. Watch the startup sequence and notice that the two "
            "sides come up in step with each other — whenever one lights up, so "
            "does its twin. That symmetry is not decoration; it is what makes "
            "the promise of continuous availability real. There is also a "
            "battery inside, and its job is unusual: if the power fails, it "
            "keeps the write-cache drives powered just long enough for them to "
            "copy what they hold safely into flash, so nothing in flight is "
            "lost."
        ),
        plain=(
            "A 2U all-NVMe array with two active-active controller nodes "
            "sharing one 25-slot, dual-ported drive bay. Both controllers serve "
            "data simultaneously, and each drive is reachable from either, so "
            "losing one node costs capacity to serve rather than access. The "
            "startup sequence shows the pair coming up in lockstep — whenever "
            "one side lights, its twin lights too — which is the visible form "
            "of that guarantee. Writes are acknowledged from a mirrored pair of "
            "NVRAM drives in the shared bay, and battery backup exists to vault that cache to flash "
            "if mains power is lost."
        ),
        standard=(
            "PowerStore is Dell's all-NVMe midrange storage array: a 2U "
            "appliance that serves block storage (Fibre Channel, iSCSI, "
            "NVMe-oF) and file storage (NFS, SMB) from the same box. The "
            "defining design is the pair of controller canisters — Node A and "
            "Node B — two independent x86 computers running PowerStoreOS, a "
            "container-based operating system on embedded Linux. Both nodes are "
            "active at once and every NVMe drive is dual-ported, so either node "
            "can serve any host path; inline deduplication and compression are "
            "always on. Capacity scales up by adding expansion shelves and "
            "scales out by clustering up to four appliances under one "
            "management plane."
        ),
        technical=(
            "2U all-NVMe appliance: dual active-active controller nodes over a "
            "shared 25-slot dual-ported bay. Both nodes serve concurrently; "
            "per-node regions are `-a`/`-b` twins and bring-up is lockstep, "
            "which the engine tests assert. Writes land on a mirrored NVRAM "
            "drive pair in the shared bay before acknowledgement; BBUs exist to vault "
            "cache to flash on AC loss. Phase order is power → boot → drives → "
            "cluster → services → online, with container-based OS boot carrying "
            "the largest dwell."
        ),
        expert=(
            "Dual active-active controllers, shared dual-ported NVMe bay. "
            "Lockstep bring-up asserted on `-a`/`-b` twins. Mirrored NVRAM "
            "write acknowledgement; BBU-backed vault-to-flash on AC loss. OS "
            "container boot holds max dwell."
        ),
    ),
    regions=[
        ChassisRegion(
            id="drive-bay", kind="storage", label="21× NVMe SSD",
            x=0, y=0, w=9, h=37,
            description=(
                "The NVMe drive bay and backplane: up to 25 hot-swap 2.5″ "
                "drives, of which these 21 slots hold capacity SSDs. Every "
                "drive is dual-ported — it has two independent PCIe "
                "connections, one to each node — so both controllers reach "
                "all storage directly, with no SAS expanders or protocol "
                "bridges in the path."
            ),
            photo=P_FRONT,
        ),
        ChassisRegion(
            id="nvram", kind="nvram", label="4× NVMe NVRAM",
            x=0, y=38, w=9, h=8,
            description=(
                "The last four drive slots (21 through 24) hold NVMe NVRAM "
                "devices: small, very-low-latency drives used as the write "
                "cache, installed as mirrored pairs. The 5200T and 9200T "
                "carry four, the 1200T and 3200T two, and the 500T none. "
                "Incoming writes land in NVRAM, mirrored across the pair, "
                "and are acknowledged to the host immediately — the array "
                "destages them to the capacity SSDs later. On a power cut "
                "the node batteries hold these slots up while each drive "
                "saves its contents to its own flash. This is why write "
                "latency stays flat even when the SSDs are busy."
            ),
            photo=P_FRONT,
        ),
        *_node("a", 1),
        ChassisRegion(
            id="interconnect", kind="board", label="Node interconnect",
            x=30, y=22.2, w=40, h=1.6,
            description=(
                "The internal link between the two nodes. Heartbeat and "
                "coordination traffic cross here: each node watches the "
                "other so the survivor can take over all host paths in "
                "seconds if its partner fails. It is not the write mirror "
                "— the protected copy of a write is on the NVRAM drive pair "
                "in the shared bay, which is why a write survives this link "
                "and a whole node going quiet."
            ),
        ),
        *_node("b", 25),
    ],
    stats=[
        Stat(label="Controller nodes", value="2 per appliance · active/active"),
        Stat(label="Drive slots", value="25× 2.5″ NVMe (21 SSD + 4 NVRAM)"),
        Stat(label="Max effective capacity",
             value="~23.6 PBe per cluster (Dell spec sheet, assumes 5:1)"),
        Stat(label="Protocols", value="FC · iSCSI · NVMe-oF · NFS · SMB"),
        Stat(label="Scale-out", value="Up to 4 appliances per cluster"),
        Stat(label="Data reduction",
             value="Always-on inline · Dell 5:1 guarantee on reducible data"),
        Stat(label="Compute (5200T)",
             value="4 Xeon CPUs · 96 cores · 1,152 GB per appliance"),
        Stat(label="Max power (5200T, full)",
             value="~1.39 kW at 26 °C (Dell spec sheet)"),
    ],
    photo=P_REAR,
    sources=[
        SourceLink(
            label="Dell PowerStore Gen 2 spec sheet",
            url="https://www.delltechnologies.com/asset/en-us/products/storage/technical-support/dell-powerstore-gen2-spec-sheet.pdf",
        ),
        SourceLink(
            label="Dell PowerStore: Introduction to the Platform (white paper H18149)",
            url="https://www.delltechnologies.com/asset/en-us/products/storage/industry-market/h18149-dell-powerstore-platform-introduction.pdf",
        ),
        SourceLink(
            label="Dell press release, May 2024: PowerStore 5:1 data reduction guarantee",
            url="https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2024~05~20240521-dell-technologies-bolsters-dell-powerstore-with-storage-performance-resiliency-and-efficiency-advancements.htm",
        ),
        SourceLink(
            label="Dell Future-Proof Program (data reduction guarantee: 5:1 for PowerStore Gen 2)",
            url="https://www.dell.com/en-us/lp/dt/future-proof-program",
        ),
        SourceLink(
            label="Dell PowerStore product page",
            url="https://www.dell.com/en-us/shop/powerstore/sf/power-store",
        ),
    ],
)
