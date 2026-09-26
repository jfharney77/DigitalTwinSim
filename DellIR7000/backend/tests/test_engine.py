"""Full-trace invariants for the thermal bring-up engine (style of the GPU,
R760, and PowerStore twins): assert over the whole simulate() trace, no HTTP
layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import BAYS, simulate
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PHASE_ORDER = [
    "off", "fill", "pump", "verify", "airdoor", "load", "balance", "steady",
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


def test_heat_balance_holds_on_every_step():
    """The twin's defining invariant: energy is conserved. Every watt of IT
    load leaves through the liquid loop or the rear door — exactly, on every
    step, with no tolerance. Heat is not managed; it is conserved."""
    for s in simulate():
        assert s.liquid_watts + s.air_watts == s.it_load_watts, (
            f"step {s.step} ({s.phase}): {s.liquid_watts} + {s.air_watts} "
            f"!= {s.it_load_watts}"
        )


def test_liquid_carries_the_overwhelming_share():
    """Direct liquid cooling is the point: whenever there is load, at least
    85% of it leaves through the liquid loop, the rest via the rear door."""
    for s in simulate():
        if s.it_load_watts > 0:
            assert s.liquid_watts / s.it_load_watts >= 0.85, (
                f"step {s.step}: liquid share "
                f"{s.liquid_watts / s.it_load_watts:.2f} < 0.85"
            )


def test_flow_before_heat():
    """Liquid before silicon, seen from the loop's side: coolant is flowing
    (flow_lpm > 0) strictly before the first watt of IT load appears, and
    flow never decreases while load is climbing."""
    trace = simulate()
    first_flow = next(i for i, s in enumerate(trace) if s.flow_lpm > 0)
    first_load = next(i for i, s in enumerate(trace) if s.it_load_watts > 0)
    assert first_flow < first_load
    flows = [s.flow_lpm for s in trace]
    assert flows == sorted(flows), "flow regressed during bring-up"


def test_load_monotonic_to_design_point():
    trace = simulate()
    loads = [s.it_load_watts for s in trace]
    assert loads[0] == 0, "starts with a dry, dark rack"
    assert loads == sorted(loads), "IT load regressed during the ramp"
    assert loads[-1] >= 200_000, "ends at the IR7000-class design point"


def test_verification_is_the_longest_stage():
    """The per-branch leak/flow verification is the single longest stage —
    the careful commissioning work the compute twins' liquid-before-silicon
    interlock waits on. The UI dwells here."""
    trace = simulate()
    verify = [s for s in trace if s.phase == "verify"]
    assert verify, "no verification step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert verify[0].cycle_cost == max_cost
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


def test_bays_heat_in_lockstep():
    """Whenever any bay's cold plates are active, all four bays' are — the
    loop treats the payload as uniform heat, and verification, load, and
    balance sweep every branch together."""
    for state in simulate():
        active = set(state.active_regions)
        lit = {rid for rid in active if rid.startswith("coldplate-")}
        if lit:
            assert lit == {f"coldplate-{b}" for b in BAYS}, (
                f"step {state.step}: bays {lit} lit without their twins"
            )


def test_flow_tracks_load_so_the_loop_rise_holds_steady():
    """The prose says the CDU speeds its pumps to hold the supply-return
    temperature difference steady. Both heat paths reject into the one rack
    loop, so that claim means load / flow is constant once load exists: a
    reader dividing the two numbers on the panel must get the same answer
    (within 2%) on every loaded step."""
    trace = simulate()
    ratios = [s.it_load_watts / s.flow_lpm for s in trace if s.it_load_watts]
    assert len(ratios) >= 3
    assert max(ratios) / min(ratios) < 1.02, ratios
