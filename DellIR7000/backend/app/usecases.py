"""Worked use cases: what an IR7000 + PowerCool loop actually gets built for.

Each use case is a narrative plus a build sheet whose category/option ids
must resolve against catalog.py (enforced in tests/test_catalog.py).
Written for a technically skilled reader new to liquid cooling. Quantities
count the unit named (racks, doors, CDUs).
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="nvl72",
        title="Cooling a GB200 NVL72 row",
        summary=(
            "Eight XE9712 racks in IR7000 frames, each with its own RCDU "
            "and rear door: roughly a megawatt of AI compute whose cooling "
            "is designed with the compute, not after it."
        ),
        narrative=[
            (
                "The workload: the AI-factory row from the XE9712 twin's "
                "training use case — eight GB200 NVL72 racks, about 120 kW "
                "each. Seen from this twin, the row is not 576 GPUs; it is "
                "roughly a megawatt of heat appearing in eight points along "
                "thirty meters of floor, every hour, for years. No "
                "air-cooling architecture at any fan speed removes a "
                "megawatt from that footprint; the row is liquid-cooled or "
                "it does not exist."
            ),
            (
                "The design: one PowerCool RCDU per rack keeps each rack a "
                "self-contained failure domain — a pump fault degrades one "
                "rack, and its redundant partner carries the load while "
                "service happens on dry-break disconnects. Enclosed rear "
                "doors catch the ~10% air-side remainder so the row is "
                "room-neutral and the building's air handling never "
                "notices. The technology cooling loop reaches the row "
                "once, and every CDU exchanges into it; commissioning "
                "walks this twin's fill-pump-verify trace eight times "
                "before a single GPU is allowed to power on."
            ),
            (
                "Run this twin beside the XE9712 twin and the story "
                "closes: the GPU twin's power-on trace pauses at 'coolant "
                "loop primes — liquid before silicon', and this twin is "
                "what that pause is waiting for. Power and cooling are one "
                "number wearing two units."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="rack", option_id="rack-ir7000", qty=8,
                rationale="ORv3 frames with busbar power and pre-plumbed manifolds, one per NVL72.",
            ),
            UseCaseItem(
                category_id="cdu", option_id="cdu-rcdu", qty=8,
                rationale="Per-rack CDUs keep each rack its own failure domain.",
            ),
            UseCaseItem(
                category_id="door", option_id="door-erdhx", qty=8,
                rationale="Room-neutral racks — the building's air handling stays out of it.",
            ),
            UseCaseItem(
                category_id="payload", option_id="pay-xe9712", qty=8,
                rationale="The heat source: ~120 kW of Grace-Blackwell per rack.",
            ),
            UseCaseItem(
                category_id="sensor", option_id="sens-flow", qty=8,
                rationale=(
                    "Per-branch verification backs the liquid-before-"
                    "silicon interlock on every rack."
                ),
            ),
            UseCaseItem(
                category_id="facility", option_id="fac-tcs", qty=1,
                rationale="One technology cooling loop serves the row; every CDU exchanges into it.",
            ),
            UseCaseItem(
                category_id="management", option_id="mgmt-ome", qty=1,
                rationale="Compute and cooling telemetry in one fleet view, one interlock policy.",
            ),
        ],
        outcomes=[
            Stat(label="Heat removed", value="~1 MW across 8 racks"),
            Stat(label="Row air-conditioning impact", value="None — room-neutral"),
            Stat(label="Failure domain", value="One rack per CDU"),
            Stat(label="Compute twin", value="Pairs with the XE9712 power-on trace"),
        ],
    ),
    UseCase(
        id="retrofit",
        title="Dense AI in a legacy air-cooled building",
        summary=(
            "Two IR5000 racks with rear-door heat exchange drop a compact "
            "GPU cluster into a building designed for 8 kW racks — no "
            "chilled-water plant rebuild, no hot-aisle redesign."
        ),
        narrative=[
            (
                "The workload: an enterprise wants a modest GPU training "
                "and inference cluster — two racks, some 60 kW each — but "
                "its data center was built for 8 kW air-cooled racks: "
                "raised floor, CRAC units, no liquid anywhere. A forklift "
                "upgrade of the room for two racks is unjustifiable; "
                "hosting them in a colo splits the estate. The question is "
                "whether density can visit a legacy room politely."
            ),
            (
                "The design: 19-inch IR5000 frames keep the existing rows, "
                "containment, and tooling. Direct-liquid cold plates on "
                "the GPU nodes take the bulk of the heat into a compact "
                "per-rack CDU loop, and the enclosed rear door catches the "
                "air-side remainder — so each 60 kW rack presents to the "
                "room as approximately nothing. The only construction is "
                "getting a technology cooling loop to two positions, a "
                "plumbing job measured in days. Passive doors were "
                "considered and declined: at this air-side load the "
                "active eRDHx's fans earn their keep."
            ),
            (
                "The operational change is cultural as much as technical: "
                "the IT team acquires plant habits — coolant sampling, "
                "filter service, leak-alarm drills — packaged in Dell's "
                "deployment and lifecycle services until they are routine. "
                "The reward is a ten-year density path inside a building "
                "everyone had written off."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="rack", option_id="rack-ir5000", qty=2,
                rationale="19-inch frames fit the existing rows and tooling.",
            ),
            UseCaseItem(
                category_id="cdu", option_id="cdu-rcdu", qty=2,
                rationale="Self-contained per-rack loops; no row plant to build.",
            ),
            UseCaseItem(
                category_id="door", option_id="door-erdhx", qty=2,
                rationale="Active doors make 60 kW racks invisible to the CRAC plant.",
            ),
            UseCaseItem(
                category_id="payload", option_id="pay-xe9685l", qty=2,
                rationale="Dense liquid-cooled GPU nodes, configure-to-order per rack.",
            ),
            UseCaseItem(
                category_id="coldplate", option_id="plate-leaktray", qty=2,
                rationale="Leak containment first — this building has never seen water.",
            ),
            UseCaseItem(
                category_id="facility", option_id="fac-tcs", qty=1,
                rationale="A short TCS spur to two positions is the only construction.",
            ),
            UseCaseItem(
                category_id="management", option_id="mgmt-services", qty=1,
                rationale="Commissioning and coolant lifecycle until plant habits are routine.",
            ),
        ],
        outcomes=[
            Stat(label="Density achieved", value="60 kW racks in an 8 kW building"),
            Stat(label="Room modifications", value="One TCS spur; no CRAC changes"),
            Stat(label="Estate", value="Stays on-premises, one row"),
            Stat(label="Path forward", value="Same loop scales with next payload"),
        ],
    ),
    UseCase(
        id="maxdensity",
        title="Max-density HPC with heat reuse",
        summary=(
            "A research site runs IR7000 racks at the full 264 kW envelope "
            "and pipes the warm return water into the campus heating loop — "
            "the megawatt is spent twice."
        ),
        narrative=[
            (
                "The workload: a national-lab-class HPC site refreshing "
                "toward exascale-era density — CPU and GPU sleds at the "
                "IR7000's full 264 kW per-rack envelope, packed tight "
                "because interconnect latency scales with cable length. "
                "The site has a second mandate: an energy-reuse target "
                "written into its funding, with the campus district-"
                "heating loop fifty meters away."
            ),
            (
                "The design: warm-water direct liquid cooling end to end. "
                "The loop runs deliberately hot — supply in the high 30s "
                "Celsius, which modern silicon tolerates — because the "
                "warmer the return, the more useful the heat. Row-scale "
                "CDUs feed the racks (at 264 kW each, in-rack units would "
                "pair up anyway) and the technology loop's return side "
                "exchanges into the campus heating network before "
                "finishing at dry coolers. Rear doors are passive: at "
                "this design point almost everything wears a cold plate, "
                "and the air-side remainder is small."
            ),
            (
                "The result inverts the usual accounting: cooling stops "
                "being a 30% overhead line and becomes a small negative "
                "one, because the heat displaces gas the campus would "
                "have burned. Per-branch instrumentation doubles as the "
                "billing meter for reused heat — flow times temperature "
                "rise, the same conservation law this twin's trace "
                "enforces, now with a price on it."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="rack", option_id="rack-ir7000", qty=12,
                rationale="Full 264 kW ORv3 envelopes; density keeps the interconnect short.",
            ),
            UseCaseItem(
                category_id="cdu", option_id="cdu-row", qty=3,
                rationale="Row-scale pumping suits 264 kW racks and plant-aisle service.",
            ),
            UseCaseItem(
                category_id="door", option_id="door-passive", qty=12,
                rationale="Nearly everything is plated; passive coils cover the sliver of air heat.",
            ),
            UseCaseItem(
                category_id="coldplate", option_id="plate-dlc", qty=12,
                rationale="Warm-water DLC on every socket is what makes reuse-grade return temps.",
            ),
            UseCaseItem(
                category_id="manifold", option_id="mani-coolant", qty=1,
                rationale="Chemistry program sized for a decade of high-temperature service.",
            ),
            UseCaseItem(
                category_id="facility", option_id="fac-reuse", qty=1,
                rationale="The mandate: return water feeds the campus heating loop first.",
            ),
            UseCaseItem(
                category_id="sensor", option_id="sens-flow", qty=12,
                rationale="Per-branch flow × ΔT is also the reused-heat billing meter.",
            ),
        ],
        outcomes=[
            Stat(label="Rack envelope", value="264 kW × 12 racks"),
            Stat(label="Heat reused", value="Campus district heating, then dry coolers"),
            Stat(label="Chiller energy", value="Near zero — warm-water design"),
            Stat(label="Cooling overhead", value="Turns from cost line to credit"),
        ],
    ),
]
