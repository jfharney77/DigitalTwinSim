"""Full-trace invariants for the R760 thermal engine — the spec's §9
acceptance criteria as pytest, plus the two conservation identities in the
house style (Alienware's energy identity, IR7000's heat balance)."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.constants import value as C
from app.engine import DT, psu_efficiency, simulate
from app.models import Environment, Scenario, SimEvent, Workload
from app.presets import (
    AI_TRAINING,
    BALANCED,
    DATABASE,
    ENTRY,
    GPU_NODE,
    HPC,
    IDLE,
    MAX_CPU,
)

# Rounding tolerance: component powers are rounded to 0.1 W independently
# of the total, so the balance check allows the worst-case rounding sum.
ROUND_TOL = 0.5


def run(scenario: Scenario):
    return simulate(scenario)


def test_determinism():
    s = Scenario(config=BALANCED, workload=DATABASE)
    a, _, _ = run(s)
    b, _, _ = run(s)
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]


def test_power_balance_every_tick():
    """THE identity: the component powers sum to the DC total on every
    tick of every scenario — which makes the fan-feedback loop an asserted
    fact, since fan watts are inside the sum."""
    for cfg, wl in ((ENTRY, IDLE), (BALANCED, DATABASE), (MAX_CPU, HPC)):
        trace, _, _ = run(Scenario(config=cfg, workload=wl))
        for s in trace:
            parts = (
                s.cpu_power_w + s.gpu_power_w + s.dimm_power_w
                + s.drive_power_w + s.io_power_w + s.platform_power_w
                + s.fan_power_w
            )
            assert abs(parts - s.dc_power_w) <= ROUND_TOL, f"t={s.t}"


def test_wall_power_is_dc_over_efficiency():
    trace, _, _ = run(Scenario(config=BALANCED, workload=DATABASE))
    for s in trace:
        if s.powered_on and s.dc_power_w > 0:
            assert abs(s.ac_power_w - s.dc_power_w / s.psu_efficiency) <= 1.0, (
                f"t={s.t}"
            )
            assert s.ac_power_w > s.dc_power_w, "conversion loss must exist"


def test_heat_balance_at_steady_state():
    """The IR7000 identity from inside one server: at steady state the
    exhaust rise equals total DC power over (mass flow × cp)."""
    trace, _, _ = run(Scenario(config=BALANCED, workload=HPC, duration_s=900))
    s = trace[-1]
    assert s.powered_on
    # Recompute mass flow from the reported CFM and the scenario's altitude.
    m_dot = s.airflow_cfm * C("cfm_to_m3s") * C("air_density_sl")
    expected_dt = s.dc_power_w / (m_dot * C("air_cp"))
    assert abs(s.delta_t_c - expected_dt) < 0.5
    assert 5 <= s.delta_t_c <= 40, "front-to-back ΔT should be server-realistic"


def test_acceptance_1_cold_start_idle_modest_config():
    """Spec §9.1: 1× 150 W CPU, 8 DIMMs, 2 SSDs, 1+1 800 W settles near
    90–140 W wall with fans near the floor."""
    trace, _, summary = run(Scenario(config=ENTRY, workload=IDLE))
    s = trace[-1]
    assert 90 <= s.ac_power_w <= 140, s.ac_power_w
    assert s.fan_rpm_pct <= C("fan_floor_pct") + 5, "fans should sit near floor"
    assert not summary.shutdown


def test_acceptance_2_max_config_full_load():
    """Spec §9.2: the max configuration flat out lands plausibly in the
    1.2–1.9 kW DC range and stabilizes below throttle at 22 °C inlet with
    Gold fans. (Run with the AI-training workload — the spec names HPC,
    but pure HPC leaves the GPU node's accelerators idle, and the max
    config's max power needs them working.)"""
    trace, _, summary = run(
        Scenario(config=GPU_NODE, workload=AI_TRAINING, duration_s=900)
    )
    assert 1200 <= summary.peak_dc_w <= 1900, summary.peak_dc_w
    s = trace[-1]
    assert s.powered_on
    assert s.cpu_temp_c < C("cpu_throttle_c"), s.cpu_temp_c
    assert not s.cpu_throttling and not s.gpu_throttling


def test_acceptance_3_hot_inlet_causes_ramp_then_throttle_in_order():
    """Spec §9.3: raising inlet 22 → 40 °C at high load produces fan ramp,
    higher wall power, and eventually throttling — in that order, with
    lag."""
    base = Scenario(
        config=MAX_CPU, workload=HPC, duration_s=1200,
        events=[SimEvent(at_s=300, action="set-inlet", value=40)],
    )
    trace, log, _ = run(base)
    before = trace[290]
    assert not before.cpu_throttling, "must not throttle at 22 °C inlet"
    rpm_before = before.fan_rpm_pct
    ramp_at = next(
        (s.t for s in trace if s.t > 300 and s.fan_rpm_pct > rpm_before + 5),
        None,
    )
    throttle_at = next((s.t for s in trace if s.t > 300 and s.cpu_throttling), None)
    assert ramp_at is not None, "fans must ramp after the inlet step"
    assert throttle_at is not None, "throttling must eventually engage"
    assert ramp_at < throttle_at, "fans ramp first; throttling is the last resort"
    assert ramp_at > 300, "the response lags the cause"
    after = trace[-1]
    assert after.ac_power_w > before.ac_power_w or after.cpu_throttling


def test_throttling_clamps_power_and_is_logged():
    trace, log, summary = run(
        Scenario(
            config=MAX_CPU, workload=HPC, duration_s=1200,
            environment=Environment(inlet_c=42),
        )
    )
    throttled = [s for s in trace if s.cpu_throttling]
    assert throttled, "42 °C inlet at 700 W of CPU must throttle"
    full = max(s.cpu_power_w for s in trace)
    clamped = min(s.cpu_power_w for s in throttled)
    assert clamped < full * 0.95, "throttling must actually cut power"
    assert any("throttling engaged" in e.message.lower() for e in log)
    assert summary.throttle_seconds > 0


def test_fan_failure_survivors_ramp():
    """Spec §5.5: kill two fans under load; survivors ramp, temps stay
    controlled, and the event is logged."""
    trace, log, _ = run(
        Scenario(
            config=BALANCED, workload=HPC, duration_s=900,
            events=[
                SimEvent(at_s=300, action="kill-fan", index=1),
                SimEvent(at_s=300, action="kill-fan", index=4),
            ],
        )
    )
    before = trace[290]
    after = trace[-1]
    assert after.alive_fans == before.alive_fans - 2
    assert after.fan_rpm_pct > before.fan_rpm_pct, "survivors must spin faster"
    assert after.powered_on and not after.cpu_throttling, (
        "four survivors should still hold a Balanced build"
    )
    assert any("fan" in e.message.lower() for e in log)


def test_psu_failure_in_1plus1_survives_with_new_efficiency_point():
    trace, log, summary = run(
        Scenario(
            config=BALANCED, workload=DATABASE, duration_s=600,
            events=[SimEvent(at_s=300, action="kill-psu")],
        )
    )
    before = trace[290]
    after = trace[-1]
    assert after.powered_on and not summary.shutdown
    assert after.alive_psus == 1
    assert after.psu_load_pct > before.psu_load_pct, (
        "the survivor's load point must rise"
    )
    assert any("survivor" in e.message.lower() for e in log)


def test_psu_failure_in_1plus0_is_lights_out():
    cfg = ENTRY.model_copy(update={"psu_count": 1, "redundancy": "1+0"})
    trace, _, summary = run(
        Scenario(
            config=cfg, workload=IDLE, duration_s=400,
            events=[SimEvent(at_s=200, action="kill-psu")],
        )
    )
    assert summary.shutdown
    assert "PSU" in summary.shutdown_reason
    assert trace[-1].dc_power_w == 0


def test_psu_overcurrent_trips_after_sustained_overload():
    """Spec §3.5: warn, don't block — then simulate the consequence."""
    cfg = GPU_NODE.model_copy(update={"psu_capacity_w": 800})
    trace, log, summary = run(Scenario(config=cfg, workload=HPC, duration_s=300))
    assert summary.shutdown
    assert summary.shutdown_reason == "PSU overcurrent trip"
    assert any("overcurrent" in e.message.lower() for e in log)


def test_recirculation_death_spiral_ends_in_shutdown():
    trace, log, summary = run(
        Scenario(
            config=BALANCED, workload=DATABASE, duration_s=900,
            environment=Environment(recirculation_pct=90),
        )
    )
    assert summary.shutdown, "90% recirculation must run away"
    assert any("power-off" in e.message.lower() for e in log)


def test_altitude_costs_fan_speed():
    """Spec §8 scenario 7: same config and load, 0 m vs 2500 m — thinner
    air means faster fans."""
    sea, _, _ = run(Scenario(config=BALANCED, workload=HPC, duration_s=900))
    high, _, _ = run(
        Scenario(
            config=BALANCED, workload=HPC, duration_s=900,
            environment=Environment(altitude_m=2500),
        )
    )
    assert high[-1].fan_rpm_pct > sea[-1].fan_rpm_pct + 2


def test_boost_then_settle():
    """Spec §3.1: at sustained 100% the CPU briefly exceeds TDP, then
    settles to it."""
    trace, _, _ = run(Scenario(config=BALANCED, workload=HPC, duration_s=300))
    tdp_total = BALANCED.sockets * BALANCED.cpu_tdp_w
    early = max(s.cpu_power_w for s in trace if s.t <= C("cpu_boost_seconds"))
    late = trace[-1].cpu_power_w
    assert early > tdp_total * 1.05, "boost must exceed TDP"
    assert late <= tdp_total * 1.01, "and settle back to TDP"


def test_region_temps_match_anatomy():
    """Engine ↔ anatomy contract: every region id the engine paints exists
    in the chassis map, and every map region gets painted."""
    region_ids = {r.id for r in ANATOMY.regions}
    trace, _, _ = run(Scenario(config=BALANCED, workload=DATABASE, duration_s=30))
    for s in trace:
        assert set(s.region_temps.keys()) == region_ids


def test_efficiency_curve_shape():
    assert psu_efficiency(0.10) < psu_efficiency(0.50)
    assert psu_efficiency(1.00) < psu_efficiency(0.50)
    assert 0.84 <= psu_efficiency(0.0) <= 0.86


def test_timestep_and_trace_length():
    s = Scenario(config=ENTRY, workload=IDLE, duration_s=120)
    trace, _, _ = run(s)
    assert len(trace) == int(120 / DT) + 1
    assert [x.t for x in trace] == sorted(x.t for x in trace)


def test_engine_is_pure():
    """The engine must not import FastAPI/IO — same rule as every twin."""
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
