"""Data models for the iDRAC9 digital twin.

Same conventions as the PowerEdge R760 app: snake_case in Python, camelCase
over the wire (activeRegions, powerWatts, regionIds, ...), so the React
frontend can consume responses directly. None of the fields here camelize
ambiguously (no embedded numbers/acronyms), so no explicit aliases are
needed — if you add one that does, pin it with ``Field(alias=...)`` and check
frontend/src/types.ts by hand (see CLAUDE.md).

The twin's subject is a *subsystem*, not a chassis: the iDRAC9 baseboard
management controller (BMC) as a functional block diagram. So the shared
"anatomy" shape describes iDRAC's blocks and the buses that connect it to the
host and the outside world, and the "bring-up" trace is iDRAC's own firmware
boot from AC-applied standby to a ready, watching service processor.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "soc",       # the BMC system-on-chip / iDRAC service processor
    "memory",    # DRAM working memory + flash (firmware, Lifecycle Controller)
    "network",   # dedicated management NIC
    "sideband",  # host management buses: I2C/PMBus, eSPI/PECI, NC-SI
    "io",        # remote presence: virtual console, virtual media, iDRAC Direct
    "power",     # always-on standby power domain
    "security",  # silicon Root of Trust / cryptographic verification
    "sensor",    # monitoring + thermal-control engine
]

# iDRAC's own firmware bring-up, from no-AC to a ready service processor.
BringUpPhase = Literal[
    "off",       # no AC — the BMC domain is dark
    "standby",   # PSU standby rail energizes the always-on BMC domain
    "reset",     # SoC released from reset; boot ROM + Root of Trust
    "bootldr",   # first-stage bootloader (U-Boot): DRAM init, load firmware
    "kernel",    # embedded Linux boots; sideband + NIC drivers come up
    "services",  # management services + Lifecycle Controller initialize
    "ready",     # reachable, console live, watching the host out-of-band
]


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Photo(CamelModel):
    """A photograph of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class Block(CamelModel):
    """One functional block of the iDRAC subsystem, placed in a normalized
    coordinate space the frontend renders as SVG."""

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


class SubsystemMap(CamelModel):
    """The iDRAC block diagram, annotated. ``width``/``height`` set the
    viewBox; ``regions`` are the functional blocks."""

    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[Block]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class BringUpState(CamelModel):
    """One step of the iDRAC bring-up sequence; pure data the renderer
    consumes. The clock lives in the frontend, never here."""

    step: int
    phase: BringUpPhase
    label: str
    description: str
    # Block ids in the subsystem map lit up at this step.
    active_regions: list[str]
    # Illustrative draw of the always-on BMC power domain (a few watts).
    power_watts: int
    # iDRAC initialization progress, 0–100 (not host boot progress).
    progress_percent: int = Field(ge=0, le=100)
    # Illustrative wall-clock seconds since AC plug-in (not measured timing).
    elapsed_seconds: int
    # UI dwell ticks; long stages (Lifecycle Controller init) get more.
    cycle_cost: int = 1


class BringUpResponse(CamelModel):
    trace: list[BringUpState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to Dell systems
    # management; spell out jargon (Redfish, RACADM, NC-SI, LC, ...) on first
    # use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "Enterprise license or higher"
    # Subsystem blocks this capability lives in (ids from anatomy.py).
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
