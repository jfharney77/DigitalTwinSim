"""Graded labs for the PowerVault ME5 RAID physics simulator
(``docs/LAB_PATTERN.md``; pilot: ``DellPowerEdgeR760Thermal``).

A guided scenario sets the dials and tells you what to watch. A lab states a
goal and leaves the dials to you: build a Scenario with the ordinary controls,
the engine runs it, and ``grade_scenario`` scores the trace.

Pure module, same rule as ``engine.py`` and ``validation.py``: no FastAPI, no
IO, no clock, no randomness (AST-checked in ``tests/test_labs.py``). ``main.py``
is the only caller that touches HTTP, and the static-hosting build runs this
same module in the browser, so grading needs no server.

Three things here are this app's own; everything else is ``twinkit.labs``:

* ``measure()`` — turns one run into named numbers. The un-gameable ones are
  the work rates: served kIOPS (and served *write* kIOPS) averaged over every
  tick of the run, offline ticks counting as zero. An idle, saturated-away or
  lost array delivers less, so turning the load down is never a way through.
  They are illustrative proxies for useful storage work, not a benchmark.
* ``LABS`` — three labs of rising difficulty, every criterion citing the
  Explain entry (``presets.EXPLAINS``) and the equation it tests. The
  equations are read from ``EXPLAINS`` so they are verbatim by construction.
* ``REFERENCE_SOLUTIONS`` / ``GAMING_ATTEMPTS`` — a scenario that passes each
  lab, and the cheap tricks that must not. They stay server-side: the API
  serves ``LABS`` only.
"""

from __future__ import annotations

from twinkit.labs import Criterion, Lab, LabGoal, LabResult, Objective, grade

from .engine import simulate
from .leveling import L
from .models import (
    ArrayConfig,
    Scenario,
    SimEvent,
    SimState,
    Summary,
    Validation,
    Workload,
)
from .presets import ALL_FLASH, EXPLAINS, R6_CAPACITY
from .validation import validate

# The equations, exactly as the Explain entries display them.
_EQ = {e.id: e.equation for e in EXPLAINS}
EQ_PENALTY = _EQ["write-penalty"]
EQ_CAPACITY = _EQ["usable-capacity"]
EQ_REBUILD = _EQ["rebuild-time"]
EQ_KNEE = _EQ["latency-knee"]

# "Never happened" for a first-failure time: far past any run the engine
# allows, so an upper-bound criterion fails when the event is missing.
NEVER_MIN = 999999.0


# --- Measurement ----------------------------------------------------------

def measure(
    scenario: Scenario,
    trace: list[SimState],
    summary: Summary,
    validations: list[Validation],
) -> dict[str, float]:
    """One run as named numbers. Keys are the wire names criteria refer to.

    Work is read from what the array *served* on each tick, which already
    reflects every timed workload event the engine applied, so no replay of
    ``set-workload`` / ``set-offered`` is needed here.
    """
    cfg = scenario.config
    n = len(trace)
    hours_per_tick = scenario.tick_minutes / 60.0
    degraded = [s for s in trace if s.drives_failed > 0]
    first_drive = next((float(s.t) for s in trace if s.drives_failed > 0), NEVER_MIN)
    ctrl_down = [s for s in trace if s.controllers_alive < cfg.controllers]
    return {
        "durationMin": float(trace[-1].t),
        "workKiops": round(sum(s.served_kiops for s in trace) / n, 3),
        "writeWorkKiops": round(sum(s.served_write_kiops for s in trace) / n, 3),
        "minServedKiops": round(min(s.served_kiops for s in trace), 3),
        "peakLatencyMs": round(max(s.latency_ms for s in trace), 2),
        "saturatedTicks": float(sum(1 for s in trace if s.saturated)),
        "offlineTicks": float(sum(1 for s in trace if not s.online)),
        "dataLost": 1.0 if summary.data_lost else 0.0,
        "usableTb": float(summary.usable_tb),
        "hotSpares": float(cfg.spares),
        "ssdDrives": float(cfg.drive_count if cfg.drive_type == "ssd" else 0),
        "catalogWarnings": float(sum(
            1 for v in validations
            if v.rule_id == "drive-catalog" and v.level != "ok"
        )),
        "validationErrors": float(sum(1 for v in validations if v.level == "error")),
        "firstDriveFailureMin": first_drive,
        "maxDrivesFailed": float(max(s.drives_failed for s in trace)),
        "finalDrivesFailed": float(trace[-1].drives_failed),
        "rebuildHours": float(summary.rebuild_hours_total),
        "degradedHours": round(len(degraded) * hours_per_tick, 2),
        "exposureIndexHours": round(
            sum(s.risk_index for s in trace) * hours_per_tick, 1
        ),
        "controllerDownHours": round(len(ctrl_down) * hours_per_tick, 2),
    }


# --- Criteria shared between labs ------------------------------------------

def _never_saturated() -> Criterion:
    return Criterion(
        id="never-saturated", label="Never saturated: every asked I/O is served",
        metric="saturatedTicks", op="<=", threshold=0, unit="ticks", weight=2.0,
        explain_id="write-penalty", equation=EQ_PENALTY,
        why=L(
            standard=(
                "The drives have a fixed budget of disk I/Os. Reads cost 1 "
                "each (about 2 while a parity group is degraded) and writes "
                "cost the RAID penalty. When the asked load costs more than "
                "the budget, the array serves less than it was asked for and "
                "the saturation flag goes up. One saturated tick fails this "
                "line."
            ),
            novice=(
                "Every drive can only do so many operations per second, and "
                "the drives together make up the array's budget. A read "
                "spends one operation. A write spends several, because the "
                "array also has to update its protection data: 2 for "
                "mirrors, 4 for RAID 5, 6 for RAID 6. If the servers ask "
                "for more than the budget covers, the array cannot keep up "
                "and some requests simply wait. That is called saturation. "
                "This line fails if it happens even once during the run, so "
                "watch the 'saturated' readout and the rules panel."
            ),
            expert=(
                "reads × read_cost + writes × wp ≤ budget on every tick; "
                "zero saturated ticks."
            ),
        ),
    )


