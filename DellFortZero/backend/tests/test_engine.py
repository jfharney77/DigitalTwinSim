"""Full-trace invariants for the Fort Zero access engine (style of the GPU,
R760, and PowerStore twins): assert over the whole simulate() trace, no HTTP
layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import BREACH_PHASES, GRANTED_PHASES, PILLARS, simulate

PHASE_ORDER = [
    "idle", "request", "verify", "context", "decide",
    "grant", "monitor", "expire", "breach", "contained",
]

KIND_BY_REGION = {r.id: r.kind for r in ANATOMY.regions}


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


def test_nothing_is_ever_trusted_implicitly():
    """THE invariant, and this twin's reason for existing. No access in this
    trace is granted by position, membership, or the fact that something
    similar was allowed a moment ago. Every grant is a decision made for one
    request against one resource."""
    for s in simulate():
        assert s.implicit_trust_grants == 0, (
            f"step {s.step} ({s.phase}): {s.implicit_trust_grants} implicit "
            f"grants — that is a perimeter wearing a zero-trust label"
        )


def test_network_location_never_authorizes():
    """The pivotal distinction. When network context is gathered it raises
    confidence and grants nothing: the request is still unauthorized until
    the policy engine rules on it. In a perimeter model this step *is* the
    authorization."""
    trace = simulate()
    ctx = next(s for s in trace if s.phase == "context")
    assert "network" in ctx.active_regions, "context step must consider location"
    assert ctx.resources_reachable == 0, (
        "being on the network reached something — that is the perimeter model"
    )
    decide_idx = next(i for i, s in enumerate(trace) if s.phase == "decide")
    for s in trace[:decide_idx + 1]:
        assert s.resources_reachable == 0, (
            f"step {s.step} ({s.phase}): access before a decision"
        )


def test_the_breach_reaches_nothing():
    """The step every architecture is actually judged on. An attacker holds
    a valid position inside the network — the exact position a boundary
    model defines as trusted — and reaches zero resources. Not because the
    attack was blocked, but because being inside was never worth anything."""
    trace = simulate()
    breached = [s for s in trace if s.phase in BREACH_PHASES]
    assert breached, "no breach in the trace — the claim would be untested"
    for s in breached:
        assert s.resources_reachable == 0, (
            f"step {s.step}: attacker inside reached {s.resources_reachable} "
            f"resources"
        )
        assert s.implicit_trust_grants == 0
        assert s.trust_score == 0, (
            f"step {s.step}: the intruder inherited standing confidence"
        )


def test_the_breach_is_actually_inside():
    """The claim is only interesting if the attacker genuinely has the
    position a perimeter would have honoured: on the internal network, with
    the network pillar registering them."""
    trace = simulate()
    breach = next(s for s in trace if s.phase == "breach")
    assert "network" in breach.active_regions
    assert "visibility" in breach.active_regions


def test_verification_is_continuous_not_once():
    """One check at the door is not this model. Verifications climb through
    the session, and most steeply while access is live."""
    trace = simulate()
    counts = [s.verifications for s in trace]
    assert all(a <= b for a, b in zip(counts, counts[1:])), (
        "verification count went backwards"
    )
    granted = [s for s in trace if s.phase in GRANTED_PHASES]
    assert granted[-1].verifications > granted[0].verifications, (
        "no verification happened during a live session"
    )


def test_trust_is_a_lease_not_a_property():
    """A grant carries an expiry, and when it runs out the session is back
    to nothing — no residual confidence, no reachable resource."""
    trace = simulate()
    for s in trace:
        if s.phase in GRANTED_PHASES:
            assert s.trust_ttl_seconds > 0, (
                f"step {s.step}: access granted with no expiry"
            )
        else:
            assert s.trust_ttl_seconds == 0, (
                f"step {s.step} ({s.phase}): a lease outside a grant"
            )
    expire = next(s for s in trace if s.phase == "expire")
    assert expire.trust_score == 0
    assert expire.resources_reachable == 0


def test_least_privilege_is_literal():
    """At most one resource, ever. Not a share, not a segment, not a role's
    worth of things."""
    for s in simulate():
        assert s.resources_reachable <= 1, (
            f"step {s.step}: {s.resources_reachable} resources reachable at once"
        )


def test_no_grant_without_a_decision():
    """Access follows a ruling by the policy engine, and the engine is
    consulted at that ruling."""
    trace = simulate()
    first_decide = next(i for i, s in enumerate(trace) if s.phase == "decide")
    first_grant = next(i for i, s in enumerate(trace) if s.resources_reachable > 0)
    assert first_decide < first_grant
    assert "policy" in trace[first_decide].active_regions


def test_the_policy_engine_is_consulted_on_every_active_step():
    """It is a decision point, not a gateway that steps aside once opened —
    so from the first request onward it is never absent."""
    trace = simulate()
    for s in trace:
        if s.phase == "idle":
            continue
        assert "policy" in s.active_regions, (
            f"step {s.step} ({s.phase}): decision made without the policy engine"
        )


def test_all_seven_pillars_feed_the_decision():
    """The DoD model is an architecture, not a menu: a gap in any pillar is
    a route around all of them. At the decision step, every one of them is
    represented."""
    trace = simulate()
    decide = next(s for s in trace if s.phase == "decide")
    active = set(decide.active_regions)
    missing = [p for p in PILLARS if p not in active]
    assert not missing, f"pillars absent from the decision: {missing}"
    kinds = {KIND_BY_REGION[r] for r in active}
    assert len(kinds) == 8, "the decision must draw on all seven pillars plus policy"


def test_active_regions_exist_in_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    for state in simulate():
        for rid in state.active_regions:
            assert rid in region_ids, f"step {state.step}: unknown region {rid!r}"


def test_cycle_cost_at_least_one():
    assert all(s.cycle_cost >= 1 for s in simulate())


def test_continuous_monitoring_is_the_longest_stage():
    """The honest shape of zero trust's cost. It is not the login that is
    expensive — it is the never stopping. The UI dwells there for the same
    reason the Cyber Detect twin dwells on reading every byte."""
    trace = simulate()
    mon = [s for s in trace if s.phase == "monitor"]
    assert mon, "no monitoring step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert mon[0].cycle_cost == max_cost
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


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
