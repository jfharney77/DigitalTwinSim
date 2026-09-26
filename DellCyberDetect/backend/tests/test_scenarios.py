"""The failure scenario: dwell time exceeds snapshot retention.

House style: assert over the whole trace. The shared invariants come from
twinkit.testing; what stays here is what must hold *because* the failure
happened — above all, that the product never certifies a corrupted copy as
clean, even when every retained copy is corrupted and somebody wants an
answer."""

from __future__ import annotations

import hashlib
import json

from fastapi.testclient import TestClient

from app.anatomy import ANATOMY, TOTAL_SNAPSHOTS
from app.engine import ANALYSIS_PHASES, simulate
from app.main import app
from app.scenarios import (
    BASELINE,
    BASELINE_RPO_HOURS,
    DWELL_EXCEEDS_RETENTION,
    RETENTION_HOURS,
    SCENARIOS,
    VAULT_SOURCE,
    simulate_dwell_exceeds_retention,
    simulate_scenario,
)
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PHASE_ORDER = [
    "clean", "intrusion", "encrypt", "blind",
    "inspect", "classify", "verdict", "recover", "restored",
]
PROFILE = TraceProfile(phases=PHASE_ORDER, anatomy=ANATOMY)
SNAPS = {f"snap-{i}" for i in range(1, TOTAL_SNAPSHOTS + 1)}

# Fields added for failure scenarios. Everything else on the baseline trace
# is pinned byte-for-byte below.
ADDITIVE = {
    "snapshotsExpired", "verdict", "recoverySource",
    "recoveryPointAgeHours", "failedRegions",
}
# sha256 of the baseline trace's JSON (level 3, sorted keys), additive fields
# excluded. Re-pinned deliberately after the student-review pass, which
# changed the baseline itself: a uniform 30 h snapshot interval (intrusion at
# t+24 h with three copies, encryption at t+66 h), the named copy's timestamp
# (lastCleanTakenAtHours), and prose that states what triggers inspection
# and what the precise restore still loses. Scenario work must not move it.
BASELINE_SHA256 = "3e930aba96f0bd6e4ba909a20790ca994e59276bf6bdd86b4abc6b366be0c1a2"

fail = simulate_dwell_exceeds_retention


def _retained(s) -> int:
    return s.snapshots_taken - s.snapshots_expired


def test_trace_invariants():
    assert_trace_invariants(fail(), PROFILE)
    assert_deterministic(fail)


def test_scenarios_module_is_pure():
    import app.scenarios as module

    assert_engine_is_pure(module)


def test_the_happy_path_is_byte_identical_to_before():
    """The baseline incident did not move. Every field it had before is
    hashed; only the additive fields are left out of the hash."""
    dumped = [
        {k: v for k, v in s.model_dump(by_alias=True).items() if k not in ADDITIVE}
        for s in simulate()
    ]
    blob = json.dumps(dumped, sort_keys=True, ensure_ascii=False)
    assert hashlib.sha256(blob.encode()).hexdigest() == BASELINE_SHA256
    assert simulate_scenario(BASELINE) == simulate()
    # And the baseline never uses the failure vocabulary.
    for s in simulate():
        assert s.failed_regions == []
        assert s.snapshots_expired == 0
        assert s.verdict in ("", "clean-copy-named")


def test_each_scenario_carries_its_own_leveled_page_copy():
    """The intro and the two notes describe the trace beside them. The
    baseline's copy talks about four ruined snapshots; on the failure trace
    that would contradict a map showing seven of seven, so each scenario
    brings its own, and every block has reading-level variants."""
    from app.leveling import registry

    by_id = {s.id: s for s in SCENARIOS}
    for info in SCENARIOS:
        for text in (info.heading, info.intro, info.map_note, info.counters_note):
            assert text
        for text in (info.intro, info.map_note, info.counters_note):
            assert registry().get(text), f"{info.id}: unleveled page copy"
    assert "four snapshots" in by_id[BASELINE].intro
    assert "four" not in by_id[DWELL_EXCEEDS_RETENTION].intro
    assert "seven" in by_id[DWELL_EXCEEDS_RETENTION].intro
    # Both map notes point at the tab that holds the tour.
    for info in SCENARIOS:
        assert "Guided tour" in info.map_note
    # The failure note quotes both recovery points, and they are the trace's.
    recover = next(s for s in fail() if s.phase == "recover")
    note = by_id[DWELL_EXCEEDS_RETENTION].counters_note
    assert f"{recover.recovery_point_age_hours}h" in note
    assert f"{BASELINE_RPO_HOURS}h" in note


