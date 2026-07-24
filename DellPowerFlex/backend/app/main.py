"""FastAPI app: serves the PowerFlex pool map, cluster trace, catalog, and
use cases. All content is static data + a pure engine — no state."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .models import CatalogCategory, ClusterAnatomy, ClusterResponse, UseCase
from .usecases import USE_CASES

app = FastAPI(title="Dell PowerFlex Inside", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5189",
        "http://127.0.0.1:5189",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/anatomy", response_model=ClusterAnatomy)
def get_anatomy() -> ClusterAnatomy:
    return ANATOMY


@app.get("/api/cluster", response_model=ClusterResponse)
def get_cluster() -> ClusterResponse:
    return ClusterResponse(trace=simulate())


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog() -> list[CatalogCategory]:
    return CATALOG


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases() -> list[UseCase]:
    return USE_CASES
