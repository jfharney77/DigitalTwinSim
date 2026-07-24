"""Component catalog: what you actually choose when you build content-based
ransomware detection into a storage estate, as backend data.

Written for a technically skilled reader new to cyber recovery: dwell time,
entropy, indicators of compromise, false negatives, immutability, RPO, and
forensic reporting are all spelled out on first use. Categories map to the
detection-map regions in ``anatomy.py`` via ``region_ids``, and
``tests/test_catalog.py`` enforces that every id resolves.

The first category is where detection *runs*, not what it detects, because
that placement decision is the one that determines how early an answer is
possible — and in an incident, earliness is most of the value.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="placement",
        name="Where detection runs",
        blurb=(
            "On the primary array, in the backup appliance, or in an "
            "isolated vault — the choice that sets how early an answer is "
            "possible."
        ),
        limits="Cyber Detect for PowerStore (Q3 2026) and PowerMax (2H 2026)",
        region_ids=["array"],
        options=[
            CatalogOption(
                id="primary-array",
                name="On primary storage",
                summary=(
                    "Analysis runs against snapshots on the production "
                    "array itself."
                ),
                details=(
                    "The earliest place the question can be asked. "
                    "Snapshots are already on the array, so there is no "
                    "replication lag to wait out before analysis can "
                    "begin — and the interval between corruption and "
                    "discovery is the number that decides how much an "
                    "incident costs. The trade is that the analysis "
                    "consumes array resources, and that anything running "
                    "on production is, in principle, reachable by an "
                    "attacker who has production. It is a detection "
                    "control, not a last line of defence, and should not "
                    "be mistaken for one."
                ),
            ),
            CatalogOption(
                id="backup-appliance",
                name="On the backup appliance",
                summary=(
                    "Analysis against backup copies on Data Domain, away "
                    "from production load."
                ),
                details=(
                    "Scanning where the backups land keeps the work off "
                    "the production array and covers data from systems "
                    "that never had array snapshots. It answers later than "
                    "primary-side analysis, by however long the backup "
                    "window is, which in practice means the difference "
                    "between discovering something in hours and "
                    "discovering it the next day."
                ),
            ),
            CatalogOption(
                id="vault-side",
                name="Inside the isolated vault",
                summary=(
                    "Analysis behind the air gap, on copies the attacker "
                    "provably cannot have touched."
                ),
                details=(
                    "The most trustworthy result and the latest one. "
                    "Because the vault is unreachable from production, a "
                    "verdict issued there cannot have been influenced by "
                    "an attacker who owns the estate — which matters, "
                    "because a sufficiently patient adversary attacks the "
                    "detection before attacking the data. This repo's "
                    "PowerProtect twin models this environment in full, "
                    "including the CyberSense scan that is the same "
                    "content-analysis technology applied vault-side. Best "
                    "practice is both: early answers on the array, "
                    "authoritative ones in the vault."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="method",
        name="Detection method",
        blurb=(
            "What the analysis actually looks at — and why the answer is "
            "'the data itself'."
        ),
        limits="Byte-level content analysis; 99.99% accuracy (Dell figure)",
        region_ids=["inspect"],
        options=[
            CatalogOption(
                id="content-analysis",
                name="Content analysis",
                summary=(
                    "Open the files and database pages; read the actual "
                    "bytes."
                ),
                details=(
                    "The method this twin is about. Rather than reasoning "
                    "from descriptions of data, the analysis opens what is "
                    "stored and examines whether it is still intelligible: "
                    "is this a valid database page, a well-formed "
                    "document, a coherent record? It is expensive, and "
                    "that expense is the point. Metadata is a description "
                    "the attacker also controls; content is not. A file "
                    "can be disguised from every angle except the one "
                    "asking whether it still means anything."
                ),
            ),
            CatalogOption(
                id="behavioural",
                name="Behavioural and metadata analysis",
                summary=(
                    "Extension changes, entropy spikes, mass renames, "
                    "unusual I/O rates."
                ),
                details=(
                    "The conventional approach, and worth keeping — it is "
                    "cheap, it runs continuously, and it catches the loud "
                    "attacks, which are still most of them. What it cannot "
                    "do is catch an attack designed against it, and "
                    "designing against it is not difficult: encrypt "
                    "slowly, preserve extensions, raise entropy "
                    "gradually, imitate the I/O profile of ordinary work. "
                    "Every one of those choices costs the attacker time "
                    "and they make it anyway. Treat this as a filter, not "
                    "as an assurance."
                ),
            ),
            CatalogOption(
                id="signatures",
                name="Signature matching",
                summary=(
                    "Identify known malware by its fingerprint."
                ),
                details=(
                    "Essential at the endpoint and largely beside the "
                    "point at the storage layer, for a simple reason: by "
                    "the time you are examining snapshots, the malware is "
                    "not what you are looking at. You are looking at what "
                    "it did. Signatures also only recognize what has been "
                    "catalogued, whereas the shapes that corruption takes "
                    "generalize — there are far fewer ways to wreck a file "
                    "than there are programs that do it."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="model",
        name="The trained model",
        blurb=(
            "What turns raw content into a judgement, and how it was "
            "taught."
        ),
        limits="Trained across thousands of ransomware variants",
        region_ids=["classifier", "models"],
        options=[
            CatalogOption(
                id="variant-corpus",
                name="Variant corpus training",
                summary=(
                    "Thousands of ransomware families, analysed for what "
                    "their damage looks like from the inside."
                ),
                details=(
                    "The corpus teaches the classifier the statistical "
                    "shapes corruption takes rather than the identities of "
                    "the programs causing it, which is what lets it "
                    "recognize variants nobody has catalogued. Keeping it "
                    "current is a vendor responsibility and a real one: a "
                    "corpus is a perishable asset, and the honest question "
                    "to ask a vendor is how often it is refreshed and what "
                    "happens to accuracy on families added after your "
                    "deployment shipped."
                ),
            ),
            CatalogOption(
                id="accuracy",
                name="Accuracy and error budget",
                summary=(
                    "99.99% — but the two error types are not equally "
                    "expensive."
                ),
                details=(
                    "A false positive costs an unnecessary investigation "
                    "and some credibility. A false negative certifies a "
                    "corrupted snapshot as clean, and somebody restores "
                    "from it — reinstating the attack from a copy the "
                    "product vouched for. Those are not comparable "
                    "outcomes, and a detection product should be evaluated "
                    "almost entirely on the second. When comparing "
                    "vendors, the useful question is not the headline "
                    "accuracy figure but which error the figure is "
                    "tuned against."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="output",
        name="What the analysis produces",
        blurb=(
            "The difference between an alert and a usable recovery "
            "decision."
        ),
        limits="Forensic report naming the last provably clean copy",
        region_ids=["verdict"],
        options=[
            CatalogOption(
                id="clean-copy",
                name="Last known clean copy",
                summary=(
                    "A named snapshot and a timestamp, with the evidence "
                    "attached."
                ),
                details=(
                    "The deliverable that matters. During an incident "
                    "nobody needs to be told they are under attack; they "
                    "need to know which copy to restore. Without that, the "
                    "options are the newest copy — which reinstates the "
                    "attack — or something far enough back to feel safe, "
                    "which discards weeks of legitimate work. The gap "
                    "between those two is precisely what a precise answer "
                    "is worth, and it is usually the largest single number "
                    "in the incident's cost."
                ),
            ),
            CatalogOption(
                id="forensics",
                name="Forensic detail and scope",
                summary=(
                    "Which files, which systems, and when it started."
                ),
                details=(
                    "Beyond the recovery point, the analysis establishes "
                    "the shape of the incident: which data was touched, "
                    "how far back the earliest corruption goes, and "
                    "therefore how long the attacker had access before "
                    "acting — the dwell time. That last figure is what "
                    "regulators, insurers, and the eventual post-incident "
                    "review will all ask for first, and reconstructing it "
                    "after the fact without content evidence is close to "
                    "guesswork."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="snapshots",
        name="Snapshot and retention policy",
        blurb=(
            "The timeline the analysis navigates — and how far back it "
            "goes."
        ),
        limits="Frequency sets granularity; retention sets how far back you can go",
        region_ids=["snap-1", "snap-4", "snap-7"],
        options=[
            CatalogOption(
                id="frequency",
                name="Snapshot frequency",
                summary=(
                    "How much work you lose between the last clean copy "
                    "and the corruption."
                ),
                details=(
                    "Snapshot interval sets the granularity of any "
                    "recovery point — this is the recovery point "
                    "objective, or RPO, in its most literal form. Hourly "
                    "snapshots mean at most an hour of work sits between "
                    "the clean copy and the first corrupt one. Daily "
                    "snapshots mean a day. Since content analysis can only "
                    "name a copy that exists, frequency is a limit on how "
                    "good the answer can possibly be, however good the "
                    "detection is."
                ),
            ),
            CatalogOption(
                id="retention",
                name="Retention depth",
                summary=(
                    "Whether a clean copy still exists once dwell time is "
                    "measured in weeks."
                ),
                details=(
                    "The uncomfortable arithmetic of long dwell times: if "
                    "an attacker was inside for six weeks and retention is "
                    "four, every surviving copy is corrupt and there is "
                    "nothing for the analysis to find. Retention depth "
                    "should be set against realistic dwell times rather "
                    "than against storage cost, and realistic dwell times "
                    "are considerably longer than most estates assume."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="immutability",
        name="Immutability and isolation",
        blurb=(
            "Making sure the copy the analysis names still exists when you "
            "reach for it."
        ),
        limits="Retention Lock, operational air gap, isolated vault",
        region_ids=["recovery"],
        options=[
            CatalogOption(
                id="retention-lock",
                name="Immutable snapshots",
                summary=(
                    "Copies that cannot be deleted or altered, even with "
                    "administrative credentials."
                ),
                details=(
                    "A well-run attack deletes the backups before "
                    "encrypting anything, using the administrative access "
                    "it already has — which is why immutability is not a "
                    "compliance feature but a survival one. Locked copies "
                    "cannot be removed within their retention period by "
                    "anybody, including whoever holds the credentials. "
                    "Detection and immutability answer different halves of "
                    "the same problem: one tells you which copy, the other "
                    "guarantees the copy is still there."
                ),
            ),
            CatalogOption(
                id="air-gap",
                name="Operational air gap",
                summary=(
                    "A vault reachable only from the vault side, and only "
                    "briefly."
                ),
                details=(
                    "The isolated vault this repo's PowerProtect twin "
                    "models in full: a copy in an environment with no "
                    "route in from production, where the link opens from "
                    "the vault side on a schedule and closes again. It is "
                    "the strongest guarantee available that a copy exists, "
                    "and it says nothing whatsoever about whether that "
                    "copy is clean — which is the gap this product fills."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="estate",
        name="Estate coverage",
        blurb=(
            "Which systems the analysis reaches, and what happens to the "
            "ones it does not."
        ),
        limits="PowerStore, PowerMax, Data Domain, PowerScale",
        region_ids=["array"],
        options=[
            CatalogOption(
                id="block",
                name="Block storage — PowerStore and PowerMax",
                summary=(
                    "Detection on the arrays serving databases and virtual "
                    "machines."
                ),
                details=(
                    "Both twinned separately in this repo. Block arrays "
                    "hold the systems whose corruption is hardest to "
                    "notice and most expensive to restore incorrectly — "
                    "databases, where a partially-encrypted page can sit "
                    "undetected for a long time and then surface as a "
                    "puzzling application fault rather than as an "
                    "incident."
                ),
            ),
            CatalogOption(
                id="file-object",
                name="File and object — PowerScale and beyond",
                summary=(
                    "Unstructured data, where most of the volume and most "
                    "of the exposure lives."
                ),
                details=(
                    "Unstructured file data is where ransomware usually "
                    "starts, because it is the largest surface and the "
                    "least closely watched. It is also where content "
                    "analysis works most naturally, since documents and "
                    "images have well-understood internal structure that "
                    "either parses or does not."
                ),
            ),
            CatalogOption(
                id="observability",
                name="Alerting and AIOps integration",
                summary=(
                    "Getting the verdict in front of the right people "
                    "quickly."
                ),
                details=(
                    "A finding that sits in a console nobody watches is "
                    "not a control. Integration with the estate's "
                    "observability and ticketing — this repo's CloudIQ "
                    "twin covers the AIOps side — is what turns an "
                    "analysis result into a response. During an incident "
                    "the useful measure of a detection product includes "
                    "how fast its answer reached a human who could act on "
                    "it."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="operations",
        name="Running it",
        blurb=(
            "Scheduling, cost, and the rehearsal that decides whether any "
            "of this works."
        ),
        limits="Continuous or scheduled scanning; resource cost on the array",
        region_ids=["inspect", "recovery"],
        options=[
            CatalogOption(
                id="scanning-schedule",
                name="Scan scheduling",
                summary=(
                    "How often content analysis runs, and what it costs to "
                    "run it."
                ),
                details=(
                    "Continuous analysis of new snapshots shrinks the "
                    "interval between corruption and discovery to the "
                    "length of one scan, which is the whole game — in the "
                    "incident this twin traces, five of the six days were "
                    "spent before anyone had a reason to look. Reading "
                    "every byte is not free, so the schedule is a genuine "
                    "trade between detection latency and array resources, "
                    "and it should be made deliberately rather than left "
                    "at a default."
                ),
            ),
            CatalogOption(
                id="rehearsal",
                name="Recovery rehearsal",
                summary=(
                    "Practising the restore before you need it."
                ),
                details=(
                    "The step that is always agreed to and rarely done. A "
                    "recovery plan that has never been executed is a "
                    "hypothesis, and incidents are a poor time to test "
                    "one. Rehearsal also surfaces the unglamorous "
                    "blockers — who has the authority to declare an "
                    "incident, who can approve a restore, whether the "
                    "runbook references a system that was decommissioned "
                    "last year."
                ),
            ),
        ],
    ),
]