def test_the_trigger_for_inspection_is_stated_at_every_level():
    """Alerts are zero, so something else must start the content read. Both
    traces say what, at every authored level: an on-demand run after a user
    report, because scanning was not scheduled."""
    from app.leveling import registry

    for trace in (simulate(), fail()):
        step = next(s for s in trace if s.phase == "inspect")
        for text in [step.description, *registry()[step.description].values()]:
            low = text.lower()
            assert "report" in low or "notices" in low, text
            assert (
                "schedule" in low or "timetable" in low or "by hand" in low
            ), text


def test_the_premise_dwell_really_exceeds_retention():
    """Tested, not asserted: corruption runs for longer than the array keeps
    snapshots before anyone inspects, and the window really is full of
    corruption when they do."""
    trace = fail()
    first_corrupt = next(s for s in trace if s.snapshots_corrupted > 0)
    inspect = next(s for s in trace if s.phase == "inspect")
    assert inspect.elapsed_hours - first_corrupt.elapsed_hours > RETENTION_HOURS
    assert _retained(inspect) == TOTAL_SNAPSHOTS
    assert inspect.snapshots_corrupted == _retained(inspect)


def test_each_scenario_states_a_retention_its_own_trace_obeys():
    """Retention in hours is slots x interval, and the two incidents run at
    different cadences. The baseline's window is wider than its whole trace,
    which is why nothing expires there; the failure's is not."""
    from app.scenarios import BASELINE_RETENTION_HOURS

    by_id = {s.id: s for s in SCENARIOS}
    assert by_id[BASELINE].retention_hours == BASELINE_RETENTION_HOURS
    assert by_id[DWELL_EXCEEDS_RETENTION].retention_hours == RETENTION_HOURS
    assert BASELINE_RETENTION_HOURS > RETENTION_HOURS
    base = simulate()
    assert base[-1].elapsed_hours < BASELINE_RETENTION_HOURS
    assert all(s.snapshots_expired == 0 for s in base)
    assert fail()[-1].elapsed_hours > RETENTION_HOURS
    assert fail()[-1].snapshots_expired > 0


def test_the_window_rolls_and_never_holds_more_than_the_map_draws():
    trace = fail()
    for prev, cur in zip(trace, trace[1:]):
        assert cur.snapshots_taken >= prev.snapshots_taken
        assert cur.snapshots_expired >= prev.snapshots_expired
    for s in trace:
        assert 1 <= _retained(s) <= TOTAL_SNAPSHOTS
        assert s.snapshots_corrupted <= _retained(s)


def test_a_corrupted_copy_is_never_certified_clean():
    """THE invariant of the failure. Every retained copy is corrupted and
    somebody wants a snapshot number; the product does not supply one. A
    'least bad' answer here would be a false negative with a certificate
    on it."""
    trace = fail()
    for s in trace:
        assert s.last_clean_snapshot == -1, (
            f"step {s.step} ({s.phase}): named snapshot "
            f"{s.last_clean_snapshot} while every retained copy is corrupt"
        )
        assert s.verdict != "clean-copy-named"
    verdict = next(s for s in trace if s.phase == "verdict")
    assert _retained(verdict) - verdict.snapshots_corrupted == 0  # the hero number
    assert verdict.verdict == "no-clean-copy-on-array"
    assert "verdict" in verdict.active_regions, "a no is still a verdict"


def test_no_false_negative_in_any_scenario():
    """The general form, across every scenario served: a named copy must be
    older than every corrupted one. Corruption occupies the newest
    ``snapshots_corrupted`` retained slots."""
    for info in SCENARIOS:
        for s in simulate_scenario(info.id):
            if s.last_clean_snapshot > 0 and s.snapshots_corrupted > 0:
                first_corrupt = _retained(s) - s.snapshots_corrupted + 1
                assert s.last_clean_snapshot < first_corrupt, (info.id, s.step)


def test_confidence_still_comes_only_from_content():
    trace = fail()
    idx = next(i for i, s in enumerate(trace) if s.phase == "inspect")
    for s in trace[: idx + 1]:
        assert s.content_confidence_percent == 0
        assert s.verdict == ""
    for s in trace:
        if s.phase in ANALYSIS_PHASES:
            assert s.content_confidence_percent >= 99
    assert all(s.metadata_alerts == 0 for s in trace)


