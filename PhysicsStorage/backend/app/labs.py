"""Graded labs for the storage-platforms simulator (docs/LAB_PATTERN.md).

A guided scenario sets the dials and narrates. A lab states a goal and leaves
the dials to you: build a Scenario with the ordinary controls, the engine runs
it, and ``grade_scenario`` scores the trace.

Pure module, same rule as ``engine.py`` and ``validation.py``: no FastAPI, no
IO, no clock, no randomness (AST-checked in ``tests/test_labs.py``). ``main.py``
is the only caller that touches HTTP, so the static build grades in the
browser by running this same file under Pyodide.

Three things here are this app's own; everything else is ``twinkit.labs``:

* ``measure()`` — turns one run into named numbers. The un-gameable ones are
  ``workIopsK`` (delivered IOPS averaged over every hour of the run; an
  offline array delivers zero) and ``minDeliveredIopsK`` (the worst single
  hour, which closes "load early, idle through the hard part"). Both are
  illustrative proxies for useful storage work, not benchmarks.
* ``LABS`` — three labs of rising difficulty, every criterion citing the
  Explain entry (``presets.EXPLAINS``) and the equation it tests.
* ``REFERENCE_SOLUTIONS`` / ``GAMING_ATTEMPTS`` — a scenario that passes each
  lab, and the cheap tricks that must not. Server-side only.
"""

from __future__ import annotations

from twinkit.labs import Criterion, Lab, LabGoal, LabResult, Objective, grade

from .constants import PROTECTION_OVERHEAD, value as C
from .engine import simulate
from .leveling import L
from .models import (
    Scenario,
    SimEvent,
    SimState,
    StorageConfig,
    Summary,
    Validation,
    Workload,
)
from .presets import OLTP, POWERMAX_4, POWERSTORE_2
from .validation import validate

# The equations, exactly as the Explain entries display them.
EQ_QUEUE = "latency = service_time × 1 / (1 − ρ),  ρ = demand / capacity"
EQ_CAP = "usable = raw × (1 − protection);  effective = usable × reduction"
EQ_REBUILD = "hours = drive_TB × 1000 / (rate_GB/s × 3600);  rate ∝ survivors (scale-out)"
EQ_SRDF = "sync: +d × 0.005 × 2 ms per write;  async: RPO = backlog / link"

#: "It never happened" for the time-of-event metrics, so ``<=`` criteria fail.
NEVER = 9999.0


# --- Measurement ----------------------------------------------------------

def measure(
    scenario: Scenario,
    trace: list[SimState],
    summary: Summary,
    validations: list[Validation],
) -> dict[str, float]:
    """One run as named numbers. Keys are the wire names criteria refer to."""
    cfg = scenario.config
    duration = trace[-1].t_h
    events = sorted(scenario.events, key=lambda e: e.at_h)
    live = [e for e in events if e.at_h <= duration]

    # Replay the workload dial exactly as the engine applied it.
    wl = scenario.workload
    min_write_share = 100.0 - wl.read_pct
    ei = 0
    for s in trace:
        while ei < len(live) and live[ei].at_h <= s.t_h:
            ev = live[ei]
            ei += 1
            if ev.action == "set-workload" and ev.workload is not None:
                wl = ev.workload
        min_write_share = min(min_write_share, 100.0 - wl.read_pct)

    n = len(trace)
    delivered = [s.iops_delivered_k if s.online else 0.0 for s in trace]

    # A controller failure only halves the ceiling on the PowerStore pair.
    ctrl_fail = next(
        (float(e.at_h) for e in live
         if e.action == "fail-controller" and cfg.product == "powerstore"),
        NEVER,
    )
    # Bursts count when their whole six hours fit inside the run.
    bursts = [
        e for e in live
        if e.action == "write-burst" and e.value is not None
        and e.at_h + 6 <= duration
    ]
    peak_burst = max((float(e.value) for e in bursts), default=0.0)
    burst_on_survivor = max(
        (float(e.value) for e in bursts if e.at_h >= ctrl_fail), default=0.0
    )

    # A node loss is read from the trace: controller arrays ignore the event.
    node_loss = NEVER
    for prev, cur in zip(trace, trace[1:]):
        if cur.units_online < prev.units_online:
            node_loss = float(cur.t_h)
            break
    drive_gap = next(
        (float(e.at_h) - node_loss for e in live
         if e.action == "fail-drive" and e.at_h >= node_loss),
        NEVER,
    )

    replicated_km = (
        float(cfg.distance_km)
        if cfg.product == "powermax" and cfg.srdf != "off" else 0.0
    )

    return {
        "durationH": float(duration),
        "workIopsK": round(sum(delivered) / n, 1),
        "minDeliveredIopsK": round(min(delivered), 1),
        "peakUtilizationPct": round(max(s.utilization_pct for s in trace), 1),
        "peakP99Ms": round(max(s.p99_ms for s in trace), 3),
        "peakRpoS": round(max(s.rpo_seconds for s in trace), 1),
        "minWriteSharePct": round(min_write_share, 1),
        "controllerFailedH": ctrl_fail,
        "peakBurstMult": peak_burst,
        "burstOnSurvivorMult": burst_on_survivor,
        "replicatedKm": replicated_km,
        "rawTb": round(min(s.raw_tb for s in trace), 1),
        "usableTb": round(min(s.usable_tb for s in trace), 1),
        "protectionOverheadPct": round(
            100.0 * C(PROTECTION_OVERHEAD[cfg.protection]), 2
        ),
        "nodeLossH": node_loss,
        "driveFailGapH": drive_gap,
        "rebuildHours": float(summary.rebuild_hours),
        "dataSurvived": 1.0 if summary.data_survived else 0.0,
        "validationErrors": float(sum(1 for v in validations if v.level == "error")),
    }


