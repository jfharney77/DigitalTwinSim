"""Graded labs for the AI Factory capstone — built to ``docs/LAB_PATTERN.md``
(pilot: ``DellPowerEdgeR760Thermal/backend/app/labs.py``).

A guided scenario sets the dials and tells you what to watch. A lab states a
goal and leaves the dials to you: size the factory with the ordinary controls,
the engine runs it, and ``grade_scenario`` scores the trace.

Pure module, same rule as ``engine.py`` and ``validation.py``: no FastAPI, no
IO, no clock, no randomness (AST-checked in ``tests/test_labs.py``). ``main.py``
is the only caller that touches HTTP, so a static-hosting build runs this same
grading in the browser.

Three things here are this app's own; everything else is ``twinkit.labs``:

* ``measure()`` — turns one run into named numbers. The un-gameable one is
  ``effectiveGpus``: the tokens the run actually kept (net of every rollback),
  divided by what ONE GPU at full rate would have produced over the WHOLE run
  — procurement, install and bring-up hours count as zero. It is a rate, so a
  long run at low load earns nothing extra, and it is normalized by the job's
  per-GPU rate, so inflating that rate earns nothing either. An illustrative
  proxy for useful training, not a benchmark, and labeled so.
* ``LABS`` — three labs of rising difficulty. They are the engine's acceptance
  scenarios turned into problems with a twist: starvation sized for the
  platform's *worst* day, the power wall as a reason to buy *fewer* racks, and
  checkpoint economics where the second lever is storage and the third is the
  megawatt budget. Every criterion cites an Explain entry and its equation.
* ``REFERENCE_SOLUTIONS`` / ``GAMING_ATTEMPTS`` — a scenario that passes each
  lab, and the cheap tricks that must not. They stay server-side: the API
  serves ``LABS`` only.
"""

from __future__ import annotations

from twinkit.labs import Criterion, Lab, LabGoal, LabResult, Objective, grade

from .constants import value as C
from .engine import simulate
from .leveling import L
from .models import (
    ComputeBlock,
    CostBlock,
    DataBlock,
    FacilityBlock,
    FactoryConfig,
    ResilienceBlock,
    Scenario,
    SimEvent,
    SimState,
    Summary,
    TrainingJob,
    Validation,
)
from .presets import EXPLAINS
from .validation import validate

# The equations, exactly as the Explain entries display them — read from the
# entries themselves so a reworded entry can never leave a lab quoting a stale
# equation.
_EQ = {e.id: e.equation for e in EXPLAINS}
EQ_TOKENS = _EQ["tokens-per-s"]
EQ_IDLE = _EQ["idle-data"]
EQ_MW = _EQ["facility-mw"]
EQ_USD = _EQ["usd-per-mtok"]
EQ_CKPT = _EQ["checkpoint"]

LAB_DURATION_H = 720  # every lab is graded over the same 30-day run

# The inputs a learner may not make easier than the stock factory's: the
# workload's appetite, the GPU tier, the failure arithmetic and the prices.
# Sizing (racks, storage, fabric, cooling, budget, checkpoint interval) is the
# learner's to change; these are the world it is sized against.
_STOCK_JOB = TrainingJob()
_STOCK_RES = ResilienceBlock()
_STOCK_COST = CostBlock()
_STOCK_GPU_W = ComputeBlock().gpu_peak_w


def _unfair_inputs(scenario: Scenario) -> int:
    """How many world-inputs were made easier than stock. Zero is fair."""
    job, cfg = scenario.job, scenario.config
    easier = [
        job.tokens_per_gpu_s > _STOCK_JOB.tokens_per_gpu_s,
        job.data_gbps_per_gpu < _STOCK_JOB.data_gbps_per_gpu,
        job.state_gb_per_gpu < _STOCK_JOB.state_gb_per_gpu,
        job.ramp_h < _STOCK_JOB.ramp_h,
        cfg.compute.gpu_peak_w < _STOCK_GPU_W,
        cfg.resilience.gpu_mtbf_h > _STOCK_RES.gpu_mtbf_h,
        cfg.resilience.restart_min < _STOCK_RES.restart_min,
        cfg.costs.usd_per_kwh < _STOCK_COST.usd_per_kwh,
        cfg.costs.capex_musd_per_rack < _STOCK_COST.capex_musd_per_rack,
        cfg.costs.amortization_years > _STOCK_COST.amortization_years,
    ]
    return sum(1 for e in easier if e)


# --- Measurement ----------------------------------------------------------

