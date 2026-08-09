"""Full-trace invariants for the rack power engine — the spec's scenarios
as pytest, plus the conservation identities in the house style (the
Alienware energy identity, the IR7000 heat balance, applied to the rack's
power layer)."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.constants import value as C
from app.engine import DT, battery_capacity_fraction, simulate
from app.models import Environment, Scenario, SimEvent
from app.presets import (
    BALANCED,
    HEAVY_PHASE,
    LITHIUM_AGED,
    LOPSIDED,
    OLD_BATTERIES,
)

# Component watts are rounded to 0.1 W independently of the totals, so
# balance checks allow the worst-case rounding sum across ~13 terms.
ROUND_TOL = 1.0


def run(scenario: Scenario):
    return simulate(scenario)


def test_determinism():
    s = Scenario(config=BALANCED)
    a, _, _ = run(s)
    b, _, _ = run(s)
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]


def test_power_conservation_every_tick():
    """THE identity: live outlet watts sum to the per-phase watts, which
    sum to the PDU input, on every tick of every scenario."""
    scenarios = [
        Scenario(config=BALANCED),
        Scenario(config=LOPSIDED),
        Scenario(
            config=OLD_BATTERIES, duration_s=900,
            events=[SimEvent(at_s=60, action="utility-fail")],
        ),
    ]
    for sc in scenarios:
        trace, _, _ = run(sc)
        for s in trace:
            outlets = sum(
                w for rid, w in s.region_watts.items() if rid.startswith("load-")
            )
            phases = s.phase_a_w + s.phase_b_w + s.phase_c_w
            assert abs(outlets - phases) <= ROUND_TOL, f"t={s.t}"
            assert abs(phases - s.pdu_input_w) <= ROUND_TOL, f"t={s.t}"


def test_battery_conservation_while_on_battery():
    """On battery: battery output × inverter efficiency = PDU input, and
    the wall draws nothing."""
    trace, _, _ = run(Scenario(
        config=OLD_BATTERIES, duration_s=300,
        events=[SimEvent(at_s=60, action="utility-fail")],
    ))
    on_batt = [s for s in trace if s.on_battery]
    assert on_batt, "the scenario must actually reach battery"
    for s in on_batt:
        assert s.ac_input_w == 0
        assert abs(s.battery_output_w * C("inverter_efficiency") - s.pdu_input_w) <= 2.0
        assert s.battery_output_w > s.pdu_input_w, "inverter loss must exist"


def test_utility_conservation_wall_covers_load_and_charger():
    trace, _, _ = run(Scenario(config=BALANCED, duration_s=60))
    for s in trace:
        if s.utility_on and s.pdu_input_w > 0:
            expected = s.pdu_input_w / C("ups_pass_efficiency") + s.charge_draw_w
            assert abs(s.ac_input_w - expected) <= 2.0, f"t={s.t}"
            assert s.ac_input_w > s.pdu_input_w, "pass-through loss must exist"


def test_balance_the_phases_moves_conserve_and_relieve():
    """Spec scenario 1: staged moves cut imbalance; total input is
    unchanged across each move (a move never creates or destroys watts)."""
    sc = Scenario(
        config=LOPSIDED, duration_s=600,
        events=[
            SimEvent(at_s=120, action="move-load", index=1, phase="B"),
            SimEvent(at_s=120, action="move-load", index=2, phase="C"),
            SimEvent(at_s=150, action="move-load", index=4, phase="B"),
            SimEvent(at_s=180, action="move-load", index=5, phase="C"),
        ],
    )
    trace, log, _ = run(sc)
    before = trace[100]
    after = trace[-1]
    assert before.imbalance_pct > 100, "all-on-A is maximally lopsided"
    assert after.imbalance_pct < 20, "the moves must genuinely balance"
    assert abs(before.pdu_input_w - after.pdu_input_w) <= ROUND_TOL
    assert after.phase_a_pct < before.phase_a_pct, "phase A must be relieved"
    assert any("moved from phase" in e.message for e in log)


def test_old_batteries_runtime_gap_is_the_capacity_fraction():
    """Spec scenario 2, the hero assertion: predicted (nameplate) runtime
    exceeds what the faded battery delivers, and the ratio between them is
    the fade model's capacity fraction."""
    sc = Scenario(
        config=OLD_BATTERIES, duration_s=1800,
        events=[SimEvent(at_s=60, action="utility-fail")],
    )
    trace, _, summary = run(sc)
    frac = battery_capacity_fraction(OLD_BATTERIES, Environment().room_temp_c)
    assert summary.battery_capacity_fraction == round(frac, 3)
    assert frac < 0.8, "four VRLA years must land past end-of-life"
    assert summary.rack_went_dark and summary.dark_reason == "battery exhausted"
    predicted = summary.predicted_runtime_min_at_failure
    actual = summary.actual_runtime_min_survived
    assert predicted > actual, "the panel must overpromise"
    assert abs(actual / predicted - frac) < 0.05, (
        f"gap ratio {actual / predicted:.3f} should equal capacity "
        f"fraction {frac:.3f}"
    )


