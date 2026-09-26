"""Pure bring-up sequence engine for iDRAC9.

``simulate()`` returns the deterministic trace of what happens *inside the
iDRAC service processor itself* from the moment AC reaches the standby rail
until iDRAC is a ready, watching management controller — the host is still
powered off the whole time. Same purity rule as the other twins: no FastAPI,
no IO, no timers — the frontend owns the playback clock, and each
``BringUpState`` is plain data the renderer consumes. ``cycle_cost`` marks
the long stages (Lifecycle Controller init) so the UI dwells on them.

``elapsed_seconds`` is stamped at the END of each step in both traces, so a
step's duration is its stamp minus the previous step's — the UI shows that
difference. Timing and power draw are illustrative but plausible
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
                    "server is never truly 'off'. Engineers call a helper computer "
                    "like this a BMC, short for baseboard management controller; "
                    "iDRAC is Dell's. The counter labelled 'BMC domain draw' is the "
                    "power this island is using."
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
                    "here, at the very bottom of the stack. Two Dell features are "
                    "anchored on this check: System Lockdown, a mode that blocks "
                    "configuration and firmware changes, and Secured Component "
                    "Verification, a factory-signed list of the server's parts that "
                    "is checked when the server arrives. Only a valid image "
                    "proceeds."
                ),
                standard=(
                    "Before that firmware is allowed to execute, the silicon Root "
                    "of Trust checks its cryptographic signature against a key "
                    "fused into the chip. Tampered or corrupt firmware is rejected "
                    "here, at the very bottom of the stack — this is the anchor "
                    "for System Lockdown (a mode that blocks configuration and "
                    "firmware changes) and Secured Component Verification (a "
                    "factory-signed hardware inventory checked on arrival). Only a "
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
                    "takes over. It initializes the iDRAC SoC's dedicated DRAM "
                    "memory — separate from the host's system RAM — and copies the "
                    "compressed iDRAC firmware image out of flash, ready to hand "
                    "control to the embedded operating system."
                ),
                standard=(
                    "The verified first-stage bootloader (a U-Boot-class loader) "
                    "takes over. It initializes the iDRAC SoC's dedicated DRAM "
                    "memory — separate from the host's system RAM — and copies the "
                    "compressed iDRAC firmware image out of flash, ready to hand "
                    "control to the embedded operating system."
                ),
                technical=(
                    "Verified U-Boot-class first stage initializes the SoC's "
                    "dedicated DRAM — physically and logically distinct from host "
                    "system memory — and decompresses the iDRAC firmware image from "
                    "flash for handoff to the embedded OS."
                ),
                expert=(
                    "First stage inits dedicated DRAM (separate from host RAM) and "
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
                    "The programs that let people talk to the management computer "
                    "start up: a web page for a person to click through, a "
                    "connection that other software can use to send it commands, a "
                    "typed command line, and two older ways of connecting kept so "
                    "that older tools still work. The front desk is now staffed. "
                    "It still needs a network address so anyone can find it, and "
                    "the tools behind the desk have not started yet."
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
                    "The longest stage: about 25 of the 86 seconds in this example, "
                    "which is why the clock jumps from 30 to 55 here. The management "
                    "computer is waking up the Lifecycle Controller, a set-up tool "
                    "kept in the same storage chip as its own software. The tool "
                    "compares its saved list of the server's parts with what it can "
                    "see now over the links into the server, and gets ready to "
                    "install software, update firmware and change settings. It is "
                    "what runs when someone presses F10 as the server starts. "
                    "Because it lives inside the management computer, a brand new "
                    "server with no operating system and no install disk can still "
                    "have one installed."
                ),
                plain=(
                    "The longest stage, about 25 seconds of this example's 86. The "
                    "embedded Lifecycle Controller mounts "
                    "its repository, reconciles the stored hardware inventory "
                    "against what the sideband buses report, and readies its "
                    "deployment, firmware-update, and configuration services. This "
                    "is the machinery behind pressing F10 at boot and behind "
                    "zero-touch provisioning — a bare server with no OS and no "
                    "media can deploy one because this engine lives in flash."
                ),
                standard=(
                    "The longest stage: the clock runs from t+30 s to t+55 s "
                    "across it (illustrative). The embedded Lifecycle Controller "
                    "mounts its repository, reconciles the stored hardware inventory "
                    "against what the sideband buses report, and readies its "
                    "deployment, firmware-update and configuration services. This "
                    "is the machinery behind pressing F10 at boot, and behind "
                    "zero-touch provisioning — a bare server with no OS and no "
                    "media can deploy one because this engine lives in flash."
                ),
                technical=(
                    "Longest stage, t+30 s to t+55 s (illustrative). Lifecycle "
                    "Controller mounts its repository, "
                    "reconciles stored inventory against live sideband reporting, "
                    "and initializes deployment, firmware-update, and configuration "
                    "services. This engine backs the F10 path and zero-touch "
                    "provisioning — an OS-less, media-less server can deploy one "
                    "because the capability is resident in flash."
                ),
                expert=(
                    "Longest stage, 25 s: LC repository mounted, inventory reconciled against "
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
                    "Bluetooth, which work on any licence. The console and media "
                    "are paid extras. Dell sells the management computer's features "
                    "in levels, and these two switch on only at the higher levels; "
                    "on the cheaper ones they stay dark. The hardware is the same "
                    "in every server. What you pay for is how much of it is "
                    "unlocked."
                ),
                plain=(
                    "The Virtual Console (KVM) and Virtual Media engines start, "
                    "along with the front-panel paths — iDRAC Direct over USB and "
                    "Quick Sync 2 over Bluetooth. With these up, a remote admin can "
                    "see the real console and mount an ISO as if standing at the "
                    "rack. The console and media are licensed Enterprise features; "
                    "on Basic or Express they stay dark. The front-panel paths "
                    "work at every tier."
                ),
                standard=(
                    "The Virtual Console (KVM) and Virtual Media engines start, "
                    "along with the front-panel paths — iDRAC Direct over USB and "
                    "Quick Sync 2 over Bluetooth. With these up, a remote admin "
                    "can see the real console and mount an ISO as if standing at "
                    "the rack. Virtual Console and Virtual Media are licensed "
                    "Enterprise features; on a Basic or Express rack server they "
                    "stay dark. The front-panel paths are not licence-gated."
                ),
                technical=(
                    "Remote-presence engines start: Virtual Console (KVM) and "
                    "Virtual Media, plus front-panel paths — iDRAC Direct over USB "
                    "and Quick Sync 2 over Bluetooth. Full console visibility and "
                    "ISO mounting from anywhere. Console and media are licensed at "
                    "Enterprise tier; dark "
                    "on Basic and Express (front-panel paths are ungated), which is the licence model's whole shape "
                    "— identical silicon, gated capability."
                ),
                expert=(
                    "Virtual Console and Virtual Media up, plus iDRAC Direct (USB) "
                    "and Quick Sync 2 (BT). Console/media Enterprise-gated; dark on "
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
                    "The always-running monitoring engine starts reading every "
                    "sensor over the links into the server, builds a picture of the "
                    "server's health, and starts its permanent diary, the Lifecycle "
                    "Log. It also loads its cooling rules. The server is off, so "
                    "the fans are still; from the moment the server is switched on, "
                    "this engine is what sets the fan speeds from the temperatures "
                    "it reads. Two extras build on the same engine on the "
                    "higher-priced licence levels: performance monitoring, and "
                    "sending the readings out continuously to other software."
                ),
                plain=(
                    "The always-running monitoring engine begins sampling every "
                    "sensor over the sideband buses, building the health tree, "
                    "writing the Lifecycle Log, and loading its thermal policy. "
                    "With the server off the fans are not turning; once the main "
                    "power rails are up, iDRAC owns the fan speeds and drives them "
                    "from the temperatures it reads. Out-of-band performance "
                    "monitoring and telemetry streaming ride on this engine, gated "
                    "by licence."
                ),
                standard=(
                    "The always-running monitoring engine begins sampling every "
                    "sensor over the sideband buses, building the health tree, "
                    "writing the Lifecycle Log, and — critically — loading the "
                    "thermal policy. The host is off, so no fan is turning yet; "
                    "fan control is iDRAC's once the main rails are up, driven from "
                    "the temperatures it reads. Out-of-band performance monitoring "
                    "and telemetry streaming ride on this engine, gated by license."
                ),
                technical=(
                    "Monitoring engine begins continuous sideband sensor sampling, "
                    "populates the health tree, writes the Lifecycle Log, and "
                    "loads the thermal policy — fan control is BMC-owned and "
                    "sensor-driven once main rails are up; in standby no fan turns. "
                    "Out-of-band performance monitoring and "
                    "telemetry streaming are layered on this engine, licence-gated."
                ),
                expert=(
                    "Monitoring engine sampling sideband sensors; health tree "
                    "populated, Lifecycle Log writing, thermal policy loaded — fan "
                    "control is BMC-owned once main rails are up. Telemetry "
                    "streaming licence-gated."
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


# ---------------------------------------------------------------------------
# Failure scenario: a firmware update that fails its boot check and rolls back
# ---------------------------------------------------------------------------
#
# A second pure trace alongside the bring-up. It starts where the bring-up
# ends — iDRAC ready and watching — with one difference that is the whole
# point: the host is powered on and running its workload, and stays that way
# on every step. What is sourced (Dell's iDRAC9 Security Configuration Guide,
# the iDRAC recovery KB 000120131, the reset KB 000126703, and the
# failed-update KB 000343194): firmware packages are
# signed and a package failing validation is aborted and logged; iDRAC keeps
# two operating-system images "to ensure a bootable iDRAC"; an iDRAC update or
# rollback needs no server reboot; a restart of the iDRAC is logged as RAC0182.
# What is illustrative: every timing, the version strings, the partition
# letters, the exact trigger of the fallback (modelled as the boot-time
# verification rejecting a staged image that was damaged in the flash write),
# the automatic switch between the two images (inferred from the two-image
# KB, whose mechanics Dell does not publish), and the RAC0182 reason text.

#: Example version strings only — the shape of real iDRAC9 versions.
RUNNING_VERSION = "7.10.30.00"
NEW_VERSION = "7.10.50.00"

#: The bound on the management-plane outage, in illustrative seconds. One
#: failed boot attempt plus one good boot of the previous image; the trace
#: must stay under it (``tests/test_firmware_rollback.py``).
MAX_MANAGEMENT_OUTAGE_S = 300

SCENARIO_IDS = ("bring-up", "firmware-update-rollback")


def _update_state(
    step: int,
    phase: str,
    label: str,
    description: str,
    active_regions: list[str],
    elapsed_seconds: int,
    *,
    power_watts: int = 6,
    progress_percent: int,
    cycle_cost: int = 1,
    writing_partition: str | None = None,
    signature_verified: bool,
    bootable_images: int = 2,
    management_reachable: bool = True,
    management_outage_seconds: int = 0,
    failed_regions: list[str] | None = None,
    log_entry: str | None = None,
) -> BringUpState:
    """One step of the update scenario. The three facts that never change are
    set here rather than at each call site: the host is powered, iDRAC runs
    from partition A, and the version it runs is the old one."""
    return BringUpState(
        step=step,
        phase=phase,
        label=label,
        description=description,
        active_regions=active_regions,
        power_watts=power_watts,
        progress_percent=progress_percent,
        elapsed_seconds=elapsed_seconds,
        cycle_cost=cycle_cost,
        host_powered=True,
        active_partition="A",
        running_version=RUNNING_VERSION,
        writing_partition=writing_partition,
        signature_verified=signature_verified,
        bootable_images=bootable_images,
        management_reachable=management_reachable,
        management_outage_seconds=management_outage_seconds,
        failed_regions=failed_regions or [],
        log_entry=log_entry,
    )


def simulate_firmware_rollback() -> list[BringUpState]:
    """An iDRAC firmware update that fails its boot check and rolls back, as
    pure data. The host never changes power state; nothing unverified is ever
    written, and nothing at all is written to the running partition; there is
    always a bootable image; and the management outage is bounded."""
    reboot_at = 210  # illustrative second at which management goes dark
    return [
        _update_state(
            0,
            "ready",
            "Steady state, host running",
            L(
                novice=(
                    "This story starts where the bring-up ended, with one "
                    "difference: the server itself is switched on and doing "
                    "its job. iDRAC, the small management computer inside "
                    "it, is watching sensors and answering its web page. Its "
                    f"software (version {RUNNING_VERSION}, an example number) "
                    "lives in a flash memory chip that is split into two "
                    "halves, called partitions. iDRAC runs from half A. Half "
                    "B holds the version before it, kept as a spare. Two "
                    "copies that can start is the safety net for everything "
                    "that follows."
                ),
                standard=(
                    "The scenario starts where the bring-up ends, with one "
                    "difference: the host is powered on and running its "
                    "workload. iDRAC is ready and watching, running firmware "
                    f"{RUNNING_VERSION} (an example version) from flash "
                    "partition A. Partition B holds the previous version. "
                    "Dell keeps two iDRAC operating-system images so that one "
                    "is always bootable, and that is the safety net for "
                    "every step that follows."
                ),
                expert=(
                    f"Host up, iDRAC ready on {RUNNING_VERSION} (example) "
                    "from partition A; B holds N-1. Two bootable images."
                ),
            ),
            ["soc", "monitor", "sb-i2c", "sb-espi", "nic"],
            0,
            progress_percent=0,
            signature_verified=False,
        ),
        _update_state(
            1,
            "upload",
            "Administrator uploads the update package",
            L(
                novice=(
                    "An administrator opens iDRAC's web page and uploads a "
                    f"new version of its software, {NEW_VERSION}. The file "
                    "travels over the management network port and is held in "
                    "iDRAC's working memory. Nothing has been written to the "
                    "flash chip yet. iDRAC lists the update as a job, which "
                    "is its word for a task it will carry out and report on. "
                    "The server keeps running; nobody using it can tell "
                    "anything is happening."
                ),
                standard=(
                    "An administrator uploads a Dell Update Package for "
                    f"firmware {NEW_VERSION} through the web console (Redfish "
                    "and RACADM, Dell's command-line tool, do the same). The "
                    "package arrives over the management NIC and sits in "
                    "DRAM. Nothing touches flash yet. iDRAC creates an "
                    "update job in its job queue. The host is unaffected: an "
                    "iDRAC update needs no server reboot."
                ),
                expert=(
                    f"DUP for {NEW_VERSION} uploaded via GUI/Redfish/RACADM "
                    "into DRAM; job queued. No flash write. Host unaffected."
                ),
            ),
            ["nic", "soc", "dram"],
            20,
            progress_percent=10,
            signature_verified=False,
            log_entry="Job queue: firmware update, status Downloading",
        ),
        _update_state(
            2,
            "verify",
            "Signature checked against the Root of Trust",
            L(
                novice=(
                    "Before iDRAC will write anything, it checks that the "
                    "file really came from Dell and was not altered on the "
                    "way. Dell signs every update, which works like a wax "
                    "seal that only Dell can make. iDRAC checks the seal "
                    "using keys locked into its security hardware, the Root "
                    "of Trust. A file with a broken or missing seal is "
                    "refused here and the refusal is written to the "
                    "Lifecycle log, iDRAC's permanent diary. This file "
                    "passes."
                ),
                standard=(
                    "Before anything is written, iDRAC verifies the "
                    "package's digital signature. Dell signs firmware "
                    "packages with SHA-256 hashing and 2048-bit RSA, and "
                    "iDRAC compares the signature to what the silicon Root "
                    "of Trust expects. Dell's own wording is that a package "
                    "which fails validation is aborted and an error is "
                    "logged to the Lifecycle Controller log. The published "
                    "message for that failure, RED007, unable to verify "
                    "update package signature, is documented for iDRAC7 and "
                    "iDRAC8; the check itself is the one iDRAC9 runs. This "
                    "package passes, so it is allowed to reach flash."
                ),
                expert=(
                    "Package signature (SHA-256, RSA-2048) verified against "
                    "the silicon RoT. Failure aborts with an LC log error "
                    "before any flash write (published as RED007 for "
                    "iDRAC7/8). Passes."
                ),
            ),
            ["rot", "soc", "dram"],
            35,
            progress_percent=25,
            signature_verified=True,
            log_entry="Job queue: firmware update, signature verified",
        ),
        _update_state(
            3,
            "stage",
            "Image written to the inactive partition",
            L(
                novice=(
                    "Now iDRAC writes the new software into the flash chip, "
                    "and where it writes matters more than anything else in "
                    "this story. It writes to half B, the spare, and the older "
                    "version that was kept there is erased. Half A, the "
                    "one iDRAC is running from right now, is not touched. "
                    "Had the update worked, half A would have become the "
                    "spare in its turn, and the copy to go back to. "
                    "While the write is under way half B is a mix of old and "
                    "new and could not start, so for these minutes there is "
                    "exactly one good copy. That is why the good copy is the "
                    "one left alone. This is the slowest step. The server "
                    "keeps working throughout."
                ),
                standard=(
                    "iDRAC writes the verified image to flash partition B, "
                    "the inactive one. The previous N-1 image in B is "
                    "overwritten, so from here any fallback is to the "
                    "running image in A. Partition A is never the target — "
                    "and had the update succeeded, A would have become the "
                    "prior trusted version Dell's rollback page offers. "
                    "During the write, B is "
                    "neither the old image nor the new one, so the count of "
                    "bootable images drops to one. That one is the running "
                    "partition, which is why it is left alone. The "
                    "Lifecycle log records SUP0516, updating firmware for "
                    "iDRAC. This is the longest stage, a few minutes on "
                    "real hardware. The host runs on."
                ),
                expert=(
                    "Verified image written to inactive partition B, "
                    "destroying the N-1 copy held there; A untouched. Bootable images: 1 for the duration of the "
                    "write. LC log SUP0516. Longest stage. Host unaffected."
                ),
            ),
            ["flash", "soc", "dram"],
            200,
            progress_percent=40,
            cycle_cost=5,
            writing_partition="B",
            signature_verified=True,
            bootable_images=1,
            log_entry=f"SUP0516: Updating firmware for iDRAC to version {NEW_VERSION}",
        ),
        _update_state(
            4,
            "stage",
            "New image marked for the next boot",
            L(
                novice=(
                    "The write finishes. iDRAC leaves itself a note: next "
                    "time you start, try half B. Half A still holds the "
                    "software iDRAC is running, unchanged. The count of "
                    "copies that can be started goes back up to two — but "
                    "read that counter carefully, because it is iDRAC's own "
                    "opinion. What iDRAC has actually checked is that the "
                    "package it was sent carried the right signature. "
                    "Whether the copy now sitting in half B will start has "
                    "not been tested, and cannot be until something tries to "
                    "start it. That gap is what this whole story is about. "
                    "One thing has gone wrong that nobody can see yet. In "
                    "this story a few bytes of the new copy were damaged as "
                    "they were written. That is our example of a fault, not "
                    "a description of a known Dell bug."
                ),
                standard=(
                    "The write completes and the bootloader is told to try "
                    "partition B on the next start. Partition A is "
                    "unchanged. The bootable-image count returns to two, and "
                    "the counter says so — iDRAC counts the staged image "
                    "because its signature verified, not because anything "
                    "has booted it. The boot check has not run yet, and that "
                    "gap is the subject of this trace. In this scenario the "
                    "count is wrong: the staged copy was damaged during the "
                    "flash write. The cause is illustrative. What matters is "
                    "that the package check in the verify phase cannot see "
                    "damage that happens after it, which is what the "
                    "boot-time check is for."
                ),
                expert=(
                    "Write complete; boot flag points at B; A unchanged. "
                    "Bootable count back to 2 on signature verification "
                    "alone — no boot check has run. Staged copy is silently "
                    "damaged (illustrative fault), which the package-level "
                    "check cannot see."
                ),
            ),
            ["flash", "soc"],
            205,
            progress_percent=60,
            signature_verified=True,
            log_entry="Job queue: firmware update, restarting iDRAC",
        ),
        _update_state(
            5,
            "reboot",
            "iDRAC restarts and management goes dark",
            L(
                novice=(
                    "To start using the new software, iDRAC has to restart "
                    "itself. For the next couple of minutes its web page "
                    "does not answer, remote control is gone, and no alerts "
                    "are sent. This is the cost of the update. Look at what "
                    "did not happen: the server did not restart. iDRAC and "
                    "the server are separate computers that share a box, "
                    "and only the small one is rebooting. The programs "
                    "running on the server carry on. The one thing people "
                    "in the room may notice is noise. iDRAC is what decides "
                    "how fast the fans spin, so with iDRAC away "
                    "administrators often report them running loud until it "
                    "comes back. Dell does not document that as part of an "
                    "update, so treat it as something people see rather "
                    "than a rule."
                ),
                standard=(
                    "iDRAC restarts to boot the new image. The web console, "
                    "Redfish, RACADM, the virtual console and alerting all "
                    "stop answering. This is the management-plane outage, "
                    "and the clock on it starts here. The host does not "
                    "reboot: iDRAC runs on its own processor, memory and "
                    "standby power, so restarting it takes nothing from the "
                    "workload. Dell's reset guidance says the same: only "
                    "the iDRAC reboots, and the running operating system is "
                    "not affected. iDRAC's thermal-control engine is also "
                    "away, and administrators commonly report the fans "
                    "ramping up until it returns. Dell documents a "
                    "full-speed ramp as a sign of a hard iDRAC reset, not "
                    "of an update, so that detail is reported behaviour "
                    "rather than a documented one."
                ),
                expert=(
                    "iDRAC reset to boot B. GUI, Redfish, RACADM, vKVM and "
                    "alerting down; outage clock starts. Host untouched. "
                    "Fan ramp commonly reported, not documented for updates."
                ),
            ),
            ["pwr"],
            reboot_at,
            power_watts=4,
            progress_percent=70,
            signature_verified=True,
            management_reachable=False,
            management_outage_seconds=0,
        ),
        _update_state(
            6,
            "bootcheck",
            "Root of Trust verifies the new image",
            L(
                novice=(
                    "iDRAC starts the same way it did on the day the server "
                    "was first plugged in. The small program built "
                    "permanently into the chip runs first, and the Root of "
                    "Trust checks the seal on the software in half B before "
                    "any of it is allowed to run. The check happens on "
                    "every start, not only after an update, so a copy that "
                    "was fine when it was uploaded still has to prove "
                    "itself now."
                ),
                standard=(
                    "The boot path is the one the bring-up trace shows: the "
                    "immutable boot ROM runs, and the silicon Root of Trust "
                    "verifies the image in partition B before any of it "
                    "executes. This check runs on every boot, which is what "
                    "lets it catch damage that happened after the package "
                    "was verified. Management is still dark. The host is "
                    "still running."
                ),
                expert=(
                    "Boot ROM, then RoT verification of the image in B "
                    "before execution. Management still down; host up."
                ),
            ),
            ["rot", "soc", "flash"],
            reboot_at + 8,
            power_watts=5,
            progress_percent=75,
            signature_verified=True,
            management_reachable=False,
            management_outage_seconds=8,
        ),
        _update_state(
            7,
            "bootcheck",
            "New image fails its boot check",
            L(
                novice=(
                    "The check fails. Half B is the spare half of iDRAC's "
                    "flash chip, where the update was written; the counters "
                    "call it partition B, and half A is partition A. The "
                    "software in half B does not match "
                    "its seal, so iDRAC refuses to run it. This is the "
                    "moment the design exists for. A copy that cannot be "
                    "trusted is never started, not even to see how far it "
                    "gets. Half B is marked as bad. The count of copies "
                    "that can start drops to one, and that one is half A, "
                    "which nothing has written to since before the update "
                    "began."
                ),
                standard=(
                    "Verification fails: the image in partition B does not "
                    "match its signature, and the Root of Trust refuses to "
                    "execute it. Partition B is marked not bootable. One "
                    "bootable image remains, and it is partition A, which "
                    "nothing has written to at any point in this trace. How "
                    "many attempts real firmware makes before giving up on "
                    "an image is not published, so the single attempt shown "
                    "here is illustrative."
                ),
                expert=(
                    "RoT rejects B; B marked not bootable. Bootable images: "
                    "1 (A, never written in this trace). Retry count "
                    "illustrative."
                ),
            ),
            ["rot", "soc"],
            reboot_at + 18,
            power_watts=5,
            progress_percent=80,
            signature_verified=True,
            bootable_images=1,
            management_reachable=False,
            management_outage_seconds=18,
            failed_regions=["flash"],
        ),
        _update_state(
            8,
            "rollback",
            "Bootloader falls back to the previous partition",
            L(
                novice=(
                    "Nobody has to do anything. The starting program turns "
                    "to half A on its own, and the Root of Trust checks "
                    "that copy in the same way. It passes, because it is "
                    "the software that was running a few minutes ago. This "
                    "automatic step back is called a rollback. No "
                    "technician, no cable and no visit to the server room "
                    "are needed, and the administrator, who cannot reach "
                    "iDRAC right now, could not have helped anyway."
                ),
                standard=(
                    "The bootloader falls back to partition A without "
                    "anyone asking it to, and the Root of Trust verifies "
                    "that image the same way. It passes. Dell documents two "
                    "iDRAC images kept to ensure a bootable iDRAC, and a "
                    "recovery mode entered only when both boot paths are "
                    "lost. The mechanics of the switch between them are not "
                    "published, so this step is our reading of that design. "
                    "The fallback has to be automatic, because at this "
                    "moment there is no management interface through which "
                    "an administrator could request it."
                ),
                expert=(
                    "Bootloader falls back to A; RoT verifies A; passes. "
                    "Automatic by necessity: no management path exists. "
                    "Switch mechanics inferred from Dell's two-image KB."
                ),
            ),
            ["rot", "soc", "flash"],
            reboot_at + 26,
            power_watts=5,
            progress_percent=82,
            signature_verified=True,
            bootable_images=1,
            management_reachable=False,
            management_outage_seconds=26,
            failed_regions=["flash"],
        ),
        _update_state(
            9,
            "rollback",
            "Previous firmware boots: kernel and services",
            L(
                novice=(
                    "From here it is an ordinary start of the old software: "
                    "the operating system comes up, the links to the "
                    "server's sensors reconnect, and the management "
                    "services start one by one. It takes about as long as "
                    "it did in the bring-up story. The outage clock is "
                    "still running, but there is a limit to how long it can "
                    "run: one failed try plus one normal start."
                ),
                standard=(
                    "From here it is the bring-up trace again on the old "
                    "image: embedded Linux boots, the sideband buses and "
                    "sensor monitoring reconnect, and the management "
                    "services and Lifecycle Controller initialize. The "
                    "outage is still counting, and it is bounded: one "
                    "failed boot attempt plus one normal boot."
                ),
                expert=(
                    "Normal boot of A: kernel, sideband, monitoring, "
                    "services, LC. Outage bounded at one failed attempt "
                    "plus one boot."
                ),
            ),
            ["soc", "dram", "flash", "sb-i2c", "sb-espi", "monitor"],
            reboot_at + 110,
            progress_percent=84,
            cycle_cost=3,
            signature_verified=True,
            bootable_images=1,
            management_reachable=False,
            management_outage_seconds=110,
            failed_regions=["flash"],
        ),
        _update_state(
            10,
            "restored",
            "iDRAC returns on the old version",
            L(
                novice=(
                    "iDRAC's web page answers again. The outage lasted "
                    "about two minutes in this example, and the server "
                    "worked through all of it. The administrator logs in "
                    "and sees the old version number, which is the first "
                    "sign that the update did not take. The Lifecycle log "
                    "explains why: it records that iDRAC restarted, and "
                    "that the update could not be applied."
                ),
                standard=(
                    "The web console, Redfish and RACADM answer again, and "
                    "the outage clock stops at about two minutes "
                    f"(illustrative). The version shown is {RUNNING_VERSION}"
                    ", not the one that was uploaded. The Lifecycle log "
                    "carries the sequence Dell's own failed-update KB "
                    "shows: SUP0516, updating firmware for iDRAC, then "
                    "RAC0182, the iDRAC firmware was rebooted with the "
                    "following reason, then SUP0520, unable to update the "
                    "iDRAC firmware. That KB describes an iDRAC10 case on "
                    "17G servers; the message identifiers are Dell's common "
                    "ones. The reason text varies on real systems. The "
                    "host's uptime counter did not reset."
                ),
                expert=(
                    "Management back after ~120 s (illustrative) on "
                    f"{RUNNING_VERSION}. LC log SUP0516, RAC0182, SUP0520 "
                    "(sequence published for an iDRAC10 case); job Failed. "
                    "Host uptime unbroken."
                ),
            ),
            ["soc", "nic", "kvm", "monitor"],
            reboot_at + 120,
            progress_percent=85,
            signature_verified=True,
            bootable_images=1,
            management_outage_seconds=120,
            failed_regions=["flash"],
            log_entry=(
                "RAC0182: The iDRAC firmware was rebooted with the following "
                "reason: unknown. SUP0520: Unable to update the iDRAC "
                f"firmware to version {NEW_VERSION}. Running {RUNNING_VERSION}"
            ),
        ),
        _update_state(
            11,
            "restored",
            "What is left for the administrator",
            L(
                novice=(
                    "The server is safe and iDRAC works, but the job is not "
                    "finished. Half B still holds the bad copy, so the "
                    "safety net is down to one good copy until someone "
                    "repairs it. The repair is to download the update from "
                    "Dell again and upload it again, which rewrites half B. "
                    "If both halves ever went bad, iDRAC could still be "
                    "rescued by putting its software on a memory card in "
                    "the server, but that needs someone standing at the "
                    "machine. Real failures are not always this tidy: Dell "
                    "has documented one where the management computer only "
                    "came back after the power cords were pulled."
                ),
                standard=(
                    "The system is safe but not whole: partition B holds a "
                    "rejected image, so one bootable image remains until "
                    "the administrator acts. The recovery action is to "
                    "download the package again and re-run the update, "
                    "which rewrites partition B. If iDRAC is sluggish after "
                    "the episode, racadm racreset restarts it, again "
                    "without touching the host. Had both images failed, "
                    "Dell's documented last resort is the bootloader's "
                    "recovery mode, which reloads firmware from an SD card "
                    "or a TFTP server. Not every real failure ends this "
                    "cleanly: Dell's KB 000343194 describes an iDRAC10 "
                    "update failure where an unresponsive iDRAC needed AC "
                    "power removed to recover."
                ),
                expert=(
                    "Safe, not whole: B rejected, one bootable image. "
                    "Re-download and re-stage to restore redundancy; "
                    "racreset if sluggish; SD/TFTP recovery mode is the "
                    "last resort if both images fail. Real cases can need "
                    "an AC cycle (KB 000343194)."
                ),
            ),
            ["soc", "nic", "monitor", "sb-i2c", "sb-espi"],
            reboot_at + 130,
            progress_percent=85,
            signature_verified=True,
            bootable_images=1,
            management_outage_seconds=120,
            failed_regions=["flash"],
            log_entry="Job queue: firmware update Failed; re-stage to repair partition B",
        ),
    ]


def simulate_scenario(scenario: str = "bring-up") -> list[BringUpState]:
    """The trace for a named scenario. Raises ``KeyError`` for an unknown id;
    the HTTP layer turns that into a 404."""
    if scenario == "bring-up":
        return simulate()
    if scenario == "firmware-update-rollback":
        return simulate_firmware_rollback()
    raise KeyError(scenario)
