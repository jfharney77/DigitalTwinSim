"""Presets and the teaching layer (spec §4, §7, §8) — backend data.

Config presets, workload presets, guided scenarios (scripted walkthroughs
that set the scenario and narrate what to watch), and Explain-mode entries
(the equation behind each key readout, with placeholders the frontend
substitutes with live values). Explain and scenario prose carries reading
levels — the natural authoring surface in a twin whose trace states are
numbers rather than sentences.
"""

from __future__ import annotations

from .leveling import L
from .models import (
    ConfigPreset,
    Environment,
    Explain,
    GuidedScenario,
    Scenario,
    ServerConfig,
    SimEvent,
    Workload,
    WorkloadPreset,
)

# --- Config presets (spec §7 build panel) ---------------------------------

ENTRY = ServerConfig(
    sockets=1, cpu_tdp_w=150, heatsink="standard", fan_kit="standard",
    dimms=8, chassis="24x2.5", drives=2, gpus_double_wide=0,
    accels_single_wide=0, io_card_w=20, psu_count=2, psu_capacity_w=800,
    redundancy="1+1",
)

BALANCED = ServerConfig(
    sockets=2, cpu_tdp_w=250, heatsink="high-performance", fan_kit="standard",
    dimms=16, chassis="24x2.5", drives=8, io_card_w=25,
    psu_count=2, psu_capacity_w=1400, redundancy="1+1",
)

MAX_CPU = ServerConfig(
    sockets=2, cpu_tdp_w=350, heatsink="high-performance", fan_kit="gold",
    dimms=32, chassis="16xE3.S", drives=16, gpus_double_wide=0,
    accels_single_wide=0, io_card_w=100, psu_count=2, psu_capacity_w=2400,
    redundancy="1+1",
)

GPU_NODE = ServerConfig(
    sockets=2, cpu_tdp_w=300, heatsink="high-performance", fan_kit="gold",
    dimms=32, chassis="16xE3.S", drives=8, gpus_double_wide=2,
    accels_single_wide=0, io_card_w=100, psu_count=2, psu_capacity_w=2400,
    redundancy="1+1",
)

CONFIG_PRESETS = [
    ConfigPreset(id="entry", name="Entry", config=ENTRY,
                 blurb="1× 150 W CPU, 8 DIMMs, 2 SSDs — the modest baseline."),
    ConfigPreset(id="balanced", name="Balanced", config=BALANCED,
                 blurb="2× 250 W CPUs, 16 DIMMs — the mainstream build."),
    ConfigPreset(id="max-cpu", name="Max CPU", config=MAX_CPU,
                 blurb="2× 350 W CPUs, 32 DIMMs, Gold fans — the 350 W problem."),
    ConfigPreset(id="gpu-node", name="GPU node", config=GPU_NODE,
                 blurb="2× double-wide 300 W GPUs — lane B earns its fan floor."),
]

# --- Workload presets (spec §4) -------------------------------------------

IDLE = Workload()
WEB = Workload(cpu_pct=35, mem_pct=30, storage_pct=20, gpu_pct=0)
DATABASE = Workload(cpu_pct=60, mem_pct=75, storage_pct=70, gpu_pct=0)
HPC = Workload(cpu_pct=100, mem_pct=80, storage_pct=10, gpu_pct=0)
AI_TRAINING = Workload(cpu_pct=50, mem_pct=70, storage_pct=40, gpu_pct=100)

WORKLOAD_PRESETS = [
    WorkloadPreset(id="idle", name="Idle", workload=IDLE),
    WorkloadPreset(id="web", name="Web serving", workload=WEB),
    WorkloadPreset(id="database", name="Database", workload=DATABASE),
    WorkloadPreset(id="hpc", name="HPC", workload=HPC),
    WorkloadPreset(id="ai", name="AI training", workload=AI_TRAINING),
]

# --- Guided scenarios (spec §8 — the differentiator) ----------------------

