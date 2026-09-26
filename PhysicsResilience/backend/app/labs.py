"""Graded labs for the security & resilience simulator (docs/LAB_PATTERN.md).

A guided scenario sets the architecture and the incident script and tells you
what to watch. A lab states a goal and leaves the architecture — and the
contain/restore half of the script — to you. ``grade_scenario`` runs the pure
engine on whatever you built and scores the trace.

Pure module, same rule as ``engine.py``: no FastAPI, no IO, no clock, no
randomness (AST-checked in ``tests/test_labs.py``). ``main.py`` is the only
caller that touches HTTP, so the static-hosting build grades in the browser
from the same code and data.

The hard scope boundary of ``models.SCOPE_NOTE`` holds here too: the
"incident" in every lab is an abstract corruption rate and a timestamp. The
labs grade defensive architecture — which copies survive, who notices, how
fast the estate is clean again — and nothing else.

Three things here are this app's own; everything else is ``twinkit.labs``:

* ``measure()`` — turns one run into named numbers. The un-gameable one is
  ``serviceRatePct``: the share of the estate serving clean data, averaged
  over the 336 hours that follow the incident's onset. Corrupted terabytes
  earn nothing, an estate that is mid-restore earns nothing, hours past the
  end of the run earn nothing, and a run with no incident at all earns zero —
  an architecture that was never tested has proven nothing. It is an
  illustrative proxy for "the business kept running", not an SLA.
* ``LABS`` — three labs of rising difficulty, every criterion citing the
  Explain entry (``presets.EXPLAINS``) and the equation it tests.
* ``REFERENCE_SOLUTIONS`` / ``GAMING_ATTEMPTS`` — a scenario that passes each
  lab, and the cheap tricks that must not. They stay server-side: the API
  serves ``LABS`` only.
"""

from __future__ import annotations

from twinkit.labs import Criterion, Lab, LabGoal, LabResult, Objective, grade

from .engine import simulate
from .leveling import L
from .models import (
    Scenario,
    SimEvent,
    SimState,
    Summary,
    Validation,
)
from .presets import DETECTING, INHOUSE, REPO_ONLY, VAULTED
from .validation import validate

# The equations, exactly as the Explain entries display them.
EQ_RPO = "RPO = now − newest intact copy (schedule + detection delay)"
EQ_RTO = "RTO = decision hours + TB × 1000 ÷ (GB/s × 3600), ×~2 if the first restore is corrupt"
EQ_BLAST = "blast = spread rate × time-to-contain  (or reachable assets, Fort Zero)"
EQ_ROC = "detection latency ∝ 1/sensitivity;  false alarms ∝ sensitivity"

#: Hours after onset over which delivered service is averaged (two weeks).
SERVICE_WINDOW_H = 336

#: What a metric reads when the thing it times never happened.
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
    onset = next((s.t_h for s in trace if s.incident_active), -1)
    contained_at = next((s.t_h for s in trace if s.contained), -1)
    first_restoring = next((s for s in trace if s.restoring), None)
    restore_at = first_restoring.t_h if first_restoring is not None else -1
    recovered_at = next((s.t_h for s in trace if s.recovered), -1)

    # Delivered service: clean share of the estate, hour by hour, over the
    # window after onset. Restoring hours and hours past the run are dark.
    service = 0.0
    if onset >= 0:
        for s in trace:
            if onset <= s.t_h < onset + SERVICE_WINDOW_H and not s.restoring:
                service += s.clean_tb / cfg.estate_tb
    service_pct = 100.0 * service / SERVICE_WINDOW_H

    # Hours in which corruption actually grew (an estate with nothing clean
    # left has stopped spreading, whatever the flags say).
    spreading_h = sum(
        1 for prev, s in zip(trace, trace[1:]) if s.corrupted_tb > prev.corrupted_tb
    ) + (1 if trace[0].corrupted_tb > 0 else 0)
    peak_blast = max(s.blast_radius_gb for s in trace)
    mean_spread = peak_blast / spreading_h if spreading_h else 0.0

    # A scripted "contain" counts as manual if it lands inside the incident
    # and no later than the hour the spread actually stopped. (The engine
    # applies events before its own response model, so such a click wins.)
    manual = sum(
        1 for e in scenario.events
        if e.action == "contain" and onset >= 0 and e.at_h >= onset
        and (contained_at < 0 or e.at_h <= contained_at)
    )
    first_incident = next(
        (e for e in sorted(scenario.events, key=lambda e: e.at_h)
         if e.action in ("incident", "slow-incident")), None,
    )
    months = scenario.duration_h // 720
    investigation = trace[-1].investigation_hours_cum
    return {
        "durationH": float(scenario.duration_h),
        "estateTb": float(cfg.estate_tb),
        "serviceRatePct": round(service_pct, 1),
        "incidentStartH": float(onset),
        "slowIncident": 1.0 if (
            first_incident is not None and first_incident.action == "slow-incident"
        ) else 0.0,
        "peakBlastGb": round(peak_blast, 1),
        "spreadingHours": float(spreading_h),
        "meanSpreadGbh": round(mean_spread, 1),
        "timeToContainH": float(contained_at - onset) if contained_at >= 0 and onset >= 0 else NEVER,
        "manualContains": float(manual),
        "restoreAfterContainH": (
            float(restore_at - contained_at)
            if restore_at >= 0 and contained_at >= 0 else -1.0
        ),
        "rpoAtRestoreH": round(
            first_restoring.last_clean_point_age_h
            if first_restoring is not None else trace[-1].last_clean_point_age_h, 1,
        ),
        "rtoHours": float(summary.rto_hours),
        "recovered": 1.0 if summary.recovery_succeeded else 0.0,
        "onsetToCleanH": (
            float(recovered_at - onset) if recovered_at >= 0 and onset >= 0 else NEVER
        ),
        "failedRestores": float(summary.failed_restores),
        "detectionLatencyH": float(summary.detection_latency_h),
        "investigationHPerMonth": round(investigation / months, 1) if months else investigation,
        "sensitivity": float(cfg.sensitivity),
        "validationErrors": float(sum(1 for v in validations if v.level == "error")),
    }


