"""Data models for the telecom & sustainability simulator
(physics_specs/08). Two personalities, tick = one sim-day:

* **Telecom Infrastructure Blocks** — a mobile-network build-out: 50–500
  cell sites of ruggedized compute, where the product's reason to exist
  is the integration-effort model (DIY compatibility-matrix validation
  vs pre-validated bundles) and the environment is hostile on purpose
  (the heatwave event separates standard from extended-temp fleets).
* **Circular Design** — a laptop's 8-year lifecycle as consequences of
  design decisions (glued vs screwed battery, soldered vs socketed RAM,
  recycled chassis, modular ports). The headline instrument is **carbon
  per useful-year**, and the accounting closes: total = embodied + use,
  every tick.

Sustainability honesty rule (spec 08, test-enforced): never invent
sustainability numbers — every carbon constant is a labeled literature
estimate, and the intended calibration source is Dell's published
per-product PCF reports.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

PCF_NOTE = (
    "All carbon figures are illustrative estimates for education. Dell "
    "publishes per-product Product Carbon Footprint (PCF) reports — "
    "those PDFs are the real calibration source, and swapping their "
    "numbers into the constants table is the intended exercise."
)


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Constant(CamelModel):
    value: float
    unit: str
    source: str
    estimated: bool
    blurb: str


# --- Configuration --------------------------------------------------------

Product = Literal["telecomblocks", "circulardesign"]
DeployMode = Literal["diy", "blocks"]
Grid = Literal["clean", "average", "coal"]


class LifecycleConfig(CamelModel):
    product: Product = "telecomblocks"
    # Telecom.
    sites: int = Field(100, ge=10, le=500)
    deploy_mode: DeployMode = "blocks"
    extended_temp: bool = True
    spare_capacity: bool = True          # N+1 site capacity for updates
    remote_remediation: bool = True
    subscribers_per_site_k: int = Field(20, ge=1, le=100)
    # Circular Design.
    battery_replaceable: bool = True
    ram_socketed: bool = True
    chassis_recycled: bool = True
    ports_modular: bool = True
    grid: Grid = "average"
    first_owner_years: int = Field(4, ge=3, le=5)
    annual_kwh: int = Field(60, ge=20, le=200)


EventAction = Literal[
    "deploy-sites",      # value: how many
    "heatwave",          # value: peak ambient °C for 3 days
    "bundle-update",     # roll the fleet's software
]


class SimEvent(CamelModel):
    at_d: int = Field(ge=0)
    action: EventAction
    value: float | None = None


class Scenario(CamelModel):
    config: LifecycleConfig = LifecycleConfig()
    duration_d: int = Field(365, ge=30, le=2920)
    events: list[SimEvent] = Field(default_factory=list)


RuleLevel = Literal["ok", "warning", "error"]


class Validation(CamelModel):
    rule_id: str
    level: RuleLevel
    message: str
    source: str


# --- Simulation output ----------------------------------------------------

class SimState(CamelModel):
    t_d: int
    # Telecom.
    sites_total: int
    sites_up: int
    coverage_pct: float
    subscribers_served_k: float
    integration_hours_cum: float
    mismatch_events_cum: int
    availability_pct: float
    ambient_c: float
    updating: bool
    # Circular Design (the ledger that must close).
    embodied_kg_cum: float
    use_kg_cum: float
    total_carbon_kg: float
    useful_years: float
    carbon_per_useful_year: float
    devices_consumed: int
    ewaste_kg: float
    tco_usd: float
    device_alive: bool
    on_second_life: bool
    disassembly_minutes: float
    region_load: dict[str, float]


class LogEntry(CamelModel):
    t_d: int
    severity: Literal["info", "warning", "critical"]
    message: str


class Summary(CamelModel):
    integration_hours: float
    mismatch_events: int
    availability_pct: float
    min_coverage_pct: float
    total_carbon_kg: float
    carbon_per_useful_year: float
    devices_consumed: int
    ewaste_kg: float
    tco_usd: float
    got_second_life: bool


class SimResponse(CamelModel):
    validations: list[Validation]
    trace: list[SimState]
    log: list[LogEntry]
    summary: Summary


# --- Maps -------------------------------------------------------------------

RegionKind = Literal[
    "coverage", "site", "integration", "environment", "device", "battery",
    "materials", "grid", "ledger", "secondlife",
]


class MapRegion(CamelModel):
    id: str
    kind: RegionKind
    label: str
    x: float
    y: float
    w: float
    h: float
    description: str


class LifecycleMap(CamelModel):
    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[MapRegion]
    overview: str
    sources: list[dict[str, str]] = Field(default_factory=list)


# --- Presets & teaching layer ---------------------------------------------

class ConfigPreset(CamelModel):
    id: str
    name: str
    blurb: str
    # V8: the canonical foil to run beside this preset (A/B compare).
    compare_preset_id: str | None = None
    config: LifecycleConfig


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
