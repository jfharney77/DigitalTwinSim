"""Failure scenario: why free space keeps shrinking on a Data Domain.

``simulate_cleaning()`` is a second pure trace beside ``engine.simulate()``.
Same rule as the engine: no FastAPI, no IO, no timers, no randomness. It is
served by ``GET /api/lifecycle?scenario=cleaning-gc``.

What the real product does, and the sources for it (also carried in
``SCENARIOS`` so the UI can render them):

- Expiring or deleting a backup removes the file from the namespace. The
  physical segments stay on disk until the cleaning (garbage collection)
  cycle runs. "Only a filesys clean operation reclaims the physical storage
  used by files that are deleted and that are not present in a snapshot."
  (Dell KB 000012089). The default schedule is weekly, Tuesday 06:00, at a
  50% throttle.
- The "Cleanable GiB" column of ``filesys show space`` is an estimate, and
  "clean may have to be run multiple times before all potential space is
  reclaimed" (Dell KB 000054303). Dell KB 000434998 documents the same
  estimate running high or low on the *vault* appliance of a Cyber Recovery
  estate; this scenario is on the production appliance, so that KB is cited
  as a related case, not as the cause here.
- Two things keep deleted files' segments referenced, so cleaning skips
  them: a replication context that has not synced (its MTree replication
  snapshot still references the deleted files) and a snapshot nobody expired
  (Dell KB 000015007, 000054303).
- Retention Lock is a different mechanism: the backup application's delete
  is refused outright (Dell KB 000079803), so the file never leaves the
  namespace and never enters the Cleanable estimate at all. The backup
  catalog calls it expired; the appliance does not. When the lock ends the
  appliance still does not delete the file by itself.
- Dell advises against daily cleaning: "Running cleaning every day will
  fragment the data" (Dell KB 000012089).
- A Data Domain raises a space-usage alert when the data collection crosses a
  threshold; Dell's KB titles the alert "Space usage in Data Collection has
  exceeded 90% threshold". The thresholds are configurable, and the 95%
  figure used here is illustrative, so the alert text below is Dell's wording
  with this scenario's number in it, not a quotation. At 100% "no new data
  can be written to the DD, which may cause backups/replication to fail"
  (Dell KB 000054303) and the file system can go read-only, which blocks
  deletes too. Data Domain never deletes on its own, so stored backups are
  not lost to a full appliance; new ones are.

The ledger closes on every step:

    stored = live + reclaimable + held(replication) + held(snapshot) + held(lock)

All terabytes, hours and day counts are illustrative. The alert text, the
default schedule and the behaviours above are sourced.
"""

from __future__ import annotations

from .leveling import L
from .models import CleaningState, ScenarioInfo, SourceLink

SCENARIO_ID = "cleaning-gc"
DEFAULT_SCENARIO_ID = "attack-recovery"

CAPACITY_TB = 100
ALERT_PERCENT = 95  # illustrative; Dell's documented example threshold is 90%
LOCK_DAYS_AT_START = 21
START_HOUR = 1344  # eight weeks of backups before the scenario opens

CLEAN_PHASES = ("clean", "reclean")

# Dell's space-usage alert wording, with this scenario's illustrative
# threshold substituted for the 90% in Dell's KB title.
SPACE_ALERT = "Space usage in Data Collection has exceeded 95% threshold"

SOURCES = [
    SourceLink(
        label="Dell KB 000054303: how to solve high space consumption on Data Domain",
        url="https://www.dell.com/support/kbdoc/en-us/000054303/data-domain-how-to-resolve-issues-with-high-space-utilisation-or-a-lack-of-available-capacity-on-data-domain-restorers-ddrs",
    ),
    SourceLink(
        label="Dell KB 000015007: cleaning not recovering disk space",
        url="https://www.dell.com/support/kbdoc/en-us/000015007/71716-cleaning-not-recovering-disk-space",
    ),
    SourceLink(
        label="Dell KB 000012089: scheduling cleaning (default Tuesday 06:00, 50% throttle; daily cleaning fragments data)",
        url="https://www.dell.com/support/kbdoc/en-us/000012089/1327-scheduling-cleaning-on-a-ddr",
    ),
    SourceLink(
        label="Dell KB 000434998: the cleaning estimate on a Cyber Recovery vault (a related case)",
        url="https://www.dell.com/support/kbdoc/en-us/000434998/data-domain-cyber-recovery-vault-has-inaccurate-cleaning-estimate",
    ),
    SourceLink(
        label="Dell KB 000079803: Retention Lock frequently asked questions",
        url="https://www.dell.com/support/kbdoc/en-us/000079803/data-domain-retention-lock-frequently-asked-questions-faq",
    ),
    SourceLink(
        label=(
            "Dell Community: free space is decreasing constantly "
            "(2015, unanswered - the symptom as an administrator reports it)"
        ),
        url="https://www.dell.com/community/Data-Domain/Free-space-is-decreasing-constantly/td-p/7054720",
    ),
]

