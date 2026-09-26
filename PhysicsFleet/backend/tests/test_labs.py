"""Graded labs (docs/LAB_PATTERN.md): the shared invariants plus this app's
own checks — the work metric, the API surface, and the specific fleet
arithmetic each lab's 'aha' depends on staying true."""

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
from app.models import FleetConfig, Scenario, Workload
from app.presets import APEX_SPIKY, EXPLAINS
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


def test_work_is_nothing_on_an_empty_fleet_and_scales_with_the_estate():
    cfg = FleetConfig(sites=1, nodes_per_site=8)
    empty = _metrics(Scenario(config=cfg, workload=Workload(vms_per_site=1, growth_pct_month=0)))
    half = _metrics(Scenario(config=cfg, workload=Workload(vms_per_site=30, growth_pct_month=0)))
    full = _metrics(Scenario(config=cfg, workload=Workload(vms_per_site=60, growth_pct_month=0)))
    assert empty["workVms"] <= 1
    assert empty["workVms"] < half["workVms"] < full["workVms"]


def test_an_undersized_fleet_earns_only_what_it_can_host():
    """The fleet's version of 'a tripped server stops earning': asking for
    more than the nodes (or the APEX ceiling) can hold earns nothing extra."""
    cfg = FleetConfig(sites=1, nodes_per_site=4)
    over = _metrics(Scenario(config=cfg, workload=Workload(vms_per_site=200, growth_pct_month=0)))
    assert over["workVms"] <= 40
    assert over["capacityShortDays"] > 0
    capped = _metrics(GAMING_ATTEMPTS["commit-to-the-trough"]["tiny buffer, let the spikes drop"])
    assert capped["workVms"] < 147
    assert capped["capacityShortDays"] > 0


def test_every_metric_a_lab_names_is_measured():
    m = _metrics(Scenario(duration_d=30))
    for lab in LABS:
        for c in lab.criteria:
            assert c.metric in m, (lab.id, c.id, c.metric)
        assert lab.objective.metric in m


def test_lab_one_turns_on_growth_not_on_the_three_node_trap():
    """Four nodes — the guided scenario's answer — closes the protection
    window and still fails, for exactly one reason: by day 150 three
    survivors cannot hold the grown estate. Five pass; FTT=2 on five reopens
    the window."""
    lab = "headroom-for-the-last-day"
    ref = REFERENCE_SOLUTIONS[lab]
    four = ref.model_copy(update={
        "config": ref.config.model_copy(update={"nodes_per_site": 4})})
    ftt2 = ref.model_copy(update={"config": ref.config.model_copy(update={"ftt": 2})})
    assert grade_scenario(lab, ref).passed
    assert _failed(lab, four) == ["no-hard-outage"]
    assert _failed(lab, ftt2) == ["protected"]


def test_lab_two_automation_has_a_ceiling_too():
    """Manual cannot pass at any useful size; automated passes and then hits
    the same 16 h/day wall ten times further out."""
    lab = "two-person-ceiling"
    start = Scenario.model_validate(LABS_BY_ID[lab].start)
    assert _failed(lab, start) == ["current", "no-trucks"]
    automated = start.model_copy(update={
        "config": start.config.model_copy(update={"ops_mode": "automated"})})
    flipped = grade_scenario(lab, automated)
    assert flipped.passed and flipped.score == PASS_FLOOR
    too_big = REFERENCE_SOLUTIONS[lab].model_copy(update={
        "config": REFERENCE_SOLUTIONS[lab].config.model_copy(update={"sites": 480})})
    assert "current" in _failed(lab, too_big)


def test_lab_three_the_trough_is_the_cheapest_commitment():
    """Cost per VM-hour is V-shaped in the base with its minimum near the
    trough, and a buffer sized for the first spike drops the last one."""
    wl = REFERENCE_SOLUTIONS["commit-to-the-trough"].workload

    def cost(base: int) -> float:
        cfg = APEX_SPIKY.model_copy(update={"committed_vms": base, "buffer_pct": 100})
        return _metrics(Scenario(config=cfg, workload=wl, duration_d=180))["costPerKVmHour"]

    assert cost(131) < cost(120) and cost(131) < cost(150)
    first_spike = GAMING_ATTEMPTS["commit-to-the-trough"]["buffer sized to the first spike"]
    assert "served" in _failed("commit-to-the-trough", first_spike)


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
    """The hosted site grades in the browser by calling the same route
    functions through twinkit.static_dispatch (path parameter + body)."""
    from app.main import app
    from twinkit.static_dispatch import dispatch

    lab = LABS[0]
    body = REFERENCE_SOLUTIONS[lab.id].model_dump(by_alias=True)
    status, out = dispatch(app, "POST", f"/api/labs/{lab.id}/grade", {"level": "1"}, body)
    assert status == 200 and out["passed"] and out["score"] >= PASS_FLOOR
    status, _ = dispatch(app, "POST", "/api/labs/nope/grade", {}, body)
    assert status == 404


def test_api_serves_labs_and_grades_without_leaking_solutions():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    listing = client.get("/api/labs?level=1")
    assert listing.status_code == 200
    body = listing.json()
    assert [x["id"] for x in body] == [lab.id for lab in LABS]
    assert "reference" not in listing.text.lower()

    ref = REFERENCE_SOLUTIONS["two-person-ceiling"].model_dump(by_alias=True)
    graded = client.post("/api/labs/two-person-ceiling/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404
