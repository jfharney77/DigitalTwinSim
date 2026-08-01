"""Pure data-lifecycle engine for PowerProtect Data Domain + Cyber Recovery.

``simulate()`` returns the deterministic trace of a protected estate's data
from first backup through a ransomware attack to recovery from the vault.
Same purity rule as every other twin in this repo: no FastAPI, no IO, no
timers — the frontend owns the playback clock, and each ``LifecycleState``
is plain data the renderer consumes. ``cycle_cost`` marks the long stages
(the CyberSense scan) so the UI dwells on them.

Two disciplines shape the trace, and the tests hold the engine to both:

- **Dedupe economics**: ``stored_tb`` never exceeds ``logical_tb``, and once
  weeks of backups accumulate the ratio goes long — Data Domain's variable-
  length deduplication is why a petabyte of backups fits in a closet.
- **Air-gap discipline**: the ``gap`` region is active only while the vault
  itself opens it (replication in, recovery out). At the attack step nothing
  on the vault side lights at all — the malware cannot reach what has no
  network path and no writable surface.

Sizes and hours are illustrative but plausible; favor a correct mental
model over measured numbers (project scope guardrail).
"""

from __future__ import annotations

from .leveling import L
from .models import LifecycleState

PRODUCTION = ["workload-vm", "workload-db", "backup-server", "dd-prod"]
VAULT = ["dd-vault", "cybersense", "recovery-host"]


