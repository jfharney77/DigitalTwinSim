"""Geometry/data invariants for the Cyber Detect detection map."""

from typing import get_args

from app.anatomy import ANATOMY, TOTAL_SNAPSHOTS
from app.models import RegionKind

EXPECTED_KINDS = set(get_args(RegionKind))


def _by_kind():
    out: dict[str, list] = {}
    for r in ANATOMY.regions:
        out.setdefault(r.kind, []).append(r)
    return out


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


def test_the_middle_band_is_a_timeline():
    """Unlike every other twin's map, this one's middle band is an axis of
    *time*: snapshots run left to right, oldest to newest, uniformly sized
    and on one row. The product's entire output is a point on that line, so
    the ordering is part of the lesson and is pinned here."""
    snaps = sorted(_by_kind()["snapshot"], key=lambda r: r.id)
    assert len(snaps) == TOTAL_SNAPSHOTS
    xs = [r.x for r in snaps]
    assert xs == sorted(xs), "snapshots are not in chronological order"
    assert all(a < b for a, b in zip(xs, xs[1:])), "snapshots share a position"
    first = snaps[0]
    for s in snaps[1:]:
        assert s.w == first.w and s.h == first.h, (
            f"{s.id} is drawn differently — every copy looks equally "
            f"trustworthy from outside, which is the problem"
        )
        assert s.y == first.y, f"{s.id} is off the timeline"


def test_evidence_sits_above_conclusion():
    """Content inspection and the classifier are drawn above the verdict and
    the recovery, because a verdict may never precede the evidence for
    it — the engine asserts the same thing in time."""
    by_kind = _by_kind()
    evidence_bottom = max(
        r.y + r.h for k in ("inspect", "classifier", "models") for r in by_kind[k]
    )
    conclusion_top = min(
        r.y for k in ("verdict", "recovery") for r in by_kind[k]
    )
    assert evidence_bottom <= conclusion_top


def test_the_analysis_reads_the_timeline_from_below():
    """The inspection band sits beneath the snapshots it opens: the arrow of
    the diagram is downward, from copies to conclusions."""
    by_kind = _by_kind()
    snaps_bottom = max(r.y + r.h for r in by_kind["snapshot"])
    inspect_top = min(r.y for r in by_kind["inspect"])
    assert snaps_bottom <= inspect_top


def test_the_array_is_the_source_and_sits_on_top():
    by_kind = _by_kind()
    array = by_kind["array"][0]
    snaps_top = min(r.y for r in by_kind["snapshot"])
    assert array.y + array.h <= snaps_top


def test_region_counts():
    by_kind = _by_kind()
    for kind in ("array", "inspect", "classifier", "models", "verdict", "recovery"):
        assert len(by_kind[kind]) == 1, f"expected exactly one {kind} region"
    assert len(by_kind["snapshot"]) == TOTAL_SNAPSHOTS


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
