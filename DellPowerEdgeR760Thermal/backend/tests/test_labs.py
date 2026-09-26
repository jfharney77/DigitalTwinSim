"""Graded labs (docs/LAB_PATTERN.md): the shared invariants plus this app's
own checks — the work metric, the API surface, and the specific physics each
lab's 'aha' depends on staying true."""

from __future__ import annotations

import app.labs as labs_module
import app.presets  # noqa: F401  (registers the Explain prose)
from app.labs import (
    GAMING_ATTEMPTS,
    LABS,
    LABS_BY_ID,
    REFERENCE_SOLUTIONS,
    grade_scenario,
    measure,
)
from app.engine import simulate
from app.leveling import leveled, registry
from app.models import Scenario, Workload
from app.presets import EXPLAINS
from app.validation import validate
from twinkit.labs import PASS_FLOOR, Lab, grade
from twinkit.testing import assert_lab_invariants


def test_lab_invariants():
    assert_lab_invariants(
        LABS,
        grade_scenario,
        REFERENCE_SOLUTIONS,
        explain_ids=[e.id for e in EXPLAINS],
        registry=registry(),
        parse_start=Scenario.model_validate,
        gaming_attempts=GAMING_ATTEMPTS,
        module=labs_module,
    )


def test_there_are_three_labs_of_rising_difficulty():
    assert [lab.difficulty for lab in LABS] == [1, 2, 3]


def test_equations_are_the_explain_entries_verbatim():
    by_id = {e.id: e.equation for e in EXPLAINS}
    for lab in LABS:
        for c in lab.criteria:
            assert c.equation == by_id[c.explain_id], (lab.id, c.id)
        assert lab.objective.equation == by_id[lab.objective.explain_id]


def _metrics(scenario: Scenario) -> dict[str, float]:
    trace, _log, summary = simulate(scenario)
    return measure(scenario, trace, summary, validate(scenario))


def test_work_is_zero_at_idle_and_scales_with_load():
    idle = _metrics(Scenario(workload=Workload(), duration_s=120))
    half = _metrics(Scenario(workload=Workload(cpu_pct=50), duration_s=120))
    full = _metrics(Scenario(workload=Workload(cpu_pct=99), duration_s=120))
    assert idle["workRateW"] == 0
    assert 0 < half["workRateW"] < full["workRateW"]


def test_a_tripped_server_stops_earning_work():
    tripped = GAMING_ATTEMPTS["psu-sweet-spot"]["undersized PSU that trips"]
    m = _metrics(tripped)
    assert m["shutdown"] == 1
    # Two 350 W CPUs at 100% would be 700 W-TDP if the box had stayed up.
    assert m["workRateW"] < 100


def test_every_metric_a_lab_names_is_measured():
    m = _metrics(Scenario(duration_s=30))
    for lab in LABS:
        for c in lab.criteria:
            assert c.metric in m, (lab.id, c.id, c.metric)
        assert lab.objective.metric in m


def test_the_boost_is_what_the_hard_lab_turns_on():
    """Lab 3's lesson: 100% trips the turbo boost and throttles; 99% does not."""
    ref = REFERENCE_SOLUTIONS["lose-a-fan"]
    at_100 = ref.model_copy(update={
        "workload": ref.workload.model_copy(update={"cpu_pct": 100}),
    })
    assert grade_scenario("lose-a-fan", ref).passed
    hot = grade_scenario("lose-a-fan", at_100)
    assert not hot.passed
    assert [c.id for c in hot.criteria if not c.passed] == ["no-throttle"]


def test_score_agrees_with_passed():
    for lab in LABS:
        for scenario in [REFERENCE_SOLUTIONS[lab.id], *GAMING_ATTEMPTS[lab.id].values()]:
            r = grade_scenario(lab.id, scenario)
            assert (r.score >= PASS_FLOOR) == r.passed


def test_grading_a_lab_needs_only_data():
    """The static-hosting contract: a Lab round-tripped through JSON plus a
    metrics dict is everything grade() needs."""
    lab = LABS_BY_ID["psu-sweet-spot"]
    rebuilt = Lab.model_validate(lab.model_dump(by_alias=True))
    m = _metrics(REFERENCE_SOLUTIONS[lab.id])
    assert grade(rebuilt, m).model_dump() == grade(lab, m).model_dump()


def test_lab_prose_is_levelled_end_to_end():
    lab = LABS[0]
    novice, expert = leveled(lab, 1), leveled(lab, 5)
    assert novice.goal.statement != lab.goal.statement != expert.goal.statement
    assert len(novice.hints[0]) > len(expert.hints[0])
    # Numbers do not change with the reading level.
    assert [c.threshold for c in novice.criteria] == [c.threshold for c in lab.criteria]


def test_api_serves_labs_and_grades_without_leaking_solutions():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    listing = client.get("/api/labs?level=1")
    assert listing.status_code == 200
    body = listing.json()
    assert [x["id"] for x in body] == [lab.id for lab in LABS]
    assert "reference" not in listing.text.lower()

    ref = REFERENCE_SOLUTIONS["hot-aisle-lean-wall"].model_dump(by_alias=True)
    graded = client.post("/api/labs/hot-aisle-lean-wall/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404
