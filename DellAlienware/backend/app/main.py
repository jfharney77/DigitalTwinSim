"""FastAPI app: serves the laptop catalog, interior anatomies, use cases,
and the AC power-path simulation. All content is static data + a pure
engine — no state. Runs on port 8003 (frontend Vite dev server on 5176
proxies /api here)."""

from __future__ import annotations

from fastapi import HTTPException

from twinkit.api import Level, make_app

from .anatomy import ANATOMIES
from .catalog import DEFAULT_PROFILE, PROFILES
from .engine import analyze, simulate
from .leveling import leveled, leveled_all
from .models import (
    Anatomy,
    LaptopProfile,
    SimulateRequest,
    SimulateResponse,
    UseCase,
)
from .usecases import USE_CASES

app = make_app(
    title="Alienware m18 Inside",
    frontend_port=5176,
)


@app.get("/api/catalog", response_model=list[LaptopProfile])
def get_catalog(level: int = Level) -> list[LaptopProfile]:
    return leveled_all(list(PROFILES.values()), level)


@app.get("/api/catalog/default", response_model=LaptopProfile)
def get_default_profile(level: int = Level) -> LaptopProfile:
    return leveled(DEFAULT_PROFILE, level)


@app.get("/api/anatomy", response_model=list[Anatomy])
def get_anatomies(level: int = Level) -> list[Anatomy]:
    return leveled_all(list(ANATOMIES.values()), level)


@app.get("/api/anatomy/{anatomy_id}", response_model=Anatomy)
def get_anatomy(anatomy_id: str, level: int = Level) -> Anatomy:
    anatomy = ANATOMIES.get(anatomy_id)
    if anatomy is None:
        raise HTTPException(status_code=404, detail=f"unknown anatomy {anatomy_id!r}")
    return leveled(anatomy, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)


@app.post("/api/simulate", response_model=SimulateResponse)
def post_simulate(req: SimulateRequest, level: int = Level) -> SimulateResponse:
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
    return leveled(
        SimulateResponse(
            profile=profile,
            scenario=scenario,
            adapter=adapter,
            summary=analyze(profile, adapter, scenario, trace),
            trace=trace,
        ),
        level,
    )
