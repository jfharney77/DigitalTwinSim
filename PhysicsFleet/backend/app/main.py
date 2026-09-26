"""FastAPI app for the network-fabrics simulator. The engine is pure;
this file is the only impure edge."""

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
    FleetMap,
    GuidedScenario,
    Intro,
    Scenario,
    SimResponse,
    WorkloadPreset,
)
from .presets import (
    STEADY_WL,
    CONFIG_PRESETS,
    EXPLAINS,
    GUIDED_SCENARIOS,
    INTRO,
    VXRAIL_8,
    WORKLOAD_PRESETS,
)
from .validation import validate
from .labs import LABS, LABS_BY_ID, grade_scenario
from twinkit.labs import Lab, LabResult

app = make_app(
    title="Fleet-Operations Physics Simulator",
    frontend_port=5208,
)


@app.get("/api/anatomy", response_model=FleetMap)
def get_anatomy(product: str = Query("vxrail"), level: int = Level) -> FleetMap:
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


@app.get("/api/presets/workloads", response_model=list[WorkloadPreset])
def get_workload_presets() -> list[WorkloadPreset]:
    return WORKLOAD_PRESETS


@app.get("/api/scenarios", response_model=list[GuidedScenario])
def get_scenarios(level: int = Level) -> list[GuidedScenario]:
    return leveled_all(GUIDED_SCENARIOS, level)


@app.get("/api/intro", response_model=Intro)
def get_intro(level: int = Level) -> Intro:
    return leveled(INTRO, level)


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
    """Default scenario (VxRail, steady estate) — GET liveness."""
    return _run(Scenario(config=VXRAIL_8, workload=STEADY_WL))


# --- Graded labs (docs/LAB_PATTERN.md) --------------------------------------

@app.get("/api/labs", response_model=list[Lab])
def get_labs(level: int = Level) -> list[Lab]:
    return leveled_all(LABS, level)


@app.post("/api/labs/{lab_id}/grade", response_model=LabResult)
def post_lab_grade(lab_id: str, scenario: Scenario, level: int = Level) -> LabResult:
    if lab_id not in LABS_BY_ID:
        raise HTTPException(404, f"unknown lab {lab_id}")
    return leveled(grade_scenario(lab_id, scenario), level)
