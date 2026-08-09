"""Data models for the PowerVault ME5 storage physics simulator.

Same conventions as every twin: snake_case in Python, camelCase over the
wire. Same pattern as the R760 thermal simulator: ``POST /api/simulate``
takes a ``Scenario`` (array configuration, workload dials, timed events)
and returns the deterministic trace; the frontend owns only the playback
clock.

Scope framing: this is the suite's *first* storage sim on purpose — the
ME5 is Dell's entry SAN, and its physics is classic RAID with nothing
else in the way. No dedupe, no tiering, no snapshots in the model: drive
mechanics, RAID write penalties, dual controllers, and the rebuild
window. Correct relationships and orders of magnitude, not a benchmark.
Every constant lives in ``constants.py`` with a source field.
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

ArrayModel = Literal["ME5012", "ME5024"]
DriveType = Literal["hdd-7.2k", "hdd-10k", "ssd"]
RaidLevel = Literal["1", "5", "6", "10"]
HostInterface = Literal["iSCSI", "SAS", "FC"]

# Populated-slot ceilings per enclosure model (base enclosure only — the
# real ME5 chains expansion shelves; one shelf is enough for the physics).
MODEL_MAX_DRIVES: dict[str, int] = {"ME5012": 12, "ME5024": 24}

DRIVE_TB_OPTIONS = [2, 4, 8, 12, 16, 20]

# RAID write penalty: how many physical disk I/Os one host write costs.
# This is arithmetic, not an estimate: mirrors write twice; RAID 5 must
# read old data + old parity, then write new data + new parity (4); RAID 6
# does the same against two parities (6).
WRITE_PENALTY: dict[str, int] = {"1": 2, "10": 2, "5": 4, "6": 6}

# Concurrent drive failures a healthy group survives. RAID 10's true answer
# is "1 guaranteed, more if you're lucky about which mirror" — the engine
# deliberately models the unlucky case and says so in the log.
FAILURE_TOLERANCE: dict[str, int] = {"1": 1, "10": 1, "5": 1, "6": 2}


class ArrayConfig(CamelModel):
    model: ArrayModel = "ME5024"
    drive_type: DriveType = "hdd-10k"
    drive_count: int = Field(24, ge=2, le=24)   # populated slots
    drive_tb: int = 4                            # one of DRIVE_TB_OPTIONS
    raid_level: RaidLevel = "6"
    spares: int = Field(1, ge=0, le=4)           # global hot spares
    controllers: int = Field(2, ge=1, le=2)
    host_interface: HostInterface = "iSCSI"


class Workload(CamelModel):
    """Host offered load. ``offered_kiops`` is what the hosts are asking
    for; the array serves what its drives and controllers can carry."""

    offered_kiops: float = Field(2.0, ge=0, le=500)
    read_pct: int = Field(70, ge=0, le=100)
    block_kb: int = Field(8, ge=1, le=1024)


EventAction = Literal[
    "set-workload",       # swap the workload dials mid-run
    "fail-drive",         # index into populated slots
    "replace-drive",      # insert a fresh drive into a failed slot
    "fail-controller",    # one controller drops
    "restore-controller",
    "set-offered",        # value = kIOPS
]


class SimEvent(CamelModel):
    """A timed intervention — clicks on the array become deterministic
    events so the engine stays pure and every run is reproducible."""

    at_min: int = Field(ge=0)
    action: EventAction
    index: int | None = None
    value: float | None = None
    workload: Workload | None = None


class Scenario(CamelModel):
    config: ArrayConfig = ArrayConfig()
    workload: Workload = Workload()
    duration_min: int = Field(720, ge=10, le=200000)
    tick_minutes: int = Field(1, ge=1, le=120)   # storage time is long; rebuilds are days
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
    """One sim tick (t in sim-minutes); pure data the renderer consumes."""

    t: int
    online: bool
    # Service.
    offered_kiops: float
    served_read_kiops: float
    served_write_kiops: float
    served_kiops: float
    throughput_mbps: float
    latency_ms: float
    # The disk-side ledger — the IOPS-balance identity asserted in tests:
    # backend_disk_kiops == reads×read_cost + writes×write_penalty.
    backend_disk_kiops: float
    read_cost: float           # 1.0 healthy; >1 while degraded (reconstruct reads)
    write_penalty: int
    disk_util_pct: float
    saturated: bool
    # Hardware.
    controllers_alive: int
    drives_serving: int
    drives_failed: int
    spares_left: int
    degraded: bool
    rebuilding: bool
    rebuild_pct: float
    rebuild_hours_remaining: float
    risk_index: float          # 0–100 second-failure exposure, illustrative
    # Capacity ledger — raw = usable + protection overhead + spares, exact.
    raw_tb: float
    usable_tb: float
    overhead_tb: float
    spare_tb: float
    # Region id → state string for the enclosure drawing. Keys must exist
    # in the anatomy (asserted in tests). States: ok | failed | rebuilding
    # | spare | empty | offline | degraded.
    region_states: dict[str, str]


class LogEntry(CamelModel):
    t: int
    severity: Literal["info", "warning", "critical"]
    message: str


class Summary(CamelModel):
    peak_served_kiops: float
    peak_latency_ms: float
    steady_served_kiops: float
    rebuild_hours_total: float
    data_lost: bool
    offline_reason: str = ""
    usable_tb: float


class SimResponse(CamelModel):
    validations: list[Validation]
    trace: list[SimState]
    log: list[LogEntry]
    summary: Summary


# --- Enclosure map ---------------------------------------------------------

RegionKind = Literal["drive", "controller", "power", "cache"]


class ArrayRegion(CamelModel):
    id: str
    kind: RegionKind
    label: str
    x: float
    y: float
    w: float
    h: float
    description: str


class ArrayMap(CamelModel):
    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[ArrayRegion]
    overview: str
    sources: list[dict[str, str]] = Field(default_factory=list)


# --- Presets & teaching layer ----------------------------------------------

class ConfigPreset(CamelModel):
    id: str
    name: str
    blurb: str
    config: ArrayConfig


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
