"""Data models for the PowerProtect Data Domain dedupe physics simulator.

Same conventions as every twin: snake_case in Python, camelCase over the
wire. Same trace pattern as the R760 thermal twin: ``POST /api/simulate``
takes a ``Scenario`` (appliance, dataset properties, schedule, timed
events) and returns the deterministic trace — one ``SimState`` per
simulated backup day. The frontend owns only the playback clock.

The one idea, and the reason this app exists apart from the narrative
DellPowerProtect twin: **the dedupe ratio is emergent, not configured.**
Nothing in the scenario sets a ratio. It falls out of the data's own
properties — daily change rate, retention length, entropy — the same way
the R760 twin's exhaust temperature falls out of watts and airflow.

Scope framing: this is an analytic model of chunk liveness, not a
hash-level simulation. Correct relationships and orders of magnitude;
every constant lives in ``constants.py`` with a source field.
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

ApplianceId = Literal["dd3410", "dd9910", "dd-all-flash"]


class Appliance(CamelModel):
    """One Data Domain model — capacity, index RAM, and ingest headroom.
    Values come from constants.py-adjacent APPLIANCES data with the same
    honesty rule (sources cited, estimates flagged)."""

    id: ApplianceId
    name: str
    usable_tb: float
    index_ram_gb: float
    base_ingest_gbps: float
    blurb: str
    source: str
    estimated: bool


class Dataset(CamelModel):
    """The protected data's own properties — the inputs the ratio
    emerges from."""

    full_tb: float = Field(50, gt=0, le=2000, description="Logical size of one full backup")
    daily_change_pct: float = Field(2.0, ge=0, le=100)
    entropy_pct: float = Field(30, ge=0, le=100, description="0 text-like, 100 encrypted/random")


class Schedule(CamelModel):
    retention_days: int = Field(30, ge=1, le=3650, description="Generations kept")


EventAction = Literal[
    "set-change-rate",        # value = %/day
    "set-entropy",            # value = 0–100
    "enable-host-encryption",  # source encrypts before backup — fresh session keys daily
    "disable-host-encryption",
    "ransomware-start",       # value = % of dataset newly encrypted per day
    "ransomware-stop",
]


class SimEvent(CamelModel):
    """A timed intervention, in sim-days — deterministic so the engine
    stays pure and the trace reproducible."""

    at_day: int = Field(ge=0)
    action: EventAction
    value: float | None = None


class Scenario(CamelModel):
    appliance: ApplianceId = "dd9910"
    dataset: Dataset = Dataset()
    schedule: Schedule = Schedule()
    duration_days: int = Field(90, ge=2, le=730)
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
    """One backup day; pure data the renderer consumes."""

    day: int
    generations_retained: int
    # The capacity ledger — the identity the tests assert:
    # dedupe_ratio == logical_tb / physical_tb, every day.
    logical_tb: float
    physical_tb: float
    dedupe_ratio: float
    todays_logical_tb: float
    todays_novel_physical_tb: float
    gc_reclaimed_tb: float
    capacity_used_pct: float
    # The entropy instrument — the smoke alarm.
    stream_entropy_pct: float
    entropy_alarm: bool
    host_encrypted: bool
    ransomware_active: bool
    encrypted_fraction_pct: float
    # Ingest vs fingerprint-index pressure.
    unique_chunks_m: float
    index_gb: float
    index_pressure_pct: float
    ingest_gbps: float
    logical_ingest_gbps: float
    backup_window_hours: float
    # Region id → activity 0..1, keys pinned to the anatomy in tests.
    region_load: dict[str, float]


class LogEntry(CamelModel):
    day: int
    severity: Literal["info", "warning", "critical"]
    message: str


class Summary(CamelModel):
    final_ratio: float
    final_logical_tb: float
    final_physical_tb: float
    peak_stream_entropy_pct: float
    alarm_day: int          # -1 if the alarm never fired
    capacity_full_day: int  # -1 if the store never filled
    final_capacity_used_pct: float


class SimResponse(CamelModel):
    validations: list[Validation]
    trace: list[SimState]
    log: list[LogEntry]
    summary: Summary


# --- Pipeline map (the "anatomy": stream → chunk → index → store) ----------

RegionKind = Literal["source", "transport", "chunk", "index", "store", "clean"]


class PipelineRegion(CamelModel):
    id: str
    kind: RegionKind
    label: str
    x: float
    y: float
    w: float
    h: float
    description: str


class PipelineMap(CamelModel):
    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[PipelineRegion]
    overview: str
    sources: list[dict[str, str]] = Field(default_factory=list)


# --- Presets & teaching layer ----------------------------------------------

class DatasetPreset(CamelModel):
    id: str
    name: str
    blurb: str
    appliance: ApplianceId
    dataset: Dataset
    schedule: Schedule


class GuidedScenario(CamelModel):
    """A scripted walkthrough: sets the scenario, narrates what to watch,
    ends with a question the user can verify by experiment."""

    id: str
    title: str
    narration: list[str]
    question: str
    scenario: Scenario


class Explain(CamelModel):
    """Explain-mode content: the arithmetic behind a readout, with
    placeholders the frontend substitutes with live values."""

    id: str
    title: str
    equation: str
    inputs: list[str]
    explanation: str
