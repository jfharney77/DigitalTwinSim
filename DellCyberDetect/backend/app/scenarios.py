"""Failure scenarios for the Dell Cyber Detect twin.

``engine.simulate()`` is the incident that ends well: the analysis names a
clean copy on the array and recovery uses it. This module carries the
incident that does not, as a second pure trace over the same
``DetectState`` model. Same purity rule as the engine: no FastAPI, no IO,
no timers, nothing random.

**dwell-exceeds-retention.** The catalog already says it in one line: if
the attacker's dwell time exceeds snapshot retention, there is no clean
copy left to find. Here that line is played out. The array keeps seven
daily snapshots (an illustrative 168-hour window). The attacker corrupts
slowly for longer than that, so by the time anyone runs content
inspection the last clean snapshot has already been deleted by the
retention policy, on schedule, working as designed.

What the product does next is the point. It reads every byte as before, it
scores every copy as before, and then it reports that none of the seven is
clean. ``last_clean_snapshot`` stays at -1 for the whole trace. There is an
administrator who badly wants a snapshot number, and the analysis does not
supply one, because certifying a corrupted copy is the one error this
product exists to prevent. Recovery then comes from somewhere else: the
isolated PowerProtect Cyber Recovery vault (this repo's DellPowerProtect
twin). The vault holds backup copies, not array snapshots: backups of the
volume land on a production Data Domain and are replicated into the vault,
where they are retention-locked and scanned by the same content analytics.
So the vault helps only if the volume was being backed up and the vault
keeps copies for longer than the attacker waited; this scenario assumes
both, and the prose says so. The price is the recovery point: the restored
data is older.

What is sourced and what is not. Dell's Cyber Recovery guide documents the
per-copy results an administrator sees (Good, Suspicious, Partial) and the
alert a Suspicious result raises; Index Engines documents that the
analytics identify the last known clean copy and produce forensic reports
and impacted-file lists. Neither publishes a worked "every copy is
suspicious" walkthrough, so the sequence here is this twin's reading of
those documented behaviours. A Dell Community search turned up only a
CyberSense course notice with no technical content, so no community thread
is cited. Retention windows, hours, and counts are illustrative.
"""

from __future__ import annotations

from .anatomy import TOTAL_SNAPSHOTS
from .engine import (
    BASELINE_RECOVERY_POINT_AGE_HOURS,
    SNAPSHOT_INTERVAL_HOURS,
    simulate,
)
from .leveling import L
from .models import DetectState, ScenarioInfo, SourceLink

BASELINE = "baseline"
DWELL_EXCEEDS_RETENTION = "dwell-exceeds-retention"

# Retention in hours is just slots x interval, and the two incidents run on
# arrays with different cadences. The failure array snapshots daily and keeps
# seven: 168 hours. The baseline array snapshots every 30 hours and keeps the
# same seven slots: 210 hours, which is why nothing expires during its
# shorter trace. Both figures are illustrative.
SNAPSHOT_INTERVAL_HOURS_FAILURE = 24
RETENTION_HOURS = SNAPSHOT_INTERVAL_HOURS_FAILURE * TOTAL_SNAPSHOTS
BASELINE_RETENTION_HOURS = SNAPSHOT_INTERVAL_HOURS * TOTAL_SNAPSHOTS

# The vault's newest clean copy was synced at t+72h, a day before corruption
# began. Illustrative.
_VAULT_CLEAN_COPY_TAKEN_AT_HOURS = 72

VAULT_SOURCE = "powerprotect-vault"

_SNAPSHOTS = [f"snap-{i}" for i in range(1, TOTAL_SNAPSHOTS + 1)]

