"""FastAPI app: serves the PowerScale cluster map, namespace trace,
catalog, and use cases. All content is static data + a pure engine — no
state."""

from __future__ import annotations

from twinkit.api import Level, make_app

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import CatalogCategory, ClusterAnatomy, NamespaceResponse, UseCase
from .usecases import USE_CASES

app = make_app(
    title="Dell PowerScale Inside",
    frontend_port=5196,
)


@app.get("/api/anatomy", response_model=ClusterAnatomy)
def get_anatomy(level: int = Level) -> ClusterAnatomy:
    return leveled(ANATOMY, level)


@app.get("/api/namespace", response_model=NamespaceResponse)
def get_namespace(level: int = Level) -> NamespaceResponse:
    return leveled(NamespaceResponse(trace=simulate()), level)


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog(level: int = Level) -> list[CatalogCategory]:
    return leveled_all(CATALOG, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)
