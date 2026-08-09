"""FastAPI app: serves the pipeline map, constants, appliance table,
presets, guided scenarios, explain entries, and the simulator itself. The
engine is pure; this file is the only impure edge. ``POST /api/simulate``
takes a Scenario and returns the deterministic trace; ``GET /api/simulate``
runs the default scenario so a zero-click first paint (and any liveness
enrichment) has something to read."""

from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .anatomy import ANATOMY
from .constants import APPLIANCES, CONSTANTS
from .engine import simulate
from .leveling import DEFAULT_LEVEL, LEVEL_NAMES, leveled, leveled_all
from .models import (
    Appliance,
    DatasetPreset,
    Explain,
    GuidedScenario,
    PipelineMap,
    Scenario,
    SimResponse,
)
from .presets import DATASET_PRESETS, EXPLAINS, GUIDED_SCENARIOS
from .validation import validate

app = FastAPI(title="Data Domain Dedupe Physics Simulator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5215",
        "http://127.0.0.1:5215",
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


@app.get("/api/anatomy", response_model=PipelineMap)
def get_anatomy(level: int = Level) -> PipelineMap:
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


@app.get("/api/appliances", response_model=list[Appliance])
def get_appliances() -> list[Appliance]:
    return list(APPLIANCES.values())


@app.get("/api/presets/datasets", response_model=list[DatasetPreset])
def get_dataset_presets() -> list[DatasetPreset]:
    return DATASET_PRESETS


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
    """The default scenario (thirty fulls on the DD9910) — a zero-click
    first paint that happens to be the product's founding demo."""
    from .presets import THIRTY_FULLS

    return _run(THIRTY_FULLS)
