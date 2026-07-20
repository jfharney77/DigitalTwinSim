"""Component catalog: what an IR7000 + PowerCool deployment is built from.

Same pattern as the other twins: categories map onto rack regions via
``region_ids`` (ids from anatomy.py; an empty list means the item is not a
physical part of the drawn loop — the rack frame itself, coolant chemistry,
services). Written for a technically skilled reader new to liquid cooling;
jargon (ORv3, CDU, eRDHx, quick disconnect, PG25, TCS/FWS, ...) is spelled
out on first use. Figures are illustrative, anchored to Dell's OCP-2024
announcement and PowerCool product material.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

_BAY_REGIONS = [f"coldplate-b{i}" for i in (1, 2, 3, 4)]
_MANIFOLD_REGIONS = ["manifold-supply", "manifold-return"]

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="rack",
        name="Rack platform",
        blurb=(
            "The frame everything else mounts in. The IR7000 adopts the "
            "Open Compute ORv3 standard — wider payload space, a shared DC "
            "busbar, and liquid-cooling provisions designed in rather than "
            "bolted on."
        ),
        limits="33–264 kW per rack today; Dell's roadmap points to 480 kW",
        region_ids=[],
        options=[
            CatalogOption(
                id="rack-ir7000",
                name="Integrated Rack 7000 (ORv3, 21-inch)",
                summary="Dell's extreme-density rack: open standard, busbar power, liquid-native.",
                details=(
                    "ORv3 (Open Rack v3) is the Open Compute Project's rack "
                    "standard: a 21-inch-wide payload bay in roughly the "
                    "same floor footprint as a classic 19-inch rack, power "
                    "delivered by shelf-fed DC busbar instead of per-server "
                    "supplies, and mounting provisions for manifolds and "
                    "CDUs. The IR7000 is Dell's productization — tall (up "
                    "to 50 OU), seismically rated, and shipped under IRSS "
                    "with the payload integrated and the loop pre-plumbed."
                ),
            ),
            CatalogOption(
                id="rack-ir5000",
                name="Integrated Rack 5000 (19-inch)",
                summary="The EIA 19-inch sibling for sites standardized on classic racks.",
                details=(
                    "Not every site can adopt ORv3. The IR5000 carries the "
                    "same PowerCool liquid-cooling approach into a standard "
                    "19-inch EIA frame, trading some density for "
                    "compatibility with existing rows, containment, and "
                    "service tooling. The loop architecture — CDU, "
                    "manifolds, cold plates, optional rear door — is the "
                    "same story at lower wattage."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="cdu",
        name="Coolant distribution",
        blurb=(
            "The pump house. The CDU circulates the rack loop, exchanges "
            "heat to facility water, and keeps the two liquids forever "
            "separate."
        ),
        limits="~160 kW per in-rack unit; pair units or go row-scale beyond",
        region_ids=["cdu"],
        options=[
            CatalogOption(
                id="cdu-rcdu",
                name="PowerCool in-rack CDU (RCDU)",
                summary="Rack-mounted, redundant-pump CDU serving its own rack.",
                details=(
                    "The rack-mounted coolant distribution unit takes a few "
                    "rack units at the bottom of the frame: redundant "
                    "pumps, a plate heat exchanger against facility water, "
                    "filtration, and the controls that hold the "
                    "supply-return temperature difference steady as load "
                    "moves. One RCDU class-rates on the order of 160 kW. "
                    "Keeping the CDU in the rack keeps the failure domain "
                    "small: a pump problem affects one rack, not a row."
                ),
            ),
            CatalogOption(
                id="cdu-row",
                name="Row-scale CDU",
                summary="A floor-standing CDU serving a whole row of racks.",
                details=(
                    "Beyond a few hundred kilowatts per rack, or when the "
                    "operator prefers plant equipment out of the IT frame, "
                    "a floor-standing CDU serves the row through underfloor "
                    "or overhead piping. Larger pumps run more efficiently "
                    "and maintenance moves to the plant aisle — at the cost "
                    "of a wider failure domain and more site plumbing. Most "
                    "AI-factory designs mix both: RCDUs for compute racks, "
                    "row CDUs for shared infrastructure."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="door",
        name="Rear-door heat exchange",
        blurb=(
            "The air-side catch. Cold plates take ~90% of the heat; the "
            "rear door captures the rest so the room never has to."
        ),
        limits="Sized to the rack's air-side remainder (tens of kW)",
        region_ids=["door"],
        options=[
            CatalogOption(
                id="door-erdhx",
                name="PowerCool enclosed rear-door heat exchanger (eRDHx)",
                summary="Active fan-assisted door coil; makes the rack room-neutral.",
                details=(
                    "The enclosed rear-door heat exchanger seals the rack's "
                    "airflow path: internal fans draw exhaust air through a "
                    "water coil in the rear door and return it, cooled, "
                    "inside the enclosure. The room-facing effect is a rack "
                    "that is thermally invisible — no hot aisle, no "
                    "added CRAC load — which is what lets a legacy "
                    "air-cooled building host a 264 kW row. Dell quotes up "
                    "to 60% cooling-energy savings versus conventional room "
                    "cooling."
                ),
            ),
            CatalogOption(
                id="door-passive",
                name="Passive rear-door coil",
                summary="Fanless coil for moderate air-side loads.",
                details=(
                    "Where the air-side remainder is small, a passive coil "
                    "in the rear door — no fans, driven only by the "
                    "servers' own airflow — removes most of it with zero "
                    "added energy and nothing to fail. The trade is "
                    "capacity: past a few kilowatts of air-side heat, the "
                    "pressure drop across a passive coil starts fighting "
                    "the server fans, and the active eRDHx wins."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="coldplate",
        name="Cold plates & payload loops",
        blurb=(
            "Where heat enters the liquid. Cold plates clamp onto the "
            "processors of whatever payload the site racks; to the loop, "
            "the payload is just resistance."
        ),
        limits="Per-chip plates up to ~1 kW class parts (Blackwell, EPYC, Xeon)",
        region_ids=_BAY_REGIONS,
        options=[
            CatalogOption(
                id="plate-dlc",
                name="Direct liquid cooling (DLC) cold-plate kits",
                summary="Machined copper plates with coolant channels, per CPU/GPU.",
                details=(
                    "Direct liquid cooling replaces each processor's "
                    "heatsink with a cold plate: a copper block whose "
                    "internal micro-channels carry coolant a millimeter or "
                    "two from the silicon. Because water carries roughly "
                    "3,500 times more heat per volume than air, a plate the "
                    "size of a matchbox removes what a fist-sized heatsink "
                    "and a wall of fans could not. Dell factory-fits DLC "
                    "kits on the payloads that need them — a kilowatt-class "
                    "Blackwell GPU cannot ship any other way."
                ),
            ),
            CatalogOption(
                id="plate-leaktray",
                name="Bay leak containment",
                summary="Drip trays + rope sensors under every bay's plumbing.",
                details=(
                    "Defense in depth for the one failure liquid cooling "
                    "cannot talk its way out of. Each bay's branch plumbing "
                    "sits over a drip tray with a rope-style moisture "
                    "sensor; a wet rope raises an alarm and, policy "
                    "permitting, the CDU isolates the branch. Combined with "
                    "dry-break quick disconnects, the design goal is that a "
                    "single fitting failure wets a tray, not a server."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="manifold",
        name="Manifolds & quick disconnects",
        blurb=(
            "The rack's arteries: vertical supply and return pipes with a "
            "blind-mate tap for every bay."
        ),
        limits="Sized for hundreds of L/min at full rack load",
        region_ids=_MANIFOLD_REGIONS,
        options=[
            CatalogOption(
                id="mani-orv3",
                name="ORv3 vertical manifold pair",
                summary="Full-height supply/return manifolds with per-bay branches.",
                details=(
                    "The manifold pair runs the height of the rack — cool "
                    "supply up one side, warm return down the other — with "
                    "a branch tap at every payload position. Generous pipe "
                    "diameter is deliberate: pressure drop is pump energy, "
                    "and pump energy is overhead paid every hour of the "
                    "rack's life. The manifolds are the part of the loop "
                    "that ships welded, pressure-tested, and never touched "
                    "again."
                ),
            ),
            CatalogOption(
                id="mani-qd",
                name="Blind-mate dry-break quick disconnects",
                summary="Self-sealing couplings; pull a sled without draining the loop.",
                details=(
                    "Every branch ends in a quick disconnect (QD): a "
                    "coupling whose halves each seal automatically the "
                    "instant they part, losing at most a droplet. Blind-"
                    "mate versions engage as the sled slides home, so "
                    "service is exactly the hot-swap experience the compute "
                    "twins take for granted — the liquid loop's equivalent "
                    "of a hot-plug drive bay."
                ),
            ),
            CatalogOption(
                id="mani-coolant",
                name="Treated coolant (PG25 class)",
                summary="Propylene-glycol mix with corrosion and biological inhibitors.",
                details=(
                    "The working fluid is not tap water. A typical fill is "
                    "PG25 — 25% propylene glycol — with inhibitor packages "
                    "against corrosion and biological growth, chosen to "
                    "protect copper plates, brazed exchangers, and "
                    "elastomer seals over a decade of service. Coolant "
                    "chemistry is a maintenance item: sampled, tested, and "
                    "topped up on schedule like any plant fluid."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="sensor",
        name="Instrumentation & leak detection",
        blurb=(
            "The loop's nervous system — and the concrete thing behind the "
            "'liquid before silicon' interlock every liquid-cooled compute "
            "twin depends on."
        ),
        limits="Per-branch flow/temp; rope leak sensing along all plumbing",
        region_ids=["sensors"],
        options=[
            CatalogOption(
                id="sens-flow",
                name="Per-branch flow & temperature probes",
                summary="Confirms every cold plate actually receives coolant.",
                details=(
                    "A whole-rack flow reading can look perfect while one "
                    "blocked branch quietly cooks a server, so "
                    "commissioning and steady-state monitoring both work "
                    "branch by branch: flow and supply/return temperature "
                    "on each bay. Flow times temperature rise is heat — the "
                    "same conservation law the trace enforces — so the "
                    "sensors double as a per-bay power meter."
                ),
            ),
            CatalogOption(
                id="sens-leak",
                name="Rope leak sensors + drip trays",
                summary="Moisture-sensing cable along manifolds and under fittings.",
                details=(
                    "Rope sensors — cables that alarm when any point along "
                    "their length gets wet — run the manifolds and every "
                    "tray. Response policy is graded: a damp QD raises a "
                    "ticket; a wet manifold rope can trip the branch "
                    "valves. The design assumption is not that leaks never "
                    "happen but that they are found while they are still "
                    "droplets."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="power",
        name="Rack power",
        blurb=(
            "The other half of the same number: every watt the busbar "
            "delivers, the loop must remove. Power and cooling are sized "
            "as a matched pair."
        ),
        limits="ORv3 shelf-fed DC busbar · 33–264 kW envelopes",
        region_ids=["power-shelf"],
        options=[
            CatalogOption(
                id="pow-orv3",
                name="ORv3 power shelves + DC busbar",
                summary="Centralized rectification feeding a full-height busbar.",
                details=(
                    "As in the XE9712 twin: power shelves rectify facility "
                    "AC to DC once and a copper busbar distributes it to "
                    "every payload position, cutting conversion losses and "
                    "per-server supplies. In the thermal twin this region "
                    "is the *input* meter — the busbar wattage is, to the "
                    "watt, the heat load the CDU and door will see a few "
                    "seconds later."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="facility",
        name="Facility integration",
        blurb=(
            "Where the heat finally goes. The rack loop ends at a heat "
            "exchanger; what the building does with the warm water is a "
            "design choice."
        ),
        limits="Facility water loop (TCS/FWS) required at the row",
        region_ids=["facility"],
        options=[
            CatalogOption(
                id="fac-tcs",
                name="Technology cooling loop connection",
                summary="The building-side water loop the CDU exchanges into.",
                details=(
                    "Data centers separate the technology cooling system "
                    "(TCS) — the clean, temperature-controlled loop that "
                    "visits the racks — from the facility water system "
                    "(FWS) that reaches cooling towers or dry coolers. The "
                    "CDU's plate exchanger is the boundary: rack coolant on "
                    "one side, TCS water on the other, heat crossing and "
                    "chemistry not. Site readiness for liquid cooling "
                    "mostly means getting this loop to the row."
                ),
            ),
            CatalogOption(
                id="fac-reuse",
                name="Heat reuse / warm-water economization",
                summary="Treat 264 kW of warm water as a product, not a waste stream.",
                details=(
                    "Direct liquid cooling runs happily with warm supply "
                    "water — often 30–40 °C — which means the return is "
                    "warm enough to matter: district-heating feeds, office "
                    "heating, or dry coolers that dissipate to outdoor air "
                    "for a fraction of a chiller's energy. At AI-factory "
                    "scale the difference between rejecting and reusing a "
                    "megawatt of heat shows up on both the power bill and "
                    "the sustainability report."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="payload",
        name="IT payload",
        blurb=(
            "What the loop exists to cool. The bays are drawn generic "
            "because the loop does not care — to the cooling system, every "
            "payload is heat."
        ),
        limits="Any DLC-fitted Dell payload; the loop sees only watts",
        region_ids=_BAY_REGIONS,
        options=[
            CatalogOption(
                id="pay-xe9712",
                name="PowerEdge XE9712 (GB200 NVL72)",
                summary="The rack-scale AI system — this repo's tenth twin — as payload.",
                details=(
                    "The XE9712's 72 liquid-cooled Blackwell GPUs are "
                    "exactly the payload class the IR7000 and PowerCool "
                    "exist for; its power-on trace even interlocks on this "
                    "twin's verify phase (liquid before silicon). Run the "
                    "two twins side by side for the full picture: that "
                    "twin's 120 kW is this twin's 120 kW, seen from the "
                    "other side of the cold plate."
                ),
            ),
            CatalogOption(
                id="pay-xe9685l",
                name="PowerEdge XE9685L (dense GPU nodes)",
                summary="4U liquid-cooled nodes — up to 96 GPUs per IR7000 rack.",
                details=(
                    "The XE9685L packs two AMD EPYC CPUs and eight NVIDIA "
                    "GPUs into a liquid-cooled 4U node; Dell's density "
                    "claim is up to 96 GPUs per IR7000 rack. Where the "
                    "XE9712 is one integrated NVL72 system, XE9685L racks "
                    "are configure-to-order — a reminder that the loop "
                    "serves whatever the site racks, one bay at a time."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="management",
        name="Monitoring & management",
        blurb=(
            "The loop is plant equipment with a service life measured in "
            "years; something has to watch it every hour of them."
        ),
        limits="Telemetry into the same planes the compute twins use",
        region_ids=["sensors", "cdu"],
        options=[
            CatalogOption(
                id="mgmt-ome",
                name="Dell OpenManage + CDU telemetry",
                summary="Pump, flow, temperature, and leak telemetry in the fleet view.",
                details=(
                    "The CDU and door controllers publish their telemetry — "
                    "pump speeds, flows, temperatures, leak status — into "
                    "Dell OpenManage Enterprise alongside the servers' own "
                    "BMC data, so the operator sees compute and cooling as "
                    "one system. The interlocks live here too: the rule "
                    "that no GPU powers on without verified coolant flow is "
                    "management-plane policy, enforced through the same "
                    "path."
                ),
            ),
            CatalogOption(
                id="mgmt-services",
                name="Dell liquid-cooling deployment services",
                summary="Site assessment, commissioning, and coolant lifecycle service.",
                details=(
                    "Most operators have never commissioned a hydraulic "
                    "system. Dell's services cover the site assessment "
                    "(can the floor take the weight, can the TCS reach the "
                    "row), the fill/degas/verify commissioning this twin's "
                    "trace walks through, and the ongoing coolant-chemistry "
                    "and filter service — the plant-maintenance habits that "
                    "IT organizations are still acquiring."
                ),
            ),
        ],
    ),
]
