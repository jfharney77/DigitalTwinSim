"""FastAPI app: serves GPU profiles and computes matmul simulation traces."""

from __future__ import annotations

import asyncio

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .anatomy import ANATOMIES, DieAnatomy
from .engine import (
    analyze,
    attach_energy,
    effective_tile_size,
    resolve_dims,
    simulate,
)
from .leveling import DEFAULT_LEVEL, LEVEL_NAMES, leveled, leveled_all
from pathlib import Path

from .live import LiveState, ProbeEvent, SessionSummary, replay, summarize
from .live_store import HUB, SessionInfo, load_events, load_recording
from .remap import remap_events
from .tour import LessonTour, build_tour

TOURS_DIR = Path(__file__).resolve().parent.parent / "tours" / "lessons"
from .llm import analyze_llm, mac_total_decode, mac_total_prefill, simulate_llm
from .matrices import make_operands
from .mlp import MATMULS_PER_STEP, analyze_mlp, simulate_mlp
from .models import CamelModel, GpuProfile, SimulateRequest, SimulateResponse
from .profiles import DEFAULT_PROFILE, DEVICE_MATCHES, PROFILES

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
def health() -> dict[str, object]:
    active = HUB.active_session()
    return {
        "status": "ok",
        "version": app.version,
        "sessions": len(HUB.list_sessions(limit=500)),
        "activeSession": active.id if active else None,
        "toursAvailable": len(list(TOURS_DIR.glob("*.jsonl")))
        if TOURS_DIR.exists()
        else 0,
    }


@app.get("/api/profiles", response_model=list[GpuProfile])
def list_profiles() -> list[GpuProfile]:
    return list(PROFILES.values())


@app.get("/api/profiles/default", response_model=GpuProfile)
def default_profile() -> GpuProfile:
    return DEFAULT_PROFILE


# -- Cross-navigation atlas (spec_30) -----------------------------------------


class AtlasPair(CamelModel):
    profile_name: str
    die_id: str
    device_match: list[str]  # substrings matched against live device names


class Atlas(CamelModel):
    pairs: list[AtlasPair]


@app.get("/api/atlas", response_model=Atlas)
def get_atlas() -> Atlas:
    """spec_30: the profile↔die correspondences as data. Only mapped pairs
    appear — unmapped profiles/dies are honest gaps, not empty entries."""
    return Atlas(
        pairs=[
            AtlasPair(
                profile_name=p.name,
                die_id=p.die_id,
                device_match=DEVICE_MATCHES.get(p.name, []),
            )
            for p in PROFILES.values()
            if p.die_id is not None
        ]
    )


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
    total: int | None = None  # full frame count when the trace is paginated


# spec_28: fleet replay rides a query param on the two existing trace routes —
# deliberately NOT a new route, so test_api_surface_snapshot stays untouched.
AsProfile = Query(
    None,
    alias="asProfile",
    description="Remap the recording onto this fleet profile's die (spec_28).",
)


def _as_profile(name: str | None) -> GpuProfile | None:
    if name is None:
        return None
    if not name.strip():
        raise HTTPException(status_code=422, detail="asProfile must name a profile")
    profile = PROFILES.get(name)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"unknown profile {name!r}")
    return profile


@app.post("/api/live/ingest", response_model=LiveState)
def live_ingest(event: ProbeEvent = Body(...)) -> LiveState:
    try:
        return HUB.ingest(event)
    except OverflowError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        # The fold rejected it (smid beyond the session's device, device
        # change under recorded kernels) — and rejected it BEFORE persisting.
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/api/measurements")
def get_measurements() -> dict:
    """Latest calibration measurement per metric (spec_15)."""
    return HUB.measurements()


@app.get("/api/tour", response_model=LessonTour)
def get_tour(level: int = Level) -> LessonTour:
    # spec_29: resolution at the transport edge — tour.py stays level-3 data.
    return leveled(build_tour(), level)


@app.get("/api/tour/recordings/{lesson_id}", response_model=TraceResponse)
def get_tour_recording(
    lesson_id: str, as_profile: str | None = AsProfile
) -> TraceResponse:
    if "/" in lesson_id or ".." in lesson_id:
        raise HTTPException(status_code=404, detail="unknown lesson")
    target = _as_profile(as_profile)
    path = TOURS_DIR / f"{lesson_id}.jsonl"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"unknown lesson {lesson_id!r}")
    try:
        if target is None:
            trace = load_recording(path, lesson_id)
        else:
            trace = replay(lesson_id, remap_events(load_events(path), target))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"recording corrupt: {e}")
    return TraceResponse(session_id=lesson_id, trace=trace)


