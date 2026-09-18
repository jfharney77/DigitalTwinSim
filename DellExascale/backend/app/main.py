"""FastAPI app: serves the Exascale platform map, data-path trace, catalog,
use cases, and narrated tour. All content is static data + a pure engine — no state."""

from __future__ import annotations

from twinkit.api import Level, make_app
from twinkit.tour import TourResponse

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import CatalogCategory, DataResponse, PlatformAnatomy, UseCase
from .tour import TOUR_RESPONSE
from .usecases import USE_CASES

app = make_app(
    title="Exascale + Lightning Inside",
    frontend_port=5184,
)


@app.get("/api/anatomy", response_model=PlatformAnatomy)
def get_anatomy(level: int = Level) -> PlatformAnatomy:
    return leveled(ANATOMY, level)


@app.get("/api/datapath", response_model=DataResponse)
def get_datapath(level: int = Level) -> DataResponse:
    return leveled(DataResponse(trace=simulate()), level)


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
    the clock and pins the data-path trace cursor from each step."""
    return leveled(TOUR_RESPONSE, level)
