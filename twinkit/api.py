"""The FastAPI skeleton every component's ``main.py`` re-typed.

Before this module, ``/api/health`` existed 42 times, ``/api/levels`` 42
times, and the CORS block and the shared ``Query(3, ge=1, le=5)`` reading-level
parameter alongside them. A fix to any of those was a 42-file edit, so in
practice it was a three-file edit.

``make_app`` returns a configured ``FastAPI`` with the shared routes already
mounted. A component's ``main.py`` keeps only what is actually its own: its
title, the port its frontend runs on, and its domain routes.

    from twinkit.api import Level, make_app

    app = make_app(title="PowerMax Inside", frontend_port=5178)

    @app.get("/api/anatomy", response_model=ChassisAnatomy)
    def get_anatomy(level: int = Level) -> ChassisAnatomy:
        return leveled(ANATOMY, level)

``profiles`` and ``simulate`` are optional: pass them and the trace and
profile-list routes are mounted too, which is the whole of a simple
component's ``main.py``. Components whose trace endpoint is named for their
domain (``/api/boot``, ``/api/thermal``, ``/api/join``, ...) or whose trace
takes a scenario keep declaring that route themselves — the name is part of
what the component is, not boilerplate.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .leveling import DEFAULT_LEVEL, LEVEL_NAMES, Leveling
from .leveling import leveled as _leveled
from .leveling import leveled_all as _leveled_all

__all__ = ["Level", "make_app", "health_payload", "levels_payload"]

#: The reading-level query parameter, shared so the scale is declared once.
Level = Query(
    DEFAULT_LEVEL,
    ge=1,
    le=5,
    description="Reading level: 1 newcomer, 3 standard, 5 specialist.",
)


def health_payload() -> dict[str, str]:
    """What ``/api/health`` answers. The CustomerSetup liveness chips ping
    this on every twin, so the shape is a contract."""
    return {"status": "ok"}


def levels_payload() -> dict[str, object]:
    """What the reading-level control offers, so the UI does not hard-code
    the scale."""
    return {
        "default": DEFAULT_LEVEL,
        "levels": [
            {"level": level, "name": name} for level, name in LEVEL_NAMES.items()
        ],
    }


def make_app(
    *,
    title: str,
    frontend_port: int | Sequence[int],
    version: str = "0.1.0",
    profiles: Sequence[Any] | Callable[[], Sequence[Any]] | None = None,
    simulate: Callable[[], Any] | None = None,
    trace_path: str = "/api/trace",
    trace_response_model: Any = None,
    leveling: Leveling | None = None,
    health: bool = True,
) -> FastAPI:
    """A component backend with the shared routes already mounted.

    ``frontend_port`` is the vite port from ``ports.json``; CORS is opened to
    localhost and 127.0.0.1 on it (a sequence opens several, for the few
    components that share a frontend or moved ports).

    ``health=False`` suppresses the default ``/api/health`` for the one
    component that answers it with more than a status — the GPU twin reports
    its live-session count there. Anything richer than that belongs in its own
    route; the shared one is what the CustomerSetup liveness chips ping.

    ``leveling`` is the component's own :class:`~twinkit.leveling.Leveling`
    registry; pass it whenever ``profiles`` or ``simulate`` is passed, so the
    mounted routes read prose out of the right registry.
    """
    leveled = leveling.leveled if leveling else _leveled
    leveled_all = leveling.leveled_all if leveling else _leveled_all
    app = FastAPI(title=title, version=version)

    ports = [frontend_port] if isinstance(frontend_port, int) else list(frontend_port)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            f"http://{host}:{port}"
            for port in ports
            for host in ("localhost", "127.0.0.1")
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if health:
        @app.get("/api/health")
        def get_health() -> dict[str, str]:  # pragma: no cover - trivial
            return health_payload()

    @app.get("/api/levels")
    def get_levels() -> dict[str, object]:  # pragma: no cover - trivial
        return levels_payload()

    if profiles is not None:
        @app.get("/api/profiles")
        def get_profiles(level: int = Level) -> Any:
            listing = profiles() if callable(profiles) else profiles
            return leveled_all(list(listing), level)

    if simulate is not None:
        @app.get(trace_path, response_model=trace_response_model)
        def get_trace(level: int = Level) -> Any:
            return leveled(simulate(), level)

    return app
