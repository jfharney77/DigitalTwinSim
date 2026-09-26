"""Cluster-anatomy data: a mixed-generation PowerStore cluster, annotated.

Like the other twins, the map is *data*, not code: regions placed in a
normalized coordinate space the frontend renders as SVG. Geometry is
stylized, drawn from Dell's PowerStore hardware guide and the PowerStore
Elite launch materials — favor a correct mental model over exact
millimetres (project scope guardrail).

The map is deliberately not one box. The top band is a prior-generation
PowerStore appliance (2U, 25 drive slots); the bottom band is the new
PowerStore Elite appliance (3U, 40 low-profile E3 NVMe slots); the thin
band between them is the cluster network that joins the two appliances
(Ethernet through the top-of-rack switches — *not* Elite's 200 Gb RDMA node
interconnect, which joins the two controllers inside the Elite chassis and
is described on the Elite board regions; corrected in the 2026-09
fact-check). Drawing the two
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
    "to vault: copy cached writes out of memory to an on-board M.2 flash "
    "device so no acknowledged write is ever lost. A short ride-through, "
    "not minutes of UPS — the same vaulting contract as the prior "
    "generation, kept a new way. StorageReview's hands-on review reports "
    "two 54 Wh packs per controller on the 5500 and 9500."
)

_ELITE_CPU_DESC = (
    "The Elite node's Intel Xeon Scalable processors — up to 50% more "
    "cores, by Dell's comparison of the new PowerStore 5500 with the "
    "3200T. Dell describes dynamic core allocation that adjusts CPU "
    "resources as workloads fluctuate, and claims the platform's built-in "
    "intelligence cuts manual effort by up to 95% (Dell's internal "
    "analysis against traditional array management)."
)

_ELITE_DIMM_DESC = (
    "The Elite node's DDR5 DIMM bank — a generation up from the prior "
    "array's memory, feeding metadata and cache, and also holding the "
    "battery-backed write cache. Metadata Acceleration arrives with "
    "PowerStoreOS 5.0 for every PowerStore, not only Elite; Dell credits "
    "it with reads up to 70% faster, a figure measured on a PowerStore "
    "500T under a read-only 8 KB workload."
)

_ELITE_MGMT_DESC = (
    "Management and service ports. One PowerStore Manager instance runs "
    "the whole mixed-generation cluster — the old appliance and the new "
    "one appear side by side in the same pane, which is what makes the "
    "join an operation rather than a project."
)

_ELITE_IO_DESC = (
    "The Elite node's front-end connectivity: up to 40 network ports per "
    "appliance, which Dell calls twice the current generation, at 64 Gb "
    "Fibre Channel (128 Gb-ready) and 100 Gb Ethernet (200/400 Gb-ready). "
    "PCIe Gen 5 lanes feed the ports. Dell's 3x throughput claim compares "
    "a 9500 with a 9200T on a 70/30 read/write mix at 1 MB blocks."
)

_ELITE_BOARD_DESC = (
    "The Elite node's system board: a PCIe Gen 5 fabric fanning out from "
    "the CPUs to the 40 dual-ported E3 drives, the I/O modules, and the "
    "200 Gb RDMA (remote direct memory access) node interconnect: the "
    "cable-free link across the midplane to the partner node in the same "
    "chassis, which carries mirrored writes. StorageReview puts the prior "
    "generation's equivalent at 2× 10 GbE and its fabric at PCIe Gen 3, "
    "so Gen 5 is four times the per-lane bandwidth. The 1500 runs the "
    "node link at 100 Gb."
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
            "over the cluster network drawn between them, and the data "
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
            "effective, by Dell's figure); the thin band between them is "
            "the cluster network that joins the appliances. Elite's "
            "defining feature is "
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
            "reduction guarantee, and a 200 Gb RDMA interconnect between "
            "the two controller nodes inside the chassis. "
            "This map deliberately draws it beside a prior-generation "
            "PowerStore, because Elite's signature capability is "
            "mixed-generation clustering: the existing array joins the "
            "Elite's cluster with no service interruption, workloads "
            "rebalance live across the cluster network, and the older appliance "
            "is repurposed — snapshot host, test and development "
            "estate — instead of forklifted out. The dual active-active "
            "controller design, mirrored write cache, and battery-backed "
            "vaulting all carry over from the PowerStore twin this one "
            "extends, though Elite keeps its write cache in battery-backed "
            "DDR5 rather than in NVRAM drives. Performance, capacity and "
            "effort figures on this page are Dell's launch claims."
        ),
        technical=(
            "3U Elite appliance: dual active-active nodes, Xeon Scalable "
            "(+50% cores, 5500 vs 3200T), DDR5, PCIe Gen 5, 40× "
            "dual-ported E3 NVMe (QLC/TLC; 24 bays on the 1500 at "
            "launch), DDR5 software-defined persistent-memory write cache "
            "with BBU vaulting to M.2, up to 40 front-end ports at 64 Gb "
            "FC (128 Gb-ready) / 100 GbE (200/400-ready), 200 Gb RDMA "
            "intra-appliance node interconnect (100 Gb on the 1500). "
            "Drawn beside a prior-generation 2U "
            "appliance because the trace's subject is the mixed-generation "
            "join: cluster membership first, intra-cluster network, live rebalance, "
            "cutover (3x IOPS/throughput claims realized post-cutover, "
            "70/30 mix basis), then repurposing of the prior array. "
            "Downtime is asserted zero across the entire sequence."
        ),
        expert=(
            "Elite 3U: dual A/A nodes, Xeon Scalable +50% cores, DDR5, "
            "Gen 5 fabric, 40× E3 NVMe, 6:1 DRR guarantee, 5.8 PB "
            "effective, 200 Gb RDMA node-to-node (in-chassis), 40 ports @ "
            "64G FC / 100 GbE. Mixed-generation join → cluster net → live rebalance → "
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
            id="cluster-mesh", kind="board", label="Cluster network (Ethernet)",
            x=15, y=24, w=70, h=4,
            description=(
                "The cluster network between the two appliances — the "
                "wire the whole modernization travels. PowerStore "
                "appliances in one cluster reach each other over an "
                "internal Ethernet network that runs through the "
                "top-of-rack switches, and volume migration between "
                "appliances rides it. It is not Elite's 200 Gb RDMA node "
                "interconnect: that link joins the two controllers inside "
                "the Elite chassis and never leaves it. The speed of the "
                "link drawn here is illustrative."
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
                "box reaches Dell's figure of 5.8 PB effective (a 9500 "
                "base chassis at an assumed 6:1). The 1500 opens 24 of the "
                "bays at launch."
            ),
        ),
        ChassisRegion(
            id="elite-nvram", kind="nvram", label="Write cache",
            x=0, y=63, w=11, h=7,
            description=(
                "The Elite's persistent write cache. Incoming writes land "
                "here, mirrored across both nodes over the 200 Gb RDMA "
                "node link, and are acknowledged to hosts immediately — "
                "destaging to the E3 capacity drives happens later. The "
                "contract matches every PowerStore generation, but the "
                "mechanism is new: the prior generation spent up to four "
                "front drive slots on NVRAM drives, and Elite instead "
                "presents battery-backed DDR5 as persistent memory and "
                "copies it to an M.2 flash device on power loss "
                "(software-defined persistent memory, as StorageReview's "
                "review describes it). It is drawn as its own block so "
                "the write path stays visible; physically it lives in the "
                "nodes' memory."
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
        Stat(label="Models", value="PowerStore 1500 · 5500 · 9500"),
        Stat(label="Form factor", value="3U · up to 40× E3 NVMe (QLC/TLC)"),
        Stat(label="Effective capacity", value="Up to 5.8 PB per 3U (Dell, 9500 at 6:1)"),
        Stat(label="Data reduction", value="6:1 guaranteed (up from 5:1)"),
        Stat(label="Performance", value="Up to 3x IOPS & throughput (Dell claim)"),
        Stat(label="Front end", value="Up to 40 ports · 64 Gb FC · 100 GbE"),
        Stat(label="Node interconnect", value="200 Gb RDMA, inside the chassis"),
        Stat(label="Cluster size", value="Up to 4 appliances, mixed generations"),
        Stat(label="Availability", value="Announced for July 2026, global"),
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
            label="StorageReview — Dell PowerStore Gen 3 hands-on (node interconnect, write cache, per-model specs)",
            url="https://www.storagereview.com/review/dell-powerstore-gen-3",
        ),
        SourceLink(
            label="Dell blog — Introducing PowerStore Elite (100 GbE, 2x ports)",
            url="https://www.dell.com/en-us/blog/introducing-powerstore-elite-built-to-lead-in-an-unpredictable-world/",
        ),
        SourceLink(
            label="Dell white paper H18157 — PowerStore clustering and high availability (cluster networks)",
            url="https://www.delltechnologies.com/asset/en-us/products/storage/industry-market/h18157-dell-powerstore-clustering-high-availability.pdf",
        ),
        SourceLink(
            label="DCD — Dell announces PowerStore Elite storage platform",
            url="https://www.datacenterdynamics.com/en/news/dell-announces-powerstore-elite-storage-platform-unveils-18th-generation-of-poweredge-servers/",
        ),
    ],
)
