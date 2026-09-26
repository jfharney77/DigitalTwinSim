"""C4 — A gray failure in the fabric becomes lost tokens in the factory.

A training step is a compute part and a collective part. Only the collective
part stretches when the fabric's flow-completion time stretches::

    stretch      = (1 − comm_fraction) + comm_fraction × fct_regime / fct_healthy
    tokens_scale = 1 / stretch

PhysicsAIFactory has no mid-run fabric event, so the factory runs once per
fabric regime with ``tokens_per_gpu_s × tokens_scale`` and the traces are
spliced at the regime boundaries.
"""

from __future__ import annotations

import copy
from typing import Any, Sequence

from .. import constants as K
from ..reader import get
from ..seam import compare
from ..models import SeamResult

ID = "c4"


def regimes(fabric_trace: Sequence[Any]) -> list[dict]:
    """Consecutive stretches of the fabric run that share a gray/healthy state."""
    out: list[dict] = []
    for i, s in enumerate(fabric_trace):
        gray = float(get(s, "goodput_penalty_pct", 0.0)) > 0.0
        if not out or out[-1]["gray"] != gray:
            out.append({"gray": gray, "start": i, "end": i + 1})
        else:
            out[-1]["end"] = i + 1
    for r in out:
        ticks = fabric_trace[r["start"]:r["end"]]
        tail = ticks[int(0.8 * len(ticks)):] or ticks
        r["fctMs"] = sum(float(get(s, "fct_ms", 0.0)) for s in tail) / len(tail)
        r["allGreen"] = all(bool(get(s, "status_all_green", True)) for s in ticks)
        r["goodputPenaltyPct"] = max(float(get(s, "goodput_penalty_pct", 0.0)) for s in ticks)
    return out


def tokens_scale(fct_ms: float, fct_healthy_ms: float) -> float:
    f = K.value("comm_fraction")
    ratio = fct_ms / fct_healthy_ms if fct_healthy_ms > 0 else 1.0
    return 1.0 / ((1.0 - f) + f * ratio)


def plan(fabric_trace: Sequence[Any]) -> list[dict]:
    rs = regimes(fabric_trace)
    healthy = [r for r in rs if not r["gray"]]
    ref = healthy[0]["fctMs"] if healthy else rs[0]["fctMs"]
    n = len(fabric_trace)
    for r in rs:
        r["tokensScale"] = round(tokens_scale(r["fctMs"], ref), 6)
        r["startFrac"], r["endFrac"] = r["start"] / n, r["end"] / n
        r["fctMs"] = round(r["fctMs"], 3)
    return rs


def adapt(base_scenario: dict | None, scale: float) -> dict:
    """The factory scenario for one fabric regime."""
    scenario = copy.deepcopy(base_scenario or {})
    job = scenario.setdefault("job", {})
    job["tokensPerGpuS"] = round(float(job.get("tokensPerGpuS", 200.0)) * scale, 6)
    return scenario


def train_start_h(factory_trace: Sequence[Any]) -> int:
    for s in factory_trace:
        if get(s, "phase") == "train":
            return int(get(s, "t_h"))
    return len(factory_trace)


def boundaries(rs: list[dict], factory_trace: Sequence[Any]) -> None:
    """Map each fabric regime onto factory hours: the fabric run stands for the
    training span, start to end."""
    t0 = train_start_h(factory_trace)
    span = len(factory_trace) - t0
    for i, r in enumerate(rs):
        r["startH"] = 0 if i == 0 else t0 + int(round(r["startFrac"] * span))
        r["endH"] = len(factory_trace) if i == len(rs) - 1 else t0 + int(round(r["endFrac"] * span))


def splice(runs: Sequence[Sequence[dict]], rs: list[dict]) -> list[dict]:
    """Hours ``[startH, endH)`` of regime i's run, with the cumulative counters
    (``tokensTotalB``, ``costUsdM``) restamped so they carry across the joins.
    Within a regime the run's own deltas are kept, including failure rewinds."""
    out: list[dict] = []
    tokens = cost = 0.0
    for run, r in zip(runs, rs):
        a, b = r["startH"], r["endH"]
        base_tokens = run[a - 1]["tokensTotalB"] if a > 0 else 0.0
        base_cost = run[a - 1]["costUsdM"] if a > 0 else 0.0
        for h in range(a, b):
            row = dict(run[h])
            row["tokensTotalB"] = round(tokens + (run[h]["tokensTotalB"] - base_tokens), 3)
            row["costUsdM"] = round(cost + (run[h]["costUsdM"] - base_cost), 3)
            row["usdPerMtok"] = (
                round(row["costUsdM"] * 1e6 / (row["tokensTotalB"] * 1e3), 2)
                if row["tokensTotalB"] > 0 else 0.0
            )
            out.append(row)
        if b > a:
            tokens, cost = out[-1]["tokensTotalB"], out[-1]["costUsdM"]
    return out


def check(
    fabric_trace: Sequence[Any],
    healthy_run: Sequence[dict],
    spliced: Sequence[dict],
    rs: list[dict],
) -> list[SeamResult]:
    seams: list[SeamResult] = []
    gray = [r for r in rs if r["gray"]]
    for r in gray[:1] or rs[:1]:
        hours = [h for h in range(r["startH"], r["endH"])
                 if healthy_run[h]["tokensPerS"] > 0]
        got = sum(spliced[h]["tokensPerS"] for h in hours)
        ref = sum(healthy_run[h]["tokensPerS"] for h in hours)
        ratio = got / ref if ref else 1.0
        seams.append(compare(
            ID, "Factory.tokens_per_s(gray) / Factory.tokens_per_s(healthy) == tokens_scale",
            ratio, r["tokensScale"], "ratio", 0.005 * r["tokensScale"],
            note=f"over factory hours {r['startH']}–{r['endH']}; comm_fraction is an estimate",
            lhs_key="PhysicsAIFactory.tokens_ratio", rhs_key="PhysicsFabric.tokens_scale",
        ))
        green_ticks = sum(1 for s in fabric_trace[r["start"]:r["end"]]
                          if get(s, "status_all_green", True))
        total = r["end"] - r["start"]
        seams.append(compare(
            ID, "Fabric.status_all_green on every gray tick, while factory tokens/s is lower",
            float(green_ticks), float(total), "ticks", 0.0,
            # Both halves, or neither: a fabric run with no gray regime has no
            # gray tick to read as green, so this identity asserts nothing and
            # must not report that it held.
            holds=bool(r["gray"]) and green_ticks == total and ratio < 1.0,
            note=("green and slower, both asserted — the adversarial half crosses the seam"
                  if r["gray"] else
                  "No gray regime in this fabric run: there is no gray tick to read as "
                  "green, and nothing was asserted."),
        ))
    return seams
