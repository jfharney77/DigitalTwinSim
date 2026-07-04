"""Data models for the PowerEdge R760 digital twin.

Same conventions as the GPU app: snake_case in Python, camelCase over the
wire (activeRegions, powerWatts, regionIds, ...), so the React frontend can
consume responses directly. None of the fields here camelize ambiguously
(no embedded numbers/acronyms), so no explicit aliases are needed — if you
add one that does, pin it with ``Field(alias=...)`` and check
frontend/src/types.ts by hand (see CLAUDE.md).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "storage",     # drive bay/backplane, RAID controller, boot module
    "cooling",     # hot-swap fans
    "cpu",         # processor socket + heatsink
    "memory",      # DDR5 DIMM banks
    "power",       # PSUs, power distribution board
    "expansion",   # PCIe risers, OCP 3.0 NIC slot
    "management",  # iDRAC baseboard management controller
    "board",       # system board, PCH, battery
]

PowerPhase = Literal["off", "standby", "bmc", "poweron", "post", "boot", "os"]


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
    """One server chassis, annotated. ``width``/``height`` set the viewBox."""

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
    # UI dwell ticks; long stages (memory training, drive spin-up) get more.
    cycle_cost: int = 1


class PowerOnResponse(CamelModel):
    trace: list[PowerOnState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to Dell servers;
    # spell out Dell jargon (PERC, BOSS, OCP, iDRAC, ...) on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "2 sockets max"
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
