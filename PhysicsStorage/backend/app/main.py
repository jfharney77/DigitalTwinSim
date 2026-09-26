"""FastAPI app for the storage-platforms simulator. The engine is pure;
this file is the only impure edge."""

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
    ConfigPreset,
    Explain,
    GuidedScenario,
    ProductMap,
    Scenario,
    SimResponse,
    WorkloadPreset,
)
from .presets import (
    CONFIG_PRESETS,
    EXPLAINS,
    GUIDED_SCENARIOS,
    OLTP,
    POWERSTORE_2,
    WORKLOAD_PRESETS,
)
from .validation import validate

app = make_app(
    title="Storage-Platforms Physics Simulator",
    frontend_port=5206,
)


@app.get("/api/anatomy", response_model=ProductMap)
def get_anatomy(product: str = Query("powerstore"), level: int = Level) -> ProductMap:
    if product not in MAPS:
        raise HTTPException(404, f"unknown product {product}")
    return leveled(MAPS[product], level)


@app.get("/api/media")
def get_media(level: int = Level) -> dict[str, object]:
    """V1/V9 product media — photos/facsimiles with mandatory credits.
    Captions (the V10 x-ray text) are leveled like all teaching prose."""
    return {k: leveled(v, level).model_dump(by_alias=True) for k, v in MEDIA.items()}


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
    """Default scenario (PowerStore, OLTP) — the GET liveness probe."""
    return _run(Scenario(config=POWERSTORE_2, workload=OLTP))


# --- Graded labs (docs/LAB_PATTERN.md) --------------------------------------

@app.get("/api/labs", response_model=list[Lab])
def get_labs(level: int = Level) -> list[Lab]:
    """The labs only — reference solutions never leave the server."""
    return leveled_all(LABS, level)


@app.post("/api/labs/{lab_id}/grade", response_model=LabResult)
def post_lab_grade(lab_id: str, scenario: Scenario, level: int = Level) -> LabResult:
    if lab_id not in LABS_BY_ID:
        raise HTTPException(404, f"unknown lab {lab_id}")
    return leveled(grade_scenario(lab_id, scenario), level)
