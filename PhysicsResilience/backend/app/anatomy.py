"""Resilience maps — one shared two-site diagram (production estate on
the left, air gap, vault on the right, with the detection, queue, and
access-graph blocks), reused by all four products with per-product
overviews. The left/right split is the PowerProtect twin's geometry,
honored here: everything the incident can reach is left of the gap."""

from __future__ import annotations

from .leveling import L
from .models import SCOPE_NOTE, MapRegion, ResilienceMap


def _regions() -> list[MapRegion]:
    return [
        MapRegion(
            id="estate", kind="estate", label="Production estate",
            x=2, y=1, w=56, h=14,
            description=(
                "The VMs, shares, and arrays being protected. Colored "
                "by corrupted fraction — the incident script's damage, "
                "expressed only as terabytes and timestamps."
            ),
        ),
        MapRegion(
            id="backup", kind="backup", label="Backup repository",
            x=2, y=19, w=56, h=12,
            description=(
                "The standard repository — reachable from production, "
                "which is exactly its weakness: the incident corrupts "
                "these copies too. Colored by the share of copies lost."
            ),
        ),
        MapRegion(
            id="analytics", kind="analytics", label="Cyber Detect scan",
            x=2, y=35, w=27, h=10,
            description=(
                "Content analysis over the copies. Its color is the "
                "corruption score a scanner would read; the sensitivity "
                "knob trades detection latency against false alarms — "
                "the ROC curve, taught by knob."
            ),
        ),
        MapRegion(
            id="queue", kind="queue", label="Alert queue",
            x=31, y=35, w=27, h=10,
            description=(
                "Where alerts wait for a human. Colored by backlog — "
                "in-house teams drain it business-hours-only, and the "
                "real alert waits behind the noise. The 2 a.m. problem "
                "lives here."
            ),
        ),
        MapRegion(
            id="responder", kind="responder", label="Response",
            x=2, y=49, w=56, h=8,
            description=(
                "Whoever acts: in-house (capacity-bound, office-hours) "
                "or MDR (24/7, minutes). Containment stops the spread; "
                "everything before it is blast radius."
            ),
        ),
        MapRegion(
            id="gap", kind="gap", label="AIR GAP",
            x=61, y=1, w=6, h=56,
            description=(
                "The operational air gap — closed except during "
                "scheduled sync windows, opened from the vault side. "
                "Lit only in the moments it is open. Everything right "
                "of this strip is unreachable from production."
            ),
        ),
        MapRegion(
            id="vault", kind="vault", label="Cyber Vault",
            x=70, y=1, w=28, h=30,
            description=(
                "Locked, immutable copies behind the gap. The incident "
                "cannot reach them — the tests assert it — so the "
                "question the vault answers is never 'did a copy "
                "survive?' but 'which one, and how old?'"
            ),
        ),
        MapRegion(
            id="identity", kind="identity", label="Identities",
            x=70, y=35, w=13, h=10,
            description=(
                "Fort Zero's actors: users and devices. The compromise "
                "event marks one hostile (abstractly) and the flood "
                "measures what it can reach."
            ),
        ),
        MapRegion(
            id="segments", kind="segment", label="Segments",
            x=86, y=35, w=12, h=10,
            description=(
                "Micro-segmentation: more segments, smaller flood. "
                "Colored by segment size — smaller is safer and "
                "chattier."
            ),
        ),
        MapRegion(
            id="policy", kind="policy", label="Policy checks",
            x=70, y=49, w=28, h=8,
            description=(
                "The friction meter: policy evaluations per session. "
                "Zero trust is not free — this block is its honest "
                "price."
            ),
        ),
    ]


def _map(map_id: str, name: str, gen: str, overview: str) -> ResilienceMap:
    return ResilienceMap(
        id=map_id,
        name=name,
        vendor="Dell Technologies",
        form_factor="Two-site resilience view",
        generation=gen,
        year=2026,
        width=100,
        height=59,
        overview=overview,
        regions=_regions(),
        sources=[
            {"label": "physics_specs/05-security-resilience.md (this repo)",
             "url": "../physics_specs/05-security-resilience.md"},
            {"label": "Scope boundary", "url": SCOPE_NOTE},
        ],
    )


POWERPROTECT = _map(
    "powerprotect",
    "PowerProtect · backup & Cyber Vault",
    "Data Domain + Cyber Recovery",
    L(
        novice=(
            "Two buildings, drawn left and right. On the left: the "
            "systems being protected and their everyday backups — "
            "which live close enough to production that a disaster "
            "that encrypts one usually encrypts both. On the right, "
            "behind a strip that is almost always closed: the vault, "
            "where copies are locked so that nothing — including an "
            "administrator — can alter them. The simulator's incident "
            "is deliberately abstract (corruption starting at a time, "
            "spreading at a rate); what it teaches is which copies "
            "are still there afterwards, and how long getting them "
            "back takes. Restoring two hundred terabytes through a "
            "one-gigabyte-per-second pipe is days, and that "
            "arithmetic surprises everyone once."
        ),
        standard=(
            "The backup topology as physics: repository copies are "
            "reachable from production and the incident corrupts them "
            "(spec 05's common, devastating pattern, shown "
            "abstractly); vault copies behind the operational air gap "
            "survive — the tests assert the gap holds. RPO is the "
            "last-clean-point age; RTO = decision hours + TB ÷ "
            "restore-throughput (the '200 TB at N GB/s takes days' "
            "surprise, done live); retention × change-rate ÷ dedupe "
            "is the capacity line. The DellPowerProtect twin (:5183) "
            "narrates this architecture; this app runs it under the "
            "scrubber."
        ),
        expert=(
            "Repo dies with prod; vault survives by construction "
            "(asserted). RPO = clean-point age; RTO = decide + "
            "TB/GBps — days at scale. Retention·Δ/dedupe fills the "
            "line. The twin narrates; this scrubs."
        ),
    ),
)