_SOURCES = [
    SourceLink(
        label="Dell PowerProtect Cyber Recovery product guide: analyzing a "
        "copy (Good / Suspicious / Partial results, the alert on Suspicious)",
        url="https://www.dell.com/support/manuals/en-us/cyber-recovery/"
        "irs_p_19.13_userguide/analyzing-a-copy"
        "?guid=guid-7eefd80a-ef14-4417-8554-63399a30adc3&lang=en-us",
    ),
    SourceLink(
        label="Index Engines CyberSense FAQ: last known clean copy, forensic "
        "reports, impacted-file lists, slow-acting variants",
        url="https://indexengines.com/cybersense-frequently-asked-questions/",
    ),
    SourceLink(
        label="Index Engines: Dell Cyber Detect (content analytics on "
        "primary-storage snapshots)",
        url="https://indexengines.com/products/dell-cyber-detect/",
    ),
    SourceLink(
        label="Dell PowerProtect Cyber Recovery reference architecture "
        "(H18661): backup copies replicated to the air-gapped vault, "
        "retention lock, CyberSense and recovery hosts in the vault",
        url="https://www.delltechnologies.com/asset/en-us/products/"
        "data-protection/industry-market/"
        "h18661-dell-powerprotect-cyber-recovery-reference-architecture-wp.pdf",
    ),
    SourceLink(
        label="Mandiant M-Trends 2025: median dwell time (most ransomware "
        "is fast; the slow campaign modelled here is the tail, not the norm)",
        url="https://cloud.google.com/blog/topics/threat-intelligence/"
        "m-trends-2025/",
    ),
]

# Page copy for the incident page, per scenario and per reading level. The
# labels explained here are the ones anatomy.py draws: each snapshot box is
# numbered oldest first, and "T-n" means n snapshots before the newest.
_LABEL_KEY_NOVICE = (
    "Each box on the row is one saved copy. The first number counts from the "
    "oldest copy, and T-4 means four copies before the newest one, which is "
    "T-0. It counts copies, not days."
)
_LABEL_KEY = (
    "Boxes are numbered oldest first; T-n means n snapshots before the "
    "newest (T-0), a position on the row and not a number of days."
)
_LABEL_KEY_EXPERT = "Boxes: index oldest-first, T-n = n snapshots before newest."

_BASELINE_INTRO = L(
    novice=(
        "Most ransomware defences do not look at your data. They look at "
        "descriptions of the data, called metadata: what files are named, "
        "how many were renamed at once, how much is changing per hour. Some "
        "also watch for files suddenly turning into random-looking noise "
        "(measured as entropy), which is what scrambled files look like. "
        "These signs are cheap to watch, so attackers learned to avoid "
        "them: scramble slowly, keep the file names, look like an ordinary "
        "busy day, and every one of those alarms stays quiet. What is far "
        "harder to hide is whether a file still makes sense when you open "
        "it. Play the trace and watch four saved copies get ruined while the "
        "alarm count never leaves zero. Then watch what the analysis hands "
        "back: not an alarm, but a *date*, the time of the last good copy."
    ),
    standard=(
        "Almost every ransomware defence watches descriptions of data (its "
        "metadata) rather than data: did extensions change, did entropy "
        "(how random the bytes look) spike, was there a mass rename, is the "
        "I/O rate unusual. Those are cheap to measure, which is exactly why "
        "attackers stopped triggering them — encrypt slowly, preserve "
        "extensions, imitate a busy Tuesday, and every one of those "
        "detectors stays quiet. What is far harder to disguise is whether a "
        "file still means anything. Play the trace and watch four snapshots "
        "get ruined while the alert counter never leaves zero. Then watch "
        "what the analysis produces: not an alert, but a *date*."
    ),
    expert=(
        "Metadata and threshold detectors (extension delta, entropy spike, "
        "mass rename, I/O anomaly) are evadable by shaping the attack. "
        "Whether content still parses is far harder to fake. Four snapshots "
        "corrupt at zero alerts; the output is a recovery point, a *date*."
    ),
)

