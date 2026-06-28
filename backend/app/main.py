"""FastAPI app: serves GPU profiles and computes matmul simulation traces."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .engine import simulate
from .matrices import make_operands
from .models import GpuProfile, SimulateRequest, SimulateResponse
from .profiles import DEFAULT_PROFILE, PROFILES

app = FastAPI(title="GPU Matmul Visualizer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/profiles", response_model=list[GpuProfile])
def list_profiles() -> list[GpuProfile]:
    return list(PROFILES.values())


@app.get("/api/profiles/default", response_model=GpuProfile)
def default_profile() -> GpuProfile:
    return DEFAULT_PROFILE


@app.post("/api/simulate", response_model=SimulateResponse)
def post_simulate(req: SimulateRequest) -> SimulateResponse:
    profile, workload = req.profile, req.workload
    total_cores = profile.total_cores()
    if total_cores < 1:
        raise HTTPException(status_code=422, detail="profile has no cores")

    trace = simulate(profile, workload)
    a, b = make_operands(workload.n, workload.seed)
    return SimulateResponse(
        profile=profile,
        workload=workload,
        total_cores=total_cores,
        mac_total=workload.n ** 3,
        a=a,
        b=b,
        trace=trace,
    )
