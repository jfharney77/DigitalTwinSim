"""Data models for the security & resilience simulator (physics_specs/05).

One Archetype-E timeline engine — sim-hours tick, backups per policy,
an abstract incident script, RPO/RTO as first-class instruments — with
four product personalities: PowerProtect (backup + Cyber Vault air
gap), Cyber Detect (the detection layer and its ROC knob), MDR (the
alert-queue operations game), and Fort Zero (the access-graph mode:
blast radius = reachable set).

**Hard scope boundary (spec 05, non-negotiable, test-enforced):** these
simulators teach *defensive architecture* — backup topology, detection
placement, recovery mechanics, zero-trust structure. The "attack" is an
abstract scripted event ("corruption begins at T, spreads at X GB/h")
with zero technique detail. No exploit content, no evasion, no
offensive realism. If a scenario can't be expressed as abstract
data-corruption rates and timestamps, it doesn't belong here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

SCOPE_NOTE = (
    "These simulators teach defensive architecture only: backup "
    "topology, detection placement, recovery mechanics, zero-trust "
    "structure. The 'attack' is an abstract scripted event — a data-"
    "corruption rate and a timestamp. No exploit content, no technique "
    "detail, no offensive realism."
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

Product = Literal["powerprotect", "cyberdetect", "mdr", "fortzero"]
ResponseModel = Literal["inhouse", "mdr"]
Architecture = Literal["perimeter", "zerotrust"]


class ResilienceConfig(CamelModel):
    product: Product = "powerprotect"
    # The estate.
    estate_tb: float = Field(200, ge=1, le=2000)
    change_gb_day: float = Field(500, ge=10, le=20000)
    # Backup policy (PowerProtect / Cyber Detect).
    backup_every_h: int = Field(24, ge=1, le=168)
    retention_copies: int = Field(14, ge=1, le=90)
    dedupe_ratio: float = Field(10, ge=1, le=40)
    vault: bool = True
    vault_sync_every_h: int = Field(24, ge=6, le=168)
    restore_gbps: float = Field(1.0, ge=0.1, le=10)
    # Detection (Cyber Detect).
    detection: bool = False
    sensitivity: int = Field(5, ge=1, le=10)   # higher = earlier + noisier
    # Response (MDR).
    response: ResponseModel = "inhouse"
    noise_alerts_day: int = Field(40, ge=0, le=500)
    inhouse_capacity_day: int = Field(60, ge=1, le=1000)
    # Fort Zero (access-graph mode).
    architecture: Architecture = "perimeter"
    assets: int = Field(60, ge=10, le=500)     # users+devices+apps+stores
    grants_per_user: int = Field(3, ge=1, le=20)
    microseg_segments: int = Field(1, ge=1, le=20)
    review_cadence_days: int = Field(0, ge=0, le=180)  # 0 = never


EventAction = Literal[
    "incident",          # corruption begins; value = spread GB/h
    "slow-incident",     # low-and-slow corruption; value = spread GB/h
    "attempt-restore",   # start recovery from the best known point
    "contain",           # manual containment now (stops the spread)
    "compromise",        # Fort Zero: one identity marked hostile (abstract)
    "access-review",     # Fort Zero: prune stale grants now
]


class SimEvent(CamelModel):
    at_h: int = Field(ge=0)
    action: EventAction
    value: float | None = None


class Scenario(CamelModel):
    config: ResilienceConfig = ResilienceConfig()
    duration_h: int = Field(720, ge=24, le=2160)
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
    # The estate & the (abstract) damage.
    clean_tb: float
    corrupted_tb: float
    incident_active: bool
    contained: bool
    # Backups.
    backup_storage_tb: float
    repo_copies_intact: int
    vault_copies_intact: int
    last_clean_point_age_h: float     # the RPO gauge
    # Detection.
    corruption_score: float           # 0–100, what a scanner would read
    detected: bool
    detection_latency_h: float        # incident start → first alert (once known)
    false_alarms_cum: int
    investigation_hours_cum: float
    # Response (MDR).
    alerts_backlog: int
    time_to_contain_h: float          # once containment happens
    blast_radius_gb: float
    # Recovery.
    restoring: bool
    restore_progress_pct: float
    rto_hours: float                  # live estimate (or actual once done)
    recovered: bool
    failed_restores: int
    # Fort Zero.
    reachable_assets: int
    policy_checks_per_session: int
    stale_grants: int
    region_load: dict[str, float]


class LogEntry(CamelModel):
    t_h: int
    severity: Literal["info", "warning", "critical"]
    message: str


class Summary(CamelModel):
    rpo_hours: float                  # data lost at recovery, as hours of change
    rto_hours: float
    blast_radius_gb: float
    detection_latency_h: float
    time_to_contain_h: float
    false_alarms: int
    data_recovered_tb: float
    recovery_succeeded: bool
    failed_restores: int
    peak_reachable_assets: int


class SimResponse(CamelModel):
    validations: list[Validation]
    trace: list[SimState]
    log: list[LogEntry]
    summary: Summary


# --- Maps -------------------------------------------------------------------

RegionKind = Literal[
    "estate", "backup", "gap", "vault", "analytics", "queue", "responder",
    "identity", "segment", "policy",
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


class ResilienceMap(CamelModel):
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
    config: ResilienceConfig


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
