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
    "assert_tour_invariants",
    "TOUR_MIN_MS",
    "TOUR_MAX_MS",
    "assert_lab_invariants",
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


# --- tour mode ---------------------------------------------------------------

#: A tour lands between two and six minutes (ACTIVE_TWIN_SPEC.md section 6):
#: shorter is a slideshow, longer is a lecture nobody finishes.
TOUR_MIN_MS = 2 * 60 * 1000
TOUR_MAX_MS = 6 * 60 * 1000


def assert_tour_invariants(
    tour: Any,
    anatomy: Any,
    trace: Sequence[Any],
    signature_step_id: str,
    *,
    module: Any = None,
    layers: dict[str, int] | None = None,
    public_dir: Any = None,
    max_travel: float | None = None,
) -> None:
    """Assert the tour-mode invariants of ACTIVE_TWIN_SPEC.md section 6.

    ``tour`` is a :class:`twinkit.tour.Tour` or a
    :class:`twinkit.tour.TourResponse` (whose ``layers`` are then checked to
    cover the map). ``anatomy`` is the component's map, ``trace`` the engine's
    full trace, and ``signature_step_id`` the step the product's one idea lives
    in — a tour without it fails.

    Optional: ``module`` — the component's ``app.tour`` module, AST-checked for
    purity exactly like an engine; ``layers`` — the region-to-layer mapping when
    ``tour`` is a bare ``Tour``; ``public_dir`` — the frontend's ``public/``
    directory, so every photo URL must name a file that actually ships;
    ``max_travel`` — the camera-travel bound between steps whose boxes do not
    overlap (default ``(W + H) / 2``, in map units).
    """
    import pathlib as _pathlib

    from .tour import boxes_overlap, camera_travel, region_boxes

    if hasattr(tour, "tour") and hasattr(tour, "layers"):
        layers = tour.layers if layers is None else layers
        tour = tour.tour
    steps = list(tour.steps)
    assert steps, "tour has no steps"

    known = set(region_boxes(anatomy))
    W, H = float(anatomy.width), float(anatomy.height)
    bound = max_travel if max_travel is not None else (W + H) / 2

    # Ids are unique and kebab-case — they key deep links and audio files.
    ids = [s.id for s in steps]
    assert len(ids) == len(set(ids)), f"duplicate step ids: {ids}"
    for sid in ids:
        assert sid and sid == sid.lower() and " " not in sid and "_" not in sid, (
            f"step id {sid!r} is not kebab-case"
        )
    assert signature_step_id in ids, (
        f"signature step {signature_step_id!r} missing — the tour cannot ship "
        "without the product's one idea"
    )

    # Scripts and titles are non-empty; the script *is* the content.
    for s in steps:
        assert s.title.strip(), f"step {s.id}: empty title"
        assert s.script.strip(), f"step {s.id}: empty script"

    # Every lit region resolves.
    for s in steps:
        for rid in s.region_ids:
            assert rid in known, f"step {s.id}: unknown region {rid!r}"

    # Camera boxes: positive area, inside the map.
    eps = 1e-6
    for s in steps:
        c = s.camera
        assert c.w > 0 and c.h > 0, f"step {s.id}: camera has no area"
        assert c.x >= -eps and c.y >= -eps, f"step {s.id}: camera starts off the map"
        assert c.x + c.w <= W + eps and c.y + c.h <= H + eps, (
            f"step {s.id}: camera {c} runs past the map ({W} x {H})"
        )

    # No teleporting: consecutive boxes overlap, or the move is bounded.
    for a, b in zip(steps, steps[1:]):
        if not boxes_overlap(a.camera, b.camera):
            travel = camera_travel(a.camera, b.camera)
            assert travel <= bound, (
                f"camera jumps {travel:.1f} units from {a.id} to {b.id} "
                f"(bound {bound:.1f}) with no overlap"
            )

    # Layers peel inward; at most one decrease, and only into the final step.
    reveals = [s.layer_reveal for s in steps]
    for i, (a, b) in enumerate(zip(reveals, reveals[1:]), start=1):
        if b < a:
            assert i == len(steps) - 1, (
                f"layer_reveal falls at {steps[i].id} ({a} -> {b}); only the "
                "final reassemble step may close the product back up"
            )
    assert all(r >= 0 for r in reveals), "negative layer_reveal"

    # Layer map covers the whole map and nothing else.
    if layers is not None:
        assert set(layers) == known, (
            f"layers do not match the map: missing {sorted(known - set(layers))}, "
            f"extra {sorted(set(layers) - known)}"
        )
        deepest = max(layers.values())
        assert max(reveals) <= deepest, (
            f"a step reveals layer {max(reveals)} but the deepest layer is {deepest}"
        )

    # Trace cursor: valid, and the tour never runs the simulation backwards.
    cursors = [s.trace_cursor for s in steps if s.trace_cursor is not None]
    for s in steps:
        if s.trace_cursor is not None:
            assert 0 <= s.trace_cursor < len(trace), (
                f"step {s.id}: trace_cursor {s.trace_cursor} outside 0..{len(trace) - 1}"
            )
    for a, b in zip(cursors, cursors[1:]):
        assert a <= b, f"trace_cursor runs backwards ({a} -> {b})"

    # Duration: every step positive, the whole tour 2-6 minutes.
    for s in steps:
        assert s.duration_ms > 0, f"step {s.id}: non-positive duration"
    total = sum(s.duration_ms for s in steps)
    assert TOUR_MIN_MS <= total <= TOUR_MAX_MS, (
        f"tour runs {total / 1000:.0f} s; it must land in 120-360 s"
    )

    # Photos resolve, are local, and are credited.
    photos = {p.id: p for p in getattr(tour, "photos", [])}
    for p in photos.values():
        assert p.credit.strip(), f"photo {p.id}: missing credit"
        assert p.url.startswith("/") and "//" not in p.url, (
            f"photo {p.id}: {p.url!r} is not a local file — no hotlinking"
        )
        if public_dir is not None:
            path = _pathlib.Path(public_dir) / p.url.lstrip("/")
            assert path.is_file(), f"photo {p.id}: {path} does not exist"
    for s in steps:
        if s.photo_id is not None:
            assert s.photo_id in photos, f"step {s.id}: unknown photo {s.photo_id!r}"

    if module is not None:
        assert_engine_is_pure(module)


