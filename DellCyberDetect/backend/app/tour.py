"""The narrated tour of Dell Cyber Detect — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: eight beats that
move a camera along the snapshot timeline and down into the machinery that
reads it, pin the incident trace at the moments that carry the story, and
narrate each one. The frontend player owns the clock; nothing here knows
about time, IO or the web (AST-checked in ``tests/test_tour.py``, the same
rule as ``engine.py``).

The signature beat is ``blind-then-read``: four of seven snapshots are
corrupted, the metadata alert counter reads zero, and the timeline is drawn
with every copy identical — because from outside they are. The only way out
is to open the copies and read the bytes, which is the next beat. Every
claim the scripts make is one the engine and the anatomy already make; the
trace index named in each beat is the step whose description says the same
thing.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``DetectAnatomy`` is unchanged:

    0  what an administrator sees and acts on: the live volume, the report,
       the restore
    1  the snapshot timeline beneath the volume
    2  the machinery that reads inside the snapshots: inspection, classifier,
       variant corpus
"""

from __future__ import annotations

from twinkit.tour import (
    CameraTarget,
    Tour,
    TourPhoto,
    TourResponse,
    TourSource,
    TourStep,
    camera_around,
    whole_map,
)

from .leveling import L
from .models import DetectAnatomy

#: The step the tests pin: the product's one idea lives here.
SIGNATURE_STEP_ID = "blind-then-read"

_SURFACE = 0
_TIMELINE = 1
_CONTENT = 2

_LAYER_BY_KIND = {
    "array": _SURFACE,
    "verdict": _SURFACE,
    "recovery": _SURFACE,
    "snapshot": _TIMELINE,
    "inspect": _CONTENT,
    "classifier": _CONTENT,
    "models": _CONTENT,
}


