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
            description=(
                "The switch is unplugged in the wiring closet. No power, no "
                "link lights, nothing forwarding. Both power-supply bays are "
                "dark."
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
            description=(
                "A power cord is connected. The 80 PLUS Platinum power supply "
                "detects line voltage and brings up a small standby rail — a "
                "few watts — enough to wake the boot logic. The main rails that "
                "feed the ASIC and PoE stay off for now."
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
            description=(
                "The main rails come up. The 4-core control-plane CPU powers "
                "on, and all fans briefly spin to full — the safe default "
                "until firmware has read the thermal sensors — before dropping "
                "to a managed speed. The switch is now a small computer "
                "starting to boot; it has not looked at a single packet yet."
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
            description=(
                "Before the network OS loads, the platform firmware inventories "
                "the hardware over internal management buses: it reads both "
                "power supplies' wattage and health, the fan modules, the "
                "optics in the SFP/QSFP cages, and the PoE controllers — "
                "establishing how much PoE budget the installed PSUs will "
                "allow."
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
            description=(
                "ONIE — the Open Network Install Environment — runs. This is "
                "what the '-ON' in E3200-ON means: instead of a fixed vendor "
                "OS, the switch boots a small open installer that either "
                "launches the network OS already installed in flash, or, on a "
                "factory-fresh unit, fetches and installs one over the network. "
                "It is the disaggregation layer that lets the same silicon run "
                "OS10 or SONiC."
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
            description=(
                "The longest stage. ONIE hands off to the installed network "
                "operating system — SmartFabric OS10 on the E3224F, Enterprise "
                "SONiC on the E3248 models — and a full Linux control plane "
                "boots: kernel, then the switching stack and databases. This "
                "is where a switch spends most of its boot time, apparently "
                "idle, exactly as a server does during memory training."
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
            description=(
                "The OS brings up its management surfaces — CLI, SNMP, REST "
                "API, Telnet/SSH — and applies the startup configuration. On a "
                "new switch this is where USB auto-configuration or zero-touch "
                "provisioning pulls a config so no one has to drive to the "
                "branch. VLANs, interfaces and routing intent are now known; "
                "next they get pushed into hardware."
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
            description=(
                "The OS loads the ASIC's driver/SDK and initializes the "
                "switching silicon: the forwarding pipeline, the packet "
                "buffers, and the on-chip tables come alive. Until this "
                "moment the box is just a Linux server; from here it is a "
                "switch. This is the second-longest stage."
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
            description=(
                "The control plane pushes its decisions into the ASIC's "
                "hardware tables: the MAC address table for L2 switching, the "
                "IP route and next-hop tables for L3 routing, VLAN membership, "
                "and access-control lists into TCAM. Once these are resident "
                "in silicon, forwarding no longer needs the CPU — it happens "
                "at wire speed."
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
            description=(
                "The PHYs train and the ports negotiate: copper access ports "
                "auto-sense their speed (1/2.5/5/10GbE on the Multigig model), "
                "the SFP+/SFP28 front uplinks and the rear 100GbE QSFP28 ports "
                "bring up their optics, and link lights come on. The switch is "
                "now electrically connected to everything plugged into it."
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
            description=(
                "The Power Sourcing Equipment negotiates with each attached "
                "powered device — detect, classify, then energize — and begins "
                "delivering power over the data pairs: up to 30W (802.3at) or "
                "90W (802.3bt) per port. This is where the access points, "
                "phones and cameras actually turn on, and where total draw "
                "jumps, because most of the switch's wattage is the PoE budget "
                "leaving through the front ports."
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
            description=(
                "The control plane forms its adjacencies: MLAG peers with its "
                "partner for active/active, loop-free redundancy without "
                "spanning tree; BGP and OSPF neighbors come up; VXLAN tunnels "
                "and multicast (PIM/IGMP) establish. The switch stops being an "
                "island and takes its place in the wider fabric."
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
            description=(
                "Steady state. Every port forwards at line rate through the "
                "non-blocking store-and-forward fabric — up to 1560 Gbps and "
                "2167 Mpps on the E3248PXE — with the CPU only handling "
                "control traffic and exceptions. Fans track the real thermal "
                "load, PoE holds the edge devices up, and the switch simply "
                "moves traffic."
            ),
            active_regions=["asic", "access-ports", "sfp-uplinks", "qsfp-uplinks", *_FANS],
            power_watts=860,
            fan_percent=55,
            data_rate_gbps=1560,
            elapsed_seconds=270,
        ),
    ]
