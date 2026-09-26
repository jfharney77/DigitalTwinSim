"""The narrated tour of PowerProtect + Cyber Recovery — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: nine beats that
follow the data across the two-site map, from production on the left to the
Cyber Recovery vault on the right, pin the lifecycle trace at the moments
that carry the story, and narrate each one. The frontend player owns the
clock; nothing here knows about time, IO or the web (AST-checked in
``tests/test_tour.py``, the same rule as ``engine.py``).

The signature beat is ``airgap-discipline``: the gap opens only from the
vault side, and only for replication in and recovery out. Every claim the
scripts make is one ``engine.py`` and ``anatomy.py`` already make, and the
trace index named in each beat is the step whose description says it.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``SiteAnatomy`` is unchanged. This twin is a data path, not a box,
so "peeling" moves attention rightward, toward the vault:

    0  the estate people see: workloads and the consoles
    1  production's protection plumbing, and the gap at its edge
    2  inside the vault: its appliance, CyberSense, the clean room
"""

from __future__ import annotations

from twinkit.tour import (
    CameraTarget,
    Tour,
    TourResponse,
    TourSource,
    TourStep,
    camera_around,
    whole_map,
)

from .leveling import L
from .models import SiteAnatomy

#: The step the tests pin: the product's one idea lives here.
SIGNATURE_STEP_ID = "airgap-discipline"

_ESTATE = 0
_PLUMBING = 1
_VAULT = 2


