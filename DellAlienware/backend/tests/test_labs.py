"""Graded labs (docs/LAB_PATTERN.md): the shared invariants plus this twin's
own checks — the work metric, the API surface, and the specific power-path
behaviour each lab's lesson depends on staying true."""

from __future__ import annotations

import app.labs as labs_module
from app.engine import simulate
from app.labs import (
    EXPLAINS,
    EXPLAINS_BY_ID,
    GAMING_ATTEMPTS,
    LABS,
    LABS_BY_ID,
    NO_DRAIN_MIN,
    REFERENCE_SOLUTIONS,
    grade_scenario,
    measure,
    resolve,
)
from app.leveling import leveled, registry
from app.models import Scenario
from twinkit.labs import PASS_FLOOR, Lab, grade
from twinkit.testing import assert_lab_invariants


def _sc(profile, adapter, pct, mode, workload) -> Scenario:
    return Scenario(
        profile_id=profile, adapter_id=adapter, start_battery_pct=pct,
        thermal_mode=mode, workload=workload,
    )


def _metrics(scenario: Scenario) -> dict[str, float]:
    profile, adapter = resolve(scenario)
    return measure(profile, adapter, scenario, simulate(profile, adapter, scenario))


def _failed(lab_id: str, scenario: Scenario) -> list[str]:
    return [c.id for c in grade_scenario(lab_id, scenario).criteria if not c.passed]


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


def test_explain_entries_are_unique_and_levelled():
    ids = [e.id for e in EXPLAINS]
    assert len(ids) == len(set(ids))
    reg = registry()
    for e in EXPLAINS:
        assert e.equation.strip() and e.title.strip()
        assert {1, 3, 5} <= set(reg[e.body]), e.id
        assert len(reg[e.body][1]) > len(reg[e.body][5]), e.id


def test_equations_are_the_explain_entries_verbatim():
    for lab in LABS:
        for c in lab.criteria:
            assert c.equation == EXPLAINS_BY_ID[c.explain_id].equation, (lab.id, c.id)
        assert lab.objective.equation == EXPLAINS_BY_ID[lab.objective.explain_id].equation


def test_every_explain_entry_is_used_by_some_lab():
    cited = {c.explain_id for lab in LABS for c in lab.criteria}
    cited |= {lab.objective.explain_id for lab in LABS}
    assert cited == set(EXPLAINS_BY_ID)


def test_work_is_zero_at_idle_and_rises_with_the_thermal_mode():
    idle = _metrics(_sc("m18-r2", "barrel-360", 30, "fullSpeed", "idle"))
    quiet = _metrics(_sc("m18-r2", "barrel-360", 30, "quiet", "gaming"))
    full = _metrics(_sc("m18-r2", "barrel-360", 30, "fullSpeed", "gaming"))
    assert idle["workW"] == 0
    assert 0 < quiet["workW"] < full["workW"]


def test_an_unrecognized_adapter_stops_earning_work():
    """The Unknown adapter is this twin's 'tripped' state: it never goes
    hybrid, and it delivers almost nothing."""
    m = _metrics(_sc("m18-r2", "barrel-unknown", 30, "fullSpeed", "fullLoad"))
    assert m["adapterRecognized"] == 0
    assert m["hybridPeakW"] == 0 and m["steadyChargeW"] == 0
    assert m["workW"] < 40


def test_every_metric_a_lab_names_is_measured():
    m = _metrics(LABS[0].start and Scenario.model_validate(LABS[0].start))
    for lab in LABS:
        for c in lab.criteria:
            assert c.metric in m, (lab.id, c.id, c.metric)
        assert lab.objective.metric in m


def test_the_supply_identity_is_what_the_metrics_read():
    """headroomW and steadyChargeW come from the same identity the engine keeps."""
    for sc in REFERENCE_SOLUTIONS.values():
        profile, adapter = resolve(sc)
        last = simulate(profile, adapter, sc)[-1]
        assert abs(last.ac_w + last.battery_w - last.system_w - last.charge_w) <= 0.5
        m = _metrics(sc)
        assert m["steadyChargeW"] <= max(0.0, m["headroomW"]) + 0.5


