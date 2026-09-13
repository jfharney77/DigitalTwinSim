"""Full-trace invariants for the AC power-path engine (style of the GPU and
R760 apps): assert over the whole simulate() trace, no HTTP layer."""

from __future__ import annotations

import itertools

import pytest

from app.anatomy import ANATOMIES
from app.catalog import PROFILES
from app.engine import analyze, simulate
from app.models import Scenario
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PHASE_ORDER = [
    "off", "detect", "handshake", "budget", "charge", "boot", "load", "steady",
]

THERMAL_MODES = ["quiet", "balanced", "performance", "fullSpeed"]
WORKLOADS = ["idle", "gaming", "fullLoad"]
START_PCTS = [0, 5, 30, 80, 100]


def _scenarios():
    """Every profile × adapter × a spread of modes/workloads/start levels."""
    for profile in PROFILES.values():
        for adapter in profile.adapters:
            for mode, workload, start in itertools.product(
                THERMAL_MODES, WORKLOADS, START_PCTS
            ):
                yield pytest.param(
                    profile,
                    adapter,
                    Scenario(
                        profile_id=profile.id,
                        adapter_id=adapter.id,
                        start_battery_pct=start,
                        thermal_mode=mode,
                        workload=workload,
                    ),
                    id=f"{profile.id}-{adapter.id}-{mode}-{workload}-{start}",
                )


SCENARIOS = list(_scenarios())


@pytest.mark.parametrize("profile,adapter,scenario", SCENARIOS)
def test_trace_invariants(profile, adapter, scenario):
    """Cycle is the trace index, the phases run in order and all of them are
    reached — the machine gets to steady state even with an unknown adapter —
    only the profile's own regions light, and the same scenario gives the same
    trace. The shared definitions live in twinkit.testing."""
    profile_check = TraceProfile(
        phases=PHASE_ORDER, anatomy=ANATOMIES[profile.anatomy_id]
    )
    assert_trace_invariants(simulate(profile, adapter, scenario), profile_check)
    assert_deterministic(lambda: simulate(profile, adapter, scenario))


@pytest.mark.parametrize("profile,adapter,scenario", SCENARIOS)
def test_energy_invariant_every_state(profile, adapter, scenario):
    """acW + batteryW == systemW + chargeW (contract tolerance ±0.5 W)."""
    for s in simulate(profile, adapter, scenario):
        assert s.ac_w + s.battery_w == pytest.approx(
            s.system_w + s.charge_w, abs=0.5
        ), f"{s.stage_id}: energy imbalance"


@pytest.mark.parametrize("profile,adapter,scenario", SCENARIOS)
def test_ac_never_exceeds_adapter_rating(profile, adapter, scenario):
    for s in simulate(profile, adapter, scenario):
        assert s.ac_w <= adapter.watts + 0.05, f"{s.stage_id}: acW over rating"
        assert s.ac_w >= 0, f"{s.stage_id}: negative acW"


@pytest.mark.parametrize("profile,adapter,scenario", SCENARIOS)
def test_battery_pct_bounds_and_sign_consistency(profile, adapter, scenario):
    trace = simulate(profile, adapter, scenario)
    for s in trace:
        assert 0.0 <= s.battery_pct <= 100.0, s.stage_id
    for prev, s in zip(trace, trace[1:]):
        if s.charge_w > 0:
            assert s.battery_pct >= prev.battery_pct, (
                f"{s.stage_id}: charging but pct fell"
            )
        if s.battery_w > 0:
            assert s.battery_pct <= prev.battery_pct, (
                f"{s.stage_id}: discharging but pct rose"
            )


@pytest.mark.parametrize("profile,adapter,scenario", SCENARIOS)
def test_never_charging_and_discharging_at_once(profile, adapter, scenario):
    for s in simulate(profile, adapter, scenario):
        assert not (s.charge_w > 0 and s.battery_w > 0), s.stage_id


@pytest.mark.parametrize("profile,adapter,scenario", SCENARIOS)
def test_hybrid_flag_matches_battery_supplement(profile, adapter, scenario):
    for s in simulate(profile, adapter, scenario):
        if s.hybrid:
            assert s.battery_w > 0, f"{s.stage_id}: hybrid without supplement"


@pytest.mark.parametrize("profile,adapter,scenario", SCENARIOS)
def test_cycle_cost_and_fan_bounds(profile, adapter, scenario):
    for s in simulate(profile, adapter, scenario):
        assert s.cycle_cost >= 1
        assert 0.0 <= s.fan_pct <= 100.0


