"""Geometry/data invariants for the VxRail cluster floorplan."""

from typing import get_args

from app.anatomy import ANATOMY
from app.models import RegionKind

EXPECTED_KINDS = set(get_args(RegionKind))
NODES = ["n1", "n2", "n3", "n4"]


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


def test_four_node_symmetry():
    """Every per-node region has a same-kind, same-size counterpart on all
    four nodes — a VxRail cluster is built from identical building blocks."""
    by_id = {r.id: r for r in ANATOMY.regions}
    n1_regions = [r for r in ANATOMY.regions if r.id.endswith("-n1")]
    assert n1_regions, "expected per-node '-n1' regions"
    for a in n1_regions:
        base = a.id[:-3]  # strip "-n1"
        for n in NODES[1:]:
            twin_id = f"{base}-{n}"
            assert twin_id in by_id, f"missing {n} twin for {a.id}"
            twin = by_id[twin_id]
            assert twin.kind == a.kind
            assert twin.w == a.w and twin.h == a.h


def test_expected_node_and_fabric_counts():
    # One region of each per-node kind on every node.
    per_node_kinds = [k for k in EXPECTED_KINDS if k != "fabric"]
    for n in NODES:
        node_kinds = {r.kind for r in ANATOMY.regions if r.id.endswith(f"-{n}")}
        assert set(per_node_kinds) <= node_kinds, f"node {n} missing kinds"
    # Exactly two fabric switches (the redundant top-of-rack pair).
    fabric = [r for r in ANATOMY.regions if r.kind == "fabric"]
    assert len(fabric) == 2


def test_kinds_are_expected_set():
    kinds = {r.kind for r in ANATOMY.regions}
    assert kinds <= EXPECTED_KINDS
    # The floorplan should exercise every kind the model defines.
    assert kinds == EXPECTED_KINDS


def test_photos_have_credit_when_present():
    photos = [ANATOMY.photo] + [r.photo for r in ANATOMY.regions]
    for p in photos:
        if p is not None:
            assert p.credit.strip(), "a photo must always carry a credit line"


def test_stats_and_sources_nonempty():
    assert ANATOMY.stats
    assert ANATOMY.sources
    assert ANATOMY.overview.strip()


def test_camel_case_wire_format():
    # Spot-check the alias generator end to end.
    data = ANATOMY.model_dump(by_alias=True)
    assert "formFactor" in data
    assert "regions" in data and "description" in data["regions"][0]
