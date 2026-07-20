"""Worked use cases: what PowerProtect + Cyber Recovery actually gets
deployed for.

Each use case is a narrative plus a build sheet whose category/option ids
must resolve against catalog.py (enforced in tests/test_catalog.py).
Written for a technically skilled reader new to data protection.
Quantities count the unit named (appliances, sites, vaults).
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="hospital",
        title="Hospital ransomware vault",
        summary=(
            "A regional health system puts its EHR and imaging estate "
            "behind an all-flash Data Domain and a Cyber Recovery vault — "
            "because for a hospital, restore time is measured in diverted "
            "ambulances."
        ),
        narrative=[
            (
                "The workload: a regional health system — electronic "
                "health records, PACS imaging, pharmacy, scheduling. "
                "Healthcare is ransomware's favorite sector for a grim "
                "reason: the victim cannot wait. Every hour of EHR "
                "downtime is paper charting, cancelled procedures, and "
                "ambulances diverted to other hospitals, so the pressure "
                "to pay is enormous — unless recovery is fast enough to "
                "make the ransom the slower option."
            ),
            (
                "The design: an all-flash production Data Domain takes "
                "nightly PPDM backups of the whole estate (the EHR "
                "database through application-aware agents, imaging as "
                "file workloads), and a Cyber Recovery vault syncs daily "
                "through the operational air gap with Retention Lock "
                "Compliance on every copy — HIPAA's integrity "
                "requirements and the vault's immutability point the same "
                "direction. CyberSense scans every vaulted copy, tuned "
                "attention on the database: page-level corruption in an "
                "EHR is exactly the signature it exists to catch."
            ),
            (
                "The metric that justified the all-flash premium is the "
                "restore: at up to 4× disk speed, the EHR database comes "
                "back in hours. The clean room is rehearsed quarterly "
                "with the incident-response retainer team, so the 3 a.m. "
                "version of the recovery is a checklist someone has "
                "already run four times this year."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="appliance", option_id="app-allflash", qty=2,
                rationale=(
                    "One for production, one in the vault — restore speed "
                    "is the point, and the vault restores too."
                ),
            ),
            UseCaseItem(
                category_id="backup", option_id="bk-ppdm", qty=1,
                rationale="Application-aware EHR and imaging policies, one control plane.",
            ),
            UseCaseItem(
                category_id="cyberrecovery", option_id="cr-software", qty=1,
                rationale="Automates gap, sync, lock, and the recovery workflow.",
            ),
            UseCaseItem(
                category_id="immutability", option_id="imm-retlock", qty=1,
                rationale="Compliance-mode WORM aligns with HIPAA integrity duties.",
            ),
            UseCaseItem(
                category_id="analytics", option_id="cs-analytics", qty=1,
                rationale="Database-corruption signatures decide which copy is clean.",
            ),
            UseCaseItem(
                category_id="cyberrecovery", option_id="cr-cleanroom", qty=1,
                rationale="Restores rehearsed quarterly, off any attacker-touched network.",
            ),
            UseCaseItem(
                category_id="services", option_id="svc-response", qty=1,
                rationale="A practiced team on call — the hospital's staff will be busy.",
            ),
        ],
        outcomes=[
            Stat(label="EHR restore target", value="Hours, not weeks"),
            Stat(label="Vault cadence", value="Daily sync, minutes of gap exposure"),
            Stat(label="Immutability", value="Retention Lock Compliance on every copy"),
            Stat(label="Rehearsal", value="Quarterly clean-room restore drills"),
        ],
    ),
    UseCase(
        id="bank",
        title="Bank compliance & cyber resilience",
        summary=(
            "A mid-size bank pairs SEC-grade immutable retention with a "
            "vault that satisfies its regulator's operational-resilience "
            "rules — one architecture answering two mandates."
        ),
        narrative=[
            (
                "The workload: core banking, trading records, and the "
                "communications archives regulators care about. Two "
                "mandates converge: records-retention rules (SEC 17a-4 "
                "class) demand provably unalterable storage for years, and "
                "operational-resilience regulation (DORA in Europe, "
                "FFIEC guidance in the US) demands demonstrated ability "
                "to recover core services from destructive cyber attack. "
                "Historically those were two systems; here they are one "
                "architecture."
            ),
            (
                "The design: Retention Lock Compliance mode is the load-"
                "bearing choice — dual-authorization setup, a separated "
                "security-officer role, and no early-unlock path for "
                "admins or for Dell, which is what lets the WORM copies "
                "stand in for optical-era compliance storage. The vault "
                "doubles as the resilience answer: daily air-gapped "
                "copies of the core-banking estate, CyberSense verdicts "
                "as the evidence trail, and clean-room recovery exercises "
                "whose reports go straight into the regulator's annual "
                "resilience testing file."
            ),
            (
                "Long-term retention rides Cloud Tier: the seven-year "
                "tail ages to object storage still deduplicated, keeping "
                "the appliances sized for hot restore points rather than "
                "archives. Forensics matter more than usual — after any "
                "incident a bank answers to its regulator in detail, and "
                "CyberSense's per-copy timeline of what corrupted when is "
                "the difference between a report and a shrug."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="appliance", option_id="app-dd9910", qty=2,
                rationale="Petabyte-class estates; production and vault sized alike.",
            ),
            UseCaseItem(
                category_id="immutability", option_id="imm-retlock", qty=1,
                rationale="Compliance mode is the SEC-grade WORM the records rules demand.",
            ),
            UseCaseItem(
                category_id="immutability", option_id="imm-hardening", qty=1,
                rationale="Separated duties + dual authorization for the audit narrative.",
            ),
            UseCaseItem(
                category_id="cyberrecovery", option_id="cr-airgap", qty=1,
                rationale="Daily vault points evidence the resilience mandate.",
            ),
            UseCaseItem(
                category_id="analytics", option_id="cs-forensics", qty=1,
                rationale="Per-copy corruption timelines for regulator-grade reporting.",
            ),
            UseCaseItem(
                category_id="replication", option_id="rep-cloudtier", qty=1,
                rationale="Seven-year retention tail ages to object storage, still deduped.",
            ),
            UseCaseItem(
                category_id="services", option_id="svc-design", qty=1,
                rationale="Vault isolation and runbooks built to survive an audit.",
            ),
        ],
        outcomes=[
            Stat(label="Records compliance", value="SEC 17a-4-class WORM retention"),
            Stat(label="Resilience evidence", value="Drilled recoveries + scan verdicts"),
            Stat(label="Retention economics", value="Hot points on-array, tail in cloud"),
            Stat(label="Forensics", value="Attack timeline per vaulted copy"),
        ],
    ),
    UseCase(
        id="robo",
        title="Branch offices into one vault",
        summary=(
            "Forty retail branches each run a compact DD3410; everything "
            "replicates into one core Data Domain and one shared Cyber "
            "Recovery vault — uniform recovery for a very non-uniform "
            "estate."
        ),
        narrative=[
            (
                "The workload: a retailer with forty branches, each with "
                "a small local footprint — point-of-sale databases, file "
                "servers, a handful of VMs. Nobody staffs backup at a "
                "branch, WAN links are modest, and yet a ransomware crew "
                "that lands in one store's network expects to reach the "
                "whole estate. The classic ROBO (remote office / branch "
                "office) problem, with a modern threat model."
            ),
            (
                "The design: a DD3410 in each branch — small enough for a "
                "closet, 8 TBu growing in place to 32 as the store's data "
                "does, running the same DDOS as the data center. Local "
                "backups restore locally at LAN speed (a dead POS server "
                "is back before lunch), and MTree replication forwards "
                "only unique segments over the WAN to the core appliance "
                "— after cross-branch dedupe, forty nearly-identical "
                "store images cost barely more than one. The core then "
                "vaults into a single shared Cyber Recovery vault: one "
                "air gap, one CyberSense, one clean room serving the "
                "whole chain."
            ),
            (
                "The operational win is uniformity: every branch, the "
                "core, and the vault speak one filesystem and one "
                "catalog, so the recovery runbook for store #7 is the "
                "runbook for store #34. AIOps observability watches the "
                "fleet — a branch whose dedupe ratio suddenly collapses "
                "is a branch whose data stopped looking like data, which "
                "is how one store's incident gets caught before it "
                "becomes the chain's."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="appliance", option_id="app-dd3410", qty=40,
                rationale="One compact appliance per branch; grow-in-place by license.",
            ),
            UseCaseItem(
                category_id="appliance", option_id="app-allflash", qty=2,
                rationale="Core target + shared vault; restores for any branch run fast.",
            ),
            UseCaseItem(
                category_id="ddos", option_id="ddos-boost", qty=1,
                rationale="Client-side dedupe keeps branch WAN traffic to uniques.",
            ),
            UseCaseItem(
                category_id="replication", option_id="rep-mtree", qty=40,
                rationale="Every branch replicates into the core, encrypted, deduped.",
            ),
            UseCaseItem(
                category_id="cyberrecovery", option_id="cr-software", qty=1,
                rationale="One vault, one gap, one recovery workflow for the chain.",
            ),
            UseCaseItem(
                category_id="analytics", option_id="cs-analytics", qty=1,
                rationale="Scans the consolidated copies; flags the branch that turned.",
            ),
            UseCaseItem(
                category_id="integration", option_id="int-cloudiq", qty=1,
                rationale="Fleet-wide capacity forecasts and dedupe-anomaly alerts.",
            ),
        ],
        outcomes=[
            Stat(label="Branches protected", value="40 · one uniform runbook"),
            Stat(label="WAN cost", value="Unique segments only, after dedupe"),
            Stat(label="Local restores", value="LAN-speed at every branch"),
            Stat(label="Vaults to operate", value="One, for the entire chain"),
        ],
    ),
]
