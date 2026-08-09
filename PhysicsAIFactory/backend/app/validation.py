"""Validation rules for a factory design: evaluated on every change, each
rule yielding ok | warning | error with an explanation and a source. Reads
like a sizing review — the warnings are the meetings this simulator lets
you skip.

Pure module: no FastAPI, no IO.
"""

from __future__ import annotations

from .constants import value as C
from .engine import fabric_efficiency
from .models import Scenario, Validation


def steady_facility_mw(scenario: Scenario) -> float:
    """Nominal steady-state facility draw: everything training flat out."""
    cfg = scenario.config
    job = scenario.job
    n = cfg.compute.racks * cfg.compute.gpus_per_rack
    peak_w = float(cfg.compute.gpu_peak_w)
    idle_w = C("gpu_idle_fraction") * peak_w
    demand = n * job.data_gbps_per_gpu
    data_util = min(1.0, cfg.data.storage_gbps / demand) if demand else 1.0
    u = data_util * fabric_efficiency(cfg.fabric.type, cfg.fabric.oversubscription)
    gpu_mw = n * (idle_w + (peak_w - idle_w) * u) / 1e6
    fabric_mw = n * C("fabric_kw_per_gpu") / 1000.0
    storage_mw = cfg.data.storage_gbps * C("storage_w_per_gbps") / 1e6
    it = (gpu_mw + fabric_mw + storage_mw) * (1.0 + C("other_it_fraction"))
    pue = C("pue_liquid") if cfg.facility.cooling == "liquid" else C("pue_air")
    return it * pue


def optimal_checkpoint_min(scenario: Scenario) -> float:
    """Young/Daly-style optimum: I* = sqrt(2 · t_ckpt · MTBF_cluster)."""
    cfg = scenario.config
    job = scenario.job
    n = cfg.compute.racks * cfg.compute.gpus_per_rack
    t_ckpt_h = (job.state_gb_per_gpu * n / max(cfg.data.storage_gbps, 1e-9)) / 3600.0
    mtbf_cluster_h = cfg.resilience.gpu_mtbf_h / max(n, 1)
    return ((2.0 * t_ckpt_h * mtbf_cluster_h) ** 0.5) * 60.0


def validate(scenario: Scenario) -> list[Validation]:
    cfg = scenario.config
    job = scenario.job
    out: list[Validation] = []

    # Rule 1 — facility budget vs the design's steady draw.
    steady = steady_facility_mw(scenario)
    budget = cfg.facility.mw_budget
    if steady > budget:
        out.append(Validation(
            rule_id="mw-budget", level="error",
            message=(
                f"Steady training draw ≈ {steady:.2f} MW exceeds the "
                f"{budget:g} MW facility budget. The engine will shed load "
                "(cap GPU clocks) rather than trip the feed — you paid for "
                "GPUs the building cannot power."
            ),
            source="power identity: facility = IT × PUE (engine-enforced)",
        ))
    elif steady > 0.85 * budget:
        out.append(Validation(
            rule_id="mw-budget", level="warning",
            message=(
                f"Steady draw ≈ {steady:.2f} MW is {100 * steady / budget:.0f}% "
                "of the facility budget — no headroom for a warm day. "
                "A PUE excursion will cap the cluster."
            ),
            source="power identity: facility = IT × PUE (engine-enforced)",
        ))
    else:
        out.append(Validation(
            rule_id="mw-budget", level="ok",
            message=f"Steady draw ≈ {steady:.2f} MW fits the {budget:g} MW budget with headroom.",
            source="power identity: facility = IT × PUE (engine-enforced)",
        ))

    # Rule 2 — data platform vs the cluster's appetite.
    n = cfg.compute.racks * cfg.compute.gpus_per_rack
    demand = n * job.data_gbps_per_gpu
    supply = cfg.data.storage_gbps
    if supply < demand:
        out.append(Validation(
            rule_id="storage", level="warning",
            message=(
                f"The cluster wants {demand:.0f} GB/s and the data platform "
                f"delivers {supply:.0f} GB/s — {100 * (1 - supply / demand):.0f}% "
                "of every GPU-hour will be spent waiting for data. The "
                "simulator will show you, not stop you."
            ),
            source="throughput coupling: util = min(1, supply/demand) (engine-enforced)",
        ))
    else:
        out.append(Validation(
            rule_id="storage", level="ok",
            message=(
                f"Data platform ({supply:.0f} GB/s) covers the cluster's "
                f"{demand:.0f} GB/s appetite."
            ),
            source="throughput coupling: util = min(1, supply/demand) (engine-enforced)",
        ))

    # Rule 3 — checkpoint interval vs the Young/Daly optimum.
    opt = optimal_checkpoint_min(scenario)
    interval = cfg.resilience.checkpoint_interval_min
    if opt > 0 and (interval > 5 * opt or interval < 0.2 * opt):
        direction = (
            "rare — every failure rolls back hours of work"
            if interval > opt else
            "frequent — the writes themselves tax every training hour"
        )
        out.append(Validation(
            rule_id="checkpoint", level="warning",
            message=(
                f"Checkpoint interval {interval} min vs an optimum near "
                f"{opt:.0f} min for this cluster's failure rate: too "
                f"{direction}."
            ),
            source="Young/Daly optimum I* = √(2·t_ckpt·MTBF) — estimate",
        ))

    # Rule 4 — oversubscribed training fabric.
    if cfg.fabric.oversubscription > 1.0:
        eff = fabric_efficiency(cfg.fabric.type, cfg.fabric.oversubscription)
        out.append(Validation(
            rule_id="oversub", level="warning",
            message=(
                f"{cfg.fabric.oversubscription:g}:1 oversubscription on a "
                f"training fabric costs ≈{100 * (1 - eff / fabric_efficiency(cfg.fabric.type, 1.0)):.0f}% "
                "of every step — collectives are gated by the thinnest layer. "
                "Storage fabrics tolerate it; training fabrics pay for it."
            ),
            source="estimate — oversubscription penalty in constants.py",
        ))

    return out
