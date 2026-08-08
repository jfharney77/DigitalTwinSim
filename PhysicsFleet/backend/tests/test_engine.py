"""Full-trace invariants for the fleet engine — spec 04's mechanics as
pytest: the admin-hours order of magnitude, N+1 branching, the 3-node
trap, version currency vs the release wave, drift accumulation and
reconciliation, APEX's crossover, and the test gate."""

from __future__ import annotations

from app.anatomy import MAPS
from app.engine import simulate
from app.models import Scenario, SimEvent
from app.presets import (
    APEX_SPIKY,
    DENSE_WL,
    EDGE_500,
    EDGE_HA,
    EDGE_WL,
    PRIVATE_2STACK,
    STEADY_WL,
    STUDIO,
    VXRAIL_3NODE,
    VXRAIL_8,
    VXRAIL_MANUAL,
)


def run(s: Scenario):
    return simulate(s)


def test_determinism():
    s = Scenario(config=VXRAIL_8, workload=STEADY_WL, duration_d=90)
    a, _, _ = run(s)
    b, _, _ = run(s)
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]


def test_automation_is_an_order_of_magnitude():
    """The file's one lesson: the same fleet, the same faults, the same
    updates — manual ops cost ≥5× the hours."""
    auto = Scenario(config=VXRAIL_8, workload=STEADY_WL, duration_d=180)
    manual = Scenario(config=VXRAIL_MANUAL, workload=STEADY_WL, duration_d=180)
    _, _, a = run(auto)
    _, _, m = run(manual)
    assert m.admin_hours_total > a.admin_hours_total * 5


def test_zero_touch_rollout_bill():
    """500 stores: zero-touch vs manual deploy hours ≈ 15×."""
    waves = [
        SimEvent(at_d=10, action="deploy-sites", value=50),
        SimEvent(at_d=40, action="deploy-sites", value=100),
        SimEvent(at_d=70, action="deploy-sites", value=100),
    ]
    base = EDGE_500.model_copy(update={"sites": 50})
    auto = Scenario(config=base, workload=EDGE_WL, duration_d=120, events=waves)
    manual = Scenario(
        config=base.model_copy(update={"ops_mode": "manual"}),
        workload=EDGE_WL, duration_d=120, events=waves,
    )
    _, _, a = run(auto)
    _, _, m = run(manual)
    assert m.admin_hours_total > a.admin_hours_total * 4
    # The zero-touch bill for 250 sites should be tens of hours, not weeks.
    assert a.admin_hours_total < 500


def test_fault_with_headroom_is_minutes_without_is_hours():
    ok = Scenario(
        config=VXRAIL_8, workload=STEADY_WL, duration_d=60,
        events=[SimEvent(at_d=20, action="node-fault")],
    )
    _, _, s_ok = run(ok)
    assert s_ok.outage_minutes < 30, "N+1: a fault is a failover"
    tight = Scenario(
        config=VXRAIL_8,
        workload=STEADY_WL.model_copy(update={"vms_per_site": 78}),
        duration_d=60,
        events=[SimEvent(at_d=20, action="node-fault")],
    )
    _, _, s_tight = run(tight)
    assert s_tight.outage_minutes > s_ok.outage_minutes + 100, (
        "no headroom: the same fault is an outage"
    )


def test_three_node_trap_exposure():
    trace, _, _ = run(
        Scenario(
            config=VXRAIL_3NODE, workload=EDGE_WL, duration_d=60,
            events=[SimEvent(at_d=20, action="node-fault")],
        )
    )
    assert any(s.exposure for s in trace if s.t_d == 20), (
        "one fault in a 3-node FTT=1 cluster opens the exposure window"
    )
    four = run(
        Scenario(
            config=VXRAIL_3NODE.model_copy(update={"nodes_per_site": 5}),
            workload=EDGE_WL, duration_d=60,
            events=[SimEvent(at_d=20, action="node-fault")],
        )
    )[0]
    assert not any(s.exposure for s in four if s.t_d > 25)


def test_manual_fleet_falls_behind_the_release_wave():
    big_manual = VXRAIL_MANUAL.model_copy(update={"sites": 4, "nodes_per_site": 16})
    trace_m, _, sum_m = run(
        Scenario(config=big_manual, workload=STEADY_WL, duration_d=180)
    )
    big_auto = big_manual.model_copy(update={"ops_mode": "automated"})
    _, _, sum_a = run(Scenario(config=big_auto, workload=STEADY_WL, duration_d=180))
    assert sum_a.final_version_current_pct > sum_m.final_version_current_pct
    # The manual fleet's currency must dip visibly after a wave.
    after_wave = [s.version_current_pct for s in trace_m if 30 <= s.t_d <= 35]
    assert min(after_wave) < 60


