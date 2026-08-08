"""Data models for the storage-platforms simulator (physics_specs/02).

One shared Archetype-B engine — workload generator, M/M/1-style
queueing knee, capacity arithmetic (raw → usable → effective), rebuild
dynamics — parameterized into six product personalities: PowerStore,
PowerMax, PowerScale, ObjectScale, PowerFlex, and the Exascale
meta-simulator that partitions one rack's node pool among the others.

The clock: one tick = **one sim-hour** (storage stories happen over
rebuild-hours and capacity-months, not seconds); the frontend still owns
playback. Conventions as everywhere: camelCase wire, pure engine,
constants with sources.
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

Product = Literal[
    "powerstore", "powermax", "powerscale", "objectscale", "powerflex",
    "exascale",
]
DriveClass = Literal["nvme", "ssd", "hdd"]
Protection = Literal["raid5", "raid6", "mirror", "ec8+2", "ec16+4"]
Srdf = Literal["off", "sync", "async"]


class StorageConfig(CamelModel):
    product: Product = "powerstore"
    units: int = Field(2, ge=1, le=100)       # appliances / bricks / nodes
    drives_per_unit: int = Field(12, ge=2, le=24)
    drive_tb: float = Field(15.36, ge=1, le=61.44)
    drive_class: DriveClass = "nvme"
    protection: Protection = "ec8+2"
    # PowerFlex: the network is the array.
    nic_gbps: int = Field(25, ge=10, le=100)
    # PowerMax replication.
    srdf: Srdf = "off"
    distance_km: int = Field(0, ge=0, le=1000)
    # ObjectScale.
    small_objects: bool = False               # small-object metadata tax
    immutable: bool = False                   # object lock / versioning
    # Exascale partition of the node pool (units must cover the sum).
    lightning_units: int = Field(0, ge=0)
    file_units: int = Field(0, ge=0)
    object_units: int = Field(0, ge=0)
    block_units: int = Field(0, ge=0)


class Workload(CamelModel):
    """The workload generator's dials (spec 02)."""

    iops_demand_k: int = Field(100, ge=0, le=20000)
    block_kb: int = Field(8, ge=4, le=1024)
    read_pct: int = Field(70, ge=0, le=100)
    sequential_pct: int = Field(20, ge=0, le=100)
    working_set_fit_pct: int = Field(60, ge=0, le=100)  # → cache-hit rate
    ingest_tb_day: float = Field(2.0, ge=0, le=500)
    snapshots_per_day: int = Field(0, ge=0, le=48)
    reduction_ratio: float = Field(3.0, ge=1.0, le=10.0)  # dedupe+compress


EventAction = Literal[
    "set-workload",
    "fail-drive",
    "fail-controller",    # PowerStore: one of the pair; PowerMax: a director
    "fail-node",          # scale-out products
    "add-nodes",          # value: how many (PowerFlex elasticity)
    "attempt-delete",     # ObjectScale immutability demo
    "write-burst",        # value: ×multiplier on write demand for 6 h
]


class SimEvent(CamelModel):
    at_h: int = Field(ge=0)
    action: EventAction
    value: float | None = None
    workload: Workload | None = None


class Scenario(CamelModel):
    config: StorageConfig = StorageConfig()
    workload: Workload = Workload()
    duration_h: int = Field(168, ge=6, le=2160)   # a week by default
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
    online: bool
    # Capacity ledger (raw → usable → effective is asserted in tests).
    raw_tb: float
    usable_tb: float
    effective_tb: float
    used_tb: float
    snapshot_tb: float
    used_pct: float
    reduction_ratio: float
    capacity_alert: Literal["none", "80", "90", "95"]
    # Performance.
    iops_capacity_k: float
    iops_delivered_k: float
    iops_demand_k: float
    throughput_gbs: float
    latency_ms: float
    p99_ms: float
    utilization_pct: float
    cache_hit_pct: float
    saturated: bool
    # Resilience.
    units_online: int
    rebuilding: bool
    rebuild_pct: float
    rebuild_hours_left: float
    exposure: bool            # rebuild window: one more failure loses data
    # Replication (PowerMax).
    srdf_latency_ms: float
    rpo_seconds: float
    # Exascale meta-view: per-pool utilization.
    pool_util_pct: dict[str, float]
    gpu_idle_due_to_data_pct: float
    region_load: dict[str, float]   # map coloring, 0–100


class LogEntry(CamelModel):
    t_h: int
    severity: Literal["info", "warning", "critical"]
    message: str


class Summary(CamelModel):
    peak_latency_ms: float
    steady_latency_ms: float
    min_delivered_ratio: float    # worst delivered/demand over the run
    hours_saturated: int
    rebuild_hours: float
    final_used_pct: float
    data_survived: bool


class SimResponse(CamelModel):
    validations: list[Validation]
    trace: list[SimState]
    log: list[LogEntry]
    summary: Summary


# --- Product maps ----------------------------------------------------------

RegionKind = Literal[
    "controller", "media", "cache", "node", "network", "namespace",
    "replication", "pool", "client",
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


class ProductMap(CamelModel):
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
    config: StorageConfig


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
