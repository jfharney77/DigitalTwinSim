"""FastAPI app: serves the Cyber Detect detection map, incident trace,
catalog, and use cases. All content is static data + a pure engine — no
state."""

from __future__ import annotations

from fastapi import HTTPException, Query

from twinkit.api import Level, make_app
from twinkit.tour import TourResponse

from .anatomy import ANATOMY
from .catalog import CATALOG
from .leveling import leveled, leveled_all
from .models import (
    CatalogCategory,
    DetectAnatomy,
    DetectResponse,
    ScenarioInfo,
    UseCase,
)
from .scenarios import BASELINE, SCENARIOS, simulate_scenario
from .tour import TOUR_RESPONSE
from .usecases import USE_CASES

app = make_app(
    title="Dell Cyber Detect Inside",
    frontend_port=5192,
)


@app.get("/api/anatomy", response_model=DetectAnatomy)
def get_anatomy(level: int = Level) -> DetectAnatomy:
    return leveled(ANATOMY, level)


@app.get("/api/detect", response_model=DetectResponse)
def get_detect(
    level: int = Level,
    scenario: str = Query(BASELINE),
) -> DetectResponse:
    # ?scenario= selects a failure trace; without it this is the original
    # incident, unchanged. GET /api/scenarios lists the ids.
    try:
        trace = simulate_scenario(scenario)
    except KeyError:
        raise HTTPException(404, f"unknown scenario {scenario!r}") from None
    return leveled(DetectResponse(trace=trace, scenario=scenario), level)


@app.get("/api/scenarios", response_model=list[ScenarioInfo])
def get_scenarios(level: int = Level) -> list[ScenarioInfo]:
    return leveled_all(SCENARIOS, level)


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog(level: int = Level) -> list[CatalogCategory]:
    return leveled_all(CATALOG, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)


@app.get("/api/tour", response_model=TourResponse)
def get_tour(level: int = Level) -> TourResponse:
    return leveled(TOUR_RESPONSE, level)
