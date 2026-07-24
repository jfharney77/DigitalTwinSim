"""Geometry/data invariants for the Pro Max Plus inference-path map."""

from typing import get_args

from app.anatomy import ANATOMY
from app.models import RegionKind

EXPECTED_KINDS = set(get_args(RegionKind))

HOST_SIDE = {"host", "memory", "storage"}
CARD_SIDE = {"npu", "aimemory"}


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


def test_the_boundary_is_drawn_and_the_sides_are_separate():
    """The geometry carries the lesson, so it is pinned: every host-side
    region lies strictly left of the PCIe strip and every card-side region
    strictly right of it. Weights cross that line once, during load, and
    never again — which is the whole subject of this twin."""
    by_kind = _by_kind()
    link = by_kind["link"]
    assert len(link) == 1, "exactly one boundary, or it is not a boundary"
    strip = link[0]
    for kind in HOST_SIDE:
        for r in by_kind[kind]:
            assert r.x + r.w <= strip.x, f"{r.id} is not strictly host-side"
    for kind in CARD_SIDE:
        for r in by_kind[kind]:
            assert r.x >= strip.x + strip.w, f"{r.id} is not strictly card-side"


def test_ai_memory_spans_both_npus():
    """The 64 GB is one pool serving the whole card, not per-NPU — so it is
    drawn spanning both, and drawn large, because capacity is what decides
    which models the machine can run at all."""
    by_kind = _by_kind()
    mem = by_kind["aimemory"]
    assert len(mem) == 1, "one shared pool of AI memory"
    pool = mem[0]
    npus = by_kind["npu"]
    assert pool.x <= min(n.x for n in npus)
    assert pool.x + pool.w >= max(n.x + n.w for n in npus)


def test_ai_memory_is_the_biggest_block_on_the_card():
    """Emphasis is part of the argument: the capacity, not the TOPS, is why
    a 109-billion-parameter model runs here."""
    by_kind = _by_kind()
    pool = by_kind["aimemory"][0]
    for n in by_kind["npu"]:
        assert pool.w * pool.h > n.w * n.h


def test_two_npus_drawn_identically():
    by_kind = _by_kind()
    npus = by_kind["npu"]
    assert len(npus) == 2, "the card carries two AI-100 NPUs"
    a, b = npus
    assert a.w == b.w and a.h == b.h


def test_region_counts():
    by_kind = _by_kind()
    for kind in ("host", "memory", "storage", "link", "aimemory",
                 "thermal", "power", "runtime"):
        assert len(by_kind[kind]) == 1, f"expected exactly one {kind} region"


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
