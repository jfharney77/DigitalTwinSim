"""Geometry/data invariants for the PowerMax node-pair floorplan."""

from typing import get_args

from app.anatomy import ANATOMY
from app.models import RegionKind

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


def test_node_ab_symmetry():
    """Every per-node region has a same-kind, same-size twin on the other node.

    Uses the '-a'/'-b' suffix rather than a substring so the shared
    'fabric-bus' region (no node suffix) is correctly excluded."""
    by_id = {r.id: r for r in ANATOMY.regions}
    a_regions = [r for r in ANATOMY.regions if r.id.endswith("-a")]
    assert a_regions, "expected per-node '-a' regions"
    for a in a_regions:
        twin_id = a.id[:-2] + "-b"
        assert twin_id in by_id, f"missing Node B twin for {a.id}"
        twin = by_id[twin_id]
        assert twin.kind == a.kind
        assert twin.w == a.w and twin.h == a.h


def test_exactly_one_dme_storage_region():
    storage = [r for r in ANATOMY.regions if r.kind == "storage"]
    assert len(storage) == 1


def test_kinds_are_expected_set():
    kinds = {r.kind for r in ANATOMY.regions}
    assert kinds <= EXPECTED_KINDS
    # The floorplan should exercise every kind the model defines.
    assert kinds == EXPECTED_KINDS


def test_photos_when_present_are_credited():
    photos = [ANATOMY.photo] + [r.photo for r in ANATOMY.regions]
    for p in photos:
        if p is not None:
            assert p.url.strip()
            assert p.credit.strip()


def test_stats_and_sources_nonempty():
    assert ANATOMY.stats
    assert ANATOMY.sources
    assert ANATOMY.overview.strip()


def test_camel_case_wire_format():
    # Spot-check the alias generator end to end.
    data = ANATOMY.model_dump(by_alias=True)
    assert "formFactor" in data
    assert "regions" in data and "description" in data["regions"][0]
