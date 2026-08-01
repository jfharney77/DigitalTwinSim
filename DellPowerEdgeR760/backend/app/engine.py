"""Pure power-on sequence engine for the PowerEdge R760.

``simulate()`` returns the deterministic trace of what happens inside the
server from the moment the AC cords are connected until the operating system
is running. Same purity rule as the GPU app's engine: no FastAPI, no IO, no
timers — the frontend owns the playback clock, and each ``PowerOnState`` is
plain data the renderer consumes. ``cycle_cost`` marks the long stages
(memory training, drive spin-up) so the UI dwells on them.

Timing (``elapsed_seconds``) and power draw are illustrative but plausible
for a dual-socket 2U machine; per the project's scope guardrails, favor a
correct mental model over measured numbers.
"""

from __future__ import annotations

from .leveling import L
from .models import PowerOnState

_FANS = [f"fan-{i}" for i in range(6)]
_DIMMS = ["dimm-a1", "dimm-a2", "dimm-b1", "dimm-b2"]


def simulate() -> list[PowerOnState]:
    """The R760's journey from AC plug-in to a running OS, as pure data."""
    return [
        PowerOnState(
            step=0,
            phase="off",
            label="AC connected",
            description=L(
                novice=(
                    "Both power cords are plugged in. To all appearances nothing "
                    "happens — the fans are still, the lights are off, and the "
                    "machine draws no measurable power. But the power supplies have "
                    "noticed that there is voltage at the wall, and they are about "
                    "to wake the one part of this server that never really sleeps."
                ),
                plain=(
                    "Both power cords are connected. Nothing appears to happen — "
                    "fans still, LEDs dark, no measurable draw. But the power "
                    "supplies have detected line voltage and are about to wake the "
                    "one subsystem that never truly sleeps."
                ),
                standard=(
                    "Both power cords are plugged in. Nothing appears to happen "
                    "— fans are still, LEDs dark, zero measurable draw. But the "
                    "power supplies have detected line voltage and are about to "
                    "wake the one subsystem that never really sleeps."
                ),
                technical=(
                    "AC present at both PSUs. No fans, no LEDs, negligible draw — "
                    "but line voltage is detected and the management domain is "
                    "about to come up."
                ),
                expert=(
                    "AC present. Zero apparent activity; PSUs detect line voltage "
                    "and the management domain wakes."
                ),
            ),
            active_regions=[],
            power_watts=0,
            fan_percent=0,
            elapsed_seconds=0,
        ),
        PowerOnState(
            step=1,
            phase="standby",
            label="Standby rail up",
            description=L(
                novice=(
                    "Each power supply brings up a small trickle of standby power — "
                    "a few watts, routed through a distribution board. The main "
                    "power that feeds the processors and drives stays off. This "
                    "trickle is the reason a plugged-in server is never truly "
                    "switched off: it powers the management computer, the power "
                    "button circuit, and the ability to be woken over the network."
                ),
                plain=(
                    "Each PSU brings up a small 12 V standby rail — a trickle feed "
                    "of a few watts, routed through the power distribution board. "
                    "The main rails that feed CPUs and drives stay off. This "
                    "standby rail is why a plugged-in server is never truly off: it "
                    "powers the management controller, the power button circuit, "
                    "and wake-on-LAN."
                ),
                standard=(
                    "Each PSU brings up a small 12 V standby rail — a trickle "
                    "feed, a few watts, routed through the power distribution "
                    "board. The main rails that feed CPUs and drives stay off. "
                    "This standby rail is why a plugged-in server is never "
                    "truly off: it powers the management controller, the power "
                    "button circuit, and wake-on-LAN."
                ),
                technical=(
                    "PSUs bring up the 12 V standby rail through the PDB — a few "
                    "watts. Main rails remain down. Standby is what makes a "
                    "plugged-in server never genuinely off: it feeds the BMC, the "
                    "power button circuit, and wake-on-LAN."
                ),
                expert=(
                    "12 V standby up through the PDB, main rails down. Standby "
                    "feeds BMC, power button circuit, WOL."
                ),
            ),
            active_regions=["psu1", "psu2", "pdb"],
            power_watts=15,
            fan_percent=0,
            elapsed_seconds=2,
        ),
        PowerOnState(
            step=2,
            phase="bmc",
            label="iDRAC boots",
            description=L(
                novice=(
                    "That standby power wakes the management controller — a small "
                    "always-on computer with its own storage, its own operating "
                    "system, and its own network port, sitting inside the server. "
                    "It starts up in under a minute. The server itself is still "
                    "'off', and yet you can already log into that controller's web "
                    "console over the network from anywhere."
                ),
                plain=(
                    "The standby rail wakes iDRAC9, the baseboard management "
                    "controller — a small always-on ARM computer with its own flash "
                    "storage, operating system, and network port. It boots its "
                    "embedded Linux in under a minute. The host server is still "
                    "'off', yet you can already log into iDRAC's web console over "
                    "the network."
                ),
                standard=(
                    "The standby rail wakes iDRAC9 (integrated Dell Remote "
                    "Access Controller), the baseboard management controller — "
                    "a small always-on ARM computer with its own flash storage, "
                    "operating system, and network port. It boots its embedded "
                    "Linux in under a minute. The host server is still 'off', "
                    "yet you can already log into iDRAC's web console over the "
                    "network."
                ),
                technical=(
                    "Standby wakes iDRAC9 — an always-on ARM SoC with dedicated "
                    "flash, OS, and NIC. Embedded Linux up in under a minute. The "
                    "host remains powered off while its management console is "
                    "already network-reachable."
                ),
                expert=(
                    "iDRAC9 up on standby: dedicated SoC, flash, OS, NIC. Console "
                    "reachable with the host still off."
                ),
            ),
            active_regions=["idrac"],
            power_watts=20,
            fan_percent=0,
            elapsed_seconds=10,
            cycle_cost=3,
        ),
        PowerOnState(
            step=3,
            phase="bmc",
            label="Hardware inventory",
            description=L(
                novice=(
                    "Before the server ever powers on, the management controller "
                    "walks the whole chassis over low-speed side channels that work "
                    "without the main processors: it reads every memory module's "
                    "serial number, asks the drive backplane what is installed, "
                    "checks both power supplies' capacity and firmware, and maps "
                    "the temperature sensors it will later use to drive the fans."
                ),
                plain=(
                    "Before the host ever powers on, iDRAC walks the chassis over "
                    "sideband buses — I2C and NC-SI, low-speed management links "
                    "that work without the CPUs. It reads every DIMM's serial "
                    "number, queries the drive backplane, checks both PSUs' "
                    "capacity and firmware, and maps the thermal sensors it will "
                    "later use to drive the fans."
                ),
                standard=(
                    "Before the host ever powers on, iDRAC walks the chassis "
                    "over sideband buses (I2C and NC-SI — low-speed management "
                    "links that work without the CPUs): it reads every DIMM's "
                    "serial number, queries the drive backplane, checks both "
                    "PSUs' capacity and firmware, and maps the thermal sensors "
                    "it will later use to drive the fans."
                ),
                technical=(
                    "Pre-power inventory over sideband — I2C and NC-SI, functional "
                    "with the CPUs down. Per-DIMM serials, backplane enumeration, "
                    "PSU capacity and firmware, and the thermal sensor map that "
                    "will drive fan control."
                ),
                expert=(
                    "Sideband inventory pre-power (I2C, NC-SI): DIMM serials, "
                    "backplane, PSU capacity/firmware, thermal sensor map."
                ),
            ),
            active_regions=["idrac", "board", "backplane", "psu1", "psu2"],
            power_watts=22,
            fan_percent=0,
            elapsed_seconds=45,
        ),
        PowerOnState(
            step=4,
            phase="poweron",
            label="Power on · main rails",
            description=L(
                novice=(
                    "The power button is pressed — or an administrator clicks Power "
                    "On in the management console from anywhere in the world, "
                    "because the physical button is just another input to that "
                    "controller. The controller tells the power supplies to enable "
                    "their main output, and the distribution board sequences "
                    "current out to the system board, the drive backplane, the "
                    "fans, and the expansion slots."
                ),
                plain=(
                    "The power button is pressed — or an admin clicks Power On in "
                    "iDRAC from anywhere in the world; the button is just another "
                    "input to the management controller. iDRAC signals the PSUs to "
                    "enable their main 12 V output, and the power distribution "
                    "board sequences current to the system board, backplane, fans, "
                    "and risers."
                ),
                standard=(
                    "The power button is pressed — or an admin clicks Power On "
                    "in iDRAC from anywhere in the world; the button is just "
                    "another input to the management controller. iDRAC signals "
                    "the PSUs to enable their main 12 V output, and the power "
                    "distribution board sequences current out to the system "
                    "board, backplane, fans, and risers."
                ),
                technical=(
                    "Power-on asserted, whether by front-panel button or remotely "
                    "through iDRAC — the button is one input among several to the "
                    "BMC. PSUs enable main 12 V; the PDB sequences to system board, "
                    "backplane, fans, and risers."
                ),
                expert=(
                    "Power-on asserted (panel or BMC-remote). Main 12 V enabled; "
                    "PDB sequences board, backplane, fans, risers."
                ),
            ),
            active_regions=["pdb", "psu1", "psu2"],
            power_watts=80,
            fan_percent=10,
            elapsed_seconds=60,
        ),
        PowerOnState(
            step=5,
            phase="poweron",
            label="Fans to full — the jet-engine moment",
            description=L(
                novice=(
                    "All six fans slam to full speed — the roar every data-centre "
                    "technician knows. It is deliberate. Until the firmware has "
                    "actually read the temperature sensors, the only safe "
                    "assumption is maximum airflow. A few seconds later, once the "
                    "management controller's thermal control takes over, the speeds "
                    "drop to whatever the readings actually justify."
                ),
                plain=(
                    "Every fan jumps to full speed — the roar anyone who has stood "
                    "in a data centre will recognise. It is intentional. Until the "
                    "firmware has actually read the thermal sensors, maximum "
                    "airflow is the only safe assumption to make. A few seconds "
                    "later iDRAC's thermal management takes over and the speeds "
                    "fall back to whatever the sensor readings genuinely justify."
                ),
                standard=(
                    "All six fans slam to 100% — the roar every datacenter tech "
                    "knows. It is deliberate: until the firmware has read the "
                    "thermal sensors, the safe assumption is maximum airflow. "
                    "Once iDRAC's thermal management takes over a few seconds "
                    "later, speeds drop to whatever the sensors actually "
                    "justify."
                ),
                technical=(
                    "Fans to 100% by design — with no validated sensor data yet, "
                    "maximum airflow is the only safe default. iDRAC's thermal loop "
                    "assumes control within seconds and speeds fall to the "
                    "sensor-justified level."
                ),
                expert=(
                    "Fans to 100% — safe default absent validated sensor data. "
                    "Thermal loop assumes control within seconds."
                ),
            ),
            active_regions=_FANS,
            power_watts=300,
            fan_percent=100,
            elapsed_seconds=63,
            cycle_cost=2,
        ),
        PowerOnState(
            step=6,
            phase="poweron",
            label="CPU power sequencing",
            description=L(
                novice=(
                    "Voltage regulators on the board bring the processor supplies "
                    "up in a strict order — core, cache, and input/output each "
                    "settling within tight limits before the next may rise. A "
                    "modern server processor can draw over 300 watts at less than "
                    "one volt, which means hundreds of amps. Getting this order "
                    "wrong destroys silicon, so dedicated hardware logic enforces "
                    "it rather than software."
                ),
                plain=(
                    "Voltage regulators on the system board step the CPU supplies "
                    "up in strict order — core, cache, and I/O rails each within "
                    "tight tolerances before the next may rise. A modern Xeon can "
                    "draw over 300 W at under one volt, meaning hundreds of amps; "
                    "getting this wrong kills silicon, so dedicated sequencing "
                    "logic, not software, enforces it on both sockets."
                ),
                standard=(
                    "Voltage regulators on the system board step the CPU "
                    "supplies up in strict order — core, cache, and I/O rails "
                    "each within tight tolerances before the next may rise. A "
                    "modern Xeon can draw over 300 W at under one volt, i.e. "
                    "hundreds of amps; getting this wrong kills silicon, so "
                    "dedicated sequencing logic, not software, enforces it on "
                    "both sockets."
                ),
                technical=(
                    "VRs sequence the CPU rails in fixed order — core, cache, I/O — "
                    "each settling within tolerance before the next. >300 W at "
                    "sub-1 V is hundreds of amps, and mis-sequencing is "
                    "destructive, so dedicated hardware logic enforces the order on "
                    "both sockets rather than firmware."
                ),
                expert=(
                    "VR sequencing: core, cache, I/O in order, per-rail tolerance "
                    "gated. >300 W at sub-1 V; hardware-enforced because "
                    "mis-sequencing is destructive."
                ),
            ),
            active_regions=["cpu1", "cpu2", "board"],
            power_watts=180,
            fan_percent=60,
            elapsed_seconds=66,
        ),
        PowerOnState(
            step=7,
            phase="post",
            label="CPUs out of reset · UEFI starts",
            description=L(
                novice=(
                    "Reset is released and the first processor fetches its opening "
                    "instructions from a small flash chip on the board — the "
                    "firmware that replaced the classic BIOS. The self-test begins. "
                    "There is no usable memory yet, so the firmware runs using the "
                    "processor's own internal cache as temporary memory, which is "
                    "as awkward as it sounds and is one reason this stage is "
                    "fiddly."
                ),
                plain=(
                    "Reset is released and CPU 1 fetches its first instructions "
                    "from a SPI flash chip on the system board — the UEFI firmware, "
                    "successor to the classic BIOS. POST, the Power-On Self-Test, "
                    "begins. There is no usable RAM yet, so the firmware runs with "
                    "the CPU's own cache configured as temporary memory: "
                    "cache-as-RAM."
                ),
                standard=(
                    "Reset is released and CPU 1 fetches its first instructions "
                    "from a SPI flash chip on the system board — the UEFI "
                    "firmware (successor to the classic BIOS; Dell's is built "
                    "on it). POST, the Power-On Self-Test, begins. There is no "
                    "usable RAM yet, so the firmware runs with the CPU's own "
                    "cache configured as temporary memory ('cache-as-RAM')."
                ),
                technical=(
                    "Reset deasserted; CPU 1 fetches from SPI flash into UEFI. POST "
                    "begins with no initialized DRAM, so the firmware executes in "
                    "cache-as-RAM until the memory controllers are trained."
                ),
                expert=(
                    "Reset deasserted, CPU 1 fetches UEFI from SPI. POST runs "
                    "cache-as-RAM pending DRAM init."
                ),
            ),
            active_regions=["cpu1", "cpu2", "board"],
            power_watts=220,
            fan_percent=55,
            elapsed_seconds=70,
        ),
        PowerOnState(
            step=8,
            phase="post",
            label="DDR5 memory training",
            description=L(
                novice=(
                    "The longest part of the start-up. Each processor's memory "
                    "controller tunes every memory module: it sweeps the signal "
                    "timing and voltage on each electrical lane to find settings "
                    "that work reliably at these very high speeds. The margins are "
                    "far too fine to fix in advance, so the machine measures them "
                    "itself. A fully populated server can sit here for minutes on "
                    "its first start, apparently doing nothing at all. The results "
                    "are saved, so later starts are much quicker."
                ),
                plain=(
                    "The longest POST stage. Each CPU's memory controller trains "
                    "every DIMM: sweeping signal timing and voltage per lane to "
                    "find reliable settings at 4800–5600 MT/s, because at those "
                    "speeds the margins are too fine to hardcode. A fully loaded "
                    "32-DIMM machine can sit here for minutes on first boot, "
                    "apparently doing nothing. Results are cached, so later boots "
                    "are much faster."
                ),
                standard=(
                    "The longest POST stage. Each CPU's memory controller "
                    "'trains' every DIMM: it sweeps signal timing and voltage "
                    "per lane to find reliable settings at 4800–5600 MT/s — "
                    "at those speeds the margins are too fine to hardcode. A "
                    "fully loaded 32-DIMM machine can sit here for minutes on "
                    "first boot, apparently doing nothing. Results are cached, "
                    "so later boots are much faster."
                ),
                technical=(
                    "Max-dwell stage. Per-DIMM training: the memory controllers "
                    "sweep timing and voltage per lane to find reliable operating "
                    "points at 4800–5600 MT/s, since margins at those rates are "
                    "board- and part-specific and cannot be hardcoded. A 32-DIMM "
                    "configuration can take minutes on a cold first boot; results "
                    "are cached for subsequent boots."
                ),
                expert=(
                    "Max dwell: per-lane DDR5 timing/voltage sweep at 4800–5600 "
                    "MT/s. Margins are board-specific, not hardcodable. Minutes on "
                    "first boot with 32 DIMMs; cached thereafter."
                ),
            ),
            active_regions=_DIMMS + ["cpu1", "cpu2"],
            power_watts=260,
            fan_percent=50,
            elapsed_seconds=180,
            cycle_cost=6,
        ),
        PowerOnState(
            step=9,
            phase="post",
            label="PCIe enumeration",
            description=L(
                novice=(
                    "The firmware walks the expansion bus and discovers every "
                    "device attached to it: cards in the expansion slots, the "
                    "network card in its dedicated mezzanine, the storage "
                    "controller by the drive backplane, and the boot module. Each "
                    "device is assigned its own memory windows and interrupt lines "
                    "— the address map that the operating system will simply "
                    "inherit when it starts."
                ),
                plain=(
                    "The firmware walks the PCIe Gen5 fabric and discovers every "
                    "device: cards on the risers, the OCP 3.0 network mezzanine, "
                    "the PERC RAID controller by the backplane, and the BOSS-N1 "
                    "boot module. Each is assigned memory windows and interrupts — "
                    "the address map the OS will inherit."
                ),
                standard=(
                    "The firmware walks the PCIe Gen5 fabric and discovers "
                    "every device: cards on the risers, the OCP 3.0 network "
                    "mezzanine, the PERC RAID controller by the backplane, and "
                    "the BOSS-N1 boot module. Each device is assigned memory "
                    "windows and interrupts — the address map the OS will "
                    "inherit."
                ),
                technical=(
                    "PCIe Gen5 enumeration across risers, the OCP 3.0 mezzanine, "
                    "the PERC controller, and the BOSS-N1 module. BAR allocation "
                    "and interrupt assignment produce the address map the OS "
                    "inherits wholesale."
                ),
                expert=(
                    "PCIe Gen5 enumeration: risers, OCP 3.0 NIC, PERC, BOSS-N1. BAR "
                    "and interrupt allocation; the OS inherits the map."
                ),
            ),
            active_regions=["riser1", "riser2", "ocp", "perc", "boss"],
            power_watts=280,
            fan_percent=45,
            elapsed_seconds=195,
        ),
        PowerOnState(
            step=10,
            phase="post",
            label="Storage init · staggered spin-up",
            description=L(
                novice=(
                    "The storage controller runs its own firmware, checks its "
                    "battery-backed cache, and verifies its disk arrays. Any "
                    "spinning disks are started in staggered groups, because a disk "
                    "motor draws a large surge of current as it spins up and "
                    "twenty-four starting at once could exceed the very power "
                    "budget the supplies were sized for. Builds with only "
                    "solid-state drives clear this stage quickly."
                ),
                plain=(
                    "The PERC RAID controller runs its own firmware, checks its "
                    "battery-backed cache, and verifies its RAID volumes. Spinning "
                    "drives start in staggered groups — a motor draws a large "
                    "inrush current, and 24 disks starting at once could trip the "
                    "very power budget the PSUs were sized for. SSD-only builds "
                    "clear this quickly."
                ),
                standard=(
                    "The PERC (PowerEdge RAID Controller) runs its own "
                    "firmware, checks its battery-backed cache, and verifies "
                    "its RAID volumes. Spinning drives are started in staggered "
                    "groups — a motor draws a large inrush current, and 24 "
                    "disks starting at once could trip the very power budget "
                    "the PSUs were sized for. SSD-only builds clear this stage "
                    "quickly."
                ),
                technical=(
                    "PERC firmware init, battery-backed cache validation, RAID "
                    "volume verification. Rotational media spin up in staggered "
                    "groups because inrush across 24 spindles would exceed the PSU "
                    "budget. All-flash configurations pass through quickly."
                ),
                expert=(
                    "PERC init, BBU cache check, RAID verify. Staggered spin-up "
                    "bounds inrush against the PSU budget; all-flash skips it."
                ),
            ),
            active_regions=["perc", "backplane"],
            power_watts=340,
            fan_percent=45,
            elapsed_seconds=215,
            cycle_cost=3,
        ),
        PowerOnState(
            step=11,
            phase="post",
            label="POST complete",
            description=L(
                novice=(
                    "The self-test passes: the logo appears on the console with the "
                    "prompt to enter setup, and the management controller records "
                    "the milestone. The temperature picture is now fully known, so "
                    "the fans settle from their initial roar to a managed thirty "
                    "percent or so. Every component the operating system will use "
                    "has been found, tested, and mapped."
                ),
                plain=(
                    "The self-test passes. The Dell logo appears on the console "
                    "with the prompt to press F2 for setup, and iDRAC records the "
                    "milestone in its log. Because the temperature picture is now "
                    "completely known, the fans come down from their opening roar "
                    "to a managed thirty percent or so. Every component the "
                    "operating system is going to use has been found, tested, and "
                    "given an address."
                ),
                standard=(
                    "Self-test passes: the Dell logo is on the console with the "
                    "F2 System Setup prompt, and iDRAC logs the milestone. The "
                    "thermal picture is now fully known, so the fans settle to "
                    "a managed ~30%. Every component the OS will use has been "
                    "found, tested, and mapped."
                ),
                technical=(
                    "POST complete: console shows the setup prompt and iDRAC logs "
                    "the milestone. With the thermal picture resolved, fans settle "
                    "to ~30% under managed control. The full device inventory is "
                    "discovered, tested, and mapped."
                ),
                expert=(
                    "POST complete, milestone logged. Fans settle to ~30% under "
                    "thermal control. Inventory discovered, tested, mapped."
                ),
            ),
            active_regions=["board", "idrac"],
            power_watts=250,
            fan_percent=30,
            elapsed_seconds=225,
        ),
        PowerOnState(
            step=12,
            phase="boot",
            label="UEFI boot manager",
            description=L(
                novice=(
                    "The firmware reads its configured boot order and hands control "
                    "to the boot device: a dedicated module holding two small "
                    "solid-state sticks mirrored in hardware. Booting from that "
                    "module keeps all twenty-four front drive bays free for actual "
                    "data, and either half of the mirror can fail without losing "
                    "the operating system."
                ),
                plain=(
                    "The firmware consults the boot order it was configured with "
                    "and passes control to the boot device — the BOSS-N1 module, "
                    "which holds two small M.2 solid-state drives mirrored by "
                    "hardware. Booting from there leaves all 24 front bays "
                    "available for actual data, and either half of the mirror can "
                    "die without taking the operating system with it."
                ),
                standard=(
                    "The firmware reads its boot order and hands control to "
                    "the boot device: the BOSS-N1 module and its two M.2 NVMe "
                    "sticks in a hardware RAID-1 mirror. Booting from BOSS "
                    "keeps all 24 front bays free for data, and either mirror "
                    "half can fail without losing the OS."
                ),
                technical=(
                    "UEFI boot manager resolves boot order to the BOSS-N1 module — "
                    "two M.2 NVMe devices in hardware RAID-1. Dedicating boot to "
                    "BOSS keeps all 24 front bays available for data and tolerates "
                    "single-device failure without OS loss."
                ),
                expert=(
                    "Boot manager hands off to BOSS-N1 (2× M.2 NVMe, HW RAID-1). "
                    "Front bays stay free for data; single-device tolerant."
                ),
            ),
            active_regions=["boss"],
            power_watts=245,
            fan_percent=28,
            elapsed_seconds=230,
        ),
        PowerOnState(
            step=13,
            phase="boot",
            label="Operating system loads",
            description=L(
                novice=(
                    "The bootloader pulls the operating system or virtualization "
                    "software off that mirror into memory. The kernel brings up "
                    "both processors and all the tuned memory, then attaches "
                    "drivers to the inventory the firmware handed over — storage "
                    "volumes become disks, the network card gets its interfaces, "
                    "any graphics processors attach to their drivers."
                ),
                plain=(
                    "The bootloader loads the operating system or hypervisor kernel "
                    "from the mirrored boot module into main memory. The kernel "
                    "starts both processors and all the memory that was just "
                    "trained, then attaches drivers to the inventory the firmware "
                    "handed it: RAID volumes turn into disks the system can use, "
                    "the network card gets its interfaces, and any accelerators "
                    "find their drivers."
                ),
                standard=(
                    "The bootloader pulls the OS or hypervisor kernel off the "
                    "BOSS mirror into DRAM. The kernel brings up both sockets "
                    "and all trained memory, then binds drivers to the "
                    "inventory UEFI handed over — PERC volumes become block "
                    "devices, the OCP NIC gets its interfaces, any GPUs attach "
                    "to their drivers."
                ),
                technical=(
                    "Bootloader loads the OS or hypervisor kernel from the BOSS "
                    "mirror into DRAM. The kernel enumerates both sockets and the "
                    "trained memory map, then binds drivers against the "
                    "UEFI-supplied inventory: PERC volumes to block devices, OCP "
                    "NIC to interfaces, accelerators to their drivers."
                ),
                expert=(
                    "Kernel loaded from BOSS into DRAM; both sockets and trained "
                    "memory up. Drivers bound against the UEFI inventory."
                ),
            ),
            active_regions=["boss", "cpu1", "cpu2"] + _DIMMS,
            power_watts=310,
            fan_percent=32,
            elapsed_seconds=260,
            cycle_cost=2,
        ),
        PowerOnState(
            step=14,
            phase="os",
            label="Steady state",
            description=L(
                novice=(
                    "The system is up and serving. A two-processor machine idles at "
                    "around 250 watts with fans near a quarter speed, both rising "
                    "with load under the management controller's thermal control. "
                    "That controller keeps watching from the side — sensors, logs, "
                    "remote console — exactly as it has since about ten seconds "
                    "after the cords went in. The management plane was running "
                    "before the server was, and it never stops."
                ),
                plain=(
                    "The operating system is up and serving traffic. A two-socket "
                    "R760 sits at roughly 250 W when idle with its fans around a "
                    "quarter speed, both figures rising with load under iDRAC's "
                    "thermal control. iDRAC carries on watching from the side — "
                    "sensors, logs, remote console — exactly as it has since about "
                    "ten seconds after the cords went in. The management plane "
                    "started before the server and does not stop when it does."
                ),
                standard=(
                    "The OS is up and serving. A dual-socket R760 idles around "
                    "250 W with fans near 25%, both climbing with load under "
                    "iDRAC's thermal control. iDRAC keeps watching out-of-band "
                    "— sensors, logs, remote console — exactly as it has since "
                    "ten seconds after the cords went in: the management plane "
                    "was running before the server, and it never stops."
                ),
                technical=(
                    "Steady state: OS serving, ~250 W idle at ~25% fan under iDRAC "
                    "thermal control, both scaling with load. Out-of-band "
                    "monitoring continues unchanged from ten seconds after AC — the "
                    "management plane preceded the host and outlives every host "
                    "power cycle."
                ),
                expert=(
                    "Steady: ~250 W idle, ~25% fan under BMC thermal control. "
                    "Out-of-band watch unchanged since AC — management precedes and "
                    "outlives the host."
                ),
            ),
            active_regions=["cpu1", "cpu2", "idrac"] + _FANS,
            power_watts=250,
            fan_percent=25,
            elapsed_seconds=290,
        ),
    ]
