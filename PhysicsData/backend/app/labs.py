"""Graded labs for the data & observability simulator (docs/LAB_PATTERN.md).

A guided scenario sets the dials and tells you what to watch. A lab states a
goal and leaves the dials to you: build a Scenario with the ordinary controls,
the engine runs it, and ``grade_scenario`` scores the trace.

Pure module, same rule as ``engine.py`` and ``validation.py``: no FastAPI, no
IO, no clock, no randomness (AST-checked in ``tests/test_labs.py``). ``main.py``
is the only caller that touches HTTP, so a static-hosting build grades in the
browser with the same code and the same data.

What is this app's own; everything else is ``twinkit.labs``:

* ``measure()`` turns one run into named numbers. Each lab has a delivered-work
  number that is a rate over the whole run and is zero for an idle system:
  ``meanThroughputTbh`` (data through the pipeline), ``diagnosedIssuePct`` (the
  share of the run's issue-hours the detector had under diagnosis) and
  ``dataLandedPctDay`` (how fast the array actually absorbed data; a full array
  absorbs nothing). All three are illustrative proxies and are labeled so.
* ``LABS`` holds three labs of rising difficulty, every criterion citing the
  Explain entry (``presets.EXPLAINS``) and the equation it tests.
* ``REFERENCE_SOLUTIONS`` / ``GAMING_ATTEMPTS`` hold a scenario that passes
  each lab and the cheap tricks that must not. They stay server-side: the API
  serves ``LABS`` only.
"""

from __future__ import annotations

from twinkit.labs import Criterion, Lab, LabGoal, LabResult, Objective, grade

from .engine import simulate
from .leveling import L
from .models import (
    DataConfig,
    Scenario,
    SimEvent,
    SimState,
    Summary,
    Validation,
    Workload,
)
from .presets import CONSOLE, PIPELINE_CPU, PIPELINE_GPU
from .validation import validate

# The equations, exactly as the Explain entries display them.
EQ_MIN = "throughput = min(stage rates);  the argmin is the bottleneck"
EQ_LITTLE = "in-flight data = throughput × lag;  lag = backlog ÷ throughput"
EQ_KV = "sessions = base × (offload ? 4 : 1);  token latency × (1 + tax)"
EQ_SCORED = "precision = TP/flags;  recall = found/planted;  MTTD = mean(detect − onset)"
EQ_FORECAST = "days-to-full = (100 − fill) ÷ slope(last 168 h);  lag = the window"

#: The console lab plants three issues; the share below is measured against it.
PLANTED = 3
#: "Never planted" marker for ``lastPlantH`` (beyond any allowed run length).
NEVER = 9999.0


# --- Measurement ----------------------------------------------------------

def measure(
    scenario: Scenario,
    trace: list[SimState],
    summary: Summary,
    validations: list[Validation],
) -> dict[str, float]:
    """One run as named numbers. Keys are the wire names criteria refer to."""
    events = sorted(scenario.events, key=lambda e: e.at_h)
    ei = 0
    wl = scenario.workload
    min_gpu_demand = wl.gpu_read_demand_tbh
    min_long_context = wl.inference_sessions_demand * wl.long_context_pct / 100.0
    for s in trace:
        # Replay the workload dial exactly as the engine applied it.
        while ei < len(events) and events[ei].at_h <= s.t_h:
            ev = events[ei]
            ei += 1
            if ev.action == "set-workload" and ev.workload is not None:
                wl = ev.workload
        min_gpu_demand = min(min_gpu_demand, wl.gpu_read_demand_tbh)
        min_long_context = min(
            min_long_context,
            wl.inference_sessions_demand * wl.long_context_pct / 100.0,
        )

    n = len(trace)
    last = trace[-1]
    days = max(last.t_h / 24.0, 1e-9)
    fills = [s.array_fill_pct for s in trace]
    steps = list(zip(fills, fills[1:]))
    landed = sum(b - a for a, b in steps if b > a)
    expansions = sum(1 for a, b in steps if b < a - 1.0)
    last_plant = next((s.t_h for s in trace if s.issues_active >= PLANTED), NEVER)

    return {
        "durationH": float(last.t_h),
        # Pipeline.
        "meanThroughputTbh": round(sum(s.throughput_tbh for s in trace) / n, 2),
        "meanGpuIdlePct": round(sum(s.gpu_idle_due_to_data_pct for s in trace) / n, 1),
        "peakFreshnessLagH": round(max(s.freshness_lag_h for s in trace), 1),
        "meanProvisionedTbh": round(
            sum(sum(s.stage_rates_tbh.values()) for s in trace) / n, 1
        ),
        "meanSessionsActive": round(sum(s.sessions_active for s in trace) / n, 1),
        "meanTokenTaxPct": round(sum(s.token_latency_tax_pct for s in trace) / n, 1),
        "minGpuDemandTbh": round(min_gpu_demand, 1),
        "minLongContextSessions": round(min_long_context, 1),
        # Console: the detector.
        "issuesPlanted": float(last.issues_active),
        "issuesCaught": float(last.issues_detected),
        "lastPlantH": float(last_plant),
        "diagnosedIssuePct": round(
            100.0 * sum(s.issues_detected for s in trace) / (PLANTED * n), 1
        ),
        "precisionPct": float(last.precision_pct),
        "recallPct": float(last.recall_pct),
        "mttdH": float(last.mttd_h),
        "falsePositives": float(last.false_positives_cum),
        # Console: the forecast.
        "peakFillPct": round(max(fills), 2),
        "meanFillPct": round(sum(fills) / n, 1),
        "dataLandedPctDay": round(landed / days, 2),
        "expansions": float(expansions),
        "validationErrors": float(sum(1 for v in validations if v.level == "error")),
    }


