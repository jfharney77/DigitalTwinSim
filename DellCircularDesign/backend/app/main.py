"""FastAPI app: serves the circular-design lifecycle map, material trace,
catalog, use cases, and narrated tour. All content is static data + a pure
engine — no state."""

from __future__ import annotations

from twinkit.api import Level, make_app
from twinkit.tour import TourResponse

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import CatalogCategory, LifecycleMap, MaterialResponse, UseCase
from .tour import TOUR_RESPONSE
from .usecases import USE_CASES

app = make_app(
    title="Dell Circular Design Inside",
    frontend_port=5197,
)


@app.get("/api/anatomy", response_model=LifecycleMap)
def get_anatomy(level: int = Level) -> LifecycleMap:
    return leveled(ANATOMY, level)


@app.get("/api/lifecycle", response_model=MaterialResponse)
def get_lifecycle(level: int = Level) -> MaterialResponse:
    return leveled(MaterialResponse(trace=simulate()), level)


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog(level: int = Level) -> list[CatalogCategory]:
    return leveled_all(CATALOG, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)


@app.get("/api/tour", response_model=TourResponse)
def get_tour(level: int = Level) -> TourResponse:
    return leveled(TOUR_RESPONSE, level)
