"""C4 — a gray failure in the fabric becomes lost tokens in the factory."""

from __future__ import annotations

from compose import Chain, Link, assert_seams, presets, run
from compose import constants as K
from compose.couplings import c4_fabric_gray_to_factory as c4


def test_gray_failure_is_green_in_the_fabric_and_red_in_the_tokens():
    trace = run(presets.chain("gray-fabric"))
    assert_seams(trace)
    ratio_seam, green_seam = trace.seams[0], trace.seams[1]
    assert abs(ratio_seam.lhs - ratio_seam.rhs) <= 0.005 * ratio_seam.rhs
    assert ratio_seam.rhs < 0.9, "the gray link must actually cost something"
    assert green_seam.lhs == green_seam.rhs > 0, "every gray tick read all-green"
    fabric = trace.stages[0].trace
    gray = [row for row in fabric if row["goodputPenaltyPct"] > 0]
    assert gray and all(row["statusAllGreen"] for row in gray)


def test_the_scale_is_the_step_time_model():
    f = K.value("comm_fraction")
    assert K.CONSTANTS["comm_fraction"].estimated, "and it says so"
    assert abs(c4.tokens_scale(20.0, 10.0) - 1.0 / ((1 - f) + f * 2.0)) < 1e-12
    assert c4.tokens_scale(10.0, 10.0) == 1.0


def test_clearing_the_gray_link_restores_the_tokens():
    trace = run(presets.chain("gray-fabric"))
    regimes = trace.stages[1].injected_config["regimes"]
    assert [r["gray"] for r in regimes] == [False, True, False]
    assert regimes[0]["tokensScale"] == regimes[2]["tokensScale"] == 1.0
    last = trace.timeline[-1].values
    assert abs(last["PhysicsAIFactory.tokens_ratio"] - 1.0) < 1e-6
    assert last["PhysicsAIFactory.tokens_total_b"] < last["healthy.tokens_total_b"], \
        "the tokens lost in the gray weeks stay lost"


def test_splice_preserves_cumulative_counters():
    trace = run(presets.chain("gray-fabric"))
    rows = trace.stages[1].trace
    assert [row["tH"] for row in rows] == list(range(len(rows)))
    for prev, row in zip(rows, rows[1:]):
        if row["failuresCum"] == prev["failuresCum"]:
            assert row["tokensTotalB"] >= prev["tokensTotalB"] - 1e-9, row["tH"]
        assert row["costUsdM"] >= prev["costUsdM"] - 1e-9
    assert trace.seams[2].holds
    # A healthy fabric splices to exactly the unspliced run.
    healthy = Chain(id="t-c4-healthy",
                    scenarios={"PhysicsFabric": presets.HEALTHY_FABRIC, "PhysicsAIFactory": presets.FACTORY},
                    links=(Link("c4", "PhysicsFabric", "PhysicsAIFactory"),))
    h = run(healthy)
    assert h.timeline[-1].values["PhysicsAIFactory.tokens_total_b"] == \
        h.timeline[-1].values["healthy.tokens_total_b"]
