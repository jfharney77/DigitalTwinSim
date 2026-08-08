"""Pure timeline engine for the resilience simulator (physics_specs/05).
Tick = one sim-hour; the timeline scrubber is the UI's centre.

Scope boundary, restated where the code lives: the incident is an
abstract corruption process — a start time and a GB/h rate. Nothing
here models how such an event is caused; everything models whether the
architecture survives it: which copies stay intact (the vault's
operational air gap), how soon anyone knows (detection latency and its
false-alarm price), how fast someone acts (business hours vs 24/7), and
how long recovery takes (RTO = decision + data ÷ throughput, doubled by
a corrupt first restore).

Fort Zero runs in the same trace as an access-graph mode: blast radius
is a reachable-asset count, and the perimeter-vs-zero-trust comparison
is the whole story.
"""

from __future__ import annotations

from .constants import value as C
from .models import (
    LogEntry,
    ResilienceConfig,
    Scenario,
    SimState,
    Summary,
)

DT_H = 1.0


def business_hours(t_h: int) -> bool:
    """Mon–Fri 08:00–18:00; t=0 is Monday 00:00."""
    day = (t_h // 24) % 7
    hour = t_h % 24
    return day < 5 and 8 <= hour < 18


def simulate(scenario: Scenario) -> tuple[list[SimState], list[LogEntry], Summary]:
    cfg = scenario.config
    events = sorted(scenario.events, key=lambda e: e.at_h)
    p = cfg.product
    detection_on = cfg.detection or p == "cyberdetect"

    clean_tb = cfg.estate_tb
    corrupted_tb = 0.0
    incident_active = False
    incident_start = -1
    spread_gbh = 0.0
    slow = False
    contained = False
    contain_time = -1.0
    detected = False
    detect_time = -1.0
    false_alarms = 0
    investigation_h = 0.0
    alerts_backlog = 0.0
    # Backup bookkeeping: list of (taken_at_h, clean: bool, in_vault: bool).
    repo_copies: list[tuple[int, bool]] = []
    vault_copies: list[tuple[int, bool]] = []
    last_vault_sync = 0
    restoring = False
    restore_done_h = -1.0
    restore_from_clean = True
    restore_started = -1.0
    failed_restores = 0
    recovered = False
    rto_actual = 0.0
    rpo_hours = 0.0
    # Fort Zero.
    compromised = False
    compromise_start = -1
    reachable = 0
    stale_grants = 0.0

    trace: list[SimState] = []
    log: list[LogEntry] = []
    ei = 0
    peak_reachable = 0

    steps = int(scenario.duration_h / DT_H)
    for step in range(steps + 1):
        t = int(step * DT_H)

        while ei < len(events) and events[ei].at_h <= t:
            ev = events[ei]
            ei += 1
            if ev.action in ("incident", "slow-incident"):
                incident_active = True
                incident_start = t
                slow = ev.action == "slow-incident"
                spread_gbh = ev.value if ev.value is not None else (
                    20.0 if slow else 500.0
                )
                log.append(LogEntry(
                    t_h=t, severity="critical",
                    message=(
                        f"Incident script: corruption begins, {spread_gbh:g} GB/h"
                        + (" (low and slow)" if slow else "")
                    ),
                ))
            elif ev.action == "contain":
                if incident_active and not contained:
                    contained = True
                    contain_time = t - incident_start
                    log.append(LogEntry(t_h=t, severity="warning",
                                        message="Containment (manual) — spread stopped"))
            elif ev.action == "attempt-restore":
                if not restoring and not recovered:
                    restoring = True
                    restore_started = t
                    # Which copy? Detection names the last clean point. A
                    # loud incident at least dates itself, so the operator
                    # picks a pre-incident copy. A quiet one leaves only
                    # the newest copy — which may be silently corrupt.
                    newest = repo_copies[-1] if repo_copies else None
                    vault_ok = [c for c in vault_copies if c[1]]
                    any_ok = vault_ok or [c for c in repo_copies if c[1]]
                    if detection_on and detected:
                        restore_from_clean = True
                        source = "the identified last-clean point"
                    elif incident_active and not slow:
                        restore_from_clean = bool(any_ok)
                        source = "a pre-incident copy (the onset was obvious)"
                    elif newest is not None and not newest[1]:
                        restore_from_clean = False
                        source = "the newest backup (unverified)"
                    else:
                        restore_from_clean = True
                        source = "the newest backup"
                    if not any_ok:
                        restoring = False
                        log.append(LogEntry(
                            t_h=t, severity="critical",
                            message="No backup exists intact to restore from",
                        ))
                    else:
                        hours = (
                            C("decision_hours")
                            + cfg.estate_tb * 1000.0 / (cfg.restore_gbps * 3600.0)
                        )
                        restore_done_h = t + hours
                        log.append(LogEntry(
                            t_h=t, severity="info",
                            message=f"Restore started from {source} — ≈ {hours:.0f} h of data movement",
                        ))
            elif ev.action == "compromise":
                compromised = True
                compromise_start = t
                log.append(LogEntry(
                    t_h=t, severity="critical",
                    message="One identity marked hostile (abstract) — watch the reachable set",
                ))
            elif ev.action == "access-review":
                pruned = int(stale_grants)
                stale_grants = 0.0
                log.append(LogEntry(
                    t_h=t, severity="info",
                    message=f"Access review — {pruned} stale grants pruned",
                ))

        # --- Corruption spread & containment -------------------------------
        if incident_active and not contained:
            delta = min(spread_gbh / 1000.0 * DT_H, clean_tb)
            clean_tb -= delta
            corrupted_tb += delta

        # --- Backups (per policy) ------------------------------------------
        if t > 0 and t % cfg.backup_every_h == 0:
            is_clean = corrupted_tb < 0.001
            repo_copies.append((t, is_clean))
            if len(repo_copies) > cfg.retention_copies:
                repo_copies.pop(0)
        # The incident also corrupts the *standard repository* — backups
        # reachable from production are encrypted too (spec 05's
        # devastating, common pattern, shown abstractly).
        if incident_active and not contained and repo_copies:
            repo_copies = [(ts, False) for ts, _ in repo_copies]
        # Vault sync: the gap opens briefly on schedule; copies inside are
        # locked immutable and unreachable between windows.
        if cfg.vault and t > 0 and t % cfg.vault_sync_every_h == 0:
            candidates = [c for c in repo_copies if c[1]]
            if candidates:
                vault_copies.append(candidates[-1])
                if len(vault_copies) > cfg.retention_copies:
                    vault_copies.pop(0)
            last_vault_sync = t

        # --- Detection ------------------------------------------------------
        score = min(100.0, 100.0 * corrupted_tb / max(cfg.estate_tb * 0.2, 0.01))
        if detection_on and incident_active and not detected:
            latency_needed = C("detect_threshold_base_h") / cfg.sensitivity
            if slow:
                latency_needed *= 2.0
            if t - incident_start >= latency_needed:
                detected = True
                detect_time = t - incident_start
                log.append(LogEntry(
                    t_h=t, severity="critical",
                    message=(
                        f"Content analysis fired {detect_time:.0f} h after "
                        "onset — last clean recovery point identified"
                    ),
                ))
        # False alarms accrue with sensitivity (the ROC price).
        if detection_on and t > 0 and t % 720 == 0:
            month_alarms = int(
                C("false_alarms_per_month_per_sensitivity") * cfg.sensitivity
            )
            false_alarms += month_alarms
            investigation_h += month_alarms * C("investigation_h_per_alarm")
            if month_alarms:
                log.append(LogEntry(
                    t_h=t, severity="info",
                    message=f"{month_alarms} false alarms this month — "
                            f"{month_alarms * C('investigation_h_per_alarm'):.0f} h investigated",
                ))

        # --- Response: containment via the alert queue ---------------------
        noise_rate = cfg.noise_alerts_day / 24.0
        if cfg.response == "mdr":
            alerts_backlog = 0.0
            if incident_active and detected and not contained:
                if t - incident_start - max(detect_time, 0) >= C("mdr_triage_h"):
                    contained = True
                    contain_time = t - incident_start
                    log.append(LogEntry(
                        t_h=t, severity="warning",
                        message="MDR containment — spread stopped (24/7 triage)",
                    ))
        else:
            if business_hours(t):
                worked = cfg.inhouse_capacity_day / 10.0  # per business hour
                alerts_backlog = max(0.0, alerts_backlog + noise_rate - worked)
                if incident_active and detected and not contained \
                        and alerts_backlog < 1.0:
                    if t - incident_start - max(detect_time, 0) >= C("inhouse_triage_h"):
                        contained = True
                        contain_time = t - incident_start
                        log.append(LogEntry(
                            t_h=t, severity="warning",
                            message="In-house containment — during business hours, after the queue",
                        ))
            else:
                alerts_backlog += noise_rate

        # --- Recovery -------------------------------------------------------
        progress = 0.0
        if restoring:
            span = restore_done_h - restore_started
            progress = min(100.0, 100.0 * (t - restore_started) / span) if span else 100.0
            if t >= restore_done_h:
                if restore_from_clean:
                    recovered = True
                    restoring = False
                    rto_actual = t - restore_started
                    clean_tb = cfg.estate_tb
                    corrupted_tb = 0.0
                    incident_active = False
                    log.append(LogEntry(
                        t_h=t, severity="info",
                        message=f"Recovery complete — RTO {rto_actual:.0f} h",
                    ))
                else:
                    failed_restores += 1
                    have_clean = any(ok for _, ok in repo_copies) or \
                        any(ok for _, ok in vault_copies)
                    if have_clean:
                        restore_from_clean = True
                        restore_done_h = t + C("failed_restore_penalty_h") \
                            + cfg.estate_tb * 1000.0 / (cfg.restore_gbps * 3600.0)
                        log.append(LogEntry(
                            t_h=t, severity="critical",
                            message=(
                                "Restored data was CORRUPT — falling back to an "
                                "older copy and restarting (the restore-and-pray tax)"
                            ),
                        ))
                    else:
                        restoring = False
                        log.append(LogEntry(
                            t_h=t, severity="critical",
                            message="Restored data was CORRUPT and no intact copy remains",
                        ))

        # --- RPO gauge ------------------------------------------------------
        clean_points = [ts for ts, ok in repo_copies if ok] + \
            [ts for ts, ok in vault_copies if ok]
        last_clean_age = float(t - max(clean_points)) if clean_points else float(t)

        # --- Fort Zero access graph ----------------------------------------
        if p == "fortzero":
            stale_grants += cfg.assets * C("grant_decay_per_user_month") / 720.0
            if cfg.review_cadence_days and t > 0 \
                    and t % (cfg.review_cadence_days * 24) == 0:
                stale_grants = 0.0
            if compromised:
                if cfg.architecture == "perimeter":
                    target = int(cfg.assets * C("perimeter_reach_fraction"))
                else:
                    base_reach = cfg.grants_per_user + int(stale_grants / max(cfg.assets, 1))
                    target = max(1, int(base_reach / max(cfg.microseg_segments, 1)) + 1)
                grow = int(C("spread_hops_per_h") * DT_H)
                reachable = min(target, reachable + max(grow, 1))
            peak_reachable = max(peak_reachable, reachable)
        checks = int(
            C("zt_policy_checks") if cfg.architecture == "zerotrust"
            else C("perimeter_policy_checks")
        )

        rto_estimate = (
            rto_actual if recovered else
            C("decision_hours") + cfg.estate_tb * 1000.0 / (cfg.restore_gbps * 3600.0)
        )

        vault_intact = sum(1 for _, ok in vault_copies if ok)
        repo_intact = sum(1 for _, ok in repo_copies if ok)
        backup_storage = (
            len(repo_copies) * cfg.change_gb_day / 1000.0
            * cfg.backup_every_h / 24.0 / cfg.dedupe_ratio
            + cfg.estate_tb / cfg.dedupe_ratio
        )

        region_load = {
            "estate": round(100.0 * corrupted_tb / cfg.estate_tb, 1),
            "backup": round(
                100.0 * (1.0 - repo_intact / max(len(repo_copies), 1)), 1
            ),
            "gap": round(100.0 if (t - last_vault_sync) < 1 else 0.0, 1),
            "vault": round(0.0 if vault_intact else 50.0, 1),
            "analytics": round(score if detection_on else 0.0, 1),
            "queue": round(min(100.0, alerts_backlog * 2), 1),
            "responder": round(100.0 if contained else (50.0 if detected else 0.0), 1),
            "identity": round(100.0 if compromised else 0.0, 1),
            "segments": round(100.0 / max(cfg.microseg_segments, 1), 1),
            "policy": round(min(100.0, checks * 10.0), 1),
        }

        trace.append(SimState(
            t_h=t,
            clean_tb=round(clean_tb, 2),
            corrupted_tb=round(corrupted_tb, 2),
            incident_active=incident_active,
            contained=contained,
            backup_storage_tb=round(backup_storage, 2),
            repo_copies_intact=repo_intact,
            vault_copies_intact=vault_intact,
            last_clean_point_age_h=round(last_clean_age, 1),
            corruption_score=round(score, 1),
            detected=detected,
            detection_latency_h=round(max(detect_time, 0.0), 1),
            false_alarms_cum=false_alarms,
            investigation_hours_cum=round(investigation_h, 1),
            alerts_backlog=int(alerts_backlog),
            time_to_contain_h=round(max(contain_time, 0.0), 1),
            blast_radius_gb=round(corrupted_tb * 1000.0, 1),
            restoring=restoring,
            restore_progress_pct=round(progress, 1),
            rto_hours=round(rto_estimate, 1),
            recovered=recovered,
            failed_restores=failed_restores,
            reachable_assets=reachable,
            policy_checks_per_session=checks,
            stale_grants=int(stale_grants),
            region_load=region_load,
        ))

    last = trace[-1]
    summary = Summary(
        rpo_hours=last.last_clean_point_age_h if not recovered else round(
            max(detect_time, 0.0) + cfg.backup_every_h, 1
        ),
        rto_hours=round(rto_actual if recovered else last.rto_hours, 1),
        blast_radius_gb=last.blast_radius_gb if not recovered else round(
            max(s.blast_radius_gb for s in trace), 1
        ),
        detection_latency_h=last.detection_latency_h,
        time_to_contain_h=last.time_to_contain_h,
        false_alarms=false_alarms,
        data_recovered_tb=round(cfg.estate_tb if recovered else 0.0, 1),
        recovery_succeeded=recovered,
        failed_restores=failed_restores,
        peak_reachable_assets=peak_reachable,
    )
    return trace, log, summary
