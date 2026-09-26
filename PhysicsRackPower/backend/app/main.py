"""FastAPI app: serves the rack map, constants, presets, guided
scenarios, explain entries, and the simulator itself. The engine is pure;
this file is the only impure edge. ``POST /api/simulate`` takes a Scenario
and returns the deterministic trace; ``GET /api/simulate`` runs the
default scenario so a liveness check that expects a GET has something to
read."""

from __future__ import annotations

from twinkit.api import Level, make_app

from .anatomy import ANATOMY
from .constants import CONSTANTS
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import (
    ConfigPreset,
    Explain,
    GuidedScenario,
    RackMap,
    Scenario,
    SimResponse,
)
from .presets import CONFIG_PRESETS, EXPLAINS, GUIDED_SCENARIOS
from .validation import validate

app = make_app(
    title="Rack PDU & UPS Physics Simulator",
    frontend_port=5217,
)


@app.get("/api/anatomy", response_model=RackMap)
def get_anatomy(level: int = Level) -> RackMap:
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


@app.get("/api/scenarios", response_model=list[GuidedScenario])
def get_scenarios(level: int = Level) -> list[GuidedScenario]:
    return leveled_all(GUIDED_SCENARIOS, level)


@app.get("/api/explain", response_model=list[Explain])
def get_explain(level: int = Level) -> list[Explain]:
    return leveled_all(EXPLAINS, level)


def _run(scenario: Scenario) -> SimResponse:
    trace, log, summary = simulate(scenario)
    return SimResponse(
        validations=validate(scenario),
        trace=trace,
        log=log,
        summary=summary,
    )


@app.post("/api/simulate", response_model=SimResponse)
def post_simulate(scenario: Scenario) -> SimResponse:
    return _run(scenario)


@app.get("/api/simulate", response_model=SimResponse)
def get_simulate() -> SimResponse:
    """The default scenario (Balanced rack, a utility failure mid-run) —
    for liveness checks and a zero-click first paint."""
    from .models import SimEvent
    from .presets import BALANCED

    return _run(Scenario(
        config=BALANCED,
        events=[SimEvent(at_s=180, action="utility-fail")],
    ))


# --- Graded labs (docs/LAB_PATTERN.md) -----------------------------------------
# app/labs.py is pure; this is its HTTP edge, and the only place lab prose is
# resolved to a reading level. The static build runs these same two routes
# under Pyodide, so grading works with no backend.
from fastapi import HTTPException  # noqa: E402
from twinkit.labs import Lab, LabResult  # noqa: E402

from .labs import LABS, LABS_BY_ID, grade_scenario  # noqa: E402


@app.get("/api/labs", response_model=list[Lab])
def get_labs(level: int = Level) -> list[Lab]:
    """The graded labs: goal, criteria, hints and start scenario. Reference
    solutions and the gaming attempts stay server-side."""
    return leveled_all(LABS, level)


@app.post("/api/labs/{lab_id}/grade", response_model=LabResult)
def post_lab_grade(lab_id: str, scenario: Scenario, level: int = Level) -> LabResult:
    """Run the learner's scenario through the pure engine and grade the trace."""
    if lab_id not in LABS_BY_ID:
        raise HTTPException(status_code=404, detail=f"unknown lab {lab_id!r}")
    return leveled(grade_scenario(lab_id, scenario), level)
