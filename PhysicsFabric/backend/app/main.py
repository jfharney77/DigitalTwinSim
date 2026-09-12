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
    FabricMap,
    GuidedScenario,
    Scenario,
    SimResponse,
    WorkloadPreset,
)
from .presets import (
    ALLREDUCE,
    CONFIG_PRESETS,
    EXPLAINS,
    GUIDED_SCENARIOS,
    SN6000_ADAPTIVE,
    WORKLOAD_PRESETS,
)
from .validation import validate

app = make_app(
    title="Network-Fabrics Physics Simulator",
    frontend_port=5207,
)


@app.get("/api/anatomy", response_model=FabricMap)
def get_anatomy(product: str = Query("sn6000"), level: int = Level) -> FabricMap:
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
    """Default scenario (SN6000 adaptive, all-reduce) — GET liveness."""
    return _run(Scenario(config=SN6000_ADAPTIVE, workload=ALLREDUCE))
