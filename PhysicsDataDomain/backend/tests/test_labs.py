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
from app.models import Dataset, Scenario, Schedule, SimEvent
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


def _with_retention(scenario: Scenario, r: int) -> Scenario:
    return scenario.model_copy(update={"schedule": Schedule(retention_days=r)})


def test_work_is_near_zero_with_nothing_to_protect_and_scales_with_the_estate():
    def run(full_tb: float, r: int) -> float:
        return _metrics(Scenario(
            dataset=Dataset(full_tb=full_tb, daily_change_pct=1, entropy_pct=30),
            schedule=Schedule(retention_days=r), duration_days=60,
        ))["protectedTbMean"]

    assert run(0.1, 1) < 1
    assert run(50, 1) < run(50, 10) < run(50, 30) < run(100, 30)


def test_a_full_store_stops_earning_work():
    """The 'tripped server' of this app: once the store is full its backups
    fail, and those days protect nothing."""
    full = GAMING_ATTEMPTS["encrypted-tenant"]["the faster appliance"]
    fits = full.model_copy(update={"appliance": "dd9910"})
    m_full, m_fits = _metrics(full), _metrics(fits)
    assert m_full["peakCapacityPct"] >= 100
    assert m_fits["peakCapacityPct"] < 100
    # Same dataset, same retention: only the full days differ.
    assert m_full["protectedTbMean"] < 0.5 * m_fits["protectedTbMean"]


def test_every_metric_a_lab_names_is_measured():
    m = _metrics(Scenario(duration_days=10))
    for lab in LABS:
        for c in lab.criteria:
            assert c.metric in m, (lab.id, c.id, c.metric)
        assert lab.objective.metric in m


def test_measure_replays_the_dataset_events():
    m = _metrics(Scenario(duration_days=20, events=[
        SimEvent(at_day=5, action="set-change-rate", value=0.5),
        SimEvent(at_day=6, action="set-entropy", value=90),
        SimEvent(at_day=7, action="ransomware-start", value=3),
        SimEvent(at_day=9, action="ransomware-stop"),
    ]))
    assert m["minChangePct"] == 0.5
    assert m["minEntropyPct"] == 30 and m["maxEntropyPct"] == 90
    assert m["maxRansomwareRatePct"] == 3
    assert m["ransomwareDays"] == 2


def test_lab_one_turns_on_the_index_knee_not_the_disks():
    """One generation past the reference, the only failing line is the index —
    and the store is still far from its 85% line."""
    ref = REFERENCE_SOLUTIONS["branch-box-memory"]
    assert grade_scenario("branch-box-memory", ref).passed
    over = grade_scenario(
        "branch-box-memory", _with_retention(ref, ref.schedule.retention_days + 1))
    assert [c.id for c in over.criteria if not c.passed] == ["rated-ingest"]
    assert over.metrics["peakCapacityPct"] < 70


def test_lab_two_the_bigger_index_beats_the_faster_box():
    """Under ciphertext the DD9910 (15 GB/s, 192 GB index RAM) carries more
    generations inside the window than the all-flash box (20 GB/s, 96 GB)."""
    ref = REFERENCE_SOLUTIONS["encrypted-tenant"]
    assert ref.appliance == "dd9910"
    r = ref.schedule.retention_days
    over = grade_scenario("encrypted-tenant", _with_retention(ref, r + 1))
    assert [c.id for c in over.criteria if not c.passed] == ["window"]
    flash = grade_scenario(
        "encrypted-tenant", ref.model_copy(update={"appliance": "dd-all-flash"}))
    assert "window" in [c.id for c in flash.criteria if not c.passed]
    # The flash box can pass, but only by protecting less.
    best_flash = max(
        (grade_scenario("encrypted-tenant", _with_retention(
            ref.model_copy(update={"appliance": "dd-all-flash"}), k))
         for k in range(1, r + 1)),
        key=lambda g: g.score,
    )
    assert best_flash.score < grade_scenario("encrypted-tenant", ref).score


def test_lab_three_churn_masks_the_slow_attack():
    """The acceptance test's alarm fires within two days; under 5%/day churn
    the same instrument takes weeks, and retention is what that costs."""
    ref = REFERENCE_SOLUTIONS["late-alarm"]
    m = _metrics(ref)
    assert m["alarmLagDays"] > 30
    quiet = ref.model_copy(update={
        "dataset": ref.dataset.model_copy(update={"daily_change_pct": 1.0})})
    assert 0 <= _metrics(quiet)["alarmLagDays"] <= 2
    # One generation short, and the only failing line is the clean copies.
    short = grade_scenario(
        "late-alarm", _with_retention(ref, ref.schedule.retention_days - 1))
    assert [c.id for c in short.criteria if not c.passed] == ["clean-copies"]


def test_a_false_alarm_counts_no_clean_copies():
    noisy = GAMING_ATTEMPTS["late-alarm"]["trip the alarm with random churn"].model_copy(
        update={"events": [
            SimEvent(at_day=10, action="set-entropy", value=100),
            SimEvent(at_day=30, action="ransomware-start", value=1),
        ]})
    m = _metrics(noisy)
    assert 0 < m["alarmDay"] < 30
    assert m["cleanGenerationsAtAlarm"] == 0


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
    # The start is the naive default, never the answer.
    for x in body:
        ref = REFERENCE_SOLUTIONS[x["id"]].model_dump(by_alias=True)
        assert x["start"] != ref

    ref = REFERENCE_SOLUTIONS["encrypted-tenant"].model_dump(by_alias=True)
    graded = client.post("/api/labs/encrypted-tenant/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404
    assert LABS_BY_ID.keys() == REFERENCE_SOLUTIONS.keys()
