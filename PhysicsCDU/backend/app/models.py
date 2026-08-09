"""Data models for the PowerCool CDU C7000 / PowerRack / IRC physics twin.

Same conventions as every twin in this repo: snake_case in Python,
camelCase over the wire. Same pattern as the R760 thermal simulator:
``POST /api/simulate`` takes a ``Scenario`` (CDU configuration, rack
payload, environment, timed events) and returns the deterministic
timestepped trace the pure engine computes. The frontend owns only the
playback clock.

Scope framing: a simplified, legible model of a coolant distribution
unit — primary (facility water) loop, plate heat exchanger, secondary
(rack coolant) loop — with the Integrated Rack Controller as the policy
layer above it. Correct relationships and orders of magnitude, not CFD
and not a pump datasheet. Every constant lives in ``constants.py`` with
a source field; estimates are flagged through to the UI.
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

IrcPolicy = Literal["coordinated", "uncoordinated"]

MAX_TRAY_GROUPS = 6
PUMP_COUNTS = [2, 3]


class CduConfig(CamelModel):
    """The CDU + rack build the user assembles."""

    tray_groups: int = Field(5, ge=1, le=MAX_TRAY_GROUPS)
    pumps: int = Field(3, ge=2, le=3)          # 2 = N, 3 = N+1
    flow_setpoint_lpm: int = Field(340, ge=200, le=400)
    min_supply_c: float = Field(32, ge=15, le=45)
    policy: IrcPolicy = "coordinated"


class Workload(CamelModel):
    """One dial: how hard the trays are computing."""

    util_pct: int = Field(100, ge=0, le=100)


class Environment(CamelModel):
    facility_supply_c: float = Field(17, ge=8, le=45)
    dew_point_c: float = Field(12, ge=2, le=28)


EventAction = Literal[
    "set-util",             # value = %
    "set-facility-supply",  # value = °C
    "set-dew-point",        # value = °C
    "set-min-supply",       # value = °C
    "fail-pump",            # index 0–2
    "restore-pump",
    "add-tray-group",
    "remove-tray-group",
]


class SimEvent(CamelModel):
    """A timed intervention — interactivity kept deterministic so the
    engine stays pure and every run is reproducible."""

    at_s: int = Field(ge=0)
    action: EventAction
    index: int | None = None
    value: float | None = None


class Scenario(CamelModel):
    config: CduConfig = CduConfig()
    workload: Workload = Workload()
    environment: Environment = Environment()
    duration_s: int = Field(900, ge=10, le=7200)
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
    """One sim tick; pure data the renderer consumes."""

    t: int
    # Heat.
    it_load_kw: float
    heat_removed_kw: float
    hx_load_pct: float
    # Primary (facility) loop.
    fac_supply_c: float
    fac_return_c: float
    fac_flow_lpm: float
    # Secondary (rack) loop.
    sec_supply_c: float
    sec_return_c: float
    sec_flow_lpm: float
    approach_c: float
    pump_speed_pct: float
    pumps_alive: int
    pump_power_kw: float
    # Rack / IRC.
    groups_present: int
    groups_online: int
    # Per-bank status, index-aligned with the map's tray regions.
    bank_status: list[Literal["absent", "online", "tripped"]]
    trips: int
    cap_pct: float
    capping: bool
    chip_temp_c: float
    # Condensation guard.
    dew_margin_c: float
    floor_active: bool
    # Region id → temperature for the loop map (keys must exist in the
    # anatomy — asserted in tests).
    region_temps: dict[str, float]


class LogEntry(CamelModel):
    t: int
    severity: Literal["info", "warning", "critical"]
    message: str


class Summary(CamelModel):
    peak_it_kw: float
    steady_it_kw: float
    peak_chip_c: float
    min_cap_pct: float
    capped_seconds: int
    trips: int
    delivered_kwh: float


class SimResponse(CamelModel):
    validations: list[Validation]
    trace: list[SimState]
    log: list[LogEntry]
    summary: Summary


# --- Loop map (the anatomy of a cooling loop) ------------------------------

RegionKind = Literal[
    "facility", "pipe", "hx", "pump", "controller", "manifold", "tray",
]


class LoopRegion(CamelModel):
    id: str
    kind: RegionKind
    label: str
    x: float
    y: float
    w: float
    h: float
    description: str


class LoopMap(CamelModel):
    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[LoopRegion]
    overview: str
    sources: list[dict[str, str]] = Field(default_factory=list)


# --- Presets & teaching layer ----------------------------------------------

class ConfigPreset(CamelModel):
    id: str
    name: str
    blurb: str
    config: CduConfig


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
