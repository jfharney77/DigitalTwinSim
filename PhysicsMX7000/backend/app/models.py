"""Data models for the PowerEdge MX7000 shared-infrastructure simulator.

Same conventions as every twin: snake_case in Python, camelCase over the
wire; ``POST /api/simulate`` takes a ``Scenario`` and returns the
deterministic trace (the R760Thermal pattern). The subject differs: this
is a 7U modular chassis where fans and PSUs belong to the *chassis*, not
to any sled — so the physics of interest is what sharing does. One hot
sled raises the fan bill for all eight bays, PSU redundancy is a pooled
policy rather than a per-server pair, and a storage sled's activity
follows whichever compute sled owns it.

Scope framing (physics_specs file 10 §1): correct relationships and
orders of magnitude, not CFD. Every constant lives in ``constants.py``
with a source field; estimates are flagged through to the UI.
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

SledKind = Literal["compute", "storage", "empty"]
Redundancy = Literal["grid", "n+1", "none"]

SLED_COUNT = 8
FAN_COUNT = 9   # 4 front + 5 rear hot-swap fans, chassis-level
PSU_MAX = 6

CPU_TDP_TIERS = [125, 165, 205, 250, 270, 350]
DIMM_COUNTS = [8, 16, 24, 32]


class SledConfig(CamelModel):
    """One of the eight single-width bays. A storage sled has no CPUs of
    its own — its drive activity follows the compute sled named by
    ``owner_slot`` (1-based), which is the chassis's composability story."""

    kind: SledKind = "empty"
    cpu_tdp_w: int = 205            # compute sleds: one of CPU_TDP_TIERS
    dimms: int = Field(16, ge=0, le=32)
    drives: int = Field(2, ge=0, le=6)   # compute sleds' local drives
    owner_slot: int | None = None   # storage sleds: owning compute slot (1–8)


class ChassisConfig(CamelModel):
    sleds: list[SledConfig] = Field(default_factory=lambda: [SledConfig() for _ in range(SLED_COUNT)])
    psu_count: int = Field(6, ge=2, le=PSU_MAX)
    redundancy: Redundancy = "grid"
    power_cap_w: int = Field(0, ge=0)   # 0 = uncapped chassis power budget


class SledLoad(CamelModel):
    """Utilization dials for one sled, each 0–100."""

    cpu_pct: int = Field(0, ge=0, le=100)
    mem_pct: int = Field(0, ge=0, le=100)
    storage_pct: int = Field(0, ge=0, le=100)


class Workload(CamelModel):
    loads: list[SledLoad] = Field(default_factory=lambda: [SledLoad() for _ in range(SLED_COUNT)])


class Environment(CamelModel):
    inlet_c: float = Field(22, ge=15, le=45)


EventAction = Literal[
    "set-sled-load",     # index = slot 0–7, load = new dials
    "set-all-load",      # load applied to every occupied sled
    "kill-fan",          # index 0–8
    "restore-fan",
    "kill-psu",          # one PSU fails (lowest-numbered alive)
    "lose-feed",         # index 0 = feed A, 1 = feed B
    "restore-feed",
    "set-inlet",         # value = °C
    "reassign-storage",  # index = storage slot 0–7, value = new owner slot 1–8
]


class SimEvent(CamelModel):
    """A timed intervention — interactive dials made deterministic so the
    engine stays pure and every run is reproducible."""

    at_s: int = Field(ge=0)
    action: EventAction
    index: int | None = None
    value: float | None = None
    load: SledLoad | None = None


class Scenario(CamelModel):
    config: ChassisConfig = ChassisConfig()
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


# --- Simulation output -----------------------------------------------------

class SimState(CamelModel):
    """One sim tick; pure data the renderer consumes. Per-sled lists are
    indexed by slot (0–7); empty bays read 0 W / inlet temperature."""

    t: int
    powered_on: bool
    sled_power_w: list[float]
    sled_temp_c: list[float]
    sled_throttling: list[bool]
    hottest_slot: int            # 1-based; 0 when nothing is powered
    fabric_power_w: float
    mgmt_power_w: float
    fan_power_w: float
    dc_power_w: float
    ac_power_w: float
    psu_efficiency: float
    psu_load_pct: float
    alive_psus: int
    feed_a_up: bool
    feed_b_up: bool
    fan_rpm_pct: float
    alive_fans: int
    airflow_cfm: float
    inlet_c: float
    exhaust_c: float
    delta_t_c: float
    chassis_capped: bool
    region_temps: dict[str, float]


class LogEntry(CamelModel):
    t: int
    severity: Literal["info", "warning", "critical"]
    message: str


class Summary(CamelModel):
    peak_dc_w: float
    peak_ac_w: float
    steady_dc_w: float
    steady_fan_w: float
    hottest_sled_c: float
    throttle_seconds: int
    shutdown: bool
    shutdown_reason: str = ""


class SimResponse(CamelModel):
    validations: list[Validation]
    trace: list[SimState]
    log: list[LogEntry]
    summary: Summary


# --- Chassis map -----------------------------------------------------------

RegionKind = Literal["bay", "cooling", "power", "management", "fabric"]


class ChassisRegion(CamelModel):
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
    regions: list[ChassisRegion]
    overview: str
    sources: list[dict[str, str]] = Field(default_factory=list)


# --- Presets & teaching layer ----------------------------------------------

class ConfigPreset(CamelModel):
    id: str
    name: str
    blurb: str
    config: ChassisConfig


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