def _latency(ms: float) -> Criterion:
    return Criterion(
        id="latency", label=f"Peak latency {ms:g} ms or less",
        metric="peakLatencyMs", op="<=", threshold=ms, unit="ms", weight=2.0,
        explain_id="latency-knee", equation=EQ_KNEE,
        why=L(
            standard=(
                f"Latency is the drive's service time divided by (1 − "
                f"utilization), plus overheads: flat until about 70% busy, "
                f"vertical past 90%. The cap is {ms:g} ms at the worst moment "
                "of the run, so the busiest tick decides this line — "
                "including degraded and failover ticks, which add their own "
                "milliseconds."
            ),
            novice=(
                f"Latency is how long one request waits for its answer, and "
                f"this lab allows at most {ms:g} ms at the worst moment. A "
                "drive that is half busy answers almost as fast as an idle "
                "one. A drive that is nearly always busy makes every request "
                "queue behind the others, and the wait shoots up — like a "
                "motorway that flows fine until it is almost full and then "
                "stops. So the question is not only 'can the drives do the "
                "work' but 'how busy does that make them'. Watch the disk "
                "utilization readout: past about 70% the latency climbs "
                "fast."
            ),
            expert=f"max(S/(1−ρ) + overheads) ≤ {ms:g} ms; degraded and failover terms included.",
        ),
    )


def _spinning_only() -> Criterion:
    return Criterion(
        id="spinning-only", label="Spinning drives only (no SSDs in the budget)",
        metric="ssdDrives", op="<=", threshold=0, unit="SSDs",
        explain_id="write-penalty", equation=EQ_PENALTY,
        why=L(
            standard=(
                "An SSD delivers roughly a hundred times a spindle's IOPS, "
                "which makes every budget problem disappear. This lab's "
                "budget is hard drives, so the RAID arithmetic has to do the "
                "work."
            ),
            novice=(
                "Solid-state drives (SSDs) are about a hundred times faster "
                "than spinning hard drives, so buying them would make this "
                "problem vanish without teaching anything. They also cost "
                "far more per terabyte. This lab's budget only covers "
                "spinning hard drives (the 10k or 7.2k kinds), so you have "
                "to solve it with the RAID level and the drive choice."
            ),
            expert="HDD only; the per-drive IOPS budget stays the binding term.",
        ),
    )


def _real_parts() -> Criterion:
    return Criterion(
        id="real-parts", label="Only drives Dell lists for this enclosure",
        metric="catalogWarnings", op="<=", threshold=0, unit="warnings",
        explain_id="usable-capacity", equation=EQ_CAPACITY,
        why=L(
            standard=(
                "The rules panel warns when a drive is not one Dell sells "
                "for the enclosure: 10k SAS above 2 TB, 7.2k NL-SAS in the "
                "24-bay 2.5-inch ME5024, SSDs above 8 TB. The simulator lets "
                "you build them to show the arithmetic; the lab does not "
                "count them."
            ),
            novice=(
                "The simulator will let you build drives that do not exist, "
                "such as a fast 10k drive that is also 20 TB, so you can see "
                "the arithmetic. The rules panel on the left marks those "
                "builds with a yellow 'illustrative' warning. In this lab "
                "they do not count. Fast 10k drives stop at 2 TB, the big "
                "7.2k drives only fit the 12-bay ME5012 enclosure, and SSDs "
                "stop at 8 TB."
            ),
            expert="Zero drive-catalog warnings: 10k ≤ 2 TB, 7.2k in ME5012 only, SSD ≤ 8 TB.",
        ),
    )


def _valid_build() -> Criterion:
    return Criterion(
        id="valid-build", label="Build has no configuration errors",
        metric="validationErrors", op="<=", threshold=0, unit="errors",
        explain_id="usable-capacity", equation=EQ_CAPACITY,
        why=L(
            standard=(
                "Errors in the rules panel are builds that cannot exist: "
                "more drives than the enclosure has slots, or too few "
                "members for the RAID level. Warnings are allowed; errors "
                "are not."
            ),
            novice=(
                "The rules panel on the left checks your build. A red error "
                "means the array could not be built at all, for example "
                "more drives than the box has slots, or too few drives for "
                "the RAID level you chose. Yellow warnings are allowed in a "
                "lab. Red errors are not."
            ),
            expert="Zero error-level findings (slots, RAID membership).",
        ),
    )


def _no_loss() -> Criterion:
    return Criterion(
        id="no-loss", label="No data loss; the array never goes offline",
        metric="offlineTicks", op="<=", threshold=0, unit="ticks", weight=3.0,
        explain_id="rebuild-time", equation=EQ_REBUILD,
        why=L(
            standard=(
                "Inside the rebuild window a RAID 5 or mirrored group has no "
                "redundancy left, and RAID 6 has one parity in hand. A "
                "failure beyond the tolerance takes the array offline with "
                "data loss, and an offline array serves nothing for the rest "
                "of the run. Losing the last controller does the same."
            ),
            novice=(
                "While the array is rebuilding a failed drive, it has less "
                "protection than usual, or none. RAID 5 and mirrors can "
                "survive one failed drive, so a second failure before the "
                "rebuild finishes destroys the data. RAID 6 can survive two. "
                "When the data is lost the array goes offline and stays "
                "offline, and an offline array does no work. The same "
                "happens if the only working controller fails. This line "
                "needs the array online on every tick of the run."
            ),
            expert="Failures outstanding ≤ tolerance and ≥ 1 controller on every tick.",
        ),
    )


