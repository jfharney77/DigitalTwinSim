"""Geometry/data invariants for the laptop interior floorplans, parametrized
over every anatomy in the registry (style of the GPU/R760 apps)."""

from __future__ import annotations

import pytest

from app.anatomy import ANATOMIES

# The region vocabulary PowerState.activeRegions speaks — required by the
# API contract in every anatomy.
REQUIRED_REGION_IDS = {
    "dc-in", "ec", "charger", "battery", "cpu", "gpu", "vram", "dimm",
    "fan-left", "fan-right", "heatpipes", "ssd", "io-left", "io-right", "wlan",
}


@pytest.fixture(params=list(ANATOMIES.values()), ids=lambda a: a.id)
def anatomy(request):
    return request.param


def test_region_ids_unique(anatomy):
    ids = [r.id for r in anatomy.regions]
    assert len(ids) == len(set(ids))


def test_required_region_ids_present(anatomy):
    ids = {r.id for r in anatomy.regions}
    missing = REQUIRED_REGION_IDS - ids
    assert not missing, f"{anatomy.id}: missing required regions {missing}"


def test_regions_within_bounds(anatomy):
    for r in anatomy.regions:
        assert 0 <= r.x and r.x + r.w <= anatomy.width, r.id
        assert 0 <= r.y and r.y + r.h <= anatomy.height, r.id


def test_regions_positive_size(anatomy):
    for r in anatomy.regions:
        assert r.w > 0 and r.h > 0, r.id


def test_regions_do_not_overlap(anatomy):
    rs = anatomy.regions
    for i, a in enumerate(rs):
        for b in rs[i + 1:]:
            disjoint = (
                a.x + a.w <= b.x
                or b.x + b.w <= a.x
                or a.y + a.h <= b.y
                or b.y + b.h <= a.y
            )
            assert disjoint, f"{anatomy.id}: {a.id} overlaps {b.id}"


def test_every_region_described(anatomy):
    for r in anatomy.regions:
        assert r.description.strip(), r.id
        assert r.label.strip(), r.id


def test_canvas_is_contract_size(anatomy):
    assert anatomy.width == 100
    assert anatomy.height == 62


def test_metadata_nonempty(anatomy):
    assert anatomy.stats
    assert anatomy.sources
    assert anatomy.overview.strip()
    assert anatomy.name.strip() and anatomy.vendor.strip()


def test_photo_credit_present(anatomy):
    assert anatomy.photo is not None
    assert anatomy.photo.credit.strip()
    assert anatomy.photo.url == "/alienware-interior.jpg"
    for r in anatomy.regions:
        if r.photo is not None:
            assert r.photo.credit.strip(), r.id


def test_camel_case_wire_format(anatomy):
    # Spot-check the alias generator end to end.
    data = anatomy.model_dump(by_alias=True)
    assert "regions" in data and "description" in data["regions"][0]
    assert "overview" in data