# --- Criteria shared between labs ------------------------------------------

def _full_run(hours: int, explain_id: str, equation: str, reason: str,
              reason_novice: str, reason_expert: str) -> Criterion:
    return Criterion(
        id="full-run", label=f"Run lasts at least {hours} h",
        metric="durationH", op=">=", threshold=hours, unit="h",
        explain_id=explain_id, equation=equation,
        why=L(standard=reason, novice=reason_novice, expert=reason_expert),
    )


# --- Lab 1: tune the detector to a service level ---------------------------

_DETECTOR_EVENTS = [
    SimEvent(at_h=48, action="inject-capacity"),
    SimEvent(at_h=120, action="inject-gray"),
    SimEvent(at_h=240, action="inject-fan-drift"),
]
_DETECTOR_START = Scenario(config=CONSOLE, duration_h=480, events=_DETECTOR_EVENTS)

QUIET_AND_QUICK = Lab(
    id="quiet-and-quick",
    title="A detector that is quiet and quick",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "Three issues are planted at known hours. Tune the anomaly "
                "detector so that at least 60% of its flags are real, every "
                "planted issue is found, and the mean time to detect stays at "
                "or under 100 h. Then make detection as fast as the precision "
                "floor allows."
            ),
            novice=(
                "The simulator hides three real problems in the fleet at "
                "hours 48, 120 and 240: an array filling too fast, a network "
                "link quietly losing traffic, and a fan drifting upward. The "
                "detector raises a flag when a measurement strays far enough "
                "from normal, and the 'Anomaly k' slider sets how far is far "
                "enough. Your job is to set it so that at least 60% of the "
                "flags are real problems (that share is called precision), "
                "all three problems are found, and finding one takes 100 "
                "hours or less on average. After that, make finding as fast "
                "as you can without breaking the 60% rule."
            ),
            expert=(
                "GT at 48/120/240 h. Precision ≥ 60%, recall 100%, MTTD ≤ "
                "100 h; then minimize MTTD."
            ),
        ),
        constraints=[
            L(standard="All three issues planted, the last one by hour 240.",
              novice="Keep all three planted problems in the run, and the last of them must start by hour 240. Removing a problem, or planting it near the end, makes the test easier than the one this lab sets.",
              expert="3 issues, last onset ≤ 240 h."),
            L(standard="Precision at least 60% and recall 100% at the end of the run.",
              novice="At the end of the run, at least 60 of every 100 flags must have been real problems (precision), and every planted problem must have been flagged (recall 100%).",
              expert="P ≥ 60%, R = 100% at t_end."),
            L(standard="Mean time to detect no more than 100 h, over a run of at least 480 h.",
              novice="Averaged over the three problems, the time from a problem starting to the detector flagging it must be 100 hours or less. The run has to last the full 480 hours, because false alarms keep arriving for as long as the detector runs.",
              expert="MTTD ≤ 100 h; run ≥ 480 h."),
        ],
        delivered_work=L(
            standard=(
                "At least 40% of the run's issue-hours under diagnosis: the "
                "count of detected issues, averaged over every hour and "
                "divided by the three planted. Illustrative."
            ),
            novice=(
                "The detector has to be doing its job for a good part of the "
                "run. Each hour we count how many of the three problems have "
                "already been found, then average that over the whole run; "
                "the result must be at least 40% of three. A run with nothing "
                "planted scores zero here, so an empty fleet cannot pass. "
                "This is a simple stand-in for useful monitoring, not an "
                "industry measure."
            ),
            expert="mean(issues_detected)/3 ≥ 40% over all ticks. Illustrative proxy.",
        ),
    ),
    criteria=[
        Criterion(
            id="work", label="At least 40% of issue-hours under diagnosis",
            metric="diagnosedIssuePct", op=">=", threshold=40, unit="%",
            weight=2.0, guards_work=True,
            explain_id="scored-detection", equation=EQ_SCORED,
            why=L(
                standard=(
                    "The work of a detector is issues under diagnosis. This "
                    "line averages found ÷ planted over every hour of the "
                    "run, so nothing planted, or everything planted late, "
                    "earns little. 40% is the floor. The proxy is "
                    "illustrative."
                ),
                novice=(
                    "A detector earns its keep by having real problems "
                    "found and known about. Each hour, this line looks at "
                    "how many of the three planted problems have been found "
                    "so far, and it averages that over the whole run. If "
                    "nothing is planted the answer is zero, and if the "
                    "problems are planted very late there is little time "
                    "left to have found them. The floor is 40%. It is a "
                    "simple stand-in, not a real monitoring benchmark."
                ),
                expert="mean over ticks of found/planted, planted = 3; floor 40%. Illustrative.",
            ),
        ),
        Criterion(
            id="planted", label="All three issues planted",
            metric="issuesPlanted", op=">=", threshold=PLANTED, unit="issues",
            explain_id="scored-detection", equation=EQ_SCORED,
            why=L(
                standard=(
                    "Recall is found ÷ planted. With fewer issues planted "
                    "the denominator shrinks and the score flatters the "
                    "knob, so the ground truth is part of the grade."
                ),
                novice=(
                    "Recall means: of the problems that were really there, "
                    "how many did the detector find? If you remove a planted "
                    "problem there is less to find and the score looks "
                    "better without the detector being any better. So the "
                    "lab checks that all three problems are still in the run."
                ),
                expert="recall's denominator is fixed at 3.",
            ),
        ),
        Criterion(
            id="planted-in-time", label="Last issue planted by hour 240",
            metric="lastPlantH", op="<=", threshold=240, unit="h",
            explain_id="scored-detection", equation=EQ_SCORED,
            why=L(
                standard=(
                    "An issue's signal grows about 1.2σ per day, so "
                    "detection needs k ÷ 1.2 days after onset. An issue "
                    "planted near the end of the run is never given that "
                    "time, and the false positives before it go unanswered."
                ),
                novice=(
                    "A planted problem does not show up at once. Its "
                    "measurement drifts away from normal a little more each "
                    "day, and the detector flags it only when the drift "
                    "passes the k setting. That takes days. A problem "
                    "planted close to the end of the run never gets those "
                    "days, so the lab requires the last one to start by "
                    "hour 240."
                ),
                expert="detect delay ≈ 20k h; onsets must leave room for it.",
            ),
        ),
        Criterion(
            id="precision", label="Precision at least 60%",
            metric="precisionPct", op=">=", threshold=60, unit="%", weight=2.0,
            explain_id="scored-detection", equation=EQ_SCORED,
            why=L(
                standard=(
                    "Precision is TP ÷ flags. The three true positives are "
                    "fixed, so precision is set by how many noise excursions "
                    "cross the threshold, and in this model one does every "
                    "48 × k hours. A higher k means fewer false flags over "
                    "the same 480 h."
                ),
                novice=(
                    "Precision is the share of flags that were real. The "
                    "three real problems give three real flags whatever you "
                    "do, so precision depends on how many false alarms join "
                    "them. Ordinary measurements wobble, and a low k treats "
                    "the wobble as a problem. In this simulator a false "
                    "alarm arrives every 48 × k hours, so raising k spaces "
                    "them out and fewer fit into the 480-hour run."
                ),
                expert="FP cadence 48k h ⇒ FP = ⌊480 ÷ ⌊48k⌋⌋; P = 3 ÷ (3 + FP).",
            ),
        ),
        Criterion(
            id="recall", label="Every planted issue found",
            metric="recallPct", op=">=", threshold=100, unit="%",
            explain_id="scored-detection", equation=EQ_SCORED,
            why=L(
                standard=(
                    "Recall is found ÷ planted at the end of the run. A slow "
                    "issue that is never flagged is the failure a quiet feed "
                    "hides."
                ),
                novice=(
                    "By the end of the run the detector must have flagged "
                    "all three planted problems. A detector set so high that "
                    "it stays quiet looks calm, but a quiet screen and a "
                    "healthy fleet are different things."
                ),
                expert="found = planted at t_end.",
            ),
        ),
        Criterion(
            id="mttd", label="Mean time to detect no more than 100 h",
            metric="mttdH", op="<=", threshold=100, unit="h", weight=2.0,
            explain_id="scored-detection", equation=EQ_SCORED,
            why=L(
                standard=(
                    "MTTD is mean(detect − onset). The signal must climb "
                    "past k at about 1.2σ per day, so each step of k costs "
                    "roughly 20 h of detection time. The same knob that "
                    "buys precision spends MTTD."
                ),
                novice=(
                    "MTTD is the average wait between a problem starting "
                    "and the detector flagging it. A planted problem drifts "
                    "about 1.2 units further from normal each day, and it "
                    "is flagged when the drift passes k. So each extra "
                    "point of k adds roughly 20 hours of waiting. The "
                    "slider that reduces false alarms also makes real "
                    "alarms later, and that is the whole difficulty of "
                    "tuning."
                ),
                expert="delay = ⌊20k⌋ + 1 h per issue; MTTD ≤ 100 h ⇒ k < 5.",
            ),
        ),
        _full_run(
            480, "scored-detection", EQ_SCORED,
            "False positives accrue for as long as the detector runs. A short "
            "run ends before the noise has been given its chances, and "
            "precision reads better than the knob deserves.",
            "False alarms keep arriving for as long as the detector is "
            "watching. If the run were cut short, fewer of them would have "
            "arrived and the detector would look more trustworthy than it is. "
            "So the run has to last the full 480 hours the lab starts with.",
            "FP count ∝ run length; 480 h fixes the exposure.",
        ),
    ],
    objective=Objective(
        label="Mean time to detect", metric="mttdH", direction="minimize",
        par=71, worst=100, unit="h",
        explain_id="scored-detection", equation=EQ_SCORED,
    ),
    hints=[
        L(standard="Run the start and read the scoreboard: recall is already 100%, MTTD is fine, and precision is the line that fails. Count the benign flags in the event log.",
          novice="Run the lab as it starts and look at the three scores on the right. Recall is already 100% and the detection time is fine. Precision is what fails. Now read the event log under the picture and count the flags marked as benign noise: those are the false alarms dragging precision down.",
          expert="Start: R = 100%, P = 50% with 3 FPs. Precision is the failing line."),
        L(standard="Raising k removes false flags in steps, not smoothly: a false flag arrives every 48 × k hours, and what matters is how many fit into 480 h. Meanwhile every step of k adds about 20 h to MTTD.",
          novice="Move the k slider up one notch at a time and re-run. Precision does not rise smoothly. It jumps only when one fewer false alarm fits into the 480 hours, because a false alarm arrives every 48 × k hours. The detection time, though, gets about 20 hours worse with every full point of k. So some notches cost you time and buy nothing.",
          expert="FP count is a step function of k; MTTD is linear in k."),
        L(standard="k = 3.5 is the first setting with only two false flags in 480 h (one every 168 h), which is 60% precision at an MTTD of 71 h. k = 4 to 5 buys no precision and costs 10 h per half step.",
          novice="Set k to 3.5. A false alarm then arrives every 168 hours, so only two fit into the run: three real flags out of five is exactly 60%. The average detection time is 71 hours. Going up to 4, 4.5 or 5 still leaves two false alarms, so precision stays at 60% while each half notch adds 10 hours of waiting.",
          expert="k = 3.5: FP = 2, P = 60%, MTTD = 71 h. The plateau to k = 5 is pure cost."),
    ],
    start=_DETECTOR_START.model_dump(by_alias=True),
)


