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
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

# Rounding tolerance: component powers are rounded to 0.1 W independently
# of the total, so the balance check allows the worst-case rounding sum.
ROUND_TOL = 0.5


def run(scenario: Scenario):
    return simulate(scenario)


# Scenario-driven: no step index or phase order to check, but the tick has to
# advance and the same scenario has to give the same trace. The conservation
# identities below are this app's own.
PROFILE = TraceProfile()


def test_trace_invariants():
    s = Scenario(config=CELL_SITE, workload=RAN)
    assert_trace_invariants(run(s)[0], PROFILE)
    assert_deterministic(lambda: run(s))


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
    """One config, two climates (the spec's headline scenario): the 52 °C
    rooftop (48 °C before the CPU tier was corrected to Dell's 205 W
    platform maximum — the cooler part needs a hotter afternoon to pin) pins the fans and clips clocks; the −15 °C rooftop leaves the
    fans at the floor and the silicon untroubled."""
    phoenix = Scenario(
        config=CELL_SITE, workload=RAN,
        environment=Environment(inlet_c=38, dust="moderate"),
        duration_s=900,
        events=[SimEvent(at_s=240, action="set-inlet", value=52)],
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
    import app.engine as engine_module

    assert_engine_is_pure(engine_module)


def test_guided_narration_matches_what_the_trace_does():
    """The guided scenarios promise specific outcomes; hold them to it.
    Phoenix pins the fans but never throttles (the filter scenario is the
    one that throttles), and the mountain site holds the sea-level CPU
    temperature by running its fans harder — neither throttles, so neither
    scenario's prose may ask when the throttle landed."""
    from app.presets import GUIDED_SCENARIOS

    g = {s.id: s for s in GUIDED_SCENARIOS}

    p_trace, _, p_sum = run(g["phoenix-rooftop"].scenario)
    assert max(s.fan_rpm_pct for s in p_trace) >= 99
    assert p_sum.throttle_seconds == 0
    assert "throttle step land" not in g["phoenix-rooftop"].question

    _, _, f_sum = run(g["filter-nobody-changed"].scenario)
    assert f_sum.throttle_seconds > 0

    mtn = g["mountain-site"].scenario
    sea = mtn.model_copy(
        update={"environment": mtn.environment.model_copy(update={"altitude_m": 0})}
    )
    m_trace, _, m_sum = run(mtn)
    s_trace, _, s_sum = run(sea)
    assert m_sum.throttle_seconds == 0 and s_sum.throttle_seconds == 0
    assert m_trace[-1].fan_rpm_pct > s_trace[-1].fan_rpm_pct
    assert "throttle" not in g["mountain-site"].question


def test_warm_start_opens_on_the_settled_operating_point():
    """A warm start means the sled has been carrying this load for a while:
    tick 0 already sits where an event-free run ends up, fans off the floor,
    no boost window, and the heat identity holds from the first frame."""
    s = Scenario(config=CELL_SITE, workload=FULL,
                 environment=Environment(inlet_c=30),
                 duration_s=300, warm_start=True)
    trace, log, _ = run(s)
    first, last = trace[0], trace[-1]
    assert first.fan_rpm_pct > C("fan_floor_accel_pct")
    assert abs(first.fan_rpm_pct - last.fan_rpm_pct) < 1.0
    assert abs(first.cpu_temp_c - last.cpu_temp_c) < 0.5
    assert abs(first.exhaust_c - last.exhaust_c) < 0.5
    assert first.cpu_power_w <= CELL_SITE.cpu_tdp_w  # boost long spent
    assert log == []
    assert_deterministic(lambda: run(s)[0])


def test_the_opening_frames_are_physical():
    """Guided scenarios open warmed up, and even a cold start at full load
    through a fouled filter never reports an oven: a part that is still
    warming keeps its watts, so the exhaust rise stays server-realistic."""
    from app.presets import GUIDED_SCENARIOS

    for g in GUIDED_SCENARIOS:
        assert g.scenario.warm_start, g.id
        trace, _, _ = run(g.scenario)
        # Settled: the air never leaves hotter than the silicon it cooled.
        assert trace[0].exhaust_c < max(trace[0].cpu_temp_c, trace[0].accel_temp_c), g.id

    cold = Scenario(
        config=CELL_SITE, workload=FULL, duration_s=120,
        environment=Environment(inlet_c=38, dust="heavy", filter_months=6),
    )
    trace, _, _ = run(cold)
    assert trace[0].fan_rpm_pct == C("fan_floor_accel_pct")
    assert max(s.delta_t_c for s in trace) <= 40


def test_the_filter_scenario_tells_the_story_its_narration_tells():
    """Fans pinned and nothing throttling before the heat wave; the
    accelerators (not the CPU) throttle within seconds of it, and the log
    says so at that moment. The clean-filter rerun had fan speed in hand,
    pins in the same heat wave, and never clips."""
    from app.presets import GUIDED_SCENARIOS

    sc = next(g for g in GUIDED_SCENARIOS if g.id == "filter-nobody-changed").scenario
    wave = sc.events[0].at_s
    trace, log, _ = run(sc)
    before = trace[:wave]
    assert all(not s.cpu_throttling and not s.accel_throttling for s in before)
    assert before[-1].fan_rpm_pct == 100
    throttle_log = [e for e in log if "throttling engaged" in e.message]
    assert [e.message for e in throttle_log] == ["Accelerator throttling engaged"]
    assert wave < throttle_log[0].t <= wave + 15
    assert not any(s.cpu_throttling for s in trace)
    assert trace[-1].cpu_temp_c < C("cpu_throttle_c")
    assert 25 <= trace[-1].accel_perf_lost_pct <= 35
    assert trace[-1].ac_power_w < before[-1].ac_power_w

    clean = sc.model_copy(update={
        "environment": sc.environment.model_copy(update={"filter_months": 0})
    })
    c_trace, _, c_sum = run(clean)
    assert 65 <= c_trace[wave - 1].fan_rpm_pct <= 80
    assert c_trace[-1].fan_rpm_pct == 100
    assert c_sum.throttle_seconds == 0


def test_accelerator_throttle_release_is_logged():
    s = Scenario(
        config=CELL_SITE, workload=FULL, duration_s=600, warm_start=True,
        environment=Environment(inlet_c=30, dust="heavy", filter_months=6),
        events=[SimEvent(at_s=60, action="set-inlet", value=45),
                SimEvent(at_s=200, action="set-inlet", value=25)],
    )
    trace, log, _ = run(s)
    msgs = [e.message for e in log]
    assert "Accelerator throttling released" in msgs
    assert trace[-1].accel_perf_lost_pct == 0