def test_self_test_corrects_the_prediction():
    """Spec scenario 3: a prior self-test swaps the prediction onto the
    faded watt-hours, so predicted ≈ actual through the outage."""
    sc = Scenario(
        config=OLD_BATTERIES, duration_s=1800,
        events=[
            SimEvent(at_s=30, action="self-test"),
            SimEvent(at_s=60, action="utility-fail"),
        ],
    )
    trace, log, summary = run(sc)
    assert any("self-test" in e.message.lower() for e in log)
    at_fail = next(s for s in trace if not s.utility_on)
    assert at_fail.self_tested
    assert abs(at_fail.predicted_runtime_min - at_fail.actual_runtime_min) <= 0.5
    predicted = summary.predicted_runtime_min_at_failure
    actual = summary.actual_runtime_min_survived
    assert abs(predicted - actual) / predicted < 0.10


def test_breaker_over_100pct_trips_and_drops_the_phase():
    """Spec scenario 4: pushing a phase past its rating trips the breaker
    after the thermal delay; every load on the phase reads zero; the other
    phases are untouched."""
    sc = Scenario(
        config=HEAVY_PHASE, duration_s=600,
        events=[
            SimEvent(at_s=120, action="set-load", index=i, value=1200)
            for i in range(4)
        ],
    )
    trace, log, summary = run(sc)
    assert "A" in summary.tripped_phases
    trip_tick = next(s for s in trace if s.tripped_phases)
    assert trip_tick.t > 120, "the trip must lag the overload — I²t, not instant"
    assert trip_tick.t < 300, "133% of rating cannot hold for minutes"
    last = trace[-1]
    assert last.phase_a_w == 0
    for rid, w in last.region_watts.items():
        if rid.startswith("load-"):
            assert w == 0 or rid not in {f"load-{i}" for i in range(1, 5)}
    assert any("breaker tripped" in e.message.lower() for e in log)
    # Loads were all on A; B and C never had anything to lose.
    assert last.phase_b_w == 0 and last.phase_c_w == 0


def test_breaker_under_80pct_never_trips():
    trace, _, summary = run(Scenario(config=BALANCED, duration_s=600))
    assert summary.tripped_phases == []
    assert all(not s.tripped_phases for s in trace)


def test_deep_overload_trips_within_seconds():
    cfg = HEAVY_PHASE.model_copy(deep=True)
    sc = Scenario(
        config=cfg, duration_s=120,
        events=[
            SimEvent(at_s=60, action="set-load", index=i, value=2000)
            for i in range(4)
        ] + [SimEvent(at_s=60, action="set-load", index=4, value=2000),
             SimEvent(at_s=60, action="move-load", index=4, phase="A"),
             SimEvent(at_s=60, action="set-load", index=5, value=2000),
             SimEvent(at_s=60, action="move-load", index=5, phase="A"),
             SimEvent(at_s=60, action="set-load", index=6, value=2000),
             SimEvent(at_s=60, action="move-load", index=6, phase="A"),
             SimEvent(at_s=60, action="set-load", index=7, value=2000),
             SimEvent(at_s=60, action="move-load", index=7, phase="A")],
    )
    trace, _, summary = run(sc)
    # 16 kW on one 16 A / 230 V feed is ~71 A ≈ 4.4×; magnetic threshold
    # is 5×, so verify the thermal path still trips fast at this depth.
    trip_tick = next((s for s in trace if "A" in s.tripped_phases), None)
    assert trip_tick is not None
    assert trip_tick.t - 60 <= 5, "a ~4.4× overload must trip within seconds"


def test_vrla_fades_faster_hot_and_lithium_fades_less():
    vrla_25 = battery_capacity_fraction(OLD_BATTERIES, 25)
    vrla_35 = battery_capacity_fraction(OLD_BATTERIES, 35)
    li_25 = battery_capacity_fraction(LITHIUM_AGED, 25)
    assert vrla_35 < vrla_25, "+10 °C must age VRLA faster"
    assert abs((1 - vrla_35) - 2 * (1 - vrla_25)) < 0.01, (
        "VRLA loss should double per +10 °C"
    )
    assert li_25 > vrla_25, "lithium must fade less at equal age"


def test_charge_recovers_after_restore():
    sc = Scenario(
        config=BALANCED, duration_s=1200,
        events=[
            SimEvent(at_s=60, action="utility-fail"),
            SimEvent(at_s=180, action="utility-restore"),
        ],
    )
    trace, _, _ = run(sc)
    at_restore = next(s for s in trace if s.t == 185)
    later = trace[-1]
    assert later.charge_pct > at_restore.charge_pct, "the charger must work"
    assert later.utility_on and later.rack_powered


def test_region_watts_match_anatomy():
    """Engine ↔ anatomy contract: every region id the engine paints exists
    in the rack map, and every map region gets painted."""
    region_ids = {r.id for r in ANATOMY.regions}
    trace, _, _ = run(Scenario(config=BALANCED, duration_s=30))
    for s in trace:
        assert set(s.region_watts.keys()) == region_ids


def test_timestep_and_trace_length():
    trace, _, _ = run(Scenario(config=BALANCED, duration_s=120))
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
