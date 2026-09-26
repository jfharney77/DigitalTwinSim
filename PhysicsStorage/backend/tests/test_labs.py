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
from app.models import Scenario, SimEvent
from app.presets import EXPLAINS, OLTP, POWERSTORE_2
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


def _oltp(k: int):
    return OLTP.model_copy(update={"iops_demand_k": k})


def test_work_is_zero_at_idle_and_scales_with_load():
    idle = _metrics(Scenario(config=POWERSTORE_2, workload=_oltp(0), duration_h=24))
    half = _metrics(Scenario(config=POWERSTORE_2, workload=_oltp(200), duration_h=24))
    full = _metrics(Scenario(config=POWERSTORE_2, workload=_oltp(400), duration_h=24))
    assert idle["workIopsK"] == 0 and idle["minDeliveredIopsK"] == 0
    assert 0 < half["workIopsK"] < full["workIopsK"]


def test_work_cannot_exceed_the_ceiling():
    """Cranking demand past capacity buys nothing: delivered clamps."""
    over = _metrics(Scenario(config=POWERSTORE_2, workload=_oltp(4000), duration_h=24))
    assert over["workIopsK"] == 800


def test_an_array_that_lost_data_stops_earning_work():
    lost = Scenario.model_validate(LABS_BY_ID["win-the-rebuild-race"].start)
    m = _metrics(lost)
    assert m["dataSurvived"] == 0
    assert m["minDeliveredIopsK"] == 0
    # 160k for 30 of 73 hours, nothing after.
    assert m["workIopsK"] < 80


def test_every_metric_a_lab_names_is_measured():
    m = _metrics(Scenario(duration_h=6))
    for lab in LABS:
        for c in lab.criteria:
            assert c.metric in m, (lab.id, c.id, c.metric)
        assert lab.objective.metric in m


def test_lab_one_turns_on_the_burst_landing_on_the_survivor():
    """Four appliances at 280k pass; at 300k the ONLY failing line is the knee,
    and it fails in the burst on the halved ceiling (82.5%), not before."""
    ref = REFERENCE_SOLUTIONS["size-for-the-survivor"]
    assert grade_scenario("size-for-the-survivor", ref).passed
    greedy = ref.model_copy(update={"workload": _oltp(300)})
    out = grade_scenario("size-for-the-survivor", greedy)
    assert [c.id for c in out.criteria if not c.passed] == ["below-knee"]
    trace, _, _ = simulate(greedy)
    assert trace[23].utilization_pct < 20 and trace[25].utilization_pct < 40
    assert trace[50].utilization_pct == 82.5


def test_lab_two_turns_on_sync_being_infeasible_and_async_being_a_pipe():
    ref = REFERENCE_SOLUTIONS["burst-fits-the-pipe"]
    assert grade_scenario("burst-fits-the-pipe", ref).passed
    # Sync at the reference demand fails on latency alone: physics, not sizing.
    sync = ref.model_copy(update={
        "config": ref.config.model_copy(update={"srdf": "sync", "units": 8})})
    out = grade_scenario("burst-fits-the-pipe", sync)
    assert [c.id for c in out.criteria if not c.passed] == ["p99"]
    # Async one slider step higher fails on RPO alone.
    hot = ref.model_copy(update={"workload": _oltp(380)})
    out = grade_scenario("burst-fits-the-pipe", hot)
    assert [c.id for c in out.criteria if not c.passed] == ["rpo"]


def test_lab_three_turns_on_the_inversion():
    """Same raw capacity, different shape: thin nodes win the race, fat nodes
    lose the data. Brute force (sixty fat nodes) survives but earns no
    objective marks."""
    ref = REFERENCE_SOLUTIONS["win-the-rebuild-race"]
    good = grade_scenario("win-the-rebuild-race", ref)
    assert good.passed and good.metrics["rebuildHours"] <= 7
    start = Scenario.model_validate(LABS_BY_ID["win-the-rebuild-race"].start)
    assert start.config.units * start.config.drives_per_unit * start.config.drive_tb \
        > ref.config.units * ref.config.drives_per_unit * ref.config.drive_tb
    assert not grade_scenario("win-the-rebuild-race", start).metrics["dataSurvived"]
    brute = start.model_copy(update={
        "config": start.config.model_copy(update={"units": 60})})
    out = grade_scenario("win-the-rebuild-race", brute)
    assert out.passed and out.score == PASS_FLOOR


def test_the_second_failure_must_really_race_the_rebuild():
    ref = REFERENCE_SOLUTIONS["win-the-rebuild-race"]
    late = ref.model_copy(update={"events": [
        SimEvent(at_h=24, action="fail-node"), SimEvent(at_h=31, action="fail-drive")]})
    out = grade_scenario("win-the-rebuild-race", late)
    assert [c.id for c in out.criteria if not c.passed] == ["second-failure"]


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

    ref = REFERENCE_SOLUTIONS["burst-fits-the-pipe"]
    status, out = dispatch(app, "POST", "/api/labs/burst-fits-the-pipe/grade",
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
    for served, lab in zip(body, LABS):
        assert served["start"] != REFERENCE_SOLUTIONS[lab.id].model_dump(by_alias=True)

    ref = REFERENCE_SOLUTIONS["win-the-rebuild-race"].model_dump(by_alias=True)
    graded = client.post("/api/labs/win-the-rebuild-race/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404