# --- Lab 2: feed the GPUs for the least capacity ---------------------------

_HUNGRY = Workload(
    raw_arrival_tbh=8, gpu_read_demand_tbh=25,
    inference_sessions_demand=300, long_context_pct=60,
)
_FEED_START = Scenario(config=PIPELINE_CPU, workload=_HUNGRY, duration_h=240)

FEED_THE_GPUS = Lab(
    id="feed-the-gpus",
    title="Feed the GPUs for the least capacity",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "A training cluster wants 25 TB/h and 180 long-context "
                "sessions. Get mean GPU idle due to data to 2% or less with "
                "fresh data, serve at least 150 sessions, and do it with the "
                "least total stage capacity."
            ),
            novice=(
                "A group of GPUs wants to read 25 TB of prepared data every "
                "hour, and 180 long AI conversations want serving at the "
                "same time. Data passes through four stages in a row "
                "(ingest, process, index, serve), and the GPUs sit idle "
                "whenever the pipeline cannot keep up. Your job is to get "
                "the time the GPUs spend waiting for data down to 2% or "
                "less, keep the data no more than an hour old, serve at "
                "least 150 of the conversations, and then do all of that "
                "while buying as little stage capacity as you can."
            ),
            expert=(
                "Demand 25 TB/h, 180 long-context sessions. Idle ≤ 2%, lag ≤ "
                "1 h, sessions ≥ 150; minimize Σ stage rates."
            ),
        ),
        constraints=[
            L(standard="GPU read demand never below 25 TB/h, and long-context demand never below 180 sessions.",
              novice="Leave the GPU read demand at 25 TB/h or more, and the long-context sessions at 300 or more (60% of 300 is the 180 long conversations). Asking for less would make the GPUs easy to satisfy, and that is a different problem.",
              expert="min demand ≥ 25 TB/h; min long-context ≥ 180."),
            L(standard="Mean GPU idle due to data no more than 2%, and peak freshness lag no more than 1 h.",
              novice="Averaged over the run, the GPUs may wait for data no more than 2% of the time. The data they read must never be more than 1 hour old, which means no queue may build up anywhere in the pipeline.",
              expert="mean idle ≤ 2%; max W ≤ 1 h."),
            L(standard="At least 150 long-context sessions active on average, over a run of at least 240 h.",
              novice="On average at least 150 of the long conversations must be running, and the run has to last the full 240 hours so that a slowly growing queue has time to show itself.",
              expert="mean sessions ≥ 150; run ≥ 240 h."),
        ],
        delivered_work=L(
            standard="At least 20 TB/h of data through the whole pipeline, averaged over the run. Illustrative.",
            novice="The pipeline itself must deliver at least 20 TB of finished data per hour, averaged over the whole run. A pipeline with nothing arriving delivers nothing, so switching the sources off cannot pass. This is a simple stand-in for useful work, not a benchmark.",
            expert="mean throughput ≥ 20 TB/h over all ticks. Illustrative proxy.",
        ),
    ),
    criteria=[
        Criterion(
            id="work", label="Pipeline throughput at least 20 TB/h",
            metric="meanThroughputTbh", op=">=", threshold=20, unit="TB/h",
            weight=2.0, guards_work=True,
            explain_id="min-stages", equation=EQ_MIN,
            why=L(
                standard=(
                    "Throughput is min(stage rates), and it can never exceed "
                    "what arrives. Averaged over every hour of the run, 20 "
                    "TB/h is the floor: the serve stage can lend the GPUs "
                    "about 5 TB/h beyond fresh throughput and no more. The "
                    "proxy is illustrative."
                ),
                novice=(
                    "The pipeline moves only as fast as its slowest stage, "
                    "and never faster than raw data arrives at the front. "
                    "This line averages the finished data per hour over the "
                    "whole run and needs at least 20 TB/h. The reason for "
                    "20: the serve stage can hand the GPUs about 5 TB/h "
                    "more than is freshly arriving, and no more, so 25 for "
                    "the GPUs needs 20 coming through. It is a simple "
                    "stand-in for useful work."
                ),
                expert="X = min(λ, μᵢ) averaged over ticks; served ≤ X + 5 ⇒ X ≥ 20.",
            ),
        ),
        Criterion(
            id="gpu-fed", label="Mean GPU idle due to data no more than 2%",
            metric="meanGpuIdlePct", op="<=", threshold=2, unit="%", weight=2.0,
            explain_id="min-stages", equation=EQ_MIN,
            why=L(
                standard=(
                    "The GPUs are served min(demand, serve rate, throughput "
                    "+ 5). Whichever term is smallest is the constraint, and "
                    "fixing it hands the job to the next one: process, then "
                    "the sources, then index, then serve."
                ),
                novice=(
                    "What the GPUs receive is the smallest of three "
                    "numbers: what they ask for, what the serve stage can "
                    "deliver, and what the pipeline is producing (plus a "
                    "little from the serve stage's store). Whichever number "
                    "is smallest is holding the GPUs back. When you fix it, "
                    "the next-smallest takes over. Expect to fix more than "
                    "one thing, and check the 'bottleneck' readout after "
                    "every change."
                ),
                expert="served = min(D, μ_serve, X + 5); the argmin relocates on every fix.",
            ),
        ),
        Criterion(
            id="fresh", label="Peak freshness lag no more than 1 h",
            metric="peakFreshnessLagH", op="<=", threshold=1, unit="h",
            explain_id="littles-law", equation=EQ_LITTLE,
            why=L(
                standard=(
                    "Lag is backlog ÷ throughput. Any stage slower than what "
                    "arrives at it grows a backlog every hour, and the lag "
                    "grows with it. Raising arrival past the slowest stage "
                    "feeds the queue, not the GPUs."
                ),
                novice=(
                    "How old is the data coming out? Divide what is waiting "
                    "inside the pipeline by how fast it moves. If more data "
                    "arrives each hour than the slowest stage can handle, "
                    "the extra waits in a queue, the queue grows every "
                    "hour, and the data gets older and older. Turning the "
                    "arrival slider up past your slowest stage fills the "
                    "queue and does nothing for the GPUs."
                ),
                expert="W = Q/X; λ > min μ ⇒ Q grows linearly and W with it.",
            ),
        ),
        Criterion(
            id="sessions", label="At least 150 long-context sessions active",
            metric="meanSessionsActive", op=">=", threshold=150, unit="sessions",
            explain_id="kv-sessions", equation=EQ_KV,
            why=L(
                standard=(
                    "GPU memory holds about 40 long-context sessions; "
                    "spilling the KV cache to shared storage holds 160 at a "
                    "12% per-token tax. 150 cannot be reached without the "
                    "offload, and the tax is the accepted price."
                ),
                novice=(
                    "Each long conversation keeps a working memory (the KV "
                    "cache), and GPU memory has room for only about 40 of "
                    "them. Letting that memory spill over to fast shared "
                    "storage makes room for about 160, and each word of "
                    "reply then arrives about 12% slower. There is no way "
                    "to 150 sessions without turning the offload on, so "
                    "here the small delay is the price you agree to pay."
                ),
                expert="40 resident vs 160 spilled, +12%/token. 150 requires the spill.",
            ),
        ),
        Criterion(
            id="demand-held", label="GPU read demand never below 25 TB/h",
            metric="minGpuDemandTbh", op=">=", threshold=25, unit="TB/h",
            explain_id="min-stages", equation=EQ_MIN,
            why=L(
                standard=(
                    "Idle is 1 − served ÷ demand. Lowering the demand "
                    "shrinks the idle gauge without feeding a single GPU, so "
                    "the demand is graded too."
                ),
                novice=(
                    "The idle gauge compares what the GPUs get with what "
                    "they ask for. If you lower what they ask for, the "
                    "gauge looks better and the GPUs are no better fed. So "
                    "the lab checks that the GPU read demand stays at 25 "
                    "TB/h or more for the whole run."
                ),
                expert="idle = 1 − served/D; D is fixed at ≥ 25.",
            ),
        ),
        Criterion(
            id="sessions-held", label="Long-context demand never below 180 sessions",
            metric="minLongContextSessions", op=">=", threshold=180, unit="sessions",
            explain_id="kv-sessions", equation=EQ_KV,
            why=L(
                standard=(
                    "Active sessions are min(long-context demand, capacity). "
                    "The demand side is part of the lab's setting, measured "
                    "from the workload over the whole run."
                ),
                novice=(
                    "The number of conversations running is the smaller of "
                    "how many want to run and how many fit. The lab sets "
                    "how many want to run (60% of 300, which is 180), and "
                    "it checks that this stayed true for the whole run."
                ),
                expert="active = min(demand, capacity); demand ≥ 180 throughout.",
            ),
        ),
        _full_run(
            240, "littles-law", EQ_LITTLE,
            "A backlog that grows 1 TB/h looks harmless for a day. Ten days "
            "is long enough for any stage that is even slightly short to "
            "show up in the lag.",
            "A queue that grows by a little each hour looks harmless at "
            "first. Over the ten days this lab runs, even a stage that is "
            "only slightly too slow builds a queue big enough to make the "
            "data stale, so the run has to last the full 240 hours.",
            "Long enough for a 1 TB/h shortfall to breach W ≤ 1 h.",
        ),
    ],
    objective=Objective(
        label="Total stage capacity", metric="meanProvisionedTbh",
        direction="minimize", par=85, worst=150, unit="TB/h",
        explain_id="min-stages", equation=EQ_MIN,
    ),
    hints=[
        L(standard="Run the start and read the bottleneck readout, then turn on GPU processing and read it again. Throughput will stop at 8 TB/h: compare that with the raw arrival slider.",
          novice="Run the lab as it starts and find the 'bottleneck' readout: it names the slowest stage. Turn on GPU processing, which makes that stage six times faster, and run again. The throughput now stops at 8 TB/h. Look at the 'Raw arrival' slider on the right: a pipeline cannot deliver more than it is given.",
          expert="After ×6 on process the binding term is λ = 8, not a stage."),
        L(standard="Every fix relocates the constraint: process, then the sources, then index, then serve against the 25 TB/h demand. Sessions are a separate constraint with its own switch. Capacity above the constraint buys nothing and counts against the objective.",
          novice="Each time you fix the slowest thing, something else becomes the slowest: first the process stage, then the raw arrival, then the index stage, then the serve stage, which has to cover the full 25 TB/h the GPUs ask for. The conversations are a separate problem with their own switch (KV-cache offload). Any stage capacity above what the pipeline needs does nothing, and the objective counts it against you.",
          expert="argmin walk: process → λ → index → serve vs D. KV is orthogonal. Slack is pure cost."),
        L(standard="Arrival 20 with ingest, process and index all at 20 and serve at 25 gives 20 TB/h, no backlog, no idle, for 85 TB/h of capacity. GPU processing is not needed once process is sized to 20; KV offload on covers the sessions.",
          novice="Set raw arrival to 20, set ingest, process and index to 20 each, and set serve to 25. That gives 20 TB/h through the pipeline with no queue, and the serve stage covers the GPUs' 25. The total capacity is 85 TB/h. You do not need GPU processing once the process stage is set to 20, because its ×6 would be capacity you do not use. Turn KV-cache offload on for the conversations.",
          expert="λ = μ_ingest = μ_process = μ_index = 20, μ_serve = 25, KV on: Σ = 85."),
    ],
    start=_FEED_START.model_dump(by_alias=True),
)


