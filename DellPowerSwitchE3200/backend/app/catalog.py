"""The components-and-options menu for the PowerSwitch E3200-ON.

Like anatomy.py, the catalog is data, not code: each ``CatalogCategory``
maps to the chassis regions it slots into (``region_ids`` from anatomy.py)
and lists the orderable options, described for a technically skilled reader
who is new to Dell networking. Contents follow the E3200-ON spec sheet
(August 2024); option lists are representative, not exhaustive.

The first choice is the model, because it fixes the front-panel port bank,
the PoE class, the uplink speed, the network OS and the default PSU all at
once — the E3200 is a series of fixed configurations, not a slot-by-slot
build like a server.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

_FANS = [f"fan-{i}" for i in range(4)]

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="model",
        name="Model",
        blurb=(
            "The E3200-ON ships as three fixed configurations. Picking the "
            "model sets the access ports, the PoE class, the front uplink "
            "speed and the network OS together — the rest of this menu is "
            "mostly a consequence of it."
        ),
        limits="One model per switch; all are 1RU",
        region_ids=["access-ports", "sfp-uplinks"],
        options=[
            CatalogOption(
                id="mdl-e3224f",
                name="E3224F-ON · 24× 1G SFP (fiber)",
                summary="Fiber distribution switch; runs SmartFabric OS10.",
                details=(
                    "24 line-rate 1GbE SFP fiber ports, four 10GbE SFP+ "
                    "uplinks and two rear 100GbE QSFP28. No PoE — it is a "
                    "fiber aggregation/distribution switch. 528 Gbps fabric, "
                    "733 Mpps, 550W PSU, only ~230W max draw. Runs SmartFabric "
                    "OS10, Dell's easier-to-learn NOS. Americas only."
                ),
            ),
            CatalogOption(
                id="mdl-e3248p",
                name="E3248P-ON · 48× 1G copper, 30W PoE",
                summary="Classic 48-port PoE access switch; runs SONiC.",
                details=(
                    "48 line-rate 1GbE RJ45 copper ports with 802.3at (30W) "
                    "PoE, four 10GbE SFP+ uplinks and two rear 100GbE QSFP28. "
                    "576 Gbps fabric, 800 Mpps, 1050W PSU. The workhorse for "
                    "powering a floor of access points, phones and cameras. "
                    "Runs Enterprise SONiC Distribution by Dell."
                ),
            ),
            CatalogOption(
                id="mdl-e3248pxe",
                name="E3248PXE-ON · 48× Multigig, 90W PoE",
                summary="Top model: Multigig copper + 90W PoE + 25G uplinks.",
                details=(
                    "48 RJ45 ports that auto-sense 1/2.5/5/10GbE (Multigigabit) "
                    "with 802.3bt (90W) PoE, four 25GbE SFP28 uplinks and two "
                    "rear 100GbE QSFP28. The big one: 1560 Gbps fabric, 2167 "
                    "Mpps, 32MB buffer, 1600W PSU. Built for Wi-Fi 6E/7 access "
                    "points that need both Multigig speed and high-wattage PoE. "
                    "Runs Enterprise SONiC."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="nos",
        name="Network operating system",
        blurb=(
            "'ON' hardware boots ONIE and runs a disaggregated network OS, so "
            "the software is chosen with (and constrained by) the model. Both "
            "are Linux-based and share the CLI/SNMP/automation surfaces."
        ),
        limits="OS10 on E3224F; Enterprise SONiC on E3248 models",
        region_ids=["cpu"],
        options=[
            CatalogOption(
                id="nos-os10",
                name="SmartFabric OS10",
                summary="Dell's own NOS — easier deployment, lower learning curve.",
                details=(
                    "Dell SmartFabric OS10: a Linux-based network OS aimed at "
                    "easier deployment, broad interoperability and a gentle "
                    "learning curve for network administrators. It is the OS "
                    "for the E3224F fiber model, and the one to pick when you "
                    "want a familiar, fully Dell-supported CLI and SmartFabric "
                    "automation."
                ),
            ),
            CatalogOption(
                id="nos-sonic",
                name="Enterprise SONiC Distribution by Dell",
                summary="Open-source NOS hardened for enterprise, on the 48-port models.",
                details=(
                    "Enterprise SONiC Distribution by Dell Technologies: a "
                    "commercially supported build of SONiC, the open-source "
                    "network OS born in hyperscale data centers, with "
                    "enterprise management features and 24/7 support. It runs "
                    "on the E3248P/PXE PoE models and suits shops standardizing "
                    "on an open, container-based NOS across a large fabric."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="poe",
        name="Power over Ethernet",
        blurb=(
            "PoE injects DC power onto the data pairs so an edge device needs "
            "one cable. The class caps the per-port wattage; the total budget "
            "is set by the power supplies."
        ),
        limits="48-port copper models only; budget bounded by installed PSUs",
        region_ids=["poe-system", "access-ports"],
        options=[
            CatalogOption(
                id="poe-none",
                name="No PoE (fiber)",
                summary="The E3224F fiber model carries data only.",
                details=(
                    "The E3224F-ON is a fiber switch with no PoE — SFP optical "
                    "links do not carry power. Its job is bandwidth and "
                    "distance, not powering devices, which is why it needs only "
                    "a 550W supply and draws about 230W."
                ),
            ),
            CatalogOption(
                id="poe-at",
                name="802.3at (Type 2) · 30W/port",
                summary="Standard PoE+ for APs, phones, cameras.",
                details=(
                    "The E3248P delivers up to 30W per port (802.3at, 'PoE+') "
                    "across all 48 copper ports — plenty for most wireless "
                    "access points, VoIP handsets, and IP cameras. The 1050W "
                    "supply sizes the shared budget across the ports drawing at "
                    "once."
                ),
            ),
            CatalogOption(
                id="poe-bt",
                name="802.3bt (Type 4) · 90W/port",
                summary="High-power PoE for Wi-Fi 6E/7, PTZ cameras, displays.",
                details=(
                    "The E3248PXE delivers up to 90W per port (802.3bt, Type 4) "
                    "— enough for the newest multi-radio Wi-Fi 6E/7 access "
                    "points, pan-tilt-zoom cameras, LED luminaires, and small "
                    "displays. At 90W across many ports the 1600W supply, and "
                    "often an external power shelf, is what makes the budget "
                    "add up."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="uplinks",
        name="Uplinks",
        blurb=(
            "How the edge switch hands traffic up to aggregation, distribution "
            "or the core. Front cages for medium speeds; dedicated rear ports "
            "for the fat pipes."
        ),
        limits="4 front SFP+/SFP28 + 2 rear 100G QSFP28, integrated",
        region_ids=["sfp-uplinks", "qsfp-uplinks"],
        options=[
            CatalogOption(
                id="up-sfpplus",
                name="4× 10GbE SFP+ (front)",
                summary="Ten-gig uplinks on the E3224F/E3248P.",
                details=(
                    "Four integrated 10GbE SFP+ cages up front, taking optical "
                    "transceivers or direct-attach copper (DAC). The standard "
                    "uplink for the fiber and 30W-PoE models when 10G to the "
                    "aggregation layer is enough."
                ),
            ),
            CatalogOption(
                id="up-sfp28",
                name="4× 25GbE SFP28 (front)",
                summary="Twenty-five-gig uplinks on the E3248PXE.",
                details=(
                    "The Multigig model upgrades the four front cages to 25GbE "
                    "SFP28, matching the heavier traffic that Multigig access "
                    "ports and high-power APs generate. SFP28 is backward "
                    "compatible with 10G optics."
                ),
            ),
            CatalogOption(
                id="up-qsfp28",
                name="2× 100GbE QSFP28 (rear)",
                summary="High-capacity rear uplinks on every model.",
                details=(
                    "Two 100GbE QSFP28 ports on the rear of every E3200, the "
                    "'built-in rear high capacity ports' for handing off to the "
                    "core or spine without using a front cage. Each QSFP28 also "
                    "breaks out to 4× 25GbE for flexible aggregation."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="power",
        name="Power supplies",
        blurb=(
            "Dual internal, hot-swap 80 PLUS Platinum supplies (87%+ efficient) "
            "for 1+1 redundancy. Wattage is chosen mostly to size the PoE "
            "budget, not the switch's own draw."
        ),
        limits="2 internal PSU bays; AC or DC on the E3224F",
        region_ids=["psu-1", "psu-2"],
        options=[
            CatalogOption(
                id="pwr-550ac",
                name="550W AC",
                summary="For the E3224F fiber switch.",
                details=(
                    "550W 80 PLUS Platinum AC supply — the E3224F's default and "
                    "redundant option. With no PoE to feed, 550W is ample; add "
                    "a second for 1+1 redundancy."
                ),
            ),
            CatalogOption(
                id="pwr-550dc",
                name="550W DC",
                summary="DC-plant option for the E3224F.",
                details=(
                    "550W 80 PLUS Platinum DC supply for central-office or "
                    "telco environments running on a -48V DC plant. Add two for "
                    "DC redundancy on the E3224F."
                ),
            ),
            CatalogOption(
                id="pwr-1050ac",
                name="1050W AC",
                summary="For the E3248P (30W PoE) budget.",
                details=(
                    "1050W 80 PLUS Platinum AC supply — included on the E3248P "
                    "and the unit that sizes its 802.3at PoE budget. A second "
                    "adds redundancy or extends the budget; it also fits the "
                    "external MPS power shelves."
                ),
            ),
            CatalogOption(
                id="pwr-1600ac",
                name="1600W AC",
                summary="For the E3248PXE (90W PoE) budget.",
                details=(
                    "1600W 80 PLUS Platinum AC supply — included on the "
                    "E3248PXE to feed 802.3bt (90W) PoE. Because 90W across "
                    "many ports can exceed even 1600W, this is the model most "
                    "likely to pair with an external power shelf."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="shelf",
        name="External power shelf",
        blurb=(
            "When the internal supplies cannot cover a full load of high-"
            "wattage PoE, an external shelf adds more PSUs dedicated to the PoE "
            "budget. Mounts separately in the rack."
        ),
        limits="Optional; for E3248P / E3248PXE PoE budgets",
        region_ids=[],
        options=[
            CatalogOption(
                id="shelf-mps1s",
                name="MPS-1S (1 PSU)",
                summary="Single-supply shelf to top up the PoE budget.",
                details=(
                    "An external Modular Power Shelf holding one PSU (1050W AC, "
                    "1600W AC, 2000W AC or 1300W DC). It extends the PoE budget "
                    "of an E3248P or E3248PXE beyond what the two internal bays "
                    "can supply — mounts in the rack alongside the switch."
                ),
            ),
            CatalogOption(
                id="shelf-mps3s",
                name="MPS-3S (up to 3 PSUs)",
                summary="Three-supply shelf for the biggest PoE loads.",
                details=(
                    "A larger shelf holding up to three PSUs in any combination "
                    "(1050/1600/2000W AC, or up to three 1300W DC). For a fully "
                    "loaded row of 90W access points, this is how the PoE "
                    "budget is actually met."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="cooling",
        name="Cooling",
        blurb=(
            "Redundant variable-speed fans move air front-to-rear (I/O to PSU) "
            "and spin only as fast as the load needs, keeping cooling power and "
            "noise down."
        ),
        limits="Field-replaceable fan modules; I/O-to-PSU airflow",
        region_ids=_FANS,
        options=[
            CatalogOption(
                id="fan-io-psu",
                name="Fan module · I/O-to-PSU airflow",
                summary="Variable-speed, hot-serviceable, Fresh Air rated.",
                details=(
                    "The E3200 uses redundant variable-speed fan modules with "
                    "'I/O to PSU' airflow — intake at the port side, exhaust "
                    "past the power supplies — matching a wiring closet where "
                    "cabling is at the front. Dell Fresh Air compliance allows "
                    "operation up to 45°C / 113°F, cutting closet cooling "
                    "costs. Modules are field-replaceable."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="mgmt",
        name="Management & deployment",
        blurb=(
            "How you reach and provision the switch out-of-band — separate from "
            "the data ports — so a closet switch deploys and recovers without a "
            "site visit."
        ),
        limits="Integrated on every model",
        region_ids=["mgmt-panel"],
        options=[
            CatalogOption(
                id="mgmt-oob",
                name="Out-of-band management port",
                summary="Dedicated 1GbE management on an isolated network.",
                details=(
                    "A 10/100/1000BASE-T management port on a network separate "
                    "from the switched data ports, so you can log in and manage "
                    "the switch even if the data plane is misconfigured or "
                    "saturated — the networking equivalent of a server's iDRAC "
                    "port."
                ),
            ),
            CatalogOption(
                id="mgmt-usb-ztp",
                name="USB auto-configuration / ZTP",
                summary="Deploy by flash drive or zero-touch, no TFTP.",
                details=(
                    "USB auto-configuration reads a config file from a flash "
                    "drive in the Type-A port and applies it on boot — no "
                    "complex TFTP setup and no sending staff to a remote "
                    "office. With zero-touch provisioning the switch pulls its "
                    "config over the network on first boot instead."
                ),
            ),
            CatalogOption(
                id="mgmt-console",
                name="Serial console (RJ45 + MicroUSB)",
                summary="Direct serial access when there is no network.",
                details=(
                    "Two console options for hands-on setup and recovery: an "
                    "RJ45 RS-232 port (with an RJ45-to-DB9 cable) and a MicroUSB "
                    "Type-B port. The fallback when a switch has no IP yet, or "
                    "when you need to watch it boot at the rack."
                ),
            ),
            CatalogOption(
                id="mgmt-snmp",
                name="CLI / SNMP / OpenManage",
                summary="Familiar CLI plus SNMP and OpenManage Network Manager.",
                details=(
                    "Day-to-day operation through a familiar industry-standard "
                    "CLI, SNMP-based consoles including Dell OpenManage Network "
                    "Manager, and Telnet/SSH. AAA with TACACS+ accounting and "
                    "RADIUS secures administrative access."
                ),
            ),
        ],
    ),
]
