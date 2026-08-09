"""Pure physics engine for the Data Domain dedupe simulator.

``simulate(scenario)`` returns the deterministic day-by-day trace of a
backup estate writing into a deduplicating store. Same purity rule as
every twin in this repo: no FastAPI, no IO, no timers, no randomness —
the frontend owns the playback clock, and each ``SimState`` is plain data.

The model is an **analytic chunk-liveness model**, not a hash simulation:
chunk novelty fractions are computed in closed form from the data's own
properties. What emerges — and is asserted in the tests rather than
configured anywhere — is the dedupe ratio:

* **Capacity conservation, every day**: physical(t) = physical(t−1) +
  novel(t) − reclaimed(t), and ratio = logical ÷ physical. The ledger
  balances exactly; the ratio is its quotient, never an input.
* **Generational dedupe**: each retained backup is logically a full, but
  only changed data adds chunks — so the ratio *grows* with retention.
* **Entropy kills the machinery twice**: high entropy alone kills local
  compression (cf → 1); host-side encryption (fresh session keys every
  backup) kills cross-generation dedupe too, and the ratio collapses to
  ~1:1. Ransomware is the adversarial version: the *changed* portion of
  the stream turns to ciphertext, so the stream-entropy instrument fires
  days before any capacity curve bends — the smoke-alarm bridge to the
  DellCyberDetect twin, seen from the backup side.

How the ledger works: the store is the current dataset image plus a
history window of stranded old versions (one entry per retained older
generation). Novel bytes enter the image; replaced bytes migrate from the
image into history; cleaning (GC) pops history entries as generations age
out of retention. Each flow is conserved, so the identity above holds by
construction.
"""

from __future__ import annotations

from .constants import APPLIANCES, value as C
from .models import (
    LogEntry,
    Scenario,
    SimState,
    Summary,
)


def local_compression(entropy_pct: float) -> float:
    """Local (lz) compression factor: lz_max at entropy 0, 1.0 at 100."""
    lz_max = C("lz_max_ratio")
    return 1.0 + (lz_max - 1.0) * (1.0 - entropy_pct / 100.0)


