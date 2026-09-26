"""Graded labs (docs/LAB_PATTERN.md): the shared invariants plus this app's
own checks — the work metric, the API surface, and the specific physics each
lab's 'aha' depends on staying true."""

from __future__ import annotations

import app.labs as labs_module
import app.presets  # noqa: F401  (registers the Explain prose)
from app.engine import simulate
from app.labs import (
    GAMING_ATTEMPTS,
    LABS,
    LABS_BY_ID,
    REFERENCE_SOLUTIONS,
    grade_scenario,
    measure,
)
from app.leveling import leveled, registry
from app.models import Scenario, SimEvent, SystemConfig, Workload
from app.presets import EXPLAINS, XE9680_H100, XE9712_FULL
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


def test_there_are_three_labs_one_per_machine():
    assert [lab.difficulty for lab in LABS] == [1, 2, 3]
    assert [lab.start["config"]["product"] for lab in LABS] == [
        "xe7745", "xe9680", "xe9712",
    ]


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
    half = _metrics(Scenario(workload=Workload(gpu_pct=50), duration_s=120))
    full = _metrics(Scenario(workload=Workload(gpu_pct=100), duration_s=120))
    assert idle["workRateW"] == 0
    assert 0 < half["workRateW"] < full["workRateW"]


def test_a_starved_gpu_earns_only_what_it_was_fed():
    fed = _metrics(Scenario(config=XE9680_H100, workload=Workload(gpu_pct=100), duration_s=120))
    starved = _metrics(Scenario(
        config=XE9680_H100, workload=Workload(gpu_pct=100, data_feed_pct=30),
        duration_s=120,
    ))
    assert abs(starved["workRateW"] - 0.3 * fed["workRateW"]) < 1.0


def test_a_tripped_rack_stops_earning_work():
    tripped = Scenario(
        config=XE9712_FULL.model_copy(update={"shelf_capacity_kw": 66}),
        workload=Workload(gpu_pct=100, cpu_pct=50), duration_s=600,
    )
    m = _metrics(tripped)
    assert m["shutdown"] == 1
    # 72 × 1400 W at 100% would be 100,800 W-TDP had the shelves held.
    assert m["workRateW"] < 10_000


def test_every_metric_a_lab_names_is_measured():
    m = _metrics(Scenario(duration_s=30))
    for lab in LABS:
        for c in lab.criteria:
            assert c.metric in m, (lab.id, c.id, c.metric)
        assert lab.objective.metric in m


def test_constraints_are_measured_from_events_not_trusted_from_dials():
    base = REFERENCE_SOLUTIONS["starved-not-stalled"]
    cheat = base.model_copy(update={
        "events": [SimEvent(at_s=400, action="set-data-feed", value=100)],
    })
    assert _metrics(base)["maxDataFeedPct"] == 60
    assert _metrics(cheat)["maxDataFeedPct"] == 100


def test_the_worst_seat_is_what_lab_one_turns_on():
    """Lab 1's lesson: the full row at 100% fails only on the hot slot's
    lines, and the fix is the dial, not the seating plan."""
    start = Scenario.model_validate(LABS_BY_ID["worst-seat"].start)
    failed = [c.id for c in grade_scenario("worst-seat", start).criteria if not c.passed]
    assert failed == ["no-throttle", "margin"]
    # Unthrottled, the back of the row settles 7 × 1.1 K above the front.
    trace, _log, _s = simulate(REFERENCE_SOLUTIONS["worst-seat"])
    last = trace[-1].region_temps
    assert last["gpu-7"] > last["gpu-0"] + 7


def test_bigger_silicon_opens_the_window_in_lab_two():
    """Lab 2's lesson: on the 700 W board no dial setting meets both the work
    floor and the waste cap; on the 1,000 W board a window exists."""
    def passes(tdp: int, pct: int) -> bool:
        return grade_scenario("starved-not-stalled", Scenario(
            config=SystemConfig(product="xe9680", sxm_gpu_tdp_w=tdp),
            workload=Workload(gpu_pct=pct, cpu_pct=50, data_feed_pct=60),
            duration_s=900,
        )).passed
    assert not any(passes(700, pct) for pct in range(50, 101, 5))
    assert passes(1000, 70)
    assert not passes(1000, 100)


def test_design_flow_is_what_lab_three_turns_on():
    """Lab 3's lesson: the reference's dials on the default 120 L/min loop
    throttle; one more degree of supply does too."""
    ref = REFERENCE_SOLUTIONS["warm-water-pump-down"]
    assert grade_scenario("warm-water-pump-down", ref).passed
    thin = ref.model_copy(update={
        "config": ref.config.model_copy(update={"coolant_flow_lpm": 120}),
    })
    r = grade_scenario("warm-water-pump-down", thin)
    assert not r.passed
    assert "no-throttle" in [c.id for c in r.criteria if not c.passed]
    warmer = ref.model_copy(update={
        "config": ref.config.model_copy(update={"coolant_supply_c": 44}),
    })
    hot = grade_scenario("warm-water-pump-down", warmer)
    assert not hot.passed
    assert "no-throttle" in [c.id for c in hot.criteria if not c.passed]


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

    ref = REFERENCE_SOLUTIONS["starved-not-stalled"].model_dump(by_alias=True)
    graded = client.post("/api/labs/starved-not-stalled/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404
