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

_DIMM_DESC = L(
    novice=(
        "A row of 8 slots for memory sticks. Memory is where the server keeps "
        "whatever it is working on right now; these sticks are the server "
        "version of the memory in a laptop, only there are far more of them. "
        "Each of the two processors owns 16 slots, so a full machine has 32, "
        "and with the largest sticks available that comes to 8 TB of memory. "
        "The slots line up with the direction the fans blow, so air runs "
        "straight along them. A stick only works if the processor next to it "
        "is fitted — that is why a server bought with one processor can only "
        "use half its memory slots."
    ),
    plain=(
        "A bank of 8 memory-module slots (DIMMs, the sticks that hold the "
        "server's working memory — DDR5 is the current generation). Each of "
        "the two processors owns 16 slots, 32 in total, which comes to 8 TB "
        "with the largest 256 GB modules. The slots sit parallel to the "
        "airflow so the fans pull air straight across them; a module only "
        "works if its processor socket is populated, which is why single-"
        "processor builds halve the usable slots."
    ),
    standard=(
        "A bank of 8 DDR5 DIMM slots. Each of the two processors owns 16 slots "
        "(8 memory channels × 2 slots per channel), 32 slots total — up to 8 TB "
        "with 256 GB RDIMMs. Slots sit parallel to the airflow so the fans can "
        "pull air straight across them; a DIMM only works if its CPU socket is "
        "populated, which is why single-CPU configs halve the usable slots."
    ),
)

_CPU_DESC = L(
    novice=(
        "One of the two processor sockets — the places the main chips that do "
        "the computing sit. Each chip can hold up to 64 separate processing "
        "cores and turn 350 watts of electricity into heat, so a solid block "
        "of finned metal sits on top to carry that heat away. There is no fan "
        "on the chip itself: the wall of fans at the front of the machine "
        "moves all the air. A server can be bought with one chip or two, and "
        "the second one brings half the memory slots and some of the card "
        "slots with it, because those connections come out of the chip."
    ),
    plain=(
        "One of two sockets for an Intel Xeon Scalable server processor (up to "
        "64 cores, 350 W each), under a passive heatsink — a finned block with "
        "no fan of its own, because the front fan wall moves all the air. Dell "
        "sells the R760 with one or two processors; the second socket also "
        "gates half the memory slots and some of the expansion-card slots, "
        "because those connections come off the processor."
    ),
    standard=(
        "One of two LGA-4677 sockets for 4th/5th-generation Intel Xeon Scalable "
        "processors (up to 64 cores, 350 W each), under a passive heatsink — "
        "there is no fan on the CPU itself; the front fan wall moves all the "
        "air. Dell sells the R760 with one or two CPUs; the second socket also "
        "gates half the DIMM slots and some PCIe slots, because the PCIe lanes "
        "come off the processors."
    ),
)

_FAN_DESC = L(
    novice=(
        "One of six fan modules standing in a row behind the drive bay, like a "
        "wall. Together they pull air in at the front of the machine and push "
        "it out at the back, over the drives, the memory, the processors and "
        "the cards. The small management computer inside the server decides "
        "how fast they spin, using readings from dozens of temperature "
        "sensors. A fan can be pulled out and replaced while the server keeps "
        "running, and the others speed up to cover for it. Machines with "
        "hotter parts inside need the stronger version of these fans."
    ),
    plain=(
        "One of six replaceable fan modules forming a wall behind the drive "
        "bay. Together they pull air front-to-rear across the drives, memory, "
        "processors and cards. The management controller sets their speed from "
        "dozens of thermal sensors; a failed fan can be swapped with the "
        "system running, and the rest spin up to compensate. Higher-power "
        "builds (graphics cards, 350 W processors) require the "
        "high-performance fan variants."
    ),
    standard=(
        "One of six hot-swap fan modules forming a wall behind the drive bay. "
        "Together they pull air front-to-rear across drives, DIMMs, CPUs, and "
        "risers. Speeds are managed by iDRAC from dozens of thermal sensors; a "
        "failed fan can be replaced with the system running, and the rest spin "
        "up to compensate. Higher-power configs (GPUs, 350 W CPUs) require the "
        "high-performance fan variants."
    ),
)

