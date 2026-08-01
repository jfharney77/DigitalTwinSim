"""Pure boot-sequence engine for the PowerSwitch E3200-ON.

``simulate()`` returns the deterministic trace of what happens inside the
switch from the moment the AC cords are connected until it is forwarding
traffic at line rate. Same purity rule as the other twins: no FastAPI, no IO,
no timers — the frontend owns the playback clock, and each ``BootState`` is
plain data the renderer consumes. ``cycle_cost`` marks the long stages (the
network-OS boot) so the UI dwells on them.

The distinctive part is the '-ON' (Open Networking) path: the hardware boots
ONIE (the Open Network Install Environment, a small bootloader-cum-installer),
which hands off to a disaggregated network OS — SmartFabric OS10 on the
E3224F, Enterprise SONiC on the E3248 models — which then programs the
switching ASIC. Wattages and timings are illustrative but plausible for a
PoE edge switch; per the project's scope guardrails, favor a correct mental
model over measured numbers. Power draw here is dominated by the PoE budget
handed to attached devices, not the switch's own consumption.
"""

from __future__ import annotations

from .leveling import L
from .models import BootState

_FANS = [f"fan-{i}" for i in range(4)]


def simulate() -> list[BootState]:
    """The E3200's journey from AC plug-in to line-rate forwarding, as pure
    data."""
    return [
        BootState(
            step=0,
            phase="off",
            label="AC disconnected",
            description=L(
                novice=(
                    "The switch sits unplugged in a wiring closet. No power, no "
                    "link lights, nothing moving between the machines connected to "
                    "it. Both of its power-supply bays are dark. A network switch "
                    "is the box that lets everything in a building talk to "
                    "everything else, and right now it is doing none of that."
                ),
                plain=(
                    "The switch sits unplugged in a wiring closet. There is no "
                    "power, no link lights, and nothing being forwarded between the "
                    "devices connected to it. Both power-supply bays are dark."
                ),
                standard=(
                    "The switch is unplugged in the wiring closet. No power, no "
                    "link lights, nothing forwarding. Both power-supply bays are "
                    "dark."
                ),
                technical=(
                    "Unpowered in the closet. No rails, no link state, no "
                    "forwarding; both PSU bays dark."
                ),
                expert=(
                    "Unpowered. No rails, no links, no forwarding."
                ),
            ),
            active_regions=[],
            power_watts=0,
            fan_percent=0,
            elapsed_seconds=0,
        ),
        BootState(
            step=1,
            phase="standby",
            label="Standby rail up",
            description=L(
                novice=(
                    "A power cord is connected. The power supply notices there is "
                    "voltage and brings up a small trickle of standby power — a few "
                    "watts, just enough to wake the logic that will start the boot "
                    "process. The main power that feeds the switching chip and the "
                    "power-over-Ethernet circuitry stays off for the moment."
                ),
                plain=(
                    "A power cord is connected. The 80 PLUS Platinum power supply "
                    "detects line voltage and brings up a small standby rail — a "
                    "few watts — enough to wake the boot logic. The main rails "
                    "feeding the ASIC and PoE stay off for now."
                ),
                standard=(
                    "A power cord is connected. The 80 PLUS Platinum power supply "
                    "detects line voltage and brings up a small standby rail — a "
                    "few watts — enough to wake the boot logic. The main rails that "
                    "feed the ASIC and PoE stay off for now."
                ),
                technical=(
                    "AC applied; the PSU detects line voltage and raises the "
                    "standby rail — single-digit watts, sufficient to wake boot "
                    "logic. ASIC and PoE rails remain down."
                ),
                expert=(
                    "Standby rail up on AC detect. ASIC and PoE rails down."
                ),
            ),
            active_regions=["psu-1", "psu-2"],
            power_watts=15,
            fan_percent=0,
            elapsed_seconds=2,
        ),
        BootState(
            step=2,
            phase="poweron",
            label="Main rails · CPU · fans",
            description=L(
                novice=(
                    "The main power comes up. The switch's control processor powers "
                    "on, and all the fans briefly spin to full speed — the safe "
                    "default until the firmware has read the temperature sensors — "
                    "before dropping to a managed speed. The switch is now a small "
                    "computer starting to boot. It has not looked at a single "
                    "packet of network traffic yet."
                ),
                plain=(
                    "The main power comes up. The four-core control processor "
                    "starts, and every fan briefly runs to full speed — the safe "
                    "default until the firmware has read the temperature sensors — "
                    "before settling to a managed speed. What is booting here is a "
                    "small computer; it has not yet looked at a single packet of "
                    "network traffic."
                ),
                standard=(
                    "The main rails come up. The 4-core control-plane CPU powers "
                    "on, and all fans briefly spin to full — the safe default "
                    "until firmware has read the thermal sensors — before dropping "
                    "to a managed speed. The switch is now a small computer "
                    "starting to boot; it has not looked at a single packet yet."
                ),
                technical=(
                    "Main rails up; the 4-core control-plane CPU powers on and fans "
                    "go to full as the pre-sensor default before settling to "
                    "managed speed. At this point the device is a Linux host that "
                    "has not yet touched a packet."
                ),
                expert=(
                    "Main rails up, control-plane CPU on, fans full then managed. A "
                    "Linux host; no packets yet."
                ),
            ),
            active_regions=["psu-1", "psu-2", "cpu", *_FANS],
            power_watts=110,
            fan_percent=100,
            elapsed_seconds=6,
            cycle_cost=2,
        ),
        BootState(
            step=3,
            phase="poweron",
            label="System inventory",
            description=L(
                novice=(
                    "Before the network operating system loads, the platform "
                    "firmware takes stock of the hardware over internal management "
                    "links: it reads both power supplies' wattage and health, the "
                    "fan modules, the optical transceivers in their cages, and the "
                    "power-over-Ethernet controllers — which is how it works out "
                    "how much power budget the installed supplies will allow it to "
                    "hand out to connected devices."
                ),
                plain=(
                    "Before the network OS loads, the platform firmware inventories "
                    "the hardware over internal management buses: both power "
                    "supplies' wattage and health, the fan modules, the optics in "
                    "the SFP/QSFP cages, and the PoE controllers — establishing how "
                    "much PoE budget the installed PSUs will allow."
                ),
                standard=(
                    "Before the network OS loads, the platform firmware inventories "
                    "the hardware over internal management buses: it reads both "
                    "power supplies' wattage and health, the fan modules, the "
                    "optics in the SFP/QSFP cages, and the PoE controllers — "
                    "establishing how much PoE budget the installed PSUs will "
                    "allow."
                ),
                technical=(
                    "Platform firmware inventories over internal management buses "
                    "ahead of the NOS: PSU wattage and health, fan modules, optics "
                    "presence in the SFP/QSFP cages, and the PoE controllers. The "
                    "PSU inventory is what determines the available PoE budget."
                ),
                expert=(
                    "Pre-NOS inventory over management buses: PSU wattage/health, "
                    "fans, cage optics, PoE controllers. PSU inventory sets the PoE "
                    "budget."
                ),
            ),
            active_regions=["cpu", "mgmt-panel", "psu-1", "psu-2", "poe-system"],
            power_watts=125,
            fan_percent=60,
            elapsed_seconds=20,
        ),
        BootState(
            step=4,
            phase="onie",
            label="ONIE bootloader",
            description=L(
                novice=(
                    "A small open installer runs. This is what the '-ON' in the "
                    "product name means: instead of a fixed operating system welded "
                    "to the hardware by the manufacturer, the switch boots a "
                    "standard installer that either launches whichever network "
                    "operating system is already in flash or, on a factory-fresh "
                    "unit, fetches and installs one over the network. It is the "
                    "layer that lets the same silicon run software from different "
                    "suppliers."
                ),
                plain=(
                    "ONIE — the Open Network Install Environment — runs. This is "
                    "what the '-ON' in E3200-ON means: instead of a fixed vendor "
                    "OS, the switch boots a small open installer that either "
                    "launches the network OS already in flash or, on a "
                    "factory-fresh unit, fetches and installs one over the network. "
                    "It is the disaggregation layer that lets the same silicon run "
                    "OS10 or SONiC."
                ),
                standard=(
                    "ONIE — the Open Network Install Environment — runs. This is "
                    "what the '-ON' in E3200-ON means: instead of a fixed vendor "
                    "OS, the switch boots a small open installer that either "
                    "launches the network OS already installed in flash, or, on a "
                    "factory-fresh unit, fetches and installs one over the network. "
                    "It is the disaggregation layer that lets the same silicon run "
                    "OS10 or SONiC."
                ),
                technical=(
                    "ONIE executes — the disaggregation layer behind the '-ON' "
                    "designation. Rather than a vendor-welded OS, an open installer "
                    "either chain-loads the resident NOS from flash or, on a "
                    "factory unit, retrieves and installs one over the network. The "
                    "same silicon therefore runs OS10 or SONiC."
                ),
                expert=(
                    "ONIE: chain-loads the resident NOS or network-installs on a "
                    "factory unit. The disaggregation layer — same silicon, OS10 or "
                    "SONiC."
                ),
            ),
            active_regions=["cpu"],
            power_watts=135,
            fan_percent=55,
            elapsed_seconds=35,
            cycle_cost=2,
        ),
        BootState(
            step=5,
            phase="nos",
            label="Network OS boots (OS10 / SONiC)",
            description=L(
                novice=(
                    "The longest stage. The installer hands off to the installed "
                    "network operating system and a full Linux control plane boots: "
                    "the kernel first, then the switching software and its "
                    "databases. This is where a switch spends most of its start-up "
                    "time, apparently doing nothing — exactly as a server does "
                    "while it tunes its memory."
                ),
                plain=(
                    "The longest stage. The installer hands off to whichever "
                    "network operating system is installed — SmartFabric OS10 on "
                    "the E3224F, Enterprise SONiC on the E3248 models — and a "
                    "complete Linux control plane boots: the kernel first, then the "
                    "switching software and its state databases. Most of a switch's "
                    "boot time is spent right here, looking idle, in the same way a "
                    "server does while it trains memory."
                ),
                standard=(
                    "The longest stage. ONIE hands off to the installed network "
                    "operating system — SmartFabric OS10 on the E3224F, Enterprise "
                    "SONiC on the E3248 models — and a full Linux control plane "
                    "boots: kernel, then the switching stack and databases. This "
                    "is where a switch spends most of its boot time, apparently "
                    "idle, exactly as a server does during memory training."
                ),
                technical=(
                    "Max-dwell stage. ONIE hands off to the resident NOS — "
                    "SmartFabric OS10 on the E3224F, Enterprise SONiC on the E3248 "
                    "variants — and a full Linux control plane boots: kernel, then "
                    "switching stack and state databases. This dominates "
                    "time-to-forwarding, the direct analogue of DDR5 training in "
                    "the R760 twin."
                ),
                expert=(
                    "Max dwell: NOS boot (OS10 or SONiC) — kernel, switching stack, "
                    "state databases. Dominates time-to-forwarding, as DDR5 "
                    "training does on the R760."
                ),
            ),
            active_regions=["cpu"],
            power_watts=155,
            fan_percent=50,
            elapsed_seconds=120,
            cycle_cost=6,
        ),
        BootState(
            step=6,
            phase="nos",
            label="Control-plane services · config",
            description=L(
                novice=(
                    "The operating system brings up the ways an administrator can "
                    "talk to it — a command line, monitoring interfaces, a "
                    "programming interface — and applies whatever configuration it "
                    "was told to start with. On a brand-new switch this is where "
                    "automatic provisioning pulls a configuration down, so nobody "
                    "has to drive out to a branch office. The intended network "
                    "layout is now known; the next steps push it into the hardware."
                ),
                plain=(
                    "The OS brings up its management surfaces — CLI, SNMP, REST "
                    "API, SSH — and applies the startup configuration. On a new "
                    "switch this is where USB auto-configuration or zero-touch "
                    "provisioning pulls a config so no one has to drive to the "
                    "branch. VLANs, interfaces and routing intent are now known; "
                    "next they get pushed into hardware."
                ),
                standard=(
                    "The OS brings up its management surfaces — CLI, SNMP, REST "
                    "API, Telnet/SSH — and applies the startup configuration. On a "
                    "new switch this is where USB auto-configuration or zero-touch "
                    "provisioning pulls a config so no one has to drive to the "
                    "branch. VLANs, interfaces and routing intent are now known; "
                    "next they get pushed into hardware."
                ),
                technical=(
                    "Management surfaces up — CLI, SNMP, REST, SSH — and the "
                    "startup configuration is applied. On a factory unit, USB "
                    "auto-configuration or zero-touch provisioning supplies it, "
                    "removing the site visit. VLAN, interface, and routing intent "
                    "now exist in software, pending programming into silicon."
                ),
                expert=(
                    "Management surfaces up (CLI, SNMP, REST, SSH); startup config "
                    "applied, or ZTP/USB auto-config on a factory unit. Intent in "
                    "software, not yet in silicon."
                ),
            ),
            active_regions=["cpu", "mgmt-panel"],
            power_watts=165,
            fan_percent=50,
            elapsed_seconds=150,
        ),
        BootState(
            step=7,
            phase="dataplane",
            label="Switching ASIC init",
            description=L(
                novice=(
                    "The operating system loads the driver for the switching chip "
                    "and brings the silicon to life: the forwarding pipeline, the "
                    "packet buffers, and the on-chip lookup tables. Until this "
                    "moment the box is just a Linux server; from here it is a "
                    "switch. This is the second-longest stage."
                ),
                plain=(
                    "The OS loads the ASIC's driver and SDK and initializes the "
                    "switching silicon: the forwarding pipeline, the packet "
                    "buffers, and the on-chip tables come alive. Until this moment "
                    "the box is just a Linux server; from here it is a switch. This "
                    "is the second-longest stage."
                ),
                standard=(
                    "The OS loads the ASIC's driver/SDK and initializes the "
                    "switching silicon: the forwarding pipeline, the packet "
                    "buffers, and the on-chip tables come alive. Until this "
                    "moment the box is just a Linux server; from here it is a "
                    "switch. This is the second-longest stage."
                ),
                technical=(
                    "The NOS loads the ASIC driver and SDK and initializes the "
                    "switching silicon — forwarding pipeline, packet buffers, "
                    "on-chip table structures. The transition from general-purpose "
                    "host to switch happens here; second-longest stage in the "
                    "trace."
                ),
                expert=(
                    "ASIC driver/SDK loaded; pipeline, buffers, and on-chip tables "
                    "initialized. Host becomes switch. Second-longest stage."
                ),
            ),
            active_regions=["asic", "cpu"],
            power_watts=210,
            fan_percent=55,
            elapsed_seconds=175,
            cycle_cost=3,
        ),
        BootState(
            step=8,
            phase="dataplane",
            label="Forwarding tables programmed",
            description=L(
                novice=(
                    "The control software pushes its decisions into the chip's "
                    "hardware tables: the table of hardware addresses for local "
                    "switching, the routing tables for traffic heading elsewhere, "
                    "which ports belong to which virtual networks, and the access "
                    "rules. Once those live in silicon, forwarding no longer "
                    "involves the processor at all — it happens at the full speed "
                    "of the wire."
                ),
                plain=(
                    "The control plane pushes its decisions into the ASIC's "
                    "hardware tables: the MAC address table for layer-2 switching, "
                    "the IP route and next-hop tables for layer-3 routing, VLAN "
                    "membership, and access-control lists into TCAM. Once these are "
                    "resident in silicon, forwarding no longer needs the CPU — it "
                    "happens at wire speed."
                ),
                standard=(
                    "The control plane pushes its decisions into the ASIC's "
                    "hardware tables: the MAC address table for L2 switching, the "
                    "IP route and next-hop tables for L3 routing, VLAN membership, "
                    "and access-control lists into TCAM. Once these are resident "
                    "in silicon, forwarding no longer needs the CPU — it happens "
                    "at wire speed."
                ),
                technical=(
                    "Control plane programs the ASIC tables: MAC table for L2, "
                    "route and next-hop tables for L3, VLAN membership, and ACLs "
                    "into TCAM. With state resident in silicon the CPU leaves the "
                    "forwarding path entirely and packets move at wire rate."
                ),
                expert=(
                    "Tables programmed: MAC, route/next-hop, VLAN membership, ACLs "
                    "to TCAM. CPU exits the forwarding path; wire-rate from here."
                ),
            ),
            active_regions=["asic", "cpu"],
            power_watts=220,
            fan_percent=55,
            elapsed_seconds=190,
            cycle_cost=2,
        ),
        BootState(
            step=9,
            phase="ports",
            label="Interfaces link up",
            description=L(
                novice=(
                    "The port electronics train and negotiate: copper ports sense "
                    "what speed the device on the other end can manage, the fibre "
                    "uplinks at the front and the high-speed ports at the rear "
                    "bring up their optical transceivers, and the link lights come "
                    "on. The switch is now electrically connected to everything "
                    "plugged into it."
                ),
                plain=(
                    "The PHYs train and the ports negotiate: copper access ports "
                    "auto-sense their speed — 1, 2.5, 5 or 10 GbE on the Multigig "
                    "model — the SFP+/SFP28 front uplinks and the rear 100 GbE "
                    "QSFP28 ports bring up their optics, and link lights come on. "
                    "The switch is now electrically connected to everything plugged "
                    "into it."
                ),
                standard=(
                    "The PHYs train and the ports negotiate: copper access ports "
                    "auto-sense their speed (1/2.5/5/10GbE on the Multigig model), "
                    "the SFP+/SFP28 front uplinks and the rear 100GbE QSFP28 ports "
                    "bring up their optics, and link lights come on. The switch is "
                    "now electrically connected to everything plugged into it."
                ),
                technical=(
                    "PHY training and autonegotiation: copper access ports resolve "
                    "1/2.5/5/10 GbE on the Multigigabit variant, SFP+/SFP28 front "
                    "uplinks and rear 100 GbE QSFP28 ports bring their optics up, "
                    "link state asserts. Electrical connectivity to every attached "
                    "device is now established."
                ),
                expert=(
                    "PHYs train, autoneg resolves (1/2.5/5/10 GbE copper), front "
                    "SFP+/SFP28 and rear QSFP28 optics up. Link state asserted."
                ),
            ),
            active_regions=["asic", "access-ports", "sfp-uplinks", "qsfp-uplinks"],
            power_watts=250,
            fan_percent=55,
            data_rate_gbps=40,
            elapsed_seconds=205,
        ),
        BootState(
            step=10,
            phase="ports",
            label="PoE delivered to devices",
            description=L(
                novice=(
                    "The power-sourcing circuitry negotiates with each attached "
                    "device — detect it, work out its class, then energize it — and "
                    "begins delivering power over the same cables that carry data: "
                    "up to 30 W or 90 W per port depending on the standard. This is "
                    "where the wireless access points, telephones and cameras "
                    "actually turn on, and where the total power draw jumps, "
                    "because most of this switch's wattage is not consumed by the "
                    "switch at all — it is the budget leaving through the front "
                    "ports."
                ),
                plain=(
                    "The Power Sourcing Equipment negotiates with each attached "
                    "powered device — detect, classify, then energize — and begins "
                    "delivering power over the data pairs: up to 30 W under 802.3at "
                    "or 90 W under 802.3bt per port. This is where the access "
                    "points, phones and cameras turn on, and where total draw "
                    "jumps, because most of the switch's wattage is the PoE budget "
                    "leaving through the front ports."
                ),
                standard=(
                    "The Power Sourcing Equipment negotiates with each attached "
                    "powered device — detect, classify, then energize — and begins "
                    "delivering power over the data pairs: up to 30W (802.3at) or "
                    "90W (802.3bt) per port. This is where the access points, "
                    "phones and cameras actually turn on, and where total draw "
                    "jumps, because most of the switch's wattage is the PoE budget "
                    "leaving through the front ports."
                ),
                technical=(
                    "PSE runs detection, classification, and energization per port, "
                    "then delivers over the data pairs — up to 30 W (802.3at) or 90 "
                    "W (802.3bt). Attached endpoints power on here and total draw "
                    "steps sharply, because the dominant term is budget leaving the "
                    "front panel rather than switch consumption. The engine asserts "
                    "this step is the power peak."
                ),
                expert=(
                    "PSE detect/classify/energize; 30 W (802.3at) or 90 W (802.3bt) "
                    "per port. Power peak asserted — the dominant term is egress "
                    "budget, not consumption."
                ),
            ),
            active_regions=["poe-system", "access-ports"],
            power_watts=900,
            fan_percent=65,
            data_rate_gbps=120,
            elapsed_seconds=220,
            cycle_cost=2,
        ),
        BootState(
            step=11,
            phase="forwarding",
            label="Protocols converge",
            description=L(
                novice=(
                    "The control software forms its relationships with neighbouring "
                    "equipment: it pairs with a partner switch so the two can act "
                    "as one for redundancy without the old, slow loop-prevention "
                    "protocol; routing neighbours come up; tunnels and multicast "
                    "groups establish. The switch stops being an island and takes "
                    "its place in the wider network."
                ),
                plain=(
                    "The control plane forms its adjacencies: MLAG peers with its "
                    "partner for active/active, loop-free redundancy without "
                    "spanning tree; BGP and OSPF neighbours come up; VXLAN tunnels "
                    "and multicast establish. The switch stops being an island and "
                    "takes its place in the wider fabric."
                ),
                standard=(
                    "The control plane forms its adjacencies: MLAG peers with its "
                    "partner for active/active, loop-free redundancy without "
                    "spanning tree; BGP and OSPF neighbors come up; VXLAN tunnels "
                    "and multicast (PIM/IGMP) establish. The switch stops being an "
                    "island and takes its place in the wider fabric."
                ),
                technical=(
                    "Control-plane adjacencies form: MLAG peering for active/active "
                    "redundancy without spanning-tree convergence delay, BGP and "
                    "OSPF neighbour establishment, VXLAN tunnel and PIM/IGMP "
                    "multicast setup. The device joins the wider fabric rather than "
                    "operating standalone."
                ),
                expert=(
                    "Adjacencies up: MLAG peering (active/active, no STP), BGP/OSPF "
                    "neighbours, VXLAN tunnels, PIM/IGMP. Joined to the fabric."
                ),
            ),
            active_regions=["asic", "cpu", "qsfp-uplinks", "sfp-uplinks"],
            power_watts=880,
            fan_percent=60,
            data_rate_gbps=800,
            elapsed_seconds=245,
        ),
        BootState(
            step=12,
            phase="forwarding",
            label="Line-rate forwarding",
            description=L(
                novice=(
                    "Steady state. Every port forwards at full speed through a "
                    "non-blocking fabric, with the processor only handling control "
                    "traffic and exceptions. The fans track the real thermal load, "
                    "the power-over-Ethernet keeps the edge devices running, and "
                    "the switch simply moves traffic — which is the only review a "
                    "switch ever gets."
                ),
                plain=(
                    "Steady state. Every port forwards at line rate through the "
                    "non-blocking store-and-forward fabric — up to 1560 Gbps and "
                    "2167 Mpps on the E3248PXE — with the CPU handling only control "
                    "traffic and exceptions. Fans track the real thermal load, PoE "
                    "holds the edge devices up, and the switch simply moves "
                    "traffic."
                ),
                standard=(
                    "Steady state. Every port forwards at line rate through the "
                    "non-blocking store-and-forward fabric — up to 1560 Gbps and "
                    "2167 Mpps on the E3248PXE — with the CPU only handling "
                    "control traffic and exceptions. Fans track the real thermal "
                    "load, PoE holds the edge devices up, and the switch simply "
                    "moves traffic."
                ),
                technical=(
                    "Steady state: line-rate forwarding across every port through a "
                    "non-blocking store-and-forward fabric, up to 1560 Gbps and "
                    "2167 Mpps on the E3248PXE, with the CPU restricted to control "
                    "and exception traffic. Fans track measured thermal load and "
                    "PoE sustains the attached endpoints."
                ),
                expert=(
                    "Line rate across all ports, non-blocking; 1560 Gbps / 2167 "
                    "Mpps on the E3248PXE. CPU handles control and exceptions only."
                ),
            ),
            active_regions=["asic", "access-ports", "sfp-uplinks", "qsfp-uplinks", *_FANS],
            power_watts=860,
            fan_percent=55,
            data_rate_gbps=1560,
            elapsed_seconds=270,
        ),
    ]