def layer_map(anatomy: SiteAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    layers: dict[str, int] = {}
    for region in anatomy.regions:
        if region.kind in {"workload", "mgmt"}:
            layers[region.id] = _ESTATE
        elif region.kind in {"analytics", "recovery"}:
            layers[region.id] = _VAULT
        elif region.kind == "appliance" and region.x > _gap_x(anatomy):
            layers[region.id] = _VAULT
        else:
            layers[region.id] = _PLUMBING
    return layers


def _gap_x(anatomy: SiteAnatomy) -> float:
    gaps = [r for r in anatomy.regions if r.kind == "gap"]
    return gaps[0].x if gaps else anatomy.width / 2


def build_tour(anatomy: SiteAnatomy) -> Tour:
    """The PowerProtect tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 3.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    steps = [
        TourStep(
            id="two-sites",
            title="Two sites, one gap between them",
            script=L(
                novice=(
                    "This twin follows data, not a machine. The map has two sides. "
                    "On the left is production: the computers and databases an "
                    "organization runs on every day, plus a Dell PowerProtect Data "
                    "Domain, an appliance built only to store backups. On the right, "
                    "past a narrow strip called the air gap, is the Cyber Recovery "
                    "vault: a second Data Domain, drawn exactly the same size, "
                    "because what makes it special is not better hardware but the "
                    "fact that it is so hard to reach. Right now nothing is "
                    "protected yet, and all of the organization's data exists in "
                    "exactly one place."
                ),
                standard=(
                    "This twin follows the data rather than a machine. On the left "
                    "is production: virtual machines, databases, and a PowerProtect "
                    "Data Domain, Dell's purpose-built backup appliance. On the "
                    "right, beyond the air gap, is the Cyber Recovery vault, with a "
                    "second Data Domain. The vault appliance is the same hardware; "
                    "what protects it is that production cannot reach it. At this "
                    "step nothing is "
                    "protected yet: a few hundred terabytes exist in exactly one "
                    "place."
                ),
                expert=(
                    "Two sites. Left: production estate plus Data Domain. Right, "
                    "past the gap: Cyber Recovery vault, identical appliance. "
                    "Nothing protected yet."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["workload-vm", "workload-db", "dd-prod", "dd-vault"],
            layer_reveal=_ESTATE,
            trace_cursor=0,
            duration_ms=26_000,
        ),
        TourStep(
            id="first-backup",
            title="The first full backup lands",
            script=L(
                novice=(
                    "The first full backup runs. The backup software, PowerProtect "
                    "Data Manager, sends copies of the machines and databases to "
                    "the Data Domain on the left. It uses DD Boost, a way of "
                    "sending that does part of the work on the sending side, so "
                    "only pieces of data the appliance has never seen before "
                    "actually travel. Even this very first copy shrinks to about "
                    "a fifth of its size: 100 terabytes of backup fits in about 20 "
                    "on flash, in this illustrative example. Real computers repeat "
                    "themselves a lot, with the same system files everywhere and "
                    "the same attachment sent to forty people."
                ),
                standard=(
                    "The first full backup streams from PowerProtect Data Manager "
                    "(PPDM) to the production Data Domain over DD Boost, a protocol "
                    "that pushes part of the deduplication work to the client so "
                    "only segments the appliance has never seen cross the wire. "
                    "Even the first full reduces about 5:1: 100 TB of logical "
                    "backup becomes roughly 20 TB of physical flash (illustrative), "
                    "because real estates repeat themselves."
                ),
                expert=(
                    "First full over DD Boost: client-side segment filtering. "
                    "~5:1 on day one, 100 TB logical to ~20 TB stored (illustrative)."
                ),
            ),
            camera=frame("workload-vm", "workload-db", "backup-server", "dd-prod"),
            region_ids=["workload-vm", "workload-db", "backup-server", "dd-prod"],
            layer_reveal=_PLUMBING,
            trace_cursor=1,
            duration_ms=28_000,
        ),
        TourStep(
            id="dedupe-arithmetic",
            title="Logical and stored part ways",
            script=L(
                novice=(
                    "A month of daily backups piles up. Compare the two numbers "
                    "beside the map with the last step. Logical is how much data "
                    "the backups say they hold, and it went from 100 terabytes to "
                    "500. Stored is how much space they really take up, and it only "
                    "went from 20 to 25. Each new backup is mostly things the "
                    "appliance already has, so it keeps only a pointer to the old "
                    "copy plus the day's truly new pieces. This trick is called "
                    "deduplication. In this illustrative month, 500 terabytes of "
                    "backups sit in about 25 terabytes of flash, twenty to one. "
                    "That saving is what makes a whole second copy in a vault "
                    "affordable at all."
                ),
                standard=(
                    "A month of daily backups accumulates, and the counters part "
                    "ways: logical TB climbs from 100 to 500 while stored TB moves "
                    "only from 20 to 25. "
                    "Variable-length deduplication keeps only pointers plus each "
                    "day's genuinely new segments, so 500 TB of logical protection "
                    "occupies about 25 TB of flash, 20:1 here "
                    "(illustrative; Dell quotes up to 65:1 on the all-flash "
                    "appliance). This arithmetic is what makes weeks of restore "
                    "points, fast replication and an affordable vault possible."
                ),
                expert=(
                    "Variable-length dedupe over a month: 500 TB logical, ~25 TB "
                    "stored, 20:1 (illustrative; Dell claims up to 65:1). Stored "
                    "never exceeds logical."
                ),
            ),
            camera=frame("backup-server", "dd-prod"),
            region_ids=["backup-server", "dd-prod"],
            layer_reveal=_PLUMBING,
            trace_cursor=2,
            duration_ms=28_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="The gap opens from the vault side only",
            script=L(
                novice=(
                    "This is the moment the whole design is built around. The air "
                    "gap opens, and a copy crosses into the vault. Two things "
                    "matter. First, the vault decides when: it reaches out and "
                    "pulls the copy, on its own schedule. Nothing on the production "
                    "side, and no password stored there, can open the gap. Second, "
                    "only the new, deduplicated pieces cross, so the gap is open "
                    "for minutes, not days. Across the whole story the gap opens "
                    "exactly twice: now, to bring a copy in, and at the very end, "
                    "to send clean data back out. Both times the vault opens it. "
                    "The rest of the time it is closed and dark. Dell's largest "
                    "storage array, PowerMax, protects itself the same way, and "
                    "it has a model of its own here."
                ),
                standard=(
                    "This is the idea the whole design rests on. On the vault's "
                    "schedule, never "
                    "production's, the operational air gap opens and Data Domain "
                    "replication syncs the vault. The vault pulls: the connection "
                    "is initiated and controlled from inside the Cyber Recovery "
                    "vault, so no credential stored in production can open it. "
                    "Only deduplicated unique segments cross, so the window lasts "
                    "minutes, not days. The gap opens for exactly two phases, "
                    "replication in and recovery out, both from the vault side; "
                    "the rest of its life it is closed. The PowerMax twin's cyber "
                    "vault use case is this architecture."
                ),
                expert=(
                    "Air-gap discipline. Gap open only in replicate and "
                    "recover, both vault-initiated pulls or pushes. No production "
                    "credential opens it; deduped segments keep the window short."
                ),
            ),
            camera=frame("dd-prod", "gap", "dd-vault", pad=2.0),
            region_ids=["dd-prod", "gap", "dd-vault"],
            layer_reveal=_PLUMBING,
            trace_cursor=3,
            duration_ms=42_000,
        ),
        TourStep(
            id="seal",
            title="Sealed, and locked against everyone",
            script=L(
                novice=(
                    "The copy has arrived, and the vault seals itself. The network "
                    "path is cut. Then a feature called Retention Lock switches on. "
                    "It means write once, read many: until a set date passes, "
                    "nobody can change or delete that copy. Not an administrator, "
                    "and not someone with a stolen password. Dell says the "
                    "strictest version cannot be unlocked early even by Dell. The vault now holds "
                    "exactly what ransomware gangs hunt for first, a good backup, "
                    "and they cannot touch it. And this all happens before any "
                    "attack."
                ),
                standard=(
                    "Replication completes and the vault seals: the network path is "
                    "administratively severed and Retention Lock Compliance arms on "
                    "the vaulted copy. Retention Lock is WORM (write-once-read-many) "
                    "enforcement inside the Data Domain filesystem; until the "
                    "retention clock expires, no administrator, root shell or stolen "
                    "credential can modify or delete it; Dell states that the "
                    "compliance edition has no vendor back door either. The copy is sealed strictly before the "
                    "attack arrives."
                ),
                expert=(
                    "Gap closed. Retention Lock Compliance (WORM) armed: no admin "
                    "or root override until expiry, and no vendor override by Dell's "
                    "account. Sealed before the attack."
                ),
            ),
            camera=frame("gap", "dd-vault"),
            region_ids=["dd-vault"],
            layer_reveal=_VAULT,
            trace_cursor=4,
            duration_ms=26_000,
        ),
        TourStep(
            id="cybersense-scan",
            title="Asking which copy is clean",
            script=L(
                novice=(
                    "Inside the vault, a tool called CyberSense reads the locked "
                    "copy. Reading every file is the most demanding single job in "
                    "the story, so the playback lingers here, though by the clock "
                    "it is about four hours (illustrative). It looks for signs of "
                    "damage: "
                    "files that suddenly look scrambled, the way encrypted files "
                    "do, files renamed in bulk, broken databases. It compares each "
                    "copy with the ones before it. The question it answers is not "
                    "do we have a copy, but which copy is clean. Ransomware can "
                    "hide quietly for weeks before it strikes, and this is how you "
                    "avoid restoring the problem. The Cyber Detect twin asks the "
                    "same question on primary storage."
                ),
                standard=(
                    "The most expensive single operation in the trace, so the playback "
                    "dwells here; by the clock it is about four hours "
                    "(illustrative). CyberSense "
                    "indexes the locked copy and runs machine-learning analytics "
                    "over content features: entropy (encrypted files look "
                    "statistically different from documents), file-type "
                    "corruption, mass renames, database page damage, compared "
                    "against every previous scan. It answers the question that "
                    "decides a recovery: not whether a copy exists, but which copy "
                    "is clean, including after weeks of dwell time. The Cyber "
                    "Detect twin asks the same question on primary storage."
                ),
                expert=(
                    "Costliest stage (max dwell, ~4 h illustrative): CyberSense content analytics on the locked copy "
                    "(entropy, corruption, renames, DB pages), diffed against prior "
                    "scans. Output: the last clean restore point."
                ),
            ),
            camera=frame("dd-vault", "cybersense"),
            region_ids=["dd-vault", "cybersense"],
            layer_reveal=_VAULT,
            trace_cursor=5,
            duration_ms=34_000,
        ),
        TourStep(
            id="attack",
            title="The attack finds no vault",
            script=L(
                novice=(
                    "The bad night. Ransomware that had been hiding in production "
                    "goes off. It scrambles the computers and databases, deletes "
                    "the backup software's records using stolen administrator "
                    "passwords, and attacks the production Data Domain too. Look "
                    "at the right side of the map: nothing there lights up. The gap is "
                    "closed, so there is no network route to the vault at all, and "
                    "the passwords production held are useless, because the vault "
                    "only ever called out and never listened. What the attack "
                    "cannot reach, it cannot encrypt."
                ),
                standard=(
                    "Ransomware dwelling in the estate detonates: production volumes "
                    "encrypt, the backup server's catalog is deleted with stolen "
                    "admin credentials, and the production Data Domain comes under "
                    "attack. Nothing on the right half of the map lights up. The gap is "
                    "closed, so there is no route, no DNS entry and no session to "
                    "hijack, and production's replication credentials are useless "
                    "because the vault only ever called out. What the malware "
                    "cannot reach, it cannot encrypt."
                ),
                expert=(
                    "Detonation: prod volumes, PPDM catalog and prod DD hit. Vault, "
                    "CyberSense, clean room and gap all dark. No inbound path exists."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["workload-vm", "workload-db", "backup-server", "dd-prod"],
            layer_reveal=_VAULT,
            trace_cursor=6,
            duration_ms=30_000,
        ),
        TourStep(
            id="recover-from-vault",
            title="Recovery, on the vault's terms",
            script=L(
                novice=(
                    "Now recovery, and again the vault is in charge. In the clean "
                    "room, an isolated space inside the vault, the team uses "
                    "CyberSense's findings to pick the newest copy that is "
                    "definitely clean. Here that is the one copy in the vault, "
                    "scanned and not flagged four hours before the attack; if it "
                    "had been flagged they would step back to an older locked "
                    "copy, which is why a real vault keeps many days of them. They "
                    "practise the restore on a separate recovery computer first. "
                    "Only then does the vault open the gap for the second and last "
                    "time, and push clean data back to a rebuilt production Data "
                    "Domain. Flash storage makes this hours rather than weeks; Dell "
                    "quotes up to four times faster restores."
                ),
                standard=(
                    "Recovery runs at the vault's pace, from the vault's side. In "
                    "the clean room, the team uses CyberSense's verdicts to choose "
                    "the last provably clean restore point. Here that is the one "
                    "vaulted copy, scanned and not flagged four hours before "
                    "detonation; a flagged copy would send them back to an older "
                    "locked one, which is why a real vault retains many days of "
                    "them. The team rehearses on the isolated recovery host. "
                    "Only then does the vault open the gap outward, the second of "
                    "its two openings, and push clean data to a rebuilt production "
                    "Data Domain. Dell quotes up to 4x faster restores on all-flash."
                ),
                expert=(
                    "Clean-room restore: pick last clean point (1 scanned, 0 flagged), rehearse on the "
                    "recovery host, then vault-initiated push through the gap. Up "
                    "to 4x faster restore (Dell's claim)."
                ),
            ),
            camera=frame("dd-prod", "gap", "dd-vault", "recovery-host", pad=2.0),
            region_ids=["dd-vault", "recovery-host", "gap", "dd-prod"],
            layer_reveal=_VAULT,
            trace_cursor=7,
            duration_ms=30_000,
        ),
        TourStep(
            id="restored",
            title="Back, from data the attacker never touched",
            script=L(
                novice=(
                    "Everything is running again, restored from a copy that spent "
                    "the whole attack sealed behind a closed gap and a lock nobody "
                    "could open. Two ideas made that possible: deduplication made "
                    "a second copy cheap enough to keep, and the gap plus the lock "
                    "made it impossible to reach. The routine starts again, backup, "
                    "copy, lock, scan, because the vault's protection was never one "
                    "device. It was a habit that was already running before anyone "
                    "needed it. The block labelled DDMC / consoles lights here too: "
                    "DDMC is Data Domain Management Center, the screen administrators "
                    "use to watch the appliances. The timeline here is illustrative."
                ),
                standard=(
                    "Workloads run again, restored from a copy that spent the attack "
                    "behind a closed gap under Retention Lock. Dedupe made an "
                    "affordable vault possible; the air gap plus immutability made "
                    "it unreachable. The cycle resumes, backup, replicate, lock, "
                    "scan, because the protection was never a device but a routine "
                    "already running before anyone needed it. The consoles block lights "
                    "too: Data Domain Management Center (DDMC) and the PowerProtect "
                    "Data Manager (PPDM) console, watching the cycle. The lifecycle page "
                    "walks the same trace one step at a time."
                ),
                expert=(
                    "Restored from the sealed copy. Dedupe paid for the vault; gap "
                    "plus WORM kept it out of reach. Cycle resumes."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[
                "workload-vm", "workload-db", "backup-server",
                "dd-prod", "dd-vault", "mgmt",
            ],
            layer_reveal=_ESTATE,
            trace_cursor=8,
            duration_ms=26_000,
        ),
    ]

    return Tour(
        id="powerprotect-tour",
        title="A backup's life, through an attack and back",
        intro=L(
            novice=(
                "A guided walk that follows one organization's backups from the "
                "first copy, into a sealed vault, through a ransomware attack, and "
                "back again. Watch it play, or pause and click anything to look "
                "closer; the tour waits for you."
            ),
            standard=(
                "A narrated walk along the data's path, from first backup through "
                "the vault to recovery after an attack. Watch it play, or pause and "
                "explore; Resume tour brings the camera back."
            ),
            expert="Narrated lifecycle walk-through. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: SiteAnatomy) -> TourResponse:
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
