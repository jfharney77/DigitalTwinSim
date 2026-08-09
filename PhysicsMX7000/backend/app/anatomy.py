"""Chassis map for the MX7000 simulator — a stylized front elevation of
the 7U enclosure: eight single-width sled bays across the top, the
management and fabric modules in the right column, the nine-fan wall
below the bays, and the six-PSU pool along the bottom. The vertical axis
is the airflow story (bays breathe first, fans drive, PSUs sit with the
exhaust), and the fan/PSU rows being drawn *chassis-wide* rather than
per-sled is the architecture: nothing in those rows belongs to any bay.

Regions are thermal zones keyed to the engine's ``region_temps`` dict;
the frontend paints them on a fixed 20–110 °C scale. Stylized — a mental
model, not a service manual.
"""

from __future__ import annotations

from .leveling import L
from .models import ChassisMap, ChassisRegion


def _sled(i: int) -> ChassisRegion:
    return ChassisRegion(
        id=f"sled-{i + 1}", kind="bay", label=f"Sled {i + 1}",
        x=2 + i * 10, y=2, w=9, h=40,
        description=(
            "One of eight single-width bays. It can hold a dual-socket "
            "compute sled, a 16-drive storage sled, or nothing — and "
            "whatever it holds, it has no fans and no power supplies of "
            "its own. Its heat is the chassis's problem, which is the "
            "whole lesson of this simulator."
        ),
    )


def _fan(i: int) -> ChassisRegion:
    return ChassisRegion(
        id=f"fan-{i}", kind="cooling", label=f"Fan {i + 1}",
        x=2 + i * 10.7, y=44, w=9.7, h=7,
        description=(
            "One of nine hot-swap chassis fans (four front, five rear on "
            "the real machine — drawn as one shared wall here, because "
            "that is what they are). The controller runs them to hold the "
            "hottest sled at target, so one busy neighbor sets the speed "
            "— and the cubic power bill — for everyone. Click to kill "
            "this fan and watch the survivors ramp."
        ),
    )


def _psu(i: int) -> ChassisRegion:
    feed = "A" if i % 2 == 0 else "B"
    return ChassisRegion(
        id=f"psu-{i}", kind="power", label=f"PSU {i + 1}·{feed}",
        x=2 + i * 16.2, y=53, w=15.2, h=8,
        description=(
            f"One of up to six 3000 W supplies in the pooled budget. Under "
            f"grid redundancy this slot hangs off AC feed {feed} — the "
            "pool alternates feeds so losing a whole feed leaves half the "
            "supplies alive. Under N+1 every PSU shares one feed, which "
            "is exactly the difference the pooled-redundancy scenario "
            "exists to show."
        ),
    )


