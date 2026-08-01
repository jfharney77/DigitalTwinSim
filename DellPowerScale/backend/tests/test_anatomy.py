"""Geometry/data invariants for the PowerScale cluster map."""

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


def test_the_namespace_spans_every_node():
    """The lesson, drawn. The namespace region's horizontal extent must
    cover every node region, and it must be the only region in the map
    that does. Everything else belongs to a node or sits in a band; the
    namespace is the one thing that refuses to be partitioned, and the
    drawing has to say so."""
    by_kind = _by_kind()
    namespaces = by_kind["namespace"]
    assert len(namespaces) == 1, "one file system, one region"
    ns = namespaces[0]
    nodes = by_kind["node"]
    left = min(n.x for n in nodes)
    right = max(n.x + n.w for n in nodes)
    assert ns.x <= left and ns.x + ns.w >= right, (
        "the namespace must horizontally span every node"
    )
    for r in ANATOMY.regions:
        if r.id == ns.id:
            continue
        covers_all = r.x <= left and r.x + r.w >= right
        assert not covers_all, (
            f"{r.id} also spans every node — the namespace must be the "
            f"only region that does"
        )


def test_nodes_are_drawn_identically():
    """No node is a controller, a head, or a spare, so none may be drawn
    as though it were. Uniformity in the picture is the architecture."""
    nodes = _by_kind()["node"]
    assert len(nodes) == 6, "six nodes: four initial, two joining mid-trace"
    first = nodes[0]
    for n in nodes[1:]:
        assert n.w == first.w and n.h == first.h, f"node not uniform: {n.id}"
        assert n.y == first.y, f"node out of the band: {n.id}"


def test_every_node_has_its_media():
    """Each node carries its own drives, drawn directly beneath it."""
    by_kind = _by_kind()
    media = by_kind["media"]
    nodes = by_kind["node"]
    assert len(media) == len(nodes) == 6
    node_by_x = {n.x: n for n in nodes}
    first = media[0]
    for m in media[1:]:
        assert m.w == first.w and m.h == first.h, f"media not uniform: {m.id}"
        assert m.y == first.y, f"media out of the band: {m.id}"
    for m in media:
        assert m.x in node_by_x, f"{m.id} not aligned under a node"
        assert m.y >= node_by_x[m.x].y + node_by_x[m.x].h, (
            f"{m.id} not beneath its node"
        )


def test_the_protocol_band_sits_above_the_namespace_and_nodes():
    """Access comes from above: protocols over the namespace over the
    nodes. All four protocols are drawn — reachable cluster-wide, none
    attached to any single node."""
    by_kind = _by_kind()
    protos = by_kind["protocol"]
    assert {p.id for p in protos} == {
        "proto-nfs", "proto-smb", "proto-s3", "proto-hdfs",
    }
    ns = by_kind["namespace"][0]
    top_of_nodes = min(n.y for n in by_kind["node"])
    for p in protos:
        assert p.y + p.h <= ns.y, f"{p.id} not above the namespace"
    assert ns.y + ns.h <= top_of_nodes, "the namespace must sit above the nodes"


def test_region_counts():
    by_kind = _by_kind()
    for kind in ("namespace", "interconnect", "management"):
        assert len(by_kind[kind]) == 1, f"expected exactly one {kind} region"
    assert len(by_kind["node"]) == 6
    assert len(by_kind["media"]) == 6
    assert len(by_kind["protocol"]) == 4


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
