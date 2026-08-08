"""Full-trace invariants for the storage engine — spec 02's mechanics
as pytest: the knee, capacity arithmetic, rebuild dynamics per
architecture, replication physics, product personalities, and the
Exascale meta-view."""

from __future__ import annotations

from app.anatomy import MAPS
from app.constants import value as C
from app.engine import iops_capacity_k, network_cap_iops_k, simulate
from app.models import Scenario, SimEvent, StorageConfig, Workload
from app.presets import (
    AI_READ,
    BACKUP,
    EXASCALE_32,
    OBJECTSCALE_12,
    OLTP,
    POWERFLEX_20,
    POWERMAX_4,
    POWERSCALE_20,
    POWERSTORE_2,
    VDI,
)


def run(s: Scenario):
    return simulate(s)


def test_determinism():
    s = Scenario(config=POWERSTORE_2, workload=OLTP, duration_h=48)
    a, _, _ = run(s)
    b, _, _ = run(s)
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]


def test_capacity_arithmetic_every_tick():
    """raw → usable → effective, and used never exceeds usable."""
    for cfg in (POWERSTORE_2, POWERSCALE_20, POWERFLEX_20):
        trace, _, _ = run(Scenario(config=cfg, workload=OLTP, duration_h=72))
        for s in trace:
            assert s.usable_tb < s.raw_tb
            assert abs(s.effective_tb - s.usable_tb * s.reduction_ratio) < 0.5
            assert s.used_tb <= s.usable_tb + 0.01
            prev = s


def test_used_capacity_is_monotone_and_alerts_ladder():
    wl = OLTP.model_copy(update={"ingest_tb_day": 40.0, "snapshots_per_day": 24})
    cfg = POWERSTORE_2.model_copy(update={"drives_per_unit": 6, "drive_tb": 7.68})
    trace, log, _ = run(Scenario(config=cfg, workload=wl, duration_h=2160))
    useds = [s.used_tb for s in trace]
    assert useds == sorted(useds)
    fired = [e for e in log if "full" in e.message]
    assert len(fired) >= 2, "the 80/90 alerts must fire on a filling array"
    alerts = [s.capacity_alert for s in trace]
    assert "80" in alerts and "90" in alerts


def test_the_knee():
    """Latency at ρ≈0.9 is many times latency at ρ≈0.4 — the 1/(1−ρ)
    shape that is this app's reason for existing."""
    cap = iops_capacity_k(POWERSTORE_2, 2, 8)
    low = OLTP.model_copy(update={"iops_demand_k": int(cap * 0.4)})
    high = OLTP.model_copy(update={"iops_demand_k": int(cap * 0.9)})
    a, _, _ = run(Scenario(config=POWERSTORE_2, workload=low, duration_h=12))
    b, _, _ = run(Scenario(config=POWERSTORE_2, workload=high, duration_h=12))
    assert b[-1].latency_ms > a[-1].latency_ms * 4


def test_saturation_clamps_delivery_not_latency():
    wl = OLTP.model_copy(update={"iops_demand_k": 2000})
    trace, _, summary = run(Scenario(config=POWERSTORE_2, workload=wl, duration_h=12))
    s = trace[-1]
    assert s.saturated
    assert s.iops_delivered_k <= s.iops_capacity_k + 0.5
    assert s.iops_delivered_k < s.iops_demand_k
    assert summary.hours_saturated > 0


def test_controller_failover_halves_the_ceiling():
    wl = VDI.model_copy(update={"iops_demand_k": 400})
    trace, log, _ = run(
        Scenario(
            config=POWERSTORE_2, workload=wl, duration_h=48,
            events=[SimEvent(at_h=24, action="fail-controller")],
        )
    )
    before = trace[23]
    after = trace[30]
    assert after.iops_capacity_k < before.iops_capacity_k * 0.55
    assert after.latency_ms > before.latency_ms * 2, "the knee must move left"
    assert after.online, "failover is degradation, not outage"
    assert any("controller" in e.message.lower() for e in log)


