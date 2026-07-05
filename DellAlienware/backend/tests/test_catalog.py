"""Integrity checks for the catalog and use cases: defaults resolve, ids
unique, and every cross-reference (adapter, anatomy, region) points at
something real."""

from __future__ import annotations

from app.anatomy import ANATOMIES
from app.catalog import DEFAULT_PROFILE, PROFILES
from app.usecases import USE_CASES


def test_default_profile_exists():
    assert DEFAULT_PROFILE.id in PROFILES
    assert PROFILES[DEFAULT_PROFILE.id] is DEFAULT_PROFILE
    assert DEFAULT_PROFILE.id == "m18-r2"


def test_profile_ids_unique():
    ids = list(PROFILES)
    assert len(ids) == len(set(ids))
    assert len(ids) >= 2


def test_adapter_ids_unique_within_each_profile():
    for profile in PROFILES.values():
        ids = [a.id for a in profile.adapters]
        assert len(ids) == len(set(ids)), profile.id


def test_default_adapter_resolves():
    for profile in PROFILES.values():
        assert profile.default_adapter_id in {a.id for a in profile.adapters}, (
            profile.id
        )
        # The default must be a recognized adapter — the happy path.
        default = next(
            a for a in profile.adapters if a.id == profile.default_adapter_id
        )
        assert default.recognized


def test_every_profile_has_an_unrecognized_adapter_option():
    for profile in PROFILES.values():
        assert any(not a.recognized for a in profile.adapters), profile.id


def test_profile_anatomy_id_resolves():
    for profile in PROFILES.values():
        assert profile.anatomy_id in ANATOMIES, profile.id


def test_adapter_physics_sane():
    for profile in PROFILES.values():
        for a in profile.adapters:
            assert a.watts > 0 and a.voltage > 0 and a.amps > 0, a.id
            # Rated wattage roughly equals V × A.
            assert abs(a.voltage * a.amps - a.watts) / a.watts < 0.05, a.id
            assert a.description.strip(), a.id


def test_profiles_have_content():
    for profile in PROFILES.values():
        assert profile.description.strip(), profile.id
        assert profile.battery.wh > 0
        assert profile.cpu_max_w > 0 and profile.gpu_tgp_w > 0
        assert profile.idle_w > 0


def test_use_case_ids_unique_and_content_present():
    ids = [uc.id for uc in USE_CASES]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 2
    assert "sustained-gpu" in ids
    for uc in USE_CASES:
        assert uc.summary.strip() and uc.persona.strip() and uc.outcome.strip()
        assert len(uc.steps) >= 3, uc.id
        assert uc.sources, uc.id
        for step in uc.steps:
            assert step.title.strip() and step.body.strip(), uc.id


def test_use_case_region_ids_resolve_in_every_anatomy():
    # Use cases are not tied to one profile, so their regions must exist in
    # every anatomy (all share the required-region vocabulary).
    for anatomy in ANATOMIES.values():
        region_ids = {r.id for r in anatomy.regions}
        for uc in USE_CASES:
            for step in uc.steps:
                for rid in step.region_ids:
                    assert rid in region_ids, (
                        f"{uc.id}/{step.title}: unknown region {rid!r} "
                        f"in anatomy {anatomy.id!r}"
                    )
