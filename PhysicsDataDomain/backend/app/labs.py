"""Graded labs for the Data Domain dedupe physics simulator
(``docs/LAB_PATTERN.md``; pilot: ``DellPowerEdgeR760Thermal``).

A guided scenario sets the dials and tells you what to watch. A lab states a
goal and leaves the dials to you: build a Scenario with the ordinary controls,
the engine runs it, and ``grade_scenario`` scores the trace.

Pure module, same rule as ``engine.py`` and ``validation.py``: no FastAPI, no
IO, no clock, no randomness (AST-checked in ``tests/test_labs.py``).
``main.py`` is the only caller that touches HTTP, so the static-hosting build
runs this same grading in the browser.

Three things here are this app's own; everything else is ``twinkit.labs``:

* ``measure()`` — turns one run into named numbers. The un-gameable one is
  ``protectedTbMean``: the logical terabytes under protection (retained
  generations × full size), averaged over every day of the run, with any day
  the store is full counted as zero — a full store fails its backups. A tiny
  dataset or a one-generation policy protects almost nothing, so it passes
  nothing. It is an illustrative proxy for the job a backup appliance is
  bought to do, not a benchmark, and is labeled so.
* ``LABS`` — three labs of rising difficulty. Each is one of the engine's
  acceptance scenarios turned into a problem with a twist, and every criterion
  cites the Explain entry (``presets.EXPLAINS``) and the equation it tests.
* ``REFERENCE_SOLUTIONS`` / ``GAMING_ATTEMPTS`` — a scenario that passes each
  lab, and the cheap tricks that must not. They stay server-side: the API
  serves ``LABS`` only.
"""

from __future__ import annotations

from twinkit.labs import Criterion, Lab, LabGoal, LabResult, Objective, grade

from .constants import APPLIANCES
from .engine import simulate
from .leveling import L
from .models import (
    Dataset,
    Scenario,
    Schedule,
    SimEvent,
    SimState,
    Summary,
    Validation,
)
from .presets import EXPLAINS
from .validation import validate

# The equations, exactly as the Explain entries display them — read from the
# entries themselves so the two can never drift.
_EQ: dict[str, str] = {e.id: e.equation for e in EXPLAINS}
EQ_RATIO = _EQ["dedupe-ratio"]
EQ_NOVEL = _EQ["novelty"]
EQ_CF = _EQ["compression"]
EQ_INDEX = _EQ["index-pressure"]
EQ_WINDOW = _EQ["backup-window"]


# --- Measurement ----------------------------------------------------------

def measure(
    scenario: Scenario,
    trace: list[SimState],
    summary: Summary,
    validations: list[Validation],
) -> dict[str, float]:
    """One run as named numbers. Keys are the wire names criteria refer to."""
    ds = scenario.dataset
    retention = scenario.schedule.retention_days

    # Replay the dataset dials exactly as the engine applied them (events take
    # effect before the day's backup; values are clamped the same way).
    events = sorted(scenario.events, key=lambda e: e.at_day)
    ei = 0
    change = ds.daily_change_pct
    entropy = ds.entropy_pct
    rw_rate = 0.0
    min_change, min_entropy, max_entropy, max_rw = change, entropy, entropy, 0.0
    for s in trace:
        while ei < len(events) and events[ei].at_day <= s.day:
            ev = events[ei]
            ei += 1
            if ev.action == "set-change-rate" and ev.value is not None:
                change = max(0.0, min(100.0, ev.value))
            elif ev.action == "set-entropy" and ev.value is not None:
                entropy = max(0.0, min(100.0, ev.value))
            elif ev.action == "ransomware-start" and ev.value is not None:
                rw_rate = max(0.0, min(100.0, ev.value))
            elif ev.action == "ransomware-stop":
                rw_rate = 0.0
        min_change = min(min_change, change)
        min_entropy = min(min_entropy, entropy)
        max_entropy = max(max_entropy, entropy)
        max_rw = max(max_rw, rw_rate)

    n = len(trace)
    # Delivered work: terabytes under protection, a full store earning zero.
    protected = sum(s.logical_tb for s in trace if s.capacity_used_pct < 100.0)

    # The clean copies still on the shelf when the alarm fires. Generation d
    # is clean if it was written before the attack's first day; at alarm day A
    # the shelf holds days max(1, A−R+1)..A. No alarm, or an alarm before the
    # attack (a false one), leaves nothing to count.
    first_rw = next((s.day for s in trace if s.ransomware_active), -1)
    alarm = summary.alarm_day
    clean = 0
    if first_rw >= 1 and alarm >= first_rw:
        oldest_kept = max(1, alarm - retention + 1)
        clean = max(0, (first_rw - 1) - oldest_kept + 1)

    return {
        "durationDays": float(trace[-1].day),
        "protectedTbMean": round(protected / n, 1),
        "fullTb": float(ds.full_tb),
        "minChangePct": round(min_change, 2),
        "minEntropyPct": round(min_entropy, 1),
        "maxEntropyPct": round(max_entropy, 1),
        "applianceUsableTb": float(APPLIANCES[scenario.appliance].usable_tb),
        "peakCapacityPct": round(max(s.capacity_used_pct for s in trace), 2),
        "peakIndexPressurePct": round(max(s.index_pressure_pct for s in trace), 1),
        "peakWindowHours": round(max(s.backup_window_hours for s in trace), 3),
        "peakPhysicalTb": round(max(s.physical_tb for s in trace), 1),
        "finalRatio": float(trace[-1].dedupe_ratio),
        "finalGenerations": float(trace[-1].generations_retained),
        "finalLogicalTb": float(trace[-1].logical_tb),
        "encryptedDays": float(sum(1 for s in trace if s.host_encrypted)),
        "ransomwareDays": float(sum(1 for s in trace if s.ransomware_active)),
        "maxRansomwareRatePct": round(max_rw, 2),
        "alarmDay": float(alarm),
        "alarmLagDays": float(alarm - first_rw) if first_rw >= 1 and alarm >= first_rw else -1.0,
        "cleanGenerationsAtAlarm": float(clean),
        "validationErrors": float(sum(1 for v in validations if v.level == "error")),
    }


