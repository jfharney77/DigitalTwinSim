"""FastAPI app: serves the R760 chassis anatomy, power-on trace, catalog,
and use cases. All content is static data + a pure engine — no state."""

from __future__ import annotations

from twinkit.api import Level, make_app

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import CatalogCategory, ChassisAnatomy, PowerOnResponse, UseCase
from .usecases import USE_CASES

app = make_app(
    title="PowerEdge R760 Inside",
    frontend_port=5174,
)


@app.get("/api/anatomy", response_model=ChassisAnatomy)
def get_anatomy(level: int = Level) -> ChassisAnatomy:
    return leveled(ANATOMY, level)


@app.get("/api/poweron", response_model=PowerOnResponse)
def get_poweron(level: int = Level) -> PowerOnResponse:
    return leveled(PowerOnResponse(trace=simulate()), level)


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog(level: int = Level) -> list[CatalogCategory]:
    return leveled_all(CATALOG, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)