def measure(
    scenario: Scenario,
    trace: list[SimState],
    summary: Summary,
    validations: list[Validation],
) -> dict[str, float]:
    """One run as named numbers. Keys are the wire names criteria refer to."""
    cfg = scenario.config
    job = scenario.job
    train = [s for s in trace if s.phase == "train"]
    base_pue = C("pue_liquid") if cfg.facility.cooling == "liquid" else C("pue_air")

    # Delivered work: tokens kept ÷ (one GPU's full-rate output over the
    # whole run). Dark hours are in the denominator and earn nothing.
    full_rate_tokens = job.tokens_per_gpu_s * 3600.0 * max(scenario.duration_h, 1)
    effective_gpus = trace[-1].tokens_total_b * 1e9 / full_rate_tokens

    # Tokens rewound by failures: what the counter should have reached this
    # hour minus what it shows.
    rolled_b = 0.0
    for prev, cur in zip(trace, trace[1:]):
        lost = prev.tokens_total_b + cur.tokens_per_s * 3600.0 / 1e9 - cur.tokens_total_b
        if lost > 0.002:
            rolled_b += lost

    half = 0.5 * cfg.data.storage_gbps + 1e-6
    n_train = max(len(train), 1)
    return {
        "durationH": float(trace[-1].t_h),
        "effectiveGpus": round(effective_gpus, 1),
        "tokensTotalB": float(trace[-1].tokens_total_b),
        "peakIdleDataPct": round(max((s.gpu_idle_data_pct for s in train), default=0.0), 1),
        "degradedTrainHours": float(sum(1 for s in train if s.storage_supply_gbps <= half)),
        "warmTrainHours": float(sum(1 for s in train if s.pue >= base_pue + 0.2 - 1e-9)),
        "powerCappedHours": float(summary.power_capped_hours),
        "peakFacilityMw": float(summary.peak_facility_mw),
        "mwBudget": float(cfg.facility.mw_budget),
        "usdPerMtok": float(summary.usd_per_mtok),
        "storageGbps": float(cfg.data.storage_gbps),
        "racks": float(cfg.compute.racks),
        "stateGbPerGpu": float(job.state_gb_per_gpu),
        "meanOverheadPct": round(sum(s.overhead_pct for s in train) / n_train, 2),
        "tokensRolledBackB": round(rolled_b, 2),
        "failures": float(summary.failures),
        "unfairInputs": float(_unfair_inputs(scenario)),
        "validationErrors": float(sum(1 for v in validations if v.level == "error")),
    }


# --- Criteria shared between labs ------------------------------------------

def _work(floor: int) -> Criterion:
    return Criterion(
        id="work", label=f"Delivered work at least {floor} effective GPUs",
        metric="effectiveGpus", op=">=", threshold=floor, unit="GPUs",
        weight=3.0, guards_work=True, explain_id="tokens-per-s", equation=EQ_TOKENS,
        why=L(
            standard=(
                "Work is the tokens the run kept — after every rollback — "
                "divided by what one GPU at full rate would make over all "
                f"{LAB_DURATION_H} hours, so it reads as GPUs' worth of "
                f"full-speed training; the floor is {floor}. Procurement, "
                "install and bring-up hours count as zero, and so does every "
                "hour a GPU waits for data, a checkpoint, a restart or the "
                "power cap. A small or idle factory cannot reach it. The proxy "
                "is illustrative, not a benchmark."
            ),
            novice=(
                "The factory has to really produce. We take every token the "
                "run still had at the end — tokens lost when a failure "
                "rewound the counter do not count — and ask: how many GPUs, "
                "running flat out for the whole "
                f"{LAB_DURATION_H} hours, would it take to make that many? "
                f"That number must be at least {floor}. The days spent buying "
                "and installing racks count as zero, and so does any hour the "
                "GPUs spent waiting — for data, for a save to finish, for a "
                "restart, or because the building ran out of power. So you "
                "cannot pass by building a tiny factory or leaving it idle. "
                "This is a simple stand-in for useful training, not a real "
                "benchmark score."
            ),
            expert=(
                "tokens kept ÷ (rate × 3600 × "
                f"{LAB_DURATION_H} h), dark hours zero; floor {floor}. "
                "Illustrative proxy."
            ),
        ),
    )


def _full_run() -> Criterion:
    return Criterion(
        id="full-run", label=f"Run lasts exactly {LAB_DURATION_H} h",
        metric="durationH", op="==", threshold=LAB_DURATION_H, unit="h",
        explain_id="tokens-per-s", equation=EQ_TOKENS,
        why=L(
            standard=(
                "Work is a rate over the whole run, and the first ~5 days of "
                "any run are procurement and install with no tokens at all. A "
                "longer run dilutes that dead time and a shorter one hides "
                f"the events, so every attempt is graded over the same "
                f"{LAB_DURATION_H} hours."
            ),
            novice=(
                "Every factory spends its first several days being bought, "
                "installed and switched on, making nothing. If you could "
                "stretch the run, those empty days would matter less and a "
                "weaker design would look better; if you could shorten it, "
                "the hard part of the lab would never happen. So the Run "
                f"length slider has to stay at {LAB_DURATION_H} hours (30 "
                "days), the length the lab starts with."
            ),
            expert=f"durationH == {LAB_DURATION_H}; the rate's denominator is fixed.",
        ),
    )


