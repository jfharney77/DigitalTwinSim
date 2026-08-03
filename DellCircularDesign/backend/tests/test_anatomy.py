"""Geometry/data invariants for the circular-design lifecycle map — most
importantly, that the loop actually closes and that the leak is drawn."""

from typing import get_args

from app.anatomy import ANATOMY
from app.models import RegionKind

EXPECTED_KINDS = set(get_args(RegionKind))


def _by_kind():
    out: dict[str, list] = {}
    for r in ANATOMY.regions:
        out.setdefault(r.kind, []).append(r)
    return out


def _by_id():
    return {r.id: r for r in ANATOMY.regions}


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


def test_flows_reference_real_regions():
    ids = set(_by_id())
    for r in ANATOMY.regions:
        for target in r.flows_to:
            assert target in ids, f"{r.id} flows to unknown region {target!r}"
            assert target != r.id, f"{r.id} flows to itself"


def test_the_loop_closes_geometrically():
    """The lesson, drawn. Following flows_to from recovery must reach both
    materials (the outer return, via reclaim) and deployment (the inner
    return, via refurbish) — the map is a loop, not a line. And every
    region except `loss` has at least one outgoing edge: nothing is an
    accidental terminus. Loss is the only permitted dead end, exists, and
    is drawn at nonzero size — a lifecycle map that hides the leak is
    marketing."""
    by_id = _by_id()

    # BFS from recovery along the directed edges.
    reachable: set[str] = set()
    frontier = ["recovery"]
    while frontier:
        current = frontier.pop()
        for target in by_id[current].flows_to:
            if target not in reachable:
                reachable.add(target)
                frontier.append(target)
    assert "materials" in reachable, (
        "recovery cannot reach materials — the outer return is broken"
    )
    assert "deployment" in reachable, (
        "recovery cannot reach deployment — the inner return is broken"
    )

    # No accidental terminus: only loss may have no outgoing edge.
    for r in ANATOMY.regions:
        if r.id == "loss":
            assert r.flows_to == [], (
                "loss has an outgoing edge — a leak that flows somewhere "
                "is not a leak"
            )
        else:
            assert r.flows_to, f"{r.id} is a terminus — the loop leaks silently"

    # The leak exists and is drawn, at real size.
    loss = by_id["loss"]
    assert loss.kind == "loss"
    assert loss.w > 0 and loss.h > 0, "the loss region must be drawn"


def test_the_loop_returns_to_its_own_beginning():
    """From materials, following the edges, you can get back to
    materials. That is what makes this the one map in the repo with no
    end."""
    by_id = _by_id()
    reachable: set[str] = set()
    frontier = list(by_id["materials"].flows_to)
    while frontier:
        current = frontier.pop()
        if current in reachable:
            continue
        reachable.add(current)
        frontier.extend(by_id[current].flows_to)
    assert "materials" in reachable, "the cycle does not return to materials"


def test_the_two_returns_run_at_different_radii():
    """Reuse and recycling are not the same thing, and the drawing must
    say so: refurbish (the inner return) sits strictly inside the outer
    ring that reclaim travels — closer to deployment than reclaim is."""
    by_id = _by_id()
    refurbish, reclaim, deployment = (
        by_id["refurbish"], by_id["reclaim"], by_id["deployment"],
    )

    def center(r):
        return (r.x + r.w / 2, r.y + r.h / 2)

    def dist2(a, b):
        (ax, ay), (bx, by) = center(a), center(b)
        return (ax - bx) ** 2 + (ay - by) ** 2

    assert dist2(refurbish, deployment) < dist2(reclaim, deployment), (
        "refurbish is not the inner return — reuse must be drawn as the "
        "shorter path back"
    )


def test_region_counts():
    by_kind = _by_kind()
    # One region of every kind: the map is a cycle of stages, not a rack
    # of duplicated hardware.
    for kind in EXPECTED_KINDS:
        assert len(by_kind.get(kind, [])) == 1, f"expected exactly one {kind}"


def test_kinds_are_expected_set():
    kinds = {r.kind for r in ANATOMY.regions}
    assert kinds <= EXPECTED_KINDS
    # The map should exercise every kind the model defines — including
    # loss, which is the one a brochure would omit.
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
    # Spot-check the alias generator end to end — flowsTo especially,
    # since the frontend draws the loop's arrows from it.
    data = ANATOMY.model_dump(by_alias=True)
    assert "formFactor" in data
    assert "regions" in data and "description" in data["regions"][0]
    assert "flowsTo" in data["regions"][0]
