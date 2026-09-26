"""Presets and the teaching layer for the client-device simulator —
config presets, workload presets, guided scenarios (spec 07's scenario
list for both products), and Explain-mode entries. Scenario and explain
prose carries reading levels, R760-thermal style.
"""

from __future__ import annotations

from .leveling import L
from .models import (
    ConfigPreset,
    DeviceConfig,
    Environment,
    Explain,
    GuidedScenario,
    PageIntro,
    Term,
    Scenario,
    SimEvent,
    Workload,
    WorkloadPreset,
)

# --- Config presets --------------------------------------------------------

AW_LAPTOP = DeviceConfig(
    product="alienware", form_factor="laptop", cpu_pl1_w=55, gpu_tgp_w=140,
    ram_gb=32, nvme_count=1, battery_wh=90, charger_w=240,
)

AW_LAPTOP_MAX = DeviceConfig(
    product="alienware", form_factor="laptop", cpu_pl1_w=65, gpu_tgp_w=175,
    ram_gb=64, nvme_count=2, battery_wh=97, charger_w=330,
)

AW_DESKTOP = DeviceConfig(
    product="alienware", form_factor="desktop", cpu_pl1_w=125, gpu_tgp_w=450,
    ram_gb=64, nvme_count=2, psu_capacity_w=1000,
)

PROMAX_NPU = DeviceConfig(
    product="promax", form_factor="laptop", cpu_pl1_w=55, gpu_tgp_w=115,
    npu=True, ram_gb=64, nvme_count=2, battery_wh=96, charger_w=280,
)

PROMAX_GPU = DeviceConfig(
    product="promax", form_factor="laptop", cpu_pl1_w=55, gpu_tgp_w=115,
    npu=False, ram_gb=64, nvme_count=2, battery_wh=96, charger_w=280,
)

CONFIG_PRESETS = [
    ConfigPreset(id="aw-laptop", compare_preset_id="aw-desktop", name="Alienware 16 laptop", config=AW_LAPTOP,
                 blurb="55 W CPU, 140 W GPU, 90 Wh — the mainstream gaming laptop."),
    ConfigPreset(id="aw-laptop-max", name="Alienware 18 max", config=AW_LAPTOP_MAX,
                 blurb="65 W CPU, 175 W TGP, 330 W brick — the biggest laptop build."),
    ConfigPreset(id="aw-desktop", name="Alienware tower", config=AW_DESKTOP,
                 blurb="125 W CPU, 450 W GPU, 1000 W PSU — the control group."),
    ConfigPreset(id="promax-npu", compare_preset_id="promax-gpu", name="Pro Max Plus + NPU", config=PROMAX_NPU,
                 blurb="Workstation with the discrete NPU card. Dell ships the card in place of the discrete GPU; this model keeps both so one machine can run the comparison."),
    ConfigPreset(id="promax-gpu", name="Pro Max Plus (GPU only)", config=PROMAX_GPU,
                 blurb="Same workstation without the NPU — the honest contrast."),
]

# --- Workload presets (spec 07) --------------------------------------------

IDLE = Workload()
ESPORTS = Workload(cpu_pct=40, gpu_pct=60)
AAA = Workload(cpu_pct=70, gpu_pct=100)
STREAM = Workload(cpu_pct=90, gpu_pct=95)
STRESS = Workload(cpu_pct=100, gpu_pct=100)
RENDER = Workload(cpu_pct=100, gpu_pct=30)
LLM_CPU = Workload(cpu_pct=100, inference=True)
LLM_GPU = Workload(gpu_pct=90, inference=True)
LLM_NPU = Workload(npu_pct=100, cpu_pct=10, inference=True)

WORKLOAD_PRESETS = [
    WorkloadPreset(id="idle", name="Idle", workload=IDLE),
    WorkloadPreset(id="esports", name="Esports title", workload=ESPORTS),
    WorkloadPreset(id="aaa", name="AAA ray-traced", workload=AAA),
    WorkloadPreset(id="stream", name="Stream + game", workload=STREAM),
    WorkloadPreset(id="stress", name="Synthetic stress", workload=STRESS),
    WorkloadPreset(id="render", name="ISV render", workload=RENDER),
    WorkloadPreset(id="llm-cpu", name="Local LLM · CPU", workload=LLM_CPU),
    WorkloadPreset(id="llm-gpu", name="Local LLM · GPU", workload=LLM_GPU),
    WorkloadPreset(id="llm-npu", name="Local LLM · NPU", workload=LLM_NPU),
]

