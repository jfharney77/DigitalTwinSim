"""Data models for the PowerSwitch E3200-ON digital twin.

Same conventions as the PowerEdge R760 app: snake_case in Python, camelCase
over the wire (activeRegions, powerWatts, regionIds, ...), so the React
frontend can consume responses directly. None of the fields here camelize
ambiguously (no embedded numbers/acronyms), so no explicit aliases are
needed — if you add one that does, pin it with ``Field(alias=...)`` and check
frontend/src/types.ts by hand (see CLAUDE.md).

The E3200-ON is a 1RU open-networking edge switch, so this is a chassis twin
like the R760: the "anatomy" is a top-down floorplan of the switch, and the
"boot" trace is the switch coming up from AC to line-rate forwarding — the
"-ON" (Open Networking) path runs ONIE, then a disaggregated network OS
(SmartFabric OS10 or Enterprise SONiC), then programs the switching ASIC.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "ports",    # front-panel access ports (RJ45 copper or SFP fiber)
    "uplink",   # SFP+/SFP28 front uplinks + rear 100G QSFP28
    "poe",      # Power-over-Ethernet PSE subsystem
    "asic",     # the switching ASIC / packet processor (the data plane)
    "cpu",      # control-plane CPU, memory, SSD (runs the NOS)
    "mgmt",     # out-of-band mgmt port, console (RJ45/microUSB), USB
    "cooling",  # variable-speed fan modules
    "power",    # hot-swap PSUs
]

# The switch's journey from AC to line-rate forwarding.
BootPhase = Literal[
    "off",         # no AC
    "standby",     # PSU standby rail up
    "poweron",     # main rails, CPU, fans; system inventory
    "onie",        # ONIE (Open Network Install Environment) bootloader
    "nos",         # network OS boots (SmartFabric OS10 / Enterprise SONiC)
    "dataplane",   # switching ASIC + forwarding tables programmed
    "ports",       # interfaces negotiate link; PoE delivered
    "forwarding",  # line-rate, non-blocking forwarding (steady state)
]


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
    """One switch chassis, annotated. ``width``/``height`` set the viewBox."""

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


class BootState(CamelModel):
    """One step of the switch boot sequence; pure data the renderer consumes.
    The clock lives in the frontend, never here."""

    step: int
    phase: BootPhase
    label: str
    description: str
    # Region ids in the chassis anatomy lit up at this step.
    active_regions: list[str]
    # Illustrative total draw incl. PoE (watts) — PoE dominates on the P/PXE
    # models, so this jumps hard when PoE powers up.
    power_watts: int
    fan_percent: int = Field(ge=0, le=100)
    # Illustrative aggregate forwarding rate (Gbps); 0 until the data plane
    # carries traffic, then ramps toward the model's line-rate capacity.
    data_rate_gbps: int = 0
    # Illustrative wall-clock seconds since AC plug-in (not measured timing).
    elapsed_seconds: int
    # UI dwell ticks; long stages (NOS boot) get more.
    cycle_cost: int = 1


class BootResponse(CamelModel):
    trace: list[BootState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to Dell networking;
    # spell out jargon (ONIE, NOS, PSE, MLAG, QSFP28, ...) on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "2 PSU bays"
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
