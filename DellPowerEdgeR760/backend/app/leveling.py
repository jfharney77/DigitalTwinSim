"""Reading-level variants for the twin's prose.

Every twin in this repo teaches, and the audience is not one person. A
storage architect reading the PowerFlex twin wants "mesh mirroring across
the fault domain"; someone three months into their first infrastructure job
wants the same sentence with the jargon opened up and the comparative
asides removed. Writing for the midpoint serves neither well.

So each block of prose can carry up to five variants — level 1 for a
newcomer through level 5 for a specialist — and the API serves whichever
the reader asked for. The mechanism is deliberately boring:

* ``L(...)`` registers the variants and **returns the level-3 string**, so
  the data modules read exactly as they did before and every model field
  stays a plain ``str``. No pydantic types change, no wire format changes,
  and the frontend's TypeScript is untouched.
* ``resolve(payload, level)`` walks a dumped payload and swaps any
  registered string for the requested level's variant.

Registration is keyed by the level-3 text. Two blocks with byte-identical
level-3 prose would therefore share variants — which is almost always what
you want, and ``tests/test_leveling.py`` fails loudly if two ``L()`` calls
ever register *different* variants under the same key.

Blocks that were never wrapped in ``L()`` simply read the same at every
level. That is a deliberate fallback rather than a gap to be ashamed of:
some sentences have one good phrasing, and inventing five of them would
make the text worse.
"""

from __future__ import annotations

from typing import Any

# 1 is a newcomer to the subject; 5 is a specialist who wants the jargon
# left in and the explanations taken out. 3 is the register the twins were
# originally written in.
LEVELS = (1, 2, 3, 4, 5)

LEVEL_NAMES = {
    1: "novice",
    2: "plain",
    3: "standard",
    4: "technical",
    5: "expert",
}

DEFAULT_LEVEL = 3

# Most twins register a fixed set of blocks once, at import or on the first
# ``simulate()``. The Alienware twin is the exception: its descriptions are
# f-strings interpolating the scenario (adapter name, battery percentage,
# thermal mode), so a distinct scenario produces distinct level-3 text and
# therefore a distinct key. That is correct behaviour — all five variants
# are rendered together in the same call, so they stay consistent — but it
# means the registry grows with the number of scenarios a long-running
# server has been asked for.
#
# This cap bounds that growth. Past it, further blocks simply go
# unregistered, which degrades them to reading the same at every level
# rather than failing. A few thousand entries is far more than any twin
# needs and a few megabytes at worst.
MAX_REGISTERED = 4096

# level-3 text -> {level: text}
_REGISTRY: dict[str, dict[int, str]] = {}


class LevelingConflict(ValueError):
    """Two L() calls registered different variants under the same key."""


def L(
    *,
    standard: str,
    novice: str | None = None,
    plain: str | None = None,
    technical: str | None = None,
    expert: str | None = None,
) -> str:
    """Register reading-level variants and return the level-3 text.

    ``standard`` is required and is what the data module actually holds, so
    dropping ``L(...)`` from any call site leaves the twin working exactly
    as it did. The other four are optional; any level with no variant falls
    back to the nearest one that exists (see ``variant_for``).
    """
    variants = {3: standard}
    for level, text in ((1, novice), (2, plain), (4, technical), (5, expert)):
        if text is not None:
            variants[level] = text

    existing = _REGISTRY.get(standard)
    if existing is None and len(_REGISTRY) >= MAX_REGISTERED:
        # Bounded: this block reads the same at every level rather than
        # growing the registry without limit. See MAX_REGISTERED.
        return standard
    if existing is not None and existing != variants:
        raise LevelingConflict(
            "two blocks share level-3 text but declare different variants; "
            "give them distinguishable standard text:\n"
            f"  {standard[:120]!r}"
        )
    _REGISTRY[standard] = variants
    return standard


def variant_for(text: str, level: int) -> str:
    """The best available variant of ``text`` at ``level``.

    Unregistered text is returned unchanged. When the requested level has
    no variant, the nearest authored level wins.

    Ties break *away* from the standard register, in the direction the
    reader asked for. Someone requesting level 2 against variants authored
    at 1 and 3 is equidistant from both, and handing them level 3 would
    give them denser prose than they asked for — the opposite of what the
    request meant. Level 1 is the safer miss: overshooting toward more
    explanation costs a specialist a few seconds, while undershooting
    leaves a newcomer stuck. The same logic runs upward, so a request for
    4 against {3, 5} lands on 5.
    """
    variants = _REGISTRY.get(text)
    if not variants:
        return text
    if level in variants:
        return variants[level]
    return variants[
        min(variants, key=lambda a: (abs(a - level), -abs(a - DEFAULT_LEVEL), a))
    ]


def resolve(payload: Any, level: int) -> Any:
    """Recursively swap registered strings in a dumped payload."""
    if level == DEFAULT_LEVEL:
        # Fast path: the data already holds the level-3 text.
        return payload
    if isinstance(payload, str):
        return variant_for(payload, level)
    if isinstance(payload, dict):
        return {k: resolve(v, level) for k, v in payload.items()}
    if isinstance(payload, list):
        return [resolve(v, level) for v in payload]
    return payload


def leveled(model: Any, level: int) -> Any:
    """Return a copy of a pydantic model with its prose set to ``level``."""
    return type(model).model_validate(resolve(model.model_dump(), level))


def leveled_all(models: list[Any], level: int) -> list[Any]:
    return [leveled(m, level) for m in models]


def registry() -> dict[str, dict[int, str]]:
    """The registered blocks — for tests and for coverage reporting."""
    return dict(_REGISTRY)


def coverage() -> dict[str, int]:
    """How many registered blocks carry each level. Used by the tests to
    keep an eye on how much of the prose is actually written for the ends
    of the scale rather than only the middle."""
    counts = {level: 0 for level in LEVELS}
    for variants in _REGISTRY.values():
        for level in variants:
            counts[level] += 1
    return counts
