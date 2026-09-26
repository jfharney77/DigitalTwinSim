"""C3 — Exascale delivered throughput becomes the GPUs' data feed.

PhysicsStorage ticks in hours, PhysicsCompute in seconds. The storage run is
reduced to its *distinct operating points* (deduplicated — a week with
checkpoint bursts is two or three points, not 168), and one compute run visits
each point for ``window_s`` seconds through ``set-data-feed`` events.

``feed_pct = round(100 − gpu_idle_due_to_data_pct)`` is exactly the quantity
Storage already computes from delivered over demanded read IOPS.
"""

from __future__ import annotations

import copy
from typing import Any, Sequence

from ..reader import get, series
from ..seam import compare
from ..models import SeamResult

ID = "c3"
MAX_POINTS = 12   # 12 × 600 s = PhysicsCompute's 7200 s ceiling


def feed_series(storage_trace: Sequence[Any]) -> list[float]:
    return [100.0 - v for v in series(storage_trace, "gpu_idle_due_to_data_pct")]


def operating_points(storage_trace: Sequence[Any]) -> list[dict]:
    """Distinct feed levels, in first-seen order, with the hours spent at each."""
    points: dict[int, dict] = {}
    for state, feed in zip(storage_trace, feed_series(storage_trace)):
        pct = int(round(feed))
        entry = points.setdefault(pct, {
            "feedPct": pct, "firstHour": int(get(state, "t_h", 0)), "hours": 0,
            "storageIdlePct": round(100.0 - feed, 1),
        })
        entry["hours"] += 1
    return list(points.values())


def adapt(
    storage_trace: Sequence[Any],
    base_scenario: dict | None = None,
    params: dict | None = None,
) -> tuple[dict, list[dict], list[dict], list[str]]:
    """PhysicsStorage trace -> PhysicsCompute scenario visiting each operating point.

    Returns ``(scenario, injected_events, points, notes)``; each point carries
    the ``[startS, endS)`` window it occupies in the compute run.
    """
    window = int((params or {}).get("window_s", 600))
    points = operating_points(storage_trace)
    notes: list[str] = []
    if len(points) > MAX_POINTS:
        notes.append(f"{len(points)} distinct operating points; only the first "
                     f"{MAX_POINTS} fit PhysicsCompute's 7200 s run.")
        points = points[:MAX_POINTS]
    scenario = copy.deepcopy(base_scenario or {})
    scenario.setdefault("workload", {})["dataFeedPct"] = points[0]["feedPct"]
    scenario["durationS"] = max(10, window * len(points))
    injected = []
    for i, point in enumerate(points):
        point["startS"], point["endS"] = i * window, (i + 1) * window
        if i > 0:
            injected.append({"atS": i * window, "action": "set-data-feed",
                             "value": point["feedPct"]})
    kept = [e for e in scenario.get("events", []) or [] if e.get("action") != "set-data-feed"]
    scenario["events"] = sorted(kept + injected, key=lambda e: e["atS"])
    return scenario, injected, points, notes


def measure(compute_trace: Sequence[Any], points: list[dict], gpu_pct: float, gpus: int) -> None:
    """Fill each point with what the compute run experienced in its window."""
    for p in points:
        a, b = p["startS"], min(p["endS"], len(compute_trace) - 1)
        tail = compute_trace[a + int(0.8 * (b - a)):b]
        util = sum(float(get(s, "effective_gpu_util_pct", 0.0)) for s in tail) / max(len(tail), 1)
        p["computeFedPct"] = round(100.0 * util / gpu_pct, 2) if gpu_pct else 0.0
        wasted = float(get(compute_trace[b], "gpu_hours_wasted", 0.0)) - \
            float(get(compute_trace[a], "gpu_hours_wasted", 0.0))
        p["gpuHoursWasted"] = round(wasted, 3)
        p["gpuHoursExpected"] = round(
            (1.0 - p["feedPct"] / 100.0) * gpus * (gpu_pct / 100.0) * (b - a) / 3600.0, 3)
        p["dcW"] = round(sum(float(get(s, "dc_power_w", 0.0)) for s in tail) / max(len(tail), 1), 1)
        p["tokensPerS"] = round(sum(float(get(s, "tokens_per_s", 0.0)) for s in tail) / max(len(tail), 1), 1)


def check(points: list[dict]) -> list[SeamResult]:
    """The two idle gauges are the same number, at every operating point."""
    worst = max(points, key=lambda p: abs((100.0 - p["storageIdlePct"]) - p["computeFedPct"]))
    gauge = compare(
        ID, "100 − Storage.gpu_idle_due_to_data_pct == Compute.effective_gpu_util / gpu_pct × 100",
        100.0 - worst["storageIdlePct"], worst["computeFedPct"], "%", 1.0,
        note=f"worst of {len(points)} operating point(s), at feed {worst['feedPct']}%; "
             "integer data_feed_pct accounts for up to 0.5",
        lhs_key="PhysicsStorage.fed_pct", rhs_key="PhysicsCompute.fed_pct",
    )
    w = max(points, key=lambda p: abs(p["gpuHoursWasted"] - p["gpuHoursExpected"]))
    wasted = compare(
        ID, "Δ Compute.gpu_hours_wasted == idle fraction × GPUs × window",
        w["gpuHoursWasted"], w["gpuHoursExpected"], "GPU-hours",
        0.02 * max(w["gpuHoursExpected"], 1e-9) + 0.002,
        note="2% + the 0.001 GPU-hour output rounding at each end of the window",
    )
    return [gauge, wasted]
