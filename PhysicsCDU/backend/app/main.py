"""FastAPI app: serves the loop map, constants, presets, guided
scenarios, explain entries, and the simulator itself. The engine is
pure; this file is the only impure edge. ``POST /api/simulate`` takes a
Scenario and returns the deterministic trace; ``GET /api/simulate`` runs
the default scenario so a liveness check that expects a GET has
something to read."""

from __future__ import annotations

from fastapi import HTTPException

from twinkit.api import Level, make_app
from twinkit.labs import Lab, LabResult

from .anatomy import ANATOMY
from .constants import CONSTANTS
from .engine import simulate
from .labs import LABS, LABS_BY_ID, grade_scenario
from .leveling import leveled, leveled_all
from .models import (
    ConfigPreset,
    Explain,
    GuidedScenario,
    LoopMap,
    Scenario,
    SimResponse,
    WorkloadPreset,
)
from .presets import CONFIG_PRESETS, EXPLAINS, GUIDED_SCENARIOS, WORKLOAD_PRESETS
from .validation import validate

app = make_app(
    title="PowerCool CDU Physics Simulator",
    frontend_port=5216,
)


@app.get("/api/anatomy", response_model=LoopMap)
def get_anatomy(level: int = Level) -> LoopMap:
    return leveled(ANATOMY, level)


@app.get("/api/constants")
def get_constants() -> dict[str, object]:
    """The whole constants table, sources and all — so the UI can badge
    estimate-derived readouts and there is no second copy of any value."""
    return {
        "constants": {
            k: v.model_dump(by_alias=True) for k, v in CONSTANTS.items()
        },
    }


@app.get("/api/presets/configs", response_model=list[ConfigPreset])
def get_config_presets() -> list[ConfigPreset]:
    return CONFIG_PRESETS


@app.get("/api/presets/workloads", response_model=list[WorkloadPreset])
def get_workload_presets() -> list[WorkloadPreset]:
    return WORKLOAD_PRESETS


@app.get("/api/scenarios", response_model=list[GuidedScenario])
def get_scenarios(level: int = Level) -> list[GuidedScenario]:
    return leveled_all(GUIDED_SCENARIOS, level)


@app.get("/api/explain", response_model=list[Explain])
def get_explain(level: int = Level) -> list[Explain]:
    return leveled_all(EXPLAINS, level)


def _run(scenario: Scenario, level: int = 3) -> SimResponse:
    trace, log, summary = simulate(scenario)
    return SimResponse(
        # Rule messages carry reading levels; the trace is numbers.
        validations=leveled_all(validate(scenario), level),
        trace=trace,
        log=log,
        summary=summary,
    )


@app.post("/api/simulate", response_model=SimResponse)
def post_simulate(scenario: Scenario, level: int = Level) -> SimResponse:
    return _run(scenario, level)


@app.get("/api/simulate", response_model=SimResponse)
def get_simulate(level: int = Level) -> SimResponse:
    """The default scenario (Standard build, full-tilt workload) — for
    liveness checks and a zero-click first paint."""
    from .presets import FULL_TILT, STANDARD

    return _run(Scenario(config=STANDARD, workload=FULL_TILT), level)


# --- Graded labs (docs/LAB_PATTERN.md) ---------------------------------------

@app.get("/api/labs", response_model=list[Lab])
def get_labs(level: int = Level) -> list[Lab]:
    """The labs — goals, criteria, hints, start scenarios. Reference
    solutions stay server-side."""
    return leveled_all(LABS, level)


@app.post("/api/labs/{lab_id}/grade", response_model=LabResult)
def post_lab_grade(lab_id: str, scenario: Scenario, level: int = Level) -> LabResult:
    if lab_id not in LABS_BY_ID:
        raise HTTPException(status_code=404, detail=f"no lab {lab_id!r}")
    return leveled(grade_scenario(lab_id, scenario), level)
