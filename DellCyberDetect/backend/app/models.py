"""Data models for the Dell Cyber Detect ransomware-detection twin.

Same conventions as the other twins in this repo: snake_case in Python,
camelCase over the wire (activeRegions, snapshotsCorrupted, metadataAlerts,
lastCleanSnapshot, regionIds, ...), so the React frontend consumes responses
directly. None of the fields here camelize ambiguously (no embedded
numbers/acronyms), so no explicit aliases are needed — if you add one that
does, pin it with ``Field(alias=...)`` and check frontend/src/types.ts by
hand (see CLAUDE.md).

The twist versus the PowerProtect twin already here: that one is about
*isolation*. Put a copy of the data somewhere the attacker cannot reach,
seal it, and you have somewhere to recover from. It is a good answer and it
leaves one question conspicuously open — recover from *which* copy? A vault
full of faithfully replicated, immutably locked, thoroughly corrupted
snapshots has protected exactly nothing. Restoring from an already-infected
backup is not a hypothetical failure mode; it is the common one.

Cyber Detect answers that question, and the way it answers it is the reason
for this twin. Conventional detection watches metadata and behaviour: file
extensions changing, entropy spiking, mass renames, unusual I/O rates.
Attackers have spent years learning to defeat exactly that — encrypt
slowly, preserve extensions, mimic the I/O profile of ordinary work. So
Cyber Detect opens the files and reads the bytes, running content analysis
trained on thousands of ransomware variants directly against snapshots on
the array. You can disguise how data was written. You cannot disguise
whether it is still intelligible.

``metadata_alerts`` is on every state and stays at zero while corruption is
actively spreading — that is not a bug in the model, it is the premise, and
``tests/test_engine.py`` asserts it.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "array",       # the production volume being written to
    "snapshot",    # one point-in-time copy on the array's timeline
    "inspect",     # content inspection: opening files and reading bytes
    "classifier",  # the trained model scoring what the inspection found
    "models",      # the variant corpus the classifier was trained against
    "verdict",     # the forensic report — and the date it names
    "recovery",    # restoring from the copy the verdict identified
]

# The life of an attack and its detection. Note where the first six phases
# put the reader: inside an incident that nothing has noticed yet.
DetectPhase = Literal[
    "clean",      # normal operations; snapshots on schedule
    "intrusion",  # the attacker is inside, doing nothing visible
    "encrypt",    # corruption begins, deliberately shaped to look ordinary
    "blind",      # metadata and behaviour detection see nothing at all
    "inspect",    # content inspection reads the actual bytes in each snapshot
    "classify",   # the trained model scores every snapshot
    "verdict",    # the deliverable: the last provably clean copy, by name
    "recover",    # restore from that specific copy
    "restored",   # back to a known-good baseline
]


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Photo(CamelModel):
    """An image of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class DetectRegion(CamelModel):
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


class DetectAnatomy(CamelModel):
    """The detection map. ``width``/``height`` set the viewBox.

    The middle band is a *timeline* — snapshots left to right, oldest to
    newest — because the product's whole output is a point on it.
    """

    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[DetectRegion]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class DetectState(CamelModel):
    """One step in the life of an attack; pure data the renderer consumes.

    ``metadata_alerts`` exists to be zero. Everything the industry
    conventionally detects with — extension changes, entropy spikes, mass
    renames, I/O anomalies — is silent throughout this incident, because
    the attack was built to keep it silent. That silence is the argument
    for reading content instead.

    ``last_clean_snapshot`` is the deliverable. It is ``-1`` until the
    verdict, because a detection product that produces an alert rather than
    a date has not finished its job: knowing you were attacked is not the
    same as knowing what to restore.
    """

    step: int
    phase: DetectPhase
    label: str
    description: str
    # Region ids in the detection map lit up at this step.
    active_regions: list[str]
    # Snapshots on the array's timeline so far.
    snapshots_taken: int = Field(ge=0)
    # How many of them contain corrupted data.
    snapshots_corrupted: int = Field(ge=0)
    # Alerts raised by metadata and behaviour analysis. Stays at zero.
    metadata_alerts: int = 0
    # Confidence from content inspection, percent. Zero until bytes are
    # actually read; there is no shortcut to it.
    content_confidence_percent: int = Field(ge=0, le=100)
    # Index of the last snapshot proven clean; -1 before the verdict.
    last_clean_snapshot: int = -1
    # Illustrative hours since the intrusion began.
    elapsed_hours: int
    # UI dwell ticks; reading every byte of every snapshot is the long one.
    cycle_cost: int = 1


class DetectResponse(CamelModel):
    trace: list[DetectState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to cyber recovery;
    # spell out jargon (entropy, dwell time, indicators of compromise,
    # immutability, RPO, false positive, forensic report) on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "99.99% detection accuracy"
    # Detection-map regions this category slots into (ids from anatomy.py).
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