def _fair_inputs() -> Criterion:
    return Criterion(
        id="fair-inputs", label="Job, GPU tier, failure rate and prices not made easier",
        metric="unfairInputs", op="<=", threshold=0, unit="inputs",
        explain_id="tokens-per-s", equation=EQ_TOKENS,
        why=L(
            standard=(
                "The factory is yours to size; the world it is sized against "
                "is not. The count is how many of these were made easier than "
                "stock: tokens per GPU above 200, data per GPU below 1.5 GB/s, "
                "state per GPU below 10 GB, ramp below 24 h, GPUs below "
                "1200 W, GPU MTBF above 50000 h, restart below 15 min, energy "
                "below $0.08/kWh, racks below $3.0M, amortization above 4 "
                "years."
            ),
            novice=(
                "You may change how the factory is built — how many racks, "
                "how much storage, which network, which cooling, how often it "
                "saves. You may not make the problem itself easier. This line "
                "counts how many of these you changed in the easy direction: "
                "tokens per GPU above 200, data per GPU below 1.5 GB/s, state "
                "per GPU below 10 GB, ramp below 24 h, GPUs below 1200 W, GPU "
                "MTBF (how long one GPU lasts between failures) above 50000 h, "
                "restart below 15 min, energy below $0.08/kWh, racks below "
                "$3.0M, amortization above 4 years. The count must be zero. "
                "'Reset to the lab's start' puts everything back."
            ),
            expert=(
                "Zero world-inputs eased: rate ≤ 200, data ≥ 1.5 GB/s, state ≥ "
                "10 GB, ramp ≥ 24 h, GPU ≥ 1200 W, MTBF ≤ 50000 h, restart ≥ "
                "15 min, ≥ $0.08/kWh, ≥ $3.0M/rack, amortization ≤ 4 y."
            ),
        ),
    )


def _budget(mw: float) -> Criterion:
    return Criterion(
        id="budget", label=f"Facility budget no higher than {mw:g} MW",
        metric="mwBudget", op="<=", threshold=mw, unit="MW",
        explain_id="facility-mw", equation=EQ_MW,
        why=L(
            standard=(
                f"The building's feed is {mw:g} MW and the lab does not let "
                "you buy a bigger one. Everything on the left of the identity "
                "— GPUs, fabric, storage, overhead, times PUE — has to live "
                "under that number."
            ),
            novice=(
                f"The building can supply {mw:g} MW of electricity and no "
                "more. Raising the Facility budget slider would be the easy "
                "answer — it is also the one a real site cannot give you "
                "without a new substation — so it has to stay at "
                f"{mw:g} MW or lower. Everything the factory draws, multiplied "
                "by the cooling overhead (PUE), must fit under it."
            ),
            expert=f"B ≤ {mw:g} MW; the right-hand side of the identity is fixed.",
        ),
    )


def _no_cap() -> Criterion:
    return Criterion(
        id="no-cap", label="Never power-capped while training",
        metric="powerCappedHours", op="<=", threshold=0, unit="h", weight=2.0,
        explain_id="facility-mw", equation=EQ_MW,
        why=L(
            standard=(
                "When IT × PUE would exceed the budget the engine sheds load: "
                "GPU clocks fall until facility power sits exactly on the "
                "ceiling. Every watt spent on something that is not a GPU — "
                "storage draws 10 W per GB/s here — is a watt the GPUs cannot "
                "have, so an over-built platform can cap the cluster it was "
                "bought to serve."
            ),
            novice=(
                "If the factory tries to draw more power than the building "
                "has, the GPUs are slowed down until it fits. That is called "
                "power capping, and this lab allows none of it. Remember that "
                "GPUs are not the only thing plugged in: the network and the "
                "storage draw power too — storage draws 10 W for every GB/s "
                "you buy — and the cooling multiplies all of it. Power spent "
                "on anything else is power the GPUs cannot use."
            ),
            expert="powerCappedHours = 0; storage at 10 W per GB/s shares the ceiling.",
        ),
    )


# --- Lab 1: feed the cluster on its worst day -------------------------------

_DEGRADE_AT_H = 300

_WORST_DAY_START = Scenario(
    config=FactoryConfig(
        compute=ComputeBlock(racks=16),
        data=DataBlock(storage_gbps=1728),
        facility=FacilityBlock(mw_budget=2.5),
    ),
    job=TrainingJob(),
    duration_h=LAB_DURATION_H,
    events=[SimEvent(at_h=_DEGRADE_AT_H, action="degrade-storage", value=50)],
)