_BASELINE_MAP_NOTE = L(
    novice=(
        "Pause on the *detectors silent* step and look at the row of copies. "
        "Every box is drawn the same, because at that moment they really "
        "cannot be told apart: four of them are ruined and nothing you can "
        "see from outside says which. That is where the administrator "
        "actually stands. The boxes only turn red once the analysis has "
        "read what is inside them, and only then can a marker go on the "
        f"last good one. {_LABEL_KEY_NOVICE} Click any block to read what it "
        "is. For a narrated walk through the same story, open the Guided "
        "tour tab."
    ),
    standard=(
        "Pause on the *detectors silent* step and look at the timeline. "
        "Every snapshot is drawn identically, because at that moment they "
        "genuinely are indistinguishable — four of them are ruined and "
        "nothing visible from outside says which. That is the position an "
        "administrator is actually in. The copies only turn red once the "
        "analysis has read the bytes inside them, and only then can a "
        f"marker be placed on the last clean one. {_LABEL_KEY} Click a block "
        "to pin what it is; the narrated walk-through is under Guided tour."
    ),
    expert=(
        "At *detectors silent* the row is uniform by design: 4/7 corrupt, "
        "nothing external distinguishes them. Red appears only after the "
        f"content read. {_LABEL_KEY_EXPERT} Click a block to pin it; "
        "narration under Guided tour."
    ),
)

_BASELINE_COUNTERS_NOTE = L(
    novice=(
        "Read the corrupted row against the alerts row. Copies are being "
        "ruined and the alarms have raised nothing. They are not broken. "
        "The attack was shaped to keep them quiet: file names kept, the "
        "scrambling spread out so the random-looking-noise measure "
        "(entropy) never jumped, and the amount of activity kept normal. "
        "Everything watching a *description* of the data is satisfied while "
        "the data is destroyed. The last clean copy row is the answer, and "
        "notice how long it stays unknown. The restored data age row fills "
        "in at recovery: it is how old the data you get back is, which is "
        "the work you lose. Values are examples, meant to show shape and "
        "rough size."
    ),
    standard=(
        "Read the corrupted row against the alert row. Snapshots are ruined "
        "and the metadata detectors have raised nothing — not because they "
        "are broken, but because the attack was shaped to keep them quiet: "
        "extensions preserved, entropy (how random the bytes look) raised "
        "gradually, I/O inside the normal range. Everything watching a "
        "*description* of the data is satisfied while the data is "
        "destroyed. The last clean copy row is the deliverable, and note "
        "how long it stays unknown. The restored data age row fills in at "
        "recovery: 134h here, the writes lost even with the right copy. "
        "Values are illustrative, meant to show shape and order of "
        "magnitude."
    ),
    expert=(
        "Corrupted vs alerts: the detectors are evaded, not broken "
        "(extensions kept, sub-threshold entropy, in-profile I/O). Last "
        "clean copy is the deliverable; restored data age (134h at "
        "recovery) is the achieved RPO. Illustrative values."
    ),
)

_DWELL_INTRO = L(
    novice=(
        "Same product, same attacker, one change: the attacker is patient. "
        "The storage system saves a copy a day and keeps seven, deleting "
        "the oldest each time. Content checking here is only run when "
        "somebody asks for it. So the attacker scrambles slowly for longer "
        "than a week, and the good copies are deleted on schedule before "
        "anyone looks. Play the trace and watch the clean-copies count fall "
        "to zero while the alarm count stays at zero too. Then watch what "
        "the analysis says when all seven copies are bad. It does not pick "
        "the least bad one. It says there is no clean copy here, and "
        "recovery has to come from somewhere else."
    ),
    standard=(
        "The same analysis, against a patient attacker. This array takes "
        "one snapshot a day and keeps seven, and content inspection runs "
        "only on demand, so nothing reads the copies until somebody "
        "complains. The attacker corrupts slowly for longer than the "
        "168-hour retention window, and the last clean snapshot expires on "
        "schedule. Play the trace and watch clean copies fall to zero "
        "while the alert counter never moves. Then watch the verdict: all "
        "seven retained snapshots are corrupted, and the analysis names "
        "none of them. Recovery comes from the PowerProtect vault, with an "
        "older recovery point. Hours and windows are illustrative."
    ),
    expert=(
        "Daily snapshots, seven retained (168 h), content scans on demand "
        "only. Corruption age exceeds retention before anyone inspects; "
        "7/7 retained copies corrupt; verdict names none; recovery is "
        "off-array from the vault at an older recovery point. Illustrative."
    ),
)

