"""Reading-level variants for this twin's prose.

The mechanism lives in :mod:`twinkit.leveling`. It used to be copied
byte-for-byte into all 42 component backends, which meant "if you change one,
change them all". This module is now this component's binding to the shared
mechanism: its own registry, re-exported under the names the data modules,
``main.py`` and ``tests/test_leveling.py`` already import.

A registry per component matters now that a root ``pytest`` imports every
component into one interpreter — see :class:`twinkit.leveling.Leveling`.
"""

from __future__ import annotations

from twinkit.leveling import (  # noqa: F401
    DEFAULT_LEVEL,
    LEVELS,
    LEVEL_NAMES,
    MAX_REGISTERED,
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

__all__ = [
    "DEFAULT_LEVEL",
    "LEVELS",
    "LEVEL_NAMES",
    "MAX_REGISTERED",
    "Leveling",
    "LevelingConflict",
    "L",
    "variant_for",
    "resolve",
    "leveled",
    "leveled_all",
    "registry",
    "coverage",
]
