"""FastAPI app: serves the Fort Zero zero-trust map, access trace, catalog,
and use cases. All content is static data + a pure engine — no state."""

from __future__ import annotations

from twinkit.api import Level, make_app

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import AccessResponse, CatalogCategory, UseCase, ZeroTrustMap
from .usecases import USE_CASES

app = make_app(
    title="Dell Project Fort Zero Inside",
    frontend_port=5195,
)


@app.get("/api/anatomy", response_model=ZeroTrustMap)
def get_anatomy(level: int = Level) -> ZeroTrustMap:
    return leveled(ANATOMY, level)


@app.get("/api/access", response_model=AccessResponse)
def get_access(level: int = Level) -> AccessResponse:
    return leveled(AccessResponse(trace=simulate()), level)


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog(level: int = Level) -> list[CatalogCategory]:
    return leveled_all(CATALOG, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)
