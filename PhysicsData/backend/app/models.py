"""Data models for the data & observability simulator (physics_specs/06).

Two personalities in one app:

* **Dell AI Data Platform** — a dataset's journey (raw → ingest →
  process → index → serve) as a pipeline whose throughput is
  min(stage rates); the bottleneck stage is a first-class output, the
  GPU-idle-due-to-data gauge is the north star, and the KV-cache
  offload toggle is the most 2026-current concept in the suite.
* **CloudIQ / APEX AIOps** — the meta-instrument: a simulated console
  observing a synthetic fleet with *injected, known* issues, so the
  anomaly detector's tuning can be scored (precision/recall against
  ground truth), the capacity forecast can be wrong in measurable ways,
  and the gray failure caught-by-trend-missed-by-status pays off.

Tick = one sim-hour. Deterministic throughout: injected issues are
scripted, and "noise" is a sum of fixed sinusoids, never random.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Constant(CamelModel):
    value: float
    unit: str
    source: str
    estimated: bool
    blurb: str


# --- Configuration --------------------------------------------------------

Product = Literal["aidataplatform", "cloudiq"]

STAGES = ["ingest", "process", "index", "serve"]


class DataConfig(CamelModel):
    product: Product = "aidataplatform"
    # Pipeline stage capacities, TB/h.
    ingest_tbh: float = Field(20, ge=1, le=200)
    process_tbh: float = Field(6, ge=1, le=200)
    index_tbh: float = Field(15, ge=1, le=200)
    serve_tbh: float = Field(30, ge=1, le=200)
    gpu_processing: bool = False          # ×6-class speedup on process (verify)
    gpu_analytics: bool = False           # ×6-class scan speedup (verify)
    kv_offload: bool = False              # KV cache spills to shared storage
    # CloudIQ console.
    anomaly_k: float = Field(3.0, ge=1.0, le=6.0)   # baseline ± kσ
    weight_capacity: int = Field(40, ge=0, le=100)
    weight_performance: int = Field(40, ge=0, le=100)
    weight_config: int = Field(20, ge=0, le=100)


class Workload(CamelModel):
    raw_arrival_tbh: float = Field(8, ge=0, le=200)
    gpu_read_demand_tbh: float = Field(10, ge=0, le=200)
    inference_sessions_demand: int = Field(60, ge=0, le=1000)
    long_context_pct: int = Field(30, ge=0, le=100)
    analytics_scan_tbh: float = Field(20, ge=0, le=500)


EventAction = Literal[
    "set-workload",
    "fix-stage",          # value encodes stage index; raises its rate ×2
    "toggle-kv",          # KV offload on/off mid-run
    "toggle-gpu-process", # GPU processing on/off mid-run
    "inject-capacity",    # CloudIQ: an array starts filling fast
    "inject-gray",        # CloudIQ: silent packet loss on a switch
    "inject-fan-drift",   # CloudIQ: a fan slowly rises — green but sick
    "demand-change",      # CloudIQ: fill rate doubles (forecast lag demo)
    "expand-capacity",    # CloudIQ: act on the forecast
]


class SimEvent(CamelModel):
    at_h: int = Field(ge=0)
    action: EventAction
    value: float | None = None
    workload: Workload | None = None


class Scenario(CamelModel):
    config: DataConfig = DataConfig()
    workload: Workload = Workload()
    duration_h: int = Field(360, ge=24, le=2160)
    events: list[SimEvent] = Field(default_factory=list)


RuleLevel = Literal["ok", "warning", "error"]


class Validation(CamelModel):
    rule_id: str
    level: RuleLevel
    message: str
    source: str


# --- Simulation output ----------------------------------------------------

class SimState(CamelModel):
    t_h: int
    # Pipeline.
    stage_rates_tbh: dict[str, float]
    stage_backlogs_tb: dict[str, float]
    bottleneck: str
    throughput_tbh: float
    freshness_lag_h: float
    gpu_idle_due_to_data_pct: float
    sessions_capacity: int
    sessions_active: int
    token_latency_tax_pct: float
    analytics_scan_rate_tbh: float
    # CloudIQ.
    health_score_worst: float
    health_score_mean: float
    anomalies_flagged_cum: int
    true_positives_cum: int
    false_positives_cum: int
    precision_pct: float
    recall_pct: float
    issues_active: int
    issues_detected: int
    mttd_h: float
    array_fill_pct: float
    days_to_full_forecast: float
    forecast_error_days: float
    device_status_all_green: bool
    region_load: dict[str, float]


class LogEntry(CamelModel):
    t_h: int
    severity: Literal["info", "warning", "critical"]
    message: str


class Summary(CamelModel):
    mean_throughput_tbh: float
    final_bottleneck: str
    peak_freshness_lag_h: float
    mean_gpu_idle_pct: float
    precision_pct: float
    recall_pct: float
    mttd_h: float
    capacity_outage: bool


class SimResponse(CamelModel):
    validations: list[Validation]
    trace: list[SimState]
    log: list[LogEntry]
    summary: Summary


# --- Maps -------------------------------------------------------------------

RegionKind = Literal[
    "source", "stage", "gpu", "kvcache", "analytics", "fleet", "detector",
    "forecast", "console",
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


class DataMap(CamelModel):
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
    config: DataConfig


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
