"""Moving a series from one engine's time base to another's. All pure.

Engines tick at 1 s, 1 h or 1 d. Energy-like quantities ("flow") are pooled so
the integral survives; state-like quantities are held.
"""

from __future__ import annotations

from typing import Any, Sequence

from .reader import get


def steady_window(trace: Sequence[Any], field: str, frac: float = 0.2) -> float:
    """Mean of the last ``frac`` of the run: "this operating point"."""
    if not trace:
        return 0.0
    n = max(1, int(round(len(trace) * frac)))
    window = trace[-n:]
    return sum(float(get(s, field, 0.0) or 0.0) for s in window) / len(window)


def mean_pool(values: Sequence[float], n: int) -> list[float]:
    """Block mean, ``n`` fast ticks per slow tick. Conserves the integral over
    whole blocks: ``sum(pooled) * n == sum(values[:len(pooled) * n])``."""
    if n <= 0:
        raise ValueError("n must be positive")
    blocks = len(values) // n
    return [sum(values[i * n:(i + 1) * n]) / n for i in range(blocks)]


def hold(values: Sequence[float], n: int) -> list[float]:
    """Zero-order hold: one slow tick becomes ``n`` fast ticks."""
    if n <= 0:
        raise ValueError("n must be positive")
    out: list[float] = []
    for v in values:
        out.extend([v] * n)
    return out


def integral(values: Sequence[float], dt: float = 1.0) -> float:
    return sum(values) * dt


def to_events(
    values: Sequence[float],
    deadband: float,
    max_events: int = 240,
    start: int = 0,
    first: bool = True,
) -> tuple[list[tuple[int, float]], float]:
    """``(tick, value)`` pairs, emitted only when the value has moved by more
    than ``deadband`` since the last emitted pair.

    Returns the pairs and the deadband actually used: if the series would need
    more than ``max_events`` the deadband is doubled until it fits, and the
    caller widens its seam tolerance by the same amount.
    """
    band = float(deadband)
    while True:
        out: list[tuple[int, float]] = []
        last: float | None = None
        for i in range(start, len(values)):
            v = values[i]
            if last is None:
                if first:
                    out.append((i, v))
                last = v
                continue
            if abs(v - last) > band:
                out.append((i, v))
                last = v
        if len(out) <= max_events:
            return out, band
        band = band * 2.0 if band > 0 else 1e-9


def downsample(values: Sequence[float], points: int = 120) -> list[float]:
    """Evenly spaced picks, for the iteration scrubber's small charts."""
    n = len(values)
    if n <= points:
        return [round(float(v), 4) for v in values]
    return [round(float(values[int(i * (n - 1) / (points - 1))]), 4) for i in range(points)]
