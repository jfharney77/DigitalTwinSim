"""Data models for the rack PDU & UPS physics simulator.

Same conventions as every twin: snake_case in Python, camelCase over the
wire. Scenario in (rack loads on three phase feeds + breaker ratings +
UPS battery + timed events), deterministic trace out — the
DellPowerEdgeR760Thermal pattern applied to the power layer under every
rack.

Scope framing (physics_specs/10-additional-products.md §6): correct
relationships and orders of magnitude, not an electrical-engineering
tool. Every constant lives in ``constants.py`` with a source field, and
readouts derived from estimates are badged in the UI.
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

Phase = Literal["A", "B", "C"]
Chemistry = Literal["vrla", "lithium"]

BREAKER_AMP_TIERS = [16, 20, 30, 32]
UPS_WH_TIERS = [500, 1000, 2000]

LOAD_SLOTS = 8  # fixed rack elevation: eight 1U/2U slots, 0 W = empty


class RackLoad(CamelModel):
    """One server (or 0 W empty slot) plugged into a phase feed."""

    label: str = "Server"
    power_w: float = Field(300, ge=0, le=2000)
    phase: Phase = "A"


class RackConfig(CamelModel):
    """The PDU + UPS hardware: three phase feeds behind per-phase
    breakers, all fed by one rack UPS."""

    loads: list[RackLoad] = Field(
        default_factory=lambda: [RackLoad() for _ in range(LOAD_SLOTS)],
        min_length=LOAD_SLOTS, max_length=LOAD_SLOTS,
    )
    breaker_amps: int = 16          # one of BREAKER_AMP_TIERS, per phase
    ups_chemistry: Chemistry = "vrla"
    ups_nameplate_wh: int = 1000    # one of UPS_WH_TIERS
    ups_age_years: float = Field(0, ge=0, le=10)
    start_charge_pct: float = Field(100, ge=0, le=100)


class Environment(CamelModel):
    room_temp_c: float = Field(25, ge=15, le=45)


EventAction = Literal[
    "utility-fail",     # mains drops; UPS carries the rack on battery
    "utility-restore",
    "move-load",        # index = load slot, phase = target feed
    "set-load",         # index = load slot, value = new watts
    "self-test",        # UPS measures true capacity; prediction corrected
]


class SimEvent(CamelModel):
    """A timed intervention — deterministic, so the engine stays pure and
    the trace reproducible."""

    at_s: int = Field(ge=0)
    action: EventAction
    index: int | None = None
    value: float | None = None
    phase: Phase | None = None


class Scenario(CamelModel):
    config: RackConfig = RackConfig()
    environment: Environment = Environment()
    duration_s: int = Field(600, ge=10, le=7200)
    events: list[SimEvent] = Field(default_factory=list)


# --- Validation rules -------------------------------------------------------

RuleLevel = Literal["ok", "warning", "error"]


class Validation(CamelModel):
    rule_id: str
    level: RuleLevel
    message: str
    source: str


# --- Simulation output ------------------------------------------------------

class SimState(CamelModel):
    """One sim tick; pure data the renderer consumes."""

    t: int
    utility_on: bool
    on_battery: bool
    rack_powered: bool
    # Per-phase electrical state. Conservation identity, asserted every
    # tick in the tests: sum of live outlet watts == sum of phase watts
    # == PDU input watts.
    phase_a_w: float
    phase_b_w: float
    phase_c_w: float
    phase_a_amps: float
    phase_b_amps: float
    phase_c_amps: float
    phase_a_pct: float          # of breaker rating
    phase_b_pct: float
    phase_c_pct: float
    tripped_phases: list[Phase]
    imbalance_pct: float        # max deviation from the phase average
    pdu_input_w: float
    # UPS state.
    ac_input_w: float           # drawn from the utility (0 on battery)
    battery_output_w: float     # drawn from the battery (0 on utility)
    inverter_loss_w: float
    charge_draw_w: float
    charge_pct: float           # of the battery's TRUE (faded) capacity
    battery_wh_remaining: float
    predicted_runtime_min: float  # what the front panel believes
    actual_runtime_min: float     # what the faded battery can really do
    self_tested: bool
    # Region id → live watts, for the rack elevation coloring. Keys must
    # exist in the anatomy (asserted in tests).
    region_watts: dict[str, float]


class LogEntry(CamelModel):
    t: int
    severity: Literal["info", "warning", "critical"]
    message: str


class Summary(CamelModel):
    peak_input_w: float
    worst_imbalance_pct: float
    battery_capacity_fraction: float   # the fade the sim applied
    predicted_runtime_min_at_failure: float
    actual_runtime_min_survived: float
    tripped_phases: list[Phase]
    rack_went_dark: bool
    dark_reason: str = ""


class SimResponse(CamelModel):
    validations: list[Validation]
    trace: list[SimState]
    log: list[LogEntry]
    summary: Summary


# --- Rack map ---------------------------------------------------------------

RegionKind = Literal["load", "pdu", "ups", "battery"]


class RackRegion(CamelModel):
    id: str
    kind: RegionKind
    label: str
    x: float
    y: float
    w: float
    h: float
    description: str


class RackMap(CamelModel):
    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[RackRegion]
    overview: str
    sources: list[dict[str, str]] = Field(default_factory=list)


# --- Presets & teaching layer ------------------------------------------------

class ConfigPreset(CamelModel):
    id: str
    name: str
    blurb: str
    config: RackConfig


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
