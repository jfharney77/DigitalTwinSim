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

from .leveling import L
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
            description=L(
                novice=(
                    "The server is unplugged. The management computer's power "
                    "domain is completely dark — no monitoring, no network port, "
                    "nothing at all. Nothing about this server can be reached until "
                    "a power cord carries mains voltage to a power supply."
                ),
                plain=(
                    "The server has no power cord attached, so the iDRAC power "
                    "domain is completely unpowered: no management, no network "
                    "port, no reachability of any kind. Until line voltage reaches "
                    "a power supply, there is nothing here to talk to."
                ),
                standard=(
                    "The server is unplugged. The iDRAC power domain is dark — no "
                    "management, no network port, nothing. Nothing about the "
                    "server can be reached until a power cord carries line "
                    "voltage to a power supply."
                ),
                technical=(
                    "No AC. The iDRAC power domain is unpowered — no management "
                    "surface, no NIC, no reachability of any kind until line "
                    "voltage reaches a PSU."
                ),
                expert=(
                    "No AC; iDRAC domain unpowered. Zero reachability."
                ),
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
            description=L(
                novice=(
                    "A power cord is connected. Before anything else, the power "
                    "supply brings up a small standby feed — a few watts — that "
                    "powers only the management computer's island: its processor, "
                    "its memory, and its network port. The server's main power "
                    "stays off. This standby feed is the entire reason a plugged-in "
                    "server is never truly 'off'."
                ),
                plain=(
                    "A power cord is connected. Before anything else happens, the "
                    "power supply brings up a small standby rail — a few watts — "
                    "feeding only the iDRAC power island: the SoC, its memory, and "
                    "the management NIC. The host's main rails stay off. This "
                    "standby feed is why a plugged-in server is never truly off."
                ),
                standard=(
                    "A power cord is connected. Before anything else happens, the "
                    "power supply brings up a small standby rail — a few watts — "
                    "that feeds only the iDRAC power island: the SoC, its memory, "
                    "and the management NIC. The host's main rails stay off. This "
                    "standby feed is the whole reason a plugged-in server is never "
                    "truly 'off'."
                ),
                technical=(
                    "AC applied; the PSU energizes the standby rail — single-digit "
                    "watts feeding only the iDRAC island: SoC, dedicated DRAM, "
                    "management NIC. Host rails remain down. Standby is the "
                    "mechanism behind a plugged-in server never being genuinely "
                    "off."
                ),
                expert=(
                    "Standby rail up, feeding the iDRAC island only (SoC, DRAM, "
                    "mgmt NIC). Host rails down."
                ),
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
            description=L(
                novice=(
                    "With standby power stable, the management chip is released "
                    "from reset. A small piece of code permanently burned into the "
                    "silicon runs first — the one piece that cannot be replaced or "
                    "updated — and its only job is to find the first stage of the "
                    "management firmware in flash storage and hand control to it."
                ),
                plain=(
                    "Once the standby supply is stable, the iDRAC processor is "
                    "released from reset. The first code to run is a small program "
                    "burned permanently into the chip during manufacture — it "
                    "cannot be updated or replaced, which is the point of it — and "
                    "its only job is to find the first stage of iDRAC's firmware in "
                    "flash memory and hand over to it."
                ),
                standard=(
                    "With standby power stable, the iDRAC system-on-chip is "
                    "released from reset. Its immutable on-chip boot ROM runs "
                    "first — the one piece of code that cannot be reflashed — and "
                    "its only job is to locate and hand off to iDRAC's first-stage "
                    "firmware in flash."
                ),
                technical=(
                    "SoC out of reset on stable standby. The immutable on-chip boot "
                    "ROM executes first — non-reflashable by construction — and its "
                    "sole function is to locate and transfer control to first-stage "
                    "firmware in flash."
                ),
                expert=(
                    "SoC out of reset; immutable boot ROM locates and hands off to "
                    "first-stage firmware in flash."
                ),
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
            description=L(
                novice=(
                    "Before that firmware is allowed to run, hardware built into "
                    "the chip checks its cryptographic signature against a key "
                    "permanently fused into the silicon. Tampered or corrupted "
                    "firmware is rejected right here, at the very bottom of the "
                    "stack — which matters, because anything that could compromise "
                    "this layer would be able to lie about everything above it. "
                    "Only a valid image proceeds."
                ),
                plain=(
                    "Before that firmware is allowed to execute, the silicon Root "
                    "of Trust checks its cryptographic signature against a key "
                    "fused into the chip. Tampered or corrupt firmware is rejected "
                    "here, at the very bottom of the stack — the anchor for System "
                    "Lockdown and Secured Component Verification. Only a valid "
                    "image proceeds."
                ),
                standard=(
                    "Before that firmware is allowed to execute, the silicon Root "
                    "of Trust checks its cryptographic signature against a key "
                    "fused into the chip. Tampered or corrupt firmware is rejected "
                    "here, at the very bottom of the stack — this is the anchor "
                    "for System Lockdown and Secured Component Verification. Only a "
                    "valid image proceeds."
                ),
                technical=(
                    "Silicon Root of Trust verifies the first-stage image against a "
                    "fused key before execution is permitted. Rejection happens at "
                    "the base of the trust chain, which is what makes System "
                    "Lockdown and Secured Component Verification meaningful — a "
                    "compromise above this layer cannot forge attestation from "
                    "below it."
                ),
                expert=(
                    "Silicon RoT verifies first-stage against a fused key "
                    "pre-execution. Base of the trust chain; anchors Lockdown and "
                    "SCV."
                ),
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
            description=L(
                novice=(
                    "The verified first-stage loader takes over. It sets up the "
                    "management chip's own dedicated memory — entirely separate "
                    "from the server's main memory — and unpacks the compressed "
                    "management firmware out of flash, ready to hand control to the "
                    "small operating system inside."
                ),
                plain=(
                    "The verified first-stage bootloader, a U-Boot-class loader, "
                    "takes over. It initializes the iDRAC SoC's dedicated DDR4 "
                    "memory — separate from the host's system RAM — and copies the "
                    "compressed iDRAC firmware image out of flash, ready to hand "
                    "control to the embedded operating system."
                ),
                standard=(
                    "The verified first-stage bootloader (a U-Boot-class loader) "
                    "takes over. It initializes the iDRAC SoC's dedicated DDR4 "
                    "memory — separate from the host's system RAM — and copies the "
                    "compressed iDRAC firmware image out of flash, ready to hand "
                    "control to the embedded operating system."
                ),
                technical=(
                    "Verified U-Boot-class first stage initializes the SoC's "
                    "dedicated DDR4 — physically and logically distinct from host "
                    "system memory — and decompresses the iDRAC firmware image from "
                    "flash for handoff to the embedded OS."
                ),
                expert=(
                    "First stage inits dedicated DDR4 (separate from host RAM) and "
                    "decompresses the firmware image from flash."
                ),
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
            description=L(
                novice=(
                    "The management computer's own Linux kernel starts and mounts "
                    "its filesystem out of flash into memory. This is worth stating "
                    "plainly: the thing being described is literally a small Linux "
                    "computer bolted to the side of the server, and this is its "
                    "operating system coming up — entirely independent of whatever "
                    "the server itself will eventually run."
                ),
                plain=(
                    "iDRAC's own Linux kernel starts and mounts its filesystem out "
                    "of flash memory into RAM. It is worth saying plainly what this "
                    "means: iDRAC is a small Linux computer attached to the side of "
                    "the server, and this is that computer's operating system "
                    "booting — with no relationship at all to whatever the server "
                    "itself will run later."
                ),
                standard=(
                    "iDRAC's embedded Linux kernel starts and mounts its firmware "
                    "filesystem out of flash into DRAM. iDRAC is, quite literally, "
                    "a small Linux computer bolted to the side of the server — "
                    "this is its operating system coming up, wholly independent of "
                    "whatever the host will eventually run."
                ),
                technical=(
                    "Embedded Linux kernel boots and mounts the firmware filesystem "
                    "from flash into DRAM. The BMC is a discrete Linux system "
                    "co-resident with the host and entirely independent of the "
                    "host's eventual OS."
                ),
                expert=(
                    "Embedded Linux up, firmware filesystem mounted from flash. "
                    "Discrete system, independent of the host OS."
                ),
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
            description=L(
                novice=(
                    "The kernel attaches drivers to the management buses that reach "
                    "into the server: low-speed links for sensors, power supplies, "
                    "and memory modules; separate links for the processors and "
                    "firmware; and a shared path to the network. These are called "
                    "out-of-band links, and the defining property is that they work "
                    "with the server's own processors powered off — which is "
                    "exactly the state the server is in right now."
                ),
                plain=(
                    "The kernel binds drivers to the management buses reaching into "
                    "the host: I2C and PMBus for sensors, PSUs and DIMMs; eSPI and "
                    "PECI for the CPUs and BIOS; NC-SI for the shared network path. "
                    "These are out-of-band links — they work with the host CPUs "
                    "powered off, which is exactly the state the host is in right "
                    "now."
                ),
                standard=(
                    "The kernel binds drivers to the management buses that reach "
                    "into the host: I2C and PMBus for sensors, PSUs and DIMMs; "
                    "eSPI and PECI for the CPUs and BIOS; NC-SI for the shared-LOM "
                    "path. These are 'out-of-band' links — they work with the host "
                    "CPUs powered off, which is exactly the state the host is in "
                    "right now."
                ),
                technical=(
                    "Drivers bind to the sideband fabric: I2C and PMBus for "
                    "sensors, PSUs, and DIMMs; eSPI and PECI for CPU and BIOS "
                    "access; NC-SI for the shared-LOM path. Out-of-band by "
                    "definition — functional with host CPUs unpowered, which is the "
                    "current host state."
                ),
                expert=(
                    "Sideband drivers bound: I2C/PMBus (sensors, PSU, DIMM), "
                    "eSPI/PECI (CPU, BIOS), NC-SI (shared LOM). Functional with "
                    "host CPUs down."
                ),
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
            description=L(
                novice=(
                    "The interface services come online: the web server, the modern "
                    "management programming interface, the command line over a "
                    "secure shell, and the older standard protocols kept for "
                    "compatibility. From this point the control surface exists — it "
                    "just needs a network address and its back-end engines."
                ),
                plain=(
                    "The interface daemons come online: the HTML5 web server, the "
                    "Redfish REST API — the modern, schema-driven management "
                    "standard — the RACADM command line over SSH, and legacy IPMI "
                    "2.0 and SNMP. From this point the control surface exists; it "
                    "just needs an address and its back-end engines."
                ),
                standard=(
                    "The interface daemons come online: the HTML5 web server, the "
                    "Redfish REST API (the modern, schema-driven management "
                    "standard), the RACADM command line over SSH, and legacy IPMI "
                    "2.0 and SNMP. From this point the control surface exists — it "
                    "just needs an address and its back-end engines."
                ),
                technical=(
                    "Interface daemons start: HTML5 web server, Redfish REST API, "
                    "RACADM over SSH, and legacy IPMI 2.0 and SNMP for "
                    "compatibility. The control surface now exists pending "
                    "addressing and back-end engine initialization."
                ),
                expert=(
                    "Daemons up: HTML5, Redfish, RACADM/SSH, legacy IPMI 2.0 and "
                    "SNMP. Control surface pending address and back-ends."
                ),
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
            description=L(
                novice=(
                    "The longest stage. The built-in lifecycle engine mounts its "
                    "repository, reconciles the hardware inventory it has stored "
                    "against what the side channels are currently reporting, and "
                    "readies its deployment, firmware-update, and configuration "
                    "services. This is the machinery behind pressing F10 during "
                    "start-up, and behind provisioning a server with no operating "
                    "system and no installation media at all — a bare machine can "
                    "deploy one because this engine lives in flash."
                ),
                plain=(
                    "The longest stage. The embedded Lifecycle Controller mounts "
                    "its repository, reconciles the stored hardware inventory "
                    "against what the sideband buses report, and readies its "
                    "deployment, firmware-update, and configuration services. This "
                    "is the machinery behind pressing F10 at boot and behind "
                    "zero-touch provisioning — a bare server with no OS and no "
                    "media can deploy one because this engine lives in flash."
                ),
                standard=(
                    "The longest stage. The embedded Lifecycle Controller mounts "
                    "its repository, reconciles the stored hardware inventory "
                    "against what the sideband buses report, and readies its "
                    "deployment, firmware-update and configuration services. This "
                    "is the machinery behind pressing F10 at boot, and behind "
                    "zero-touch provisioning — a bare server with no OS and no "
                    "media can deploy one because this engine lives in flash."
                ),
                technical=(
                    "Max-dwell stage. Lifecycle Controller mounts its repository, "
                    "reconciles stored inventory against live sideband reporting, "
                    "and initializes deployment, firmware-update, and configuration "
                    "services. This engine backs the F10 path and zero-touch "
                    "provisioning — an OS-less, media-less server can deploy one "
                    "because the capability is resident in flash."
                ),
                expert=(
                    "Max dwell: LC repository mounted, inventory reconciled against "
                    "sideband, deployment/update/config services up. Backs F10 and "
                    "ZTP from flash."
                ),
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
            description=L(
                novice=(
                    "The dedicated management network port acquires its address — "
                    "automatically by default, or a fixed one set in the settings. "
                    "The moment it has an address, the management computer is "
                    "reachable: an administrator on the management network can open "
                    "the web console, even though the server itself is still "
                    "switched off."
                ),
                plain=(
                    "The separate 1 gigabit management network port gets an "
                    "address, assigned automatically by DHCP unless someone has set "
                    "a fixed one in iDRAC Settings or the Lifecycle Controller. As "
                    "soon as it has that address iDRAC can be reached: an "
                    "administrator on the management network can open the web "
                    "console while the server itself is still switched off."
                ),
                standard=(
                    "The dedicated 1GbE management port acquires its IP — DHCP by "
                    "default, or a static address set in iDRAC Settings or the "
                    "Lifecycle Controller. The moment it has an address, iDRAC is "
                    "reachable: an administrator on the management network can "
                    "open the web console even though the host is still off."
                ),
                technical=(
                    "The dedicated 1GbE management interface acquires an address, "
                    "DHCP by default or statically via iDRAC Settings or the "
                    "Lifecycle Controller. Reachability begins here — the console "
                    "is available with the host still unpowered."
                ),
                expert=(
                    "Dedicated 1GbE mgmt NIC addressed (DHCP or static). Console "
                    "reachable, host still down."
                ),
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
            description=L(
                novice=(
                    "The remote-presence engines start: the virtual console that "
                    "shows the real screen, and virtual media that lets you mount "
                    "an installation image as though you were standing at the rack "
                    "with a disc. There are also front-panel paths over USB and "
                    "Bluetooth. These are licensed features — on a lower-tier "
                    "licence they stay dark, which is the point the licence model "
                    "makes: the same silicon does more as the tier rises."
                ),
                plain=(
                    "The Virtual Console (KVM) and Virtual Media engines start, "
                    "along with the front-panel paths — iDRAC Direct over USB and "
                    "Quick Sync 2 over Bluetooth. With these up, a remote admin can "
                    "see the real console and mount an ISO as if standing at the "
                    "rack. These are licensed Enterprise features; on Basic or "
                    "Express they stay dark."
                ),
                standard=(
                    "The Virtual Console (KVM) and Virtual Media engines start, "
                    "along with the front-panel paths — iDRAC Direct over USB and "
                    "Quick Sync 2 over Bluetooth. With these up, a remote admin "
                    "can see the real console and mount an ISO as if standing at "
                    "the rack. These are licensed Enterprise features; on a Basic "
                    "or Express server they stay dark."
                ),
                technical=(
                    "Remote-presence engines start: Virtual Console (KVM) and "
                    "Virtual Media, plus front-panel paths — iDRAC Direct over USB "
                    "and Quick Sync 2 over Bluetooth. Full console visibility and "
                    "ISO mounting from anywhere. Licensed at Enterprise tier; dark "
                    "on Basic and Express, which is the licence model's whole shape "
                    "— identical silicon, gated capability."
                ),
                expert=(
                    "Virtual Console and Virtual Media up, plus iDRAC Direct (USB) "
                    "and Quick Sync 2 (BT). Enterprise-gated; dark on "
                    "Basic/Express."
                ),
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
            description=L(
                novice=(
                    "The always-running monitoring engine begins sampling every "
                    "sensor over the side channels, building the health picture, "
                    "writing the lifecycle log, and — critically — closing the "
                    "thermal loop: it now owns fan speeds, driving them from the "
                    "temperatures it reads. Performance monitoring and telemetry "
                    "streaming ride on this engine too, gated by licence tier."
                ),
                plain=(
                    "The always-running monitoring engine begins sampling every "
                    "sensor over the sideband buses, building the health tree, "
                    "writing the Lifecycle Log, and — critically — closing the "
                    "thermal loop: it now owns fan speeds, driving them from the "
                    "temperatures it reads. Out-of-band performance monitoring and "
                    "telemetry streaming ride on this engine, gated by licence."
                ),
                standard=(
                    "The always-running monitoring engine begins sampling every "
                    "sensor over the sideband buses, building the health tree, "
                    "writing the Lifecycle Log, and — critically — closing the "
                    "thermal loop: it now owns fan speeds, driving them from the "
                    "temperatures it reads. Out-of-band performance monitoring and "
                    "telemetry streaming ride on this engine, gated by license."
                ),
                technical=(
                    "Monitoring engine begins continuous sideband sensor sampling, "
                    "populates the health tree, writes the Lifecycle Log, and "
                    "closes the thermal control loop — fan speeds are now BMC-owned "
                    "and sensor-driven. Out-of-band performance monitoring and "
                    "telemetry streaming are layered on this engine, licence-gated."
                ),
                expert=(
                    "Monitoring engine sampling sideband sensors; health tree "
                    "populated, Lifecycle Log writing, thermal loop closed — fan "
                    "control now BMC-owned. Telemetry streaming licence-gated."
                ),
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
            description=L(
                novice=(
                    "Bring-up is complete. The web console answers, the programming "
                    "interfaces respond, the health picture is populated, and the "
                    "physical power button is now just another input to this "
                    "controller — an administrator can power the server on from "
                    "anywhere. Everything the rack-server twin in this repo shows "
                    "begins from a signal sent right here."
                ),
                plain=(
                    "Bring-up is finished. The web console responds, the Redfish "
                    "and RACADM interfaces answer, the health tree is filled in, "
                    "and the physical power button has become just one more input "
                    "into iDRAC — an administrator can now power the server on from "
                    "anywhere in the world. Everything the R760 power-on twin shows "
                    "starts from a signal sent at exactly this point."
                ),
                standard=(
                    "Bring-up is complete. The web console answers, Redfish and "
                    "RACADM respond, the health tree is populated, and the power "
                    "button is now just another input to iDRAC — an admin can "
                    "power the host on from anywhere. Everything the R760 "
                    "power-on twin shows begins from a signal sent right here."
                ),
                technical=(
                    "Bring-up complete: web console responsive, Redfish and RACADM "
                    "answering, health tree populated, and the front-panel power "
                    "button reduced to one input among several into the BMC. The "
                    "R760 twin's entire trace originates from a signal issued at "
                    "this point."
                ),
                expert=(
                    "Ready: console, Redfish, RACADM live; health tree populated; "
                    "power button is one BMC input among several. The R760 trace "
                    "starts from a signal issued here."
                ),
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
            description=L(
                novice=(
                    "The management plane settles into what it does forever after: "
                    "watching. It samples sensors, keeps the logs, holds the "
                    "network interfaces open for the console and remote media, and "
                    "waits for an administrator's command — power control, a "
                    "firmware update, an operating-system deployment. It has been "
                    "running since seconds after the cords went in, and it never "
                    "stops while the server is plugged in."
                ),
                plain=(
                    "The management plane settles into what it does forever after: "
                    "watching. It samples sensors, keeps the logs, holds the "
                    "network interfaces open for the web console, Redfish and "
                    "virtual media, and waits for an administrator's command — "
                    "power control, a firmware update, an OS deployment. It has "
                    "been running since seconds after the cords went in, and never "
                    "stops while the server is plugged in."
                ),
                standard=(
                    "The management plane settles into what it does forever after: "
                    "watching. It samples sensors, keeps the logs, holds the "
                    "network interfaces open for the web console, Redfish and "
                    "virtual media, and waits for an administrator's command — "
                    "power control, a firmware update, an OS deployment. It has "
                    "been running since seconds after the cords went in, and it "
                    "never stops while the server is plugged in."
                ),
                technical=(
                    "Steady state: continuous sensor sampling, log retention, "
                    "interfaces held open for console, Redfish, and virtual media, "
                    "awaiting operator action — power control, firmware update, OS "
                    "deployment. Running since seconds after AC and persistent for "
                    "as long as AC is present."
                ),
                expert=(
                    "Steady: sensor sampling, log retention, interfaces held open, "
                    "awaiting operator action. Persistent for as long as AC is "
                    "present."
                ),
            ),
            active_regions=["soc", "monitor", "sb-i2c", "sb-espi", "nic"],
            power_watts=6,
            progress_percent=100,
            elapsed_seconds=86,
        ),
    ]
