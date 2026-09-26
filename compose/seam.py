"""The seam is where the test lives.

``run()`` never raises on a broken seam: it reports ``holds=False`` and the
page shows it. ``assert_seams`` raises, and is what the pytest cases call.
"""

from __future__ import annotations

from typing import Sequence

from .models import CoupledTrace, SeamResult


class BrokenSeam(AssertionError):
    pass


def compare(
    coupling: str,
    identity: str,
    lhs: float,
    rhs: float,
    unit: str,
    tolerance: float,
    *,
    note: str = "",
    worst_tick: int | None = None,
    lhs_key: str | None = None,
    rhs_key: str | None = None,
    holds: bool | None = None,
) -> SeamResult:
    err = abs(lhs - rhs)
    return SeamResult(
        coupling=coupling, identity=identity,
        lhs=round(lhs, 6), rhs=round(rhs, 6), unit=unit,
        abs_error=round(err, 6), tolerance=round(tolerance, 6),
        holds=(err <= tolerance) if holds is None else holds,
        worst_tick=worst_tick, note=note, lhs_key=lhs_key, rhs_key=rhs_key,
    )


def per_tick(
    coupling: str,
    identity: str,
    lhs: Sequence[float],
    rhs: Sequence[float],
    unit: str,
    tolerance: float,
    *,
    skip: Sequence[bool] | None = None,
    note: str = "",
    lhs_key: str | None = None,
    rhs_key: str | None = None,
) -> SeamResult:
    """The worst tick of ``|lhs[t] − rhs[t]|``, ignoring ticks flagged in ``skip``."""
    worst, worst_i = -1.0, None
    for i, (a, b) in enumerate(zip(lhs, rhs)):
        if skip is not None and skip[i]:
            continue
        e = abs(a - b)
        if e > worst:
            worst, worst_i = e, i
    if worst_i is None:
        return compare(coupling, identity, 0.0, 0.0, unit, tolerance,
                       note=(note + " No tick was eligible for comparison.").strip(),
                       lhs_key=lhs_key, rhs_key=rhs_key, holds=False)
    return compare(coupling, identity, lhs[worst_i], rhs[worst_i], unit, tolerance,
                   note=note, worst_tick=worst_i, lhs_key=lhs_key, rhs_key=rhs_key)


def assert_seams(trace: CoupledTrace, only: str | None = None) -> None:
    broken = [
        s for s in trace.seams
        if not s.holds and (only is None or s.coupling == only)
    ]
    if broken:
        lines = [
            f"  [{s.coupling}] {s.identity}: {s.lhs} vs {s.rhs} {s.unit} "
            f"(error {s.abs_error} > tolerance {s.tolerance}"
            + (f", worst tick {s.worst_tick}" if s.worst_tick is not None else "")
            + (f"; {s.note}" if s.note else "") + ")"
            for s in broken
        ]
        raise BrokenSeam(f"chain {trace.chain_id!r}: broken seam(s)\n" + "\n".join(lines))
