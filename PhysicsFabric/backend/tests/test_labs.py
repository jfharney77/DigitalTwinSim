"""Graded labs (docs/LAB_PATTERN.md): the shared invariants plus this app's
own checks — the work metrics, the API surface, and the specific physics each
lab's lesson depends on staying true in the engine."""

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
from app.models import Scenario, SimEvent, Workload
from app.presets import EXPLAINS, SN6000_ADAPTIVE, SN6000_STATIC, X800_FABRIC
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


def _failed(lab_id: str, scenario: Scenario) -> list[str]:
    return [c.id for c in grade_scenario(lab_id, scenario).criteria if not c.passed]


def test_work_is_zero_at_idle_and_scales_with_load():
    def run(gbps: int) -> dict[str, float]:
        return _metrics(Scenario(
            config=SN6000_ADAPTIVE,
            workload=Workload(demand_gbps=gbps, pattern="alltoall", collective_pct=70),
            duration_s=120,
        ))

    idle, half, full = run(0), run(8000), run(16000)
    for key in ("goodputRateGbps", "allreduceRateGbps", "otherGoodputGbps"):
        assert idle[key] == 0
        assert 0 < half[key] < full[key]


def test_congested_demand_stops_earning_work():
    """Offering more than the links carry does not raise goodput: the excess
    is dropped, paused or stalled, and none of it counts."""
    wl = Workload(demand_gbps=60000, pattern="elephant")
    m = _metrics(Scenario(config=SN6000_STATIC, workload=wl, duration_s=120))
    assert m["goodputRateGbps"] < 0.5 * 60000
    assert m["damageSeconds"] > 0


def test_every_metric_a_lab_names_is_measured():
    m = _metrics(Scenario(duration_s=30))
    for lab in LABS:
        for c in lab.criteria:
            assert c.metric in m, (lab.id, c.id, c.metric)
        assert lab.objective.metric in m


def test_a_never_event_cannot_pass_an_early_deadline():
    m = _metrics(Scenario(duration_s=30))
    assert m["firstSpineLossS"] > 100 and m["firstGrayS"] > 100
    # A one-spine fabric cannot lose its spine, so it reads as never failed.
    one = Scenario(
        config=SN6000_ADAPTIVE.model_copy(update={"spines": 1}),
        events=[SimEvent(at_s=5, action="kill-spine")], duration_s=30,
    )
    assert _metrics(one)["spineDownSeconds"] == 0


def test_lab_one_turns_on_adaptive_routing_and_cpo_together():
    """Lab 1's lesson: the budget rules out buying spines, and each of the two
    free levers alone fails on exactly the line the other one fixes."""
    lab = "elephants-on-a-budget"
    ref = REFERENCE_SOLUTIONS[lab]
    no_ar = ref.model_copy(update={
        "config": ref.config.model_copy(update={"adaptive_routing": False})})
    no_cpo = ref.model_copy(update={
        "config": ref.config.model_copy(update={"cpo_optics": False})})
    assert "below-knee" in _failed(lab, no_ar)
    assert "power-budget" not in _failed(lab, no_ar)
    assert _failed(lab, no_cpo) == ["power-budget"]
    assert _failed(lab, GAMING_ATTEMPTS[lab]["brute-force spines"]) == ["power-budget"]


def test_lab_two_is_sized_on_the_survivors():
    """Lab 2's lesson: 1:1 as built is not 1:1 after the loss, and the grader
    recomputes the ratio on the surviving spines."""
    lab = "non-blocking-minus-one"
    ref = REFERENCE_SOLUTIONS[lab]
    assert _metrics(ref)["worstOversubRatio"] == 1.0
    bought = GAMING_ATTEMPTS[lab]["sized for the spines you bought"]
    trace, _log, _summary = simulate(bought)
    assert trace[0].oversub_ratio <= 1.0              # looks fine on the gauge
    assert "non-blocking" in _failed(lab, bought)      # is not, on the survivors
    assert _metrics(bought)["worstOversubRatio"] > 1.0


def test_lab_three_needs_sharp_and_headroom_for_the_gray_tax():
    """Lab 3's lesson: offering exactly the target passes without the gray
    failure and fails with it, status green throughout; SHARP is what makes
    the target reachable on twelve switches."""
    lab = "collectives-past-a-liar"
    exact = GAMING_ATTEMPTS[lab]["offer exactly the target"]
    clean = _metrics(exact.model_copy(update={"events": []}))
    taxed = _metrics(exact)
    assert clean["allreduceRateGbps"] >= 25000 > taxed["allreduceRateGbps"]
    trace, _log, _summary = simulate(exact)
    assert all(s.status_all_green for s in trace)
    assert "allreduce" in _failed(lab, GAMING_ATTEMPTS[lab]["infiniband without SHARP"])
    headroom = exact.model_copy(update={
        "workload": exact.workload.model_copy(update={"demand_gbps": 23500})})
    assert exact.config == X800_FABRIC and grade_scenario(lab, headroom).passed


def test_score_agrees_with_passed():
    for lab in LABS:
        for scenario in [REFERENCE_SOLUTIONS[lab.id], *GAMING_ATTEMPTS[lab.id].values()]:
            r = grade_scenario(lab.id, scenario)
            assert (r.score >= PASS_FLOOR) == r.passed


def test_grading_a_lab_needs_only_data():
    """The static-hosting contract: a Lab round-tripped through JSON plus a
    metrics dict is everything grade() needs."""
    for lab in LABS:
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

    ref = REFERENCE_SOLUTIONS["non-blocking-minus-one"].model_dump(by_alias=True)
    graded = client.post("/api/labs/non-blocking-minus-one/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404


def test_the_static_dispatcher_grades_like_the_api():
    """Static hosting runs the routes through twinkit.static_dispatch in the
    browser; it must answer the grade route exactly as FastAPI does."""
    from fastapi.testclient import TestClient

    from app.main import app
    from twinkit.static_dispatch import dispatch

    lab_id = LABS[0].id
    body = REFERENCE_SOLUTIONS[lab_id].model_dump(by_alias=True)
    status, payload = dispatch(
        app, "POST", f"/api/labs/{lab_id}/grade", {"level": "1"}, body)
    native = TestClient(app).post(f"/api/labs/{lab_id}/grade?level=1", json=body)
    assert status == 200 and payload == native.json()
    assert LABS_BY_ID[lab_id].title
