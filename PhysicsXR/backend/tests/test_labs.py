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
from app.models import Scenario, Workload
from app.presets import CELL_SITE, EXPLAINS
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
    def at(cpu: int, accel: int) -> float:
        return _metrics(Scenario(
            config=CELL_SITE, workload=Workload(cpu_pct=cpu, accel_pct=accel),
            duration_s=120,
        ))["workRateW"]

    assert at(0, 0) == 0
    assert 0 < at(50, 0) < at(99, 0) < at(99, 50)


def test_a_tripped_sled_stops_earning_work():
    """Lab 2's start: the full-load cell site trips in the sag at t+300 and
    earns nothing for the second half of the run."""
    m = _metrics(Scenario.model_validate(LABS_BY_ID["ride-the-sag"].start))
    assert m["shutdown"] == 1
    # 205 + 150 W-TDP had it stayed up; it was dark for half the run.
    assert m["workRateW"] < 0.6 * 355
    assert m["sagWorkRateW"] < 355


def test_throttling_accelerators_stop_earning_their_share():
    start = Scenario.model_validate(LABS_BY_ID["dust-and-heat"].start)
    m = _metrics(start)
    assert m["throttleSeconds"] > 0
    # The CPU still earns; the clamped cards do not.
    assert m["workRateW"] < 205 + 30


def test_every_metric_a_lab_names_is_measured():
    m = _metrics(Scenario(duration_s=30))
    for lab in LABS:
        for c in lab.criteria:
            assert c.metric in m, (lab.id, c.id, c.metric)
        assert lab.objective.metric in m


def test_the_lanes_are_separate_is_what_the_dust_lab_turns_on():
    """Lab 1's lesson: the accelerators throttle, in their own air lane, so
    turning the CPU down buys nothing and turning the cards down is the fix."""
    ref = REFERENCE_SOLUTIONS["dust-and-heat"]
    assert grade_scenario("dust-and-heat", ref).passed
    cpu_down = ref.model_copy(update={
        "workload": ref.workload.model_copy(update={"cpu_pct": 0, "accel_pct": 100}),
    })
    trace, log, _ = simulate(cpu_down)
    assert any(s.accel_throttling for s in trace)
    assert not any(s.cpu_throttling for s in trace)
    assert "no-throttle" in _failed("dust-and-heat", cpu_down)
    # One notch too greedy on the accelerator dial, and only that line fails.
    greedy = ref.model_copy(update={
        "workload": ref.workload.model_copy(update={"accel_pct": 80}),
    })
    assert _failed("dust-and-heat", greedy) == ["no-throttle"]


def test_a_bigger_supply_does_not_move_the_breaker():
    """Lab 2's lesson: the second supply survives the sag the single 800 W
    unit trips on — and the 7 A line still fails, alone."""
    attempt = GAMING_ATTEMPTS["ride-the-sag"]["second supply, full load"]
    m = _metrics(attempt)
    assert m["shutdown"] == 0
    assert _failed("ride-the-sag", attempt) == ["breaker"]


def test_the_sag_multiplies_current_by_the_voltage_ratio():
    trace, _, _ = simulate(REFERENCE_SOLUTIONS["ride-the-sag"])
    before, during = trace[299], trace[305]
    assert before.input_v_pct == 100 and during.input_v_pct == 65
    ratio = (during.input_current_a / during.ac_power_w) / (
        before.input_current_a / before.ac_power_w
    )
    assert abs(ratio - 1 / 0.65) < 0.02


def test_the_first_two_answers_both_fail_the_worst_afternoon():
    """Lab 3's lesson: dust and heat pin the fans, fan watts are wall watts,
    and the sag multiplies them — so lab 1's load breaks the breaker and
    lab 2's load breaks the accelerators."""
    tries = GAMING_ATTEMPTS["worst-afternoon"]
    assert "breaker" in _failed("worst-afternoon", tries["the dust lab's answer"])
    assert "no-throttle" in _failed("worst-afternoon", tries["the sag lab's answer"])
    # The coupling itself: the fouled, hot run spends far more on fans than
    # the cool cabinet does, at less work.
    cool = _metrics(REFERENCE_SOLUTIONS["ride-the-sag"])
    worst = _metrics(REFERENCE_SOLUTIONS["worst-afternoon"])
    assert worst["meanFanW"] > 3 * cool["meanFanW"]
    assert worst["workRateW"] < cool["workRateW"]


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
    # The start scenario is the naive default, never the answer.
    for x in body:
        ref = REFERENCE_SOLUTIONS[x["id"]].model_dump(by_alias=True)
        assert x["start"]["workload"] != ref["workload"]

    ref = REFERENCE_SOLUTIONS["ride-the-sag"].model_dump(by_alias=True)
    graded = client.post("/api/labs/ride-the-sag/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404