def _drive_fails_early() -> Criterion:
    return Criterion(
        id="drive-fails-early", label="A drive fails within the first 60 minutes",
        metric="firstDriveFailureMin", op="<=", threshold=60, unit="min",
        explain_id="rebuild-time", equation=EQ_REBUILD,
        why=L(
            standard=(
                "The lab is about the rebuild window, so a member drive has "
                "to fail early enough for the whole window to fit in the "
                "run. The start scenario fails slot 1 at t+60; if your "
                "change removed that event, click a healthy drive to fail "
                "it again."
            ),
            novice=(
                "This lab only means something if a drive actually breaks. "
                "The lab starts with a drive set to fail one hour in. If you "
                "press Reset or otherwise lose that event, drag the time "
                "slider to the first hour and click a healthy drive in the "
                "picture to fail it again. A run with no failure, or one "
                "where the drive fails at the very end, does not pass."
            ),
            expert="First member failure at t ≤ 60 min, measured from the trace.",
        ),
    )


def _protection_restored() -> Criterion:
    return Criterion(
        id="protection-restored", label="Every rebuild finishes before the run ends",
        metric="finalDrivesFailed", op="<=", threshold=0, unit="drives", weight=2.0,
        explain_id="rebuild-time", equation=EQ_REBUILD,
        why=L(
            standard=(
                "A rebuild needs somewhere to go: a hot spare, or a "
                "replacement inserted by hand. Each failed member needs its "
                "own, and rebuilds run one at a time. At the last tick no "
                "member may still be failed or rebuilding."
            ),
            novice=(
                "After a drive fails, the array copies the missing data onto "
                "a spare drive. That only starts if a spare is waiting (the "
                "'spares' setting), or if you click the failed drive to put "
                "a fresh one in. Each failed drive needs its own spare, and "
                "the array rebuilds them one after another. By the end of "
                "the run every rebuild must be finished, so the array is "
                "fully protected again."
            ),
            expert="drives_failed = 0 at the final tick; one spare or replacement per failure.",
        ),
    )


# --- Lab 1: pay the write tax ----------------------------------------------

_VDI_LIGHT = Workload(offered_kiops=1.0, read_pct=40, block_kb=4)

_TAX_START = Scenario(
    config=ArrayConfig(), workload=_VDI_LIGHT, duration_min=120, tick_minutes=1,
)

WRITE_TAX = Lab(
    id="pay-the-write-tax",
    title="Pay the write tax",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "A write-heavy desktop workload lands on 24 spinning drives. "
                "Serve at least 0.6 kIOPS of writes without saturating and "
                "with peak latency of 25 ms or less, keep a hot spare — and "
                "then keep as many usable terabytes as you can."
            ),
            novice=(
                "Lots of office desktops are saving their work to this "
                "array, so most of the traffic is writes. Your array has "
                "spinning hard drives only. It has to keep up with at least "
                "0.6 thousand writes per second, never fall behind, and "
                "answer every request within 25 ms even at its busiest. It "
                "also has to keep one spare drive ready. Once all of that "
                "works, the real game starts: different RAID levels leave "
                "you different amounts of space, so find the layout that "
                "passes and keeps the most usable terabytes."
            ),
            expert=(
                "HDD only, ≥1 spare, write work ≥ 0.6 kIOPS, zero saturated "
                "ticks, peak latency ≤ 25 ms; maximize usable TB."
            ),
        ),
        constraints=[
            L(standard="Spinning drives only, and only drives Dell lists for the enclosure.",
              novice="No SSDs, and no drives with a yellow 'illustrative' warning in the rules panel.",
              expert="HDD, zero drive-catalog warnings."),
            L(standard="At least one hot spare; no configuration errors.",
              novice="Keep the 'spares' setting at 1 or more, and no red errors in the rules panel.",
              expert="spares ≥ 1, zero errors."),
            L(standard="Never saturated; peak latency 25 ms or less; run at least 120 minutes.",
              novice="The array must never fall behind, its slowest moment must be 25 ms or faster, and the run must last at least two hours.",
              expert="0 saturated ticks, max latency ≤ 25 ms, duration ≥ 120 min."),
        ],
        delivered_work=L(
            standard="At least 0.6 kIOPS of served writes, averaged over the whole run.",
            novice="The array must actually save at least 0.6 thousand writes per second on average, for example 1 kIOPS of traffic that is 60% writes. Reads do not count toward this, and an idle array does not count at all.",
            expert="writeWorkKiops ≥ 0.6.",
        ),
    ),
    criteria=[
        Criterion(
            id="write-work", label="Served writes at least 0.6 kIOPS",
            metric="writeWorkKiops", op=">=", threshold=0.6, unit="kIOPS",
            weight=2.0, guards_work=True,
            explain_id="write-penalty", equation=EQ_PENALTY,
            why=L(
                standard=(
                    "Work here is served write kIOPS averaged over every "
                    "tick of the run; 0.6 is the floor. Writes are the I/Os "
                    "the RAID level taxes, so turning the mix toward reads "
                    "or turning the load down is not a way through. The "
                    "proxy is illustrative, not a benchmark."
                ),
                novice=(
                    "The array has to do real work: at least 0.6 thousand "
                    "writes saved per second, averaged over the whole run. "
                    "We count writes because writes are what the RAID level "
                    "makes expensive. If you slide the mix toward reads, or "
                    "turn the load down, the array gets an easy life but "
                    "this number drops and the line fails. It is a simple "
                    "stand-in for useful storage work, not a real benchmark "
                    "score."
                ),
                expert="Mean served write kIOPS over all ticks ≥ 0.6. Illustrative proxy.",
            ),
        ),
        _never_saturated(),
        _latency(25),
        Criterion(
            id="hot-spare", label="At least one hot spare",
            metric="hotSpares", op=">=", threshold=1, unit="drives",
            explain_id="usable-capacity", equation=EQ_CAPACITY,
            why=L(
                standard=(
                    "A spare holds no data and adds no IOPS: it is one "
                    "drive's worth of raw capacity set aside so a rebuild "
                    "can start the moment a member fails. Dropping it buys "
                    "back 2 TB and a little budget, and is not allowed here."
                ),
                novice=(
                    "A hot spare is an empty drive that sits in the box "
                    "doing nothing until another drive breaks, and then "
                    "takes its place straight away. It costs you one "
                    "drive's worth of space and speed. Removing it would "
                    "make this lab a little easier, which is why the lab "
                    "insists you keep at least one."
                ),
                expert="spares ≥ 1; the spare is outside the group's budget and capacity.",
            ),
        ),
        _spinning_only(),
        _real_parts(),
        Criterion(
            id="full-run", label="Run lasts at least 120 minutes",
            metric="durationMin", op=">=", threshold=120, unit="min",
            explain_id="latency-knee", equation=EQ_KNEE,
            why=L(
                standard=(
                    "The work floor is a rate over the run, and the latency "
                    "cap is the worst tick in it. Two hours is the run this "
                    "lab grades."
                ),
                novice=(
                    "The lab measures an average over the run and the single "
                    "slowest moment in it, so it needs a run of a fair "
                    "length. Leave the Duration slider at two hours or more."
                ),
                expert="duration ≥ 120 min.",
            ),
        ),
        _valid_build(),
    ],
    objective=Objective(
        label="Usable capacity", metric="usableTb",
        direction="maximize", par=44, worst=22, unit="TB",
        explain_id="usable-capacity", equation=EQ_CAPACITY,
    ),
    hints=[
        L(standard="Open the rules panel and the write-penalty readout. The start build is RAID 6: every host write costs 6 disk I/Os, and 23 × 170 IOPS of drives cannot pay for 600 writes and 400 reads.",
          novice="Look at the rules panel on the left and the 'write penalty' number in the instruments. The lab starts on RAID 6, where every write costs 6 drive operations. The 23 working drives manage about 170 operations a second each, and that is not enough for this many writes, so the array falls behind.",
          expert="R6: 400 + 600 × 6 = 4000 > 23 × 170 = 3910. Saturated."),
        L(standard="RAID 10 cuts the tax to ×2 and passes easily — but a mirror gives half the raw capacity to protection. The objective is usable TB, so ask what the cheapest tax is that still fits.",
          novice="RAID 10 (mirroring) makes each write cost only 2 operations, so the array keeps up easily. But mirroring keeps a full second copy of everything, so you only get to use half the space you bought. The score rewards usable space. Is there a RAID level that costs less space than a mirror and still keeps up?",
          expert="R10 passes at ρ ≈ 0.43 but usable = n/2. Objective is usable TB."),
        L(standard="RAID 5 pays ×4: 400 + 600 × 4 = 2800 disk I/Os on a 3910 budget is 72% busy, which is about 21 ms — just under the knee — and it keeps n − 1 members' worth of capacity.",
          novice="Try RAID 5. Each write costs 4 operations, so the total is 400 + 600 × 4 = 2800, and the drives can do 3910. That makes them about 72% busy, which gives roughly 21 ms at worst: inside the 25 ms limit, though not by much. And RAID 5 only gives up one drive's worth of space, so you keep about twice the usable terabytes of the mirror.",
          expert="R5 + 1 spare: ρ = 0.72, ≈ 21 ms, usable = (n − 1) × TB = 44 TB."),
    ],
    start=_TAX_START.model_dump(by_alias=True),
)


