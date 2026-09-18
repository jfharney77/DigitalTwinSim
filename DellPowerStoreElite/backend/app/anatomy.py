"""Cluster-anatomy data: a mixed-generation PowerStore cluster, annotated.

Like the other twins, the map is *data*, not code: regions placed in a
normalized coordinate space the frontend renders as SVG. Geometry is
stylized, drawn from Dell's PowerStore hardware guide and the PowerStore
Elite launch materials — favor a correct mental model over exact
millimetres (project scope guardrail).

The map is deliberately not one box. The top band is a prior-generation
PowerStore appliance (2U, 25 drive slots); the bottom band is the new
PowerStore Elite appliance (3U, 40 low-profile E3 NVMe slots); the thin
band between them is the 200 Gb RDMA cluster interconnect. Drawing the two
generations as peers in one picture *is* the lesson: Elite's launch claim
is that the old array joins the new one's cluster and keeps working — no
forklift, no migration weekend — so the diagram refuses to show a
replacement and shows a partnership instead.

No product photographs ship with this twin (Elite imagery is too new to
carry with clean licensing); the ``photo`` fields stay ``None``, which the
tests treat as acceptable — credit is only required *when* a photo exists.
"""

from __future__ import annotations

from .leveling import L
from .models import ChassisAnatomy, ChassisRegion, SourceLink, Stat

# --- Prior-generation appliance (top band) -----------------------------------

_PRIOR_CPU_DESC = (
    "One controller node of the prior-generation PowerStore. Each node is a "
    "complete Intel Xeon x86 computer running PowerStoreOS; the pair works "
    "active/active. It keeps doing exactly this after the Elite joins — "
    "membership in a mixed-generation cluster asks nothing new of it."
)

_PRIOR_IO_DESC = (
    "The prior array's front-end ports: Fibre Channel, iSCSI, NVMe-oF and "
    "file traffic from hosts. During the modernization these paths never "
    "close — hosts keep talking to the old array while its volumes drain "
    "to the Elite behind the scenes."
)

_PRIOR_BOARD_DESC = (
    "The prior node's system board and PCIe fabric: CPU to drives, drives "
    "to both nodes (every slot is dual-ported). Nothing on this board is "
    "changed by the Elite's arrival, which is precisely the point of "
    "mixed-generation clustering."
)

_PRIOR_PSU_DESC = (
    "The prior node's hot-swap power supply. The old appliance stays on "
    "its own feeds throughout — joining a cluster is a network event, not "
    "an electrical one."
)

# --- Elite appliance (bottom band) -------------------------------------------

_ELITE_FAN_DESC = (
    "The Elite node's fan pack. Airflow runs front to rear across the 40 "
    "E3 drives and through the node canister. Cooling is per node — the "
    "dual-canister design carries over from every PowerStore generation."
)

_ELITE_BBU_DESC = (
    "Battery backup unit. On AC loss it powers the node just long enough "
    "to vault: flush cached writes to the non-volatile NVMe NVRAM slots so "
    "no acknowledged write is ever lost. Seconds of ride-through, not "
    "minutes of UPS — the same vaulting contract as the prior generation."
)

_ELITE_CPU_DESC = (
    "The Elite node's Intel Xeon Scalable processor — up to 50% more cores "
    "than the PowerStore 3200T/5500 class it succeeds. PowerStore Elite's "
    "built-in AI does dynamic core allocation: cores move between block, "
    "file and data-reduction work as the load mix shifts, which is part of "
    "how the platform claims up to 95% less manual tuning."
)

_ELITE_DIMM_DESC = (
    "The Elite node's DDR5 DIMM bank — a generation up from the prior "
    "array's memory, feeding metadata and cache. Metadata Acceleration, "
    "new in Elite, keeps hot metadata structures resident here and is "
    "credited with reads up to 70% faster."
)

_ELITE_MGMT_DESC = (
    "Management and service ports. One PowerStore Manager instance runs "
    "the whole mixed-generation cluster — the old appliance and the new "
    "one appear side by side in the same pane, which is what makes the "
    "join an operation rather than a project."
)

_ELITE_IO_DESC = (
    "The Elite node's front-end connectivity: up to 40 network ports per "
    "appliance — twice the prior generation — at 64 Gb Fibre Channel "
    "(128 Gb-ready) and 100 Gb Ethernet (200/400 Gb-ready). PCIe Gen 5 "
    "lanes feed the ports, which is what makes the 3x network-throughput "
    "claim mechanical rather than aspirational."
)