# --- Criteria shared between labs ------------------------------------------

def _work(floor_k: int) -> Criterion:
    return Criterion(
        id="work", label=f"Delivered work at least {floor_k}k IOPS",
        metric="workIopsK", op=">=", threshold=floor_k, unit="k IOPS",
        weight=2.0, guards_work=True, explain_id="queueing", equation=EQ_QUEUE,
        why=L(
            standard=(
                f"Work is delivered IOPS — min(demand, capacity) — averaged "
                f"over every hour of the run; {floor_k}k is the floor. An idle "
                "array, a saturated one, or one that lost its data and went "
                "offline delivers less, so turning the load down is not a way "
                "through. The proxy is illustrative, not a benchmark."
            ),
            novice=(
                f"The storage has to do real work the whole time: at least "
                f"{floor_k} thousand reads and writes per second (IOPS), "
                "averaged over every hour of the run. We count only what the "
                "system actually delivers. It can never deliver more than its "
                "ceiling, and an array that has lost its data and gone "
                "offline delivers nothing at all. So you cannot win by "
                "turning the IOPS demand slider down to zero. This is a "
                "simple stand-in for useful storage work, not a real "
                "benchmark score."
            ),
            expert=(
                f"Mean of min(demand, capacity) over all ticks, offline ticks "
                f"zero; floor {floor_k}k IOPS. Illustrative proxy."
            ),
        ),
    )


def _every_hour(floor_k: int) -> Criterion:
    return Criterion(
        id="every-hour", label=f"Every hour delivers at least {floor_k}k IOPS",
        metric="minDeliveredIopsK", op=">=", threshold=floor_k, unit="k IOPS",
        guards_work=True, explain_id="queueing", equation=EQ_QUEUE,
        why=L(
            standard=(
                f"The worst single hour must still deliver {floor_k}k IOPS. "
                "An average can be earned before the failure and coasted "
                "through it; the application does not get to do that."
            ),
            novice=(
                f"Every single hour of the run has to deliver at least "
                f"{floor_k} thousand IOPS. Without this rule you could work "
                "very hard early, then go quiet during the difficult part, "
                "and the average would still look fine. A real application "
                "cannot take the difficult hours off."
            ),
            expert=f"min over ticks of delivered ≥ {floor_k}k; closes load-early-idle-later.",
        ),
    )


def _below_knee(pct: int) -> Criterion:
    return Criterion(
        id="below-knee", label=f"Utilization never above {pct}%",
        metric="peakUtilizationPct", op="<=", threshold=pct, unit="%",
        weight=2.0, explain_id="queueing", equation=EQ_QUEUE,
        why=L(
            standard=(
                f"At ρ = {pct}% the queue factor 1/(1−ρ) is already "
                f"{1 / (1 - pct / 100):.0f}×; past it latency runs away. The "
                "peak is taken over the whole run, so it is set by the worst "
                "hour on the smallest ceiling, not by the healthy steady state."
            ),
            novice=(
                f"Utilization is demand divided by the ceiling — how full "
                f"the system is. It must never go above {pct}%. Storage gets "
                "slow long before it is full: waiting time grows as "
                f"1 ÷ (1 − utilization), so at {pct}% every request already "
                f"waits about {1 / (1 - pct / 100):.0f} times longer than on "
                "an empty system, and beyond that it shoots up. We look at "
                "the worst hour of the whole run, which is the hour when "
                "demand is highest and the ceiling is lowest."
            ),
            expert=f"max ρ over the run ≤ {pct}%; binding tick is peak demand on the degraded ceiling.",
        ),
    )


def _write_share(pct: int) -> Criterion:
    return Criterion(
        id="write-share", label=f"Writes stay at least {pct}% of the I/O",
        metric="minWriteSharePct", op=">=", threshold=pct, unit="%",
        explain_id="queueing", equation=EQ_QUEUE,
        why=L(
            standard=(
                f"The application writes {pct}% of the time. A burst "
                "multiplies write demand only, so an all-read workload would "
                "make the burst vanish — and would not be this application."
            ),
            novice=(
                f"The application in this lab writes data {pct}% of the time, "
                f"so the Read slider has to stay at {100 - pct}% or lower. "
                "A write burst only multiplies the writes. If you turned the "
                "workload into all reads, the burst would disappear — but "
                "you would be solving a different, easier problem."
            ),
            expert=f"min(1 − read%) ≥ {pct}%; the burst scales the write term only.",
        ),
    )


