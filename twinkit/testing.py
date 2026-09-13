"""The trace invariants every component's ``test_engine.py`` restated.

Counted across the components before this module existed: the same six
assertions appeared 23, 23, 23, 23, 19 and 25 times respectively, each written
out locally with its own loop and its own message. They are the interesting
property a simulation trace has — it starts at zero and steps one at a time,
its phases never run backwards, its clock never runs backwards, it only ever
lights regions that exist on the map, and every step costs at least one cycle
— and the engine that produces it is pure.

A component's ``test_engine.py`` now spends four lines on all of that and
keeps its file for what is actually its own: the dual-node symmetry, the
heat balance, the atomic NVLink fuse, the air gap that stays shut.

    from twinkit.testing import TraceProfile, assert_trace_invariants

    PROFILE = TraceProfile(phases=PHASE_ORDER, anatomy=ANATOMY)

    def test_trace_invariants():
        assert_trace_invariants(simulate(), PROFILE)
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

__all__ = [
    "TraceProfile",
    "claim_backend",
    "activate_backend_for",
    "assert_trace_invariants",
    "assert_deterministic",
    "assert_engine_is_pure",
    "IMPURE_MODULES",
]

#: Imports an engine must never carry. The engine is a pure function from a
#: scenario to a list of states; the clock lives in the frontend and the IO
#: lives in ``main.py``. ``random`` is on the list because a trace has to be
#: reproducible to be worth testing at all.
IMPURE_MODULES = frozenset(
    {"fastapi", "time", "asyncio", "threading", "os", "io", "random"}
)

#: The elapsed-clock field a state might carry. Components measure in seconds
#: (bring-up), hours (data lifecycles), days (fleet lifecycles) or months
#: (material lifecycles); the physics apps tick on ``t`` / ``t_h`` / ``t_d`` /
#: ``day``; and a few carry no clock at all.
_ELAPSED_FIELDS = (
    "elapsed_seconds",
    "elapsed_minutes",
    "elapsed_hours",
    "elapsed_days",
    "elapsed_months",
    "elapsed_ms",
    "t",
    "t_h",
    "t_d",
    "day",
)

#: The step-index field: ``step`` on the twins, ``cycle`` on the GPU and
#: Alienware traces. Physics traces carry a clock instead and skip the check.
_STEP_FIELDS = ("step", "cycle")


@dataclass(frozen=True)
class TraceProfile:
    """What a trace should be true of.

    ``phases`` is the phase order in full — the invariant is both that the
    trace never runs backwards through it *and* that every declared phase
    actually appears, because a phase nobody reaches is a phase nobody tested.

    ``anatomy`` is the component's map (anything with a ``.regions`` or
    ``.blocks`` or ``.pillars`` list of id-bearing items); pass it and every
    lit region id is checked to exist. ``region_ids`` is the same check given
    the ids directly.

    ``strict_clock`` turns off the strictly-increasing elapsed-clock check for
    the handful of components whose trace deliberately holds the clock still.
    """

    phases: Sequence[str] | None = None
    anatomy: Any = None
    region_ids: Iterable[str] | None = None
    strict_clock: bool = True
    min_cycle_cost: int = 1
    extra: dict[str, Any] = field(default_factory=dict)

    def known_region_ids(self) -> set[str] | None:
        if self.region_ids is not None:
            return set(self.region_ids)
        if self.anatomy is None:
            return None
        for attr in ("regions", "blocks", "pillars", "areas"):
            items = getattr(self.anatomy, attr, None)
            if items:
                return {item.id for item in items}
        raise AssertionError(
            "TraceProfile.anatomy has no regions/blocks/pillars list to read "
            "ids from; pass region_ids= instead"
        )


def _state_phase(state: Any) -> str | None:
    return getattr(state, "phase", None)


def _where(state: Any) -> Any:
    for name in _STEP_FIELDS + _ELAPSED_FIELDS:
        if hasattr(state, name):
            return getattr(state, name)
    return "?"


def assert_trace_invariants(trace: Sequence[Any], profile: TraceProfile) -> None:
    """Assert the six invariants every trace in this repo has.

    Raises ``AssertionError`` with the offending step named, in the house
    style — the message should tell you which step broke, not merely that one
    did.
    """
    assert trace, "empty trace"

    # 1. Steps are sequential from zero.
    for name in _STEP_FIELDS:
        if hasattr(trace[0], name):
            steps = [getattr(s, name) for s in trace]
            assert steps == list(range(len(trace))), (
                f"{name}s are not sequential from zero: {steps[:12]}..."
            )
            break

    # 2. The phase order never regresses, and every declared phase appears.
    if profile.phases is not None:
        order = list(profile.phases)
        seen = [_state_phase(s) for s in trace]
        unknown = {p for p in seen if p not in order}
        assert not unknown, f"trace has phases not in the declared order: {unknown}"
        indices = [order.index(p) for p in seen]
        for i, (a, b) in enumerate(zip(indices, indices[1:]), start=1):
            assert a <= b, (
                f"step {i}: phase regressed from {seen[i - 1]!r} to {seen[i]!r}"
            )
        missing = set(order) - set(seen)
        assert not missing, f"declared phases never reached: {sorted(missing)}"

    # 3. The clock never runs backwards.
    if profile.strict_clock:
        for name in _ELAPSED_FIELDS:
            if hasattr(trace[0], name):
                elapsed = [getattr(s, name) for s in trace]
                for i, (a, b) in enumerate(zip(elapsed, elapsed[1:]), start=1):
                    assert a < b, (
                        f"step {i}: {name} did not advance ({a} -> {b})"
                    )
                break

    # 4. Every lit region exists on the map.
    known = profile.known_region_ids()
    if known is not None:
        for state in trace:
            for attr in ("active_regions", "active_blocks", "active_pillars"):
                for rid in getattr(state, attr, ()) or ():
                    assert rid in known, (
                        f"step {_where(state)}: unknown region {rid!r}"
                    )

    # 5. Every step costs at least one cycle.
    if hasattr(trace[0], "cycle_cost"):
        for state in trace:
            assert state.cycle_cost >= profile.min_cycle_cost, (
                f"step {_where(state)}: cycle_cost {state.cycle_cost} below "
                f"{profile.min_cycle_cost}"
            )


def assert_deterministic(produce: Any) -> None:
    """Run a simulation twice and require byte-identical output.

    ``produce`` is a zero-argument callable — ``simulate`` itself for the
    twins, ``lambda: simulate(SCENARIO)`` for the scenario-driven apps. Traces
    are compared through ``model_dump`` where the states are pydantic models,
    so a float that differs in the last bit fails.
    """

    def dump(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if isinstance(value, (list, tuple)):
            return [dump(v) for v in value]
        return value

    first, second = dump(produce()), dump(produce())
    assert first == second, "the same input produced two different traces"


def assert_engine_is_pure(module: Any, also_ban: Iterable[str] = ()) -> None:
    """AST-check that an engine module imports nothing impure.

    Reading the source rather than the imported module is deliberate: an
    engine that imports ``time`` only inside a function would still pass a
    ``sys.modules`` check, and would still be able to put a clock in the
    trace.
    """
    banned = IMPURE_MODULES | set(also_ban)
    source = open(module.__file__, encoding="utf-8").read()
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])
    offending = sorted(imported & banned)
    assert not offending, (
        f"{module.__name__} imports {offending} — the engine must stay pure "
        "(the clock lives in the frontend, the IO lives in main.py)"
    )


#: Top-level package names a component backend owns. Every component has an
#: ``app`` package and a ``tests`` package; running them all in one interpreter
#: means taking turns. (Leaving ``tests`` out is silent and wrong: pytest's
#: importlib mode reuses a cached ``tests.test_engine`` and collects the first
#: component's tests again under every later component's path.)
OWNED_PACKAGES = ("app", "tests")


#: backend dir -> the ``app.*``/``tests.*`` modules it imported, while another backend
#: holds the name.
_STASH: dict[str, dict[str, Any]] = {}
_OWNER: list[str | None] = [None]


def _owned(modules: dict[str, Any]) -> list[str]:
    prefixes = tuple(f"{name}." for name in OWNED_PACKAGES)
    return [
        name
        for name in modules
        if name in OWNED_PACKAGES or name.startswith(prefixes)
    ]


def _activate(backend: str) -> None:
    import sys as _sys

    if _OWNER[0] != backend:
        if _OWNER[0] is not None:
            _STASH[_OWNER[0]] = {name: _sys.modules[name] for name in _owned(_sys.modules)}
        for name in _owned(_sys.modules):
            del _sys.modules[name]
        _sys.modules.update(_STASH.get(backend, {}))
        _OWNER[0] = backend
    while backend in _sys.path:
        _sys.path.remove(backend)
    _sys.path.insert(0, backend)


def claim_backend(conftest_file: str) -> None:
    """Make this backend the one whose ``app`` package is importable.

    Called from each ``<component>/backend/conftest.py``, which pytest imports
    before it imports anything under that directory. The previous owner's
    ``app.*`` modules are stashed rather than dropped, so that
    :func:`activate_backend_for` can put them back before that backend's tests
    run — a test that does ``from app.models import X`` inside its body must
    get the same class its module imported at collection, not a fresh copy
    (or, worse, a different component's). This is the only way a root
    ``pytest`` can run 42 components that all spell their package ``app``.

    Running one component from inside its own directory is unaffected: there
    is no previous owner and nothing to stash.
    """
    import pathlib as _pathlib

    _activate(str(_pathlib.Path(conftest_file).resolve().parent))


def activate_backend_for(path: Any) -> None:
    """Before a test runs, give ``app`` back to the backend that owns it.

    Called from the root ``conftest.py``'s ``pytest_runtest_setup``. Paths
    outside every claimed backend (twinkit's own tests) leave things alone.
    """
    import pathlib as _pathlib

    target = str(_pathlib.Path(path).resolve())
    candidates = [
        backend
        for backend in list(_STASH) + ([_OWNER[0]] if _OWNER[0] else [])
        if target == backend or target.startswith(backend + "/")
    ]
    if candidates:
        _activate(max(candidates, key=len))