# --- Lab 3: buy capacity on time, not early --------------------------------

_FORECAST_EVENTS = [
    SimEvent(at_h=48, action="inject-capacity"),
    SimEvent(at_h=240, action="demand-change"),
]
_FORECAST_START = Scenario(config=CONSOLE, duration_h=600, events=_FORECAST_EVENTS)


def _forecast_run(*expand_at: int, events: list[SimEvent] | None = None,
                  duration_h: int = 600) -> Scenario:
    base = list(_FORECAST_EVENTS if events is None else events)
    return Scenario(
        config=CONSOLE, duration_h=duration_h,
        events=base + [SimEvent(at_h=h, action="expand-capacity") for h in expand_at],
    )


LAST_WEEKS_QUESTION = Lab(
    id="last-weeks-question",
    title="The forecast answers last week's question",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "An array starts filling fast at hour 48 and the fill rate "
                "doubles at hour 240. Keep the array at or under 95% for 600 "
                "h with at most two expansions, and keep the capacity you "
                "bought as full as you can."
            ),
            novice=(
                "A storage array starts filling quickly at hour 48, and at "
                "hour 240 the filling gets twice as fast. The console shows "
                "a 'days to full' countdown, worked out from the last week "
                "of history. You may expand the array twice (each expansion "
                "is a purchase). Your job is to keep the array from ever "
                "going above 95% full for the whole 600 hours, and to buy "
                "as late as is safe, because capacity bought early sits "
                "empty. Be careful with the countdown just after hour 240: "
                "it is still describing the week before the change."
            ),
            expert=(
                "2.5%/day from 48 h, ×2 at 240 h. max fill ≤ 95% over 600 h, "
                "≤ 2 expansions; maximize mean fill."
            ),
        ),
        constraints=[
            L(standard="Peak fill never above 95%.",
              novice="The array must never be more than 95% full at any hour of the run. At 100% it stops accepting data, and that is an outage.",
              expert="max fill ≤ 95%."),
            L(standard="No more than two capacity expansions.",
              novice="You may press 'Expand capacity' at most twice. Each press is a purchase order, and buying again and again is not planning.",
              expert="≤ 2 expansions."),
            L(standard="The run lasts at least 600 h.",
              novice="The run has to last the full 600 hours, which is long enough that one expansion is not enough.",
              expert="run ≥ 600 h."),
        ],
        delivered_work=L(
            standard="At least 3.7% of the array landed per day, averaged over the run. A full array lands nothing. Illustrative.",
            novice="The array's work is taking in data. Averaged over the whole run it must take in at least 3.7% of its size per day, which is what the planted growth and its doubling add up to. An array that reaches 100% stops taking data in, so an outage fails this line too, and so does removing the growth. This is a simple stand-in for useful work.",
            expert="Σ positive Δfill ÷ days ≥ 3.7 %/day. Illustrative proxy.",
        ),
    ),
    criteria=[
        Criterion(
            id="work", label="Data landed at least 3.7% of the array per day",
            metric="dataLandedPctDay", op=">=", threshold=3.7, unit="%/day",
            weight=2.0, guards_work=True,
            explain_id="forecast-lag", equation=EQ_FORECAST,
            why=L(
                standard=(
                    "The slope in the forecast is data landing. This line "
                    "sums every hour's rise in fill and divides by the days "
                    "run: 2.5%/day from hour 48 and 5%/day from hour 240 "
                    "come to about 3.8. Without the doubling it is 2.3, and "
                    "a full array lands nothing for the rest of the run. "
                    "The proxy is illustrative."
                ),
                novice=(
                    "The work of a storage array is accepting data. This "
                    "line adds up how much the array filled each hour and "
                    "divides by the number of days. With the planted growth "
                    "and its doubling, that comes to about 3.8% of the "
                    "array per day, and the floor is 3.7. If you remove the "
                    "doubling it falls to 2.3. If the array reaches 100% it "
                    "accepts nothing from then on, and the number falls "
                    "below the floor. It is a simple stand-in for useful "
                    "work."
                ),
                expert="mean slope over the run ≈ 3.8 %/day with both events; 100% fill zeroes it.",
            ),
        ),
        Criterion(
            id="never-full", label="Peak fill no more than 95%",
            metric="peakFillPct", op="<=", threshold=95, unit="%", weight=3.0,
            explain_id="forecast-lag", equation=EQ_FORECAST,
            why=L(
                standard=(
                    "At hour 240 the forecast reads about 9.6 days because "
                    "its 168 h window still holds the old 2.5%/day slope. "
                    "The truth at 5%/day is under 5 days. An expansion "
                    "scheduled from that reading arrives after the array is "
                    "full."
                ),
                novice=(
                    "The countdown divides the space left by how fast the "
                    "array filled over the last week. At hour 240 the "
                    "filling doubles, but the last week is still all "
                    "old, slower filling, so the countdown reads about 9.6 "
                    "days when the truth is under 5. If you plan your "
                    "purchase from that reading, the array is full days "
                    "before the purchase arrives. The countdown catches up "
                    "only as the new, faster hours replace the old ones."
                ),
                expert="d2f(240 h) ≈ 9.6 d vs true < 5 d; error decays over one 168 h window.",
            ),
        ),
        Criterion(
            id="two-purchases", label="No more than two expansions",
            metric="expansions", op="<=", threshold=2, unit="expansions",
            explain_id="forecast-lag", equation=EQ_FORECAST,
            why=L(
                standard=(
                    "Each expansion frees 35 points of fill. At 5%/day that "
                    "is one week of runway, so two purchases cover the run "
                    "only if neither is wasted on an array that was not yet "
                    "close to full."
                ),
                novice=(
                    "Each expansion lowers the fill by 35 points. At the "
                    "doubled rate of 5% per day, that buys one week. Two "
                    "expansions are enough for this run, but only if each "
                    "one is used when the array is nearly full."
                ),
                expert="35 points ÷ 5 %/day = 7 days per expansion; two suffice.",
            ),
        ),
        _full_run(
            600, "forecast-lag", EQ_FORECAST,
            "The run has to outlast the first expansion: at 5%/day the "
            "second 95% arrives a week after the first, and the lab is about "
            "timing both.",
            "The run has to be long enough to need the second purchase. At "
            "the doubled rate the array is nearly full again a week after "
            "the first expansion, and timing both purchases is the point of "
            "the lab.",
            "600 h spans two 35-point cycles at 5 %/day.",
        ),
    ],
    objective=Objective(
        label="Mean fill", metric="meanFillPct", direction="maximize",
        par=71.5, worst=55, unit="%",
        explain_id="forecast-lag", equation=EQ_FORECAST,
    ),
    hints=[
        L(standard="Run the start and scrub to hour 240. Read days-to-full and the forecast-error gauge there, then find the hour the array actually fills.",
          novice="Run the lab as it starts, pause, and drag the timeline to hour 240. Read the 'days to full' number and the forecast-error gauge beside it. Then drag forward to find the hour the array really reaches 100%, and compare that with what the countdown promised.",
          expert="Compare d2f at 240 h with the actual full hour (357 h)."),
        L(standard="For one window after the doubling the forecast reads up to twice the truth. Buying at hour 49 is safe and leaves the capacity empty for weeks; buying when the forecast says to is an outage. Watch the fill itself and halve the forecast until the error gauge settles.",
          novice="For about a week after the doubling, the countdown reads up to twice the real time left. There are two easy mistakes. Buying straight away at hour 49 is safe, but the new space then sits empty for weeks, and the objective counts that against you. Waiting until the countdown says it is time means the array fills first. Watch the fill percentage itself, and treat the countdown as about half of what it says until the error gauge has settled.",
          expert="Error ≤ ×2 for 168 h after the slope change; discount d2f accordingly."),
        L(standard="At 5%/day the array passes 95% near hour 333 and again a week after an expansion. Expanding at about hour 330 and again at about hour 497 keeps the peak under 95% and the mean fill near 71%.",
          novice="At the doubled rate the array reaches 95% at about hour 333. Drag the timeline to about hour 330 and press 'Expand capacity'. The fill drops by 35 points and climbs back to 95% one week later, so drag to about hour 497 and expand again. The peak stays just under 95% and the average fill is about 71%, which is full marks.",
          expert="Expand at ≈ 330 h and ≈ 497 h: peak < 95%, mean ≈ 71.5%."),
    ],
    start=_FORECAST_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [QUIET_AND_QUICK, FEED_THE_GPUS, LAST_WEEKS_QUESTION]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Reference solutions and the tricks that must not work -----------------
