"""Data models for the fleet-operations simulator (physics_specs/04).

One Archetype-D fleet engine — sites × nodes, workload placement, N+1
HA math, deterministic MTBF faults, config drift, and the teaching
core: every operation costs **admin-hours**, and central automation vs
manual changes that cost by an order of magnitude. Five product
personalities: VxRail (lifecycle bundle), Dell Private Cloud (stack
pluralism + catalog), APEX (pure Archetype-F economics), NativeEdge /
Distributed Private Cloud (zero-touch at 10–1,000 sites), and
Automation Studio (the pipeline integrator, built last).

Tick = one sim-day. Faults are deterministic (a fault every N
node-days, rotating around the fleet) — no randomness, per the suite's
purity rule.
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

Product = Literal["vxrail", "privatecloud", "apex", "nativeedge", "automationstudio"]
OpsMode = Literal["manual", "automated"]
DemandCurve = Literal["steady", "seasonal", "spiky"]
SiteClass = Literal["factory", "store", "clinic"]


class FleetConfig(CamelModel):
    product: Product = "vxrail"
    sites: int = Field(1, ge=1, le=1000)
    nodes_per_site: int = Field(4, ge=1, le=16)
    ops_mode: OpsMode = "automated"
    # VxRail.
    ftt: int = Field(1, ge=1, le=2)          # failures to tolerate (vSAN policy)
    # Private Cloud.
    stacks: int = Field(1, ge=1, le=2)       # e.g. vSphere + OpenShift
    catalog: bool = True                     # catalog deploys vs artisanal
    # APEX economics.
    committed_vms: int = Field(100, ge=10, le=5000)
    buffer_pct: int = Field(20, ge=0, le=100)
    demand_curve: DemandCurve = "steady"
    # NativeEdge.
    site_class: SiteClass = "store"
    two_node_ha: bool = True
    wan_reliable: bool = True
    # Automation Studio.
    test_gate: bool = True


class Workload(CamelModel):
    vms_per_site: int = Field(20, ge=1, le=1000)
    growth_pct_month: int = Field(3, ge=0, le=50)
    vm_size_capacity: int = Field(10, ge=1, le=100)  # VMs one node can host


EventAction = Literal[
    "deploy-sites",      # value: how many new sites
    "node-fault",        # force one now (on top of the MTBF schedule)
    "cluster-update",    # the monthly patch, on demand
    "bad-change",        # Automation Studio's gate demo
    "wan-outage",        # value: days (NativeEdge disconnected operation)
    "demand-spike",      # value: ×multiplier for 30 days (APEX)
]


class SimEvent(CamelModel):
    at_d: int = Field(ge=0)
    action: EventAction
    value: float | None = None


class Scenario(CamelModel):
    config: FleetConfig = FleetConfig()
    workload: Workload = Workload()
    duration_d: int = Field(180, ge=10, le=730)
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
    # The teaching core: the admin-hours ledger.
    admin_hours_today: float
    admin_hours_cum: float
    admin_hours_per_month: float      # trailing-30-day rate
    # Fleet state.
    sites_deployed: int
    nodes_total: int
    nodes_healthy: int
    vms_running: int
    vms_demand: int
    capacity_vms: int
    headroom_pct: float
    exposure: bool                    # a failure now would lose service
    # Software currency & drift.
    version_current_pct: float
    drift_count: int
    # Availability.
    outage_minutes_cum: float
    availability_pct: float
    truck_rolls: int
    faults_cum: int
    updating: bool
    # APEX economics.
    monthly_bill: float
    commitment_utilization_pct: float
    cost_per_vm_hour_asvc: float
    cost_per_vm_hour_capex: float
    region_load: dict[str, float]


class LogEntry(CamelModel):
    t_d: int
    severity: Literal["info", "warning", "critical"]
    message: str


class Summary(CamelModel):
    admin_hours_total: float
    availability_pct: float
    outage_minutes: float
    truck_rolls: int
    faults: int
    final_version_current_pct: float
    total_bill: float
    mean_cost_per_vm_hour_asvc: float
    mean_cost_per_vm_hour_capex: float


class SimResponse(CamelModel):
    validations: list[Validation]
    trace: list[SimState]
    log: list[LogEntry]
    summary: Summary


# --- Fleet maps ------------------------------------------------------------

RegionKind = Literal[
    "controlplane", "site", "node", "workload", "ops", "economics",
    "pipeline", "catalog", "wan",
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


class FleetMap(CamelModel):
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
    config: FleetConfig


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
