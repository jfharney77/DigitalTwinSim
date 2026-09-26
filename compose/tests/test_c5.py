"""C5 — server wall watts load the rack's phases."""

from __future__ import annotations

import pytest

from compose import Chain, Link, assert_seams, presets, run
from compose.couplings.c5_wall_watts_to_rackpower import OversizedServer


def _chain(servers: list[dict]) -> Chain:
    return Chain(id="t-c5", scenarios={"PhysicsRackPower": {"config": {"breakerAmps": 32}}},
                 links=(Link("c5", "servers", "PhysicsRackPower", {"servers": servers}),))


def test_wall_watts_are_conserved_across_the_seam():
    trace = run(presets.chain("wall-watts"))
    assert_seams(trace)
    tick, energy = trace.seams
    assert tick.abs_error <= 10.0 * 3 + 0.3
    assert energy.abs_error / energy.lhs <= 0.002
    rack = trace.stages[-1]
    assert rack.scenario["config"]["loads"][3]["powerW"] == 0, "unused slots stay empty"


def test_a_fan_failure_upstream_moves_the_phase_meter():
    trace = run(presets.chain("wall-watts"))
    before = trace.timeline[190].values
    after = trace.timeline[-1].values
    assert after["servers.fan_power_w"] > before["servers.fan_power_w"]
    # R760 B (the one that lost a fan) sits on phase B; A and C carry its healthy twins.
    rise_b = after["PhysicsRackPower.phase_b_amps"] - before["PhysicsRackPower.phase_b_amps"]
    rise_a = after["PhysicsRackPower.phase_a_amps"] - before["PhysicsRackPower.phase_a_amps"]
    assert rise_b > 0 and rise_b > rise_a


def test_a_server_that_fits_a_slot_stays_one_slot():
    # 4 PCIe GPUs at 300 W peaks under 1.7 kW, inside the 2000 W a slot carries,
    # so there is nothing to split: one server, one outlet.
    xe7745 = {"label": "XE7745", "component": "PhysicsCompute", "scenario": {
        "config": {"product": "xe7745", "pcieGpus": 4, "pcieGpuTdpW": 300},
        "workload": {"gpuPct": 80, "cpuPct": 40}, "durationS": 300}}
    trace = run(_chain([xe7745]))
    assert_seams(trace)
    rack = trace.stages[-1]
    assert rack.injected_config["slotsUsed"] == 1
    assert [l["label"] for l in rack.injected_config["loads"]] == ["XE7745"]


def test_a_gpu_server_is_split_one_slot_per_psu_feed():
    xe9680 = {"label": "XE9680", "component": "PhysicsCompute", "scenario": {
        "config": {"product": "xe9680"}, "workload": {"gpuPct": 100, "cpuPct": 60},
        "durationS": 300}}
    trace = run(_chain([xe9680]))
    assert_seams(trace)
    rack = trace.stages[-1]
    # ~11.7 kW over six PSU feeds is ~1.95 kW each — six slots, none over the cap.
    assert rack.injected_config["slotsUsed"] == 6
    assert all(l["label"].startswith("XE9680 PSU") for l in rack.injected_config["loads"])


def test_an_oversized_server_is_refused_not_clamped():
    # The same server on four surviving feeds is ~2.96 kW each, above what one
    # slot carries. The split has nowhere left to go, so the adapter refuses.
    xe9680 = {"label": "XE9680", "component": "PhysicsCompute", "scenario": {
        "config": {"product": "xe9680"}, "workload": {"gpuPct": 100, "cpuPct": 60},
        "durationS": 120,
        "events": [{"atS": 30, "action": "kill-psu"}, {"atS": 40, "action": "kill-psu"}]}}
    with pytest.raises(OversizedServer, match="Refused rather than clamped"):
        run(_chain([xe9680]))
    busbar = {"label": "NVL72", "component": "PhysicsCompute",
              "scenario": {"config": {"product": "xe9712"}, "durationS": 60}}
    with pytest.raises(OversizedServer, match="busbar"):
        run(_chain([busbar]))