@app.get("/api/live/stream")
async def live_stream() -> StreamingResponse:
    sub = HUB.subscribe()

    async def gen():
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(sub.queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"  # hold the connection open when idle
                    continue
                dropped = sub.take_dropped()
                if dropped:
                    # This consumer lagged and frames were skipped — say so.
                    yield f"event: dropped\ndata: {dropped}\n\n"
                yield f"data: {payload}\n\n"
        finally:
            HUB.unsubscribe(sub)

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


@app.get("/api/live/config")
def live_config() -> dict[str, int]:
    """The live path's caps as data (spec_21 #12) — tools and UI read these
    instead of hardcoding what the backend already knows."""
    from . import live, live_store

    return {
        "maxSessionEvents": live_store.MAX_SESSION_EVENTS,
        "maxSmid": live.MAX_SMID,
        "maxSpans": live.MAX_SPANS,
        "defaultSmCount": live.DEFAULT_SM_COUNT,
        "measurementHistory": live_store.MEASUREMENT_HISTORY,
    }


@app.post("/api/live/ingest/batch", response_model=LiveState)
def live_ingest_batch(events: list[ProbeEvent] = Body(...)) -> LiveState:
    """One request, many events (spec_21 #14). All-or-nothing per event:
    the first rejected event stops the batch with its error; events before
    it are already recorded (append-only, same as separate POSTs)."""
    if not events:
        raise HTTPException(status_code=422, detail="empty batch")
    if len(events) > 1000:
        raise HTTPException(status_code=422, detail="batch too large (max 1000)")
    last: LiveState | None = None
    for event in events:
        try:
            last = HUB.ingest(event)
        except OverflowError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    assert last is not None
    return last


@app.get("/api/live/latest", response_model=LiveState)
def live_latest() -> LiveState:
    state = HUB.latest()
    if state is None:
        raise HTTPException(status_code=404, detail="no frames yet")
    return state


@app.get("/api/live/sessions", response_model=list[SessionInfo])
def live_sessions(limit: int = Query(50, ge=1, le=500)) -> list[SessionInfo]:
    return HUB.list_sessions(limit)


@app.delete("/api/live/sessions/{session_id}")
def live_delete_session(session_id: str) -> dict[str, str]:
    try:
        HUB.delete_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"unknown session {session_id!r}")
    except (PermissionError, ValueError) as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"status": "deleted"}


class ImportRequest(CamelModel):
    name: str
    jsonl: str


class RenameRequest(CamelModel):
    name: str


@app.get("/api/live/sessions/{session_id}/summary", response_model=SessionSummary)
def live_summary(session_id: str) -> SessionSummary:
    try:
        trace = HUB.load_trace(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"unknown session {session_id!r}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"recording corrupt: {e}")
    return summarize(session_id, trace)


@app.post("/api/live/import", response_model=SessionInfo)
def live_import(req: ImportRequest) -> SessionInfo:
    try:
        return HUB.import_session(req.name, req.jsonl)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"not a valid recording: {e}")


@app.patch("/api/live/sessions/{session_id}", response_model=SessionInfo)
def live_rename(session_id: str, req: RenameRequest) -> SessionInfo:
    try:
        return HUB.rename_session(session_id, req.name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"unknown session {session_id!r}")
    except (PermissionError, ValueError) as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.get("/api/live/sessions/{session_id}/events.csv")
def live_events_csv(session_id: str):
    from fastapi.responses import PlainTextResponse

    try:
        trace = HUB.load_trace(session_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail=f"unknown session {session_id!r}")
    rows = ["kernel,tMs,elapsedMs,occupancyPct,source"]
    for s in trace:
        if s.kind != "kernel":
            continue
        rows.append(
            f"{s.kernel},{s.t_ms:.3f},"
            f"{'' if s.elapsed_ms is None else f'{s.elapsed_ms:.4f}'},"
            f"{'' if s.occupancy_pct is None else f'{s.occupancy_pct:.1f}'},"
            f"{s.source}"
        )
    return PlainTextResponse(
        "\n".join(rows) + "\n",
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{session_id}.csv"'},
    )


@app.get("/api/live/sessions/{session_id}/download")
def live_download(session_id: str):
    from fastapi.responses import PlainTextResponse

    try:
        raw = HUB.raw_recording(session_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail=f"unknown session {session_id!r}")
    return PlainTextResponse(
        raw,
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": f'attachment; filename="{session_id}.jsonl"'
        },
    )


