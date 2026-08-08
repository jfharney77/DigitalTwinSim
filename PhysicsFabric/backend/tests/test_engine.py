"""Full-trace invariants for the fabric engine — spec 03's mechanics as
pytest: flow conservation, the oversubscription prediction, ECMP vs
adaptive routing, the three congestion personalities, SHARP's crossing
counters, the gray-failure liar, and the PoE budget."""

from __future__ import annotations

from app.anatomy import MAPS
from app.constants import value as C
from app.engine import oversub_ratio, simulate
from app.models import FabricConfig, Scenario, SimEvent, Workload
from app.presets import (
    ALLREDUCE,
    CAMPUS,
    CAMPUS_DAY,
    ELEPHANTS,
    INCAST,
    SN6000_ADAPTIVE,
    SN6000_STATIC,
    STEADY,
    X800_FABRIC,
)


def run(s: Scenario):
    return simulate(s)


def test_determinism():
    s = Scenario(config=SN6000_STATIC, workload=ALLREDUCE, duration_s=120)
    a, _, _ = run(s)
    b, _, _ = run(s)
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]


def test_flow_conservation_in_drop_mode():
    """demand = delivered + lost, every tick — the fabric's conservation
    identity (drop-mode Ethernet)."""
    cfg = SN6000_STATIC.model_copy(update={"lossless_roce": False})
    wl = ALLREDUCE.model_copy(update={"demand_gbps": 60000})
    trace, _, _ = run(Scenario(config=cfg, workload=wl, duration_s=120))
    for s in trace:
        assert abs(s.demanded_gbps - s.delivered_gbps - s.lost_gbps) <= max(
            2.0, s.demanded_gbps * 0.02
        ), f"t={s.t}"
    assert any(s.dropped_pps > 0 for s in trace), "this load must drop"


def test_uncongested_fabric_delivers_everything():
    trace, _, summary = run(
        Scenario(config=SN6000_ADAPTIVE, workload=STEADY, duration_s=120)
    )
    assert summary.min_delivered_ratio >= 0.999
    assert summary.total_drops == 0
    assert all(s.worst_link_pct < 90 for s in trace)


def test_oversubscription_predicts_congestion():
    """Congestion appears exactly where the ratio predicts: a 2:1
    fabric congests when endpoint demand reaches uplink capacity."""
    cfg = SN6000_ADAPTIVE.model_copy(update={"spines": 2, "uplink_gbps": 800})
    ratio = oversub_ratio(cfg)
    assert ratio > 1.5
    at_uplink_cap = cfg.leaves * cfg.spines * cfg.uplink_gbps
    wl = STEADY.model_copy(update={"demand_gbps": int(at_uplink_cap * 1.05)})
    trace, _, _ = run(Scenario(config=cfg, workload=wl, duration_s=60))
    assert trace[-1].worst_link_pct > 95


def test_adaptive_routing_flattens_the_worst_link():
    wl = ELEPHANTS.model_copy(update={"demand_gbps": 18000})
    static, _, _ = run(Scenario(config=SN6000_STATIC, workload=wl, duration_s=60))
    adaptive, _, _ = run(Scenario(config=SN6000_ADAPTIVE, workload=wl, duration_s=60))
    assert adaptive[-1].worst_link_pct < static[-1].worst_link_pct * 0.75
    assert adaptive[-1].delivered_gbps >= static[-1].delivered_gbps
    assert adaptive[-1].fct_ms <= static[-1].fct_ms


def test_mid_run_adaptive_toggle():
    wl = ELEPHANTS.model_copy(update={"demand_gbps": 18000})
    trace, log, _ = run(
        Scenario(
            config=SN6000_STATIC, workload=wl, duration_s=600,
            events=[SimEvent(at_s=300, action="toggle-adaptive")],
        )
    )
    assert trace[600].worst_link_pct < trace[290].worst_link_pct
    assert any("Adaptive routing ON" in e.message for e in log)


def test_spine_loss_concentrates_load():
    trace, _, _ = run(
        Scenario(
            config=SN6000_ADAPTIVE, workload=STEADY, duration_s=300,
            events=[SimEvent(at_s=120, action="kill-spine")],
        )
    )
    assert trace[-1].spines_alive == SN6000_ADAPTIVE.spines - 1
    assert trace[200].worst_link_pct > trace[100].worst_link_pct * 1.2


def test_lossless_roce_pauses_instead_of_dropping():
    wl = INCAST.model_copy(update={"demand_gbps": 40000})
    trace, _, summary = run(
        Scenario(config=SN6000_ADAPTIVE, workload=wl, duration_s=120)
    )
    assert summary.total_drops == 0, "PFC: no drops, ever"
    assert any(s.pause_events_s > 0 for s in trace), "the cost surfaces as pauses"
    assert summary.min_delivered_ratio < 1.0


