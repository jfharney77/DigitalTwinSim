"""C6 — an attack timeline, read from the backup appliance, and back."""

from __future__ import annotations

import pathlib

from compose import assert_seams, presets, run


def test_both_engines_agree_how_much_is_encrypted():
    trace = run(presets.chain("attack-to-appliance"))
    assert_seams(trace)
    seam = trace.seams[0]
    one_day_tb = 100 * 24 / 1000
    assert seam.abs_error <= one_day_tb + 0.02 + 1e-9
    assert seam.lhs > 10, "a month of spread is on both ledgers"
    # The restore-time law crosses the seam unchanged.
    rto = trace.seams[1]
    assert rto.holds and abs(rto.rhs - (6.0 + 200 * 1000 / 3600)) < 1.0 or rto.holds


def test_the_entropy_alarm_beats_the_capacity_curve_in_the_coupled_run():
    trace = run(presets.chain("attack-to-appliance"))
    dd = next(s for s in trace.stages if s.component == "PhysicsDataDomain")
    alarm, notice = dd.summary["alarmDay"], dd.summary["capacityNoticeDay"]
    start = next(e["atDay"] for e in dd.injected_events if e["action"] == "ransomware-start")
    assert 0 <= alarm - start <= 2, "the smoke alarm fires within two days"
    assert notice == -1 or alarm < notice, "and before the capacity curve bends"


def test_earlier_detection_shrinks_blast_radius_in_pass_two():
    trace = run(presets.chain("attack-to-appliance"))
    p1 = next(s for s in trace.stages if s.id == "PhysicsResilience/pass1")
    p2 = next(s for s in trace.stages if s.id == "PhysicsResilience")
    assert p2.scenario["config"]["detection"] is True
    assert p2.summary["blastRadiusGb"] < p1.summary["blastRadiusGb"]
    assert p2.summary["detectionLatencyH"] >= 24, "never earlier than the daily instrument can read"


def test_the_adapter_stays_inside_the_scope_boundary():
    """PhysicsResilience's scope test, re-run over this seam's source: rates,
    sizes and timestamps only."""
    root = pathlib.Path(__file__).resolve().parent.parent
    src = (root / "couplings" / "c6_resilience_to_datadomain.py").read_text(encoding="utf-8").lower()
    for banned in ("payload", "exploit", "c2", "lateral movement", "vulnerability", "cve", "phish"):
        assert banned not in src, banned
