"""Validation rules for the data & observability simulator. Pure."""

from __future__ import annotations

from .engine import stage_rates
from .models import STAGES, Scenario, Validation


def validate(scenario: Scenario) -> list[Validation]:
    cfg = scenario.config
    wl = scenario.workload
    out: list[Validation] = []

    rates = stage_rates(cfg)
    bottleneck = min(STAGES, key=lambda s: rates[s])
    slowest = rates[bottleneck]

    # Rule 1 — the constraint, named before the run.
    out.append(Validation(
        rule_id="bottleneck", level="ok",
        message=(
            f"The constraint is '{bottleneck}' at {slowest:.0f} TB/h — "
            "the pipeline will move exactly that fast, whatever the "
            "other stages cost."
        ),
        source="spec 06 — throughput = min(stage rates)",
    ))

    # Rule 2 — arrival above the constraint = unbounded backlog.
    if wl.raw_arrival_tbh > slowest:
        out.append(Validation(
            rule_id="arrival", level="warning",
            message=(
                f"Raw arrival {wl.raw_arrival_tbh:.0f} TB/h exceeds the "
                f"constraint ({slowest:.0f}): the backlog and the "
                "freshness lag grow without bound. 'Stale data, "
                "confident model' is this warning, ignored."
            ),
            source="spec 06 — under-provisioned ingest",
        ))

    # Rule 3 — GPU demand above serve capacity.
    if wl.gpu_read_demand_tbh > min(rates["serve"], slowest):
        out.append(Validation(
            rule_id="starvation", level="warning",
            message=(
                f"GPU read demand {wl.gpu_read_demand_tbh:.0f} TB/h "
                "exceeds what the pipeline can serve — the idle gauge "
                "will say so, and PhysicsCompute's wasted-GPU-hours "
                "ledger is the bill."
            ),
            source="spec 06 — GPU idle due to data",
        ))

    # Rule 4 — long-context sessions vs KV capacity.
    long_context = wl.inference_sessions_demand * wl.long_context_pct / 100.0
    base = 40 * (4 if cfg.kv_offload else 1)
    if long_context > base:
        out.append(Validation(
            rule_id="kv", level="warning",
            message=(
                f"≈ {long_context:.0f} long-context sessions against "
                f"capacity {base}: "
                + ("even offloaded KV is full — sessions queue."
                   if cfg.kv_offload else
                   "GPU memory alone can't hold them — the KV-offload "
                   "toggle is the ×4 answer, at a ~12% token tax.")
            ),
            source="estimate — KV-cache session capacity math",
        ))

    # Rule 5 — a detector tuned to either extreme.
    if cfg.anomaly_k <= 1.5:
        out.append(Validation(
            rule_id="detector", level="warning",
            message=(
                f"k = {cfg.anomaly_k:g}: everything is an anomaly. "
                "Recall will look great and precision will make the "
                "feed unreadable — alert fatigue by configuration."
            ),
            source="spec 06 — the sensitivity trade, again on purpose",
        ))
    elif cfg.anomaly_k >= 5.5:
        out.append(Validation(
            rule_id="detector", level="warning",
            message=(
                f"k = {cfg.anomaly_k:g}: nearly nothing is an anomaly. "
                "The quiet feed is hiding the slow issues, not solving "
                "them."
            ),
            source="spec 06",
        ))

    return out