# --- Guided scenarios ------------------------------------------------------

GUIDED_SCENARIOS = [
    GuidedScenario(
        id="benchmark-lie",
        title="The 10-minute benchmark lie",
        narration=[
            L(
                novice=(
                    "A stress test starts at the one-minute mark and runs "
                    "for the rest of the trace. Watch the frame counter: "
                    "for about half a minute the machine is faster than "
                    "it can afford to stay, because processors are "
                    "allowed a short burst above their sustainable "
                    "limit. Then the burst window closes, the case "
                    "warms toward its touch limit, and performance "
                    "settles to what the cooling — and your palms — can "
                    "actually live with. A review that benchmarks for "
                    "two minutes measures the burst; you will own the "
                    "settle."
                ),
                standard=(
                    "Synthetic stress lands at t=60 s. The CPU opens at "
                    "PL2 (the ~28 s boost window), the shared budget "
                    "then arbitrates between CPU and GPU, and the skin "
                    "zone — slow, τ ≈ 120 s — creeps toward its cap and "
                    "claws power back. Compare fps at minute 1 against "
                    "minute 15 in the summary: the gap between them is "
                    "the burst-then-fade shape that defines laptop "
                    "benchmarking, and the reason 'up to' clauses exist."
                ),
                expert=(
                    "Stress at t=60: PL2 window → budget arbitration → "
                    "skin governor. fps(1 min) vs fps(15 min) is the "
                    "whole story."
                ),
            ),
        ],
        question="How many FPS separate minute 1 from minute 15, and which limiter took each bite?",
        scenario=Scenario(
            config=AW_LAPTOP, workload=IDLE, environment=Environment(),
            duration_s=1200,
            events=[SimEvent(at_s=60, action="set-workload", workload=STRESS)],
        ),
    ),
    GuidedScenario(
        id="on-lap",
        title="On-lap gaming",
        narration=[
            L(
                novice=(
                    "Five minutes into a demanding game, the laptop "
                    "moves from the desk to a lap. The bottom of the "
                    "machine is where it breathes in, and a lap blocks "
                    "much of that. Watch the chain: less air, hotter "
                    "chips, faster fans, and then the case itself warms "
                    "past what skin should touch — at which point the "
                    "machine cuts its own power no matter what the fans "
                    "say. The frame counter sags, and the surface stays "
                    "just barely comfortable. That is the machine "
                    "choosing your legs over your frame rate."
                ),
                standard=(
                    "AAA load; at t=300 s the machine moves on-lap: the "
                    "bottom intake blocks, the thermal budget derates, "
                    "and interior preheat rises. Fans ramp first, then "
                    "the skin zone crosses the contact cap and the skin "
                    "governor steps power limits down — the one "
                    "controller in this machine that fan speed cannot "
                    "appease. FPS sags accordingly. Note the order: "
                    "airflow, silicon, skin, watts — each on its own "
                    "time constant."
                ),
                expert=(
                    "AAA; on-lap at t=300. Budget derates, preheat +6 K, "
                    "skin crosses cap → governor clamps. Fans can't fix "
                    "a blocked intake."
                ),
            ),
        ],
        question="How long after moving on-lap does the skin governor engage?",
        scenario=Scenario(
            config=AW_LAPTOP, workload=AAA, environment=Environment(),
            duration_s=1200,
            events=[SimEvent(at_s=300, action="set-on-lap", value=1)],
        ),
    ),
    GuidedScenario(
        id="quiet-cost",
        title="Quiet mode cost",
        narration=[
            L(
                novice=(
                    "Mid-game, the machine switches to quiet mode: the "
                    "fans are capped so the room stays peaceful. The "
                    "heat has to go somewhere, so the chips run hotter, "
                    "and to keep them safe the machine lowers how much "
                    "power they may draw. The result is a trade you can "
                    "read on two meters at once: the noise number falls, "
                    "and the frame counter falls with it. Silence is a "
                    "setting, and it has a price in frames."
                ),
                standard=(
                    "AAA load; quiet mode engages at t=300 s, capping "
                    "the fan ceiling and shrinking the thermal budget. "
                    "Component temperatures rise toward their throttle "
                    "lines, the allocator clips harder, and delivered "
                    "GPU watts — therefore FPS — fall. Watch dB(A) and "
                    "FPS move together: acoustics is a first-class "
                    "output on a client device, and this scenario "
                    "prices it."
                ),
                expert=(
                    "Quiet at t=300: fan cap + budget ×0.62 → hotter "
                    "silicon → clipped watts → FPS. dB(A) and FPS are "
                    "one trade."
                ),
            ),
        ],
        question="How many dB(A) did quiet mode buy, and how many FPS did it cost?",
        scenario=Scenario(
            config=AW_LAPTOP, workload=AAA, environment=Environment(),
            duration_s=1200,
            events=[SimEvent(at_s=300, action="set-mode", mode="quiet")],
        ),
    ),
    GuidedScenario(
        id="undersized-charger",
        title="The undersized charger",
        narration=[
            L(
                novice=(
                    "This machine ships with a 330-watt power brick; "
                    "someone has plugged in a 180-watt travel charger "
                    "instead, and then started a heavy game. The "
                    "charger gives everything it has, and the "
                    "difference comes out of the battery — even though "
                    "the machine is plugged in. Watch the battery "
                    "percentage fall during the game. Plugged in does "
                    "not mean charging; it means the wall is helping."
                ),
                standard=(
                    "The max laptop build with a 180 W charger swapped "
                    "in at t=120 s, then stream+game load: system draw "
                    "exceeds the adapter, and the hybrid path makes up "
                    "the deficit from the pack — battery discharge "
                    "while plugged in, exactly as the energy identity "
                    "requires (adapter + battery = system + charge, "
                    "every tick). The validation panel warned about "
                    "this; the trace demonstrates it."
                ),
                expert=(
                    "180 W brick vs ~280 W draw: hybrid deficit from "
                    "the pack, plugged in. Identity holds; battery "
                    "falls anyway."
                ),
            ),
        ],
        question="At the observed drain rate, how long until the pack is empty despite the charger?",
        scenario=Scenario(
            config=AW_LAPTOP_MAX, workload=IDLE, environment=Environment(),
            duration_s=1800,
            events=[
                SimEvent(at_s=120, action="set-charger", value=180),
                SimEvent(at_s=180, action="set-workload", workload=STREAM),
            ],
        ),
    ),
    GuidedScenario(
        id="three-engines",
        title="Same model, three engines",
        narration=[
            L(
                novice=(
                    "The same AI language model runs three times, 400 "
                    "seconds each: first on the processor (CPU), then "
                    "on the graphics chip (GPU), then on the dedicated "
                    "AI chip (NPU). The event log names each switch, "
                    "and the results table under the instruments keeps "
                    "one row per run so you can compare them at the "
                    "end. Before it plays, guess which chip writes "
                    "words fastest and which needs the least energy "
                    "for each word. Then read four things on each run: "
                    "tokens per second (a token is about one word), "
                    "system power in watts, fan noise in dB(A), and "
                    "tokens per joule, which says how many words one "
                    "unit of energy buys. The machine is on battery "
                    "the whole time, so look at the runtime left row "
                    "as well. All three runs use the same model — a "
                    "roughly 13-billion-parameter local model, kept in "
                    "the same small 4-bit number format on every chip — "
                    "so the differences you read come from the chips, "
                    "not from one run being handed an easier version of "
                    "the model."
                ),
                standard=(
                    "The local-LLM preset rotates across engines on "
                    "battery: CPU at t=0, GPU at t=400, NPU at t=800. "
                    "The log names each switch and the results table "
                    "keeps one row per leg. Read five instruments per "
                    "leg: tokens/s, system watts, fan noise in dB(A), "
                    "tok/J per engine watt, and tok/J per system watt. "
                    "The two tok/J figures differ because the display, "
                    "memory, storage and fans draw power whichever "
                    "chip is working, and the system figure is the one "
                    "that sets battery runtime. Each load step opens a "
                    "short boost window (PL2 on the CPU, an excursion "
                    "above TGP on the GPU); the log marks where it "
                    "ends, so compare the legs after the fade. One "
                    "assumption makes the table readable: all three "
                    "legs run the same ~13B-class model at the same "
                    "numeric precision (4-bit weights), so what the "
                    "rows compare is silicon rather than quantization. "
                    "On real hardware an NPU's efficiency lead is "
                    "partly an INT8/INT4-versus-FP16 result — see the "
                    "DellProMaxPlus twin, which runs MXINT4 weights "
                    "with FP16 compute."
                ),
                expert=(
                    "CPU→GPU→NPU legs at t=0/400/800, on battery, same "
                    "~13B-class model at 4-bit weights on every leg — "
                    "the rows isolate silicon, not quantization. Per "
                    "leg: tok/s, system W, dB(A), tok/J at the engine "
                    "and at the system. Compare after each boost "
                    "window closes."
                ),
            ),
        ],
        question=(
            "Which engine gives the most tokens per second, which is "
            "loudest, and how much of the NPU's tokens-per-joule lead is "
            "left when you count system watts instead of engine watts?"
        ),
        scenario=Scenario(
            config=PROMAX_NPU, workload=LLM_CPU,
            environment=Environment(plugged_in=False),
            duration_s=1200,
            events=[
                SimEvent(at_s=400, action="set-workload", workload=LLM_GPU),
                SimEvent(at_s=800, action="set-workload", workload=LLM_NPU),
            ],
        ),
    ),
    GuidedScenario(
        id="render-on-battery",
        title="8-hour render on battery?",
        narration=[
            L(
                novice=(
                    "A long render job starts on a full battery with no "
                    "charger. The machine holds its sustained pace — "
                    "workstations are tuned for exactly this — but "
                    "look at the runtime estimate: a 96 watt-hour "
                    "battery feeding a machine drawing around 90 watts "
                    "lasts about an hour, not eight. No setting changes "
                    "this; it is division. The scenario exists so the "
                    "arithmetic is felt rather than read."
                ),
                standard=(
                    "The ISV render preset, unplugged, full pack: "
                    "sustained PL1 work at ~85–95 W system draw against "
                    "96 Wh × 0.92 usable — the runtime readout does the "
                    "Wh ÷ W division live and lands near an hour. The "
                    "trace ends in the low-battery power-off. The "
                    "lesson is that battery capacity is a numerator, "
                    "not a feature: sustained workloads are wall-power "
                    "workloads."
                ),
                expert=(
                    "96 Wh · 0.92 / ~90 W ≈ 1 h. The render is 8. "
                    "Division, dramatized."
                ),
            ),
        ],
        question="How many minutes did the pack actually last, and what would 8 hours require in Wh?",
        scenario=Scenario(
            config=PROMAX_NPU, workload=RENDER,
            environment=Environment(plugged_in=False),
            duration_s=6000,
        ),
    ),
    GuidedScenario(
        id="meeting-room",
        title="Meeting-room inference",
        narration=[
            L(
                novice=(
                    "An AI assistant runs locally during a meeting — "
                    "first on the graphics chip, then the same job "
                    "moves to the AI chip. Watch the noise meter: the "
                    "graphics chip pushes the fans into the audible "
                    "range, the AI chip barely wakes them. The words "
                    "arrive a little slower and nobody in the room can "
                    "hear the machine thinking. For work that happens "
                    "near people, quiet is a feature you can measure."
                ),
                standard=(
                    "GPU inference to t=400 s, then the same load on "
                    "the NPU. The GPU leg drives ~130 W of system draw "
                    "and holds the fans near 40% and ~29 dB(A) after a "
                    "louder burst at the start; the NPU leg drops draw "
                    "by about 40% and lets the fans fall to the floor "
                    "at ~25 dB(A), with tokens/s down by about a "
                    "quarter. dB(A) is the instrument to watch: the "
                    "NPU's efficiency shows up as silence before it "
                    "shows up on any battery gauge."
                ),
                expert=(
                    "GPU leg vs NPU leg, same prompt stream: ~0.6× the "
                    "system watts, fans at the floor, ~0.75× tok/s. "
                    "Efficiency audible."
                ),
            ),
        ],
        question="Where does the noise settle on each engine, and what did the swap cost in tokens/s?",
        scenario=Scenario(
            config=PROMAX_NPU, workload=LLM_GPU, environment=Environment(),
            duration_s=900,
            events=[SimEvent(at_s=400, action="set-workload", workload=LLM_NPU)],
        ),
    ),
]

