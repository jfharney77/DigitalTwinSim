"""FastAPI app: serves the circular-design lifecycle map, material trace,
catalog, and use cases. All content is static data + a pure engine — no
state."""

from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .leveling import DEFAULT_LEVEL, LEVEL_NAMES, leveled, leveled_all
from .models import CatalogCategory, LifecycleMap, MaterialResponse, UseCase
from .usecases import USE_CASES

app = FastAPI(title="Dell Circular Design Inside", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5197",
        "http://127.0.0.1:5197",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

Level = Query(
    DEFAULT_LEVEL,
    ge=1,
    le=5,
    description="Reading level: 1 newcomer, 3 standard, 5 specialist.",
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/levels")
def get_levels() -> dict[str, object]:
    """What the reading-level control offers, so the UI does not
    hard-code the scale."""
    return {
        "default": DEFAULT_LEVEL,
        "levels": [
            {"level": level, "name": name}
            for level, name in LEVEL_NAMES.items()
        ],
    }


@app.get("/api/anatomy", response_model=LifecycleMap)
def get_anatomy(level: int = Level) -> LifecycleMap:
    return leveled(ANATOMY, level)


@app.get("/api/lifecycle", response_model=MaterialResponse)
def get_lifecycle(level: int = Level) -> MaterialResponse:
    return leveled(MaterialResponse(trace=simulate()), level)


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog(level: int = Level) -> list[CatalogCategory]:
    return leveled_all(CATALOG, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)