_ELITE_BOARD_DESC = (
    "The Elite node's system board: a PCIe Gen 5 fabric fanning out from "
    "the CPU to the 40 dual-ported E3 drives, the I/O modules, and the "
    "200 Gb RDMA cluster interconnect. Gen 5 doubles per-lane bandwidth "
    "over the prior generation's Gen 4 — headroom the E3 drives can "
    "actually use."
)

_ELITE_PSU_DESC = (
    "The Elite node's hot-swap power supply. Per-node PSUs on separate "
    "feeds, as on every PowerStore — the availability story is inherited, "
    "not reinvented."
)


ANATOMY = ChassisAnatomy(
    id="powerstore-elite-cluster",
    name="PowerStore Elite mixed-generation cluster",
    vendor="Dell Technologies",
    form_factor="2U prior appliance + 3U Elite appliance",
    generation="PowerStore Elite",
    year=2026,
    width=100,
    height=70,
    overview=L(
        novice=(
            "This picture shows two storage systems, not one — and that is "
            "the whole idea. The top box is a PowerStore array a company "
            "already owns and is already using. The bottom, larger box is "
            "the new PowerStore Elite, announced by Dell in May 2026. "
            "Normally, replacing a storage system means copying everything "
            "to the new box and switching over — a risky, carefully "
            "scheduled event. Elite is built so that never has to happen: "
            "the new box simply joins the old one's cluster, they link up "
            "over the fast connection drawn between them, and the data "
            "drifts across while everyone keeps working. The old box is "
            "not thrown away afterwards — it takes a lighter job, like "
            "holding backup copies. Play the sequence to watch the whole "
            "handover happen with the downtime counter pinned at zero."
        ),
        plain=(
            "Two appliances drawn as peers in one cluster. The top band is "
            "a prior-generation PowerStore (2U, 25 NVMe slots) that is "
            "already in service; the bottom band is the new PowerStore "
            "Elite (3U, 40 low-profile E3 NVMe slots, up to 5.8 PB "
            "effective); the thin band between them is the 200 Gb RDMA "
            "cluster interconnect. Elite's defining feature is "
            "mixed-generation clustering: the old array joins the new "
            "one's cluster live, volumes rebalance across the link while "
            "hosts keep reading and writing, and the old array is then "
            "repurposed rather than retired. The trace's downtime counter "
            "exists to stay at zero."
        ),
        standard=(
            "PowerStore Elite is Dell's 2026 successor to the PowerStore "
            "line, announced at Dell Technologies World 2026: a 3U "
            "appliance on Intel Xeon Scalable processors with DDR5 memory, "
            "a PCIe Gen 5 fabric, 40 low-profile E3 NVMe slots (QLC or "
            "TLC), up to 5.8 PB effective capacity behind a 6:1 data "
            "reduction guarantee, and a 200 Gb RDMA node interconnect. "
            "This map deliberately draws it beside a prior-generation "
            "PowerStore, because Elite's signature capability is "
            "mixed-generation clustering: the existing array joins the "
            "Elite's cluster with no service interruption, workloads "
            "rebalance live across the RDMA mesh, and the older appliance "
            "is repurposed — replication target, snapshot host, test "
            "estate — instead of forklifted out. The dual active-active "
            "controller design, mirrored NVRAM write cache, and "
            "battery-backed vaulting all carry over from the PowerStore "
            "twin this one extends."
        ),
        technical=(
            "3U Elite appliance: dual active-active nodes, Xeon Scalable "
            "(+50% cores vs 3200T/5500 class), DDR5, PCIe Gen 5, 40× "
            "dual-ported E3 NVMe (QLC/TLC), NVMe NVRAM write cache with "
            "BBU vaulting, up to 40 front-end ports at 64 Gb FC "
            "(128 Gb-ready) / 100 GbE (200/400-ready), 200 Gb RDMA "
            "cluster interconnect. Drawn beside a prior-generation 2U "
            "appliance because the trace's subject is the mixed-generation "
            "join: cluster membership first, RDMA mesh, live rebalance, "
            "cutover (3x IOPS/throughput claims realized post-cutover, "
            "70/30 mix basis), then repurposing of the prior array. "
            "Downtime is asserted zero across the entire sequence."
        ),
        expert=(
            "Elite 3U: dual A/A nodes, Xeon Scalable +50% cores, DDR5, "
            "Gen 5 fabric, 40× E3 NVMe, 6:1 DRR guarantee, 5.8 PB "
            "effective, 200 Gb RDMA interconnect, 40 ports @ 64G FC / "
            "100 GbE. Mixed-generation join → mesh → live rebalance → "
            "cutover → repurpose; downtime ≡ 0."
        ),
    ),
    regions=[
        # --- Prior-generation appliance (top band, y 0–20) -------------------
        ChassisRegion(
            id="prior-bay", kind="storage", label="25× NVMe (prior gen)",
            x=0, y=0, w=9, h=20,
            description=(
                "The prior array's drive bay: 25 hot-swap 2.5″ NVMe drives, "
                "each dual-ported to both of its controller nodes. These "
                "drives keep their data and their jobs while the cluster "
                "grows — nothing is pulled, copied offline, or reformatted."
            ),
        ),
        ChassisRegion(
            id="prior-cpu-a", kind="cpu", label="Xeon · prior A",
            x=11, y=0, w=12, h=9, description=_PRIOR_CPU_DESC,
        ),
        ChassisRegion(
            id="prior-io-a", kind="io", label="Front-end ports A",
            x=25, y=0, w=14, h=9, description=_PRIOR_IO_DESC,
        ),
        ChassisRegion(
            id="prior-board-a", kind="board", label="Prior node A board",
            x=41, y=0, w=42, h=9, description=_PRIOR_BOARD_DESC,
        ),
        ChassisRegion(
            id="prior-psu-a", kind="power", label="PSU · prior A",
            x=85, y=0, w=14, h=9, description=_PRIOR_PSU_DESC,
        ),
        ChassisRegion(
            id="prior-cpu-b", kind="cpu", label="Xeon · prior B",
            x=11, y=11, w=12, h=9, description=_PRIOR_CPU_DESC,
        ),
        ChassisRegion(
            id="prior-io-b", kind="io", label="Front-end ports B",
            x=25, y=11, w=14, h=9, description=_PRIOR_IO_DESC,
        ),
        ChassisRegion(
            id="prior-board-b", kind="board", label="Prior node B board",
            x=41, y=11, w=42, h=9, description=_PRIOR_BOARD_DESC,
        ),
        ChassisRegion(
            id="prior-psu-b", kind="power", label="PSU · prior B",
            x=85, y=11, w=14, h=9, description=_PRIOR_PSU_DESC,
        ),
        # --- The cluster interconnect (between the generations) --------------
        ChassisRegion(
            id="cluster-mesh", kind="board", label="200 Gb RDMA cluster mesh",
            x=15, y=24, w=70, h=4,
            description=(
                "The 200 Gb RDMA (remote direct memory access) node "
                "interconnect — the wire the whole modernization travels. "
                "RDMA lets one appliance read and write the other's memory "
                "without a round trip through either CPU, which is what "
                "makes live rebalancing and fast failover between "
                "generations affordable. This link is the only new "
                "plumbing the join requires."
            ),
        ),
        # --- PowerStore Elite appliance (bottom band, y 32–70) ---------------
        ChassisRegion(
            id="elite-bay", kind="storage", label="40× E3 NVMe (Elite)",
            x=0, y=32, w=11, h=30,
            description=(
                "The Elite drive bay: 40 hot-swap low-profile E3 NVMe "
                "slots — the industry-standard EDSFF E3 form factor "
                "replacing 2.5″ drives — taking QLC or TLC flash, "
                "dual-ported to both nodes. Forty slots of dense E3 flash "
                "behind a 6:1 data reduction guarantee is how a single 3U "
                "box reaches 5.8 PB effective."
            ),
        ),
        ChassisRegion(
            id="elite-nvram", kind="nvram", label="NVMe NVRAM",
            x=0, y=63, w=11, h=7,
            description=(
                "NVMe NVRAM write-cache slots. Incoming writes land here, "
                "mirrored across both nodes over the internal link, and are "
                "acknowledged to hosts immediately — destaging to the E3 "
                "capacity drives happens later. Same contract as every "
                "PowerStore generation; only the speeds changed."
            ),
        ),
        ChassisRegion(
            id="elite-fans-a", kind="cooling", label="Fans A",
            x=12.5, y=33, w=5, h=17, description=_ELITE_FAN_DESC,
        ),
        ChassisRegion(
            id="elite-bbu-a", kind="battery", label="BBU A",
            x=18.5, y=33, w=8, h=8, description=_ELITE_BBU_DESC,
        ),
        ChassisRegion(
            id="elite-dimm-a", kind="memory", label="DDR5 A",
            x=18.5, y=42, w=8, h=8, description=_ELITE_DIMM_DESC,
        ),
        ChassisRegion(
            id="elite-cpu-a", kind="cpu", label="Xeon · Elite A",
            x=28, y=33, w=11, h=10, description=_ELITE_CPU_DESC,
        ),
        ChassisRegion(
            id="elite-mgmt-a", kind="management", label="Mgmt A",
            x=28, y=44, w=11, h=6, description=_ELITE_MGMT_DESC,
        ),
        ChassisRegion(
            id="elite-io-a", kind="io", label="40-port front end A",
            x=41, y=33, w=14, h=17, description=_ELITE_IO_DESC,
        ),
        ChassisRegion(
            id="elite-board-a", kind="board", label="Elite node A board",
            x=57, y=33, w=26, h=17, description=_ELITE_BOARD_DESC,
        ),
        ChassisRegion(
            id="elite-psu-a", kind="power", label="PSU A",
            x=85, y=33, w=14, h=17, description=_ELITE_PSU_DESC,
        ),
        ChassisRegion(
            id="elite-fans-b", kind="cooling", label="Fans B",
            x=12.5, y=52, w=5, h=17, description=_ELITE_FAN_DESC,
        ),
        ChassisRegion(
            id="elite-bbu-b", kind="battery", label="BBU B",
            x=18.5, y=52, w=8, h=8, description=_ELITE_BBU_DESC,
        ),
        ChassisRegion(
            id="elite-dimm-b", kind="memory", label="DDR5 B",
            x=18.5, y=61, w=8, h=8, description=_ELITE_DIMM_DESC,
        ),
        ChassisRegion(
            id="elite-cpu-b", kind="cpu", label="Xeon · Elite B",
            x=28, y=52, w=11, h=10, description=_ELITE_CPU_DESC,
        ),
        ChassisRegion(
            id="elite-mgmt-b", kind="management", label="Mgmt B",
            x=28, y=63, w=11, h=6, description=_ELITE_MGMT_DESC,
        ),
        ChassisRegion(
            id="elite-io-b", kind="io", label="40-port front end B",
            x=41, y=52, w=14, h=17, description=_ELITE_IO_DESC,
        ),
        ChassisRegion(
            id="elite-board-b", kind="board", label="Elite node B board",
            x=57, y=52, w=26, h=17, description=_ELITE_BOARD_DESC,
        ),
        ChassisRegion(
            id="elite-psu-b", kind="power", label="PSU B",
            x=85, y=52, w=14, h=17, description=_ELITE_PSU_DESC,
        ),
    ],
    stats=[
        Stat(label="Models", value="Elite 1500 · 5500 · 9500"),
        Stat(label="Form factor", value="3U · 40× E3 NVMe (QLC/TLC)"),
        Stat(label="Effective capacity", value="Up to 5.8 PB per 3U appliance"),
        Stat(label="Data reduction", value="6:1 guaranteed (up from 5:1)"),
        Stat(label="Performance", value="Up to 3x IOPS & network throughput"),
        Stat(label="Front end", value="Up to 40 ports · 64 Gb FC · 100 GbE"),
        Stat(label="Cluster interconnect", value="200 Gb RDMA"),
        Stat(label="Availability", value="Global from July 2026"),
    ],
    photo=None,
    sources=[
        SourceLink(
            label="Dell press release — PowerStore Elite (DTW 2026)",
            url="https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2026~05~dell-technologies-rewrites-the-rules-of-storage-modernization-and-performance-with-dell-powerstore-elite.htm",
        ),
        SourceLink(
            label="TechTarget — Dell pushes in-place storage upgrades in PowerStore Elite",
            url="https://www.techtarget.com/searchstorage/news/366643482/Dell-pushes-in-place-storage-upgrades-in-PowerStore-Elite",
        ),
        SourceLink(
            label="StorageNewsletter — PowerStore Elite at Dell Tech World 2026",
            url="https://www.storagenewsletter.com/2026/05/21/dell-tech-world-2026-dell-rewrites-the-rules-of-storage-modernization-and-performance-with-dell-powerstore-elite/",
        ),
        SourceLink(
            label="DCD — Dell announces PowerStore Elite storage platform",
            url="https://www.datacenterdynamics.com/en/news/dell-announces-powerstore-elite-storage-platform-unveils-18th-generation-of-poweredge-servers/",
        ),
    ],
)
