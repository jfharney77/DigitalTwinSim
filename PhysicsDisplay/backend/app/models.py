"""Data models for the UltraSharp display physics simulator.

Same conventions as every twin: snake_case in Python, camelCase over the
wire; ``POST /api/simulate`` takes a ``Scenario`` and returns the
deterministic trace (the R760Thermal pattern). This is deliberately the
smallest app in the physics suite — spec file 10 calls the display "a
small module, not a full sim" — so the model surface is one panel, one
question: where do a monitor's watts and its lifetime carbon actually go?
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

PanelModel = Literal["edge-27", "miniled-32"]
ContentProfile = Literal["dark", "mixed", "bright", "hdr"]


class DisplayConfig(CamelModel):
    model: PanelModel = "edge-27"
    brightness_pct: int = Field(75, ge=0, le=100)
    content: ContentProfile = "mixed"
    # Only meaningful on the mini-LED panel; the edge-lit panel has one
    # global backlight and nothing to dim locally.
    local_dimming: bool = True
    # USB-C power delivery to a docked laptop, W. Pass-through, not panel
    # heat — but it rides the same wall cord, which is the teaching point.
    hub_laptop_w: int = Field(0, ge=0, le=90)


class Lifecycle(CamelModel):
    """The use-phase assumptions the carbon arithmetic integrates over."""

    hours_per_day: float = Field(8, ge=0, le=24)
    days_per_year: int = Field(230, ge=1, le=366)
    service_years: float = Field(6, ge=1, le=12)
    grid_kgco2_per_kwh: float = Field(0.4, ge=0.0, le=1.5)


EventAction = Literal[
    "set-brightness",   # value = %
    "set-content",      # content = profile
    "set-dimming",      # value = 0/1
    "hub-plug",         # value = W drawn by the laptop
    "hub-unplug",
    "standby",          # display sleeps
    "wake",
]


class SimEvent(CamelModel):
    at_s: int = Field(ge=0)
    action: EventAction
    value: float | None = None
    content: ContentProfile | None = None


class Scenario(CamelModel):
    config: DisplayConfig = DisplayConfig()
    lifecycle: Lifecycle = Lifecycle()
    duration_s: int = Field(300, ge=10, le=3600)
    events: list[SimEvent] = Field(default_factory=list)


# --- Validation ------------------------------------------------------------

RuleLevel = Literal["ok", "warning", "error"]


class Validation(CamelModel):
    rule_id: str
    level: RuleLevel
    message: str
    source: str


# --- Simulation output ------------------------------------------------------

class SimState(CamelModel):
    """One sim tick. The power identity asserted every tick in the tests:
    electronics + backlight + hub_out + hub_loss == dc, ac == dc / η."""

    t: int
    on: bool
    brightness_pct: int
    content: ContentProfile
    # Component powers (W).
    electronics_w: float
    backlight_w: float
    hub_out_w: float     # delivered to the laptop — leaves over the cable
    hub_loss_w: float    # conversion loss of that delivery — stays as heat
    dc_power_w: float
    ac_power_w: float
    heat_w: float        # dc − hub_out: what actually warms the room
    # Backlight state the renderer paints.
    lit_fraction: float  # share of the backlight actually driven, 0–1
    zones_lit: int       # mini-LED zones above threshold (0 on edge-lit)
    # Running energy for this trace, Wh at the wall.
    cumulative_wh: float


class LogEntry(CamelModel):
    t: int
    severity: Literal["info", "warning", "critical"]
    message: str


class CarbonBreakdown(CamelModel):
    """Lifetime carbon, closed by construction and asserted in tests:
    embodied + use == lifetime, and the shares sum to 100."""

    embodied_kg: float       # manufacturing + transport + end-of-life
    use_kg: float            # computed from this scenario's lifecycle
    lifetime_kg: float
    embodied_pct: float
    use_pct: float
    annual_kwh: float
    avg_on_power_w: float


class Summary(CamelModel):
    peak_ac_w: float
    steady_ac_w: float
    standby_w: float
    carbon: CarbonBreakdown


class SimResponse(CamelModel):
    validations: list[Validation]
    trace: list[SimState]
    log: list[LogEntry]
    summary: Summary


# --- Panel map (the "anatomy" — a front view plus the electronics shelf) ---

RegionKind = Literal["panel", "backlight", "electronics", "hub", "power", "chassis"]


class PanelRegion(CamelModel):
    id: str
    kind: RegionKind
    label: str
    x: float
    y: float
    w: float
    h: float
    description: str


class PanelMap(CamelModel):
    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[PanelRegion]
    overview: str
    sources: list[dict[str, str]] = Field(default_factory=list)


# --- Presets & teaching layer ----------------------------------------------

class ModelPreset(CamelModel):
    id: str
    name: str
    blurb: str
    config: DisplayConfig


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
