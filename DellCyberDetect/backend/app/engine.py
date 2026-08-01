"""Pure detection engine for the Dell Cyber Detect twin.

``simulate()`` returns the deterministic trace of a ransomware incident and
the analysis that resolves it — from a quiet intrusion nobody notices, past
a corruption campaign designed to keep conventional detection silent, to a
forensic verdict naming the last provably clean copy. Same purity rule as
every other twin in this repo: no FastAPI, no IO, no timers — the frontend
owns the playback clock, and each ``DetectState`` is plain data the
renderer consumes.

The idea this twin exists to teach: **it reads the data, not the
metadata.**

Nearly every ransomware defence watches descriptions of data rather than
data. Did extensions change? Did entropy spike? Was there a mass rename? Is
the I/O rate unusual? These are cheap to measure and they worked well for
years, which is exactly why attackers stopped triggering them: encrypt
slowly, preserve extensions, imitate the I/O profile of ordinary work, and
every one of those detectors stays quiet. Metadata is a description the
adversary also controls.

What the adversary cannot control is whether a file still means anything.
So Cyber Detect opens files and databases inside snapshots on the array and
reads the bytes, scoring them with a model trained on thousands of
variants. Dell puts the accuracy at 99.99%.

The second half matters as much as the first. The output is not an alert —
by the time anyone runs this, being under attack is not news. The output is
a *date*: this snapshot, at this timestamp, is the last one whose contents
are intact. This repo's PowerProtect twin models the isolated vault that
guarantees a copy survives, and leaves that question open; a vault full of
faithfully replicated and immutably locked corruption has protected
nothing.

Two counters carry it. ``metadata_alerts`` is zero throughout, including
while corruption is actively spreading, because the attack was shaped to
keep it there. And ``last_clean_snapshot`` is -1 until the verdict, then
names a snapshot that is strictly older than the first corrupted one.
``tests/test_engine.py`` asserts both.

Timings, counts, and confidences are illustrative but plausible; favor a
correct mental model over measured numbers (project scope guardrail).
"""

from __future__ import annotations

from .anatomy import CLEAN_SNAPSHOTS, TOTAL_SNAPSHOTS
from .leveling import L
from .models import DetectState

# Phases in which data is corrupted and nothing has noticed. The premise of
# the product lives here: corruption present, alerts at zero.
CORRUPTION_PHASES = {"encrypt", "blind"}

# Phases in which content inspection has run and its confidence is real.
ANALYSIS_PHASES = {"classify", "verdict", "recover", "restored"}

_SNAPSHOTS = [f"snap-{i}" for i in range(1, TOTAL_SNAPSHOTS + 1)]

# The copies the verdict will vindicate, and the ones it will condemn.
_CLEAN = _SNAPSHOTS[:CLEAN_SNAPSHOTS]
_DIRTY = _SNAPSHOTS[CLEAN_SNAPSHOTS:]


