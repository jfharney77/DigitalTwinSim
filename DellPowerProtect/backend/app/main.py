"""FastAPI app: serves the PowerProtect site map, data-lifecycle trace,
catalog, use cases, and narrated tour. All content is static data + a pure engine — no
state."""

from __future__ import annotations

from fastapi import HTTPException, Query

from twinkit.api import Level, make_app
from twinkit.tour import TourResponse

from .anatomy import ANATOMY
from .catalog import CATALOG
from .cleaning import DEFAULT_SCENARIO_ID, SCENARIO_ID, SCENARIOS, simulate_cleaning
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import (
    CatalogCategory,
    CleaningResponse,
    LifecycleResponse,
    ScenarioInfo,
    SiteAnatomy,
    UseCase,
)
from .tour import TOUR_RESPONSE
from .usecases import USE_CASES

app = make_app(
    title="PowerProtect + Cyber Recovery Inside",
    frontend_port=5183,
)


@app.get("/api/anatomy", response_model=SiteAnatomy)
def get_anatomy(level: int = Level) -> SiteAnatomy:
    return leveled(ANATOMY, level)


@app.get("/api/lifecycle", response_model=LifecycleResponse | CleaningResponse)
def get_lifecycle(
    level: int = Level,
    scenario: str = Query(DEFAULT_SCENARIO_ID),
) -> LifecycleResponse | CleaningResponse:
    """The trace. Without ``scenario`` (or with the default id) this is the
    happy path, byte-for-byte what it was before scenarios existed;
    ``?scenario=cleaning-gc`` serves the failure trace, whose states extend
    ``LifecycleState`` with a capacity ledger."""
    if scenario == DEFAULT_SCENARIO_ID:
        return leveled(LifecycleResponse(trace=simulate()), level)
    if scenario == SCENARIO_ID:
        return leveled(
            CleaningResponse(scenario=SCENARIO_ID, trace=simulate_cleaning()), level
        )
    raise HTTPException(status_code=404, detail=f"unknown scenario {scenario!r}")


@app.get("/api/scenarios", response_model=list[ScenarioInfo])
def get_scenarios(level: int = Level) -> list[ScenarioInfo]:
    """The traces ``/api/lifecycle`` can serve, with the failure's sources."""
    return leveled_all(SCENARIOS, level)


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog(level: int = Level) -> list[CatalogCategory]:
    return leveled_all(CATALOG, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)


@app.get("/api/tour", response_model=TourResponse)
def get_tour(level: int = Level) -> TourResponse:
    """The narrated tour: steps, the region-to-layer map, and the map bounds.

    Pure data built once at import (``app/tour.py``); the frontend player owns
    the clock."""
    return leveled(TOUR_RESPONSE, level)