# --- Criteria shared between labs ------------------------------------------

def _work(floor_tb: int) -> Criterion:
    return Criterion(
        id="work", label=f"Mean data under protection at least {floor_tb} TB",
        metric="protectedTbMean", op=">=", threshold=floor_tb, unit="TB",
        weight=2.0, guards_work=True, explain_id="dedupe-ratio", equation=EQ_RATIO,
        why=L(
            standard=(
                f"Work is the logical data under protection — retained "
                f"generations × full size, the numerator of the ratio — "
                f"averaged over every day of the run; {floor_tb} TB is the "
                "floor. A day the store is full counts as zero, because a "
                "full store fails its backups. Shrinking the dataset or the "
                "retention is therefore not a way through. The proxy is "
                "illustrative, not a benchmark."
            ),
            novice=(
                f"A backup appliance is bought to keep copies safe, so the "
                f"lab counts how much it is keeping: the size of one full "
                f"backup times the number of daily copies on the shelf. "
                f"Averaged over every day of the run, that has to reach "
                f"{floor_tb} TB. If the appliance fills up, its backups fail, "
                "and those days count as nothing. So you cannot win by "
                "protecting a tiny dataset or by keeping only a copy or two. "
                "This is a simple stand-in for useful protection, not a real "
                "benchmark score."
            ),
            expert=(
                f"Mean over all days of logical TB (gens × full), store-full "
                f"days zero; floor {floor_tb} TB. Illustrative proxy."
            ),
        ),
    )


def _dataset_size(tb: int) -> Criterion:
    return Criterion(
        id="dataset-size", label=f"Full backup at least {tb} TB",
        metric="fullTb", op=">=", threshold=tb, unit="TB",
        explain_id="dedupe-ratio", equation=EQ_RATIO,
        why=L(
            standard=(
                f"The customer's dataset is {tb} TB and it is not yours to "
                "shrink. Both sides of the ratio scale with the full size, so "
                "a smaller dataset makes every capacity line easier without "
                "teaching anything."
            ),
            novice=(
                f"The data you are asked to protect is {tb} TB in size. That "
                "is the customer's data, so the Full backup slider has to "
                f"stay at {tb} TB or more. Making the dataset smaller would "
                "make everything fit, but it would be protecting less than "
                "you were asked to."
            ),
            expert=f"full ≥ {tb} TB; the dataset is a given, not a lever.",
        ),
    )


def _change_rate(pct: float) -> Criterion:
    return Criterion(
        id="change-rate", label=f"Daily change never below {pct:g}%",
        metric="minChangePct", op=">=", threshold=pct, unit="%/day",
        explain_id="novelty", equation=EQ_NOVEL,
        why=L(
            standard=(
                f"Churn is a property of the data: this estate rewrites "
                f"{pct:g}% of itself a day. Novel data is churn ÷ cf, so a "
                "lower change rate would shrink every generation's footprint "
                "for free. Timed changes to the rate are measured too."
            ),
            novice=(
                f"Every day about {pct:g}% of this data changes, and only the "
                "changed part adds new chunks to the appliance. How fast data "
                "changes belongs to the customer's applications, not to you, "
                f"so the Daily change slider must stay at {pct:g}% or higher "
                "for the whole run. Lowering it would make the problem go "
                "away without solving it."
            ),
            expert=f"min over the run of c ≥ {pct:g}%/day, events included.",
        ),
    )


def _entropy_floor(pct: int) -> Criterion:
    return Criterion(
        id="entropy-floor", label=f"Dataset entropy never below {pct}",
        metric="minEntropyPct", op=">=", threshold=pct, unit="",
        explain_id="compression", equation=EQ_CF,
        why=L(
            standard=(
                f"Entropy {pct} fixes local compression at cf = "
                f"{1.0 + (1.0 - pct / 100.0):.1f}. More compressible data "
                "would shrink every stored chunk, and how compressible the "
                "data is belongs to the customer, not to the plan."
            ),
            novice=(
                "Entropy says how random the data looks: 0 is like plain "
                "text, which squeezes down well, and 100 is like encrypted "
                "data, which does not squeeze at all. This customer's data "
                f"sits at {pct}, where the appliance squeezes it to a little "
                f"over half its size (a factor of "
                f"{1.0 + (1.0 - pct / 100.0):.1f}). You cannot make someone's "
                f"data more squeezable, so the Entropy slider must stay at "
                f"{pct} or above."
            ),
            expert=f"min entropy ≥ {pct} → cf ≤ {1.0 + (1.0 - pct / 100.0):.1f}.",
        ),
    )


def _full_run(days: int) -> Criterion:
    return Criterion(
        id="full-run", label=f"Run lasts at least {days} days",
        metric="durationDays", op=">=", threshold=days, unit="days",
        explain_id="dedupe-ratio", equation=EQ_RATIO,
        why=L(
            standard=(
                "The store keeps growing until the retention window is full "
                "and cleaning starts reclaiming expired generations. A "
                f"run shorter than {days} days would be graded before the "
                "footprint it is graded on had arrived."
            ),
            novice=(
                "An appliance fills up slowly: one more copy arrives every "
                "day until the shelf holds as many copies as the retention "
                "setting allows, and only then does it start throwing the "
                "oldest away. If the run were shorter it would end before "
                "the appliance reached its real, settled size, so the lab "
                f"needs at least {days} days."
            ),
            expert=f"≥ {days} days, so the window fills and GC reaches steady state.",
        ),
    )


