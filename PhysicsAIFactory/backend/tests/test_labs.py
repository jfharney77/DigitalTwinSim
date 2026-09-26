"""Graded labs (docs/LAB_PATTERN.md): the shared invariants plus this app's
own checks — the work metric, the API surface, and the specific physics each
lab's 'aha' depends on staying true in the engine."""

from __future__ import annotations

import app.labs as labs_module
import app.presets  # noqa: F401  (registers the Explain prose)
from app.engine import simulate
from app.labs import (
    GAMING_ATTEMPTS,
    LAB_DURATION_H,
    LABS,
    LABS_BY_ID,
    REFERENCE_SOLUTIONS,
    grade_scenario,
    measure,
)
from app.leveling import leveled, registry
from app.models import (
    ComputeBlock,
    DataBlock,
    ResilienceBlock,
    Scenario,
    SimEvent,
    TrainingJob,
)
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


def _ref(lab_id: str, **config_blocks) -> Scenario:
    ref = REFERENCE_SOLUTIONS[lab_id]
    return ref.model_copy(update={
        "config": ref.config.model_copy(update=config_blocks),
    })


def test_work_is_zero_before_training_and_scales_with_the_factory():
    # A 100 h run never leaves procurement/install: the factory is dark.
    dark = _metrics(Scenario(duration_h=100))
    assert dark["effectiveGpus"] == 0
    small = _metrics(Scenario(
        config=Scenario().config.model_copy(update={"compute": ComputeBlock(racks=2)}),
        duration_h=LAB_DURATION_H))
    full = _metrics(Scenario(duration_h=LAB_DURATION_H))
    assert 0 < small["effectiveGpus"] < full["effectiveGpus"]
    # Never more than the GPUs that exist.
    assert full["effectiveGpus"] < 8 * 72


def test_work_cannot_be_inflated_by_the_per_gpu_rate():
    base = _metrics(Scenario(duration_h=LAB_DURATION_H))
    fast = _metrics(Scenario(job=TrainingJob(tokens_per_gpu_s=2000),
                             duration_h=LAB_DURATION_H))
    assert abs(base["effectiveGpus"] - fast["effectiveGpus"]) <= 0.2
    assert fast["unfairInputs"] == 1


def test_a_starved_factory_stops_earning_work():
    starved = GAMING_ATTEMPTS["feed-the-worst-day"]["zero load: starve the GPUs to 10 GB/s"]
    m = _metrics(starved)
    assert m["effectiveGpus"] < 10          # 1152 GPUs installed, ~none working
    assert m["peakIdleDataPct"] > 95


def test_rollbacks_are_measured_and_cost_work():
    rare = _metrics(_ref("checkpoint-the-giant",
                         resilience=ResilienceBlock(checkpoint_interval_min=1440)))
    hourly = _metrics(REFERENCE_SOLUTIONS["checkpoint-the-giant"])
    assert rare["tokensRolledBackB"] > 10 * max(hourly["tokensRolledBackB"], 0.1)
    assert rare["effectiveGpus"] < hourly["effectiveGpus"]


def test_every_metric_a_lab_names_is_measured():
    m = _metrics(Scenario(duration_h=48))
    for lab in LABS:
        for c in lab.criteria:
            assert c.metric in m, (lab.id, c.id, c.metric)
        assert lab.objective.metric in m


def test_lab1_sizing_for_the_good_day_fails_only_on_starvation_and_work():
    """Lab 1's lesson: supply is what the platform delivers today. Sized to
    demand, the 50% failure idles half of every GPU-hour; sized to twice
    demand, nothing waits."""
    naive = grade_scenario("feed-the-worst-day",
                           Scenario.model_validate(LABS_BY_ID["feed-the-worst-day"].start))
    assert [c.id for c in naive.criteria if not c.passed] == ["work", "never-starved"]
    assert naive.metrics["peakIdleDataPct"] == 50.0
    assert grade_scenario("feed-the-worst-day",
                          REFERENCE_SOLUTIONS["feed-the-worst-day"]).metrics["peakIdleDataPct"] == 0


