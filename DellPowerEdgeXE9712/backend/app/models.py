"""Data models for the PowerEdge XE9712 digital twin.

Same conventions as the other twins in this repo: snake_case in Python,
camelCase over the wire (activeRegions, powerWatts, gpusInDomain,
regionIds, ...), so the React frontend can consume responses directly. None
of the fields here camelize ambiguously (no embedded numbers/acronyms), so
no explicit aliases are needed — if you add one that does, pin it with
``Field(alias=...)`` and check frontend/src/types.ts by hand (see CLAUDE.md).

The twist versus the chassis twins (R760, PowerStore, PowerMax): the subject
is a *rack-scale system*, not one server. The Dell PowerEdge XE9712 is a
whole liquid-cooled rack built around NVIDIA GB200 NVL72: 18 compute trays
(36 NVIDIA Grace CPUs + 72 Blackwell GPUs) and 9 NVLink switch trays joined
by a copper cable cartridge, so the "anatomy" is a front-of-rack elevation
and the "power-on" trace ends with the signature move no earlier twin has —
the NVLink fabric *fusing* all 72 GPUs into one giant accelerator.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "gpu",         # per-tray NVIDIA Blackwell GPUs (the reason the rack exists)
    "compute",     # per-tray NVIDIA Grace Arm CPUs
    "network",     # per-tray scale-out NICs / DPUs (InfiniBand or Spectrum-X)
    "nvswitch",    # shared NVLink switch trays — the scale-up fabric
    "cooling",     # liquid loop: in-rack CDU and the coolant manifolds
    "power",       # power shelves feeding the rack's DC busbar
    "management",  # rack management switch + every tray's BMC path
]

# Rack power-on phases, in order. Power and coolant must be flowing before
# any silicon wakes; trays boot in lockstep; then the NVLink fabric trains
# and fuses the GPUs into a single 72-GPU domain.
PowerOnPhase = Literal[
    "off",         # rack integrated and cabled, everything dark
    "power",       # power shelves energize the busbar, management wakes
    "coolant",     # CDU pumps prime the manifolds — liquid before silicon
    "trayboot",    # 18 compute trays power on; Grace CPUs boot in lockstep
    "gpuinit",     # Blackwell GPUs power up on their cold plates
    "fabric",      # NVLink switch trays boot and 5,000+ links train
    "fused",       # all 72 GPUs join one NVLink domain — one giant GPU
    "ready",       # burn-in passed; the rack accepts jobs
]


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Photo(CamelModel):
    """An image of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class RackRegion(CamelModel):
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


class RackAnatomy(CamelModel):
    """The rack floorplan, annotated. ``width``/``height`` set the viewBox."""

    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[RackRegion]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class PowerOnState(CamelModel):
    """One step of the rack power-on sequence; pure data the renderer consumes."""

    step: int
    phase: PowerOnPhase
    label: str
    description: str
    # Region ids in the rack anatomy lit up at this step.
    active_regions: list[str]
    # Whole-rack draw in watts — a loaded NVL72 rack runs near 120 kW.
    power_watts: int
    # GPUs joined into the unified NVLink domain, 0 → 72. This replaces the
    # chassis twins' fanPercent: the number that matters in this rack is not
    # airflow but how many GPUs the fabric has fused into one accelerator.
    gpus_in_domain: int = Field(ge=0, le=72)
    # Illustrative wall-clock seconds since the power shelves energized.
    elapsed_seconds: int
    # UI dwell ticks; long stages (GPU init, NVLink fabric training) get more.
    cycle_cost: int = 1


class PowerOnResponse(CamelModel):
    trace: list[PowerOnState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to rack-scale AI;
    # spell out Dell and NVIDIA jargon (NVLink, superchip, CDU, DPU, ...)
    # on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "18 compute trays + 9 NVLink switch trays per rack"
    # Rack regions this category slots into (ids from anatomy.py).
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
