"""Graded labs (docs/LAB_PATTERN.md): the shared invariants plus this app's
own checks — the work metrics, the API surface, and the specific engine
behavior each lab's lesson depends on staying true."""

from __future__ import annotations

import app.labs as labs_module
import app.presets  # noqa: F401  (registers the Explain prose)
from app.engine import simulate
from app.labs import (
    GAMING_ATTEMPTS,
    LABS,
    LABS_BY_ID,
    NEVER,
    REFERENCE_SOLUTIONS,
    grade_scenario,
    measure,
)
from app.leveling import leveled, registry
from app.models import Scenario, SimEvent
from app.presets import BLOCKS, EXPLAINS, SEALED, SERVICEABLE
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
    assert [lab.id for lab in LABS] == [
        "outage-budget", "crossover-window", "sealed-fleet",
    ]


def test_equations_are_the_explain_entries_verbatim():
    by_id = {e.id: e.equation for e in EXPLAINS}
    for lab in LABS:
        for c in lab.criteria:
            assert c.equation == by_id[c.explain_id], (lab.id, c.id)
        assert lab.objective.equation == by_id[lab.objective.explain_id]


def _metrics(scenario: Scenario) -> dict[str, float]:
    trace, _log, summary = simulate(scenario)
    return measure(scenario, trace, summary, validate(scenario))


def test_every_metric_a_lab_names_is_measured():
    for scenario in (Scenario(config=BLOCKS, duration_d=30),
                     Scenario(config=SERVICEABLE, duration_d=30)):
        m = _metrics(scenario)
        for lab in LABS:
            for c in lab.criteria:
                assert c.metric in m, (lab.id, c.id, c.metric)
            assert lab.objective.metric in m


def test_dark_sites_earn_no_subscribers():
    heat = [SimEvent(at_d=10, action="heatwave", value=48)]
    xr = _metrics(Scenario(config=BLOCKS, duration_d=30, events=heat))
    std = _metrics(Scenario(
        config=BLOCKS.model_copy(update={"extended_temp": False}),
        duration_d=30, events=heat))
    assert std["meanSubscribersK"] < xr["meanSubscribersK"]
    assert xr["meanSubscribersK"] == 100 * 20


def test_a_recycled_laptop_stops_earning_work():
    """Dead years count as zero: a sealed laptop recycled at year 3 of 8
    delivers three eighths of its annual use."""
    cfg = SEALED.model_copy(update={"first_owner_years": 3, "annual_kwh": 160})
    m = _metrics(Scenario(config=cfg, duration_d=2920))
    assert m["deliveredKwhPerYear"] == 60.0
    alive = _metrics(Scenario(
        config=SERVICEABLE.model_copy(update={"annual_kwh": 160}), duration_d=2920))
    assert alive["deliveredKwhPerYear"] == 160.0
    # Work scales with use and is zero for the other product.
    assert _metrics(Scenario(config=BLOCKS, duration_d=30))["deliveredKwhPerYear"] == 0


def test_patch_then_grow_is_what_the_first_lab_turns_on():
    """Update hours scale with the fleet on the day of the patch, so the same
    events in the start's order pass with a worse objective."""
    ref = grade_scenario("outage-budget", REFERENCE_SOLUTIONS["outage-budget"])
    start = Scenario.model_validate(LABS_BY_ID["outage-budget"].start)
    fixed_dials = grade_scenario(
        "outage-budget", start.model_copy(update={"config": BLOCKS}))
    assert fixed_dials.passed and ref.passed
    assert fixed_dials.metrics["integrationHours"] > ref.metrics["integrationHours"]
    assert fixed_dials.score < ref.score


def test_each_bad_dial_alone_breaks_five_nines():
    ref = REFERENCE_SOLUTIONS["outage-budget"]
    for patch in ({"deploy_mode": "diy"}, {"extended_temp": False},
                  {"spare_capacity": False}):
        r = grade_scenario("outage-budget", ref.model_copy(update={
            "config": ref.config.model_copy(update=patch)}))
        failed = [c.id for c in r.criteria if not c.passed]
        assert "five-nines" in failed, patch


def test_the_crossover_window_is_squeezed_from_both_sides():
    ref = REFERENCE_SOLUTIONS["crossover-window"]

    def failing(**patch: object) -> list[str]:
        r = grade_scenario("crossover-window", ref.model_copy(update={
            "config": ref.config.model_copy(update=patch)}))
        return [c.id for c in r.criteria if not c.passed]

    assert failing() == []
    assert failing(annual_kwh=120) == ["crossover"]      # too little use
    assert failing(annual_kwh=150) == ["footprint"]      # too much
    assert "crossover" in failing(chassis_recycled=False)
    assert _metrics(Scenario(config=SERVICEABLE, duration_d=2920))["crossoverYear"] == NEVER


def test_a_sealed_laptop_gets_worse_the_longer_it_is_kept():
    ref = REFERENCE_SOLUTIONS["sealed-fleet"]
    cpy = []
    for years in (3, 4, 5):
        cfg = ref.config.model_copy(update={"first_owner_years": years})
        cpy.append(_metrics(Scenario(config=cfg, duration_d=2920))["carbonPerUsefulYear"])
    assert cpy[0] < cpy[1] < cpy[2]
    assert cpy[0] <= 180 < cpy[1]
    # And the best sealed result is still more than double the serviceable one.
    good = _metrics(REFERENCE_SOLUTIONS["crossover-window"])["carbonPerUsefulYear"]
    assert cpy[0] > 2 * good


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


def test_api_serves_labs_and_grades_without_leaking_solutions():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    listing = client.get("/api/labs?level=1")
    assert listing.status_code == 200
    body = listing.json()
    assert [x["id"] for x in body] == [lab.id for lab in LABS]
    assert "reference" not in listing.text.lower()
    for lab in LABS:
        ref = REFERENCE_SOLUTIONS[lab.id].model_dump(by_alias=True)
        assert all(x["start"] != ref for x in body)

    ref = REFERENCE_SOLUTIONS["crossover-window"].model_dump(by_alias=True)
    graded = client.post("/api/labs/crossover-window/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404


def test_static_dispatch_grades_like_the_api():
    """The hosted build has no server: the browser calls the same route
    function through twinkit.static_dispatch under Pyodide."""
    from twinkit.static_dispatch import dispatch

    from app.main import app

    ref = REFERENCE_SOLUTIONS["sealed-fleet"].model_dump(by_alias=True)
    status, body = dispatch(app, "POST", "/api/labs/sealed-fleet/grade",
                            {"level": "1"}, ref)
    assert status == 200 and body["passed"] and body["score"] == 100
    status, _ = dispatch(app, "POST", "/api/labs/nope/grade", {}, ref)
    assert status == 404
