"""Pure bring-up sequence engine for iDRAC9.

``simulate()`` returns the deterministic trace of what happens *inside the
iDRAC service processor itself* from the moment AC reaches the standby rail
until iDRAC is a ready, watching management controller — the host is still
powered off the whole time. Same purity rule as the other twins: no FastAPI,
no IO, no timers — the frontend owns the playback clock, and each
``BringUpState`` is plain data the renderer consumes. ``cycle_cost`` marks
the long stages (Lifecycle Controller init) so the UI dwells on them.

Timing (``elapsed_seconds``) and power draw are illustrative but plausible
for an embedded BMC bringing up in under a minute; per the project's scope
guardrails, favor a correct mental model over measured numbers.
"""

from __future__ import annotations

from .models import BringUpState


def simulate() -> list[BringUpState]:
    """iDRAC's journey from AC standby to a ready service processor, as pure
    data. The host never powers on here — that is the R760 twin's story; this
    is the management plane coming alive underneath it."""
    return [
        BringUpState(
            step=0,
            phase="off",
            label="No AC",
            description=(
                "The server is unplugged. The iDRAC power domain is dark — no "
                "management, no network port, nothing. Nothing about the "
                "server can be reached until a power cord carries line "
                "voltage to a power supply."
            ),
            active_regions=[],
            power_watts=0,
            progress_percent=0,
            elapsed_seconds=0,
        ),
        BringUpState(
            step=1,
            phase="standby",
            label="Standby rail energizes the BMC domain",
            description=(
                "A power cord is connected. Before anything else happens, the "
                "power supply brings up a small standby rail — a few watts — "
                "that feeds only the iDRAC power island: the SoC, its memory, "
                "and the management NIC. The host's main rails stay off. This "
                "standby feed is the whole reason a plugged-in server is never "
                "truly 'off'."
            ),
            active_regions=["pwr"],
            power_watts=4,
            progress_percent=5,
            elapsed_seconds=1,
        ),
        BringUpState(
            step=2,
            phase="reset",
            label="SoC out of reset · boot ROM",
            description=(
                "With standby power stable, the iDRAC system-on-chip is "
                "released from reset. Its immutable on-chip boot ROM runs "
                "first — the one piece of code that cannot be reflashed — and "
                "its only job is to locate and hand off to iDRAC's first-stage "
                "firmware in flash."
            ),
            active_regions=["pwr", "soc"],
            power_watts=5,
            progress_percent=10,
            elapsed_seconds=3,
            cycle_cost=2,
        ),
        BringUpState(
            step=3,
            phase="reset",
            label="Root of Trust verifies firmware",
            description=(
                "Before that firmware is allowed to execute, the silicon Root "
                "of Trust checks its cryptographic signature against a key "
                "fused into the chip. Tampered or corrupt firmware is rejected "
                "here, at the very bottom of the stack — this is the anchor "
                "for System Lockdown and Secured Component Verification. Only a "
                "valid image proceeds."
            ),
            active_regions=["soc", "rot", "flash"],
            power_watts=5,
            progress_percent=15,
            elapsed_seconds=6,
        ),
        BringUpState(
            step=4,
            phase="bootldr",
            label="Bootloader · DRAM init",
            description=(
                "The verified first-stage bootloader (a U-Boot-class loader) "
                "takes over. It initializes the iDRAC SoC's dedicated DDR4 "
                "memory — separate from the host's system RAM — and copies the "
                "compressed iDRAC firmware image out of flash, ready to hand "
                "control to the embedded operating system."
            ),
            active_regions=["soc", "flash", "dram"],
            power_watts=6,
            progress_percent=25,
            elapsed_seconds=10,
        ),
        BringUpState(
            step=5,
            phase="kernel",
            label="Embedded Linux boots",
            description=(
                "iDRAC's embedded Linux kernel starts and mounts its firmware "
                "filesystem out of flash into DRAM. iDRAC is, quite literally, "
                "a small Linux computer bolted to the side of the server — "
                "this is its operating system coming up, wholly independent of "
                "whatever the host will eventually run."
            ),
            active_regions=["soc", "dram", "flash"],
            power_watts=7,
            progress_percent=40,
            elapsed_seconds=18,
            cycle_cost=2,
        ),
        BringUpState(
            step=6,
            phase="kernel",
            label="Sideband buses come up",
            description=(
                "The kernel binds drivers to the management buses that reach "
                "into the host: I2C and PMBus for sensors, PSUs and DIMMs; "
                "eSPI and PECI for the CPUs and BIOS; NC-SI for the shared-LOM "
                "path. These are 'out-of-band' links — they work with the host "
                "CPUs powered off, which is exactly the state the host is in "
                "right now."
            ),
            active_regions=["soc", "sb-i2c", "sb-espi", "sb-ncsi"],
            power_watts=7,
            progress_percent=50,
            elapsed_seconds=24,
        ),
        BringUpState(
            step=7,
            phase="services",
            label="Management services start",
            description=(
                "The interface daemons come online: the HTML5 web server, the "
                "Redfish REST API (the modern, schema-driven management "
                "standard), the RACADM command line over SSH, and legacy IPMI "
                "2.0 and SNMP. From this point the control surface exists — it "
                "just needs an address and its back-end engines."
            ),
            active_regions=["soc", "dram"],
            power_watts=8,
            progress_percent=65,
            elapsed_seconds=30,
        ),
        BringUpState(
            step=8,
            phase="services",
            label="Lifecycle Controller initializes",
            description=(
                "The longest stage. The embedded Lifecycle Controller mounts "
                "its repository, reconciles the stored hardware inventory "
                "against what the sideband buses report, and readies its "
                "deployment, firmware-update and configuration services. This "
                "is the machinery behind pressing F10 at boot, and behind "
                "zero-touch provisioning — a bare server with no OS and no "
                "media can deploy one because this engine lives in flash."
            ),
            active_regions=["soc", "flash", "dram"],
            power_watts=8,
            progress_percent=80,
            elapsed_seconds=55,
            cycle_cost=6,
        ),
        BringUpState(
            step=9,
            phase="services",
            label="Management NIC gets its address",
            description=(
                "The dedicated 1GbE management port acquires its IP — DHCP by "
                "default, or a static address set in iDRAC Settings or the "
                "Lifecycle Controller. The moment it has an address, iDRAC is "
                "reachable: an administrator on the management network can "
                "open the web console even though the host is still off."
            ),
            active_regions=["soc", "nic", "sb-ncsi"],
            power_watts=7,
            progress_percent=88,
            elapsed_seconds=62,
        ),
        BringUpState(
            step=10,
            phase="services",
            label="Remote-presence engine ready",
            description=(
                "The Virtual Console (KVM) and Virtual Media engines start, "
                "along with the front-panel paths — iDRAC Direct over USB and "
                "Quick Sync 2 over Bluetooth. With these up, a remote admin "
                "can see the real console and mount an ISO as if standing at "
                "the rack. These are licensed Enterprise features; on a Basic "
                "or Express server they stay dark."
            ),
            active_regions=["soc", "kvm", "vmedia", "direct"],
            power_watts=7,
            progress_percent=93,
            elapsed_seconds=68,
        ),
        BringUpState(
            step=11,
            phase="services",
            label="Monitoring & thermal engine online",
            description=(
                "The always-running monitoring engine begins sampling every "
                "sensor over the sideband buses, building the health tree, "
                "writing the Lifecycle Log, and — critically — closing the "
                "thermal loop: it now owns fan speeds, driving them from the "
                "temperatures it reads. Out-of-band performance monitoring and "
                "telemetry streaming ride on this engine, gated by license."
            ),
            active_regions=["soc", "monitor", "sb-i2c", "sb-espi"],
            power_watts=7,
            progress_percent=97,
            elapsed_seconds=74,
        ),
        BringUpState(
            step=12,
            phase="ready",
            label="iDRAC ready · console live",
            description=(
                "Bring-up is complete. The web console answers, Redfish and "
                "RACADM respond, the health tree is populated, and the power "
                "button is now just another input to iDRAC — an admin can "
                "power the host on from anywhere. Everything the R760 "
                "power-on twin shows begins from a signal sent right here."
            ),
            active_regions=["soc", "nic", "kvm", "monitor"],
            power_watts=6,
            progress_percent=100,
            elapsed_seconds=80,
        ),
        BringUpState(
            step=13,
            phase="ready",
            label="Out-of-band watch (steady state)",
            description=(
                "The management plane settles into what it does forever after: "
                "watching. It samples sensors, keeps the logs, holds the "
                "network interfaces open for the web console, Redfish and "
                "virtual media, and waits for an administrator's command — "
                "power control, a firmware update, an OS deployment. It has "
                "been running since seconds after the cords went in, and it "
                "never stops while the server is plugged in."
            ),
            active_regions=["soc", "monitor", "sb-i2c", "sb-espi", "nic"],
            power_watts=6,
            progress_percent=100,
            elapsed_seconds=86,
        ),
    ]
