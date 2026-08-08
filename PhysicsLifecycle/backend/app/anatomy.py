"""Lifecycle maps — one shared diagram: the telecom build-out band on
top (coverage, sites, integration ledger, environment) and the
laptop-lifecycle band below (device, battery, materials, grid, the
carbon ledger, second life). Two overviews over one geometry."""

from __future__ import annotations

from .leveling import L
from .models import PCF_NOTE, LifecycleMap, MapRegion


def _regions() -> list[MapRegion]:
    return [
        MapRegion(
            id="coverage", kind="coverage", label="Coverage map",
            x=2, y=1, w=44, h=12,
            description=(
                "The subscribers' view: cells go gray when sites go "
                "dark. Telecom availability is measured in people, "
                "not servers."
            ),
        ),
        MapRegion(
            id="sites", kind="site", label="Cell sites (XR-class)",
            x=50, y=1, w=48, h=12,
            description=(
                "Short-depth ruggedized compute on hilltops and "
                "rooftops — reachable by ladder, not by elevator. "
                "Colored by the share currently dark."
            ),
        ),
        MapRegion(
            id="integration", kind="integration", label="Integration ledger",
            x=2, y=17, w=44, h=10,
            description=(
                "The product's reason to exist: DIY = validate server "
                "+ OS + RAN software per site (and hit the mismatches "
                "the matrix guarantees); Blocks = one tested bundle. "
                "Colored by hours burned."
            ),
        ),
        MapRegion(
            id="environment", kind="environment", label="Environment",
            x=50, y=17, w=48, h=10,
            description=(
                "Cell sites are harsh: the heatwave event pushes "
                "ambient past the standard ceiling and separates the "
                "extended-temperature fleet from the one that saved "
                "money on the spec sheet."
            ),
        ),
        MapRegion(
            id="device", kind="device", label="The laptop",
            x=2, y=32, w=30, h=12,
            description=(
                "One device, eight simulated years, three scheduled "
                "crises (a broken port, a worn battery, insufficient "
                "RAM). Each resolves per the design: a part, or a "
                "whole new device."
            ),
        ),
        MapRegion(
            id="battery", kind="battery", label="Battery",
            x=36, y=32, w=14, h=12,
            description=(
                "The year-3.5 fork in the road. Screwed: a 12 kgCO2e "
                "part. Glued: a 280 kgCO2e new device."
            ),
        ),
        MapRegion(
            id="materials", kind="materials", label="Materials & e-waste",
            x=54, y=32, w=20, h=12,
            description=(
                "Recycled-content chassis on the way in; the e-waste "
                "scale on the way out. Colored by kilograms discarded."
            ),
        ),
        MapRegion(
            id="grid", kind="grid", label="Grid",
            x=78, y=32, w=20, h=12,
            description=(
                "The electricity behind the use phase: 0.05–0.85 "
                "kgCO2e/kWh from clean to coal. The same laptop's "
                "footprint can be dominated by either phase — the "
                "grid decides."
            ),
        ),
        MapRegion(
            id="ledger", kind="ledger", label="Carbon ledger (closes)",
            x=2, y=49, w=64, h=10,
            description=(
                "Total = embodied + use, every tick, asserted. The "
                "headline is carbon per useful-year — the only "
                "number that lets a sealed and a serviceable design "
                "be compared honestly."
            ),
        ),
        MapRegion(
            id="secondlife", kind="secondlife", label="Second life",
            x=70, y=49, w=28, h=10,
            description=(
                "At first-owner end the design is judged: modular "
                "choices make refurbishment economic and the carbon "
                "amortizes over more years; sealed ones go to the "
                "scale on the left."
            ),
        ),
    ]


def _map(map_id: str, name: str, gen: str, overview: str) -> LifecycleMap:
    return LifecycleMap(
        id=map_id,
        name=name,
        vendor="Dell Technologies",
        form_factor="Lifecycle view",
        generation=gen,
        year=2026,
        width=100,
        height=61,
        overview=overview,
        regions=_regions(),
        sources=[
            {"label": "physics_specs/08-telecom-and-sustainability.md (this repo)",
             "url": "../physics_specs/08-telecom-and-sustainability.md"},
            {"label": "Dell Product Carbon Footprint reports (the calibration source)",
             "url": PCF_NOTE},
        ],
    )


