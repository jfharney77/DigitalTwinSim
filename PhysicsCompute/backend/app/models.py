"""Data models for the AI-compute physics simulator (physics_specs/01).

One app, three system personalities on a shared engine:

* **XE7745** — 4U air-cooled PCIe-GPU server: positional thermal
  inequality across eight riser slots, a fan wall whose overhead is
  non-trivial at full bore.
* **XE9680** — 6U 8-way HGX server: one SXM baseboard with shared
  thermal fate, per-GPU NICs, and the data-starvation slider that links
  this app to the storage suite.
* **XE9712 + IR7000** — the rack as the unit: liquid loop to a CDU,
  busbar power shelves, residual air fraction, and the IR7000's
  budget-validation rules (built as one model, per the spec's
  implementation note).

Plus the iDRAC panel: a mock Redfish thermal endpoint shaped from the
live SimState (``redfish.py``) — the "from sim to twin" closer.

Conventions as everywhere: snake_case in Python, camelCase on the wire;
``POST /api/simulate`` takes a Scenario, returns the deterministic
trace; the frontend owns the playback clock. Constants live in
``constants.py`` with sources; estimates are flagged.
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

Product = Literal["xe7745", "xe9680", "xe9712"]

CPU_TDP_TIERS = [250, 300, 350, 400, 500]
PCIE_GPU_TDP = [300, 450, 600]           # XE7745 tiers (verify — spec 01)
SXM_GPU_TDP = [700, 1000]                # XE9680: H100-class / B200-class
PSU_7745_W = [2400, 2800]
SHELF_KW = [66, 132, 198]                # IR7000 power-shelf capacity options


class SystemConfig(CamelModel):
    product: Product = "xe9680"
    cpu_tdp_w: int = 350                 # per socket, 2 sockets (air products)
    # XE7745 only:
    pcie_gpus: int = Field(8, ge=0, le=8)
    pcie_gpu_tdp_w: int = 450
    psu_capacity_w: int = 2800           # per PSU, N+N (XE7745/XE9680)
    # XE9680 only:
    sxm_gpu_tdp_w: int = 1000            # ×8, fixed count
    nics: int = Field(8, ge=0, le=10)    # one 400G NIC per GPU
    # XE9712 / IR7000 rack:
    trays: int = Field(18, ge=1, le=18)  # 4 GPUs + 2 CPUs per tray
    shelf_capacity_kw: int = 132         # power-shelf budget (IR7000 rule)
    manifold_capacity_lpm: int = 200     # coolant the manifolds can carry
    coolant_supply_c: float = Field(25, ge=17, le=45)
    coolant_flow_lpm: int = Field(120, ge=30, le=240)


class Workload(CamelModel):
    """Demand dials. ``data_feed_pct`` is the data-starvation slider
    (spec 01, XE9680): the storage pipeline's delivery rate as a cap on
    effective GPU utilization — 100 means fully fed."""

    gpu_pct: int = Field(0, ge=0, le=100)
    cpu_pct: int = Field(0, ge=0, le=100)
    data_feed_pct: int = Field(100, ge=0, le=100)


class Environment(CamelModel):
    inlet_c: float = Field(22, ge=15, le=45)


EventAction = Literal[
    "set-workload",
    "set-inlet",
    "set-data-feed",       # value: %
    "set-coolant-supply",  # value: °C (CDU excursion)
    "degrade-pump",        # value: fraction of flow lost, 0–1
    "restrict-tray",       # index: tray whose coolant is restricted
    "kill-psu",
]


class SimEvent(CamelModel):
    at_s: int = Field(ge=0)
    action: EventAction
    index: int | None = None
    value: float | None = None
    workload: Workload | None = None


class Scenario(CamelModel):
    config: SystemConfig = SystemConfig()
    workload: Workload = Workload()
    environment: Environment = Environment()
    duration_s: int = Field(900, ge=10, le=7200)
    events: list[SimEvent] = Field(default_factory=list)


RuleLevel = Literal["ok", "warning", "error"]


class Validation(CamelModel):
    rule_id: str
    level: RuleLevel
    message: str
    source: str


# --- Simulation output ----------------------------------------------------

class SimState(CamelModel):
    t: int
    powered_on: bool
    # Power balance: components sum to dc_power_w (asserted every tick).
    cpu_power_w: float
    gpu_power_w: float
    nic_power_w: float
    base_power_w: float
    fan_power_w: float
    pump_power_w: float
    dc_power_w: float
    ac_power_w: float
    psu_efficiency: float
    alive_psus: int
    # Thermals.
    gpu_temp_hot_c: float      # worst airflow/coolant position
    gpu_temp_cool_c: float     # best position
    cpu_temp_c: float
    gpus_throttled: int
    # Liquid loop (XE9712 only; zeros elsewhere). Heat split identity:
    # liquid_watts + air_watts == dc_power_w, exactly.
    liquid_watts: float
    air_watts: float
    coolant_supply_c: float
    coolant_return_c: float
    coolant_delta_t_c: float
    flow_lpm: float
    # Airflow (air products).
    fan_rpm_pct: float
    # Performance & the starvation ledger.
    effective_gpu_util_pct: float
    tokens_per_s: float
    gpu_hours_wasted: float    # cumulative, stalls × GPUs
    cooling_overhead_pct: float  # (fan + pump) / IT power
    region_temps: dict[str, float]


class LogEntry(CamelModel):
    t: int
    severity: Literal["info", "warning", "critical"]
    message: str


class Summary(CamelModel):
    peak_dc_w: float
    steady_dc_w: float
    idle_dc_w: float
    peak_tokens_per_s: float
    gpu_hours_wasted: float
    throttle_seconds: int
    shutdown: bool
    shutdown_reason: str = ""


class SimResponse(CamelModel):
    validations: list[Validation]
    trace: list[SimState]
    log: list[LogEntry]
    summary: Summary


# --- System maps ----------------------------------------------------------

RegionKind = Literal[
    "gpu", "cpu", "memory", "storage", "network", "nvswitch", "cooling",
    "power", "management", "cdu", "manifold", "tray",
]


class SystemRegion(CamelModel):
    id: str
    kind: RegionKind
    label: str
    x: float
    y: float
    w: float
    h: float
    description: str


class SystemMap(CamelModel):
    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[SystemRegion]
    overview: str
    sources: list[dict[str, str]] = Field(default_factory=list)


# --- Presets & teaching layer ---------------------------------------------

class ConfigPreset(CamelModel):
    id: str
    name: str
    blurb: str
    config: SystemConfig


class WorkloadPreset(CamelModel):
    id: str
    name: str
    workload: Workload


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
