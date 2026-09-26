"""Reading-level variants for the composition layer's prose.

This package's binding to the shared mechanism in :mod:`twinkit.leveling`,
with its own registry, like every component backend's ``leveling.py``.
"""

from __future__ import annotations

from twinkit.leveling import (  # noqa: F401
    DEFAULT_LEVEL,
    LEVELS,
    LEVEL_NAMES,
    Leveling,
    LevelingConflict,
    make_leveling,
)

_LEVELING = make_leveling(__name__)

L = _LEVELING.L
variant_for = _LEVELING.variant_for
resolve = _LEVELING.resolve
leveled = _LEVELING.leveled
leveled_all = _LEVELING.leveled_all
registry = _LEVELING.registry
coverage = _LEVELING.coverage