# --- Criteria shared between labs ------------------------------------------

def _service(floor_pct: int) -> Criterion:
    return Criterion(
        id="service", label=f"Clean service at least {floor_pct}% after onset",
        metric="serviceRatePct", op=">=", threshold=floor_pct, unit="%",
        weight=2.0, guards_work=True, explain_id="rto", equation=EQ_RTO,
        why=L(
            standard=(
                "Service is the share of the estate serving clean data, "
                f"averaged over the {SERVICE_WINDOW_H} hours after the incident "
                f"begins; {floor_pct}% is the floor. Corrupted terabytes earn "
                "nothing, every hour of a restore earns nothing, and a run "
                "with no incident earns zero — an untested architecture has "
                "proven nothing. The RTO is the biggest dark stretch, so a "
                "slow restore pipe fails this line. The proxy is illustrative, "
                "not an SLA."
            ),
            novice=(
                "The point of all this equipment is that the business keeps "
                "running on good data. So we measure exactly that: for the "
                f"{SERVICE_WINDOW_H} hours (two weeks) after the trouble "
                "starts, what share of your data was clean and usable, hour "
                f"by hour? The average has to be at least {floor_pct}%. Data "
                "that has been corrupted counts for nothing. While a restore "
                "is running the whole estate is offline, so those hours count "
                "for nothing too — which is why a slow restore fails this "
                "line. And if you never script an incident at all, the score "
                "is zero, because a defence that was never tested has not "
                "shown anything. This is a simple stand-in for 'the business "
                "stayed up', not a real service contract."
            ),
            expert=(
                f"Mean clean fraction over the {SERVICE_WINDOW_H} h after onset; "
                f"restoring and out-of-run hours zero; no incident → 0. Floor "
                f"{floor_pct}%. Illustrative proxy."
            ),
        ),
    )


def _recovered() -> Criterion:
    return Criterion(
        id="recovered", label="Recovery succeeds",
        metric="recovered", op=">=", threshold=1, unit="", weight=2.0,
        explain_id="rpo", equation=EQ_RPO,
        why=L(
            standard=(
                "A restore needs an intact copy to start from. The incident "
                "corrupts every copy in the standard repository, because "
                "production can reach it; only copies locked behind the "
                "vault's air gap stay intact. No intact copy means no "
                "recovery, whatever the restore pipe can do."
            ),
            novice=(
                "To get your data back you need at least one backup copy that "
                "the trouble did not reach. Ordinary backups sit where the "
                "production systems can get at them, so when production is "
                "corrupted, those copies are corrupted too. The Cyber Vault "
                "is different: it is cut off from the network (an 'air gap') "
                "except for a short, scheduled moment when it takes in a new "
                "copy, and the copies inside are locked. Without an intact "
                "copy somewhere, there is nothing to restore from and this "
                "line fails."
            ),
            expert="Needs ≥1 intact copy; repo copies fall with production, vault copies do not.",
        ),
    )


def _full_estate() -> Criterion:
    return Criterion(
        id="full-estate", label="Estate stays at 200 TB or more",
        metric="estateTb", op=">=", threshold=200, unit="TB",
        explain_id="rto", equation=EQ_RTO,
        why=L(
            standard=(
                "Restore time is terabytes ÷ throughput, so shrinking the "
                "estate is the cheap way to a short RTO. The lab is about a "
                "200 TB estate; the TB term is the one you may not lower."
            ),
            novice=(
                "How long a restore takes depends on how much data there is "
                "to move. Making the estate smaller would make every number "
                "in this lab look better without solving anything, so the "
                "lab does not allow it: the Estate slider has to stay at "
                "200 TB or more."
            ),
            expert="TB is fixed at ≥ 200; RTO must be bought with GB/s, not by shrinking TB.",
        ),
    )


def _restore_after_contain() -> Criterion:
    return Criterion(
        id="restore-after-contain", label="Restore starts only after the spread is contained",
        metric="restoreAfterContainH", op=">=", threshold=0, unit="h",
        explain_id="blast", equation=EQ_BLAST,
        why=L(
            standard=(
                "Restoring clean data into an estate where corruption is "
                "still spreading rebuilds what is about to be corrupted "
                "again. Time-to-contain ends first; only then does the RTO "
                "clock start. A run with no containment or no restore reads "
                "−1 here."
            ),
            novice=(
                "You have to stop the damage before you start repairing it. "
                "If you pour clean data back in while the corruption is still "
                "spreading, the clean data simply gets corrupted too. So the "
                "order matters: first the spread is contained, then the "
                "restore begins. This line measures the gap between those two "
                "moments, and it must not be negative. If the run never had a "
                "containment, or never had a restore, the reading is −1 and "
                "the line fails."
            ),
            expert="t_restore − t_contained ≥ 0; −1 if either never happened.",
        ),
    )


