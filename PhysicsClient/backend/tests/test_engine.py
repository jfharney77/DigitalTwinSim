"""Full-trace invariants for the client-device engine: the supply
identity, the burst-then-fade shape, the shared-budget allocator, the
skin cap, and the battery arithmetic — spec 07's mechanics as pytest."""

from __future__ import annotations

from app.anatomy import map_for
from app.constants import value as C
from app.engine import DT, psu_efficiency, simulate, thermal_budget_w
from app.models import Environment, Scenario, SimEvent, Workload
from app.presets import (
    AAA,
    AW_DESKTOP,
    AW_LAPTOP,
    AW_LAPTOP_MAX,
    IDLE,
    LLM_CPU,
    LLM_GPU,
    LLM_NPU,
    PROMAX_NPU,
    RENDER,
    STREAM,
    STRESS,
)

ROUND_TOL = 0.5


def run(scenario: Scenario):
    return simulate(scenario)


def test_determinism():
    s = Scenario(config=AW_LAPTOP, workload=AAA)
    a, _, _ = run(s)
    b, _, _ = run(s)
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]


def test_power_balance_every_tick():
    """Component powers sum to the system total on every tick."""
    for cfg, wl in ((AW_LAPTOP, AAA), (AW_DESKTOP, STRESS), (PROMAX_NPU, LLM_NPU)):
        trace, _, _ = run(Scenario(config=cfg, workload=wl))
        for s in trace:
            parts = (
                s.cpu_power_w + s.gpu_power_w + s.npu_power_w
                + s.base_power_w + s.fan_power_w
            )
            assert abs(parts - s.system_power_w) <= ROUND_TOL, f"t={s.t}"


def test_supply_identity_every_tick():
    """THE identity (Alienware-twin style): adapter DC + battery
    discharge = system + charge, on every tick of every regime —
    plugged, unplugged, and the undersized-charger hybrid."""
    scenarios = [
        Scenario(config=AW_LAPTOP, workload=AAA),
        Scenario(config=AW_LAPTOP, workload=AAA,
                 environment=Environment(plugged_in=False)),
        Scenario(config=AW_LAPTOP_MAX, workload=STREAM,
                 events=[SimEvent(at_s=60, action="set-charger", value=180)]),
    ]
    for sc in scenarios:
        trace, _, _ = run(sc)
        for s in trace:
            if not s.powered_on:
                continue
            adapter_dc = s.ac_input_w * s.psu_efficiency
            supply = adapter_dc + s.battery_discharge_w
            demand = s.system_power_w + s.charge_w
            assert abs(supply - demand) <= 1.5, f"t={s.t}: {supply} vs {demand}"


def test_burst_then_fade():
    """PL2 → PL1: under sustained stress the CPU opens above PL1 and
    settles to (at most) PL1 once the boost window closes."""
    trace, _, _ = run(Scenario(config=AW_LAPTOP, workload=STRESS, duration_s=600))
    pl1 = AW_LAPTOP.cpu_pl1_w
    early = max(s.cpu_power_w for s in trace if s.t <= C("pl2_tau_s"))
    late = trace[-1].cpu_power_w
    assert early > pl1 * 1.1, "boost must exceed PL1"
    assert late <= pl1 * 1.01, "and settle to PL1 or below"


def test_fps_minute_1_beats_minute_15_under_stress():
    """The 10-minute benchmark lie, as a summary-level assertion: on the
    max build the skin zone (slow, τ ≈ 120 s) claws power back after the
    early minutes look great."""
    _, _, summary = run(
        Scenario(config=AW_LAPTOP_MAX, workload=STRESS, duration_s=1000)
    )
    assert summary.fps_minute_1 > summary.fps_minute_15


def test_shared_budget_binds_and_favors_gpu():
    """Max CPU + max GPU exceeds the laptop budget; the allocator clips
    the CPU first and the sum respects the ceiling."""
    env = Environment()
    budget = thermal_budget_w(AW_LAPTOP_MAX, env)
    trace, _, _ = run(
        Scenario(config=AW_LAPTOP_MAX, workload=STRESS, duration_s=600, environment=env)
    )
    s = trace[-1]
    assert s.pl_state in ("budget-limited", "skin-limited")
    assert s.cpu_power_w + s.gpu_power_w + s.npu_power_w <= budget + 1.0
    # GPU keeps most of its ask; the CPU is the one clipped.
    assert s.gpu_power_w > s.cpu_power_w
    assert s.cpu_power_w < AW_LAPTOP_MAX.cpu_pl1_w


def test_desktop_never_budget_limited():
    """The tower is the control group: separate coolers, no shared
    ceiling — the same stress load never enters budget-limited state."""
    trace, _, _ = run(Scenario(config=AW_DESKTOP, workload=STRESS, duration_s=600))
    assert all(s.pl_state != "budget-limited" for s in trace)
    assert all(s.pl_state != "skin-limited" for s in trace)


def test_skin_cap_is_enforced_on_lap():
    """On-lap AAA gaming crosses the contact cap; the skin governor
    engages and the skin temperature is pulled back near the cap."""
    trace, log, _ = run(
        Scenario(
            config=AW_LAPTOP_MAX, workload=AAA, duration_s=2400,
            environment=Environment(on_lap=True, perf_mode="performance"),
        )
    )
    assert any(s.pl_state == "skin-limited" for s in trace), (
        "the skin governor must engage on-lap at full tilt"
    )
    assert any("skin" in e.message.lower() for e in log)
    # The governor holds the line: skin may overshoot, not run away.
    assert max(s.skin_temp_c for s in trace) < C("skin_cap_c") + 4


