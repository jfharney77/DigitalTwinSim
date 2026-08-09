"""Pure physics engine for the PowerVault ME5 storage simulator.

``simulate(scenario)`` returns the deterministic timestepped trace of the
configured array under the given host load and timed events — the causal
chain this sim exists to teach: drives set the I/O budget, RAID sets the
write tax, controllers set the ceiling, and a failure turns time into
risk. Same purity rule as every twin: no FastAPI, no IO, no timers, no
randomness — the frontend owns the playback clock.

Two identities hold by construction and are asserted in the tests, in the
house style (Alienware's energy identity, IR7000's heat balance):

* **IOPS balance, every tick**: backend disk I/O equals served reads ×
  read cost + served writes × write penalty. The RAID write penalty is
  therefore an asserted fact of the ledger, not a label on a chart.
* **Capacity arithmetic**: raw = usable + protection overhead + spares,
  exactly, for every configuration — the raw→usable→effective identity
  the build plan names.

Time: one tick is ``tick_minutes`` sim-minutes, because storage time is
long — a 20 TB spindle rebuild is measured in days, and the simulator has
to be able to show you all of it.

Deliberate simplifications, stated honestly: one disk group (plus global
spares), averaged reconstruct-on-read cost, an M/M/1-shaped latency knee,
no read/write cache modeling beyond the controllers' flat overhead, and
RAID 10's second failure always hits the degraded mirror — the unlucky
case, so the lesson is the guarantee, not the coin flip.
"""

from __future__ import annotations

from .constants import RISK_FACTOR, value as C
from .models import (
    ArrayConfig,
    FAILURE_TOLERANCE,
    LogEntry,
    Scenario,
    SimState,
    Summary,
    WRITE_PENALTY,
    Workload,
)

# Drawn enclosure: 24 slots + 2 controllers + 2 PSUs + 2 cache modules.
SLOT_COUNT = 24


def drive_iops(drive_type: str) -> float:
    return {
        "hdd-7.2k": C("hdd_72k_iops"),
        "hdd-10k": C("hdd_10k_iops"),
        "ssd": C("ssd_iops"),
    }[drive_type]


def drive_latency_ms(drive_type: str) -> float:
    return {
        "hdd-7.2k": C("hdd_72k_latency_ms"),
        "hdd-10k": C("hdd_latency_ms"),
        "ssd": C("ssd_latency_ms"),
    }[drive_type]


def rebuild_mbps(drive_type: str) -> float:
    return C("ssd_rebuild_mbps") if drive_type == "ssd" else C("hdd_rebuild_mbps")


