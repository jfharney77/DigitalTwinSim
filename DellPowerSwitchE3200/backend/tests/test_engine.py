"""Full-trace invariants for the E3200 boot engine (style of the R760 app's
test_engine.py): assert over the whole simulate() trace, no HTTP layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import simulate
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PHASE_ORDER = [
    "off", "standby", "poweron", "onie", "nos", "dataplane", "ports", "forwarding",
]


PROFILE = TraceProfile(phases=PHASE_ORDER, anatomy=ANATOMY)


def test_trace_invariants():
    """Steps from zero, phases in order and all reached, the clock advancing,
    only real regions lit, every step at least one cycle — and deterministic.
    The shared definitions live in twinkit.testing."""
    assert_trace_invariants(simulate(), PROFILE)
    assert_deterministic(simulate)


def test_engine_is_pure():
    import app.engine as engine_module

    assert_engine_is_pure(engine_module)


def test_power_watts_bounds():
    trace = simulate()
    assert all(s.power_watts >= 0 for s in trace)
    assert trace[0].power_watts == 0, "starts dark at AC disconnect"
    assert trace[-1].power_watts > 0, "ends forwarding with PoE up"


def test_fan_percent_in_range():
    trace = simulate()
    assert all(0 <= s.fan_percent <= 100 for s in trace)


def test_data_rate_zero_until_ports_then_nonzero_at_end():
    trace = simulate()
    # No traffic before the data plane / ports come up.
    early = [s for s in trace if s.phase in ("off", "standby", "poweron", "onie", "nos")]
    assert all(s.data_rate_gbps == 0 for s in early)
    assert trace[-1].data_rate_gbps > 0, "ends carrying line-rate traffic"


def test_poe_step_is_the_power_peak():
    """Most of the switch's wattage is the PoE budget leaving the front ports,
    so total draw peaks once PoE is delivered."""
    trace = simulate()
    poe = [s for s in trace if "poe" in s.label.lower()]
    assert poe, "no PoE step in the trace"
    assert max(s.power_watts for s in trace) == max(s.power_watts for s in poe)


def test_nos_boot_is_the_longest_stage():
    trace = simulate()
    nos = [s for s in trace if "network os" in s.label.lower()]
    assert nos, "no network-OS boot step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert nos[0].cycle_cost == max_cost
    # Strictly the single longest stage.
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1
