"""FastAPI app: serves the iDRAC9 subsystem map, bring-up trace, capability
catalog, management use cases, and narrated tour. All content is static data + a pure engine
— no state."""

from __future__ import annotations

from fastapi import HTTPException, Query

from twinkit.api import Level, make_app
from twinkit.tour import TourResponse

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate_scenario
from .leveling import leveled, leveled_all
from .models import (
    BringUpResponse,
    CatalogCategory,
    ScenarioInfo,
    SubsystemMap,
    UseCase,
)
from .scenarios import DEFAULT_SCENARIO, SCENARIOS
from .tour import TOUR_RESPONSE
from .usecases import USE_CASES

app = make_app(
    title="iDRAC9 Inside",
    frontend_port=5177,
)


@app.get("/api/anatomy", response_model=SubsystemMap)
def get_anatomy(level: int = Level) -> SubsystemMap:
    return leveled(ANATOMY, level)


# The failure-scenario fields on BringUpState default to None and the
# bring-up trace never sets them; dropping None keeps the happy path's wire
# format exactly what it was before scenarios existed.
# (One line on purpose: scripts/gen_components.py finds the trace route by
# scanning for the decorator and its response model on the same line.)
@app.get("/api/bringup", response_model=BringUpResponse, response_model_exclude_none=True)  # noqa: E501
def get_bringup(
    level: int = Level,
    scenario: str = Query(DEFAULT_SCENARIO),
) -> dict:
    """The trace. ``?scenario=firmware-update-rollback`` serves the failure
    scenario; without it this is the bring-up, as it always was."""
    try:
        trace = simulate_scenario(scenario)
    except KeyError:
        raise HTTPException(404, f"unknown scenario {scenario!r}") from None
    # Returned as the already-dumped dict (None fields dropped) so the static
    # snapshot builder, which calls this function directly, writes exactly what
    # FastAPI's response_model_exclude_none path serves. See docs/STATIC_HOSTING.md.
    return leveled(BringUpResponse(trace=trace), level).model_dump(
        mode="json", by_alias=True, exclude_none=True
    )


@app.get("/api/scenarios", response_model=list[ScenarioInfo])
def get_scenarios(level: int = Level) -> list[ScenarioInfo]:
    """The traces this twin can play, with each one's sources."""
    return leveled_all(SCENARIOS, level)


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog(level: int = Level) -> list[CatalogCategory]:
    return leveled_all(CATALOG, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)


@app.get("/api/tour", response_model=TourResponse)
def get_tour(level: int = Level) -> TourResponse:
    """The narrated tour: steps, the block-to-layer map, and the map bounds.

    Pure data built once at import (``app/tour.py``); the frontend player owns
    the clock."""
    return leveled(TOUR_RESPONSE, level)
