"""Use cases: three deployments of content-based detection, as backend data.

Each is a build sheet whose category and option ids must resolve against
``catalog.py`` — enforced in ``tests/test_catalog.py``. The narratives are
written for a reader who understands storage but has not run an incident.

All three turn on the same distinction from different angles: knowing you
were attacked is not the same as knowing what to restore. What differs is
who pays for the gap — a business losing days of work, a regulator asking
when it started, or an insurer asking to see the evidence.
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="manufacturer-recovery",
        title="A manufacturer choosing between last night and last month",
        summary=(
            "Production systems encrypted over six days. Without a verdict "
            "the only safe restore point is weeks back; with one it is "
            "Tuesday morning."
        ),
        narrative=[
            "The incident is discovered on a Friday, when an application "
            "starts failing on records it cannot parse. By then the "
            "encryption campaign has been running for most of a week, "
            "carefully enough that nothing tripped. The immediate question "
            "is not who did it or how — those matter later. The question "
            "is which snapshot to restore, and every snapshot on the array "
            "looks identical from the outside.",
            "Without content evidence there are two options and both are "
            "bad. Restore the most recent copy and the corruption comes "
            "back with it, possibly not obviously, possibly surfacing "
            "weeks later as another puzzling application fault. Or go back "
            "far enough to feel safe — a month, say — and discard a "
            "month of orders, production records, and quality data that "
            "were perfectly fine. Organizations routinely choose the "
            "second, and the cost of that choice is usually the largest "
            "single number in the incident.",
            "Content analysis collapses the choice into a fact. Reading "
            "the bytes inside every snapshot establishes that Tuesday "
            "03:00 is the last copy whose contents parse, and the restore "
            "runs from there. The lasting change is not the recovery: it "
            "is that scanning now runs continuously against new snapshots, "
            "so the next incident is discovered in the length of a scan "
            "rather than in the length of a week.",
        ],
        config=[
            UseCaseItem(
                category_id="placement", option_id="primary-array", qty=1,
                rationale=(
                    "Detection on the array asks the question earliest — "
                    "no replication lag between corruption and the "
                    "possibility of noticing."
                ),
            ),
            UseCaseItem(
                category_id="method", option_id="content-analysis", qty=1,
                rationale=(
                    "The attack was shaped to keep behavioural detection "
                    "silent, and it succeeded for six days."
                ),
            ),
            UseCaseItem(
                category_id="output", option_id="clean-copy", qty=1,
                rationale=(
                    "The deliverable that makes the restore decision "
                    "possible: a named snapshot, not an alert."
                ),
            ),
            UseCaseItem(
                category_id="snapshots", option_id="frequency", qty=1,
                rationale=(
                    "Snapshot interval is a hard ceiling on how good the "
                    "answer can be — the analysis can only name a copy "
                    "that exists."
                ),
            ),
            UseCaseItem(
                category_id="immutability", option_id="retention-lock", qty=1,
                rationale=(
                    "A competent attacker deletes backups first, using "
                    "credentials they already hold."
                ),
            ),
            UseCaseItem(
                category_id="estate", option_id="block", qty=1,
                rationale=(
                    "Database corruption is the hardest to see and the "
                    "most expensive to restore wrongly."
                ),
            ),
            UseCaseItem(
                category_id="operations", option_id="scanning-schedule", qty=1,
                rationale=(
                    "Continuous scanning is what turns six days of "
                    "undetected corruption into one scan interval."
                ),
            ),
            UseCaseItem(
                category_id="operations", option_id="rehearsal", qty=1,
                rationale=(
                    "A restore plan nobody has executed is a hypothesis, "
                    "and an incident is a poor time to test one."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Restore point", value="Tuesday 03:00, established"),
            Stat(label="Work discarded", value="Hours, not weeks"),
            Stat(label="Metadata alerts during the attack", value="Zero"),
            Stat(label="Detection interval afterwards", value="One scan"),
        ],
    ),
    UseCase(
        id="regulated-evidence",
        title="A bank that has to prove when it started",
        summary=(
            "Regulators and insurers ask for dwell time and scope. "
            "Reconstructing those after the fact without content evidence "
            "is guesswork."
        ),
        narrative=[
            "In a regulated industry the recovery is only half the "
            "obligation. Within days there will be questions from a "
            "supervisor, an insurer, and eventually a post-incident "
            "review, and they converge on the same three: when did the "
            "attacker get in, what did they touch, and how do you know. "
            "Answers assembled from logs and inference are weak, "
            "particularly when the attacker had administrative access and "
            "the logs were reachable.",
            "Content analysis produces evidence rather than inference. "
            "Because every snapshot has been read, the earliest corrupted "
            "copy is a fact with a timestamp, which fixes the start of the "
            "damage; the set of affected files fixes the scope; and the "
            "gap between intrusion and first corruption gives the dwell "
            "time that everyone will ask about first. None of this depends "
            "on logs the attacker could have edited.",
            "This is also the configuration where vault-side analysis "
            "earns its place. A verdict issued inside an isolated vault "
            "cannot have been influenced by an adversary who owns "
            "production — which matters more than it sounds, because a "
            "patient attacker attacks the detection before attacking the "
            "data. The practical answer is both: fast answers on the "
            "array, authoritative ones behind the air gap.",
        ],
        config=[
            UseCaseItem(
                category_id="placement", option_id="vault-side", qty=1,
                rationale=(
                    "A verdict from behind the air gap cannot have been "
                    "influenced by an attacker who holds production."
                ),
            ),
            UseCaseItem(
                category_id="placement", option_id="primary-array", qty=1,
                rationale=(
                    "Run both: the array answers fastest, the vault "
                    "answers most credibly."
                ),
            ),
            UseCaseItem(
                category_id="output", option_id="forensics", qty=1,
                rationale=(
                    "Dwell time and scope are the first things a "
                    "supervisor asks for, and the hardest to reconstruct "
                    "later."
                ),
            ),
            UseCaseItem(
                category_id="immutability", option_id="air-gap", qty=1,
                rationale=(
                    "The strongest guarantee a copy still exists — which "
                    "says nothing about whether it is clean, hence the "
                    "analysis."
                ),
            ),
            UseCaseItem(
                category_id="snapshots", option_id="retention", qty=1,
                rationale=(
                    "If dwell time exceeds retention, every surviving copy "
                    "is corrupt and there is nothing to find."
                ),
            ),
            UseCaseItem(
                category_id="model", option_id="accuracy", qty=1,
                rationale=(
                    "In a regulated restore, a false negative is a "
                    "certified-clean copy that reinstates the attack."
                ),
            ),
            UseCaseItem(
                category_id="estate", option_id="file-object", qty=1,
                rationale=(
                    "Unstructured data is the largest surface and the "
                    "least watched — usually where it starts."
                ),
            ),
            UseCaseItem(
                category_id="method", option_id="behavioural", qty=1,
                rationale=(
                    "Keep it as a cheap continuous filter; it catches the "
                    "loud attacks, which are still most of them."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Dwell time", value="Established from content, not logs"),
            Stat(label="Scope", value="Files and systems, enumerated"),
            Stat(label="Verdict provenance", value="Issued behind the air gap"),
            Stat(label="Evidence", value="Attached to the recovery point"),
        ],
    ),
    UseCase(
        id="health-continuity",
        title="A hospital that cannot go back a month",
        summary=(
            "Clinical systems where the over-cautious restore is not "
            "available, because a month of records is not a cost — it is a "
            "patient-safety event."
        ),
        narrative=[
            "Most organizations, faced with an unresolvable question about "
            "which copy is clean, take the safe option and restore from "
            "far enough back that nobody can argue. Clinical systems "
            "cannot. A month of missing results, medication records, and "
            "notes is not an accounting cost to be written off; it is a "
            "direct risk to patients, and the systems downstream will "
            "carry the inconsistency for years.",
            "So the precision of the answer is doing something different "
            "here from what it does elsewhere. In the manufacturer's case "
            "it saves money. Here it is the difference between a recovery "
            "that is clinically acceptable and one that is not, which "
            "means the detection is not a cost-optimization control at "
            "all — it is what makes recovery an option.",
            "The configuration follows from that. Snapshot frequency has "
            "to be high, because the interval sets how much is lost even "
            "with a perfect answer. Retention has to be deep enough for "
            "realistic dwell times rather than for a storage budget. And "
            "the finding has to reach a human quickly, because a verdict "
            "sitting in an unwatched console is not a control — this repo's "
            "PowerProtect twin covers the vault side of the same hospital "
            "scenario, and the two are designed to be read together.",
        ],
        config=[
            UseCaseItem(
                category_id="placement", option_id="primary-array", qty=1,
                rationale=(
                    "Clinical systems need the earliest possible answer; "
                    "waiting for a backup window is waiting too long."
                ),
            ),
            UseCaseItem(
                category_id="snapshots", option_id="frequency", qty=1,
                rationale=(
                    "Frequent snapshots bound the loss even when the "
                    "detection is perfect."
                ),
            ),
            UseCaseItem(
                category_id="snapshots", option_id="retention", qty=1,
                rationale=(
                    "Retention shorter than realistic dwell time means "
                    "there is no clean copy left to name."
                ),
            ),
            UseCaseItem(
                category_id="output", option_id="clean-copy", qty=1,
                rationale=(
                    "The over-cautious month-old restore is not available "
                    "here, so precision is what makes recovery possible at "
                    "all."
                ),
            ),
            UseCaseItem(
                category_id="model", option_id="variant-corpus", qty=1,
                rationale=(
                    "Generalizing to uncatalogued variants matters when "
                    "the sector is actively targeted."
                ),
            ),
            UseCaseItem(
                category_id="immutability", option_id="retention-lock", qty=1,
                rationale=(
                    "Immutability guarantees the named copy still exists "
                    "when it is reached for."
                ),
            ),
            UseCaseItem(
                category_id="estate", option_id="observability", qty=1,
                rationale=(
                    "A verdict in an unwatched console is not a control; "
                    "it has to reach someone who can act."
                ),
            ),
            UseCaseItem(
                category_id="operations", option_id="rehearsal", qty=1,
                rationale=(
                    "Rehearsal surfaces the unglamorous blockers — who "
                    "may declare an incident, who may approve a restore."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Acceptable data loss", value="Hours, bounded by snapshot interval"),
            Stat(label="Month-old restore", value="Not a clinically viable option"),
            Stat(label="Detection", value="Continuous, content-based"),
            Stat(label="Pairs with", value="The isolated vault (PowerProtect twin)"),
        ],
    ),
]
