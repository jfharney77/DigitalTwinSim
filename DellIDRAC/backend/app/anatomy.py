"""Subsystem-anatomy data: a functional block diagram of the iDRAC9 BMC.

Like the R760 app's anatomy.py, the subsystem is data, not code. ``ANATOMY``
describes iDRAC9 as blocks in a normalized coordinate space the frontend
renders as SVG. This is a *logical* diagram, not a die shot or a board
photo: the host side (sensors, CPUs, PSUs reached over sideband buses) is on
the left (x=0), the BMC core in the middle, and the outside world (management
network, remote-presence redirection, front-panel access) on the right
(x=100).

Per the project's scope guardrails: favor a correct mental model over exact
placement. iDRAC9 on PowerEdge 14G–16G is an embedded service processor with
its own SoC, DRAM, and flash, sharing the system board but powered from an
always-on standby domain so it runs whenever the server is plugged in.
"""

from __future__ import annotations

from .leveling import L
from .models import Block, Photo, SourceLink, Stat, SubsystemMap

P_IDRAC = Photo(
    url="/idrac9-console.svg",
    caption=(
        "iDRAC9 presents its management plane as an HTML5 web console, a "
        "Redfish REST API, a RACADM command line, and legacy IPMI/SNMP — all "
        "served by the embedded controller diagrammed here, reachable while "
        "the host is powered off."
    ),
    credit="Illustration for this teaching tool; not a Dell product image.",
)

_SIDEBAND_NOTE = (
    "iDRAC does not sit in the host's data path — it reaches host hardware "
    "over slow, always-available management buses that work with the CPUs "
    "powered off. That is what 'out-of-band' means: the management plane and "
    "the production plane are physically separate."
)

