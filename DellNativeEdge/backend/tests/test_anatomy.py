"""Geometry/data invariants for the NativeEdge platform map."""

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


def test_the_endpoint_band_is_uniform():
    """An estate is one building block repeated: at least four endpoint
    regions, all the same size — the drawing must not suggest any site is
    special, because none is."""
    endpoints = [r for r in ANATOMY.regions if r.kind == "endpoint"]
    assert len(endpoints) >= 4, "an estate needs a band, not a couple of boxes"
    first = endpoints[0]
    for r in endpoints[1:]:
        assert r.w == first.w and r.h == first.h, (
            f"endpoint band not uniform: {r.id}"
        )


def test_the_orchestrator_is_central_and_singular():
    """One control plane is the product: exactly one orchestrator region,
    drawn larger than anything else and horizontally central — the singular
    answer to the plural estate."""
    orchestrators = [r for r in ANATOMY.regions if r.kind == "orchestrator"]
    assert len(orchestrators) == 1
    orch = orchestrators[0]
    for r in ANATOMY.regions:
        if r.id != orch.id:
            assert orch.w * orch.h > r.w * r.h, (
                f"{r.id} out-draws the Orchestrator"
            )
    center = orch.x + orch.w / 2
    assert 0.35 * ANATOMY.width <= center <= 0.65 * ANATOMY.width, (
        "the Orchestrator must sit centrally in the diagram"
    )


def test_the_estate_is_left_and_the_control_is_right():
    """The diagram's axis is the platform's direction of trust: every
    endpoint sits strictly left of the Orchestrator, and the blueprint /
    catalog / policy / observability planes sit strictly right of it —
    nothing at a site configures a site."""
    orch = next(r for r in ANATOMY.regions if r.kind == "orchestrator")
    for r in ANATOMY.regions:
        if r.kind in ("endpoint", "network", "identity"):
            assert r.x + r.w <= orch.x, f"{r.id} not left of the Orchestrator"
        if r.kind in ("blueprint", "catalog", "policy", "observability"):
            assert orch.x + orch.w <= r.x, f"{r.id} not right of the Orchestrator"


def test_topology_counts():
    kinds = {}
    for r in ANATOMY.regions:
        kinds.setdefault(r.kind, []).append(r.id)
    assert len(kinds["endpoint"]) == 4
    for singleton in (
        "network", "identity", "orchestrator",
        "blueprint", "catalog", "policy", "observability",
    ):
        assert len(kinds[singleton]) == 1, singleton


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
