"""Data models for the Dell NativeEdge digital twin.

Same conventions as the other twins in this repo: snake_case in Python,
camelCase over the wire (activeRegions, endpointsOnline, operatorActions,
regionIds, ...), so the React frontend can consume responses directly. None
of the fields here camelize ambiguously (no embedded numbers/acronyms), so
no explicit aliases are needed — if you add one that does, pin it with
``Field(alias=...)`` and check frontend/src/types.ts by hand (see CLAUDE.md).

Like the CloudIQ twin, the subject is **software, not a box**, so both
shared metaphors adapt: the "anatomy" is a platform architecture diagram
(edge endpoints on the far left, many and identical; the Orchestrator
central and singular; blueprints, catalog, policy, and observability to the
right), and the "power-on trace" is the **zero-touch onboarding of one
site's endpoints** — from a sealed crate to a managed estate.

The one idea: **nobody touches the device.** Every hardware twin in this
repo assumes a person at the moment of truth — someone presses the R760's
power button, racks the XE9712, plugs in the Alienware. Edge estates break
that assumption at scale: four hundred sites, no IT staff at any of them.
NativeEdge inverts the direction of trust — the device wakes, proves
cryptographically that it is the machine Dell built, and asks the
Orchestrator what it should become. ``operator_actions`` is this twin's
``droppedPackets``: it exists to be **1** (power and a network cable), and
it never increments again.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "endpoint",       # the edge devices themselves — many, identical, remote
    "network",        # the WAN between sites and the Orchestrator
    "identity",       # secure device onboarding: attestation, device identity
    "orchestrator",   # the NativeEdge Orchestrator — central and singular
    "blueprint",      # declarative site definitions: what each site runs
    "catalog",        # the application catalog (Dell, ISV, customer apps)
    "policy",         # Zero Trust and security policy enforcement
    "observability",  # telemetry, health, and AIOps integration
]

# The zero-touch onboarding of one site, in order. The only human action in
# the entire sequence is the `power` phase — everything downstream is
# pulled by the device, never pushed by a person.
OnboardPhase = Literal[
    "crated",     # the box arrives at the site; nothing is configured
    "power",      # power + network applied — the ONLY human action
    "attest",     # the device proves hardware integrity and identity
    "onboard",    # the Orchestrator claims it into the estate
    "provision",  # OS and platform software land
    "blueprint",  # the declarative site definition is applied
    "workload",   # applications from the catalog start
    "managed",    # steady state: policy enforced, telemetry flowing
]


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Photo(CamelModel):
    """An image of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class PlatformRegion(CamelModel):
    """One functional block of the edge platform, placed in the diagram."""

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


class PlatformMap(CamelModel):
    """The edge-platform architecture diagram. ``width``/``height`` set the
    viewBox; the flow runs left (the estate) to right (control & insight)."""

    id: str
    name: str
    vendor: str
    form_factor: str  # e.g. "Edge operations software platform"
    generation: str
    year: int
    width: float
    height: float
    regions: list[PlatformRegion]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class OnboardState(CamelModel):
    """One step of the zero-touch onboarding; pure data the renderer consumes.

    ``operator_actions`` exists to be 1. It is 0 while the crate sits
    sealed, becomes 1 when someone supplies power and a network cable, and
    never increments again — no state in this trace requires a local
    operator, which is the platform's entire reason for existing.
    """

    step: int
    phase: OnboardPhase
    label: str
    description: str
    # Region ids in the platform map lit up at this step.
    active_regions: list[str]
    # Endpoints claimed into the estate and reporting, 0 → N. The
    # Orchestrator itself is never counted — it is the thing doing the
    # claiming, not the thing being claimed.
    endpoints_online: int = Field(ge=0)
    # Local human actions taken so far. Reaches 1 at the power phase
    # (power + network cable) and stays there forever.
    operator_actions: int = Field(ge=0, le=1)
    # Whether the device has cryptographically proven it is the machine
    # Dell built. Nothing runs before this is true; once true, never false.
    trust_established: bool = False
    # Site bring-up progress, monotonic 0 → 100.
    progress_percent: int = Field(ge=0, le=100)
    # Illustrative wall-clock seconds since the crate was opened.
    elapsed_seconds: int
    # UI dwell ticks; the long stage (attestation) gets more.
    cycle_cost: int = 1


class OnboardResponse(CamelModel):
    trace: list[OnboardState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to edge operations;
    # spell out jargon (zero-touch, attestation, blueprint, ISV, ZTP, ...)
    # on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "one Orchestrator instance per estate"
    # Platform regions this category slots into (ids from anatomy.py).
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
