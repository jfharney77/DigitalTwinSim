"""FastAPI app: serves the CloudIQ / Dell AIOps platform architecture, the
telemetry-to-insight pipeline trace, the capability catalog, and use cases.
All content is static data + a pure engine — no state."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .models import CatalogCategory, PipelineResponse, PlatformMap, UseCase
from .usecases import USE_CASES

app = FastAPI(title="CloudIQ Inside", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5180",
        "http://127.0.0.1:5180",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/anatomy", response_model=PlatformMap)
def get_anatomy() -> PlatformMap:
    return ANATOMY


@app.get("/api/pipeline", response_model=PipelineResponse)
def get_pipeline() -> PipelineResponse:
    return PipelineResponse(trace=simulate())


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog() -> list[CatalogCategory]:
    return CATALOG


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases() -> list[UseCase]:
    return USE_CASES