_DWELL_MAP_NOTE = L(
    novice=(
        "Pause on the step where the last clean snapshot expires and look "
        "at the row of copies. It looks exactly as it did on the first "
        "day, and by then all seven copies are ruined. After the analysis "
        "has read them the whole row turns red, and no marker is placed, "
        "because no copy has earned it. The report and recovery blocks "
        f"below say so in words. {_LABEL_KEY_NOVICE} Click any block to read "
        "what it is. The Guided tour tab narrates the other incident, the "
        "one where a clean copy is found."
    ),
    standard=(
        "Pause on the step where the last clean snapshot expires. The "
        "timeline is drawn exactly as it was at the start, and by then "
        "seven of seven retained copies are corrupted. Once the analysis "
        "has read them the whole row turns red and no marker is placed, "
        "because no copy has earned one; the report and recovery blocks "
        f"carry the status instead. {_LABEL_KEY} Click a block to pin what "
        "it is. The Guided tour narrates the baseline incident, where a "
        "clean copy is found."
    ),
    expert=(
        "At expiry of the last clean copy the row is visually unchanged "
        "with 7/7 corrupt. After the read: all red, no marker, status on "
        f"the report and recovery blocks. {_LABEL_KEY_EXPERT} Guided tour "
        "covers the baseline."
    ),
)

_DWELL_COUNTERS_NOTE = L(
    novice=(
        "Watch the clean-copies row fall to zero while the row counting "
        "copies no longer on the array climbs. The clean-up rule deletes "
        "the good copies on schedule, and "
        "the attacker only has to wait. Then watch the last clean copy "
        "row. It never names a copy, because none of the seven deserves "
        "it. The alerts row stays at zero all the way through: the alarms "
        "that watch file names and activity were avoided on purpose. The "
        "restored data age row is empty until recovery. When it fills in "
        "it reads 310h, against 134h in the incident where a clean copy "
        "was still on the storage system. Values are examples."
    ),
    standard=(
        "Watch the clean-copies row fall to zero while the row of copies no "
        "longer on the array climbs: the retention policy deletes the good "
        "copies on schedule, "
        "and the attacker only has to wait. Then watch the last clean copy "
        "row. It never names a snapshot, because none of the seven "
        "deserves it. Metadata alerts stay at zero throughout, as in the "
        "baseline. The restored data age row stays empty until the "
        "recovery step, where it reads 310h against 134h when a clean copy "
        "was still on the array. Values are illustrative."
    ),
    expert=(
        "Clean copies fall to 0 as copies leave the array; last clean copy never "
        "set; alerts 0 throughout. Restored data age is blank until "
        "recovery, then 310h vs 134h baseline. Illustrative."
    ),
)

SCENARIOS = [
    ScenarioInfo(
        id=BASELINE,
        name="A clean copy is found",
        summary=(
            "Four of seven snapshots are corrupted. Content analysis names "
            "snapshot 3 as the last clean copy and recovery uses it."
        ),
        hero_label="last clean copy",
        hero_value="snapshot 3",
        retention_hours=BASELINE_RETENTION_HOURS,
        heading="It reads the data, not the metadata",
        intro=_BASELINE_INTRO,
        map_note=_BASELINE_MAP_NOTE,
        counters_note=_BASELINE_COUNTERS_NOTE,
    ),
    ScenarioInfo(
        id=DWELL_EXCEEDS_RETENTION,
        name="Dwell time exceeds retention",
        summary=(
            "The attacker corrupts slowly for longer than the array keeps "
            "snapshots. Every retained copy is ruined, the analysis says so "
            "instead of naming one, and recovery comes from the PowerProtect "
            "vault with an older recovery point."
        ),
        hero_label="clean copies on the array",
        hero_value="0",
        retention_hours=RETENTION_HOURS,
        sources=_SOURCES,
        heading="The attacker outwaits the snapshots",
        intro=_DWELL_INTRO,
        map_note=_DWELL_MAP_NOTE,
        counters_note=_DWELL_COUNTERS_NOTE,
    ),
]

SCENARIO_IDS = [s.id for s in SCENARIOS]


