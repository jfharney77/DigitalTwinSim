"""Presets and the teaching layer for the data & observability sim."""

from __future__ import annotations

from .leveling import L
from .models import (
    ConfigPreset,
    DataConfig,
    Explain,
    GuidedScenario,
    Scenario,
    SimEvent,
    Workload,
)

# --- Config presets --------------------------------------------------------

PIPELINE_CPU = DataConfig(
    product="aidataplatform", ingest_tbh=20, process_tbh=6, index_tbh=15,
    serve_tbh=30, gpu_processing=False, kv_offload=False,
)
PIPELINE_GPU = PIPELINE_CPU.model_copy(update={"gpu_processing": True})
PIPELINE_KV = PIPELINE_GPU.model_copy(update={"kv_offload": True})
CONSOLE = DataConfig(product="cloudiq", anomaly_k=3.0)
CONSOLE_TOUCHY = CONSOLE.model_copy(update={"anomaly_k": 1.5})
CONSOLE_DEAF = CONSOLE.model_copy(update={"anomaly_k": 5.5})

CONFIG_PRESETS = [
    ConfigPreset(id="pipeline-cpu", compare_preset_id="pipeline-gpu", name="Pipeline · CPU process", config=PIPELINE_CPU,
                 blurb="The clean/transform stage is the constraint."),
    ConfigPreset(id="pipeline-gpu", name="Pipeline · GPU process", config=PIPELINE_GPU,
                 blurb="×6 on the old bottleneck — meet the new one."),
    ConfigPreset(id="pipeline-kv", name="Pipeline + KV offload", config=PIPELINE_KV,
                 blurb="×4 long-context sessions for a 12% token tax."),
    ConfigPreset(id="console", compare_preset_id="console-touchy", name="Console · k=3", config=CONSOLE,
                 blurb="The balanced detector, ready to be graded."),
    ConfigPreset(id="console-touchy", name="Console · k=1.5", config=CONSOLE_TOUCHY,
                 blurb="Everything is an anomaly."),
    ConfigPreset(id="console-deaf", name="Console · k=5.5", config=CONSOLE_DEAF,
                 blurb="Nothing is an anomaly."),
]

DEFAULT_WL = Workload()
HUNGRY_WL = Workload(raw_arrival_tbh=8, gpu_read_demand_tbh=30,
                     inference_sessions_demand=300, long_context_pct=60)

# --- Guided scenarios ------------------------------------------------------

