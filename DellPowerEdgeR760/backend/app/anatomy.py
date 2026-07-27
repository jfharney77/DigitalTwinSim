"""Chassis-anatomy data: an annotated floorplan of the PowerEdge R760.

Like the GPU app's anatomy.py, the chassis is data, not code. ``ANATOMY``
describes a top-down view of the R760 with the lid off — the major field-
replaceable blocks placed in a normalized coordinate space the frontend
renders as SVG. Front of the chassis is at x=0 (left), rear at x=100.

Geometry is stylized, traced from Dell's own top-down interior product
photo (frontend/public/r760-interior.webp) and the R760 spec sheet. Per the
project's scope guardrails: favor a correct mental model over exact mm
placement.
"""

from __future__ import annotations

from .leveling import L
from .models import ChassisAnatomy, ChassisRegion, Photo, SourceLink, Stat

P_R760_INTERIOR = Photo(
    url="/r760-interior.webp",
    caption=(
        "Top-down view inside the R760 with the lid and air shroud removed: "
        "drive backplane at the front (left), the six-fan cooling wall, two "
        "CPU heatsinks flanked by DDR5 DIMM banks, and risers plus power "
        "supplies at the rear (right)."
    ),
    credit="Dell Technologies product image",
)

_DIMM_DESC = (
    "A bank of 8 DDR5 DIMM slots. Each of the two processors owns 16 slots "
    "(8 memory channels × 2 slots per channel), 32 slots total — up to 8 TB "
    "with 256 GB RDIMMs. Slots sit parallel to the airflow so the fans can "
    "pull air straight across them; a DIMM only works if its CPU socket is "
    "populated, which is why single-CPU configs halve the usable slots."
)

_CPU_DESC = (
    "One of two LGA-4677 sockets for 4th/5th-generation Intel Xeon Scalable "
    "processors (up to 64 cores, 350 W each), under a passive heatsink — "
    "there is no fan on the CPU itself; the front fan wall moves all the "
    "air. Dell sells the R760 with one or two CPUs; the second socket also "
    "gates half the DIMM slots and some PCIe slots, because the PCIe lanes "
    "come off the processors."
)

_FAN_DESC = (
    "One of six hot-swap fan modules forming a wall behind the drive bay. "
    "Together they pull air front-to-rear across drives, DIMMs, CPUs, and "
    "risers. Speeds are managed by iDRAC from dozens of thermal sensors; a "
    "failed fan can be replaced with the system running, and the rest spin "
    "up to compensate. Higher-power configs (GPUs, 350 W CPUs) require the "
    "high-performance fan variants."
)

_PSU_DESC = (
    "One of two hot-swap power supply units in the rear corner. PSUs range "
    "from 700 W to 2800 W (most 80 PLUS Titanium efficiency) and normally "
    "run 1+1 redundant: either PSU can carry the whole system, each fed "
    "from a separate power feed. As soon as AC is applied the PSU brings up "
    "a small standby rail that powers iDRAC — the server is never fully "
    "'off' while plugged in."
)

