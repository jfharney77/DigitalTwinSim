"""Full-trace invariants for the ME5 RAID engine — the spec's scenarios
as pytest, plus the two conservation identities in the house style
(Alienware's energy identity, IR7000's heat balance): the per-tick IOPS
ledger and the exact capacity arithmetic."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.constants import value as C
from app.engine import capacity_ledger, simulate
from app.models import ArrayConfig, Scenario, SimEvent, Workload
from app.presets import ALL_FLASH, ENTRY, OLTP, R6_CAPACITY, R10_PERF

# served/backend kIOPS are rounded to 3 decimals independently.
ROUND_TOL = 0.02


def run(scenario: Scenario):
    return simulate(scenario)


def test_determinism():
    s = Scenario(config=R10_PERF, workload=OLTP, duration_min=200)
    a, _, _ = run(s)
    b, _, _ = run(s)
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]


def test_iops_balance_every_tick():
    """THE identity: backend disk I/O equals served reads × read cost +
    served writes × write penalty, every tick of every scenario — the
    RAID write penalty as an asserted fact of the ledger."""
    scenarios = [
        Scenario(config=R10_PERF, workload=OLTP, duration_min=120),
        Scenario(config=R6_CAPACITY,
                 workload=Workload(offered_kiops=0.5, read_pct=60, block_kb=64),
                 duration_min=2000, tick_minutes=30,
                 events=[SimEvent(at_min=60, action="fail-drive", index=3)]),
        Scenario(config=ALL_FLASH,
                 workload=Workload(offered_kiops=400, read_pct=70, block_kb=8),
                 duration_min=120),
    ]
    for s in scenarios:
        trace, _, _ = run(s)
        for st in trace:
            expected = (
                st.served_read_kiops * st.read_cost
                + st.served_write_kiops * st.write_penalty
            )
            assert abs(st.backend_disk_kiops - expected) <= ROUND_TOL, f"t={st.t}"


def test_capacity_arithmetic_closes_exactly():
    """raw = usable + protection overhead + spares, exactly, for every
    RAID level — the build plan's raw→usable→effective identity."""
    for cfg in (
        ENTRY, R10_PERF, R6_CAPACITY, ALL_FLASH,
        ArrayConfig(model="ME5012", drive_count=2, raid_level="1", spares=0),
    ):
        raw, usable, overhead, spare = capacity_ledger(cfg)
        assert raw == usable + overhead + spare, cfg.raid_level
        assert usable > 0
        trace, _, _ = run(Scenario(config=cfg, duration_min=20))
        st = trace[-1]
        assert st.raw_tb == raw and st.usable_tb == usable
        assert st.raw_tb == st.usable_tb + st.overhead_tb + st.spare_tb


def test_raid10_capacity_is_half_and_r6_is_n_minus_2():
    _, usable10, _, _ = capacity_ledger(R10_PERF)
    assert usable10 == 24 // 2 * 4
    _, usable6, _, _ = capacity_ledger(R6_CAPACITY)
    assert usable6 == (12 - 1 - 2) * 20  # 12 drives, 1 spare, dual parity


def test_write_penalty_ratio_r10_vs_r6():
    """The spec's key scenario: same drives, saturating pure-write load —
    served write IOPS differ by exactly the 6:2 penalty ratio."""
    wl = Workload(offered_kiops=10.0, read_pct=0, block_kb=8)
    r10 = R10_PERF.model_copy(update={"raid_level": "10"})
    r6 = R10_PERF.model_copy(update={"raid_level": "6"})
    t10, _, _ = run(Scenario(config=r10, workload=wl, duration_min=60))
    t6, _, _ = run(Scenario(config=r6, workload=wl, duration_min=60))
    w10, w6 = t10[-1].served_write_kiops, t6[-1].served_write_kiops
    assert t10[-1].saturated and t6[-1].saturated
    assert abs(w10 / w6 - 3.0) < 0.05, (w10, w6)


def test_rebuild_of_20tb_takes_days_and_scales_with_drive_size():
    """The other key scenario: 20 TB spindle rebuilds are measured in
    days, and the window scales linearly with drive size."""
    def window(tb: int) -> float:
        cfg = R6_CAPACITY.model_copy(update={"drive_tb": tb})
        s = Scenario(
            config=cfg,
            workload=Workload(offered_kiops=0.4, read_pct=60, block_kb=64),
            duration_min=200000, tick_minutes=120,
            events=[SimEvent(at_min=120, action="fail-drive", index=3)],
        )
        _, _, summary = run(s)
        assert not summary.data_lost
        assert summary.rebuild_hours_total > 0, "rebuild must have run"
        return summary.rebuild_hours_total

    h20 = window(20)
    assert h20 > 72, f"20 TB must take days, got {h20} h"
    h8 = window(8)
    ratio = h20 / h8
    assert 2.0 < ratio < 3.2, f"window should scale ~linearly (20/8), got {ratio}"


def test_risk_gauge_prices_r5_far_above_r6_in_the_window():
    def peak_risk(level: str) -> float:
        cfg = R6_CAPACITY.model_copy(update={"raid_level": level})
        s = Scenario(
            config=cfg,
            workload=Workload(offered_kiops=0.4, read_pct=60, block_kb=64),
            duration_min=4000, tick_minutes=60,
            events=[SimEvent(at_min=60, action="fail-drive", index=3)],
        )
        trace, _, _ = run(s)
        return max(st.risk_index for st in trace)

    r5, r6 = peak_risk("5"), peak_risk("6")
    assert r5 > 3 * r6, (r5, r6)
    assert r5 > 50