SCENARIOS = [
    ScenarioInfo(
        id=DEFAULT_SCENARIO_ID,
        title="Attack and recovery",
        summary=(
            "The life of a backup: deduplicated, vaulted through the air gap, "
            "locked, scanned, attacked in production and restored from the vault."
        ),
        hero="Air gap: open only when the vault opens it",
        is_failure=False,
        intro=L(
            novice=(
                "This page follows an organization's backups, not a machine. The "
                "everyday computers and databases are copied to a backup appliance, "
                "a Dell PowerProtect Data Domain. The appliance stores each "
                "repeated piece of data only once, a trick called deduplication, "
                "so hundreds of terabytes of backups fit in a few tens. Then a copy "
                "crosses the air gap, a network link that is switched off almost "
                "all the time, into a separate vault called Cyber Recovery. There "
                "the copy is locked so nobody can change or delete it, and a tool "
                "called CyberSense reads it to check it is not damaged. Then the "
                "night the whole design was built for: ransomware, software that "
                "scrambles data and demands payment, goes off in production, and "
                "has no way to reach the vault. Play the story and watch the gap: "
                "it opens only when the vault opens it."
            ),
            standard=(
                "This twin follows the data, not a machine. An estate, meaning the "
                "organization's servers and databases, backs up to a PowerProtect "
                "Data Domain; deduplication, which stores each repeated segment "
                "once, collapses hundreds of terabytes into a few tens; and a copy "
                "crosses a briefly-open air gap into a Cyber Recovery vault, where "
                "it is locked immutable and scanned by CyberSense, the vault's "
                "content analytics. Then the part every design decision assumed: "
                "ransomware detonates in production and finds the vault simply is "
                "not there. Play the trace and watch the gap open only when the "
                "vault opens it."
            ),
            expert=(
                "Backup to Data Domain, 20:1 dedupe, vault-initiated replication "
                "across an operational air gap, Retention Lock, CyberSense scan, "
                "detonation in production, vault-side recovery. Watch the gap."
            ),
        ),
        counters_note=L(
            novice=(
                "Protected (logical) is how much data the backups say they hold. "
                "Stored (physical) is the space they really take up on the "
                "appliance. The difference is deduplication: repeated data is kept "
                "only once. Watch the air gap row. It says OPEN only when the vault "
                "itself opens the link, and it says closed when the attack comes. "
                "Copies scanned / flagged counts the vault copies CyberSense has "
                "read and how many it found damaged: a copy that was scanned and "
                "not flagged is the one to restore from. All "
                "values are illustrative, chosen to show shape and rough size."
            ),
            standard=(
                "Logical is what the estate believes it has protected; physical is "
                "the flash actually consumed. The gap between them is Data "
                "Domain's deduplication. Watch the air gap row: it opens only when "
                "the vault itself opens it, and it is closed when the attack "
                "comes. Copies scanned / flagged is CyberSense's verdict on the "
                "vaulted copies, and recovery restores from one that was scanned "
                "and not flagged. Values are illustrative, meant to show shape "
                "and order of magnitude."
            ),
            expert=(
                "Logical vs physical is the dedupe ratio. Gap opens only "
                "vault-side. Scanned / flagged is the CyberSense verdict recovery "
                "selects on. Values illustrative."
            ),
        ),
    ),
    ScenarioInfo(
        id=SCENARIO_ID,
        title="Free space keeps shrinking",
        summary=L(
            novice=(
                "Old backups expire on schedule, yet the backup appliance keeps "
                "filling up. Expiring a backup only crosses it off the list. The "
                "disk space comes back later, when a weekly housekeeping job called "
                "cleaning runs, and even then some of it is held back by copies, "
                "snapshots and locks that still point at the old data."
            ),
            standard=(
                "Backups expire by retention, but Data Domain returns no space until "
                "the cleaning (garbage collection) cycle runs. Then cleaning "
                "reclaims less than the estimate, because a lagging replication "
                "context and a stale snapshot still reference the dead segments, "
                "and Retention Lock keeps copies the catalog has already expired."
            ),
            expert=(
                "Expiry is a namespace operation; space returns only in filesys "
                "clean, and only for segments no replication snapshot or user "
                "snapshot still references. Retention-locked files refuse the "
                "delete and never become cleanable."
            ),
        ),
        hero="Reclaimed by cleaning, against the cleanable estimate",
        is_failure=True,
        sources=SOURCES,
    ),
]


