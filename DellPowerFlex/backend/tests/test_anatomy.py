"""Geometry/data invariants for the PowerFlex pool map."""

from typing import get_args

from app.anatomy import ANATOMY
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


def test_nodes_are_drawn_identically():
    """No node is a controller, a spare, or a primary, so none may be drawn
    as though it were. Uniformity in the picture is the architecture."""
    nodes = _by_kind()["node"]
    assert len(nodes) >= 4, "too few nodes to show the pattern"
    first = nodes[0]
    for n in nodes[1:]:
        assert n.w == first.w and n.h == first.h, f"node not uniform: {n.id}"
        assert n.y == first.y, f"node out of the band: {n.id}"


def test_the_coordinator_is_the_smallest_thing_in_the_picture():
    """The metadata manager maps chunks and referees failures; it carries no
    data. Drawing it as large as a node would tell the reader something
    false about where the bytes go, so the geometry is pinned."""
    by_kind = _by_kind()
    coords = by_kind["coordinator"]
    assert len(coords) == 1, "one referee"
    mdm = coords[0]
    mdm_area = mdm.w * mdm.h
    for n in by_kind["node"]:
        assert mdm_area < n.w * n.h, (
            "the coordinator must be drawn smaller than any storage node"
        )


def test_there_is_no_tier_between_clients_and_nodes():
    """The client band sits above the node band with only the fabric
    between them. Any region drawn in that gap would be a controller, and
    the whole point is that there isn't one."""
    by_kind = _by_kind()
    clients = by_kind["client"][0]
    fabric = by_kind["network"][0]
    top_of_nodes = min(n.y for n in by_kind["node"])
    gap_top = clients.y + clients.h
    intruders = [
        r.id
        for r in ANATOMY.regions
        if r.id not in (clients.id, fabric.id)
        and r.y >= gap_top
        and r.y + r.h <= top_of_nodes
    ]
    assert not intruders, f"something sits between clients and nodes: {intruders}"
    assert fabric.y >= gap_top and fabric.y + fabric.h <= top_of_nodes


def test_region_counts():
    by_kind = _by_kind()
    for kind in ("client", "network", "coordinator", "protection", "management"):
        assert len(by_kind[kind]) == 1, f"expected exactly one {kind} region"
    assert len(by_kind["node"]) == 6


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
