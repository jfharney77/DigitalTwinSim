"""Graded labs (docs/LAB_PATTERN.md): the shared invariants plus this app's
own checks — the work metrics, the API surface, and the specific RAID physics
each lab's 'aha' depends on staying true."""

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
from app.models import ArrayConfig, Scenario, SimEvent, Workload
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


def test_every_lab_has_a_zero_load_gaming_attempt():
    for lab in LABS:
        assert "zero load" in GAMING_ATTEMPTS[lab.id], lab.id


def _metrics(scenario: Scenario) -> dict[str, float]:
    trace, _log, summary = simulate(scenario)
    return measure(scenario, trace, summary, validate(scenario))


def test_work_is_zero_at_idle_and_scales_with_load():
    def at(kiops: float) -> dict[str, float]:
        return _metrics(Scenario(
            config=ArrayConfig(raid_level="10"),
            workload=Workload(offered_kiops=kiops, read_pct=40), duration_min=60,
        ))

    idle, half, full = at(0.0), at(0.5), at(1.0)
    assert idle["workKiops"] == 0 and idle["writeWorkKiops"] == 0
    assert 0 < half["workKiops"] < full["workKiops"]
    assert 0 < half["writeWorkKiops"] < full["writeWorkKiops"]


def test_work_is_what_was_served_not_what_was_asked():
    """Overdriving a saturated array earns no more work than the budget pays for."""
    m = _metrics(GAMING_ATTEMPTS["pay-the-write-tax"]["overdrive a saturated array"])
    assert m["saturatedTicks"] > 0
    assert m["workKiops"] < 1.0  # asked 50 kIOPS; 23 × 170 IOPS ÷ 6 served


def test_a_lost_array_stops_earning_work():
    lost = GAMING_ATTEMPTS["size-for-the-worst-day"]["raid 10 for cheap writes"]
    m = _metrics(lost)
    assert m["dataLost"] == 1 and m["offlineTicks"] > 0
    # 100 kIOPS asked for three days; the array died four hours in.
    assert m["workKiops"] < 10
    assert m["minServedKiops"] == 0


def test_every_metric_a_lab_names_is_measured():
    m = _metrics(Scenario(duration_min=30))
    for lab in LABS:
        for c in lab.criteria:
            assert c.metric in m, (lab.id, c.id, c.metric)
        assert lab.objective.metric in m


def test_a_missing_failure_cannot_pass_an_upper_bound():
    m = _metrics(Scenario(duration_min=30))
    assert m["firstDriveFailureMin"] > 60


def _failed(lab_id: str, scenario: Scenario) -> list[str]:
    return [c.id for c in grade_scenario(lab_id, scenario).criteria if not c.passed]


def test_lab_one_turns_on_the_write_penalty_ladder():
    """×6 saturates, ×2 passes on half the capacity, ×4 passes on nearly all of it."""
    ref = REFERENCE_SOLUTIONS["pay-the-write-tax"]

    def with_raid(level: str, spares: int = 1) -> Scenario:
        return ref.model_copy(update={
            "config": ref.config.model_copy(update={"raid_level": level, "spares": spares}),
        })

    assert "never-saturated" in _failed("pay-the-write-tax", with_raid("6"))
    r10 = grade_scenario("pay-the-write-tax", with_raid("10", spares=2))
    r5 = grade_scenario("pay-the-write-tax", ref)
    assert r10.passed and r5.passed
    assert r5.score > r10.score
    assert r5.metrics["usableTb"] == 2 * r10.metrics["usableTb"]


