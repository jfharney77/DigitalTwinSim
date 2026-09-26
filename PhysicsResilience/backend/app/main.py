"""FastAPI app for the resilience simulator. The engine is pure; this
file is the only impure edge. ``GET /api/scope`` serves the hard scope
boundary so the UI can keep it in the footer."""

from __future__ import annotations

from fastapi import HTTPException, Query

from twinkit.api import Level, make_app
from twinkit.labs import Lab, LabResult

from .anatomy import MAPS
from .constants import CONSTANTS
from .engine import simulate
from .labs import LABS, LABS_BY_ID, grade_scenario
from .media import MEDIA
from .leveling import leveled, leveled_all
from .models import (
    SCOPE_NOTE,
    ConfigPreset,
    Explain,
    GuidedScenario,
    ResilienceMap,
    Scenario,
    SimResponse,
)
from .presets import CONFIG_PRESETS, EXPLAINS, GUIDED_SCENARIOS, VAULTED
from .validation import validate

app = make_app(
    title="Security & Resilience Simulator",
    frontend_port=5209,
)


@app.get("/api/scope")
def get_scope() -> dict[str, str]:
    return {"scope": SCOPE_NOTE}


@app.get("/api/anatomy", response_model=ResilienceMap)
def get_anatomy(product: str = Query("powerprotect"), level: int = Level) -> ResilienceMap:
    if product not in MAPS:
        raise HTTPException(404, f"unknown product {product}")
    return leveled(MAPS[product], level)


@app.get("/api/media")
def get_media() -> dict[str, object]:
    """V1/V9 product media — photos/facsimiles with mandatory credits."""
    return {k: v.model_dump(by_alias=True) for k, v in MEDIA.items()}


@app.get("/api/constants")
def get_constants() -> dict[str, object]:
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
    """Default: the vaulted estate with the canonical incident script."""
    from .models import SimEvent

    return _run(Scenario(
        config=VAULTED, duration_h=720,
        events=[
            SimEvent(at_h=240, action="incident", value=500),
            SimEvent(at_h=280, action="contain"),
            SimEvent(at_h=290, action="attempt-restore"),
        ],
    ))


# --- Graded labs (docs/LAB_PATTERN.md) --------------------------------------
# The reference solutions and gaming attempts in labs.py are never served.

@app.get("/api/labs", response_model=list[Lab])
def get_labs(level: int = Level) -> list[Lab]:
    return leveled_all(LABS, level)


@app.post("/api/labs/{lab_id}/grade", response_model=LabResult)
def post_lab_grade(lab_id: str, scenario: Scenario, level: int = Level) -> LabResult:
    if lab_id not in LABS_BY_ID:
        raise HTTPException(404, f"unknown lab {lab_id}")
    return leveled(grade_scenario(lab_id, scenario), level)