def _full_run(hours: int) -> Criterion:
    return Criterion(
        id="full-run", label=f"Run lasts at least {hours} h",
        metric="durationH", op=">=", threshold=hours, unit="h",
        explain_id="rebuild", equation=EQ_REBUILD,
        why=L(
            standard=(
                "Storage stories take hours: a rebuild, a burst draining, a "
                f"degraded ceiling under a peak. A run shorter than {hours} h "
                "would be graded before the hard hours arrived."
            ),
            novice=(
                "Things in storage happen slowly — repairing after a failure "
                "takes hours, and so does clearing a backlog. The run has to "
                f"last at least {hours} hours so that the difficult hours are "
                "actually part of what gets graded."
            ),
            expert=f"duration ≥ {hours} h so every event and its aftermath are in the trace.",
        ),
    )


def _valid_build() -> Criterion:
    return Criterion(
        id="valid-build", label="Build has no validation errors",
        metric="validationErrors", op="<=", threshold=0, unit="errors",
        explain_id="capacity", equation=EQ_CAP,
        why=L(
            standard=(
                "Each product runs inside a unit-count envelope (PowerStore "
                "1–4 appliances, PowerScale from 3 nodes, PowerFlex from 4). "
                "A cluster the product cannot be is not a solution."
            ),
            novice=(
                "Each product only comes in certain sizes. A PowerStore "
                "cluster is 1 to 4 appliances; PowerScale needs at least 3 "
                "nodes and PowerFlex at least 4. The validation panel shows "
                "a red error if your build is outside those limits, and a "
                "build with a red error does not count. Yellow warnings are "
                "allowed."
            ),
            expert="Zero error-level findings (unit-count envelope, Exascale partition).",
        ),
    )


def _data_survives() -> Criterion:
    return Criterion(
        id="data-survives", label="No data is lost",
        metric="dataSurvived", op=">=", threshold=1, unit="", weight=3.0,
        explain_id="rebuild", equation=EQ_REBUILD,
        why=L(
            standard=(
                "While a rebuild runs the protection level is spent; one more "
                "failure than it survives inside that window is data loss, "
                "and an array that lost data goes offline."
            ),
            novice=(
                "After a failure the system rebuilds the missing data from "
                "what is left. Until that repair finishes, it has used up "
                "some of its protection. If another failure arrives during "
                "the repair — more failures than the protection level can "
                "take — the data is gone and the system goes offline. The "
                "red band on the timeline marks that dangerous window."
            ),
            expert="failures in window ≤ protection level at every tick.",
        ),
    )


# --- Lab 1: size for the survivor -------------------------------------------

_BURST = SimEvent(at_h=48, action="write-burst", value=5)
_SURVIVOR_EVENTS = [SimEvent(at_h=24, action="fail-controller"), _BURST]

_SURVIVOR_START = Scenario(
    config=POWERSTORE_2, workload=OLTP, duration_h=72, events=_SURVIVOR_EVENTS,
)

