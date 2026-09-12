"""FastAPI app: serves the IR7000 loop anatomy, thermal trace, catalog,
and use cases. All content is static data + a pure engine — no state."""

from __future__ import annotations

from twinkit.api import Level, make_app

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import CatalogCategory, RackAnatomy, ThermalResponse, UseCase
from .usecases import USE_CASES

app = make_app(
    title="IR7000 + PowerCool Inside",
    frontend_port=5182,
)


@app.get("/api/anatomy", response_model=RackAnatomy)
def get_anatomy(level: int = Level) -> RackAnatomy:
    return leveled(ANATOMY, level)


@app.get("/api/thermal", response_model=ThermalResponse)
def get_thermal(level: int = Level) -> ThermalResponse:
    return leveled(ThermalResponse(trace=simulate()), level)


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog(level: int = Level) -> list[CatalogCategory]:
    return leveled_all(CATALOG, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)