WORST_DAY = Lab(
    id="feed-the-worst-day",
    title="Feed the cluster on its worst day",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "Sixteen racks — 1152 GPUs — behind a data platform sized to "
                "feed them exactly. At hour 300 the platform loses half its "
                "throughput and stays that way. Size the platform so no GPU "
                "ever waits for data, deliver real work, and then buy no "
                "more storage than that worst day needs."
            ),
            novice=(
                "This factory has sixteen racks (1152 GPUs) and a storage "
                "system that was sized to feed them exactly — on a good day. "
                "At hour 300 something breaks and the storage can only "
                "deliver half of what it was built for, for the rest of the "
                "run. When storage cannot keep up, GPUs do not break; they "
                "wait, and waiting GPUs cost as much as working ones. Your "
                "job: choose a storage size so that no GPU ever waits, even "
                "after the failure, while the factory still does real work — "
                "and then do not buy more storage than that bad day needs."
            ),
            expert=(
                "16 racks, S = D, S × 0.5 from t = 300 h. Hold idle ≤ 1%, work "
                "≥ 850, then minimize S."
            ),
        ),
        constraints=[
            L(standard="GPU idle due to data never above 1% while training.",
              novice="While the factory is training, the 'GPU idle — waiting for data' gauge must never go above 1%, not even after the storage failure.",
              expert="max idle% ≤ 1 over train ticks."),
            L(standard="The platform runs at 50% or less of its configured throughput for at least 400 training hours.",
              novice="The storage failure has to stay in the run: for at least 400 of the training hours the platform must be delivering 50% or less of the size you chose. Pressing Restore, or Reset (which removes the failure), fails this line; 'Reset to the lab's start' brings it back.",
              expert="≥ 400 train hours at supply ≤ 50% of configured S."),
            L(standard="Run length exactly 720 h; job, GPU tier, failure rate and prices not made easier.",
              novice="Keep the run at 720 hours, and do not make the problem easier: leave the training job, the 1200 W GPUs, the failure settings and the prices as they are.",
              expert="720 h; world-inputs at stock."),
        ],
        delivered_work=L(
            standard="At least 850 effective GPUs of training, averaged over the whole 720 h run.",
            novice="Over the whole 720 hours — including the days before training starts, which count as zero — the factory must produce as many tokens as 850 GPUs running flat out the entire time. Shrinking the cluster until the broken storage can feed it will not reach that.",
            expert="effectiveGpus ≥ 850.",
        ),
    ),
    criteria=[
        _work(850),
        Criterion(
            id="never-starved", label="GPU idle due to data never above 1%",
            metric="peakIdleDataPct", op="<=", threshold=1, unit="%", weight=2.0,
            explain_id="idle-data", equation=EQ_IDLE,
            why=L(
                standard=(
                    "Idle is the shortfall of supply against demand, and "
                    "supply is what the platform delivers *today*, not what "
                    "was bought. Demand is 1152 GPUs × 1.5 GB/s = 1728 GB/s; "
                    "a platform sized to that number delivers 864 GB/s after "
                    "the failure, and half of every GPU-hour is lost."
                ),
                novice=(
                    "GPUs wait whenever the storage delivers less data than "
                    "they ask for. All together these GPUs ask for 1152 × 1.5 "
                    "= 1728 GB/s. The catch is that what counts is what the "
                    "storage delivers right now, not the size on the purchase "
                    "order: a 1728 GB/s system that has lost half its "
                    "throughput delivers 864 GB/s, and then every GPU spends "
                    "half its time waiting."
                ),
                expert="idle = 1 − min(1, S_today/D); D = 1728 GB/s, S_today = 0.5 S.",
            ),
        ),
        Criterion(
            id="degraded", label="Platform at 50% or less for at least 400 training hours",
            metric="degradedTrainHours", op=">=", threshold=400, unit="h",
            explain_id="idle-data", equation=EQ_IDLE,
            why=L(
                standard=(
                    "The failure is the lab. Supply is measured against the "
                    "storage you configured, hour by hour, so restoring the "
                    "platform, removing the event or degrading it late all "
                    "show up here rather than being taken on trust."
                ),
                novice=(
                    "The storage failure is the whole point of this lab, so "
                    "the grader checks that it really happened: it counts the "
                    "training hours in which the storage delivered half or "
                    "less of the size you chose. If you press Restore, or "
                    "remove the failure with Reset, that count falls below "
                    "400 and this line fails."
                ),
                expert="Σ train ticks with supply ≤ 0.5 × configured S ≥ 400.",
            ),
        ),
        _full_run(),
        _fair_inputs(),
    ],
    objective=Objective(
        label="Storage bought", metric="storageGbps", direction="minimize",
        par=3456, worst=8000, unit="GB/s",
        explain_id="idle-data", equation=EQ_IDLE,
    ),
    hints=[
        L(standard="Play the start to hour 300 and watch two instruments together: GPU idle — waiting for data, and tokens per second. Then read the storage line in the validation panel: it judges the platform you bought, not the one you have after the failure.",
          novice="Press Run and let the start scenario play past hour 300. Watch the 'GPU idle — waiting for data' tile jump and 'tokens / second' fall by the same share at the same moment. Then look at the checks under the build panel: the storage check says everything is fine, because it looks at the storage you bought, not at the storage you have left after the failure.",
          expert="At t = 300 idle steps to 50% while the storage rule still reads ok: it checks nameplate."),
        L(standard="Two ways to close the gap: shrink the cluster until 864 GB/s feeds it, or grow the platform. Try the first and read the work line — 8 racks of fed GPUs are still only 8 racks.",
          novice="There are two ways to stop the waiting. You can make the cluster smaller, so that the half-broken storage is enough for it — try 8 racks and look at the 'Delivered work' line: the GPUs are fed, but there are too few of them to reach 850. Or you can make the storage bigger.",
          expert="Shrinking N fixes idle and fails the work floor; the lever is S."),
        L(standard="Size for the day the platform is at 50%: storage × 0.5 must still cover 1152 × 1.5 = 1728 GB/s. The objective then rewards stopping there.",
          novice="Size the storage for its bad day, not its good one. After the failure you get half of what you bought, and the GPUs need 1152 × 1.5 = 1728 GB/s, so you need to buy twice that. Buying much more than twice earns nothing: the score's last 30 points are for buying no more than the bad day needs.",
          expert="S = 2D = 3456 GB/s; anything above is scored against you."),
    ],
    start=_WORST_DAY_START.model_dump(by_alias=True),
)


