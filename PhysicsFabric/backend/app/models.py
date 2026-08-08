"""Data models for the network-fabrics simulator (physics_specs/03).

One flow-level fluid engine (no packets — per-link utilization from
routed flow demand) with three product personalities: the **E3200**
campus access line (PoE budgets, STP failover — the same physics at
human scale), the **SN6000** AI Ethernet fabric (ECMP hash collisions
vs adaptive routing, lossless RoCE, CPO vs pluggable optics power), and
the Dell-integrated **Quantum-X800** InfiniBand (lossless by
construction — drops are unexpressible — plus SHARP in-network
collectives).

Tick = one second. Conventions as everywhere in the suite.
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

Product = Literal["e3200", "sn6000", "x800"]
Pattern = Literal["uniform", "incast", "alltoall", "elephant"]

UPLINK_GBPS = {
    "e3200": [1, 10, 25],
    "sn6000": [400, 800],
    "x800": [400, 800],
}


class FabricConfig(CamelModel):
    product: Product = "sn6000"
    spines: int = Field(2, ge=1, le=8)
    leaves: int = Field(4, ge=2, le=16)
    endpoints_per_leaf: int = Field(16, ge=1, le=64)
    downlink_gbps: int = Field(400, ge=1, le=800)
    uplink_gbps: int = Field(800, ge=1, le=800)
    # SN6000 personality toggles.
    adaptive_routing: bool = False
    lossless_roce: bool = False
    cpo_optics: bool = False
    # X800.
    sharp: bool = False
    # E3200 campus/PoE world (leaves = access switches).
    poe_aps: int = Field(0, ge=0, le=200)
    poe_cameras: int = Field(0, ge=0, le=200)
    poe_phones: int = Field(0, ge=0, le=200)
    poe_budget_w: int = Field(740, ge=0, le=2000)
    psu_redundant: bool = True


class Workload(CamelModel):
    demand_gbps: int = Field(1000, ge=0, le=200000)
    pattern: Pattern = "uniform"
    collective_pct: int = Field(0, ge=0, le=100)  # all-reduce share (SHARP)


EventAction = Literal[
    "set-workload",
    "kill-spine",
    "restore-spine",
    "kill-uplink",        # E3200: one of the access uplinks (STP failover)
    "gray-failure",       # a link silently drops 0.1% — nothing looks down
    "clear-gray",
    "toggle-adaptive",
    "toggle-sharp",
    "kill-psu",           # E3200: PoE budget halves
]


class SimEvent(CamelModel):
    at_s: int = Field(ge=0)
    action: EventAction
    value: float | None = None
    workload: Workload | None = None


class Scenario(CamelModel):
    config: FabricConfig = FabricConfig()
    workload: Workload = Workload()
    duration_s: int = Field(600, ge=10, le=3600)
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
    # Flow accounting: delivered + lost == demanded (drop mode); in
    # lossless modes lost is zero by construction and the excess waits.
    demanded_gbps: float
    delivered_gbps: float
    lost_gbps: float
    dropped_pps: float
    pause_events_s: float      # lossless Ethernet: PFC pauses per second
    stall_us_per_s: float      # InfiniBand: credit-stall time
    worst_link_pct: float
    mean_link_pct: float
    oversub_ratio: float
    latency_us: float
    fct_ms: float              # flow-completion-time proxy (64 MB flow)
    allreduce_gbps: float      # effective collective rate (SHARP story)
    spines_alive: int
    # Power.
    fabric_power_w: float
    optics_power_w: float
    asic_power_w: float
    # The gray-failure liar: device status vs experienced goodput.
    status_all_green: bool
    goodput_penalty_pct: float
    # E3200 PoE.
    poe_budget_w: float
    poe_demand_w: float
    devices_powered: int
    devices_total: int
    region_load: dict[str, float]


class LogEntry(CamelModel):
    t: int
    severity: Literal["info", "warning", "critical"]
    message: str


class Summary(CamelModel):
    peak_worst_link_pct: float
    total_drops: float
    min_delivered_ratio: float
    seconds_congested: int
    peak_latency_us: float
    fabric_power_w: float


class SimResponse(CamelModel):
    validations: list[Validation]
    trace: list[SimState]
    log: list[LogEntry]
    summary: Summary


# --- Fabric maps ----------------------------------------------------------

RegionKind = Literal[
    "spine", "leaf", "endpoint", "optics", "telemetry", "manager",
    "access", "distribution", "device", "power",
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


class FabricMap(CamelModel):
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
    config: FabricConfig


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
