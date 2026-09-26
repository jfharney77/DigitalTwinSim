from __future__ import annotations

import pytest

from compose import assert_seams, presets, run


@pytest.mark.parametrize("chain_id", sorted(presets.CHAINS))
def test_every_preset_chain_is_deterministic_and_its_seams_hold(chain_id):
    first = run(presets.chain(chain_id))
    second = run(presets.chain(chain_id))
    assert first.model_dump_json() == second.model_dump_json()
    assert_seams(first)
    assert first.illustrative is True
    assert first.timeline and first.charts
    keys = set(first.timeline[0].values)
    for chart in first.charts:
        for s in chart.series:
            assert s.key in keys, (chain_id, s.key)
    for seam in first.seams:
        for key in (seam.lhs_key, seam.rhs_key):
            assert key is None or key in keys, (chain_id, key)
    assert any(chart.seam for chart in first.charts), "the seam quantity is charted"


def test_estimated_constants_are_carried():
    trace = run(presets.chain("gray-fabric"))
    assert "compose.comm_fraction" in trace.estimated_constants
