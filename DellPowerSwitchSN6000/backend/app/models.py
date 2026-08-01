"""Data models for the PowerSwitch SN6000 AI-fabric digital twin.

Same conventions as the other twins in this repo: snake_case in Python,
camelCase over the wire (activeRegions, fabricTbps, droppedPackets,
regionIds, ...), so the React frontend can consume responses directly. None
of the fields here camelize ambiguously (no embedded numbers/acronyms), so
no explicit aliases are needed — if you add one that does, pin it with
``Field(alias=...)`` and check frontend/src/types.ts by hand (see CLAUDE.md).

The twist versus the E3200 campus-switch twin: that twin is one 1RU box
booting a network OS. This one is a **fabric** — a leaf/spine topology of
NVIDIA Spectrum-6-based PowerSwitch SN6000 switches (1.6 Tb/s ports, up to
409.6 Tb/s of switching capacity, liquid cooling and co-packaged optics
options) joining GPU racks into one training cluster. The XE9712 twin's
NVLink domain stops at the rack wall; this is what carries traffic past it.

The subject is therefore a *property*, not a box: an AI fabric's whole
reason for existing is that it does not drop packets under the brutal
many-to-one bursts that collective operations produce. ``dropped_packets``
is on every state and is zero on every step — enforced in
``tests/test_engine.py``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "spine",      # spine switches — every leaf connects to every one of them
    "leaf",       # leaf (top-of-rack) switches — where the GPU racks attach
    "endpoint",   # the GPU racks themselves, as fabric endpoints
    "optics",     # the optics layer: transceivers or co-packaged optics
    "telemetry",  # the congestion-control and telemetry engine
    "cooling",    # liquid cooling for the switch silicon
    "management", # fabric management / network OS control plane
]

# The fabric's life, in order: bring-up, then a training step's collective
# and the congestion it provokes.
FabricPhase = Literal[
    "off",         # racked and cabled, dark
    "power",       # switches power on, network OS boots
    "linktrain",   # every leaf-to-spine and leaf-to-endpoint link trains
    "topology",    # routing converges; the leaf/spine fabric becomes one fabric
    "ready",       # fabric idle and ready, no job traffic yet
    "collective",  # an all-reduce runs — every GPU exchanging gradients at once
    "congestion",  # incast: many senders, one receiver, buffers filling
    "reroute",     # adaptive routing spreads the flows; congestion clears
    "steady",      # the training loop's traffic pattern, sustained
]


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Photo(CamelModel):
    """An image of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class FabricRegion(CamelModel):
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


class FabricAnatomy(CamelModel):
    """The leaf/spine topology map. ``width``/``height`` set the viewBox."""

    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[FabricRegion]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class FabricState(CamelModel):
    """One step of the fabric's life; pure data the renderer consumes.

    ``dropped_packets`` exists to be zero. A lossless fabric is the whole
    product claim, so the field is carried explicitly on every state and
    asserted zero in the tests — including at peak congestion, where a
    conventional Ethernet fabric would be discarding frames.
    """

    step: int
    phase: FabricPhase
    label: str
    description: str
    # Region ids in the fabric map lit up at this step.
    active_regions: list[str]
    # Aggregate traffic crossing the fabric, terabits per second.
    fabric_tbps: int
    # Utilization of the busiest link, percent — the number that matters,
    # since a collective runs at the speed of its slowest path.
    peak_link_percent: int = Field(ge=0, le=100)
    # Packets discarded. Always zero: the fabric pauses or reroutes instead.
    dropped_packets: int = 0
    # Illustrative wall-clock seconds since power was applied.
    elapsed_seconds: int
    # UI dwell ticks; long stages (link training) get more.
    cycle_cost: int = 1


class FabricResponse(CamelModel):
    trace: list[FabricState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to AI networking;
    # spell out jargon (leaf/spine, incast, RoCE, ECN/PFC, adaptive routing,
    # CPO, SHARP, ...) on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "409.6 Tb/s switching capacity per system"
    # Fabric regions this category slots into (ids from anatomy.py).
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