def test_powermax_component_failure_is_a_blip_not_an_outage():
    trace, _, summary = run(
        Scenario(
            config=POWERMAX_4, workload=OLTP, duration_h=48,
            events=[
                SimEvent(at_h=12, action="fail-controller"),
                SimEvent(at_h=24, action="fail-controller"),
            ],
        )
    )
    assert all(s.online for s in trace), "six-nines: degraded, never down"
    assert summary.min_delivered_ratio > 0.99
    at_blip = trace[12].latency_ms
    later = trace[20].latency_ms
    assert at_blip > later, "the blip must decay"


def test_sync_srdf_distance_tax():
    near = POWERMAX_4.model_copy(update={"srdf": "sync", "distance_km": 0})
    far = POWERMAX_4.model_copy(update={"srdf": "sync", "distance_km": 800})
    a, _, _ = run(Scenario(config=near, workload=OLTP, duration_h=12))
    b, _, _ = run(Scenario(config=far, workload=OLTP, duration_h=12))
    write_frac = 1 - OLTP.read_pct / 100
    expected = 800 * C("srdf_ms_per_km") * 2 * write_frac
    assert abs(b[-1].srdf_latency_ms - expected) < 0.01
    assert b[-1].latency_ms > a[-1].latency_ms + expected * 0.9


def test_async_rpo_grows_under_burst_then_drains():
    cfg = POWERMAX_4.model_copy(update={"srdf": "async"})
    wl = OLTP.model_copy(update={"read_pct": 40, "iops_demand_k": 150})
    trace, _, _ = run(
        Scenario(
            config=cfg, workload=wl, duration_h=72,
            events=[SimEvent(at_h=12, action="write-burst", value=5)],
        )
    )
    before = trace[11].rpo_seconds
    peak = max(s.rpo_seconds for s in trace)
    end = trace[-1].rpo_seconds
    assert peak > before + 60, "the burst must open an RPO"
    assert end < peak * 0.5, "and the backlog must drain after it"


def test_scaleout_is_near_linear_with_a_tax():
    small = POWERSCALE_20.model_copy(update={"units": 10})
    cap10 = iops_capacity_k(small, 10, 8)
    cap20 = iops_capacity_k(POWERSCALE_20, 20, 8)
    assert cap20 > cap10 * 1.55, "scaling 10→20 must stay near-linear"
    assert cap20 < cap10 * 2.0, "but the coordination tax forbids exactly 2×"


def test_rebuild_faster_with_more_nodes_and_the_inversion():
    """Spec 02's key lesson: scale-out rebuilds speed up with membership;
    the controller array is fixed — and slower."""
    def rebuild_hours(cfg):
        _, _, summary = run(
            Scenario(
                config=cfg, workload=VDI, duration_h=48,
                events=[SimEvent(at_h=6, action="fail-drive")],
            )
        )
        return summary.rebuild_hours

    five = rebuild_hours(POWERSCALE_20.model_copy(update={"units": 5}))
    twenty = rebuild_hours(POWERSCALE_20)
    store = rebuild_hours(POWERSTORE_2)
    assert twenty < five, "more nodes must rebuild faster"
    assert twenty < store, "and the 20-node cluster must beat the controller array"


def test_powerflex_rebuild_is_minutes_class():
    _, _, flex = run(
        Scenario(
            config=POWERFLEX_20, workload=OLTP, duration_h=24,
            events=[SimEvent(at_h=6, action="fail-drive")],
        )
    )
    _, _, store = run(
        Scenario(
            config=POWERSTORE_2, workload=OLTP, duration_h=24,
            events=[SimEvent(at_h=6, action="fail-drive")],
        )
    )
    assert flex.rebuild_hours <= 1.0, "massively parallel: under an hour"
    assert store.rebuild_hours >= 3.0, "controller budget: hours"


def test_the_network_is_the_array():
    slow = POWERFLEX_20.model_copy(update={"nic_gbps": 10})
    cap_slow = iops_capacity_k(slow, 20, 8)
    cap_fast = iops_capacity_k(POWERFLEX_20, 20, 8)
    net_slow = network_cap_iops_k(slow, 20, 8)
    assert abs(cap_slow - net_slow) < 1.0, "10 GbE must be the binding term"
    assert cap_fast > cap_slow * 1.9, "100 GbE must free the nodes"