# --- Lab 2: close the window ------------------------------------------------

_ARCHIVE_LOAD = Workload(offered_kiops=0.3, read_pct=95, block_kb=64)
_FAIL_FIRST = [SimEvent(at_min=60, action="fail-drive", index=0)]

_WINDOW_START = Scenario(
    config=R6_CAPACITY, workload=_ARCHIVE_LOAD,
    duration_min=10080, tick_minutes=10, events=_FAIL_FIRST,
)

CLOSE_THE_WINDOW = Lab(
    id="close-the-window",
    title="Close the rebuild window",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "A 12-bay archive array loses a drive in its first hour. "
                "Keep at least 100 TB usable, keep serving at least 0.2 "
                "kIOPS through the rebuild, and have protection back within "
                "96 rebuild hours — then make the week's exposure to a "
                "second failure as small as you can."
            ),
            novice=(
                "This array is a big, slow archive, and one of its drives "
                "breaks an hour into the week. The array then has to rebuild "
                "the missing data onto a spare while still serving its "
                "users. Until that finishes, another broken drive is far "
                "more dangerous than usual. Your job: keep at least 100 TB "
                "of usable space, never serve less than 0.2 thousand "
                "requests per second, and finish rebuilding within 96 "
                "hours. After that, the score rewards the smallest total "
                "danger over the week, shown by the exposure gauge."
            ),
            expert=(
                "HDD, usable ≥ 100 TB, min served ≥ 0.2 kIOPS, failure at "
                "t ≤ 60 min, rebuild ≤ 96 h and complete; minimize Σ exposure·dt."
            ),
        ),
        constraints=[
            L(standard="A member drive fails within the first 60 minutes, and its rebuild finishes inside the run in 96 hours or less.",
              novice="A drive must break in the first hour (the lab sets this up for you), and the rebuild must be completely finished within 96 hours.",
              expert="First failure ≤ 60 min; rebuild hours ≤ 96; 0 failed at end."),
            L(standard="At least 100 TB usable, on spinning drives Dell lists for the enclosure; no configuration errors.",
              novice="Keep at least 100 TB of usable space. No SSDs, no drives with a yellow 'illustrative' warning, and no red errors.",
              expert="usable ≥ 100 TB, HDD, zero catalog warnings, zero errors."),
            L(standard="Never saturated, never offline, no data loss.",
              novice="The array must never fall behind, never go offline, and never lose data.",
              expert="0 saturated ticks, 0 offline ticks."),
        ],
        delivered_work=L(
            standard="At least 0.2 kIOPS served on average, and never less than 0.2 kIOPS on any tick — including every tick of the rebuild.",
            novice="The array must serve at least 0.2 thousand requests per second the whole time, on average and at every single moment. That includes the days it spends rebuilding, so you cannot switch the users off to make the rebuild go faster.",
            expert="workKiops ≥ 0.2 and minServedKiops ≥ 0.2.",
        ),
    ),
    criteria=[
        Criterion(
            id="work", label="Served load at least 0.2 kIOPS on average",
            metric="workKiops", op=">=", threshold=0.2, unit="kIOPS",
            weight=2.0, guards_work=True,
            explain_id="rebuild-time", equation=EQ_REBUILD,
            why=L(
                standard=(
                    "Work is served kIOPS averaged over every tick, offline "
                    "ticks counting as zero; 0.2 is the floor. Host load is "
                    "the 'load' term that slows the rebuild, so an idle "
                    "array would rebuild fastest — and fail this line. "
                    "Illustrative proxy, not a benchmark."
                ),
                novice=(
                    "The array has to keep doing its job: at least 0.2 "
                    "thousand requests served per second, averaged over the "
                    "whole week. A busy array rebuilds more slowly, so it is "
                    "tempting to turn the users off. This line is what stops "
                    "that. It is a simple stand-in for useful storage work, "
                    "not a real benchmark score."
                ),
                expert="Mean served kIOPS ≥ 0.2, dark ticks zero. Illustrative proxy.",
            ),
        ),
        Criterion(
            id="serves-throughout", label="Never serves less than 0.2 kIOPS",
            metric="minServedKiops", op=">=", threshold=0.2, unit="kIOPS",
            weight=2.0, guards_work=True,
            explain_id="rebuild-time", equation=EQ_REBUILD,
            why=L(
                standard=(
                    "The rebuild rate is derated by up to half as host "
                    "utilization rises. Idling through the rebuild and "
                    "catching up afterwards would dodge that term, so the "
                    "floor applies to every tick, not only to the average."
                ),
                novice=(
                    "Here is a trick that does not work: leave the array "
                    "idle while it rebuilds, so the rebuild is quick, and "
                    "then make up the work later. Real users do not wait "
                    "four days. So the lab checks the quietest moment of "
                    "the run too, and it must still be at least 0.2 "
                    "thousand requests per second."
                ),
                expert="min over ticks of served kIOPS ≥ 0.2; closes idle-through-rebuild.",
            ),
        ),
        _drive_fails_early(),
        Criterion(
            id="window", label="Rebuild takes 96 hours or less",
            metric="rebuildHours", op="<=", threshold=96, unit="h", weight=2.0,
            explain_id="rebuild-time", equation=EQ_REBUILD,
            why=L(
                standard=(
                    "Hours are drive TB × 1000 over the effective rate: "
                    "about 50 MB/s for a spindle, derated by up to half as "
                    "host load rises. The window scales with the size of "
                    "one drive, not with the size of the array, and the "
                    "RAID level does not appear in it at all."
                ),
                novice=(
                    "How long a rebuild takes depends on how much data one "
                    "drive holds and how fast the array can copy. A spinning "
                    "drive rebuilds at about 50 MB per second, and slower "
                    "when the array is busy with users. So a 20 TB drive "
                    "takes roughly twice as long as a 10 TB drive would. "
                    "Notice what is not in the sum: the RAID level, and the "
                    "number of drives. Only the size of a single drive, the "
                    "copy speed, and how busy the array is."
                ),
                expert="TB × 1000 ÷ (rate × (1 − 0.5u) × 3.6) ≤ 96 h. Linear in drive TB.",
            ),
        ),
        _protection_restored(),
        Criterion(
            id="capacity", label="At least 100 TB usable",
            metric="usableTb", op=">=", threshold=100, unit="TB", weight=2.0,
            explain_id="usable-capacity", equation=EQ_CAPACITY,
            why=L(
                standard=(
                    "Usable is raw minus protection overhead minus spares. "
                    "Smaller drives shorten the window but shrink raw "
                    "capacity, and the 12-bay enclosure fixes the drive "
                    "count — so the capacity floor decides how small the "
                    "drives can get."
                ),
                novice=(
                    "Usable space is what is left after protection and "
                    "spares take their share. Smaller drives rebuild faster, "
                    "but twelve small drives hold less than twelve big ones, "
                    "and this box only has twelve slots. So this line and "
                    "the 96-hour line pull in opposite directions: find the "
                    "drive size that satisfies both."
                ),
                expert="usable = raw − overhead − spares ≥ 100 TB at n ≤ 12.",
            ),
        ),
        _never_saturated(),
        _no_loss(),
        _spinning_only(),
        _real_parts(),
        _valid_build(),
    ],
    objective=Objective(
        label="Exposure over the run (exposure index × hours)",
        metric="exposureIndexHours",
        direction="minimize", par=520, worst=3300, unit="index·h",
        explain_id="rebuild-time", equation=EQ_REBUILD,
    ),
    hints=[
        L(standard="Watch 'rebuild hours remaining' on the start build: 20 TB at 50 MB/s is 111 hours unloaded, and the host load stretches it past 150. The window follows the size of one drive.",
          novice="Play the starting build and watch the 'rebuild hours remaining' number. One 20 TB drive at 50 MB per second takes about 111 hours even with no users, and with users it is over 150. That is far more than the 96 hours allowed. The time depends on the size of one drive.",
          expert="20 TB ÷ 50 MB/s ≈ 111 h at u = 0; > 150 h under load."),
        L(standard="Two floors squeeze the drive size: 96 hours from above, 100 TB usable from below, in a 12-bay box. Then look at the load term: every kIOPS you serve beyond the floor slows the rebuild, and reads cost 2 while the group is degraded.",
          novice="Two rules pull against each other. Smaller drives rebuild faster, but twelve of them must still add up to 100 TB of usable space. Try the drive sizes between 8 and 20 TB. Then look at the workload: the busier the array, the slower the rebuild, so serve what the lab asks for and no more. While a drive is missing, each read costs the drives double.",
          expert="TB bounded by window above, capacity below; u enters via (1 − 0.5u) with degraded read_cost = 2."),
        L(standard="12 TB drives meet both floors on RAID 5 and on RAID 6. The window is the same length either way; what differs is what a second failure costs inside it. The exposure gauge weights RAID 6's hours at 0.15 of RAID 5's.",
          novice="12 TB drives pass both rules, and they pass on RAID 5 and on RAID 6. The rebuild takes about as long on either. The difference is the danger while it runs: on RAID 5 one more failure loses everything, while RAID 6 still has one layer of protection left. The exposure gauge counts RAID 6's hours as far less dangerous, so RAID 6 with 12 TB drives, one spare, and 0.2 kIOPS of load scores best.",
          expert="12 × 12 TB R6 + 1 spare at 0.2 kIOPS: 108 TB, ≈ 92 h, factor 0.15 vs 1.0."),
    ],
    start=_WINDOW_START.model_dump(by_alias=True),
)