def test_quiet_mode_trades_noise_for_fps():
    base = Scenario(config=AW_LAPTOP, workload=AAA, duration_s=1200)
    quiet = Scenario(
        config=AW_LAPTOP, workload=AAA, duration_s=1200,
        environment=Environment(perf_mode="quiet"),
    )
    b, _, _ = run(base)
    q, _, _ = run(quiet)
    assert q[-1].noise_dba < b[-1].noise_dba - 2, "quiet mode must be quieter"
    assert q[-1].fps_proxy < b[-1].fps_proxy, "and it must cost frames"
    assert q[-1].fan_rpm_pct <= C("quiet_fan_cap_pct") + 0.1


def test_undersized_charger_drains_battery_while_plugged():
    sc = Scenario(
        config=AW_LAPTOP_MAX.model_copy(update={"charger_w": 180}),
        workload=STREAM, duration_s=1200,
    )
    trace, _, summary = run(sc)
    s = trace[-1]
    assert s.powered_on
    assert s.battery_discharge_w > 0, "the pack must cover the deficit"
    assert s.ac_input_w > 0, "while the charger still contributes"
    assert summary.min_battery_pct < 99, "and the gauge must actually fall"


def test_battery_runtime_is_wh_over_watts():
    """Unplugged render: the runtime readout matches Wh × η ÷ W."""
    trace, _, _ = run(
        Scenario(
            config=PROMAX_NPU, workload=RENDER, duration_s=300,
            environment=Environment(plugged_in=False),
        )
    )
    s = trace[-1]
    capacity = PROMAX_NPU.battery_wh * PROMAX_NPU.battery_health_pct / 100
    remaining = capacity * s.battery_pct / 100
    expected = remaining * C("discharge_efficiency") / s.battery_discharge_w * 60
    assert abs(s.runtime_min - expected) / expected < 0.05
    assert s.runtime_min < 120, "a render on battery is an hour-class affair"


def test_battery_exhaustion_powers_off():
    trace, log, summary = run(
        Scenario(
            config=AW_LAPTOP, workload=STRESS, duration_s=14000,
            environment=Environment(plugged_in=False, start_charge_pct=20),
        )
    )
    assert summary.shutdown
    assert summary.shutdown_reason == "battery exhausted"
    assert trace[-1].system_power_w == 0
    assert any("exhausted" in e.message.lower() for e in log)


def test_npu_wins_tokens_per_joule():
    """The Pro Max Plus lesson: GPU fastest, NPU most efficient."""
    results = {}
    for name, wl in (("cpu", LLM_CPU), ("gpu", LLM_GPU), ("npu", LLM_NPU)):
        trace, _, _ = run(
            Scenario(config=PROMAX_NPU, workload=wl, duration_s=400)
        )
        s = trace[-1]
        assert s.active_engine == name
        results[name] = (s.tokens_per_s, s.tokens_per_joule)
    assert results["gpu"][0] > results["npu"][0] > results["cpu"][0], (
        "token rate: GPU > NPU > CPU"
    )
    assert results["npu"][1] > results["gpu"][1] > results["cpu"][1], (
        "tokens per joule: NPU > GPU > CPU — the product's whole argument"
    )


def test_npu_is_quieter_than_gpu_for_the_same_job():
    gpu, _, _ = run(Scenario(config=PROMAX_NPU, workload=LLM_GPU, duration_s=600))
    npu, _, _ = run(Scenario(config=PROMAX_NPU, workload=LLM_NPU, duration_s=600))
    assert npu[-1].noise_dba < gpu[-1].noise_dba
    assert npu[-1].system_power_w < gpu[-1].system_power_w


def test_desktop_psu_trip_on_oversubscription():
    cfg = AW_DESKTOP.model_copy(update={"psu_capacity_w": 750, "gpu_tgp_w": 450})
    trace, log, summary = run(Scenario(config=cfg, workload=STRESS, duration_s=300))
    if summary.shutdown:
        assert summary.shutdown_reason == "PSU overcurrent trip"
        assert any("overcurrent" in e.message.lower() for e in log)
    else:  # boost/throttle dynamics kept it under the trip line — the
        # wall must still have exceeded the rating at peak
        assert max(s.ac_input_w for s in trace) > 750


def test_desktop_wall_power_uses_the_psu_curve():
    trace, _, _ = run(Scenario(config=AW_DESKTOP, workload=AAA, duration_s=300))
    for s in trace:
        if s.powered_on and s.system_power_w > 0:
            assert abs(s.ac_input_w - s.system_power_w / s.psu_efficiency) <= 1.0
            assert s.ac_input_w > s.system_power_w


def test_efficiency_curve_shape():
    assert psu_efficiency(0.10) < psu_efficiency(0.50)
    assert psu_efficiency(1.00) < psu_efficiency(0.50)


def test_region_temps_match_map():
    """Engine ↔ map contract, per product/form factor."""
    for cfg in (AW_LAPTOP, AW_DESKTOP, PROMAX_NPU):
        region_ids = {r.id for r in map_for(cfg.product, cfg.form_factor).regions}
        trace, _, _ = run(Scenario(config=cfg, workload=IDLE, duration_s=30))
        for s in trace:
            assert set(s.region_temps.keys()) == region_ids, cfg.product


def test_timestep_and_trace_length():
    trace, _, _ = run(Scenario(config=AW_LAPTOP, workload=IDLE, duration_s=120))
    assert len(trace) == int(120 / DT) + 1
    assert [x.t for x in trace] == sorted(x.t for x in trace)


def test_engine_is_pure():
    """No FastAPI/IO/randomness — same rule as every twin."""
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
