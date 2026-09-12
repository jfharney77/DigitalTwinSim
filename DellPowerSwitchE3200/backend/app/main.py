"""FastAPI app: serves the E3200-ON switch anatomy, boot trace, catalog, and
use cases. All content is static data + a pure engine — no state."""

from __future__ import annotations

from twinkit.api import Level, make_app

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import BootResponse, CatalogCategory, ChassisAnatomy, UseCase
from .usecases import USE_CASES

app = make_app(
    title="PowerSwitch E3200-ON Inside",
    frontend_port=5178,
)


@app.get("/api/anatomy", response_model=ChassisAnatomy)
def get_anatomy(level: int = Level) -> ChassisAnatomy:
    return leveled(ANATOMY, level)


@app.get("/api/boot", response_model=BootResponse)
def get_boot(level: int = Level) -> BootResponse:
    return leveled(BootResponse(trace=simulate()), level)


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog(level: int = Level) -> list[CatalogCategory]:
    return leveled_all(CATALOG, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)
