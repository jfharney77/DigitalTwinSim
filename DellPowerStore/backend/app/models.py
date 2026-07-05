"""Data models for the PowerStore digital twin.

Same conventions as the GPU and R760 apps: snake_case in Python, camelCase
over the wire (activeRegions, powerWatts, regionIds, ...), so the React
frontend can consume responses directly. None of the fields here camelize
ambiguously (no embedded numbers/acronyms), so no explicit aliases are
needed — if you add one that does, pin it with ``Field(alias=...)`` and
check frontend/src/types.ts by hand (see CLAUDE.md).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "storage",     # NVMe drive bay + backplane
    "nvram",       # NVMe NVRAM write-cache drive slots
    "cpu",         # per-node Xeon socket + heatsink
    "memory",      # per-node DDR4/DDR5 DIMM banks
    "io",          # embedded module mezz ports, hot-swap I/O modules
    "power",       # per-node PSUs
    "cooling",     # per-node fan packs
    "battery",     # battery backup units (cache vaulting)
    "management",  # management / service ports
    "board",       # node system board, node interconnect
]

PowerPhase = Literal["off", "power", "boot", "drives", "cluster", "services", "online"]


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Photo(CamelModel):
    """A photograph of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class ChassisRegion(CamelModel):
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


class ChassisAnatomy(CamelModel):
    """One appliance enclosure, annotated. ``width``/``height`` set the viewBox."""

    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[ChassisRegion]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class PowerOnState(CamelModel):
    """One step of the power-on sequence; pure data the renderer consumes."""

    step: int
    phase: PowerPhase
    label: str
    description: str
    # Region ids in the chassis anatomy lit up at this step.
    active_regions: list[str]
    power_watts: int
    fan_percent: int = Field(ge=0, le=100)
    # Illustrative wall-clock seconds since AC plug-in (not measured timing).
    elapsed_seconds: int
    # UI dwell ticks; long stages (node boot, pool assembly) get more.
    cycle_cost: int = 1


class PowerOnResponse(CamelModel):
    trace: list[PowerOnState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to storage arrays;
    # spell out Dell jargon (NVRAM, PowerStoreOS, vVols, ...) on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "2 nodes per appliance"
    # Chassis regions this category slots into (ids from anatomy.py).
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