def _no_manual_contain() -> Criterion:
    return Criterion(
        id="no-manual-contain", label="Containment comes from the response model, not the Contain button",
        metric="manualContains", op="<=", threshold=0, unit="clicks",
        explain_id="blast", equation=EQ_BLAST,
        why=L(
            standard=(
                "The Contain button is a person who is already at the desk "
                "and already knows. In this lab nobody knows until detection "
                "fires, and nobody acts until the response model gets to the "
                "alert — that is the time-to-contain term you are here to "
                "shorten."
            ),
            novice=(
                "The Contain button in the incident script stops the damage "
                "instantly, as if someone happened to be watching at exactly "
                "the right moment. Real incidents are not like that. In this "
                "lab the damage can only be stopped the honest way: the "
                "detector has to notice it, and then whoever answers alerts "
                "(your own staff, or a 24-hour service) has to get to it. "
                "Using the Contain button during the incident fails this line."
            ),
            expert="Zero scripted 'contain' events during the spread; TTC must be detection + triage.",
        ),
    )


def _zero_failed_restores() -> Criterion:
    return Criterion(
        id="no-failed-restore", label="No failed restores",
        metric="failedRestores", op="<=", threshold=0, unit="restores",
        explain_id="rto", equation=EQ_RTO,
        why=L(
            standard=(
                "A quiet incident does not date itself. Restore before "
                "content analysis has named the last clean point and the "
                "operator picks the newest copy, which is silently corrupt — "
                "the restore completes, fails validation, and starts again "
                "from an older copy. That is the ×~2 in the RTO equation."
            ),
            novice=(
                "When corruption creeps in slowly, nobody can tell by looking "
                "which backup is the last good one. If you restore before the "
                "detector has worked that out, you restore the newest copy — "
                "and the newest copy is already damaged. You only find out "
                "after the whole restore has finished, and then you have to "
                "do it all again from an older copy. That wasted restore is "
                "what this line forbids. Wait for the detector to name the "
                "clean copy first."
            ),
            expert="No restore-and-pray: restore only after the last-clean point is identified.",
        ),
    )


def _alarm_budget(hours: int) -> Criterion:
    return Criterion(
        id="alarm-budget", label=f"False-alarm investigation at most {hours} h a month",
        metric="investigationHPerMonth", op="<=", threshold=hours, unit="h/month",
        weight=2.0, explain_id="roc", equation=EQ_ROC,
        why=L(
            standard=(
                "Sensitivity buys earlier detection and pays in false alarms: "
                "about 1.2 a month per sensitivity point, 3 hours of "
                f"investigation each. The team has {hours} hours a month for "
                "chasing alarms that turn out to be nothing, so the knob "
                "cannot simply go to 10."
            ),
            novice=(
                "You can make the detector more sensitive so it notices "
                "trouble sooner. The price is that a twitchy detector also "
                "raises more false alarms, and each false alarm costs someone "
                "about 3 hours to check out. Your team can spare "
                f"{hours} hours a month for that, no more. So turning "
                "Sensitivity all the way up is not allowed — you have to find "
                "the highest setting the team can afford."
            ),
            expert=f"int(1.2 × sensitivity) alarms/month × 3 h ≤ {hours} h.",
        ),
    )


def _full_month() -> Criterion:
    return Criterion(
        id="full-month", label="Run lasts at least 720 h",
        metric="durationH", op=">=", threshold=720, unit="h",
        explain_id="roc", equation=EQ_ROC,
        why=L(
            standard=(
                "False alarms are billed monthly. A run shorter than a month "
                "would be graded before the bill for its sensitivity setting "
                "had arrived."
            ),
            novice=(
                "The false-alarm cost is added up once a month. If the run "
                "stopped before the month was over, a very twitchy detector "
                "would look free, because its bill had not come in yet. So "
                "the run has to last the full 720 hours (30 days) the lab "
                "starts with."
            ),
            expert="≥ one 720 h billing period, so the ROC price is on the books.",
        ),
    )


def _onset_pinned(hour: int, when: str) -> Criterion:
    return Criterion(
        id="scripted-onset", label=f"Incident begins at h+{hour} ({when})",
        metric="incidentStartH", op="==", threshold=hour, unit="h",
        explain_id="blast", equation=EQ_BLAST,
        why=L(
            standard=(
                f"The incident is scripted for you at h+{hour}, {when}. When "
                "it starts decides who is awake to answer it, so moving it to "
                "a convenient hour is not part of the exercise. 'Reset to the "
                "lab's start' puts it back."
            ),
            novice=(
                f"The lab has already placed the incident for you, at hour "
                f"{hour} of the run — that is {when}. Trouble does not wait "
                "for office hours, and the time it starts decides who is "
                "around to deal with it. Moving it to an easier time would "
                "miss the point, so the lab checks that it is still where it "
                "was put. If you cleared the script by accident, the 'Reset "
                "to the lab's start' button brings it back."
            ),
            expert=f"Onset fixed at h+{hour} ({when}); the clock is part of the stage.",
        ),
    )


def _spread_rate(rate: int) -> Criterion:
    return Criterion(
        id="spread-rate", label=f"Corruption spreads at {rate} GB/h or faster",
        metric="meanSpreadGbh", op=">=", threshold=rate, unit="GB/h",
        explain_id="blast", equation=EQ_BLAST,
        why=L(
            standard=(
                f"Blast radius is rate × time. The rate is the incident's, not "
                f"yours: {rate} GB/h. A gentler incident would shrink the "
                "blast without the architecture having done anything."
            ),
            novice=(
                "How much data gets damaged is how fast the damage spreads "
                "multiplied by how long it spreads for. You only control the "
                f"second part. The speed — {rate} GB every hour — belongs to "
                "the incident, and the lab checks that it was not turned down."
            ),
            expert=f"Spread rate ≥ {rate} GB/h; only time-to-contain is yours.",
        ),
    )


# --- Shared goal prose