ANATOMY = ChassisAnatomy(
    id="r760",
    name="PowerEdge R760",
    vendor="Dell Technologies",
    form_factor="2U rack server",
    generation="16th generation (16G)",
    year=2023,
    width=100,
    height=46,
    overview=L(
        novice=(
            "This follows what happens inside an ordinary rack-mounted server "
            "between plugging it in and it being ready to use — a stretch of a "
            "few minutes that most people never think about. Pressing the power "
            "button is not the beginning. Long before that, a small always-on "
            "computer inside the machine has already woken up and started "
            "checking the hardware. When the main power does come on, the "
            "server spends a surprising amount of its startup time on one task: "
            "memory training, where it tests and tunes the timing of every "
            "memory module until the signals are reliable. Modern memory runs "
            "so fast that the exact electrical timing has to be measured for "
            "each machine, each time. That step is why servers take minutes to "
            "start rather than seconds, and the animation deliberately lingers "
            "there so you can see where the time actually goes."
        ),
        plain=(
            "The power-on sequence of a 2U rack server, from applying mains "
            "power to a running operating system. The order matters more than "
            "people expect: the management controller comes up first on standby "
            "power and checks the hardware before the main rails are even "
            "energized. Then the power-on self-test runs, and the longest "
            "single stage by far is memory training — measuring and tuning the "
            "electrical timing of every memory module, which modern DDR5 speeds "
            "make unavoidable and machine-specific. The trace dwells there on "
            "purpose. Wattages and timings are illustrative rather than "
            "measured."
        ),
        standard=(
            "The PowerEdge R760 is Dell's mainstream two-socket 2U rack server "
            "(16th generation, 2023), built around 4th/5th-generation Intel "
            "Xeon Scalable processors. It is a general-purpose workhorse: up to "
            "128 cores, 8 TB of DDR5 across 32 DIMM slots, 24 NVMe/SAS/SATA "
            "drive bays behind a hardware RAID controller, eight PCIe Gen5 "
            "slots on risers, and dual hot-swap power supplies. Everything a "
            "datacenter tech touches — drives, fans, PSUs, the boot module — is "
            "a hot-swap or tool-less part reachable from the front or rear, and "
            "the whole machine is managed out-of-band by an embedded controller "
            "(iDRAC9) that runs whenever the server is plugged in."
        ),
        technical=(
            "Power-on sequence for a 2U dual-socket server: standby rails, BMC "
            "bring-up and hardware inventory, main power, POST, boot, OS. "
            "Memory training carries the largest dwell cost — per-module DDR5 "
            "timing calibration is machine-specific and unavoidable at current "
            "signalling rates, and it dominates time-to-ready. Region "
            "activation follows the real dependency order rather than the "
            "chassis layout. Illustrative timings."
        ),
        expert=(
            "2U server bring-up: standby → BMC → main rails → POST → boot → OS. "
            "DDR5 training dominates time-to-ready and holds the max dwell. "
            "Phase order encodes dependency, not physical layout."
        ),
    ),
    regions=[
        ChassisRegion(
            id="backplane",
            kind="storage",
            label="24× 2.5″ drive bay · backplane",
            x=0.5, y=0.5, w=7, h=45,
            description=(
                "The front drive bay and its backplane — the circuit board "
                "the drives plug into. This chassis config takes 24 "
                "hot-swap 2.5-inch drives (NVMe, SAS, or SATA); other R760 "
                "builds trade it for 12× 3.5-inch or 16× EDSFF E3.S NVMe. "
                "The backplane routes each bay either to the PERC RAID "
                "controller or directly to CPU PCIe lanes for NVMe, and "
                "lets drives be swapped with the system running."
            ),
        ),
        *[
            ChassisRegion(
                id=f"fan-{i}",
                kind="cooling",
                label=f"Fan {i + 1}",
                x=8.5, y=0.5 + i * 7.6, w=6, h=7.0,
                description=_FAN_DESC,
            )
            for i in range(6)
        ],
        ChassisRegion(
            id="perc",
            kind="storage",
            label="PERC 12",
            x=15.5, y=1, w=3.5, h=13,
            description=(
                "The front-mounted PERC (PowerEdge RAID Controller) slot. "
                "PERC is Dell's hardware RAID card: it sits between the "
                "drive backplane and the CPUs, builds RAID volumes across "
                "the front drives, and adds battery-backed cache so writes "
                "survive a power cut. Mounting it at the front, next to the "
                "backplane, keeps cabling short and frees a rear PCIe slot."
            ),
        ),
        ChassisRegion(
            id="dimm-a1", kind="memory", label="8× DDR5 DIMM",
            x=20, y=1, w=26, h=3.5, description=_DIMM_DESC,
        ),
        ChassisRegion(
            id="cpu1", kind="cpu", label="CPU 1 · Xeon Scalable",
            x=24, y=5.5, w=18, h=13, description=_CPU_DESC,
        ),
        ChassisRegion(
            id="dimm-a2", kind="memory", label="8× DDR5 DIMM",
            x=20, y=19.5, w=26, h=3.5, description=_DIMM_DESC,
        ),
        ChassisRegion(
            id="dimm-b1", kind="memory", label="8× DDR5 DIMM",
            x=20, y=24, w=26, h=3.5, description=_DIMM_DESC,
        ),
        ChassisRegion(
            id="cpu2", kind="cpu", label="CPU 2 · Xeon Scalable",
            x=24, y=28.5, w=18, h=13, description=_CPU_DESC,
        ),
        ChassisRegion(
            id="dimm-b2", kind="memory", label="8× DDR5 DIMM",
            x=20, y=42, w=26, h=3.5, description=_DIMM_DESC,
        ),
        ChassisRegion(
            id="board",
            kind="board",
            label="System board · PCH",
            x=48, y=12, w=12, h=20,
            description=(
                "The system board area around the PCH (Platform Controller "
                "Hub), Intel's companion chipset. It fans out the slower "
                "I/O the CPUs don't handle directly — USB, the SPI flash "
                "that stores UEFI/BIOS firmware, SATA, and the sideband "
                "buses iDRAC uses to read sensors and inventory parts. "
                "During boot, CPU 1 fetches its very first instructions "
                "from flash through this hub."
            ),
        ),
        ChassisRegion(
            id="battery",
            kind="board",
            label="CMOS battery",
            x=48, y=34, w=5, h=4,
            description=(
                "A coin-cell battery that keeps the real-time clock running "
                "and preserves BIOS settings while the server is unplugged. "
                "One of the few parts that is neither hot-swap nor "
                "redundant — a dead cell means the clock and settings reset "
                "on the next cold start."
            ),
        ),
        ChassisRegion(
            id="idrac",
            kind="management",
            label="iDRAC9",
            x=62, y=30, w=12, h=8,
            description=(
                "The iDRAC9 (integrated Dell Remote Access Controller) — a "
                "baseboard management controller, a small always-on ARM "
                "computer with its own OS, network port, and web/Redfish "
                "API. It boots seconds after AC is applied, long before the "
                "host powers on, and gives admins remote console, virtual "
                "media, sensor telemetry, firmware updates, and the power "
                "button itself — no trip to the datacenter required. It is "
                "also the thermal brain that sets fan speeds."
            ),
        ),
        ChassisRegion(
            id="boss",
            kind="storage",
            label="BOSS-N1",
            x=62, y=40, w=12, h=5,
            description=(
                "The BOSS-N1 (Boot Optimized Storage Solution): a rear "
                "hot-swap module holding two M.2 NVMe drives in a hardware "
                "RAID-1 mirror, dedicated to the operating system or "
                "hypervisor. Booting from BOSS keeps all 24 front bays free "
                "for data and means a failed boot drive is swapped from the "
                "rear without opening the lid."
            ),
        ),
        ChassisRegion(
            id="riser1",
            kind="expansion",
            label="Riser 1 · PCIe Gen5",
            x=76, y=1, w=12, h=16,
            description=(
                "A PCIe riser: a small board that turns motherboard slots "
                "90° so full-size cards lie flat in the 2U chassis. Riser "
                "configurations give the R760 up to eight PCIe Gen5 slots "
                "for NICs, HBAs, and up to two double-wide 350 W GPUs. "
                "Which slots exist — and how many lanes each gets — depends "
                "on the riser config ordered and on whether CPU 2 is "
                "populated."
            ),
        ),
        ChassisRegion(
            id="riser2",
            kind="expansion",
            label="Riser 2 · PCIe Gen5",
            x=76, y=18, w=12, h=16,
            description=(
                "Second PCIe riser bay. Like Riser 1, it carries Gen5 x16 "
                "slots wired to the CPUs' PCIe lanes; heavier riser configs "
                "add Risers 3 and 4 for the full eight-slot layout. Cards "
                "on Riser 2 typically hang off CPU 2, so single-CPU builds "
                "lose these slots."
            ),
        ),
        ChassisRegion(
            id="ocp",
            kind="expansion",
            label="OCP 3.0 NIC",
            x=76, y=40, w=12, h=5,
            description=(
                "The OCP 3.0 slot — a standardized mezzanine slot from the "
                "Open Compute Project, dedicated to the primary network "
                "card. The NIC slides in from the rear on rails without "
                "tools and without consuming a PCIe riser slot. Options "
                "range from quad-port 1 GbE to dual-port 100 GbE."
            ),
        ),
        ChassisRegion(
            id="pdb",
            kind="power",
            label="Power distribution",
            x=90, y=24, w=9, h=8,
            description=(
                "The power distribution board: takes the PSUs' 12 V output "
                "and fans it out to the system board, backplane, fans, and "
                "risers. It also carries the standby rail that keeps iDRAC "
                "alive, and the circuitry that sequences the main rails up "
                "in order when the host is told to power on."
            ),
        ),
        ChassisRegion(
            id="psu1", kind="power", label="PSU 1",
            x=90, y=1, w=9, h=10, description=_PSU_DESC,
        ),
        ChassisRegion(
            id="psu2", kind="power", label="PSU 2",
            x=90, y=12, w=9, h=10, description=_PSU_DESC,
        ),
    ],
    stats=[
        Stat(label="Processors", value="1–2× Intel Xeon Scalable, ≤64 cores ea."),
        Stat(label="Memory", value="32 DIMM slots · ≤8 TB DDR5"),
        Stat(label="Drive bays", value="≤24× 2.5″ NVMe/SAS/SATA"),
        Stat(label="PCIe", value="≤8 slots, Gen5, on risers"),
        Stat(label="Power", value="2× hot-swap PSU · 700–2800 W"),
        Stat(label="Management", value="iDRAC9, always-on"),
    ],
    sources=[
        SourceLink(
            label="Dell PowerEdge R760 spec sheet (PDF)",
            url="https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-r760-spec-sheet.pdf",
        ),
        SourceLink(
            label="Dell PowerEdge R760 product page",
            url="https://www.dell.com/en-us/shop/servers-storage-and-networking/new-poweredge-r760-rack-server/spd/poweredge-r760",
        ),
    ],
    photo=P_R760_INTERIOR,
)
