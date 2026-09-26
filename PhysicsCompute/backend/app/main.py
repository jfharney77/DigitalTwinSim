"""FastAPI app for the AI-compute physics simulator. The engine is
pure; this file is the only impure edge. ``POST /api/simulate`` takes a
Scenario and returns the deterministic trace; ``GET /api/simulate``
runs the default scenario; ``POST /api/redfish/thermal`` reshapes a
SimState as the mock iDRAC Redfish payload (spec 01 §5)."""

from __future__ import annotations

from fastapi import HTTPException, Query

from twinkit.api import Level, make_app
from twinkit.labs import Lab, LabResult

from .anatomy import MAPS
from .constants import CONSTANTS, PSU_CURVE_SOURCE, PSU_EFFICIENCY_CURVE
from .engine import simulate
from .labs import LABS, LABS_BY_ID, grade_scenario
from .media import MEDIA
from .leveling import leveled, leveled_all
from .models import (
    ConfigPreset,
    Explain,
    GuidedScenario,
    Intro,
    Scenario,
    SimResponse,
    SimState,
    SystemMap,
    WorkloadPreset,
)
from .presets import (
    CONFIG_PRESETS,
    EXPLAINS,
    GUIDED_SCENARIOS,
    INTRO,
    TRAINING,
    WORKLOAD_PRESETS,
    XE9680_H100,
)
from .redfish import to_redfish_thermal
from .validation import validate

app = make_app(
    title="AI-Compute Physics Simulator",
    frontend_port=5205,
)


@app.get("/api/anatomy", response_model=SystemMap)
def get_anatomy(product: str = Query("xe9680"), level: int = Level) -> SystemMap:
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
        "psuEfficiencyCurve": PSU_EFFICIENCY_CURVE,
        "psuCurveSource": PSU_CURVE_SOURCE,
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


class RedfishRequest(SimState):
    """The frontend posts the SimState at its playback cursor."""


@app.post("/api/redfish/thermal")
def post_redfish(state: RedfishRequest, product: str = Query("xe9680")) -> dict:
    return to_redfish_thermal(state, product)


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
    """Default scenario (XE9680 H100, fed training) — zero-click first
    paint and the GET liveness probe."""
    return _run(Scenario(config=XE9680_H100, workload=TRAINING))


# --- Graded labs (docs/LAB_PATTERN.md) --------------------------------------
# Reading-level resolution happens here and only here; app/labs.py is pure.
# The reference solutions and gaming attempts are never served.

@app.get("/api/labs", response_model=list[Lab])
def get_labs(level: int = Level) -> list[Lab]:
    return leveled_all(LABS, level)


@app.post("/api/labs/{lab_id}/grade", response_model=LabResult)
def post_lab_grade(lab_id: str, scenario: Scenario, level: int = Level) -> LabResult:
    if lab_id not in LABS_BY_ID:
        raise HTTPException(404, f"unknown lab {lab_id}")
    return leveled(grade_scenario(lab_id, scenario), level)
