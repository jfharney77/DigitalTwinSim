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
    "assert_trace_invariants",
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
#: (bring-up), hours (data lifecycles) or days (fleet lifecycles), and a few
#: carry none at all.
_ELAPSED_FIELDS = (
    "elapsed_seconds",
    "elapsed_minutes",
    "elapsed_hours",
    "elapsed_days",
    "elapsed_ms",
)


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


def assert_trace_invariants(trace: Sequence[Any], profile: TraceProfile) -> None:
    """Assert the six invariants every trace in this repo has.

    Raises ``AssertionError`` with the offending step named, in the house
    style — the message should tell you which step broke, not merely that one
    did.
    """
    assert trace, "empty trace"

    # 1. Steps are sequential from zero.
    steps = [s.step for s in trace]
    assert steps == list(range(len(trace))), (
        f"steps are not sequential from zero: {steps[:12]}..."
    )

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
                        f"step {state.step}: unknown region {rid!r}"
                    )

    # 5. Every step costs at least one cycle.
    if hasattr(trace[0], "cycle_cost"):
        for state in trace:
            assert state.cycle_cost >= profile.min_cycle_cost, (
                f"step {state.step}: cycle_cost {state.cycle_cost} below "
                f"{profile.min_cycle_cost}"
            )


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