ANATOMY = SubsystemMap(
    id="idrac9",
    name="iDRAC9",
    vendor="Dell Technologies",
    form_factor="Baseboard management controller (embedded)",
    generation="iDRAC9 · PowerEdge 14G–16G",
    year=2017,
    width=100,
    height=52,
    overview=L(
        novice=(
            "Every Dell server contains a second, much smaller computer whose "
            "only job is to look after the first one. It is called a baseboard "
            "management controller, and the striking thing about it is that it "
            "runs even when the server itself is switched off — as long as the "
            "machine is plugged in, this little controller is awake. That is "
            "what lets an administrator on the other side of the world power a "
            "server on, watch it boot, install an operating system, or read its "
            "temperature, without anyone visiting the building. This twin "
            "follows that controller starting up, and the whole time you are "
            "watching, the actual server stays off. The power figures stay in "
            "single or low double digits for exactly that reason."
        ),
        plain=(
            "iDRAC9 is the always-on management controller embedded in every "
            "PowerEdge server. It runs on standby power, so it is working "
            "whenever the machine is plugged in — even with the host powered "
            "down — which is what makes remote power control, console access, "
            "firmware updates, and telemetry possible without anyone in the "
            "room. This trace is the controller's own bring-up, and the host "
            "never powers on during it, so the draw stays in single or low "
            "double-digit watts. Lifecycle Controller initialisation is the "
            "longest stage. Capability here is unlocked by licence tier rather "
            "than by adding hardware."
        ),
        standard=(
            "The integrated Dell Remote Access Controller (iDRAC) is the "
            "always-on service processor embedded on every PowerEdge server — a "
            "small, self-contained computer with its own SoC, memory, flash, "
            "operating system, and network port, soldered to the system board "
            "but powered from a separate standby rail. It boots seconds after AC "
            "is applied, long before the host, and lets an administrator manage "
            "the server 'out-of-band' — power it on or off, watch every sensor, "
            "redirect its console and virtual media, and update firmware — over "
            "the network, with the host CPUs switched off and no agent installed "
            "in the operating system. iDRAC9 is the 9th generation, shipping on "
            "PowerEdge 14th- through 16th-generation servers, paired with the "
            "embedded Lifecycle Controller for deployment and updates. This "
            "diagram is a logical block view: host-facing management buses on the "
            "left, the BMC core in the middle, the outside world on the right."
        ),
        technical=(
            "iDRAC9 bring-up on standby power, host held off throughout — the "
            "engine asserts BMC-domain draw stays ≤20 W across the trace. Phase "
            "order is standby → reset → bootloader → kernel → services → ready, "
            "with Lifecycle Controller init as the single longest stage. The "
            "anatomy is a functional block diagram rather than a floorplan: "
            "host-facing sideband buses left, SoC centre, external interfaces "
            "right. Capability scales by licence tier on identical silicon."
        ),
        expert=(
            "BMC bring-up on standby rails, host off throughout (≤20 W "
            "asserted). standby → reset → bootldr → kernel → services → ready; "
            "LC init holds max dwell. Functional block diagram, not a "
            "floorplan. Licence tier gates capability on fixed silicon."
        ),
    ),
    regions=[
        # --- Host side (left): the sideband buses into the server ---
        Block(
            id="sb-espi",
            kind="sideband",
            label="eSPI / PECI · host CPU & BIOS",
            x=2, y=2, w=20, h=13,
            description=(
                "The link to the host CPUs and firmware. Over eSPI (the "
                "Enhanced Serial Peripheral Interface that replaced LPC) and "
                "PECI (Platform Environment Control Interface) iDRAC reads CPU "
                "temperatures, collects POST codes and boot progress, and "
                "exchanges data with the UEFI/BIOS — so the web console can "
                "show exactly where the host is in POST. " + _SIDEBAND_NOTE
            ),
        ),
        Block(
            id="sb-i2c",
            kind="sideband",
            label="I2C / PMBus · sensors",
            x=2, y=17, w=20, h=13,
            description=(
                "The instrumentation bus. Over I2C and PMBus (the power-"
                "management variant of I2C) iDRAC walks the chassis: it reads "
                "every DIMM's SPD data, each PSU's capacity, wattage and "
                "firmware, the drive backplane, and dozens of thermal probes. "
                "This is the data behind the health tree and the fan-speed "
                "decisions. " + _SIDEBAND_NOTE
            ),
        ),
        Block(
            id="sb-ncsi",
            kind="sideband",
            label="NC-SI · shared LOM",
            x=2, y=32, w=20, h=13,
            description=(
                "NC-SI (Network Controller Sideband Interface) is the path "
                "that lets iDRAC borrow one of the host's LAN-on-Motherboard "
                "ports instead of using its own dedicated NIC — 'shared LOM'. "
                "iDRAC9 supports NC-SI 1.2. It is cheaper (no extra cable) but "
                "couples management traffic to a production port; the "
                "dedicated NIC keeps the two physically apart."
            ),
        ),
        # --- Center: the BMC core ---
        Block(
            id="dram",
            kind="memory",
            label="DDR4 working memory",
            x=30, y=2, w=34, h=4,
            description=(
                "Dedicated DRAM for the iDRAC SoC — the working memory the "
                "embedded Linux runs in, entirely separate from the host's "
                "system memory. It is initialized by the bootloader before "
                "the kernel can start."
            ),
        ),
        Block(
            id="soc",
            kind="soc",
            label="iDRAC SoC · service processor",
            x=30, y=8, w=34, h=22,
            description=(
                "The heart of iDRAC: a system-on-chip that is a complete "
                "computer in its own right, running an embedded Linux. It "
                "hosts every management interface — the HTML5 web GUI, the "
                "Redfish REST API, the RACADM command line, and legacy IPMI "
                "2.0 and SNMP — drives the sideband buses, and runs the "
                "monitoring and remote-presence engines. On PowerEdge this "
                "role is filled by a dedicated BMC ASIC on the system board. "
                "It runs whenever the server has AC, independent of the host."
            ),
        ),
        Block(
            id="flash",
            kind="memory",
            label="Flash · firmware + LC",
            x=30, y=32, w=16, h=6,
            description=(
                "Non-volatile flash holding iDRAC's own firmware image and "
                "the embedded Lifecycle Controller (LC) — Dell's on-board "
                "deployment and update engine, with its repository of drivers "
                "and its record of hardware inventory and configuration. "
                "Because LC lives here, a bare server with no OS and no media "
                "can still deploy an operating system and update firmware."
            ),
        ),
        Block(
            id="rot",
            kind="security",
            label="Root of Trust",
            x=48, y=32, w=16, h=6,
            description=(
                "A silicon-based cryptographic Root of Trust. At power-on it "
                "verifies iDRAC's own firmware signature before the SoC is "
                "allowed to run it, and anchors the chain that validates BIOS "
                "and other firmware — so tampered code is caught before it "
                "executes. It underpins System Lockdown and Secured Component "
                "Verification."
            ),
        ),
        Block(
            id="monitor",
            kind="sensor",
            label="Monitoring & thermal engine",
            x=30, y=40, w=20, h=8,
            description=(
                "The always-running engine that samples the sideband sensors, "
                "maintains the server's health tree, logs events to the "
                "Lifecycle Log, and closes the thermal loop — setting fan "
                "speeds from the temperatures it reads. Out-of-band "
                "performance monitoring and telemetry streaming are extensions "
                "of this block, gated by license."
            ),
        ),
        Block(
            id="pwr",
            kind="power",
            label="Standby power domain",
            x=52, y=40, w=12, h=8,
            description=(
                "iDRAC's power island. When AC is applied the PSUs bring up a "
                "small standby rail that feeds this domain — a few watts — so "
                "the SoC, its memory, and the management NIC run while the "
                "host's main rails stay off. This is why a plugged-in server "
                "is never truly 'off', and why you can reach iDRAC before you "
                "press power."
            ),
        ),
        # --- External side (right): the outside world ---
        Block(
            id="nic",
            kind="network",
            label="Dedicated 1GbE NIC",
            x=72, y=2, w=26, h=10,
            description=(
                "iDRAC's own network port — a dedicated RJ-45, separate from "
                "every host NIC, that carries only management traffic. It "
                "gets its own IP (DHCP or static) as services start, and is "
                "the front door for the web console, Redfish, RACADM over SSH, "
                "IPMI-over-LAN, and virtual media. Keeping it on an isolated "
                "management network is the standard secure deployment."
            ),
        ),
        Block(
            id="kvm",
            kind="io",
            label="Virtual Console (KVM)",
            x=72, y=14, w=26, h=10,
            description=(
                "The remote keyboard-video-mouse engine. It captures the "
                "host's video output and relays keyboard and mouse over the "
                "network, so an administrator sees the real console — BIOS "
                "setup, the boot menu, a kernel panic — from anywhere, as if "
                "standing at a crash cart. HTML5-based on iDRAC9; a licensed "
                "Enterprise feature."
            ),
        ),
        Block(
            id="vmedia",
            kind="io",
            label="Virtual Media",
            x=72, y=26, w=26, h=10,
            description=(
                "USB redirection: iDRAC presents an ISO image or a local "
                "drive to the host as if it were a USB CD/DVD or disk plugged "
                "into the front panel. Combined with Virtual Console it lets "
                "you install an operating system on a headless server across "
                "the world with no one in the datacenter. A licensed "
                "Enterprise feature."
            ),
        ),
        Block(
            id="direct",
            kind="io",
            label="iDRAC Direct + Quick Sync 2",
            x=72, y=38, w=26, h=10,
            description=(
                "Front-panel access paths. iDRAC Direct is a micro-USB port "
                "on the front of the server: plug a laptop in and reach the "
                "full iDRAC interface over USB, no network needed. Quick Sync "
                "2 is a Bluetooth/Wi-Fi module in the bezel that pairs with "
                "the OpenManage Mobile app so a technician can read status and "
                "configure the server from a phone at the rack."
            ),
        ),
    ],
    stats=[
        Stat(label="Role", value="Always-on baseboard management controller"),
        Stat(label="Generation", value="iDRAC9 · PowerEdge 14G–16G"),
        Stat(label="Interfaces", value="Web GUI, Redfish, RACADM, IPMI 2.0, SNMP"),
        Stat(label="Management NIC", value="Dedicated 1GbE or shared LOM (NC-SI 1.2)"),
        Stat(label="Boots in", value="~30–60 s after AC, before the host"),
        Stat(label="Licenses", value="Basic · Express · Enterprise · Datacenter"),
    ],
    sources=[
        SourceLink(
            label="iDRAC9 User's Guide — Overview of iDRAC (Dell)",
            url="https://www.dell.com/support/manuals/en-us/idrac9-lifecycle-controller-v4.x-series/idrac9_4.00.00.00_ug_new/overview-of-idrac",
        ),
        SourceLink(
            label="Licensed features in iDRAC9 (Dell User's Guide)",
            url="https://www.dell.com/support/manuals/en-us/idrac9-lifecycle-controller-v3.1-series/idrac_3.15.15.15_ug/licensed-features-in-idrac9",
        ),
        SourceLink(
            label="Dedicated NIC and shared LOM (iDRAC9 Security Configuration Guide)",
            url="https://www.dell.com/support/manuals/en-us/idrac9-lifecycle-controller-v5.x-series/idrac9_security_configuration_guide/dedicated-nic-and-shared-lom",
        ),
        SourceLink(
            label="Support for iDRAC9 (Dell knowledge base)",
            url="https://www.dell.com/support/kbdoc/en-us/000178016/support-for-integrated-dell-remote-access-controller-9-idrac9",
        ),
    ],
    photo=P_IDRAC,
)
