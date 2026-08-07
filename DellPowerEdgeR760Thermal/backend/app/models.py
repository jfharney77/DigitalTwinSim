"""Data models for the R760 power & thermal simulator twin.

Same conventions as the other twins: snake_case in Python, camelCase over
the wire. The twist versus every earlier twin: the trace is not a fixed
narrative — ``POST /api/simulate`` takes a ``Scenario`` (configuration,
workload, environment, timed events) and returns the deterministic
timestepped trace the physics engine computes, the ``DellAlienware``
twin's pattern generalized. The frontend owns only the playback clock.

Scope framing from the spec (§1): this is a simplified, legible physics
model — correct *relationships and orders of magnitude*, not CFD and not
exact numbers. Every constant lives in ``constants.py`` with a source
field, and readouts derived from estimates are badged in the UI.
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


# --- Configuration (spec §3) ---------------------------------------------

Heatsink = Literal["standard", "high-performance"]
FanKit = Literal["standard", "gold"]
Chassis = Literal["12x3.5", "24x2.5", "16xE3.S"]
Redundancy = Literal["1+0", "1+1"]

CPU_TDP_TIERS = [125, 150, 185, 205, 250, 270, 300, 330, 350]
PSU_CAPACITIES = [800, 1100, 1400, 2400]
DIMM_COUNTS = [8, 16, 24, 32]


class ServerConfig(CamelModel):
    sockets: int = Field(2, ge=1, le=2)
    cpu_tdp_w: int = 250          # one of CPU_TDP_TIERS (validated as a rule)
    heatsink: Heatsink = "high-performance"
    fan_kit: FanKit = "standard"
    dimms: int = 16               # one of DIMM_COUNTS
    chassis: Chassis = "24x2.5"
    drives: int = Field(8, ge=0)  # populated front-bay drives
    gpus_double_wide: int = Field(0, ge=0, le=2)
    accels_single_wide: int = Field(0, ge=0, le=6)
    io_card_w: int = Field(25, ge=0, le=100)
    psu_count: int = Field(2, ge=1, le=2)
    psu_capacity_w: int = 1400    # one of PSU_CAPACITIES
    redundancy: Redundancy = "1+1"


class Workload(CamelModel):
    """Utilization dials, each 0–100 (spec §4)."""

    cpu_pct: int = Field(0, ge=0, le=100)
    mem_pct: int = Field(0, ge=0, le=100)
    storage_pct: int = Field(0, ge=0, le=100)
    gpu_pct: int = Field(0, ge=0, le=100)


class Environment(CamelModel):
    inlet_c: float = Field(22, ge=15, le=45)
    altitude_m: int = Field(0, ge=0, le=3000)
    recirculation_pct: int = Field(0, ge=0, le=100)
    blocked_intake_pct: int = Field(0, ge=0, le=100)


EventAction = Literal[
    "set-workload",   # swap the workload dials mid-run
    "kill-fan",       # index 0–5
    "restore-fan",
    "kill-psu",       # one PSU fails
    "set-inlet",      # value = °C
    "set-recirculation",  # value = %
    "set-blocked-intake",  # value = %
]


class SimEvent(CamelModel):
    """A timed intervention — the spec's interactive dials, made
    deterministic so the engine stays pure and the trace reproducible."""

    at_s: int = Field(ge=0)
    action: EventAction
    index: int | None = None
    value: float | None = None
    workload: Workload | None = None


class Scenario(CamelModel):
    config: ServerConfig = ServerConfig()
    workload: Workload = Workload()
    environment: Environment = Environment()
    duration_s: int = Field(600, ge=10, le=7200)
    events: list[SimEvent] = Field(default_factory=list)


# --- Validation rules (spec §6) -------------------------------------------

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
    gpu_power_w: float
    dimm_power_w: float
    drive_power_w: float
    io_power_w: float
    platform_power_w: float
    fan_power_w: float
    dc_power_w: float
    # Wall side.
    ac_power_w: float
    psu_efficiency: float
    psu_load_pct: float
    alive_psus: int
    # Airflow & thermals.
    fan_rpm_pct: float
    alive_fans: int
    airflow_cfm: float
    inlet_effective_c: float
    cpu_temp_c: float
    gpu_temp_c: float
    drive_temp_c: float
    exhaust_c: float
    delta_t_c: float
    # Protective state.
    cpu_throttling: bool
    gpu_throttling: bool
    perf_lost_pct: float
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


# --- Chassis map (geometry reused from the R760 power-on twin) ------------

RegionKind = Literal[
    "storage", "cooling", "memory", "cpu", "gpu", "io", "power", "management",
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


# --- Presets & teaching layer (spec §4, §7, §8) ---------------------------

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
    """A scripted walkthrough (spec §8): sets the scenario, narrates what
    to watch, and ends with a question the user can verify by experiment."""

    id: str
    title: str
    narration: list[str]
    question: str
    scenario: Scenario


class Explain(CamelModel):
    """Explain-mode content (spec §8): the equation behind a readout, with
    placeholders the frontend substitutes with live values."""

    id: str
    title: str
    equation: str          # e.g. "P = idle + (TDP − idle) × util^1.4"
    inputs: list[str]      # causal-chain labels, in order
    explanation: str       # leveled prose
