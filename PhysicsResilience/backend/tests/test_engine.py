"""Full-trace invariants for the resilience engine — spec 05's
mechanics as pytest: the air gap holds, RPO/RTO arithmetic, the
detection branch, the response clock, and the access graph. Plus the
scope boundary itself."""

from __future__ import annotations

from app.anatomy import MAPS
from app.constants import value as C
from app.engine import business_hours, simulate
from app.models import SCOPE_NOTE, Scenario, SimEvent
from app.presets import (
    BLIND,
    DETECTING,
    INHOUSE,
    MDR_247,
    PERIMETER,
    REPO_ONLY,
    VAULTED,
    ZT,
)

INCIDENT = [
    SimEvent(at_h=240, action="incident", value=500),
    SimEvent(at_h=280, action="contain"),
    SimEvent(at_h=290, action="attempt-restore"),
]


def run(s: Scenario):
    return simulate(s)


def test_scope_boundary_is_stated_and_abstract():
    """The hard boundary, enforced: the scope note exists, says what it
    must, and the engine's vocabulary stays architectural."""
    assert "defensive architecture" in SCOPE_NOTE
    assert "No exploit content" in SCOPE_NOTE
    import app.engine as engine_module

    src = open(engine_module.__file__, encoding="utf-8").read().lower()
    for banned in ("payload", "exploit", "c2", "lateral movement technique"):
        assert banned not in src, f"engine vocabulary must stay abstract: {banned}"


def test_determinism():
    s = Scenario(config=VAULTED, duration_h=400, events=INCIDENT[:1])
    a, _, _ = run(s)
    b, _, _ = run(s)
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]


def test_the_air_gap_holds():
    """The incident corrupts every repository copy and no vault copy —
    the architecture's whole claim, asserted."""
    trace, _, _ = run(Scenario(config=VAULTED, duration_h=400,
                               events=[SimEvent(at_h=240, action="incident", value=500)]))
    late = trace[-1]
    assert late.repo_copies_intact == 0, "reachable copies die with production"
    assert late.vault_copies_intact > 0, "vaulted copies survive — the gap held"


def test_vault_recovers_repo_only_does_not():
    _, _, vaulted = run(Scenario(config=VAULTED, duration_h=720, events=INCIDENT))
    _, log, repo = run(Scenario(config=REPO_ONLY, duration_h=720, events=INCIDENT))
    assert vaulted.recovery_succeeded
    assert vaulted.data_recovered_tb == VAULTED.estate_tb
    assert not repo.recovery_succeeded, "nothing intact to restore from"
    assert any("No backup exists intact" in e.message or "CORRUPT" in e.message
               for e in log)


def test_rto_is_decision_plus_bandwidth():
    _, _, summary = run(Scenario(config=VAULTED, duration_h=720, events=INCIDENT))
    expected = C("decision_hours") + VAULTED.estate_tb * 1000 / (
        VAULTED.restore_gbps * 3600
    )
    assert abs(summary.rto_hours - expected) < 2.0
    assert summary.rto_hours > 48, "200 TB at 1 GB/s is a days-scale affair"


def test_rpo_tracks_the_newest_clean_copy():
    trace, _, _ = run(Scenario(config=VAULTED, duration_h=400,
                               events=[SimEvent(at_h=240, action="incident", value=500)]))
    before = next(s for s in trace if s.t_h == 239)
    assert before.last_clean_point_age_h <= VAULTED.backup_every_h
    after = next(s for s in trace if s.t_h == 350)
    assert after.last_clean_point_age_h > 100, (
        "post-incident copies are worthless; the clean point ages"
    )


def test_detection_names_the_point_blindness_doubles_the_rto():
    slow = [
        SimEvent(at_h=200, action="slow-incident", value=20),
        SimEvent(at_h=560, action="contain"),
        SimEvent(at_h=570, action="attempt-restore"),
    ]
    _, _, seeing = run(Scenario(config=DETECTING, duration_h=1080, events=slow))
    _, log_b, blind = run(Scenario(config=BLIND, duration_h=1080, events=slow))
    assert seeing.recovery_succeeded and seeing.failed_restores == 0
    assert blind.failed_restores >= 1, "restore-and-pray fails first"
    assert blind.rto_hours > seeing.rto_hours * 1.7
    assert any("CORRUPT" in e.message for e in log_b)