GUIDED_SCENARIOS = [
    GuidedScenario(
        id="idle-to-full",
        title="Idle to full load",
        narration=[
            L(
                novice=(
                    "The server starts idle and, two minutes in, is given "
                    "everything at once: full processor load. Watch the "
                    "order things happen in. Power jumps immediately — "
                    "electricity has no inertia. Temperature climbs over "
                    "tens of seconds, because metal takes time to heat. "
                    "And the fans respond after the temperature, because "
                    "they react to what the sensors read. Nothing here is "
                    "instant except the watts."
                ),
                standard=(
                    "From idle, the HPC workload lands at t=120 s. Watch "
                    "the strip charts' order of events: power steps up "
                    "instantly, CPU temperature follows with its ~20 s "
                    "time constant, and fan rpm trails the temperature — "
                    "the controller reacts to what the thermal mass has "
                    "only begun to show. The lag between cause and effect "
                    "is the whole lesson of §5.2."
                ),
                expert=(
                    "HPC at t=120. Order: P step, T first-order (τ≈20 s), "
                    "rpm trails via P-control. Lag is the lesson."
                ),
            ),
        ],
        question="How many seconds pass between the power step and the fans reaching their new steady speed?",
        scenario=Scenario(
            config=BALANCED, workload=IDLE, environment=Environment(),
            duration_s=600,
            events=[SimEvent(at_s=120, action="set-workload", workload=HPC)],
        ),
    ),
    GuidedScenario(
        id="fan-feedback",
        title="The fan-power feedback loop",
        narration=[
            L(
                novice=(
                    "The workload never changes in this run — only the "
                    "room gets hotter, from 22 to 40 degrees. Yet the "
                    "server's electricity bill rises. Why? The fans. "
                    "Hotter intake air means the fans must spin faster to "
                    "hold the processors at temperature, fan power rises "
                    "with the cube of speed, and those extra watts come "
                    "through the same power supplies as everything else. "
                    "Cooling is not free, and this run makes you watch "
                    "yourself pay for it."
                ),
                standard=(
                    "Constant database workload; at t=180 s the inlet "
                    "rises from 22 to 40 °C. Compute work is unchanged, "
                    "but wall power climbs anyway: the fans ramp to hold "
                    "target temperature against hotter air, fan power "
                    "goes with rpm³, and that overhead routes through the "
                    "PSUs like any other load. The highlighted fan-power "
                    "readout is the feedback loop the spec calls a core "
                    "teaching point."
                ),
                expert=(
                    "Fixed load, inlet 22→40 at t=180. Wall rises on fan "
                    "rpm³ overhead alone. The loop, priced."
                ),
            ),
        ],
        question="How many watts of wall power did 18 °C of room temperature cost, at constant work?",
        scenario=Scenario(
            config=BALANCED, workload=DATABASE, environment=Environment(),
            duration_s=720,
            events=[SimEvent(at_s=180, action="set-inlet", value=40)],
        ),
    ),
    GuidedScenario(
        id="kill-a-fan",
        title="Kill a fan",
        narration=[
            L(
                novice=(
                    "Six fans share the work of moving air; at three "
                    "minutes, one of them dies. The machine does not "
                    "overheat — the surviving five simply spin faster to "
                    "move the same air. But look at the cost: five fans "
                    "at higher speed use more electricity than six at "
                    "lower speed, because fan power grows so steeply with "
                    "speed. Redundancy works, and it is never free."
                ),
                standard=(
                    "Under HPC load, fan 3 fails at t=180 s. The "
                    "survivors ramp to restore airflow and the CPUs "
                    "barely notice — that is the redundancy working. The "
                    "bill shows up in fan power: five fans running "
                    "faster draw more than six running slower (rpm³ "
                    "again), so total power rises even as cooling "
                    "capacity merely recovers."
                ),
                expert=(
                    "Fan 3 dies at t=180 under HPC. Survivors ramp; "
                    "ΔT holds; fan watts rise (rpm³ across 5 > 6)."
                ),
            ),
        ],
        question="Is total fan power higher before or after the failure, once temperatures re-settle?",
        scenario=Scenario(
            config=BALANCED, workload=HPC, environment=Environment(),
            duration_s=600,
            events=[SimEvent(at_s=180, action="kill-fan", index=2)],
        ),
    ),
    GuidedScenario(
        id="350w-problem",
        title="The 350 W problem",
        narration=[
            L(
                novice=(
                    "The biggest processors this server takes run hot "
                    "enough that the room itself becomes part of the "
                    "specification. This run puts the maximum "
                    "configuration in a warm room — 35 degrees, still "
                    "within what data-center standards allow — and full "
                    "load. Watch the throttle margin shrink: the fans max "
                    "out, and the processors end up slowing themselves "
                    "down to survive. The same machine in a 22-degree "
                    "room never breaks a sweat. That is why the spec "
                    "sheets restrict ambient ranges for top-TDP builds."
                ),
                standard=(
                    "The Max CPU preset (2× 350 W, Gold fans) at 100% "
                    "load in a 35 °C room — inside ASHRAE A2's allowable "
                    "band, and yet: fans saturate at 100%, CPU temperature "
                    "walks up to the throttle line, and performance is "
                    "clipped to hold 98 °C. At 22 °C the identical build "
                    "holds full speed with margin. Maximum-TDP "
                    "configurations constrain the supported ambient "
                    "range — the validation panel's warning, demonstrated."
                ),
                expert=(
                    "2×350 W @ 100%, 35 °C inlet: fans pin, T→98, clamp "
                    "engages. Same build at 22 °C: margin. QED ambient "
                    "restriction."
                ),
            ),
        ],
        question="At what inlet temperature does this build first start throttling under full load?",
        scenario=Scenario(
            config=MAX_CPU, workload=HPC,
            environment=Environment(inlet_c=35),
            duration_s=900,
        ),
    ),
    GuidedScenario(
        id="recirculation",
        title="Recirculation death spiral",
        narration=[
            L(
                novice=(
                    "A badly arranged server room can feed a machine its "
                    "own hot exhaust. This run raises that recirculation "
                    "step by step: warmer intake means hotter exhaust, "
                    "which means an even warmer intake. Past a point the "
                    "loop feeds itself and temperature runs away until "
                    "the server shuts itself off to survive. This is why "
                    "data centers obsess over hot-aisle containment."
                ),
                standard=(
                    "Recirculation mixes a fraction of the server's own "
                    "exhaust back into its inlet, and it ratchets up "
                    "mid-run: 30% at t=120, 60% at t=300, 85% at t=420. "
                    "Each step raises the effective inlet, which raises "
                    "the exhaust, which raises the inlet — positive "
                    "feedback. At high fractions the loop diverges, the "
                    "effective inlet crosses the emergency threshold, and "
                    "the server powers off. Containment is what keeps "
                    "this knob near zero in a real hall."
                ),
                expert=(
                    "Recirc 30/60/85% steps. Inlet_eff = inlet + "
                    "r·(exhaust−inlet) diverges; emergency power-off. "
                    "Containment, argued by simulation."
                ),
            ),
        ],
        question="At which recirculation fraction does the loop stop converging?",
        scenario=Scenario(
            config=BALANCED, workload=DATABASE, environment=Environment(),
            duration_s=720,
            events=[
                SimEvent(at_s=120, action="set-recirculation", value=30),
                SimEvent(at_s=300, action="set-recirculation", value=60),
                SimEvent(at_s=420, action="set-recirculation", value=85),
            ],
        ),
    ),
    GuidedScenario(
        id="psu-sweet-spot",
        title="PSU efficiency sweet spot",
        narration=[
            L(
                novice=(
                    "Power supplies waste a little of everything that "
                    "passes through them, and how much depends on how "
                    "hard they are working — they are least efficient "
                    "when barely loaded and most efficient near half "
                    "load. This run kills one of the two supplies "
                    "mid-run at constant work: the survivor carries "
                    "everything, its operating point shifts, and the "
                    "wall wattage changes even though the computer's "
                    "work did not."
                ),
                standard=(
                    "Same database workload throughout; at t=300 s one "
                    "PSU of the 1+1 pair fails. The survivor takes the "
                    "full load and its efficiency point moves along the "
                    "Titanium curve (90% at light load, 96% near half, "
                    "94% flat out). Watch DC stay put while AC shifts — "
                    "the gap between the two readouts is the conversion "
                    "loss this scenario exists to make visible."
                ),
                expert=(
                    "1+1 → 1 at t=300, load const. η point shifts on the "
                    "curve; DC flat, AC moves. Loss made visible."
                ),
            ),
        ],
        question="Did wall power rise or fall when the survivor took the whole load — and why?",
        scenario=Scenario(
            config=BALANCED, workload=DATABASE, environment=Environment(),
            duration_s=600,
            events=[SimEvent(at_s=300, action="kill-psu")],
        ),
    ),
    GuidedScenario(
        id="altitude",
        title="Altitude",
        narration=[
            L(
                novice=(
                    "The same server, the same work, but at 2,500 metres "
                    "— a data center in Mexico City or Denver's high "
                    "suburbs. Thin air carries less heat per litre, so "
                    "the fans must move more of it to do the same job: "
                    "higher speeds, more fan power, less margin. Nothing "
                    "else changed. Mountains show up on server spec "
                    "sheets for exactly this reason."
                ),
                standard=(
                    "The HPC workload at 2,500 m: air density is about "
                    "22% lower, so mass flow per CFM drops and the fans "
                    "run measurably faster for the same silicon "
                    "temperatures — with the rpm³ power cost that "
                    "implies. Dell's derating note (supported ambient "
                    "falls ~1 °C per 300 m above 950 m) is this physics, "
                    "written as a warranty condition; the validation "
                    "panel carries it as a warning."
                ),
                expert=(
                    "2,500 m: ρ −22%, ṁ per CFM down, rpm up, fan W up. "
                    "The derating note is this, contractualized."
                ),
            ),
        ],
        question="Compare fan rpm at sea level and at 2,500 m for this load — what is the difference costing in watts?",
        scenario=Scenario(
            config=BALANCED, workload=HPC,
            environment=Environment(altitude_m=2500),
            duration_s=600,
        ),
    ),
]

