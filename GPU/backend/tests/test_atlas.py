"""spec_30 — the cross-navigation atlas.

The profile↔die correspondence is data (GpuProfile.die_id) with a derived
reverse map. These tests pin resolution in both directions, injectivity, and
the known gaps BY NAME — closing a gap (or opening one) must be a deliberate
test edit, never an accident.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.anatomy import ANATOMIES
from app.main import app
from app.profiles import DEVICE_MATCHES, DIE_TO_PROFILE, PROFILES

client = TestClient(app)

# The authored mapping, pinned. Edit deliberately alongside profiles.py.
MAPPED = {
    "H100-SXM": "gh100",
    "B300-Blackwell-Ultra": "gb300",
    "RTX-5090": "gb202",
    "MI300X": "mi300x",
}
# Profiles without a die: the generics are teaching abstractions on purpose;
# the 4060's AD107 is the honest gap (no anatomy entry yet — follow-up spec).
PROFILES_WITHOUT_DIES = {"Generic-128", "Generic-512", "RTX-4060-Laptop"}
# Dies without a profile: the museum is allowed to be bigger than the bench.
DIES_WITHOUT_PROFILES = {"ga100", "ad102", "navi31", "gb200"}


def test_every_die_id_resolves_in_anatomies() -> None:
    for p in PROFILES.values():
        if p.die_id is not None:
            assert p.die_id in ANATOMIES, f"{p.name}: unknown die {p.die_id!r}"


def test_reverse_map_is_derived_and_injective() -> None:
    # Derived from PROFILES at import, never authored twice — and injective:
    # no two profiles may claim the same die.
    die_ids = [p.die_id for p in PROFILES.values() if p.die_id is not None]
    assert len(die_ids) == len(set(die_ids)), "two profiles claim one die"
    assert DIE_TO_PROFILE == {die: name for name, die in MAPPED.items()}


def test_the_gaps_are_pinned_by_name() -> None:
    unmapped_profiles = {p.name for p in PROFILES.values() if p.die_id is None}
    assert unmapped_profiles == PROFILES_WITHOUT_DIES
    unmapped_dies = set(ANATOMIES) - set(DIE_TO_PROFILE)
    assert unmapped_dies == DIES_WITHOUT_PROFILES
    # Both sides together cover everything: no third category.
    assert {p.name: p.die_id for p in PROFILES.values() if p.die_id} == MAPPED


def test_device_matches_are_nonempty_and_resolvable() -> None:
    # Every deviceMatch belongs to a mapped profile and carries at least one
    # nonempty substring; every mapped profile has match strings (a badge
    # that can never fire is a mapping nobody authored).
    assert set(DEVICE_MATCHES) == set(MAPPED)
    for name, subs in DEVICE_MATCHES.items():
        assert PROFILES[name].die_id is not None
        assert subs and all(s.strip() for s in subs), name


def test_lesson_07_goldens_match_the_atlas() -> None:
    # The motivating payoff: the lesson-07 recordings' device names must hit
    # a deviceMatch substring so the Live tab can badge them.
    for device, want in [
        ("NVIDIA H100 80GB HBM3", "gh100"),
        ("NVIDIA B300 288GB HBM3e", "gb300"),
    ]:
        hits = [
            PROFILES[name].die_id
            for name, subs in DEVICE_MATCHES.items()
            if any(s in device for s in subs)
        ]
        assert hits == [want], f"{device}: matched {hits}"


def test_atlas_endpoint_serves_the_mapping_camelcased() -> None:
    r = client.get("/api/atlas")
    assert r.status_code == 200
    pairs = r.json()["pairs"]
    assert {p["profileName"]: p["dieId"] for p in pairs} == MAPPED
    for p in pairs:
        # camelCase hand-check (spec_30): plain to_camel, no alias gotchas.
        assert set(p) == {"profileName", "dieId", "deviceMatch"}
        assert p["deviceMatch"] == DEVICE_MATCHES[p["profileName"]]
