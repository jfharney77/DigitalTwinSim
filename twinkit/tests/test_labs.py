"""twinkit.labs.grade — pure, deterministic, and importable without FastAPI."""

from __future__ import annotations

import ast
import pathlib

import twinkit.labs as labs_mod
from twinkit.labs import PASS_FLOOR, Criterion, Lab, LabGoal, Objective, grade


def _lab(objective: Objective | None = None) -> Lab:
    def c(id, metric, op, threshold, **kw):
        return Criterion(id=id, label=id, metric=metric, op=op, threshold=threshold,
                         explain_id="e", equation="y = x", why="because", **kw)
    return Lab(
        id="toy", title="Toy", difficulty=1,
        goal=LabGoal(statement="s", constraints=["c"], delivered_work="w"),
        criteria=[c("work", "work", ">=", 10, guards_work=True, weight=2),
                  c("temp", "temp", "<=", 90)],
        objective=objective, hints=["a", "b"], start={},
    )


def test_pass_and_fail_split_at_the_floor():
    lab = _lab()
    assert grade(lab, {"work": 10, "temp": 90}).score == 100
    r = grade(lab, {"work": 0, "temp": 50})
    assert not r.passed and r.score < PASS_FLOOR
    assert [c.passed for c in r.criteria] == [False, True]
    assert r.verdict.startswith("Not yet")


def test_objective_scales_a_pass_in_both_directions():
    low = _lab(Objective(label="Watts", metric="w", direction="minimize", par=100,
                         worst=200, explain_id="e", equation="y"))
    ok = {"work": 10, "temp": 80}
    assert grade(low, {**ok, "w": 100}).score == 100
    assert grade(low, {**ok, "w": 150}).score == PASS_FLOOR + 15
    assert grade(low, {**ok, "w": 500}).score == PASS_FLOOR
    high = _lab(Objective(label="Eff", metric="w", direction="maximize", par=96,
                          worst=94, explain_id="e", equation="y"))
    assert grade(high, {**ok, "w": 97}).score == 100
    assert grade(high, {**ok, "w": 95}).score == PASS_FLOOR + 15
    # The objective never rescues a failed run.
    assert grade(high, {"work": 0, "temp": 80, "w": 99}).score < PASS_FLOOR


def test_grade_is_deterministic_and_survives_a_json_round_trip():
    lab = _lab()
    m = {"work": 12.5, "temp": 88.0}
    rebuilt = Lab.model_validate_json(lab.model_dump_json(by_alias=True))
    assert grade(lab, m).model_dump() == grade(rebuilt, m).model_dump()


def test_wire_format_is_camel_case():
    dumped = _lab().model_dump(by_alias=True)
    assert "deliveredWork" in dumped["goal"]
    assert {"guardsWork", "explainId"} <= set(dumped["criteria"][0])


def test_module_is_pure_and_fastapi_free():
    tree = ast.parse(pathlib.Path(labs_mod.__file__).read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    assert not roots & {"fastapi", "time", "random", "os", "io", "asyncio"}
