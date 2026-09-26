"""System maps for the AI-compute simulator — three stylized views whose
region ids key the engine's ``region_temps``. Same idiom as the physics
suite's other apps: mental models, not service manuals. The two servers
are top-down (front at x=0); the rack is a front elevation.
"""

from __future__ import annotations

from .leveling import L
from .models import SystemMap, SystemRegion


XE7745 = SystemMap(
    id="xe7745",
    name="PowerEdge XE7745 · air-cooled PCIe GPU density",
    vendor="Dell Technologies",
    form_factor="4U rack server — top-down thermal view",
    generation="PCIe Gen5 GPU platform, dual AMD EPYC 9005",
    year=2024,
    width=100,
    height=52,
    overview=L(
        novice=(
            "A four-rack-unit server built to hold up to eight full-size "
            "graphics cards, cooled by air alone. The front wall of "
            "sixteen fans pushes air across the processors and then "
            "through the row of graphics cards behind them. Here is the "
            "unfairness this machine teaches: the air warms as it "
            "travels, so the card in the worst seat breathes the hottest "
            "air and slows down first — even though all eight cards are "
            "identical. And moving that much air is itself expensive: at "
            "full speed the fans alone draw hundreds of watts."
        ),
        standard=(
            "The XE7745 top-down: fan wall behind the NVMe bay, two CPUs "
            "mid-chassis, then the field of eight double-wide PCIe GPUs "
            "(300–600 W tiers) sharing one front-to-back airstream. The "
            "personality is positional thermal inequality — each riser "
            "slot inhales air its neighbors have warmed, so per-slot "
            "inlet preheat accumulates and the worst position throttles "
            "first, which is why the instruments show hottest and "
            "coolest GPU separately. Fan overhead is the other lesson: "
            "sixteen fans at full bore are a triple-digit-watt tax on "
            "the same PSUs that feed the GPUs. Contrast with the XE9680 "
            "(one shared SXM fate) and the XE9712 (liquid, where the "
            "whole airflow story disappears)."
        ),
        expert=(
            "Per-slot preheat gradient → positional throttle order; "
            "hottest/coolest spread is the instrument. 16-fan wall, "
            "rpm³: cooling overhead is triple-digit watts. PCIe-attached "
            "8×600 W ceiling ≈ 6–10 kW DC."
        ),
    ),
    regions=[
        SystemRegion(
            id="nvme", kind="storage", label="NVMe bay",
            x=0.5, y=0.5, w=6, h=51,
            description="Front bay of up to eight E3.S NVMe drives — first heat into the airstream.",
        ),
        SystemRegion(
            id="fanwall", kind="cooling", label="Fan wall ×16",
            x=8, y=0.5, w=7, h=51,
            description=(
                "Sixteen hot-swap fan modules, drawn as one wall — Dell's "
                "spec sheet lists twelve at the front and four dual-fan "
                "modules on the mid tray. Power goes with the "
                "cube of speed: the difference between 60% and 100% rpm "
                "is the difference between tens and hundreds of watts of "
                "pure overhead."
            ),
        ),
        SystemRegion(
            id="cpu1", kind="cpu", label="CPU 1",
            x=18, y=3, w=13, h=20,
            description="First AMD EPYC 9005 socket — feeds the GPUs, preheats their air.",
        ),
        SystemRegion(
            id="cpu2", kind="cpu", label="CPU 2",
            x=18, y=29, w=13, h=20,
            description="Second socket.",
        ),
        SystemRegion(
            id="dimm", kind="memory", label="DIMMs",
            x=33, y=3, w=6, h=46,
            description="Twenty-four DDR5 DIMM slots between the CPUs and the GPU field.",
        ),
        *[
            SystemRegion(
                id=f"gpu-{i}", kind="gpu", label=f"GPU {i + 1}",
                x=42 + (i % 4) * 12, y=3 if i < 4 else 29, w=10, h=20,
                description=(
                    f"PCIe riser position {i + 1}. "
                    + (
                        "An early seat in the airstream — coolest air, "
                        "last to throttle."
                        if i % 4 == 0 else
                        "A downstream seat: this card breathes air the "
                        "cards before it have warmed. Watch the per-slot "
                        "spread under load — identical silicon, unequal "
                        "physics."
                    )
                ),
            )
            for i in range(8)
        ],
        SystemRegion(
            id="idrac", kind="management", label="iDRAC",
            x=91, y=3, w=8, h=8,
            description=(
                "The BMC — the machine's always-on manager. The iDRAC "
                "tab renders this simulator's state as the Redfish "
                "thermal JSON a real iDRAC would serve: swap the sim for "
                "hardware and the same calls make this a twin."
            ),
        ),
        SystemRegion(
            id="psu", kind="power", label="PSU bank",
            x=91, y=29, w=8, h=20,
            description=(
                "Eight hot-swap 3200 W Titanium supplies (2900 W each on "
                "200–220 V input). The model budgets four of them, the "
                "half a 4+4 redundant bank can count on."
            ),
        ),
    ],
    sources=[
        {"label": "physics_specs/01-gpu-compute-and-management.md (this repo)",
         "url": "../physics_specs/01-gpu-compute-and-management.md"},
        {"label": "Dell PowerEdge XE7745 spec sheet (July 2025) — dual AMD EPYC 9005, 8× 600 W double-wide GPUs, 24 DIMMs, 3200 W Titanium PSUs, 12 front + 4 mid-tray fan modules",
         "url": "https://www.delltechnologies.com/asset/en-in/products/servers/technical-support/poweredge-xe7745-spec-sheet.pdf"},
    ],
)


