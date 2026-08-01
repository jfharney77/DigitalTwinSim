"""Geometry/data invariants for the Exascale data-path map."""

from typing import get_args

from app.anatomy import ANATOMY
from app.models import RegionKind

EXPECTED_KINDS = set(get_args(RegionKind))
DATA_SERVERS = ["ds1", "ds2", "ds3", "ds4"]


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


def test_data_server_symmetry():
    """Every data server is the same size and kind, each paired with its own
    media — a parallel file system scales by repeating one building block."""
    by_id = {r.id: r for r in ANATOMY.regions}
    first = by_id["data-ds1"]
    for d in DATA_SERVERS:
        srv, media = by_id.get(f"data-{d}"), by_id.get(f"media-{d}")
        assert srv is not None and media is not None, f"missing pair for {d}"
        assert srv.kind == "dataserver" and media.kind == "media"
        assert srv.w == first.w and srv.h == first.h


def test_metadata_sits_off_the_data_path():
    """The metadata server is drawn above the horizontal band the data
    servers occupy — architecturally beside the data path, not on it. The
    geometry is the lesson, so the test guards it."""
    by_id = {r.id: r for r in ANATOMY.regions}
    mds = by_id["metadata"]
    for d in DATA_SERVERS:
        srv = by_id[f"data-{d}"]
        assert mds.y + mds.h <= srv.y, (
            "metadata server must sit above the data-server band"
        )


def test_topology_counts():
    kinds = {}
    for r in ANATOMY.regions:
        kinds.setdefault(r.kind, []).append(r.id)
    assert len(kinds["metadata"]) == 1, "exactly one metadata server"
    assert len(kinds["dataserver"]) == 4
    assert len(kinds["media"]) == 4
    assert len(kinds["client"]) == 1
    assert len(kinds["management"]) == 1
    # File, object, and block engines all present — the unified rack.
    assert sorted(kinds["protocol"]) == [
        "protocol-block", "protocol-file", "protocol-object",
    ]


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