GUIDED_SCENARIOS = [
    GuidedScenario(
        id="find-the-bottleneck",
        title="Find the bottleneck",
        narration=[
            L(
                novice=(
                    "The pipeline moves as fast as its slowest stage — "
                    "here, the cleaning stage, and the map paints it "
                    "hot while data piles up in front of it. At hour "
                    "120 that stage gets six times faster (GPU "
                    "acceleration). Watch what happens: the pipeline "
                    "speeds up, and a different stage immediately "
                    "becomes the slowest. There is always exactly one "
                    "bottleneck; improvement is the art of choosing "
                    "which one you can live with."
                ),
                standard=(
                    "Theory of constraints, run live: process at "
                    "6 TB/h binds (arrival 8 exceeds it — the "
                    "validation panel warned), backlog and freshness "
                    "lag grow, and the fix-stage event at t=120 (×6 "
                    "GPU processing) relocates the constraint to "
                    "index at 15 TB/h. Fix that and serve binds "
                    "next. The bottleneck field names the constraint "
                    "each tick; the tests pin its movement."
                ),
                expert=(
                    "min() argmin: process → (×6) → index → serve. "
                    "The constraint moves; it never dies. Warned, "
                    "then demonstrated."
                ),
            ),
        ],
        question="Which stage became the constraint after the fix, and what did throughput do?",
        scenario=Scenario(
            config=PIPELINE_CPU, workload=DEFAULT_WL, duration_h=360,
            events=[SimEvent(at_h=120, action="toggle-gpu-process")],
        ),
    ),
    GuidedScenario(
        id="kv-trick",
        title="The KV-cache trick",
        narration=[
            L(
                novice=(
                    "An AI chat with a long history must keep that "
                    "history's working memory somewhere, and GPU "
                    "memory fits only about forty such sessions. This "
                    "run starts with three hundred long conversations "
                    "demanding service: most wait. At hour 120 the "
                    "spill switch turns on — session memory overflows "
                    "to fast shared storage — and capacity roughly "
                    "quadruples, while each word arrives about twelve "
                    "percent slower. Four times the customers for a "
                    "barely-felt delay: that is the trick, and the "
                    "two bars tell it whole."
                ),
                standard=(
                    "The KV-offload toggle mid-run: session capacity "
                    "40 → 160 (GPU-memory-resident vs spilled to "
                    "shared storage, NVIDIA CMX-class), active "
                    "long-context sessions jump to meet demand, and "
                    "the per-token latency tax appears at ~12%. Spec "
                    "06 calls this the most 2026-current concept in "
                    "the suite and asks for exactly this two-bar "
                    "display. PhysicsStorage's Lightning pool is "
                    "where the spilled bytes physically live."
                ),
                expert=(
                    "KV spill: sessions ×4, tokens +12%. Two bars, "
                    "one trade. The bytes land on the storage app's "
                    "Lightning pool."
                ),
            ),
        ],
        question="How many sessions were served before and after the toggle, and what did each token pay?",
        scenario=Scenario(
            config=PIPELINE_GPU, workload=HUNGRY_WL, duration_h=360,
            events=[SimEvent(at_h=120, action="toggle-kv")],
        ),
    ),
    GuidedScenario(
        id="stale-data",
        title="Stale data, confident model",
        narration=[
            L(
                novice=(
                    "Raw data arrives faster than the pipeline can "
                    "clean it, forever. Nothing crashes — the backlog "
                    "just grows, and with it the age of what the "
                    "models are actually trained on. Watch the "
                    "freshness gauge climb: by the end, the 'current' "
                    "data is days old, and every model consuming it "
                    "is confidently describing the past. The "
                    "validation panel warned about this before the "
                    "run started; the gauge is that warning, aging."
                ),
                standard=(
                    "Arrival 12 TB/h against a 6 TB/h constraint: "
                    "backlog grows linearly, freshness lag = backlog ÷ "
                    "throughput climbs without bound, and the model-"
                    "facing consequence is silent — served data stays "
                    "plentiful, just increasingly old. Spec 06's "
                    "'stale data, confident model' scenario: the "
                    "failure mode with no error message. Little's law "
                    "in the explain tab prices the in-flight data."
                ),
                expert=(
                    "λ > μ: Q ↑ linearly, lag = Q/X unbounded, no "
                    "alarm anywhere. Staleness is the silent failure; "
                    "Little's law audits it."
                ),
            ),
        ],
        question="How old is the freshest served data by the end of the run?",
        scenario=Scenario(
            config=PIPELINE_CPU,
            workload=DEFAULT_WL.model_copy(update={"raw_arrival_tbh": 12}),
            duration_h=360,
        ),
    ),
    GuidedScenario(
        id="tune-the-detector",
        title="Tune the anomaly detector (scored)",
        narration=[
            L(
                novice=(
                    "Three problems are planted at known times: an "
                    "array filling too fast, a network link silently "
                    "losing traffic, a fan drifting upward. The "
                    "detector watches trends and flags departures. "
                    "Because the simulator knows the truth, your "
                    "tuning gets a report card: how many plants were "
                    "found, how fast, and how many alarms were false. "
                    "Run the touchy and deaf presets afterward and "
                    "compare report cards. Every monitoring team on "
                    "earth is somewhere on this dial; few get graded."
                ),
                standard=(
                    "The scored tuning exercise: capacity at t=48, "
                    "gray at t=120, fan drift at t=240 — ground "
                    "truth. At k=3 the issues cross threshold in "
                    "order (signal grows ~1.2σ/day) while noise "
                    "excursions add false positives on a fixed "
                    "cadence. The scoreboard: precision, recall, "
                    "MTTD. The k=1.5 and k=5.5 presets bracket the "
                    "trade — same knob as Cyber Detect's sensitivity, "
                    "deliberately (spec 06 notes the rhyme)."
                ),
                expert=(
                    "GT at 48/120/240; signal 1.2σ/d vs k; FP "
                    "cadence ∝ k. P/R/MTTD scored. Same knob as the "
                    "resilience app — the rhyme is the syllabus."
                ),
            ),
        ],
        question="What were precision, recall, and MTTD at k=3 — and at the two extremes?",
        scenario=Scenario(
            config=CONSOLE, duration_h=480,
            events=[
                SimEvent(at_h=48, action="inject-capacity"),
                SimEvent(at_h=120, action="inject-gray"),
                SimEvent(at_h=240, action="inject-fan-drift"),
            ],
        ),
    ),
    GuidedScenario(
        id="days-to-full",
        title="Days-to-full",
        narration=[
            L(
                novice=(
                    "An array begins filling fast at day two, and the "
                    "console's forecast starts counting down the days "
                    "until it is full. The useful part is what "
                    "happens next: acting on the forecast — expanding "
                    "capacity at day ten, while the countdown still "
                    "reads comfortable — and watching the outage that "
                    "never happens. Rerun without the expansion "
                    "event: the array hits 100% and the run records "
                    "a capacity outage. A forecast's value is "
                    "measured in the disasters it converts into "
                    "purchase orders."
                ),
                standard=(
                    "Inject-capacity at t=48 (fill 2.5%/day), the "
                    "windowed fit converges on the true slope, and "
                    "expand-capacity at t=240 acts on it — "
                    "capacity_outage stays false. The no-action rerun "
                    "hits 100% and records the outage; the tests pin "
                    "both branches. Note the forecast-error gauge "
                    "settling as the week-long window fills with the "
                    "new slope — and try demand-change to watch it "
                    "spike again."
                ),
                expert=(
                    "Fill 2.5%/d from t=48; fit converges; act at "
                    "t=240 → no outage. Inaction → 100%. Forecasts "
                    "are outage-to-PO converters."
                ),
            ),
        ],
        question="What did the forecast read when the expansion happened, and what does the no-action rerun record?",
        scenario=Scenario(
            config=CONSOLE, duration_h=720,
            events=[
                SimEvent(at_h=48, action="inject-capacity"),
                SimEvent(at_h=240, action="expand-capacity"),
            ],
        ),
    ),
    GuidedScenario(
        id="green-but-sick",
        title="Green but sick",
        narration=[
            L(
                novice=(
                    "A network link begins silently losing a fraction "
                    "of its traffic. Every status light on every "
                    "device stays green for the entire run — check "
                    "the status readout as often as you like. But "
                    "the trend detector, watching behavior rather "
                    "than self-reports, flags the anomaly within a "
                    "couple of days. This is the fleet-telemetry "
                    "argument in one picture: devices report their "
                    "health honestly and wrongly, because the checks "
                    "they run are not the experience users have."
                ),
                standard=(
                    "The gray failure's payoff (spec 06 names it): "
                    "inject-gray at t=72, device_status_all_green "
                    "holds for the whole trace — asserted — while "
                    "the anomaly feed flags the trend departure at "
                    "k=3 within ~60 h. PhysicsFabric's gray toggle "
                    "showed the damage; this app shows the catch. "
                    "Together they are the argument for AIOps: "
                    "status is a claim, telemetry is evidence."
                ),
                expert=(
                    "Gray at t=72: green ∀t (asserted) ∧ flagged "
                    "≈ 60 h. Fabric shows the wound, console the "
                    "diagnosis. Status claims; trends testify."
                ),
            ),
        ],
        question="How long did the trend take to catch what the status lights never admitted?",
        scenario=Scenario(
            config=CONSOLE, duration_h=360,
            events=[SimEvent(at_h=72, action="inject-gray")],
        ),
    ),
]

