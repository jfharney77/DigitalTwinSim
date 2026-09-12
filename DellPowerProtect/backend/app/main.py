"""FastAPI app: serves the PowerProtect site map, data-lifecycle trace,
catalog, and use cases. All content is static data + a pure engine — no
state."""

from __future__ import annotations

from twinkit.api import Level, make_app

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import CatalogCategory, LifecycleResponse, SiteAnatomy, UseCase
from .usecases import USE_CASES

app = make_app(
    title="PowerProtect + Cyber Recovery Inside",
    frontend_port=5183,
)


@app.get("/api/anatomy", response_model=SiteAnatomy)
def get_anatomy(level: int = Level) -> SiteAnatomy:
    return leveled(ANATOMY, level)


@app.get("/api/lifecycle", response_model=LifecycleResponse)
def get_lifecycle(level: int = Level) -> LifecycleResponse:
    return leveled(LifecycleResponse(trace=simulate()), level)


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog(level: int = Level) -> list[CatalogCategory]:
    return leveled_all(CATALOG, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)