def simulate() -> list[DetectState]:
    """An incident, and the analysis that produces a usable answer."""
    return [
        DetectState(
            step=0,
            phase="clean",
            label="Normal operations — snapshots on schedule",
            description=L(
                novice=(
                    "An ordinary week. Programs write to a storage system, the "
                    "scheduled job that saves point-in-time copies runs, and three "
                    "of those copies now sit on the array. Every one of them can "
                    "genuinely be restored. Hold on to that, because — and this is "
                    "the whole problem coming — every one of them also looks "
                    "exactly like the copies that will be taken later, once none of "
                    "them can be restored."
                ),
                plain=(
                    "An ordinary week. Applications write to a production volume, "
                    "the snapshot schedule runs, and three point-in-time copies sit "
                    "on the array. All three are genuinely restorable — and the "
                    "part worth holding on to is that they look exactly like the "
                    "copies taken later, once none of them are. The uniformity of a "
                    "snapshot timeline is what makes the problem ahead hard."
                ),
                standard=(
                    "An ordinary week. Applications write to a production "
                    "volume, the snapshot schedule runs, and three "
                    "point-in-time copies sit on the array. Every one of them "
                    "is genuinely restorable, and — this is the part worth "
                    "holding on to — every one of them looks exactly like the "
                    "copies that will be taken later, once none of them are. "
                    "The uniformity of a snapshot timeline is what makes the "
                    "problem ahead hard."
                ),
                technical=(
                    "Baseline. Applications writing, snapshot schedule running, "
                    "three restorable copies on the array. They are visually and "
                    "structurally identical to the copies taken after compromise — "
                    "that uniformity is the problem the product addresses."
                ),
                expert=(
                    "Baseline: three restorable snapshots, indistinguishable by any "
                    "external property from post-compromise copies."
                ),
            ),
            active_regions=["array", *_CLEAN],
            snapshots_taken=3,
            snapshots_corrupted=0,
            metadata_alerts=0,
            content_confidence_percent=0,
            last_clean_snapshot=-1,
            elapsed_hours=0,
        ),
        DetectState(
            step=1,
            phase="intrusion",
            label="An intruder is inside, doing nothing visible",
            description=L(
                novice=(
                    "Someone has got in — a stolen password, an unpatched piece of "
                    "software, a convincing email weeks ago. Nothing is being "
                    "scrambled yet. This waiting period is called dwell time, and "
                    "in real incidents it is routinely measured in weeks: the "
                    "intruder is quietly mapping the network, finding where the "
                    "backups live, and learning what normal activity looks like so "
                    "they can imitate it. Every copy saved during this period is "
                    "still perfectly good, which means recovery would still be "
                    "easy. Nobody knows there is anything to recover from."
                ),
                plain=(
                    "Access has been obtained — a stolen credential, an unpatched "
                    "service, a phishing success weeks ago. Nothing is being "
                    "encrypted yet. This is dwell time, and in real incidents it is "
                    "routinely weeks: the attacker is mapping the estate, finding "
                    "the backup system, and learning what normal looks like so they "
                    "can imitate it. Every snapshot taken now is still clean, so "
                    "recovery would still be easy. Nobody knows there is anything "
                    "to recover from."
                ),
                standard=(
                    "Access has been obtained — a stolen credential, an "
                    "unpatched service, a phishing success weeks ago. Nothing "
                    "is being encrypted yet. This is dwell time, and in real "
                    "incidents it is routinely measured in weeks: the attacker "
                    "is mapping the estate, finding the backup system, and "
                    "learning what normal looks like so they can imitate it. "
                    "Every snapshot taken during this period is still perfectly "
                    "clean, which means recovery is still easy. Nobody knows "
                    "there is anything to recover from."
                ),
                technical=(
                    "Initial access achieved; no encryption yet. Dwell time — "
                    "routinely weeks in practice — spent on discovery, locating the "
                    "backup infrastructure, and baselining normal activity for "
                    "later imitation. Snapshots taken in this window remain clean, "
                    "so recovery is trivial and nobody knows it is needed."
                ),
                expert=(
                    "Access established, pre-encryption. Dwell: discovery, backup "
                    "enumeration, behavioural baselining. Snapshots still clean; "
                    "recovery trivial and unknown to be necessary."
                ),
            ),
            active_regions=["array", *_CLEAN],
            snapshots_taken=4,
            snapshots_corrupted=0,
            metadata_alerts=0,
            content_confidence_percent=0,
            last_clean_snapshot=-1,
            elapsed_hours=72,
            cycle_cost=2,
        ),
        DetectState(
            step=2,
            phase="encrypt",
            label="Corruption begins, deliberately shaped to look ordinary",
            description=L(
                novice=(
                    "The scrambling begins, and it is designed around the alarms. "
                    "Files are rewritten slowly rather than all at once. Their "
                    "names are left alone rather than being given a conspicuous new "
                    "ending. The amount of data changing stays within what ordinary "
                    "work produces. Every one of those choices costs the attacker "
                    "time, and they make it anyway, because the alternative is "
                    "setting something off on the first afternoon. Two saved copies "
                    "now contain damaged data, and from the outside they are "
                    "indistinguishable from the four before them."
                ),
                plain=(
                    "The encryption campaign starts, and it is designed around the "
                    "detectors. Files are rewritten slowly rather than in a burst. "
                    "Extensions are preserved rather than appended with something "
                    "conspicuous. The volume of changed blocks stays inside the "
                    "range ordinary work produces. Each of those choices costs the "
                    "attacker time, and they make it anyway, because the "
                    "alternative is tripping something on the first afternoon. Two "
                    "snapshots now contain corrupted data, indistinguishable from "
                    "the others by every visible property."
                ),
                standard=(
                    "The encryption campaign starts, and it is designed around "
                    "the detectors. Files are rewritten slowly rather than in "
                    "a burst. Extensions are preserved rather than appended "
                    "with something conspicuous. The volume of changed blocks "
                    "stays inside the range that ordinary work produces. Every "
                    "one of those choices costs the attacker time, and they "
                    "make it anyway, because the alternative is tripping "
                    "something on the first afternoon. Two snapshots now "
                    "contain corrupted data, and they are indistinguishable "
                    "from the four before them by every property visible from "
                    "outside."
                ),
                technical=(
                    "Encryption begins, shaped against the detection surface: "
                    "rate-limited rewrites, extensions preserved, changed-block "
                    "volume held inside the normal envelope. Each constraint costs "
                    "the attacker time and is accepted, because the alternative is "
                    "a first-day alert. Two snapshots corrupted, externally "
                    "indistinguishable from the clean ones."
                ),
                expert=(
                    "Encryption begins, evasion-shaped: rate-limited, extensions "
                    "preserved, changed-block volume within envelope. Two snapshots "
                    "corrupt, externally indistinguishable."
                ),
            ),
            active_regions=["array", *_SNAPSHOTS[:5]],
            snapshots_taken=5,
            snapshots_corrupted=2,
            metadata_alerts=0,
            content_confidence_percent=0,
            last_clean_snapshot=-1,
            elapsed_hours=96,
            cycle_cost=2,
        ),
        DetectState(
            step=3,
            phase="blind",
            label="Metadata and behaviour detection see nothing",
            description=L(
                novice=(
                    "The uncomfortable step. Four of the seven saved copies are now "
                    "damaged, the attack has been running for two days, and the "
                    "alarm count reads zero — not because the security tools are "
                    "broken, but because they are working exactly as designed and "
                    "are being asked the wrong question. No file name changed, so "
                    "the name monitor is quiet. The scrambling happened gradually, "
                    "so the threshold for sudden change was never crossed. Nothing "
                    "was renamed in bulk. The activity looks like a busy Tuesday. "
                    "Everything that watches *descriptions* of the data is "
                    "satisfied, and the data is ruined."
                ),
                plain=(
                    "The uncomfortable step. Four of seven snapshots are now "
                    "corrupted, the campaign has run for two days, and the alert "
                    "counter reads zero — not because the tools are misconfigured, "
                    "but because they are working as designed and being asked the "
                    "wrong question. No extension changed, so the extension monitor "
                    "is quiet. Entropy rose gradually, so the threshold was never "
                    "crossed. Nothing was renamed en masse. The I/O profile looks "
                    "like a busy Tuesday. Everything watching descriptions of the "
                    "data is satisfied, and the data is ruined."
                ),
                standard=(
                    "The uncomfortable step. Four of seven snapshots are now "
                    "corrupted, the campaign has been running for two days, "
                    "and the alert counter reads zero — not because the tools "
                    "are misconfigured, but because they are working exactly "
                    "as designed and are being asked the wrong question. No "
                    "extension changed, so the extension monitor is quiet. "
                    "Entropy rose gradually, so the entropy threshold was "
                    "never crossed. Nothing was renamed en masse. The I/O "
                    "profile looks like a busy Tuesday. Everything that "
                    "watches *descriptions* of the data is satisfied, and the "
                    "data is ruined."
                ),
                technical=(
                    "Four of seven snapshots corrupt, two days in, alert count zero "
                    "— the detectors are working correctly and answering the wrong "
                    "question. No extension delta, entropy raised below threshold "
                    "gradient, no mass rename, I/O within profile. Every "
                    "metadata-derived signal is nominal while the payload is "
                    "destroyed."
                ),
                expert=(
                    "4/7 corrupt, zero alerts. Every metadata-derived signal "
                    "nominal by construction: no extension delta, sub-threshold "
                    "entropy gradient, no mass rename, in-profile I/O."
                ),
            ),
            active_regions=["array", *_SNAPSHOTS],
            snapshots_taken=7,
            snapshots_corrupted=4,
            metadata_alerts=0,
            content_confidence_percent=0,
            last_clean_snapshot=-1,
            elapsed_hours=120,
            cycle_cost=2,
        ),
        DetectState(
            step=4,
            phase="inspect",
            label="Content inspection opens the snapshots and reads the bytes",
            description=L(
                novice=(
                    "The long step, and the one being paid for. Instead of "
                    "reasoning about the data from the outside, the analysis opens "
                    "the files and database records inside every saved copy and "
                    "reads what is actually there. This is expensive — by some "
                    "distance the slowest thing in the whole story — and the "
                    "expense is the entire product. A description of a file is "
                    "something the attacker can also control; the contents are not. "
                    "A file can be made to look ordinary from every angle except "
                    "the one that asks whether it still means anything, and that is "
                    "the only angle being used. Note too that this runs on the "
                    "storage system itself, so there is no waiting for copies to "
                    "travel elsewhere before the question can even be asked."
                ),
                plain=(
                    "The long stage, and the one being paid for. Rather than "
                    "reasoning about the data, the analysis opens files and "
                    "database pages inside every snapshot and reads what is there. "
                    "It is expensive — by some distance the slowest thing in this "
                    "trace — and the expense is the product. Metadata is a "
                    "description the attacker also controls; content is not. A file "
                    "can be made to look ordinary from every angle except the one "
                    "asking whether it still means anything. It runs on the array "
                    "against local snapshots, so there is no replication lag before "
                    "the question can be asked."
                ),
                standard=(
                    "The long stage, and the one being paid for. Rather than "
                    "reasoning about the data, the analysis opens files and "
                    "database pages inside every snapshot on the array and "
                    "reads what is actually there. This is expensive — it is "
                    "by some distance the slowest thing in this trace — and "
                    "the expense is the entire product. Metadata is a "
                    "description the attacker also controls; content is not. "
                    "A file can be made to look ordinary from every angle "
                    "except the one that asks whether it still means anything, "
                    "and that is the only angle being used here. Note that it "
                    "runs on the array itself, against local snapshots, so "
                    "there is no replication lag to wait out before the "
                    "question can even be asked."
                ),
                technical=(
                    "Max-dwell stage and the one being paid for: files and database "
                    "pages inside each snapshot are opened and inspected at byte "
                    "level. Expensive, and the expense is the product — metadata is "
                    "attacker-controlled, payload integrity is not. Runs "
                    "array-local against local snapshots, so no replication lag "
                    "gates the question."
                ),
                expert=(
                    "Byte-level content inspection across all snapshots. Max dwell; "
                    "cost is the product. Metadata is attacker-controlled, payload "
                    "integrity is not. Array-local — no replication lag."
                ),
            ),
            active_regions=["array", *_SNAPSHOTS, "inspect"],
            snapshots_taken=7,
            snapshots_corrupted=4,
            metadata_alerts=0,
            content_confidence_percent=0,
            last_clean_snapshot=-1,
            elapsed_hours=126,
            cycle_cost=6,
        ),
        DetectState(
            step=5,
            phase="classify",
            label="The trained model scores every snapshot",
            description=L(
                novice=(
                    "What the inspection found is scored against the characteristic "
                    "patterns of intact data versus damaged data — is this still a "
                    "valid database record, a well-formed document, something "
                    "coherent? The model was trained on thousands of ransomware "
                    "families, which is not the same as a list of known viruses: by "
                    "the time you are examining saved copies, the malicious program "
                    "is not what you are looking at. You are looking at the damage "
                    "it did, and there are far fewer ways to wreck a file than "
                    "there are programs that do it — which is why this recognises "
                    "variants nobody has catalogued. The error that matters is the "
                    "one where damaged data is declared safe, because somebody then "
                    "restores from it."
                ),
                plain=(
                    "What the inspection read is scored against the statistical "
                    "fingerprints of intact versus corrupted data — is this a valid "
                    "database page, a well-formed document, a coherent record? The "
                    "model was trained across thousands of ransomware variants, "
                    "which is not a signature database: by the time you are "
                    "examining snapshots, the malware is not what you are looking "
                    "at. You are looking at the damage, and there are far fewer "
                    "ways to wreck a file than programs that do it — which is why "
                    "this generalizes to uncatalogued variants. Confidence lands in "
                    "the 99%-plus range. The error that matters is the false "
                    "negative."
                ),
                standard=(
                    "What the inspection read is scored against the "
                    "statistical fingerprints of intact versus corrupted "
                    "data — is this still a valid database page, a well-formed "
                    "document, a coherent record? The model was trained across "
                    "thousands of ransomware variants, which is not the same "
                    "as a signature database: signatures identify malware, and "
                    "the malware is not what is being examined here. What is "
                    "being examined is the damage, and the number of ways to "
                    "wreck a file is far smaller than the number of programs "
                    "that do it — which is why this generalizes to variants "
                    "nobody has catalogued. Confidence lands at the 99%-plus "
                    "range Dell publishes. The error that matters is the "
                    "false negative, because it certifies a corrupt snapshot "
                    "as safe and somebody restores from it."
                ),
                technical=(
                    "Inspection output scored against integrity fingerprints — "
                    "valid database page, well-formed document, coherent record. "
                    "Trained across thousands of variants, which is not signature "
                    "matching: the artefact under examination is the damage, not "
                    "the malware, and damage morphology generalizes far better than "
                    "binaries do. Confidence ≥99%. The consequential error is the "
                    "false negative, which certifies corruption as clean."
                ),
                expert=(
                    "Integrity scoring against trained fingerprints; damage "
                    "morphology generalizes where signatures do not. ≥99% "
                    "confidence. False negative is the consequential error — it "
                    "certifies corruption."
                ),
            ),
            active_regions=["array", *_SNAPSHOTS, "inspect", "classifier", "models"],
            snapshots_taken=7,
            snapshots_corrupted=4,
            metadata_alerts=0,
            content_confidence_percent=99,
            last_clean_snapshot=-1,
            elapsed_hours=129,
            cycle_cost=3,
        ),
        DetectState(
            step=6,
            phase="verdict",
            label="The answer is a date, not an alert",
            description=L(
                novice=(
                    "Copy 3 is the last one whose contents are provably intact; "
                    "everything from copy 4 onward carries the damage. That "
                    "sentence, with the evidence attached, is the deliverable — and "
                    "notice how different it is from what a security product "
                    "usually produces. 'You have ransomware' is not useful here; by "
                    "this point it is not news. What a recovery decision needs is "
                    "*which copy*, and there is no way to work that out by "
                    "inference. It had to be established by reading every byte, "
                    "which is why the previous step cost what it did."
                ),
                plain=(
                    "Snapshot 3 is the last copy whose contents are provably "
                    "intact; everything from snapshot 4 onward carries the "
                    "corruption. That sentence, with evidence attached, is the "
                    "deliverable — and it is very different from what a detection "
                    "product usually produces. 'You have ransomware' is not useful "
                    "here; by this point it is not news. A recovery decision "
                    "requires which copy, and there is no way to answer that by "
                    "inference. It had to be established by reading every byte, "
                    "which is why the inspection cost what it did."
                ),
                standard=(
                    "Snapshot 3 is the last copy whose contents are provably "
                    "intact; everything from snapshot 4 onward carries the "
                    "corruption. That sentence — with evidence attached — is "
                    "the deliverable, and it is worth noticing how different "
                    "it is from what a detection product usually produces. "
                    "'You have ransomware' is not useful here; by this point "
                    "it is not news. What a recovery decision requires is "
                    "which copy, and there is no way to answer that by "
                    "inference. It had to be established by reading every "
                    "byte, which is why the inspection stage cost what it did."
                ),
                technical=(
                    "Recovery point established: snapshot 3 is the last "
                    "provably-intact copy, corruption from 4 onward, evidence "
                    "attached. The deliverable is a recovery point rather than an "
                    "alert — detection is not news at this stage. Which copy is not "
                    "inferable; it is established by exhaustive content read, which "
                    "is what the inspection stage bought."
                ),
                expert=(
                    "Recovery point: snapshot 3, corruption from 4. Deliverable is "
                    "a point, not an alert. Not inferable — established by "
                    "exhaustive read."
                ),
            ),
            active_regions=[*_SNAPSHOTS, "classifier", "verdict"],
            snapshots_taken=7,
            snapshots_corrupted=4,
            metadata_alerts=0,
            content_confidence_percent=99,
            last_clean_snapshot=CLEAN_SNAPSHOTS,
            elapsed_hours=130,
        ),
        DetectState(
            step=7,
            phase="recover",
            label="Restore from the named copy — not the newest, not the oldest",
            description=L(
                novice=(
                    "Recovery runs from copy 3 specifically. The value of a precise "
                    "answer shows up in what is *not* done: the newest copy is not "
                    "used, because it would bring the attack back, and a copy from "
                    "three months ago is not used out of caution, because it would "
                    "throw away three months of legitimate work. The gap between "
                    "those two options is what precision is worth. This is also "
                    "where the vault twin elsewhere in this repo joins on — it "
                    "covers where a guaranteed-reachable copy comes from. Isolation "
                    "without detection leaves you a safe copy you cannot identify; "
                    "detection without isolation leaves you an answer about copies "
                    "the attacker may already have deleted."
                ),
                plain=(
                    "Recovery runs from snapshot 3 specifically. The value of "
                    "precision shows in what is not done: the newest snapshot is "
                    "not used, because it would reinstate the attack, and a "
                    "three-month-old copy is not used out of caution, because it "
                    "would discard three months of legitimate work. The gap between "
                    "those is what a precise answer is worth. This repo's "
                    "PowerProtect twin covers where a guaranteed-reachable copy "
                    "comes from — isolation without detection gives you a safe copy "
                    "you cannot identify, detection without isolation gives you an "
                    "answer about copies the attacker may have deleted."
                ),
                standard=(
                    "Recovery runs from snapshot 3 specifically. The value of "
                    "precision shows up in what is *not* done: the newest "
                    "snapshot is not used, because it would reinstate the "
                    "attack, and a copy from three months ago is not used out "
                    "of caution, because it would throw away three months of "
                    "legitimate work. The gap between those two options is "
                    "what a precise answer is worth. This is where this repo's "
                    "PowerProtect twin joins on — it models where a "
                    "guaranteed-reachable copy comes from, behind an "
                    "operational air gap and immutably locked. Isolation "
                    "without detection leaves you a safe copy you cannot "
                    "identify; detection without isolation leaves you an "
                    "answer about copies the attacker may already have "
                    "deleted."
                ),
                technical=(
                    "Restore from the identified snapshot. Precision shows in the "
                    "avoided alternatives: the newest copy reinstates the attack, "
                    "an over-cautious old copy discards weeks of legitimate work, "
                    "and the spread between them is the value. Pairs with the "
                    "PowerProtect twin's vault: isolation without detection yields "
                    "an unidentifiable safe copy, detection without isolation "
                    "yields an answer about copies that may be gone."
                ),
                expert=(
                    "Restore from the identified point. Avoided: reinstating the "
                    "attack (newest) and discarding weeks (over-cautious). Pairs "
                    "with vault isolation — neither control is sufficient alone."
                ),
            ),
            active_regions=[*_CLEAN, "verdict", "recovery", "array"],
            snapshots_taken=7,
            snapshots_corrupted=0,
            metadata_alerts=0,
            content_confidence_percent=99,
            last_clean_snapshot=CLEAN_SNAPSHOTS,
            elapsed_hours=134,
            cycle_cost=2,
        ),
        DetectState(
            step=8,
            phase="restored",
            label="A known-good baseline, and a schedule that now gets checked",
            description=L(
                novice=(
                    "The system is back, from a copy whose integrity was "
                    "established rather than assumed, and the next saved copy is "
                    "taken against a baseline someone can vouch for. The lasting "
                    "change is not the recovery but the routine: content analysis "
                    "now runs continuously against new copies, so the gap between "
                    "damage and discovery — which is the number that decides how "
                    "much an incident costs — shrinks from days to the length of "
                    "one scan. This incident took 130 hours to resolve, and almost "
                    "all of that was the five days before anyone had any reason to "
                    "look."
                ),
                plain=(
                    "The volume is back, from a copy whose integrity was "
                    "established rather than assumed, and the next snapshot is "
                    "taken against a baseline someone can vouch for. The lasting "
                    "change is the routine, not the recovery: content analysis now "
                    "runs continuously against new snapshots, so the interval "
                    "between corruption and discovery — the number that decides "
                    "what an incident costs — shrinks from days to one scan. This "
                    "incident took 130 hours, and almost all of it was the five "
                    "days before anyone had reason to look."
                ),
                standard=(
                    "The volume is back, from a copy whose integrity was "
                    "established rather than assumed, and the next snapshot is "
                    "taken against a baseline someone can vouch for. The "
                    "lasting change is not the recovery but the routine: "
                    "content analysis now runs continuously against new "
                    "snapshots, so the interval between corruption and "
                    "discovery — which is the number that decides how much an "
                    "incident costs — shrinks from days to the length of one "
                    "scan. The incident above took 130 hours to resolve. "
                    "Almost all of that was the five days before anyone had "
                    "any reason to look."
                ),
                technical=(
                    "Restored from a copy with established rather than assumed "
                    "integrity; the next snapshot baselines against something "
                    "vouched for. The durable change is operational — continuous "
                    "content analysis against new snapshots collapses the "
                    "corruption-to-discovery interval from days to one scan period. "
                    "130 hours elapsed, of which five days preceded any reason to "
                    "look."
                ),
                expert=(
                    "Restored from an established-integrity copy; continuous "
                    "scanning thereafter collapses corruption-to-discovery from "
                    "days to one scan period. 130 h elapsed, ~5 d of it "
                    "pre-suspicion."
                ),
            ),
            active_regions=["array", *_CLEAN, "inspect", "classifier"],
            snapshots_taken=8,
            snapshots_corrupted=0,
            metadata_alerts=0,
            content_confidence_percent=99,
            last_clean_snapshot=CLEAN_SNAPSHOTS,
            elapsed_hours=138,
        ),
    ]
