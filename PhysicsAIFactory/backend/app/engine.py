"""Pure roll-up engine for the AI Factory capstone.

``simulate(scenario)`` returns the deterministic hour-by-hour trace of
standing up and running a training factory: procurement → install →
bring-up → training ramp → steady, with checkpoints, deterministic
failures, and timed events. Same purity rule as every twin: no FastAPI,
no IO, no timers, no randomness — failures arrive from MTBF arithmetic,
not dice, so every run is reproducible.

Identities asserted in the tests, house style:

* **Power balance, every tick**: gpu + fabric + storage + other == IT MW,
  and facility MW == IT × PUE. The power cap keeps facility ≤ budget by
  clamping GPU utilization — load shedding as arithmetic, not adjectives.
* **Throughput coupling**: tokens/s = GPUs × per-GPU rate × utilization,
  where utilization = data availability × fabric efficiency × (1 −
  checkpoint tax) × ramp. Undersized storage therefore *emerges* as
  GPU-idle-due-to-data %, the dashboard's hero number.
* **Checkpoint economics**: the tax of writing checkpoints is continuous;
  the cost of *not* writing them arrives as rollbacks when a failure
  rewinds the token counter to the last checkpoint. The interior optimum
  between the two is a tested fact.

Every subsystem is a first-order aggregate on purpose: this app is the
integrated dashboard, and the per-product physics lives (or will live)
in the sibling Physics* apps.
"""

from __future__ import annotations

from .constants import value as C
from .models import (
    LogEntry,
    Scenario,
    SimState,
    Summary,
)

DT_H = 1  # sim timestep, hours — fixed; playback pacing is the frontend's

REGION_IDS = (
    "ops", "compute", "fabric", "data", "power", "cooling", "resilience",
)

REPAIR_H = 24  # hours a failed-GPU batch stays offline (estimate)


def fabric_efficiency(fabric_type: str, oversubscription: float) -> float:
    base = C("fabric_eff_ib") if fabric_type == "quantum-ib" else C("fabric_eff_ethernet")
    eff = base - C("oversub_penalty") * (oversubscription - 1.0)
    return max(0.5, eff)