def _capacity(pct: int) -> Criterion:
    return Criterion(
        id="capacity", label=f"Store never above {pct}% full",
        metric="peakCapacityPct", op="<=", threshold=pct, unit="%", weight=2.0,
        explain_id="dedupe-ratio", equation=EQ_RATIO,
        why=L(
            standard=(
                f"Physical stored is the ratio's denominator and the thing "
                f"the disks hold. {pct}% is the planning threshold: above it "
                "one surprise — a re-baseline, an encrypted source — fills "
                "the store, and a full store fails its backups."
            ),
            novice=(
                f"The appliance's disks must never be more than {pct}% full. "
                "What fills them is the physical data: the chunks actually "
                "stored after duplicates are removed. Planners leave the "
                "last part empty on purpose, because one bad surprise can "
                "use it up in days, and an appliance that is completely full "
                "cannot take tonight's backup."
            ),
            expert=f"max(physical ÷ usable) ≤ {pct}%, the planning threshold.",
        ),
    )


def _rated_ingest() -> Criterion:
    return Criterion(
        id="rated-ingest", label="Fingerprint index never outgrows its RAM",
        metric="peakIndexPressurePct", op="<=", threshold=0, unit="%", weight=2.0,
        explain_id="index-pressure", equation=EQ_INDEX,
        why=L(
            standard=(
                "Every unique chunk costs an index entry, and the index "
                "lives in RAM. Once index/RAM passes 1 the max(0, …) term "
                "wakes up and ingest falls below the rated figure — on a "
                "small appliance this knee arrives long before the disks "
                "fill. The index figures are flagged estimates."
            ),
            novice=(
                "To spot a duplicate, the appliance looks every chunk up in "
                "a list of fingerprints, and it keeps that list in fast "
                "memory (RAM). Each new unique chunk makes the list longer. "
                "When the list no longer fits in memory, lookups go to disk "
                "and the whole appliance slows down. On a small appliance "
                "this happens well before the disks are full, so watch the "
                "Index pressure readout, not just the capacity bar. The "
                "memory sizes here are estimates."
            ),
            expert="max(index/RAM − 1) ≤ 0: ingest stays at base. Index constants are estimates.",
        ),
    )


def _valid_plan() -> Criterion:
    return Criterion(
        id="valid-plan", label="Plan has no validation errors",
        metric="validationErrors", op="<=", threshold=0, unit="errors",
        explain_id="compression", equation=EQ_CF,
        why=L(
            standard=(
                "The planning review's one hard error is a first full that "
                "cannot fit: full ÷ cf, plus metadata, against usable "
                "capacity. No retention policy rescues that. Warnings are "
                "allowed; the simulator exists to show their consequence."
            ),
            novice=(
                "The Planning review on the left checks your plan. Yellow "
                "warnings are allowed, because the simulator is there to "
                "show you what they lead to. A red error is not: it means "
                "even the very first backup, after it has been squeezed "
                "down, is bigger than the whole appliance, and nothing else "
                "you change can fix that."
            ),
            expert="Zero error-level findings (first-fit: full/cf·(1+ovh) ≤ usable).",
        ),
    )


# --- Lab 1: how long can the branch box remember? --------------------------

_BRANCH_DATA = Dataset(full_tb=20, daily_change_pct=2.0, entropy_pct=30)

_BRANCH_START = Scenario(
    appliance="dd3410", dataset=_BRANCH_DATA,
    schedule=Schedule(retention_days=90), duration_days=120,
)

