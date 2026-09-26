"""Chassis map for the thermal simulator — geometry reused from the R760
power-on twin's floorplan (spec §1, adjusted): same 100×46 top-down view,
front at x=0, rear at x=100, so the two R760 twins draw the same machine.
Regions here are *thermal zones* keyed to the engine's ``region_temps``
dict; the frontend paints them on a fixed 20–110 °C scale instead of the
power-on twin's activity highlight. Stylized — a mental model, not a
service manual (project scope guardrail).
"""

from __future__ import annotations

from .leveling import L
from .models import ChassisMap, ThermalRegion


def _fan(i: int) -> ThermalRegion:
    return ThermalRegion(
        id=f"fan-{i}", kind="cooling", label=f"Fan {i + 1}",
        x=8.5, y=0.5 + i * 7.6, w=6, h=7.0,
        description=(
            "One of six hot-swap fan modules in the fan wall. Fan power "
            "rises with the cube of speed — doubling rpm costs eight times "
            "the watts — and that power feeds back into the total the PSUs "
            "must supply and the heat the airflow must remove. Click to "
            "kill this fan and watch the survivors ramp."
        ),
    )


ANATOMY = ChassisMap(
    id="r760-thermal",
    name="PowerEdge R760 · power & thermal model",
    vendor="Dell Technologies",
    form_factor="2U rack server — thermal-zone view",
    generation="16th-generation PowerEdge (4th/5th Gen Intel Xeon Scalable)",
    year=2023,
    width=100,
    height=46,
    overview=L(
        novice=(
            "This is the same server the R760 power-on twin shows, asked a "
            "different question: not what happens when it turns on, but "
            "what happens while it runs. Air enters at the front (left), "
            "is pushed by a wall of six fans across the memory, "
            "processors, and expansion cards, and leaves hot at the back. "
            "Every watt of electricity the parts consume becomes heat that "
            "the moving air has to carry away — and the fans that move the "
            "air consume watts themselves, which become more heat. The "
            "colors show temperature: cool blue at the front intake, hot "
            "red where the processors work. Build a configuration, give "
            "it work to do, and watch the chain: work makes power, power "
            "makes heat, heat makes the fans spin, and the fans add to "
            "the power."
        ),
        plain=(
            "The R760 chassis as thermal zones, front (x=0) to rear: drive "
            "backplane in the intake path, the six-fan wall, DIMM banks and "
            "CPUs in one airflow lane, the PCIe/GPU risers in the other, "
            "PSUs at the rear corner. The engine computes the causal chain "
            "configuration → load → power → heat → fan response → feedback "
            "each second; regions are painted on a fixed 20–110 °C scale. "
            "Two identities hold throughout: component powers sum exactly "
            "to DC (wall = DC ÷ PSU efficiency), and exhaust = inlet + "
            "Q/(ṁ·cp) — the IR7000 twin's heat balance, inside one box."
        ),
        standard=(
            "This is the R760 power-on twin's chassis, repainted as the "
            "thermal system it becomes once the OS is up. Air flows front "
            "(left) to rear: the drive backplane sits in the intake path "
            "and warms the air first, the fan wall drives everything, and "
            "the flow then splits into two lanes — DIMM banks and CPUs in "
            "one, the PCIe/GPU risers in the other — before leaving "
            "through the rear, where the PSUs draw their own cooling. "
            "Every electrical watt becomes heat the airflow must carry "
            "(exhaust = inlet + Q/(ṁ·cp), the same identity the IR7000 "
            "twin enforces for a whole rack), and the fans obey a cubic "
            "law — twice the rpm, eight times the watts — which feeds "
            "back into the very total they exist to cool. The model is "
            "deliberately simple: serial zones, first-order thermal "
            "masses, a proportional fan controller. Correct relationships "
            "and orders of magnitude, not CFD — every constant carries a "
            "source tag, and the estimated ones say so."
        ),
        technical=(
            "Zone model per spec §5.1: intake (drives) → fan wall → lane "
            "A (DIMM/CPU, 60% flow share) ∥ lane B (PCIe/GPU) → rear; "
            "PSUs vent separately. First-order component masses (τ = "
            "20 s silicon, 300 s drives); proportional fan control on "
            "max(CPU−85, GPU−80); cubic fan power. Asserted: per-tick "
            "power balance (Σ components = DC; AC = DC/η(load)), heat "
            "balance (exhaust = inlet_eff + DC/(ṁ·cp)), and the spec's "
            "acceptance envelope. Constants in constants.py, each with a "
            "source field; estimates flagged."
        ),
        expert=(
            "Serial zones + lane split, first-order masses, P-controller, "
            "cubic fans. Per-tick: ΣP = DC, AC = DC/η; exhaust = inlet + "
            "DC/(ṁ·cp). Constants sourced, estimates tagged. Not CFD, "
            "on purpose."
        ),
    ),
    regions=[
        ThermalRegion(
            id="backplane", kind="storage", label="Drive bay",
            x=0.5, y=0.5, w=7, h=45,
            description=(
                "The front drive bay — first thing the intake air meets, "
                "so every populated drive both adds heat ahead of "
                "everything downstream and slightly obstructs the airflow "
                "(about half a percent each). Drive temperature moves "
                "slowly (τ ≈ 300 s): watch it lag the CPUs by minutes "
                "after a load change."
            ),
        ),
        *[_fan(i) for i in range(6)],
        ThermalRegion(
            id="dimm-a", kind="memory", label="DIMM bank A",
            x=20, y=1, w=26, h=8,
            description=(
                "CPU 1's DDR5 DIMM banks. Each DIMM draws ~1.5 W idle to "
                "~4 W at full memory bandwidth; a fully populated board "
                "(32 DIMMs) also adds ~5% airflow resistance through the "
                "CPU lane — population is a thermal decision, not just a "
                "capacity one."
            ),
        ),
        ThermalRegion(
            id="cpu1", kind="cpu", label="CPU 1",
            x=24, y=11, w=18, h=11,
            description=(
                "The first Xeon socket. Power follows utilization "
                "nonlinearly (P = idle + (TDP−idle)·util^1.4), briefly "
                "boosts ~15% above TDP at full load, and the die "
                "approaches its steady temperature with a ~20 s time "
                "constant. Above 98 °C it throttles in 10% steps — "
                "protection you can watch, and provoke."
            ),
        ),
        ThermalRegion(
            id="cpu2", kind="cpu", label="CPU 2",
            x=24, y=24, w=18, h=11,
            description=(
                "The second socket, populated in 2-CPU builds. Note the "
                "airflow reality the zone model encodes: this CPU inhales "
                "air the drive bay and DIMM bank have already warmed — "
                "the front-to-back path means downstream parts always run "
                "against a warmer inlet than the badge on the front of "
                "the rack suggests."
            ),
        ),
        ThermalRegion(
            id="dimm-b", kind="memory", label="DIMM bank B",
            x=20, y=37, w=26, h=8,
            description=(
                "CPU 2's DIMM banks — same power model as bank A. Memory "
                "bandwidth utilization, not capacity, is what moves the "
                "watts: an idle terabyte draws little more than an idle "
                "128 GB."
            ),
        ),
        ThermalRegion(
            id="gpu-riser", kind="gpu", label="PCIe / GPU risers",
            x=52, y=1, w=20, h=33,
            description=(
                "The PCIe riser zone — lane B of the airflow split. Up to "
                "two double-wide GPUs (Dell's ceiling is 350 W each; this "
                "model uses a 300 W-class card) or six single-wide 75 W "
                "accelerators live here. Dell's thermal restriction "
                "matrix allows GPU builds only with the Gold fan kit; "
                "the 30% fan floor is this model's estimate, because "
                "this lane gets less airflow than the CPU lane and a "
                "300 W part in it has no margin for quiet fans."
            ),
        ),
        ThermalRegion(
            id="ocp", kind="io", label="OCP NIC",
            x=52, y=40, w=20, h=5,
            description=(
                "The OCP 3.0 network mezzanine and other I/O cards — "
                "modeled as a flat aggregate (0–100 W). Small next to the "
                "CPUs, but it sits in lane B's airflow and every watt "
                "still exits through the exhaust."
            ),
        ),
        ThermalRegion(
            id="idrac", kind="management", label="iDRAC",
            x=76, y=40, w=10, h=5,
            description=(
                "The BMC — this repo's DellIDRAC twin. In this simulator "
                "it is the implied narrator: the fan controller, the "
                "throttle decisions, and the emergency power-off are all "
                "policies a real iDRAC enforces from exactly this corner "
                "of the board."
            ),
        ),
        ThermalRegion(
            id="psu-a", kind="power", label="PSU 1",
            x=88, y=1, w=11, h=14,
            description=(
                "The first hot-swap PSU. Efficiency depends on load point "
                "(~90% at 10% load, ~96% at 50%, ~91% flat out — the 80 PLUS "
                "Titanium minimums; Dell's 800, 1400 and 2400 W supplies "
                "are Platinum and run slightly lower), so wall watts "
                "exceed DC watts by a "
                "margin that changes with configuration. In 1+1 the pair "
                "shares load at a lower, often more efficient point each; "
                "kill one and watch the survivor's efficiency shift."
            ),
        ),
        ThermalRegion(
            id="psu-b", kind="power", label="PSU 2",
            x=88, y=17, w=11, h=14,
            description=(
                "The second PSU, present in 1+1 and 2+0 builds. PSU "
                "conversion loss (AC − DC) becomes heat vented by the "
                "PSUs' own rear airflow — deliberately outside the "
                "front-to-back zone model, and honestly footnoted as "
                "such."
            ),
        ),
    ],
    limitations=L(
        novice=(
            "What this model leaves out, in plain words. It does not work "
            "out how the air actually swirls and eddies inside the box — "
            "it treats the air as moving straight from front to back. It "
            "does not model the fine-grained tricks a processor uses to "
            "shave its own power core by core. It ignores the small "
            "losses in the circuitry that feeds the processors, and it "
            "ignores humidity, which barely affects cooling at these "
            "temperatures. It has no noise figure: fan speed is used as a "
            "stand-in for how loud the server is. Two fan simplifications "
            "matter if you are planning for real spare-fan cover: airflow "
            "here is simply added up across the running fans, so five "
            "fans spinning a fifth faster restore exactly the airflow six "
            "were moving, and a stopped fan is treated as a sealed hole "
            "rather than a gap air can leak back through. A real machine "
            "recovers less than this, so treat the cost of losing a fan "
            "as the optimistic case. The processors' power here depends "
            "only on how busy they are, never on how hot they are, "
            "although hot silicon really does leak a little more power — "
            "that is a deliberate choice so the fan story can be read on "
            "its own. Heat lost inside the power supplies leaves through "
            "their own rear vents, outside the front-to-back path drawn "
            "here. Most numbers are estimates waiting to be checked "
            "against Dell's published documents; every one carries a "
            "source tag in the backend's constants table."
        ),
        plain=(
            "What we do not model: airflow detail inside the chassis (no "
            "CFD — air goes front to back), per-core power management, "
            "losses in the voltage regulators, humidity (not a factor at "
            "these temperatures), and noise, for which fan speed is the "
            "stand-in. Two fan simplifications matter for redundancy "
            "planning: airflow adds linearly across the running fans, "
            "with no fan curve against the chassis's own resistance, and "
            "a dead fan is sealed rather than a backflow path — so "
            "survivors recover more airflow here than on real hardware. "
            "CPU power depends on utilization only, never on die "
            "temperature, so temperature-driven leakage is absent; that "
            "keeps the fan-overhead lesson clean but understates the wall "
            "power of a hot-aisle excursion. PSU conversion loss vents "
            "rearward, outside the front-to-back path. Most constants are "
            "estimates pending calibration against Dell's published "
            "documentation — every one carries a source tag in the "
            "backend's constants table."
        ),
        standard=(
            "What we don't model: CFD, per-core DVFS, VR losses, humidity "
            "(listed non-factor), acoustics beyond rpm as proxy. Airflow "
            "superposes linearly across live fans — no fan curve against a "
            "system impedance, and a dead rotor is sealed rather than a "
            "bypass path — so survivors recover more flow here than on "
            "real hardware, and the cost of an N+1 fan loss reads "
            "optimistic. CPU power is a function of utilization and TDP "
            "only: there is no temperature-dependent leakage term, which "
            "keeps the fan-overhead reading clean and understates wall "
            "power in a hot-aisle excursion. PSU conversion loss is vented "
            "by the PSUs' own airflow, outside the front-to-back path. "
            "Most constants are estimates pending calibration against "
            "Dell's published documentation — every one carries a source "
            "tag in the backend's constants table."
        ),
        expert=(
            "Not modelled: CFD, per-core DVFS, VR loss, humidity, "
            "acoustics (rpm proxy). Linear airflow superposition — no "
            "fan/system curve, no dead-rotor bypass: N+1 loss reads "
            "optimistic. P_cpu(util, TDP) only — no T-dependent leakage. "
            "PSU loss vented rear, outside the zone chain. Most constants "
            "estimated; sources in the constants table."
        ),
    ),
    sources=[
        {"label": "Dell PowerEdge R760 Technical Guide",
         "url": "https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-r760-technical-guide.pdf"},
        {"label": "Dell PowerEdge R760 spec sheet (PSUs, fans, GPU and drive options)",
         "url": "https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-r760-spec-sheet.pdf"},
        {"label": "Dell R760 Installation and Service Manual — environmental specifications (ASHRAE classes, altitude de-rating)",
         "url": "https://www.dell.com/support/manuals/en-us/poweredge-r760/per760_ism_pub/environmental-specifications?guid=guid-11193b30-1caa-4e7b-900f-bc79a66398ad&lang=en-us"},
        {"label": "Dell R760 Installation and Service Manual — thermal restriction matrix (heatsinks, fan kits, GPU rules)",
         "url": "https://www.dell.com/support/manuals/en-us/poweredge-r760/per760_ism_pub/thermal-restriction-matrix?guid=guid-3fe6e7bc-1d2c-4b91-a8ec-dff2e88e1168&lang=en-us"},
        {"label": "80 PLUS program details (Titanium and Platinum efficiency thresholds)",
         "url": "https://www.clearesult.com/80plus/program-details"},
        {"label": "Simulator spec (this repo)",
         "url": "../DellPowerEdgeR760/r760-interactive-simulator-spec.md"},
        {"label": "ASHRAE thermal guidelines (A2 envelope)",
         "url": "https://www.ashrae.org/technical-resources/bookstore/datacom-series"},
    ],
)
