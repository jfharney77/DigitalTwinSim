"""Geometry/data invariants for the PowerProtect site map."""

from typing import get_args

from app.anatomy import ANATOMY
from app.models import RegionKind

EXPECTED_KINDS = set(get_args(RegionKind))
VAULT_IDS = {"dd-vault", "cybersense", "recovery-host"}


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


def test_appliance_twins_are_identical():
    """Production and vault Data Domains are the same appliance, drawn the
    same size on purpose — the vault's power is reachability, not hardware."""
    by_id = {r.id: r for r in ANATOMY.regions}
    prod, vault = by_id["dd-prod"], by_id["dd-vault"]
    assert prod.kind == vault.kind == "appliance"
    assert prod.w == vault.w and prod.h == vault.h


def test_vault_sits_beyond_the_gap():
    """Left→right data path: everything in the vault zone lies strictly to
    the right of the air gap, and all production regions strictly left."""
    by_id = {r.id: r for r in ANATOMY.regions}
    gap = by_id["gap"]
    for rid in VAULT_IDS:
        assert by_id[rid].x >= gap.x + gap.w, f"{rid} not beyond the gap"
    for rid in ("workload-vm", "workload-db", "backup-server", "dd-prod"):
        r = by_id[rid]
        assert r.x + r.w <= gap.x, f"{rid} not left of the gap"


def test_topology_counts():
    kinds = {}
    for r in ANATOMY.regions:
        kinds.setdefault(r.kind, []).append(r.id)
    assert len(kinds["appliance"]) == 2
    assert len(kinds["gap"]) == 1
    assert len(kinds["analytics"]) == 1
    assert len(kinds["recovery"]) == 1
    assert len(kinds["backup"]) == 1
    assert len(kinds["workload"]) >= 2


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
