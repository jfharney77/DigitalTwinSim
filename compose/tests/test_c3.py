"""C3 — Exascale delivered throughput becomes the GPUs' data feed."""

from __future__ import annotations

import copy

from compose import Chain, Link, assert_seams, presets, run


def _points(trace):
    return next(s for s in trace.stages if s.id == "PhysicsCompute").injected_config["operatingPoints"]


def test_the_two_idle_gauges_are_the_same_number():
    trace = run(presets.chain("storage-feed"))
    assert_seams(trace)
    points = _points(trace)
    assert len(points) >= 3, "baseline, checkpoint burst, and the surge"
    assert len(points) < 12 < len(trace.stages[0].trace), "72 hours reduce to a handful of runs"
    for p in points:
        assert abs((100.0 - p["storageIdlePct"]) - p["computeFedPct"]) <= 1.0, p


def test_a_demand_surge_in_storage_shows_up_as_wasted_gpu_hours():
    calm = copy.deepcopy(presets.chain("storage-feed"))
    calm_scn = copy.deepcopy(presets.EXASCALE)
    calm_scn["events"] = []
    calm_scn["workload"]["iopsDemandK"] = 2000
    calm_chain = Chain(id="t-c3-calm",
                       scenarios={"PhysicsStorage": calm_scn, "PhysicsCompute": presets.XE9712_FULL},
                       links=(Link("c3", "PhysicsStorage", "PhysicsCompute", {"window_s": 600}),))
    surged = _points(run(presets.chain("storage-feed")))
    quiet = _points(run(calm_chain))
    assert max(p["gpuHoursWasted"] for p in surged) > 10 * max(p["gpuHoursWasted"] for p in quiet)
    worst = min(surged, key=lambda p: p["feedPct"])
    expected = (1 - worst["feedPct"] / 100) * 72 * 600 / 3600
    assert abs(worst["gpuHoursWasted"] - expected) <= 0.02 * expected + 0.002
    assert calm is not None


def test_starved_gpus_still_burn_power():
    trace = run(presets.chain("storage-feed"))
    seam = next(s for s in trace.seams if "still burn power" in s.identity)
    assert seam.holds
    power_ratio, token_ratio = seam.lhs, seam.rhs
    assert token_ratio < power_ratio < 1.0, "power falls, but by less than tokens fall"