def test_lab_two_turns_on_drive_size_load_and_parity():
    ref = REFERENCE_SOLUTIONS["close-the-window"]

    def change(cfg: dict | None = None, kiops: float | None = None) -> Scenario:
        upd: dict = {}
        if cfg:
            upd["config"] = ref.config.model_copy(update=cfg)
        if kiops is not None:
            upd["workload"] = ref.workload.model_copy(update={"offered_kiops": kiops})
        return ref.model_copy(update=upd)

    # Bigger drives: the only failing line is the window.
    assert _failed("close-the-window", change({"drive_tb": 16})) == ["window"]
    # Same drives, more host load: the (1 − 0.5 × load) term alone breaks it.
    assert _failed("close-the-window", change(kiops=0.25)) == ["window"]
    # RAID 5 passes every line — same window — and earns nothing for it.
    r5 = grade_scenario("close-the-window", change({"raid_level": "5"}))
    r6 = grade_scenario("close-the-window", ref)
    assert r5.passed and r6.passed
    assert abs(r5.metrics["rebuildHours"] - r6.metrics["rebuildHours"]) < 3
    assert r5.metrics["exposureIndexHours"] > 5 * r6.metrics["exposureIndexHours"]
    assert r5.score == PASS_FLOOR and r6.score >= 97


def test_lab_three_is_sized_by_the_degraded_state():
    """The load the rules panel approves for the healthy array saturates the
    degraded one; only the worst-day sum passes."""
    healthy = GAMING_ATTEMPTS["size-for-the-worst-day"]["size for the healthy day"]
    assert not any(
        v.rule_id == "headroom" and v.level != "ok" for v in validate(healthy)
    )
    failed = _failed("size-for-the-worst-day", healthy)
    assert "never-saturated" in failed and "no-loss" not in failed

    ref = REFERENCE_SOLUTIONS["size-for-the-worst-day"]
    assert grade_scenario("size-for-the-worst-day", ref).passed
    pushed = ref.model_copy(update={
        "workload": ref.workload.model_copy(update={"offered_kiops": 110.0}),
    })
    assert _failed("size-for-the-worst-day", pushed) == ["latency"]

    for level in ("5", "10"):
        dead = ref.model_copy(update={
            "config": ref.config.model_copy(update={"raid_level": level}),
        })
        assert "no-loss" in _failed("size-for-the-worst-day", dead), level


def test_clicked_failures_grade_the_same_as_the_scripted_ones():
    """The UI appends events at the cursor; order in the list must not matter."""
    ref = REFERENCE_SOLUTIONS["size-for-the-worst-day"]
    shuffled = ref.model_copy(update={"events": list(reversed(ref.events))})
    a = grade_scenario("size-for-the-worst-day", ref)
    b = grade_scenario("size-for-the-worst-day", shuffled)
    assert a.model_dump() == b.model_dump()


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


def test_start_scenarios_carry_the_stage():
    """The failures are part of the start, on slots that are always members."""
    for lab_id in ("close-the-window", "size-for-the-worst-day"):
        start = Scenario.model_validate(LABS_BY_ID[lab_id].start)
        fails = [e for e in start.events if e.action == "fail-drive"]
        assert fails and all(e.index in (0, 1) for e in fails)
    assert isinstance(SimEvent(at_min=0, action="fail-controller"), SimEvent)


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

    ref = REFERENCE_SOLUTIONS["close-the-window"].model_dump(by_alias=True)
    graded = client.post("/api/labs/close-the-window/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404


def test_labs_grade_through_the_static_dispatcher():
    """Static hosting runs main.py's routes in the browser through
    twinkit.static_dispatch; the lab routes must answer there too."""
    from twinkit.static_dispatch import dispatch

    from app.main import app

    status, labs = dispatch(app, "GET", "/api/labs", {"level": "1"})
    assert status == 200 and [x["id"] for x in labs] == [lab.id for lab in LABS]
    ref = REFERENCE_SOLUTIONS["pay-the-write-tax"].model_dump(by_alias=True)
    status, out = dispatch(
        app, "POST", "/api/labs/pay-the-write-tax/grade", {"level": "3"}, ref,
    )
    assert status == 200 and out["passed"] and out["score"] == 100
    status, _ = dispatch(app, "POST", "/api/labs/nope/grade", {}, ref)
    assert status == 404