XE9680 = SystemMap(
    id="xe9680",
    name="PowerEdge XE9680 · 8-way HGX trainer",
    vendor="Dell Technologies",
    form_factor="6U rack server — top-down thermal view",
    generation="HGX H100/H200/B200 platform",
    year=2023,
    width=100,
    height=52,
    overview=L(
        novice=(
            "Dell's flagship air-cooled AI trainer: eight of the biggest "
            "GPUs made, mounted together on one board with its own "
            "high-speed links between them. Because they share that "
            "board and its cooling, they behave like one organism — if "
            "heat forces a slowdown, all eight slow together. The "
            "machine swings from about one kilowatt at idle to more "
            "than ten flat out, which is why AI data centers are power "
            "projects before they are computer projects. The other "
            "lesson is hunger: a GPU waiting for data still burns most "
            "of its power while producing almost nothing — the "
            "data-feed slider makes that waste visible."
        ),
        standard=(
            "The XE9680 top-down: NVMe bay and fan wall at the front, "
            "host CPUs and DIMMs midboard, and the HGX baseboard — "
            "eight SXM GPUs (700 W H100-class or 1000 W B200-class) "
            "with their NVSwitch spine — dominating the rear, one NIC "
            "per GPU beside it. Two personalities drive the sim: shared "
            "thermal fate (the baseboard is modeled as one zone; all "
            "eight throttle together, a stated simplification), and "
            "the data-starvation slider — effective utilization is "
            "capped by what the storage pipeline delivers, so power "
            "stays high while tokens/s and the GPU-hours-wasted ledger "
            "tell the truth. The idle-to-full swing (~1 → 10+ kW) is "
            "the 'power-plant problem' scenario."
        ),
        expert=(
            "8× SXM on one thermal zone — collective throttle, stated "
            "simplification. data_feed caps eff-util: P ≈ high, tok/s ∝ "
            "feed; wasted-GPU-hours ledger. Idle ~1.5 kW → ~11 kW. "
            "Per-GPU 400G NICs ≈ 240 W of 'plumbing'."
        ),
    ),
    regions=[
        SystemRegion(
            id="nvme", kind="storage", label="NVMe bay",
            x=0.5, y=0.5, w=6, h=51,
            description=L(
                novice=(
                    "A row of fast solid-state drives at the front of "
                    "the machine. They hold working copies of whatever "
                    "the GPUs are chewing on right now; the training "
                    "data itself lives on storage elsewhere in the "
                    "building and arrives over the network."
                ),
                standard=(
                    "Front NVMe — local scratch for a machine fed over "
                    "the fabric."
                ),
            ),
        ),
        SystemRegion(
            id="fanwall", kind="cooling", label="Fan wall ×16",
            x=8, y=0.5, w=7, h=51,
            description=L(
                novice=(
                    "Sixteen fans, drawn here as one wall. They have to "
                    "push air through a machine six rack units tall and "
                    "packed solid, which takes far more force than "
                    "moving air across an open desk. Six of the fans sit "
                    "in the middle of the chassis for the processors and "
                    "ten sit at the back for the graphics chips. Air is "
                    "the only thing cooling this machine, so how much "
                    "air the fans can move is also the limit on how much "
                    "heat it may make."
                ),
                standard=(
                    "Six rack units of static pressure, drawn as one "
                    "wall: the real chassis splits its sixteen fans into "
                    "six on the mid tray for the host and ten at the "
                    "rear for the GPUs. Air is this machine's coolant, "
                    "and its ceiling."
                ),
            ),
        ),
        SystemRegion(
            id="cpu", kind="cpu", label="Host CPUs",
            x=18, y=3, w=12, h=30,
            description="Two Xeon Scalable processors that exist to feed eight GPUs — the host is staff, not talent.",
        ),
        SystemRegion(
            id="dimm", kind="memory", label="DIMMs",
            x=18, y=37, w=12, h=12,
            description="Up to 32 DIMMs of staging memory.",
        ),
        SystemRegion(
            id="hgx", kind="gpu", label="HGX baseboard ×8 SXM",
            x=34, y=3, w=42, h=46,
            description=L(
                novice=(
                    "The HGX board — NVIDIA's eight-GPU carrier board — "
                    "holding eight graphics chips in the bolted-down "
                    "socket style called SXM, which lets each chip draw "
                    "far more power than a plug-in card could. They are "
                    "drawn as one block because this model treats them "
                    "as one hot object: they share the board and they "
                    "share the cold air, so when the block gets too hot "
                    "all eight slow down together."
                ),
                standard=(
                    "The HGX board: eight SXM GPUs drawn as the single "
                    "thermal zone the model treats them as. NVLink makes "
                    "them one computer; the shared cold-air budget makes "
                    "them one thermal fate — when this zone crosses the "
                    "throttle line, all eight step down together."
                ),
            ),
        ),
        SystemRegion(
            id="nvswitch", kind="nvswitch", label="NVSwitch",
            x=78, y=3, w=6, h=46,
            description=L(
                novice=(
                    "The switch that lets the eight graphics chips read "
                    "each other's memory directly, inside the box. "
                    "Because this path exists, work passed between the "
                    "eight of them never goes out through the network "
                    "cards at the back — it stays on the board, which is "
                    "much faster."
                ),
                standard=(
                    "The NVSwitch spine at the board's edge — in-box "
                    "traffic never touches the NICs."
                ),
            ),
        ),
        SystemRegion(
            id="nic", kind="network", label="NICs ×8",
            x=86, y=3, w=6, h=46,
            description=L(
                novice=(
                    "Eight network cards, one for each graphics chip, "
                    "each carrying 400 gigabits per second. They draw "
                    "about 30 W apiece — the eight of them together use "
                    "more electricity than a desktop PC, and they do no "
                    "computing at all. Their job starts where the box "
                    "ends: talking to the other machines in the cluster."
                ),
                standard=(
                    "One 400G-class NIC per GPU (~30 W each — a NIC bank "
                    "that outdraws a desktop PC). Scale past the chassis "
                    "wall is their job, and the fabric app's story."
                ),
            ),
        ),
        SystemRegion(
            id="idrac", kind="management", label="iDRAC",
            x=94, y=3, w=5, h=12,
            description="The BMC. The iDRAC tab serves this state as Redfish JSON.",
        ),
        SystemRegion(
            id="psu", kind="power", label="PSUs ×6",
            x=94, y=19, w=5, h=30,
            description=L(
                novice=(
                    "Six power supplies, each rated 2800 W, sharing a "
                    "load that reaches about eleven kilowatts — roughly "
                    "what five electric kettles draw, in one server. "
                    "They convert the building's alternating-current "
                    "electricity into the direct current the parts run "
                    "on. 'Titanium' is not a material here: it is the "
                    "top efficiency grade, meaning very little of the "
                    "electricity is lost as heat in the conversion."
                ),
                standard=(
                    "Six 2800 W Titanium PSUs sharing an 11 kW-class "
                    "load."
                ),
            ),
        ),
    ],
    sources=[
        {"label": "physics_specs/01-gpu-compute-and-management.md (this repo)",
         "url": "../physics_specs/01-gpu-compute-and-management.md"},
        {"label": "Dell PowerEdge XE9680 Installation and Service Manual — two Xeon Scalable sockets, 32 DIMMs, six PSUs, six mid-tray + ten rear fans, HGX 8-GPU boards",
         "url": "https://www.dell.com/support/manuals/en-us/poweredge-xe9680/xe9680_ism_pub/dell-poweredge-xe9680-system-configurations-and-features?guid=guid-219a12b6-5232-49fe-9506-ac2aed25ac30&lang=en-us"},
        {"label": "DellPowerEdgeXE9680 twin — the same machine's power-on story",
         "url": "http://localhost:5201/"},
    ],
)


