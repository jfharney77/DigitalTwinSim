"""Full-trace invariants for the MX7000 shared-infrastructure engine —
the expansion-roster spec's two named scenarios as acceptance tests
("The noisy neighbor, thermally"; "Pooled redundancy math") plus the two
conservation identities in the house style."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.constants import value as C
from app.engine import DT, psu_efficiency, simulate
from app.models import Scenario, SimEvent, SledLoad
from app.presets import (
    EIGHT_COMPUTE,
    FULL,
    HOT_HALF,
    IDLE,
    MIXED,
    NPLUS1,
    ONE_HOT,
    STEADY,
)

# Component powers are rounded to 0.1 W independently of the total, so the
# balance check allows the worst-case rounding sum (8 sleds + 3 lines).
ROUND_TOL = 1.0


def run(scenario: Scenario):
    return simulate(scenario)


def test_determinism():
    s = Scenario(config=EIGHT_COMPUTE, workload=STEADY)
    a, _, _ = run(s)
    b, _, _ = run(s)
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]


def test_power_balance_every_tick():
    """THE identity: sled powers + fabric + management + fans sum to DC on
    every tick of every scenario — which makes the shared fan tax an
    asserted fact, since fan watts are inside the sum."""
    for cfg, wl in ((EIGHT_COMPUTE, IDLE), (MIXED, STEADY), (HOT_HALF, FULL)):
        trace, _, _ = run(Scenario(config=cfg, workload=wl))
        for s in trace:
            parts = (
                sum(s.sled_power_w) + s.fabric_power_w + s.mgmt_power_w
                + s.fan_power_w
            )
            assert abs(parts - s.dc_power_w) <= ROUND_TOL, f"t={s.t}"


def test_wall_power_is_dc_over_efficiency():
    trace, _, _ = run(Scenario(config=EIGHT_COMPUTE, workload=STEADY))
    for s in trace:
        if s.powered_on and s.dc_power_w > 0:
            assert abs(s.ac_power_w - s.dc_power_w / s.psu_efficiency) <= 1.0, f"t={s.t}"
            assert s.ac_power_w > s.dc_power_w, "conversion loss must exist"


def test_heat_balance_at_steady_state():
    """The IR7000 identity, one enclosure down: at steady state the
    exhaust rise equals total DC power over (mass flow × cp)."""
    trace, _, _ = run(Scenario(config=EIGHT_COMPUTE, workload=FULL, duration_s=900))
    s = trace[-1]
    assert s.powered_on
    m_dot = s.airflow_cfm * C("cfm_to_m3s") * C("air_density")
    expected_dt = s.dc_power_w / (m_dot * C("air_cp"))
    assert abs(s.delta_t_c - expected_dt) < 0.5
    assert 5 <= s.delta_t_c <= 40, "front-to-back ΔT should stay chassis-realistic"


# --- Scenario: the noisy neighbor, thermally --------------------------------

def test_noisy_neighbor_taxes_the_shared_fans():
    """One 100%-load sled vs seven idle: the seven don't draw more, but
    the chassis fan bill rises for everyone — and the controller's target
    is visibly the hot slot."""
    baseline, _, _ = run(
        Scenario(config=EIGHT_COMPUTE, workload=IDLE, duration_s=600)
    )
    noisy, _, _ = run(
        Scenario(config=EIGHT_COMPUTE, workload=ONE_HOT, duration_s=600)
    )
    base, hot = baseline[-1], noisy[-1]
    # The seven innocent sleds draw what they drew before...
    for i in range(1, 8):
        assert abs(hot.sled_power_w[i] - base.sled_power_w[i]) < 2.0, f"sled {i + 1}"
    # ...but the shared wall spun up for the one hot neighbor.
    assert hot.fan_rpm_pct > base.fan_rpm_pct + 10
    assert hot.fan_power_w > base.fan_power_w + 15
    assert hot.hottest_slot == 1


# --- Scenario: pooled redundancy math ----------------------------------------

def test_grid_redundancy_survives_a_whole_feed_loss():
    trace, log, summary = run(
        Scenario(
            config=EIGHT_COMPUTE, workload=STEADY, duration_s=600,
            events=[SimEvent(at_s=300, action="lose-feed", index=0)],
        )
    )
    before, after = trace[290], trace[-1]
    assert not summary.shutdown, "grid redundancy must ride through a feed loss"
    assert after.powered_on
    assert not after.feed_a_up and after.feed_b_up
    assert after.alive_psus == before.alive_psus // 2
    assert after.psu_load_pct > before.psu_load_pct, "the survivors' load point must rise"
    assert any("feed A lost" in e.message for e in log)


def test_nplus1_does_not_survive_a_feed_loss():
    trace, log, summary = run(
        Scenario(
            config=NPLUS1, workload=STEADY, duration_s=600,
            events=[SimEvent(at_s=300, action="lose-feed", index=0)],
        )
    )
    assert summary.shutdown
    assert "feed" in summary.shutdown_reason.lower()
    assert trace[-1].dc_power_w == 0
    assert any("Grid redundancy would have survived" in e.message for e in log)


def test_single_psu_failure_is_survivable_under_nplus1():
    trace, _, summary = run(
        Scenario(
            config=NPLUS1, workload=STEADY, duration_s=600,
            events=[SimEvent(at_s=300, action="kill-psu")],
        )
    )
    assert not summary.shutdown
    assert trace[-1].alive_psus == NPLUS1.psu_count - 1


# --- Composability -------------------------------------------------------------

def test_storage_sled_follows_its_owner():
    """Reassigning the storage sled from a storage-heavy owner to an idle
    one drops its power — the drives didn't move, the mapping did."""
    from app.models import Workload

    wl = Workload(loads=[
        SledLoad(cpu_pct=60, mem_pct=40, storage_pct=90),
        SledLoad(cpu_pct=10, mem_pct=10, storage_pct=5),
        *[SledLoad() for _ in range(6)],
    ])
    trace, log, _ = run(
        Scenario(
            config=MIXED, workload=wl, duration_s=600,
            events=[SimEvent(at_s=300, action="reassign-storage", index=6, value=2)],
        )
    )
    before, after = trace[290], trace[-1]
    assert before.sled_power_w[6] > after.sled_power_w[6] + 20, (
        "the storage sled's draw must follow its new, idler owner"
    )
    assert any("reassigned" in e.message for e in log)


