"""FastAPI app: serves the NativeEdge platform map, onboarding trace,
catalog, and use cases. All content is static data + a pure engine — no
state."""

from __future__ import annotations

from fastapi import HTTPException

from twinkit.api import Level, make_app
from twinkit.tour import TourResponse

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import (
    CatalogCategory,
    OnboardResponse,
    PlatformMap,
    ScenarioInfo,
    ScenarioResponse,
    UseCase,
)
from .scenarios import SCENARIOS, scenario_info, simulate_scenario
from .tour import TOUR_RESPONSE
from .usecases import USE_CASES

app = make_app(
    title="Dell NativeEdge Inside",
    frontend_port=5187,
)


@app.get("/api/anatomy", response_model=PlatformMap)
def get_anatomy(level: int = Level) -> PlatformMap:
    return leveled(ANATOMY, level)


@app.get("/api/onboard", response_model=OnboardResponse | ScenarioResponse)
def get_onboard(
    level: int = Level, scenario: str | None = None
) -> OnboardResponse | ScenarioResponse:
    """The onboarding trace. Without ``scenario`` (or with the happy path's
    id) this is the zero-touch trace, byte-identical to what it always was;
    ``?scenario=attestation-fails`` serves the failure trace from
    ``app/scenarios.py`` in the additive ``ScenarioResponse`` shape."""
    if scenario is None or scenario == SCENARIOS[0].id:
        return leveled(OnboardResponse(trace=simulate()), level)
    trace = simulate_scenario(scenario)
    info = scenario_info(scenario)
    if trace is None or info is None:
        raise HTTPException(
            status_code=404,
            detail=f"unknown scenario {scenario!r}; see /api/scenarios",
        )
    return leveled(ScenarioResponse(scenario=info, trace=trace), level)


@app.get("/api/scenarios", response_model=list[ScenarioInfo])
def get_scenarios(level: int = Level) -> list[ScenarioInfo]:
    """The selectable traces, the happy path first."""
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
