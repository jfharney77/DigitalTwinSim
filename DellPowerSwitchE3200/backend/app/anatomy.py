"""Chassis-anatomy data: an annotated top-down floorplan of the E3200-ON.

Like the R760 app's anatomy.py, the chassis is data, not code. ``ANATOMY``
describes a top-down view of the 1RU switch as blocks in a normalized
coordinate space the frontend renders as SVG. Front of the switch — the
access ports, console and management — is at x=0 (left); the rear, with the
power supplies, fans and the 100GbE uplinks, is at x=100. Air flows the same
way the data does not: intake at the port (I/O) side, exhaust at the PSU
side ("I/O to PSU" airflow).

Geometry is stylized and representative of the series (the PoE-heavy 48-port
layout); the three models differ mainly in the front-panel port bank and the
PSU wattage, both called out in the catalog. Per the project's scope
guardrails: favor a correct mental model over exact mm placement. All figures
are from the Dell PowerSwitch E3200-ON spec sheet (August 2024, v1.9).
"""

from __future__ import annotations

from .leveling import L
from .models import ChassisAnatomy, ChassisRegion, Photo, SourceLink, Stat

P_E3200_FRONT = Photo(
    url="/e3200-front.svg",
    caption=(
        "Front panel of an E3200-ON 48-port model: a bank of RJ45 access "
        "ports with PoE, four SFP+/SFP28 uplinks, and the console, USB and "
        "out-of-band management cluster. The two 100GbE QSFP28 uplinks and "
        "the power supplies sit on the rear."
    ),
    credit="Illustration for this teaching tool; not a Dell product image.",
)

