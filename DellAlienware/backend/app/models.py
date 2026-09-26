"""Data models for the Alienware m18 digital twin.

Same conventions as the GPU and R760 apps: snake_case in Python, camelCase
over the wire, so the React frontend can consume responses directly. Many
fields here end in a bare ``_w`` (watts) or embed digits (``_80_``), which
is exactly the ambiguous-camelization territory CLAUDE.md warns about — so
every such field pins its wire name with an explicit ``Field(alias=...)``
matching the normative API contract, rather than trusting ``to_camel``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from twinkit.models import CamelModel

RegionKind = Literal[
    "board",     # motherboard, EC, CPU/GPU dies
    "power",     # DC-in jack, charger/power-path stage
    "battery",   # the battery pack
    "cooling",   # fans, heat-pipe/vapor-chamber assembly
    "memory",    # SO-DIMMs, GPU VRAM
    "storage",   # M.2 SSDs
    "io",        # port clusters on the chassis edges
    "display",   # display-related parts (unused on this floorplan, reserved)
    "wireless",  # WLAN card
]

# Contract phase machine: monotonic, never regresses.
PowerPhase = Literal[
    "off", "detect", "handshake", "budget", "charge", "boot", "load", "steady",
    # Additive: phases only the charging-diagnostics trace reaches
    # (app/diagnostics.py). The plug-in trace never emits them.
    "cap", "taper", "heat", "resume", "swap",
]

ChargeStage = Literal["idle", "precharge", "cc", "cv", "full"]
Connector = Literal["barrel", "usbc"]
ThermalMode = Literal["quiet", "balanced", "performance", "fullSpeed"]
WorkloadKind = Literal["idle", "gaming", "fullLoad"]
Regime = Literal["adapter-limited", "within-budget", "throttled"]


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


class AdapterOption(CamelModel):
    """One AC adapter the laptop can be plugged into.

    ``recognized=False`` models a failed PSID handshake — the 1-Wire ID chip
    in the adapter can't be read (damaged center pin, third-party brick), so
    the EC sees "Unknown" and distrusts the supply.
    """

    id: str
    name: str
    watts: float
    connector: Connector
    voltage: float
    amps: float
    recognized: bool = True
    description: str


class Battery(CamelModel):
    wh: float
    cells: int
    voltage: float
    express_charge: bool = True


class LaptopProfile(CamelModel):
    id: str
    name: str
    family: str
    cpu: str
    cpu_max_w: float = Field(alias="cpuMaxW")
    gpu: str
    gpu_tgp_w: float = Field(alias="gpuTgpW")
    battery: Battery
    adapters: list[AdapterOption]
    default_adapter_id: str
    idle_w: float = Field(alias="idleW")
    anatomy_id: str  # ties profile → anatomy floorplan
    description: str


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


class Scenario(CamelModel):
    profile_id: str
    adapter_id: str
    start_battery_pct: float = Field(ge=0, le=100)
    thermal_mode: ThermalMode
    workload: WorkloadKind


class SimulateRequest(CamelModel):
    scenario: Scenario


class PowerState(CamelModel):
    """One trace entry; pure data the renderer consumes.

    Energy invariant, every state: acW + batteryW == systemW + chargeW.
    """

    cycle: int  # == index in trace
    phase: PowerPhase
    stage_id: str  # stable kebab-case id from the research S0..S10 machine
    label: str
    description: str
    # Region ids lit up at this step; must exist in the profile's anatomy.
    active_regions: list[str]
    ac_w: float = Field(alias="acW")  # power drawn from the adapter
    system_w: float = Field(alias="systemW")  # CPU + GPU + rest of platform
    charge_w: float = Field(alias="chargeW")  # >0 charging into the battery
    battery_w: float = Field(alias="batteryW")  # >0 battery DIScharging
    battery_pct: float = Field(ge=0, le=100)
    charge_stage: ChargeStage
    cpu_w: float = Field(alias="cpuW")
    gpu_w: float = Field(alias="gpuW")
    fan_pct: float = Field(ge=0, le=100)
    hybrid: bool = False  # true while the battery supplements the adapter
    stalled: bool = False  # long stages the UI should dwell on
    cycle_cost: int = 1  # dwell weight, >=1


class Summary(CamelModel):
    adapter_w: float = Field(alias="adapterW")
    peak_system_w: float = Field(alias="peakSystemW")
    peak_hybrid_w: float = Field(alias="peakHybridW")  # max battery supplement
    hybrid_used: bool
    end_battery_pct: float
    regime: Regime  # "throttled" == unrecognized adapter
    # Illustrative ExpressCharge estimate; None when not charging.
    minutes_to_80_pct: float | None = Field(alias="minutesTo80Pct")
    notes: list[str] = Field(default_factory=list)


class SimulateResponse(CamelModel):
    profile: LaptopProfile
    scenario: Scenario
    adapter: AdapterOption
    summary: Summary
    trace: list[PowerState]


# ---------------------------------------------------------------------------
# Failure scenario: charging diagnostics (additive — see app/diagnostics.py)
# ---------------------------------------------------------------------------

# Why the pack is taking less than the full constant-current rate right now.
# "none" is the only value that means nothing is limiting the charge.
ChargeLimiter = Literal[
    "none",         # charging at the full constant-current rate
    "charge-cap",   # a BIOS charge mode stopped the charge below 100%
    "taper",        # constant-voltage taper: the cells set the pace
    "budget",       # the adapter's watts are all going to the silicon
    "temperature",  # pack over its charge-temperature limit
    "adapter",      # adapter not recognized: the EC refuses to charge
    "full",         # charge terminated at 100%
]
ChargeMode = Literal["primarily-ac", "standard"]
TraceScenarioKind = Literal["baseline", "failure"]


class DiagnosticState(PowerState):
    """A PowerState plus what the owner can read off the machine.

    Same energy invariant as its parent. The extra fields are the diagnostic
    walk's evidence: the BIOS adapter line, the battery status line, the pack temperature, and
    the single reason the charge is below the constant-current rate.
    """

    charge_limiter: ChargeLimiter = "none"
    charge_mode: ChargeMode = "standard"
    charge_cap_pct: float = Field(default=100.0, ge=0, le=100)
    pack_temp_c: float = Field(alias="packTempC")
    adapter_readout: str  # the BIOS "AC Adapter" line
    battery_readout: str  # the battery status line (BIOS / Windows); names no cause
    # Region ids drawn in the error colour; a subset of the anatomy's ids.
    failed_regions: list[str] = Field(default_factory=list)


class DiagnosticCheck(CamelModel):
    """One symptom of the walk: what is seen, what it means, what to do."""

    id: str
    phase: PowerPhase  # the trace phase that shows it
    limiter: ChargeLimiter
    symptom: str
    readout: str
    cause: str
    action: str


class TraceScenario(CamelModel):
    """A playable trace the simulate endpoint can serve (?scenario=<id>)."""

    id: str
    title: str
    kind: TraceScenarioKind
    summary: str
    phases: list[PowerPhase]
    hero_label: str
    checks: list[DiagnosticCheck] = Field(default_factory=list)
    sources: list["SourceLink"] = Field(default_factory=list)
    illustrative: str = ""


class DiagnosticResponse(SimulateResponse):
    """SimulateResponse whose trace carries the diagnostic fields."""

    trace: list[DiagnosticState]  # type: ignore[assignment]
    trace_scenario: TraceScenario


# ---------------------------------------------------------------------------
# Anatomy (mirrors R760/GPU anatomy shape)
# ---------------------------------------------------------------------------


class Photo(CamelModel):
    """A photograph of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class Region(CamelModel):
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


class Anatomy(CamelModel):
    """One laptop interior, annotated. ``width``/``height`` set the viewBox."""

    id: str
    name: str
    vendor: str
    platform: str
    year: int
    width: float
    height: float
    regions: list[Region]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


# ---------------------------------------------------------------------------
# Use cases
# ---------------------------------------------------------------------------


class UseCaseStep(CamelModel):
    title: str
    body: str
    # Anatomy region ids this step touches (resolved by tests).
    region_ids: list[str] = Field(default_factory=list)


class UseCase(CamelModel):
    id: str
    title: str
    summary: str
    persona: str
    steps: list[UseCaseStep]
    outcome: str
    sources: list[SourceLink] = Field(default_factory=list)


TraceScenario.model_rebuild()
DiagnosticResponse.model_rebuild()
