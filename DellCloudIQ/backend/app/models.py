"""Data models for the CloudIQ / Dell AIOps digital twin.

CloudIQ is not a box — it is Dell's cloud-native AIOps observability SaaS
(renamed APEX AIOps Infrastructure Observability in 2024, then **Dell
AIOps** in 2025). So the shared
"anatomy" is not a chassis floorplan but a **platform architecture diagram**
(the telemetry-to-insight pipeline), and the "power-on trace" is the
**lifecycle of a batch of telemetry becoming an actionable insight**. The
model shapes are renamed to fit — ``PlatformMap`` / ``PlatformRegion`` instead
of ``ChassisAnatomy`` / ``ChassisRegion``, and ``PipelineState`` instead of
``PowerOnState`` — but the wire shape and camelCase rules are identical to the
hardware twins, so the frontend and its tests carry over. (Same move the
iDRAC twin made with ``SubsystemMap`` / ``Block``.)

snake_case in Python, camelCase over the wire (activeRegions, healthScore,
regionIds, ...). None of the fields camelize ambiguously, so no explicit
aliases are needed — if you add one that does, pin it with ``Field(alias=...)``
and check frontend/src/types.ts by hand (see CLAUDE.md).
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from twinkit.models import CamelModel

RegionKind = Literal[
    "source",     # monitored Dell systems (storage, servers, network, ...)
    "gateway",    # Secure Connect Gateway / AIOps Collector / SupportAssist
    "ingest",     # cloud ingestion + data lake
    "analytics",  # the ML engine: health scoring, anomaly detection, forecast
    "security",   # cybersecurity monitoring engine
    "insight",    # surfaced insights + the CloudIQ / AIOps web & mobile app
    "assistant",  # the generative-AI AIOps Assistant
    "action",     # notifications & integrations (webhooks, ITSM, email/mobile)
]

# The lifecycle of telemetry becoming an insight — the "trace".
PipelinePhase = Literal[
    "idle",      # systems healthy and connected; nothing anomalous in flight
    "collect",   # telemetry gathered on the monitored Dell systems
    "transmit",  # Secure Connect Gateway sends it one-way to Dell's cloud
    "ingest",    # cloud ingests + normalizes across the fleet
    "analyze",   # ML engine scores health, detects anomalies, forecasts
    "detect",    # a risk crosses threshold — health score drops
    "surface",   # the insight appears in the CloudIQ / AIOps UI
    "assist",    # the AIOps Assistant explains it and recommends a fix
    "notify",    # notifications / ITSM / webhooks fire; a later collection rescoring
    # --- the "connected, no data" failure scenario (engine.simulate_scenario).
    # Additive: the happy path never enters these phases.
    "register",  # the system is onboarded in the portal; no score exists yet
    "handshake", # the gateway's connection test to Dell passes — "connected"
    "blocked",   # the telemetry upload is refused at the customer's own egress
    "starved",   # collection intervals pass and the cloud receives nothing
    "stale",     # the portal lists the system as not sending; still no score
    "repair",    # the admin unblocks the upload at the proxy, customer side
    "backfill",  # the waiting telemetry flows, one way, as always
    "resume",    # a first real Health Score, computed from delivered data
]

# What the Health Score readout is allowed to claim. "fresh" — computed from
# telemetry that actually arrived. "no-data" — nothing has arrived, so there is
# no score to show: CloudIQ draws a grey dash, never a green number.
ScoreState = Literal["fresh", "no-data"]


class Photo(CamelModel):
    """An illustration of the component; ``credit`` must always be rendered."""

    url: str
    caption: str
    credit: str


class PlatformRegion(CamelModel):
    """One functional block of the AIOps platform, placed in the diagram."""

    id: str
    kind: RegionKind
    label: str
    x: float
    y: float
    w: float
    h: float
    description: str
    photo: Photo | None = None


class SourceLink(CamelModel):
    label: str
    url: str


class Stat(CamelModel):
    label: str
    value: str


class PlatformMap(CamelModel):
    """The AIOps platform architecture diagram. ``width``/``height`` set the
    viewBox; the flow runs left (telemetry in) to right (insights & actions)."""

    id: str
    name: str
    vendor: str
    form_factor: str  # e.g. "Cloud-native SaaS" (kept for wire-shape parity)
    generation: str
    year: int
    width: float
    height: float
    regions: list[PlatformRegion]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class PipelineState(CamelModel):
    """One step of the telemetry-to-insight pipeline; pure data the renderer
    consumes. Replaces the hardware twins' watts/fan telemetry with the
    signature CloudIQ metrics: pipeline progress and the Health Score."""

    step: int
    phase: PipelinePhase
    label: str
    description: str
    # Platform regions in the architecture diagram lit up at this step.
    active_regions: list[str]
    # Pipeline progress, 0 → 100, monotonic.
    progress_percent: int = Field(ge=0, le=100)
    # The CloudIQ Health Score (0–100): 100 when healthy, drops when a risk is
    # detected, recovers once a later collection shows the issue cleared.
    health_score: int = Field(ge=0, le=100)
    # Telemetry data points processed so far across the fleet (illustrative).
    data_points: int = 0
    # Illustrative pipeline latency in seconds (not measured timing).
    elapsed_seconds: int
    # UI dwell ticks; the ML analyze stage gets the most.
    cycle_cost: int = 1
    # --- additive fields for failure scenarios; the defaults are the happy
    # path's truth, so its trace is unchanged in every original field.
    # Regions that are failing at this step (drawn in the error colour).
    failed_regions: list[str] = Field(default_factory=list)
    # Whether ``health_score`` may be shown at all (see ScoreState).
    score_state: ScoreState = "fresh"
    # Minutes the cloud has gone without telemetry from the system (illustrative).
    minutes_without_data: int = Field(default=0, ge=0)
    # Telemetry collected on the system but not yet delivered (illustrative).
    backlog_points: int = Field(default=0, ge=0)


class PipelineResponse(CamelModel):
    trace: list[PipelineState]
    # Which trace this is: "healthy" (the default) or a failure scenario id.
    scenario: str = "healthy"


class ScenarioInfo(CamelModel):
    """One selectable trace. ``sources`` carries the research a failure
    scenario's behaviour is anchored to; the UI renders them."""

    id: str
    name: str
    summary: str
    # The pipeline page's opening paragraph and the counters panel's note while
    # this scenario plays. Backend data so they follow the reading level like
    # the step prose beside them.
    intro: str = ""
    note: str = ""
    # The counter the scenario exists for, as a PipelineState field name
    # (camelCase, as on the wire).
    hero_field: str
    phases: list[str]
    sources: list[SourceLink] = Field(default_factory=list)


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to AIOps; spell out
    # Dell/observability jargon (SCG, telemetry, health score, ...) on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "Included with ProSupport and above"
    # Platform regions this capability maps to (ids from anatomy.py).
    region_ids: list[str] = Field(default_factory=list)
    options: list[CatalogOption]


class UseCaseItem(CamelModel):
    category_id: str
    option_id: str
    qty: int
    rationale: str


class UseCase(CamelModel):
    id: str
    title: str
    summary: str
    narrative: list[str]  # paragraphs
    config: list[UseCaseItem]
    outcomes: list[Stat] = Field(default_factory=list)
