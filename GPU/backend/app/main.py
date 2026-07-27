"""FastAPI app: serves GPU profiles and computes matmul simulation traces."""

from __future__ import annotations

import asyncio

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .anatomy import ANATOMIES, DieAnatomy
from .engine import analyze, effective_tile_size, simulate
from .leveling import DEFAULT_LEVEL, LEVEL_NAMES, leveled, leveled_all
from .live import LiveState, ProbeEvent
from .live_store import HUB, SessionInfo
from .matrices import make_operands
from .mlp import MATMULS_PER_STEP, analyze_mlp, simulate_mlp
from .models import CamelModel, GpuProfile, SimulateRequest, SimulateResponse
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


Level = Query(
    DEFAULT_LEVEL,
    ge=1,
    le=5,
    description="Reading level: 1 newcomer, 3 standard, 5 specialist.",
)


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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/profiles", response_model=list[GpuProfile])
def list_profiles() -> list[GpuProfile]:
    return list(PROFILES.values())


@app.get("/api/profiles/default", response_model=GpuProfile)
def default_profile() -> GpuProfile:
    return DEFAULT_PROFILE


@app.get("/api/anatomy", response_model=list[DieAnatomy])
def list_anatomies(level: int = Level) -> list[DieAnatomy]:
    return leveled_all(list(ANATOMIES.values()), level)


@app.get("/api/anatomy/{anatomy_id}", response_model=DieAnatomy)
def get_anatomy(anatomy_id: str, level: int = Level) -> DieAnatomy:
    anatomy = ANATOMIES.get(anatomy_id)
    if anatomy is None:
        raise HTTPException(status_code=404, detail=f"unknown die {anatomy_id!r}")
    return leveled(anatomy, level)


# -- Live CUDA co-browsing (spec_08) ------------------------------------------
# The routes are the transport edge only: stamping/persistence/broadcast live
# in live_store.py, the pure event fold in live.py.


class StartSessionRequest(CamelModel):
    name: str | None = None


class TraceResponse(CamelModel):
    session_id: str
    trace: list[LiveState]


@app.post("/api/live/ingest", response_model=LiveState)
def live_ingest(event: ProbeEvent = Body(...)) -> LiveState:
    return HUB.ingest(event)


@app.get("/api/live/stream")
async def live_stream() -> StreamingResponse:
    q = HUB.subscribe()

    async def gen():
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"  # hold the connection open when idle
                    continue
                yield f"data: {payload}\n\n"
        finally:
            HUB.unsubscribe(q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/live/session", response_model=SessionInfo)
def live_start_session(req: StartSessionRequest | None = None) -> SessionInfo:
    return HUB.start_session(req.name if req else None)


@app.delete("/api/live/session")
def live_stop_session() -> dict[str, str]:
    HUB.stop_session()
    return {"status": "stopped"}


@app.get("/api/live/sessions", response_model=list[SessionInfo])
def live_sessions() -> list[SessionInfo]:
    return HUB.list_sessions()


@app.get("/api/live/sessions/{session_id}/trace", response_model=TraceResponse)
def live_trace(session_id: str) -> TraceResponse:
    try:
        trace = HUB.load_trace(session_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail=f"unknown session {session_id!r}")
    return TraceResponse(session_id=session_id, trace=trace)


@app.post("/api/simulate", response_model=SimulateResponse)
def post_simulate(req: SimulateRequest) -> SimulateResponse:
    profile, workload = req.profile, req.workload
    total_cores = profile.total_cores()
    if total_cores < 1:
        raise HTTPException(status_code=422, detail="profile has no cores")

    tile_size = effective_tile_size(workload.n, workload.tile_size)

    if workload.kind == "mlp_step":
        trace, info = simulate_mlp(profile, workload)
        first = info.ops[0]
        return SimulateResponse(
            profile=profile,
            workload=workload,
            total_cores=total_cores,
            mac_total=workload.steps * MATMULS_PER_STEP * workload.n ** 3,
            tile_size=tile_size,
            summary=analyze_mlp(profile, workload),
            a=first.a or [],
            b=first.b or [],
            trace=trace,
            mlp=info,
        )

    trace = simulate(profile, workload)
    a, b = make_operands(workload.n, workload.seed)
    return SimulateResponse(
        profile=profile,
        workload=workload,
        total_cores=total_cores,
        mac_total=workload.n ** 3,
        tile_size=tile_size,
        summary=analyze(profile, workload),
        a=a,
        b=b,
        trace=trace,
    )
