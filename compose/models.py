"""What a coupled run returns. Plain data, camelCase on the wire."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from twinkit.models import CamelModel


class SeamResult(CamelModel):
    """One identity asserted across one seam."""

    coupling: str
    identity: str                 # human-readable equation
    lhs: float
    rhs: float
    unit: str
    abs_error: float
    tolerance: float
    holds: bool
    worst_tick: int | None = None
    note: str = ""
    # Timeline keys the page reads for the live `lhs = rhs` readout.
    lhs_key: str | None = None
    rhs_key: str | None = None


class Stage(CamelModel):
    """One engine run."""

    id: str                       # unique within the trace, e.g. "PhysicsCompute/coupled"
    component: str
    label: str
    time_unit: Literal["s", "h", "d"]
    scenario: dict                # the scenario actually run, including injected events
    injected_events: list[dict] = Field(default_factory=list)
    injected_config: dict = Field(default_factory=dict)
    trace: list[dict]
    summary: dict
    validations: list[dict] = Field(default_factory=list)
    log: list[dict] = Field(default_factory=list)


class JoinedTick(CamelModel):
    t: float
    values: dict[str, float | None]


class ChartSeries(CamelModel):
    key: str                      # a key of JoinedTick.values
    label: str
    role: Literal["source", "target", "context"]


class Chart(CamelModel):
    title: str
    unit: str
    seam: bool = False            # True: this chart shows the quantity the seam carries
    series: list[ChartSeries]


Cause = Literal[
    "stall_power", "hourly_rounding", "cap_vs_shed", "checkpoint_burst",
    # Added while building: two gaps the design's list could not name.
    "gpu_tier_vs_detailed", "gray_fabric",
]


class Divergence(CamelModel):
    """Where fed and aggregate modes disagree beyond tolerance, and why."""

    instrument: str
    aggregate: float
    fed: float
    tolerance: float
    cause: Cause | None = None    # None = unexplained; the agreement test fails on it
    explanation: str = ""


class IterationRecord(CamelModel):
    index: int
    loop_value: float             # the loop variable after this iteration
    residual: float               # relative change from the previous iteration
    note: str = ""
    series: dict[str, list[float]] = Field(default_factory=dict)


class CoupledTrace(CamelModel):
    chain_id: str
    title: str = ""
    time_unit: Literal["s", "h", "d"] = "s"
    stages: list[Stage]
    seams: list[SeamResult]
    iterations: int = 1
    converged: bool = True
    residual_history: list[float] = Field(default_factory=list)
    iteration_log: list[IterationRecord] = Field(default_factory=list)
    timeline: list[JoinedTick] = Field(default_factory=list)
    charts: list[Chart] = Field(default_factory=list)
    divergences: list[Divergence] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    illustrative: bool = True
    estimated_constants: list[str] = Field(default_factory=list)
