"""C2 — the CDU's limits come back as compute throttling (closed loop with C1)."""

from __future__ import annotations

import copy

from compose import Chain, Link, assert_seams, presets, run

LINKS = (Link("c1", "PhysicsCompute", "PhysicsCDU", {"racks": 2}),
         Link("c2", "PhysicsCDU", "PhysicsCompute"))


def _loop(cdu: dict) -> Chain:
    return Chain(id="t-c2", scenarios={"PhysicsCompute": presets.XE9712_RAMP, "PhysicsCDU": cdu},
                 links=LINKS, closed=True)


def test_closed_loop_converges_and_is_deterministic():
    first = run(presets.chain("closed-loop"))
    second = run(presets.chain("closed-loop"))
    assert first.model_dump_json() == second.model_dump_json()
    assert first.converged and 1 < first.iterations <= 12
    assert first.residual_history[-1] < 0.005
    # Monotone non-increasing after iteration 2: the loop settles, it does not ring.
    tail = first.residual_history[1:]
    assert all(b <= a + 1e-9 for a, b in zip(tail, tail[1:])), first.residual_history
    assert_seams(first)
    # At the fixed point the CDU no longer needs most of the cap it asked for open-loop.
    open_cap = min(v for v in first.iteration_log[0].series["cap_pct"])
    final_cap = min(v for v in first.iteration_log[-1].series["cap_pct"])
    assert final_cap > open_cap


def test_a_design_day_needs_one_pass():
    trace = run(_loop({}))
    assert trace.converged and trace.iterations == 1
    assert_seams(trace)


def test_warm_water_day_costs_tokens_in_the_coupled_run():
    trace = run(presets.chain("closed-loop"))
    tokens = next(s for s in trace.seams if "tokens" in s.identity)
    assert tokens.holds and tokens.lhs < tokens.rhs, "coupled strictly below open loop"
    design = run(_loop({}))
    same = next(s for s in design.seams if "tokens" in s.identity)
    assert same.lhs == same.rhs, "with nothing wrong the loop costs nothing"


def test_uncoordinated_policy_trips_restrict_the_right_trays():
    panic = copy.deepcopy(presets.WARM_WATER)
    panic["config"] = {"policy": "uncoordinated"}
    trace = run(_loop(panic))
    cdu = next(s for s in trace.stages if s.id == "PhysicsCDU")
    compute = next(s for s in trace.stages if s.id == "PhysicsCompute")
    tripped = [i for i, status in enumerate(cdu.trace[-1]["bankStatus"]) if status == "tripped"]
    assert tripped, "the panic run trips banks"
    restricted = sorted(e["index"] for e in compute.injected_events if e["action"] == "restrict-tray")
    assert restricted == sorted(t for bank in tripped for t in range(3 * bank, 3 * bank + 3))
    assert any("trip set" in r.note for r in trace.iteration_log), "the pinned trip set is recorded"
    # Latched trips make the map discontinuous; the solver still stops inside its budget.
    assert trace.iterations <= 12
