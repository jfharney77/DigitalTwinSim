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
            description=(
                "An ordinary week. Applications write to a production "
                "volume, the snapshot schedule runs, and three "
                "point-in-time copies sit on the array. Every one of them "
                "is genuinely restorable, and — this is the part worth "
                "holding on to — every one of them looks exactly like the "
                "copies that will be taken later, once none of them are. "
                "The uniformity of a snapshot timeline is what makes the "
                "problem ahead hard."
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
            description=(
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
            description=(
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
            description=(
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
            description=(
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
            description=(
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
            description=(
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
            description=(
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
            description=(
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
            active_regions=["array", *_CLEAN, "inspect", "classifier"],
            snapshots_taken=8,
            snapshots_corrupted=0,
            metadata_alerts=0,
            content_confidence_percent=99,
            last_clean_snapshot=CLEAN_SNAPSHOTS,
            elapsed_hours=138,
        ),
    ]