@app.get("/api/live/sessions/{session_id}/trace", response_model=TraceResponse)
def live_trace(
    session_id: str,
    from_: int = Query(0, ge=0, alias="from"),
    limit: int | None = Query(None, ge=1, le=100_000),
    as_profile: str | None = AsProfile,
) -> TraceResponse:
    target = _as_profile(as_profile)
    try:
        if target is None:
            trace = HUB.load_trace(session_id)
        else:
            # Read path only: the remap rewrites events in memory and the
            # pure replay folds them — the session file is never touched.
            trace = replay(
                session_id, remap_events(HUB.load_events(session_id), target)
            )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"unknown session {session_id!r}")
    except ValueError as e:
        # The file exists but the recording is unreadable (bad JSON line,
        # non-monotonic stamps). "404 unknown" would be a lie.
        raise HTTPException(
            status_code=422, detail=f"recording {session_id!r} is corrupt: {e}"
        )
    total = len(trace)
    window = trace[from_ : from_ + limit if limit else None]
    return TraceResponse(session_id=session_id, trace=window, total=total)


@app.post("/api/simulate", response_model=SimulateResponse)
def post_simulate(req: SimulateRequest) -> SimulateResponse:
    profile, workload = req.profile, req.workload
    total_cores = profile.total_cores()
    if total_cores < 1:
        raise HTTPException(status_code=422, detail="profile has no cores")

    # spec_23: tensor mode requires the die to declare the dtype. Validate at
    # the API edge so the pure engine never sees an unsupported pair (its own
    # fallback is the scalar path, but that fallback is defense, not UX).
    if workload.execution == "tensor":
        ts = profile.tensor
        supported = sorted(ts.multipliers) if ts else []
        if workload.dtype not in supported:
            detail = (
                f"{profile.name} has no tensor path for {workload.dtype}: "
                + (
                    f"supported dtypes are {', '.join(supported)}"
                    if supported
                    else "this profile has no tensor units"
                )
            )
            raise HTTPException(status_code=422, detail=detail)

    # spec_27: the link is a feature of the die, not the workload. A profile
    # without one cannot scale up — the refusal is the lesson, not a fallback
    # (the engine's own single-die fallback is defense, not UX). mlp_step /
    # llm_decode with gpus=2 already 422 at model validation.
    if workload.gpus == 2 and profile.link is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{profile.name} has no die-to-die link: consumer dies scale "
                "out over PCIe or not at all. Pick H100-SXM (NVLink4) or "
                "B300-Blackwell-Ultra (NVLink5) to run gpus=2."
            ),
        )

    # spec_22: resolve the M/K sentinels once, server-side. mlp_step is
    # square-only (nonzero M/K already 422 at model validation).
    m_dim, k_dim, n = resolve_dims(workload)
    tile_size = effective_tile_size(max(m_dim, k_dim, n), workload.tile_size)

    if workload.kind == "mlp_step":
        trace, info = simulate_mlp(profile, workload)
        first = info.ops[0]
        return SimulateResponse(
            profile=profile,
            workload=workload,
            total_cores=total_cores,
            mac_total=workload.steps * MATMULS_PER_STEP * workload.n ** 3,
            m=m_dim,
            k=k_dim,
            n=n,
            tile_size=tile_size,
            summary=attach_energy(analyze_mlp(profile, workload), trace),
            a=first.a or [],
            b=first.b or [],
            trace=trace,
            mlp=info,
        )

    if workload.kind == "llm_decode":
        trace, info = simulate_llm(profile, workload)
        first = next(op for op in info.ops if op.kind == "matmul")
        return SimulateResponse(
            profile=profile,
            workload=workload,
            total_cores=total_cores,
            mac_total=mac_total_prefill(n, workload.steps)
            if workload.prefill
            else mac_total_decode(n, workload.kv_len, workload.steps),
            m=m_dim,
            k=k_dim,
            n=n,
            tile_size=tile_size,
            summary=attach_energy(analyze_llm(profile, workload), trace),
            a=first.a or [],
            b=first.b or [],
            trace=trace,
            llm=info,
        )

    trace = simulate(profile, workload)
    a, b = make_operands(workload.n, workload.seed, m=workload.m, k=workload.k_dim)
    return SimulateResponse(
        profile=profile,
        workload=workload,
        total_cores=total_cores,
        mac_total=m_dim * k_dim * n,
        m=m_dim,
        k=k_dim,
        n=n,
        tile_size=tile_size,
        summary=attach_energy(analyze(profile, workload), trace),
        a=a,
        b=b,
        trace=trace,
    )
