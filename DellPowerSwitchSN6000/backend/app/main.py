"""FastAPI app: serves the SN6000 fabric map, fabric trace, catalog, and
use cases, and narrated tour. All content is static data + a pure engine — no state."""

from __future__ import annotations

from fastapi import HTTPException, Query

from twinkit.api import Level, make_app
from twinkit.tour import TourResponse

from .anatomy import ANATOMY
from .catalog import CATALOG
from .leveling import leveled, leveled_all
from .models import (
    CatalogCategory,
    FabricAnatomy,
    FabricResponse,
    Scenario,
    UseCase,
)
from .scenarios import HEALTHY, SCENARIOS, TRACES
from .tour import TOUR_RESPONSE
from .usecases import USE_CASES

app = make_app(
    title="PowerSwitch SN6000 Inside",
    frontend_port=5185,
)


@app.get("/api/anatomy", response_model=FabricAnatomy)
def get_anatomy(level: int = Level) -> FabricAnatomy:
    return leveled(ANATOMY, level)


@app.get("/api/fabric", response_model=FabricResponse)
def get_fabric(
    level: int = Level,
    scenario: str = Query(HEALTHY, description="A scenario id from /api/scenarios"),
) -> FabricResponse:
    """The fabric trace. Without ``?scenario=`` this is the healthy bring-up,
    exactly as before; ``?scenario=gray-link`` is the failure trace."""
    produce = TRACES.get(scenario)
    if produce is None:
        raise HTTPException(
            status_code=404,
            detail=f"unknown scenario {scenario!r}; see /api/scenarios",
        )
    return leveled(FabricResponse(trace=produce(), scenario=scenario), level)


@app.get("/api/scenarios", response_model=list[Scenario])
def get_scenarios(level: int = Level) -> list[Scenario]:
    """The selectable traces, healthy first, each failure with its sources."""
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
