"""Invariants for the reading-level system.

The mechanism (``app/leveling.py``) is shared verbatim across every twin in
this repo. This variant of the test file covers the twins that carry
*several* annotated subjects rather than one — here, five real GPU dies —
so it asserts over ``ANATOMIES`` rather than a single ``ANATOMY``.
"""

from __future__ import annotations

from app.anatomy import ANATOMIES
from app.leveling import (
    DEFAULT_LEVEL,
    LEVELS,
    LEVEL_NAMES,
    coverage,
    leveled,
    registry,
    resolve,
    variant_for,
)


def test_levels_are_one_to_five():
    assert LEVELS == (1, 2, 3, 4, 5)
    assert set(LEVEL_NAMES) == set(LEVELS)
    assert DEFAULT_LEVEL in LEVELS


def test_something_is_actually_levelled():
    """A guard against the control shipping as a no-op."""
    assert registry(), "no prose registered — the level control would do nothing"


def test_every_registered_block_has_a_standard_variant():
    for key, variants in registry().items():
        assert DEFAULT_LEVEL in variants, key[:80]
        assert variants[DEFAULT_LEVEL] == key


def test_every_variant_is_nonempty_and_distinct_from_its_neighbours():
    for key, variants in registry().items():
        for level, text in variants.items():
            assert text.strip(), f"level {level} of {key[:60]!r} is empty"
        ordered = [variants[level] for level in sorted(variants)]
        for a, b in zip(ordered, ordered[1:]):
            assert a != b, f"duplicate adjacent variants in {key[:60]!r}"


def test_the_scale_runs_the_right_way():
    """Level 1 opens the jargon up and level 5 leaves it in, so where both
    ends are authored the novice text should not be the terser one."""
    for key, variants in registry().items():
        if 1 in variants and 5 in variants:
            assert len(variants[1]) > len(variants[5]), (
                f"level 1 is shorter than level 5 in {key[:60]!r}"
            )


def test_every_die_resolves_at_every_level():
    for level in LEVELS:
        for die_id, die in ANATOMIES.items():
            out = leveled(die, level)
            assert out.overview.strip(), f"{die_id} at level {level}"
            for region in out.regions:
                assert region.description.strip(), f"{die_id}/{region.id} @ {level}"


def test_default_level_is_the_untouched_text():
    """Requesting level 3 must be byte-identical to no leveling at all."""
    for die in ANATOMIES.values():
        assert leveled(die, DEFAULT_LEVEL).model_dump() == die.model_dump()


def test_levels_actually_differ_for_every_die():
    """Each die carries its own authored prose, so each must respond to the
    control — one leveled die and four static ones would be worse than
    none, because the control would look broken on four tabs."""
    for die_id, die in ANATOMIES.items():
        assert (
            leveled(die, 1).model_dump() != leveled(die, 5).model_dump()
        ), f"{die_id} reads identically at both ends of the scale"


def test_unregistered_text_passes_through_unchanged():
    novel = "a sentence that was never wrapped in L()"
    for level in LEVELS:
        assert variant_for(novel, level) == novel


def test_resolve_walks_nested_structures():
    key = next(iter(registry()))
    variants = registry()[key]
    target = max(variants)
    payload = {"a": [{"b": key}], "c": ("untouched", 7, None)}
    out = resolve(payload, target)
    assert out["a"][0]["b"] == variants[target]
    assert out["c"] == ("untouched", 7, None)


def test_coverage_is_reported_and_the_ends_are_not_empty():
    counts = coverage()
    assert counts[3] == len(registry())
    assert counts[1] > 0, "no novice-level prose authored"
    assert counts[5] > 0, "no expert-level prose authored"


def test_coverage_floor_after_spec_29():
    """spec_29 authored the ends of the scale for the 8 die overviews, all
    40 unique region descriptions, and the 15 lesson-tour blocks — 63
    registered blocks with levels 1 and 5. Floor set just under that count
    so the registry can't quietly regress to overviews-only."""
    import app.main  # noqa: F401 — ensures anatomy and tour are loaded

    counts = coverage()
    assert counts[1] >= 60, f"novice coverage regressed: {counts[1]}"
    assert counts[5] >= 60, f"expert coverage regressed: {counts[5]}"