# --- Page intro and instrument glossary ------------------------------------

PAGE_INTRO = PageIntro(
    heading="Burst, budget, skin, battery — the client-device physics",
    text=L(
        novice=(
            "This page is a working model of the power and heat inside "
            "a laptop or desktop: an Alienware gaming machine, or the "
            "Dell Pro Max Plus workstation with its separate AI chip "
            "(NPU). Pick a guided scenario, press Run, and watch the "
            "instruments. Four ideas explain most of what you will see. "
            "Chips sprint for about half a minute and then settle to a "
            "pace they can hold; the readout calls the sprint PL2 and "
            "the steady pace PL1. In a laptop the processor and the "
            "graphics chip share one cooler, so they cannot both run "
            "flat out. The case has to stay cool enough to touch, below "
            "46 °C, and that rule beats every other. Battery life is "
            "division: energy stored, divided by power drawn. The "
            "numbers are illustrative, and estimates are marked."
        ),
        standard=(
            "The R760 thermal twin's engine, shrunk to the machines "
            "that sit on desks and laps: an Alienware laptop or tower "
            "and the Pro Max Plus workstation with its discrete NPU. "
            "Three mechanics that servers never meet. A load step opens "
            "a burst window: the CPU runs at its short-term power limit "
            "(PL2) and the GPU above its total graphics power (TGP), "
            "then both fade to their sustained limits (PL1 and TGP). "
            "One shared thermal budget is what CPU and GPU fight over. "
            "A skin-temperature cap, the limit on how hot the case may "
            "get where people touch it, has the final say. Add a "
            "battery whose runtime is division, watt-hours over watts. "
            "Every constant is sourced or marked as an estimate."
        ),
        expert=(
            "Client power and thermal proxy model: PL2→PL1 fade "
            "(τ ≈ 28 s) with a GPU excursion above TGP, a shared "
            "heat-pipe budget that favors the GPU, a 46 °C skin "
            "governor, and Wh ÷ W runtime. Constants are sourced or "
            "flagged as estimates."
        ),
    ),
    terms=[
        Term(term="limit state", meaning="What is holding the chips back right now: the boost window, the sustained limits, the shared cooling budget, or the skin cap."),
        Term(term="PL2 and PL1", meaning="The CPU's two power limits. PL2 is the short sprint allowed after a load step; PL1 is the pace it can hold indefinitely."),
        Term(term="TGP", meaning="Total graphics power, the GPU's sustained power limit. It may run a little above it during the boost window."),
        Term(term="skin temp", meaning="The temperature of the case where a person touches it. Above 46 °C the machine cuts power, whatever the fans are doing."),
        Term(term="dB(A)", meaning="Fan noise as the ear weighs it. About 25 is a quiet room; each extra 10 sounds roughly twice as loud."),
        Term(term="FPS proxy", meaning="A stand-in for game frame rate, scaled from the power the GPU receives. It is a model output, not a benchmark."),
        Term(term="tok/s", meaning="Tokens per second, the speed of a language model. A token is about one word."),
        Term(term="tok/J (engine) and tok/J (system)", meaning="Tokens per joule of energy. The engine figure divides by the working chip's watts alone; the system figure divides by the whole machine's watts, which is what the battery supplies."),
    ],
)