# Goal lines the three labs share. Registered once: L() keys on the standard
# text, so one block reused is safer than three that must stay identical.
_ESTATE_LINE = L(
    standard="The estate stays at 200 TB or more.",
    novice="Keep the Estate slider at 200 TB or more; making the estate smaller is not a solution.",
    expert="Estate ≥ 200 TB.",
)
_WORK_LINE = L(
    standard="At least 90% of the estate serving clean data, averaged over the 336 h after onset; restore hours count as zero.",
    novice="Over the two weeks (336 hours) after the trouble starts, at least 90% of your data must be clean and usable on average. Hours spent restoring count as zero, because the estate is offline — and a restore that has to be done twice costs twice the hours.",
    expert="serviceRatePct ≥ 90 over the 336 h window.",
)


# --- Lab 1: back within a day -----------------------------------------------

_DAY_EVENTS = [
    SimEvent(at_h=240, action="incident", value=500),
    SimEvent(at_h=280, action="contain"),
    SimEvent(at_h=290, action="attempt-restore"),
]
_DAY_START = Scenario(config=REPO_ONLY, duration_h=720, events=_DAY_EVENTS)

BACK_WITHIN_A_DAY = Lab(
    id="back-within-a-day",
    title="Back within a day, losing as little as you can",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "A 500 GB/h incident corrupts 20 TB of a 200 TB estate before "
                "anyone contains it. Build the architecture that recovers "
                "anyway, with an RTO of 24 hours or less — then shrink the "
                "RPO, the age of the newest intact copy at the moment the "
                "restore begins."
            ),
            novice=(
                "Something starts damaging your data at 500 GB every hour, "
                "and 40 hours go by before anyone stops it. By then 20 TB of "
                "your 200 TB is ruined. Your job is to set up the backups so "
                "that you can still get everything back, and get it back "
                "within 24 hours of starting the restore (that time is called "
                "the RTO). Once that works, go one better: make the backup "
                "you restore from as fresh as possible, so that fewer hours "
                "of work are lost. The age of that backup when the restore "
                "starts is called the RPO."
            ),
            expert=(
                "500 GB/h, ≥ 20 TB blast, 200 TB estate: recover with RTO ≤ 24 h, "
                "then minimize RPO at restore start."
            ),
        ),
        constraints=[
            L(standard="The incident corrupts at least 20,000 GB, at no more than 500 GB/h.",
              novice="The incident has to do its full damage: at least 20,000 GB corrupted, spreading no faster than 500 GB every hour. You may not stop it early or speed it up to get it over with.",
              expert="Blast ≥ 20,000 GB at ≤ 500 GB/h."),
            L(standard="Recovery succeeds, the RTO is 24 h or less, and the restore starts only after containment.",
              novice="The restore has to work, it has to take 24 hours or less, and it may only begin once the damage has been stopped.",
              expert="Recovered; RTO ≤ 24 h; restore ≥ containment."),
            _ESTATE_LINE,
        ],
        delivered_work=_WORK_LINE,
    ),
    criteria=[
        _service(90),
        Criterion(
            id="real-damage", label="The incident corrupts at least 20,000 GB",
            metric="peakBlastGb", op=">=", threshold=20000, unit="GB",
            explain_id="blast", equation=EQ_BLAST,
            why=L(
                standard=(
                    "The lab is set 40 hours into a 500 GB/h incident: "
                    "500 × 40 = 20,000 GB. Containing at once, or restoring "
                    "before the incident has run, would be grading an "
                    "incident that never tested the backups."
                ),
                novice=(
                    "This lab is about recovering from a serious incident, so "
                    "the incident has to be serious: 500 GB an hour for 40 "
                    "hours is 20,000 GB of damage. If you stop it straight "
                    "away there is hardly anything to recover from, and the "
                    "backups were never really tested. Leave the scripted "
                    "incident and containment where the lab put them."
                ),
                expert="rate × TTC = 500 × 40 = 20,000 GB; the stage, not a lever.",
            ),
        ),
        Criterion(
            id="spread-cap", label="Corruption spreads at 500 GB/h or slower",
            metric="meanSpreadGbh", op="<=", threshold=500, unit="GB/h",
            explain_id="blast", equation=EQ_BLAST,
            why=L(
                standard=(
                    "A faster incident reaches 20,000 GB in fewer hours, "
                    "which would shorten the wait before the restore and "
                    "flatter the RPO. The rate is the incident's: 500 GB/h."
                ),
                novice=(
                    "If the damage spread faster, it would reach 20,000 GB "
                    "sooner, you could restore sooner, and your backup would "
                    "look fresher than it deserves. So the lab checks that "
                    "the incident spreads at 500 GB an hour, as scripted, and "
                    "no faster."
                ),
                expert="Rate ≤ 500 GB/h, so 20,000 GB costs ≥ 40 h of RPO.",
            ),
        ),
        _restore_after_contain(),
        _recovered(),
        Criterion(
            id="rto", label="RTO at most 24 h",
            metric="rtoHours", op="<=", threshold=24, unit="h", weight=2.0,
            explain_id="rto", equation=EQ_RTO,
            why=L(
                standard=(
                    "RTO is 6 decision hours plus data ÷ throughput. At "
                    "1 GB/s, 200 TB takes 56 hours to move — 62 h in all. "
                    "The estate is fixed, so the 24-hour promise has to be "
                    "bought with the restore pipe."
                ),
                novice=(
                    "The time to recover has two parts. First, about 6 hours "
                    "of people deciding what to do and checking the backup. "
                    "Second, the time to copy the data back, which depends on "
                    "how much data there is and how fast the restore "
                    "connection is. At 1 GB per second, 200 TB takes 56 "
                    "hours to copy — 62 hours in total, far over the 24 "
                    "allowed. You cannot shrink the data, so you need a "
                    "faster restore connection (the Restore pipe slider)."
                ),
                expert="6 + 200,000 ÷ (GB/s × 3600) ≤ 24 → GB/s ≥ 3.1.",
            ),
        ),
        _full_estate(),
    ],
    objective=Objective(
        label="RPO when the restore begins", metric="rpoAtRestoreH",
        direction="minimize", par=46, worst=75, unit="h",
        explain_id="rpo", equation=EQ_RPO,
    ),
    hints=[
        L(standard="Run the start as it is and read the event log at the restore. How many intact copies existed, and where would one have had to be?",
          novice="Press 'Run and grade' without changing anything and look at the event log around hour 290, when the restore is attempted. It says there is no intact backup. Ask yourself where a backup would have to be kept for the incident not to reach it.",
          expert="Start: zero intact copies at h+290. Where does a copy survive?"),
        L(standard="With the vault on, recovery works but takes 62 h. Open Explain mode on the RTO gauge: only one term in that equation is yours to change.",
          novice="Turn the Cyber Vault on and the restore works — but it takes 62 hours. Switch on Explain mode and look at the RTO gauge. The sum has three parts: decision time, the amount of data, and the speed of the restore connection. The lab fixes the first two. Raise the third (Restore pipe) until the total is 24 hours or less.",
          expert="Vault → recoverable at 62 h. RTO ≤ 24 needs ≥ 3.1 GB/s."),
        L(standard="Now the RPO. The copy you restore from is the newest one inside the vault, so the vault's sync interval sets it — backing up hourly changes nothing if the gap still opens once a day.",
          novice="Now make the backup fresher. The copy you restore from is the newest one that made it into the vault before the trouble began. The vault only takes in a new copy when its gap opens, so how often that happens (Vault sync) is what matters. Taking backups every hour does not help if the vault still only collects one a day. Shorten both.",
          expert="RPO follows vault sync cadence, not backup cadence. Shorten both to 6 h."),
        L(standard="Every hour between containment and the restore is an hour added to the RPO. Put the restore at the hour of containment, not ten hours later.",
          novice="One more thing: the lab's script waits 10 hours after containment before it starts the restore, and every one of those hours makes the backup an hour older. In the Incident script panel each event shows its hour in a small box. Change the restore's hour from 290 to 280, the same hour as containment.",
          expert="Restore at the containment tick; the 10 h wait is pure RPO."),
    ],
    start=_DAY_START.model_dump(by_alias=True),
)


