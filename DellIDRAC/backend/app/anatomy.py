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

# The same point in the tour's level-1 register, so a reader who has just
# heard it narrated meets the same words when they click the block.
_SIDEBAND_NOTE_NOVICE = (
    "Links like this one are called out-of-band, because they work even while "
    "the server's main processors are switched off — which is exactly how "
    "they are right now. The wires that look after the machine and the wires "
    "that do the machine's actual work are kept separate."
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
            "but powered from a separate standby rail. It starts booting seconds after AC "
            "is applied and is ready within about two minutes, before the host "
            "is powered on, and lets an administrator manage "
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
            label=L(
                standard="eSPI / PECI · host CPU & BIOS",
                novice="CPU + BIOS wires (eSPI/PECI)",
            ),
            x=2, y=2, w=20, h=13,
            description=L(
                novice=(
                    "This is the wire that talks to the server's main "
                    "processors and to the start-up software they run. Over it "
                    "the iDRAC reads how hot each processor is, and watches the "
                    "server's start-up tick past each of its checks — which is "
                    "how the web page can tell you exactly where a server has "
                    "got stuck. The two names on the label are the two kinds of "
                    "wire: eSPI carries the conversation with the start-up "
                    "software, PECI carries the processor temperatures. "
                    + _SIDEBAND_NOTE_NOVICE
                ),
                standard=(
                    "The link to the host CPUs and firmware. Over eSPI (the "
                    "Enhanced Serial Peripheral Interface that replaced LPC) and "
                    "PECI (Platform Environment Control Interface) iDRAC reads CPU "
                    "temperatures, collects POST codes and boot progress, and "
                    "exchanges data with the UEFI/BIOS — so the web console can "
                    "show exactly where the host is in POST. " + _SIDEBAND_NOTE
                ),
                expert=(
                    "eSPI (LPC successor) to the UEFI/BIOS for POST codes and "
                    "boot progress; PECI for CPU thermals. Out-of-band: usable "
                    "with the host CPUs unpowered."
                ),
            ),
        ),
        Block(
            id="sb-i2c",
            kind="sideband",
            label=L(
                standard="I2C / PMBus · sensors",
                novice="sensor wires (I2C / PMBus)",
            ),
            x=2, y=17, w=20, h=13,
            description=L(
                novice=(
                    "This is the wire that reads the sensors. The iDRAC walks "
                    "round the inside of the server over it, asking each part "
                    "what it is and how it is doing: every memory stick, every "
                    "power supply, the tray the disks plug into, and dozens of "
                    "temperature probes. Everything the health page shows you "
                    "arrived this way, and so did the numbers the iDRAC uses to "
                    "decide how fast the fans should spin. The two names on the "
                    "label are the wire itself and the version of it the power "
                    "supplies speak. " + _SIDEBAND_NOTE_NOVICE
                ),
                standard=(
                    "The instrumentation bus. Over I2C and PMBus (the power-"
                    "management variant of I2C) iDRAC walks the chassis: it reads "
                    "every DIMM's SPD data, each PSU's capacity, wattage and "
                    "firmware, the drive backplane, and dozens of thermal probes. "
                    "This is the data behind the health tree and the fan-speed "
                    "decisions. " + _SIDEBAND_NOTE
                ),
                expert=(
                    "I2C plus PMBus for the PSUs: DIMM SPD, PSU capacity and "
                    "firmware, backplane, thermal probes. Feeds the health tree "
                    "and the fan loop. Out-of-band."
                ),
            ),
        ),
        Block(
            id="sb-ncsi",
            kind="sideband",
            label=L(
                standard="NC-SI · shared LOM",
                novice="borrowed host port (NC-SI)",
            ),
            x=2, y=32, w=20, h=13,
            description=L(
                novice=(
                    "This is the wire that lets the iDRAC borrow one of the "
                    "server's own network ports, instead of using the port of "
                    "its own on the right-hand side of the map. Borrowing is "
                    "cheaper, because it saves running a second cable to the "
                    "rack. The cost is that the traffic used to manage the "
                    "server now shares a port with the server's ordinary work, "
                    "so anyone who can reach that port is a step closer to the "
                    "controls. The iDRAC's own port keeps the two apart. NC-SI "
                    "is simply the name of this borrowing arrangement."
                ),
                standard=(
                    "NC-SI (Network Controller Sideband Interface) is the path "
                    "that lets iDRAC borrow one of the host's LAN-on-Motherboard "
                    "ports instead of using its own dedicated NIC — 'shared LOM'. "
                    "iDRAC9 supports the NC-SI 1.2 specification from firmware "
                    "7.00.00.00. It is cheaper (no extra cable) but "
                    "couples management traffic to a production port; the "
                    "dedicated NIC keeps the two physically apart."
                ),
                expert=(
                    "Shared-LOM path: NC-SI 1.2 from firmware 7.00.00.00. "
                    "Saves a cable, couples the management plane to a "
                    "production port. Dedicated NIC keeps them separate."
                ),
            ),
        ),
        # --- Center: the BMC core ---
        Block(
            id="dram",
            kind="memory",
            label=L(
                standard="Dedicated DRAM · working memory",
                novice="its own working memory",
            ),
            x=30, y=2, w=34, h=4,
            description=L(
                novice=(
                    "Memory that belongs to the iDRAC alone. It is where the "
                    "iDRAC's own small operating system does its thinking "
                    "while it runs, and it is nothing to do with the memory "
                    "sticks the server itself uses — those stay switched off "
                    "the whole time you are watching this. Memory like this "
                    "forgets everything the moment the power goes, so it has "
                    "to be woken up and made ready early in the start-up, "
                    "before the iDRAC's operating system can load into it. "
                    "Dell does not publish how much of it there is, so the "
                    "block is drawn plain."
                ),
                standard=(
                    "Dedicated DRAM for the iDRAC SoC — the working memory the "
                    "embedded Linux runs in, entirely separate from the host's "
                    "system memory. It is initialized by the bootloader before "
                    "the kernel can start. Dell does not publish the memory type "
                    "or size, so the block is drawn generically."
                ),
                expert=(
                    "BMC-private DRAM, initialised by the bootloader before "
                    "kernel start. Not host system memory. Type and size "
                    "unpublished; drawn generically."
                ),
            ),
        ),
        Block(
            id="soc",
            kind="soc",
            label=L(
                standard="iDRAC SoC · service processor",
                novice="the iDRAC's own chip",
            ),
            x=30, y=8, w=34, h=22,
            description=L(
                novice=(
                    "The iDRAC's own processor chip, and the reason people "
                    "say the iDRAC is a computer hiding inside a computer: it "
                    "runs its own small operating system, quite separate from "
                    "whatever the server is running. Everything an "
                    "administrator uses to reach the machine is served from "
                    "here — the web page, the ways of driving it by typed "
                    "command or by another program, and the older tools some "
                    "sites still rely on. It also drives the wires on the "
                    "left of the map, and it works whenever the server is "
                    "plugged in, whether or not the server itself is on."
                ),
                standard=(
                    "The heart of iDRAC: a system-on-chip that is a complete "
                    "computer in its own right, running an embedded Linux. It "
                    "hosts every management interface — the HTML5 web GUI, the "
                    "Redfish REST API, the RACADM command line, and legacy IPMI "
                    "2.0 and SNMP — drives the sideband buses, and runs the "
                    "monitoring and remote-presence engines. On PowerEdge this "
                    "role is filled by a dedicated BMC ASIC on the system board. "
                    "It runs whenever the server has AC, independent of the host."
                ),
                expert=(
                    "BMC ASIC running embedded Linux: web GUI, Redfish, "
                    "RACADM, IPMI 2.0 and SNMP, the sideband drivers, and the "
                    "monitoring and remote-presence engines. Alive on AC, "
                    "independent of host power state."
                ),
            ),
        ),
        Block(
            id="flash",
            kind="memory",
            label=L(
                standard="Flash · firmware + LC",
                novice="firmware storage chip",
            ),
            x=30, y=32, w=16, h=6,
            description=L(
                novice=(
                    "A storage chip that keeps its contents with the power "
                    "off. Two things live in it: the iDRAC's own software, and "
                    "a set-up tool called the Lifecycle Controller, which holds "
                    "drivers, a record of every part in the server, and the "
                    "settings someone chose. Because that tool sits in here "
                    "rather than on a disk, a brand new server with no "
                    "operating system and no install disk can still have one "
                    "installed, and can update its own software."
                ),
                standard=(
                    "Non-volatile flash holding iDRAC's own firmware image and "
                    "the embedded Lifecycle Controller (LC) — Dell's on-board "
                    "deployment and update engine, with its repository of drivers "
                    "and its record of hardware inventory and configuration. "
                    "Because LC lives here, a bare server with no OS and no media "
                    "can still deploy an operating system and update firmware."
                ),
                expert=(
                    "Non-volatile store: iDRAC firmware image plus the embedded "
                    "Lifecycle Controller — driver repository, hardware "
                    "inventory, configuration. Backs bare-metal deploy and "
                    "firmware update with no OS and no media."
                ),
            ),
        ),
        Block(
            id="rot",
            kind="security",
            label=L(
                standard="Root of Trust",
                novice="signature check chip",
            ),
            x=48, y=32, w=16, h=6,
            description=L(
                novice=(
                    "A small piece of silicon that checks signatures. Before "
                    "the iDRAC is allowed to run its own software, this chip "
                    "checks that the software still carries Dell's unforgeable "
                    "mark and has not been altered by anyone. Software that "
                    "fails the check is never started, so tampering is caught "
                    "before it can do anything rather than after. The same "
                    "check is then used to vouch for the server's own start-up "
                    "software, which is why this block is drawn underneath "
                    "everything else: it is the thing the rest is trusted on."
                ),
                standard=(
                    "A silicon-based cryptographic Root of Trust. At power-on it "
                    "verifies iDRAC's own firmware signature before the SoC is "
                    "allowed to run it, and anchors the chain that validates BIOS "
                    "and other firmware — so tampered code is caught before it "
                    "executes. It underpins System Lockdown and Secured Component "
                    "Verification."
                ),
                expert=(
                    "Silicon RoT: firmware signature verified before the SoC "
                    "executes it, anchoring the chain on to BIOS and other "
                    "firmware. Underpins System Lockdown and Secured Component "
                    "Verification."
                ),
            ),
        ),
        Block(
            id="monitor",
            kind="sensor",
            label=L(
                standard="Monitoring & thermal engine",
                novice="sensor watch + fan speed",
            ),
            x=30, y=40, w=20, h=8,
            description=L(
                novice=(
                    "The part that never stops watching. It reads the sensors "
                    "over the wires on the left, keeps the picture of the "
                    "server's health that the web page shows, writes anything "
                    "notable into a permanent log, and decides how fast the "
                    "fans should spin from the temperatures it is seeing. "
                    "Because it is this controller that sets the fan speed, "
                    "the fans are one of the few things in the server that "
                    "carry on being managed while nothing else in the machine "
                    "is running. Richer versions of this watching are unlocked "
                    "by paying for a higher licence, not by adding parts."
                ),
                standard=(
                    "The always-running engine that samples the sideband sensors, "
                    "maintains the server's health tree, logs events to the "
                    "Lifecycle Log, and closes the thermal loop — setting fan "
                    "speeds from the temperatures it reads. Out-of-band "
                    "performance monitoring and telemetry streaming are extensions "
                    "of this block, gated by license."
                ),
                expert=(
                    "Samples the sideband sensors, maintains the health tree, "
                    "writes the Lifecycle Log, closes the thermal loop. "
                    "Out-of-band performance monitoring and telemetry "
                    "streaming extend it, gated by licence tier."
                ),
            ),
        ),
        Block(
            id="pwr",
            kind="power",
            label=L(
                standard="Standby power",
                novice="always-on power",
            ),
            x=52, y=40, w=12, h=8,
            description=L(
                novice=(
                    "The trickle of power that keeps the iDRAC alive. When "
                    "the cords go in, the server's power supplies bring up a "
                    "small always-on supply — a few watts — and it feeds only "
                    "this corner of the machine: the iDRAC's chip, its memory "
                    "and its network port. The lines that feed the server "
                    "proper stay dead until somebody asks for them. That is "
                    "why a plugged-in server is never really off, and why an "
                    "administrator can reach it and turn it on from far away."
                ),
                standard=(
                    "iDRAC's power island. When AC is applied the PSUs bring up a "
                    "small standby rail that feeds this domain — a few watts — so "
                    "the SoC, its memory, and the management NIC run while the "
                    "host's main rails stay off. This is why a plugged-in server "
                    "is never truly 'off', and why you can reach iDRAC before you "
                    "press power."
                ),
                expert=(
                    "Standby rail, a few watts, feeding the SoC, its DRAM and "
                    "the management NIC while the host rails stay down. The "
                    "reason remote power-on exists."
                ),
            ),
        ),
        # --- External side (right): the outside world ---
        Block(
            id="nic",
            kind="network",
            label=L(
                standard="Dedicated 1GbE NIC",
                novice="its own network port",
            ),
            x=72, y=2, w=26, h=10,
            description=L(
                novice=(
                    "The iDRAC's own network socket, separate from all of the "
                    "server's normal ones, carrying only the traffic used to "
                    "manage the machine. It picks up an address on the network "
                    "as the iDRAC finishes starting, and from that moment it is "
                    "the front door: the web page, the remote screen, and the "
                    "ways of driving the iDRAC by command or by program all "
                    "arrive here. The alternative is to borrow a host port over "
                    "the link at the bottom left of the map. Most sites put "
                    "this port on a network of its own, reachable only by the "
                    "people who administer the machines."
                ),
                standard=(
                    "iDRAC's own network port — a dedicated RJ-45, separate from "
                    "every host NIC, that carries only management traffic. It "
                    "gets its own IP (DHCP or static) as services start, and is "
                    "the front door for the web console, Redfish, RACADM over SSH, "
                    "IPMI-over-LAN, and virtual media. Keeping it on an isolated "
                    "management network is the standard secure deployment."
                ),
                expert=(
                    "Dedicated RJ-45, management traffic only; DHCP or static. "
                    "Front door for the web console, Redfish, RACADM over SSH, "
                    "IPMI-over-LAN and virtual media. Isolated management VLAN "
                    "is the standard deployment; NC-SI shared LOM is the "
                    "alternative."
                ),
            ),
        ),
        Block(
            id="kvm",
            kind="io",
            label=L(
                standard="Virtual Console (KVM)",
                novice="remote screen + keyboard",
            ),
            x=72, y=14, w=26, h=10,
            description=L(
                novice=(
                    "The part that gives you the server's screen. It picks up "
                    "whatever the server would be sending to a monitor and "
                    "sends it over the network to a browser, and it carries "
                    "your keystrokes and mouse the other way. So you see the "
                    "real screen — the start-up settings, the menu that picks "
                    "what to boot, or the message a crashed machine has left "
                    "on it — from anywhere, exactly as if you had wheeled a "
                    "screen and keyboard up to the rack. It is part of the "
                    "more expensive licences rather than the basic one."
                ),
                standard=(
                    "The remote keyboard-video-mouse engine. It captures the "
                    "host's video output and relays keyboard and mouse over the "
                    "network, so an administrator sees the real console — BIOS "
                    "setup, the boot menu, a kernel panic — from anywhere, as if "
                    "standing at a crash cart. HTML5-based on iDRAC9; a licensed "
                    "Enterprise feature."
                ),
                expert=(
                    "KVM redirection: host video out, keyboard and mouse in, "
                    "over the management network. HTML5 on iDRAC9; Enterprise "
                    "licence."
                ),
            ),
        ),
        Block(
            id="vmedia",
            kind="io",
            label=L(
                standard="Virtual Media",
                novice="remote CD / USB drive",
            ),
            x=72, y=26, w=26, h=10,
            description=L(
                novice=(
                    "The part that lends the server a disc drive it does not "
                    "have. A file on your own laptop — the sort of disc image "
                    "an operating system is shipped as — is presented to the "
                    "server as though someone had walked up and plugged a "
                    "CD or a memory stick into the front of it. Put that "
                    "together with the remote screen and you can install an "
                    "operating system on a bare machine on the other side of "
                    "the world, with nobody in the building. It belongs to "
                    "the more expensive licences."
                ),
                standard=(
                    "USB redirection: iDRAC presents an ISO image or a local "
                    "drive to the host as if it were a USB CD/DVD or disk plugged "
                    "into the front panel. Combined with Virtual Console it lets "
                    "you install an operating system on a headless server across "
                    "the world with no one in the datacenter. A licensed "
                    "Enterprise feature."
                ),
                expert=(
                    "USB redirection of an ISO or local drive as a front-panel "
                    "CD/DVD or disk. With Virtual Console, bare-metal OS "
                    "install with nobody on site. Enterprise licence."
                ),
            ),
        ),
        Block(
            id="direct",
            kind="io",
            label=L(
                standard="iDRAC Direct + Quick Sync 2",
                novice="plug-in + phone access",
            ),
            x=72, y=38, w=26, h=10,
            description=L(
                novice=(
                    "The two ways in for somebody standing at the rack. One "
                    "is a small socket on the front of the server: plug a "
                    "laptop into it with an ordinary cable and you get the "
                    "whole iDRAC, with no network involved at all — which is "
                    "how a machine that has not been given a network address "
                    "yet gets set up. The other is a wireless module in the "
                    "front panel that pairs with a Dell phone app, so an "
                    "engineer can read the machine's status and change its "
                    "settings from a phone while standing in front of it."
                ),
                standard=(
                    "Front-panel access paths. iDRAC Direct is a micro-USB port "
                    "on the front of the server: plug a laptop in and reach the "
                    "full iDRAC interface over USB, no network needed. Quick Sync "
                    "2 is a Bluetooth/Wi-Fi module in the bezel that pairs with "
                    "the OpenManage Mobile app so a technician can read status and "
                    "configure the server from a phone at the rack."
                ),
                expert=(
                    "iDRAC Direct: front micro-USB, full interface, no "
                    "network. Quick Sync 2: bezel Bluetooth/Wi-Fi paired to "
                    "OpenManage Mobile for status and config at the rack."
                ),
            ),
        ),
    ],
    stats=[
        Stat(label="Role", value="Always-on baseboard management controller"),
        Stat(label="Generation", value="iDRAC9 · PowerEdge 14G–16G (17G moves to iDRAC10)"),
        Stat(label="Interfaces", value="Web GUI, Redfish, RACADM, IPMI 2.0, SNMP"),
        Stat(label="Management NIC", value="Dedicated 1GbE or shared LOM (NC-SI 1.2 from firmware 7.00)"),
        Stat(label="Boots in", value="~1–2 min after AC (Dell guidance); trace timing illustrative"),
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
            label="iDRAC9 7.00.00.00 Release Notes — NC-SI 1.2 support (Dell)",
            url="https://www.dell.com/support/manuals/en-us/idrac9-lifecycle-controller-v7.x-series/idrac9_pub_rn_7.00.00.00/idrac9-release-notes",
        ),
        SourceLink(
            label="How to reset and power-drain a PowerEdge — wait about two minutes for iDRAC to initialize (Dell knowledge base)",
            url="https://www.dell.com/support/kbdoc/en-us/000175625/how-do-i-reset-and-drain-power-of-my-dell-poweredge-server",
        ),
        SourceLink(
            label="Support for iDRAC9 (Dell knowledge base)",
            url="https://www.dell.com/support/kbdoc/en-us/000178016/support-for-integrated-dell-remote-access-controller-9-idrac9",
        ),
    ],
    photo=P_IDRAC,
)
