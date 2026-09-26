"""The same couplings over recorded JSON: no engine import on the source side."""

from __future__ import annotations

from compose import json_adapter, presets, run
from compose.runner import run_engine


def _response(run_) -> dict:
    return {"trace": [s.model_dump(by_alias=True) for s in run_.trace],
            "summary": run_.summary.model_dump(by_alias=True)}


def _events(scenario: dict) -> list[dict]:
    return [{k: v for k, v in e.items() if v is not None}
            for e in scenario.get("events", []) or []]


def test_c1_over_json_matches_the_live_path():
    live = run(presets.chain("heat-to-cdu"))
    recorded = _response(run_engine("PhysicsCompute", presets.XE9712_RAMP))
    scenario = json_adapter.adapt("c1", recorded, {}, {"racks": 2})
    # The live stage carries the scenario as the target engine validated it —
    # defaults filled in, absent event fields spelled out as null. The JSON path
    # produces the body you would POST, so compare what the adapter decided.
    assert _events(scenario) == _events(live.stages[1].scenario)
    assert scenario["config"].items() <= live.stages[1].scenario["config"].items()
    target = _response(run_engine("PhysicsCDU", scenario))
    seams = json_adapter.check("c1", recorded, target, {"racks": 2})
    assert all(s.holds for s in seams)
    assert seams[0].abs_error == live.seams[0].abs_error


def test_c5_over_json():
    recorded = [("R760", _response(run_engine("DellPowerEdgeR760Thermal", presets.R760_BUSY)))]
    scenario = json_adapter.adapt("c5", recorded, {})
    target = _response(run_engine("PhysicsRackPower", scenario))
    assert all(s.holds for s in json_adapter.check("c5", recorded, target))
