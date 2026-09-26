"""Graded labs (docs/LAB_PATTERN.md): the shared invariants plus this app's
own checks — the work metrics, the API surface, and the specific physics each
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
from app.presets import CONSOLE, EXPLAINS
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


def test_the_labs_use_every_half_of_the_app():
    cited = {c.explain_id for lab in LABS for c in lab.criteria}
    assert cited == {e.id for e in EXPLAINS}


def _metrics(scenario: Scenario) -> dict[str, float]:
    trace, _log, summary = simulate(scenario)
    return measure(scenario, trace, summary, validate(scenario))


def test_every_metric_a_lab_names_is_measured():
    m = _metrics(Scenario(duration_h=24))
    for lab in LABS:
        for c in lab.criteria:
            assert c.metric in m, (lab.id, c.id, c.metric)
        assert lab.objective.metric in m


def test_work_is_zero_when_idle_and_scales_with_load():
    idle = _metrics(Scenario(workload=Workload(raw_arrival_tbh=0), duration_h=48))
    some = _metrics(Scenario(workload=Workload(raw_arrival_tbh=3), duration_h=48))
    more = _metrics(Scenario(workload=Workload(raw_arrival_tbh=6), duration_h=48))
    assert idle["meanThroughputTbh"] == 0
    assert 0 < some["meanThroughputTbh"] < more["meanThroughputTbh"]
    # The console's work metrics: nothing planted, nothing diagnosed.
    quiet = _metrics(Scenario(config=CONSOLE, duration_h=480))
    assert quiet["diagnosedIssuePct"] == 0
    assert quiet["issuesPlanted"] == 0


def test_a_full_array_stops_earning_work():
    """Lab 3's work floor: at 100% the array lands nothing more."""
    start = Scenario.model_validate(LABS_BY_ID["last-weeks-question"].start)
    full = _metrics(start)
    saved = _metrics(REFERENCE_SOLUTIONS["last-weeks-question"])
    assert full["peakFillPct"] == 100
    assert full["dataLandedPctDay"] < 3.7 <= saved["dataLandedPctDay"]


def test_precision_is_a_step_function_of_k_and_mttd_is_not():
    """Lab 1's lesson: k = 3.5 to 5 buys no precision and costs MTTD."""
    ref = REFERENCE_SOLUTIONS["quiet-and-quick"]

    def at(k: float) -> dict[str, float]:
        cfg = ref.config.model_copy(update={"anomaly_k": k})
        return _metrics(ref.model_copy(update={"config": cfg}))

    assert at(3.0)["precisionPct"] < 60
    plateau = [at(k) for k in (3.5, 4.0, 4.5, 5.0)]
    assert {m["precisionPct"] for m in plateau} == {60.0}
    mttds = [m["mttdH"] for m in plateau]
    assert mttds == sorted(mttds) and len(set(mttds)) == 4
    # The start (k = 3) fails on precision alone; k = 5 fails on MTTD alone.
    start = grade_scenario("quiet-and-quick", Scenario.model_validate(LABS[0].start))
    assert [c.id for c in start.criteria if not c.passed] == ["precision"]
    slow = ref.model_copy(update={
        "config": ref.config.model_copy(update={"anomaly_k": 5.0})})
    graded = grade_scenario("quiet-and-quick", slow)
    assert [c.id for c in graded.criteria if not c.passed] == ["mttd"]


def test_the_constraint_relocates_through_the_feed_lab():
    """Lab 2's lesson: each fix hands the constraint to the next term."""
    lab_id = "feed-the-gpus"
    greedy = grade_scenario(lab_id, GAMING_ATTEMPTS[lab_id]["gpu processing only"])
    # ×6 on process and the pipeline is now bound by what arrives.
    assert greedy.metrics["meanThroughputTbh"] == 8
    assert not greedy.passed
    # Serve sized to throughput, not to the GPUs' demand, starves them by 20%.
    ref = REFERENCE_SOLUTIONS[lab_id]
    short_serve = ref.model_copy(update={
        "config": ref.config.model_copy(update={"serve_tbh": 20})})
    graded = grade_scenario(lab_id, short_serve)
    assert [c.id for c in graded.criteria if not c.passed] == ["gpu-fed"]
    # Over-provisioning passes and earns nothing on the objective.
    fat = ref.model_copy(update={"config": ref.config.model_copy(update={
        "ingest_tbh": 60, "process_tbh": 60, "index_tbh": 60, "serve_tbh": 60})})
    graded = grade_scenario(lab_id, fat)
    assert graded.passed and graded.score == PASS_FLOOR


def test_the_forecast_misleads_for_a_window_after_the_doubling():
    """Lab 3's lesson: at h 240 the forecast reads about twice the truth."""
    start = Scenario.model_validate(LABS_BY_ID["last-weeks-question"].start)
    trace, _log, _summary = simulate(start)
    forecast_days = trace[240].days_to_full_forecast
    full_at = next(s.t_h for s in trace if s.array_fill_pct >= 100)
    true_days = (full_at - 240) / 24.0
    assert forecast_days > 1.8 * true_days
    # Buying on the forecast's schedule is an outage; buying on day two passes
    # and earns almost nothing on the objective.
    trusting = grade_scenario(
        "last-weeks-question", GAMING_ATTEMPTS["last-weeks-question"]["trust the forecast"])
    assert not trusting.passed
    early = start.model_copy(update={"events": start.events + [
        SimEvent(at_h=49, action="expand-capacity"),
        SimEvent(at_h=500, action="expand-capacity"),
    ]})
    graded = grade_scenario("last-weeks-question", early)
    assert graded.passed and graded.score <= PASS_FLOOR + 3


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

    ref = REFERENCE_SOLUTIONS["feed-the-gpus"].model_dump(by_alias=True)
    graded = client.post("/api/labs/feed-the-gpus/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404


def test_grading_works_through_the_static_dispatcher():
    """Hosted builds grade in the browser: the same route, run by
    twinkit.static_dispatch (what Pyodide calls), must agree with FastAPI."""
    from fastapi.testclient import TestClient

    from app.main import app
    from twinkit.static_dispatch import dispatch

    ref = REFERENCE_SOLUTIONS["quiet-and-quick"].model_dump(by_alias=True)
    path = "/api/labs/quiet-and-quick/grade"
    status, payload = dispatch(app, "POST", path, {"level": "1"}, ref)
    assert status == 200
    assert payload == TestClient(app).post(path + "?level=1", json=ref).json()
    assert dispatch(app, "POST", "/api/labs/nope/grade", {}, ref)[0] == 404