# --- Lab 2: a detector nobody answers --------------------------------------

_SLOW_ONSET = 188   # Monday of week two, 20:00
_SLOW_EVENTS = [SimEvent(at_h=_SLOW_ONSET, action="slow-incident", value=20)]
_SLOW_START = Scenario(config=DETECTING, duration_h=720, events=_SLOW_EVENTS)

SLOW_BURN_BUDGET = Lab(
    id="slow-burn-on-a-budget",
    title="Catch the slow burn on an alarm budget",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "A low-and-slow incident corrupts 20 GB/h from Monday 20:00. "
                "Nobody may press Contain: detection has to notice and the "
                "response model has to act. Recover cleanly on the first "
                "restore, keep false-alarm investigation within 24 hours a "
                "month, and make the blast radius as small as that budget "
                "allows."
            ),
            novice=(
                "This time the damage is quiet: only 20 GB an hour, starting "
                "on a Monday at 8 in the evening. Nobody notices by looking, "
                "and you are not allowed to press Contain yourself. The "
                "detector has to spot it, and whoever answers alerts has to "
                "stop it. Then you restore — and it must work first time. "
                "There is a catch: a more sensitive detector raises more "
                "false alarms, and your team can only spend 24 hours a month "
                "checking alarms that turn out to be nothing. Within that "
                "limit, keep the amount of damaged data as small as you can."
            ),
            expert=(
                "20 GB/h slow incident at h+188. No manual containment, zero "
                "failed restores, ≤ 24 h/month false-alarm cost; minimize blast."
            ),
        ),
        constraints=[
            L(standard="The scripted slow incident stays at h+188 and at 20 GB/h or faster.",
              novice="Leave the scripted incident where it is: a slow one, starting at hour 188, spreading at 20 GB an hour.",
              expert="slow-incident, h+188, ≥ 20 GB/h."),
            L(standard="No Contain button during the spread; the restore starts only after containment and succeeds first time.",
              novice="Do not press Contain while the damage is spreading. Start the restore only after the spread has been stopped, and it has to succeed on the first try.",
              expert="No manual contain; restore ≥ containment; failedRestores = 0."),
            L(standard="False-alarm investigation at most 24 h a month, measured over a full 720 h run.",
              novice="The false alarms must cost your team no more than 24 hours a month, and the run has to last the full 30 days so that the monthly cost is counted.",
              expert="≤ 24 h/month over ≥ 720 h."),
            _ESTATE_LINE,
        ],
        delivered_work=_WORK_LINE,
    ),
    criteria=[
        _service(90),
        _onset_pinned(_SLOW_ONSET, "Monday 20:00"),
        Criterion(
            id="slow-incident", label="The incident is the low-and-slow kind",
            metric="slowIncident", op=">=", threshold=1, unit="",
            explain_id="roc", equation=EQ_ROC,
            why=L(
                standard=(
                    "A low-and-slow incident stays under the detector's "
                    "threshold twice as long as a loud one at the same "
                    "sensitivity, and it does not date itself for the "
                    "operator. Swapping it for a loud incident at a low rate "
                    "would remove both difficulties."
                ),
                novice=(
                    "A quiet incident is harder in two ways. The detector "
                    "takes twice as long to be sure about it, and nobody can "
                    "tell afterwards when it began, so nobody knows which "
                    "backup is safe. The lab is about exactly that kind of "
                    "incident, so it checks that the scripted one is still "
                    "the 'slow' kind."
                ),
                expert="slow-incident: latency × 2, onset not self-dating.",
            ),
        ),
        _spread_rate(20),
        _no_manual_contain(),
        _restore_after_contain(),
        _recovered(),
        _zero_failed_restores(),
        _alarm_budget(24),
        _full_month(),
        _full_estate(),
    ],
    objective=Objective(
        label="Blast radius", metric="peakBlastGb",
        direction="minimize", par=400, worst=900, unit="GB",
        explain_id="blast", equation=EQ_BLAST,
    ),
    hints=[
        L(standard="The start never restores, so it cannot pass. Before you add a restore, scrub to the detection pin in the timeline: a restore placed earlier than that pin picks the newest copy, and the newest copy is corrupt.",
          novice="The lab starts with no restore in the script at all, so it cannot pass yet. But do not just add one anywhere. Find the pin on the timeline where the detector fires. If you start a restore before that moment, nobody yet knows which backup is safe, the newest one gets used, and it is already damaged — you pay for the whole restore twice.",
          expert="Restore only after the detection pin, or you restore-and-pray."),
        L(standard="Raise the sensitivity and watch time-to-contain: with the in-house team it does not move. Look at the alert queue gauge when the detection fires.",
          novice="Try turning Sensitivity up and down and watch the time-to-contain reading. With your own staff answering alerts, it barely changes. Look at the alert-queue gauge at the moment the detector fires: the real alert is sitting behind a pile of routine ones, waiting for office hours.",
          expert="In-house TTC is queue-bound, not detector-bound. Check the backlog at detection."),
        L(standard="Blast = 20 GB/h × (detection latency + time to act). A 24/7 response removes the second term; then sensitivity is what is left, and the budget caps it at int(1.2 × s) × 3 ≤ 24.",
          novice="The damage is the speed (20 GB an hour) multiplied by two waits added together: how long the detector takes to notice, and how long until somebody acts. A 24-hour response service (the MDR option) makes the second wait almost nothing. After that the only wait left is the detector's, which gets shorter as Sensitivity goes up. Work out the highest Sensitivity whose false alarms still fit in 24 hours a month — each alarm costs 3 hours.",
          expert="MDR zeroes triage; then s = 7 is the budget ceiling (8 alarms × 3 h)."),
        L(standard="The service floor is the RTO again: at 1 GB/s the restore keeps the estate dark for 62 of the 336 hours.",
          novice="If the 'clean service' line is still failing, it is the slow restore again: at 1 GB per second the estate is offline for 62 hours. Raise the Restore pipe as you did in the first lab.",
          expert="Service < 90% at 1 GB/s: 62 dark hours. Buy GB/s."),
    ],
    start=_SLOW_START.model_dump(by_alias=True),
)


