"""Graded labs (docs/LAB_PATTERN.md): the shared invariants plus this app's
own checks — the service metric, the API surface, the scope boundary, and the
specific physics each lab's 'aha' depends on staying true."""

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
from app.presets import EXPLAINS, VAULTED
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


def _script(*events: tuple[int, str, float | None]) -> list[SimEvent]:
    return [SimEvent(at_h=h, action=a, value=v) for h, a, v in events]


def test_service_is_zero_when_nothing_is_tested():
    """The zero-load case of this app: no incident, so nothing was proven."""
    idle = _metrics(Scenario(config=VAULTED, duration_h=720))
    assert idle["serviceRatePct"] == 0
    assert idle["incidentStartH"] == -1


def test_a_dark_estate_stops_earning_service():
    """Every restore hour is a zero: the slow pipe earns less service than
    the fast one on the same incident, by about the RTO difference."""
    ev = _script((240, "incident", 500), (280, "contain", None),
                 (280, "attempt-restore", None))
    slow = _metrics(Scenario(config=VAULTED, events=ev))
    fast = _metrics(Scenario(
        config=VAULTED.model_copy(update={"restore_gbps": 3.5}), events=ev))
    assert slow["recovered"] == fast["recovered"] == 1
    assert fast["serviceRatePct"] - slow["serviceRatePct"] > 10


def test_an_unrecovered_estate_never_reads_as_clean():
    start = Scenario.model_validate(LABS_BY_ID["two-am-whole-clock"].start)
    m = _metrics(start)
    assert m["recovered"] == 0 and m["onsetToCleanH"] == NEVER
    assert m["serviceRatePct"] < 60  # 200 TB gone in 400 h; never restored


def test_a_run_cut_short_earns_nothing_for_the_missing_hours():
    ev = _script((240, "incident", 500), (280, "contain", None),
                 (280, "attempt-restore", None))
    cfg = VAULTED.model_copy(update={"restore_gbps": 3.5})
    full = _metrics(Scenario(config=cfg, duration_h=720, events=ev))
    cut = _metrics(Scenario(config=cfg, duration_h=320, events=ev))
    assert cut["serviceRatePct"] < full["serviceRatePct"] / 2


def test_every_metric_a_lab_names_is_measured():
    m = _metrics(Scenario(duration_h=48))
    for lab in LABS:
        for c in lab.criteria:
            assert c.metric in m, (lab.id, c.id, c.metric)
        assert lab.objective.metric in m


def test_lab_one_turns_on_the_vault_cadence_not_the_backup_cadence():
    """Hourly backups with a daily gap restore an older copy than six-hourly
    backups with a six-hourly gap: the RPO that survives is the vault's."""
    ref = REFERENCE_SOLUTIONS["back-within-a-day"]
    hourly_daily = ref.model_copy(update={"config": ref.config.model_copy(
        update={"backup_every_h": 1, "vault_sync_every_h": 24})})
    good = grade_scenario("back-within-a-day", ref)
    lazy_gap = grade_scenario("back-within-a-day", hourly_daily)
    assert good.passed and lazy_gap.passed
    assert lazy_gap.metrics["rpoAtRestoreH"] > good.metrics["rpoAtRestoreH"] + 12
    assert lazy_gap.score < good.score
    # And the pipe is what the pass itself turns on: 3.0 GB/s misses 24 h.
    narrow = ref.model_copy(update={"config": ref.config.model_copy(
        update={"restore_gbps": 3.0})})
    failed = [c.id for c in grade_scenario("back-within-a-day", narrow).criteria
              if not c.passed]
    assert failed == ["rto"]