ANATOMY = ChassisAnatomy(
    id="e3200",
    name="PowerSwitch E3200-ON",
    vendor="Dell Technologies",
    form_factor="1RU open-networking edge switch",
    generation="E3200-ON Series (2024)",
    year=2024,
    width=100,
    height=48,
    overview=L(
        novice=(
            "A network switch is the box that lets all the computers in a "
            "building talk to each other. Historically you bought the switch "
            "and its software as one inseparable product from one company. This "
            "one is different: the hardware and the operating system are "
            "separate purchases, and the switch boots through a small standard "
            "program whose only job is to go and fetch whichever network "
            "operating system you chose. Watch where the power actually goes, "
            "too. Most of the electricity this switch draws is not consumed by "
            "the switch at all — it is sent back out of the front ports to "
            "power the telephones, cameras, and wireless access points plugged "
            "into it. That is why the power peak happens when those ports come "
            "up, not when the switch is working hardest."
        ),
        plain=(
            "A 1RU open-networking campus switch booting from mains power to "
            "line-rate forwarding. The distinctive path is the '-ON' part: "
            "hardware initialisation, then ONIE — a standard bootloader whose "
            "job is to install and launch a network operating system chosen "
            "independently of the switch vendor — then the switching silicon is "
            "programmed and the ports come up. The network OS boot is the "
            "longest stage. Note where the wattage goes: most of it leaves "
            "through the front ports as Power over Ethernet for phones, "
            "cameras, and access points, so the power peak is the PoE step "
            "rather than peak forwarding."
        ),
        standard=(
            "The Dell PowerSwitch E3200-ON is a 1RU, high-performance open-"
            "networking switch built for Layer 3 distribution at the network edge "
            "— large enterprise offices, branches and campuses. A non-blocking, "
            "store-and-forward architecture gives every port line-rate L2 "
            "switching and L3 routing, up to 1560 Gbps of switching capacity and "
            "2167 Mpps of forwarding on the top model. The series spans three "
            "variants: the E3224F-ON (24× 1GbE SFP fiber, runs SmartFabric OS10), "
            "the E3248P-ON (48× 1GbE copper with 30W PoE, runs Enterprise SONiC), "
            "and the E3248PXE-ON (48× 1/2.5/5/10GbE Multigigabit copper with 90W "
            "PoE, runs Enterprise SONiC). All three add four SFP+/SFP28 uplinks up "
            "front and two 100GbE QSFP28 uplinks at the rear, dual hot-swap 80 "
            "PLUS Platinum power supplies, and variable-speed fans. 'ON' means "
            "Open Networking: the hardware boots ONIE and runs a disaggregated "
            "network OS, so the switch silicon and the software are chosen "
            "separately. This floorplan is the PoE-heavy 48-port layout, top-down "
            "with the lid off: ports on the left, power and uplinks on the right."
        ),
        technical=(
            "1RU open-networking L3 campus switch: power-on → ONIE → "
            "disaggregated NOS (SmartFabric OS10 or Enterprise SONiC) → ASIC "
            "programming → ports and PoE → line rate. NOS boot holds the max "
            "dwell. Data rate is zero through every boot phase and ramps only "
            "at forwarding. PoE delivery is the power peak and the engine "
            "asserts it — most of the draw is budget leaving the front panel, "
            "not switch consumption. Airflow is I/O-to-PSU; the floorplan is "
            "the 48-port PoE layout."
        ),
        expert=(
            "1RU open-networking L3 switch: ONIE → disaggregated NOS → ASIC → "
            "ports/PoE → line rate. NOS boot holds max dwell; data rate zero "
            "until forwarding. PoE step is the asserted power peak — the budget "
            "leaves the front panel rather than being consumed."
        ),
    ),
    regions=[
        ChassisRegion(
            id="access-ports",
            kind="ports",
            label="Access ports · front panel",
            x=1, y=1, w=7, h=32,
            description=(
                "The front-panel access ports — the edge-facing side of the "
                "switch. Depending on model this is 24 fiber SFP ports "
                "(E3224F), 48 RJ45 copper GbE ports (E3248P), or 48 RJ45 "
                "Multigigabit ports that auto-sense 1/2.5/5/10GbE "
                "(E3248PXE). Each copper port pairs a PHY (the analog "
                "transceiver that puts bits on the wire) with the switching "
                "ASIC. Auto-negotiation, auto-MDI/MDIX and per-port "
                "Energy-Efficient Ethernet live here."
            ),
        ),
        ChassisRegion(
            id="sfp-uplinks",
            kind="uplink",
            label="4× SFP+ / SFP28",
            x=1, y=34, w=7, h=6,
            description=(
                "Four integrated front uplink cages: 10GbE SFP+ on the "
                "E3224F/E3248P, or 25GbE SFP28 on the E3248PXE. These take "
                "pluggable optics or direct-attach copper and are the usual "
                "path to an aggregation or distribution layer when the rear "
                "100GbE ports are more than the site needs."
            ),
        ),
        ChassisRegion(
            id="mgmt-panel",
            kind="mgmt",
            label="Console · USB · OOB mgmt",
            x=1, y=41, w=7, h=6,
            description=(
                "The management cluster on the front panel: a 10/100/1000BASE-T "
                "out-of-band (OOB) management port on a network isolated from "
                "the data ports, a USB Type-A port for USB auto-configuration "
                "(drop a config file on a flash drive and the switch deploys "
                "itself), and two console ports — a MicroUSB Type-B and an RJ45 "
                "RS-232 — for direct serial access when there is no network at "
                "all."
            ),
        ),
        ChassisRegion(
            id="poe-system",
            kind="poe",
            label="PoE power subsystem (PSE)",
            x=10, y=1, w=14, h=46,
            description=(
                "The Power-over-Ethernet subsystem: the Power Sourcing "
                "Equipment (PSE) controllers that inject DC power onto the "
                "same twisted pairs that carry data, so an access point, "
                "IP phone or camera needs only one cable. The E3248P delivers "
                "802.3at (Type 2, up to 30W per port); the E3248PXE delivers "
                "802.3bt (Type 4, up to 90W per port). The total PoE budget is "
                "set by the installed power supplies, which is why these "
                "models take the biggest PSUs and optional external power "
                "shelves. The fiber E3224F has no PoE."
            ),
        ),
        ChassisRegion(
            id="cpu",
            kind="cpu",
            label="Control plane · 4-core CPU",
            x=27, y=1, w=28, h=6,
            description=(
                "The control-plane computer: a 4-core CPU with 8GB (E3224F) or "
                "16GB (E3248) of memory and a 32GB SSD. It runs the network "
                "operating system — the Linux-based SmartFabric OS10 or "
                "Enterprise SONiC — which owns the CLI, SNMP and APIs, speaks "
                "the routing protocols (BGP, OSPF, PIM, BFD), and programs the "
                "ASIC. It does not touch packets in the fast path; it decides "
                "the rules the ASIC then enforces at line rate. Dual firmware "
                "images on-board allow a safe upgrade or rollback."
            ),
        ),
        ChassisRegion(
            id="asic",
            kind="asic",
            label="Switching ASIC · data plane",
            x=27, y=8, w=28, h=32,
            description=(
                "The switching ASIC — the packet processor at the heart of "
                "the switch, and where 'non-blocking, line-rate' is actually "
                "delivered. Every frame is switched or routed in hardware here "
                "in a store-and-forward pipeline: it looks up the destination "
                "in on-chip tables (MAC address table, IP routes, VLANs, "
                "ACLs held in TCAM), buffers it (8MB, or 32MB on the "
                "E3248PXE), and forwards it — up to 2167 Mpps with no CPU in "
                "the loop. VXLAN encapsulation and MLAG hashing run in this "
                "silicon too."
            ),
        ),
        *[
            ChassisRegion(
                id=f"fan-{i}",
                kind="cooling",
                label=f"Fan {i + 1}",
                x=58, y=1 + i * 11, w=14, h=11,
                description=(
                    "One of the redundant, variable-speed fan modules. They "
                    "pull air front-to-rear — intake at the port (I/O) side, "
                    "exhaust past the power supplies ('I/O to PSU' airflow) — "
                    "and spin only as fast as the sensed temperature and port "
                    "load require, which (with Dell Fresh Air support up to "
                    "45°C / 113°F) keeps cooling power and noise down. A failed "
                    "fan is a field-replaceable module."
                ),
            )
            for i in range(4)
        ],
        ChassisRegion(
            id="psu-1",
            kind="power",
            label="PSU 1 · 80+ Platinum",
            x=76, y=1, w=23, h=16,
            description=(
                "One of two internal, hot-swappable 80 PLUS Platinum power "
                "supplies (87%+ efficient in all modes). Rated per model — "
                "550W on the E3224F, 1050W on the E3248P, 1600W on the "
                "E3248PXE — because most of that wattage is the PoE budget "
                "handed to the front ports, not the switch's own draw. Running "
                "two gives 1+1 redundancy; either can carry the system, and "
                "each is fed from a separate cord."
            ),
        ),
        ChassisRegion(
            id="psu-2",
            kind="power",
            label="PSU 2 · 80+ Platinum",
            x=76, y=18, w=23, h=16,
            description=(
                "The second hot-swap power supply. On the E3224F it can be AC "
                "or DC (add two 550W DC supplies for DC redundancy). Optional "
                "external MPS-1S / MPS-3S power shelves add still more supplies "
                "to extend the PoE budget on the E3248P and E3248PXE beyond "
                "what fits internally — the way you power a full row of 90W "
                "Wi-Fi access points."
            ),
        ),
        ChassisRegion(
            id="qsfp-uplinks",
            kind="uplink",
            label="2× 100GbE QSFP28 (rear)",
            x=76, y=35, w=23, h=12,
            description=(
                "Two high-capacity 100GbE QSFP28 uplink ports on the rear of "
                "the chassis — the 'built-in rear high capacity ports' that let "
                "an edge switch hand off to the core or spine without "
                "consuming the front cages. QSFP28 also breaks out to 4× 25GbE "
                "with the right cable. These are the fat pipes out of the "
                "closet."
            ),
        ),
    ],
    stats=[
        Stat(label="Form factor", value="1RU · non-blocking store-and-forward"),
        Stat(label="Access ports", value="24× 1G SFP or 48× 1–10G copper (PoE)"),
        Stat(label="Uplinks", value="4× SFP+/SFP28 front + 2× 100G QSFP28 rear"),
        Stat(label="Switching capacity", value="528 / 576 / 1560 Gbps (by model)"),
        Stat(label="Forwarding rate", value="733 / 800 / 2167 Mpps (by model)"),
        Stat(label="PoE", value="802.3at 30W or 802.3bt 90W (48-port models)"),
        Stat(label="Power", value="Dual hot-swap 80 PLUS Platinum PSU"),
        Stat(label="Network OS", value="SmartFabric OS10 or Enterprise SONiC (ONIE)"),
    ],
    sources=[
        SourceLink(
            label="Dell PowerSwitch E3200-ON spec sheet (PDF, Aug 2024)",
            url="https://www.delltechnologies.com/asset/en-us/products/networking/technical-support/dell-powerswitch-e3200-specsheet.pdf",
        ),
        SourceLink(
            label="Dell PowerSwitch E3200 Series product page",
            url="https://www.dell.com/en-us/shop/ipovw/networking-e3200-series",
        ),
        SourceLink(
            label="OS10: installing a new image with ONIE (Dell KB)",
            url="https://www.dell.com/support/kbdoc/en-us/000199005/dell-emc-networking-os10-install-via-onie-install-fresh-install",
        ),
        SourceLink(
            label="Enterprise SONiC: Getting Started and Basics (Dell KB)",
            url="https://www.dell.com/support/kbdoc/en-us/000263481/dell-networking-enterprise-sonic-getting-started-and-basics-guide",
        ),
        SourceLink(
            label="Dell EMC Networking ONIE Technology Guide (PDF)",
            url="https://infohub.delltechnologies.com/static/media/client/7phukh/57ae5efd-8700-40e4-a268-37a88b6763fc.pdf",
        ),
    ],
    photo=P_E3200_FRONT,
)