# --- Lab 3: two a.m. Saturday, the whole clock ------------------------------

_SAT_ONSET = 122    # Saturday 02:00
_SAT_EVENTS = [SimEvent(at_h=_SAT_ONSET, action="incident", value=500)]
_SAT_START = Scenario(
    config=INHOUSE.model_copy(update={
        "estate_tb": 200, "noise_alerts_day": 120, "vault": False,
    }),
    duration_h=720, events=_SAT_EVENTS,
)

WHOLE_CLOCK = Lab(
    id="two-am-whole-clock",
    title="Two a.m. Saturday: clean again in 30 hours",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "A 500 GB/h incident begins at 02:00 on a Saturday. From that "
                "hour to a fully clean 200 TB estate you have 30 hours — "
                "detection latency, time to act, decision time and data "
                "movement all come out of the same 30. No Contain button, no "
                "failed restore, and the false-alarm budget is still 24 hours "
                "a month. Then make the blast radius as small as you can."
            ),
            novice=(
                "It is 2 o'clock on a Saturday morning and your data starts "
                "being damaged at 500 GB an hour. You have 30 hours, counted "
                "from that moment, to have all 200 TB clean again. Everything "
                "comes out of those 30 hours: the time the detector takes to "
                "notice, the time until somebody acts, the 6 hours of "
                "deciding, and the time to copy the data back. You may not "
                "press Contain yourself, the restore has to work first time, "
                "and false alarms may still cost no more than 24 hours a "
                "month. When all of that holds, make the damage as small as "
                "you can."
            ),
            expert=(
                "500 GB/h at h+122 (Sat 02:00). Onset → clean ≤ 30 h, no manual "
                "contain, zero failed restores, ≤ 24 h/month alarms; minimize blast."
            ),
        ),
        constraints=[
            L(standard="The scripted incident stays at h+122 and at 500 GB/h or faster.",
              novice="Leave the scripted incident where it is: starting at hour 122 (Saturday, 2 in the morning), spreading at 500 GB an hour.",
              expert="incident, h+122, ≥ 500 GB/h."),
            L(standard="Onset to a clean estate in 30 h or less; recovery succeeds on the first restore, started only after containment.",
              novice="From the hour the trouble starts to the hour all your data is clean again: 30 hours or less. The restore must succeed first time, and may only start after the spread has been stopped.",
              expert="onsetToCleanH ≤ 30; restore ≥ containment; failedRestores = 0."),
            L(standard="No Contain button during the spread; false-alarm investigation at most 24 h a month over a full 720 h run.",
              novice="Do not press Contain while the damage is spreading. False alarms may cost at most 24 hours a month, and the run must last the full 30 days.",
              expert="No manual contain; ≤ 24 h/month over ≥ 720 h."),
            _ESTATE_LINE,
        ],
        delivered_work=_WORK_LINE,
    ),
    criteria=[
        _service(90),
        _onset_pinned(_SAT_ONSET, "Saturday 02:00"),
        _spread_rate(500),
        _no_manual_contain(),
        _restore_after_contain(),
        _recovered(),
        _zero_failed_restores(),
        Criterion(
            id="whole-clock", label="Onset to a clean estate in 30 h or less",
            metric="onsetToCleanH", op="<=", threshold=30, unit="h", weight=3.0,
            explain_id="rto", equation=EQ_RTO,
            why=L(
                standard=(
                    "The RTO equation starts its clock at the restore. The "
                    "business starts it at onset: detection latency + time "
                    "to act + any wait before the restore + 6 decision hours "
                    "+ data ÷ throughput. At sensitivity 7 with 24/7 "
                    "response the first two are 10 h, which leaves 14 h to "
                    "move 200 TB — about 4 GB/s. A run that never recovers "
                    "reads 9999."
                ),
                novice=(
                    "The RTO gauge only starts counting when the restore "
                    "starts. The business starts counting when the trouble "
                    "starts. So add up everything in between: the hours until "
                    "the detector notices, the hours until somebody acts, any "
                    "hours you leave between containment and the restore, "
                    "6 hours of deciding, and the hours to copy 200 TB back. "
                    "The total has to be 30 or less. Every part you shorten "
                    "gives the others more room — a quicker detector lets you "
                    "get away with a slower restore connection, and the other "
                    "way round. If the estate is never recovered, this line "
                    "reads 9999."
                ),
                expert=(
                    "latency + triage + wait + 6 + 200,000 ÷ (GB/s × 3600) ≤ 30; "
                    "9999 if never recovered."
                ),
            ),
        ),
        _alarm_budget(24),
        _full_month(),
        _full_estate(),
    ],
    objective=Objective(
        label="Blast radius", metric="peakBlastGb",
        direction="minimize", par=5500, worst=8000, unit="GB",
        explain_id="blast", equation=EQ_BLAST,
    ),
    hints=[
        L(standard="Run the start and read which lines fail. Each of the first two labs is in here: a copy has to survive, and someone has to be awake.",
          novice="Press 'Run and grade' on the start and read the list of failed lines. You have met most of them before. In the first lab a backup had to survive; in the second somebody had to be there to act. Both problems are back, together, at the worst time of the week.",
          expert="Start fails on the vault, the queue and the pipe at once."),
        L(standard="At 02:00 on a Saturday the in-house team is 54 hours from its desks, and at 120 alerts a day the queue never empties. Tuning the noise does not bring Monday forward.",
          novice="At 2 on a Saturday morning your own staff will not be at their desks for 54 hours, and by then 27 TB is gone. The start also has 120 routine alerts a day against a team that can handle 60, so the queue never clears. You can turn the noise down, but that does not make Monday come sooner. Look at the Response model control.",
          expert="In-house: TTC ≥ 54 h regardless of noise. Response model is the lever."),
        L(standard="Write the 30 hours out: 60 ÷ sensitivity to detect, 1 to act, 6 to decide, 200,000 ÷ (GB/s × 3600) to move. The alarm budget caps sensitivity; the pipe has to cover the rest.",
          novice="Write the 30 hours out as a sum. Detecting takes 60 divided by the Sensitivity setting (so 10 hours at setting 6). Acting takes about 1 hour with a 24-hour service. Deciding takes 6. Copying 200 TB takes 200,000 divided by (the pipe speed in GB/s × 3600) hours. The false-alarm budget limits how high Sensitivity can go, so the rest has to come from a faster Restore pipe.",
          expert="60/s + 1 + 6 + 55.6/GBps ≤ 30, s ≤ 7 → GB/s ≥ 4."),
        L(standard="The restore event lands at the playback cursor. Scrub to the containment pin and place it there: every hour between containment and the restore comes straight out of the 30.",
          novice="The 'Attempt restore' button adds the restore at the hour the playback cursor is on. Pause, drag the timeline to the pin where containment happens, and press it there — or press it anywhere and then type the right hour into the event's box in the Incident script panel. If you place it later, every hour of delay is an hour taken out of your 30.",
          expert="Restore at the containment tick; slack there is slack nowhere else."),
    ],
    start=_SAT_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [BACK_WITHIN_A_DAY, SLOW_BURN_BUDGET, WHOLE_CLOCK]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Reference solutions and gaming attempts (server-side only) -------------

