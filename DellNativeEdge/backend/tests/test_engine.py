"""Full-trace invariants for the zero-touch onboarding engine (style of the
GPU, R760, and CloudIQ twins): assert over the whole simulate() trace, no
HTTP layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import ENDPOINTS, simulate

PHASE_ORDER = [
    "crated", "power", "attest", "onboard",
    "provision", "blueprint", "workload", "managed",
]


def test_steps_sequential_from_zero():
    trace = simulate()
    assert [s.step for s in trace] == list(range(len(trace)))


def test_phase_order_never_regresses_and_all_phases_appear():
    trace = simulate()
    indices = [PHASE_ORDER.index(s.phase) for s in trace]
    assert indices == sorted(indices), "phase order regressed"
    assert set(s.phase for s in trace) == set(PHASE_ORDER)


def test_elapsed_seconds_strictly_increasing():
    trace = simulate()
    elapsed = [s.elapsed_seconds for s in trace]
    assert all(a < b for a, b in zip(elapsed, elapsed[1:]))


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


def test_active_regions_exist_in_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    for state in simulate():
        for rid in state.active_regions:
            assert rid in region_ids, f"step {state.step}: unknown region {rid!r}"


def test_cycle_cost_at_least_one():
    assert all(s.cycle_cost >= 1 for s in simulate())


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
    assert not imported & {"fastapi", "time", "asyncio", "threading", "os", "io"}
