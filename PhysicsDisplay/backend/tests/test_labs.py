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
from app.models import DisplayConfig, Lifecycle, Scenario, SimEvent
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


def _cfg(**kw) -> DisplayConfig:
    return DisplayConfig(**kw)


def test_light_is_zero_when_dark_and_scales_with_brightness():
    off = _metrics(Scenario(config=_cfg(brightness_pct=0), duration_s=60))
    half = _metrics(Scenario(config=_cfg(brightness_pct=50), duration_s=60))
    full = _metrics(Scenario(config=_cfg(brightness_pct=100), duration_s=60))
    assert off["usefulLightPct"] == 0
    assert 0 < half["usefulLightPct"] < full["usefulLightPct"]


def test_a_sleeping_monitor_stops_earning_light():
    awake = _metrics(Scenario(config=_cfg(brightness_pct=100), duration_s=100))
    asleep = _metrics(Scenario(
        config=_cfg(brightness_pct=100), duration_s=100,
        events=[SimEvent(at_s=0, action="standby")],
    ))
    assert asleep["usefulLightPct"] == 0
    assert asleep["standbySeconds"] == 101
    assert awake["usefulLightPct"] > 0


def test_light_does_not_depend_on_the_backlight_architecture():
    """Same picture, same brightness, same useful light: the proxy measures
    what reaches the viewer, so the panels differ in watts, not in work."""
    edge = _metrics(Scenario(config=_cfg(model="edge-27", content="dark",
                                         local_dimming=False)))
    mini = _metrics(Scenario(config=_cfg(model="miniled-32", content="dark")))
    assert edge["usefulLightPct"] == mini["usefulLightPct"] == 9.0
    assert mini["meanWallW"] < edge["meanWallW"]


def test_brightness_events_are_replayed_into_the_work_metric():
    m = _metrics(Scenario(
        config=_cfg(brightness_pct=100, content="bright"), duration_s=99,
        events=[SimEvent(at_s=50, action="set-brightness", value=0)],
    ))
    assert m["usefulLightPct"] == 45.0  # 50 of 100 ticks at 0.9 × 100


def test_every_metric_a_lab_names_is_measured():
    m = _metrics(Scenario(duration_s=30))
    for lab in LABS:
        for c in lab.criteria:
            assert c.metric in m, (lab.id, c.id, c.metric)
        assert lab.objective.metric in m


def _failed(lab_id: str, scenario: Scenario) -> list[str]:
    return [c.id for c in grade_scenario(lab_id, scenario).criteria if not c.passed]


def test_lab_one_turns_on_zones_that_can_switch_off():
    """Dimming off on the zoned panel, or the edge-lit strip, fails on watts
    alone; dimming the edge-lit panel to 25 W fails on light alone."""
    ref = REFERENCE_SOLUTIONS["dark-mode-that-pays"]
    assert grade_scenario("dark-mode-that-pays", ref).score == 100
    no_dim = ref.model_copy(update={
        "config": ref.config.model_copy(update={"local_dimming": False})})
    assert _failed("dark-mode-that-pays", no_dim) == ["wall"]
    assert _failed("dark-mode-that-pays",
                   Scenario.model_validate(LABS_BY_ID["dark-mode-that-pays"].start)) == ["wall"]
    dimmed = GAMING_ATTEMPTS["dark-mode-that-pays"]["dim the edge-lit panel"]
    assert _failed("dark-mode-that-pays", dimmed) == ["light"]


def test_lab_two_turns_on_delivered_watts_leaving_by_cable():
    """90 W of charging moves the wall ~114 W and the heat 10 W; the panel
    spends the heat budget, and one 5 W step separates pass from fail."""
    ref = REFERENCE_SOLUTIONS["dock-cool-desk"]
    assert grade_scenario("dock-cool-desk", ref).score == 100
    start = Scenario.model_validate(LABS_BY_ID["dock-cool-desk"].start)
    undocked = start.model_copy(update={
        "config": start.config.model_copy(update={"hub_laptop_w": 0})})
    a, b = _metrics(start), _metrics(undocked)
    assert 110 < a["meanWallW"] - b["meanWallW"] < 118
    assert abs((a["peakHeatW"] - b["peakHeatW"]) - 10.0) < 0.05
    # Undocking does not even rescue the heat line on the mini-LED panel.
    assert "heat" in _failed("dock-cool-desk", undocked)
    too_much = GAMING_ATTEMPTS["dock-cool-desk"]["full charge at the floor"]
    assert _failed("dock-cool-desk", too_much) == ["heat"]


def test_lab_three_turns_on_duty_deciding_the_greener_panel():
    """At desk duty the cheaper-to-build edge-lit panel has the lower carbon
    per year; at control-room duty on dark content the mini-LED does. Neither
    lever alone (service life, panel) passes; both together do."""
    def per_year(model: str, life: Lifecycle) -> float:
        cfg = _cfg(model=model, content="dark",
                   local_dimming=(model == "miniled-32"))
        return _metrics(Scenario(config=cfg, lifecycle=life))["carbonPerYearKg"]

    desk = Lifecycle()
    room = Lifecycle(hours_per_day=16, days_per_year=360, service_years=12)
    assert per_year("edge-27", desk) < per_year("miniled-32", desk)
    assert per_year("miniled-32", room) < per_year("edge-27", room)

    assert grade_scenario("greener-control-room",
                          REFERENCE_SOLUTIONS["greener-control-room"]).score == 100
    for name in ("keep the edge-lit panel twelve years",
                 "mini-LED on a six-year refresh"):
        attempt = GAMING_ATTEMPTS["greener-control-room"][name]
        assert _failed("greener-control-room", attempt) == ["carbon"], name


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

    ref = REFERENCE_SOLUTIONS["dock-cool-desk"].model_dump(by_alias=True)
    graded = client.post("/api/labs/dock-cool-desk/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404