_DAY_GOOD = VAULTED.model_copy(update={
    "restore_gbps": 3.5, "backup_every_h": 6, "vault_sync_every_h": 6,
})
_SLOW_GOOD = DETECTING.model_copy(update={
    "sensitivity": 7, "response": "mdr", "restore_gbps": 3.5,
})
_SAT_GOOD = INHOUSE.model_copy(update={
    "estate_tb": 200, "noise_alerts_day": 120, "vault": True,
    "sensitivity": 7, "response": "mdr", "restore_gbps": 4.0,
})

REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    "back-within-a-day": Scenario(
        config=_DAY_GOOD, duration_h=720,
        events=[
            SimEvent(at_h=240, action="incident", value=500),
            SimEvent(at_h=280, action="contain"),
            SimEvent(at_h=280, action="attempt-restore"),
        ],
    ),
    "slow-burn-on-a-budget": Scenario(
        config=_SLOW_GOOD, duration_h=720,
        events=_SLOW_EVENTS + [SimEvent(at_h=208, action="attempt-restore")],
    ),
    "two-am-whole-clock": Scenario(
        config=_SAT_GOOD, duration_h=720,
        events=_SAT_EVENTS + [SimEvent(at_h=132, action="attempt-restore")],
    ),
}

GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "back-within-a-day": {
        "zero incident": Scenario(config=_DAY_GOOD, duration_h=720, events=[]),
        "contain at once": Scenario(
            config=_DAY_GOOD, duration_h=720,
            events=[
                SimEvent(at_h=240, action="incident", value=500),
                SimEvent(at_h=240, action="contain"),
                SimEvent(at_h=240, action="attempt-restore"),
            ],
        ),
        "restore into a live incident": Scenario(
            config=_DAY_GOOD, duration_h=720,
            events=[
                SimEvent(at_h=240, action="incident", value=500),
                SimEvent(at_h=258, action="attempt-restore"),
            ],
        ),
        "restore before the incident": Scenario(
            config=_DAY_GOOD, duration_h=720,
            events=[
                SimEvent(at_h=239, action="attempt-restore"),
                SimEvent(at_h=240, action="incident", value=500),
            ],
        ),
        "a faster incident to shorten the wait": Scenario(
            config=_DAY_GOOD, duration_h=720,
            events=[
                SimEvent(at_h=240, action="incident", value=5000),
                SimEvent(at_h=244, action="contain"),
                SimEvent(at_h=244, action="attempt-restore"),
            ],
        ),
        "shrink the estate": Scenario(
            config=VAULTED.model_copy(update={"estate_tb": 60}),
            duration_h=720, events=_DAY_EVENTS,
        ),
        "vault but the default pipe": Scenario(
            config=VAULTED, duration_h=720, events=_DAY_EVENTS,
        ),
    },
    "slow-burn-on-a-budget": {
        "zero incident": Scenario(config=_SLOW_GOOD, duration_h=720, events=[]),
        "press contain at onset": Scenario(
            config=_SLOW_GOOD, duration_h=720,
            events=_SLOW_EVENTS + [
                SimEvent(at_h=189, action="contain"),
                SimEvent(at_h=189, action="attempt-restore"),
            ],
        ),
        "sensitivity to ten": Scenario(
            config=_SLOW_GOOD.model_copy(update={"sensitivity": 10}),
            duration_h=720,
            events=_SLOW_EVENTS + [SimEvent(at_h=202, action="attempt-restore")],
        ),
        "short run dodges the monthly bill": Scenario(
            config=_SLOW_GOOD.model_copy(update={"sensitivity": 10}),
            duration_h=700,
            events=_SLOW_EVENTS + [SimEvent(at_h=202, action="attempt-restore")],
        ),
        "restore and pray": Scenario(
            config=_SLOW_GOOD, duration_h=720,
            events=_SLOW_EVENTS + [SimEvent(at_h=195, action="attempt-restore")],
        ),
        "a loud incident at a quiet rate": Scenario(
            config=_SLOW_GOOD, duration_h=720,
            events=[
                SimEvent(at_h=_SLOW_ONSET, action="incident", value=20),
                SimEvent(at_h=199, action="attempt-restore"),
            ],
        ),
        "a trickle instead of a burn": Scenario(
            config=_SLOW_GOOD, duration_h=720,
            events=[
                SimEvent(at_h=_SLOW_ONSET, action="slow-incident", value=1),
                SimEvent(at_h=208, action="attempt-restore"),
            ],
        ),
        "move the onset to office hours": Scenario(
            config=_SLOW_GOOD, duration_h=720,
            events=[
                SimEvent(at_h=176, action="slow-incident", value=20),
                SimEvent(at_h=196, action="attempt-restore"),
            ],
        ),
        "shrink the estate": Scenario(
            config=_SLOW_GOOD.model_copy(update={"estate_tb": 20, "restore_gbps": 1.0}),
            duration_h=720,
            events=_SLOW_EVENTS + [SimEvent(at_h=208, action="attempt-restore")],
        ),
    },
    "two-am-whole-clock": {
        "zero incident": Scenario(config=_SAT_GOOD, duration_h=720, events=[]),
        "press contain at onset": Scenario(
            config=_SAT_GOOD, duration_h=720,
            events=_SAT_EVENTS + [
                SimEvent(at_h=123, action="contain"),
                SimEvent(at_h=123, action="attempt-restore"),
            ],
        ),
        "restore into a live incident": Scenario(
            config=_SAT_GOOD.model_copy(update={"response": "inhouse"}),
            duration_h=720,
            events=_SAT_EVENTS + [SimEvent(at_h=122, action="attempt-restore")],
        ),
        "sensitivity to ten": Scenario(
            config=_SAT_GOOD.model_copy(update={"sensitivity": 10}),
            duration_h=720,
            events=_SAT_EVENTS + [SimEvent(at_h=129, action="attempt-restore")],
        ),
        "in-house with the noise tuned out": Scenario(
            config=_SAT_GOOD.model_copy(update={
                "response": "inhouse", "noise_alerts_day": 0,
                "inhouse_capacity_day": 1000,
            }),
            duration_h=720,
            events=_SAT_EVENTS + [SimEvent(at_h=176, action="attempt-restore")],
        ),
        "move the onset to Tuesday morning": Scenario(
            config=_SAT_GOOD, duration_h=720,
            events=[
                SimEvent(at_h=32, action="incident", value=500),
                SimEvent(at_h=42, action="attempt-restore"),
            ],
        ),
        "a gentler incident": Scenario(
            config=_SAT_GOOD, duration_h=720,
            events=[
                SimEvent(at_h=_SAT_ONSET, action="incident", value=50),
                SimEvent(at_h=132, action="attempt-restore"),
            ],
        ),
        "shrink the estate": Scenario(
            config=_SAT_GOOD.model_copy(update={"estate_tb": 50, "restore_gbps": 1.0}),
            duration_h=720,
            events=_SAT_EVENTS + [SimEvent(at_h=132, action="attempt-restore")],
        ),
        "right architecture, default pipe": Scenario(
            config=_SAT_GOOD.model_copy(update={"restore_gbps": 1.0}),
            duration_h=720,
            events=_SAT_EVENTS + [SimEvent(at_h=132, action="attempt-restore")],
        ),
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
