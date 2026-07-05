"""FastAPI app: serves the laptop catalog, interior anatomies, use cases,
and the AC power-path simulation. All content is static data + a pure
engine — no state. Runs on port 8002 (frontend Vite dev server on 5175
proxies /api here)."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .anatomy import ANATOMIES
from .catalog import DEFAULT_PROFILE, PROFILES
from .engine import analyze, simulate
from .models import (
    Anatomy,
    LaptopProfile,
    SimulateRequest,
    SimulateResponse,
    UseCase,
)
from .usecases import USE_CASES

app = FastAPI(title="Alienware m18 Inside", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/catalog", response_model=list[LaptopProfile])
def get_catalog() -> list[LaptopProfile]:
    return list(PROFILES.values())


@app.get("/api/catalog/default", response_model=LaptopProfile)
def get_default_profile() -> LaptopProfile:
    return DEFAULT_PROFILE


@app.get("/api/anatomy", response_model=list[Anatomy])
def get_anatomies() -> list[Anatomy]:
    return list(ANATOMIES.values())


@app.get("/api/anatomy/{anatomy_id}", response_model=Anatomy)
def get_anatomy(anatomy_id: str) -> Anatomy:
    anatomy = ANATOMIES.get(anatomy_id)
    if anatomy is None:
        raise HTTPException(status_code=404, detail=f"unknown anatomy {anatomy_id!r}")
    return anatomy


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases() -> list[UseCase]:
    return USE_CASES


@app.post("/api/simulate", response_model=SimulateResponse)
def post_simulate(req: SimulateRequest) -> SimulateResponse:
    scenario = req.scenario
    profile = PROFILES.get(scenario.profile_id)
    if profile is None:
        raise HTTPException(
            status_code=422, detail=f"unknown profileId {scenario.profile_id!r}"
        )
    adapter = next(
        (a for a in profile.adapters if a.id == scenario.adapter_id), None
    )
    if adapter is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"unknown adapterId {scenario.adapter_id!r} "
                f"for profile {profile.id!r}"
            ),
        )
    trace = simulate(profile, adapter, scenario)
    return SimulateResponse(
        profile=profile,
        scenario=scenario,
        adapter=adapter,
        summary=analyze(profile, adapter, scenario, trace),
        trace=trace,
    )