SIZE_FOR_THE_SURVIVOR = Lab(
    id="size-for-the-survivor",
    title="Size for the survivor's worst hour",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "A PowerStore cluster loses a controller at h+24 and takes a "
                "×5 write burst at h+48. Deliver at least 250k IOPS through "
                "all of it without utilization ever passing 80%."
            ),
            novice=(
                "A PowerStore cluster has two controllers — the computers "
                "inside it that handle every read and write. One of them "
                "fails 24 hours in, and 24 hours after that the application "
                "suddenly writes 5 times as much for six hours. Your job: "
                "keep delivering at least 250 thousand IOPS through all of "
                "it, and never let the system get more than 80% full of work."
            ),
            expert="PowerStore, controller loss h+24, ×5 write burst h+48: ≥250k IOPS, ρ ≤ 80% throughout.",
        ),
        constraints=[
            L(standard="A PowerStore controller fails by h+24 and a write burst of ×5 or more lands after it.",
              novice="Keep the two events on the timeline: a PowerStore controller failure in the first 24 hours, and after it a write burst of ×5 or more.",
              expert="fail-controller ≤ h+24 on PowerStore; write-burst ≥ ×5 after it."),
            L(standard="Writes stay at least 30% of the I/O, the run lasts 72 h, and the build has no validation errors.",
              novice="Keep the Read slider at 70% or lower (so writes are at least 30%), keep the run 72 hours long, and do not leave any red errors in the validation panel.",
              expert="write share ≥ 30%; 72 h; zero validation errors."),
        ],
        delivered_work=L(
            standard="Work is delivered IOPS averaged over the run — at least 250k, and at least 250k in every single hour. Illustrative proxy.",
            novice="Work means the reads and writes per second the system actually delivers. The average over the whole run must be at least 250 thousand, and so must every single hour. It is a simple stand-in for useful work, not a benchmark.",
            expert="mean and min of delivered ≥ 250k IOPS. Illustrative.",
        ),
    ),
    criteria=[
        _work(250),
        _every_hour(250),
        _below_knee(80),
        Criterion(
            id="controller-fails", label="A PowerStore controller fails by h+24",
            metric="controllerFailedH", op="<=", threshold=24, unit="h",
            explain_id="queueing", equation=EQ_QUEUE,
            why=L(
                standard="A PowerStore controller loss halves the front-end ceiling, so the same demand lands at twice the ρ. On a PowerMax the same event is a latency blip, which is a different lesson.",
                novice="The lab is about losing one of a PowerStore's two controllers early in the run. When that happens the ceiling is cut in half, so the same demand suddenly fills the system twice as much. (On a PowerMax the same failure is only a brief hiccup, so switching product does not count.)",
                expert="capacity × 0.5 from the event on; ρ doubles at constant demand.",
            ),
        ),
        Criterion(
            id="burst-on-survivor", label="A ×5 write burst lands after the failure",
            metric="burstOnSurvivorMult", op=">=", threshold=5, unit="×",
            explain_id="queueing", equation=EQ_QUEUE,
            why=L(
                standard="The binding hour is the burst on the halved ceiling: demand × (read + write × 5) over half the capacity. Sizing for the healthy steady state misses it twice over.",
                novice="The hardest hour is when the write burst arrives and only one controller is left: demand is at its highest exactly when the ceiling is at its lowest. The burst must come after the controller failure and last its full six hours inside the run.",
                expert="ρ_peak = D × (r + w × 5) / (C / 2); the burst must sit wholly inside the run.",
            ),
        ),
        _write_share(30),
        _full_run(72),
        _valid_build(),
    ],
    objective=Objective(
        label="Delivered work", metric="workIopsK", direction="maximize",
        par=312, worst=250, unit="k IOPS", explain_id="queueing", equation=EQ_QUEUE,
    ),
    hints=[
        L(standard="Read the utilization gauge at h+23, h+25 and h+50. The number that fails the lab is the last one.",
          novice="Drag the timeline to hour 23, then hour 25, then hour 50, and read the utilization gauge each time. The first is the healthy system, the second has lost a controller, the third has the write burst on top. The third number is the one that fails the lab.",
          expert="Compare ρ at h+23, h+25, h+50."),
        L(standard="A ×5 burst at 30% writes multiplies demand by 0.7 + 0.3 × 5 = 2.2, and the controller loss halves the ceiling. Together the worst hour runs at 4.4× the healthy ρ.",
          novice="With 30% writes, a ×5 burst turns demand into 0.7 + 0.3 × 5 = 2.2 times normal. Losing a controller halves the ceiling, which doubles utilization. Both at once means the worst hour is 4.4 times as full as a normal healthy hour.",
          expert="ρ_peak = 4.4 × ρ_healthy."),
        L(standard="Four appliances give 1,600k healthy and 800k on the survivors; 80% of that is 640k, and 640 ÷ 2.2 ≈ 290k. Adding appliances alone at 300k demand still peaks at 82.5%.",
          novice="Use the largest cluster, four appliances: 1,600 thousand IOPS healthy, 800 thousand after the failure. 80% of 800 is 640, and 640 ÷ 2.2 is about 290. So the demand slider has to sit a little under 290 thousand. At 300 thousand the worst hour is 82.5% — just over the line.",
          expert="4 appliances, demand ≤ 290k (slider: 280k)."),
    ],
    start=_SURVIVOR_START.model_dump(by_alias=True),
)


# --- Lab 2: the burst has to fit the pipe -----------------------------------

_PIPE_START = Scenario(
    config=POWERMAX_4.model_copy(update={"srdf": "sync", "distance_km": 300}),
    workload=OLTP.model_copy(update={"iops_demand_k": 500}),
    duration_h=168,
    events=[SimEvent(at_h=24, action="write-burst", value=5)],
)