CYBERDETECT = _map(
    "cyberdetect",
    "Cyber Detect · content-level detection",
    "Index Engines analytics",
    L(
        novice=(
            "The same two buildings, plus a scanner that actually "
            "reads the backup copies' contents. Without it, the "
            "first anyone learns of quiet corruption is when a "
            "restore comes back ruined — and the recovery starts "
            "over from an older copy, twice as slow. With it, the "
            "scanner names the last clean copy before anyone "
            "restores anything. The knob is sensitivity: turned up, "
            "it catches trouble earlier and cries wolf more often, "
            "and every false alarm costs an afternoon of "
            "investigation. There is no setting without a price; "
            "there is only choosing which price."
        ),
        standard=(
            "The detection layer on the same timeline: latency = "
            "base ÷ sensitivity (doubled for low-and-slow), false "
            "alarms ∝ sensitivity at 3 h of investigation each — the "
            "ROC trade as a slider. The payoff is the restore path: "
            "detection names the last clean point (one restore); "
            "without it the newest copy restores corrupt and the "
            "failed-restore penalty doubles RTO — both branches "
            "asserted. Companion: DellCyberDetect (:5192), whose "
            "'the deliverable is a date' idiom this app inherits."
        ),
        expert=(
            "latency = base/sens (×2 slow); FP ∝ sens × 3 h. "
            "Detected → 1 restore; blind → corrupt-first, RTO ×~2. "
            "The date is the deliverable."
        ),
    ),
)

MDR = _map(
    "mdr",
    "MDR · managed detection & response",
    "Dell MDR service",
    L(
        novice=(
            "Detection is only half the clock; someone must act. "
            "This mode runs the alert queue: dozens of routine "
            "alerts a day, a small team that works office hours — "
            "and an incident that begins at two in the morning on a "
            "Saturday. Watch the damage accumulate until Monday's "
            "first triage, then rerun with a 24/7 response service "
            "and watch the same incident die in minutes. Same "
            "detection, different clocks; the blast radius is the "
            "area under the delay."
        ),
        standard=(
            "The alert-queue operations game: noise at N/day, "
            "in-house capacity drained business-hours-only (backlog "
            "grows nights and weekends), MDR at 24/7 with "
            "minutes-scale triage. Containment stops the spread, so "
            "blast radius = rate × time-to-contain — the 2 a.m. "
            "Saturday scenario is the headline, and alert fatigue "
            "(raise the noise, watch the real alert wait) is the "
            "second lesson. Both asserted."
        ),
        expert=(
            "Backlog integrates off-hours; contain = f(clock, "
            "queue). Blast = rate × TTC. 2 a.m. Saturday and "
            "fatigue, both pinned."
        ),
    ),
)

FORTZERO = _map(
    "fortzero",
    "Fort Zero · the access graph",
    "DoD-aligned zero trust",
    L(
        novice=(
            "A different question: not 'will a copy survive?' but "
            "'what can a stolen identity reach?' The simulator marks "
            "one user hostile — abstractly, a flag, no technique — "
            "and floods the map of who-may-reach-what. Inside a "
            "traditional perimeter, that flood touches nearly "
            "everything, because inside means trusted. Under zero "
            "trust it touches only what that one identity was "
            "explicitly granted — a handful of things — and "
            "splitting the estate into segments shrinks it further. "
            "The honest cost is friction: every session now answers "
            "several checks instead of one, and unused permissions "
            "quietly pile up unless someone reviews them."
        ),
        standard=(
            "The access-graph mode: blast radius = reachable-asset "
            "count. Perimeter: one compromise floods ~90% of assets. "
            "Zero trust: grants-per-user ÷ segments, plus whatever "
            "stale grants entropy has added (0.5/user/month without "
            "review — least-privilege decay, prunable by the "
            "access-review event). The friction meter (checks per "
            "session, 9 vs 1) keeps the comparison honest. The "
            "DellFortZero twin (:5195) argues the architecture; this "
            "mode counts it."
        ),
        expert=(
            "Radius: perimeter ≈ 0.9N; ZT ≈ grants/segments + "
            "decay(0.5/u/mo, review-prunable). Friction 9 vs 1 "
            "checks. The twin argues; this counts."
        ),
    ),
)


MAPS: dict[str, ResilienceMap] = {
    "powerprotect": POWERPROTECT,
    "cyberdetect": CYBERDETECT,
    "mdr": MDR,
    "fortzero": FORTZERO,
}
