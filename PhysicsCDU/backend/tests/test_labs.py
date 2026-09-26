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
from app.models import Scenario, SimEvent, Workload
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


def _failed(lab_id: str, scenario: Scenario) -> list[str]:
    return [c.id for c in grade_scenario(lab_id, scenario).criteria if not c.passed]


def test_work_is_zero_at_idle_and_scales_with_load():
    idle = _metrics(Scenario(workload=Workload(util_pct=0), duration_s=120))
    half = _metrics(Scenario(workload=Workload(util_pct=50), duration_s=120))
    full = _metrics(Scenario(workload=Workload(util_pct=100), duration_s=120))
    assert idle["workRateKw"] == 0
    assert 0 < half["workRateKw"] < full["workRateKw"]
    # Five banks × 40 kW, uncapped.
    assert full["workRateKw"] == 200


def test_work_replays_the_utilization_events():
    late = _metrics(Scenario(
        workload=Workload(util_pct=0), duration_s=100,
        events=[SimEvent(at_s=51, action="set-util", value=100)],
    ))
    # 50 of 101 ticks at 200 kW-compute.
    assert late["workRateKw"] == round(200 * 50 / 101, 1)


def test_a_tripped_bank_stops_earning_work():
    m = _metrics(Scenario.model_validate(LABS_BY_ID["ride-the-chiller-trip"].start))
    assert m["trips"] >= 2
    # Six banks at 100% would be 240 kW-compute had they stayed up.
    assert m["workRateKw"] < 160


def test_every_metric_a_lab_names_is_measured():
    m = _metrics(Scenario(duration_s=30))
    for lab in LABS:
        for c in lab.criteria:
            assert c.metric in m, (lab.id, c.id, c.metric)
        assert lab.objective.metric in m


def test_lab_one_turns_on_flow_and_the_cube_law():
    """Max flow passes but earns nothing on the objective; the lean setpoint
    earns it all; one notch leaner leaves the silicon over target."""
    ref = REFERENCE_SOLUTIONS["full-rack-lean-pumps"]

    def at(flow: int) -> Scenario:
        return ref.model_copy(update={
            "config": ref.config.model_copy(update={"flow_setpoint_lpm": flow}),
        })

    greedy = grade_scenario("full-rack-lean-pumps", at(400))
    assert greedy.passed and greedy.score == PASS_FLOOR
    assert grade_scenario("full-rack-lean-pumps", ref).score >= 97
    assert _failed("full-rack-lean-pumps", at(350)) == ["chip-ceiling"]


def test_lab_two_turns_on_coordination_beating_a_static_derate():
    """The IRC's argument: capping only while the water is warm delivers more
    than any fixed derate, with or without the controller."""
    attempts = GAMING_ATTEMPTS["ride-the-chiller-trip"]
    ref_work = _metrics(REFERENCE_SOLUTIONS["ride-the-chiller-trip"])["workRateKw"]
    for name in ("static derate, controller off", "static derate, controller on"):
        m = _metrics(attempts[name])
        assert m["trips"] == 0, name
        assert m["workRateKw"] < ref_work, name
        assert "work" in _failed("ride-the-chiller-trip", attempts[name]), name
    # Coordination alone is not enough: the default flow makes the cap cut deep.
    assert "work" in _failed(
        "ride-the-chiller-trip", attempts["coordinated at the default flow"])


def test_lab_three_turns_on_the_spare_pump_and_the_cube_law():
    attempts = GAMING_ATTEMPTS["pump-down-warm-day"]
    # One survivor cannot carry the floor on 23 °C water, however it is sized.
    assert "work" in _failed("pump-down-warm-day",
                             attempts["no spare, sized to the survivor"])
    # Two survivors at the default setpoint run flat out: the only thing
    # wrong with that run is what the pumps cost (and the heat that rides
    # with the extra load it was sized for).
    assert "pump-budget" in _failed("pump-down-warm-day",
                                    attempts["ignore the pump budget"])
    # Spreading the load wins: six gentle banks out-deliver five hard ones
    # at the same flow, and four cannot reach the floor.
    ref = REFERENCE_SOLUTIONS["pump-down-warm-day"]
    six = _metrics(ref)["workRateKw"]

    def best(banks: int) -> float:
        top = 0.0
        for util in range(60, 101):
            sc = ref.model_copy(update={
                "config": ref.config.model_copy(update={"tray_groups": banks}),
                "workload": Workload(util_pct=util),
            })
            r = grade_scenario("pump-down-warm-day", sc)
            if not [c for c in r.criteria if not c.passed and c.id != "work"]:
                top = max(top, r.metrics["workRateKw"])
        return top

    assert six > best(5) > best(4)
    assert best(4) < 165


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
    for lab in LABS:
        novice, expert = leveled(lab, 1), leveled(lab, 5)
        assert novice.goal.statement != lab.goal.statement != expert.goal.statement
        assert len(novice.hints[0]) > len(expert.hints[0])
        # Numbers do not change with the reading level.
        assert [c.threshold for c in novice.criteria] == [c.threshold for c in lab.criteria]


def test_grading_works_through_the_static_dispatcher():
    """The hosted site grades in the browser: Pyodide calls this dispatcher
    with the same path, query and body the dev server would receive."""
    from twinkit.static_dispatch import dispatch

    from app.main import app

    ref = REFERENCE_SOLUTIONS["full-rack-lean-pumps"]
    status, out = dispatch(app, "POST", "/api/labs/full-rack-lean-pumps/grade",
                           {"level": "1"}, ref.model_dump(by_alias=True))
    assert status == 200 and out["passed"] and out["score"] >= PASS_FLOOR
    status, _ = dispatch(app, "POST", "/api/labs/nope/grade", {},
                         ref.model_dump(by_alias=True))
    assert status == 404
    status, listing = dispatch(app, "GET", "/api/labs", {"level": "5"})
    assert status == 200 and [x["id"] for x in listing] == [lab.id for lab in LABS]


def test_api_serves_labs_and_grades_without_leaking_solutions():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    listing = client.get("/api/labs?level=1")
    assert listing.status_code == 200
    body = listing.json()
    assert [x["id"] for x in body] == [lab.id for lab in LABS]
    assert "reference" not in listing.text.lower()
    # The start is the naive default, never the answer.
    for served, lab in zip(body, LABS):
        ref = REFERENCE_SOLUTIONS[lab.id].model_dump(by_alias=True)
        assert served["start"] != ref

    ref = REFERENCE_SOLUTIONS["ride-the-chiller-trip"].model_dump(by_alias=True)
    graded = client.post("/api/labs/ride-the-chiller-trip/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404
