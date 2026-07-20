"""FastAPI app: serves the XE9712 rack anatomy, power-on trace, catalog,
and use cases. All content is static data + a pure engine — no state."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .models import CatalogCategory, PowerOnResponse, RackAnatomy, UseCase
from .usecases import USE_CASES

app = FastAPI(title="PowerEdge XE9712 Inside", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5181",
        "http://127.0.0.1:5181",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/anatomy", response_model=RackAnatomy)
def get_anatomy() -> RackAnatomy:
    return ANATOMY


@app.get("/api/poweron", response_model=PowerOnResponse)
def get_poweron() -> PowerOnResponse:
    return PowerOnResponse(trace=simulate())


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog() -> list[CatalogCategory]:
    return CATALOG


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases() -> list[UseCase]:
    return USE_CASES