def test_second_failure_mid_rebuild_r6_survives_r5_does_not():
    def outcome(level: str):
        cfg = R6_CAPACITY.model_copy(update={"raid_level": level})
        s = Scenario(
            config=cfg,
            workload=Workload(offered_kiops=0.4, read_pct=60, block_kb=64),
            duration_min=10080, tick_minutes=60,
            events=[
                SimEvent(at_min=60, action="fail-drive", index=3),
                SimEvent(at_min=1500, action="fail-drive", index=7),
            ],
        )
        trace, log, summary = run(s)
        return trace, log, summary

    _, _, s6 = outcome("6")
    assert not s6.data_lost and s6.offline_reason == ""
    t5, log5, s5 = outcome("5")
    assert s5.data_lost
    assert "tolerate" in s5.offline_reason or "tolerate" in s5.offline_reason.lower() \
        or "tolerat" in s5.offline_reason
    assert t5[-1].served_kiops == 0 and not t5[-1].online
    assert any(e.severity == "critical" for e in log5)


def test_degraded_reads_cost_more_on_parity_raid():
    s = Scenario(
        config=R6_CAPACITY,
        workload=Workload(offered_kiops=0.3, read_pct=100, block_kb=8),
        duration_min=600, tick_minutes=10,
        events=[SimEvent(at_min=100, action="fail-drive", index=2)],
    )
    trace, _, _ = run(s)
    before = next(st for st in trace if st.t == 90)
    after = next(st for st in trace if st.t == 200)
    assert before.read_cost == 1.0
    assert after.read_cost > 1.0 and after.degraded
    assert after.latency_ms > before.latency_ms


def test_controller_failover_service_survives_at_a_price():
    s = Scenario(
        config=ALL_FLASH,
        workload=Workload(offered_kiops=400, read_pct=100, block_kb=8),
        duration_min=300,
        events=[SimEvent(at_min=150, action="fail-controller")],
    )
    trace, log, summary = run(s)
    before = next(st for st in trace if st.t == 140)
    after = trace[-1]
    assert after.online and not summary.data_lost
    assert after.controllers_alive == 1
    assert after.served_kiops < before.served_kiops, "the ceiling halves"
    assert after.latency_ms > before.latency_ms
    assert any("survivor" in e.message.lower() for e in log)


def test_both_controllers_down_is_offline():
    s = Scenario(
        config=R10_PERF, workload=OLTP, duration_min=200,
        events=[
            SimEvent(at_min=50, action="fail-controller"),
            SimEvent(at_min=100, action="fail-controller"),
        ],
    )
    trace, _, summary = run(s)
    assert summary.offline_reason == "both controllers down"
    assert trace[-1].served_kiops == 0
    assert not summary.data_lost, "offline is not data loss"


def test_no_spare_means_degraded_until_replacement():
    cfg = R10_PERF  # spares=0
    s = Scenario(
        config=cfg, workload=OLTP, duration_min=400,
        events=[
            SimEvent(at_min=50, action="fail-drive", index=5),
            SimEvent(at_min=200, action="replace-drive", index=5),
        ],
    )
    trace, log, _ = run(s)
    mid = next(st for st in trace if st.t == 150)
    assert mid.degraded and not mid.rebuilding
    assert any("no hot spare" in e.message.lower() for e in log)
    late = next(st for st in trace if st.t == 210)
    assert late.rebuilding


def test_all_flash_hits_the_frontend_ceiling_not_the_drives():
    s = Scenario(
        config=ALL_FLASH,
        workload=Workload(offered_kiops=500, read_pct=100, block_kb=8),
        duration_min=100,
        events=[SimEvent(at_min=50, action="fail-controller")],
    )
    trace, _, _ = run(s)
    late = trace[-1]
    # One controller: front-end cap binds below the SSD disk budget.
    assert abs(late.served_kiops - C("ctrl_cap_kiops")) < 1.0
    assert late.saturated


def test_saturation_climbs_the_latency_curve():
    light, _, _ = run(Scenario(
        config=R10_PERF,
        workload=Workload(offered_kiops=0.5, read_pct=70, block_kb=8),
        duration_min=60,
    ))
    heavy, _, _ = run(Scenario(
        config=R10_PERF,
        workload=Workload(offered_kiops=20, read_pct=70, block_kb=8),
        duration_min=60,
    ))
    assert heavy[-1].saturated and not light[-1].saturated
    assert heavy[-1].latency_ms > 2 * light[-1].latency_ms


def test_region_states_match_anatomy():
    """Engine ↔ anatomy contract: every region id the engine paints
    exists in the map, and every map region gets painted."""
    region_ids = {r.id for r in ANATOMY.regions}
    trace, _, _ = run(Scenario(config=ENTRY, workload=OLTP, duration_min=30))
    for st in trace:
        assert set(st.region_states.keys()) == region_ids


def test_timestep_and_trace_length():
    s = Scenario(config=ENTRY, workload=OLTP, duration_min=120, tick_minutes=10)
    trace, _, _ = run(s)
    assert len(trace) == 12 + 1
    assert [x.t for x in trace] == [i * 10 for i in range(13)]


def test_engine_is_pure():
    """The engine must not import FastAPI/IO/randomness — house rule."""
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