def test_infiniband_cannot_drop_and_stalls_instead():
    """The X800's constitution: drops are unexpressible on every step of
    every load; congestion is sender stall time."""
    wl = ALLREDUCE.model_copy(update={"demand_gbps": 60000, "collective_pct": 0})
    trace, _, summary = run(Scenario(config=X800_FABRIC, workload=wl, duration_s=120))
    assert summary.total_drops == 0
    assert all(s.dropped_pps == 0 for s in trace)
    assert any(s.stall_us_per_s > 0 for s in trace), (
        "over-demand must surface as stalls"
    )
    calm, _, _ = run(Scenario(config=X800_FABRIC, workload=STEADY, duration_s=60))
    assert all(s.stall_us_per_s == 0 for s in calm), (
        "and losslessness must be proven under stress, not asserted at idle"
    )


def test_sharp_counters_cross():
    """SHARP on: link bytes fall, effective all-reduce rate rises — the
    DellQuantumX800 twin's signature, continuous."""
    trace, log, _ = run(
        Scenario(
            config=X800_FABRIC.model_copy(update={"sharp": False}),
            workload=ALLREDUCE, duration_s=600,
            events=[SimEvent(at_s=300, action="toggle-sharp")],
        )
    )
    before = trace[290]
    after = trace[400]
    assert after.worst_link_pct < before.worst_link_pct, "link load must fall"
    assert after.allreduce_gbps > before.allreduce_gbps * 1.4, (
        "while the effective collective rate rises"
    )
    assert any("SHARP" in e.message for e in log)


def test_gray_failure_green_and_wrong():
    """The adversarial invariant: after the gray event the status stays
    all-green AND goodput/FCT demonstrably degrade — both halves
    asserted, because silence proves nothing unless damage is shown."""
    trace, _, _ = run(
        Scenario(
            config=SN6000_ADAPTIVE, workload=STEADY, duration_s=600,
            events=[SimEvent(at_s=180, action="gray-failure")],
        )
    )
    before = trace[170]
    after = trace[400]
    assert after.status_all_green, "nothing may look down"
    assert after.goodput_penalty_pct > 0
    assert after.delivered_gbps < before.delivered_gbps
    assert after.fct_ms > before.fct_ms * 1.5
    assert after.dropped_pps == 0, "the loss is silent — no counter admits it"


def test_cpo_cuts_the_optics_line():
    pluggable, _, _ = run(Scenario(config=SN6000_ADAPTIVE, workload=STEADY, duration_s=10))
    cpo_cfg = SN6000_ADAPTIVE.model_copy(update={"cpo_optics": True})
    cpo, _, _ = run(Scenario(config=cpo_cfg, workload=STEADY, duration_s=10))
    a, b = pluggable[-1], cpo[-1]
    assert b.optics_power_w < a.optics_power_w * 0.4
    assert a.optics_power_w > a.asic_power_w * 0.5, (
        "at scale, pluggable optics rival the ASIC — the lesson"
    )
    assert b.fabric_power_w < a.fabric_power_w


def test_poe_budget_binds_and_sheds_by_priority():
    over = CAMPUS.model_copy(update={"poe_aps": 30, "poe_cameras": 10,
                                     "poe_phones": 20})
    trace, _, _ = run(Scenario(config=over, workload=CAMPUS_DAY, duration_s=30))
    s = trace[-1]
    assert s.poe_demand_w > s.poe_budget_w
    assert s.devices_powered < s.devices_total
    # The deficit fits inside the phone class: no AP or camera sheds.
    assert s.devices_powered >= over.poe_aps + over.poe_cameras


def test_psu_loss_halves_poe_and_sheds():
    trace, log, _ = run(
        Scenario(
            config=CAMPUS, workload=CAMPUS_DAY, duration_s=300,
            events=[SimEvent(at_s=120, action="kill-psu")],
        )
    )
    before = trace[110]
    after = trace[200]
    assert after.poe_budget_w < before.poe_budget_w * 0.6
    assert after.devices_powered < before.devices_powered
    assert any("PoE budget halved" in e.message for e in log)


def test_uplink_loss_outage_then_concentration():
    wl = CAMPUS_DAY.model_copy(update={"demand_gbps": 60})
    trace, _, _ = run(
        Scenario(
            config=CAMPUS, workload=wl, duration_s=300,
            events=[SimEvent(at_s=120, action="kill-uplink")],
        )
    )
    during = trace[121]
    assert during.delivered_gbps == 0, "the STP reconvergence is a real outage"
    after = trace[200]
    before = trace[110]
    assert after.delivered_gbps > 0
    assert after.worst_link_pct > before.worst_link_pct * 1.8, (
        "the survivor carries both wires' load"
    )


def test_region_load_matches_maps():
    for cfg in (CAMPUS, SN6000_ADAPTIVE, X800_FABRIC):
        region_ids = {r.id for r in MAPS[cfg.product].regions}
        trace, _, _ = run(Scenario(config=cfg, workload=STEADY, duration_s=10))
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
