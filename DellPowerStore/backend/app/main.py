"""FastAPI app: serves the PowerStore chassis anatomy, power-on trace,
catalog, use cases, and narrated tour. All content is static data + a pure engine — no
state."""

from __future__ import annotations

from fastapi import HTTPException

from twinkit.api import Level, make_app
from twinkit.tour import TourResponse

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .failover import POWER_ON, SCENARIO, SCENARIO_ID, SCENARIOS, simulate_node_loss
from .leveling import leveled, leveled_all
from .models import (
    CatalogCategory,
    ChassisAnatomy,
    FailoverResponse,
    PowerOnResponse,
    ScenarioInfo,
    UseCase,
)
from .tour import TOUR_RESPONSE
from .usecases import USE_CASES

app = make_app(
    title="PowerStore Inside",
    frontend_port=5175,
)


@app.get("/api/anatomy", response_model=ChassisAnatomy)
def get_anatomy(level: int = Level) -> ChassisAnatomy:
    return leveled(ANATOMY, level)


@app.get("/api/poweron", response_model=PowerOnResponse | FailoverResponse)
def get_poweron(
    level: int = Level, scenario: str = POWER_ON.id
) -> PowerOnResponse | FailoverResponse:
    """The trace. With no ``scenario`` (or ``power-on``) this is the power-on
    sequence exactly as before; ``?scenario=node-loss-failover`` serves the
    failure trace, whose states carry the extra failure fields."""
    if scenario == POWER_ON.id:
        return leveled(PowerOnResponse(trace=simulate()), level)
    if scenario == SCENARIO_ID:
        return leveled(
            FailoverResponse(scenario=SCENARIO, trace=simulate_node_loss()), level
        )
    raise HTTPException(
        status_code=404,
        detail=f"unknown scenario {scenario!r}; see /api/scenarios",
    )


@app.get("/api/scenarios", response_model=list[ScenarioInfo])
def get_scenarios(level: int = Level) -> list[ScenarioInfo]:
    """The traces this twin can play: the power-on sequence and its failures."""
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
    the clock and drives the power-on trace cursor from it."""
    return leveled(TOUR_RESPONSE, level)
