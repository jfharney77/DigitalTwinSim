"""Geometry/data invariants for the XE9712 rack floorplan."""

from typing import get_args

from app.anatomy import ANATOMY
from app.models import RegionKind

EXPECTED_KINDS = set(get_args(RegionKind))
TRAYS = ["t1", "t2", "t3", "t4"]
PER_TRAY_KINDS = {"gpu", "compute", "network"}


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


def test_four_tray_symmetry():
    """Every per-tray region has a same-kind, same-size counterpart on all
    four drawn trays — an XE9712 is built from identical compute trays."""
    by_id = {r.id: r for r in ANATOMY.regions}
    t1_regions = [r for r in ANATOMY.regions if r.id.endswith("-t1")]
    assert t1_regions, "expected per-tray '-t1' regions"
    for a in t1_regions:
        base = a.id[:-3]  # strip "-t1"
        for t in TRAYS[1:]:
            twin_id = f"{base}-{t}"
            assert twin_id in by_id, f"missing {t} twin for {a.id}"
            twin = by_id[twin_id]
            assert twin.kind == a.kind
            assert twin.w == a.w and twin.h == a.h


def test_expected_tray_and_shared_counts():
    # One region of each per-tray kind on every drawn tray.
    for t in TRAYS:
        tray_kinds = {r.kind for r in ANATOMY.regions if r.id.endswith(f"-{t}")}
        assert PER_TRAY_KINDS <= tray_kinds, f"tray {t} missing kinds"
    # Exactly two NVLink switch blocks (stylized stand-ins for 9 trays).
    nvswitch = [r for r in ANATOMY.regions if r.kind == "nvswitch"]
    assert len(nvswitch) == 2
    # Two power shelves feeding the busbar, and both halves of the liquid
    # loop — the CDU and the manifolds.
    assert sum(1 for r in ANATOMY.regions if r.kind == "power") == 2
    cooling_ids = {r.id for r in ANATOMY.regions if r.kind == "cooling"}
    assert cooling_ids == {"cdu", "manifold"}
    # One management block for the whole rack.
    assert sum(1 for r in ANATOMY.regions if r.kind == "management") == 1


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
