"""Rack map for the PDU & UPS simulator — a stylized front elevation:
eight load slots on the left, the three phase feeds drawn as vertical
PDU strips beside them, the UPS and its battery across the bottom.
Regions are keyed to the engine's ``region_watts`` dict; the frontend
paints loads by phase assignment and everything else by live watts.
Stylized — a mental model, not an electrical drawing (project scope
guardrail).
"""

from __future__ import annotations

from .leveling import L
from .models import RackMap, RackRegion


def _load(i: int) -> RackRegion:
    return RackRegion(
        id=f"load-{i + 1}", kind="load", label=f"Slot {i + 1}",
        x=2, y=2 + i * 6.1, w=54, h=5.4,
        description=(
            "One rack load — a server drawing its configured watts from "
            "whichever phase feed it is plugged into. Click to move it to "
            "the next phase and watch the balance meters shift. A load on "
            "a tripped phase reads zero: the breaker protects the wiring, "
            "not the workload."
        ),
    )


ANATOMY = RackMap(
    id="rack-power",
    name="Rack PDU & UPS · power-layer model",
    vendor="Dell Technologies (PDUs resold from APC NetShelter)",
    form_factor="42U rack, front elevation — power-layer view",
    generation="three-phase metered/switched rack PDU + rack UPS",
    year=2026,
    width=100,
    height=64,
    overview=L(
        novice=(
            "This is the power layer of one equipment rack — the part "
            "everyone forgets until the day it matters. On the left are "
            "eight slots holding servers. Each server plugs into one of "
            "three separate electrical feeds, called phases A, B, and C — "
            "think of them as three parallel pipes carrying electricity "
            "into the rack. Each pipe has a circuit breaker that shuts it "
            "off if too much current flows, and the rule of thumb is to "
            "never fill a pipe past 80% for long. At the bottom sits the "
            "UPS — the battery box that keeps everything alive when the "
            "building power fails. Its display predicts how many minutes "
            "of battery you have, but that prediction is based on the "
            "battery as it was when new. Batteries fade with age and "
            "heat, and unless a self-test has measured the fade, the "
            "display is quietly wrong. Click a server to move it between "
            "phases; fail the utility and see whether the prediction "
            "survives contact with the battery."
        ),
        standard=(
            "The power layer under every rack, drawn as one elevation: "
            "eight load slots, each assigned to one of three phase feeds "
            "(A/B/C) behind per-phase breakers, all fed by a rack UPS. "
            "Three lessons live here. Phase balance: three feeds share "
            "the load only if you assign it evenly, and the imbalance "
            "meter shows what lopsided assignment wastes. Breaker math: "
            "the NEC's 80% continuous-load rule is drawn on every meter, "
            "and the simplified I²t curve trips the breaker if you "
            "ignore it — taking the whole phase down. Battery truth: "
            "runtime = usable Wh × inverter efficiency ÷ load W, but the "
            "front panel computes it from nameplate Wh until a self-test "
            "measures the fade that age and room temperature actually "
            "inflicted. The gap between predicted and actual runtime is "
            "the hero instrument, and it is pure arithmetic."
        ),
        expert=(
            "Rack power layer: 8 loads → A/B/C feeds → per-phase breakers "
            "(80% continuous rule, I²t trip) → UPS. Fade = f(age, "
            "chemistry, temp); panel predicts from nameplate Wh until "
            "self-test. Predicted/actual runtime ratio = 1/capacity "
            "fraction. Conservation: Σoutlets = Σphases = PDU input; on "
            "battery, batt W × η_inv = load."
        ),
    ),
    regions=[
        *[_load(i) for i in range(8)],
        RackRegion(
            id="pdu-a", kind="pdu", label="Phase A",
            x=60, y=2, w=10, h=48,
            description=(
                "Phase A feed — one of the three 230 V branches of the "
                "rack's three-phase supply, metered per outlet and "
                "protected by its own breaker. The bar meter shows load "
                "against the breaker rating with the 80% continuous-load "
                "line drawn."
            ),
        ),
        RackRegion(
            id="pdu-b", kind="pdu", label="Phase B",
            x=73, y=2, w=10, h=48,
            description=(
                "Phase B feed. Three-phase power only helps if the load "
                "is spread across all three branches — a rack drawing "
                "everything from one phase hits that breaker's limit "
                "while the other two idle."
            ),
        ),
        RackRegion(
            id="pdu-c", kind="pdu", label="Phase C",
            x=86, y=2, w=10, h=48,
            description=(
                "Phase C feed. The imbalance readout is the max deviation "
                "of any phase from the three-phase average — the number "
                "an electrician checks before adding one more server to "
                "the convenient outlet."
            ),
        ),
        RackRegion(
            id="ups", kind="ups", label="Rack UPS",
            x=2, y=53, w=54, h=9,
            description=(
                "The rack UPS: passes utility power through (~98% "
                "efficient) in normal operation, carries the whole rack "
                "from its battery through a ~93%-efficient inverter when "
                "the utility fails. Its runtime prediction believes the "
                "battery's nameplate watt-hours until a self-test "
                "measures the truth."
            ),
        ),
        RackRegion(
            id="battery", kind="battery", label="Battery module",
            x=60, y=53, w=36, h=9,
            description=(
                "The battery — VRLA (lead-acid) or lithium. VRLA fades "
                "several percent per year and ages roughly twice as fast "
                "per +10 °C of room temperature; lithium fades slower and "
                "cares less about heat. The fade is invisible from the "
                "front panel until a self-test discharges against it."
            ),
        ),
    ],
    sources=[
        {
            "label": "Dell rack power lineup — APC NetShelter Rack PDU "
                     "Advanced (switched, metered-by-outlet; 1- and "
                     "3-phase), sold on dell.com",
            "url": "https://www.dell.com/en-us/shop/power-cooling-data-center-infrastructure",
        },
        {
            "label": "NEC 80% continuous-load rule (210.19/210.20) — the "
                     "breaker headroom rule the meters draw",
            "url": "https://www.nfpa.org/codes-and-standards/nfpa-70-standard-development/70",
        },
        {
            "label": "IEEE 1188 / IEEE 535 — VRLA maintenance and "
                     "qualification practice behind the aging rule of thumb",
            "url": "https://standards.ieee.org/ieee/1188/3841/",
        },
    ],
)