# Server-side only: GET /api/labs serves LABS, never these.

def _console(k: float) -> DataConfig:
    return CONSOLE.model_copy(update={"anomaly_k": k})


_FED = DataConfig(
    ingest_tbh=20, process_tbh=20, index_tbh=20, serve_tbh=25, kv_offload=True,
)
_FED_WL = _HUNGRY.model_copy(update={"raw_arrival_tbh": 20})

REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    "quiet-and-quick": Scenario(
        config=_console(3.5), duration_h=480, events=_DETECTOR_EVENTS,
    ),
    "feed-the-gpus": Scenario(config=_FED, workload=_FED_WL, duration_h=240),
    "last-weeks-question": _forecast_run(332, 499),
}

GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "quiet-and-quick": {
        "zero load": Scenario(config=_console(3.5), duration_h=480),
        "touchy detector": Scenario(
            config=_console(1.5), duration_h=480, events=_DETECTOR_EVENTS),
        "deaf detector": Scenario(
            config=_console(6.0), duration_h=480, events=_DETECTOR_EVENTS),
        "plant everything late": Scenario(
            config=_console(3.5), duration_h=480,
            events=[SimEvent(at_h=400, action=a) for a in
                    ("inject-capacity", "inject-gray", "inject-fan-drift")]),
        "short run": Scenario(
            config=_console(3.0), duration_h=200,
            events=[SimEvent(at_h=0, action=a) for a in
                    ("inject-capacity", "inject-gray", "inject-fan-drift")]),
        "one easy issue": Scenario(
            config=_console(5.5), duration_h=480,
            events=[SimEvent(at_h=0, action="inject-gray")]),
    },
    "feed-the-gpus": {
        "zero load": Scenario(
            config=_FED, duration_h=240,
            workload=Workload(raw_arrival_tbh=0, gpu_read_demand_tbh=0,
                              inference_sessions_demand=0)),
        "lower the demand": Scenario(
            config=_FED, duration_h=240,
            workload=_FED_WL.model_copy(update={"gpu_read_demand_tbh": 10})),
        "gpu processing only": Scenario(
            config=PIPELINE_GPU.model_copy(update={"kv_offload": True}),
            workload=_HUNGRY, duration_h=240),
        "flood the sources": Scenario(
            config=_FED, duration_h=240,
            workload=_FED_WL.model_copy(update={"raw_arrival_tbh": 40})),
        "short run": Scenario(
            config=_FED, workload=_FED_WL, duration_h=24),
        "skip the sessions": Scenario(
            config=_FED.model_copy(update={"kv_offload": False}),
            workload=_FED_WL, duration_h=240),
        "idle first, load later": Scenario(
            config=_FED, duration_h=240,
            workload=_HUNGRY.model_copy(update={"raw_arrival_tbh": 0}),
            events=[SimEvent(at_h=200, action="set-workload", workload=_FED_WL)]),
    },
    "last-weeks-question": {
        "zero load": Scenario(config=CONSOLE, duration_h=600),
        "drop the doubling": _forecast_run(400, events=_FORECAST_EVENTS[:1]),
        "trust the forecast": _forecast_run(430, 550),
        "three purchases": _forecast_run(300, 400, 500),
        "short run": _forecast_run(duration_h=300),
    },
}


# --- Grading ----------------------------------------------------------------

def grade_scenario(lab_id: str, scenario: Scenario) -> LabResult:
    """Run the engine on the learner's scenario and grade the trace.

    Pure and deterministic: no state is kept between calls, and the same
    scenario always earns the same result. Raises ``KeyError`` for an
    unknown lab id (``main.py`` turns that into a 404).
    """
    lab = LABS_BY_ID[lab_id]
    trace, _log, summary = simulate(scenario)
    metrics = measure(scenario, trace, summary, validate(scenario))
    return grade(lab, metrics)
