"""Invariants for the reading-level system.

The mechanism is shared verbatim across every twin in this repo, and so is
this test file — if you change one, change them all.
"""

from __future__ import annotations

import app.anatomy  # noqa: F401  (import for the side effect of registering)
import app.catalog  # noqa: F401
import app.usecases  # noqa: F401
from app.anatomy import ANATOMY
from app.engine import simulate
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
from app.models import NamespaceResponse

# Registration happens at import time, but the engine builds its states in
# the function body, so the trace has to be constructed once before the
# registry is complete.
simulate()


def test_levels_are_one_to_five():
    assert LEVELS == (1, 2, 3, 4, 5)
    assert set(LEVEL_NAMES) == set(LEVELS)
    assert DEFAULT_LEVEL in LEVELS


def test_something_is_actually_levelled():
    """A guard against the control shipping as a no-op."""
    assert registry(), "no prose registered — the level control would do nothing"


def test_every_registered_block_has_a_standard_variant():
    """Level 3 is what the data module holds, so it must always exist —
    that is what makes dropping L(...) a safe edit."""
    for key, variants in registry().items():
        assert DEFAULT_LEVEL in variants, key[:80]
        assert variants[DEFAULT_LEVEL] == key


def test_every_variant_is_nonempty_and_distinct_from_its_neighbours():
    """Five identical paragraphs behind a five-position control would be a
    lie about the control."""
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
                f"level 1 is shorter than level 5 in {key[:60]!r} — the "
                f"scale is inverted or the novice text is under-explained"
            )


def test_resolution_is_total_at_every_level():
    """Every level must produce a complete, valid payload — no missing
    keys, no None leaking in where prose should be."""
    for level in LEVELS:
        an = leveled(ANATOMY, level)
        assert an.overview.strip()
        for region in an.regions:
            assert region.description.strip(), f"{region.id} at level {level}"
        trace = leveled(NamespaceResponse(trace=simulate()), level)
        for state in trace.trace:
            assert state.description.strip(), f"step {state.step} at level {level}"
            assert state.label.strip()


def test_default_level_is_the_untouched_text():
    """Requesting level 3 must be byte-identical to no leveling at all,
    which is what keeps the feature from changing existing behaviour."""
    assert leveled(ANATOMY, DEFAULT_LEVEL).model_dump() == ANATOMY.model_dump()
    base = NamespaceResponse(trace=simulate())
    assert leveled(base, DEFAULT_LEVEL).model_dump() == base.model_dump()


def test_levels_actually_differ_somewhere():
    """The end-to-end check: the payload a reader gets at 1 is not the
    payload they get at 5."""
    assert (
        leveled(ANATOMY, 1).model_dump() != leveled(ANATOMY, 5).model_dump()
    ) or (
        leveled(NamespaceResponse(trace=simulate()), 1).model_dump()
        != leveled(NamespaceResponse(trace=simulate()), 5).model_dump()
    )


def test_unregistered_text_passes_through_unchanged():
    novel = "a sentence that was never wrapped in L()"
    for level in LEVELS:
        assert variant_for(novel, level) == novel


def test_fallback_picks_the_nearest_authored_level():
    """Sparse authoring must degrade gracefully rather than blanking."""
    from app.leveling import L

    key = "unit-test sentinel: standard register"
    L(standard=key, novice="unit-test sentinel: opened up")
    assert variant_for(key, 1) == "unit-test sentinel: opened up"
    assert variant_for(key, 2) == "unit-test sentinel: opened up"  # nearer 1
    assert variant_for(key, 3) == key
    assert variant_for(key, 5) == key  # nothing above 3, so 3 wins


def test_resolve_walks_nested_structures():
    key = next(iter(registry()))
    variants = registry()[key]
    target = max(variants)
    payload = {"a": [{"b": key}], "c": ("untouched", 7, None)}
    out = resolve(payload, target)
    assert out["a"][0]["b"] == variants[target]
    assert out["c"] == ("untouched", 7, None)


def test_coverage_is_reported_and_the_ends_are_not_empty():
    """A soft quality gate: it is fine for a block to be authored only at
    level 3, but if *nothing* is written for the ends the control is
    decorative."""
    counts = coverage()
    assert counts[3] == len(registry())
    assert counts[1] > 0, "no novice-level prose authored"
    assert counts[5] > 0, "no expert-level prose authored"
