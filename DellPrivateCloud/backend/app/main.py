"""FastAPI app: serves the Private Cloud stack map, cloud trace, catalog,
and use cases. All content is static data + a pure engine — no state.

Every endpoint takes an optional ``level`` (1–5) that selects the reading
register of the prose: 1 opens up the jargon for a newcomer, 5 leaves it in
for a specialist. The default, 3, is the register the twin was written in,
so an unadorned request behaves exactly as it always did. Resolution
happens here rather than in the engine or the data modules, which keeps the
engine pure and the wire format unchanged — see ``leveling.py``.
"""

from __future__ import annotations

from twinkit.api import Level, make_app
from twinkit.tour import TourResponse

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import CatalogCategory, CloudAnatomy, CloudResponse, UseCase
from .tour import TOUR_RESPONSE
from .usecases import USE_CASES

app = make_app(
    title="Dell Private Cloud Inside",
    frontend_port=5198,
    version="0.2.0",
)


@app.get("/api/anatomy", response_model=CloudAnatomy)
def get_anatomy(level: int = Level) -> CloudAnatomy:
    return leveled(ANATOMY, level)


@app.get("/api/cloud", response_model=CloudResponse)
def get_cloud(level: int = Level) -> CloudResponse:
    return leveled(CloudResponse(trace=simulate()), level)


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
    the clock and drives the cloud trace cursor from it."""
    return leveled(TOUR_RESPONSE, level)
