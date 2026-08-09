"""Full-trace invariants for the CDU engine — the spec's scenarios as
pytest acceptance criteria, plus the conservation identity in the house
style (IR7000's heat balance, here across two liquid loops)."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.constants import value as C
from app.engine import DT, pump_flow_lpm, simulate
from app.models import (
    CduConfig,
    Environment,
    Scenario,
    SimEvent,
    Workload,
)
from app.presets import (
    FULL_RACK,
    FULL_TILT,
    HALF_RACK,
    IDLE,
    NO_SPARE,
    PANIC,
    STANDARD,
)

# Component values are rounded independently, so identity checks allow
# worst-case rounding.
ROUND_TOL = 0.5


def run(scenario: Scenario):
    return simulate(scenario)


def test_determinism():
    s = Scenario(config=STANDARD, workload=FULL_TILT)
    a, _, _ = run(s)
    b, _, _ = run(s)
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]


def test_heat_balance_both_loops_every_tick():
    """THE identity: the same heat crosses both loops on every tick —
    IT heat == ṁ·cp·ΔT (secondary) == ṁ·cp·ΔT (primary). A CDU is a
    device for making these three numbers equal."""
    for cfg, wl in ((HALF_RACK, FULL_TILT), (STANDARD, FULL_TILT),
                    (FULL_RACK, FULL_TILT), (STANDARD, IDLE)):
        trace, _, _ = run(Scenario(config=cfg, workload=wl))
        for s in trace:
            # Secondary loop.
            m_sec = s.sec_flow_lpm / 60.0 * C("rho_pg25")
            if m_sec > 0:
                q_sec = m_sec * C("cp_pg25") * (s.sec_return_c - s.sec_supply_c)
                assert abs(q_sec - s.heat_removed_kw) <= ROUND_TOL, f"t={s.t}"
            # Primary loop.
            if s.it_load_kw > 0:
                m_fac = s.fac_flow_lpm / 60.0 * C("rho_water")
                q_fac = m_fac * C("cp_water") * (s.fac_return_c - s.fac_supply_c)
                assert abs(q_fac - s.heat_removed_kw) <= ROUND_TOL, f"t={s.t}"
            # And the bookkeeping never invents heat.
            assert abs(s.heat_removed_kw - s.it_load_kw) <= ROUND_TOL


def test_supply_never_below_facility_water():
    """No heat exchanger delivers coolant colder than its source."""
    trace, _, _ = run(Scenario(config=FULL_RACK, workload=FULL_TILT))
    for s in trace:
        assert s.sec_supply_c >= s.fac_supply_c - 0.01, f"t={s.t}"
        assert s.approach_c >= -0.01


def test_condensation_floor_holds_on_every_tick():
    """The mixing valve is a hard constraint: supply ≥ dew point +
    margin, always — including while events move the dew point."""
    s = Scenario(
        config=CduConfig(tray_groups=1, pumps=3), workload=IDLE,
        environment=Environment(facility_supply_c=17, dew_point_c=20),
        duration_s=600,
        events=[
            SimEvent(at_s=200, action="set-min-supply", value=24),
            SimEvent(at_s=400, action="set-dew-point", value=23),
        ],
    )
    trace, log, _ = run(s)
    margin = C("dew_margin_c")
    dew = 20.0
    for st in trace:
        if st.t >= 400:
            dew = 23.0
        assert st.sec_supply_c >= dew + margin - 0.01, f"t={st.t}"
    # The floor must actually bind at idle (this is the scenario's point).
    assert any(st.floor_active for st in trace)
    assert any("condensation guard" in e.message.lower() for e in log)
    # After the humid air arrives, the floor is dew+2, over the 24 °C ask.
    assert trace[-1].sec_supply_c >= 25 - 0.1


def test_acceptance_size_the_cdu():
    """Adding tray banks until heat-exchange capacity binds: five banks
    run uncapped; the sixth pushes silicon past the IRC target and the
    caps engage, settling near the CDU's rated class."""
    for groups in range(1, 6):
        cfg = CduConfig(tray_groups=groups, pumps=3)
        trace, _, summary = run(
            Scenario(config=cfg, workload=FULL_TILT, duration_s=900)
        )
        assert trace[-1].cap_pct == 100.0, f"{groups} banks must not cap"
        assert summary.trips == 0
    trace, _, summary = run(
        Scenario(config=FULL_RACK, workload=FULL_TILT, duration_s=1500)
    )
    last = trace[-1]
    assert last.cap_pct < 100.0, "the sixth bank must bind the HX"
    # The bound heat is the CDU's real capacity here — near nameplate.
    rated = C("hx_rated_kw")
    assert 0.95 * rated <= last.heat_removed_kw <= 1.15 * rated, (
        last.heat_removed_kw
    )
    assert summary.trips == 0, "coordinated shedding never trips a bank"


