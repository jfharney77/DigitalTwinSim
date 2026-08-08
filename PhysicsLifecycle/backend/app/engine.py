"""Pure engine for the telecom & sustainability simulator
(physics_specs/08). Tick = one sim-day.

Telecom half: the integration-effort model is the product — DIY sites
pay validation hours and hit deterministic version mismatches; Blocks
sites deploy as tested bundles. The heatwave event separates
extended-temperature fleets from standard ones, and coverage counts
subscribers, not servers.

Circular half: the design decisions are made once, then eight years of
consequences are accounted. The ledger closes by construction — total
carbon = embodied + use, every tick — and the headline instrument is
carbon per useful-year. Refurbishability decides whether the device
gets a second life or becomes e-waste; a sealed design converts every
mid-life event into a whole new device's embodied carbon.
"""

from __future__ import annotations

from .constants import value as C
from .models import (
    LifecycleConfig,
    LogEntry,
    Scenario,
    SimState,
    Summary,
)

DT_D = 1.0

GRID_KEY = {
    "clean": "grid_clean_kg_kwh",
    "average": "grid_average_kg_kwh",
    "coal": "grid_coal_kg_kwh",
}


def disassembly_minutes(cfg: LifecycleConfig) -> float:
    """A derived score: minutes with a screwdriver."""
    minutes = 45.0
    if cfg.battery_replaceable:
        minutes -= 12
    if cfg.ram_socketed:
        minutes -= 8
    if cfg.ports_modular:
        minutes -= 10
    return minutes


def refurb_success(cfg: LifecycleConfig) -> float:
    bonus = sum([
        cfg.battery_replaceable, cfg.ram_socketed, cfg.ports_modular,
    ]) * C("refurb_modular_bonus")
    return min(0.95, C("refurb_base_success") + bonus)