_PSU_DESC = L(
    novice=(
        "One of the two power supplies in the back corner — the boxes that "
        "convert the electricity from the wall into the low voltage the parts "
        "inside actually use. They come in sizes from 700 to 3200 watts. The "
        "server normally runs with two, each plugged into a different circuit, "
        "and either one on its own can carry the whole machine — so losing a "
        "power supply, or a wall circuit, does not stop the server. The moment "
        "a cord is plugged in, the supply starts sending a small trickle of "
        "power to the always-on management computer, which is why a "
        "plugged-in server is never completely off."
    ),
    plain=(
        "One of two replaceable power supply units in the rear corner. They "
        "range from 700 W to 3200 W and carry an efficiency rating (80 PLUS "
        "Platinum or Titanium). Normally both are fitted and either one can "
        "carry the whole system on its own, each fed from a separate power "
        "feed. As soon as mains power is applied the supply brings up a small "
        "standby feed that powers the management controller — the server is "
        "never fully 'off' while plugged in."
    ),
    standard=(
        "One of two hot-swap power supply units in the rear corner. PSUs range "
        "from 700 W to 3200 W (80 PLUS Platinum or Titanium efficiency) and "
        "normally run 1+1 redundant: either PSU can carry the whole system, each fed "
        "from a separate power feed. As soon as AC is applied the PSU brings up "
        "a small standby rail that powers iDRAC — the server is never fully "
        "'off' while plugged in."
    ),
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
            "drive bays behind a hardware RAID controller, up to eight PCIe "
            "slots on risers (a mix of Gen4 and Gen5), and dual hot-swap power "
            "supplies. Everything a "
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
            description=L(
                novice=(
                    "The row of drive slots across the front of the machine, and "
                    "the circuit board behind them that the drives plug into. "
                    "Drives are where the server keeps data when the power is "
                    "off. This version of the chassis holds 24 small drives; "
                    "other versions trade them for 12 larger ones, or for 16 of "
                    "a newer ruler-shaped kind. Each slot is wired either to the "
                    "storage controller card or straight to a processor, "
                    "depending on the type of drive. Drives slide in and out "
                    "from the front while the server keeps running."
                ),
                plain=(
                    "The front drive bay and its backplane — the circuit board "
                    "the drives plug into. This chassis configuration takes 24 "
                    "removable 2.5-inch drives of several types (NVMe, SAS or "
                    "SATA); other R760 builds trade it for 12 larger 3.5-inch "
                    "drives or 16 of the newer E3.S NVMe format. The backplane "
                    "routes each bay either to the RAID controller card or "
                    "directly to the processors, and lets drives be swapped "
                    "with the system running."
                ),
                standard=(
                    "The front drive bay and its backplane — the circuit board "
                    "the drives plug into. This chassis config takes 24 "
                    "hot-swap 2.5-inch drives (NVMe, SAS, or SATA); other R760 "
                    "builds trade it for 12× 3.5-inch or 16× EDSFF E3.S NVMe. "
                    "The backplane routes each bay either to the PERC RAID "
                    "controller or directly to CPU PCIe lanes for NVMe, and "
                    "lets drives be swapped with the system running."
                ),
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
            description=L(
                novice=(
                    "The slot at the front of the machine for the storage "
                    "controller card — Dell calls it PERC, short for PowerEdge "
                    "RAID Controller. It sits between the drives and the "
                    "processors and does two jobs. It joins several drives "
                    "together so they behave as one, in a way that survives a "
                    "drive dying (that joining-together is what RAID means). "
                    "And it holds a small amount of memory with its own battery, "
                    "so anything the server had just asked it to write is still "
                    "there after a power cut. Putting the card at the front, "
                    "next to the drives, keeps the cables short and leaves a "
                    "card slot free at the back."
                ),
                plain=(
                    "The front-mounted slot for the PERC card (PowerEdge RAID "
                    "Controller), Dell's storage controller. It sits between the "
                    "drive backplane and the processors, groups the front drives "
                    "into RAID sets — arrangements that keep the data readable "
                    "when a drive fails — and carries a battery-backed cache so "
                    "writes in flight survive a power cut. Mounting it at the "
                    "front, next to the backplane, keeps cabling short and frees "
                    "an expansion slot at the rear."
                ),
                standard=(
                    "The front-mounted PERC (PowerEdge RAID Controller) slot. "
                    "PERC is Dell's hardware RAID card: it sits between the "
                    "drive backplane and the CPUs, builds RAID volumes across "
                    "the front drives, and adds battery-backed cache so writes "
                    "survive a power cut. Mounting it at the front, next to the "
                    "backplane, keeps cabling short and frees a rear PCIe slot."
                ),
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
            description=L(
                novice=(
                    "The part of the main circuit board around a helper chip "
                    "that Intel supplies alongside the processors. The "
                    "processors handle the fast connections themselves; this "
                    "chip handles the slower ones — the USB ports, the older "
                    "kind of drive connection, the small memory chip that "
                    "stores the software the server runs before it has an "
                    "operating system, and the quiet little wires the "
                    "management computer uses to read temperatures and ask "
                    "each part what it is. When the server starts, the first "
                    "processor fetches its very first instructions through "
                    "this chip."
                ),
                plain=(
                    "The system-board area around the Platform Controller Hub, "
                    "Intel's companion chip to the processors. It fans out the "
                    "slower connections the processors do not handle directly — "
                    "USB, SATA drive ports, the small flash chip holding the "
                    "firmware the server boots from (its UEFI/BIOS), and the "
                    "low-speed side channels the management controller uses to "
                    "read sensors and inventory parts. During start-up, "
                    "processor 1 fetches its very first instructions from that "
                    "flash chip through this hub."
                ),
                standard=(
                    "The system board area around the PCH (Platform Controller "
                    "Hub), Intel's companion chipset. It fans out the slower "
                    "I/O the CPUs don't handle directly — USB, the SPI flash "
                    "that stores UEFI/BIOS firmware, SATA, and the sideband "
                    "buses iDRAC uses to read sensors and inventory parts. "
                    "During boot, CPU 1 fetches its very first instructions "
                    "from flash through this hub."
                ),
            ),
        ),
        ChassisRegion(
            id="battery",
            kind="board",
            label="CMOS battery",
            x=48, y=34, w=5, h=4,
            description=L(
                novice=(
                    "A watch battery on the main board. It keeps the clock "
                    "ticking and remembers the machine's settings while the "
                    "server is unplugged and has no other power. It is one of "
                    "the few parts here that has no spare and cannot be changed "
                    "while the server runs — when it finally goes flat, the "
                    "clock and the settings come back to their defaults on the "
                    "next cold start."
                ),
                plain=(
                    "A coin-cell battery that keeps the clock running and "
                    "preserves the machine's firmware settings while the server "
                    "is unplugged. One of the few parts with no spare and no "
                    "swapping it while the system runs — a dead cell means the "
                    "clock and settings reset on the next cold start."
                ),
                standard=(
                    "A coin-cell battery that keeps the real-time clock running "
                    "and preserves BIOS settings while the server is unplugged. "
                    "One of the few parts that is neither hot-swap nor "
                    "redundant — a dead cell means the clock and settings reset "
                    "on the next cold start."
                ),
            ),
        ),
        ChassisRegion(
            id="idrac",
            kind="management",
            label="iDRAC9",
            x=62, y=30, w=12, h=8,
            description=L(
                novice=(
                    "iDRAC9 — a whole second, much smaller computer living "
                    "inside the server, whose only job is to look after the "
                    "server. It has its own chip, its own software and its own "
                    "network socket, and it starts a few seconds after the "
                    "power cords go in, long before the server itself turns on. "
                    "Through it, someone far away can see the screen, press the "
                    "power button, mount a disc image to install from, read "
                    "every temperature, and update the server's low-level "
                    "software — none of which needs anyone to walk into the "
                    "room. It is also what decides how fast the fans spin."
                ),
                plain=(
                    "iDRAC9 (integrated Dell Remote Access Controller) — the "
                    "server's management controller: a small always-on computer "
                    "with its own processor, operating system, network port and "
                    "web interface. It starts seconds after mains power is "
                    "applied, long before the main server does, and gives "
                    "administrators a remote screen and keyboard, the ability to "
                    "attach installation media over the network, sensor "
                    "readings, firmware updates and the power button itself — "
                    "without a trip to the datacenter. It is also the thermal "
                    "brain that sets fan speeds."
                ),
                standard=(
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
        ),
        ChassisRegion(
            id="boss",
            kind="storage",
            label="BOSS-N1",
            x=62, y=40, w=12, h=5,
            description=L(
                novice=(
                    "A small tray at the back of the server holding two little "
                    "drives — the flat, gum-stick kind used in laptops. Their "
                    "job is to hold the server's own operating system, and "
                    "nothing else. The two drives are kept as identical copies "
                    "of each other, so if one dies the server carries on from "
                    "the other. Dell calls the tray BOSS, for Boot Optimized "
                    "Storage Solution, because booting is all it is for. Keeping "
                    "the operating system here leaves all 24 front slots for "
                    "actual data, and a failed drive is pulled out from the "
                    "back without opening the machine."
                ),
                plain=(
                    "The BOSS-N1 module (Boot Optimized Storage Solution): a "
                    "removable tray at the rear holding two small M.2 flash "
                    "drives — the compact format used in laptops — kept as an "
                    "exact mirror of each other, so either one alone can keep "
                    "the server running. It is dedicated to the operating "
                    "system or hypervisor. Booting from BOSS keeps all 24 front "
                    "bays free for data and means a failed boot drive is "
                    "swapped from the rear without opening the lid."
                ),
                standard=(
                    "The BOSS-N1 (Boot Optimized Storage Solution): a rear "
                    "hot-swap module holding two M.2 NVMe drives in a hardware "
                    "RAID-1 mirror, dedicated to the operating system or "
                    "hypervisor. Booting from BOSS keeps all 24 front bays free "
                    "for data and means a failed boot drive is swapped from the "
                    "rear without opening the lid."
                ),
            ),
        ),
        ChassisRegion(
            id="riser1",
            kind="expansion",
            label="Riser 1 · PCIe Gen5",
            x=76, y=1, w=12, h=16,
            description=L(
                novice=(
                    "A riser: a small board that turns the card slots on the "
                    "main board through a right angle, so full-height expansion "
                    "cards can lie flat inside a machine only two rack units "
                    "tall. Depending on which riser arrangement was ordered, "
                    "the server ends up with as many as eight card slots, some "
                    "of them a generation faster than others. Cards that go "
                    "here are things like network cards, extra storage "
                    "adapters, and up to two large graphics cards. Which slots "
                    "exist at all, and how much bandwidth each one gets, "
                    "depends on the riser ordered and on whether the second "
                    "processor is fitted — the connections come out of the "
                    "processors."
                ),
                plain=(
                    "A riser board: it turns the main board's expansion slots "
                    "90° so full-size cards lie flat in this 2U chassis. Riser "
                    "configurations give the R760 up to eight expansion slots — "
                    "a mix of PCIe generation 4 and 5, with at most four of them "
                    "Gen5 — for network cards, storage adapters and up to two "
                    "double-width 350 W graphics cards. Which slots exist, and "
                    "how much bandwidth each gets, depends on the riser ordered "
                    "and on whether processor 2 is populated."
                ),
                standard=(
                    "A PCIe riser: a small board that turns motherboard slots "
                    "90° so full-size cards lie flat in the 2U chassis. Riser "
                    "configurations give the R760 up to eight PCIe slots — a "
                    "mix of Gen4 and Gen5, with at most four of them Gen5 — "
                    "for NICs, HBAs, and up to two double-wide 350 W GPUs. "
                    "Which slots exist — and how many lanes each gets — depends "
                    "on the riser config ordered and on whether CPU 2 is "
                    "populated."
                ),
            ),
        ),
        ChassisRegion(
            id="riser2",
            kind="expansion",
            label="Riser 2 · PCIe Gen5",
            x=76, y=18, w=12, h=16,
            description=L(
                novice=(
                    "The second riser bay. Like the first, it holds expansion "
                    "card slots of two widths, wired back to the processors; "
                    "larger arrangements add a third and a fourth riser to "
                    "reach the full eight slots. The cards here are normally "
                    "wired to the second processor, so a server bought with "
                    "only one processor does not get these slots at all."
                ),
                plain=(
                    "The second riser bay. Like Riser 1, it carries expansion "
                    "slots in two widths (PCIe generation 4 or 5, depending on "
                    "the riser ordered) wired to the processors; heavier riser "
                    "configurations add Risers 3 and 4 for the full eight-slot "
                    "layout. Cards on Riser 2 normally hang off processor 2, so "
                    "single-processor builds lose these slots."
                ),
                standard=(
                    "Second PCIe riser bay. Like Riser 1, it carries x8/x16 "
                    "slots (Gen4 or Gen5, depending on the riser ordered) wired "
                    "to the CPUs' PCIe lanes; heavier riser configs "
                    "add Risers 3 and 4 for the full eight-slot layout. Cards "
                    "on Riser 2 typically hang off CPU 2, so single-CPU builds "
                    "lose these slots."
                ),
            ),
        ),
        ChassisRegion(
            id="ocp",
            kind="expansion",
            label="OCP 3.0 NIC",
            x=76, y=40, w=12, h=5,
            description=L(
                novice=(
                    "A slot reserved for the server's main network card. Its "
                    "shape is not Dell's invention: it follows a common design "
                    "published by the Open Compute Project, so the same card "
                    "fits servers from several makers. The card slides in from "
                    "the back on rails, with no tools and without using up one "
                    "of the ordinary card slots. The choice of card runs from "
                    "four slower network ports to two very fast ones."
                ),
                plain=(
                    "The OCP 3.0 slot — a standardized slot defined by the Open "
                    "Compute Project, an industry group, and reserved for the "
                    "main network card. The card slides in from the rear on "
                    "rails without tools and without consuming one of the riser "
                    "expansion slots. Options run from four 1-gigabit ports to "
                    "two 100-gigabit ones."
                ),
                standard=(
                    "The OCP 3.0 slot — a standardized mezzanine slot from the "
                    "Open Compute Project, dedicated to the primary network "
                    "card. The NIC slides in from the rear on rails without "
                    "tools and without consuming a PCIe riser slot. Options "
                    "range from quad-port 1 GbE to dual-port 100 GbE."
                ),
            ),
        ),
        ChassisRegion(
            id="pdb",
            kind="power",
            label="Power distribution",
            x=90, y=24, w=9, h=8,
            description=L(
                novice=(
                    "The board that shares out power. It takes the low voltage "
                    "coming from the two power supplies and splits it between "
                    "the main board, the drives, the fans and the card slots. "
                    "It also carries the small trickle of power that keeps the "
                    "management computer awake while the rest of the server is "
                    "off, and it holds the circuitry that switches the main "
                    "supplies on in the right order when the server is told to "
                    "start — parts inside a server have to be powered in "
                    "sequence, not all at once."
                ),
                plain=(
                    "The power distribution board: it takes the 12-volt output "
                    "of the power supplies and fans it out to the main board, "
                    "the drive backplane, the fans and the risers. It also "
                    "carries the standby feed that keeps the management "
                    "controller alive, and the circuitry that brings the main "
                    "supplies up in the correct order when the server is told "
                    "to power on."
                ),
                standard=(
                    "The power distribution board: takes the PSUs' 12 V output "
                    "and fans it out to the system board, backplane, fans, and "
                    "risers. It also carries the standby rail that keeps iDRAC "
                    "alive, and the circuitry that sequences the main rails up "
                    "in order when the host is told to power on."
                ),
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
        Stat(label="PCIe", value="≤8 slots, Gen4/Gen5, on risers"),
        Stat(label="Power", value="2× hot-swap PSU · 700–3200 W"),
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
        SourceLink(
            label="Dell PowerEdge server GPU matrix (PDF) — GPUs supported per platform",
            url="https://www.delltechnologies.com/asset/en-us/products/servers/briefs-summaries/poweredge-server-gpu-matrix.pdf",
        ),
        SourceLink(
            label="Dell OpenManage licensing guide (PDF) — iDRAC9 tiers and defaults",
            url="https://www.delltechnologies.com/asset/en-us/products/servers/industry-market/openmanage-portfolio-software-licensing-guide.pdf",
        ),
        SourceLink(
            label="Intel Xeon Silver 4410Y specifications",
            url="https://www.intel.com/content/www/us/en/products/sku/232376/intel-xeon-silver-4410y-processor-30m-cache-2-00-ghz/specifications.html",
        ),
        SourceLink(
            label="Intel Xeon Gold 6548Y+ specifications",
            url="https://www.intel.com/content/www/us/en/products/sku/237564/intel-xeon-gold-6548y-processor-60m-cache-2-50-ghz/specifications.html",
        ),
    ],
    photo=P_R760_INTERIOR,
)
