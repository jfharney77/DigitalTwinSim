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
from app.models import Scenario
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


def _config(scenario: Scenario, **update) -> Scenario:
    return scenario.model_copy(update={
        "config": scenario.config.model_copy(update=update),
    })


def test_work_is_zero_for_an_empty_rack_and_scales_with_load():
    ref = REFERENCE_SOLUTIONS["honest-front-panel"]
    empty = _metrics(GAMING_ATTEMPTS["honest-front-panel"]["zero load"])
    full = _metrics(ref)
    assert empty["workRateW"] == 0
    assert full["workRateW"] == 6900


def test_a_tripped_phase_and_a_dark_rack_stop_earning():
    tripped = _metrics(GAMING_ATTEMPTS["three-feeds-eight-servers"][
        "everything on the convenient outlet"])
    assert tripped["trippedPhases"] == 1
    assert tripped["workRateW"] < 7600 / 2  # 7,600 W if phase A had held
    dark = _metrics(Scenario.model_validate(LABS_BY_ID["honest-front-panel"].start))
    assert dark["darkSeconds"] > 0
    assert dark["workRateW"] < 6000


def test_every_metric_a_lab_names_is_measured():
    m = _metrics(Scenario(duration_s=30))
    for lab in LABS:
        for c in lab.criteria:
            assert c.metric in m, (lab.id, c.id, c.metric)
        assert lab.objective.metric in m
    assert m["firstUtilityFailS"] > 900  # "never failed" must not read as "early"


def test_lab_one_has_no_better_split_than_par():
    """Lab 1's par is the true optimum of the partition, found by brute force
    over the engine's own imbalance figure."""
    import itertools

    from app.labs import LAB_FLEET_W

    best = min(
        max(abs(sum(w for w, q in zip(LAB_FLEET_W, p) if q == ph) - 7600 / 3)
            for ph in "ABC") / (7600 / 3) * 100
        for p in itertools.product("ABC", repeat=8)
    )
    ref = grade_scenario("three-feeds-eight-servers",
                         REFERENCE_SOLUTIONS["three-feeds-eight-servers"])
    assert round(best, 1) == ref.objective.measured == 2.6


def test_the_self_test_is_what_makes_the_panel_honest():
    """Lab 2's lesson: lithium survives, but only a self-test before the
    failure fixes the prediction — and the error is exactly the fade."""
    lab = "honest-front-panel"
    ref = REFERENCE_SOLUTIONS[lab]
    assert grade_scenario(lab, ref).passed
    untested = grade_scenario(lab, GAMING_ATTEMPTS[lab]["lithium but no self-test"])
    assert [c.id for c in untested.criteria if not c.passed] == ["honest-panel"]
    m = untested.metrics
    expected = 100.0 * (100.0 / m["batteryCapacityPct"] - 1.0)
    assert abs(m["predictionErrorPct"] - expected) < 1.0
    vrla = grade_scenario(lab, GAMING_ATTEMPTS[lab]["self-test but still VRLA"])
    assert vrla.metrics["darkSeconds"] > 0
    assert vrla.metrics["predictionErrorPct"] <= 5  # honest, and still dark


def test_overload_is_a_time_budget_in_the_hard_lab():
    """Lab 3's lesson: the doubled phase runs above 100% for the whole surge
    and holds; 150 W more on it, or a third GPU, and the only new failure is
    the trip (and the work it costs)."""
    lab = "surge-on-battery"
    ref = grade_scenario(lab, REFERENCE_SOLUTIONS[lab])
    assert ref.passed and ref.metrics["peakPhasePct"] > 105
    crowded = grade_scenario(
        lab, GAMING_ATTEMPTS[lab]["a little extra on the doubled phase"])
    assert {c.id for c in crowded.criteria if not c.passed} == {"work", "no-trip"}
    greedy = grade_scenario(lab, GAMING_ATTEMPTS[lab]["too greedy"])
    assert [c.id for c in greedy.criteria if not c.passed] == ["never-dark"]


def test_score_agrees_with_passed():
    for lab in LABS:
        for scenario in [REFERENCE_SOLUTIONS[lab.id], *GAMING_ATTEMPTS[lab.id].values()]:
            r = grade_scenario(lab.id, scenario)
            assert (r.score >= PASS_FLOOR) == r.passed


def test_grading_a_lab_needs_only_data():
    """The static-hosting contract: a Lab round-tripped through JSON plus a
    metrics dict is everything grade() needs."""
    lab = LABS_BY_ID["three-feeds-eight-servers"]
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
    assert "AABCBCCB" not in listing.text and "self-test\"" not in listing.text

    ref = REFERENCE_SOLUTIONS["surge-on-battery"].model_dump(by_alias=True)
    graded = client.post("/api/labs/surge-on-battery/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404