# --- Lab 3: size for the worst day -----------------------------------------

_BAD_WEEK = [
    SimEvent(at_min=60, action="fail-drive", index=0),
    SimEvent(at_min=240, action="fail-drive", index=1),
    SimEvent(at_min=480, action="fail-controller"),
]
_FLASH_ASK = Workload(offered_kiops=170.0, read_pct=70, block_kb=8)

_WORST_DAY_START = Scenario(
    config=ALL_FLASH, workload=_FLASH_ASK,
    duration_min=4320, tick_minutes=5, events=_BAD_WEEK,
)

WORST_DAY = Lab(
    id="size-for-the-worst-day",
    title="Size for the worst day",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "An all-flash array has a bad three days: one drive fails, a "
                "second fails while the first is still rebuilding, and then "
                "a controller drops and stays down. Lose nothing, never "
                "saturate, keep peak latency at 6 ms or less, end fully "
                "protected — and serve as many kIOPS as you can, at least 80 "
                "on every tick with at least 20 of them writes."
            ),
            novice=(
                "This array is built from fast SSDs, and it has a terrible "
                "three days. A drive breaks. A second drive breaks while "
                "the first is still being rebuilt. Then one of the two "
                "controllers (the array's brains) fails and stays failed. "
                "Through all of it the array must not lose data, must never "
                "fall behind, and must answer within 6 ms even at the worst "
                "moment. By the end, both rebuilds must be finished. It must "
                "serve at least 80 thousand requests per second at every "
                "moment, with at least 20 thousand of them writes on "
                "average. Beyond that, the more it serves the better the "
                "score. The trick is that the array is much weaker on its "
                "worst day than on a good one, and you have to plan for the "
                "worst day."
            ),
            expert=(
                "Two overlapping member failures + a persistent controller "
                "loss; 0 offline/saturated ticks, max latency ≤ 6 ms, 0 "
                "failed at end, min served ≥ 80 k, write work ≥ 20 k; "
                "maximize mean served kIOPS."
            ),
        ),
        constraints=[
            L(standard="A drive fails within 60 minutes, two members are failed at the same time at some point, and a controller is down for at least 48 hours.",
              novice="The bad days must really happen: a drive fails in the first hour, a second one fails before the first rebuild is done, and one controller is down for at least 48 hours. The lab sets all three up for you; do not remove them.",
              expert="First failure ≤ 60 min; max concurrent failed ≥ 2; controller-down ≥ 48 h."),
            L(standard="No data loss, never offline, never saturated, peak latency 6 ms or less.",
              novice="No lost data, never offline, never falling behind, and the slowest moment of the whole run must be 6 ms or faster.",
              expert="0 offline ticks, 0 saturated ticks, max latency ≤ 6 ms."),
            L(standard="Both rebuilds finish before the run ends; only SSDs Dell lists; no configuration errors.",
              novice="By the end of the run no drive may still be failed or rebuilding. No drives with a yellow 'illustrative' warning, and no red errors.",
              expert="0 failed at end; zero catalog warnings; zero errors."),
        ],
        delivered_work=L(
            standard="Never less than 80 kIOPS served on any tick, and at least 20 kIOPS of served writes on average over the run.",
            novice="At every moment the array must serve at least 80 thousand requests per second, and over the whole run at least 20 thousand per second of them must be writes. Turning the load down for the bad hours does not pass.",
            expert="minServedKiops ≥ 80; writeWorkKiops ≥ 20.",
        ),
    ),
    criteria=[
        Criterion(
            id="work", label="Never serves less than 80 kIOPS",
            metric="minServedKiops", op=">=", threshold=80, unit="kIOPS",
            weight=2.0, guards_work=True,
            explain_id="write-penalty", equation=EQ_PENALTY,
            why=L(
                standard=(
                    "The floor applies to the quietest tick of the run, "
                    "offline ticks counting as zero, so the load cannot be "
                    "turned down for the degraded hours and back up "
                    "afterwards. Illustrative proxy, not a benchmark."
                ),
                novice=(
                    "The array must serve at least 80 thousand requests per "
                    "second at every single moment of the run, including "
                    "the worst ones. You cannot turn the users down while "
                    "drives are broken and turn them up again later, and an "
                    "array that has gone offline serves nothing. It is a "
                    "simple stand-in for useful storage work, not a real "
                    "benchmark score."
                ),
                expert="min over ticks of served kIOPS ≥ 80; dark ticks zero. Illustrative proxy.",
            ),
        ),
        Criterion(
            id="write-work", label="Served writes at least 20 kIOPS on average",
            metric="writeWorkKiops", op=">=", threshold=20, unit="kIOPS",
            weight=2.0, guards_work=True,
            explain_id="write-penalty", equation=EQ_PENALTY,
            why=L(
                standard=(
                    "Writes are the I/Os the RAID level taxes — ×6 on the "
                    "only level that survives this week — so an all-read "
                    "mix would dodge the arithmetic. 20 kIOPS of served "
                    "writes, averaged over every tick, keeps the tax in the "
                    "problem."
                ),
                novice=(
                    "Writes are the expensive kind of request, because the "
                    "array must also update its protection data. If you "
                    "slid the mix to 100% reads the problem would get much "
                    "easier, and much less real. So the lab needs at least "
                    "20 thousand writes served per second on average."
                ),
                expert="Mean served write kIOPS ≥ 20; keeps wp in the budget.",
            ),
        ),
        _no_loss(),
        _never_saturated(),
        _latency(6),
        _protection_restored(),
        _drive_fails_early(),
        Criterion(
            id="double-failure", label="Two members failed at the same time",
            metric="maxDrivesFailed", op=">=", threshold=2, unit="drives",
            explain_id="rebuild-time", equation=EQ_REBUILD,
            why=L(
                standard=(
                    "The second failure has to land inside the first "
                    "rebuild window — that is the event RAID 6 exists for. "
                    "A second failure after the first rebuild completes is "
                    "just two single failures."
                ),
                novice=(
                    "The second drive must break while the first one is "
                    "still being rebuilt, so that two drives are missing at "
                    "once. That is the dangerous case. If the second drive "
                    "only breaks after the first rebuild has finished, the "
                    "array never faced the real test, and this line fails."
                ),
                expert="max concurrent outstanding failures ≥ 2.",
            ),
        ),
        Criterion(
            id="controller-down", label="A controller is down for at least 48 hours",
            metric="controllerDownHours", op=">=", threshold=48, unit="h",
            explain_id="latency-knee", equation=EQ_KNEE,
            why=L(
                standard=(
                    "On one controller the front-end ceiling halves, write "
                    "cache drops to write-through and every I/O carries a "
                    "failover term — one of the overheads in the latency "
                    "sum. Restoring the controller early, or starting with "
                    "one so there is nothing to lose, does not count."
                ),
                novice=(
                    "The array normally has two controllers sharing the "
                    "work. When one fails the other takes over everything: "
                    "the array can carry only half as much traffic, and "
                    "every request takes a little longer. The lab needs "
                    "that to be true for at least 48 hours. Clicking the "
                    "controller to bring it straight back does not count, "
                    "and neither does building the array with a single "
                    "controller to begin with."
                ),
                expert="controllers_alive < configured for ≥ 48 h; failover term in the latency sum.",
            ),
        ),
        _real_parts(),
        _valid_build(),
    ],
    objective=Objective(
        label="Served load, averaged over the run", metric="workKiops",
        direction="maximize", par=100, worst=80, unit="kIOPS",
        explain_id="write-penalty", equation=EQ_PENALTY,
    ),
    hints=[
        L(standard="Play the start build and read the log. 170 kIOPS fits the healthy array, the rules panel says so, and it saturates the moment a member fails. The rules panel sizes the good day; the grade is taken on the worst one.",
          novice="Play the starting build and read the event log under the picture. The rules panel says the load fits, and on a healthy array it does. But as soon as a drive fails the array falls behind. The rules panel only checks the good day. The lab grades the worst day.",
          expert="Validation sizes the healthy budget; the binding state is 2 failed + rebuilding."),
        L(standard="Only one RAID level is online after two overlapping failures, and it is the ×6 one. RAID 10's cheap writes are tempting; the model takes the unlucky mirror. And each failed drive needs its own spare, or the second rebuild never starts.",
          novice="Try the other RAID levels and watch what the second failure does. RAID 5 and RAID 10 both lose the data (for RAID 10 the simulator always assumes the unlucky case, and says so). Only RAID 6 survives two missing drives, and RAID 6 has the most expensive writes. Also look at the 'spares' setting: one spare only covers one failure, so the second rebuild never starts.",
          expert="R6 only; spares ≥ 2 or the second failure never rebuilds."),
        L(standard="Do the worst-day sum: 21 serving SSDs × 20k IOPS, minus the 20% rebuild reserve, with reads costing 2 and writes 6. Then keep the drives under about 75% busy so the knee stays inside 6 ms. Around 100 kIOPS at an 80/20 mix fits; 110 does not.",
          novice="Work out the worst day. Two drives are missing, so 21 SSDs are working, each good for about 20 thousand operations a second. The rebuild takes a fifth of that for itself. Every read now costs 2 operations, because the missing data has to be worked out from the other drives, and every write costs 6. On top of that the drives must stay under about 75% busy, or the waiting time goes over 6 ms. A load of about 100 thousand requests per second with 80% reads and 20% writes just fits. 110 thousand does not.",
          expert="21 × 20k × 0.8 budget; cost = 2r + 6w; ρ ≲ 0.75 incl. reserve → ≈ 100 k at 80/20."),
    ],
    start=_WORST_DAY_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [WRITE_TAX, CLOSE_THE_WINDOW, WORST_DAY]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Reference solutions and the tricks that must not work -----------------
