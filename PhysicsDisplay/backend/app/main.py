"""FastAPI app for the UltraSharp display simulator — the only impure
edge. ``POST /api/simulate`` takes a Scenario; GET runs the default so the
CustomerSetup liveness enrichment has something to read."""

from __future__ import annotations

from twinkit.api import Level, make_app

from .anatomy import ANATOMY
from .constants import CONSTANTS
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import (
    Explain,
    GuidedScenario,
    ModelPreset,
    PanelMap,
    Scenario,
    SimResponse,
)
from .presets import EXPLAINS, GUIDED_SCENARIOS, MODEL_PRESETS
from .validation import validate

app = make_app(
    title="UltraSharp Display Physics Simulator",
    frontend_port=5218,
)


@app.get("/api/anatomy", response_model=PanelMap)
def get_anatomy(level: int = Level) -> PanelMap:
    return leveled(ANATOMY, level)


@app.get("/api/constants")
def get_constants() -> dict[str, object]:
    return {
        "constants": {
            k: v.model_dump(by_alias=True) for k, v in CONSTANTS.items()
        },
    }


@app.get("/api/presets/models", response_model=list[ModelPreset])
def get_model_presets() -> list[ModelPreset]:
    return MODEL_PRESETS


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
    """Default scenario — the mini-LED panel on mixed content."""
    from .presets import MINILED

    return _run(Scenario(config=MINILED))


# Graded labs (docs/LAB_PATTERN.md). app/labs.py is pure; this is its HTTP edge.
from fastapi import HTTPException  # noqa: E402
from twinkit.labs import Lab, LabResult  # noqa: E402

from .labs import LABS, LABS_BY_ID, grade_scenario  # noqa: E402


@app.get("/api/labs", response_model=list[Lab])
def get_labs(level: int = Level) -> list[Lab]:
    """The graded labs: goal, criteria, hints and start scenario. Reference
    solutions stay server-side."""
    return leveled_all(LABS, level)


@app.post("/api/labs/{lab_id}/grade", response_model=LabResult)
def post_lab_grade(lab_id: str, scenario: Scenario, level: int = Level) -> LabResult:
    """Run the learner's scenario through the engine and grade the trace.
    Stateless and deterministic; the prose in the result is leveled."""
    if lab_id not in LABS_BY_ID:
        raise HTTPException(status_code=404, detail=f"unknown lab {lab_id!r}")
    return leveled(grade_scenario(lab_id, scenario), level)
