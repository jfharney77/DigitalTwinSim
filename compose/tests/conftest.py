"""compose/ has no ``app`` package of its own: it loads each engine under a
private package name, so it needs no claim on the name the component suites
take turns holding. The repo root goes on the path for ``compose`` and
``twinkit``."""

from __future__ import annotations

import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
