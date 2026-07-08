"""Geometry/data invariants for the iDRAC9 subsystem block diagram."""

from app.anatomy import ANATOMY
from app.models import RegionKind
from typing import get_args

EXPECTED_KINDS = set(get_args(RegionKind))


def test_region_ids_unique():
    ids = [r.id for r in ANATOMY.regions]
    assert len(ids) == len(set(ids))


def test_regions_within_bounds():
    for r in ANATOMY.regions:
        assert 0 <= r.x and r.x + r.w <= ANATOMY.width, r.id
        assert 0 <= r.y and r.y + r.h <= ANATOMY.height, r.id


def test_regions_positive_size():
    for r in ANATOMY.regions:
        assert r.w > 0 and r.h > 0, r.id


def test_regions_do_not_overlap():
    rs = ANATOMY.regions
    for i, a in enumerate(rs):
        for b in rs[i + 1:]:
            disjoint = (
                a.x + a.w <= b.x
                or b.x + b.w <= a.x
                or a.y + a.h <= b.y
                or b.y + b.h <= a.y
            )
            assert disjoint, f"{a.id} overlaps {b.id}"


def test_every_region_described():
    for r in ANATOMY.regions:
        assert r.description.strip(), r.id


def test_three_sideband_buses():
    sideband = [r for r in ANATOMY.regions if r.kind == "sideband"]
    assert len(sideband) == 3  # I2C/PMBus, eSPI/PECI, NC-SI


def test_exactly_one_soc():
    socs = [r for r in ANATOMY.regions if r.kind == "soc"]
    assert len(socs) == 1


def test_kinds_are_expected_set():
    kinds = {r.kind for r in ANATOMY.regions}
    assert kinds <= EXPECTED_KINDS
    # The diagram should exercise every kind the model defines.
    assert kinds == EXPECTED_KINDS


def test_stats_and_sources_nonempty():
    assert ANATOMY.stats
    assert ANATOMY.sources
    assert ANATOMY.overview.strip()


def test_photo_credit_present():
    assert ANATOMY.photo is not None
    assert ANATOMY.photo.credit.strip()
    for r in ANATOMY.regions:
        if r.photo is not None:
            assert r.photo.credit.strip(), r.id


def test_camel_case_wire_format():
    # Spot-check the alias generator end to end.
    data = ANATOMY.model_dump(by_alias=True)
    assert "formFactor" in data
    assert "regions" in data and "description" in data["regions"][0]
