"""Detection anatomy data: Cyber Detect reading an array's snapshot
timeline, annotated.

Like the other twins, the layout is *data*, not code: regions placed in a
normalized coordinate space the frontend renders as SVG. Geometry is
stylized — favor a correct mental model over product accuracy (project
scope guardrail).

The organizing choice here is that the middle band is a **timeline**. Seven
snapshots run left to right, oldest to newest, and ``tests/test_anatomy.py``
pins that ordering. Every other twin's map is a diagram of where things
are; this one's is a diagram of *when* things were, because the product's
entire output is a point on that line.

Below the timeline sits the machinery that reads it — content inspection,
the trained classifier, the variant corpus — and below that the two things
the machinery produces: a verdict, and a recovery driven by it. The
vertical order is deliberate and tested: evidence above conclusion.
"""

from __future__ import annotations

from .leveling import L
from .models import DetectAnatomy, DetectRegion, Photo, SourceLink, Stat

# The only shipped visual is a self-contained schematic drawn for this
# project — not a Dell product image — with an honest credit line.
TIMELINE_ILLO = Photo(
    url="/cyberdetect-timeline.svg",
    caption=(
        "A snapshot timeline with an infection somewhere in it. Metadata "
        "analysis cannot say where — the attack was shaped to keep it "
        "quiet. Reading the bytes inside each snapshot can, and the answer "
        "it produces is a date: the last copy that is provably clean."
    ),
    credit="Schematic illustration by this project — not a Dell product image",
)

# Snapshots 1–3 predate the corruption; 4–7 contain it. The engine's
# verdict must land on 3, and tests check that it lands strictly before
# the first corrupted copy.
CLEAN_SNAPSHOTS = 3
TOTAL_SNAPSHOTS = 7

_SNAP_X = [2, 16, 30, 44, 58, 72, 86]


def _snapshot(idx: int, x0: float) -> DetectRegion:
    return DetectRegion(
        id=f"snap-{idx}",
        kind="snapshot",
        label=f"T-{TOTAL_SNAPSHOTS - idx}",
        x=x0, y=15, w=12, h=12,
        description=(
            f"Snapshot {idx} of {TOTAL_SNAPSHOTS} — a point-in-time copy "
            "of the volume, taken on the ordinary schedule long before "
            "anyone suspected anything. Every one of these looks equally "
            "trustworthy from the outside: same naming, same size, same "
            "metadata, taken by the same job. That uniformity is the "
            "problem the product exists to solve. Somewhere along this row "
            "is a boundary between copies that can be restored and copies "
            "that would reinstate the attack, and nothing visible from "
            "here tells you where it is. Only opening them and reading "
            "the contents does."
        ),
    )


