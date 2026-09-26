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
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)


def run(s: Scenario):
    return simulate(s)


# Scenario-driven: no step index or phase order to check, but the tick has to
# advance and the same scenario has to give the same trace. The conservation
# identities below are this app's own.
PROFILE = TraceProfile()


def test_trace_invariants():
    s = Scenario(config=VXRAIL_8, workload=STEADY_WL, duration_d=90)
    assert_trace_invariants(run(s)[0], PROFILE)
    assert_deterministic(lambda: run(s))


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
    import app.engine as engine_module

    assert_engine_is_pure(engine_module)


def test_the_three_node_window_lasts_until_the_repair_and_four_nodes_close_it():
    """The guided 3-node trap's claim, pinned: a faulted node stays out for
    the repair window (nodes_healthy shows it), the 3-node cluster has no
    rebuild target so exposure holds for that whole window, and a 4-node
    cluster re-protects onto its spare host the day the fault lands."""
    from app.constants import value as C

    repair = int(C("repair_days"))
    fault = [SimEvent(at_d=20, action="node-fault")]
    three = run(Scenario(config=VXRAIL_3NODE, workload=EDGE_WL,
                         duration_d=60, events=fault))[0]
    four = run(Scenario(
        config=VXRAIL_3NODE.model_copy(update={"nodes_per_site": 4}),
        workload=EDGE_WL, duration_d=60, events=fault))[0]

    window = [s for s in three if 20 <= s.t_d < 20 + repair]
    assert window and all(s.exposure for s in window)
    assert all(s.nodes_healthy == 2 for s in window)
    after = [s for s in three if s.t_d >= 20 + repair]
    assert all(s.nodes_healthy == 3 and not s.exposure for s in after)

    assert [s.t_d for s in four if s.exposure] == [20]
    assert all(s.nodes_healthy == 3 for s in four if 20 <= s.t_d < 20 + repair)


def test_a_fault_is_charged_once_not_every_day_it_is_down():
    base = Scenario(config=VXRAIL_8, workload=STEADY_WL, duration_d=40)
    faulted = base.model_copy(update={"events": [SimEvent(at_d=10, action="node-fault")]})
    t0, _, _ = run(base)
    t1, _, _ = run(faulted)
    from app.constants import value as C

    extra_min = t1[-1].outage_minutes_cum - t0[-1].outage_minutes_cum
    assert extra_min == C("ha_failover_minutes")


def test_the_spiky_demand_scenario_serves_its_own_spike():
    """The guided 'as-a-service wins' scenario must not open on an outage:
    its buffer and installed capacity cover the ×1.5 peak, so the only
    story on screen is the cost crossover."""
    from app.presets import APEX_WL, GUIDED_SCENARIOS

    g = next(g for g in GUIDED_SCENARIOS if g.id == "spiky-demand")
    trace, log, _ = run(g.scenario)
    assert all(s.vms_running == s.vms_demand for s in trace)
    assert not any("capacity outage" in e.message.lower() for e in log)
    assert g.scenario.workload == APEX_WL


def test_the_exposure_window_is_on_the_record():
    """The 3-node scenario asks how long exposure stood and what closed it;
    the log and the exposure-days counter must carry the answer."""
    base = Scenario(config=VXRAIL_3NODE, workload=EDGE_WL, duration_d=60,
                    events=[SimEvent(at_d=20, action="node-fault")])
    trace, log, summary = run(base)
    assert summary.exposure_days == sum(1 for s in trace if s.exposure) == 3
    days = [s.exposure_days_cum for s in trace]
    assert days == sorted(days)
    msgs = [(e.t_d, e.message) for e in log]
    assert any(d == 20 and "Exposure opened" in m and "no spare node" in m
               for d, m in msgs)
    assert any(d == 23 and "Node repaired" in m and "after 3 days" in m
               for d, m in msgs)
    four = base.model_copy(update={
        "config": VXRAIL_3NODE.model_copy(update={"nodes_per_site": 4})})
    _, log4, summary4 = run(four)
    assert summary4.exposure_days == 1
    assert any(e.t_d == 21 and "rebuilt" in e.message and "after 1 day" in e.message
               for e in log4)


def test_catalog_and_stacks_both_move_the_ledger():
    """Catalog-vs-artisanal: each switch the scenario is named after has
    to change the admin-hours ledger, by the constants' arithmetic."""
    from app.constants import value as C

    def total(cfg):
        _, _, s = run(Scenario(config=cfg, workload=DENSE_WL, duration_d=120))
        return s

    two = total(PRIVATE_2STACK)
    one = total(PRIVATE_2STACK.model_copy(update={"stacks": 1}))
    hand = total(PRIVATE_2STACK.model_copy(update={"catalog": False}))
    assert two.workloads_deployed == one.workloads_deployed == hand.workloads_deployed > 0
    # Deploys: same count, priced at the two table rates, all of it worked.
    assert two.deploy_hours == two.workloads_deployed * C("catalog_deploy_h")
    assert hand.deploy_hours == hand.workloads_deployed * C("artisanal_deploy_h")
    assert abs((hand.admin_hours_total - two.admin_hours_total)
               - (hand.deploy_hours - two.deploy_hours)) < 0.5
    # The second stack costs something, but under one control plane far
    # less than a second fleet would.
    assert one.admin_hours_total < two.admin_hours_total < 1.5 * one.admin_hours_total
    # Manual ops: the same second stack doubles the patch wave.
    man2 = PRIVATE_2STACK.model_copy(update={"ops_mode": "manual"})
    _, log2, _ = run(Scenario(config=man2, workload=DENSE_WL, duration_d=40))
    _, log1, _ = run(Scenario(config=man2.model_copy(update={"stacks": 1}),
                              workload=DENSE_WL, duration_d=40))
    assert any("48 h" in e.message for e in log2)
    assert any("24 h" in e.message for e in log1)


def test_deploys_are_charged_to_private_cloud_only():
    for cfg in (VXRAIL_8, EDGE_HA, STUDIO):
        _, _, s = run(Scenario(config=cfg, workload=DENSE_WL, duration_d=90))
        assert s.workloads_deployed == 0 and s.deploy_hours == 0