def _state(
    step: int,
    phase: str,
    hour: int,
    *,
    logical: int,
    stored: int,
    live: int,
    reclaimable: int,
    rep: int,
    snap: int,
    lock: int,
    reclaimed: int,
    **rest,
) -> CleaningState:
    # ``stored`` is authored per step rather than summed here, so the ledger
    # is a fact the tests check rather than a definition they cannot break.
    return CleaningState(
        step=step,
        phase=phase,
        logical_tb=logical,
        stored_tb=stored,
        elapsed_hours=hour,
        capacity_tb=CAPACITY_TB,
        live_tb=live,
        reclaimable_tb=reclaimable,
        held_by_replication_tb=rep,
        held_by_snapshot_tb=snap,
        held_by_lock_tb=lock,
        # Illustrative: the estimate counts the segments of every *deleted*
        # file, whether or not a snapshot still references them. Dell documents
        # the figure as an estimate. Locked files are excluded: their delete was
        # refused, so they are still in the namespace and nothing calls them
        # cleanable.
        cleanable_tb=reclaimable + rep + snap,
        reclaimed_tb=reclaimed,
        lock_days_left=LOCK_DAYS_AT_START - (hour - START_HOUR) // 24,
        **rest,
    )


def simulate_cleaning() -> list[CleaningState]:
    """Expiry, a filling appliance, a clean that under-delivers, and the fix."""
    return [
        _state(
            0, "steady", 1344,
            logical=1600, stored=80, live=78, reclaimable=2, rep=0, snap=0, lock=0, reclaimed=0,
            label="Eight weeks in, the production appliance is 80% full",
            description=L(
                novice=(
                    "The production Data Domain, the backup appliance on the left "
                    "of the map, has taken eight weeks of backups. The backup "
                    "software believes it is protecting 1,600 terabytes. Because "
                    "the appliance stores each repeated block of data only once "
                    "(deduplication), that fits in 80 terabytes of a 100 terabyte "
                    "box. The plan is to keep four weeks of backups and let older "
                    "ones expire, so everyone expects the used space to level off. "
                    "All sizes in this scenario are illustrative."
                ),
                standard=(
                    "Eight weeks of backups sit on the production Data Domain: "
                    "1,600 TB logical in 80 TB of a 100 TB active tier. Retention "
                    "is four weeks, so from here the oldest week expires as each "
                    "new one lands and used space should level off. Sizes are "
                    "illustrative."
                ),
                expert=(
                    "Production DD at 80/100 TB post-comp, 1,600 TB pre-comp, "
                    "four-week retention about to start expiring. Illustrative "
                    "sizes."
                ),
            ),
            active_regions=["backup-server", "dd-prod"],
        ),
        _state(
            1, "expire", 1345,
            logical=1300, stored=80, live=64, reclaimable=8, rep=4, snap=2, lock=2, reclaimed=0,
            label="Retention expires the oldest backups, and no space comes back",
            description=L(
                novice=(
                    "PowerProtect Data Manager, the backup software, deletes the "
                    "backups that are past their four weeks. The protected total "
                    "drops from 1,600 to 1,300 terabytes. The used space on the "
                    "appliance does not move at all. Deleting a backup only "
                    "removes its name from the appliance's file list. The blocks "
                    "on disk (segments) are shared between many backups, so the "
                    "appliance cannot simply erase them on the spot. It leaves "
                    "them for a housekeeping job called cleaning, also known as "
                    "garbage collection, which by default runs once a week. Until "
                    "then the appliance only shows a guess, labelled Cleanable, of "
                    "what that job might return."
                ),
                standard=(
                    "PowerProtect Data Manager expires the backups past retention "
                    "and logical falls to 1,300 TB. Stored does not move. A delete "
                    "removes the file from the namespace; the deduplicated "
                    "segments it referenced stay on disk until the cleaning "
                    "(garbage collection) cycle runs, by default weekly on Tuesday "
                    "at 06:00. The appliance reports 14 TB as Cleanable, which "
                    "Dell documents as an estimate."
                ),
                expert=(
                    "PPDM expires past-retention copies: pre-comp down 300 TB, "
                    "post-comp unchanged. Delete is a namespace operation; "
                    "segments wait for filesys clean (default Tue 0600). "
                    "Cleanable reads 14 TB, an estimate."
                ),
            ),
            active_regions=["backup-server", "dd-prod"],
        ),
        _state(
            2, "ingest", 1440,
            logical=1500, stored=88, live=72, reclaimable=8, rep=4, snap=2, lock=2, reclaimed=0,
            label="New backups keep landing, and free space keeps shrinking",
            description=L(
                novice=(
                    "Four more nights of backups arrive. Each one adds a little "
                    "new data, and none of the expired data has been given back "
                    "yet, so used space climbs from 80 to 88 terabytes. This is "
                    "the moment an administrator writes the post titled free "
                    "space is decreasing constantly on Dell's community forum "
                    "(one such thread, from 2015, is linked below and was never "
                    "answered). Nothing is broken here. The weekly cleaning job "
                    "has simply not run since the expiry."
                ),
                standard=(
                    "Four more nightly backups land. New unique segments add 8 TB "
                    "while the expired segments are still on disk, so stored "
                    "climbs to 88 TB. This is the shape of the community post "
                    "free space is decreasing constantly, linked below. Nothing "
                    "is faulty; no clean has run since the expiry."
                ),
                expert=(
                    "Four nightlies add 8 TB of unique segments on top of 16 TB "
                    "the catalog has already expired: 88 TB used. Expected "
                    "between cleans."
                ),
            ),
            active_regions=["workload-vm", "workload-db", "backup-server", "dd-prod"],
            cycle_cost=2,
        ),
        _state(
            3, "alert", 1500,
            logical=1450, stored=96, live=72, reclaimable=12, rep=6, snap=3, lock=3, reclaimed=0,
            label="96% full: the space alert fires",
            description=L(
                novice=(
                    "More backups land and another batch expires, which again "
                    "frees nothing. The appliance crosses 95% full and raises an "
                    "alert. What protects the data here is that a Data Domain "
                    "never deletes anything on its own, so every backup already "
                    "stored stays safe. The danger is to tomorrow's backups: at "
                    "100% new writes fail, backup and replication jobs fail, and "
                    "the file system can turn read-only, which even blocks the "
                    "deletes that would help. The appliance now says 21 terabytes "
                    "are Cleanable, so the administrator expects cleaning to "
                    "bring usage back to about 75."
                ),
                standard=(
                    "Further ingest and a second expiry take the appliance to "
                    "96 TB and it raises its space-usage alert. "
                    "Stored backups are not at risk, because Data Domain never "
                    "deletes on its own. New ones are: at 100% writes fail, "
                    "backup and replication jobs fail, and the file system can go "
                    "read-only, which blocks deletes too. Cleanable reads 21 TB, "
                    "so the administrator expects a clean to land near 75 TB."
                ),
                expert=(
                    "96% used, space-usage alert raised. At 100% ingest and "
                    "replication fail and DDFS may go read-only. Cleanable "
                    "estimate 21 TB; expectation after clean is 75 TB."
                ),
            ),
            active_regions=["workload-vm", "workload-db", "backup-server", "dd-prod", "mgmt"],
            failed_regions=["dd-prod"],
            alerts=[SPACE_ALERT],
        ),
        _state(
            4, "clean", 1512,
            logical=1450, stored=96, live=72, reclaimable=12, rep=6, snap=3, lock=3, reclaimed=0,
            label="The weekly clean starts by finding what is still referenced",
            description=L(
                novice=(
                    "Tuesday 06:00, the default schedule, and cleaning starts. Its "
                    "first job is to walk every file the appliance still knows "
                    "about and mark every block those files use. A block counts "
                    "as in use if anything at all points at it: a current backup, "
                    "a snapshot (a frozen view of the files at one moment), or a "
                    "copy waiting to be sent to another appliance. No space comes "
                    "back during this pass. Cleaning runs at half speed by "
                    "default so that backups can continue beside it."
                ),
                standard=(
                    "Tuesday 06:00, the default schedule. Cleaning first "
                    "enumerates every live reference, including files held only "
                    "by snapshots and by replication, and marks the segments they "
                    "use. No space returns during enumeration. The default 50% "
                    "throttle leaves room for backups to run alongside."
                ),
                expert=(
                    "Scheduled filesys clean begins. Enumeration walks the "
                    "namespace plus snapshot and replication references and "
                    "builds the live-segment set at 50% throttle. Post-comp "
                    "unchanged."
                ),
            ),
            active_regions=["dd-prod", "mgmt"],
            failed_regions=["dd-prod"],
            alerts=[SPACE_ALERT],
            clean_running=True,
            cycle_cost=3,
        ),
        _state(
            5, "clean", 1524,
            logical=1450, stored=84, live=72, reclaimable=0, rep=6, snap=3, lock=3, reclaimed=12,
            label="Cleaning copies live data forward and frees 12 TB, not 21",
            description=L(
                novice=(
                    "Now cleaning does the slow part. The appliance stores blocks "
                    "packed together in large containers. For each container "
                    "that holds dead blocks, cleaning copies the blocks still in "
                    "use into a fresh container and then frees the old one. This "
                    "is the only moment in the whole story when used space falls: "
                    "96 terabytes becomes 84. The alert clears. But the appliance "
                    "had estimated 21 terabytes and delivered 12. Nothing was "
                    "lost and nothing went wrong inside cleaning. The rest of "
                    "the deleted data turned out to be still in use by something."
                ),
                standard=(
                    "The copy phase: containers holding dead segments have their "
                    "live segments copied forward, then the containers are freed. "
                    "This is the only point in the trace where stored falls, from "
                    "96 TB to 84 TB, and the alert clears. The estimate said 21 TB "
                    "and cleaning returned 12. No live data was touched; the "
                    "other 9 TB belongs to deleted files that something on the "
                    "appliance still references."
                ),
                expert=(
                    "Copy-forward frees containers: post-comp 96 to 84 TB, alert "
                    "clears. 12 of the estimated 21 TB returned; the remainder "
                    "is still referenced."
                ),
            ),
            active_regions=["dd-prod", "mgmt"],
            clean_running=True,
            cycle_cost=6,
        ),
        _state(
            6, "pinned", 1525,
            logical=1450, stored=84, live=72, reclaimable=0, rep=6, snap=3, lock=3, reclaimed=12,
            label="Two references hold the missing 9 TB, and a lock holds 3 more",
            description=L(
                novice=(
                    "The administrator goes looking for the missing 9 terabytes "
                    "and finds two holders. First, the copy to the vault is "
                    "behind. Replication keeps a snapshot of what it last sent, "
                    "and the air gap has been closed since, so that snapshot "
                    "still points at 6 terabytes of deleted backups. Second, "
                    "somebody took a snapshot before an upgrade and never removed "
                    "it: 3 terabytes. Dell's support articles list both causes "
                    "when cleaning returns less than expected. The search also "
                    "turns up a third surprise that was never in the estimate. "
                    "The month-end backups are under Retention Lock, a setting "
                    "that refuses every delete until a set date. The retention "
                    "period in the backup software was shortened after those "
                    "copies were locked, so the software's delete simply failed: "
                    "3 terabytes that the backup software lists as expired and "
                    "the appliance still keeps, with 14 days of lock left."
                ),
                standard=(
                    "Two references account for the shortfall. The MTree "
                    "replication context to the vault has not synced since the "
                    "gap last closed, and its snapshot still references 6 TB of "
                    "deleted files. A forgotten pre-upgrade snapshot holds 3 TB. "
                    "Both are causes Dell's KB lists for cleaning not recovering "
                    "space, and both sat inside the Cleanable estimate. A "
                    "further 3 TB was never in it: month-end copies under "
                    "Retention Lock with 14 days to run. Policy retention was "
                    "shortened after they were locked, so the backup "
                    "application's delete was refused and the files are still "
                    "in the namespace. The catalog calls them expired; the "
                    "appliance does not."
                ),
                expert=(
                    "Shortfall breakdown: 6 TB behind the lagging MTree "
                    "replication snapshot, 3 TB behind a stale user snapshot, "
                    "both inside the Cleanable estimate. Outside it: 3 TB "
                    "retention-locked for 14 more days, delete refused, files "
                    "still in the namespace."
                ),
            ),
            active_regions=["backup-server", "dd-prod", "mgmt"],
            cycle_cost=2,
        ),
        _state(
            7, "release", 1548,
            logical=1500, stored=86, live=74, reclaimable=9, rep=0, snap=0, lock=3, reclaimed=12,
            label="Replication catches up and the stale snapshot is expired; the lock stays",
            description=L(
                novice=(
                    "Two of the three holders can be released. The vault opens "
                    "the air gap on its own schedule and replication catches up, "
                    "so its snapshot moves forward and lets go of 6 terabytes. "
                    "The administrator expires the forgotten snapshot: 3 more. "
                    "The locked 3 terabytes stay exactly where they are, because "
                    "refusing deletes, including an administrator's, is what "
                    "Retention Lock is for. In governance mode a lock can be "
                    "reverted by a privileged user; in compliance mode it cannot "
                    "be reverted by anyone. Used space still has not fallen. "
                    "Releasing a holder only turns held blocks into blocks the "
                    "next clean is able to free."
                ),
                standard=(
                    "The vault opens the gap on its schedule and the replication "
                    "context syncs, advancing its snapshot and releasing 6 TB. "
                    "The administrator expires the stale snapshot, releasing 3 TB. "
                    "The 3 TB under Retention Lock stays: governance mode allows "
                    "a privileged revert, compliance mode allows none, and this "
                    "estate leaves it alone. Stored has not fallen. Releasing a "
                    "reference only moves segments from held to reclaimable."
                ),
                expert=(
                    "Context syncs through the open gap (6 TB released), "
                    "snapshot expire frees another 3 TB of references. Locked "
                    "3 TB untouched. Post-comp unchanged until the next clean."
                ),
            ),
            active_regions=["dd-prod", "gap", "dd-vault", "mgmt"],
        ),
        _state(
            8, "reclean", 1572,
            logical=1500, stored=77, live=74, reclaimable=0, rep=0, snap=0, lock=3, reclaimed=21,
            label="A second clean returns the 9 TB that was released",
            description=L(
                novice=(
                    "The administrator starts cleaning by hand instead of waiting "
                    "a week. It frees the 9 terabytes that were released and "
                    "used space falls to 77. Dell's guidance is that this should "
                    "be the exception: cleaning is heavy work, and Dell advises "
                    "against running it every day because that scatters "
                    "(fragments) the stored data and slows later restores. "
                    "Across the two cleans the appliance has now returned 21 "
                    "terabytes, the figure it first estimated. The locked 3 "
                    "terabytes were never part of that figure and stay put."
                ),
                standard=(
                    "A manual filesys clean start returns the released 9 TB and "
                    "stored falls to 77 TB. Dell's KB notes that clean may need "
                    "more than one run to return everything, and here the two "
                    "runs together return the 21 TB first estimated. Its "
                    "scheduling KB keeps weekly as the norm and advises against "
                    "daily cleaning, which fragments the data. The locked 3 TB "
                    "was never cleanable and stays."
                ),
                expert=(
                    "Manual clean: 9 TB freed, 77 TB used, 21 TB reclaimed in "
                    "total, matching the first estimate. Locked files are "
                    "still in the namespace."
                ),
            ),
            active_regions=["dd-prod", "mgmt"],
            clean_running=True,
            cycle_cost=4,
        ),
        _state(
            9, "settled", 1680,
            logical=1600, stored=79, live=76, reclaimable=0, rep=0, snap=0, lock=3, reclaimed=21,
            label="Steady again, with the locked copies waiting out their date",
            description=L(
                novice=(
                    "Usage levels off near 79 terabytes and moves in a weekly "
                    "sawtooth: it climbs between cleans and drops on Tuesday. The "
                    "locked 3 terabytes are still there with 7 days to go. Even "
                    "when the lock ends the appliance will not remove them by "
                    "itself. The backup software has to delete them, and then a "
                    "clean has to run. The lesson for sizing a Data Domain is to "
                    "leave room for a week of expired data, for the longest "
                    "replication delay, and for everything under lock."
                ),
                standard=(
                    "Stored settles near 79 TB in a weekly sawtooth, rising "
                    "between cleans and falling on Tuesday. The locked 3 TB "
                    "remains with 7 days to run, and Data Domain will not delete "
                    "it when the lock ends; the backup application must delete "
                    "it and a clean must follow. Capacity planning has to allow "
                    "for a week of uncollected expiry, the worst replication "
                    "lag, and everything under lock."
                ),
                expert=(
                    "79 TB with a weekly sawtooth. 3 TB locked, 7 days left; "
                    "post-lock removal still needs an application delete plus a "
                    "clean. Size for expiry backlog, replication lag and locked "
                    "capacity."
                ),
            ),
            active_regions=["workload-vm", "workload-db", "backup-server", "dd-prod"],
        ),
    ]