def test_powerflex_elastic_expansion():
    trace, log, _ = run(
        Scenario(
            config=POWERFLEX_20, workload=OLTP, duration_h=48,
            events=[SimEvent(at_h=12, action="add-nodes", value=5)],
        )
    )
    before = trace[11]
    after = trace[20]
    assert after.units_online == before.units_online + 5
    assert after.iops_capacity_k > before.iops_capacity_k
    assert trace[13].latency_ms > after.latency_ms, "rebalance costs a moment"
    assert any("joined" in e.message for e in log)


def test_small_object_tax():
    small = OBJECTSCALE_12.model_copy(update={"small_objects": True})
    cap_small = iops_capacity_k(small, 12, 8)
    cap_large = iops_capacity_k(OBJECTSCALE_12, 12, 8)
    assert cap_small < cap_large * 0.6


def test_immutable_bucket_bounces_deletes():
    trace, log, _ = run(
        Scenario(
            config=OBJECTSCALE_12, workload=BACKUP, duration_h=48,
            events=[SimEvent(at_h=12, action="attempt-delete")],
        )
    )
    assert any("rejected" in e.message.lower() for e in log)
    used = [s.used_tb for s in trace]
    assert used == sorted(used), "WORM: nothing was actually deleted"


def test_exposure_window_marks_the_race():
    cfg = POWERSCALE_20.model_copy(update={"units": 5, "protection": "raid5"})
    trace, _, _ = run(
        Scenario(
            config=cfg, workload=VDI, duration_h=48,
            events=[SimEvent(at_h=6, action="fail-drive")],
        )
    )
    assert any(s.exposure for s in trace), (
        "survives-1 protection mid-rebuild is the exposure window"
    )
    assert not trace[-1].exposure, "and it closes when the rebuild lands"


def test_second_failure_beyond_protection_loses_data():
    cfg = POWERSTORE_2.model_copy(update={"protection": "raid5"})
    trace, log, summary = run(
        Scenario(
            config=cfg, workload=OLTP, duration_h=24,
            events=[
                SimEvent(at_h=6, action="fail-drive"),
                SimEvent(at_h=7, action="fail-drive"),
            ],
        )
    )
    assert not summary.data_survived
    assert any("data loss" in e.message.lower() for e in log)


def test_exascale_pool_view_and_gpu_idle():
    lopsided = EXASCALE_32.model_copy(update={
        "lightning_units": 8, "file_units": 10, "object_units": 10,
        "block_units": 4,
    })
    bad, _, _ = run(Scenario(config=lopsided, workload=AI_READ, duration_h=24))
    good, _, _ = run(Scenario(config=EXASCALE_32, workload=AI_READ, duration_h=24))
    assert bad[-1].pool_util_pct["lightning"] > 100, "the starved pool saturates"
    assert bad[-1].gpu_idle_due_to_data_pct > good[-1].gpu_idle_due_to_data_pct
    assert good[-1].gpu_idle_due_to_data_pct < 5, (
        "the preset partition should feed the GPUs"
    )


def test_exascale_checkpoint_stampede_recurs():
    trace, _, _ = run(Scenario(config=EXASCALE_32, workload=AI_READ, duration_h=48))
    period = int(C("checkpoint_period_h"))
    burst_hours = [s.t_h for s in trace if s.iops_demand_k > AI_READ.iops_demand_k * 1.1]
    assert burst_hours, "checkpoint bursts must appear"
    assert all(h % period == 0 for h in burst_hours)


def test_region_load_matches_maps():
    for cfg in (POWERSTORE_2, POWERMAX_4, POWERSCALE_20, OBJECTSCALE_12,
                POWERFLEX_20, EXASCALE_32):
        region_ids = {r.id for r in MAPS[cfg.product].regions}
        trace, _, _ = run(Scenario(config=cfg, workload=OLTP, duration_h=6))
        for s in trace:
            assert set(s.region_load.keys()) == region_ids, cfg.product


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