# --- Explain-mode entries --------------------------------------------------

EXPLAINS = [
    Explain(
        id="power-limits",
        title="PL1 / PL2 power limits",
        equation="P_cpu = min(demand(util), PL2 for τ ≈ 28 s, then PL1) × clamps",
        inputs=["CPU util", "boost window", "power limit", "CPU power", "FPS/tokens"],
        explanation=L(
            novice=(
                "Laptop processors have two speed budgets: a short "
                "sprint budget and a marathon budget. When work "
                "arrives, the chip sprints — for about half a minute — "
                "then drops to the pace it can hold all day. Reviews "
                "that only time the sprint flatter every laptop; the "
                "marathon number is the one you live with."
            ),
            standard=(
                "The CPU runs at PL2 (here 1.6 × PL1) for a boost "
                "window of τ ≈ 28 s after a load step, then settles to "
                "PL1. The skin governor and the shared-budget "
                "allocator can push the effective limit below PL1 — "
                "the pl-state readout names whichever limiter "
                "currently binds. Burst-then-fade is not a defect; it "
                "is the contract."
            ),
            expert=(
                "PL2 = 1.6·PL1, τ ≈ 28 s, re-armed per load step; "
                "effective limit = min(PL, skin clamp, budget). "
                "pl-state names the binder."
            ),
        ),
    ),
    Explain(
        id="thermal-budget",
        title="The shared thermal budget",
        equation="P_cpu + P_gpu + P_npu ≤ budget(chassis, mode, intake)",
        inputs=["CPU demand", "GPU demand", "budget", "allocation", "FPS"],
        explanation=L(
            novice=(
                "In a laptop, the processor and graphics chip share "
                "the same copper heat pipes — one cooling system, two "
                "hungry chips. When both want more than the cooling "
                "can remove, the machine must choose, and under game "
                "load it favors the graphics chip because frames are "
                "what you notice. Max CPU and max GPU at the same "
                "time is not a setting; it is a physical impossibility."
            ),
            standard=(
                "The chassis can dissipate a fixed sustained wattage "
                "(scaled by GPU tier, performance mode, and intake "
                "state). When component demands exceed it, the "
                "allocator grants the NPU first (small), the GPU next "
                "(game-load favoritism), and the CPU takes the "
                "remainder down to a floor. The two-bars-fighting "
                "display is this equation drawn live; the desktop "
                "tower, with separate coolers, never enters it."
            ),
            expert=(
                "budget = (140 + 0.55·TGP)·mode·intake; grant order "
                "NPU→GPU→CPU-to-floor. Desktop: budget ≈ ∞, limiter "
                "is PSU."
            ),
        ),
    ),
    Explain(
        id="skin-cap",
        title="The skin-temperature cap",
        equation="T_skin → ambient + Q_internal × R_skin;  T_skin ≤ 46 °C enforced",
        inputs=["internal heat", "skin temp", "skin governor", "power limits"],
        explanation=L(
            novice=(
                "A server can run as hot as its parts allow; a laptop "
                "rests on skin. The case warms slowly — metal takes "
                "minutes, not seconds — and when it reaches the "
                "comfort limit the machine turns its own power down, "
                "even if the fans have headroom left. This is the "
                "quiet reason two laptops with identical chips can "
                "perform differently: the case, not the silicon, has "
                "the last word."
            ),
            standard=(
                "The skin zone follows total internal heat with "
                "τ ≈ 120 s and a hard cap near 46 °C. Crossing it "
                "engages the skin governor, which steps power limits "
                "down 2%/s until the surface recovers — overriding "
                "the fan controller entirely. Because the zone is "
                "slow, the governor engages minutes after the load "
                "that caused it: sustained performance is a "
                "skin-temperature problem before it is a silicon one."
            ),
            expert=(
                "τ_skin ≈ 120 s ≫ τ_si; cap 46 °C → −2%/s clamp, fan-"
                "independent. The slow pole owns the steady state."
            ),
        ),
    ),
    Explain(
        id="battery-runtime",
        title="Battery runtime",
        equation="runtime = Wh × health × η_discharge ÷ P_system",
        inputs=["capacity", "health", "system power", "runtime"],
        explanation=L(
            novice=(
                "Runtime is division: the battery holds so many "
                "watt-hours, the machine burns so many watts, and one "
                "over the other is your hours — minus a little lost "
                "as heat on the way out, minus whatever age has taken "
                "from the pack. Every runtime claim ever printed is "
                "this fraction with a flattering numerator."
            ),
            standard=(
                "Delivered energy is capacity × health × 0.92 "
                "discharge efficiency; runtime divides it by current "
                "system draw, live. Charging adds ~10% of charge "
                "power as heat inside the chassis, and a worn pack "
                "adds internal-resistance heat under discharge — "
                "battery state feeds the thermal model, not just the "
                "gauge."
            ),
            expert=(
                "Wh·health·0.92/W, recomputed per tick; charge heat "
                "10%, IR heat scales with wear and discharge "
                "fraction."
            ),
        ),
    ),
    Explain(
        id="energy-identity",
        title="The supply identity",
        equation="P_adapter + P_battery_discharge = P_system + P_charge",
        inputs=["adapter", "battery", "system power", "charge"],
        explanation=L(
            novice=(
                "Every watt the machine uses comes from the wall or "
                "from the battery, and every wall watt not used goes "
                "into the battery. That single sentence explains the "
                "undersized-charger surprise: if the wall cannot cover "
                "the load, the battery makes up the difference — "
                "plugged in or not."
            ),
            standard=(
                "The tick-level conservation law, inherited from the "
                "DellAlienware twin and asserted in the tests: adapter "
                "DC plus battery discharge equals system power plus "
                "charge power. Hybrid operation (both sources at "
                "once) is not an anomaly — it is the identity's "
                "third column. Wall draw is adapter DC ÷ charger "
                "efficiency; on desktops the same law wears its PSU "
                "curve form, AC = DC ÷ η(load)."
            ),
            expert=(
                "Adapter + discharge = system + charge, ±rounding, "
                "every tick; wall = DC/η. Same law, both form "
                "factors."
            ),
        ),
    ),
    Explain(
        id="tokens-per-joule",
        title="Tokens per joule",
        equation="tok/J (engine) = tok/s ÷ P_engine   ·   tok/J (system) = tok/s ÷ P_system",
        inputs=["engine", "token rate", "engine power", "system power", "efficiency"],
        explanation=L(
            novice=(
                "Speed says how fast the words come; tokens per joule "
                "says what each word costs in energy. The meter shows "
                "the cost twice. The engine figure counts only the "
                "chip doing the work. The system figure counts the "
                "whole machine, screen and fans included, and that is "
                "the one the battery feels. The dedicated AI chip "
                "loses the speed race and wins the cost race on both "
                "figures, by a wide margin at the chip and a smaller "
                "one at the battery."
            ),
            standard=(
                "Each engine has a characteristic rate at full power "
                "(estimates: CPU ~6 tok/s, GPU ~45 in the boost "
                "window and ~39 sustained, NPU ~30) and a power cost. "
                "Per engine watt the NPU's ~0.75 tok/J is about "
                "double the GPU's ~0.39. Per system watt the lead "
                "shrinks to ~0.38 against ~0.30, about 1.3×, because "
                "roughly 25 W of display, memory, storage and fans, "
                "plus the two idle engines, runs under every leg. Battery runtime follows the "
                "system figure; fan noise follows the engine watts. The "
                "rates assume one model — ~13B-class, 4-bit weights — "
                "run at the same precision on each engine, so the "
                "comparison is between chips rather than between "
                "quantizations."
            ),
            expert=(
                "tok/J at the engine: NPU ≈ 0.75, GPU ≈ 0.39, CPU ≈ "
                "0.11. At the system: ≈ 0.38 / 0.30 / 0.07. The ~25 W "
                "platform floor plus idle engines dilutes the NPU's 1.9× to 1.3× "
                "(estimates). One model, ~13B-class at 4-bit weights, "
                "same precision on every engine — the ratios are "
                "architectural, not a quantization artefact."
            ),
        ),
    ),
]