# --- Lab 2: spend the megawatt ----------------------------------------------

_WARM_EVENTS = [
    SimEvent(at_h=250, action="warm-day", value=0.2),
    SimEvent(at_h=450, action="end-warm-day"),
]

_MEGAWATT_START = Scenario(
    config=FactoryConfig(
        compute=ComputeBlock(racks=16),
        data=DataBlock(storage_gbps=1728),
        facility=FacilityBlock(mw_budget=1.0),
    ),
    job=TrainingJob(),
    duration_h=LAB_DURATION_H,
    events=list(_WARM_EVENTS),
)

MEGAWATT = Lab(
    id="spend-the-megawatt",
    title="Spend the megawatt",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "The building gives you 1 MW, and a 200-hour warm spell adds "
                "0.2 to PUE in the middle of the run. Someone filled the hall "
                "with 16 racks. Deliver at least 485 effective GPUs of "
                "training under that ceiling, then drive the cost per million "
                "tokens as low as it will go."
            ),
            novice=(
                "This building can supply 1 MW of power, and partway through "
                "the run there is a 200-hour warm spell that makes the "
                "cooling work harder (PUE, the building's overhead "
                "multiplier, goes up by 0.2). Someone has filled the hall "
                "with 16 racks of GPUs, far more than 1 MW can run at full "
                "speed. Your job: under that same 1 MW, produce at least as "
                "much training as 485 GPUs running flat out for the whole "
                "run, and then make each million tokens as cheap as you can."
            ),
            expert=(
                "B = 1 MW, ΔPUE +0.2 for 200 h. Work ≥ 485, then minimize "
                "$/Mtok."
            ),
        ),
        constraints=[
            L(standard="Facility budget stays at 1 MW or lower.",
              novice="The Facility budget slider must stay at 1 MW or lower — you cannot buy a bigger power feed.",
              expert="B ≤ 1 MW."),
            L(standard="At least 168 training hours at PUE 0.2 above the cooling's baseline.",
              novice="The warm spell has to stay in the run: at least 168 training hours with PUE 0.2 above normal for the cooling you chose. Reset removes the warm spell; 'Reset to the lab's start' brings it back.",
              expert="≥ 168 train hours at PUE ≥ base + 0.2."),
            L(standard="Run length exactly 720 h; job, GPU tier, failure rate and prices not made easier.",
              novice="Keep the run at 720 hours, and do not make the problem easier: leave the training job, the 1200 W GPUs, the failure settings and the prices as they are.",
              expert="720 h; world-inputs at stock."),
        ],
        delivered_work=L(
            standard="At least 485 effective GPUs of training, averaged over the whole 720 h run.",
            novice="Over the whole 720 hours — the days before training starts count as zero — the factory must produce as many tokens as 485 GPUs running flat out the entire time. A comfortable 8-rack factory under this ceiling does not quite get there.",
            expert="effectiveGpus ≥ 485.",
        ),
    ),
    criteria=[
        _work(485),
        _budget(1.0),
        Criterion(
            id="warm-spell", label="At least 168 training hours of warm weather",
            metric="warmTrainHours", op=">=", threshold=168, unit="h",
            explain_id="facility-mw", equation=EQ_MW,
            why=L(
                standard=(
                    "PUE multiplies everything to its left, so a +0.2 "
                    "excursion at a tight budget is a compute excursion. The "
                    "hours are counted from the trace — PUE at least 0.2 above "
                    "the baseline of the cooling you chose — so deleting or "
                    "shortening the weather shows up here."
                ),
                novice=(
                    "PUE is the building's overhead multiplier: the power the "
                    "computers draw, times PUE, is what the building has to "
                    "supply. When the weather is warm the cooling works "
                    "harder and PUE goes up by 0.2, so the same computing "
                    "suddenly needs more power. The grader counts the "
                    "training hours in which that really happened; removing "
                    "the warm spell fails this line."
                ),
                expert="Σ train ticks with PUE ≥ base(cooling) + 0.2 ≥ 168.",
            ),
        ),
        _full_run(),
        _fair_inputs(),
    ],
    objective=Objective(
        label="Cost per million tokens", metric="usdPerMtok", direction="minimize",
        par=2.36, worst=2.90, unit="$/Mtok",
        explain_id="usd-per-mtok", equation=EQ_USD,
    ),
    hints=[
        L(standard="Step the rack count down from 16 and note delivered work and $/Mtok at each size. Work does not fall as you remove racks — it rises, peaks, and only then falls.",
          novice="Start at 16 racks and take racks away a few at a time, pressing 'Run and grade' at each size and writing down the 'Delivered work' and 'Cost per million tokens' numbers. Something odd happens: with fewer racks the factory does more work, not less. Keep going until the work number starts to fall again.",
          expert="Sweep N downward: work(N) is an inverted U under a fixed B."),
        L(standard="A capped GPU still draws its idle power — 12% of peak here — before it computes anything. Under a fixed ceiling, every extra rack's idle watts come out of every other GPU's clock, so past the cap more silicon means fewer tokens and more amortization to divide them into.",
          novice="Here is why. A GPU draws some power just for being switched on — 12% of its full power in this model — even when it is doing nothing. When the building's power is the limit, every extra rack uses up part of the 1 MW just for being on, and that power is taken away from all the other GPUs, which have to slow down. So past a certain size, more racks means fewer tokens. And each rack still costs $3.0M, so the cost of every token goes up twice over.",
          expert="online × u = (P − online × P_idle)/(P_peak − P_idle): decreasing in online once capped."),
        L(standard="Find the smallest factory that clears 485: 8 racks fits the megawatt all month but falls short; one more rack is capped only during the warm spell. Then trim what is not a GPU — storage draws 10 W per GB/s and only needs to cover racks × 72 × 1.5 GB/s.",
          novice="Look for the smallest factory that reaches 485. Eight racks fits under 1 MW all month but does not quite make 485. One more rack does — it only gets slowed down during the warm spell. Then stop paying for power that is not GPUs: storage draws 10 W for every GB/s, and it only has to cover the GPUs' appetite, which is racks × 72 × 1.5 GB/s.",
          expert="N = 9, S ≈ 9 × 72 × 1.5 = 972 GB/s; capped only while warm."),
    ],
    start=_MEGAWATT_START.model_dump(by_alias=True),
)


