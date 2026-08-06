"""Data models for the PowerEdge XE9680 digital twin.

Same conventions as the other twins in this repo: snake_case in Python,
camelCase over the wire (activeRegions, powerWatts, gpusInDomain, nicsUp,
regionIds, ...), so the React frontend can consume responses directly. None
of the fields here camelize ambiguously (no embedded numbers/acronyms), so
no explicit aliases are needed — if you add one that does, pin it with
``Field(alias=...)`` and check frontend/src/types.ts by hand (see CLAUDE.md).

The twist versus the XE9712 rack twin: the subject is back to being *one
server* — the Dell PowerEdge XE9680, an 8-GPU HGX box that fits a standard
rack. Its NVLink domain is eight GPUs and stops at the chassis wall; scale
past eight comes from giving every GPU its own dedicated NIC and racking
thousands of identical boxes. That is the machine xAI's Colossus was first
built from, and the twin's two hero counters — ``gpusInDomain`` (0 → 8,
atomic, never more) and ``nicsUp`` (0 → 8, one per GPU) — carry that story.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "gpu",         # the eight SXM accelerators on the HGX baseboard
    "nvswitch",    # the NVSwitch complex that fuses them — in-box scale-up
    "compute",     # the x86 host: two Xeons and their DIMMs
    "network",     # per-GPU scale-out NICs — one 400 GbE port per GPU
    "storage",     # front NVMe bay feeding the training data in
    "cooling",     # fan banks — this server moves heat with air (or DLC on the L)
    "power",       # the PSU bank feeding ~11 kW through a 6U chassis
    "management",  # iDRAC — the BMC that sequences all of this
]

# Server power-on phases, in order. The host boots first (a GPU server is
# still a server), then the accelerators wake, fuse into an 8-GPU NVLink
# domain, and finally the per-GPU NICs join the data-center fabric — the
# order encodes the architecture: NVLink inside the box, Ethernet beyond it.
PowerOnPhase = Literal[
    "off",       # racked, cabled, dark
    "power",     # PSUs energize, iDRAC wakes on standby power
    "post",      # the two Xeons boot: BIOS, memory training, PCIe enumeration
    "gpuinit",   # eight SXM GPUs wake; HBM trains; fans ramp — the long stage
    "fuse",      # NVSwitch fuses the eight into one NVLink domain — atomic
    "fabric",    # eight NICs train 400 GbE links — one per GPU — to the leaf
    "ready",     # burn-in passed; the server joins the cluster scheduler
]


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Photo(CamelModel):
    """An image of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class ServerRegion(CamelModel):
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


class ServerAnatomy(CamelModel):
    """The chassis floorplan, annotated. ``width``/``height`` set the viewBox."""

    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[ServerRegion]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class PowerOnState(CamelModel):
    """One step of the server power-on sequence; pure data the renderer consumes."""

    step: int
    phase: PowerOnPhase
    label: str
    description: str
    # Region ids in the server anatomy lit up at this step.
    active_regions: list[str]
    # Whole-server draw in watts — a loaded XE9680 runs on the order of 11 kW.
    power_watts: int
    # GPUs joined into the in-box NVLink domain, 0 → 8 — and never more than
    # 8: the domain stops at the chassis wall. That ceiling, not the fuse
    # itself, is this server's defining number.
    gpus_in_domain: int = Field(ge=0, le=8)
    # Scale-out NICs trained onto the data-center fabric, 0 → 8 — one per
    # GPU. Everything past eight GPUs travels through these.
    nics_up: int = Field(ge=0, le=8)
    # Illustrative wall-clock seconds since the PSUs energized.
    elapsed_seconds: int
    # UI dwell ticks; long stages (GPU init / HBM training) get more.
    cycle_cost: int = 1


class PowerOnResponse(CamelModel):
    trace: list[PowerOnState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to GPU servers;
    # spell out Dell and NVIDIA jargon (HGX, SXM, NVSwitch, DPU, ...) on
    # first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "one HGX baseboard — eight SXM sockets — per chassis"
    # Server regions this category slots into (ids from anatomy.py).
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
