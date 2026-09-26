"""The node-loss scenario: a serving array loses node A and gets it back.

House style: assert over the whole trace, no server. The shared trace
invariants come from twinkit.testing; what stays here is what must hold
*because the failure happened* — and that adding the scenario left the
power-on trace exactly as it was.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

import app.failover as failover_module
from app.anatomy import ANATOMY
from app.engine import simulate
from app.failover import (
    NODE_A,
    PHASE_ORDER,
    SCENARIO,
    SCENARIO_ID,
    SCENARIOS,
    simulate_node_loss,
)
from app.leveling import leveled
from app.main import app as api
from app.models import FailoverResponse, PowerOnResponse, PowerOnState
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PROFILE = TraceProfile(phases=PHASE_ORDER, anatomy=ANATOMY)
DOWN = ("fault", "failover", "degraded")


def first(trace, phase):
    return next(s.step for s in trace if s.phase == phase)


# --- shared invariants -------------------------------------------------------


def test_trace_invariants():
    assert_trace_invariants(simulate_node_loss(), PROFILE)
    assert_deterministic(simulate_node_loss)


def test_the_scenario_module_is_pure():
    assert_engine_is_pure(failover_module)


def test_failed_regions_are_real_and_never_lit():
    known = {r.id for r in ANATOMY.regions}
    for s in simulate_node_loss():
        assert set(s.failed_regions) <= known, f"step {s.step}"
        assert not set(s.failed_regions) & set(s.active_regions), (
            f"step {s.step}: a region is drawn both failed and active"
        )


def test_it_starts_where_the_power_on_trace_ends():
    """Not a power-on trace: step 0 is the serving array, lit exactly as the
    happy path leaves it, drawing the same power."""
    start, end = simulate_node_loss()[0], simulate()[-1]
    assert start.phase == "online"
    assert set(start.active_regions) == set(end.active_regions)
    assert start.power_watts == end.power_watts
    assert not start.failed_regions


# --- what must hold because node A failed ------------------------------------


def test_no_acknowledged_write_is_ever_lost():
    """The hero number. It is zero on every step, including the step on
    which the node dies."""
    trace = simulate_node_loss()
    assert any(s.failed_regions for s in trace), "nothing actually failed"
    assert all(s.acked_writes_lost == 0 for s in trace)


def test_the_failure_is_real():
    """Zero writes lost proves nothing unless a node is genuinely down: all
    of node A's compute and ports are failed, and one node is serving."""
    trace = simulate_node_loss()
    # Derived from the chassis map, not imported from the scenario: everything
    # on node A that computes or carries traffic. Power, battery and fans stay
    # up, because a crashed node still has AC.
    node_a = {
        r.id for r in ANATOMY.regions
        if r.id.rstrip("12").endswith("-a")
        and r.kind in {"cpu", "memory", "board", "io", "management"}
    }
    assert node_a == set(NODE_A) and len(node_a) == 7
    for s in trace:
        if s.phase in DOWN:
            assert node_a <= set(s.failed_regions), f"step {s.step}"
            assert s.nodes_serving == 1
            assert not s.node_a_joined
            assert not any(r.endswith("-a") and r != "bbu-a" for r in s.active_regions)


def test_io_never_stops_and_the_dip_is_bounded():
    trace = simulate_node_loss()
    assert all(s.io_percent > 0 for s in trace), "I/O stopped"
    floor = min(s.io_percent for s in trace)
    assert 50 <= floor < 100, "the dip is node A's share at most, and it is a dip"
    assert min(trace, key=lambda s: s.io_percent).phase == "fault"
    # The dip is over before the degraded phase: one node carries the full rate.
    for s in trace:
        if s.step >= first(trace, "degraded"):
            assert s.io_percent == 100, f"step {s.step}"
    # And recovery from the dip never goes backwards.
    after = [s.io_percent for s in trace if s.step >= first(trace, "fault")]
    assert after == sorted(after)


def test_writes_stay_mirrored_while_single_node():
    """The write cache is a mirrored NVRAM pair in the shared bay, outside
    either node. So on every step — single-node ones included — writes are
    mirrored, and the shared bay that holds them is lit and never failed."""
    for s in simulate_node_loss():
        assert s.writes_mirrored, f"step {s.step}"
        assert {"nvram", "drive-bay"} <= set(s.active_regions), f"step {s.step}"
        assert not {"nvram", "drive-bay", "bbu-a", "bbu-b"} & set(s.failed_regions)


def test_the_survivor_pays_in_headroom():
    """Node B serves all volumes at reduced headroom: its load roughly
    doubles, stays under 100, and returns to where it started."""
    trace = simulate_node_loss()
    before = trace[0].node_b_load_percent
    peak = max(s.node_b_load_percent for s in trace)
    assert peak >= 2 * before - 5
    assert peak < 100
    assert trace[first(trace, "degraded")].node_b_load_percent == peak
    assert trace[-1].node_b_load_percent == before


def test_paths_fail_over_to_the_survivor():
    """While node A is out, half the volumes run on non-optimized paths —
    and none of node A's front-end ports are lit."""
    for s in simulate_node_loss():
        if s.phase in DOWN:
            assert s.optimized_paths_percent == 50
            assert {"embedded-b", "iomod-b1", "iomod-b2"} <= set(s.active_regions)