ANATOMY = ChassisMap(
    id="mx7000",
    name="PowerEdge MX7000 · shared-infrastructure model",
    vendor="Dell Technologies",
    form_factor="7U modular chassis — front elevation, thermal-zone view",
    generation="PowerEdge MX kinetic infrastructure",
    year=2018,
    width=100,
    height=62,
    overview=L(
        novice=(
            "This is a big 7U box that holds up to eight server 'sleds' — "
            "slide-in computers that share the box's fans and power "
            "supplies instead of carrying their own. That sharing is the "
            "entire story here. The fans belong to the box, and they spin "
            "fast enough to keep the *hottest* sled happy — so if one sled "
            "works hard while seven sit idle, all the extra fan noise and "
            "fan electricity is caused by that one neighbor. The power "
            "supplies are shared too, as one pool: you choose a policy for "
            "how many can fail. 'Grid' splits them across two separate "
            "wall feeds so even losing a whole feed keeps the box running; "
            "'N+1' only covers one supply dying. And a storage sled full "
            "of drives doesn't even have its own workload — it does "
            "whatever the compute sled that owns it asks, and you can hand "
            "it to a different owner mid-run without touching a cable. "
            "The colors show temperature: build a mix of sleds, load them "
            "unevenly, and watch who pays for whom."
        ),
        plain=(
            "The MX7000 as thermal zones: eight single-width sled bays "
            "across the top, management and fabric modules at the right, "
            "the nine-fan wall under the bays, six pooled 3000 W PSUs "
            "along the bottom. Fans and PSUs are chassis-level — no sled "
            "owns any of them. The fan controller targets the hottest "
            "sled, so one loaded sled raises the (cubic) fan bill for all "
            "eight bays; PSU redundancy is a pooled policy where 'grid' "
            "splits supplies across two AC feeds and survives a feed loss "
            "while 'N+1' does not; a storage sled's activity follows the "
            "compute sled that owns it, and ownership is a config action. "
            "Regions are painted on a fixed 20–110 °C scale."
        ),
        standard=(
            "The MX7000 drawn as what it architecturally is: eight bays "
            "that bring heat, and a chassis that brings everything the "
            "heat needs — nine shared fans, up to six pooled 3000 W PSUs, "
            "redundant management and fabric modules. The fan controller "
            "holds the *hottest* sled to target, which makes cooling a "
            "commons: one 100%-load sled sets the rpm, and the cubic fan "
            "power that follows, for seven innocent neighbors. The PSU "
            "pool is governed by policy rather than pairing — grid "
            "redundancy alternates supplies across two AC feeds and "
            "survives losing an entire feed; N+1 tolerates one supply "
            "failing but puts the whole pool on one feed. Storage sleds "
            "are composable: an MX5016s has no workload of its own, its "
            "drive activity follows its owning compute sled, and "
            "reassignment is a timed event, not a recable. The model is "
            "deliberately simple — per-slot airflow shares, first-order "
            "sled masses, a proportional controller on the max — and "
            "every constant carries a source tag, with estimates flagged."
        ),
        technical=(
            "Shared-plant model: per-sled P(util) curves (2 sockets, "
            "superlinear), slot airflow ṁ/8, first-order sled masses "
            "(τ 25 s compute / 180 s storage), P-controller on "
            "max(T_sled)−78, cubic fan law billed chassis-level; PSU pool "
            "η(load) on a Titanium-class curve, feeds alternated under "
            "grid policy, surviving-capacity check + overcurrent trip; "
            "storage sled draw keyed to owner's storage dial. Asserted: "
            "per-tick ΣP = DC, AC = DC/η; steady ΔT = DC/(ṁ·cp); grid "
            "survives a feed loss where N+1 goes dark."
        ),
        expert=(
            "Eight heat sources, one plant. Fan control on max(T)−target, "
            "rpm³ billed to the chassis; PSU pool split by feed parity "
            "under grid; storage sleds slave to owners. ΣP=DC, AC=DC/η, "
            "ΔT=DC/ṁcp. Not CFD, on purpose."
        ),
    ),
    regions=[
        *[_sled(i) for i in range(8)],
        ChassisRegion(
            id="mgmt-a", kind="management", label="MX9002m A",
            x=83, y=2, w=15, h=8,
            description=(
                "The first of two redundant MX9002m management modules — "
                "the chassis's OpenManage Enterprise Modular brain. Here "
                "it is the implied narrator: the shared fan policy, the "
                "power-budget cap, and the redundancy policy are all "
                "decisions this module enforces."
            ),
        ),
        ChassisRegion(
            id="mgmt-b", kind="management", label="MX9002m B",
            x=83, y=11, w=15, h=8,
            description=(
                "The second management module. Management is the one "
                "shared service the sleds could not even boot without — "
                "it owns slot power-on order and the chassis power budget."
            ),
        ),
        ChassisRegion(
            id="fabric-a", kind="fabric", label="Fabric A",
            x=83, y=21, w=15, h=10,
            description=(
                "Fabric A I/O module (MX9116n class). The MX7000's "
                "no-midplane design means sleds mate directly to these "
                "switches; in this power model the pair is a fixed load "
                "riding the shared PSU pool."
            ),
        ),
        ChassisRegion(
            id="fabric-b", kind="fabric", label="Fabric B",
            x=83, y=32, w=15, h=10,
            description=(
                "Fabric B I/O module — the redundant partner. Two fabrics, "
                "two management modules, six PSUs, nine fans: everything "
                "shared comes in pools, and every pool has a policy."
            ),
        ),
        *[_fan(i) for i in range(9)],
        *[_psu(i) for i in range(6)],
    ],
    sources=[
        {"label": "Dell PowerEdge MX7000 spec sheet",
         "url": "https://i.dell.com/sites/csdocuments/Product_Docs/en/poweredge-mx7000-spec-sheet.pdf"},
        {"label": "Dell EMC PowerEdge MX7000 Technical Guide",
         "url": "https://i.dell.com/sites/csdocuments/Product_Docs/en/dell_emc_poweredge_mx7000_technical_guide.pdf"},
        {"label": "Expansion-roster spec (this repo)",
         "url": "../physics_specs/10-additional-products.md"},
    ],
)
