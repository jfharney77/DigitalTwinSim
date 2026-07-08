"""Deployment scenarios for the PowerSwitch E3200-ON.

Same shape as the R760 use cases: each is a specific model plus the options
that follow from it, with the reasoning. Every config line's
category_id/option_id must resolve against catalog.py (enforced in
tests/test_catalog.py), and each part's home regions light up on the
floorplan.
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

WIFI_EDGE = UseCase(
    id="wifi-edge",
    title="Wi-Fi 6E/7 campus edge",
    summary=(
        "Power and connect a floor of the newest high-wattage, Multigigabit "
        "wireless access points from a single 1RU closet switch."
    ),
    narrative=[
        (
            "The scenario: a campus is rolling out Wi-Fi 6E/7. The new access "
            "points are hungry in two ways at once — they can push more than a "
            "gigabit of client traffic, so a plain 1GbE port throttles them, "
            "and their multiple radios draw well past the 30W that classic "
            "PoE+ delivers. A standard gigabit PoE switch is the bottleneck on "
            "both axes."
        ),
        (
            "The E3248PXE-ON is built exactly for this. Its 48 copper ports "
            "auto-sense 1/2.5/5/10GbE (Multigigabit), so each AP negotiates "
            "the speed it actually needs over the existing cabling, and its "
            "802.3bt PoE delivers up to 90W per port — enough for the "
            "densest Wi-Fi 6E/7 radios with headroom for pan-tilt-zoom cameras "
            "and displays on the same switch. The four 25GbE SFP28 front "
            "uplinks carry the aggregate back toward distribution without "
            "becoming the new bottleneck."
        ),
        (
            "The catch with 90W is arithmetic: 90W across dozens of ports can "
            "exceed even the 1600W internal supply, so a serious deployment "
            "adds an external power shelf to guarantee the PoE budget. "
            "Enterprise SONiC runs the switch as part of a larger open fabric, "
            "and zero-touch provisioning means the closet unit configures "
            "itself on first power-on — no truck roll to a wiring closet."
        ),
    ],
    config=[
        UseCaseItem(
            category_id="model", option_id="mdl-e3248pxe", qty=1,
            rationale="Multigig ports + 90W PoE are exactly what Wi-Fi 6E/7 APs need.",
        ),
        UseCaseItem(
            category_id="poe", option_id="poe-bt", qty=1,
            rationale="802.3bt (90W) powers multi-radio APs a 30W switch can't.",
        ),
        UseCaseItem(
            category_id="uplinks", option_id="up-sfp28", qty=1,
            rationale="25GbE uplinks keep the aggregate off the bottleneck.",
        ),
        UseCaseItem(
            category_id="power", option_id="pwr-1600ac", qty=2,
            rationale="1600W supplies size the 90W PoE budget, run 1+1 redundant.",
        ),
        UseCaseItem(
            category_id="shelf", option_id="shelf-mps3s", qty=1,
            rationale="External shelf guarantees the budget when 90W×48 exceeds the internal PSUs.",
        ),
        UseCaseItem(
            category_id="nos", option_id="nos-sonic", qty=1,
            rationale="Enterprise SONiC runs the edge as part of the open fabric.",
        ),
        UseCaseItem(
            category_id="mgmt", option_id="mgmt-usb-ztp", qty=1,
            rationale="Zero-touch provisioning deploys the closet switch with no site visit.",
        ),
    ],
    outcomes=[
        Stat(label="Per-port PoE", value="Up to 90W (802.3bt)"),
        Stat(label="Per-port speed", value="Auto 1/2.5/5/10GbE"),
        Stat(label="Uplinks", value="4× 25G + 2× 100G"),
        Stat(label="Deploy", value="Zero-touch, no truck roll"),
    ],
)

POE_ACCESS = UseCase(
    id="poe-access",
    title="Enterprise PoE access floor",
    summary=(
        "The bread-and-butter deployment: power and connect a floor of access "
        "points, IP phones and cameras over one cable each."
    ),
    narrative=[
        (
            "The scenario: a typical office floor. Dozens of ceiling access "
            "points, desk phones, and hallway cameras, each of which wants "
            "network and power. Running separate power to every one is a "
            "non-starter; the point of a PoE access switch is that one "
            "Ethernet cable does both."
        ),
        (
            "The E3248P-ON is the workhorse for this. Its 48 gigabit copper "
            "ports each deliver 802.3at (30W) PoE — comfortably enough for "
            "mainstream APs, VoIP handsets and IP cameras — and its 1050W "
            "supply sizes a budget for a whole floor drawing at once. Four "
            "10GbE SFP+ uplinks hand traffic up to the distribution layer, "
            "and the two rear 100GbE ports are there if the site grows into "
            "them."
        ),
        (
            "Operationally the wins are boring in the best way: an out-of-band "
            "management port keeps administration reachable even when the data "
            "plane is busy or misconfigured, MLAG gives active/active uplink "
            "redundancy without spanning tree, and firmware upgrades can be "
            "staged without taking the floor offline. Enterprise SONiC keeps "
            "the access layer consistent with the rest of an open fabric."
        ),
    ],
    config=[
        UseCaseItem(
            category_id="model", option_id="mdl-e3248p", qty=1,
            rationale="48 gigabit PoE ports — the standard access-floor density.",
        ),
        UseCaseItem(
            category_id="poe", option_id="poe-at", qty=1,
            rationale="30W (802.3at) covers mainstream APs, phones and cameras.",
        ),
        UseCaseItem(
            category_id="uplinks", option_id="up-sfpplus", qty=1,
            rationale="10GbE uplinks are plenty for a single access floor.",
        ),
        UseCaseItem(
            category_id="power", option_id="pwr-1050ac", qty=2,
            rationale="1050W supplies size the 30W PoE budget with 1+1 redundancy.",
        ),
        UseCaseItem(
            category_id="nos", option_id="nos-sonic", qty=1,
            rationale="Enterprise SONiC keeps the access layer consistent with the fabric.",
        ),
        UseCaseItem(
            category_id="mgmt", option_id="mgmt-oob", qty=1,
            rationale="Out-of-band port keeps management reachable independent of the data plane.",
        ),
    ],
    outcomes=[
        Stat(label="Ports", value="48× 1GbE, 30W PoE"),
        Stat(label="One cable", value="Power + data to each device"),
        Stat(label="Redundancy", value="1+1 PSU, MLAG uplinks"),
        Stat(label="Upgrades", value="Staged without floor downtime"),
    ],
)

FIBER_DISTRIBUTION = UseCase(
    id="fiber-distribution",
    title="Fiber branch distribution",
    summary=(
        "A quiet, low-power Layer 3 distribution switch for fiber runs in a "
        "branch or server room — routing, not powering devices."
    ),
    narrative=[
        (
            "The scenario: a branch or a small server room that needs a "
            "Layer 3 distribution point for fiber links — aggregating other "
            "switches, routing between subnets, reaching the core — with no "
            "need to power endpoints. Paying for (and cooling) a big PoE "
            "budget here would be waste."
        ),
        (
            "The E3224F-ON fits this precisely. Its 24 fiber SFP ports take "
            "the branch's optical links, it does full non-blocking Layer 3 "
            "routing in hardware (BGP, OSPF, VRF-lite to carve the box into "
            "isolated virtual routers), and with no PoE it draws only about "
            "230W and runs cool and quiet on a single 550W supply. The two "
            "rear 100GbE QSFP28 ports uplink to the core far above what the "
            "branch will use."
        ),
        (
            "It runs SmartFabric OS10, the more approachable NOS, which suits "
            "a site without a data-center networking team on hand. Add a "
            "second 550W supply for redundancy, manage it over the serial "
            "console for initial turn-up and SNMP/CLI thereafter, and it is a "
            "durable, unobtrusive distribution layer."
        ),
    ],
    config=[
        UseCaseItem(
            category_id="model", option_id="mdl-e3224f", qty=1,
            rationale="24 fiber SFP ports for a distribution role with no endpoints to power.",
        ),
        UseCaseItem(
            category_id="poe", option_id="poe-none", qty=1,
            rationale="No PoE needed — saves power, cooling and cost.",
        ),
        UseCaseItem(
            category_id="uplinks", option_id="up-qsfp28", qty=1,
            rationale="Rear 100GbE uplinks to the core, well above branch demand.",
        ),
        UseCaseItem(
            category_id="power", option_id="pwr-550ac", qty=2,
            rationale="550W is ample without PoE; two give 1+1 redundancy at ~230W draw.",
        ),
        UseCaseItem(
            category_id="nos", option_id="nos-os10", qty=1,
            rationale="SmartFabric OS10's lower learning curve suits a branch team.",
        ),
        UseCaseItem(
            category_id="mgmt", option_id="mgmt-console", qty=1,
            rationale="Serial console for initial turn-up where there's no management network yet.",
        ),
    ],
    outcomes=[
        Stat(label="Ports", value="24× 1G SFP fiber"),
        Stat(label="Draw", value="~230W, fan-quiet"),
        Stat(label="Routing", value="L3 BGP/OSPF, VRF-lite"),
        Stat(label="Uplinks", value="2× 100G QSFP28"),
    ],
)

USE_CASES: list[UseCase] = [
    WIFI_EDGE,
    POE_ACCESS,
    FIBER_DISTRIBUTION,
]