# --- graded labs ---------------------------------------------------------------

#: The reading levels a lab's prose must be authored at (3 is the standard text).
LAB_AUTHORED_LEVELS = (1, 3, 5)


def assert_lab_invariants(
    labs: Sequence[Any],
    grade: Any,
    reference_solutions: dict[str, Any],
    *,
    explain_ids: Iterable[str],
    registry: dict[str, dict[int, str]],
    parse_start: Any,
    gaming_attempts: dict[str, dict[str, Any]] | None = None,
    module: Any = None,
) -> None:
    """Assert the graded-lab invariants of ``docs/LAB_PATTERN.md``.

    ``labs`` is the app's ``list[twinkit.labs.Lab]``; ``grade`` is its pure
    ``grade_scenario(lab_id, scenario) -> LabResult``; ``reference_solutions``
    maps every lab id to a scenario that passes it. ``explain_ids`` are the ids
    the app's Explain entries carry; ``registry`` is the app's leveling
    registry (``app.leveling.registry()``); ``parse_start`` turns a lab's
    ``start`` JSON back into the app's Scenario (usually
    ``Scenario.model_validate``). Optional: ``gaming_attempts`` — per lab, named
    scenarios that must NOT pass (zero load is mandatory when given);
    ``module`` — the app's ``labs`` module, AST-checked for purity like an
    engine.

    What it pins:

    * ids unique and kebab-case; difficulty never falls through the list;
    * every lab has a delivered-work criterion (``guards_work``) — a lab a
      powered-down or idle system could pass is not a lab;
    * every criterion and objective cites a real Explain entry and carries the
      equation it tests;
    * the reference solution passes and the lab's own ``start`` scenario — the
      naive default — fails; the score agrees with ``passed`` either way;
    * grading is deterministic (two calls, identical dumps) and pure;
    * hints exist, and hints, goal prose and every ``why`` are authored at
      levels 1, 3 and 5;
    * every named gaming attempt fails.
    """
    from .labs import PASS_FLOOR

    labs = list(labs)
    assert labs, "no labs"
    known_explains = set(explain_ids)

    ids = [lab.id for lab in labs]
    assert len(ids) == len(set(ids)), f"duplicate lab ids: {ids}"
    for lid in ids:
        assert lid and lid == lid.lower() and " " not in lid and "_" not in lid, (
            f"lab id {lid!r} is not kebab-case"
        )
    difficulties = [lab.difficulty for lab in labs]
    assert difficulties == sorted(difficulties), (
        f"labs are not in rising difficulty: {difficulties}"
    )
    assert set(reference_solutions) == set(ids), (
        "every lab needs a reference solution: "
        f"missing {sorted(set(ids) - set(reference_solutions))}, "
        f"extra {sorted(set(reference_solutions) - set(ids))}"
    )

    def _levelled(text: str, where: str) -> None:
        assert text.strip(), f"{where}: empty prose"
        variants = registry.get(text)
        assert variants is not None, f"{where}: prose is not registered with L(...)"
        missing = [lv for lv in LAB_AUTHORED_LEVELS if lv not in variants]
        assert not missing, f"{where}: no variant at level(s) {missing}"

    for lab in labs:
        where = f"lab {lab.id}"
        assert lab.title.strip(), f"{where}: empty title"

        # Criteria: unique ids, a work floor, and a citation on every line.
        cids = [c.id for c in lab.criteria]
        assert cids, f"{where}: no criteria"
        assert len(cids) == len(set(cids)), f"{where}: duplicate criterion ids"
        assert any(c.guards_work for c in lab.criteria), (
            f"{where}: no delivered-work criterion — an idle system would pass"
        )
        for c in lab.criteria:
            assert c.explain_id in known_explains, (
                f"{where}/{c.id}: explain id {c.explain_id!r} is not an Explain entry"
            )
            assert c.equation.strip(), f"{where}/{c.id}: no equation cited"
            _levelled(c.why, f"{where}/{c.id}.why")
        if lab.objective is not None:
            o = lab.objective
            assert o.explain_id in known_explains, (
                f"{where}: objective cites unknown explain id {o.explain_id!r}"
            )
            assert o.equation.strip(), f"{where}: objective cites no equation"
            assert o.par != o.worst, f"{where}: objective par equals worst"
            assert (o.par < o.worst) == (o.direction == "minimize"), (
                f"{where}: objective par/worst are on the wrong sides for {o.direction}"
            )

        # Prose at levels 1/3/5.
        _levelled(lab.goal.statement, f"{where}.goal.statement")
        _levelled(lab.goal.delivered_work, f"{where}.goal.deliveredWork")
        assert lab.goal.constraints, f"{where}: no constraints listed"
        for i, text in enumerate(lab.goal.constraints):
            _levelled(text, f"{where}.goal.constraints[{i}]")
        assert len(lab.hints) >= 2, f"{where}: progressive hints need at least two"
        assert len(set(lab.hints)) == len(lab.hints), f"{where}: duplicate hints"
        for i, text in enumerate(lab.hints):
            _levelled(text, f"{where}.hints[{i}]")

        # The reference passes; the score says so.
        ref = grade(lab.id, reference_solutions[lab.id])
        assert ref.passed, (
            f"{where}: reference solution fails — "
            f"{[c.id for c in ref.criteria if not c.passed]}"
        )
        assert PASS_FLOOR <= ref.score <= 100, f"{where}: reference scored {ref.score}"
        assert [c.id for c in ref.criteria] == cids, f"{where}: result lines drifted"
        if lab.objective is not None:
            assert ref.objective is not None and ref.objective.fraction >= 0.9, (
                f"{where}: the reference earns only "
                f"{ref.objective.fraction if ref.objective else 0:.2f} of the "
                "objective — par is out of reach"
            )

        # The naive default — the scenario the lab page opens with — fails.
        assert lab.start, f"{where}: no start scenario"
        naive = grade(lab.id, parse_start(lab.start))
        assert not naive.passed, f"{where}: the start scenario already passes"
        assert 0 <= naive.score < PASS_FLOOR, f"{where}: naive run scored {naive.score}"

        # Deterministic: the same scenario earns the same result, byte for byte.
        again = grade(lab.id, reference_solutions[lab.id])
        assert again.model_dump() == ref.model_dump(), f"{where}: grading is not deterministic"

        # The cheap ways out are closed.
        if gaming_attempts is not None:
            attempts = gaming_attempts.get(lab.id, {})
            assert any("zero" in name or "idle" in name for name in attempts), (
                f"{where}: no zero-load gaming attempt is tested"
            )
            for name, scenario in attempts.items():
                result = grade(lab.id, scenario)
                assert not result.passed, f"{where}: gamed by {name!r} (score {result.score})"
                assert result.score < PASS_FLOOR

    if module is not None:
        assert_engine_is_pure(module)
