"""FastAPI app: serves the Quantum-X800 fabric anatomy, fabric trace,
catalog, and use cases. All content is static data + a pure engine — no
state."""

from __future__ import annotations

from twinkit.api import Level, make_app

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import CatalogCategory, FabricAnatomy, FabricResponse, UseCase
from .usecases import USE_CASES

app = make_app(
    title="Quantum-X800 InfiniBand Inside",
    frontend_port=5202,
)


@app.get("/api/anatomy", response_model=FabricAnatomy)
def get_anatomy(level: int = Level) -> FabricAnatomy:
    return leveled(ANATOMY, level)


@app.get("/api/fabric", response_model=FabricResponse)
def get_fabric(level: int = Level) -> FabricResponse:
    return leveled(FabricResponse(trace=simulate()), level)


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog(level: int = Level) -> list[CatalogCategory]:
    return leveled_all(CATALOG, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)
