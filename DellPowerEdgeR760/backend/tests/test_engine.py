"""Full-trace invariants for the power-on engine (style of the GPU app's
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

PHASE_ORDER = ["off", "standby", "bmc", "poweron", "post", "boot", "os"]


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
    assert trace[0].power_watts == 0, "starts dark at AC plug-in"
    assert trace[-1].power_watts > 0, "ends with the OS running"


def test_fan_percent_in_range():
    trace = simulate()
    assert all(0 <= s.fan_percent <= 100 for s in trace)


def test_memory_training_is_the_longest_stage():
    trace = simulate()
    training = [s for s in trace if "training" in s.label.lower()]
    assert training, "no memory-training step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert training[0].cycle_cost == max_cost
    # Strictly the single longest stage.
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


def test_the_clock_agrees_that_memory_training_is_longest():
    """``elapsed_seconds`` is stamped at the end of each step, so a step's
    duration is its stamp minus the previous one. The on-screen clock must
    tell the same story as ``cycle_cost``: training is the single largest gap."""
    trace = simulate()
    durations = [
        s.elapsed_seconds - (trace[i - 1].elapsed_seconds if i else 0)
        for i, s in enumerate(trace)
    ]
    training = next(i for i, s in enumerate(trace) if "training" in s.label.lower())
    assert durations[training] == max(durations)
    assert durations.count(max(durations)) == 1


def test_dwell_never_argues_with_the_clock():
    """Playback dwell is ``cycle_cost``; the counter prints the duration.

    A reader who presses Run while watching "this step takes" must see one
    story. So the twin may not linger longer on a shorter step: order the
    steps by duration and dwell must be weakly increasing alongside it."""
    trace = simulate()
    durations = [
        s.elapsed_seconds - (trace[i - 1].elapsed_seconds if i else 0)
        for i, s in enumerate(trace)
    ]
    pairs = sorted(zip(durations, (s.cycle_cost for s in trace)))
    for (short_s, short_cost), (long_s, long_cost) in zip(pairs, pairs[1:]):
        assert short_cost <= long_cost, (
            f"{short_s} s dwells {short_cost} ticks but {long_s} s dwells "
            f"{long_cost} — playback contradicts the clock"
        )


def test_inventory_does_not_claim_the_nic_sideband():
    """NC-SI is the BMC-to-NIC pass-through, not an inventory bus."""
    inventory = next(s for s in simulate() if s.label == "Hardware inventory")
    assert "NC-SI" not in inventory.description