TELECOM = _map(
    "telecomblocks",
    "Telecom Infrastructure Blocks · the build-out",
    "Open RAN engineered blocks",
    L(
        novice=(
            "Building a mobile network means hundreds of small "
            "computer sites on rooftops and hilltops, each of which "
            "must run a tower's software on a particular server on a "
            "particular operating system — and the combinations are "
            "where projects die. Do it yourself and every site is a "
            "small integration project with a guaranteed fraction of "
            "surprises; buy pre-validated blocks and a site is a "
            "delivery. The other lesson is weather: these sites live "
            "outdoors, and on a 48-degree day the fleet that paid "
            "for extended-temperature hardware keeps broadcasting "
            "while the one that didn't goes quiet — measured in "
            "subscribers, because that is the unit telecom actually "
            "bills in."
        ),
        standard=(
            "The fleet engine's harshest use case: DIY deployment "
            "pays 10 h/site of compatibility-matrix validation and "
            "hits a deterministic mismatch every 12th site (16 h + an "
            "outage each); Blocks pays 1.5 h/site for a tested "
            "bundle. The heatwave event (48 °C, 3 days) drops ~30% "
            "of a standard-temp fleet and none of an XR-class one; "
            "coverage counts subscribers and availability is "
            "site-hours honest. The compatibility-combination "
            "explosion (A×B×C versions) is the explain-tab equation "
            "the whole product answers."
        ),
        expert=(
            "DIY: 10 h/site + mismatch every 12th (16 h + outage). "
            "Blocks: 1.5 h bundle. 48 °C: −30% standard fleet, −0% "
            "XR. A×B×C is the villain; the bundle is the answer."
        ),
    ),
)

CIRCULAR = _map(
    "circulardesign",
    "Circular Design · a laptop's eight years",
    "Concept Luna lineage",
    L(
        novice=(
            "Design a laptop with four checkboxes — screwed or glued "
            "battery, socketed or soldered memory, recycled or virgin "
            "chassis, modular or integrated ports — then watch eight "
            "years happen to it. A port breaks in year two and a "
            "half; the battery fades at three and a half; the memory "
            "stops being enough at four and a half. Each crisis "
            "costs either a small part or an entire new machine, "
            "depending on the checkboxes. The scoreboard is carbon "
            "per useful year, and the grid the laptop plugs into "
            "matters as much as the factory it came from. Every "
            "number here is a labeled estimate — Dell publishes real "
            "per-product carbon reports, and swapping those numbers "
            "in is the intended homework."
        ),
        standard=(
            "Archetype F: design decisions → eight accounted years. "
            "Embodied ~280 kgCO2e (−12% recycled chassis), use phase "
            "= kWh × grid (0.05–0.85 kgCO2e/kWh — the clean-vs-coal "
            "run decides which phase dominates), and three scheduled "
            "events that resolve as parts (6–12 kg) or whole devices "
            "(the full embodied, again). The ledger closes every "
            "tick (total = embodied + use, asserted); the headline "
            "is carbon per useful-year; refurb success is a function "
            "of the disassembly score, so modularity literally buys "
            "a second life. Spec 08's honesty rule is test-enforced: "
            "every carbon constant is a labeled estimate pointing at "
            "Dell's PCF reports."
        ),
        expert=(
            "Design bits → 8y of consequences. E≈280·(1−0.12r); "
            "U=kWh·grid; events → part|device. Ledger closes "
            "(asserted); metric = kg/useful-yr; refurb = f(minutes). "
            "PCF is the calibration; estimates say so."
        ),
    ),
)


MAPS: dict[str, LifecycleMap] = {
    "telecomblocks": TELECOM,
    "circulardesign": CIRCULAR,
}