ANATOMY = DetectAnatomy(
    id="cyberdetect",
    name="Dell Cyber Detect — content-based ransomware detection",
    vendor="Dell Technologies (content analysis by Index Engines)",
    form_factor="AI detection running against snapshots on primary storage",
    generation="Cyber Detect for PowerStore (Q3 2026) and PowerMax (2H 2026)",
    year=2026,
    width=100,
    height=58,
    overview=L(
        novice=(
            "Ransomware is malicious software that scrambles your files and "
            "demands payment to unscramble them. Most defences against it "
            "watch "
            "for suspicious behaviour — files being renamed in bulk, or "
            "changing much faster than usual. The trouble is that attackers "
            "learned what those alarms look for and simply stopped setting "
            "them "
            "off: they work slowly, keep the file names looking normal, and "
            "behave like an ordinary busy day. This product does something "
            "different. It opens the stored copies of your files and reads "
            "what "
            "is actually inside them, checking whether the contents still make "
            "sense. You can disguise how a file was written; you cannot "
            "disguise that it has become gibberish. Dell says this is right "
            "99.99% of the time. And the answer it gives is not a warning that "
            "something is wrong — by then you know. It is a date: this copy, "
            "from this moment, is the last one you can safely go back to. The "
            "row of boxes across the middle is a timeline of saved copies, "
            "because finding the right point on that line is the entire job."
        ),
        plain=(
            "Cyber Detect runs machine-learning analysis against saved "
            "snapshots on the storage array, examining the actual contents of "
            "files rather than reasoning about file names, activity patterns, "
            "or known malware fingerprints. Dell puts its accuracy at 99.99%, "
            "trained across thousands of ransomware variants. The distinction "
            "matters because the opponent adapts: conventional detection "
            "watches for what ransomware used to do — bulk renames, sudden "
            "changes, unusual activity — and attackers now avoid all of it by "
            "working slowly and imitating normal usage. What cannot be "
            "disguised is whether a file still means anything. This repo's "
            "PowerProtect twin covers the other half, an isolated vault, and "
            "leaves one question open that isolation cannot answer: recover "
            "from *which* copy? A vault full of faithfully preserved, "
            "thoroughly corrupted snapshots has protected nothing. So the "
            "output here is a date, not an alert, and the middle band is a "
            "timeline because that is what is being searched."
        ),
        standard=(
            "Dell Cyber Detect runs machine-learning analysis directly against "
            "snapshots on the array, inspecting data at the byte level rather "
            "than reasoning about metadata, file activity, or known "
            "signatures. "
            "Dell puts its accuracy at 99.99%, trained across thousands of "
            "ransomware variants. The reason that distinction matters is "
            "adversarial. Conventional detection watches for the things "
            "ransomware historically did — extensions changing, entropy "
            "spiking, mass renames, unusual I/O — and attackers have spent "
            "years learning to do none of them: encrypt slowly, preserve "
            "extensions, imitate the I/O profile of ordinary work. What cannot "
            "be disguised is whether a file is still intelligible. This repo's "
            "PowerProtect twin models the other half of the answer, the "
            "isolated vault, and leaves one question open that isolation alone "
            "cannot close: recover from *which* copy? A vault full of "
            "faithfully replicated, immutably locked, thoroughly corrupted "
            "snapshots has protected nothing. The output of this twin is "
            "therefore not an alert but a date. The middle band is drawn as a "
            "timeline because that is what the product actually navigates."
        ),
        technical=(
            "Content-based ransomware detection running against array-local "
            "snapshots: byte-level inspection rather than metadata, file "
            "activity, or signature matching. Dell states 99.99% accuracy "
            "across thousands of variants. The distinction is adversarial — "
            "behavioural detection keys on what ransomware historically did, "
            "and modern campaigns are shaped to avoid all of it: slow "
            "encryption, preserved extensions, I/O within the normal envelope. "
            "Corruption of the payload cannot be masked. The PowerProtect twin "
            "covers isolation and leaves the recovery-point question open; an "
            "immutable vault of corrupted snapshots protects nothing. Output "
            "is "
            "a recovery point, not an alert, and the middle band is a timeline "
            "accordingly."
        ),
        expert=(
            "Content-based detection on array-local snapshots — byte-level "
            "integrity rather than metadata, behaviour, or signatures; 99.99% "
            "claimed. Adversarially motivated: behavioural detection is evaded "
            "by construction. Payload corruption is not maskable. Complements "
            "the PowerProtect vault, which guarantees a copy survives but not "
            "which copy is clean. Deliverable is a recovery point; the middle "
            "band is a time axis."
        ),
    ),
    regions=[
        DetectRegion(
            id="array", kind="array", label="Production volume",
            x=2, y=2, w=96, h=9,
            description=(
                "The live volume, on a PowerStore or PowerMax array, being "
                "written to by applications that have no idea anything is "
                "wrong. The significant architectural point is that "
                "detection runs *here*, on primary storage, rather than in "
                "a separate scanning tier that data has to be shipped to. "
                "Local analysis means the earliest possible detection, "
                "because there is no replication lag to wait out before "
                "the question can even be asked — and in an incident, the "
                "gap between corruption and discovery is the number that "
                "decides how much you lose."
            ),
        ),
        *[_snapshot(i + 1, x) for i, x in enumerate(_SNAP_X)],
        DetectRegion(
            id="inspect", kind="inspect", label="Content inspection",
            x=2, y=31, w=30, h=11,
            description=(
                "The part that does the unglamorous work: opening files "
                "and databases inside each snapshot and reading the actual "
                "bytes. Not the file name, not the extension, not the "
                "modification time, not the rate at which blocks changed — "
                "the contents. This is expensive, which is why it is the "
                "longest stage in the trace, and the expense is precisely "
                "what is being bought. Metadata is a description of data "
                "that the attacker also controls; content is the data "
                "itself. An encrypted file can be made to look ordinary "
                "from every angle except the one that asks whether it "
                "still means anything."
            ),
        ),
        DetectRegion(
            id="classifier", kind="classifier", label="Trained classifier",
            x=35, y=31, w=30, h=11,
            description=(
                "The model that turns raw content into a judgement. It "
                "scores what the inspection found against the statistical "
                "fingerprints of intact data versus corrupted data — is "
                "this still a valid database page, a well-formed document, "
                "a coherent record? Dell states 99.99% accuracy, and it is "
                "worth being clear about which error matters. A false "
                "positive costs an unnecessary investigation. A false "
                "negative certifies an infected snapshot as clean, and "
                "someone restores from it. Detection products are judged "
                "on the second number, which is why the training corpus "
                "next door is part of the product rather than a footnote."
            ),
        ),
        DetectRegion(
            id="models", kind="models", label="Variant corpus",
            x=68, y=31, w=30, h=11,
            description=(
                "Thousands of ransomware variants, analysed so the "
                "classifier knows what their damage looks like from the "
                "inside. This is not a signature database — signatures "
                "identify the malware, and by the time you are reading "
                "snapshots the malware is not what you are looking at; you "
                "are looking at what it did. The corpus teaches the model "
                "the shapes corruption takes, which generalizes to "
                "variants nobody has catalogued, because the number of "
                "ways to encrypt a file is far smaller than the number of "
                "programs that do it."
            ),
        ),
        DetectRegion(
            id="verdict", kind="verdict", label="Forensic report — the date",
            x=2, y=45, w=46, h=10,
            description=(
                "The deliverable, and the thing that distinguishes this "
                "from an alerting product. The output is not 'you have "
                "ransomware' — by the point anyone is running this, that "
                "is known. The output is 'snapshot T-4, taken at 03:00 on "
                "Tuesday, is the last copy whose contents are provably "
                "intact', with the evidence attached. That sentence is "
                "what a recovery decision actually requires, and producing "
                "it is why the inspection had to read every byte rather "
                "than sampling or inferring. It is also the reason a "
                "verdict can never be issued before the evidence exists, "
                "which the geometry of this diagram and the engine's tests "
                "both insist on."
            ),
        ),
        DetectRegion(
            id="recovery", kind="recovery", label="Recovery from the named copy",
            x=51, y=45, w=47, h=10,
            description=(
                "Restoring from the specific snapshot the verdict "
                "identified — not the most recent one, which is corrupt, "
                "and not one from three months ago chosen out of caution, "
                "which would discard three months of legitimate work. The "
                "value of a precise answer is measured in exactly that "
                "gap. This repo's PowerProtect twin covers where a "
                "guaranteed-reachable copy comes from: an isolated vault "
                "behind an operational air gap, immutably locked. The two "
                "halves need each other. Isolation without detection gives "
                "you a safe copy you cannot identify; detection without "
                "isolation gives you an answer about copies the attacker "
                "may have already deleted."
            ),
        ),
    ],
    stats=[
        Stat(label="Method", value="Byte-level content analysis, not metadata"),
        Stat(label="Accuracy", value="99.99% (Dell figure)"),
        Stat(label="Training", value="Thousands of ransomware variants"),
        Stat(label="Where it runs", value="On the array, against local snapshots"),
        Stat(label="Output", value="The last provably clean copy, by name"),
        Stat(label="Technology", value="Index Engines content analysis"),
        Stat(label="PowerStore", value="Available Q3 2026"),
        Stat(label="PowerMax", value="Available 2H 2026"),
    ],
    photo=TIMELINE_ILLO,
    sources=[
        SourceLink(
            label="Dell Cyber Detect — product page",
            url="https://www.dell.com/en-us/shop/storage-servers-and-networking-for-business/sf/cyber-detect",
        ),
        SourceLink(
            label="Dell — faster, more confident recovery starts on primary storage",
            url="https://www.dell.com/en-us/blog/faster-more-confident-recovery-starts-on-primary-storage/",
        ),
        SourceLink(
            label="Dell Technologies reimagines the modern data center for the AI era (May 2026)",
            url="https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2026~05~dell-technologies-reimagines-the-modern-data-center-for-the-ai-era.htm",
        ),
        SourceLink(
            label="Dell PowerMax cybersecurity — security and compliance",
            url="https://infohub.delltechnologies.com/en-us/l/dell-powermax-cybersecurity-3/security-and-compliance-9/",
        ),
    ],
)
