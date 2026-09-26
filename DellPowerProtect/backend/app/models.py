"""Data models for the PowerProtect Data Domain + Cyber Recovery twin.

Same conventions as the other twins in this repo: snake_case in Python,
camelCase over the wire (activeRegions, logicalTb, storedTb, regionIds,
...), so the React frontend can consume responses directly. None of the
fields here camelize ambiguously (no embedded numbers/acronyms), so no
explicit aliases are needed — if you add one that does, pin it with
``Field(alias=...)`` and check frontend/src/types.ts by hand (see CLAUDE.md).

The twist versus the hardware twins: the subject is a **data path across
two sites**, not one box. The anatomy is a left→right map (the way the
CloudIQ twin drew its pipeline): the production estate and its
PowerProtect Data Domain appliance on the left, the air gap in the middle,
and the Cyber Recovery vault — a second Data Domain, CyberSense analytics,
and a clean-room recovery host — on the right. The "power-on" trace is the
lifecycle of the data itself: backed up, deduplicated, replicated through
a briefly-open gap, locked immutable, scanned, attacked, and recovered.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from twinkit.models import CamelModel

RegionKind = Literal[
    "workload",   # the protected estate — VMs, databases, file shares
    "backup",     # the backup software/server (PowerProtect Data Manager)
    "appliance",  # PowerProtect Data Domain systems — production and vault
    "gap",        # the operational air gap between production and vault
    "analytics",  # CyberSense — ML integrity analytics inside the vault
    "recovery",   # the clean-room recovery host in the vault
    "mgmt",       # management planes (DDMC / PPDM console)
]

# Data-lifecycle phases, in order. Production hums, data is backed up and
# deduplicated, a copy crosses the briefly-open air gap into the vault and
# is locked immutable, CyberSense scans it — and then ransomware strikes
# production, and the vault is why the story ends well.
LifecyclePhase = Literal[
    "idle",       # the protected estate humming; nothing backed up yet
    "backup",     # first backup — clients stream to Data Domain via Boost
    "dedupe",     # weeks of backups accumulate; dedupe does its arithmetic
    "replicate",  # the air gap opens; deduplicated data crosses to the vault
    "airgap",     # the gap closes; Retention Lock arms — the copy is immutable
    "scan",       # CyberSense analyzes the vaulted copy for corruption patterns
    "attack",     # ransomware detonates in production — the vault is unreachable
    "recover",    # the vault opens on its own terms; a clean copy restores
    "restored",   # the estate is back, from data the attacker never touched
]


class Photo(CamelModel):
    """An image of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class SiteRegion(CamelModel):
    id: str
    kind: RegionKind
    label: str
    x: float
    y: float
    w: float
    h: float
    description: str
    photo: Photo | None = None


class SourceLink(CamelModel):
    label: str
    url: str


class Stat(CamelModel):
    label: str
    value: str


class SiteAnatomy(CamelModel):
    """The two-site data-path map, annotated. ``width``/``height`` set the viewBox."""

    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[SiteRegion]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class LifecycleState(CamelModel):
    """One step of the data lifecycle; pure data the renderer consumes.

    The telemetry pair is dedupe's arithmetic: ``logical_tb`` is the data
    the estate believes it has protected, ``stored_tb`` is the physical
    flash actually consumed. Their ratio is the number Data Domain is
    famous for.
    """

    step: int
    phase: LifecyclePhase
    label: str
    description: str
    # Region ids in the site map lit up at this step.
    active_regions: list[str]
    # Logical data protected so far, terabytes (monotonic).
    logical_tb: int
    # Physical capacity consumed after dedupe/compression, terabytes.
    stored_tb: int
    # Illustrative wall-clock hours since the first backup was scheduled.
    elapsed_hours: int
    # UI dwell ticks; long stages (the CyberSense scan) get more.
    cycle_cost: int = 1
    # CyberSense's verdicts so far: vaulted copies it has scanned, and how
    # many of those it flagged as damaged. Zero until the scan step; recovery
    # needs at least one scanned copy that was not flagged. (The cleaning
    # scenario does not tell this story and leaves both at zero.)
    copies_scanned: int = 0
    copies_flagged: int = 0


