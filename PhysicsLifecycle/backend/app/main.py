"""FastAPI app for the resilience simulator. The engine is pure; this
file is the only impure edge. the engine stays pure and the
"""

from __future__ import annotations

from fastapi import HTTPException, Query

from twinkit.api import Level, make_app

from .anatomy import MAPS
from .constants import CONSTANTS
from .engine import simulate
from .media import MEDIA
from .leveling import leveled, leveled_all
from .models import (
    ConfigPreset,
    Explain,
    GuidedScenario,
    LifecycleMap,
    Scenario,
    SimResponse,
)
from .presets import BLOCKS, CONFIG_PRESETS, EXPLAINS, GUIDED_SCENARIOS, ROLLOUT
from .validation import validate

app = make_app(
    title="Telecom & Sustainability Simulator",
    frontend_port=5211,
)


@app.get("/api/anatomy", response_model=LifecycleMap)
def get_anatomy(product: str = Query("telecomblocks"), level: int = Level) -> LifecycleMap:
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
    """Default: the Blocks rollout."""
    return _run(Scenario(config=BLOCKS, duration_d=120, events=ROLLOUT))


# --- Graded labs (docs/LAB_PATTERN.md) --------------------------------------
# app/labs.py is pure; this is its HTTP edge, and the only place lab prose is
# resolved to a reading level. Reference solutions never leave the server.

from twinkit.labs import Lab, LabResult  # noqa: E402

from .labs import LABS, LABS_BY_ID, grade_scenario  # noqa: E402


@app.get("/api/labs", response_model=list[Lab])
def get_labs(level: int = Level) -> list[Lab]:
    """The graded labs: goal, criteria, hints and start scenario."""
    return leveled_all(LABS, level)


@app.post("/api/labs/{lab_id}/grade", response_model=LabResult)
def post_lab_grade(lab_id: str, scenario: Scenario, level: int = Level) -> LabResult:
    if lab_id not in LABS_BY_ID:
        raise HTTPException(404, f"unknown lab {lab_id}")
    return leveled(grade_scenario(lab_id, scenario), level)