FIT_THE_PIPE = Lab(
    id="burst-fits-the-pipe",
    title="Replicate 300 km: the burst has to fit the pipe",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "A PowerMax replicates to a site 300 km away and takes a ×5 "
                "write burst. Hold p99 latency at 2 ms or less and RPO at 30 s "
                "or less, deliver at least 350k IOPS, then maximize work."
            ),
            novice=(
                "A PowerMax array copies every write to a second site 300 km "
                "away, so a disaster at one site does not lose the data. "
                "During the week the application writes 5 times as much for "
                "six hours. Keep the slowest 1% of requests (p99 latency) at "
                "2 ms or faster, keep the copy at the far site no more than "
                "30 seconds behind (the RPO, recovery point objective), and "
                "deliver at least 350 thousand IOPS. Then deliver as much as "
                "you can."
            ),
            expert="PowerMax SRDF at ≥300 km, ×5 burst: p99 ≤ 2 ms, RPO ≤ 30 s, ≥350k IOPS; maximize work.",
        ),
        constraints=[
            L(standard="SRDF stays on, on a PowerMax, across at least 300 km.",
              novice="Replication (SRDF) must stay switched on, the product must stay PowerMax, and the distance slider must stay at 300 km or more.",
              expert="PowerMax, srdf ≠ off, d ≥ 300 km."),
            L(standard="A write burst of ×5 or more runs its full six hours, writes stay at least 30% of the I/O, the run lasts 168 h, and the build is valid.",
              novice="Keep a write burst of ×5 or more on the timeline with all six of its hours inside the run, keep the Read slider at 70% or lower, keep the run a full week (168 hours), and leave no red validation errors.",
              expert="burst ≥ ×5 wholly in-run; write share ≥ 30%; 168 h; zero errors."),
        ],
        delivered_work=L(
            standard="Work is delivered IOPS averaged over the week — at least 350k, and at least 340k in every single hour. Illustrative proxy.",
            novice="Work means the reads and writes per second the array actually delivers. The average over the week must be at least 350 thousand, and every single hour must deliver at least 340 thousand. It is a simple stand-in for useful work, not a benchmark.",
            expert="mean delivered ≥ 350k, min ≥ 340k IOPS. Illustrative.",
        ),
    ),
    criteria=[
        _work(350),
        _every_hour(340),
        Criterion(
            id="p99", label="p99 latency never above 2 ms",
            metric="peakP99Ms", op="<=", threshold=2.0, unit="ms", weight=2.0,
            explain_id="srdf", equation=EQ_SRDF,
            why=L(
                standard="Sync SRDF holds each write until the far site acknowledges: 300 km × 0.005 ms × 2 = 3 ms per write, 0.9 ms on the mean at 30% writes, 2.7 ms at p99 before the array has done anything. No amount of hardware shortens the fiber.",
                novice="In sync mode every write waits until the far site confirms it. Light in glass fiber covers a kilometre in about 0.005 ms, so 300 km there and back costs 3 ms per write. With 30% writes that adds 0.9 ms to the average request and about 2.7 ms to the slowest 1% — already over the 2 ms limit before the array does any work. Buying more hardware does not help, because the delay is the speed of light.",
                expert="sync tax = d × 0.005 × 2 × w = 0.9 ms mean, 2.7 ms p99 at 300 km — over budget by physics.",
            ),
        ),
        Criterion(
            id="rpo", label="RPO never above 30 s",
            metric="peakRpoS", op="<=", threshold=30, unit="s", weight=2.0,
            explain_id="srdf", equation=EQ_SRDF,
            why=L(
                standard="Async SRDF acknowledges locally and ships writes over a 2 GB/s link. Any hour that writes faster than the link adds to a backlog, and RPO is that backlog divided by the link — it grows by the hour and drains slowly.",
                novice="In async mode the array confirms each write straight away and sends the copy afterwards over a link that carries 2 GB every second. If the application writes faster than that, the unsent data piles up. RPO — how far behind the far site is — is that pile divided by the link speed. One busy hour can put the far site many minutes behind, and it takes a long time to catch up.",
                expert="RPO = backlog / 2 GB/s; backlog integrates max(0, write GB/s − link).",
            ),
        ),
        Criterion(
            id="replicated", label="Replicating on a PowerMax across at least 300 km",
            metric="replicatedKm", op=">=", threshold=300, unit="km",
            explain_id="srdf", equation=EQ_SRDF,
            why=L(
                standard="The second site is 300 km away because a regional event must not take both. Distance is the term you may not shrink, and turning SRDF off is not a recovery plan.",
                novice="The second site is 300 km away on purpose, so that one flood or power failure cannot hit both. You may not move it closer, and you may not switch replication off — a lab about protecting data cannot be passed by not protecting it.",
                expert="d ≥ 300 km with srdf ∈ {sync, async} on PowerMax.",
            ),
        ),
        Criterion(
            id="burst", label="A ×5 write burst runs in full",
            metric="peakBurstMult", op=">=", threshold=5, unit="×",
            explain_id="srdf", equation=EQ_SRDF,
            why=L(
                standard="The burst is the hour the link is sized against. Month-end does not ask permission.",
                novice="The six-hour write burst is the whole test: it is the moment the link to the far site is most likely to fall behind. It has to stay on the timeline, at ×5 or more, with all six hours inside the run.",
                expert="write-burst ≥ ×5, wholly inside the run.",
            ),
        ),
        _write_share(30),
        _below_knee(80),
        _full_run(168),
        _valid_build(),
    ],
    objective=Objective(
        label="Delivered work", metric="workIopsK", direction="maximize",
        par=378, worst=350, unit="k IOPS", explain_id="srdf", equation=EQ_SRDF,
    ),
    hints=[
        L(standard="Open Explain mode on the SRDF readout and work out the sync tax at 300 km before touching the array.",
          novice="Switch on Explain mode and look at the SRDF readout. Work out what 300 km of sync replication adds to each write before you change anything about the array itself.",
          expert="Compute the sync tax first."),
        L(standard="Sync cannot make 2 ms at 300 km at any size. Switch to async and watch the RPO gauge through the burst instead.",
          novice="Sync mode cannot reach 2 ms at 300 km however big the array is, because the delay is in the fiber. Switch replication to async, then watch the RPO gauge while the write burst runs.",
          expert="Sync is infeasible; go async and watch RPO under the burst."),
        L(standard="Async holds RPO at zero only while write GB/s stays under the 2 GB/s link. In the burst the array delivers 2.2× demand; at 8 KB blocks and 30% writes that is demand × 2.2 × 0.0082 × 0.3 GB/s.",
          novice="In async mode the far site keeps up only while the array writes less than 2 GB per second. During the burst the array delivers 2.2 times the normal demand. With 8 KB requests and 30% writes, the write rate in GB/s is demand (in thousands) × 2.2 × 0.0082 × 0.3. That has to stay under 2.",
          expert="Need D × 2.2 × 0.0082 × 0.3 ≤ 2."),
        L(standard="That puts the ceiling near 369k IOPS of demand: 360k holds RPO at zero and clears the work floor; 380k puts the far site about twelve minutes behind.",
          novice="Solving that gives a demand of about 369 thousand IOPS. Set the slider to 360 thousand: the far site never falls behind, and you clear the work floor. At 380 thousand the far site ends up about twelve minutes behind.",
          expert="D ≤ 369k; 360k passes, 380k → RPO ≈ 710 s."),
    ],
    start=_PIPE_START.model_dump(by_alias=True),
)