XE9712 = SystemMap(
    id="xe9712",
    name="PowerEdge XE9712 in IR7000 · liquid-cooled rack",
    vendor="Dell Technologies",
    form_factor="Rack-scale system — front elevation",
    generation="GB200 NVL72-class (GB300 from 2026), IR7000 rack",
    year=2024,
    width=100,
    height=88,
    overview=L(
        novice=(
            "Here the machine is the whole rack. Eighteen compute "
            "drawers — seventy-two GPUs — draw over a hundred kilowatts "
            "from shared power shelves, and almost all of that heat "
            "leaves in water: cold plates sit on the chips, a "
            "distribution unit at the bottom pumps coolant up one side "
            "and down the other, and the water leaves a few degrees "
            "warmer than it arrived. The arithmetic is honest — heat "
            "picked up equals flow times temperature rise — and the "
            "simulator enforces it exactly. About a tenth of the heat "
            "still escapes into the room as air, carried by a few "
            "small fans in each drawer. The map does not draw them, "
            "but their electricity is counted as an estimate. The "
            "big fan walls are gone; in their place are quieter "
            "questions about pumps, water temperature, and what "
            "happens when either falters."
        ),
        standard=(
            "The XE9712 drawn inside its IR7000 rack, front elevation: "
            "power shelves and rack management on top, four "
            "representative compute trays (of 18 — each 2 Grace-class "
            "CPUs + 4 Blackwell-class GPUs) around the mid-rack NVLink "
            "switch block, the CDU at the bottom, supply and return "
            "manifolds up the sides. The engine's core identity is the "
            "heat split — liquid + air = DC, exactly, with ~88% in the "
            "water — and the loop obeys ΔT = Q/(ṁ·cp) with water's cp. "
            "Trays nearer the return run warmer than supply-side trays; "
            "pump degradation, CDU supply excursions, and per-tray "
            "restrictions are the failure dials. The IR7000's own "
            "product — budget validation (tray power vs 33 kW-shelf capacity, "
            "coolant demand vs manifold, weight advisory) — gates the "
            "build panel."
        ),
        expert=(
            "Rack as unit: 18 trays, 72 GPUs, ~120 kW busbar. liquid + "
            "air = DC exact, ~12% residual air; ΔT = Q/(ṁ·cp_water); "
            "return-side trays hottest; coolant-return throttle at 65, "
            "trip at 75 °C. IR7000 rules: Στray ≤ shelf, Σcoolant ≤ "
            "manifold, weight advisory. Sled fans (8 dual-rotor each) "
            "handle the residual air: not drawn, charged at a flat "
            "~6 W per 100 W of air-side heat (estimate)."
        ),
    ),
    regions=[
        SystemRegion(
            id="shelf", kind="power", label="Power shelves → busbar",
            x=2, y=1, w=76, h=8,
            description=(
                "Rack-level power shelves rectifying onto a DC busbar — "
                "the IR7000's first budget: tray power must sum inside "
                "shelf capacity, and the validation panel enforces it "
                "before the trip does."
            ),
        ),
        SystemRegion(
            id="rmc", kind="management", label="Rack mgmt",
            x=80, y=1, w=18, h=8,
            description="Rack-scope management — the iDRAC idea, one level up.",
        ),
        SystemRegion(
            id="tray-0", kind="tray", label="Compute trays (supply side)",
            x=2, y=11, w=76, h=12,
            description=(
                "Compute trays nearest the coolant supply: 2 CPUs + 4 "
                "GPUs in each 1U sled, cold plates on everything hot. These run "
                "coolest — position matters in a liquid loop too, just "
                "milder than in air."
            ),
        ),
        SystemRegion(
            id="tray-1", kind="tray", label="Compute trays",
            x=2, y=25, w=76, h=12,
            description="Mid-loop trays. Four blocks stand for eighteen.",
        ),
        SystemRegion(
            id="nvsw", kind="nvswitch", label="NVLink switch trays ×9",
            x=2, y=39, w=76, h=10,
            description=(
                "The mid-rack NVLink switch block fusing 72 GPUs into "
                "one domain — physically central so every copper run "
                "stays short. ~4.5 kW of the rack's budget."
            ),
        ),
        SystemRegion(
            id="tray-2", kind="tray", label="Compute trays",
            x=2, y=51, w=76, h=12,
            description="Trays below the switch block.",
        ),
        SystemRegion(
            id="tray-3", kind="tray", label="Compute trays (return side)",
            x=2, y=65, w=76, h=12,
            description=(
                "Return-side trays — the hottest coolant reaches them "
                "last, so they throttle first when the loop is stressed. "
                "The 'restrict tray' event pinches one tray's flow and "
                "shows a single starved cold plate in an otherwise "
                "healthy rack."
            ),
        ),
        SystemRegion(
            id="manifold-supply", kind="manifold", label="Supply",
            x=80, y=11, w=8, h=76,
            description=(
                "The supply manifold — cool water up the rack. Its "
                "capacity is the IR7000's second budget: tray coolant "
                "demand must fit inside what the manifold can carry."
            ),
        ),
        SystemRegion(
            id="manifold-return", kind="manifold", label="Return",
            x=90, y=11, w=8, h=76,
            description=(
                "The return manifold — the rack's exhaust pipe. Its "
                "temperature is the loop's honest gauge: supply + "
                "Q/(ṁ·cp), enforced every tick."
            ),
        ),
        SystemRegion(
            id="cdu", kind="cdu", label="CDU — pumps + heat exchanger",
            x=2, y=79, w=76, h=8,
            description=(
                "The in-rack coolant distribution unit: pumps and the "
                "heat exchanger to facility water. Degrade its pumps and "
                "the same watts ride a smaller flow — ΔT rises until the "
                "loop protects itself. The IR7000 twin (:5182) walks "
                "this loop's commissioning."
            ),
        ),
    ],
    sources=[
        {"label": "physics_specs/01-gpu-compute-and-management.md (this repo)",
         "url": "../physics_specs/01-gpu-compute-and-management.md"},
        {"label": "Dell PowerEdge XE9712 spec sheet (April 2026) — 2 Grace + 4 GPUs per 1U sled, 33 kW power shelves on an ORv3 busbar, eight dual-rotor fans per sled, 30 kg sled, 1,590 kg cabinet wet weight",
         "url": "https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-xe9712-spec-sheet.pdf"},
        {"label": "NVIDIA technical blog — GB200 NVL72: 18 compute trays, nine NVLink switch trays",
         "url": "https://developer.nvidia.com/blog/nvidia-gb200-nvl72-delivers-trillion-parameter-llm-training-and-real-time-inference/"},
        {"label": "Dell press release, December 2024 — first XE9712 racks ship in IR7000 racks",
         "url": "https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2024~12~dell-cw-customer-announce.htm"},
        {"label": "DellPowerEdgeXE9712 twin — the same rack's power-on story",
         "url": "http://localhost:5181/"},
        {"label": "DellIR7000 twin — the cooling loop as its own subject",
         "url": "http://localhost:5182/"},
    ],
)


MAPS: dict[str, SystemMap] = {
    "xe7745": XE7745,
    "xe9680": XE9680,
    "xe9712": XE9712,
}


def map_for(product: str) -> SystemMap:
    return MAPS[product]
