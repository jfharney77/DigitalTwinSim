"""Data models for the PowerEdge XR rugged-edge physics simulator.

Same conventions as every twin: snake_case in Python, camelCase over the
wire; ``POST /api/simulate`` takes a ``Scenario`` and returns the
deterministic timestepped trace (the R760Thermal pattern — this app is
deliberately its closest cousin).

The personality difference is the environment. The R760 lives in a data
hall with a 15–45 °C inlet slider; the XR-series lives on rooftops, in
cell-site cabinets, and in vehicles, so the sliders unlock to hostile
ranges: −25…65 °C inlet, dust classes that foul the filter over
sim-months, vibration exposure, and a single-phase feed that browns out.
Correct relationships and orders of magnitude, not CFD — every constant
in ``constants.py`` carries a source, and estimates say so.
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


# --- Configuration ---------------------------------------------------------

Platform = Literal["xr8000", "xr4000"]
DriveType = Literal["ssd", "hdd"]
ThermalConfig = Literal["standard", "extended"]
Redundancy = Literal["1+0", "1+1"]

# CPU TDP tiers per platform: the XR8000's sleds take single-socket
# 4th Gen Xeon Scalable parts; the XR4000's nodes take Xeon D. Exact
# per-SKU wattages are `verify` — these are the modeled classes.
PLATFORM_TDP_TIERS: dict[str, list[int]] = {
    "xr8000": [125, 185, 225, 250],
    "xr4000": [65, 80, 100, 122],
}
PSU_CAPACITIES = [800, 1100, 1400]
DIMM_COUNTS = [4, 8, 16]


class ServerConfig(CamelModel):
    platform: Platform = "xr8000"
    cpu_tdp_w: int = 225          # must be in PLATFORM_TDP_TIERS (a rule)
    thermal_config: ThermalConfig = "standard"
    dimms: int = 8                # one of DIMM_COUNTS
    drive_type: DriveType = "ssd"
    drives: int = Field(2, ge=0, le=8)
    accels_single_wide: int = Field(0, ge=0, le=2)
    io_card_w: int = Field(25, ge=0, le=100)
    psu_count: int = Field(2, ge=1, le=2)
    psu_capacity_w: int = 1400    # one of PSU_CAPACITIES
    redundancy: Redundancy = "1+1"


class Workload(CamelModel):
    """Utilization dials, each 0–100."""

    cpu_pct: int = Field(0, ge=0, le=100)
    mem_pct: int = Field(0, ge=0, le=100)
    storage_pct: int = Field(0, ge=0, le=100)
    accel_pct: int = Field(0, ge=0, le=100)


Dust = Literal["clean", "moderate", "heavy"]
Vibration = Literal["none", "roadside", "vehicle"]


class Environment(CamelModel):
    """The unlocked sliders — the whole point of this twin."""

    inlet_c: float = Field(25, ge=-25, le=65)
    altitude_m: int = Field(0, ge=0, le=3000)
    dust: Dust = "moderate"
    filter_months: float = Field(0, ge=0, le=24)
    vibration: Vibration = "none"


EventAction = Literal[
    "set-workload",       # swap the workload dials mid-run
    "kill-fan",           # index 0–3
    "restore-fan",
    "kill-psu",
    "set-inlet",          # value = °C (the heat wave / cold snap)
    "set-filter-months",  # value = months of accumulated fouling
    "clean-filter",       # somebody finally changed it
    "voltage-sag",        # value = % of nominal voltage, seconds = duration
]


class SimEvent(CamelModel):
    """A timed intervention — deterministic, so the engine stays pure and
    the trace reproducible."""

    at_s: int = Field(ge=0)
    action: EventAction
    index: int | None = None
    value: float | None = None
    seconds: float | None = None
    workload: Workload | None = None


class Scenario(CamelModel):
    config: ServerConfig = ServerConfig()
    workload: Workload = Workload()
    environment: Environment = Environment()
    duration_s: int = Field(600, ge=10, le=7200)
    events: list[SimEvent] = Field(default_factory=list)


# --- Validation rules ------------------------------------------------------

RuleLevel = Literal["ok", "warning", "error"]


class Validation(CamelModel):
    rule_id: str
    level: RuleLevel
    message: str
    source: str


# --- Simulation output ----------------------------------------------------

class SimState(CamelModel):
    """One sim tick; pure data the renderer consumes."""

    t: int
    powered_on: bool
    # Component DC powers (W). Their sum is dc_power_w — asserted every
    # tick in the tests: the power-balance identity.
    cpu_power_w: float
    accel_power_w: float
    dimm_power_w: float
    drive_power_w: float
    io_power_w: float
    platform_power_w: float
    fan_power_w: float
    dc_power_w: float
    # Wall side — including the feed the R760 never has to think about.
    ac_power_w: float
    psu_efficiency: float
    psu_load_pct: float
    alive_psus: int
    input_v_pct: float        # % of nominal feed voltage (100 = healthy)
    input_current_a: float    # what the sagging feed forces the PSUs to draw
    # Airflow & thermals.
    fan_rpm_pct: float
    alive_fans: int
    airflow_cfm: float
    fouling_pct: float        # filter fouling, as % airflow resistance added
    inlet_effective_c: float
    cpu_temp_c: float
    accel_temp_c: float
    drive_temp_c: float
    exhaust_c: float
    delta_t_c: float
    # Protective state.
    cpu_throttling: bool
    accel_throttling: bool
    perf_lost_pct: float
    storage_perf_lost_pct: float   # vibration tax on spinning drives
    # Region id → temperature, for the chassis coloring. Keys must exist
    # in the anatomy (asserted in tests).
    region_temps: dict[str, float]


class LogEntry(CamelModel):
    t: int
    severity: Literal["info", "warning", "critical"]
    message: str


class Summary(CamelModel):
    peak_dc_w: float
    peak_ac_w: float
    steady_dc_w: float
    steady_cpu_temp_c: float
    throttle_seconds: int
    shutdown: bool
    shutdown_reason: str = ""


class SimResponse(CamelModel):
    validations: list[Validation]
    trace: list[SimState]
    log: list[LogEntry]
    summary: Summary


# --- Chassis map -----------------------------------------------------------

RegionKind = Literal[
    "filter", "storage", "cooling", "memory", "cpu", "accel", "io",
    "power", "management",
]


class ThermalRegion(CamelModel):
    id: str
    kind: RegionKind
    label: str
    x: float
    y: float
    w: float
    h: float
    description: str


class ChassisMap(CamelModel):
    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[ThermalRegion]
    overview: str
    sources: list[dict[str, str]] = Field(default_factory=list)


# --- Presets & teaching layer ---------------------------------------------

class ConfigPreset(CamelModel):
    id: str
    name: str
    blurb: str
    config: ServerConfig


class WorkloadPreset(CamelModel):
    id: str
    name: str
    workload: Workload


class GuidedScenario(CamelModel):
    """A scripted walkthrough: sets the scenario, narrates what to watch,
    and ends with a question the user can verify by experiment."""

    id: str
    title: str
    narration: list[str]
    question: str
    scenario: Scenario


class Explain(CamelModel):
    """Explain-mode content: the equation behind a readout, with
    placeholders the frontend substitutes with live values."""

    id: str
    title: str
    equation: str
    inputs: list[str]
    explanation: str