# --- Explain-mode entries --------------------------------------------------

EXPLAINS = [
    Explain(
        id="min-stages",
        title="Pipeline throughput",
        equation="throughput = min(stage rates);  the argmin is the bottleneck",
        inputs=["stage rates", "bottleneck", "throughput", "backlog"],
        explanation=L(
            novice=(
                "A chain of stages moves as fast as its slowest link, "
                "no matter how fast the others are. Money spent "
                "anywhere except the slowest stage buys nothing — and "
                "money spent there buys a new slowest stage. Every "
                "pipeline conversation is secretly about where the "
                "min() lives."
            ),
            standard=(
                "min() over the four stage rates, with the GPU toggle "
                "multiplying one term ×6 (the labeled claim). Backlog "
                "accumulates where inflow exceeds a stage's rate — "
                "always immediately upstream of the constraint — and "
                "the fix-stage event demonstrates constraint "
                "relocation, the theory-of-constraints classic."
            ),
            expert=(
                "X = min(μᵢ); Q piles at argmin; fixes relocate the "
                "argmin. Goldratt, in four dict entries."
            ),
        ),
    ),
    Explain(
        id="littles-law",
        title="Little's law & freshness",
        equation="in-flight data = throughput × lag;  lag = backlog ÷ throughput",
        inputs=["backlog", "throughput", "freshness lag"],
        explanation=L(
            novice=(
                "How old is the data coming out of the pipeline? "
                "Divide what's waiting inside by how fast it moves. "
                "A backlog of 120 units through a pipe doing 6 per "
                "hour means today's output entered twenty hours ago "
                "— and every hour the backlog grows, the answer gets "
                "worse."
            ),
            standard=(
                "Little's law rearranged into the freshness gauge: "
                "L = λW, so W = Q/X. When arrival exceeds the "
                "constraint the lag is unbounded — the 'stale data, "
                "confident model' failure, which produces no error "
                "message anywhere. Spec 06 lists this equation as "
                "required explain-mode content."
            ),
            expert=(
                "W = Q/X (L=λW). λ>μ ⇒ W→∞ silently. The most "
                "important gauge with no alarm attached."
            ),
        ),
    ),
    Explain(
        id="kv-sessions",
        title="Session capacity & the KV offload",
        equation="sessions = base × (offload ? 4 : 1);  token latency × (1 + tax)",
        inputs=["GPU memory", "offload toggle", "sessions", "token latency"],
        explanation=L(
            novice=(
                "Each long AI conversation keeps working memory that "
                "normally must sit in scarce GPU memory. Spilling it "
                "to fast shared storage frees that memory — about "
                "four times the conversations fit — and each word "
                "pays a small toll for the longer trip. Whether that "
                "trade wins depends on what you sell: seats, or "
                "milliseconds."
            ),
            standard=(
                "The KV-cache offload arithmetic: base ~40 GPU-"
                "resident long-context sessions, ×4 with spill to "
                "shared storage (CMX-class), +12% per-token tax when "
                "running beyond the resident set. Kept deliberately "
                "simple per spec — two bars and a latency readout. "
                "The spilled bytes are PhysicsStorage's fast tier, "
                "which is why the two apps cross-reference."
            ),
            expert=(
                "40 → 160 sessions, +12%/token past resident. "
                "Seats-vs-latency; the bytes land on Lightning."
            ),
        ),
    ),
    Explain(
        id="scored-detection",
        title="Scoring the detector",
        equation="precision = TP/flags;  recall = found/planted;  MTTD = mean(detect − onset)",
        inputs=["ground truth", "k", "flags", "precision", "recall", "MTTD"],
        explanation=L(
            novice=(
                "Most monitoring tuning is vibes, because nobody "
                "knows what the truth was. Here the truth is planted "
                "on purpose, so the knob earns three honest numbers: "
                "what fraction of alarms were real, what fraction of "
                "real problems were found, and how long finding "
                "took. Watch all three move together as you turn one "
                "knob — that is why tuning is hard."
            ),
            standard=(
                "The console's advantage over reality: injected "
                "issues at known times make P/R/MTTD computable. "
                "Signal grows ~1.2σ/day per issue; noise beats low k "
                "on a fixed cadence. One knob, three coupled scores "
                "— the same ROC trade as PhysicsResilience's "
                "sensitivity slider, and the spec's instruction to "
                "note the rhyme is hereby followed."
            ),
            expert=(
                "GT ⇒ P/R/MTTD computable; one k, three coupled "
                "curves. Same knob as the resilience app. Rhyme "
                "noted, as instructed."
            ),
        ),
    ),
    Explain(
        id="forecast-lag",
        title="Forecast lag",
        equation="days-to-full = (100 − fill) ÷ slope(last 168 h);  lag = the window",
        inputs=["fill history", "window", "slope", "forecast", "error"],
        explanation=L(
            novice=(
                "The countdown to full divides the space left by how "
                "fast it's filling — measured over the last week. "
                "That week is both the forecast's wisdom and its "
                "flaw: change the fill rate today and the forecast "
                "stays wrong until a week of new evidence displaces "
                "the old. Forecasts don't lie; they just answer "
                "last week's question."
            ),
            standard=(
                "Linear fit over a 168 h rolling window: convergent "
                "on steady slopes, confidently wrong for ~a window "
                "after any slope change (the demand-change event; "
                "the forecast-error gauge decays as the window "
                "refills). The actionable output is the expansion "
                "decision — the days-to-full scenario runs both "
                "branches, outage and averted."
            ),
            expert=(
                "d2f = headroom/slope₁₆₈ₕ; error ≈ f(window ∩ "
                "regime change). Value = outages converted to POs."
            ),
        ),
    ),
]
