"""Data models for the PowerMax digital twin.

Same conventions as the GPU, R760, PowerStore, and Alienware apps:
snake_case in Python, camelCase over the wire (activeRegions, powerWatts,
regionIds, ...), so the React frontend can consume responses directly. None
of the fields here camelize ambiguously (no embedded numbers/acronyms), so
no explicit aliases are needed — if you add one that does, pin it with
``Field(alias=...)`` and check frontend/src/types.ts by hand (see CLAUDE.md).

The PowerMax-specific vocabulary in the enums:

- ``vault`` — the NVMe SED flash modules PowerMax vaults cache to on power
  loss ("Vault to Flash"), distinct from the standby-power ``battery``.
- ``cache`` — the per-node-pair DRAM PowerMax calls "cache" (mirrored global
  memory), the equivalent of the other apps' ``memory`` kind.
- ``fabric`` — the InfiniBand "Dynamic Fabric" that connects the two nodes of
  a pair (and, on the 8500, connects node pairs). This is the scale-out
  interconnect and gets its own phase in the bring-up.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "storage",     # Dynamic Media Enclosure (DME) NVMe drive bay
    "vault",       # NVMe SED vault-to-flash modules
    "cache",       # per-node DRAM (PowerMax "cache" / global memory)
    "cpu",         # per-node Intel Xeon director sockets
    "fabric",      # InfiniBand Dynamic Fabric adapters + interconnect
    "io",          # front-end I/O modules (FC, iSCSI, NVMe/TCP, FICON, ...)
    "power",       # per-node power supplies
    "cooling",     # per-node fan packs
    "battery",     # standby power supply (SPS) that powers the vault
    "management",  # management module / control station ports
    "board",       # director system board / midplane
]

PowerPhase = Literal[
    "off",       # AC present at the PDUs, nothing drawing
    "power",     # PSUs energize, SPS self-test, fans spin up
    "vault",     # validate the vault; restore cache on a dirty return
    "boot",      # each director boots PowerMaxOS 10 (longest stage)
    "fabric",    # InfiniBand Dynamic Fabric comes up, nodes connect
    "drives",    # DME NVMe discovery — both nodes see every drive
    "pool",      # Flexible RAID / storage resource pool assembles
    "services",  # data reduction, SRDF, front-end ports, Unisphere
    "online",    # serving block / file / mainframe I/O
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
    """One node-pair engine + its drive enclosure, annotated.
    ``width``/``height`` set the viewBox."""

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
    # UI dwell ticks; long stages (PowerMaxOS boot, pool assembly) get more.
    cycle_cost: int = 1


class PowerOnResponse(CamelModel):
    trace: list[PowerOnState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to enterprise storage;
    # spell out Dell jargon (SRDF, SnapVX, DME, FICON, ...) on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "1 to 8 node pairs (PowerMax 8500)"
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
