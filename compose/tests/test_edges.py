"""Adversarial edges of the C1/C2 closed loop: what the coupling refuses to
express, and whether the fixed point settles across the whole valid input range
rather than only on the preset day.

Each test here was written against a defect that was real when it was written.
"""

from __future__ import annotations

import pytest

from compose import Chain, Link, presets
from compose import constants as K
from compose.couplings import c1_compute_heat_to_cdu as c1
from compose.loader import load_engine
from compose.loop import cdu_constants
from compose.runner import run_engine
from compose.seam import assert_seams
from compose.chain import run

LOOP_LINKS = (Link("c1", "PhysicsCompute", "PhysicsCDU", {"racks": 2}),
              Link("c2", "PhysicsCDU", "PhysicsCompute"))


def _cdu_consts() -> dict:
    return cdu_constants(load_engine("PhysicsCDU"))


def _loop(cdu: dict, compute: dict | None = None, links=LOOP_LINKS, **kw) -> Chain:
    return Chain(id="t-edge", closed=True, links=links,
                 scenarios={"PhysicsCompute": compute or presets.XE9712_RAMP,
                            "PhysicsCDU": cdu}, **kw)


# --- heat the target engine cannot express ----------------------------------

def test_more_rack_heat_than_a_cdu_can_carry_is_refused_not_clamped():
    """Four XE9712 racks peak above six 40 kW banks. Clamping the utilization
    dial at 100% drops the excess silently: the CDU then runs flat out on a load
    that is not the rack's, its cap is the same on every pass, and the closed
    loop iterates against a constant it cannot move — the residual sticks and
    the loop reports a fixed point that does not exist. Refuse instead, the way
    C5 refuses a server too big for a rack slot."""
    consts = _cdu_consts()
    compute = run_engine("PhysicsCompute", presets.XE9712_FULL)
    with pytest.raises(c1.OversizedPayload) as refusal:
        c1.adapt(compute.trace, {}, cdu=consts, racks=4)
    assert "kW" in str(refusal.value)
    c1.adapt(compute.trace, {}, cdu=consts, racks=2)   # two racks of it still fit


def test_the_closed_loop_refuses_the_same_payload_the_adapter_refuses():
    chain = _loop({}, links=(Link("c1", "PhysicsCompute", "PhysicsCDU", {"racks": 4}),
                             Link("c2", "PhysicsCDU", "PhysicsCompute")))
    with pytest.raises(c1.OversizedPayload):
        run(chain)


def test_heat_below_the_idle_floor_is_excluded_from_the_seam_and_the_residual():
    """Below ``banks × 40 kW × idle`` the bank formula cannot express the heat
    either. Those ticks are excluded from the seam, so the loop's residual has
    to exclude them too — measuring agreement on a tick the coupling never
    claimed to carry gives the residual a floor no iteration can clear."""
    consts = _cdu_consts()
    trace = [{"liquid_watts": w} for w in (1_000.0, 100_000.0, 200_000.0)]
    ok = c1.expressible(trace, consts, racks=1)
    assert ok == [False, True, True], ok


# --- the fixed point, over the valid input range ----------------------------

@pytest.mark.parametrize("facility_c", [17, 29, 38, 45])
def test_the_loop_settles_everywhere_in_the_cdu_facility_water_range(facility_c):
    """``PhysicsCDU`` accepts facility water from 8 to 45 °C. The map contracts
    across that whole range, just more slowly as the water warms — 25 passes at
    45 °C against the 12 the cap once allowed. A cap that stops the solver short
    of a fixed point it would have reached is the solver's defect, not the
    day's, and it showed up as a broken C2 seam on an ordinary hot day."""
    trace = run(_loop({"environment": {"facilitySupplyC": facility_c}},
                      compute=presets.XE9712_FULL))
    assert trace.converged, (
        f"{trace.iterations} iteration(s) at {facility_c} °C, "
        f"residuals {trace.residual_history}")
    assert trace.residual_history[-1] < K.value("fixed_point_tol")
    assert trace.iterations <= K.value("fixed_point_max_iter")
    assert_seams(trace)


def test_the_iteration_cap_leaves_headroom_over_the_worst_valid_day():
    """The cap is not a number to tune per preset: it has to cover the hottest
    day the target engine accepts, with room above it."""
    worst = run(_loop({"environment": {"facilitySupplyC": 45}},
                      compute=presets.XE9712_FULL))
    assert worst.converged
    assert K.value("fixed_point_max_iter") >= worst.iterations + 4, (
        f"{worst.iterations} iteration(s) needed against a cap of "
        f"{K.value('fixed_point_max_iter')}")


# --- a refusal is an answer, not a crash ------------------------------------

def test_the_api_answers_a_refused_chain_with_a_sentence_not_a_500():
    """``POST /api/run/custom`` takes an arbitrary chain, so a scope refusal is
    reachable from the page. It has to arrive as a 422 carrying the adapter's
    sentence; a 500 tells the reader nothing about what the seam cannot do."""
    import importlib.util
    import pathlib
    import sys

    pytest.importorskip("fastapi")
    testclient = pytest.importorskip("starlette.testclient")
    path = pathlib.Path(__file__).resolve().parent.parent / "backend" / "app" / "main.py"
    name = "_compose_server_main_edges"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        client = testclient.TestClient(module.app)
        body = next(c for c in client.get("/api/chains").json()
                    if c["id"] == "heat-to-cdu")["defaultChain"]
        body["links"][0]["params"]["racks"] = 4
        answer = client.post("/api/run/custom", json=body)
        assert answer.status_code == 422, answer.status_code
        assert "kW" in answer.json()["detail"]
    finally:
        sys.modules.pop(name, None)
