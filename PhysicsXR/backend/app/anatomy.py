"""Chassis map for the XR rugged-edge simulator: a stylized 100×46
top-down view of a short-depth XR8000-class sled, front at x=0, rear at
x=100. Same idiom as the R760Thermal twin's map — regions are *thermal
zones* keyed to the engine's ``region_temps`` dict, painted on a fixed
20–110 °C scale — with one addition that carries this twin's personality:
the **dust filter** is drawn as a first-class region at the very front,
because out here it is a first-class thermal component. Stylized — a
mental model, not a service manual.
"""

from __future__ import annotations

from .leveling import L
from .models import ChassisMap, ThermalRegion


def _fan(i: int) -> ThermalRegion:
    return ThermalRegion(
        id=f"fan-{i}", kind="cooling", label=f"Fan {i + 1}",
        x=13, y=0.5 + i * 11.5, w=6, h=11.0,
        description=(
            "One of four fan modules in the sled's fan wall. Fan power "
            "rises with the cube of speed — and everything upstream of "
            "this wall (the filter, the dust on it) decides how much "
            "speed a given airflow costs. Click to kill this fan and "
            "watch the survivors ramp."
        ),
    )


ANATOMY = ChassisMap(
    id="xr-sled-thermal",
    name="PowerEdge XR-series · rugged-edge physics model",
    vendor="Dell Technologies",
    form_factor="short-depth edge sled — thermal-zone view",
    generation="XR8000 sled-based / XR4000 stackable class",
    year=2023,
    width=100,
    height=46,
    overview=L(
        novice=(
            "This is a small, short server built to live outside the data "
            "center — bolted to a cell tower cabinet, a factory wall, or a "
            "vehicle rack. Air comes in through a dust filter at the front "
            "(left), is pushed by four fans across the memory and the "
            "processor, and leaves hot at the back. The same rules apply "
            "as in any server: every watt of electricity becomes heat the "
            "air must carry away. What is different is the world outside. "
            "The room can be minus twenty or plus fifty-five degrees. The "
            "air carries dust that slowly clogs the filter, so month by "
            "month the fans must work harder to move the same air. The "
            "site vibrates, which spinning hard drives hate. And the "
            "power feed is a single line that sometimes sags. The colors "
            "show temperature: blue is cool, red is hot. Try the sliders "
            "a data-center server never gets."
        ),
        plain=(
            "A short-depth XR-class sled as thermal zones, front (x=0) to "
            "rear: dust filter, drive bay, the four-fan wall, DIMM banks "
            "and the single CPU socket in one airflow lane, the "
            "accelerator riser in the other, PSUs at the rear. Same "
            "engine as the R760 thermal twin — power balance every tick, "
            "exhaust = inlet + Q/(ṁ·cp) — with the environment unlocked: "
            "−25…65 °C ambient, filter fouling in sim-months, vibration "
            "classes, and a feed that browns out."
        ),
        standard=(
            "This is the R760Thermal engine moved to hostile ground — an "
            "XR8000-class short-depth sled whose spec sheet fences a "
            "world the R760 never sees: −5…55 °C rated ambient (−20…65 °C "
            "on select extended configs, versus a data hall's 35 °C "
            "ceiling), NEBS-class dust and vibration, a single-phase "
            "site feed with nothing between it and the weather. Air "
            "flows front (left) to rear through the one region a "
            "data-hall map never draws: the dust filter, whose fouling "
            "accumulates over sim-months and raises the resistance the "
            "fan wall must overcome — the same CFM costs more rpm, and "
            "rpm costs its cube in watts. Downstream the story is "
            "familiar on purpose: DIMMs and the single socket in lane A, "
            "the inference accelerators in lane B, PSUs at the rear, "
            "every electrical watt becoming heat the airflow must carry "
            "(exhaust = inlet + Q/(ṁ·cp)). Every constant carries a "
            "source tag; the envelope bounds are Dell's documented "
            "numbers, the fouling and vibration rates are labeled "
            "estimates."
        ),
        technical=(
            "Zone model: filter → drives → fan wall → lane A (DIMM/CPU, "
            "65% share) ∥ lane B (accel/I-O) → rear. Fouling folds into "
            "the resistance penalty ahead of the CFM term; controller "
            "buys the deficit back at rpm³. First-order masses (τ 20 s "
            "silicon / 300 s drives); P-control on max(CPU−85, "
            "accel−80). Feed model: V sags per event; I = AC/V against "
            "a per-PSU input limit; deep sag < 60% drops out. Asserted: "
            "per-tick power balance, heat balance, envelope acceptance "
            "tests. Envelope bounds documented (−5…55 / −20…65 select); "
            "rates estimated."
        ),
        expert=(
            "R760Thermal engine, hostile inputs. Fouling ↑ resistance → "
            "rpm³ tax; I = P/V brownout trip; HDD vibe derate. ΣP = DC; "
            "exhaust = inlet + DC/(ṁcp). −5…55 documented, −20…65 "
            "select; rates estimated. Not CFD."
        ),
    ),
    regions=[
        ThermalRegion(
            id="filter", kind="filter", label="Filter",
            x=0.5, y=0.5, w=4, h=45,
            description=(
                "The dust filter — the region a data-center chassis map "
                "never draws, and the star of this one. Every month of "
                "site dust raises the airflow resistance behind it, so "
                "the same fan speed moves less air and the controller "
                "answers with more speed, at the cubic power price. "
                "Click it to change the filter mid-run and watch the "
                "fans relax."
            ),
        ),
        ThermalRegion(
            id="backplane", kind="storage", label="Drives",
            x=5.5, y=0.5, w=6.5, h=45,
            description=(
                "The short front bay — a handful of drives, not the "
                "R760's wall of 24. The configuration choice that "
                "matters out here is spinning versus solid-state: a "
                "vibrating site taxes an HDD's throughput (watch the "
                "storage-performance instrument) and leaves an SSD "
                "untouched. Drive temperature moves slowly (τ ≈ 300 s)."
            ),
        ),
        *[_fan(i) for i in range(4)],
        ThermalRegion(
            id="dimm-a", kind="memory", label="DIMM bank A",
            x=21, y=1, w=26, h=8,
            description=(
                "Half of the socket's DDR5 DIMMs. Each draws ~1.5 W idle "
                "to ~4 W at full memory bandwidth. A short-depth sled "
                "offers fewer slots than a rack server — capacity is one "
                "of the prices of the form factor."
            ),
        ),
        ThermalRegion(
            id="cpu1", kind="cpu", label="CPU",
            x=25, y=11, w=18, h=14,
            description=(
                "The single socket — Xeon Scalable in an XR8000 sled, "
                "Xeon D in an XR4000 node. Power follows utilization "
                "nonlinearly (P = idle + (TDP−idle)·util^1.4), boosts "
                "briefly at full load, and throttles in 10% steps above "
                "98 °C. The same die that idles happily at −15 °C in "
                "Fargo is the one that throttles on a Phoenix rooftop — "
                "silicon does not care where it is, only how hot its "
                "intake air arrives."
            ),
        ),
        ThermalRegion(
            id="dimm-b", kind="memory", label="DIMM bank B",
            x=21, y=27, w=26, h=8,
            description=(
                "The other half of the DIMMs. Memory bandwidth "
                "utilization, not capacity, is what moves the watts."
            ),
        ),
        ThermalRegion(
            id="accel-riser", kind="accel", label="Accelerators",
            x=51, y=1, w=20, h=26,
            description=(
                "Up to two single-wide 75 W inference accelerators — the "
                "reason many of these sleds exist (video analytics at "
                "the site, RAN acceleration at the cell). Lane B of the "
                "airflow split; their presence raises the idle fan floor."
            ),
        ),
        ThermalRegion(
            id="ocp", kind="io", label="I/O",
            x=51, y=31, w=20, h=6,
            description=(
                "Network mezzanine and I/O cards, modeled as a flat "
                "aggregate (0–100 W). At a cell site this is the "
                "fronthaul/backhaul plumbing — small watts, but they "
                "ride lane B's airflow like everything else."
            ),
        ),
        ThermalRegion(
            id="bmc", kind="management", label="BMC",
            x=51, y=39, w=20, h=6,
            description=(
                "The iDRAC-class management controller — at a staffed "
                "data hall it is a convenience; at a site four hours up "
                "a fire road it is the only pair of eyes. The fan "
                "policies, throttle steps, and emergency power-off this "
                "engine models are decisions it enforces."
            ),
        ),
        ThermalRegion(
            id="psu-a", kind="power", label="PSU 1",
            x=88, y=1, w=11, h=14,
            description=(
                "The first PSU. Out here the interesting terminal is the "
                "input: a single-phase site feed with no UPS ahead of "
                "it. When the feed sags, constant power means rising "
                "current (I = P/V) — a brownout the sled idles through "
                "can trip it at full load. Efficiency follows the "
                "Titanium-class curve."
            ),
        ),
        ThermalRegion(
            id="psu-b", kind="power", label="PSU 2",
            x=88, y=17, w=11, h=14,
            description=(
                "The second PSU, when the site affords one. Many edge "
                "deployments run a single feed and a single supply — "
                "which is why the brownout scenarios here default to a "
                "1+0 build. Conversion loss vents through the PSUs' own "
                "rear airflow, outside the front-to-back path."
            ),
        ),
    ],
    sources=[
        {"label": "Dell PowerEdge XR series spec sheet (rugged ratings)",
         "url": "https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-xr-rugged-spec-sheet.pdf"},
        {"label": "Dell PowerEdge XR8000 Technical Guide",
         "url": "https://www.delltechnologies.com/asset/nl-nl/products/servers/technical-support/poweredge-xr8000-technical-guide.pdf"},
        {"label": "Dell Info Hub — XR8000 thermal design",
         "url": "https://infohub.delltechnologies.com/en-us/p/understanding-thermal-design-and-capabilities-for-the-poweredge-xr8000-server/"},
        {"label": "Physics spec (this repo)",
         "url": "../physics_specs/10-additional-products.md"},
    ],
)
