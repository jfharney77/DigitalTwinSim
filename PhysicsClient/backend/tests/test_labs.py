"""Graded labs (docs/LAB_PATTERN.md): the shared invariants plus this app's
own checks — the work metrics, the API surface, and the specific physics each
lab's 'aha' depends on staying true."""

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
from app.models import Environment, Scenario, Workload
from app.presets import AW_LAPTOP, EXPLAINS
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


def test_every_signature_explain_entry_is_used_by_some_lab():
    cited = {c.explain_id for lab in LABS for c in lab.criteria}
    assert cited == {e.id for e in EXPLAINS}


def _metrics(scenario: Scenario) -> dict[str, float]:
    trace, _log, summary = simulate(scenario)
    return measure(scenario, trace, summary, validate(scenario))


def test_work_is_zero_at_idle_and_scales_with_load():
    idle = _metrics(Scenario(workload=Workload(), duration_s=120))
    half = _metrics(Scenario(workload=Workload(cpu_pct=50, gpu_pct=50), duration_s=120))
    full = _metrics(Scenario(workload=Workload(cpu_pct=95, gpu_pct=95), duration_s=120))
    assert idle["workRateW"] == 0
    assert idle["meanTokensPerS"] == 0
    assert 0 < half["workRateW"] < full["workRateW"]


def test_a_dead_machine_stops_earning():
    dead = GAMING_ATTEMPTS["hour-of-tokens"]["faster engine: the GPU"]
    m = _metrics(dead)
    assert m["shutdown"] == 1
    # The GPU makes 45 tok/s while it lives; the dark minutes pull the mean down.
    assert m["meanTokensPerS"] < 40
    trace, _log, _s = simulate(dead)
    assert trace[-1].tokens_per_s == 0


def test_every_metric_a_lab_names_is_measured():
    m = _metrics(Scenario(duration_s=30))
    for lab in LABS:
        for c in lab.criteria:
            assert c.metric in m, (lab.id, c.id, c.metric)
        assert lab.objective.metric in m


def _only_failure(lab_id: str, scenario: Scenario) -> list[str]:
    return [c.id for c in grade_scenario(lab_id, scenario).criteria if not c.passed]


def test_lab_one_turns_on_the_surplus_and_the_boost():
    """The 240 W charger cannot both feed the work floor and charge the pack;
    with the 330 W charger the only thing left is the GPU's boost at 100%."""
    ref = REFERENCE_SOLUTIONS["charge-while-you-play"]
    small = ref.model_copy(update={
        "config": ref.config.model_copy(update={"charger_w": 240}),
    })
    assert "ends-charged" in _only_failure("charge-while-you-play", small)
    at_100 = GAMING_ATTEMPTS["charge-while-you-play"]["big charger, exactly 100% GPU"]
    assert _only_failure("charge-while-you-play", at_100) == ["no-throttle"]


def test_lab_two_every_passenger_matters_and_full_speed_is_most_efficient():
    """Put any one passenger back and the pack misses its reserve; and system
    tokens per Wh rises with NPU load because the base is a fixed cost."""
    ref = REFERENCE_SOLUTIONS["hour-of-tokens"]
    for update in ({"gpu_tgp_w": 80}, {"ram_gb": 64}):
        worse = ref.model_copy(update={
            "config": ref.config.model_copy(update=update)})
        assert "reserve" in _only_failure("hour-of-tokens", worse), update
    busy_cpu = ref.model_copy(update={
        "workload": ref.workload.model_copy(update={"cpu_pct": 10})})
    assert "reserve" in _only_failure("hour-of-tokens", busy_cpu)

    slower = ref.model_copy(update={
        "workload": ref.workload.model_copy(update={"npu_pct": 92})})
    assert grade_scenario("hour-of-tokens", slower).passed
    assert _metrics(slower)["tokensPerWh"] < _metrics(ref)["tokensPerWh"]
    assert _metrics(slower)["endBatteryPct"] > _metrics(ref)["endBatteryPct"]


def test_lab_three_the_charger_is_a_heater():
    """Same build, same dials: the bigger charger pushes more charge, makes
    more heat, and the skin governor takes it out of the compute."""
    ref = REFERENCE_SOLUTIONS["warm-lap-no-clamp"]
    big = ref.model_copy(update={
        "config": ref.config.model_copy(update={"charger_w": 240})})
    a, b = _metrics(ref), _metrics(big)
    assert a["throttleSeconds"] == 0 and b["throttleSeconds"] > 0
    assert b["peakSkinTempC"] > a["peakSkinTempC"]
    assert b["endBatteryPct"] > a["endBatteryPct"]
    # And the best a 240 W charger can do stays under the floor.
    best_240 = GAMING_ATTEMPTS["warm-lap-no-clamp"]["big charger, best possible tuning"]
    assert _only_failure("warm-lap-no-clamp", best_240) == ["work"]


def test_environment_constraints_are_measured_from_events():
    from app.models import SimEvent

    sc = Scenario(
        config=AW_LAPTOP, workload=Workload(cpu_pct=50, gpu_pct=50),
        environment=Environment(on_lap=True),
        events=[SimEvent(at_s=10, action="set-on-lap", value=0),
                SimEvent(at_s=20, action="set-ambient", value=12)],
        duration_s=60,
    )
    m = _metrics(sc)
    assert m["offLapSeconds"] == 51
    assert m["minAmbientC"] == 12


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
        assert [c.threshold for c in expert.criteria] == [c.threshold for c in lab.criteria]


def test_api_serves_labs_and_grades_without_leaking_solutions():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    listing = client.get("/api/labs?level=1")
    assert listing.status_code == 200
    body = listing.json()
    assert [x["id"] for x in body] == [lab.id for lab in LABS]
    assert "reference" not in listing.text.lower()
    # No lab ships its own answer as the start scenario.
    for x, lab in zip(body, LABS):
        assert x["start"] != REFERENCE_SOLUTIONS[lab.id].model_dump(by_alias=True)

    ref = REFERENCE_SOLUTIONS["hour-of-tokens"].model_dump(by_alias=True)
    graded = client.post("/api/labs/hour-of-tokens/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404