def capacity_ledger(cfg: ArrayConfig) -> tuple[float, float, float, float]:
    """(raw, usable, overhead, spare) in TB — exact, no rounding drift.

    The identity raw == usable + overhead + spare is asserted per tick in
    the tests; keep this function the only place the arithmetic lives.
    """
    raw = float(cfg.drive_count * cfg.drive_tb)
    spare = float(cfg.spares * cfg.drive_tb)
    group_n = cfg.drive_count - cfg.spares
    if cfg.raid_level in ("1", "10"):
        usable = (group_n // 2) * float(cfg.drive_tb)
    elif cfg.raid_level == "5":
        usable = max(0, group_n - 1) * float(cfg.drive_tb)
    else:  # "6"
        usable = max(0, group_n - 2) * float(cfg.drive_tb)
    overhead = raw - spare - usable
    return raw, usable, overhead, spare


def simulate(scenario: Scenario) -> tuple[list[SimState], list[LogEntry], Summary]:
    cfg = scenario.config
    wl: Workload = scenario.workload.model_copy()
    events = sorted(scenario.events, key=lambda e: e.at_min)

    per_drive = drive_iops(cfg.drive_type)
    base_lat = drive_latency_ms(cfg.drive_type)
    wp = WRITE_PENALTY[cfg.raid_level]
    tolerance = FAILURE_TOLERANCE[cfg.raid_level]
    group_n = cfg.drive_count - cfg.spares
    raw_tb, usable_tb, overhead_tb, spare_tb = capacity_ledger(cfg)
    rebuild_total_gb = cfg.drive_tb * 1000.0

    # Slot layout: data members first, idle spares last, unpopulated after.
    slot_state: list[str] = []
    for i in range(SLOT_COUNT):
        if i < group_n:
            slot_state.append("ok")
        elif i < cfg.drive_count:
            slot_state.append("spare")
        else:
            slot_state.append("empty")

    online = True
    data_lost = False
    offline_reason = ""
    ctrl_alive = cfg.controllers
    failures_outstanding = 0
    rebuild_slot: int | None = None
    rebuild_done_gb = 0.0
    rebuild_queue: list[int] = []
    rebuild_hours_total = 0.0

    trace: list[SimState] = []
    log: list[LogEntry] = []
    ei = 0
    peak_served = 0.0
    peak_latency = 0.0

    tick = scenario.tick_minutes
    steps = min(int(scenario.duration_min / tick), 4000)

    def start_next_rebuild(t: int) -> None:
        nonlocal rebuild_slot, rebuild_done_gb
        if rebuild_slot is None and rebuild_queue:
            rebuild_slot = rebuild_queue.pop(0)
            rebuild_done_gb = 0.0
            slot_state[rebuild_slot] = "rebuilding"
            log.append(LogEntry(
                t=t, severity="info",
                message=f"Rebuild started onto slot {rebuild_slot + 1} — "
                        f"{cfg.drive_tb} TB to reconstruct",
            ))

    for step in range(steps + 1):
        t = step * tick

        # Apply due events.
        while ei < len(events) and events[ei].at_min <= t:
            ev = events[ei]
            ei += 1
            if ev.action == "set-workload" and ev.workload is not None:
                wl = ev.workload.model_copy()
                log.append(LogEntry(t=t, severity="info", message="Workload changed"))
            elif ev.action == "set-offered" and ev.value is not None:
                wl = wl.model_copy(update={"offered_kiops": ev.value})
                log.append(LogEntry(
                    t=t, severity="info",
                    message=f"Offered load set to {ev.value:g} kIOPS",
                ))
            elif ev.action == "fail-drive" and ev.index is not None:
                i = ev.index
                if 0 <= i < SLOT_COUNT and slot_state[i] in ("ok", "rebuilding"):
                    was_rebuilding = slot_state[i] == "rebuilding"
                    slot_state[i] = "failed"
                    if was_rebuilding and rebuild_slot == i:
                        rebuild_slot = None
                        log.append(LogEntry(
                            t=t, severity="warning",
                            message=f"Rebuild target in slot {i + 1} failed — "
                                    "rebuild abandoned",
                        ))
                    else:
                        failures_outstanding += 1
                        if failures_outstanding > tolerance:
                            online = False
                            data_lost = True
                            offline_reason = (
                                f"RAID {cfg.raid_level} lost more members than "
                                "it can tolerate"
                            )
                            extra = (
                                " (RAID 10 could survive a lucky second failure; "
                                "the model takes the unlucky mirror)"
                                if cfg.raid_level == "10" and tolerance == 1 else ""
                            )
                            log.append(LogEntry(
                                t=t, severity="critical",
                                message="Drive failure exceeds RAID tolerance — "
                                        f"array offline, data loss{extra}",
                            ))
                        else:
                            severity = "warning"
                            log.append(LogEntry(
                                t=t, severity=severity,
                                message=f"Drive in slot {i + 1} failed — group "
                                        f"degraded ({failures_outstanding}/"
                                        f"{tolerance} tolerated)",
                            ))
                            # Claim an idle spare, if any.
                            spare_idx = next(
                                (j for j, s in enumerate(slot_state) if s == "spare"),
                                None,
                            )
                            if spare_idx is not None:
                                slot_state[spare_idx] = "queued"
                                rebuild_queue.append(spare_idx)
                                start_next_rebuild(t)
                            else:
                                log.append(LogEntry(
                                    t=t, severity="warning",
                                    message="No hot spare available — the group "
                                            "stays degraded until a drive is "
                                            "replaced",
                                ))
            elif ev.action == "replace-drive" and ev.index is not None:
                i = ev.index
                if 0 <= i < SLOT_COUNT and slot_state[i] == "failed" \
                        and failures_outstanding > 0:
                    slot_state[i] = "queued"
                    rebuild_queue.append(i)
                    start_next_rebuild(t)
                    log.append(LogEntry(
                        t=t, severity="info",
                        message=f"Fresh drive inserted in slot {i + 1}",
                    ))
            elif ev.action == "fail-controller":
                if ctrl_alive > 0:
                    ctrl_alive -= 1
                    if ctrl_alive == 0:
                        online = False
                        offline_reason = "both controllers down"
                        log.append(LogEntry(
                            t=t, severity="critical",
                            message="Last controller failed — array offline",
                        ))
                    else:
                        log.append(LogEntry(
                            t=t, severity="warning",
                            message="Controller failed — survivor owns all "
                                    "volumes; write cache drops to "
                                    "write-through (no mirror partner)",
                        ))
            elif ev.action == "restore-controller":
                if ctrl_alive < cfg.controllers:
                    ctrl_alive += 1
                    log.append(LogEntry(
                        t=t, severity="info",
                        message="Controller restored — cache mirroring resumes",
                    ))

        degraded = failures_outstanding > 0
        rebuilding = rebuild_slot is not None
        serving = group_n - failures_outstanding

        if online and serving > 0:
            budget_total = serving * per_drive
            host_budget = budget_total * (
                1.0 - (C("rebuild_reserve_frac") if rebuilding else 0.0)
            )

            read_cost = (
                C("degraded_read_cost")
                if degraded and cfg.raid_level in ("5", "6") else 1.0
            )
            offered = wl.offered_kiops * 1000.0
            rf = wl.read_pct / 100.0
            reads, writes = offered * rf, offered * (1.0 - rf)
            demand_ops = reads * read_cost + writes * wp
            disk_scale = min(1.0, host_budget / demand_ops) if demand_ops > 0 else 1.0
            fe_cap = ctrl_alive * C("ctrl_cap_kiops") * 1000.0
            fe_scale = min(1.0, fe_cap / offered) if offered > 0 else 1.0
            scale = min(disk_scale, fe_scale)

            served_r, served_w = reads * scale, writes * scale
            served = served_r + served_w
            backend_ops = served_r * read_cost + served_w * wp
            host_util = backend_ops / budget_total if budget_total else 0.0
            util = min(
                1.0,
                host_util + (C("rebuild_reserve_frac") if rebuilding else 0.0),
            )
            saturated = scale < 0.999

            # Latency rides whichever queue is deeper: the drives or the
            # controllers' front end (the all-flash lesson).
            fe_util = (served / fe_cap) if fe_cap > 0 else 1.0
            lat_util = max(util, min(fe_util, 1.0))
            latency = (
                base_lat / (1.0 - min(lat_util, C("util_knee_cap")))
                + C("ctrl_overhead_ms")
                + (C("failover_latency_ms") if ctrl_alive < cfg.controllers else 0.0)
                + (C("degraded_latency_ms") if degraded else 0.0)
            )
            latency = min(latency, C("latency_cap_ms"))
            throughput_mbps = served * wl.block_kb / 1024.0  # IOPS × KB → MB/s

            # Rebuild progress: slower on a busy array.
            if rebuilding:
                rate = rebuild_mbps(cfg.drive_type) * (
                    1.0 - C("rebuild_load_derate") * min(host_util, 1.0)
                )
                rebuild_done_gb += rate * 60.0 * tick / 1000.0
                rebuild_hours_total += tick / 60.0
                if rebuild_done_gb >= rebuild_total_gb and rebuild_slot is not None:
                    slot_state[rebuild_slot] = "ok"
                    failures_outstanding -= 1
                    log.append(LogEntry(
                        t=t, severity="info",
                        message=f"Rebuild complete — slot {rebuild_slot + 1} "
                                "joined the group; protection restored"
                                if failures_outstanding == 0 else
                                f"Rebuild complete — slot {rebuild_slot + 1} "
                                "joined the group",
                    ))
                    rebuild_slot = None
                    start_next_rebuild(t)
                    degraded = failures_outstanding > 0
                    rebuilding = rebuild_slot is not None
                    serving = group_n - failures_outstanding

            if rebuilding and rebuild_slot is not None:
                rate = rebuild_mbps(cfg.drive_type) * (
                    1.0 - C("rebuild_load_derate") * min(host_util, 1.0)
                )
                gb_left = max(0.0, rebuild_total_gb - rebuild_done_gb)
                hours_left = gb_left / (rate * 3.6) if rate > 0 else 0.0
                rebuild_pct = 100.0 * rebuild_done_gb / rebuild_total_gb
            else:
                hours_left = 0.0
                rebuild_pct = 0.0

            if degraded:
                factor = RISK_FACTOR[cfg.raid_level]
                if rebuilding:
                    risk = min(100.0, C("risk_per_hour") * hours_left * factor)
                else:
                    risk = min(100.0, 100.0 * factor)
            else:
                risk = 0.0
        else:
            served_r = served_w = served = 0.0
            backend_ops = 0.0
            read_cost = 1.0
            util = 0.0
            saturated = False
            latency = 0.0
            throughput_mbps = 0.0
            hours_left = 0.0
            rebuild_pct = 0.0
            risk = 100.0 if data_lost else 0.0
            rebuilding = False

        peak_served = max(peak_served, served / 1000.0)
        peak_latency = max(peak_latency, latency)

        # Region states for the enclosure drawing.
        region_states: dict[str, str] = {}
        for i in range(SLOT_COUNT):
            s = slot_state[i]
            region_states[f"drive-{i}"] = (
                "queued" if s == "queued" else s
            ) if online else ("failed" if s == "failed" else "offline")
        region_states["ctrl-a"] = "ok" if ctrl_alive >= 1 else "failed"
        region_states["ctrl-b"] = (
            "empty" if cfg.controllers < 2
            else ("ok" if ctrl_alive >= 2 else "failed")
        )
        cache_mirrored = ctrl_alive == 2
        region_states["cache-a"] = "ok" if cache_mirrored else "write-through"
        region_states["cache-b"] = (
            "empty" if cfg.controllers < 2
            else ("ok" if cache_mirrored else "write-through")
        )
        region_states["psu-a"] = "ok"
        region_states["psu-b"] = "ok"

        trace.append(SimState(
            t=t,
            online=online,
            offered_kiops=round(wl.offered_kiops, 2),
            served_read_kiops=round(served_r / 1000.0, 3),
            served_write_kiops=round(served_w / 1000.0, 3),
            served_kiops=round(served / 1000.0, 3),
            throughput_mbps=round(throughput_mbps, 1),
            latency_ms=round(latency, 2),
            backend_disk_kiops=round(backend_ops / 1000.0, 3),
            read_cost=round(read_cost, 2),
            write_penalty=wp,
            disk_util_pct=round(100.0 * util, 1),
            saturated=saturated,
            controllers_alive=ctrl_alive,
            drives_serving=serving if online else 0,
            drives_failed=failures_outstanding,
            spares_left=sum(1 for s in slot_state if s == "spare"),
            degraded=degraded and online,
            rebuilding=rebuilding and online,
            rebuild_pct=round(rebuild_pct, 2),
            rebuild_hours_remaining=round(hours_left, 2),
            risk_index=round(risk, 1),
            raw_tb=raw_tb,
            usable_tb=usable_tb,
            overhead_tb=overhead_tb,
            spare_tb=spare_tb,
            region_states=region_states,
        ))

    last = trace[-1]
    summary = Summary(
        peak_served_kiops=round(peak_served, 3),
        peak_latency_ms=round(peak_latency, 2),
        steady_served_kiops=last.served_kiops,
        rebuild_hours_total=round(rebuild_hours_total, 2),
        data_lost=data_lost,
        offline_reason=offline_reason,
        usable_tb=usable_tb,
    )
    return trace, log, summary