def test_bad_news_costs_the_same_to_produce():
    """No shortcut because the answer is unwelcome: inspection is still the
    unique longest stage."""
    trace = fail()
    top = max(s.cycle_cost for s in trace)
    assert [s.phase for s in trace if s.cycle_cost == top] == ["inspect"]


def test_recovery_names_an_off_array_source():
    trace = fail()
    recover = [s for s in trace if s.phase == "recover"]
    assert recover
    for s in recover:
        assert s.recovery_source == VAULT_SOURCE
        assert not s.recovery_source.startswith("array")
        assert not (SNAPS & set(s.active_regions)), (
            "an array snapshot took part in a recovery that had no clean one"
        )
        assert "array" in s.active_regions  # the target, not the source
    for s in trace:
        if s.phase not in ("recover", "restored"):
            assert s.recovery_source == ""


def test_the_array_restore_path_fails_before_recovery_moves_off_array():
    trace = fail()
    failed_at = [s.step for s in trace if "recovery" in s.failed_regions]
    recover_at = next(s.step for s in trace if s.phase == "recover")
    assert failed_at and max(failed_at) < recover_at
    ids = {r.id for r in ANATOMY.regions}
    for s in trace:
        assert set(s.failed_regions) <= ids


def test_the_price_is_the_recovery_point():
    """The vault saves the data and costs age: the RPO is strictly worse
    than the baseline's, and so is the time to get there."""
    recover = next(s for s in fail() if s.phase == "recover")
    base = next(s for s in simulate() if s.phase == "recover")
    assert base.recovery_point_age_hours == BASELINE_RPO_HOURS
    assert recover.recovery_point_age_hours > base.recovery_point_age_hours
    assert recover.cycle_cost > base.cycle_cost
    # The vault copy predates the corruption.
    first_corrupt = next(s for s in fail() if s.snapshots_corrupted > 0)
    taken_at = recover.elapsed_hours - recover.recovery_point_age_hours
    assert taken_at < first_corrupt.elapsed_hours


def test_service_ends_on_a_checked_baseline():
    last = fail()[-1]
    assert last.phase == "restored"
    assert last.snapshots_corrupted == 0
    assert {"inspect", "classifier"} <= set(last.active_regions)
    # The array holds a clean copy again, so the UI stops saying it has
    # none: the old verdict is history, the checked baseline is the state.
    assert _retained(last) - last.snapshots_corrupted >= 1
    assert f"snap-{TOTAL_SNAPSHOTS}" in last.active_regions


def test_scenario_data_cites_its_sources():
    by_id = {s.id: s for s in SCENARIOS}
    assert list(by_id) == [BASELINE, DWELL_EXCEEDS_RETENTION]
    info = by_id[DWELL_EXCEEDS_RETENTION]
    assert len(info.sources) >= 3
    assert all(src.url.startswith("https://") for src in info.sources)
    assert any("dell.com" in src.url for src in info.sources)


def test_prose_is_leveled_at_1_3_5():
    client = TestClient(app)
    path = f"/api/detect?scenario={DWELL_EXCEEDS_RETENTION}"
    l1, l3, l5 = (
        client.get(f"{path}&level={n}").json()["trace"] for n in (1, 3, 5)
    )
    for a, b, c in zip(l1, l3, l5):
        assert len({a["description"], b["description"], c["description"]}) == 3
        assert len(a["description"]) > len(c["description"])
        for key in a:
            if key != "description":
                assert a[key] == b[key] == c[key]


def test_the_endpoint_serves_both_and_refuses_unknowns():
    client = TestClient(app)
    plain = client.get("/api/detect").json()
    assert plain == client.get(f"/api/detect?scenario={BASELINE}").json()
    assert plain["scenario"] == BASELINE
    body = client.get(f"/api/detect?scenario={DWELL_EXCEEDS_RETENTION}").json()
    assert body["scenario"] == DWELL_EXCEEDS_RETENTION
    assert all(s["lastCleanSnapshot"] == -1 for s in body["trace"])
    assert client.get("/api/detect?scenario=nope").status_code == 404
    listed = client.get("/api/scenarios").json()
    assert [s["id"] for s in listed] == [BASELINE, DWELL_EXCEEDS_RETENTION]
    assert listed[1]["heroValue"] == "0"