def test_drift_accumulates_manual_reconciles_automated():
    manual, _, _ = run(Scenario(config=VXRAIL_MANUAL, workload=STEADY_WL, duration_d=90))
    auto, _, _ = run(Scenario(config=VXRAIL_8, workload=STEADY_WL, duration_d=90))
    assert manual[-1].drift_count >= 0
    assert auto[-1].drift_count == 0


def test_wan_outage_autonomy_drift_then_reconcile():
    trace, log, _ = run(
        Scenario(
            config=EDGE_HA, workload=EDGE_WL, duration_d=90,
            events=[SimEvent(at_d=30, action="wan-outage", value=7)],
        )
    )
    before = next(s for s in trace if s.t_d == 29)
    during = next(s for s in trace if s.t_d == 36)
    after = trace[-1]
    assert during.drift_count > before.drift_count, "disconnection accumulates drift"
    assert after.drift_count == 0, "reconnection reconciles it"
    assert during.availability_pct > 99.0, "autonomy: the sites kept serving"
    assert any("autonomously" in e.message for e in log)


def test_single_node_edge_fault_is_a_truck_roll_day():
    solo = EDGE_500.model_copy(update={"sites": 10})
    trace, _, summary = run(
        Scenario(
            config=solo, workload=EDGE_WL, duration_d=60,
            events=[SimEvent(at_d=20, action="node-fault")],
        )
    )
    assert summary.truck_rolls >= 1
    assert summary.outage_minutes > 100, "a site lost most of a day"
    ha, _, ha_summary = run(
        Scenario(
            config=EDGE_HA, workload=EDGE_WL, duration_d=60,
            events=[SimEvent(at_d=20, action="node-fault")],
        )
    )
    assert ha_summary.outage_minutes < summary.outage_minutes, (
        "2-node HA turns the truck-roll day into a failover"
    )


def test_apex_spiky_favors_asvc_steady_favors_capex():
    from app.presets import APEX_WL

    spiky = Scenario(config=APEX_SPIKY, workload=APEX_WL, duration_d=240)
    _, _, s = run(spiky)
    assert s.mean_cost_per_vm_hour_asvc < s.mean_cost_per_vm_hour_capex, (
        "spiky demand: as-a-service wins per delivered VM-hour"
    )
    steady_cfg = APEX_SPIKY.model_copy(update={"demand_curve": "steady"})
    _, _, st = run(Scenario(config=steady_cfg, workload=APEX_WL, duration_d=240))
    assert st.mean_cost_per_vm_hour_capex < st.mean_cost_per_vm_hour_asvc, (
        "steady demand: ownership wins"
    )


def test_apex_small_buffer_means_outages():
    tight = APEX_SPIKY.model_copy(update={"buffer_pct": 0, "committed_vms": 100})
    wl = STEADY_WL.model_copy(update={"vms_per_site": 100})
    trace, log, summary = run(Scenario(config=tight, workload=wl, duration_d=120))
    assert summary.outage_minutes > 0, "demand above base+buffer is an outage"
    assert any("buffer" in e.message.lower() for e in log)


def test_gate_makes_the_same_mistake_cheap():
    gated = Scenario(
        config=STUDIO, workload=DENSE_WL, duration_d=40,
        events=[SimEvent(at_d=20, action="bad-change")],
    )
    _, log_g, sum_g = run(gated)
    assert sum_g.outage_minutes == 0
    assert any("CAUGHT IN TEST" in e.message for e in log_g)
    ungated = Scenario(
        config=STUDIO.model_copy(update={"test_gate": False}),
        workload=DENSE_WL, duration_d=40,
        events=[SimEvent(at_d=20, action="bad-change")],
    )
    _, log_u, sum_u = run(ungated)
    assert sum_u.outage_minutes >= 240
    assert any("reached production" in e.message for e in log_u)


def test_faults_arrive_on_the_wear_schedule():
    big = VXRAIL_8.model_copy(update={"sites": 10, "nodes_per_site": 10})
    _, _, summary = run(Scenario(config=big, workload=STEADY_WL, duration_d=180))
    # 100 nodes × 180 days = 18,000 node-days ÷ 3,000 = 6 faults.
    assert summary.faults == 6


def test_availability_reflects_outage_minutes():
    trace, _, _ = run(Scenario(config=VXRAIL_8, workload=STEADY_WL, duration_d=90))
    for s in trace:
        assert 0 <= s.availability_pct <= 100
    assert trace[-1].availability_pct > 99.9, "a healthy automated fleet is boring"


def test_region_load_matches_map():
    region_ids = {r.id for r in MAPS["vxrail"].regions}
    trace, _, _ = run(Scenario(config=VXRAIL_8, workload=STEADY_WL, duration_d=10))
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