@pytest.mark.parametrize("workload", ["gaming", "fullLoad"])
def test_m18_280w_fullspeed_goes_hybrid(workload):
    """The headline scenario: CPU+GPU demand beats the 280 W adapter and the
    battery supplements instead of the machine throttling."""
    profile = PROFILES["m18-r2"]
    adapter = next(a for a in profile.adapters if a.id == "barrel-280")
    scenario = Scenario(
        profile_id=profile.id,
        adapter_id=adapter.id,
        start_battery_pct=80,
        thermal_mode="fullSpeed",
        workload=workload,
    )
    trace = simulate(profile, adapter, scenario)
    hybrid_states = [s for s in trace if s.hybrid]
    assert hybrid_states, "expected hybrid power states"
    for s in hybrid_states:
        assert s.battery_w > 0
        assert s.ac_w == pytest.approx(adapter.watts, abs=0.1)
    summary = analyze(profile, adapter, scenario, trace)
    assert summary.hybrid_used
    assert summary.regime == "adapter-limited"
    assert summary.peak_hybrid_w > 0
    # The battery actually drained across the hybrid states (the pack was
    # topped up during the charge phase first, so compare against the level
    # going into the first hybrid state, not the start level).
    first_hybrid = trace.index(hybrid_states[0])
    assert trace[-1].battery_pct < trace[first_hybrid - 1].battery_pct


def test_360w_fullload_stays_within_budget():
    profile = PROFILES["m18-r2"]
    adapter = next(a for a in profile.adapters if a.id == "barrel-360")
    scenario = Scenario(
        profile_id=profile.id,
        adapter_id=adapter.id,
        start_battery_pct=50,
        thermal_mode="fullSpeed",
        workload="fullLoad",
    )
    trace = simulate(profile, adapter, scenario)
    assert not any(s.hybrid for s in trace)
    summary = analyze(profile, adapter, scenario, trace)
    assert summary.regime == "within-budget"


@pytest.mark.parametrize("profile_id", list(PROFILES))
def test_unrecognized_adapter_is_throttled(profile_id):
    profile = PROFILES[profile_id]
    adapter = next(a for a in profile.adapters if not a.recognized)
    scenario = Scenario(
        profile_id=profile.id,
        adapter_id=adapter.id,
        start_battery_pct=30,
        thermal_mode="fullSpeed",
        workload="fullLoad",
    )
    trace = simulate(profile, adapter, scenario)
    # Charging disabled everywhere; battery level never rises.
    assert all(s.charge_w == 0 for s in trace)
    assert trace[-1].battery_pct <= 30
    # CPU/GPU capped low even at fullSpeed + fullLoad.
    assert max(s.cpu_w + s.gpu_w for s in trace) <= 40
    # And the phase machine still completes.
    assert trace[-1].phase == "steady"
    summary = analyze(profile, adapter, scenario, trace)
    assert summary.regime == "throttled"
    assert summary.minutes_to_80_pct is None


def test_charge_ramp_stages_in_order():
    """Starting deeply discharged walks precharge → cc → cv."""
    profile = PROFILES["m18-r2"]
    adapter = next(a for a in profile.adapters if a.id == "barrel-280")
    scenario = Scenario(
        profile_id=profile.id,
        adapter_id=adapter.id,
        start_battery_pct=5,
        thermal_mode="balanced",
        workload="idle",
    )
    charge_stages = [
        s.charge_stage
        for s in simulate(profile, adapter, scenario)
        if s.phase == "charge"
    ]
    assert charge_stages == ["precharge", "cc", "cc", "cv"]


def test_full_battery_enters_hold_band():
    profile = PROFILES["m18-r2"]
    adapter = next(a for a in profile.adapters if a.id == "barrel-280")
    scenario = Scenario(
        profile_id=profile.id,
        adapter_id=adapter.id,
        start_battery_pct=100,
        thermal_mode="quiet",
        workload="idle",
    )
    trace = simulate(profile, adapter, scenario)
    charge_states = [s for s in trace if s.phase == "charge"]
    assert [s.charge_stage for s in charge_states] == ["full"]
    assert all(s.charge_w == 0 for s in charge_states)


def test_handshake_stage_is_stalled_with_dwell():
    profile = PROFILES["m18-r2"]
    adapter = next(a for a in profile.adapters if a.id == "barrel-280")
    scenario = Scenario(
        profile_id=profile.id,
        adapter_id=adapter.id,
        start_battery_pct=30,
        thermal_mode="balanced",
        workload="gaming",
    )
    trace = simulate(profile, adapter, scenario)
    handshake = [s for s in trace if s.phase == "handshake"]
    assert handshake and all(s.stalled and s.cycle_cost > 1 for s in handshake)


def test_engine_is_pure():
    """The engine must not import FastAPI/IO — same rule as the GPU app."""
    import app.engine as engine_module

    assert_engine_is_pure(engine_module)


def test_simulate_is_deterministic():
    profile = PROFILES["m18-r2"]
    adapter = profile.adapters[0]
    scenario = Scenario(
        profile_id=profile.id,
        adapter_id=adapter.id,
        start_battery_pct=30,
        thermal_mode="performance",
        workload="gaming",
    )
    a = simulate(profile, adapter, scenario)
    b = simulate(profile, adapter, scenario)
    assert a == b