def test_sensitivity_trades_latency_for_false_alarms():
    lax = DETECTING.model_copy(update={"sensitivity": 2})
    keen = DETECTING.model_copy(update={"sensitivity": 10})
    ev = [SimEvent(at_h=100, action="incident", value=100)]
    _, _, s_lax = run(Scenario(config=lax, duration_h=1440, events=ev))
    _, _, s_keen = run(Scenario(config=keen, duration_h=1440, events=ev))
    assert s_keen.detection_latency_h < s_lax.detection_latency_h
    assert s_keen.false_alarms > s_lax.false_alarms
    assert s_keen.false_alarms * C("investigation_h_per_alarm") > 0


def test_two_am_saturday():
    """Same incident at Saturday 02:00: MDR contains in minutes,
    in-house waits for Monday — blast radius orders apart."""
    ev = [SimEvent(at_h=122, action="incident", value=300)]
    assert not business_hours(122), "t=122 must be Saturday 02:00"
    assert not any(business_hours(t) for t in range(122, 176)), (
        "no business hour until Monday 08:00"
    )
    _, _, mdr = run(Scenario(config=MDR_247, duration_h=336, events=ev))
    _, _, inh = run(Scenario(config=INHOUSE, duration_h=336, events=ev))
    assert mdr.time_to_contain_h < 12
    assert inh.time_to_contain_h > 50, "nobody is at a desk until Monday"
    assert inh.time_to_contain_h > 0
    assert inh.blast_radius_gb > mdr.blast_radius_gb * 3


def test_alert_fatigue_delays_containment():
    noisy = INHOUSE.model_copy(update={"noise_alerts_day": 300})
    ev = [SimEvent(at_h=100, action="incident", value=300)]
    trace, _, s_noisy = run(Scenario(config=noisy, duration_h=336, events=ev))
    _, _, s_calm = run(Scenario(config=INHOUSE, duration_h=336, events=ev))
    assert max(s.alerts_backlog for s in trace) > 50, "the backlog must grow"
    # Containment may never happen at all under this noise — either way
    # the damage ordering holds.
    assert s_noisy.blast_radius_gb > s_calm.blast_radius_gb * 2


def test_perimeter_floods_zero_trust_does_not():
    ev = [SimEvent(at_h=100, action="compromise")]
    _, _, per = run(Scenario(config=PERIMETER, duration_h=336, events=ev))
    _, _, zt = run(Scenario(config=ZT, duration_h=336, events=ev))
    assert per.peak_reachable_assets >= int(PERIMETER.assets * 0.85)
    assert zt.peak_reachable_assets <= 10, "the grant list, divided by segments"
    assert zt.peak_reachable_assets < per.peak_reachable_assets / 5


def test_zero_trust_friction_is_priced():
    ev = [SimEvent(at_h=10, action="compromise")]
    zt_trace, _, _ = run(Scenario(config=ZT, duration_h=48, events=ev))
    per_trace, _, _ = run(Scenario(config=PERIMETER, duration_h=48, events=ev))
    assert zt_trace[-1].policy_checks_per_session > \
        per_trace[-1].policy_checks_per_session * 5


def test_privilege_decay_and_review():
    no_review = ZT.model_copy(update={"review_cadence_days": 0})
    trace_n, _, _ = run(Scenario(config=no_review, duration_h=2160))
    trace_r, _, _ = run(Scenario(config=ZT, duration_h=2160))
    assert trace_n[-1].stale_grants > 100, "entropy accumulates without review"
    assert trace_r[-1].stale_grants < trace_n[-1].stale_grants / 2


def test_backup_storage_grows_with_retention_sublinearly():
    short = VAULTED.model_copy(update={"retention_copies": 7})
    long = VAULTED.model_copy(update={"retention_copies": 60})
    a, _, _ = run(Scenario(config=short, duration_h=2000))
    b, _, _ = run(Scenario(config=long, duration_h=2000))
    assert b[-1].backup_storage_tb > a[-1].backup_storage_tb
    assert b[-1].backup_storage_tb < a[-1].backup_storage_tb * (60 / 7), (
        "dedupe keeps retention sublinear — to a point"
    )


def test_region_load_matches_map():
    region_ids = {r.id for r in MAPS["powerprotect"].regions}
    trace, _, _ = run(Scenario(config=VAULTED, duration_h=48))
    for s in trace:
        assert set(s.region_load.keys()) == region_ids


def test_engine_is_pure():
    import ast

    import app.engine as engine_module

    tree = ast.parse(open(engine_module.__file__, encoding="utf-8").read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & {
        "fastapi", "time", "asyncio", "threading", "os", "io", "random",
    }
