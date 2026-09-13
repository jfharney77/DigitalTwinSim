"""Full-trace invariants for the power-on engine (style of the GPU, R760, and
PowerStore apps): assert over the whole simulate() trace, no HTTP layer."""

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
    "off", "power", "vault", "boot", "fabric", "drives", "pool", "services",
    "online",
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
    assert trace[0].power_watts == 0, "starts dark at AC plug-in"
    assert trace[-1].power_watts > 0, "ends serving I/O"


def test_fan_percent_in_range():
    trace = simulate()
    assert all(0 <= s.fan_percent <= 100 for s in trace)


def test_powermaxos_boot_is_the_longest_stage():
    trace = simulate()
    boot = [s for s in trace if "powermaxos" in s.label.lower()]
    assert boot, "no PowerMaxOS-boot step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert boot[0].cycle_cost == max_cost
    # Strictly the single longest stage.
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


def test_fabric_phase_precedes_drive_discovery():
    """The drives hang off the InfiniBand fabric, so the fabric must come up
    before drive discovery — the architectural point of scale-out PowerMax."""
    trace = simulate()
    first_fabric = next(i for i, s in enumerate(trace) if s.phase == "fabric")
    first_drives = next(i for i, s in enumerate(trace) if s.phase == "drives")
    assert first_fabric < first_drives


def test_dual_node_bring_up_is_symmetric():
    """In power/vault/boot, whatever lights on node A lights on node B too —
    the two directors wake in parallel, never one at a time."""
    for state in simulate():
        if state.phase not in ("power", "vault", "boot"):
            continue
        active = set(state.active_regions)
        for rid in active:
            if rid.endswith("-a"):
                twin = rid[:-2] + "-b"
                assert twin in active, (
                    f"step {state.step}: {rid} lit without its twin {twin}"
                )
            elif rid.endswith("-b"):
                twin = rid[:-2] + "-a"
                assert twin in active, (
                    f"step {state.step}: {rid} lit without its twin {twin}"
                )