def simulate(scenario: Scenario) -> tuple[list[SimState], list[LogEntry], Summary]:
    cfg = scenario.config
    job = scenario.job
    events = sorted(scenario.events, key=lambda e: e.at_h)

    n_gpus = cfg.compute.racks * cfg.compute.gpus_per_rack
    peak_w = float(cfg.compute.gpu_peak_w)
    idle_w = C("gpu_idle_fraction") * peak_w

    # Timeline boundaries (hours).
    procure_end = int(C("procure_h"))
    install_end = procure_end + int(round(cfg.compute.racks * C("install_h_per_rack")))
    train_start = install_end + int(C("bringup_h"))

    fab_eff = fabric_efficiency(cfg.fabric.type, cfg.fabric.oversubscription)
    base_pue = C("pue_liquid") if cfg.facility.cooling == "liquid" else C("pue_air")

    interval_h = cfg.resilience.checkpoint_interval_min / 60.0
    restart_h = cfg.resilience.restart_min / 60.0
    mtbf_cluster_h = cfg.resilience.gpu_mtbf_h / max(n_gpus, 1)

    capex_usd_per_h = (
        cfg.compute.racks * cfg.costs.capex_musd_per_rack * 1e6
        / (cfg.costs.amortization_years * 8760.0)
    )

    # Mutable run state.
    storage_frac = 1.0
    warm_pue_delta = 0.0
    gpus_offline = 0
    repairs: list[tuple[int, int]] = []   # (return_h, count)
    tokens_total = 0.0                    # tokens
    tokens_at_ckpt = 0.0
    last_ckpt_index = -1
    next_failure_h = train_start + mtbf_cluster_h
    failures = 0
    cost_usd = 0.0
    power_capped_hours = 0
    was_capped = False
    ttft_h = -1

    trace: list[SimState] = []
    log: list[LogEntry] = []
    ei = 0
    peak_facility = 0.0
    idle_sum = 0.0
    pue_sum = 0.0
    train_ticks = 0

    for t in range(0, scenario.duration_h + 1, DT_H):
        # Apply due events.
        while ei < len(events) and events[ei].at_h <= t:
            ev = events[ei]
            ei += 1
            if ev.action == "degrade-storage" and ev.value is not None:
                storage_frac = max(0.0, min(1.0, ev.value / 100.0))
                log.append(LogEntry(
                    t_h=t, severity="warning",
                    message=f"Data platform degraded to {ev.value:g}% of nominal throughput",
                ))
            elif ev.action == "restore-storage":
                storage_frac = 1.0
                log.append(LogEntry(t_h=t, severity="info",
                                    message="Data platform restored to nominal"))
            elif ev.action == "warm-day" and ev.value is not None:
                warm_pue_delta = ev.value
                log.append(LogEntry(
                    t_h=t, severity="warning",
                    message=f"Warm day — cooling working harder, PUE +{ev.value:g}",
                ))
            elif ev.action == "end-warm-day":
                warm_pue_delta = 0.0
                log.append(LogEntry(t_h=t, severity="info",
                                    message="Weather broke — PUE back to baseline"))
            elif ev.action == "fail-gpus" and ev.value is not None:
                lost = int(ev.value)
                gpus_offline += lost
                repairs.append((t + REPAIR_H, lost))
                failures += 1
                rolled = (tokens_total - tokens_at_ckpt) / 1e9
                tokens_total = tokens_at_ckpt
                log.append(LogEntry(
                    t_h=t, severity="critical",
                    message=(f"{lost} GPUs failed — rolled back {rolled:.2f} B "
                             f"tokens to the last checkpoint; repair ~{REPAIR_H} h"),
                ))

        # Repairs coming back.
        still = []
        for return_h, count in repairs:
            if t >= return_h:
                gpus_offline = max(0, gpus_offline - count)
                log.append(LogEntry(t_h=t, severity="info",
                                    message=f"{count} GPUs repaired and back online"))
            else:
                still.append((return_h, count))
        repairs = still

        # Phase and installed count.
        if t < procure_end:
            phase = "procure"
            installed = 0
        elif t < install_end:
            phase = "install"
            frac = (t - procure_end) / max(install_end - procure_end, 1)
            installed = int(n_gpus * frac)
        elif t < train_start:
            phase = "bringup"
            installed = n_gpus
        else:
            phase = "train"
            installed = n_gpus
        online = max(0, installed - gpus_offline)

        pue = base_pue + warm_pue_delta
        supply_gbps = cfg.data.storage_gbps * storage_frac

        stall_frac = 0.0
        if phase == "train":
            # Deterministic single-GPU failures from the MTBF arithmetic:
            # rollback to the last checkpoint plus a restart stall. The
            # node is swapped from spares, so the count recovers at once.
            if t >= next_failure_h:
                failures += 1
                rolled = (tokens_total - tokens_at_ckpt) / 1e9
                tokens_total = tokens_at_ckpt
                stall_frac = min(1.0, restart_h / DT_H)
                next_failure_h += mtbf_cluster_h
                log.append(LogEntry(
                    t_h=t, severity="warning",
                    message=(f"GPU failure (MTBF arithmetic) — rolled back "
                             f"{rolled:.2f} B tokens, {cfg.resilience.restart_min} min restart"),
                ))

            demand_gbps = online * job.data_gbps_per_gpu
            data_util = 1.0 if demand_gbps <= 0 else min(1.0, supply_gbps / demand_gbps)

            # Checkpoint tax: writing the cluster state at the platform's
            # current throughput, once per interval.
            state_gb = job.state_gb_per_gpu * online
            t_ckpt_h = (state_gb / max(supply_gbps, 1e-9)) / 3600.0
            ckpt_frac = t_ckpt_h / (interval_h + t_ckpt_h)

            ramp_t = (t - train_start) / max(job.ramp_h, 1)
            ramp = min(1.0, C("ramp_floor") + (1.0 - C("ramp_floor")) * ramp_t)

            u0 = data_util * fab_eff * (1.0 - ckpt_frac) * ramp * (1.0 - stall_frac)
        else:
            demand_gbps = 0.0
            data_util = 1.0
            ckpt_frac = 0.0
            u0 = 0.0

        # --- Power, with the facility cap as load shedding ----------------
        fabric_mw = online * C("fabric_kw_per_gpu") / 1000.0
        storage_mw = supply_gbps * C("storage_w_per_gbps") / 1e6
        fixed_mw = fabric_mw + storage_mw
        of = C("other_it_fraction")

        def it_of(u: float) -> tuple[float, float, float]:
            gpu_mw = online * (idle_w + (peak_w - idle_w) * u) / 1e6
            other_mw = of * (gpu_mw + fixed_mw)
            return gpu_mw, other_mw, (gpu_mw + fixed_mw + other_mw)

        gpu_mw, other_mw, it_mw = it_of(u0)
        facility_mw = it_mw * pue
        capped = False
        u = u0
        if facility_mw > cfg.facility.mw_budget and online > 0:
            # Shed load: solve u_max so facility == budget.
            it_allowed = cfg.facility.mw_budget / pue
            gpu_allowed = it_allowed / (1.0 + of) - fixed_mw
            u_max = (gpu_allowed * 1e6 / online - idle_w) / (peak_w - idle_w)
            u_capped = max(0.0, min(u0, u_max))
            if u_capped < u0:
                capped = True
                u = u_capped
                gpu_mw, other_mw, it_mw = it_of(u)
                facility_mw = it_mw * pue
                if phase == "train":
                    power_capped_hours += 1
                    if not was_capped:
                        log.append(LogEntry(
                            t_h=t, severity="warning",
                            message=(f"Facility at budget ({cfg.facility.mw_budget:g} MW) "
                                     "— GPU clocks capped to shed load"),
                        ))
        if was_capped and not capped and phase == "train":
            log.append(LogEntry(t_h=t, severity="info",
                                message="Power cap released — full clocks restored"))
        was_capped = capped

        # --- Tokens ---------------------------------------------------------
        tokens_per_s = online * job.tokens_per_gpu_s * u if phase == "train" else 0.0
        tokens_total += tokens_per_s * 3600.0 * DT_H
        if ttft_h < 0 and tokens_per_s > 0:
            ttft_h = t
            log.append(LogEntry(t_h=t, severity="info",
                                message="First training token — the factory is producing"))

        # Checkpoint bookkeeping (completes once per interval).
        if phase == "train" and interval_h > 0:
            ckpt_index = int((t - train_start) / interval_h)
            if ckpt_index > last_ckpt_index:
                last_ckpt_index = ckpt_index
                tokens_at_ckpt = tokens_total

        # --- Cost -------------------------------------------------------------
        cost_usd += (facility_mw * 1000.0 * cfg.costs.usd_per_kwh + capex_usd_per_h) * DT_H
        usd_per_mtok = (cost_usd / (tokens_total / 1e6)) if tokens_total > 0 else 0.0

        idle_data_pct = (1.0 - data_util) * 100.0
        overhead_pct = (ckpt_frac + stall_frac) * 100.0
        gpu_util_pct = u * 100.0

        if phase == "train":
            idle_sum += idle_data_pct
            pue_sum += pue
            train_ticks += 1
        peak_facility = max(peak_facility, facility_mw)

        # Progress for the ops block: fraction of the arc to steady state.
        if phase == "procure":
            progress = 10.0 * t / max(procure_end, 1)
        elif phase == "install":
            progress = 10.0 + 55.0 * (t - procure_end) / max(install_end - procure_end, 1)
        elif phase == "bringup":
            progress = 65.0 + 25.0 * (t - install_end) / max(train_start - install_end, 1)
        else:
            progress = min(100.0, 90.0 + 10.0 * min(1.0, (t - train_start) / max(job.ramp_h, 1)))

        region_status = {
            "ops": round(progress, 1),
            "compute": round(gpu_util_pct, 1),
            "fabric": round(gpu_util_pct if phase == "train" else 0.0, 1),
            "data": round(
                min(100.0, 100.0 * demand_gbps / supply_gbps) if supply_gbps > 0 else 0.0, 1,
            ),
            "power": round(100.0 * facility_mw / cfg.facility.mw_budget, 1),
            "cooling": round(min(100.0, (pue - 1.0) * 200.0), 1),
            "resilience": round(max(0.0, 100.0 - overhead_pct), 1),
        }

        trace.append(SimState(
            t_h=t,
            phase=phase,
            gpus_installed=installed,
            gpus_online=online,
            tokens_per_s=round(tokens_per_s, 1),
            tokens_total_b=round(tokens_total / 1e9, 3),
            gpu_idle_data_pct=round(idle_data_pct, 1),
            usd_per_mtok=round(usd_per_mtok, 2),
            pue=round(pue, 3),
            facility_mw=round(facility_mw, 4),
            gpu_util_pct=round(gpu_util_pct, 1),
            data_util_pct=round(data_util * 100.0, 1),
            fabric_eff_pct=round(fab_eff * 100.0, 1),
            overhead_pct=round(overhead_pct, 2),
            storage_demand_gbps=round(demand_gbps, 1),
            storage_supply_gbps=round(supply_gbps, 1),
            gpu_mw=round(gpu_mw, 4),
            fabric_mw=round(fabric_mw, 4),
            storage_mw=round(storage_mw, 4),
            other_mw=round(other_mw, 4),
            it_mw=round(it_mw, 4),
            mw_budget=cfg.facility.mw_budget,
            power_capped=capped,
            failures_cum=failures,
            cost_usd_m=round(cost_usd / 1e6, 3),
            region_status=region_status,
        ))

    summary = Summary(
        time_to_first_token_h=ttft_h,
        tokens_total_b=round(tokens_total / 1e9, 3),
        avg_idle_data_pct=round(idle_sum / train_ticks, 1) if train_ticks else 0.0,
        avg_pue=round(pue_sum / train_ticks, 3) if train_ticks else 0.0,
        usd_per_mtok=round(
            (cost_usd / (tokens_total / 1e6)) if tokens_total > 0 else 0.0, 2,
        ),
        peak_facility_mw=round(peak_facility, 3),
        failures=failures,
        power_capped_hours=power_capped_hours,
    )
    return trace, log, summary
