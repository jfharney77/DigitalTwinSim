"""FastAPI app: serves the CloudIQ / Dell AIOps platform architecture, the
telemetry-to-insight pipeline trace, the capability catalog, and use cases.
All content is static data + a pure engine — no state."""

from __future__ import annotations

from twinkit.api import Level, make_app

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import CatalogCategory, PipelineResponse, PlatformMap, UseCase
from .usecases import USE_CASES

app = make_app(
    title="CloudIQ Inside",
    frontend_port=5180,
)


@app.get("/api/anatomy", response_model=PlatformMap)
def get_anatomy(level: int = Level) -> PlatformMap:
    return leveled(ANATOMY, level)


@app.get("/api/pipeline", response_model=PipelineResponse)
def get_pipeline(level: int = Level) -> PipelineResponse:
    return leveled(PipelineResponse(trace=simulate()), level)


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog(level: int = Level) -> list[CatalogCategory]:
    return leveled_all(CATALOG, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)
