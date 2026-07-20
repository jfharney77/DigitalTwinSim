"""Component catalog: what a PowerProtect Cyber Recovery deployment is
built from, as data.

Same pattern as the other twins: categories map onto site regions via
``region_ids`` (ids from anatomy.py; an empty list means the item is not a
drawn part of the map — cloud tiers, services). Written for a technically
skilled reader new to data protection; jargon (dedupe, DD Boost, Retention
Lock, air gap, CyberSense, RPO/RTO, ...) is spelled out on first use.
Figures are product-literature numbers from Dell's 2025 announcements, not
benchmarks.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="appliance",
        name="Data Domain appliances",
        blurb=(
            "The purpose-built backup appliance itself — chosen twice in a "
            "Cyber Recovery design, once for production and once for the "
            "vault. The 2025 all-flash generation changed the headline "
            "number from capacity to restore speed."
        ),
        limits="From 8 TBu (DD3410) to multi-PB flagships; usable grows in place",
        region_ids=["dd-prod", "dd-vault"],
        options=[
            CatalogOption(
                id="app-allflash",
                name="Data Domain All-Flash appliance",
                summary="The 2025 flagship: up to 4× faster restores, 65:1 reduction, 40% less rack.",
                details=(
                    "The all-flash generation (announced September 2025) "
                    "rebuilds Data Domain on flash media: Dell quotes up to "
                    "4× faster restores, 2× faster replication, 2.8× faster "
                    "CyberSense analytics, 40% less rack space, and up to "
                    "80% power savings — at the same up-to-65:1 data "
                    "reduction. The design point is honest about what "
                    "changed in the world: backups used to be judged on "
                    "how cheaply they ingested; after ransomware, they are "
                    "judged on how fast they restore."
                ),
            ),
            CatalogOption(
                id="app-dd9910",
                name="Data Domain DD9910 (disk flagship)",
                summary="The high-end disk-era appliance for petabyte-scale estates.",
                details=(
                    "The established flagship: petabyte-class usable "
                    "capacity (multi-tens of PB logical after dedupe), "
                    "high-throughput ingest via DD Boost, and cloud tiering "
                    "for long-term retention. In mixed fleets it remains "
                    "the deep archive tier while all-flash takes the "
                    "restore-critical estates — DDMC manages both as one "
                    "fleet."
                ),
            ),
            CatalogOption(
                id="app-dd3410",
                name="Data Domain DD3410 (edge/ROBO)",
                summary="Compact entry appliance: 8–32 TBu, grow-in-place, full DDOS.",
                details=(
                    "The small end of the family (available Q1 2026): a "
                    "compact appliance for remote offices and smaller "
                    "estates that starts at 8 TB usable and grows in place "
                    "to 32 TBu by license, no hardware change. It runs the "
                    "same DDOS filesystem — same dedupe, same Boost, same "
                    "Retention Lock — so a branch office replicates into "
                    "the same core and vault architecture as the data "
                    "center, and the recovery story is uniform."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="ddos",
        name="DDOS software & protocols",
        blurb=(
            "The filesystem is the product: deduplication, integrity "
            "architecture, and the Boost protocol that makes clients part "
            "of the appliance."
        ),
        limits="Ships on every Data Domain; features license-enabled",
        region_ids=["dd-prod", "dd-vault"],
        options=[
            CatalogOption(
                id="ddos-dedupe",
                name="Variable-length deduplication",
                summary="Recognizes repeated segments at any offset; up to 65:1 with compression.",
                details=(
                    "Fixed-block dedupe breaks when data shifts by a byte; "
                    "Data Domain's variable-length segmentation finds the "
                    "same content at any offset, which is why real backup "
                    "streams — the same estate, nightly, forever — collapse "
                    "so dramatically. Local compression stacks on top. The "
                    "ratio is not vanity: it sets the cost of every "
                    "downstream copy, including the vault's."
                ),
            ),
            CatalogOption(
                id="ddos-boost",
                name="DD Boost",
                summary="Client-side dedupe: only never-seen segments cross the wire.",
                details=(
                    "DD Boost embeds part of the deduplication in the "
                    "backup client or application plug-in: the client "
                    "fingerprints segments and sends only those the "
                    "appliance lacks. Backup windows shrink, LANs breathe, "
                    "and databases can stream via native tools (RMAN, "
                    "SAP BR*Tools) straight to the appliance. Boost is also "
                    "how PPDM, NetWorker, and the third-party ecosystem "
                    "integrate."
                ),
            ),
            CatalogOption(
                id="ddos-dia",
                name="Data Invulnerability Architecture",
                summary="End-to-end checksums and verify-after-write inside the filesystem.",
                details=(
                    "DDOS assumes storage lies: every write is checksummed "
                    "end to end, verified after landing, and continuously "
                    "scrubbed; RAID-6 plus fault isolation covers the "
                    "hardware. For a backup appliance this paranoia is the "
                    "job description — the worst failure mode in data "
                    "protection is discovering at restore time that the "
                    "copy was quietly rotten."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="immutability",
        name="Immutability & hardening",
        blurb=(
            "What 'they can't delete the backups' actually means, "
            "mechanically: WORM enforcement, separated duties, and a "
            "hardware root of trust."
        ),
        limits="Retention Lock Governance or Compliance, per MTree",
        region_ids=["dd-vault"],
        options=[
            CatalogOption(
                id="imm-retlock",
                name="Retention Lock Compliance",
                summary="Filesystem WORM no admin, root, or vendor can override early.",
                details=(
                    "Retention Lock makes files write-once-read-many until "
                    "a per-file retention clock expires. The Governance "
                    "edition lets a privileged security officer intervene; "
                    "the Compliance edition — built for SEC 17a-4-class "
                    "regulation — removes even that: dual-authorization "
                    "setup, a hardened security-officer role, and no "
                    "override path for administrators or for Dell. In the "
                    "vault, Compliance mode is what turns 'a second copy' "
                    "into 'a copy that provably cannot be rewritten'."
                ),
            ),
            CatalogOption(
                id="imm-hardening",
                name="System hardening + root of trust",
                summary="Signed firmware, secure boot, dual authorization for destructive ops.",
                details=(
                    "The appliance itself is hardened: measured secure "
                    "boot on a hardware root of trust, signed DDOS "
                    "images, role separation between backup admin and "
                    "security officer, and dual authorization on "
                    "destructive operations like MTree deletion or "
                    "retention changes. The threat model is explicit — the "
                    "attacker *has* the admin password, because in real "
                    "incidents they usually do."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="cyberrecovery",
        name="Cyber Recovery vault",
        blurb=(
            "The architecture around the second appliance: the vault "
            "environment, the automated air gap, and the runbooks that "
            "make recovery a rehearsal instead of an improvisation."
        ),
        limits="One vault serves many production sources",
        region_ids=["gap", "dd-vault", "recovery-host"],
        options=[
            CatalogOption(
                id="cr-software",
                name="PowerProtect Cyber Recovery software",
                summary="Automates the gap, the sync, the lock, and the recovery workflow.",
                details=(
                    "Cyber Recovery is the control plane inside the vault: "
                    "it opens the air gap on schedule, drives the "
                    "replication sync, applies Retention Lock to each "
                    "copy, triggers CyberSense analysis, and orchestrates "
                    "recovery workflows back toward production. It runs in "
                    "the vault and answers only to the vault — production "
                    "has no session, credential, or API path into it."
                ),
            ),
            CatalogOption(
                id="cr-airgap",
                name="Operational air gap",
                summary="A vault-owned link, closed by default, open minutes a day.",
                details=(
                    "The gap is an automated network control, not a person "
                    "with a patch cable: the replication link exists only "
                    "while the vault raises it, and dedupe keeps those "
                    "windows to minutes. 'Operational' distinguishes it "
                    "from a physical offline copy — it is connected briefly "
                    "and automatically, which is what makes daily vault "
                    "points practical without a nightly human ritual."
                ),
            ),
            CatalogOption(
                id="cr-cleanroom",
                name="Clean-room recovery environment",
                summary="Isolated compute in the vault to validate before restoring.",
                details=(
                    "Recovery hosts inside the vault mount candidate "
                    "copies on an isolated network, boot the applications, "
                    "and prove the restore point is whole before anything "
                    "flows back to production. Incident-response reality "
                    "drives the design: after an attack, production "
                    "networks are crime scenes and possibly still hostile "
                    "— the first clean copy must come up somewhere the "
                    "attacker has never been."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="analytics",
        name="CyberSense analytics",
        blurb=(
            "The vault's intelligence: content-level machine learning that "
            "answers the only question that matters at 3 a.m. — which "
            "copy is clean?"
        ),
        limits="Scans inside the vault; verdict per restore point",
        region_ids=["cybersense"],
        options=[
            CatalogOption(
                id="cs-analytics",
                name="CyberSense integrity analytics",
                summary="200+ content signals — entropy, corruption, mass renames — per scan.",
                details=(
                    "CyberSense indexes the vaulted copies at the content "
                    "level and evaluates over 200 statistics against every "
                    "prior scan: entropy jumps that betray encryption, "
                    "malformed file internals, mass renames and "
                    "extensions, database page corruption. Machine-"
                    "learning models trained on ransomware families turn "
                    "the signals into a per-restore-point verdict with "
                    "high accuracy — the difference between restoring data "
                    "and restoring the infection. The 2025 all-flash "
                    "platform runs these scans up to 2.8× faster."
                ),
            ),
            CatalogOption(
                id="cs-forensics",
                name="Post-attack forensics",
                summary="Which files, when, and how — the attack's shape from the copies.",
                details=(
                    "Because CyberSense keeps content statistics per scan "
                    "per copy, it can reconstruct an attack's timeline "
                    "after the fact: when corruption first appears, which "
                    "systems and files it touched, how it spread. That "
                    "feeds the incident response (what to restore, what to "
                    "quarantine) and the insurers' and regulators' "
                    "questions that follow every serious incident."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="backup",
        name="Backup software",
        blurb=(
            "The orchestration layer that feeds the appliance. Dell's own "
            "PPDM leads, but Data Domain is deliberately promiscuous — "
            "most major backup products speak Boost."
        ),
        limits="PPDM, NetWorker, Avamar + broad third-party ecosystem",
        region_ids=["backup-server"],
        options=[
            CatalogOption(
                id="bk-ppdm",
                name="PowerProtect Data Manager (PPDM)",
                summary="Dell's modern orchestration: policies, SaaS option, Kubernetes-aware.",
                details=(
                    "PPDM is the current-generation backup control plane: "
                    "policy-driven protection for VMware, databases, "
                    "Kubernetes, and file workloads, streaming to Data "
                    "Domain via Boost, with Transparent Snapshots for "
                    "low-impact VM backup. It integrates directly with the "
                    "Cyber Recovery workflow, and its catalog is itself "
                    "protected — the twin's attack step shows why that "
                    "matters."
                ),
            ),
            CatalogOption(
                id="bk-ecosystem",
                name="Third-party ecosystem",
                summary="NetWorker, Commvault, Veeam, Veritas, Oracle RMAN — all land on DD.",
                details=(
                    "Data Domain's ecosystem is a deliberate moat: "
                    "long-standing Boost integrations for Dell NetWorker "
                    "and Avamar, plus Commvault, Veeam, Veritas "
                    "NetBackup, and native database tools. An organization "
                    "rarely has one backup product; the appliance and the "
                    "vault architecture work regardless, and CyberSense's "
                    "2025 updates extended analytics to Commvault "
                    "client-direct Oracle backups."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="replication",
        name="Replication & tiering",
        blurb=(
            "How copies travel: dedupe-aware replication between "
            "appliances, and cloud tiers for long-term retention."
        ),
        limits="Only unique segments cross any link",
        region_ids=["dd-prod", "gap", "dd-vault"],
        options=[
            CatalogOption(
                id="rep-mtree",
                name="MTree replication",
                summary="Dedupe-aware, encrypted replication — the vault's transport.",
                details=(
                    "MTree replication mirrors a logical partition of the "
                    "filesystem between appliances, sending only segments "
                    "the destination lacks, encrypted in flight. It is the "
                    "transport under the air gap: because the wire carries "
                    "uniques, a nightly vault sync is minutes — and the "
                    "2025 all-flash generation doubles replication speed "
                    "again. The same mechanism serves ordinary DR "
                    "replication between sites."
                ),
            ),
            CatalogOption(
                id="rep-cloudtier",
                name="DD Cloud Tier",
                summary="Cold restore points age out to object storage, still deduped.",
                details=(
                    "Cloud Tier moves aged backup data to object storage "
                    "(AWS, Azure, ECS/ObjectScale) natively from DDOS, "
                    "still deduplicated and still restorable through the "
                    "same catalog. Long-term retention — the seven-year "
                    "compliance tail — stops competing with hot restore "
                    "points for appliance capacity. It complements the "
                    "vault; it does not replace it, because object-store "
                    "credentials live in production's world."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="integration",
        name="Estate integration",
        blurb=(
            "The appliances do not exist alone: primary storage arrays "
            "back up straight to them, and the twins in this repo meet "
            "here."
        ),
        limits="Native paths from PowerStore, PowerMax, and PowerScale",
        region_ids=["workload-vm", "workload-db"],
        options=[
            CatalogOption(
                id="int-storage",
                name="PowerStore / PowerMax direct backup",
                summary="Array snapshots stream to Data Domain without a media server.",
                details=(
                    "Dell's primary arrays integrate natively: PowerStore "
                    "and PowerMax can send snapshot-based backups directly "
                    "to Data Domain, no intermediate media server, "
                    "orchestrated by PPDM. For this repo, that closes a "
                    "loop: the PowerMax twin's cyber-resiliency vault use "
                    "case is, concretely, this twin's architecture with a "
                    "PowerMax on the left edge."
                ),
            ),
            CatalogOption(
                id="int-cloudiq",
                name="CloudIQ / AIOps observability",
                summary="Fleet health, capacity forecasts, and anomaly alerts for the estate.",
                details=(
                    "Data Domain fleets report into Dell's AIOps platform "
                    "(the CloudIQ twin): capacity forecasting says when "
                    "the appliance fills, anomaly detection flags unusual "
                    "backup behavior — a sudden dedupe-ratio collapse is a "
                    "classic early ransomware tell, since encrypted data "
                    "does not deduplicate. The observability twin and this "
                    "twin are watching the same estate from different "
                    "angles."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="services",
        name="Resilience services",
        blurb=(
            "The people part: vault design, rehearsals, and who answers "
            "the phone during the worst week of the company's life."
        ),
        limits="Design, residency, and incident retainers",
        region_ids=[],
        options=[
            CatalogOption(
                id="svc-design",
                name="Vault design & deployment services",
                summary="Sizing, isolation review, and runbook build for the vault.",
                details=(
                    "A vault is an architecture, not an SKU: what gets "
                    "vaulted and how often, how the gap is isolated at "
                    "the network layer, who holds the security-officer "
                    "role, what the recovery runbooks say. Dell's services "
                    "stand the vault up and — more important — rehearse "
                    "it, because the first full restore should never be "
                    "the real one."
                ),
            ),
            CatalogOption(
                id="svc-response",
                name="Incident response & recovery retainer",
                summary="A practiced team on call for the recovery itself.",
                details=(
                    "When the attack lands, the in-house team is "
                    "firefighting identity, networks, and executives at "
                    "once. A retainer puts a practiced recovery team on "
                    "the vault side — reading CyberSense verdicts, running "
                    "the clean room, sequencing the restore — turning the "
                    "twin's final phase from heroics into procedure."
                ),
            ),
        ],
    ),
]
