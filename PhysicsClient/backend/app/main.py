"""FastAPI app for the client-device physics simulator: serves the
device maps, constants, presets, guided scenarios, explain entries, and
the simulator itself. The engine is pure; this file is the only impure
edge. ``POST /api/simulate`` takes a Scenario and returns the
deterministic trace; ``GET /api/simulate`` runs the default scenario."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .anatomy import MAPS, map_for
from .brandmap import BRAND_MAP
from .constants import CONSTANTS, PSU_CURVE_SOURCE, PSU_EFFICIENCY_CURVE
from .engine import simulate
from .media import MEDIA
from .leveling import DEFAULT_LEVEL, LEVEL_NAMES, leveled, leveled_all
from .models import (
    BrandMap,
    ConfigPreset,
    DeviceMap,
    Explain,
    GuidedScenario,
    Scenario,
    SimResponse,
    WorkloadPreset,
)
from .presets import AAA, AW_LAPTOP, CONFIG_PRESETS, EXPLAINS, GUIDED_SCENARIOS, WORKLOAD_PRESETS
from .validation import validate

app = FastAPI(title="Client-Device Physics Simulator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5204",
        "http://127.0.0.1:5204",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

Level = Query(
    DEFAULT_LEVEL,
    ge=1,
    le=5,
    description="Reading level: 1 newcomer, 3 standard, 5 specialist.",
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/levels")
def get_levels() -> dict[str, object]:
    return {
        "default": DEFAULT_LEVEL,
        "levels": [
            {"level": level, "name": name}
            for level, name in LEVEL_NAMES.items()
        ],
    }


@app.get("/api/anatomy", response_model=DeviceMap)
def get_anatomy(
    product: str = Query("alienware"),
    form_factor: str = Query("laptop", alias="formFactor"),
    level: int = Level,
) -> DeviceMap:
    return leveled(map_for(product, form_factor), level)


@app.get("/api/anatomy/{map_id}", response_model=DeviceMap)
def get_anatomy_by_id(map_id: str, level: int = Level) -> DeviceMap:
    if map_id not in MAPS:
        raise HTTPException(404, f"unknown map {map_id}")
    return leveled(MAPS[map_id], level)


@app.get("/api/brandmap", response_model=BrandMap)
def get_brandmap(level: int = Level) -> BrandMap:
    """The 2025 client-brand map (physics_specs/10 §8) — the naming
    scheme this app's two products live inside."""
    return leveled(BRAND_MAP, level)


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
    """Default scenario (Alienware laptop, AAA load) — zero-click first
    paint and the CustomerSetup-style GET liveness probe."""
    return _run(Scenario(config=AW_LAPTOP, workload=AAA))
