"""Graded labs — the models and the pure scoring function the physics apps share.

A guided scenario is watch-mode: the app sets the dials and narrates. A lab is
do-mode: it states a goal and constraints, the learner builds a Scenario with
the app's ordinary controls, the app's pure engine runs it, and a pure scoring
function grades the trace. The recipe for adding labs to an app is
``docs/LAB_PATTERN.md``; the pilot is ``DellPowerEdgeR760Thermal/backend/app/labs.py``.

The split, deliberately the same as engine vs. ``main.py``:

* An app owns **measurement**: ``measure(scenario, trace, ...) -> dict[str, float]``
  turns one run into named numbers (peak CPU temperature, mean wall watts,
  delivered work). It is the only part that knows the app's ``SimState``.
* This module owns **grading**: :func:`grade` compares those numbers with a
  lab's criteria and returns a :class:`LabResult`. It knows nothing about any
  app, imports nothing impure, and carries no FastAPI dependency — a
  static-hosting build can run the same logic in the browser from the same
  data, because a ``Lab`` dumped to JSON *is* the whole grading specification.

Two rules keep a lab honest, and ``twinkit.testing.assert_lab_invariants``
enforces both:

* **Delivered work is always a criterion.** "Hold the CPU under 80 °C" is
  trivially passed by an idle server. Every lab must carry at least one
  criterion flagged ``guards_work`` — a floor on the useful output of the run —
  so the cheap way out is closed by construction.
* **Every constraint is a criterion.** "At 35 °C inlet" is not a locked
  control; it is a measured number (``minInletC >= 35``) graded like any
  other. The grader never trusts the client about what the learner did.

Prose (``why``, hints, the goal) is plain ``str`` registered through the app's
own ``L(...)``, exactly like every other block in the repo; resolution to a
reading level happens at the edge (``main.py``), never here.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from .models import CamelModel

__all__ = [
    "Op",
    "Criterion",
    "Objective",
    "LabGoal",
    "Lab",
    "CriterionResult",
    "ObjectiveResult",
    "LabResult",
    "compare",
    "grade",
    "PASS_FLOOR",
]

Op = Literal["<=", ">=", "==", "<", ">"]

#: A run that meets every criterion scores at least this; the rest of the
#: scale (up to 100) is earned on the lab's objective. A run that misses any
#: criterion scores strictly below it, so "passed" is readable from the score.
PASS_FLOOR = 70

#: Float slack for ``==`` and for the inclusive bounds, so a metric rounded
#: to the instrument's precision does not fail on the last bit.
_EPS = 1e-9


class Criterion(CamelModel):
    """One pass/fail line of a lab: ``metric op threshold``.

    ``explain_id`` and ``equation`` are what make a lab a teaching device
    rather than a quiz: each criterion names the app's Explain entry it tests
    and the equation behind it, so a failed line points at the physics that
    failed it. ``why`` is the leveled sentence shown beside the result.
    """

    id: str
    label: str
    metric: str                # key into the app's measure() dict
    op: Op
    threshold: float
    unit: str = ""
    weight: float = Field(1.0, gt=0)
    guards_work: bool = False  # True on the delivered-work floor(s)
    explain_id: str            # an id from the app's GET /api/explain
    equation: str              # the equation this line tests, as displayed
    why: str                   # leveled prose: why this line passes or fails


class Objective(CamelModel):
    """What separates a pass from a good pass: one metric to push.

    ``par`` is the reference solution's neighbourhood (full marks at or beyond
    it); ``worst`` is where the objective earns nothing. Linear in between.
    Only counted when every criterion passes — optimizing a run that does not
    meet the constraints is optimizing the wrong thing.
    """

    label: str
    metric: str
    direction: Literal["minimize", "maximize"]
    par: float
    worst: float
    unit: str = ""
    explain_id: str
    equation: str


class LabGoal(CamelModel):
    statement: str               # leveled: what to achieve
    constraints: list[str]       # leveled, human-readable; each is ALSO a criterion
    delivered_work: str          # leveled: what counts as work, and the floor


class Lab(CamelModel):
    id: str                      # kebab-case; keys #lab=<id> and localStorage
    title: str
    difficulty: int = Field(ge=1, le=3)
    goal: LabGoal
    criteria: list[Criterion]
    objective: Objective | None = None
    hints: list[str]             # progressive, each leveled (1/3/5 authored)
    #: The scenario the lab page loads, as the app's own Scenario JSON
    #: (camelCase, opaque here). It sets the stage — duration, the room — and
    #: is the "naive default": graded as-is it must FAIL, or the lab is a
    #: button rather than a problem.
    start: dict[str, Any] = Field(default_factory=dict)


class CriterionResult(CamelModel):
    id: str
    label: str
    passed: bool
    measured: float
    op: Op
    threshold: float
    unit: str
    guards_work: bool
    explain_id: str
    equation: str
    why: str


class ObjectiveResult(CamelModel):
    label: str
    measured: float
    par: float
    worst: float
    unit: str
    direction: Literal["minimize", "maximize"]
    fraction: float              # 0..1 of the objective band earned
    explain_id: str
    equation: str


class LabResult(CamelModel):
    lab_id: str
    passed: bool
    score: int                   # 0..100; >= PASS_FLOOR iff passed
    criteria: list[CriterionResult]
    objective: ObjectiveResult | None = None
    metrics: dict[str, float]    # everything measured, for the curious
    verdict: str                 # one plain sentence


def compare(measured: float, op: Op, threshold: float) -> bool:
    if op == "<=":
        return measured <= threshold + _EPS
    if op == ">=":
        return measured >= threshold - _EPS
    if op == "<":
        return measured < threshold
    if op == ">":
        return measured > threshold
    return abs(measured - threshold) <= _EPS


def _objective_fraction(obj: Objective, measured: float) -> float:
    span = obj.worst - obj.par
    if span == 0:
        return 1.0
    # Works for both directions: for "maximize", worst < par and span < 0.
    frac = (obj.worst - measured) / span
    return max(0.0, min(1.0, frac))


def grade(lab: Lab, metrics: dict[str, float]) -> LabResult:
    """Grade one run. Pure: same lab + same metrics → same result, always.

    A metric the lab names but the app did not measure is a programming
    error, not a learner's failure, so it raises ``KeyError`` rather than
    quietly failing the line.
    """
    results: list[CriterionResult] = []
    for c in lab.criteria:
        measured = float(metrics[c.metric])
        results.append(CriterionResult(
            id=c.id, label=c.label, passed=compare(measured, c.op, c.threshold),
            measured=measured, op=c.op, threshold=c.threshold, unit=c.unit,
            guards_work=c.guards_work, explain_id=c.explain_id,
            equation=c.equation, why=c.why,
        ))

    total_w = sum(c.weight for c in lab.criteria)
    passed_w = sum(c.weight for c, r in zip(lab.criteria, results) if r.passed)
    passed = all(r.passed for r in results)

    obj_result: ObjectiveResult | None = None
    frac = 1.0
    if lab.objective is not None:
        o = lab.objective
        measured = float(metrics[o.metric])
        frac = _objective_fraction(o, measured)
        obj_result = ObjectiveResult(
            label=o.label, measured=measured, par=o.par, worst=o.worst,
            unit=o.unit, direction=o.direction, fraction=round(frac, 4),
            explain_id=o.explain_id, equation=o.equation,
        )

    if passed:
        score = PASS_FLOOR + round((100 - PASS_FLOOR) * frac)
    else:
        score = min(PASS_FLOOR - 1, int((PASS_FLOOR - 1) * passed_w / total_w))

    failed = [r.label for r in results if not r.passed]
    if passed:
        verdict = (
            "Every criterion met."
            if obj_result is None or frac >= 1.0
            else f"Every criterion met; {obj_result.label.lower()} can still improve."
        )
    else:
        verdict = "Not yet: " + "; ".join(failed) + "."

    return LabResult(
        lab_id=lab.id, passed=passed, score=score, criteria=results,
        objective=obj_result,
        metrics={k: float(v) for k, v in metrics.items()}, verdict=verdict,
    )
