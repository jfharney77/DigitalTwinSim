"""Geometry/data invariants for the Fort Zero zero-trust map."""

from typing import get_args

from app.anatomy import ANATOMY
from app.models import RegionKind

EXPECTED_KINDS = set(get_args(RegionKind))

PILLAR_KINDS = {
    "identity", "device", "network", "workload",
    "data", "visibility", "automation",
}


def _by_kind():
    out: dict[str, list] = {}
    for r in ANATOMY.regions:
        out.setdefault(r.kind, []).append(r)
    return out


def _centre(r):
    return (r.x + r.w / 2, r.y + r.h / 2)


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


def test_nothing_is_drawn_as_a_perimeter():
    """THE geometric invariant. Every other map in this repo carries its
    lesson in a boundary — a PCIe strip, an air gap, a band with nothing
    above it. This one carries its lesson in the absence of one. No region
    may be large enough to enclose the others, because a shape like that
    would be a perimeter, and the architecture's entire claim is that there
    is no inside."""
    for r in ANATOMY.regions:
        assert r.w <= ANATOMY.width * 0.4, (
            f"{r.id} is wide enough to act as a perimeter"
        )
        assert r.h <= ANATOMY.height * 0.4, (
            f"{r.id} is tall enough to act as a perimeter"
        )


def test_the_policy_engine_is_the_centre():
    """There is a middle even though there is no inside: the decision point
    is consulted on every request, so it sits at the centre of the map and
    nothing else is closer to it."""
    by_kind = _by_kind()
    policy = by_kind["policy"]
    assert len(policy) == 1, "one decision point"
    map_centre = (ANATOMY.width / 2, ANATOMY.height / 2)

    def dist(r):
        cx, cy = _centre(r)
        return ((cx - map_centre[0]) ** 2 + (cy - map_centre[1]) ** 2) ** 0.5

    policy_dist = dist(policy[0])
    for r in ANATOMY.regions:
        if r.kind == "policy":
            continue
        assert policy_dist < dist(r), (
            f"{r.id} sits closer to the centre than the policy engine"
        )


def test_the_pillars_are_co_equal():
    """The DoD model treats its seven pillars as co-equal, and a diagram
    that drew one larger would be arguing with it. All seven are identical
    in size, and the policy engine matches them — it decides using the
    pillars, it does not outrank them."""
    pillars = [r for r in ANATOMY.regions if r.kind in PILLAR_KINDS]
    assert len(pillars) == 7, "seven pillars, no more and no fewer"
    first = pillars[0]
    for p in pillars[1:]:
        assert p.w == first.w and p.h == first.h, f"{p.id} is drawn differently"
    policy = _by_kind()["policy"][0]
    assert policy.w == first.w and policy.h == first.h


def test_one_region_per_pillar_kind():
    by_kind = _by_kind()
    for kind in PILLAR_KINDS:
        assert len(by_kind[kind]) == 1, f"expected exactly one {kind} pillar"


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