BRANCH_MEMORY = Lab(
    id="branch-box-memory",
    title="How long can the branch box remember?",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "Retention is the ratio's engine, so turn it up — on the "
                "entry appliance, protecting 20 TB that changes 2% a day. "
                "Get the highest dedupe ratio you can while the store stays "
                "under 85% and the fingerprint index never outgrows its RAM."
            ),
            novice=(
                "The more daily copies an appliance keeps, the better its "
                "dedupe ratio looks, because each extra copy is mostly "
                "duplicates. Your job is to find out how many copies the "
                "smallest appliance (the DD3410) can really keep of a 20 TB "
                "dataset that changes 2% a day. Push the dedupe ratio as "
                "high as you can, but the disks must stay under 85% full "
                "and the appliance must never slow down because its "
                "fingerprint list has outgrown its memory."
            ),
            expert=(
                "DD3410, 20 TB, 2%/day, entropy 30: maximize final ratio "
                "with capacity ≤ 85% and zero index pressure."
            ),
        ),
        constraints=[
            L(standard="The entry appliance: no more than 40 TB usable.",
              novice="Stay on the smallest appliance, the DD3410, which has 40 TB of usable disk. A bigger box is not in the budget.",
              expert="usable ≤ 40 TB (DD3410)."),
            L(standard="The dataset is given: at least 20 TB, at least 2% daily change, entropy at least 30.",
              novice="The data belongs to the customer: keep Full backup at 20 TB or more, Daily change at 2% or more, and Entropy at 30 or more.",
              expert="full ≥ 20 TB, c ≥ 2%/day, entropy ≥ 30."),
            L(standard="Run at least 120 days, with no validation errors.",
              novice="Let the run last at least 120 days so the appliance reaches its settled size, and keep the Planning review free of red errors.",
              expert="≥ 120 days, zero errors."),
        ],
        delivered_work=L(
            standard="At least 500 TB under protection, averaged over the run.",
            novice="On average the appliance must be keeping at least 500 TB of backups safe — roughly thirty daily copies of the 20 TB dataset. Keeping only a few copies does not count.",
            expert="protectedTbMean ≥ 500.",
        ),
    ),
    criteria=[
        _work(500),
        _rated_ingest(),
        _capacity(85),
        Criterion(
            id="entry-appliance", label="Appliance no larger than 40 TB usable",
            metric="applianceUsableTb", op="<=", threshold=40, unit="TB",
            explain_id="dedupe-ratio", equation=EQ_RATIO,
            why=L(
                standard=(
                    "The lab is about what the entry box can hold. A larger "
                    "appliance has more disk and more index RAM, which moves "
                    "both limits without explaining either."
                ),
                novice=(
                    "This lab is about the smallest appliance, the DD3410, "
                    "with 40 TB of usable disk. Picking a bigger appliance "
                    "gives you more disk and more memory, so both limits "
                    "move out of the way and you never find out where they "
                    "were."
                ),
                expert="usable ≤ 40 TB; the DD3410's 8 GB index RAM is the point.",
            ),
        ),
        _dataset_size(20),
        _change_rate(2),
        _entropy_floor(30),
        _full_run(120),
        _valid_plan(),
    ],
    objective=Objective(
        label="Final dedupe ratio", metric="finalRatio", direction="maximize",
        par=35.7, worst=31.0, unit="×",
        explain_id="dedupe-ratio", equation=EQ_RATIO,
    ),
    hints=[
        L(
            standard=(
                "Run the start as it is and read the Planning review and the "
                "Index pressure instrument. The capacity bar never reaches "
                "85%. Something else is failing first."
            ),
            novice=(
                "Press Run and grade on the start as it is, then look at two "
                "places: the Planning review on the left, and the Index "
                "pressure readout on the right. Notice that the disks never "
                "get near 85% full. The plan fails for a different reason, "
                "and the yellow warning names it."
            ),
            expert="The 90-generation start fails on index pressure, not capacity.",
        ),
        L(
            standard=(
                "Two limits grow with the same physical terabytes: the "
                "disks (40 TB) and the index (8 GB of RAM, an estimate). At "
                "8 KiB chunks the index fills at about 25 TB of stored "
                "data — well short of 85% of the disks. The binding limit "
                "on this box is RAM."
            ),
            novice=(
                "Every terabyte the appliance stores uses up two things at "
                "once: disk space, and room in the fingerprint list that "
                "lives in memory. The DD3410 has 40 TB of disk but only "
                "8 GB of memory for that list, and the list is full when "
                "about 25 TB is stored. So memory runs out first, long "
                "before the disks reach 85%. That is the limit you have to "
                "plan around on this appliance."
            ),
            expert="Index knee ≈ 25.6 TB stored (8 GB ÷ 0.3125 GB/TB) < 0.85 × 40 TB.",
        ),
        L(
            standard=(
                "Stored data settles at (full ÷ cf) × (1 + (R − 1) × c). "
                "With 20 TB, cf = 1.7 and c = 2%, solve for the largest R "
                "that keeps it under the index knee, then check one "
                "generation either side with the Retention slider."
            ),
            novice=(
                "The stored size settles at the first backup's squeezed "
                "size (20 TB ÷ 1.7, about 11.8 TB) plus 2% of that for "
                "every extra copy kept. Work out how many copies fit before "
                "the total reaches about 25 TB, set the Retention slider "
                "there, and then try one more and one fewer. The best "
                "answer is the last one where Index pressure still reads "
                "zero."
            ),
            expert="Largest R with (20/1.7)(1 + 0.02(R − 1)) ≤ 25.6; step the slider by one.",
        ),
    ],
    start=_BRANCH_START.model_dump(by_alias=True),
)


# --- Lab 2: the tenant who encrypted first ---------------------------------

_ENCRYPT = [SimEvent(at_day=30, action="enable-host-encryption")]
_TENANT_DATA = Dataset(full_tb=50, daily_change_pct=1.0, entropy_pct=30)

_TENANT_START = Scenario(
    appliance="dd9910", dataset=_TENANT_DATA,
    schedule=Schedule(retention_days=30), duration_days=120, events=_ENCRYPT,
)

