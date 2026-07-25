"""Geometry/data invariants for the Private Cloud stack map."""

from typing import get_args

from app.anatomy import ANATOMY
from app.models import RegionKind

EXPECTED_KINDS = set(get_args(RegionKind))

POOL_KINDS = ("compute", "storage", "network")


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


def test_the_hypervisors_are_interchangeable_slots():
    """Four identical slots on one row, not one platform with alternatives
    listed underneath. A diagram that drew one larger would be picking a
    winner on the customer's behalf, which is exactly the thing this
    architecture declines to do."""
    hvs = sorted(_by_kind()["hypervisor"], key=lambda r: r.x)
    assert len(hvs) == 4, "VMware, Red Hat, Nutanix, Microsoft"
    first = hvs[0]
    for h in hvs[1:]:
        assert h.w == first.w and h.h == first.h, f"{h.id} is drawn differently"
        assert h.y == first.y, f"{h.id} is off the hypervisor row"
    xs = [h.x for h in hvs]
    assert all(a < b for a, b in zip(xs, xs[1:])), "slots share a position"


def test_the_pools_are_three_separate_columns():
    """On a hyperconverged diagram compute and storage are the same box,
    because in that architecture they are the same purchase. Here they are
    three disjoint columns side by side, and the drawing has to say so."""
    by_kind = _by_kind()
    pools = [by_kind[k][0] for k in POOL_KINDS]
    for k in POOL_KINDS:
        assert len(by_kind[k]) == 1, f"expected exactly one {k} pool"
    for a, b in zip(pools, pools[1:]):
        assert a.x + a.w <= b.x, f"{a.id} and {b.id} are not separate columns"
    ys = {p.y for p in pools}
    assert len(ys) == 1, "the pools sit on one row, as peers"


def test_the_stack_is_layered_top_to_bottom():
    """Control plane over workloads over hypervisors over pools. The order
    is the argument: what is above does not care what is below."""
    by_kind = _by_kind()
    control = by_kind["controlplane"][0]
    workloads = by_kind["workload"][0]
    hv_top = min(r.y for r in by_kind["hypervisor"])
    pool_top = min(by_kind[k][0].y for k in POOL_KINDS)
    assert control.y + control.h <= workloads.y
    assert workloads.y + workloads.h <= hv_top
    hv_bottom = max(r.y + r.h for r in by_kind["hypervisor"])
    assert hv_bottom <= pool_top


def test_the_control_plane_spans_everything():
    """One plane over the lot — so it is drawn as the widest thing in the
    map, and there is exactly one of it."""
    by_kind = _by_kind()
    assert len(by_kind["controlplane"]) == 1
    control = by_kind["controlplane"][0]
    for r in ANATOMY.regions:
        assert r.w <= control.w, f"{r.id} is wider than the control plane"


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