# Server-side only: GET /api/labs serves LABS, never these.

_R5_24 = ArrayConfig(raid_level="5")
_R6_12TB = R6_CAPACITY.model_copy(update={"drive_tb": 12})
_FLASH_2_SPARES = ALL_FLASH.model_copy(update={"spares": 2})
_WORST_DAY_LOAD = Workload(offered_kiops=100.0, read_pct=79, block_kb=8)

REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    "pay-the-write-tax": Scenario(
        config=_R5_24, workload=_VDI_LIGHT, duration_min=120, tick_minutes=1,
    ),
    "close-the-window": Scenario(
        config=_R6_12TB,
        workload=Workload(offered_kiops=0.2, read_pct=95, block_kb=64),
        duration_min=10080, tick_minutes=10, events=_FAIL_FIRST,
    ),
    "size-for-the-worst-day": Scenario(
        config=_FLASH_2_SPARES, workload=_WORST_DAY_LOAD,
        duration_min=4320, tick_minutes=5, events=_BAD_WEEK,
    ),
}

_ZERO = Workload(offered_kiops=0.0, read_pct=70, block_kb=8)

GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "pay-the-write-tax": {
        "zero load": Scenario(config=_R5_24, workload=_ZERO, duration_min=120),
        "all reads": Scenario(
            config=_R5_24,
            workload=Workload(offered_kiops=3.0, read_pct=100, block_kb=4),
            duration_min=120),
        "buy SSDs": Scenario(
            config=ArrayConfig(drive_type="ssd", drive_tb=8, raid_level="5"),
            workload=_VDI_LIGHT, duration_min=120),
        "10k drives that do not exist": Scenario(
            config=ArrayConfig(drive_tb=20, raid_level="10"),
            workload=_VDI_LIGHT, duration_min=120),
        "drop the spare": Scenario(
            config=ArrayConfig(raid_level="5", spares=0),
            workload=_VDI_LIGHT, duration_min=120),
        "overdrive a saturated array": Scenario(
            config=ArrayConfig(),
            workload=Workload(offered_kiops=50.0, read_pct=0, block_kb=4),
            duration_min=120),
        "short run": Scenario(config=_R5_24, workload=_VDI_LIGHT, duration_min=10),
    },
    "close-the-window": {
        "zero load": Scenario(
            config=_R6_12TB, workload=_ZERO,
            duration_min=10080, tick_minutes=10, events=_FAIL_FIRST),
        "no failure": Scenario(
            config=_R6_12TB,
            workload=Workload(offered_kiops=0.2, read_pct=95, block_kb=64),
            duration_min=10080, tick_minutes=10),
        "fail the drive at the end": Scenario(
            config=_R6_12TB,
            workload=Workload(offered_kiops=0.2, read_pct=95, block_kb=64),
            duration_min=10080, tick_minutes=10,
            events=[SimEvent(at_min=10070, action="fail-drive", index=0)]),
        "idle through the rebuild, load later": Scenario(
            config=_R6_12TB, workload=_ZERO,
            duration_min=10080, tick_minutes=10,
            events=_FAIL_FIRST + [SimEvent(
                at_min=4500, action="set-workload",
                workload=Workload(offered_kiops=0.4, read_pct=95, block_kb=64))]),
        "small drives, no capacity": Scenario(
            config=R6_CAPACITY.model_copy(update={"drive_tb": 8}),
            workload=Workload(offered_kiops=0.2, read_pct=95, block_kb=64),
            duration_min=10080, tick_minutes=10, events=_FAIL_FIRST),
        "buy SSDs": Scenario(
            config=ALL_FLASH,
            workload=Workload(offered_kiops=0.2, read_pct=95, block_kb=64),
            duration_min=10080, tick_minutes=10, events=_FAIL_FIRST),
        "24 bays of 7.2k that do not fit": Scenario(
            config=ArrayConfig(model="ME5024", drive_type="hdd-7.2k",
                               drive_count=24, drive_tb=8, raid_level="6"),
            workload=Workload(offered_kiops=0.2, read_pct=95, block_kb=64),
            duration_min=10080, tick_minutes=10, events=_FAIL_FIRST),
        "no spare, so nothing to wait for": Scenario(
            config=_R6_12TB.model_copy(update={"spares": 0}),
            workload=Workload(offered_kiops=0.2, read_pct=95, block_kb=64),
            duration_min=10080, tick_minutes=10, events=_FAIL_FIRST),
        "short run": Scenario(
            config=_R6_12TB,
            workload=Workload(offered_kiops=0.2, read_pct=95, block_kb=64),
            duration_min=600, tick_minutes=10, events=_FAIL_FIRST),
    },
    "size-for-the-worst-day": {
        "zero load": Scenario(
            config=_FLASH_2_SPARES, workload=_ZERO,
            duration_min=4320, tick_minutes=5, events=_BAD_WEEK),
        "size for the healthy day": Scenario(
            config=_FLASH_2_SPARES, workload=_FLASH_ASK,
            duration_min=4320, tick_minutes=5, events=_BAD_WEEK),
        "raid 10 for cheap writes": Scenario(
            config=ALL_FLASH.model_copy(update={"raid_level": "10", "spares": 2}),
            workload=_WORST_DAY_LOAD,
            duration_min=4320, tick_minutes=5, events=_BAD_WEEK),
        "raid 5 for capacity": Scenario(
            config=ALL_FLASH.model_copy(update={"raid_level": "5", "spares": 2}),
            workload=_WORST_DAY_LOAD,
            duration_min=4320, tick_minutes=5, events=_BAD_WEEK),
        "all reads": Scenario(
            config=_FLASH_2_SPARES,
            workload=Workload(offered_kiops=120.0, read_pct=100, block_kb=8),
            duration_min=4320, tick_minutes=5, events=_BAD_WEEK),
        "no failures at all": Scenario(
            config=_FLASH_2_SPARES, workload=_WORST_DAY_LOAD,
            duration_min=4320, tick_minutes=5),
        "second failure after the first rebuild": Scenario(
            config=_FLASH_2_SPARES, workload=_WORST_DAY_LOAD,
            duration_min=4320, tick_minutes=5,
            events=[_BAD_WEEK[0],
                    SimEvent(at_min=2400, action="fail-drive", index=1),
                    _BAD_WEEK[2]]),
        "restore the controller at once": Scenario(
            config=_FLASH_2_SPARES, workload=_WORST_DAY_LOAD,
            duration_min=4320, tick_minutes=5,
            events=_BAD_WEEK + [SimEvent(at_min=485, action="restore-controller")]),
        "single controller from the start": Scenario(
            config=_FLASH_2_SPARES.model_copy(update={"controllers": 1}),
            workload=_WORST_DAY_LOAD,
            duration_min=4320, tick_minutes=5, events=_BAD_WEEK),
        "one spare": Scenario(
            config=ALL_FLASH, workload=_WORST_DAY_LOAD,
            duration_min=4320, tick_minutes=5, events=_BAD_WEEK),
        "idle through the failures, load later": Scenario(
            config=_FLASH_2_SPARES, workload=_ZERO,
            duration_min=4320, tick_minutes=5,
            events=_BAD_WEEK + [SimEvent(
                at_min=3000, action="set-workload",
                workload=Workload(offered_kiops=300.0, read_pct=70, block_kb=8))]),
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