def simulate(scenario: Scenario) -> tuple[list[SimState], list[LogEntry], Summary]:
    cfg = scenario.config
    events = sorted(scenario.events, key=lambda e: e.at_d)
    p = cfg.product
    telecom = p == "telecomblocks"

    # Telecom state.
    sites = cfg.sites if telecom else 0
    sites_down = 0
    down_until: list[float] = []
    hours_cum = 0.0
    mismatches = 0
    outage_site_hours = 0.0
    site_hours = 0.0
    heat_until = -1.0
    heat_peak = 22.0
    updating_until = -1.0
    min_coverage = 100.0

    # Circular state.
    embodied = C("embodied_kg") * (
        1.0 - (C("recycled_chassis_saving") if cfg.chassis_recycled else 0.0)
    )
    embodied_cum = embodied if not telecom else 0.0
    use_cum = 0.0
    devices = 1 if not telecom else 0
    ewaste = 0.0
    tco = C("device_cost_usd") if not telecom else 0.0
    device_alive = True
    second_life = False
    grid_kg_kwh = C(GRID_KEY[cfg.grid])
    life_events_done: set[str] = set()

    trace: list[SimState] = []
    log: list[LogEntry] = []
    ei = 0

    steps = int(scenario.duration_d / DT_D)
    for step in range(steps + 1):
        t = int(step * DT_D)

        while ei < len(events) and events[ei].at_d <= t:
            ev = events[ei]
            ei += 1
            if ev.action == "deploy-sites" and ev.value is not None and telecom:
                n = int(ev.value)
                sites += n
                if cfg.deploy_mode == "blocks":
                    hours_cum += n * C("blocks_deploy_h_site")
                    log.append(LogEntry(
                        t_d=t, severity="info",
                        message=(
                            f"{n} sites deployed from validated bundles — "
                            f"{n * C('blocks_deploy_h_site'):.0f} h"
                        ),
                    ))
                else:
                    hours_cum += n * C("diy_validate_h_site")
                    failed = n // int(C("diy_mismatch_every_n"))
                    mismatches += failed
                    hours_cum += failed * C("mismatch_penalty_h")
                    outage_site_hours += failed * C("mismatch_outage_h")
                    log.append(LogEntry(
                        t_d=t, severity="warning" if failed else "info",
                        message=(
                            f"{n} DIY sites: {n * C('diy_validate_h_site'):.0f} h of "
                            f"validation, {failed} version mismatches "
                            f"(+{failed * C('mismatch_penalty_h'):.0f} h, outages)"
                        ),
                    ))
            elif ev.action == "heatwave" and ev.value is not None and telecom:
                heat_until = t + 3
                heat_peak = ev.value
                if not cfg.extended_temp and ev.value > C("standard_temp_limit_c"):
                    lost = int(sites * C("heatwave_site_fraction"))
                    sites_down += lost
                    mttr = (
                        C("site_mttr_remote_h") if cfg.remote_remediation
                        else C("site_mttr_truck_h")
                    )
                    outage_site_hours += lost * (72.0 + mttr)
                    down_until.append(t + 3 + mttr / 24.0)
                    log.append(LogEntry(
                        t_d=t, severity="critical",
                        message=(
                            f"Heatwave {ev.value:g} °C — {lost} standard-temp "
                            "sites over their ceiling and dark"
                        ),
                    ))
                else:
                    log.append(LogEntry(
                        t_d=t, severity="info",
                        message=(
                            f"Heatwave {ev.value:g} °C — extended-temp fleet "
                            "rides it out"
                            if cfg.extended_temp else
                            f"Heatwave {ev.value:g} °C — under the ceiling"
                        ),
                    ))
            elif ev.action == "bundle-update" and telecom:
                if cfg.deploy_mode == "blocks" and cfg.spare_capacity:
                    updating_until = t + 2
                    hours_cum += sites * 0.1
                    log.append(LogEntry(
                        t_d=t, severity="info",
                        message="Bundle update rolling with N+1 site logic — no coverage loss",
                    ))
                else:
                    updating_until = t + 7
                    hours_cum += sites * (0.5 if cfg.deploy_mode == "blocks" else 1.5)
                    outage_site_hours += sites * 0.5
                    log.append(LogEntry(
                        t_d=t, severity="warning",
                        message="Piecemeal update — brief per-site outages fleet-wide",
                    ))

        if telecom:
            # Repairs come due: when every recorded repair time has
            # passed, the downed sites return together.
            if down_until and all(d <= t for d in down_until):
                if sites_down:
                    log.append(LogEntry(
                        t_d=t, severity="info",
                        message=f"{sites_down} sites repaired and back on air",
                    ))
                sites_down = 0
                down_until = []
            ambient = heat_peak if t <= heat_until else 22.0
            up = sites - sites_down
            coverage = 100.0 * up / sites if sites else 0.0
            min_coverage = min(min_coverage, coverage)
            site_hours += sites * 24.0
            availability = 100.0 * (1.0 - outage_site_hours / site_hours) \
                if site_hours else 100.0
            subscribers = up * cfg.subscribers_per_site_k
        else:
            ambient = 22.0
            up = 0
            coverage = 0.0
            availability = 100.0
            subscribers = 0.0

            # --- Circular lifecycle -------------------------------------
            if device_alive:
                use_cum += cfg.annual_kwh / 365.0 * grid_kg_kwh

            def event_due(name: str, day_const: str) -> bool:
                return (
                    name not in life_events_done
                    and t >= C(day_const)
                    and device_alive
                )

            def resolve(name: str, repairable: bool, part_kg: float,
                        label: str) -> None:
                nonlocal embodied_cum, devices, ewaste, tco, device_alive
                life_events_done.add(name)
                if repairable:
                    embodied_cum += part_kg
                    tco += C("part_cost_usd")
                    log.append(LogEntry(
                        t_d=t, severity="info",
                        message=f"{label} — replaceable part fitted "
                                f"(+{part_kg:g} kgCO2e); the device lives on",
                    ))
                else:
                    ewaste += C("laptop_mass_kg")
                    devices += 1
                    embodied_cum += embodied
                    tco += C("device_cost_usd")
                    log.append(LogEntry(
                        t_d=t, severity="critical",
                        message=(
                            f"{label} — sealed design: whole-device "
                            f"replacement (+{embodied:.0f} kgCO2e embodied, "
                            "again)"
                        ),
                    ))

            if event_due("repair", "repair_day"):
                resolve("repair", cfg.ports_modular, C("repair_part_kg"),
                        "A port broke")
            if event_due("battery", "battery_wear_day"):
                resolve("battery", cfg.battery_replaceable,
                        C("battery_part_kg"), "The battery wore out")
            if event_due("ram", "ram_short_day"):
                resolve("ram", cfg.ram_socketed, C("ram_part_kg"),
                        "The RAM became insufficient")

            # First-owner end: refurbish or recycle.
            first_owner_end = cfg.first_owner_years * 365
            if "handoff" not in life_events_done and t >= first_owner_end:
                life_events_done.add("handoff")
                if refurb_success(cfg) >= 0.5:
                    second_life = True
                    log.append(LogEntry(
                        t_d=t, severity="info",
                        message=(
                            "First owner done — refurbished for a second "
                            f"life (success odds {100 * refurb_success(cfg):.0f}%)"
                        ),
                    ))
                else:
                    device_alive = False
                    ewaste += C("laptop_mass_kg")
                    log.append(LogEntry(
                        t_d=t, severity="warning",
                        message=(
                            "First owner done — refurb uneconomic for this "
                            f"design ({100 * refurb_success(cfg):.0f}% odds); "
                            "recycled"
                        ),
                    ))

        useful_years = max(t / 365.0, 0.01) if (device_alive or telecom) else \
            max(cfg.first_owner_years, 0.01)
        total_carbon = embodied_cum + use_cum
        cpy = total_carbon / useful_years if not telecom else 0.0

        region_load = {
            "coverage": round(100.0 - coverage if telecom else 0.0, 1),
            "sites": round(100.0 * sites_down / max(sites, 1) if telecom else 0.0, 1),
            "integration": round(min(100.0, hours_cum / 50.0) if telecom else 0.0, 1),
            "environment": round(
                min(100.0, max(0.0, (ambient - 22.0) * 3.0)) if telecom else 0.0, 1
            ),
            "device": round(0.0 if device_alive else 100.0, 1),
            "battery": round(
                100.0 if ("battery" in life_events_done and not cfg.battery_replaceable)
                else (40.0 if "battery" in life_events_done else 0.0), 1
            ),
            "materials": round(min(100.0, ewaste * 25.0), 1),
            "grid": round(grid_kg_kwh / C("grid_coal_kg_kwh") * 100.0, 1),
            "ledger": round(min(100.0, cpy), 1),
            "secondlife": round(100.0 if second_life else 0.0, 1),
        }

        trace.append(SimState(
            t_d=t,
            sites_total=sites,
            sites_up=up,
            coverage_pct=round(coverage, 2),
            subscribers_served_k=round(subscribers, 1),
            integration_hours_cum=round(hours_cum, 1),
            mismatch_events_cum=mismatches,
            availability_pct=round(availability, 4),
            ambient_c=round(ambient, 1),
            updating=t <= updating_until,
            embodied_kg_cum=round(embodied_cum, 1),
            use_kg_cum=round(use_cum, 1),
            total_carbon_kg=round(total_carbon, 1),
            useful_years=round(useful_years, 2),
            carbon_per_useful_year=round(cpy, 1),
            devices_consumed=devices,
            ewaste_kg=round(ewaste, 1),
            tco_usd=round(tco, 0),
            device_alive=device_alive,
            on_second_life=second_life,
            disassembly_minutes=round(disassembly_minutes(cfg), 0),
            region_load=region_load,
        ))

    last = trace[-1]
    summary = Summary(
        integration_hours=last.integration_hours_cum,
        mismatch_events=last.mismatch_events_cum,
        availability_pct=last.availability_pct,
        min_coverage_pct=round(min_coverage, 2),
        total_carbon_kg=last.total_carbon_kg,
        carbon_per_useful_year=last.carbon_per_useful_year,
        devices_consumed=last.devices_consumed,
        ewaste_kg=last.ewaste_kg,
        tco_usd=last.tco_usd,
        got_second_life=last.on_second_life,
    )
    return trace, log, summary