# --- Explain-mode entries (spec §8) ---------------------------------------

EXPLAINS = [
    Explain(
        id="cpu-power",
        title="CPU power",
        equation="P_cpu = sockets × (P_idle + (TDP − P_idle) × util^1.4) × clamp",
        inputs=["CPU util", "CPU power", "CPU heat", "fan rpm", "fan power", "total power"],
        explanation=L(
            novice=(
                "A processor never drops to zero watts — even idle it "
                "spends around fifteen percent of its maximum just being "
                "on. From there, power rises with load, and faster than "
                "you might expect: the curve bends upward, so the last "
                "stretch to 100% costs more than the first. If the chip "
                "gets too hot, the 'clamp' cuts this number down to "
                "protect it — that is throttling."
            ),
            standard=(
                "CPU package power interpolates from an idle floor "
                "(~15% of TDP) to full TDP along util^1.4 — superlinear "
                "because higher utilization brings higher clocks and "
                "voltages, not just busier cores. At sustained 100% the "
                "package briefly boosts ~15% over TDP before settling. "
                "The clamp term is the throttle multiplier: 1.0 "
                "normally, stepped down 10% per tick above 98 °C."
            ),
            expert=(
                "Idle-floor + (TDP−idle)·util^1.4, ×1.15 boost ≤60 s, "
                "×throttle clamp. Superlinearity ≈ DVFS proxy."
            ),
        ),
    ),
    Explain(
        id="zone-outlet",
        title="Zone outlet temperature",
        equation="T_out = T_in + Q / (ṁ × cp)",
        inputs=["zone heat", "airflow", "inlet temp", "outlet temp"],
        explanation=L(
            novice=(
                "Air warms as it crosses each part of the server, and by "
                "a knowable amount: the heat added, divided by how much "
                "air is passing and how much heat air can hold. Less "
                "airflow or more heat means hotter air out the back. "
                "This one line is most of what a thermal engineer does "
                "all day."
            ),
            standard=(
                "Each zone's outlet is its inlet plus Q/(ṁ·cp): heat in "
                "watts over mass flow times air's specific heat "
                "(1005 J/kg·K). Zones chain front to back — one zone's "
                "outlet is the next zone's inlet — and summing every "
                "zone gives the whole-box identity exhaust = inlet + "
                "DC/(ṁ·cp), the IR7000 twin's heat balance seen from "
                "inside."
            ),
            expert=(
                "T_out = T_in + Q/(ṁcp); zones chain; Σ gives exhaust "
                "identity. ṁ derated by altitude density."
            ),
        ),
    ),
    Explain(
        id="fan-power",
        title="Fan power",
        equation="P_fan = N_alive × P_max × (rpm%)³",
        inputs=["CPU temp", "fan rpm", "fan power", "total power", "heat"],
        explanation=L(
            novice=(
                "Fan power grows with the cube of speed: twice the speed "
                "costs eight times the electricity. That is why a "
                "slightly warmer room can noticeably raise a server's "
                "power bill — and why the fans' own watts, which also "
                "become heat, are highlighted as 'overhead' in the "
                "instruments."
            ),
            standard=(
                "Cubic fan law: power scales with rpm³ (airflow with "
                "rpm, pressure with rpm²). The feedback teaching point: "
                "fan watts pass through the PSUs like any load and then "
                "become heat in the very airflow path the fans maintain "
                "— cooling appears on both sides of its own ledger."
            ),
            expert=(
                "P ∝ rpm³ (affinity laws). Fan W is PSU load and duct "
                "heat simultaneously — the loop."
            ),
        ),
    ),
    Explain(
        id="wall-power",
        title="Wall (AC) power",
        equation="P_wall = P_dc / η(load fraction)",
        inputs=["total DC power", "PSU load point", "efficiency", "wall power"],
        explanation=L(
            novice=(
                "The power supplies convert wall electricity to the "
                "voltages the parts use, and lose a few percent doing "
                "it — least efficient when barely loaded, best around "
                "half load. So the wall meter always reads higher than "
                "the sum of the parts, and by how much depends on how "
                "hard the supplies happen to be working."
            ),
            standard=(
                "Wall power is DC load divided by efficiency at the "
                "current load fraction, read off the Titanium-class "
                "curve (≈90% at 10% load, 96% near 50%, 94% at 100%). "
                "In 1+1 the pair shares load so each sits lower on the "
                "curve; lose one and the survivor's point — and the "
                "wall wattage — moves."
            ),
            expert=(
                "AC = DC/η(load). Piecewise Titanium curve; 1+1 halves "
                "the per-PSU point. Loss = AC − DC, vented rear."
            ),
        ),
    ),
    Explain(
        id="recirculation",
        title="Effective inlet with recirculation",
        equation="T_inlet_eff = T_room + r × (T_exhaust − T_room)",
        inputs=["exhaust temp", "recirculation", "effective inlet", "CPU temp"],
        explanation=L(
            novice=(
                "If some of the server's hot exhaust finds its way back "
                "to the front, the machine breathes air warmer than the "
                "room — and warmer intake makes warmer exhaust, which "
                "makes warmer intake. Small amounts are absorbed; large "
                "amounts feed on themselves until the server must shut "
                "off. Good server rooms are built to keep the two air "
                "streams apart."
            ),
            standard=(
                "One knob stands in for every containment failure: the "
                "effective inlet mixes fraction r of the box's own "
                "exhaust into the room air. Because exhaust depends on "
                "inlet, this is positive feedback — convergent at small "
                "r, divergent past the point where the loop gain "
                "reaches one, at which point the emergency inlet limit "
                "ends the run."
            ),
            expert=(
                "Inlet_eff = T + r(exh−T); loop gain r·dExh/dInlet ≥ 1 "
                "→ divergence → thermal trip. Containment in one knob."
            ),
        ),
    ),
]
