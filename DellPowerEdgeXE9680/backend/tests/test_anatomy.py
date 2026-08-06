"""Geometry/data invariants for the XE9680 chassis floorplan."""

from typing import get_args

from app.anatomy import ANATOMY
from app.models import RegionKind

EXPECTED_KINDS = set(get_args(RegionKind))
GPUS = [f"g{i}" for i in range(1, 9)]


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


def test_eight_identical_gpus():
    """Eight SXM sockets on one baseboard, all drawn identically — the
    modules are interchangeable and the drawing must say so."""
    gpus = [r for r in ANATOMY.regions if r.kind == "gpu"]
    assert len(gpus) == 8
    assert {r.id for r in gpus} == {f"gpu-{g}" for g in GPUS}
    first = gpus[0]
    for r in gpus[1:]:
        assert r.w == first.w and r.h == first.h, f"{r.id} differs in size"


def test_every_gpu_has_its_own_nic():
    """One GPU, one NIC — the machine's design signature, drawn as a 1:1
    pairing: eight uniformly-sized network regions whose ids match the GPU
    ids suffix for suffix."""
    nics = [r for r in ANATOMY.regions if r.kind == "network"]
    assert len(nics) == 8, "expected exactly one NIC region per GPU"
    assert {r.id for r in nics} == {f"nic-{g}" for g in GPUS}
    first = nics[0]
    for r in nics[1:]:
        assert r.w == first.w and r.h == first.h, f"{r.id} differs in size"


def test_the_gpu_field_dominates_the_chassis():
    """The chassis exists to carry the HGX baseboard: the GPUs' combined
    drawn area must exceed every other kind's combined area — a floorplan
    where the host looked as big as the accelerators would tell the reader
    something false about what this machine is."""
    area: dict[str, float] = {}
    for r in ANATOMY.regions:
        area[r.kind] = area.get(r.kind, 0.0) + r.w * r.h
    gpu_area = area.pop("gpu")
    for kind, a in area.items():
        assert gpu_area > a, f"{kind} ({a}) out-draws the GPU field ({gpu_area})"


def test_the_nvswitch_sits_between_gpus_and_nics():
    """The geometry encodes the traffic hierarchy: the NVSwitch strip lies
    strictly right of every GPU and strictly left of every NIC — inside the
    box before the fabric, always."""
    nvswitch = [r for r in ANATOMY.regions if r.kind == "nvswitch"]
    assert len(nvswitch) == 1
    sw = nvswitch[0]
    for r in ANATOMY.regions:
        if r.kind == "gpu":
            assert r.x + r.w <= sw.x, f"{r.id} not left of the NVSwitch"
        if r.kind == "network":
            assert sw.x + sw.w <= r.x, f"{r.id} not right of the NVSwitch"


def test_expected_shared_counts():
    # Two fan banks (air is the coolant), one of each singleton block.
    assert sum(1 for r in ANATOMY.regions if r.kind == "cooling") == 2
    for kind in ("compute", "storage", "power", "management"):
        assert sum(1 for r in ANATOMY.regions if r.kind == kind) == 1, kind


def test_kinds_are_expected_set():
    kinds = {r.kind for r in ANATOMY.regions}
    assert kinds <= EXPECTED_KINDS
    # The floorplan should exercise every kind the model defines.
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
