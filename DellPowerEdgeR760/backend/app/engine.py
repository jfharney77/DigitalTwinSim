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
            description=(
                "Both power cords are plugged in. Nothing appears to happen "
                "— fans are still, LEDs dark, zero measurable draw. But the "
                "power supplies have detected line voltage and are about to "
                "wake the one subsystem that never really sleeps."
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
            description=(
                "Each PSU brings up a small 12 V standby rail — a trickle "
                "feed, a few watts, routed through the power distribution "
                "board. The main rails that feed CPUs and drives stay off. "
                "This standby rail is why a plugged-in server is never "
                "truly off: it powers the management controller, the power "
                "button circuit, and wake-on-LAN."
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
            description=(
                "The standby rail wakes iDRAC9 (integrated Dell Remote "
                "Access Controller), the baseboard management controller — "
                "a small always-on ARM computer with its own flash storage, "
                "operating system, and network port. It boots its embedded "
                "Linux in under a minute. The host server is still 'off', "
                "yet you can already log into iDRAC's web console over the "
                "network."
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
            description=(
                "Before the host ever powers on, iDRAC walks the chassis "
                "over sideband buses (I2C and NC-SI — low-speed management "
                "links that work without the CPUs): it reads every DIMM's "
                "serial number, queries the drive backplane, checks both "
                "PSUs' capacity and firmware, and maps the thermal sensors "
                "it will later use to drive the fans."
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
            description=(
                "The power button is pressed — or an admin clicks Power On "
                "in iDRAC from anywhere in the world; the button is just "
                "another input to the management controller. iDRAC signals "
                "the PSUs to enable their main 12 V output, and the power "
                "distribution board sequences current out to the system "
                "board, backplane, fans, and risers."
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
            description=(
                "All six fans slam to 100% — the roar every datacenter tech "
                "knows. It is deliberate: until the firmware has read the "
                "thermal sensors, the safe assumption is maximum airflow. "
                "Once iDRAC's thermal management takes over a few seconds "
                "later, speeds drop to whatever the sensors actually "
                "justify."
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
            description=(
                "Voltage regulators on the system board step the CPU "
                "supplies up in strict order — core, cache, and I/O rails "
                "each within tight tolerances before the next may rise. A "
                "modern Xeon can draw over 300 W at under one volt, i.e. "
                "hundreds of amps; getting this wrong kills silicon, so "
                "dedicated sequencing logic, not software, enforces it on "
                "both sockets."
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
            description=(
                "Reset is released and CPU 1 fetches its first instructions "
                "from a SPI flash chip on the system board — the UEFI "
                "firmware (successor to the classic BIOS; Dell's is built "
                "on it). POST, the Power-On Self-Test, begins. There is no "
                "usable RAM yet, so the firmware runs with the CPU's own "
                "cache configured as temporary memory ('cache-as-RAM')."
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
            description=(
                "The longest POST stage. Each CPU's memory controller "
                "'trains' every DIMM: it sweeps signal timing and voltage "
                "per lane to find reliable settings at 4800–5600 MT/s — "
                "at those speeds the margins are too fine to hardcode. A "
                "fully loaded 32-DIMM machine can sit here for minutes on "
                "first boot, apparently doing nothing. Results are cached, "
                "so later boots are much faster."
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
            description=(
                "The firmware walks the PCIe Gen5 fabric and discovers "
                "every device: cards on the risers, the OCP 3.0 network "
                "mezzanine, the PERC RAID controller by the backplane, and "
                "the BOSS-N1 boot module. Each device is assigned memory "
                "windows and interrupts — the address map the OS will "
                "inherit."
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
            description=(
                "The PERC (PowerEdge RAID Controller) runs its own "
                "firmware, checks its battery-backed cache, and verifies "
                "its RAID volumes. Spinning drives are started in staggered "
                "groups — a motor draws a large inrush current, and 24 "
                "disks starting at once could trip the very power budget "
                "the PSUs were sized for. SSD-only builds clear this stage "
                "quickly."
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
            description=(
                "Self-test passes: the Dell logo is on the console with the "
                "F2 System Setup prompt, and iDRAC logs the milestone. The "
                "thermal picture is now fully known, so the fans settle to "
                "a managed ~30%. Every component the OS will use has been "
                "found, tested, and mapped."
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
            description=(
                "The firmware reads its boot order and hands control to "
                "the boot device: the BOSS-N1 module and its two M.2 NVMe "
                "sticks in a hardware RAID-1 mirror. Booting from BOSS "
                "keeps all 24 front bays free for data, and either mirror "
                "half can fail without losing the OS."
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
            description=(
                "The bootloader pulls the OS or hypervisor kernel off the "
                "BOSS mirror into DRAM. The kernel brings up both sockets "
                "and all trained memory, then binds drivers to the "
                "inventory UEFI handed over — PERC volumes become block "
                "devices, the OCP NIC gets its interfaces, any GPUs attach "
                "to their drivers."
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
            description=(
                "The OS is up and serving. A dual-socket R760 idles around "
                "250 W with fans near 25%, both climbing with load under "
                "iDRAC's thermal control. iDRAC keeps watching out-of-band "
                "— sensors, logs, remote console — exactly as it has since "
                "ten seconds after the cords went in: the management plane "
                "was running before the server, and it never stops."
            ),
            active_regions=["cpu1", "cpu2", "idrac"] + _FANS,
            power_watts=250,
            fan_percent=25,
            elapsed_seconds=290,
        ),
    ]
