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

from pydantic import Field

from twinkit.models import CamelModel


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

# CPU TDP tiers per platform. XR8000 sleds (XR8610t/XR8620t) take one
# 4th/5th Gen Xeon Scalable part; the XR8000 Technical Guide lists
# 125–205 W SKUs with a 205 W platform maximum (4509Y 125 W, 4510/4514Y
# 150 W, 6403N/6421N 185 W, 6433N/6438N 205 W) — so those four classes are
# sourced. The XR4000's sleds take one Xeon D; its wattage classes are
# modeled, not taken from a Dell table.
PLATFORM_TDP_TIERS: dict[str, list[int]] = {
    "xr8000": [125, 150, 185, 205],
    "xr4000": [65, 80, 100, 122],
}
# Modeled PSU classes. On the real XR8000r the AC options are 1400 W
# (Platinum, 100–240 V; derated to 1050 W at 100–120 V) and 1800 W
# (Titanium, 200–240 V only); 800/1100/1400 W are −48 V DC units. 800 W
# and 1100 W AC supplies exist elsewhere in the XR line (XR5610/XR7620).
PSU_CAPACITIES = [800, 1100, 1400]
# XR8000 sleds have 8 DDR5 slots; XR4000 sleds have 4 DDR4 slots
# (Dell PowerEdge XR-Series spec sheet, Jan 2026).
DIMM_COUNTS = [2, 4, 8]


class ServerConfig(CamelModel):
    platform: Platform = "xr8000"
    cpu_tdp_w: int = 205          # must be in PLATFORM_TDP_TIERS (a rule)
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
    # True = the run opens on a sled that has already been carrying this
    # workload in this environment long enough to settle (fans at their
    # operating point, thermal masses warm). False = a cold start: masses
    # at ambient, fans at the floor.
    warm_start: bool = False


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
    perf_lost_pct: float           # CPU clock clipped by its throttle clamp
    accel_perf_lost_pct: float     # accelerator clipped by its throttle clamp
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
