"""Chains of couplings, and the fixed point that closes a loop.

A chain is data: base scenarios per component and an ordered tuple of links.
``run`` executes it on live engines and returns a ``CoupledTrace``. It never
raises on a broken seam; see ``seam.assert_seams``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import constants as K
from .models import CoupledTrace


@dataclass(frozen=True)
class Link:
    coupling: str                 # "c1", "c2", ...
    source: str                   # component dir, e.g. "PhysicsCompute"
    target: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Chain:
    id: str
    scenarios: dict[str, dict]    # component -> base Scenario (camelCase JSON)
    links: tuple[Link, ...]
    closed: bool = False          # True -> fixed_point() over the C1/C2 cycle
    max_iter: int = int(K.value("fixed_point_max_iter"))
    damping: float = K.value("fixed_point_damping")
    tol: float = K.value("fixed_point_tol")
    title: str = ""
    params: dict[str, Any] = field(default_factory=dict)


def run(chain: Chain) -> CoupledTrace:
    from .executors import execute  # late: executors import every coupling
    return execute(chain)
