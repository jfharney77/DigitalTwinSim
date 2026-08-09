"""Invariants for the reading-level system, adapted to this app: the
mechanism (leveling.py) is the repo-shared one byte-for-byte; the leveled
surfaces here are the anatomy overview, the Explain entries, and the
guided-scenario narration — the trace states are numbers, not prose."""

from __future__ import annotations

import app.anatomy  # noqa: F401  (import for the side effect of registering)
import app.presets  # noqa: F401
from app.anatomy import ANATOMY
from app.leveling import (
    DEFAULT_LEVEL,
    LEVELS,
    LEVEL_NAMES,
    coverage,
    leveled,
    leveled_all,
    registry,
    variant_for,
)
from app.presets import EXPLAINS, GUIDED_SCENARIOS


def test_levels_are_one_to_five():
    assert LEVELS == (1, 2, 3, 4, 5)
    assert set(LEVEL_NAMES) == set(LEVELS)
    assert DEFAULT_LEVEL in LEVELS


def test_something_is_actually_levelled():
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
    for key, variants in registry().items():
        if 1 in variants and 5 in variants:
            assert len(variants[1]) > len(variants[5]), (
                f"level 1 is shorter than level 5 in {key[:60]!r}"
            )


def test_resolution_is_total_at_every_level():
    for level in LEVELS:
        an = leveled(ANATOMY, level)
        assert an.overview.strip()
        for region in an.regions:
            assert region.description.strip(), f"{region.id} at level {level}"
        for e in leveled_all(EXPLAINS, level):
            assert e.explanation.strip(), e.id
        for g in leveled_all(GUIDED_SCENARIOS, level):
            assert all(p.strip() for p in g.narration), g.id


def test_default_level_is_the_untouched_text():
    assert leveled(ANATOMY, DEFAULT_LEVEL).model_dump() == ANATOMY.model_dump()
    assert [
        e.model_dump() for e in leveled_all(EXPLAINS, DEFAULT_LEVEL)
    ] == [e.model_dump() for e in EXPLAINS]


def test_levels_actually_differ_somewhere():
    assert leveled(ANATOMY, 1).model_dump() != leveled(ANATOMY, 5).model_dump()


def test_unregistered_text_passes_through_unchanged():
    novel = "a sentence that was never wrapped in L()"
    for level in LEVELS:
        assert variant_for(novel, level) == novel


def test_coverage_is_reported_and_the_ends_are_not_empty():
    counts = coverage()
    assert counts[3] == len(registry())
    assert counts[1] > 0, "no novice-level prose authored"
    assert counts[5] > 0, "no expert-level prose authored"