def simulate(scenario: Scenario) -> tuple[list[SimState], list[LogEntry], Summary]:
    ds = scenario.dataset
    appliance = APPLIANCES[scenario.appliance]
    retention = scenario.schedule.retention_days
    events = sorted(scenario.events, key=lambda e: e.at_day)

    full = ds.full_tb
    change = ds.daily_change_pct / 100.0
    entropy = ds.entropy_pct
    base_entropy = ds.entropy_pct
    enc_entropy = C("encrypted_entropy_pct")
    ovh = C("metadata_overhead_fraction")
    chunk_bytes = C("avg_chunk_kb") * 1024.0
    entry_bytes = C("index_entry_bytes")
    ram_fraction = C("ram_resident_fraction")
    knee = C("index_knee_factor")
    alarm_delta = C("entropy_alarm_delta")
    alarm_floor = C("entropy_alarm_floor_pct")
    boost_cap = C("boost_max_speedup")

    # Mutable estate state.
    host_encrypted = False
    rw_rate = 0.0            # ransomware: fraction of dataset newly encrypted per day
    enc_fraction = 0.0       # F: fraction of the dataset sitting encrypted at rest
    # The store ledger (physical TB, before metadata overhead).
    image_clean_phys = 0.0   # current image, clean portion (compresses)
    image_enc_phys = 0.0     # current image, ciphertext portion (cf = 1)
    history: list[float] = []  # stranded old-version physical, one per older gen

    trace: list[SimState] = []
    log: list[LogEntry] = []
    ei = 0
    alarm_day = -1
    capacity_full_day = -1
    warned_capacity = False
    gc_started = False
    peak_entropy = 0.0

    for day in range(scenario.duration_days + 1):
        # Apply due events (they take effect before the day's backup).
        while ei < len(events) and events[ei].at_day <= day:
            ev = events[ei]
            ei += 1
            if ev.action == "set-change-rate" and ev.value is not None:
                change = max(0.0, min(1.0, ev.value / 100.0))
                log.append(LogEntry(day=day, severity="info",
                                    message=f"Daily change rate set to {ev.value:g}%"))
            elif ev.action == "set-entropy" and ev.value is not None:
                entropy = max(0.0, min(100.0, ev.value))
                log.append(LogEntry(day=day, severity="info",
                                    message=f"Dataset entropy set to {ev.value:g}"))
            elif ev.action == "enable-host-encryption":
                if not host_encrypted:
                    host_encrypted = True
                    log.append(LogEntry(
                        day=day, severity="warning",
                        message="Source enabled host-side encryption — every "
                                "backup is now unique ciphertext",
                    ))
            elif ev.action == "disable-host-encryption":
                if host_encrypted:
                    host_encrypted = False
                    log.append(LogEntry(day=day, severity="info",
                                        message="Host-side encryption disabled — "
                                                "next backup re-baselines in clear"))
            elif ev.action == "ransomware-start" and ev.value is not None:
                rw_rate = max(0.0, min(1.0, ev.value / 100.0))
                log.append(LogEntry(
                    day=day, severity="critical",
                    message=f"Ransomware begins encrypting ~{ev.value:g}% of the "
                            "dataset per day (undetected at the source)",
                ))
            elif ev.action == "ransomware-stop":
                rw_rate = 0.0
                log.append(LogEntry(day=day, severity="info",
                                    message="Ransomware halted"))

        cf = local_compression(entropy)
        gc_reclaimed = 0.0
        todays_novel = 0.0
        todays_logical = 0.0
        stream_entropy = 0.0

        if day == 0:
            # Empty store — the state before the first backup.
            pass
        elif day == 1:
            # First full: the whole image is novel.
            todays_logical = full
            if host_encrypted:
                image_enc_phys = full
                todays_novel = full
                stream_entropy = enc_entropy
            else:
                image_clean_phys = (1.0 - enc_fraction) * full / cf
                image_enc_phys = enc_fraction * full
                todays_novel = image_clean_phys + image_enc_phys
                stream_entropy = (
                    (1.0 - enc_fraction) * entropy + enc_fraction * enc_entropy
                )
            log.append(LogEntry(day=day, severity="info",
                                message=f"First full backup: {full:g} TB logical, "
                                        f"{todays_novel:.1f} TB stored"))
        else:
            todays_logical = full
            if host_encrypted:
                # Fresh session keys: nothing matches yesterday's ciphertext.
                stranded = image_clean_phys + image_enc_phys
                history.append(stranded)
                image_clean_phys = 0.0
                image_enc_phys = full
                todays_novel = full
                stream_entropy = enc_entropy
            else:
                clean_frac = 1.0 - enc_fraction
                clean_logical = clean_frac * full
                clean_density = (
                    image_clean_phys / clean_logical if clean_logical > 0 else 0.0
                )
                # Ordinary churn in the clean portion of the estate.
                churn_logical = change * clean_frac * full
                # Ransomware converts clean data to ciphertext.
                newly = min(rw_rate, 1.0 - enc_fraction)
                newly_logical = newly * full

                stranded = (churn_logical + newly_logical) * clean_density
                churn_novel = churn_logical / cf
                rw_novel = newly_logical * 1.0

                image_clean_phys += churn_novel - (churn_logical + newly_logical) * clean_density
                image_enc_phys += newly_logical
                enc_fraction += newly

                history.append(stranded)
                todays_novel = churn_novel + rw_novel
                changed_logical = churn_logical + newly_logical
                stream_entropy = (
                    (churn_logical * entropy + newly_logical * enc_entropy)
                    / changed_logical
                    if changed_logical > 0 else entropy
                )

            # Cleaning: generations aging out of retention free their
            # stranded old versions.
            while len(history) > retention - 1:
                gc_reclaimed += history.pop(0)
            if gc_reclaimed > 0 and not gc_started:
                gc_started = True
                log.append(LogEntry(
                    day=day, severity="info",
                    message=f"Retention window full ({retention} generations) — "
                            "cleaning now reclaims expired chunks",
                ))

        retained = min(day, retention)
        logical = retained * full
        physical_data = image_clean_phys + image_enc_phys + sum(history)
        physical = physical_data * (1.0 + ovh)
        ratio = (logical / physical) if physical > 0 else 0.0
        capacity_used = 100.0 * physical / appliance.usable_tb

        # The smoke alarm: entropy of what *changed* in today's stream.
        peak_entropy = max(peak_entropy, stream_entropy)
        alarm = day >= 1 and (
            stream_entropy >= base_entropy + alarm_delta
            or stream_entropy >= alarm_floor
        )
        if alarm and alarm_day < 0:
            alarm_day = day
            log.append(LogEntry(
                day=day, severity="critical",
                message=f"Entropy alarm: today's changed data reads "
                        f"{stream_entropy:.0f}% random (baseline "
                        f"{base_entropy:g}%) — encrypted-write pattern",
            ))

        if capacity_used >= C("capacity_warn_pct") and not warned_capacity:
            warned_capacity = True
            log.append(LogEntry(
                day=day, severity="warning",
                message=f"Store at {capacity_used:.0f}% of "
                        f"{appliance.usable_tb:g} TB usable",
            ))
        if capacity_used >= 100.0 and capacity_full_day < 0:
            capacity_full_day = day
            log.append(LogEntry(
                day=day, severity="critical",
                message="Store full — in production, backups now fail",
            ))

        # Fingerprint index vs RAM: the ingest knee.
        unique_chunks = physical_data * 1e12 / chunk_bytes
        index_gb = unique_chunks * entry_bytes * ram_fraction / 1e9
        pressure = max(0.0, index_gb / appliance.index_ram_gb - 1.0)
        ingest = appliance.base_ingest_gbps / (1.0 + knee * pressure)
        dedupe_speedup = (
            min(todays_logical / todays_novel, boost_cap)
            if todays_novel > 0 else 1.0
        )
        logical_ingest = ingest * dedupe_speedup
        window_h = (
            todays_logical * 1000.0 / (logical_ingest * 3600.0)
            if logical_ingest > 0 and todays_logical > 0 else 0.0
        )

        region_load = {
            "streams": 1.0 if day >= 1 else 0.0,
            "boost": round(
                min(1.0, todays_novel / todays_logical) if todays_logical > 0 else 0.0, 3,
            ),
            "chunker": 1.0 if day >= 1 else 0.0,
            "index": round(min(1.0, index_gb / appliance.index_ram_gb), 3),
            "store": round(min(1.0, capacity_used / 100.0), 3),
            "cleaner": 1.0 if gc_reclaimed > 0 else 0.0,
        }

        trace.append(SimState(
            day=day,
            generations_retained=retained,
            logical_tb=round(logical, 3),
            physical_tb=round(physical, 3),
            dedupe_ratio=round(ratio, 2),
            todays_logical_tb=round(todays_logical, 3),
            todays_novel_physical_tb=round(todays_novel, 4),
            gc_reclaimed_tb=round(gc_reclaimed, 4),
            capacity_used_pct=round(capacity_used, 2),
            stream_entropy_pct=round(stream_entropy, 1),
            entropy_alarm=alarm,
            host_encrypted=host_encrypted,
            ransomware_active=rw_rate > 0,
            encrypted_fraction_pct=round(100.0 * enc_fraction, 2),
            unique_chunks_m=round(unique_chunks / 1e6, 1),
            index_gb=round(index_gb, 2),
            index_pressure_pct=round(100.0 * pressure, 1),
            ingest_gbps=round(ingest, 3),
            logical_ingest_gbps=round(logical_ingest, 2),
            backup_window_hours=round(window_h, 3),
            region_load=region_load,
        ))

    last = trace[-1]
    summary = Summary(
        final_ratio=last.dedupe_ratio,
        final_logical_tb=last.logical_tb,
        final_physical_tb=last.physical_tb,
        peak_stream_entropy_pct=round(peak_entropy, 1),
        alarm_day=alarm_day,
        capacity_full_day=capacity_full_day,
        final_capacity_used_pct=last.capacity_used_pct,
    )
    return trace, log, summary
