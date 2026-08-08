"""Full-trace invariants for the AI-compute engine — spec 01's key
mechanics as pytest: power balance, the heat-split identity, positional
inequality, shared HGX fate, data starvation, and the liquid loop's
arithmetic."""

from __future__ import annotations

from app.anatomy import MAPS
from app.constants import value as C
from app.engine import DT, gpu_count, simulate
from app.models import Environment, Scenario, SimEvent, Workload
from app.presets import (
    IDLE,
    STARVED,
    TRAINING,
    XE7745_8GPU,
    XE9680_B200,
    XE9680_H100,
    XE9712_FULL,
)

ROUND_TOL = 1.0


def run(s: Scenario):
    return simulate(s)


def test_determinism():
    s = Scenario(config=XE9680_H100, workload=TRAINING)
    a, _, _ = run(s)
    b, _, _ = run(s)
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]


def test_power_balance_every_tick():
    for cfg in (XE7745_8GPU, XE9680_B200, XE9712_FULL):
        trace, _, _ = run(Scenario(config=cfg, workload=TRAINING))
        for s in trace:
            parts = (
                s.cpu_power_w + s.gpu_power_w + s.nic_power_w
                + s.base_power_w + s.fan_power_w + s.pump_power_w
            )
            assert abs(parts - s.dc_power_w) <= ROUND_TOL, f"{cfg.product} t={s.t}"


def test_heat_split_identity_is_exact():
    """The XE9712's reason for existing: liquid + air = DC, every tick."""
    trace, _, _ = run(Scenario(config=XE9712_FULL, workload=TRAINING))
    for s in trace:
        assert abs(s.liquid_watts + s.air_watts - s.dc_power_w) <= 0.2, f"t={s.t}"
        if s.dc_power_w > 0:
            assert s.liquid_watts / s.dc_power_w >= 0.85


def test_coolant_delta_t_is_q_over_mcp():
    trace, _, _ = run(Scenario(config=XE9712_FULL, workload=TRAINING, duration_s=600))
    s = trace[-1]
    m_dot = s.flow_lpm / 60.0
    expected = s.liquid_watts / (m_dot * C("water_cp"))
    assert abs(s.coolant_delta_t_c - expected) < 0.1
    assert abs(s.coolant_return_c - s.coolant_supply_c - s.coolant_delta_t_c) < 0.05


def test_rack_full_load_sanity():
    """Spec 01 §3: full rack ≈ 100–130 kW class."""
    _, _, summary = run(Scenario(config=XE9712_FULL, workload=TRAINING, duration_s=600))
    assert 100_000 <= summary.peak_dc_w <= 135_000, summary.peak_dc_w


def test_xe9680_idle_to_full_swing():
    """Spec 01 §2: ~1 kW idle → 10+ kW full — the power-plant problem."""
    trace, _, summary = run(
        Scenario(
            config=XE9680_B200, workload=IDLE, duration_s=600,
            events=[SimEvent(at_s=120, action="set-workload", workload=TRAINING)],
        )
    )
    idle = trace[60].dc_power_w
    assert 800 <= idle <= 2000, idle
    assert summary.peak_dc_w >= 10_000, summary.peak_dc_w


def test_positional_inequality_on_the_7745():
    """Spec 01 §1: at hot inlet the worst slot throttles first — a
    nonzero spread between hottest and coolest GPU, and a throttle count
    strictly between zero and all eight."""
    trace, log, _ = run(
        Scenario(
            config=XE7745_8GPU, workload=TRAINING,
            environment=Environment(inlet_c=30),
            duration_s=900,
        )
    )
    s = trace[-1]
    assert s.gpu_temp_hot_c > s.gpu_temp_cool_c + 2, "positions must diverge"
    throttled = [x.gpus_throttled for x in trace if x.gpus_throttled > 0]
    assert throttled, "the worst seat must throttle at 30 °C"
    assert min(throttled) < 8, "and not all eight at once — inequality, not collapse"
    assert any("position" in e.message for e in log)


def test_xe9680_throttles_as_one():
    """Shared HGX fate: when the baseboard throttles it is all 8 GPUs."""
    trace, _, _ = run(
        Scenario(
            config=XE9680_B200, workload=TRAINING,
            environment=Environment(inlet_c=40),
            duration_s=900,
        )
    )
    counts = {s.gpus_throttled for s in trace}
    assert counts <= {0, 8}, f"HGX throttling must be collective: {counts}"
    assert 8 in counts, "1000 W SXM at 40 °C inlet must throttle"


