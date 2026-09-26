"""FastAPI app: serves the XE9712 rack anatomy, power-on trace, catalog,
use cases, and narrated tour. All content is static data + a pure engine — no state."""

from __future__ import annotations

from fastapi import HTTPException

from twinkit.api import Level, make_app
from twinkit.tour import TourResponse

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import SCENARIOS, simulate
from .leveling import leveled, leveled_all
from .models import (
    CatalogCategory,
    PowerOnResponse,
    RackAnatomy,
    ScenarioInfo,
    UseCase,
)
from .tour import TOUR_RESPONSE
from .usecases import USE_CASES

app = make_app(
    title="PowerEdge XE9712 Inside",
    frontend_port=5181,
)


@app.get("/api/anatomy", response_model=RackAnatomy)
def get_anatomy(level: int = Level) -> RackAnatomy:
    return leveled(ANATOMY, level)


@app.get("/api/poweron", response_model=PowerOnResponse)
def get_poweron(level: int = Level, scenario: str = "nominal") -> PowerOnResponse:
    """The power-on trace. ``?scenario=coolant-fault`` serves the failure
    trace; with no parameter this is the nominal bring-up, as before."""
    if scenario not in {s.id for s in SCENARIOS}:
        raise HTTPException(status_code=404, detail=f"unknown scenario {scenario!r}")
    return leveled(
        PowerOnResponse(trace=simulate(scenario), scenario=scenario), level
    )


@app.get("/api/scenarios", response_model=list[ScenarioInfo])
def get_scenarios(level: int = Level) -> list[ScenarioInfo]:
    """The selectable traces, with the sources each failure is modelled on."""
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
