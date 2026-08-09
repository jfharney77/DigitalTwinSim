"""Full-trace invariants for the XR rugged-edge engine — the two house
conservation identities, plus the spec's scenarios as acceptance tests:
Phoenix-vs-Fargo, the filter nobody changed, brownout ride-through, and
the HDD-under-vibration tax."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.constants import value as C
from app.engine import DT, psu_efficiency, simulate
from app.models import Environment, Scenario, SimEvent, Workload
from app.presets import (
    CELL_SITE,
    EDGE_DB,
    FACTORY_FLOOR,
    FULL,
    HDD_MISTAKE,
    IDLE,
    RAN,
    VEHICLE,
    VIDEO,
)

# Rounding tolerance: component powers are rounded to 0.1 W independently
# of the total, so the balance check allows the worst-case rounding sum.
ROUND_TOL = 0.5


def run(scenario: Scenario):
    return simulate(scenario)


def test_determinism():
    s = Scenario(config=CELL_SITE, workload=RAN)
    a, _, _ = run(s)
    b, _, _ = run(s)
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]


def test_power_balance_every_tick():
    """THE identity: the component powers sum to the DC total on every
    tick of every scenario — which makes the fouling→fan-watts story an
    asserted fact, since fan watts are inside the sum."""
    for cfg, wl in ((CELL_SITE, IDLE), (FACTORY_FLOOR, VIDEO), (VEHICLE, FULL)):
        trace, _, _ = run(Scenario(config=cfg, workload=wl))
        for s in trace:
            parts = (
                s.cpu_power_w + s.accel_power_w + s.dimm_power_w
                + s.drive_power_w + s.io_power_w + s.platform_power_w
                + s.fan_power_w
            )
            assert abs(parts - s.dc_power_w) <= ROUND_TOL, f"t={s.t}"


def test_wall_power_is_dc_over_efficiency():
    trace, _, _ = run(Scenario(config=CELL_SITE, workload=RAN))
    for s in trace:
        if s.powered_on and s.dc_power_w > 0:
            assert abs(s.ac_power_w - s.dc_power_w / s.psu_efficiency) <= 1.0, (
                f"t={s.t}"
            )
            assert s.ac_power_w > s.dc_power_w, "conversion loss must exist"


def test_heat_balance_at_steady_state():
    """The IR7000 identity inside one short-depth box: at steady state the
    exhaust rise equals total DC power over (mass flow × cp)."""
    trace, _, _ = run(
        Scenario(config=FACTORY_FLOOR, workload=VIDEO, duration_s=900)
    )
    s = trace[-1]
    assert s.powered_on
    m_dot = s.airflow_cfm * C("cfm_to_m3s") * C("air_density_sl")
    expected_dt = s.dc_power_w / (m_dot * C("air_cp"))
    assert abs(s.delta_t_c - expected_dt) < 0.5
    assert 5 <= s.delta_t_c <= 40, "front-to-back ΔT should be server-realistic"


# --- The spec's scenarios, as acceptance tests -----------------------------

def test_phoenix_throttles_where_fargo_idles_its_fans():
    """One config, two climates (the spec's headline scenario): the 48 °C
    rooftop pins the fans and clips clocks; the −15 °C rooftop leaves the
    fans at the floor and the silicon untroubled."""
    phoenix = Scenario(
        config=CELL_SITE, workload=RAN,
        environment=Environment(inlet_c=38, dust="moderate"),
        duration_s=900,
        events=[SimEvent(at_s=240, action="set-inlet", value=48)],
    )
    fargo = Scenario(
        config=CELL_SITE, workload=RAN,
        environment=Environment(inlet_c=-15, dust="clean"),
        duration_s=900,
    )
    p_trace, _, p_sum = run(phoenix)
    f_trace, _, f_sum = run(fargo)

    assert p_sum.throttle_seconds > 0 or max(
        s.fan_rpm_pct for s in p_trace
    ) >= 99, "Phoenix must at least pin the fans"
    assert p_trace[-1].fan_rpm_pct > 80

    assert f_sum.throttle_seconds == 0
    assert f_trace[-1].fan_rpm_pct <= C("fan_floor_accel_pct") + 5, (
        "cold air means fans near the floor"
    )
    assert not f_sum.shutdown
    # The whole difference in wall power is fan overhead + hotter silicon.
    assert p_trace[-1].ac_power_w > f_trace[-1].ac_power_w


def test_fouled_filter_throttles_where_a_clean_one_survives():
    """Six months of heavy dust, then a heat wave: the fouled build
    throttles; the identical build with a fresh filter rides it out."""
    def heat_wave(months: float) -> Scenario:
        return Scenario(
            config=CELL_SITE, workload=FULL,
            environment=Environment(
                inlet_c=38, dust="heavy", filter_months=months,
            ),
            duration_s=900,
            events=[SimEvent(at_s=300, action="set-inlet", value=45)],
        )

    fouled_trace, _, fouled = run(heat_wave(6))
    clean_trace, _, clean = run(heat_wave(0))
    assert fouled.throttle_seconds > 0, "the dirty filter must cost the day"
    assert clean.throttle_seconds == 0, "a clean filter must survive the same day"
    assert fouled_trace[300].fouling_pct > 30
    assert clean_trace[300].fouling_pct == 0
    # The fouled filter visibly costs airflow for the same fan wall.
    assert fouled_trace[290].airflow_cfm < clean_trace[290].airflow_cfm


def test_fouling_costs_fan_power_at_constant_work():
    """The fouling→resistance→rpm→watts chain, at fixed load and ambient."""
    def steady(months: float):
        trace, _, _ = run(Scenario(
            config=CELL_SITE, workload=RAN,
            environment=Environment(inlet_c=35, dust="heavy", filter_months=months),
            duration_s=900,
        ))
        return trace[-1]

    clean, fouled = steady(0), steady(6)
    assert fouled.fan_rpm_pct > clean.fan_rpm_pct + 5
    assert fouled.fan_power_w > clean.fan_power_w
    assert fouled.cpu_power_w == clean.cpu_power_w, "the work never changed"


def test_clean_filter_event_restores_airflow():
    trace, log, _ = run(Scenario(
        config=FACTORY_FLOOR, workload=VIDEO,
        environment=Environment(inlet_c=35, dust="heavy", filter_months=8),
        duration_s=900,
        events=[SimEvent(at_s=400, action="clean-filter")],
    ))
    assert trace[399].fouling_pct > 0
    assert trace[401].fouling_pct == 0
    assert trace[-1].fan_rpm_pct < trace[399].fan_rpm_pct, (
        "fans must relax once the filter is changed"
    )
    assert any("filter changed" in e.message.lower() for e in log)


def test_brownout_rides_through_at_idle_and_trips_at_load():
    """The spec's single-phase-weird-power lesson: I = P/V. The same sag
    is a non-event at idle and a trip at full load on a 1+0 build."""
    def sag(workload: Workload) -> Scenario:
        return Scenario(
            config=CELL_SITE, workload=workload,
            environment=Environment(inlet_c=30),
            duration_s=600,
            events=[SimEvent(at_s=300, action="voltage-sag", value=65, seconds=10)],
        )

    idle_trace, _, idle_sum = run(sag(IDLE))
    load_trace, load_log, load_sum = run(sag(FULL))

    assert not idle_sum.shutdown, "idle must ride the sag through"
    assert idle_trace[305].input_v_pct == 65
    assert idle_trace[-1].powered_on

    assert load_sum.shutdown
    assert load_sum.shutdown_reason == "input overcurrent during brownout"
    assert any("brownout" in e.message.lower() for e in load_log)
    # Current visibly rose when the voltage fell.
    assert load_trace[301].input_current_a > load_trace[299].input_current_a


def test_deep_sag_is_lights_out_regardless_of_load():
    trace, _, summary = run(Scenario(
        config=CELL_SITE, workload=IDLE,
        duration_s=400,
        events=[SimEvent(at_s=200, action="voltage-sag", value=40, seconds=5)],
    ))
    assert summary.shutdown
    assert summary.shutdown_reason == "feed sag beyond ride-through"
    assert trace[-1].dc_power_w == 0


def test_vibration_taxes_hdds_and_spares_ssds():
    env = Environment(inlet_c=30, vibration="vehicle")
    hdd_trace, _, _ = run(Scenario(config=HDD_MISTAKE, workload=EDGE_DB,
                                   environment=env))
    ssd_cfg = HDD_MISTAKE.model_copy(update={"drive_type": "ssd"})
    ssd_trace, _, _ = run(Scenario(config=ssd_cfg, workload=EDGE_DB,
                                   environment=env))
    assert hdd_trace[-1].storage_perf_lost_pct == C("vib_hdd_vehicle_pct")
    assert ssd_trace[-1].storage_perf_lost_pct == 0
    # A tax, not a fault: the machine stays healthy either way.
    assert hdd_trace[-1].powered_on


def test_cold_start_at_minus_fifteen_is_thermally_uneventful():
    trace, _, summary = run(Scenario(
        config=CELL_SITE, workload=IDLE,
        environment=Environment(inlet_c=-15, dust="clean"),
        duration_s=600,
    ))
    assert not summary.shutdown
    assert summary.throttle_seconds == 0
    s = trace[-1]
    assert s.cpu_temp_c < 40
    assert s.fan_rpm_pct <= C("fan_floor_accel_pct") + 2


def test_altitude_costs_fan_speed():
    sea, _, _ = run(Scenario(config=CELL_SITE, workload=FULL, duration_s=900,
                             environment=Environment(inlet_c=35)))
    high, _, _ = run(Scenario(
        config=CELL_SITE, workload=FULL, duration_s=900,
        environment=Environment(inlet_c=35, altitude_m=2500),
    ))
    assert high[-1].fan_rpm_pct > sea[-1].fan_rpm_pct + 2


def test_ambient_over_limit_forces_power_off():
    trace, log, summary = run(Scenario(
        config=CELL_SITE, workload=RAN,
        environment=Environment(inlet_c=45),
        duration_s=400,
        events=[SimEvent(at_s=200, action="set-inlet", value=72)],
    ))
    assert summary.shutdown
    assert summary.shutdown_reason == "ambient air over limit"
    assert any("power-off" in e.message.lower() for e in log)


def test_fan_failure_survivors_ramp():
    trace, log, _ = run(Scenario(
        config=FACTORY_FLOOR, workload=VIDEO, duration_s=900,
        environment=Environment(inlet_c=35),
        events=[SimEvent(at_s=300, action="kill-fan", index=1)],
    ))
    before = trace[290]
    after = trace[-1]
    assert after.alive_fans == before.alive_fans - 1
    assert after.fan_rpm_pct > before.fan_rpm_pct, "survivors must spin faster"
    assert after.powered_on
    assert any("fan" in e.message.lower() for e in log)


def test_psu_failure_on_the_single_feed_build_is_lights_out():
    trace, _, summary = run(Scenario(
        config=CELL_SITE, workload=IDLE, duration_s=400,
        events=[SimEvent(at_s=200, action="kill-psu")],
    ))
    assert summary.shutdown
    assert "PSU" in summary.shutdown_reason
    assert trace[-1].dc_power_w == 0


def test_boost_then_settle():
    trace, _, _ = run(Scenario(config=CELL_SITE, workload=FULL, duration_s=300,
                               environment=Environment(inlet_c=20)))
    tdp = CELL_SITE.cpu_tdp_w
    early = max(s.cpu_power_w for s in trace if s.t <= C("cpu_boost_seconds"))
    late = trace[-1].cpu_power_w
    assert early > tdp * 1.05, "boost must exceed TDP"
    assert late <= tdp * 1.01, "and settle back to TDP"


def test_region_temps_match_anatomy():
    """Engine ↔ anatomy contract: every region id the engine paints exists
    in the chassis map, and every map region gets painted."""
    region_ids = {r.id for r in ANATOMY.regions}
    trace, _, _ = run(Scenario(config=CELL_SITE, workload=RAN, duration_s=30))
    for s in trace:
        assert set(s.region_temps.keys()) == region_ids


def test_efficiency_curve_shape():
    assert psu_efficiency(0.10) < psu_efficiency(0.50)
    assert psu_efficiency(1.00) < psu_efficiency(0.50)
    assert 0.84 <= psu_efficiency(0.0) <= 0.86


def test_timestep_and_trace_length():
    s = Scenario(config=CELL_SITE, workload=IDLE, duration_s=120)
    trace, _, _ = run(s)
    assert len(trace) == int(120 / DT) + 1
    assert [x.t for x in trace] == sorted(x.t for x in trace)


def test_engine_is_pure():
    """The engine must not import FastAPI/IO/random — same rule as every
    twin."""
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
