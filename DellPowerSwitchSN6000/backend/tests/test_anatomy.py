"""Geometry/data invariants for the SN6000 leaf/spine fabric map."""

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


def test_tier_symmetry():
    """Every spine is identical to every other spine, and likewise leaves and
    endpoints — a fabric tier is one building block repeated, which is what
    makes path lengths uniform."""
    by_kind = {}
    for r in ANATOMY.regions:
        by_kind.setdefault(r.kind, []).append(r)
    for kind in ("spine", "leaf", "endpoint"):
        tier = by_kind[kind]
        first = tier[0]
        for r in tier[1:]:
            assert r.w == first.w and r.h == first.h, (
                f"{kind} tier not uniform: {r.id}"
            )


def test_tiers_are_vertically_ordered():
    """Spines above leaves above endpoints — the diagram encodes the two-hop
    path, so the geometry is part of the lesson."""
    by_kind = {}
    for r in ANATOMY.regions:
        by_kind.setdefault(r.kind, []).append(r)
    spine_bottom = max(r.y + r.h for r in by_kind["spine"])
    leaf_top = min(r.y for r in by_kind["leaf"])
    leaf_bottom = max(r.y + r.h for r in by_kind["leaf"])
    endpoint_top = min(r.y for r in by_kind["endpoint"])
    assert spine_bottom <= leaf_top, "spines must sit above leaves"
    assert leaf_bottom <= endpoint_top, "leaves must sit above endpoints"


def test_every_leaf_has_an_endpoint_rack():
    """Each leaf is top-of-rack for one GPU rack in this drawing, so the two
    tiers come in matched counts."""
    leaves = [r for r in ANATOMY.regions if r.kind == "leaf"]
    endpoints = [r for r in ANATOMY.regions if r.kind == "endpoint"]
    assert len(leaves) == len(endpoints) == 4


def test_topology_counts():
    kinds = {}
    for r in ANATOMY.regions:
        kinds.setdefault(r.kind, []).append(r.id)
    assert len(kinds["spine"]) == 2, "two spines — multiple equal-cost paths"
    assert len(kinds["leaf"]) == 4
    assert len(kinds["endpoint"]) == 4
    assert len(kinds["optics"]) == 1
    assert len(kinds["telemetry"]) == 1
    assert len(kinds["cooling"]) == 1
    assert len(kinds["management"]) == 1


def test_kinds_are_expected_set():
    kinds = {r.kind for r in ANATOMY.regions}
    assert kinds <= EXPECTED_KINDS
    # The map should exercise every kind the model defines.
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
