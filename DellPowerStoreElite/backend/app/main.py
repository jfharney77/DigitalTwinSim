"""FastAPI app: serves the PowerStore Elite cluster anatomy, join trace,
catalog, and use cases. All content is static data + a pure engine — no
state."""

from __future__ import annotations

from twinkit.api import Level, make_app
from twinkit.tour import TourResponse

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import CatalogCategory, ChassisAnatomy, JoinResponse, UseCase
from .tour import TOUR_RESPONSE
from .usecases import USE_CASES

app = make_app(
    title="PowerStore Elite Inside",
    frontend_port=5220,
)


@app.get("/api/anatomy", response_model=ChassisAnatomy)
def get_anatomy(level: int = Level) -> ChassisAnatomy:
    return leveled(ANATOMY, level)


@app.get("/api/join", response_model=JoinResponse)
def get_join(level: int = Level) -> JoinResponse:
    return leveled(JoinResponse(trace=simulate()), level)


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog(level: int = Level) -> list[CatalogCategory]:
    return leveled_all(CATALOG, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)


@app.get("/api/tour", response_model=TourResponse)
def get_tour(level: int = Level) -> TourResponse:
    return leveled(TOUR_RESPONSE, level)
