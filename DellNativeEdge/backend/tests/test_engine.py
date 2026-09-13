"""Full-trace invariants for the zero-touch onboarding engine (style of the
GPU, R760, and CloudIQ twins): assert over the whole simulate() trace, no
HTTP layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import ENDPOINTS, simulate
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PHASE_ORDER = [
    "crated", "power", "attest", "onboard",
    "provision", "blueprint", "workload", "managed",
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


def test_exactly_one_human_action():
    """THE invariant, and this twin's reason for existing: operator_actions
    is 0 before the power phase, becomes 1 there — someone plugs in power
    and a network cable — and never increments again. No state in this
    trace requires a local operator."""
    trace = simulate()
    power_at = next(i for i, s in enumerate(trace) if s.phase == "power")
    for i, s in enumerate(trace):
        expected = 0 if i < power_at else 1
        assert s.operator_actions == expected, (
            f"step {s.step} ({s.phase}): operator_actions="
            f"{s.operator_actions}, expected {expected}"
        )


def test_nothing_runs_before_trust_is_established():
    """Zero-touch without attestation is just an unauthenticated machine on
    your network: until trust_established is true, no endpoint counts as
    online and no workload-or-later phase is reached."""
    for s in simulate():
        if not s.trust_established:
            assert s.endpoints_online == 0, (
                f"step {s.step} ({s.phase}): endpoints online before trust"
            )
            assert PHASE_ORDER.index(s.phase) < PHASE_ORDER.index("workload"), (
                f"step {s.step}: reached {s.phase} without trust"
            )


def test_trust_is_never_revoked_mid_sequence():
    """Once the device has proven what it is, that proof holds for the rest
    of the trace — trust is monotone."""
    seen = False
    for s in simulate():
        if seen:
            assert s.trust_established, (
                f"step {s.step} ({s.phase}): trust revoked mid-sequence"
            )
        seen = seen or s.trust_established
    assert seen, "trust is never established anywhere in the trace"


def test_the_orchestrator_is_never_the_thing_being_onboarded():
    """endpoints_online counts the estate's endpoints and nothing else: it
    never exceeds the number of endpoint regions in the anatomy, and it
    reaches exactly that number — the Orchestrator does the claiming and
    is never claimed."""
    endpoint_count = sum(1 for r in ANATOMY.regions if r.kind == "endpoint")
    trace = simulate()
    for s in trace:
        assert s.endpoints_online <= endpoint_count, (
            f"step {s.step}: more endpoints online than exist"
        )
    assert trace[-1].endpoints_online == endpoint_count


def test_estate_scales_in_lockstep():
    """Whenever any endpoint region is active, all of them are — an estate
    is provisioned as a set, not one box at a time."""
    all_endpoints = {f"endpoint-{e}" for e in ENDPOINTS}
    for s in simulate():
        lit = {r for r in s.active_regions if r.startswith("endpoint-")}
        if lit:
            assert lit == all_endpoints, (
                f"step {s.step} ({s.phase}): partial endpoint set {lit}"
            )


def test_attestation_is_the_longest_stage():
    """Proving integrity is genuinely the slow part, and the UI dwells
    there rather than skipping the security step as boilerplate."""
    trace = simulate()
    attest = [s for s in trace if s.phase == "attest"]
    assert attest, "no attestation step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert attest[0].cycle_cost == max_cost
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


def test_progress_is_monotonic_to_100():
    trace = simulate()
    progress = [s.progress_percent for s in trace]
    assert progress == sorted(progress), "progress regressed"
    assert progress[0] == 0 and progress[-1] == 100


def test_the_site_ends_fully_managed():
    """The final step lights the whole platform — estate, gate, brain,
    blueprints, catalog, policy, observability — because managed means the
    loop is closed, not merely that software landed."""
    final = simulate()[-1]
    assert final.phase == "managed"
    region_ids = {r.id for r in ANATOMY.regions}
    assert set(final.active_regions) == region_ids
