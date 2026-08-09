"""FastAPI app: serves the factory map, constants, presets, guided
scenarios, explain entries, and the simulator itself. The engine is pure;
this file is the only impure edge. ``POST /api/simulate`` takes a Scenario
and returns the deterministic trace; ``GET /api/simulate`` runs the
default scenario so the CustomerSetup liveness enrichment — which expects
a GET — has something to read."""

from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .anatomy import ANATOMY
from .constants import CONSTANTS
from .engine import simulate
from .leveling import DEFAULT_LEVEL, LEVEL_NAMES, leveled, leveled_all
from .models import (
    Explain,
    FactoryMap,
    FactoryPreset,
    GuidedScenario,
    JobPreset,
    Scenario,
    SimResponse,
)
from .presets import EXPLAINS, FACTORY_PRESETS, GUIDED_SCENARIOS, JOB_PRESETS
from .validation import validate

app = FastAPI(title="Dell AI Factory — capstone simulator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5219",
        "http://127.0.0.1:5219",
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


@app.get("/api/anatomy", response_model=FactoryMap)
def get_anatomy(level: int = Level) -> FactoryMap:
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


@app.get("/api/presets/configs", response_model=list[FactoryPreset])
def get_factory_presets() -> list[FactoryPreset]:
    return FACTORY_PRESETS


@app.get("/api/presets/jobs", response_model=list[JobPreset])
def get_job_presets() -> list[JobPreset]:
    return JOB_PRESETS


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
    """The default scenario (the balanced AI factory, frontier-LLM job)."""
    from .presets import FACTORY, FRONTIER_LLM

    return _run(Scenario(config=FACTORY, job=FRONTIER_LLM, duration_h=480))
