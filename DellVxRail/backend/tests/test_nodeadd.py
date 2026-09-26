"""The day-2 failure scenario: a fifth node refused on a version mismatch.

House style: assert over the whole ``simulate_node_add()`` trace. The shared
trace invariants come from ``twinkit.testing``; what stays here is what must
hold *because the failure happened* — the mismatched node never joins vSAN,
the running cluster is untouched throughout, and capacity grows only after
the successful retry — plus the pin that the first-run trace is byte-identical
to what it was before scenarios existed.
"""

from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from app.anatomy import ANATOMIES, ANATOMY, NODE_ADD_ANATOMY
from app.engine import FABRIC, NODES, simulate
from app.main import app
from app.nodeadd import (
    CLUSTER_VERSION,
    FACTORY_VERSION,
    NEW_NODE,
    PHASE_ORDER,
    SCENARIO_ID,
    SCENARIOS,
    SERVING,
    TB_PER_NODE,
    simulate_node_add,
)
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PROFILE = TraceProfile(phases=PHASE_ORDER, anatomy=NODE_ADD_ANATOMY)

client = TestClient(app)


def _new_node(ids):
    return {rid for rid in ids if rid.endswith(f"-{NEW_NODE}")}


def _first(trace, phase):
    return next(s.step for s in trace if s.phase == phase)


# --- shared invariants -----------------------------------------------------


def test_trace_invariants():
    assert_trace_invariants(simulate_node_add(), PROFILE)
    assert_deterministic(simulate_node_add)


def test_engine_is_pure():
    import app.nodeadd as module

    assert_engine_is_pure(module)


def test_failed_regions_exist_on_the_map():
    known = {r.id for r in NODE_ADD_ANATOMY.regions}
    for s in simulate_node_add():
        for rid in s.failed_regions:
            assert rid in known, f"step {s.step}: unknown failed region {rid!r}"


# --- the signature invariants ----------------------------------------------


def test_a_mismatched_node_never_joins_vsan():
    """The twin's reason for this trace. On every step where the node's
    version differs from the cluster's, vSAN has exactly the original four
    hosts and the new node's drives are dark."""
    trace = simulate_node_add()
    mismatched = [s for s in trace if s.node_version != s.cluster_version]
    assert mismatched, "the trace never shows a mismatch, so it proves nothing"
    for s in trace:
        assert s.mismatched_nodes_in_vsan == 0, f"step {s.step}"
        # The counter is computed from the state, not typed in: recount it.
        extra = s.vsan_nodes - len(NODES)
        recount = extra if s.node_version != s.cluster_version else 0
        assert s.mismatched_nodes_in_vsan == recount, f"step {s.step}"
    for s in mismatched:
        assert s.vsan_nodes == len(NODES), (
            f"step {s.step}: vSAN grew while the node was at {s.node_version}"
        )
        assert f"storage-{NEW_NODE}" not in s.active_regions, (
            f"step {s.step}: the mismatched node's NVMe is lit"
        )


def test_the_mismatch_is_real_and_the_node_is_older():
    """Silence proves nothing unless the fault is present: the node really
    does arrive on an older image than the cluster runs."""
    trace = simulate_node_add()
    as_tuple = lambda v: tuple(int(p) for p in v.split("."))
    racked = next(s for s in trace if s.phase == "racked")
    assert racked.node_version == FACTORY_VERSION
    assert as_tuple(FACTORY_VERSION) < as_tuple(CLUSTER_VERSION)
    assert all(s.cluster_version == CLUSTER_VERSION for s in trace), (
        "the cluster is never downgraded to suit the node"
    )


def test_the_refusal_marks_the_new_node_and_nothing_else():
    """Exactly one step draws failed regions: the refusal, and it marks every
    region of node 5 and no region of the serving cluster."""
    trace = simulate_node_add()
    failing = [s for s in trace if s.failed_regions]
    assert [s.phase for s in failing] == ["refused"]
    refused = failing[0]
    assert set(refused.failed_regions) == _new_node(
        r.id for r in NODE_ADD_ANATOMY.regions
    )
    assert not _new_node(refused.active_regions), (
        "a refused node does no work in the cluster"
    )
    assert "mgmt-n1" in refused.active_regions, (
        "VxRail Manager is the thing doing the refusing"
    )


def test_the_refusal_comes_before_the_node_touches_vsan():
    """What protects the data is where the check sits: the node's capacity
    drives are never lit, and vSAN never counts five, before the second check
    has passed."""
    trace = simulate_node_add()
    recheck = _first(trace, "recheck")
    for s in trace:
        if s.step <= recheck:
            assert f"storage-{NEW_NODE}" not in s.active_regions, f"step {s.step}"
            assert s.vsan_nodes == len(NODES), f"step {s.step}"