def layer_map(anatomy: DetectAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    return {r.id: _LAYER_BY_KIND.get(r.kind, _TIMELINE) for r in anatomy.regions}


def _photos() -> list[TourPhoto]:
    return [
        TourPhoto(
            id="timeline",
            url="/cyberdetect-timeline.svg",
            caption=(
                "A snapshot timeline with an infection somewhere in it; only "
                "reading the bytes says where."
            ),
            credit="Schematic illustration by this project — not a Dell product image",
        ),
    ]


def build_tour(anatomy: DetectAnatomy) -> Tour:
    """The Cyber Detect tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 3.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    snaps = sorted(
        (r for r in anatomy.regions if r.kind == "snapshot"), key=lambda r: r.x
    )
    all_snaps = [r.id for r in snaps]

    steps = [
        TourStep(
            id="snapshot-timeline",
            title="Seven copies on a line",
            script=L(
                novice=(
                    "This is Dell Cyber Detect, software that runs on a Dell "
                    "storage array, a PowerStore or a PowerMax. Across the top "
                    "is the live volume, the storage that programs write to all "
                    "day. The row of boxes underneath is a timeline of "
                    "snapshots: saved point-in-time copies of that volume, "
                    "oldest on the left and newest on the right. Seven places "
                    "are drawn, numbered 1 to 7; the T-4 beside a number means "
                    "four copies before the newest. So far three copies have "
                    "been taken, the other four places are still to be filled, and every "
                    "one of them can be restored. Notice that they all look "
                    "exactly alike. That sameness is the whole problem this "
                    "tour is about."
                ),
                standard=(
                    "Dell Cyber Detect runs on the storage array itself, a "
                    "PowerStore or a PowerMax. Across the top is the production "
                    "volume that applications write to. The middle row is a "
                    "timeline of snapshots, point-in-time copies of that volume, "
                    "oldest on the left and newest on the right. Seven positions "
                    "are drawn, numbered oldest first (T-n is n snapshots before "
                    "the newest); three copies exist so far, one every 30 hours "
                    "in this illustrative trace, and all three are "
                    "restorable. They are also indistinguishable from each "
                    "other, and from the copies still to come. That uniformity "
                    "is the problem."
                ),
                expert=(
                    "Cyber Detect on PowerStore/PowerMax. Production volume on "
                    "top, snapshot timeline below, oldest left. Seven slots, "
                    "three filled so far (one every 30 h, illustrative); the "
                    "three restorable copies are externally identical."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["array", *all_snaps[:3]],
            layer_reveal=_SURFACE,
            trace_cursor=0,
            duration_ms=26_000,
            photo_id="timeline",
        ),
        TourStep(
            id="quiet-intrusion",
            title="An intruder, and nothing to see",
            script=L(
                novice=(
                    "Someone has broken in, perhaps with a stolen password or a "
                    "trick email weeks ago. They are not scrambling anything "
                    "yet. Instead they wait and watch, learning where the "
                    "backups live and what normal activity looks like so they "
                    "can imitate it later. This quiet waiting period is called "
                    "dwell time, and in real attacks it often lasts weeks. "
                    "Nothing has been scrambled yet, so the three copies on the "
                    "array are still good and recovering would be easy. Nobody "
                    "knows anything is wrong. The timings here are "
                    "illustrative, and the wait is squeezed to about a day so "
                    "the story fits."
                ),
                standard=(
                    "An intruder is inside, through a stolen credential, an "
                    "unpatched service or a phishing email, and is deliberately "
                    "doing nothing visible. This is dwell time, routinely weeks "
                    "in real incidents: mapping the estate, finding the backup "
                    "system, and learning what normal looks like in order to "
                    "imitate it. Nothing is encrypted yet, so the three "
                    "snapshots on the array are clean and recovery would be "
                    "easy. Nobody knows there is anything to recover from. "
                    "The trace compresses the wait to about a day; timings are "
                    "illustrative."
                ),
                expert=(
                    "Initial access, pre-encryption. Dwell: discovery, backup "
                    "enumeration, baselining. No encryption yet; snapshots "
                    "1-3 clean. t+24 h, compressed, illustrative."
                ),
            ),
            # The older end of the timeline; the newer copies sit off to the
            # right. (The row spans the map, so framing all of it would be
            # the whole map again.)
            camera=CameraTarget(x=0, y=0, w=60, h=34.8),
            region_ids=["array", *all_snaps[:3]],
            layer_reveal=_TIMELINE,
            trace_cursor=1,
            duration_ms=26_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="Four ruined, and the row looks the same",
            script=L(
                novice=(
                    "This is the most important moment in the tour. The "
                    "attacker has started scrambling files, but slowly, keeping "
                    "the file names unchanged and the activity looking like an "
                    "ordinary busy day. Normal defences watch for exactly the "
                    "signs the attacker avoided: file endings changing, files "
                    "suddenly turning into random-looking noise (measured as "
                    "entropy), or thousands of files renamed at once. So they "
                    "stay silent, with zero alerts. Yet four of the seven "
                    "copies on the timeline are now ruined. Look at the row. "
                    "Can you tell which four? Nobody can, and the boxes are "
                    "drawn identically because that is the truth of this "
                    "moment. Watching descriptions of the data, called "
                    "metadata, cannot answer the question. The only way left "
                    "is to open the copies and read what is inside them."
                ),
                standard=(
                    "The moment the product exists for. The encryption "
                    "campaign was shaped around the detectors: files rewritten slowly, extensions "
                    "preserved, entropy (how random the bytes look) raised "
                    "gradually, the I/O profile kept inside a busy Tuesday. So "
                    "the metadata and behaviour monitors, which watch "
                    "descriptions of the data rather than the data, report zero "
                    "alerts while four of seven snapshots are corrupted. Look "
                    "at the timeline: every copy is drawn the same, because "
                    "from outside they are the same. Nothing on this screen "
                    "says which four. The only way to find out is to open them "
                    "and read the bytes."
                ),
                expert=(
                    "Four of seven snapshots corrupted, metadata "
                    "alerts zero. Slow encryption, extensions kept, entropy "
                    "held under the statistical threshold, normal I/O. Only "
                    "byte-level reading separates them."
                ),
            ),
            camera=frame("array", *all_snaps),
            region_ids=["array", *all_snaps],
            layer_reveal=_TIMELINE,
            trace_cursor=3,
            duration_ms=42_000,
        ),
        TourStep(
            id="read-the-bytes",
            title="Opening every copy and reading it",
            script=L(
                novice=(
                    "Somebody reports records that will not open, and the "
                    "administrator starts the content check by hand; it was not "
                    "on a timetable before this. "
                    "Now the product does the slow, unglamorous work. It opens "
                    "the files and database pages inside every snapshot and "
                    "reads what is actually there: not the names, not the "
                    "dates, not how fast things changed, but the contents "
                    "themselves. An attacker can make a file look ordinary from "
                    "every angle, but it is far harder to make a scrambled file "
                    "still make sense when it is opened. This "
                    "is by far the longest stage of the whole incident, and "
                    "that cost is exactly what you are paying for. It happens "
                    "on the storage array itself, so there is no waiting for "
                    "copies to be sent somewhere else first. The row still "
                    "looks the same, because nothing has been scored yet."
                ),
                standard=(
                    "An application team reports unreadable records and the "
                    "administrator runs content inspection on demand; it was "
                    "not scheduled before this incident. It opens files and "
                    "database pages inside "
                    "every snapshot and reads what is there. Not the name, the "
                    "extension, the timestamp or the rate of change: the bytes. "
                    "It is by some distance the longest stage in the trace, and "
                    "the expense is the product. Metadata is a description the "
                    "attacker also controls; whether the content is still a "
                    "valid file or database page is far harder to fake. It "
                    "runs on the "
                    "array against local snapshots, so there is no replication "
                    "lag to wait out first. Until the reading has been scored, "
                    "the timeline still looks uniform."
                ),
                expert=(
                    "Admin-initiated on a user report; nothing was scheduled. "
                    "Byte-level inspection of every snapshot (format and "
                    "structure validity per file and DB page), on-array; longest "
                    "stage. No replication lag. Timeline still unrevealed, "
                    "nothing scored."
                ),
            ),
            camera=frame("inspect", *all_snaps),
            region_ids=["inspect", *all_snaps],
            layer_reveal=_CONTENT,
            trace_cursor=4,
            duration_ms=30_000,
        ),
        TourStep(
            id="confidence-climbs",
            title="Confidence, only now",
            script=L(
                novice=(
                    "A trained model, called a classifier, now scores what the "
                    "inspection read. It asks plain questions of every copy: is "
                    "this still a valid database page, a proper document, a "
                    "sensible record? Dell says it was trained on thousands of "
                    "kinds of ransomware, the software that scrambles files for "
                    "a payment. That is not a list of known viruses. It is not "
                    "looking for the attacker's program; it is looking for the "
                    "damage, and there are far fewer ways to wreck a file than "
                    "there are programs that do it. Until now the confidence "
                    "reading was zero, because nothing had been read. Now it "
                    "reads 99 percent, and the four ruined copies turn red on "
                    "the timeline for the first time. (Dell's own claim for "
                    "the product is 99.99 percent accuracy; the numbers here "
                    "are illustrative.) The mistake that matters most "
                    "is a false negative: calling a ruined copy safe."
                ),
                standard=(
                    "The classifier scores what the inspection read against the "
                    "fingerprints of intact versus corrupted data: is this "
                    "still a valid database page, a well-formed document, a "
                    "coherent record? Dell says it was trained across thousands "
                    "of ransomware variants; either way it is not a signature "
                    "database: "
                    "it examines the damage, not the malware. Confidence was "
                    "zero until the bytes were read. Now it reads 99 percent "
                    "(illustrative; Dell claims 99.99% accuracy), and only now "
                    "do the four corrupted snapshots show on the timeline. The error that "
                    "matters is the false negative, a corrupt copy certified "
                    "safe."
                ),
                expert=(
                    "Classifier scores damage, not malware; trained on "
                    "thousands of variants (Dell). Confidence 0 until "
                    "inspection, now 99% (Dell claims 99.99% accuracy). "
                    "Corruption revealed."
                ),
            ),
            # The scores and the four copies they condemn, in one frame:
            # the narration points at the timeline turning red.
            camera=frame("classifier", "models", *all_snaps[3:]),
            region_ids=["classifier", "models", *all_snaps[3:]],
            layer_reveal=_CONTENT,
            trace_cursor=5,
            duration_ms=30_000,
        ),
        TourStep(
            id="verdict-is-a-date",
            title="The answer is a date",
            script=L(
                novice=(
                    "Here is what the whole process produces, and it is not an "
                    "alarm. By now everyone knows there has been an attack, so "
                    "'you have ransomware' is not news. The answer is a date: "
                    "snapshot 3, the box marked 3 · T-4 on the map, saved at "
                    "t+0h on this example clock, is the last copy "
                    "whose contents are proven intact, and everything from "
                    "snapshot 4 onward carries the damage. A marker lands on "
                    "that copy. It is older than the first ruined one, and the "
                    "tests behind this simulation insist on that, because "
                    "calling a ruined copy clean is the one way this product "
                    "can truly fail someone. The answer could only come after "
                    "every byte had been read."
                ),
                standard=(
                    "The deliverable is a date, not an alert. Snapshot 3, the "
                    "box marked 3 · T-4 on the map, taken at t+0h on this "
                    "illustrative clock, is the last copy whose contents "
                    "are provably intact; everything from snapshot 4 onward "
                    "carries the corruption. It is strictly older than the "
                    "first corrupted copy, as it must be, since a false "
                    "negative here means someone restores the attack. A "
                    "recovery decision needs exactly this sentence, and it "
                    "could not be inferred: it had to be established by "
                    "reading every byte, which is why inspection cost what it "
                    "did."
                ),
                expert=(
                    "Verdict: snapshot 3 (T-4, taken t+0h) last provably clean, strictly "
                    "before the first corruption. A recovery point with "
                    "evidence, not an alert."
                ),
            ),
            camera=frame("verdict", all_snaps[2], all_snaps[3]),
            region_ids=["classifier", "verdict", all_snaps[2]],
            layer_reveal=_CONTENT,
            trace_cursor=6,
            duration_ms=28_000,
        ),
        TourStep(
            id="recover-named-copy",
            title="Restore from the named copy",
            script=L(
                novice=(
                    "Recovery runs from snapshot 3, and the precision shows in "
                    "what is not done. The newest copy is not used, because it "
                    "would bring the attack straight back. A copy from months "
                    "ago is not used just to be safe either, because that would "
                    "throw away months of honest work. The gap between those "
                    "two choices is what a precise answer is worth. It is not "
                    "free: snapshot 3 is 134 hours old, so about five and a half "
                    "days of work is still lost (example figures). Dell "
                    "PowerProtect, which has its own twin in this collection, "
                    "is the other half: a locked vault, cut off from the "
                    "network, that makes sure a good copy survives. A vault "
                    "without detection keeps a safe copy you cannot find; "
                    "detection without a vault gives an answer about copies "
                    "the attacker may already have deleted."
                ),
                standard=(
                    "Recovery runs from snapshot 3 specifically. Not the "
                    "newest, which would reinstate the attack; not one from "
                    "three months ago chosen out of caution, which would "
                    "discard three months of legitimate work. The gap between "
                    "those is what precision is worth. It is not free: the "
                    "restored data is 134 hours old (illustrative), about five "
                    "and a half days of writes lost. The PowerProtect twin "
                    "covers the other half: an isolated vault behind an "
                    "operational air gap, immutably locked. Isolation without "
                    "detection leaves a safe copy you cannot identify; "
                    "detection without isolation leaves an answer about copies "
                    "the attacker may already have deleted."
                ),
                expert=(
                    "Restore from snapshot 3: not newest (reinfects), not "
                    "ancient (loses work). Achieved RPO 134 h, illustrative. "
                    "Pairs with the PowerProtect vault: "
                    "isolation keeps a copy, detection names it."
                ),
            ),
            camera=frame("verdict", "recovery", all_snaps[2]),
            region_ids=["array", "verdict", "recovery", *all_snaps[:3]],
            layer_reveal=_CONTENT,
            trace_cursor=7,
            duration_ms=28_000,
        ),
        TourStep(
            id="checked-baseline",
            title="A baseline someone can vouch for",
            script=L(
                novice=(
                    "Back to the whole picture. The volume is running again "
                    "from a copy whose health was proven rather than assumed. "
                    "The lasting change is the routine: content checking, which "
                    "used to be started by hand, now "
                    "runs on every new snapshot, so the gap between damage and "
                    "discovery shrinks from days to the length of one scan, and "
                    "that gap decides how much an attack costs. On this "
                    "illustrative timeline the answer arrived about 130 hours "
                    "in, and nearly all of that was the five days before anyone "
                    "had a reason to look. The incident page plays the same "
                    "timeline one step at a time."
                ),
                standard=(
                    "Back to the whole picture. The volume is restored from a "
                    "copy whose integrity was established rather than assumed, "
                    "and the next snapshot is taken against a baseline someone "
                    "can vouch for. The lasting change is routine: content "
                    "analysis, on demand until now, runs continuously on new "
                    "snapshots, "
                    "shrinking the interval between corruption and discovery "
                    "from days to one scan. On this illustrative timeline the "
                    "verdict arrived about 130 hours in, almost all of it "
                    "before anyone had reason to look. The incident page walks the "
                    "same trace step by step."
                ),
                expert=(
                    "Restored to a verified baseline; scanning moves from "
                    "on-demand to continuous, which cuts "
                    "detection latency to one scan. Verdict at ~130 h, "
                    "illustrative, mostly unseen dwell."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["array", "inspect", "classifier"],
            layer_reveal=_SURFACE,
            trace_cursor=8,
            duration_ms=26_000,
        ),
    ]

    return Tour(
        id="cyberdetect-tour",
        title="Finding the last clean copy",
        intro=L(
            novice=(
                "A guided walk through a ransomware incident and the analysis "
                "that resolves it, narrated beat by beat. Sit back and watch, "
                "or pause and click anything to look closer; the tour waits "
                "for you."
            ),
            standard=(
                "A narrated walk through an incident and the content analysis "
                "that resolves it. Watch it play, or pause and explore; Resume "
                "tour brings the camera back."
            ),
            expert="Narrated incident walk-through. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=_photos(),
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: DetectAnatomy) -> TourResponse:
    """The ``GET /api/tour`` payload: the tour plus the layer map and bounds."""
    return TourResponse(
        tour=build_tour(anatomy),
        layers=layer_map(anatomy),
        map_width=anatomy.width,
        map_height=anatomy.height,
    )


# Built once at import, like ANATOMY: importing the module registers the
# narration's reading-level variants, which tests/test_leveling.py relies on.
from .anatomy import ANATOMY  # noqa: E402  (after the builders it feeds)

TOUR_RESPONSE = build_response(ANATOMY)
