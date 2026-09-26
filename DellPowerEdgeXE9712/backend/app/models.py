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

from pydantic import Field

from twinkit.models import CamelModel

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
    "fabric",      # NVLink switch trays boot; links train over 5,000+ cables
    "fused",       # all 72 GPUs join one NVLink domain (72 devices, 1 domain)
    "ready",       # burn-in passed; the rack accepts jobs
    # --- coolant-fault scenario only (additive; the nominal trace never
    # visits these). The first four sit between ``coolant`` and ``trayboot``,
    # the last three follow ``ready`` — see engine.FAULT_PHASE_ORDER.
    "flowfault",   # one tray branch fails flow/leak verification
    "isolate",     # the branch is sealed and the tray held off the busbar
    "repair",      # a technician services the tray (human time)
    "reverify",    # the loop re-primes and all 18 branches verify
    "leak",        # steady state: a cold-plate leak sensor trips under load
    "traydown",    # the leaking tray is off and sealed; the job has ended
    "held",        # rack held out of the scheduler pending service
]

#: Scenario ids the trace endpoint accepts (``?scenario=``).
ScenarioId = Literal["nominal", "coolant-fault"]


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
    # --- Additive cooling-interlock telemetry (failure-scenario work). Every
    # field below has a default, so nothing that built a PowerOnState before
    # these existed changes meaning.
    # Region ids that are faulted at this step — drawn in the error colour,
    # and never also in ``active_regions``.
    failed_regions: list[str] = Field(default_factory=list)
    # Tray coolant branches whose leak and flow checks currently pass, 0 → 18.
    branches_verified: int = Field(default=0, ge=0, le=18)
    # GPUs drawing power, 0 → 72. Distinct from ``gpus_in_domain`` on purpose:
    # after a steady-state leak 68 stay powered while the domain reads 0.
    gpus_powered: int = Field(default=0, ge=0, le=72)
    # Illustrative hottest-GPU temperature in °C. Exists so "power drops
    # before temperature rises" is a checkable statement, not a caption.
    gpu_temp_c: int = 22


class PowerOnResponse(CamelModel):
    trace: list[PowerOnState]
    scenario: ScenarioId = "nominal"


class ScenarioInfo(CamelModel):
    """One selectable trace. ``sources`` carry the product documentation the
    failure behaviour is modelled on; ``hero`` names the number to watch."""

    id: ScenarioId
    name: str
    summary: str
    hero: str
    # #phase= names worth deep-linking to, in trace order.
    key_phases: list[str] = Field(default_factory=list)
    sources: list[SourceLink] = Field(default_factory=list)


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