def simulate_dwell_exceeds_retention() -> list[DetectState]:
    """The incident where retention runs out before anyone looks."""
    return [
        DetectState(
            step=0,
            phase="clean",
            label="Normal operations, and a seven-day retention window",
            description=L(
                novice=(
                    "The storage system saves a copy of the data once a day. "
                    "These copies are called snapshots. It keeps seven of "
                    "them, and every time it saves a new one it deletes the "
                    "oldest, so the row you see is always the last week and "
                    "nothing older. That rule is called the retention policy. "
                    "It exists because copies take space, and a week feels "
                    "like plenty. Nothing reads what is inside the copies "
                    "unless somebody asks for a content check; it is not on "
                    "a timetable. Today all seven copies are good. The "
                    "seven-day figure is an example chosen for this twin, "
                    "not a Dell default."
                ),
                standard=(
                    "The array takes one snapshot a day and keeps seven, so "
                    "the timeline is a rolling week: each new copy pushes the "
                    "oldest one out. That is the retention policy, and it is "
                    "a capacity decision somebody made on a quiet afternoon. "
                    "Content inspection is not scheduled on this array; it "
                    "runs when an administrator asks for it. "
                    "All seven copies are restorable today. The window is "
                    "illustrative; the question it sets up is how long an "
                    "attacker has to stay quiet before it stops helping."
                ),
                expert=(
                    "Daily snapshots, seven retained, rolling. Content scans "
                    "on demand only, no schedule. All seven restorable. Retention is 168 h (illustrative): the "
                    "number the attacker has to outlast."
                ),
            ),
            active_regions=["array", *_SNAPSHOTS],
            snapshots_taken=7,
            snapshots_expired=0,
            snapshots_corrupted=0,
            content_confidence_percent=0,
            elapsed_hours=0,
        ),
        DetectState(
            step=1,
            phase="intrusion",
            label="An intruder is inside, and in no hurry",
            description=L(
                novice=(
                    "Someone has broken in using a stolen password. They "
                    "change nothing yet. They look around, and one thing "
                    "they look for is how many days of copies the storage "
                    "system keeps. The time an attacker spends inside before "
                    "being noticed is called dwell time. Most ransomware "
                    "attacks are over in days. This attacker plans to take "
                    "weeks, because they have worked out that a slow attack "
                    "lets the good copies delete themselves."
                ),
                standard=(
                    "Valid credentials, no changes, reconnaissance. Part of "
                    "what gets mapped is the snapshot schedule. Dwell time "
                    "(how long an intruder is present before detection) is "
                    "short for most ransomware: Mandiant's 2025 median is "
                    "five days when the attacker announces themselves. This "
                    "scenario is the patient tail of that distribution, an "
                    "attacker who reads a seven-day retention policy as a "
                    "schedule to beat. Three more snapshots are taken and "
                    "three old ones expire. All seven retained are still "
                    "clean."
                ),
                expert=(
                    "Credentialed access, recon includes the snapshot "
                    "policy. Window rolls by three; all retained copies "
                    "clean. The plan is to outlast 168 h."
                ),
            ),
            active_regions=["array", *_SNAPSHOTS],
            snapshots_taken=10,
            snapshots_expired=3,
            snapshots_corrupted=0,
            content_confidence_percent=0,
            elapsed_hours=72,
            cycle_cost=2,
        ),
        DetectState(
            step=2,
            phase="encrypt",
            label="Slow corruption begins, and the clean copies start to expire",
            description=L(
                novice=(
                    "The attacker starts scrambling files, a few at a time, "
                    "keeping the file names the same so nothing looks odd. "
                    "Each day a new snapshot is saved with the damage "
                    "inside it, and each day the oldest snapshot, a good "
                    "one, is deleted to make room. Nobody did anything "
                    "wrong there. The retention policy is doing exactly "
                    "what it was told. Four of the seven copies are now "
                    "ruined, three good ones remain, and the good ones are "
                    "at the old end of the row, next in line to go."
                ),
                standard=(
                    "Encryption starts at a rate chosen to stay inside the "
                    "normal I/O profile, extensions preserved. Every daily "
                    "snapshot now captures more damage, and every daily "
                    "expiry removes a clean copy from the old end of the "
                    "timeline. The retention policy is working as designed; "
                    "it has no idea which copies matter. Four of the seven "
                    "retained snapshots are corrupted and the three clean "
                    "ones are the next three to be deleted. Metadata alerts: "
                    "zero."
                ),
                expert=(
                    "Low-rate encryption inside normal I/O bounds. Four of "
                    "seven retained copies corrupt; the three clean ones are "
                    "oldest and expire next. Retention is now working for "
                    "the attacker. Alerts: zero."
                ),
            ),
            active_regions=["array", *_SNAPSHOTS],
            snapshots_taken=15,
            snapshots_expired=8,
            snapshots_corrupted=4,
            content_confidence_percent=0,
            elapsed_hours=192,
            cycle_cost=2,
        ),
        DetectState(
            step=3,
            phase="blind",
            label="The last clean snapshot expires, and nothing notices",
            description=L(
                novice=(
                    "More than a week has passed since the scrambling "
                    "began. The last good copy has been deleted by the "
                    "daily clean-up, on time, with no warning, because the "
                    "clean-up cannot tell a good copy from a bad one. All "
                    "seven copies on the storage system are now ruined. The "
                    "alarms that watch file names and activity levels are "
                    "still silent. Look at the row: it looks exactly like "
                    "it did on the first day."
                ),
                standard=(
                    "Corruption has now been running for longer than the "
                    "array keeps snapshots. The last clean copy aged out on "
                    "schedule, and its deletion raised nothing, because "
                    "expiry is routine and nothing had told the array that "
                    "copy was special. All seven retained snapshots contain "
                    "corrupted data. Metadata and behaviour detection are "
                    "still at zero. The timeline is drawn exactly as it was "
                    "at step one, because from outside it is identical."
                ),
                expert=(
                    "Corruption age exceeds retention. Last clean copy "
                    "expired on schedule, silently. Seven of seven retained "
                    "copies corrupt; metadata alerts zero; timeline visually "
                    "unchanged."
                ),
            ),
            active_regions=["array", *_SNAPSHOTS],
            snapshots_taken=22,
            snapshots_expired=15,
            snapshots_corrupted=7,
            content_confidence_percent=0,
            elapsed_hours=360,
            cycle_cost=3,
        ),
        DetectState(
            step=4,
            phase="inspect",
            label="Content inspection reads all seven, as it would any seven",
            description=L(
                novice=(
                    "Somebody finally notices files that will not open and "
                    "starts the content check by hand. It was never on a "
                    "timetable, so this is the first look inside any copy. "
                    "It does the same slow job it "
                    "always does: open every copy and read what is actually "
                    "inside the files, byte by byte. It does not know yet "
                    "that the answer will be bad, and it takes no "
                    "shortcuts because of who is waiting. Until the reading "
                    "is finished, it claims nothing."
                ),
                standard=(
                    "A user reports unreadable files and the administrator "
                    "runs content inspection against the retained "
                    "snapshots. Nothing had scheduled it, so this is the "
                    "first time anything has read inside a copy since the "
                    "trace began. The work is the same as in the incident "
                    "that ends well: open files and databases inside each "
                    "copy and read the bytes. It is the longest stage for "
                    "the same reason. Confidence is still zero, because "
                    "nothing has been scored. Reading is not yet a "
                    "conclusion."
                ),
                expert=(
                    "Admin-initiated after a user reports unreadable files; "
                    "no scan was scheduled, so this is the first content "
                    "read in 366 h. Full read of all seven retained "
                    "snapshots. Same cost as the baseline; confidence still zero "
                    "until scoring."
                ),
            ),
            active_regions=["array", *_SNAPSHOTS, "inspect"],
            snapshots_taken=22,
            snapshots_expired=15,
            snapshots_corrupted=7,
            content_confidence_percent=0,
            elapsed_hours=366,
            cycle_cost=6,
        ),
        DetectState(
            step=5,
            phase="classify",
            label="The model scores every snapshot, and every score is bad",
            description=L(
                novice=(
                    "The trained model gives each copy a score. Every one "
                    "of the seven comes back as corrupted. The row turns "
                    "red from end to end. The model is just as sure as it "
                    "was in the other incident; what changed is the news. "
                    "In Dell's vault product the same kind of result is "
                    "shown per copy as Good, Suspicious or Partial, with "
                    "an alert for each Suspicious one. Here all seven "
                    "would say Suspicious."
                ),
                standard=(
                    "The classifier scores what inspection read, and all "
                    "seven retained snapshots are classified corrupted. "
                    "Confidence is as high as it is in the baseline "
                    "incident, because it comes from the same place: the "
                    "content. In the Cyber Recovery vault the equivalent "
                    "result is shown per copy as Good, Suspicious, or "
                    "Partial, and a Suspicious result fails the analysis "
                    "job and raises an alert. Here that is seven Suspicious "
                    "results and no Good one. The 99.99% accuracy figure is "
                    "the vendor's claim, not a measurement made here."
                ),
                expert=(
                    "Seven of seven classified corrupt at baseline "
                    "confidence. In Cyber Recovery terms: seven Suspicious, "
                    "zero Good, an alert per copy."
                ),
            ),
            active_regions=["array", *_SNAPSHOTS, "inspect", "classifier", "models"],
            snapshots_taken=22,
            snapshots_expired=15,
            snapshots_corrupted=7,
            content_confidence_percent=99,
            elapsed_hours=369,
            cycle_cost=3,
        ),
        DetectState(
            step=6,
            phase="verdict",
            label="No clean copy on this array",
            description=L(
                novice=(
                    "This is the honest part. Everyone in the room wants "
                    "to hear a snapshot number, and the least-damaged copy "
                    "is sitting right there. The report does not name it. "
                    "It says: there is no clean copy on this storage "
                    "system. It also lists which files were damaged and "
                    "roughly when the damage started, which is what tells "
                    "people how far back they must go. A tool that named "
                    "the best of seven bad copies would be handing the "
                    "attack back to you with a certificate on it."
                ),
                standard=(
                    "The forensic report's answer is that there is no clean "
                    "copy on this array. No snapshot is named, and the "
                    "last-clean-copy field stays unset. That is the "
                    "invariant this scenario tests: under pressure to "
                    "produce something restorable, the product still does "
                    "not certify a corrupted copy, because a false negative "
                    "is somebody restoring the attack from a copy the "
                    "product vouched for. The report is still useful. The "
                    "impacted-file list and the attack timeline put the "
                    "start of corruption before the oldest retained "
                    "snapshot, which says where to look next: a copy kept "
                    "longer, somewhere else. The array's own restore path "
                    "has nothing to restore from."
                ),
                expert=(
                    "Verdict: no clean copy on array; last clean snapshot "
                    "unset. No least-bad fallback, because that is a false "
                    "negative. Forensic timeline dates corruption earlier "
                    "than the oldest retained copy, which points recovery "
                    "off-array."
                ),
            ),
            active_regions=[*_SNAPSHOTS, "classifier", "verdict"],
            snapshots_taken=22,
            snapshots_expired=15,
            snapshots_corrupted=7,
            content_confidence_percent=99,
            verdict="no-clean-copy-on-array",
            failed_regions=["recovery"],
            elapsed_hours=370,
        ),
        DetectState(
            step=7,
            phase="recover",
            label="Recover from the PowerProtect vault, with an older recovery point",
            description=L(
                novice=(
                    "There is a second set of copies in a separate, locked "
                    "place called the PowerProtect Cyber Recovery vault. "
                    "These are backups, made by backup software and copied "
                    "into the vault, so this only works because this data "
                    "was being backed up as well as snapshotted. The vault "
                    "is cut off from the network except for short planned "
                    "moments, and in this example it keeps copies for "
                    "longer than the storage system does. If it kept only "
                    "a week too, it would be just as empty. The same kind "
                    "of content check runs inside the vault, and it finds "
                    "a good copy from before the scrambling began. The "
                    "data is restored from that copy through a recovery "
                    "server inside the vault. The cost is age: the restored data is "
                    "about thirteen days old, where the other incident got "
                    "back data under six days old. Work done since then "
                    "has to be redone. These hours are examples, not "
                    "measurements."
                ),
                standard=(
                    "Recovery moves off the array to the PowerProtect Cyber "
                    "Recovery vault (the DellPowerProtect twin in this "
                    "repo). The vault holds backup copies, not array "
                    "snapshots: backups of this volume land on a production "
                    "Data Domain and are replicated across an operational "
                    "air gap, retention-locked, and scanned by CyberSense. "
                    "This scenario assumes the volume was in the backup set "
                    "and that the vault keeps copies for longer than the "
                    "array does. CyberSense names a vault copy from before "
                    "corruption began; the backup application is brought up "
                    "on a recovery host inside the vault and the data is "
                    "restored to the production volume from there. None of "
                    "the seven array snapshots is used. The price is the "
                    "recovery point objective (RPO, how old the restored "
                    "data is): roughly 310 hours here against 134 in the "
                    "baseline, and a longer restore because the data "
                    "crosses the gap. Illustrative figures. If there is no "
                    "vault, or the attacker outlasted its retention too, "
                    "this step has no good version."
                ),
                expert=(
                    "Off-array recovery from the Cyber Recovery vault: "
                    "replicated backup copies, longer retention (assumed), "
                    "CyberSense-validated copy predating corruption, "
                    "restore via a vault recovery host. No array snapshot "
                    "used. RPO ~310 h versus 134 h baseline "
                    "(illustrative)."
                ),
            ),
            active_regions=["verdict", "recovery", "array"],
            snapshots_taken=22,
            snapshots_expired=15,
            snapshots_corrupted=7,
            content_confidence_percent=99,
            verdict="no-clean-copy-on-array",
            recovery_source=VAULT_SOURCE,
            recovery_point_age_hours=382 - _VAULT_CLEAN_COPY_TAKEN_AT_HOURS,
            elapsed_hours=382,
            cycle_cost=4,
        ),
        DetectState(
            step=8,
            phase="restored",
            label="Back in service, and retention now has to outlast the scan interval",
            description=L(
                novice=(
                    "The data is back, older than anyone wanted. A fresh "
                    "snapshot is taken and checked straight away, so there "
                    "is one known-good copy to start from. The seven "
                    "ruined copies are exported for the investigators and "
                    "taken off the row. "
                    "Two habits change. Copies are checked on a schedule "
                    "instead of after a disaster, and copies are kept for "
                    "longer than the gap between checks, so a good copy "
                    "can never be deleted before anyone has looked."
                ),
                standard=(
                    "Production is restored from the vault copy, and a new "
                    "snapshot is taken and inspected immediately to give "
                    "the timeline a known-good baseline. The seven "
                    "corrupted snapshots are exported for forensics and "
                    "removed from the timeline. The lesson is arithmetic. A clean copy "
                    "survives only if retention is longer than the time "
                    "between content scans plus the time to act on one. "
                    "Scanning on a schedule shortens the first number; a "
                    "vault with long retention is the cover for the day "
                    "it is still not enough."
                ),
                expert=(
                    "Restored from vault; new baseline snapshot inspected "
                    "at once; corrupt set exported and removed. Rule going "
                    "forward: retention > scan interval + time to act, "
                    "with the vault as the backstop."
                ),
            ),
            active_regions=["array", _SNAPSHOTS[-1], "inspect", "classifier"],
            snapshots_taken=23,
            snapshots_expired=22,
            snapshots_corrupted=0,
            content_confidence_percent=99,
            verdict="no-clean-copy-on-array",
            recovery_source=VAULT_SOURCE,
            recovery_point_age_hours=382 - _VAULT_CLEAN_COPY_TAKEN_AT_HOURS,
            elapsed_hours=394,
        ),
    ]


def simulate_scenario(scenario: str) -> list[DetectState]:
    """The trace for a scenario id. Raises ``KeyError`` on an unknown id."""
    if scenario == BASELINE:
        return simulate()
    if scenario == DWELL_EXCEEDS_RETENTION:
        return simulate_dwell_exceeds_retention()
    raise KeyError(scenario)


# Exposed so tests can compare the two recovery points.
BASELINE_RPO_HOURS = BASELINE_RECOVERY_POINT_AGE_HOURS
