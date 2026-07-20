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
            description=(
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
            active_regions=["workload-vm", "workload-db"],
            logical_tb=0,
            stored_tb=0,
            elapsed_hours=0,
        ),
        LifecycleState(
            step=1,
            phase="backup",
            label="First full backup streams to Data Domain",
            description=(
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
            description=(
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
            description=(
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
            active_regions=["dd-prod", "gap", "dd-vault"],
            logical_tb=500,
            stored_tb=25,
            elapsed_hours=721,
        ),
        LifecycleState(
            step=4,
            phase="airgap",
            label="The gap closes — Retention Lock makes the copy immutable",
            description=(
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
            active_regions=["dd-vault"],
            logical_tb=500,
            stored_tb=25,
            elapsed_hours=722,
        ),
        LifecycleState(
            step=5,
            phase="scan",
            label="CyberSense analyzes the vaulted copy",
            description=(
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
            description=(
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
            description=(
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
            description=(
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
            active_regions=(
                ["workload-vm", "workload-db", "backup-server", "dd-prod",
                 "dd-vault", "mgmt"]
            ),
            logical_tb=520,
            stored_tb=26,
            elapsed_hours=768,
        ),
    ]
