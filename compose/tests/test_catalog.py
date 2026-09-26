from __future__ import annotations

import json
import pathlib

from compose import catalog, leveling, presets
from compose.constants import CONSTANTS

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def test_eight_couplings_each_with_an_identity_and_a_test_that_exists():
    assert [c.id for c in catalog.COUPLINGS] == [f"c{i}" for i in range(1, 9)]
    for c in catalog.COUPLINGS:
        assert c.identity and c.tolerance
        path, name = c.test.split("::")
        assert name in (ROOT / path).read_text(encoding="utf-8"), c.test


def test_every_chain_has_prose_and_real_ports():
    ports = json.loads((ROOT / "ports.json").read_text())["twins"]
    assert {c.id for c in catalog.CHAIN_INFOS} == set(presets.CHAINS)
    for info in catalog.CHAIN_INFOS:
        assert info.blurb and info.watch
        for engine in info.engines:
            assert ports[engine.component]["frontend"] == engine.frontend_port, engine.component


def test_prose_is_leveled_and_the_scale_is_not_inverted():
    for item in catalog.COUPLINGS:
        novice = leveling.leveled(item, 1).blurb
        standard = leveling.leveled(item, 3).blurb
        expert = leveling.leveled(item, 5).blurb
        assert standard == item.blurb, "level 3 is the text as written"
        assert len({novice, standard, expert}) == 3
        assert len(novice) > len(expert), item.id
    cov = leveling.coverage()
    assert cov[1] > 0 and cov[5] > 0


def test_constants_carry_units_sources_and_honest_flags():
    for name, c in CONSTANTS.items():
        assert c.unit and c.source and c.blurb, name
    assert CONSTANTS["comm_fraction"].estimated
    assert CONSTANTS["heatwave_days_per_year"].estimated
    assert not CONSTANTS["fixed_point_max_iter"].estimated
