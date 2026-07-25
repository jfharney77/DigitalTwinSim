"""FastAPI app: serves the Private Cloud stack map, cloud trace, catalog,
and use cases. All content is static data + a pure engine — no state."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .anatomy import ANATOMY
from .catalog import CATALOG
from .engine import simulate
from .models import CatalogCategory, CloudAnatomy, CloudResponse, UseCase
from .usecases import USE_CASES

app = FastAPI(title="Dell Private Cloud Inside", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5198",
        "http://127.0.0.1:5198",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/anatomy", response_model=CloudAnatomy)
def get_anatomy() -> CloudAnatomy:
    return ANATOMY


@app.get("/api/cloud", response_model=CloudResponse)
def get_cloud() -> CloudResponse:
    return CloudResponse(trace=simulate())


@app.get("/api/catalog", response_model=list[CatalogCategory])
def get_catalog() -> list[CatalogCategory]:
    return CATALOG


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases() -> list[UseCase]:
    return USE_CASES
