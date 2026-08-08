"""Pure engine for the data & observability simulator (physics_specs/06).
Tick = one sim-hour, deterministic throughout.

The pipeline half is theory-of-constraints made visible: throughput =
min(stage rates), the backlog piles up in front of the bottleneck, and
fixing a stage moves the bottleneck instead of removing it. The
GPU-idle gauge closes the loop with PhysicsCompute's data-feed slider.

The CloudIQ half is the meta-instrument: the simulator *knows* the
ground truth of its injected issues, so the anomaly detector's k-knob
is scored — precision, recall, time-to-detect — and the capacity
forecast can be measurably wrong while it relearns a changed slope.
Metric noise is a fixed sinusoid mix; nothing here is random.
"""

from __future__ import annotations

import math

from .constants import value as C
from .models import (
    DataConfig,
    LogEntry,
    Scenario,
    SimState,
    STAGES,
    Summary,
    Workload,
)

DT_H = 1.0


def stage_rates(cfg: DataConfig) -> dict[str, float]:
    rates = {
        "ingest": cfg.ingest_tbh,
        "process": cfg.process_tbh * (
            C("gpu_process_speedup") if cfg.gpu_processing else 1.0
        ),
        "index": cfg.index_tbh,
        "serve": cfg.serve_tbh,
    }
    return rates


def noise(t: int, channel: int) -> float:
    """Deterministic 'noise': a fixed mix of sinusoids per channel."""
    return (
        math.sin(t / 7.3 + channel) * 0.6
        + math.sin(t / 23.1 + channel * 2.7) * 0.4
    ) * C("noise_sigma")