ENCRYPTED_TENANT = Lab(
    id="encrypted-tenant",
    title="The tenant who encrypted first",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "On day 30 the source turns on host-side encryption, and it "
                "stays on: policy, not a mistake you may undo. Every backup "
                "is now unique ciphertext. Keep the nightly backup inside a "
                "2-hour window and the store under 85%, and protect as much "
                "as the physics still allows."
            ),
            novice=(
                "On day 30 the customer starts encrypting their data before "
                "it reaches the appliance, and their security team will not "
                "turn it off. Encrypted data looks different every night, so "
                "the appliance can no longer find duplicates and has to "
                "store every backup in full. Your job is to make a plan that "
                "survives this: each night's backup must finish within "
                "2 hours, the disks must stay under 85% full, and within "
                "those limits you should keep as much backup data safe as "
                "you can."
            ),
            expert=(
                "Host encryption from day ≤ 30, permanent. Window ≤ 2 h, "
                "capacity ≤ 85%, maximize final logical TB."
            ),
        ),
        constraints=[
            L(standard="The source is encrypted for at least 90 days of the run.",
              novice="The encryption has to stay on: at least 90 days of the run must be encrypted. Pressing Reset (clear events) or Disable source encryption breaks this rule.",
              expert="encryptedDays ≥ 90."),
            L(standard="The dataset is given: a full backup of at least 50 TB.",
              novice="The customer's data is 50 TB, so keep the Full backup slider at 50 TB or more.",
              expert="full ≥ 50 TB."),
            L(standard="Every nightly backup finishes within 2 hours, and the store never passes 85%.",
              novice="No single night's backup may take longer than 2 hours, and the disks may never be more than 85% full.",
              expert="max window ≤ 2 h; max capacity ≤ 85%."),
            L(standard="Run at least 120 days, encryption included, with no validation errors.",
              novice="Let the run last at least 120 days, and keep the Planning review free of red errors.",
              expert="≥ 120 days, zero errors."),
        ],
        delivered_work=L(
            standard="At least 500 TB under protection, averaged over the run — about ten generations.",
            novice="On average the appliance must be keeping at least 500 TB of backups safe — about ten daily copies of the 50 TB dataset. Keeping almost nothing does not count.",
            expert="protectedTbMean ≥ 500.",
        ),
    ),
    criteria=[
        _work(500),
        Criterion(
            id="stays-encrypted", label="Source encrypted for at least 90 days",
            metric="encryptedDays", op=">=", threshold=90, unit="days", weight=2.0,
            explain_id="novelty", equation=EQ_NOVEL,
            why=L(
                standard=(
                    "With fresh session keys every backup is all "
                    "encrypted-writes: novel equals the full size, at a "
                    "factor of 1.0, every night. That is the condition the "
                    "lab is set in. Turning the encryption off again is the "
                    "right advice and not the assignment."
                ),
                novice=(
                    "When the source encrypts with a new key every night, "
                    "nothing in tonight's backup matches last night's, so "
                    "the appliance has to store all of it, with no "
                    "squeezing. The lab is about living with that. In real "
                    "life you would ask the customer to encrypt after the "
                    "backup instead of before, and that is good advice — "
                    "but here the encryption must stay on for at least 90 "
                    "days of the run."
                ),
                expert="Host-encrypted ≥ 90 days: novel = full × 1.0 nightly is the premise.",
            ),
        ),
        Criterion(
            id="window", label="Longest backup window at most 2 hours",
            metric="peakWindowHours", op="<=", threshold=2.0, unit="h", weight=2.0,
            explain_id="backup-window", equation=EQ_WINDOW,
            why=L(
                standard=(
                    "Ciphertext removes the dedupe speedup (it falls to 1) "
                    "and floods the fingerprint index with unique chunks, so "
                    "ingest falls below the rated figure as well. Both "
                    "terms of the denominator shrink at once. The window "
                    "depends on how much is stored, which is retention × "
                    "full size."
                ),
                novice=(
                    "A night's backup normally finishes fast because the "
                    "appliance only has to store the small part that "
                    "changed. Encrypted data takes that shortcut away: "
                    "everything has to be stored. It also fills the "
                    "fingerprint list with chunks that will never match "
                    "anything, and once that list outgrows memory the "
                    "appliance slows down. So the more encrypted copies "
                    "you keep, the longer each night's backup takes."
                ),
                expert="Speedup → 1 and ingest = base ÷ (1 + k × pressure); pressure ∝ R × full.",
            ),
        ),
        _capacity(85),
        _dataset_size(50),
        _full_run(120),
        _valid_plan(),
    ],
    objective=Objective(
        label="Data under protection at the end", metric="finalLogicalTb",
        direction="maximize", par=850.0, worst=500.0, unit="TB",
        explain_id="dedupe-ratio", equation=EQ_RATIO,
    ),
    hints=[
        L(
            standard=(
                "Run the start and scrub to day 60. The ratio has collapsed "
                "to about 1, as the guided scenario promised. Now read the "
                "Backup window and Index pressure instruments: capacity is "
                "not the line that fails."
            ),
            novice=(
                "Press Run and grade, then drag the playback slider to "
                "about day 60. The dedupe ratio has fallen to about 1, "
                "which means the appliance is storing everything in full. "
                "Now look at the Backup window and Index pressure readouts "
                "on the right. The disks are not full yet. It is the "
                "nightly backup that has become too slow."
            ),
            expert="At R = 30 the store is 74% full but the window is 3.8 h: index-bound.",
        ),
        L(
            standard=(
                "The obvious fix is the faster appliance. Try it. The "
                "all-flash box has a higher rated ingest and half the index "
                "RAM, and under ciphertext the index is what sets ingest. "
                "Compare the two boxes at the same retention."
            ),
            novice=(
                "The natural idea is to pick the fastest appliance, the "
                "all-flash one. Try it and look at the Backup window again. "
                "It is rated faster, but it has only half as much memory "
                "for the fingerprint list, and with encrypted data it is "
                "that memory, not the rated speed, that decides how fast "
                "backups go. Compare both appliances with the same "
                "Retention setting."
            ),
            expert="20 GB/s with 96 GB of index RAM loses to 15 GB/s with 192 GB here.",
        ),
        L(
            standard=(
                "With the ratio at 1, stored data is simply retention × "
                "50 TB, and retention is the one lever left. On the "
                "appliance with the most index RAM, lower it a generation "
                "at a time until the window is back under 2 hours, and "
                "stop there."
            ),
            novice=(
                "With encrypted data, the amount stored is just the number "
                "of copies you keep times 50 TB. So the Retention slider is "
                "the only thing left to change. Choose the appliance with "
                "the most memory (the DD9910), then lower Retention one "
                "step at a time until the longest Backup window is under "
                "2 hours. Stop as soon as it passes, because every copy you "
                "give up is protection you lose."
            ),
            expert="DD9910; largest R with window ≤ 2 h. Smaller full would help but is fixed.",
        ),
    ],
    start=_TENANT_START.model_dump(by_alias=True),
)