# --- Lab 3: many thin nodes --------------------------------------------------

_RACE_EVENTS = [
    SimEvent(at_h=24, action="fail-node"),
    SimEvent(at_h=30, action="fail-drive"),
]
_RACE_WL = OLTP.model_copy(update={"iops_demand_k": 160})

_RACE_START = Scenario(
    config=StorageConfig(
        product="powerscale", units=4, drives_per_unit=24, drive_tb=15.36,
        drive_class="nvme", protection="raid5",
    ),
    workload=_RACE_WL, duration_h=72, events=_RACE_EVENTS,
)

WIN_THE_REBUILD_RACE = Lab(
    id="win-the-rebuild-race",
    title="Win the rebuild race on a one-failure budget",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "A scale-out cluster loses a node at h+24 and a drive six "
                "hours later. The budget allows 12.5% protection overhead — "
                "one failure's worth. Keep 1,000 TB usable, lose no data, "
                "deliver 150k IOPS, then minimize raw capacity bought."
            ),
            novice=(
                "A scale-out cluster is many storage servers (nodes) acting "
                "as one. One node dies 24 hours in, and a drive in another "
                "node dies six hours after that. The budget only allows "
                "protection that costs 12.5% of the capacity, which survives "
                "one failure at a time — so the repair of the first failure "
                "has to finish before the second one arrives. Keep at least "
                "1,000 TB of usable space, lose no data, deliver 150 thousand "
                "IOPS, and then buy as little raw capacity as you can."
            ),
            expert="Scale-out, node loss h+24, drive loss +6 h, overhead ≤ 12.5%: usable ≥ 1,000 TB, no data loss, ≥150k IOPS; minimize raw TB.",
        ),
        constraints=[
            L(standard="A node is lost by h+24 and a drive fails within 6 h after it.",
              novice="Keep both failures on the timeline: a node lost in the first 24 hours, and a drive failure no more than 6 hours after the node.",
              expert="node loss ≤ h+24; fail-drive within 6 h after."),
            L(standard="Protection overhead is 12.5% or less and usable capacity is at least 1,000 TB.",
              novice="The protection setting may cost at most 12.5% of the raw capacity, and what is left over (usable capacity) must be at least 1,000 TB.",
              expert="overhead ≤ 12.5%; usable ≥ 1,000 TB."),
            L(standard="Utilization stays at or under 80%, the run lasts 72 h, and the build has no validation errors.",
              novice="Never let utilization go above 80%, keep the run 72 hours long, and leave no red errors in the validation panel.",
              expert="ρ ≤ 80%; 72 h; zero errors."),
        ],
        delivered_work=L(
            standard="Work is delivered IOPS averaged over the run — at least 150k, and at least 150k in every single hour. A cluster that loses data goes offline and earns nothing after. Illustrative proxy.",
            novice="Work means the reads and writes per second the cluster actually delivers. The average must be at least 150 thousand, and so must every single hour. If the cluster loses data it goes offline, and an offline cluster delivers nothing. It is a simple stand-in for useful work, not a benchmark.",
            expert="mean and min of delivered ≥ 150k IOPS; offline ticks zero. Illustrative.",
        ),
    ),
    criteria=[
        _work(150),
        _every_hour(150),
        _data_survives(),
        Criterion(
            id="node-lost", label="A node is lost by h+24",
            metric="nodeLossH", op="<=", threshold=24, unit="h",
            explain_id="rebuild", equation=EQ_REBUILD,
            why=L(
                standard="Losing a node means rebuilding every drive in it at once: drives × TB each. On a controller array the event does nothing, so the cluster has to be scale-out.",
                novice="When a whole node dies, the cluster has to rebuild everything that node held — all of its drives at once. The lab needs that to happen in the first 24 hours. Products built around a controller pair (PowerStore, PowerMax) have no nodes to lose, so the product must be one of the scale-out ones.",
                expert="units_online drops by h+24; rebuild payload = drives × TB.",
            ),
        ),
        Criterion(
            id="second-failure", label="A drive fails within 6 h of the node",
            metric="driveFailGapH", op="<=", threshold=6, unit="h", weight=2.0,
            explain_id="rebuild", equation=EQ_REBUILD,
            why=L(
                standard="The second failure is the clock the rebuild races. With one-failure protection the node's data must be whole again before it lands, so the rebuild has 6 hours.",
                novice="The second failure is the deadline. With protection that survives only one failure, the cluster must finish repairing the lost node before the drive dies, six hours later. If the repair is still running, the data is lost.",
                expert="Rebuild must complete inside the 6 h gap.",
            ),
        ),
        Criterion(
            id="overhead-budget", label="Protection overhead at most 12.5%",
            metric="protectionOverheadPct", op="<=", threshold=12.5, unit="%",
            explain_id="capacity", equation=EQ_CAP,
            why=L(
                standard="Two-failure protection would ride this out at 20–25% overhead. The budget is 12.5%, so the answer has to come from rebuild speed, not from a wider stripe.",
                novice="Stronger protection that survives two failures would solve this easily, but it costs 20% to 25% of everything you buy. The budget here is 12.5%, which only pays for one-failure protection. So the answer has to be a faster repair, not stronger protection.",
                expert="usable/raw ≥ 0.875; forces the rebuild window to carry the risk.",
            ),
        ),
        Criterion(
            id="usable", label="Usable capacity at least 1,000 TB",
            metric="usableTb", op=">=", threshold=1000, unit="TB",
            explain_id="capacity", equation=EQ_CAP,
            why=L(
                standard="The data set needs 1,000 TB usable. Shrinking the cluster until a node rebuilds quickly is not allowed to shrink what it holds.",
                novice="The data needs 1,000 TB of usable space — that is raw capacity minus the share spent on protection. You may make each node smaller so it repairs faster, but the whole cluster still has to hold 1,000 TB.",
                expert="raw × (1 − overhead) ≥ 1,000 TB.",
            ),
        ),
        _below_knee(80),
        _full_run(72),
        _valid_build(),
    ],
    objective=Objective(
        label="Raw capacity bought", metric="rawTb", direction="minimize",
        par=1200, worst=1500, unit="TB", explain_id="capacity", equation=EQ_CAP,
    ),
    hints=[
        L(standard="Run the start and read the event log: the rebuild is still going when the drive fails. Note how many hours it needed.",
          novice="Run the lab as it starts and read the event log under the picture. The repair of the lost node is still running when the drive fails, and that is what loses the data. Look at how many hours the repair would have needed.",
          expert="Read rebuild hours against the 6 h gap."),
        L(standard="Rebuild hours = node TB × 1000 ÷ (rate × 3600), and in scale-out the rate is per surviving node. The node's size is on top of the fraction, the node count underneath.",
          novice="Repair time is the data in the lost node divided by the repair speed. In a scale-out cluster every surviving node helps, so the speed grows with the number of nodes. That gives you two levers: put less data in each node, and have more nodes.",
          expert="t ∝ node_TB / (N − 1)."),
        L(standard="Hold the total and change the shape: the same 1,150–1,200 TB raw as many thin nodes. Splitting it twice as many ways halves the payload and doubles the helpers — the race gets four times easier.",
          novice="Keep the total capacity the same, but build it from many small nodes instead of a few big ones. Twice as many nodes means each holds half as much and twice as many help with the repair, so the repair is about four times faster.",
          expert="Same raw, N↑, node_TB↓: t ∝ 1/N²."),
        L(standard="On PowerScale at 0.5 GB/s per survivor, thirteen nodes of 12 × 7.68 TB rebuild in 6 h and hold 1,048 TB usable from 1,198 TB raw. Sixty fat nodes also survive — at eighteen times the raw capacity.",
          novice="On PowerScale each surviving node repairs at 0.5 GB/s. Thirteen nodes with twelve 7.68 TB drives each finish the repair in 6 hours and still hold 1,048 TB usable out of 1,198 TB raw. A huge cluster of sixty big nodes would also survive, but it costs about eighteen times as much capacity.",
          expert="PowerScale 13 × 12 × 7.68 TB, RAID 5: 6 h rebuild, 1,198 TB raw."),
    ],
    start=_RACE_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [SIZE_FOR_THE_SURVIVOR, FIT_THE_PIPE, WIN_THE_REBUILD_RACE]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Reference solutions and the tricks that must not work -----------------
