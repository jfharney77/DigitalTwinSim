"""Data models for the client-device physics simulator (physics_specs/07).

One app, two product personalities — the Alienware gaming machines
(laptop or desktop tower) and the Dell Pro Max Plus mobile workstation
with its optional discrete NPU. Same conventions as every twin:
snake_case in Python, camelCase over the wire; ``POST /api/simulate``
takes a ``Scenario`` and returns the deterministic timestepped trace;
the frontend owns only the playback clock.

Scope framing (spec 07 + the R760 thermal spec it extends): a simplified,
legible physics model — correct relationships and orders of magnitude,
not a benchmark. Every constant lives in ``constants.py`` with a source
field, and estimates are flagged through to the UI.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# --- Constants (served to the UI so there is no second copy) -------------

class Constant(CamelModel):
    value: float
    unit: str
    source: str
    estimated: bool
    blurb: str


# --- Configuration --------------------------------------------------------

Product = Literal["alienware", "promax"]
FormFactor = Literal["laptop", "desktop"]
PerfMode = Literal["quiet", "balanced", "performance"]
InferenceEngine = Literal["cpu", "gpu", "npu"]

# Tier tables (spec 07; all `estimate` — see constants.py for sources).
LAPTOP_CPU_PL1 = [45, 55, 65]
DESKTOP_CPU_PL1 = [65, 125, 150]
LAPTOP_GPU_TGP = [0, 80, 115, 140, 175]
DESKTOP_GPU_TGP = [0, 200, 300, 450]
BATTERY_WH = [68, 90, 97]
CHARGER_W = [130, 180, 240, 330]
DESKTOP_PSU_W = [750, 1000, 1500]


class DeviceConfig(CamelModel):
    product: Product = "alienware"
    form_factor: FormFactor = "laptop"      # promax is laptop-only (validated)
    cpu_pl1_w: int = 55                     # sustained power limit tier
    gpu_tgp_w: int = 140                    # discrete GPU tier (0 = none)
    npu: bool = False                       # promax option: discrete AI-100 card
    ram_gb: int = Field(32, ge=8, le=256)
    nvme_count: int = Field(1, ge=1, le=4)
    battery_wh: int = 90                    # ignored for desktops
    battery_health_pct: int = Field(100, ge=50, le=100)
    charger_w: int = 240                    # laptop charger (desktop uses PSU)
    psu_capacity_w: int = 1000              # desktop tower PSU


class Workload(CamelModel):
    """Demand dials, each 0–100. NPU demand only does anything when the
    config carries the discrete NPU card."""

    cpu_pct: int = Field(0, ge=0, le=100)
    gpu_pct: int = Field(0, ge=0, le=100)
    npu_pct: int = Field(0, ge=0, le=100)


class Environment(CamelModel):
    ambient_c: float = Field(22, ge=10, le=45)
    on_lap: bool = False                    # bottom-intake blockage
    perf_mode: PerfMode = "balanced"
    plugged_in: bool = True
    start_charge_pct: int = Field(100, ge=1, le=100)


EventAction = Literal[
    "set-workload",
    "unplug",
    "plug-in",
    "set-ambient",
    "set-on-lap",       # value: 1/0
    "set-mode",         # mode field
    "set-charger",      # value: watts
]


class SimEvent(CamelModel):
    at_s: int = Field(ge=0)
    action: EventAction
    value: float | None = None
    mode: PerfMode | None = None
    workload: Workload | None = None


class Scenario(CamelModel):
    config: DeviceConfig = DeviceConfig()
    workload: Workload = Workload()
    environment: Environment = Environment()
    duration_s: int = Field(900, ge=10, le=14400)
    events: list[SimEvent] = Field(default_factory=list)


# --- Validation rules -----------------------------------------------------

RuleLevel = Literal["ok", "warning", "error"]


class Validation(CamelModel):
    rule_id: str
    level: RuleLevel
    message: str
    source: str


# --- Simulation output ----------------------------------------------------

PlState = Literal["idle", "pl2-boost", "pl1", "skin-limited", "budget-limited"]


class SimState(CamelModel):
    """One sim tick; pure data the renderer consumes."""

    t: int
    powered_on: bool
    # Component powers (W). Their sum is system_power_w — the balance
    # identity asserted every tick in the tests.
    cpu_power_w: float
    gpu_power_w: float
    npu_power_w: float
    base_power_w: float
    fan_power_w: float
    system_power_w: float
    # Supply side. The energy identity (Alienware-twin style):
    # ac_input_w + battery_discharge_w == system_power_w + charge_w (±tol).
    ac_input_w: float
    battery_discharge_w: float
    charge_w: float
    battery_pct: float
    runtime_min: float          # est. minutes left at current draw (∞→0 plugged)
    psu_efficiency: float       # desktop PSU / laptop charger conversion point
    # Limits & thermals.
    pl_state: PlState
    cpu_temp_c: float
    gpu_temp_c: float
    skin_temp_c: float
    fan_rpm_pct: float
    noise_dba: float
    cpu_throttling: bool
    gpu_throttling: bool
    # Performance proxies.
    fps_proxy: float            # gaming output ∝ GPU power delivered
    tokens_per_s: float         # inference output of the active engine
    tokens_per_joule: float
    active_engine: InferenceEngine | None
    region_temps: dict[str, float]


class LogEntry(CamelModel):
    t: int
    severity: Literal["info", "warning", "critical"]
    message: str


class Summary(CamelModel):
    peak_system_w: float
    steady_system_w: float
    fps_minute_1: float
    fps_minute_15: float
    min_battery_pct: float
    throttle_seconds: int
    shutdown: bool
    shutdown_reason: str = ""


class SimResponse(CamelModel):
    validations: list[Validation]
    trace: list[SimState]
    log: list[LogEntry]
    summary: Summary


# --- Device maps ----------------------------------------------------------

RegionKind = Literal[
    "cpu", "gpu", "npu", "memory", "storage", "battery", "cooling",
    "power", "board", "skin",
]


class DeviceRegion(CamelModel):
    id: str
    kind: RegionKind
    label: str
    x: float
    y: float
    w: float
    h: float
    description: str


class DeviceMap(CamelModel):
    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[DeviceRegion]
    overview: str
    sources: list[dict[str, str]] = Field(default_factory=list)


# --- Client-brand map (physics_specs/10 §8 — explainer, not a sim) --------

class Brand(CamelModel):
    id: str
    name: str
    formerly: str
    audience: str
    tiers: list[str]
    description: str


class BrandMap(CamelModel):
    overview: str
    naming_note: str
    since_note: str
    brands: list[Brand]
    sources: list[dict[str, str]] = Field(default_factory=list)


# --- Presets & teaching layer ---------------------------------------------

class ConfigPreset(CamelModel):
    id: str
    name: str
    blurb: str
    config: DeviceConfig


class WorkloadPreset(CamelModel):
    id: str
    name: str
    workload: Workload


class GuidedScenario(CamelModel):
    id: str
    title: str
    narration: list[str]
    question: str
    scenario: Scenario


class Explain(CamelModel):
    id: str
    title: str
    equation: str
    inputs: list[str]
    explanation: str