# --- Chassis power budget ---------------------------------------------------------

def test_power_cap_throttles_the_whole_chassis():
    capped_cfg = EIGHT_COMPUTE.model_copy(update={"power_cap_w": 4000})
    free, _, _ = run(Scenario(config=EIGHT_COMPUTE, workload=FULL, duration_s=600))
    capped, log, _ = run(Scenario(config=capped_cfg, workload=FULL, duration_s=600))
    assert free[-1].dc_power_w > 4000, "the uncapped build must actually exceed the budget"
    assert capped[-1].chassis_capped
    assert capped[-1].dc_power_w <= 4000 * 1.02
    assert any("power budget" in e.message for e in log)


# --- Shared-plant behaviors ------------------------------------------------------

def test_fan_failure_survivors_ramp():
    trace, log, _ = run(
        Scenario(
            config=EIGHT_COMPUTE, workload=FULL, duration_s=900,
            events=[
                SimEvent(at_s=300, action="kill-fan", index=2),
                SimEvent(at_s=300, action="kill-fan", index=6),
            ],
        )
    )
    before, after = trace[290], trace[-1]
    assert after.alive_fans == before.alive_fans - 2
    assert after.fan_rpm_pct > before.fan_rpm_pct, "survivors must spin faster"
    assert after.powered_on
    assert any("Fan" in e.message for e in log)


def test_overcurrent_trips_a_pool_too_small_for_the_load():
    cfg = EIGHT_COMPUTE.model_copy(update={"psu_count": 2, "redundancy": "none"})
    hot = EIGHT_COMPUTE.model_copy(update={
        "sleds": [s.model_copy(update={"cpu_tdp_w": 350, "dimms": 32})
                  for s in EIGHT_COMPUTE.sleds],
        "psu_count": 2, "redundancy": "none",
    })
    trace, log, summary = run(Scenario(config=hot, workload=FULL, duration_s=300))
    assert summary.shutdown
    assert summary.shutdown_reason == "PSU pool overcurrent trip"
    assert any("overcurrent" in e.message.lower() for e in log)


def test_empty_bays_read_inlet_and_draw_nothing():
    trace, _, _ = run(Scenario(config=HOT_HALF, workload=FULL, duration_s=300))
    s = trace[-1]
    for i in range(4, 8):
        assert s.sled_power_w[i] == 0.0
        assert abs(s.region_temps[f"sled-{i + 1}"] - s.inlet_c) < 0.2


def test_region_temps_match_anatomy():
    """Engine ↔ anatomy contract: every region id the engine paints exists
    in the chassis map, and every map region gets painted."""
    region_ids = {r.id for r in ANATOMY.regions}
    trace, _, _ = run(Scenario(config=MIXED, workload=STEADY, duration_s=30))
    for s in trace:
        assert set(s.region_temps.keys()) == region_ids


def test_efficiency_curve_shape():
    assert psu_efficiency(0.10) < psu_efficiency(0.50)
    assert psu_efficiency(1.00) < psu_efficiency(0.50)
    assert 0.84 <= psu_efficiency(0.0) <= 0.86


def test_timestep_and_trace_length():
    s = Scenario(config=EIGHT_COMPUTE, workload=IDLE, duration_s=120)
    trace, _, _ = run(s)
    assert len(trace) == int(120 / DT) + 1
    assert [x.t for x in trace] == sorted(x.t for x in trace)


def test_engine_is_pure():
    """The engine must not import FastAPI/IO/randomness — same rule as
    every twin."""
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
