"""Geometry/data invariants for the IR7000 loop floorplan."""

from typing import get_args

from app.anatomy import ANATOMY
from app.models import RegionKind

EXPECTED_KINDS = set(get_args(RegionKind))
BAYS = ["b1", "b2", "b3", "b4"]


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


def test_four_bay_symmetry():
    """The four IT bays are identical same-kind, same-size heat sources —
    the loop treats the payload as uniform resistance."""
    by_id = {r.id: r for r in ANATOMY.regions}
    b1 = by_id.get("coldplate-b1")
    assert b1 is not None, "expected coldplate-b1"
    for b in BAYS[1:]:
        twin = by_id.get(f"coldplate-{b}")
        assert twin is not None, f"missing bay {b}"
        assert twin.kind == b1.kind
        assert twin.w == b1.w and twin.h == b1.h


def test_loop_topology_counts():
    # Exactly one CDU, one rear door, one facility connection, one sensor
    # block; a supply/return manifold pair.
    kinds = {}
    for r in ANATOMY.regions:
        kinds.setdefault(r.kind, []).append(r.id)
    assert len(kinds["cdu"]) == 1
    assert len(kinds["airdoor"]) == 1
    assert len(kinds["facility"]) == 1
    assert len(kinds["sensor"]) == 1
    assert sorted(kinds["manifold"]) == ["manifold-return", "manifold-supply"]
    assert len(kinds["coldplate"]) == 4
    assert len(kinds["power"]) == 1


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