def test_acceptance_warm_water_day_coordinated_sheds_gracefully():
    """Facility +6 °C on a full rack: caps engage, every bank stays
    online, and silicon never reaches the firmware trip line."""
    trace, log, summary = run(
        Scenario(
            config=FULL_RACK, workload=FULL_TILT, duration_s=900,
            events=[SimEvent(at_s=120, action="set-facility-supply", value=23)],
        )
    )
    assert summary.trips == 0
    assert all(s.groups_online == 6 for s in trace), "every bank stays up"
    assert summary.peak_chip_c < C("chip_trip_c"), (
        "the IRC must keep silicon under the tray firmware's own trip"
    )
    after = trace[-1]
    assert after.capping and after.cap_pct < 100.0
    assert any("shedding" in e.message.lower() for e in log)


def test_acceptance_warm_water_day_uncoordinated_cascades():
    """The same +6 °C with no coordination: the loop's thermal lag keeps
    survivors hot after the first trip, so the cascade sheds more
    compute than the physics required."""
    trace, log, summary = run(
        Scenario(
            config=PANIC, workload=FULL_TILT, duration_s=900,
            events=[SimEvent(at_s=120, action="set-facility-supply", value=23)],
        )
    )
    assert summary.trips >= 2, "panic must over-shed (a cascade, not one trip)"
    assert trace[-1].groups_online < 6
    assert any("powered off" in e.message.lower() for e in log)
    # Tripped banks never come back within the run (latched).
    online = [s.groups_online for s in trace]
    assert all(b <= a for a, b in zip(online, online[1:])), (
        "recovery is a service visit, not a sim event"
    )


def test_coordination_delivers_more_compute_than_panic():
    """The IRC's argument, in kilowatt-hours: shedding 15% evenly beats
    losing whole banks to a trip cascade."""
    events = [SimEvent(at_s=120, action="set-facility-supply", value=23)]
    _, _, coord = run(Scenario(config=FULL_RACK, workload=FULL_TILT,
                               duration_s=900, events=events))
    _, _, panic = run(Scenario(config=PANIC, workload=FULL_TILT,
                               duration_s=900, events=events))
    assert coord.trips == 0 and panic.trips >= 2
    assert coord.delivered_kwh > panic.delivered_kwh


def test_acceptance_one_pump_down_with_n_plus_1_is_boring():
    """N+1 pumps: the failure costs a few percent of flow and the caps
    never engage — redundancy makes the event a non-event."""
    trace, _, summary = run(
        Scenario(
            config=STANDARD, workload=FULL_TILT, duration_s=700,
            events=[SimEvent(at_s=300, action="fail-pump", index=0)],
        )
    )
    before = trace[290]
    after = trace[-1]
    assert after.pumps_alive == 2
    assert after.sec_flow_lpm >= 0.95 * STANDARD.flow_setpoint_lpm
    assert after.pump_speed_pct > before.pump_speed_pct, "survivors ramp"
    assert summary.min_cap_pct == 100.0, "no capping with the spare pump"
    assert summary.trips == 0


def test_acceptance_one_pump_down_without_redundancy_derates():
    """N pumps: the same failure leaves one pump at ~62% of setpoint,
    the heat exchanger degrades with flow, and the IRC must cap."""
    trace, _, summary = run(
        Scenario(
            config=NO_SPARE, workload=FULL_TILT, duration_s=900,
            events=[SimEvent(at_s=300, action="fail-pump", index=0)],
        )
    )
    after = trace[-1]
    assert after.pumps_alive == 1
    assert after.sec_flow_lpm < 0.7 * NO_SPARE.flow_setpoint_lpm
    assert after.capping and after.cap_pct < 100.0, (
        "one pump cannot carry 200 kW uncapped"
    )
    assert summary.trips == 0, "coordinated mode still never trips"


