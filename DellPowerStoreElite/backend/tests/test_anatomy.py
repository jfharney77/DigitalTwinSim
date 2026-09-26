"""Geometry/data invariants for the mixed-generation cluster map."""

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


def test_node_ab_symmetry():
    """Every per-node region has a same-kind, same-size counterpart on the
    other node — on both generations."""
    by_id = {r.id: r for r in ANATOMY.regions}
    a_regions = [r for r in ANATOMY.regions if "-a" in r.id]
    assert a_regions, "expected per-node '-a' regions"
    for a in a_regions:
        twin_id = a.id.replace("-a", "-b")
        assert twin_id in by_id, f"missing node B twin for {a.id}"
        twin = by_id[twin_id]
        assert twin.kind == a.kind
        assert twin.w == a.w and twin.h == a.h


def test_exactly_one_nvram_region():
    nvram = [r for r in ANATOMY.regions if r.kind == "nvram"]
    assert len(nvram) == 1


def test_kinds_are_expected_set():
    kinds = {r.kind for r in ANATOMY.regions}
    assert kinds <= EXPECTED_KINDS
    # The map should exercise every kind the model defines.
    assert kinds == EXPECTED_KINDS


def test_the_generations_are_drawn_as_peers():
    """The map's argument in geometry: two appliances, both full-width
    members of one cluster — the Elite denser (40 E3 slots vs 25), but
    neither drawn as a satellite of the other."""
    prior = [r for r in ANATOMY.regions if r.id.startswith("prior-")]
    elite = [r for r in ANATOMY.regions if r.id.startswith("elite-")]
    assert prior and elite
    prior_right = max(r.x + r.w for r in prior)
    elite_right = max(r.x + r.w for r in elite)
    assert prior_right == elite_right, "the bands must span the same width"
    by_id = {r.id: r for r in ANATOMY.regions}
    prior_bay, elite_bay = by_id["prior-bay"], by_id["elite-bay"]
    assert elite_bay.w * elite_bay.h > prior_bay.w * prior_bay.h, (
        "the Elite bay (40 E3 slots) must be drawn larger than the prior "
        "bay (25 slots) — density is part of the story"
    )


def test_the_mesh_sits_between_the_generations():
    """The cluster network is drawn strictly between the two
    appliance bands — it is the wire the whole modernization travels."""
    by_id = {r.id: r for r in ANATOMY.regions}
    mesh = by_id["cluster-mesh"]
    prior_bottom = max(
        r.y + r.h for r in ANATOMY.regions if r.id.startswith("prior-")
    )
    elite_top = min(
        r.y for r in ANATOMY.regions if r.id.startswith("elite-")
    )
    assert prior_bottom <= mesh.y, "mesh must sit below the prior band"
    assert mesh.y + mesh.h <= elite_top, "mesh must sit above the Elite band"
    assert mesh.w >= 0.6 * ANATOMY.width, "the mesh spans the cluster"


def test_photos_carry_credit_when_present():
    """No Elite product photos ship (licensing); the rule is only that any
    photo that does exist carries its credit line."""
    photos = [ANATOMY.photo] + [r.photo for r in ANATOMY.regions]
    for p in photos:
        if p is not None:
            assert p.credit.strip()


def test_stats_and_sources_nonempty():
    assert ANATOMY.stats
    assert ANATOMY.sources
    assert ANATOMY.overview.strip()


def test_camel_case_wire_format():
    # Spot-check the alias generator end to end.
    data = ANATOMY.model_dump(by_alias=True)
    assert "formFactor" in data
    assert "regions" in data and "description" in data["regions"][0]


def test_every_label_fits_its_block():
    """Mirror ChassisView.tsx's label-fitting rule: a label too long for its
    block is silently dropped, leaving an unlabelled box on the map (the
    Elite CPUs once rendered blank this way). Every region must fit either
    horizontally or rotated."""
    for r in ANATOMY.regions:
        n = len(r.label) or 1
        h_size = min(1.9, r.h * 0.45, (r.w - 1.6) / (n * 0.62))
        v_size = min(1.9, r.w * 0.42, (r.h - 1.6) / (n * 0.62))
        fits_h = r.h > 3.4 and h_size >= 1.05
        fits_v = r.w >= 3 and v_size >= 1.05
        assert r.label and (fits_h or fits_v), f"{r.id}: label {r.label!r} does not fit"