def test_the_running_cluster_is_untouched_throughout():
    """A node add, failed or not, is not an outage. Every original node's
    CPU, memory, NVMe, NIC and power supplies and both switches are lit on every step, the VM
    count never moves, and nothing on the original nodes is ever failed."""
    trace = simulate_node_add()
    vms = {s.vms_running for s in trace}
    assert len(vms) == 1 and vms.pop() > 0
    for s in trace:
        missing = set(SERVING) - set(s.active_regions)
        assert not missing, f"step {s.step}: serving regions dark: {sorted(missing)}"
        assert not (set(s.failed_regions) - _new_node(s.failed_regions)), (
            f"step {s.step}: a region of the running cluster is drawn failed"
        )
    assert set(FABRIC) <= set(SERVING)


def test_the_datastore_never_shrinks_and_grows_exactly_once():
    """Capacity grows only after the successful retry: one jump, of one
    node's worth, strictly after the recheck passes."""
    trace = simulate_node_add()
    tb = [s.datastore_tb for s in trace]
    assert tb == sorted(tb), "the datastore shrank"
    jumps = [i for i in range(1, len(tb)) if tb[i] != tb[i - 1]]
    assert len(jumps) == 1, f"capacity changed {len(jumps)} times"
    jump = trace[jumps[0]]
    assert jump.step > _first(trace, "recheck")
    assert jump.phase == "join"
    assert tb[jumps[0]] - tb[jumps[0] - 1] == TB_PER_NODE
    assert tb[0] == len(NODES) * TB_PER_NODE
    assert tb[-1] == (len(NODES) + 1) * TB_PER_NODE
    for s in trace:
        assert s.datastore_tb == s.vsan_nodes * TB_PER_NODE, f"step {s.step}"


def test_recovery_runs_in_order():
    """Refused, then re-imaged, then checked again, then joined, then
    rebalanced. The node's version changes exactly once, during the re-image,
    and only ever to the cluster's version."""
    trace = simulate_node_add()
    order = [_first(trace, p) for p in
             ("check", "refused", "reimage", "recheck", "join", "rebalance")]
    assert order == sorted(order) and len(set(order)) == len(order)
    versions = [s.node_version for s in trace]
    changes = [i for i in range(1, len(versions)) if versions[i] != versions[i - 1]]
    assert len(changes) == 1
    assert trace[changes[0]].phase == "recheck"
    assert versions[-1] == CLUSTER_VERSION
    # Rebalancing moves data that the join made room for, never before it.
    rebalance = next(s for s in trace if s.phase == "rebalance")
    assert rebalance.vsan_nodes == len(NODES) + 1


def test_the_reimage_is_node_local():
    """The cluster is not a participant in the recovery: VxRail Manager's
    block is dark and the node's network and drives are idle while RASR runs."""
    reimage = next(s for s in simulate_node_add() if s.phase == "reimage")
    assert "mgmt-n1" not in reimage.active_regions
    lit = _new_node(reimage.active_regions)
    assert f"boot-{NEW_NODE}" in lit, "the re-image rewrites the boot device"
    assert f"storage-{NEW_NODE}" not in lit
    assert f"network-{NEW_NODE}" not in lit


def test_the_reimage_is_the_longest_stage():
    """The honest cost of the refusal is time on node 5, not risk to the
    cluster: the re-image is the unique longest stage, longer than the
    rebalance."""
    trace = simulate_node_add()
    top = max(s.cycle_cost for s in trace)
    longest = [s for s in trace if s.cycle_cost == top]
    assert [s.phase for s in longest] == ["reimage"]


def test_the_clock_agrees_with_the_dwell():
    """``elapsedSeconds`` is when a stage starts, so a stage lasts until the
    next step's reading. The stage the UI dwells longest on must also be the
    one the clock gives the most time to, or the panel and the diagram tell
    the reader opposite stories. This caught the clock spacing the re-image's
    ninety minutes *before* the re-image step, which made the refusal look
    like the expensive part."""
    trace = simulate_node_add()
    spans = {
        trace[i].phase: trace[i + 1].elapsed_seconds - trace[i].elapsed_seconds
        for i in range(len(trace) - 1)
    }
    assert all(v > 0 for v in spans.values()), "a stage takes no time at all"
    by_dwell = sorted(trace[:-1], key=lambda s: -s.cycle_cost)
    assert [s.phase for s in by_dwell[:2]] == ["reimage", "rebalance"]
    assert spans["reimage"] == max(spans.values())
    assert spans["reimage"] > spans["rebalance"] > max(
        v for k, v in spans.items() if k not in ("reimage", "rebalance")
    )
    # The refusal itself is cheap: the check is read-only.
    assert spans["refused"] < spans["reimage"] / 10


def test_progress_resets_on_refusal_and_completes_on_retry():
    trace = simulate_node_add()
    by_phase = {s.phase: s.progress_percent for s in trace}
    assert by_phase["check"] > 0
    assert by_phase["refused"] == 0, "a refused add leaves nothing half-done"
    after = [s.progress_percent for s in trace if s.step >= _first(trace, "recheck")]
    assert after == sorted(after) and after[-1] == 100