# --- Lab 3: checkpoint the giant --------------------------------------------

_GIANT_JOB = TrainingJob(state_gb_per_gpu=400)

_GIANT_START = Scenario(
    config=FactoryConfig(
        compute=ComputeBlock(racks=16),
        data=DataBlock(storage_gbps=1728),
        facility=FacilityBlock(mw_budget=1.8),
        resilience=ResilienceBlock(checkpoint_interval_min=5),
    ),
    job=_GIANT_JOB,
    duration_h=LAB_DURATION_H,
)

GIANT = Lab(
    id="checkpoint-the-giant",
    title="Checkpoint the giant",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "A 16-rack run whose state is 400 GB per GPU — 461 TB per "
                "checkpoint — on a platform sized only to feed it, saving "
                "every 5 minutes to be safe, under a 1.8 MW ceiling. One GPU "
                "in 1152 fails about every 43 hours. Deliver at least 870 "
                "effective GPUs with checkpoint-and-restart overhead at 3% or "
                "less and no power capping, then push the work higher."
            ),
            novice=(
                "This training run is enormous: every GPU holds 400 GB of "
                "state, so saving the run's progress (a checkpoint) means "
                "writing 461 TB. The storage was sized only to feed the GPUs "
                "their training data, and the run saves every 5 minutes 'to "
                "be safe'. With 1152 GPUs, one of them fails about every 43 "
                "hours, and each failure rewinds the run to its last save. "
                "The building supplies 1.8 MW. Your job: produce as much "
                "training as 870 GPUs running flat out, lose 3% or less of "
                "training time to saving and restarting, never hit the power "
                "limit — and then push the work as high as it will go."
            ),
            expert=(
                "16 racks, 400 GB/GPU, S = D, I = 5 min, B = 1.8 MW, cluster "
                "MTBF ≈ 43 h. Work ≥ 870, overhead ≤ 3%, zero capped hours; "
                "maximize work."
            ),
        ),
        constraints=[
            L(standard="Mean checkpoint-and-restart overhead 3% or less while training.",
              novice="While training, the share of time lost to writing checkpoints and restarting after failures must average 3% or less.",
              expert="mean overhead% ≤ 3 over train ticks."),
            L(standard="Facility budget 1.8 MW or lower, and never power-capped while training.",
              novice="The Facility budget slider must stay at 1.8 MW or lower, and the 'hours power-capped' line in the run summary must read 0.",
              expert="B ≤ 1.8 MW; powerCappedHours = 0."),
            L(standard="State per GPU stays at 400 GB or more; run length exactly 720 h; nothing else made easier.",
              novice="The job must keep its 400 GB of state per GPU — the big model is the point. The page has no dial for it, but the job preset buttons replace it with a smaller job, so leave them alone ('Reset to the lab's start' brings the big job back). Keep the run at 720 hours, and leave the GPUs, the failure settings and the prices as they are.",
              expert="state ≥ 400 GB/GPU; 720 h; world-inputs at stock."),
        ],
        delivered_work=L(
            standard="At least 870 effective GPUs of training, averaged over the whole 720 h run, net of every rollback.",
            novice="Over the whole 720 hours — the days before training starts count as zero — the factory must keep as many tokens as 870 GPUs running flat out the entire time would make. Tokens that a failure rewound do not count.",
            expert="effectiveGpus ≥ 870, net of rollbacks.",
        ),
    ),
    criteria=[
        _work(870),
        Criterion(
            id="overhead", label="Mean checkpoint and restart overhead at most 3%",
            metric="meanOverheadPct", op="<=", threshold=3, unit="%", weight=2.0,
            explain_id="checkpoint", equation=EQ_CKPT,
            why=L(
                standard=(
                    "The write tax is t_ckpt/(I + t_ckpt), and t_ckpt is the "
                    "cluster's state divided by the platform's throughput: "
                    "461 TB at 1728 GB/s is 267 s. Against a 5-minute "
                    "interval that is 47% of every hour. The interval is one "
                    "lever on this line; the platform's GB/s is the other."
                ),
                novice=(
                    "Every checkpoint takes time to write, and while it is "
                    "being written the GPUs are not training. How long it "
                    "takes is simple division: the 461 TB to be saved, "
                    "divided by how fast the storage can take it. At 1728 "
                    "GB/s that is 267 seconds — and the start saves every 5 "
                    "minutes (300 seconds), so nearly half of every hour "
                    "goes to saving. You can shrink this two ways: save less "
                    "often, or make the storage faster so each save is "
                    "shorter."
                ),
                expert="τ = t_c/(I + t_c), t_c = state/S = 461 TB ÷ 1728 GB/s = 267 s; two levers.",
            ),
        ),
        _no_cap(),
        _budget(1.8),
        Criterion(
            id="giant-state", label="State per GPU at least 400 GB",
            metric="stateGbPerGpu", op=">=", threshold=400, unit="GB",
            explain_id="checkpoint", equation=EQ_CKPT,
            why=L(
                standard=(
                    "t_ckpt scales with the state to be written, so a smaller "
                    "model would dissolve the problem. The lab is the 400 GB "
                    "per GPU run."
                ),
                novice=(
                    "A smaller model would be quicker to save, and the whole "
                    "problem would disappear. The lab is about the big one, "
                    "so the job's state has to stay at 400 GB per GPU or more. "
                    "The job preset buttons swap in a smaller job and fail "
                    "this line; 'Reset to the lab's start' puts the big one "
                    "back."
                ),
                expert="t_c ∝ state; state ≥ 400 GB/GPU is the problem statement.",
            ),
        ),
        _full_run(),
        _fair_inputs(),
    ],
    objective=Objective(
        label="Delivered work", metric="effectiveGpus", direction="maximize",
        par=878, worst=870, unit="GPUs",
        explain_id="checkpoint", equation=EQ_CKPT,
    ),
    hints=[
        L(standard="Grade the start and read the overhead line, then the checkpoint rule in the validation panel: it names an optimum interval for this build. Note that the optimum moves when you change the storage.",
          novice="Press 'Run and grade' on the start and open the overhead line: almost half the training time is going to saves. Then look at the checkpoint check under the build panel — it works out the best time between saves for the factory as it is built right now. Change the storage size and watch that best time move.",
          expert="I* in the validation panel is a function of S; read it, then move S."),
        L(standard="Sweep the interval alone: 5 min drowns in writes, 480 min loses hours to every one of ~13 failures, and the middle is better — but with 267 s writes even the best interval leaves the work floor out of reach. The second lever is t_ckpt itself.",
          novice="Try changing only the time between saves. At 5 minutes the factory spends its life saving. At 480 minutes saving is cheap, but each of the roughly 13 failures throws away hours of work. Somewhere in the middle is better — and yet even the best setting does not reach 870, because every single save still takes 267 seconds. The other thing you can change is how long a save takes.",
          expert="Interval-only optimum < floor at t_c = 267 s. Cut t_c."),
        L(standard="Storage sized to feed the GPUs is not sized to checkpoint them: more GB/s shortens every write. But storage draws 10 W per GB/s under the same 1.8 MW as the GPUs — buy too much and the cluster is power-capped for the whole run.",
          novice="Storage that is big enough to feed the GPUs is not big enough to save them quickly. Buying faster storage makes every save shorter. But be careful: storage uses power too — 10 W for every GB/s — and it comes out of the same 1.8 MW the GPUs need. Buy far too much and the GPUs are slowed down for the entire run.",
          expert="t_c = state/S falls with S; P_storage = 10 W·S rises into B. Interior optimum in S too."),
        L(standard="Several times the feeding size — around 8000 GB/s — with a save about once an hour clears every line; at 10000 GB/s the budget rule turns red, and by 12000 the cap starts to bite.",
          novice="A storage system several times bigger than the GPUs need for data — around 8000 GB/s — together with a save about once an hour passes every line. At 10000 GB/s the power check turns red; by 12000 the GPUs start being slowed down by the power limit.",
          expert="S ≈ 8000 GB/s, I ≈ 60 min; S ≳ 12000 GB/s caps."),
    ],
    start=_GIANT_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [WORST_DAY, MEGAWATT, GIANT]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Reference solutions and gaming attempts --------------------------------