def test_lab_two_turns_on_who_answers_not_how_sharp_the_detector_is():
    """In-house, the queue sets time-to-contain: sensitivity 3 and 7 contain
    at the same hour. With 24/7 response the knob finally matters."""
    ref = REFERENCE_SOLUTIONS["slow-burn-on-a-budget"]

    def ttc(response: str, sensitivity: int) -> float:
        cfg = ref.config.model_copy(update={
            "response": response, "sensitivity": sensitivity})
        return _metrics(ref.model_copy(update={"config": cfg}))["timeToContainH"]

    assert ttc("inhouse", 3) == ttc("inhouse", 7)
    assert ttc("mdr", 7) < ttc("mdr", 3) < ttc("inhouse", 7)
    # One notch past the budget is the only line that fails.
    eight = ref.model_copy(update={
        "config": ref.config.model_copy(update={"sensitivity": 8}),
        "events": [ref.events[0], SimEvent(at_h=205, action="attempt-restore")],
    })
    failed = [c.id for c in grade_scenario("slow-burn-on-a-budget", eight).criteria
              if not c.passed]
    assert failed == ["alarm-budget"]


def test_lab_two_punishes_restore_and_pray_with_the_doubled_rto():
    pray = GAMING_ATTEMPTS["slow-burn-on-a-budget"]["restore and pray"]
    m = _metrics(pray)
    assert m["failedRestores"] == 1
    assert m["rtoHours"] > 2 * _metrics(
        REFERENCE_SOLUTIONS["slow-burn-on-a-budget"])["rtoHours"]


def test_lab_three_is_one_clock_shared_by_every_subsystem():
    """The reference sits exactly on 30 h. An hour of slack anywhere — a late
    restore, a notch less sensitivity, a narrower pipe — breaks only the
    whole-clock line; more pipe buys a notch of sensitivity back."""
    lab_id = "two-am-whole-clock"
    ref = REFERENCE_SOLUTIONS[lab_id]
    assert grade_scenario(lab_id, ref).metrics["onsetToCleanH"] == 30

    def failed(scenario: Scenario) -> list[str]:
        return [c.id for c in grade_scenario(lab_id, scenario).criteria if not c.passed]

    late = ref.model_copy(update={
        "events": [ref.events[0], SimEvent(at_h=134, action="attempt-restore")]})
    assert failed(late) == ["whole-clock"]
    dull = ref.model_copy(update={
        "config": ref.config.model_copy(update={"sensitivity": 6}),
        "events": [ref.events[0], SimEvent(at_h=133, action="attempt-restore")]})
    assert failed(dull) == ["whole-clock"]
    dull_but_wide = dull.model_copy(update={
        "config": dull.config.model_copy(update={"restore_gbps": 5.0})})
    wide = grade_scenario(lab_id, dull_but_wide)
    assert wide.passed and wide.score < grade_scenario(lab_id, ref).score


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


def test_labs_stay_inside_the_scope_boundary():
    """The labs grade defensive architecture. Same banned vocabulary as the
    engine's scope test: no technique detail anywhere in the lab prose."""
    banned = ["exploit", "payload", "phishing", "malware", "evasion",
              "privilege escalation", "cve-", "ransom note", "c2 "]
    for level in (1, 3, 5):
        for lab in LABS:
            text = leveled(lab, level).model_dump_json().lower()
            for word in banned:
                assert word not in text, (lab.id, level, word)


def test_api_serves_labs_and_grades_without_leaking_solutions():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    listing = client.get("/api/labs?level=1")
    assert listing.status_code == 200
    body = listing.json()
    assert [x["id"] for x in body] == [lab.id for lab in LABS]
    assert "reference" not in listing.text.lower()
    # The start scenarios are served; the solutions' signature settings are not.
    for x in body:
        assert x["start"]["config"]["restoreGbps"] == 1.0

    ref = REFERENCE_SOLUTIONS["slow-burn-on-a-budget"].model_dump(by_alias=True)
    graded = client.post("/api/labs/slow-burn-on-a-budget/grade?level=5", json=ref)
    assert graded.status_code == 200
    out = graded.json()
    assert out["passed"] and out["score"] >= PASS_FLOOR
    assert all("measured" in c and "explainId" in c for c in out["criteria"])

    assert client.post("/api/labs/nope/grade", json=ref).status_code == 404