def test_the_end_state_lights_the_whole_five_node_cluster():
    last = simulate_node_add()[-1]
    assert set(last.active_regions) == {r.id for r in NODE_ADD_ANATOMY.regions}
    assert last.failed_regions == []


def test_the_other_classic_cause_is_in_the_prose():
    """Discovery failing on the network is covered in the ``found`` step."""
    found = next(s for s in simulate_node_add() if s.phase == "found")
    text = found.description.lower()
    assert "ipv6 multicast" in text and "loudmouth" in text


# --- the day-2 map is additive ---------------------------------------------


def test_the_fifth_node_is_additive_and_identical():
    """The four-node map is a strict prefix of the five-node map, and node 5
    is the same building block as node 4, one slot lower."""
    four = [r.model_dump() for r in ANATOMY.regions]
    five = [r.model_dump() for r in NODE_ADD_ANATOMY.regions]
    assert five[: len(four)] == four
    n4 = {r.kind: r for r in NODE_ADD_ANATOMY.regions if r.id.endswith("-n4")}
    n5 = {r.kind: r for r in NODE_ADD_ANATOMY.regions if r.id.endswith(f"-{NEW_NODE}")}
    assert n5 and set(n4) == set(n5)
    for kind, r in n5.items():
        twin = n4[kind]
        assert (r.x, r.w, r.h) == (twin.x, twin.w, twin.h)
        assert r.y > twin.y
        assert r.y + r.h <= NODE_ADD_ANATOMY.height
    assert ANATOMIES["first-run"] is ANATOMY


# --- the wire --------------------------------------------------------------

# sha256 of GET /api/firstrun at three reading levels, taken from the commit
# before scenarios existed (e3b77c2), recomputed once since when the clock
# was stretched and the level-4/5 copy reworded on purpose. If the first-run trace or its prose is
# edited on purpose, recompute these; the point is that adding a scenario
# did not move them.
HAPPY_PATH_SHA256 = {
    "/api/firstrun": "2c3f693c0bfccfacd910d66e24de284c5a2d9cc0642922da6f924e42c268bd08",
    "/api/firstrun?level=1": "e5fbd7188ddc105b3c846706482dbf6415566759ab143fdd815ccc1aac5b3d1f",
    "/api/firstrun?level=5": "e3546fa25b69c776bdb1f2d951cc7f3d71af22a527e0c60de13c3b8e07210050",
}


@pytest.mark.parametrize("path", sorted(HAPPY_PATH_SHA256))
def test_the_happy_path_is_byte_identical(path):
    body = client.get(path).content
    assert hashlib.sha256(body).hexdigest() == HAPPY_PATH_SHA256[path]


def test_the_default_scenario_is_the_happy_path():
    plain = client.get("/api/firstrun").content
    named = client.get("/api/firstrun?scenario=first-run").content
    assert plain == named
    assert b"failedRegions" not in plain and b"vsanNodes" not in plain
    assert all(s.failed_regions is None for s in simulate())


def test_the_scenario_is_served_on_the_same_route():
    r = client.get(f"/api/firstrun?scenario={SCENARIO_ID}")
    assert r.status_code == 200
    trace = r.json()["trace"]
    assert [s["phase"] for s in trace] == [s.phase for s in simulate_node_add()]
    refused = next(s for s in trace if s["phase"] == "refused")
    assert refused["failedRegions"] and refused["mismatchedNodesInVsan"] == 0
    regions = client.get(f"/api/anatomy?scenario={SCENARIO_ID}").json()["regions"]
    assert any(reg["id"] == f"storage-{NEW_NODE}" for reg in regions)


def test_unknown_scenarios_are_a_404():
    assert client.get("/api/firstrun?scenario=nope").status_code == 404
    assert client.get("/api/anatomy?scenario=nope").status_code == 404


def test_scenarios_are_listed_with_sources():
    listed = client.get("/api/scenarios").json()
    assert [s["id"] for s in listed] == ["first-run", SCENARIO_ID]
    failure = listed[1]
    assert failure["kind"] == "failure"
    assert failure["phases"] == PHASE_ORDER
    assert len(failure["sources"]) >= 3
    assert all(src["url"].startswith("https://") for src in failure["sources"])
    assert {s.id for s in SCENARIOS} == set(ANATOMIES)


def test_the_scenario_prose_is_leveled():
    def prose(level):
        r = client.get(f"/api/firstrun?scenario={SCENARIO_ID}&level={level}")
        return [s["description"] for s in r.json()["trace"]]

    novice, standard, expert = prose(1), prose(3), prose(5)
    for n, s, e in zip(novice, standard, expert):
        assert n != s != e
        assert len(n) > len(e), "the scale is inverted"
