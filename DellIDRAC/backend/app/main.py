"""FastAPI app: serves the iDRAC9 subsystem map, bring-up trace, capability
catalog, and management use cases. All content is static data + a pure engine
— no state."""

from __future__ import annotations

from twinkit.api import Level, make_app

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import BringUpResponse, CatalogCategory, SubsystemMap, UseCase
from .usecases import USE_CASES

app = make_app(
    title="iDRAC9 Inside",
    frontend_port=5177,
)


@app.get("/api/anatomy", response_model=SubsystemMap)
def get_anatomy(level: int = Level) -> SubsystemMap:
    return leveled(ANATOMY, level)


@app.get("/api/bringup", response_model=BringUpResponse)
def get_bringup(level: int = Level) -> BringUpResponse:
    return leveled(BringUpResponse(trace=simulate()), level)


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog(level: int = Level) -> list[CatalogCategory]:
    return leveled_all(CATALOG, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)
