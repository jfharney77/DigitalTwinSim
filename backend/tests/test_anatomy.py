"""Invariants for the die-anatomy data (spec: anatomy page).

The floorplans are hand-authored data, so these tests guard the geometry:
every region fits inside its die, ids are unique, and no two regions overlap.
"""

from __future__ import annotations

import pytest

from app.anatomy import ANATOMIES, DieAnatomy


@pytest.fixture(params=list(ANATOMIES.values()), ids=lambda a: a.id)
def anatomy(request) -> DieAnatomy:
    return request.param


def test_regions_within_die(anatomy: DieAnatomy) -> None:
    for r in anatomy.regions:
        assert r.x >= 0 and r.y >= 0, f"{anatomy.id}/{r.id} origin out of bounds"
        assert r.x + r.w <= anatomy.width + 1e-6, f"{anatomy.id}/{r.id} exceeds width"
        assert r.y + r.h <= anatomy.height + 1e-6, f"{anatomy.id}/{r.id} exceeds height"
        assert r.w > 0 and r.h > 0, f"{anatomy.id}/{r.id} has no area"


def test_region_ids_unique(anatomy: DieAnatomy) -> None:
    ids = [r.id for r in anatomy.regions]
    assert len(ids) == len(set(ids))


def test_regions_do_not_overlap(anatomy: DieAnatomy) -> None:
    rs = anatomy.regions
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            a, b = rs[i], rs[j]
            separated = (
                a.x + a.w <= b.x + 1e-6
                or b.x + b.w <= a.x + 1e-6
                or a.y + a.h <= b.y + 1e-6
                or b.y + b.h <= a.y + 1e-6
            )
            assert separated, f"{anatomy.id}: {a.id} overlaps {b.id}"


def test_has_metadata(anatomy: DieAnatomy) -> None:
    assert anatomy.regions, "die has no regions"
    assert anatomy.stats, "die has no stats"
    assert anatomy.sources, "die has no sources"
    assert anatomy.overview