def test_pump_hydraulics_are_sublinear_and_power_is_cubic():
    q1, _ = pump_flow_lpm(1, 10_000)
    q2, _ = pump_flow_lpm(2, 10_000)
    q3, _ = pump_flow_lpm(3, 10_000)
    assert q1 < q2 < q3
    assert q2 < 2 * q1, "parallel pumps must not add linearly"
    assert q3 < 3 * q1
    # Cubic power: at the same flow, fewer pumps run faster and spend more.
    trace, _, _ = run(
        Scenario(
            config=STANDARD, workload=FULL_TILT, duration_s=400,
            events=[SimEvent(at_s=200, action="fail-pump", index=0)],
        )
    )
    before = trace[190]
    after = trace[-1]
    assert after.pump_speed_pct > before.pump_speed_pct
    # Speed rose ~27%; cubic law says per-pump power rose ~2×, which
    # outweighs having one fewer pump.
    assert after.pump_power_kw > before.pump_power_kw


def test_warm_water_chain_reacts_in_order_with_lag():
    """Facility step at t=120: supply follows with the loop's time
    constant, silicon follows the supply, caps follow the silicon."""
    trace, _, _ = run(
        Scenario(
            config=FULL_RACK, workload=FULL_TILT, duration_s=900,
            events=[SimEvent(at_s=120, action="set-facility-supply", value=23)],
        )
    )
    before = trace[119]
    sup_at = next(
        (s.t for s in trace if s.t > 120
         and s.sec_supply_c > before.sec_supply_c + 2), None)
    chip_at = next(
        (s.t for s in trace if s.t > 120
         and s.chip_temp_c > before.chip_temp_c + 2), None)
    assert sup_at is not None and chip_at is not None
    assert sup_at > 120, "the supply lags the facility step"
    assert chip_at >= sup_at, "silicon follows the supply, not the plant"


def test_no_flow_is_a_crisis_not_a_glitch():
    """Both pumps dead: supply runs away and the IRC caps to the floor."""
    trace, _, _ = run(
        Scenario(
            config=NO_SPARE, workload=FULL_TILT, duration_s=600,
            events=[
                SimEvent(at_s=100, action="fail-pump", index=0),
                SimEvent(at_s=100, action="fail-pump", index=1),
            ],
        )
    )
    after = trace[-1]
    assert after.pumps_alive == 0
    assert after.sec_flow_lpm == 0
    assert after.cap_pct == 100.0 * C("cap_floor")


def test_region_temps_match_anatomy():
    """Engine ↔ anatomy contract: every region id the engine paints
    exists in the loop map, and every map region gets painted."""
    region_ids = {r.id for r in ANATOMY.regions}
    trace, _, _ = run(Scenario(config=STANDARD, workload=FULL_TILT,
                               duration_s=30))
    for s in trace:
        assert set(s.region_temps.keys()) == region_ids


def test_add_and_remove_tray_groups():
    trace, _, _ = run(
        Scenario(
            config=HALF_RACK, workload=FULL_TILT, duration_s=400,
            events=[
                SimEvent(at_s=100, action="add-tray-group"),
                SimEvent(at_s=200, action="remove-tray-group"),
                SimEvent(at_s=200, action="remove-tray-group"),
            ],
        )
    )
    assert trace[50].groups_present == 3
    assert trace[150].groups_present == 4
    assert trace[-1].groups_present == 2
    # Heat follows the population.
    assert trace[150].it_load_kw > trace[50].it_load_kw > trace[-1].it_load_kw


def test_timestep_and_trace_length():
    s = Scenario(config=HALF_RACK, workload=IDLE, duration_s=120)
    trace, _, _ = run(s)
    assert len(trace) == int(120 / DT) + 1
    assert [x.t for x in trace] == sorted(x.t for x in trace)


def test_delivered_energy_accumulates():
    _, _, summary = run(
        Scenario(config=STANDARD, workload=FULL_TILT, duration_s=3600)
    )
    # ~200 kW for an hour ≈ 200 kWh (idle fraction keeps it near-exact).
    assert 150 <= summary.delivered_kwh <= 220


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