def simulate(scenario: Scenario) -> tuple[list[SimState], list[LogEntry], Summary]:
    cfg = scenario.config.model_copy()
    wl: Workload = scenario.workload.model_copy()
    events = sorted(scenario.events, key=lambda e: e.at_h)

    backlogs = {s: 0.0 for s in STAGES}
    # CloudIQ state.
    array_fill = 55.0
    fill_rate_day = C("baseline_fill_pct_day")
    issues: dict[str, dict] = {}      # name -> {start, detected_at}
    anomalies = 0
    true_pos = 0
    false_pos = 0
    fill_history: list[tuple[int, float]] = []
    expanded = False
    capacity_outage = False

    trace: list[SimState] = []
    log: list[LogEntry] = []
    ei = 0
    throughput_acc = 0.0
    idle_acc = 0.0
    peak_lag = 0.0

    steps = int(scenario.duration_h / DT_H)
    for step in range(steps + 1):
        t = int(step * DT_H)

        while ei < len(events) and events[ei].at_h <= t:
            ev = events[ei]
            ei += 1
            if ev.action == "set-workload" and ev.workload is not None:
                wl = ev.workload.model_copy()
                log.append(LogEntry(t_h=t, severity="info", message="Workload changed"))
            elif ev.action == "fix-stage" and ev.value is not None:
                stage = STAGES[int(ev.value) % len(STAGES)]
                field = f"{stage}_tbh"
                setattr(cfg, field, getattr(cfg, field) * 2.0)
                log.append(LogEntry(
                    t_h=t, severity="info",
                    message=f"Stage '{stage}' doubled — watch where the bottleneck goes",
                ))
            elif ev.action == "toggle-kv":
                cfg.kv_offload = not cfg.kv_offload
                log.append(LogEntry(
                    t_h=t, severity="info",
                    message=f"KV-cache offload {'ON' if cfg.kv_offload else 'OFF'}",
                ))
            elif ev.action == "toggle-gpu-process":
                cfg.gpu_processing = not cfg.gpu_processing
                log.append(LogEntry(
                    t_h=t, severity="info",
                    message=f"GPU processing {'ON' if cfg.gpu_processing else 'OFF'}",
                ))
            elif ev.action == "inject-capacity":
                fill_rate_day = C("issue_fill_pct_day")
                issues["capacity"] = {"start": t, "detected": -1}
                log.append(LogEntry(
                    t_h=t, severity="info",
                    message="(ground truth: an array began filling fast)",
                ))
            elif ev.action == "inject-gray":
                issues["gray"] = {"start": t, "detected": -1}
                log.append(LogEntry(
                    t_h=t, severity="info",
                    message="(ground truth: a switch link began losing 0.1% — status stays green)",
                ))
            elif ev.action == "inject-fan-drift":
                issues["fan"] = {"start": t, "detected": -1}
                log.append(LogEntry(
                    t_h=t, severity="info",
                    message="(ground truth: a fan began a slow drift — green but sick)",
                ))
            elif ev.action == "demand-change":
                fill_rate_day *= 2.0
                log.append(LogEntry(
                    t_h=t, severity="info",
                    message="Demand doubled — watch the forecast take time to catch up",
                ))
            elif ev.action == "expand-capacity":
                array_fill = max(20.0, array_fill - 35.0)
                expanded = True
                log.append(LogEntry(
                    t_h=t, severity="info",
                    message="Capacity expanded — the forecast bought the time to do this",
                ))

        # --- Pipeline half --------------------------------------------------
        rates = stage_rates(cfg)
        flow = wl.raw_arrival_tbh
        for s in STAGES:
            capacity = rates[s]
            demand_in = flow + backlogs[s]
            passed = min(demand_in, capacity)
            backlogs[s] = max(0.0, demand_in - capacity)
            flow = passed
        throughput = flow
        bottleneck = min(STAGES, key=lambda s: rates[s])
        total_backlog = sum(backlogs.values())
        freshness = total_backlog / throughput if throughput > 0 else 0.0
        served = min(wl.gpu_read_demand_tbh, throughput + rates["serve"] * 0.0
                     ) if wl.gpu_read_demand_tbh else 0.0
        served = min(wl.gpu_read_demand_tbh, min(rates["serve"], throughput + 5.0))
        gpu_idle = (
            100.0 * (1.0 - served / wl.gpu_read_demand_tbh)
            if wl.gpu_read_demand_tbh > 0 else 0.0
        )
        base_sessions = int(C("base_sessions"))
        capacity_sessions = int(
            base_sessions * (C("kv_offload_multiplier") if cfg.kv_offload else 1.0)
        )
        long_context = int(wl.inference_sessions_demand * wl.long_context_pct / 100.0)
        active = min(long_context, capacity_sessions)
        tax = C("kv_latency_tax_pct") if (cfg.kv_offload and active > base_sessions) else 0.0
        scan_rate = min(
            wl.analytics_scan_tbh,
            wl.analytics_scan_tbh if cfg.gpu_analytics else wl.analytics_scan_tbh / C("gpu_analytics_speedup"),
        )

        # --- CloudIQ half ---------------------------------------------------
        array_fill = min(100.0, array_fill + fill_rate_day / 24.0 * DT_H)
        if array_fill >= 100.0 and not expanded:
            capacity_outage = True
        fill_history.append((t, array_fill))
        window = [p for p in fill_history if p[0] > t - C("forecast_window_h")]
        if len(window) >= 2:
            (t0, f0), (t1, f1) = window[0], window[-1]
            slope_day = (f1 - f0) / max(t1 - t0, 1) * 24.0
            days_to_full = (100.0 - array_fill) / slope_day if slope_day > 0.01 else 999.0
        else:
            days_to_full = 999.0
        true_days = (100.0 - array_fill) / fill_rate_day if fill_rate_day > 0.01 else 999.0
        forecast_error = abs(min(days_to_full, 999.0) - min(true_days, 999.0))

        # Anomaly detection, scored against ground truth. Each active
        # issue's metric departs from baseline at a known rate; the
        # detector fires when |signal| > k·σ. Deterministic noise crosses
        # low thresholds on a fixed schedule (the false-positive price).
        for name, rec in issues.items():
            if rec["detected"] < 0:
                days_active = (t - rec["start"]) / 24.0
                signal = days_active * C("issue_signal_sigma")
                if signal > cfg.anomaly_k:
                    rec["detected"] = t
                    anomalies += 1
                    true_pos += 1
                    log.append(LogEntry(
                        t_h=t, severity="warning",
                        message=(
                            f"Anomaly flagged: '{name}' — "
                            f"{t - rec['start']} h after onset (trend, not status)"
                        ),
                    ))
        # False positives: deterministic noise excursions beat low k on a
        # fixed cadence — the lower the k, the more often.
        fp_every_h = int(48 * cfg.anomaly_k)
        if t > 0 and t % fp_every_h == 0:
            anomalies += 1
            false_pos += 1
            log.append(LogEntry(
                t_h=t, severity="info",
                message="Anomaly flagged: (noise excursion — investigated, benign)",
            ))

        detected_n = sum(1 for r in issues.values() if r["detected"] >= 0)
        active_issues = len(issues)
        precision = 100.0 * true_pos / anomalies if anomalies else 100.0
        recall = 100.0 * detected_n / active_issues if active_issues else 100.0
        detect_delays = [
            r["detected"] - r["start"] for r in issues.values() if r["detected"] >= 0
        ]
        mttd = sum(detect_delays) / len(detect_delays) if detect_delays else 0.0

        # Health score: a composed opinion.
        cap_risk = max(0.0, array_fill - 70.0) / 30.0 * 100.0
        perf_risk = 40.0 if ("gray" in issues and issues["gray"]["detected"] < 0) else (
            20.0 if "gray" in issues else 0.0
        )
        conf_risk = 30.0 if "fan" in issues else 0.0
        wsum = max(cfg.weight_capacity + cfg.weight_performance + cfg.weight_config, 1)
        worst = 100.0 - (
            cap_risk * cfg.weight_capacity
            + perf_risk * cfg.weight_performance
            + conf_risk * cfg.weight_config
        ) / wsum
        mean_score = (worst + 100.0) / 2.0
        status_green = True  # the device lights never admit the injected issues

        region_load = {
            "sources": round(min(100.0, wl.raw_arrival_tbh / max(rates["ingest"], 0.1) * 100.0), 1),
            "ingest": round(min(200.0, (wl.raw_arrival_tbh + backlogs["ingest"]) / max(rates["ingest"], 0.1) * 100.0), 1),
            "process": round(min(200.0, (wl.raw_arrival_tbh + backlogs["process"]) / max(rates["process"], 0.1) * 100.0), 1),
            "index": round(min(200.0, (wl.raw_arrival_tbh + backlogs["index"]) / max(rates["index"], 0.1) * 100.0), 1),
            "serve": round(min(200.0, wl.gpu_read_demand_tbh / max(rates["serve"], 0.1) * 100.0), 1),
            "gpus": round(gpu_idle, 1),
            "kvcache": round(100.0 * active / max(capacity_sessions, 1), 1),
            "analytics": round(min(100.0, scan_rate / max(wl.analytics_scan_tbh, 0.1) * 100.0), 1),
            "fleet": round(100.0 - worst, 1),
            "detector": round(min(100.0, recall), 1),
            "forecast": round(min(100.0, forecast_error * 10.0), 1),
            "console": round(100.0 - mean_score, 1),
        }

        trace.append(SimState(
            t_h=t,
            stage_rates_tbh={k: round(v, 1) for k, v in rates.items()},
            stage_backlogs_tb={k: round(v, 1) for k, v in backlogs.items()},
            bottleneck=bottleneck,
            throughput_tbh=round(throughput, 2),
            freshness_lag_h=round(freshness, 1),
            gpu_idle_due_to_data_pct=round(gpu_idle, 1),
            sessions_capacity=capacity_sessions,
            sessions_active=active,
            token_latency_tax_pct=round(tax, 1),
            analytics_scan_rate_tbh=round(scan_rate, 1),
            health_score_worst=round(worst, 1),
            health_score_mean=round(mean_score, 1),
            anomalies_flagged_cum=anomalies,
            true_positives_cum=true_pos,
            false_positives_cum=false_pos,
            precision_pct=round(precision, 1),
            recall_pct=round(recall, 1),
            issues_active=active_issues,
            issues_detected=detected_n,
            mttd_h=round(mttd, 1),
            array_fill_pct=round(array_fill, 2),
            days_to_full_forecast=round(min(days_to_full, 999.0), 1),
            forecast_error_days=round(min(forecast_error, 999.0), 1),
            device_status_all_green=status_green,
            region_load=region_load,
        ))

        throughput_acc += throughput
        idle_acc += gpu_idle
        peak_lag = max(peak_lag, freshness)

    n = len(trace)
    last = trace[-1]
    summary = Summary(
        mean_throughput_tbh=round(throughput_acc / n, 2),
        final_bottleneck=last.bottleneck,
        peak_freshness_lag_h=round(peak_lag, 1),
        mean_gpu_idle_pct=round(idle_acc / n, 1),
        precision_pct=last.precision_pct,
        recall_pct=last.recall_pct,
        mttd_h=last.mttd_h,
        capacity_outage=capacity_outage,
    )
    return trace, log, summary
