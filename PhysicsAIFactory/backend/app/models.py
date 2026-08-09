"""Data models for the AI Factory capstone simulator.

Same conventions as every twin: snake_case in Python, camelCase over the
wire; ``POST /api/simulate`` takes a ``Scenario`` and returns the
deterministic trace (the R760Thermal pattern). The subject here is not a
box but the whole factory: compute, fabric, data, facility, resilience,
and cost, rolled into one first-order model per subsystem so the coupling
between them — the thing the per-product sims each teach one piece of —
shows on a single dashboard.

The Scenario shape is deliberately the *interface* the eight physics apps
will eventually feed: each block of it (compute, fabric, data, facility,
resilience) is the summary a per-product engine could compute and hand
over. Until those apps exist, the aggregates here are honest estimates.
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


# --- Factory configuration -------------------------------------------------

FabricType = Literal["spectrum-x", "quantum-ib"]
Cooling = Literal["liquid", "air"]

GPU_WATT_TIERS = [700, 1000, 1200]  # H100-class, B200-class, GB200-class


class ComputeBlock(CamelModel):
    """The training cluster: racks of XE9712-class 72-GPU systems."""

    racks: int = Field(8, ge=1, le=64)
    gpus_per_rack: int = Field(72, ge=8, le=72)
    gpu_peak_w: int = 1200        # one of GPU_WATT_TIERS (validated as a rule)


class FabricBlock(CamelModel):
    """The scale-out network joining the racks."""

    type: FabricType = "quantum-ib"
    oversubscription: float = Field(1.0, ge=1.0, le=4.0)


class DataBlock(CamelModel):
    """The data platform, reduced to the number that gates training."""

    storage_gbps: float = Field(1200, ge=10, le=100000)  # aggregate GB/s


class FacilityBlock(CamelModel):
    """Power and cooling, reduced to a budget and a PUE class."""

    mw_budget: float = Field(1.5, ge=0.1, le=200)
    cooling: Cooling = "liquid"


class ResilienceBlock(CamelModel):
    """Checkpoint discipline against the failure arithmetic of scale."""

    checkpoint_interval_min: int = Field(60, ge=5, le=1440)
    restart_min: int = Field(15, ge=1, le=240)
    gpu_mtbf_h: float = Field(50000, ge=1000, le=1000000)


class CostBlock(CamelModel):
    """Enough economics for a $/token proxy — deliberately coarse."""

    usd_per_kwh: float = Field(0.08, ge=0.01, le=1.0)
    capex_musd_per_rack: float = Field(3.0, ge=0.1, le=20.0)
    amortization_years: float = Field(4.0, ge=1.0, le=10.0)


class FactoryConfig(CamelModel):
    compute: ComputeBlock = ComputeBlock()
    fabric: FabricBlock = FabricBlock()
    data: DataBlock = DataBlock()
    facility: FacilityBlock = FacilityBlock()
    resilience: ResilienceBlock = ResilienceBlock()
    costs: CostBlock = CostBlock()


class TrainingJob(CamelModel):
    """The workload: what one GPU wants from the rest of the factory."""

    tokens_per_gpu_s: float = Field(200, ge=1, le=100000)
    data_gbps_per_gpu: float = Field(1.5, ge=0.01, le=100)
    state_gb_per_gpu: float = Field(10, ge=0.1, le=1000)
    ramp_h: int = Field(24, ge=1, le=336)


EventAction = Literal[
    "degrade-storage",   # value = % of nominal aggregate GB/s remaining
    "restore-storage",
    "warm-day",          # value = PUE penalty added (e.g. 0.2)
    "end-warm-day",
    "fail-gpus",         # value = extra GPUs lost at this hour
]


class SimEvent(CamelModel):
    """A timed intervention, keeping the engine pure and runs reproducible."""

    at_h: int = Field(ge=0)
    action: EventAction
    value: float | None = None


class Scenario(CamelModel):
    config: FactoryConfig = FactoryConfig()
    job: TrainingJob = TrainingJob()
    duration_h: int = Field(720, ge=24, le=4320)
    events: list[SimEvent] = Field(default_factory=list)


# --- Validation rules -------------------------------------------------------

RuleLevel = Literal["ok", "warning", "error"]


class Validation(CamelModel):
    rule_id: str
    level: RuleLevel
    message: str
    source: str


# --- Simulation output ------------------------------------------------------

Phase = Literal["procure", "install", "bringup", "train"]


class SimState(CamelModel):
    """One sim hour; pure data the dashboard consumes."""

    t_h: int
    phase: Phase
    gpus_installed: int
    gpus_online: int
    # Headline instruments.
    tokens_per_s: float
    tokens_total_b: float          # billions, cumulative (rolls back on failure)
    gpu_idle_data_pct: float       # the hero number: idle because data was late
    usd_per_mtok: float            # $ per million tokens, cumulative proxy
    pue: float
    facility_mw: float
    # Utilization decomposition.
    gpu_util_pct: float
    data_util_pct: float
    fabric_eff_pct: float
    overhead_pct: float            # checkpoint + failure-restart tax
    # Data platform coupling.
    storage_demand_gbps: float
    storage_supply_gbps: float
    # Power identity: the four parts sum to it_mw; facility = it × PUE.
    gpu_mw: float
    fabric_mw: float
    storage_mw: float
    other_mw: float
    it_mw: float
    mw_budget: float
    power_capped: bool
    failures_cum: int
    cost_usd_m: float              # cumulative $M spent (energy + amortization)
    # Region id → 0–100 activity/health, for the factory diagram painting.
    region_status: dict[str, float]


class LogEntry(CamelModel):
    t_h: int
    severity: Literal["info", "warning", "critical"]
    message: str


class Summary(CamelModel):
    time_to_first_token_h: int
    tokens_total_b: float
    avg_idle_data_pct: float
    avg_pue: float
    usd_per_mtok: float
    peak_facility_mw: float
    failures: int
    power_capped_hours: int


class SimResponse(CamelModel):
    validations: list[Validation]
    trace: list[SimState]
    log: list[LogEntry]
    summary: Summary


# --- Factory map (the block diagram) ----------------------------------------

RegionKind = Literal[
    "operations", "compute", "fabric", "data", "power", "cooling", "resilience",
]


class FactoryRegion(CamelModel):
    id: str
    kind: RegionKind
    label: str
    x: float
    y: float
    w: float
    h: float
    description: str


class FactoryMap(CamelModel):
    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[FactoryRegion]
    overview: str
    sources: list[dict[str, str]] = Field(default_factory=list)


# --- Presets & teaching layer ------------------------------------------------

class FactoryPreset(CamelModel):
    id: str
    name: str
    blurb: str
    config: FactoryConfig


class JobPreset(CamelModel):
    id: str
    name: str
    job: TrainingJob


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