def test_rejoin_precedes_rebalance():
    """Node A is a member again, and has caught up, strictly before any
    volume moves back to it."""
    trace = simulate_node_loss()
    joined = next(s.step for s in trace if s.step > 0 and s.node_a_joined)
    assert trace[joined].phase == "rejoin"
    assert joined < first(trace, "resync") < first(trace, "rebalance")
    for s in trace:
        if first(trace, "fault") <= s.step < first(trace, "rebalance"):
            assert s.nodes_serving == 1, f"step {s.step}: served before failback"
            assert s.optimized_paths_percent == 50, f"step {s.step}"
    # Once joined, never lost again.
    assert all(s.node_a_joined for s in trace if s.step >= joined)


def test_it_ends_fully_restored():
    end = simulate_node_loss()[-1]
    assert end.phase == "restored"
    assert (end.nodes_serving, end.io_percent, end.optimized_paths_percent) == (2, 100, 100)
    assert not end.failed_regions


def test_the_node_reboot_is_the_longest_stage():
    trace = simulate_node_loss()
    top = max(s.cycle_cost for s in trace)
    longest = [s for s in trace if s.cycle_cost == top]
    assert len(longest) == 1 and longest[0].phase == "rejoin"
    assert "reboot" in longest[0].label.lower()


def test_the_scenario_cites_its_sources_and_says_what_is_illustrative():
    assert SCENARIO.id == SCENARIO_ID
    assert len(SCENARIO.sources) >= 2
    assert all(src.url.startswith("https://") for src in SCENARIO.sources)
    assert "illustrative" in SCENARIO.basis
    assert [s.id for s in SCENARIOS] == ["power-on", SCENARIO_ID]


def test_the_nvram_claim_is_scoped_to_models_that_have_nvram():
    """The PowerStore 500 has no NVRAM drives (Dell H18149), so 'the write
    cache is outside both nodes' is not true of it. The scenario must say
    which models it is about, at every authored level."""
    assert "500" in SCENARIO.basis
    base = FailoverResponse(scenario=SCENARIO, trace=simulate_node_loss())
    for level in (1, 3, 5):
        degraded = next(s for s in leveled(base, level).trace if s.phase == "degraded")
        assert "500" in degraded.description, f"level {level}"


def test_the_degraded_step_answers_the_write_through_question_at_every_level():
    """The question a reader arrives with is whether the survivor drops to a
    slower write-through mode. The counters say 'writes mirrored: yes' but
    cannot say why, so the prose must answer it, and must answer it as Dell's
    architecture does — the peer is not in the write path — rather than
    leaving the reader a bare assertion."""
    base = FailoverResponse(scenario=SCENARIO, trace=simulate_node_loss())
    for level in (1, 3, 5):
        text = next(
            s for s in leveled(base, level).trace if s.phase == "degraded"
        ).description.lower()
        assert "peer" in text or "other node" in text, f"level {level}"
        assert "write-through" in text or "way of writing" in text, f"level {level}"


def test_step_prose_is_leveled_at_1_3_and_5():
    base = FailoverResponse(scenario=SCENARIO, trace=simulate_node_loss())
    novice, expert = leveled(base, 1), leveled(base, 5)
    assert leveled(base, 3).model_dump() == base.model_dump()
    for n, s, e in zip(novice.trace, base.trace, expert.trace):
        assert n.description != s.description != e.description
        assert len(n.description) > len(e.description), (
            f"step {s.step}: the scale runs the wrong way"
        )


# --- the happy path is untouched ---------------------------------------------

POWER_ON_KEYS = {
    "step", "phase", "label", "description", "activeRegions",
    "powerWatts", "fanPercent", "elapsedSeconds", "cycleCost",
}


def test_the_power_on_state_model_gained_no_fields():
    """The scenario extends the state additively, in a subclass. The
    power-on wire shape is exactly the nine keys it always had."""
    assert {f.alias for f in PowerOnState.model_fields.values()} == POWER_ON_KEYS
    for s in simulate():
        assert type(s) is PowerOnState
        assert set(s.model_dump(by_alias=True)) == POWER_ON_KEYS


def test_the_power_on_endpoint_is_byte_identical():
    """With no scenario, with the default named, and at every level, the
    endpoint returns the bytes it returned before the scenario existed:
    the serialized, leveled simulate() trace and nothing else."""
    client = TestClient(api)
    for level in (1, 3, 5):
        want = leveled(PowerOnResponse(trace=simulate()), level)
        expected = want.model_dump_json(by_alias=True).encode()
        bare = client.get(f"/api/poweron?level={level}")
        named = client.get(f"/api/poweron?level={level}&scenario=power-on")
        assert bare.status_code == named.status_code == 200
        assert bare.content == named.content == expected
    assert len(simulate()) == 14
    assert simulate()[-1].label == "Serving I/O — active/active"


def test_the_scenario_is_served_on_the_same_endpoint():
    client = TestClient(api)
    body = client.get(f"/api/poweron?scenario={SCENARIO_ID}").json()
    assert body["scenario"]["id"] == SCENARIO_ID
    assert [s["step"] for s in body["trace"]] == list(range(len(simulate_node_loss())))
    assert body["trace"][1]["failedRegions"]
    assert all(s["ackedWritesLost"] == 0 for s in body["trace"])
    assert client.get("/api/poweron?scenario=no-such").status_code == 404
    listed = client.get("/api/scenarios").json()
    assert [s["id"] for s in listed] == ["power-on", SCENARIO_ID]
