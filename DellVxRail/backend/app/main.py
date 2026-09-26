"""FastAPI app: serves the VxRail cluster anatomy, first-run trace, catalog,
and use cases. All content is static data + a pure engine — no state."""

from __future__ import annotations

from fastapi import HTTPException, Query

from twinkit.api import Level, make_app
from twinkit.tour import TourResponse

from .anatomy import ANATOMIES
from .catalog import CATALOG
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import (
    CatalogCategory,
    ClusterAnatomy,
    FirstRunResponse,
    Scenario,
    UseCase,
)
from .nodeadd import SCENARIOS, simulate_node_add
from .tour import TOUR_RESPONSE
from .usecases import USE_CASES

app = make_app(
    title="VxRail Inside",
    frontend_port=5179,
)


# Scenario id -> the pure function that produces its trace. ``first-run`` is
# the default, so every existing caller of /api/firstrun and /api/anatomy
# gets exactly what it got before scenarios existed.
DEFAULT_SCENARIO = "first-run"
TRACES = {
    DEFAULT_SCENARIO: simulate,
    "node-add-mismatch": simulate_node_add,
}

ScenarioParam = Query(
    DEFAULT_SCENARIO,
    description="Which trace: first-run (default) or node-add-mismatch.",
)


def _known(scenario: str) -> str:
    if scenario not in TRACES:
        raise HTTPException(
            status_code=404,
            detail=f"unknown scenario {scenario!r}; see /api/scenarios",
        )
    return scenario


@app.get("/api/anatomy", response_model=ClusterAnatomy)
def get_anatomy(level: int = Level, scenario: str = ScenarioParam) -> ClusterAnatomy:
    # The node-add scenario is drawn on a taller copy of the map with a fifth
    # node; the default is the four-node map, unchanged.
    return leveled(ANATOMIES[_known(scenario)], level)


# exclude_none keeps the first-run response byte-identical: the scenario-only
# fields on FirstRunState are None there and never reach the wire.
# (One line on purpose: scripts/gen_components.py finds the trace route by
# scanning for `@app.get("/api/...", response_model=...Response`.)
@app.get("/api/firstrun", response_model=FirstRunResponse, response_model_exclude_none=True)
def get_firstrun(level: int = Level, scenario: str = ScenarioParam) -> dict:
    # Returned as the already-dumped dict (None fields dropped) so the static
    # snapshot builder, which calls this function directly, writes exactly what
    # FastAPI's response_model_exclude_none path serves. See docs/STATIC_HOSTING.md.
    return leveled(FirstRunResponse(trace=TRACES[_known(scenario)]()), level).model_dump(
        mode="json", by_alias=True, exclude_none=True
    )


@app.get("/api/scenarios", response_model=list[Scenario])
def get_scenarios(level: int = Level) -> list[Scenario]:
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