def test_lab_one_turns_on_one_thermal_mode_step():
    """Full Speed gaming goes hybrid on 280 W; Performance fits with charge to
    spare; full load in Performance goes hybrid again."""
    assert _failed("fit-the-brick", _sc("m18-r2", "barrel-280", 30, "fullSpeed", "gaming")) == [
        "no-hybrid", "still-charging",
    ]
    assert grade_scenario("fit-the-brick", REFERENCE_SOLUTIONS["fit-the-brick"]).passed
    assert "no-hybrid" in _failed(
        "fit-the-brick", _sc("m18-r2", "barrel-280", 30, "performance", "fullLoad")
    )
    # The 94% hold band: same settings, nearly full pack, charger off at the end.
    assert _failed("fit-the-brick", _sc("m18-r2", "barrel-280", 96, "performance", "gaming")) == [
        "still-charging",
    ]


def test_lab_two_runtime_is_the_battery_arithmetic():
    sc = REFERENCE_SOLUTIONS["travel-charger"]
    profile, adapter = resolve(sc)
    last = simulate(profile, adapter, sc)[-1]
    assert last.hybrid and last.battery_w > 0
    expected = (last.battery_pct - 20) / 100 * profile.battery.wh / last.battery_w * 60
    assert abs(_metrics(sc)["hybridRuntimeMin"] - expected) < 0.06
    # Right mode with a low pack fails on the runtime line and nothing else.
    assert _failed("travel-charger", _sc("area51-18", "usbc-100", 30, "quiet", "gaming")) == ["runtime"]
    # No drain at all reads as the sentinel, and idle still does not pass.
    idle = _sc("area51-18", "usbc-100", 100, "quiet", "idle")
    assert _metrics(idle)["hybridRuntimeMin"] == NO_DRAIN_MIN
    assert _failed("travel-charger", idle) == ["work"]


def test_lab_three_is_a_three_way_tension():
    """Each near-miss fails exactly the line its lesson is about."""
    lab = "charge-play-quiet"
    assert _failed(lab, _sc("m18-r2", "barrel-280", 30, "balanced", "fullLoad")) == ["pack-gain"]
    assert _failed(lab, _sc("m18-r2", "barrel-360", 30, "performance", "gaming")) == ["quiet-fans"]
    assert _failed(lab, _sc("m18-r2", "barrel-360", 30, "balanced", "gaming")) == ["work"]
    assert _failed(lab, _sc("m18-r2", "barrel-360", 60, "balanced", "fullLoad")) == ["pack-gain"]
    assert grade_scenario(lab, REFERENCE_SOLUTIONS[lab]).passed
    # A bigger brick buys charge, not speed.
    small = _metrics(_sc("m18-r2", "barrel-280", 30, "balanced", "fullLoad"))
    big = _metrics(_sc("m18-r2", "barrel-360", 30, "balanced", "fullLoad"))
    assert small["workW"] == big["workW"]
    assert small["steadyChargeW"] < big["steadyChargeW"] == 90


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
    assert [c.threshold for c in novice.criteria] == [c.threshold for c in lab.criteria]


def test_an_unknown_machine_or_adapter_is_a_value_error():
    import pytest

    with pytest.raises(ValueError):
        grade_scenario("fit-the-brick", _sc("m18-r2", "usbc-100", 30, "quiet", "gaming"))
    with pytest.raises(KeyError):
        grade_scenario("nope", REFERENCE_SOLUTIONS["fit-the-brick"])


def test_api_serves_labs_and_grades_without_leaking_solutions():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    listing = client.get("/api/labs?level=1")
    assert listing.status_code == 200
    assert [x["id"] for x in listing.json()] == [lab.id for lab in LABS]
    assert "reference" not in listing.text.lower()

    explains = client.get("/api/explain?level=5").json()
    assert [e["id"] for e in explains] == [e.id for e in EXPLAINS]

    ref = REFERENCE_SOLUTIONS["travel-charger"].model_dump(by_alias=True)
    graded = client.post("/api/labs/travel-charger/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404
    bad = dict(ref, adapterId="no-such-adapter")
    assert client.post("/api/labs/travel-charger/grade", json=bad).status_code == 422


def test_the_static_dispatcher_grades_like_fastapi():
    """In-browser grading runs the route through twinkit.static_dispatch."""
    from fastapi.testclient import TestClient

    from app.main import app
    from twinkit.static_dispatch import dispatch

    ref = REFERENCE_SOLUTIONS["fit-the-brick"].model_dump(by_alias=True)
    status, body = dispatch(app, "POST", "/api/labs/fit-the-brick/grade", {"level": "1"}, ref)
    native = TestClient(app).post("/api/labs/fit-the-brick/grade?level=1", json=ref)
    assert status == 200 and body == native.json()