def test_data_starvation_cuts_tokens_more_than_watts():
    fed, _, _ = run(Scenario(config=XE9680_H100, workload=TRAINING, duration_s=400))
    starved, _, _ = run(Scenario(config=XE9680_H100, workload=STARVED, duration_s=400))
    f, s = fed[-1], starved[-1]
    token_ratio = s.tokens_per_s / f.tokens_per_s
    power_ratio = s.dc_power_w / f.dc_power_w
    assert token_ratio < 0.4, "tokens must fall with the feed"
    assert power_ratio > 0.6, "power must NOT fall with the feed — that's the waste"
    assert power_ratio > token_ratio + 0.2
    assert s.gpu_hours_wasted > 0


def test_wasted_gpu_hours_accumulate_only_when_starved():
    fed, _, sum_fed = run(Scenario(config=XE9680_H100, workload=TRAINING, duration_s=400))
    assert sum_fed.gpu_hours_wasted < 0.01
    _, _, sum_starved = run(Scenario(config=XE9680_H100, workload=STARVED, duration_s=3600))
    # 8 GPUs × 0.7 shortfall × 1 h ≈ 5.6 GPU-hours.
    assert 4.5 <= sum_starved.gpu_hours_wasted <= 6.5


def test_fan_overhead_is_hundreds_of_watts_at_full_bore():
    trace, _, _ = run(
        Scenario(
            config=XE7745_8GPU, workload=TRAINING,
            environment=Environment(inlet_c=32),
            duration_s=900,
        )
    )
    assert max(s.fan_power_w for s in trace) >= 250
    assert max(s.cooling_overhead_pct for s in trace) >= 3


def test_liquid_cooling_overhead_beats_air():
    air, _, _ = run(Scenario(config=XE9680_B200, workload=TRAINING, duration_s=600))
    liq, _, _ = run(Scenario(config=XE9712_FULL, workload=TRAINING, duration_s=600))
    assert liq[-1].cooling_overhead_pct < air[-1].cooling_overhead_pct, (
        "the pump must be cheaper than the fans per IT watt — spec 01's "
        "air-vs-liquid lesson"
    )


def test_pump_degradation_raises_delta_t_then_throttles():
    trace, log, summary = run(
        Scenario(
            config=XE9712_FULL, workload=TRAINING, duration_s=1200,
            events=[SimEvent(at_s=300, action="degrade-pump", value=0.75)],
        )
    )
    before = trace[290]
    after = next(s for s in trace if s.t == 400)
    assert after.coolant_delta_t_c > before.coolant_delta_t_c * 1.5
    assert any(s.gpus_throttled > 0 for s in trace if s.t > 300), (
        "half flow at full load must cross the coolant throttle line"
    )
    assert not summary.shutdown, "throttling should save the rack from the trip"
    assert any("pump" in e.message.lower() for e in log)


def test_cdu_excursion_translates_the_loop():
    trace, _, _ = run(
        Scenario(
            config=XE9712_FULL, workload=TRAINING, duration_s=900,
            events=[SimEvent(at_s=300, action="set-coolant-supply", value=42)],
        )
    )
    before = trace[290]
    after = next(s for s in trace if s.t == 500)
    assert abs(after.coolant_supply_c - 42) < 0.01
    # Same heat, same flow: ΔT roughly unchanged, return translated up.
    assert abs(after.coolant_delta_t_c - before.coolant_delta_t_c) < 2.0
    assert after.coolant_return_c > before.coolant_return_c + 10


def test_restricted_tray_throttles_alone():
    trace, _, _ = run(
        Scenario(
            config=XE9712_FULL, workload=TRAINING, duration_s=900,
            events=[SimEvent(at_s=300, action="restrict-tray", index=17)],
        )
    )
    later = [s for s in trace if s.t > 500]
    assert any(0 < s.gpus_throttled <= 8 for s in later), (
        "one starved tray (4 GPUs) should throttle without dragging the rack"
    )


def test_shelf_oversubscription_trips():
    cfg = XE9712_FULL.model_copy(update={"shelf_capacity_kw": 66})
    _, log, summary = run(Scenario(config=cfg, workload=TRAINING, duration_s=300))
    assert summary.shutdown
    assert "overcurrent" in summary.shutdown_reason
    assert any("overcurrent" in e.message.lower() for e in log)


def test_region_temps_match_maps():
    for cfg in (XE7745_8GPU, XE9680_H100, XE9712_FULL):
        region_ids = {r.id for r in MAPS[cfg.product].regions}
        trace, _, _ = run(Scenario(config=cfg, workload=IDLE, duration_s=30))
        for s in trace:
            assert set(s.region_temps.keys()) == region_ids, cfg.product


def test_gpu_counts():
    assert gpu_count(XE7745_8GPU) == 8
    assert gpu_count(XE9680_H100) == 8
    assert gpu_count(XE9712_FULL) == 72


def test_timestep_and_trace_length():
    trace, _, _ = run(Scenario(config=XE9680_H100, workload=IDLE, duration_s=120))
    assert len(trace) == int(120 / DT) + 1
    assert [x.t for x in trace] == sorted(x.t for x in trace)


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