# Server-side only: GET /api/labs serves LABS, never these.

_PS4 = POWERSTORE_2.model_copy(update={"units": 4})
_ASYNC_300 = POWERMAX_4.model_copy(update={"srdf": "async", "distance_km": 300})
_PIPE_EVENTS = [SimEvent(at_h=24, action="write-burst", value=5)]
_THIN = StorageConfig(
    product="powerscale", units=13, drives_per_unit=12, drive_tb=7.68,
    drive_class="nvme", protection="raid5",
)


def _oltp(k: int, **kw: int) -> Workload:
    return OLTP.model_copy(update={"iops_demand_k": k, **kw})


REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    "size-for-the-survivor": Scenario(
        config=_PS4, workload=_oltp(280), duration_h=72, events=_SURVIVOR_EVENTS,
    ),
    "burst-fits-the-pipe": Scenario(
        config=_ASYNC_300, workload=_oltp(360), duration_h=168, events=_PIPE_EVENTS,
    ),
    "win-the-rebuild-race": Scenario(
        config=_THIN, workload=_RACE_WL, duration_h=72, events=_RACE_EVENTS,
    ),
}

GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "size-for-the-survivor": {
        "zero load": Scenario(
            config=_PS4, workload=_oltp(0), duration_h=72, events=_SURVIVOR_EVENTS),
        "more appliances, same demand": Scenario(
            config=_PS4, workload=_oltp(300), duration_h=72, events=_SURVIVOR_EVENTS),
        "switch to PowerMax, where the failure is a blip": Scenario(
            config=POWERMAX_4, workload=_oltp(280), duration_h=72,
            events=_SURVIVOR_EVENTS),
        "burst before the failure": Scenario(
            config=_PS4, workload=_oltp(320), duration_h=72,
            events=[SimEvent(at_h=2, action="write-burst", value=5),
                    SimEvent(at_h=24, action="fail-controller")]),
        "all-read workload hides the burst": Scenario(
            config=_PS4, workload=_oltp(600, read_pct=100), duration_h=72,
            events=_SURVIVOR_EVENTS),
        "load early, idle through the failure": Scenario(
            config=_PS4, workload=_oltp(1200), duration_h=72,
            events=[SimEvent(at_h=20, action="set-workload", workload=_oltp(20)),
                    *_SURVIVOR_EVENTS]),
        "burst at the last tick": Scenario(
            config=_PS4, workload=_oltp(600), duration_h=72,
            events=[SimEvent(at_h=24, action="fail-controller"),
                    SimEvent(at_h=72, action="write-burst", value=5)]),
        "five appliances": Scenario(
            config=POWERSTORE_2.model_copy(update={"units": 5}),
            workload=_oltp(360), duration_h=72, events=_SURVIVOR_EVENTS),
    },
    "burst-fits-the-pipe": {
        "zero load": Scenario(
            config=_ASYNC_300, workload=_oltp(0), duration_h=168, events=_PIPE_EVENTS),
        "sync, because zero RPO sounds safe": Scenario(
            config=_ASYNC_300.model_copy(update={"srdf": "sync"}),
            workload=_oltp(360), duration_h=168, events=_PIPE_EVENTS),
        "async at the naive demand": Scenario(
            config=_ASYNC_300, workload=_oltp(500), duration_h=168, events=_PIPE_EVENTS),
        "replication off": Scenario(
            config=POWERMAX_4, workload=_oltp(500), duration_h=168, events=_PIPE_EVENTS),
        "move the site closer": Scenario(
            config=_ASYNC_300.model_copy(update={"srdf": "sync", "distance_km": 25}),
            workload=_oltp(360), duration_h=168, events=_PIPE_EVENTS),
        "no burst": Scenario(
            config=_ASYNC_300, workload=_oltp(500), duration_h=168),
        "all-read workload": Scenario(
            config=_ASYNC_300, workload=_oltp(500, read_pct=100), duration_h=168,
            events=_PIPE_EVENTS),
        "idle through the burst": Scenario(
            config=_ASYNC_300, workload=_oltp(20), duration_h=168,
            events=[*_PIPE_EVENTS,
                    SimEvent(at_h=31, action="set-workload", workload=_oltp(800))]),
        "short run": Scenario(
            config=_ASYNC_300, workload=_oltp(360), duration_h=36, events=_PIPE_EVENTS),
    },
    "win-the-rebuild-race": {
        "zero load": Scenario(
            config=_THIN, workload=_oltp(0), duration_h=72, events=_RACE_EVENTS),
        "two-failure protection": Scenario(
            config=_RACE_START.config.model_copy(update={"protection": "ec8+2"}),
            workload=_RACE_WL, duration_h=72, events=_RACE_EVENTS),
        "drive fails long after the rebuild": Scenario(
            config=_RACE_START.config, workload=_RACE_WL, duration_h=168,
            events=[SimEvent(at_h=24, action="fail-node"),
                    SimEvent(at_h=160, action="fail-drive")]),
        "no second failure": Scenario(
            config=_RACE_START.config, workload=_RACE_WL, duration_h=72,
            events=[SimEvent(at_h=24, action="fail-node")]),
        "controller array has no node to lose": Scenario(
            config=POWERSTORE_2.model_copy(update={
                "units": 4, "drives_per_unit": 24, "protection": "raid5"}),
            workload=_RACE_WL, duration_h=72, events=_RACE_EVENTS),
        "thin nodes, too little capacity": Scenario(
            config=_THIN.model_copy(update={"units": 8}),
            workload=_RACE_WL, duration_h=72, events=_RACE_EVENTS),
        "one node short": Scenario(
            config=_THIN.model_copy(update={"units": 11, "drives_per_unit": 14}),
            workload=_RACE_WL, duration_h=72, events=_RACE_EVENTS),
        "short run": Scenario(
            config=_THIN, workload=_RACE_WL, duration_h=28,
            events=[SimEvent(at_h=24, action="fail-node")]),
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
