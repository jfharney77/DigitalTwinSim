"""twinkit — the skeleton every DigitalTwinSim component shares.

The repo is forty-two components that are each a pure-engine FastAPI backend
plus a React/Vite frontend. Before this package, the parts of that skeleton
which are genuinely identical — the camelCase model base, the reading-level
mechanism, the ``/api/health`` and ``/api/levels`` routes, the CORS block, and
the six trace invariants every engine test restated — existed once per
component. A fix went into three of them and drifted in the other thirty-nine.

Adding a component is now a directory with an engine, a profile list, and a
``main.py`` that calls :func:`twinkit.api.make_app`.

    twinkit.models    CamelModel, camel()
    twinkit.leveling  L(), leveled(), leveled_all(), resolve()
    twinkit.api       make_app(), Level
    twinkit.testing   TraceProfile, assert_trace_invariants(), assert_engine_is_pure()

``twinkit.testing`` is importable without FastAPI installed, so it stays cheap
for the pure-engine tests.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .leveling import (  # noqa: F401
    DEFAULT_LEVEL,
    LEVEL_NAMES,
    LEVELS,
    L,
    LevelingConflict,
    coverage,
    leveled,
    leveled_all,
    registry,
    resolve,
    variant_for,
)
from .models import CamelModel, camel  # noqa: F401

__all__ = [
    "CamelModel",
    "camel",
    "L",
    "LEVELS",
    "LEVEL_NAMES",
    "DEFAULT_LEVEL",
    "LevelingConflict",
    "leveled",
    "leveled_all",
    "resolve",
    "variant_for",
    "registry",
    "coverage",
]