def simulate() -> list[LifecycleState]:
    """The data's journey from first backup to post-attack recovery."""
    return [
        LifecycleState(
            step=0,
            phase="idle",
            label="The estate hums — nothing is protected yet",
            description=L(
                novice=(
                    "A working estate: virtual machines, databases, file shares — a "
                    "few hundred terabytes of the organization's memory, all of it "
                    "currently existing in exactly one place. The administrator "
                    "schedules the first backup policy. Everything that follows "
                    "exists because of an uncomfortable modern fact: backups are no "
                    "longer only insurance against a broken disk. They are a "
                    "target, and attackers go for them first."
                ),
                plain=(
                    "A working estate: virtual machines, databases, file shares — a "
                    "few hundred terabytes of the organization's memory, all "
                    "currently existing in exactly one place. The backup "
                    "administrator schedules the first policy in PowerProtect Data "
                    "Manager. Everything that follows exists because of an "
                    "uncomfortable modern fact: backups are no longer only "
                    "insurance against hardware failure — they are a target, and a "
                    "competent attacker destroys them first."
                ),
                standard=(
                    "A working estate: virtual machines, databases, file "
                    "shares — a few hundred terabytes of the organization's "
                    "memory, all of it currently existing in exactly one "
                    "place. The backup administrator schedules the first "
                    "policy in PowerProtect Data Manager (PPDM), Dell's backup "
                    "software. Everything that follows exists because of an "
                    "uncomfortable modern fact: backups are no longer only "
                    "insurance against failure — they are the primary target "
                    "of ransomware crews, who encrypt or delete them first."
                ),
                technical=(
                    "Production estate — VMs, databases, file shares, a few hundred "
                    "TB — with a single copy of everything. First policy scheduled "
                    "in PowerProtect Data Manager. The design premise: backups are "
                    "an attack target rather than only failure insurance, and are "
                    "destroyed first in a competent intrusion."
                ),
                expert=(
                    "Production estate, single copy, first policy scheduled. "
                    "Premise: backups are a target, destroyed first."
                ),
            ),
            active_regions=["workload-vm", "workload-db"],
            logical_tb=0,
            stored_tb=0,
            elapsed_hours=0,
        ),
        LifecycleState(
            step=1,
            phase="backup",
            label="First full backup streams to Data Domain",
            description=L(
                novice=(
                    "The first full backup runs. Clients send data to the backup "
                    "appliance using a protocol that moves part of the work out to "
                    "the client, so only pieces the appliance has never seen before "
                    "travel across the network. Even this very first backup shrinks "
                    "by about five to one — a hundred terabytes becomes roughly "
                    "twenty — because real estates repeat themselves far more than "
                    "people expect."
                ),
                plain=(
                    "The first full backup runs. Clients stream to the PowerProtect "
                    "Data Domain appliance over DD Boost — a protocol that moves "
                    "part of the deduplication work to the client, so only segments "
                    "the appliance has never seen cross the wire. Even this first "
                    "full lands at about 5:1 reduction: 100 TB of logical backup "
                    "becomes roughly 20 TB of physical flash, because real estates "
                    "repeat themselves."
                ),
                standard=(
                    "The first full backup runs. Clients stream to the "
                    "PowerProtect Data Domain appliance over DD Boost — a "
                    "protocol that moves part of the deduplication work to the "
                    "client, so only data segments the appliance has never "
                    "seen cross the wire. Even this first full lands at about "
                    "5:1 reduction: 100 TB of logical backup becomes roughly "
                    "20 TB of physical flash, because real estates repeat "
                    "themselves — same OS images, same libraries, same "
                    "documents attached to forty emails."
                ),
                technical=(
                    "First full backup over DD Boost, which distributes segment "
                    "identification to the client so only unseen segments traverse "
                    "the network. ~5:1 on a first full — 100 TB logical to ~20 TB "
                    "physical — reflecting the intrinsic redundancy of a real "
                    "estate."
                ),
                expert=(
                    "First full over DD Boost; client-side segment identification, "
                    "only unseen segments on the wire. ~5:1 (100 TB → ~20 TB)."
                ),
            ),
            active_regions=["workload-vm", "workload-db", "backup-server", "dd-prod"],
            logical_tb=100,
            stored_tb=20,
            elapsed_hours=12,
            cycle_cost=2,
        ),
        LifecycleState(
            step=2,
            phase="dedupe",
            label="Weeks accumulate — dedupe does its arithmetic",
            description=L(
                novice=(
                    "Daily backups pile up for a month, and the appliance's "
                    "deduplication earns its reputation. Each new backup is mostly "
                    "data it has already stored, so it keeps only pointers plus the "
                    "day's genuinely new pieces: 500 terabytes of logical "
                    "protection now occupies about 25 terabytes of actual flash. "
                    "That arithmetic is what makes the next step affordable at all "
                    "— you cannot keep a second isolated copy of something you "
                    "cannot afford to store once."
                ),
                plain=(
                    "Daily backups pile up for a month, and Data Domain's "
                    "variable-length deduplication earns its reputation. Each new "
                    "backup is mostly data the appliance has already stored, so it "
                    "keeps pointers plus the day's genuinely new segments: 500 TB "
                    "of logical protection now occupies about 25 TB of flash — 20:1 "
                    "and climbing, with Dell quoting up to 65:1 on the all-flash "
                    "appliance. This arithmetic is what makes the vault affordable."
                ),
                standard=(
                    "Daily backups pile up for a month, and Data Domain's "
                    "variable-length deduplication earns its reputation. Each "
                    "new backup is mostly data the appliance has already "
                    "stored, so it keeps only pointers plus the day's genuinely "
                    "new segments: 500 TB of logical protection now occupies "
                    "about 25 TB of flash — 20:1 and climbing (Dell quotes up "
                    "to 65:1 on the all-flash appliance). This arithmetic is "
                    "what makes everything downstream affordable: weeks of "
                    "restore points, fast replication, and a vault that does "
                    "not need a second data center's worth of storage."
                ),
                technical=(
                    "A month of dailies, and variable-length deduplication "
                    "compounds: each backup is predominantly resident data, so only "
                    "pointers plus genuinely novel segments are stored. 500 TB "
                    "logical at ~25 TB physical — 20:1 and climbing, with up to "
                    "65:1 quoted on the all-flash generation. The economics of the "
                    "vault depend entirely on this ratio."
                ),
                expert=(
                    "A month of dailies: 500 TB logical at ~25 TB physical, 20:1 "
                    "climbing to a quoted 65:1. Vault economics depend on the "
                    "ratio."
                ),
            ),
            active_regions=["backup-server", "dd-prod"],
            logical_tb=500,
            stored_tb=25,
            elapsed_hours=720,
            cycle_cost=2,
        ),
        LifecycleState(
            step=3,
            phase="replicate",
            label="The air gap opens — a copy crosses into the vault",
            description=L(
                novice=(
                    "On the vault's schedule — never production's — the connection "
                    "opens and the vault appliance synchronizes. Two details matter "
                    "enormously. The vault *pulls*: the connection is started and "
                    "controlled from inside the vault, so no credential stored in "
                    "production can open it. And only the genuinely new pieces "
                    "cross, so the window stays short — and a short window is a "
                    "small target."
                ),
                plain=(
                    "On the vault's schedule — never production's — the operational "
                    "air gap opens and Data Domain replication syncs the vault "
                    "appliance. Two details matter. The vault *pulls*: the "
                    "connection is initiated and controlled from inside the Cyber "
                    "Recovery vault, so no credential stored in production can open "
                    "it. And only deduplicated unique segments cross, so the window "
                    "stays short — and a short window is a small target."
                ),
                standard=(
                    "On the vault's schedule — never production's — the "
                    "operational air gap opens and Data Domain replication "
                    "syncs the vault appliance. Two details matter. The vault "
                    "*pulls*: the connection is initiated and controlled from "
                    "inside the Cyber Recovery vault, so no credential stored "
                    "in production can open it. And only deduplicated unique "
                    "segments cross, so the window stays short — minutes to "
                    "tens of minutes, not the days a raw 500 TB copy would "
                    "need. Short windows are the point: the gap spends almost "
                    "all of its life closed."
                ),
                technical=(
                    "Gap opens on the vault's schedule, never production's, and "
                    "replication syncs the vault appliance. Two properties: the "
                    "connection is vault-initiated and vault-controlled, so no "
                    "production-resident credential can open it; and only unique "
                    "deduplicated segments transit, bounding the window. The engine "
                    "asserts the gap is active in exactly {replicate, recover}."
                ),
                expert=(
                    "Vault-initiated, vault-scheduled sync; no production "
                    "credential can open it. Unique segments only, bounding the "
                    "window. Gap active in exactly {replicate, recover}, asserted."
                ),
            ),
            active_regions=["dd-prod", "gap", "dd-vault"],
            logical_tb=500,
            stored_tb=25,
            elapsed_hours=721,
        ),
        LifecycleState(
            step=4,
            phase="airgap",
            label="The gap closes — Retention Lock makes the copy immutable",
            description=L(
                novice=(
                    "Replication completes and the vault seals: the network path is "
                    "administratively cut, and the copy inside becomes immutable. "
                    "That immutability is enforced by the storage system itself — "
                    "until the retention clock expires, no administrator, no root "
                    "access, and no stolen credential can alter or delete it. This "
                    "is the difference between a copy that is merely elsewhere and "
                    "a copy that cannot be destroyed."
                ),
                plain=(
                    "Replication completes and the vault seals: the network path is "
                    "administratively severed, and Retention Lock Compliance arms "
                    "on the vaulted copy. Retention Lock is write-once-read-many "
                    "enforcement in the Data Domain filesystem itself — until the "
                    "retention clock expires, no administrator, no root shell, and "
                    "no stolen credential can modify or delete the locked data."
                ),
                standard=(
                    "Replication completes and the vault seals: the network "
                    "path is administratively severed, and Retention Lock "
                    "Compliance arms on the vaulted copy. Retention Lock is "
                    "write-once-read-many (WORM) enforcement in the Data "
                    "Domain filesystem itself — until the retention clock "
                    "expires, no administrator, no root shell, and no stolen "
                    "credential can modify or delete the locked data. The "
                    "compliance edition even resists the vendor: there is no "
                    "Dell back door to unlock it early. The vault now holds "
                    "what ransomware crews hunt hardest for and cannot reach: "
                    "a copy that provably cannot be rewritten."
                ),
                technical=(
                    "Replication completes; the path is administratively severed "
                    "and Retention Lock Compliance arms on the vaulted copy. WORM "
                    "enforcement lives in the filesystem, not in policy above it — "
                    "for the retention period the data is immutable to "
                    "administrators, root, and any stolen credential alike. Sealed "
                    "strictly before the attack, which the engine asserts."
                ),
                expert=(
                    "Path severed, Retention Lock Compliance armed. "
                    "Filesystem-level WORM — immutable to admin, root, and stolen "
                    "credentials for the retention period. Sealed pre-attack, "
                    "asserted."
                ),
            ),
            active_regions=["dd-vault"],
            logical_tb=500,
            stored_tb=25,
            elapsed_hours=722,
        ),
        LifecycleState(
            step=5,
            phase="scan",
            label="CyberSense analyzes the vaulted copy",
            description=L(
                novice=(
                    "The long stage, and deliberately the longest here. Inside the "
                    "vault, the analysis software indexes the locked copy and runs "
                    "machine-learning analytics over what is actually in the files: "
                    "how random the content looks (encrypted files are "
                    "statistically distinctive), whether file types are corrupted, "
                    "whether things were renamed en masse, whether database pages "
                    "are damaged — over 200 signals, compared against every "
                    "previous scan. This is how the vault knows not merely that it "
                    "holds a copy, but that it holds a *good* one."
                ),
                plain=(
                    "The long stage, and deliberately the longest in this trace. "
                    "Inside the vault, CyberSense indexes the locked copy and runs "
                    "machine-learning analytics over content features: entropy "
                    "(encrypted files look statistically different from documents), "
                    "file-type corruption, mass renames, database page damage — "
                    "over 200 signals, compared against every previous scan. This "
                    "is how the vault knows it holds not merely a copy but a good "
                    "one."
                ),
                standard=(
                    "The long stage — and deliberately the longest in this "
                    "trace. Inside the vault, CyberSense indexes the locked "
                    "copy and runs machine-learning analytics over content "
                    "features: entropy (encrypted files look statistically "
                    "different from documents), file-type corruption, mass "
                    "renames, database page damage — over 200 signals, "
                    "compared against every previous scan. This is how the "
                    "vault answers the question that decides a recovery: not "
                    "'do we have a copy?' but 'which copy is *clean*?' "
                    "Ransomware that dwelt quietly for weeks is exactly what "
                    "this pass exists to catch, and each scan's verdict is "
                    "recorded against that restore point."
                ),
                technical=(
                    "Max-dwell stage. CyberSense indexes the locked copy and "
                    "applies ML analytics across 200+ content features — entropy "
                    "distribution, file-type integrity, mass rename patterns, "
                    "database page damage — differenced against every prior scan. "
                    "The vault's assurance is not that a copy exists but that its "
                    "contents are intact, which is exactly what the CyberDetect "
                    "twin covers on primary storage."
                ),
                expert=(
                    "Max dwell: CyberSense indexes and scores 200+ content features "
                    "against prior scans. Assurance is content integrity, not copy "
                    "existence — cf. the CyberDetect twin on primary."
                ),
            ),
            active_regions=["dd-vault", "cybersense"],
            logical_tb=500,
            stored_tb=25,
            elapsed_hours=726,
            cycle_cost=5,
        ),
        LifecycleState(
            step=6,
            phase="attack",
            label="Ransomware detonates — and the vault isn't there",
            description=L(
                novice=(
                    "The bad night. Ransomware that has been quietly waiting in the "
                    "estate detonates: production data encrypts, the backup "
                    "catalogue is deleted using stolen administrator credentials, "
                    "and the production appliance comes under attack from inside "
                    "the management network. And the vault? The attacker's tooling "
                    "cannot even establish that it exists. The gap is closed — "
                    "there is no route, no name to look up, and no credential that "
                    "would help."
                ),
                plain=(
                    "The bad night. Ransomware that has been dwelling in the estate "
                    "detonates: production volumes encrypt, the backup server's "
                    "catalog is deleted with stolen admin credentials, and the "
                    "production Data Domain comes under attack from inside the "
                    "management network. And the vault? The attacker's tooling "
                    "cannot even establish that it exists. The gap is closed — "
                    "there is no route, no DNS entry, and no credential that would "
                    "help."
                ),
                standard=(
                    "The bad night. Ransomware that has been dwelling in the "
                    "estate detonates: production volumes encrypt, the backup "
                    "server's catalog is deleted with stolen admin "
                    "credentials, and the production Data Domain comes under "
                    "attack from inside the management network. And the vault? "
                    "The attacker's tooling cannot even establish that it "
                    "exists. The gap is closed — there is no route, no DNS "
                    "entry, no session to hijack — and even the replication "
                    "credentials production held are useless, because the "
                    "vault only ever called out, never listened. What the "
                    "malware cannot reach, it cannot encrypt."
                ),
                technical=(
                    "Detonation: production volumes encrypted, backup catalog "
                    "destroyed with stolen administrative credentials, production "
                    "appliance attacked from inside the management network. The "
                    "vault is not merely defended but unreachable — no route, no "
                    "name resolution, no credential of use. The engine asserts no "
                    "vault region and no gap is active at this step while "
                    "production's blast radius is."
                ),
                expert=(
                    "Detonation: volumes encrypted, catalog destroyed, production "
                    "appliance attacked from the management network. Vault "
                    "unreachable — no route, no resolution, no useful credential. "
                    "Asserted: no vault region, no gap active."
                ),
            ),
            active_regions=["workload-vm", "workload-db", "backup-server", "dd-prod"],
            logical_tb=500,
            stored_tb=25,
            elapsed_hours=730,
            cycle_cost=2,
        ),
        LifecycleState(
            step=7,
            phase="recover",
            label="The vault opens on its own terms — clean copy restores",
            description=L(
                novice=(
                    "Recovery runs at the vault's pace, from the vault's side. "
                    "Inside an isolated clean room, the team uses the analysis "
                    "verdicts to choose the last provably clean restore point — "
                    "skipping the recent copies the dwell-time analysis flagged — "
                    "and rehearses the restore on an isolated host before touching "
                    "production. Only then does the vault open its connection "
                    "outward and push the clean copy back."
                ),
                plain=(
                    "Recovery runs at the vault's pace, from the vault's side. "
                    "Inside the clean room, the team consults CyberSense's verdicts "
                    "to choose the last provably-clean restore point — skipping the "
                    "recent copies the dwell-time analysis flagged — and rehearses "
                    "the restore on the isolated recovery host before touching "
                    "production. Only then does the vault open its gap outward and "
                    "push the clean copy back."
                ),
                standard=(
                    "Recovery runs at the vault's pace, from the vault's side. "
                    "Inside the clean room, the team consults CyberSense's "
                    "verdicts to choose the last provably-clean restore point "
                    "— skipping the recent copies the dwell-time analysis "
                    "flagged — and rehearses the restore on the isolated "
                    "recovery host before touching production. Only then does "
                    "the vault open its gap outward and push the clean data "
                    "back to a rebuilt production Data Domain. The all-flash "
                    "appliance is why this is hours, not weeks: Dell quotes up "
                    "to 4× faster restores, and restore speed is the number "
                    "the whole architecture is ultimately judged on."
                ),
                technical=(
                    "Recovery is vault-paced and vault-initiated. In the clean "
                    "room, CyberSense verdicts select the last provably-clean "
                    "restore point, excluding copies the dwell-time analysis "
                    "flagged, and the restore is rehearsed on the isolated recovery "
                    "host before production is touched. Only then does the gap open "
                    "outward — the second and last time it opens in this trace."
                ),
                expert=(
                    "Vault-paced, vault-initiated. Clean-room verdict selects the "
                    "last provably-clean point; rehearsed on the isolated host, "
                    "then the gap opens outward — its second and final opening."
                ),
            ),
            active_regions=["dd-vault", "recovery-host", "gap", "dd-prod"],
            logical_tb=500,
            stored_tb=25,
            elapsed_hours=744,
            cycle_cost=3,
        ),
        LifecycleState(
            step=8,
            phase="restored",
            label="The estate is back — from data the attacker never touched",
            description=L(
                novice=(
                    "Workloads run again, restored from a copy that spent the "
                    "attack sealed behind a closed gap and locked against "
                    "modification. The post-incident report writes itself around "
                    "this twin's two disciplines: deduplication made an affordable "
                    "second copy possible at all, and the air gap plus immutability "
                    "made it unreachable. The cycle resumes — back up, replicate, "
                    "lock, scan — because the protection was never a one-time "
                    "event."
                ),
                plain=(
                    "Workloads run again, restored from a copy that spent the "
                    "attack sealed behind a closed gap under Retention Lock. The "
                    "post-incident report writes itself around the twin's two "
                    "disciplines: dedupe made an affordable vault possible, and the "
                    "air gap plus immutability made it unreachable. The cycle "
                    "resumes — backup, replicate, lock, scan — because the vault's "
                    "protection was never a one-time event."
                ),
                standard=(
                    "Workloads run again, restored from a copy that spent the "
                    "attack sealed behind a closed gap under Retention Lock. "
                    "The post-incident report writes itself around the twin's "
                    "two disciplines: dedupe made an affordable vault "
                    "possible, and the air gap plus immutability made it "
                    "unreachable. The cycle resumes — backup, replicate, "
                    "lock, scan — because the vault's protection was never a "
                    "device; it was a routine that was already running before "
                    "anyone needed it."
                ),
                technical=(
                    "Restored from a copy that was sealed and immutable throughout "
                    "the incident. The two disciplines are separable and both "
                    "necessary: deduplication makes a second isolated copy "
                    "economically possible, and the operational air gap plus WORM "
                    "immutability make it unreachable. The cycle resumes, because "
                    "protection is a schedule rather than an event."
                ),
                expert=(
                    "Restored from a sealed, immutable copy. Dedupe makes the vault "
                    "affordable; air gap plus WORM make it unreachable. Protection "
                    "is a schedule, not an event."
                ),
            ),
            active_regions=(
                ["workload-vm", "workload-db", "backup-server", "dd-prod",
                 "dd-vault", "mgmt"]
            ),
            logical_tb=520,
            stored_tb=26,
            elapsed_hours=768,
        ),
    ]
