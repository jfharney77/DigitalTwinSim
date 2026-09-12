"""FastAPI app: serves the NativeEdge platform map, onboarding trace,
catalog, and use cases. All content is static data + a pure engine — no
state."""

from __future__ import annotations

from twinkit.api import Level, make_app

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import CatalogCategory, OnboardResponse, PlatformMap, UseCase
from .usecases import USE_CASES

app = make_app(
    title="Dell NativeEdge Inside",
    frontend_port=5187,
)


@app.get("/api/anatomy", response_model=PlatformMap)
def get_anatomy(level: int = Level) -> PlatformMap:
    return leveled(ANATOMY, level)


@app.get("/api/onboard", response_model=OnboardResponse)
def get_onboard(level: int = Level) -> OnboardResponse:
    return leveled(OnboardResponse(trace=simulate()), level)


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog(level: int = Level) -> list[CatalogCategory]:
    return leveled_all(CATALOG, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)