# Server-side only: GET /api/labs serves LABS, never these.

def _with(base: Scenario, **blocks: object) -> Scenario:
    """``base`` with whole config blocks (or job/duration_h/events) replaced."""
    top = {k: v for k, v in blocks.items() if k in ("job", "duration_h", "events")}
    cfg = {k: v for k, v in blocks.items() if k not in top}
    return base.model_copy(update={
        **top, "config": base.config.model_copy(update=cfg),
    })


REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    # Size the platform for the day it runs at half: 2 × 1728 GB/s.
    "feed-the-worst-day": _with(_WORST_DAY_START, data=DataBlock(storage_gbps=3456)),
    # The smallest factory that clears the floor, with no watts spent on
    # storage the GPUs do not need: 9 racks, 9 × 72 × 1.5 = 972 GB/s.
    "spend-the-megawatt": _with(
        _MEGAWATT_START,
        compute=ComputeBlock(racks=9), data=DataBlock(storage_gbps=972),
    ),
    # Cut t_ckpt with storage, stop short of the power wall, save hourly.
    "checkpoint-the-giant": _with(
        _GIANT_START,
        data=DataBlock(storage_gbps=8000),
        resilience=ResilienceBlock(checkpoint_interval_min=60),
    ),
}

GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "feed-the-worst-day": {
        "zero load: starve the GPUs to 10 GB/s": _with(
            _WORST_DAY_START, data=DataBlock(storage_gbps=10)),
        "size for the good day (the start, unchanged)": _WORST_DAY_START,
        "shrink the cluster until half a platform feeds it": _with(
            _WORST_DAY_START, compute=ComputeBlock(racks=8)),
        "restore the platform an hour later": _with(
            _WORST_DAY_START, events=[
                SimEvent(at_h=_DEGRADE_AT_H, action="degrade-storage", value=50),
                SimEvent(at_h=_DEGRADE_AT_H + 1, action="restore-storage"),
            ]),
        "delete the failure": _with(_WORST_DAY_START, events=[]),
        "fail the platform in the last hours only": _with(
            _WORST_DAY_START, events=[
                SimEvent(at_h=700, action="degrade-storage", value=50)]),
        "long run to dilute the dead time": _with(
            _WORST_DAY_START, data=DataBlock(storage_gbps=3456), duration_h=2160),
        "a job with a smaller appetite": _with(
            _WORST_DAY_START, job=TrainingJob(data_gbps_per_gpu=0.7)),
    },
    "spend-the-megawatt": {
        "idle: one rack sipping power": _with(
            _MEGAWATT_START, compute=ComputeBlock(racks=1)),
        "fill the hall (the start, unchanged)": _MEGAWATT_START,
        "the comfortable 8 racks": _with(
            _MEGAWATT_START, compute=ComputeBlock(racks=8),
            data=DataBlock(storage_gbps=900)),
        "overshoot to 12 racks": _with(
            _MEGAWATT_START, compute=ComputeBlock(racks=12),
            data=DataBlock(storage_gbps=1296)),
        "buy a bigger feed": _with(
            _MEGAWATT_START, facility=FacilityBlock(mw_budget=2.5)),
        "skip the weather": _with(
            _MEGAWATT_START, compute=ComputeBlock(racks=9),
            data=DataBlock(storage_gbps=972), events=[]),
        "700 W GPUs that make the same tokens": _with(
            _MEGAWATT_START, compute=ComputeBlock(racks=12, gpu_peak_w=700)),
        "cheaper racks and power": _with(
            _MEGAWATT_START, compute=ComputeBlock(racks=9),
            data=DataBlock(storage_gbps=972),
            costs=CostBlock(usd_per_kwh=0.01, capex_musd_per_rack=0.1)),
        "a faster model per GPU": _with(
            _MEGAWATT_START, compute=ComputeBlock(racks=9),
            data=DataBlock(storage_gbps=972),
            job=TrainingJob(tokens_per_gpu_s=2000)),
        "short run": _with(
            _MEGAWATT_START, compute=ComputeBlock(racks=9),
            data=DataBlock(storage_gbps=972), duration_h=480),
    },
    "checkpoint-the-giant": {
        "zero load: starve the GPUs to 10 GB/s": _with(
            _GIANT_START, data=DataBlock(storage_gbps=10)),
        "save every 5 minutes (the start, unchanged)": _GIANT_START,
        "best interval alone, storage untouched": _with(
            _GIANT_START, resilience=ResilienceBlock(checkpoint_interval_min=120)),
        "almost never save": _with(
            _GIANT_START, data=DataBlock(storage_gbps=8000),
            resilience=ResilienceBlock(checkpoint_interval_min=1440)),
        "buy all the storage there is": _with(
            _GIANT_START, data=DataBlock(storage_gbps=20000),
            resilience=ResilienceBlock(checkpoint_interval_min=60)),
        "buy a bigger feed for it": _with(
            _GIANT_START, data=DataBlock(storage_gbps=20000),
            facility=FacilityBlock(mw_budget=2.5),
            resilience=ResilienceBlock(checkpoint_interval_min=60)),
        "train a smaller model": _with(
            _GIANT_START, job=TrainingJob(state_gb_per_gpu=10),
            resilience=ResilienceBlock(checkpoint_interval_min=60)),
        "GPUs that never fail": _with(
            _GIANT_START, data=DataBlock(storage_gbps=8000),
            resilience=ResilienceBlock(
                checkpoint_interval_min=1440, gpu_mtbf_h=1000000)),
    },
}


# --- Grading ---------------------------------------------------------------

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