class LifecycleResponse(CamelModel):
    trace: list[LifecycleState]


# --- Failure scenario: cleaning / garbage collection -----------------------
#
# A second trace served beside the happy path (``?scenario=cleaning-gc``).
# It extends ``LifecycleState`` by subclassing, so the happy path's wire
# format does not gain a single key.

CleaningPhase = Literal[
    "steady",   # weeks in, the production appliance comfortably under its limit
    "expire",   # retention expires old backups; nothing physical comes back
    "ingest",   # new backups keep landing; used space keeps climbing
    "alert",    # the space-usage alert fires
    "clean",    # the scheduled cleaning (garbage collection) cycle runs
    "pinned",   # cleaning returned less than the estimate; find what holds the rest
    "release",  # drain replication lag, expire the stale snapshot; the lock stays
    "reclean",  # a second clean returns what was released
    "settled",  # steady again; locked data waits out its lock
]


class CleaningState(LifecycleState):
    """One step of the cleaning scenario. The extra fields are a capacity
    ledger that closes on every step:

    ``stored_tb == live_tb + reclaimable_tb + held_by_replication_tb
    + held_by_snapshot_tb + held_by_lock_tb``
    """

    phase: CleaningPhase  # type: ignore[assignment]
    # Usable capacity of the production appliance's active tier, terabytes.
    capacity_tb: int
    # Physical space still referenced by backups the catalog retains.
    live_tb: int
    # Dead space the next cleaning cycle can really return.
    reclaimable_tb: int
    # Dead to the backup catalog, but still referenced on the appliance:
    held_by_replication_tb: int  # by a replication snapshot not yet synced
    held_by_snapshot_tb: int     # by a snapshot nobody expired
    held_by_lock_tb: int         # by Retention Lock; the delete was refused
    # What the appliance reports as "Cleanable" - an estimate, per Dell.
    cleanable_tb: int
    # Physical space cleaning has returned so far (cumulative).
    reclaimed_tb: int
    # Days until the Retention Lock on the held copies ends.
    lock_days_left: int
    clean_running: bool = False
    # Regions in an alert condition at this step; drawn in the error colour.
    failed_regions: list[str] = Field(default_factory=list)
    # Alert text the administrator would see: Dell's space-usage alert
    # wording, carrying this scenario's illustrative threshold.
    alerts: list[str] = Field(default_factory=list)


class CleaningResponse(CamelModel):
    scenario: str
    trace: list[CleaningState]


class ScenarioInfo(CamelModel):
    """One selectable trace on the lifecycle endpoint."""

    id: str
    title: str
    summary: str
    hero: str  # the number to watch
    is_failure: bool
    # Page prose for the lifecycle page, leveled like everything else: the
    # paragraph under the heading, and the note under the counters. Empty
    # means the page keeps its own wording.
    intro: str = ""
    counters_note: str = ""
    sources: list[SourceLink] = Field(default_factory=list)


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to data protection;
    # spell out jargon (dedupe, Boost, Retention Lock, air gap, CyberSense,
    # RPO/RTO, ...) on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "up to 65:1 data reduction on the all-flash appliance"
    # Site regions this category slots into (ids from anatomy.py).
    region_ids: list[str] = Field(default_factory=list)
    options: list[CatalogOption]


class UseCaseItem(CamelModel):
    category_id: str
    option_id: str
    qty: int
    rationale: str


class UseCase(CamelModel):
    id: str
    title: str
    summary: str
    narrative: list[str]  # paragraphs
    config: list[UseCaseItem]
    outcomes: list[Stat] = Field(default_factory=list)