# --- Lab 3: the alarm that came late ---------------------------------------

_SLOW_RW = [SimEvent(at_day=30, action="ransomware-start", value=1)]
_CHURN_DATA = Dataset(full_tb=100, daily_change_pct=5.0, entropy_pct=30)

_LATE_START = Scenario(
    appliance="dd-all-flash", dataset=_CHURN_DATA,
    schedule=Schedule(retention_days=30), duration_days=150, events=_SLOW_RW,
)

LATE_ALARM = Lab(
    id="late-alarm",
    title="The alarm that came late",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "Slow ransomware — 1% of the dataset a day — starts on day "
                "30 in a busy database that already changes 5% a day. The "
                "entropy alarm reads the changed data, and here honest churn "
                "dilutes the ciphertext. Make sure that when the alarm does "
                "fire, at least 7 clean generations are still on the shelf, "
                "at the rated ingest, with the smallest store you can."
            ),
            novice=(
                "Ransomware starts on day 30 and quietly encrypts 1% of the "
                "data each day. The appliance has a smoke alarm: it checks "
                "how random each day's changed data looks. But this "
                "database already changes 5% a day in the normal way, and "
                "all that ordinary change hides the small encrypted part, "
                "so the alarm fires late. An alarm only helps if a clean "
                "copy from before the attack is still being kept. Make a "
                "plan where at least 7 clean daily copies are still on the "
                "shelf on the day the alarm fires, without slowing the "
                "appliance down, and using as little disk as you can."
            ),
            expert=(
                "1%/day ransomware from day 30 under 5%/day churn: ≥ 7 "
                "pre-attack generations retained at the alarm, zero index "
                "pressure, minimize peak physical."
            ),
        ),
        constraints=[
            L(standard="The attack is given: ransomware active at least 120 days, never faster than 1% a day.",
              novice="You do not get to choose the attacker. The ransomware in the lab's start must stay: active for at least 120 days, and never faster than 1% a day. The Unleash ransomware button adds a 3% attack, which breaks this rule, and so does Reset (clear events).",
              expert="ransomwareDays ≥ 120; max rate ≤ 1%/day."),
            L(standard="The dataset is given: at least 100 TB, at least 5% daily change, entropy exactly 30, never host-encrypted.",
              novice="The data belongs to the customer: keep Full backup at 100 TB or more, Daily change at 5% or more, and Entropy at 30, and do not switch on source encryption.",
              expert="full ≥ 100 TB, c ≥ 5%/day, entropy = 30, encryptedDays = 0."),
            L(standard="The index never outgrows its RAM and the store never passes 85%.",
              novice="The appliance must never slow down (Index pressure stays at zero), and the disks may never be more than 85% full.",
              expert="Zero index pressure; capacity ≤ 85%."),
            L(standard="Run at least 150 days, with no validation errors.",
              novice="Let the run last at least 150 days, and keep the Planning review free of red errors.",
              expert="≥ 150 days, zero errors."),
        ],
        delivered_work=L(
            standard="At least 2500 TB under protection, averaged over the run.",
            novice="On average the appliance must be keeping at least 2500 TB of backups safe — about twenty-five daily copies of the 100 TB dataset. Keeping almost nothing does not count.",
            expert="protectedTbMean ≥ 2500.",
        ),
    ),
    criteria=[
        _work(2500),
        Criterion(
            id="clean-copies", label="At least 7 clean generations when the alarm fires",
            metric="cleanGenerationsAtAlarm", op=">=", threshold=7,
            unit="generations", weight=3.0,
            explain_id="novelty", equation=EQ_NOVEL,
            why=L(
                standard=(
                    "The alarm reads the entropy of the changed data: churn "
                    "at the dataset's entropy mixed with encrypted-writes at "
                    "98. It fires when the mix is 20 points over baseline. "
                    "With churn five times the attack rate the mix starts "
                    "near 41 and only crosses 50 once enough of the estate "
                    "is ciphertext that the clean churn has shrunk. A "
                    "generation is clean if it was written before the "
                    "attack; it counts only if retention has not expired it "
                    "by the alarm day. No alarm, or a false one before the "
                    "attack, counts zero."
                ),
                novice=(
                    "Each day the appliance looks at the data that changed "
                    "and asks how random it looks. Normal changes look "
                    "about 30% random here; encrypted data looks 98% "
                    "random. The alarm fires when the day's mix reaches 50. "
                    "On day 30 the mix is five parts normal change to one "
                    "part ransomware, which is only about 41, so no alarm. "
                    "It fires weeks later, once so much data is already "
                    "encrypted that there is less normal change left to "
                    "hide behind. The lab then counts the daily copies on "
                    "the shelf that were made before day 30. Copies older "
                    "than your Retention setting have been thrown away and "
                    "do not count. If the alarm never fires, or fires "
                    "before the attack, the count is zero."
                ),
                expert=(
                    "Stream entropy = (churn × 30 + rw × 98) ÷ (churn + rw) "
                    "≥ 50; clean = pre-attack generations inside R at the "
                    "alarm day; none on no alarm or a false one."
                ),
            ),
        ),
        _rated_ingest(),
        _capacity(85),
        Criterion(
            id="attack-runs", label="Ransomware active at least 120 days",
            metric="ransomwareDays", op=">=", threshold=120, unit="days",
            explain_id="novelty", equation=EQ_NOVEL,
            why=L(
                standard=(
                    "The attack is the premise. It is undetected at the "
                    "source, so nobody stops it, and clearing the event "
                    "removes the problem rather than solving it."
                ),
                novice=(
                    "The ransomware is the situation the lab puts you in, "
                    "and nobody at the customer has noticed it, so nobody "
                    "stops it. It has to be active for at least 120 days of "
                    "the run. If you clear the events or halt the "
                    "ransomware, there is nothing left to detect."
                ),
                expert="ransomwareDays ≥ 120: the encrypted-writes term must be present.",
            ),
        ),
        Criterion(
            id="slow-attack", label="Ransomware never faster than 1% a day",
            metric="maxRansomwareRatePct", op="<=", threshold=1, unit="%/day",
            explain_id="novelty", equation=EQ_NOVEL,
            why=L(
                standard=(
                    "A loud attacker is easy: at 3% a day the "
                    "encrypted-writes term dominates the changed data and "
                    "the alarm fires at once. The lab is about the quiet "
                    "one, and you do not choose your attacker."
                ),
                novice=(
                    "A fast attack is easy to catch: at 3% a day the "
                    "encrypted part is a big share of what changed, and the "
                    "alarm fires on the first day. This lab is about a slow "
                    "attacker, at 1% a day, who hides inside normal change. "
                    "You do not get to pick a louder one, so the attack "
                    "rate must never go above 1% a day."
                ),
                expert="rw ≤ 1%/day; at 3% the mix clears the threshold on day one.",
            ),
        ),
        _dataset_size(100),
        _change_rate(5),
        _entropy_floor(30),
        Criterion(
            id="entropy-ceiling", label="Dataset entropy never above 30",
            metric="maxEntropyPct", op="<=", threshold=30, unit="",
            explain_id="compression", equation=EQ_CF,
            why=L(
                standard=(
                    "Raising the dataset's entropy mid-run makes all the "
                    "churn look random and trips the alarm on honest data. "
                    "That is a false alarm with the cause hidden inside it, "
                    "and it costs compression as well."
                ),
                novice=(
                    "If you made the customer's normal data look more "
                    "random, the alarm would fire straight away — but it "
                    "would be firing at ordinary data, not at the attack, "
                    "and an alarm that fires at everything tells you "
                    "nothing. Random-looking data also squeezes down less, "
                    "so it costs disk too. The Entropy slider must stay "
                    "at 30."
                ),
                expert="max entropy ≤ 30: no tripping the alarm with incompressible churn.",
            ),
        ),
        Criterion(
            id="no-host-encryption", label="Source never host-encrypted",
            metric="encryptedDays", op="<=", threshold=0, unit="days",
            explain_id="novelty", equation=EQ_NOVEL,
            why=L(
                standard=(
                    "Encrypting the source makes every stream read 98 and "
                    "fires the alarm on the spot — by destroying dedupe and "
                    "the alarm's meaning together. An instrument pinned at "
                    "full scale detects nothing."
                ),
                novice=(
                    "Switching on source encryption would make every backup "
                    "look 98% random, so the alarm would fire immediately. "
                    "But it would fire every night from then on whether or "
                    "not there was an attack, and the appliance would have "
                    "to store every backup in full. A smoke alarm that "
                    "never stops ringing is no use, so source encryption "
                    "must stay off."
                ),
                expert="encryptedDays = 0: a saturated entropy instrument is not a detector.",
            ),
        ),
        _full_run(150),
        _valid_plan(),
    ],
    objective=Objective(
        label="Peak physical stored", metric="peakPhysicalTb",
        direction="minimize", par=260.0, worst=340.0, unit="TB",
        explain_id="dedupe-ratio", equation=EQ_RATIO,
    ),
    hints=[
        L(
            standard=(
                "Run the start and find the alarm in the event log. In the "
                "guided scenario it fired within two days. Here it takes "
                "weeks. Compare the two datasets' change rates and watch "
                "the stream-entropy strip chart climb."
            ),
            novice=(
                "Press Run and grade, then look in the Event log for the "
                "day the entropy alarm fires. In the guided scenario "
                "'Entropy as a smoke alarm' it fires within two days of the "
                "attack. Here it takes many weeks. The difference is the "
                "Daily change setting: this data changes much more. Watch "
                "the stream entropy chart on the right creep upward day "
                "by day."
            ),
            expert="Alarm lag is ~52 days here against ≤ 2 in the guided scenario; churn is why.",
        ),
        L(
            standard=(
                "The alarm needs the changed data's entropy at 50: "
                "(churn × 30 + 1 × 98) ÷ (churn + 1). That holds only when "
                "clean churn is under about 2.4% of the dataset. Churn "
                "applies to the clean fraction, so it falls as the attack "
                "spreads: 5% × clean fraction ≤ 2.4% puts the alarm about "
                "52 days after the attack begins."
            ),
            novice=(
                "The alarm fires when the day's changed data looks 50% "
                "random. Normal change looks 30% random and the 1% of "
                "ransomware looks 98% random. For the mix to reach 50, "
                "normal change has to be below about 2.4% of the data. It "
                "starts at 5%, but only clean data changes normally, and "
                "the ransomware takes away 1% of the clean data every day. "
                "After about 52 days only 48% of the data is clean, 5% of "
                "that is 2.4%, and the alarm finally fires."
            ),
            expert="98r + 30c' ≥ 50(r + c') → c' ≤ 2.4r; c' = 5% × (1 − 0.01t) → t ≈ 52.",
        ),
        L(
            standard=(
                "You cannot make the alarm earlier, so retention has to "
                "outlast the dwell time: the alarm lag plus the 7 clean "
                "generations. Every extra generation also strands "
                "incompressible ciphertext, so go no longer than you must "
                "— and check which appliance's index RAM carries it."
            ),
            novice=(
                "Nothing you are allowed to change makes the alarm fire "
                "sooner. What you can change is how long copies are kept. "
                "Retention has to be longer than the time the attack goes "
                "unnoticed (about 52 days) plus the 7 clean copies you "
                "need. But encrypted data cannot be squeezed, so each "
                "extra copy costs real disk and real fingerprint memory. "
                "Set Retention just long enough, and then check Index "
                "pressure: one of the appliances does not have the memory "
                "for it."
            ),
            expert="R ≥ lag + 7 + 1; minimize beyond that. The all-flash index knees near R = 59.",
        ),
    ],
    start=_LATE_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [BRANCH_MEMORY, ENCRYPTED_TENANT, LATE_ALARM]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Reference solutions and gaming attempts (server-side only) ------------

REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    "branch-box-memory": _BRANCH_START.model_copy(update={
        "schedule": Schedule(retention_days=38)}),
    "encrypted-tenant": _TENANT_START.model_copy(update={
        "schedule": Schedule(retention_days=17)}),
    "late-alarm": _LATE_START.model_copy(update={
        "appliance": "dd9910", "schedule": Schedule(retention_days=60)}),
}

_TINY = Dataset(full_tb=0.1, daily_change_pct=0.0, entropy_pct=30)

GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "branch-box-memory": {
        "zero load": Scenario(
            appliance="dd3410", dataset=_TINY,
            schedule=Schedule(retention_days=365), duration_days=120),
        "a bigger appliance": _BRANCH_START.model_copy(update={"appliance": "dd9910"}),
        "quieter data": _BRANCH_START.model_copy(update={
            "dataset": Dataset(full_tb=20, daily_change_pct=0.5, entropy_pct=30)}),
        "more compressible data": _BRANCH_START.model_copy(update={
            "dataset": Dataset(full_tb=20, daily_change_pct=2.0, entropy_pct=0)}),
        "quiet the data mid-run": _BRANCH_START.model_copy(update={
            "events": [SimEvent(at_day=2, action="set-change-rate", value=0)]}),
        "short run": _BRANCH_START.model_copy(update={"duration_days": 30}),
        "long run with two generations": _BRANCH_START.model_copy(update={
            "schedule": Schedule(retention_days=2), "duration_days": 730}),
        "fill the store": _BRANCH_START.model_copy(update={
            "schedule": Schedule(retention_days=365), "duration_days": 365}),
    },
    "encrypted-tenant": {
        "zero load": Scenario(
            appliance="dd9910", dataset=_TINY,
            schedule=Schedule(retention_days=30), duration_days=120,
            events=_ENCRYPT),
        "clear the events": _TENANT_START.model_copy(update={"events": []}),
        "turn the encryption back off": _TENANT_START.model_copy(update={
            "events": _ENCRYPT + [SimEvent(at_day=37, action="disable-host-encryption")]}),
        "encrypt on the last day": _TENANT_START.model_copy(update={
            "events": [SimEvent(at_day=120, action="enable-host-encryption")]}),
        "the faster appliance": _TENANT_START.model_copy(update={
            "appliance": "dd-all-flash"}),
        "a smaller dataset": _TENANT_START.model_copy(update={
            "dataset": Dataset(full_tb=20, daily_change_pct=1.0, entropy_pct=30)}),
        "short run": _TENANT_START.model_copy(update={
            "schedule": Schedule(retention_days=17), "duration_days": 40}),
        "one generation for a long time": _TENANT_START.model_copy(update={
            "schedule": Schedule(retention_days=1), "duration_days": 730}),
    },
    "late-alarm": {
        "zero load": Scenario(
            appliance="dd9910", dataset=_TINY,
            schedule=Schedule(retention_days=60), duration_days=150,
            events=_SLOW_RW),
        "clear the events": _LATE_START.model_copy(update={
            "appliance": "dd9910", "schedule": Schedule(retention_days=60),
            "events": []}),
        "a louder attacker": _LATE_START.model_copy(update={
            "appliance": "dd9910",
            "events": [SimEvent(at_day=30, action="ransomware-start", value=3)]}),
        "halt the ransomware": _LATE_START.model_copy(update={
            "appliance": "dd9910", "schedule": Schedule(retention_days=60),
            "events": _SLOW_RW + [SimEvent(at_day=40, action="ransomware-stop")]}),
        "quieter data": _LATE_START.model_copy(update={
            "appliance": "dd9910",
            "dataset": Dataset(full_tb=100, daily_change_pct=2.0, entropy_pct=30)}),
        "quiet the data when the attack starts": _LATE_START.model_copy(update={
            "appliance": "dd9910",
            "events": _SLOW_RW + [SimEvent(at_day=30, action="set-change-rate", value=1)]}),
        "trip the alarm with random churn": _LATE_START.model_copy(update={
            "appliance": "dd9910",
            "events": _SLOW_RW + [SimEvent(at_day=30, action="set-entropy", value=100)]}),
        "trip the alarm by encrypting the source": _LATE_START.model_copy(update={
            "appliance": "dd9910",
            "events": _SLOW_RW + [SimEvent(at_day=30, action="enable-host-encryption")]}),
        "attack from day zero": _LATE_START.model_copy(update={
            "appliance": "dd9910", "schedule": Schedule(retention_days=60),
            "events": [SimEvent(at_day=0, action="ransomware-start", value=1)]}),
        "long retention on the flash box": _LATE_START.model_copy(update={
            "schedule": Schedule(retention_days=60)}),
        "short run": _LATE_START.model_copy(update={
            "appliance": "dd9910", "schedule": Schedule(retention_days=60),
            "duration_days": 90}),
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