def test_lab2_more_racks_under_the_cap_means_fewer_tokens():
    """Lab 2's lesson: capped GPUs still draw idle power, so under a fixed
    megawatt work is an inverted U in rack count while $/Mtok only climbs."""
    ref = REFERENCE_SOLUTIONS["spend-the-megawatt"]

    def at(racks: int) -> dict[str, float]:
        return _metrics(ref.model_copy(update={"config": ref.config.model_copy(update={
            "compute": ComputeBlock(racks=racks),
            "data": DataBlock(storage_gbps=racks * 72 * 1.5),
        })}))

    m8, m9, m12, m16 = at(8), at(9), at(12), at(16)
    assert m8["effectiveGpus"] < m9["effectiveGpus"]        # rising side
    assert m16["effectiveGpus"] < m12["effectiveGpus"] < m9["effectiveGpus"]  # falling side
    assert m9["usdPerMtok"] < m12["usdPerMtok"] < m16["usdPerMtok"]
    assert m8["powerCappedHours"] == 0 < m9["powerCappedHours"] < m16["powerCappedHours"]
    # The comfortable build misses only the work floor.
    comfy = grade_scenario(
        "spend-the-megawatt", GAMING_ATTEMPTS["spend-the-megawatt"]["the comfortable 8 racks"])
    assert [c.id for c in comfy.criteria if not c.passed] == ["work"]


def test_lab3_needs_both_levers_and_storage_hits_the_power_wall():
    """Lab 3's lesson: the interval alone cannot pass (t_ckpt is too long),
    storage shortens t_ckpt, and too much storage caps the cluster."""
    lab = "checkpoint-the-giant"
    assert grade_scenario(lab, REFERENCE_SOLUTIONS[lab]).passed
    start = Scenario.model_validate(LABS_BY_ID[lab].start)
    for interval in (5, 15, 30, 60, 90, 120, 180, 240, 480, 1440):
        only_interval = start.model_copy(update={"config": start.config.model_copy(update={
            "resilience": ResilienceBlock(checkpoint_interval_min=interval)})})
        assert not grade_scenario(lab, only_interval).passed, interval
    glut = grade_scenario(lab, _ref(lab, data=DataBlock(storage_gbps=20000)))
    assert not glut.passed
    assert "no-cap" in [c.id for c in glut.criteria if not c.passed]
    assert glut.metrics["effectiveGpus"] < grade_scenario(
        lab, REFERENCE_SOLUTIONS[lab]).metrics["effectiveGpus"]


def test_constraints_are_measured_not_trusted():
    # Restoring the platform or deleting the weather is read off the trace.
    ref1 = REFERENCE_SOLUTIONS["feed-the-worst-day"]
    healed = ref1.model_copy(update={"events": [
        *ref1.events, SimEvent(at_h=301, action="restore-storage")]})
    assert [c.id for c in grade_scenario("feed-the-worst-day", healed).criteria
            if not c.passed] == ["degraded"]
    ref2 = REFERENCE_SOLUTIONS["spend-the-megawatt"]
    mild = ref2.model_copy(update={"events": []})
    assert [c.id for c in grade_scenario("spend-the-megawatt", mild).criteria
            if not c.passed] == ["warm-spell"]


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
        assert novice.objective.par == expert.objective.par == lab.objective.par


def test_api_serves_labs_and_grades_without_leaking_solutions():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    listing = client.get("/api/labs?level=1")
    assert listing.status_code == 200
    body = listing.json()
    assert [x["id"] for x in body] == [lab.id for lab in LABS]
    assert "reference" not in listing.text.lower()
    assert "gaming" not in listing.text.lower()

    ref = REFERENCE_SOLUTIONS["spend-the-megawatt"].model_dump(by_alias=True)
    graded = client.post("/api/labs/spend-the-megawatt/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404


def test_labs_grade_through_the_static_dispatcher():
    """Static hosting answers POST /api/labs/{id}/grade in the browser through
    twinkit.static_dispatch; it must agree with the pure grader."""
    from twinkit.static_dispatch import dispatch

    from app.main import app

    lab = LABS[0]
    ref = REFERENCE_SOLUTIONS[lab.id]
    status, body = dispatch(app, "POST", f"/api/labs/{lab.id}/grade",
                            {"level": "3"}, ref.model_dump(by_alias=True))
    assert status == 200
    assert body["score"] == grade_scenario(lab.id, ref).score
    status, _ = dispatch(app, "POST", "/api/labs/nope/grade", {},
                         ref.model_dump(by_alias=True))
    assert status == 404
