"""Graded labs (docs/LAB_PATTERN.md): the shared invariants plus this app's
own checks — the work metric, the API surface, and the specific shared-
infrastructure physics each lab's 'aha' depends on staying true."""

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
from app.models import Scenario, SimEvent, SledLoad, Workload
from app.presets import EIGHT_COMPUTE, EXPLAINS, FULL, NPLUS1
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


def _all(load: SledLoad) -> Workload:
    return Workload(loads=[load.model_copy() for _ in range(8)])


def _metrics(scenario: Scenario) -> dict[str, float]:
    trace, _log, summary = simulate(scenario)
    return measure(scenario, trace, summary, validate(scenario))


def test_work_is_zero_at_idle_and_scales_with_load():
    def at(pct: int) -> float:
        return _metrics(Scenario(
            config=EIGHT_COMPUTE, workload=_all(SledLoad(cpu_pct=pct)), duration_s=120,
        ))["workRateW"]

    assert at(0) == 0
    assert 0 < at(50) < at(99)
    # Eight dual-205 W sleds at 100%, nothing clamped: exactly 8 × 2 × 205.
    assert at(100) == 3280


def test_a_dark_chassis_stops_earning_work():
    dark = GAMING_ATTEMPTS["smallest-pool-that-survives"]["more PSUs on n+1"]
    m = _metrics(dark)
    assert m["shutdown"] == 1
    # Full work until the feed dies at t=300, nothing afterwards.
    assert 1500 < m["workRateW"] < 1700


def test_a_capped_chassis_earns_less_than_it_asked_for():
    """The clamp is read back from the trace's own watts: a chassis held
    under a power cap delivers less than its dials request."""
    capped = _metrics(Scenario(
        config=EIGHT_COMPUTE.model_copy(update={"power_cap_w": 3000}),
        workload=FULL, duration_s=300,
    ))
    assert capped["throttleSeconds"] > 0
    assert capped["workRateW"] < 3280 * 0.9


def test_every_metric_a_lab_names_is_measured():
    m = _metrics(Scenario(config=EIGHT_COMPUTE, duration_s=30))
    for lab in LABS:
        for c in lab.criteria:
            assert c.metric in m, (lab.id, c.id, c.metric)
        assert lab.objective.metric in m


def test_consolidating_is_what_the_easy_lab_punishes():
    """Lab 1's lesson: same work, and the only failing line is the fan bill."""
    lab = LABS_BY_ID["spread-the-heat"]
    start = grade_scenario(lab.id, Scenario.model_validate(lab.start))
    ref = grade_scenario(lab.id, REFERENCE_SOLUTIONS[lab.id])
    assert [c.id for c in start.criteria if not c.passed] == ["fan-bill"]
    assert start.metrics["workRateW"] == ref.metrics["workRateW"]
    assert start.metrics["meanFanW"] > 10 * ref.metrics["meanFanW"]
    assert start.metrics["meanWallW"] > ref.metrics["meanWallW"] + 250


def test_the_same_four_psus_arranged_differently():
    """Lab 2's lesson: four PSUs on N+1 go dark, four on grid survive, two on
    grid trip on overcurrent, and six on grid pass without full marks."""
    lab_id = "smallest-pool-that-survives"
    ref = REFERENCE_SOLUTIONS[lab_id]
    assert ref.config.psu_count == NPLUS1.psu_count == 4
    assert grade_scenario(lab_id, ref).score == 100
    six = ref.model_copy(update={
        "config": ref.config.model_copy(update={"psu_count": 6}),
    })
    r6 = grade_scenario(lab_id, six)
    assert r6.passed and r6.score == PASS_FLOOR
    two = GAMING_ATTEMPTS[lab_id]["grid pool of two trips"]
    _trace, log, summary = simulate(two)
    assert summary.shutdown_reason == "PSU pool overcurrent trip"


def test_the_small_sleds_cannot_reach_the_hard_labs_floor():
    """Lab 3's lesson: inside 4000 W no even load on the 205 W tier reaches
    2800 W-TDP; 350 W sleds run gently do. The only failing line is work."""
    lab_id = "the-budget-is-a-wall"
    ref = REFERENCE_SOLUTIONS[lab_id]
    best = 0.0
    for pct in range(70, 101, 2):
        m = _metrics(ref.model_copy(update={
            "config": EIGHT_COMPUTE,
            "workload": _all(SledLoad(cpu_pct=pct, mem_pct=80, storage_pct=60)),
        }))
        if m["peakDcW"] <= 4000 and m["throttleSeconds"] == 0:
            best = max(best, m["workRateW"])
    assert 0 < best < 2800
    small = grade_scenario(lab_id, GAMING_ATTEMPTS[lab_id]["205 W sleds turned down"])
    assert [c.id for c in small.criteria if not c.passed] == ["work"]
    assert grade_scenario(lab_id, ref).passed


def test_the_power_cap_does_not_hold_the_budget_line():
    r = grade_scenario(
        "the-budget-is-a-wall",
        GAMING_ATTEMPTS["the-budget-is-a-wall"]["lean on the power cap"],
    )
    failed = {c.id for c in r.criteria if not c.passed}
    assert {"budget", "no-throttle"} <= failed


def test_a_feed_nobody_uses_is_not_a_failure():
    s = Scenario(config=NPLUS1, workload=FULL, duration_s=120,
                 events=[SimEvent(at_s=10, action="lose-feed", index=1)])
    m = _metrics(s)
    assert m["firstFeedLossS"] == 10 and m["psusDarkAtEnd"] == 0


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


def test_the_static_dispatcher_grades_without_fastapi_in_the_loop():
    """The in-browser path (docs/STATIC_HOSTING.md): twinkit.static_dispatch
    calls the route function directly, path parameter and all."""
    from app.main import app
    from twinkit.static_dispatch import dispatch

    ref = REFERENCE_SOLUTIONS["spread-the-heat"].model_dump(by_alias=True)
    status, body = dispatch(app, "POST", "/api/labs/spread-the-heat/grade",
                            {"level": "1"}, ref)
    assert status == 200 and body["passed"] and body["score"] == 100
    status, _ = dispatch(app, "POST", "/api/labs/nope/grade", {}, ref)
    assert status == 404


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

    ref = REFERENCE_SOLUTIONS["the-budget-is-a-wall"].model_dump(by_alias=True)
    graded = client.post("/api/labs/the-budget-is-a-wall/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404
