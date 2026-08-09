"""Pure physics engine for the UltraSharp display simulator.

``simulate(scenario)`` returns the deterministic 1 s-timestep trace of one
monitor under brightness, content, dimming, hub, and standby events. Same
purity rule as every twin: no FastAPI, no IO, no timers, no randomness.

The whole model is one honest equation and its consequences:

    backlight W = max backlight W × brightness × lit fraction

where the lit fraction is the *content's* only when the panel can dim
locally (mini-LED zones). An edge-lit strip lights the full field no
matter what the picture shows, so its lit fraction is pinned at 1.0 —
which is why dark mode saves real watts on one panel class and almost
none on the other.

Acoustics: this product's fan curve is a flat line at zero. There are no
fans, no pumps, and nothing to spin — the M12 module's degenerate case,
recorded here as a sentence rather than pretending to be a gauge.

Identities asserted in the tests, house style:

* **Power balance, every tick**: electronics + backlight + hub delivered
  + hub loss == DC, and AC == DC ÷ PSU efficiency.
* **Heat vs delivery**: heat == DC − hub-delivered watts. Power a laptop
  through the hub and the wall meter jumps, but most of those watts leave
  over the cable instead of warming the room.
* **Carbon closure** (in the Summary): embodied + use == lifetime, and
  the shares sum to 100 — the Circular Design rule, one product at a time.
"""

from __future__ import annotations

from .constants import value as C
from .models import (
    CarbonBreakdown,
    ContentProfile,
    DisplayConfig,
    LogEntry,
    Scenario,
    SimState,
    Summary,
)

DT = 1.0  # sim timestep, seconds — playback pacing is the frontend's


def _lit_fraction(content: ContentProfile) -> float:
    return {
        "dark": C("lit_dark"),
        "mixed": C("lit_mixed"),
        "bright": C("lit_bright"),
        "hdr": C("lit_hdr"),
    }[content]


def backlight_w(cfg: DisplayConfig, content: ContentProfile,
                brightness_pct: float, dimming: bool) -> tuple[float, float]:
    """(backlight watts, effective lit fraction) for the current frame."""
    mini = cfg.model == "miniled-32"
    max_w = C("mini_backlight_max_w") if mini else C("edge_backlight_max_w")
    content_lit = _lit_fraction(content)

    if mini and dimming:
        lit = max(C("zone_floor_fraction"), content_lit)
    else:
        # One global strip (or dimming off): the whole field is driven.
        lit = 1.0

    drive = brightness_pct / 100.0
    if content == "hdr":
        # HDR overdrives whatever is lit, regardless of the SDR brightness
        # slider — highlights are mastered to the panel's peak.
        drive = C("hdr_boost") if mini else C("hdr_boost_edge")
        if not (mini and dimming):
            lit = 1.0
    return max_w * drive * lit, (content_lit if (mini and dimming) else 1.0)


def _electronics_w(cfg: DisplayConfig) -> float:
    return (
        C("mini_electronics_w") if cfg.model == "miniled-32"
        else C("edge_electronics_w")
    )


def simulate(scenario: Scenario) -> tuple[list[SimState], list[LogEntry], Summary]:
    cfg = scenario.config
    life = scenario.lifecycle
    events = sorted(scenario.events, key=lambda e: e.at_s)

    on = True
    brightness = float(cfg.brightness_pct)
    content: ContentProfile = cfg.content
    dimming = cfg.local_dimming
    hub_out = float(cfg.hub_laptop_w)

    trace: list[SimState] = []
    log: list[LogEntry] = []
    cumulative_wh = 0.0
    ei = 0
    n_ticks = int(scenario.duration_s / DT)

    zones = int(C("mini_zones"))
    psu_eff = C("psu_efficiency")
    hub_eff = C("hub_efficiency")

    for tick in range(n_ticks + 1):
        t = int(tick * DT)

        while ei < len(events) and events[ei].at_s <= t:
            e = events[ei]
            ei += 1
            if e.action == "set-brightness" and e.value is not None:
                brightness = max(0.0, min(100.0, e.value))
                log.append(LogEntry(t=t, severity="info",
                                    message=f"Brightness set to {brightness:.0f}%"))
            elif e.action == "set-content" and e.content is not None:
                content = e.content
                log.append(LogEntry(t=t, severity="info",
                                    message=f"Content switched to {content}"))
            elif e.action == "set-dimming" and e.value is not None:
                dimming = bool(e.value)
                log.append(LogEntry(t=t, severity="info",
                                    message=("Local dimming on" if dimming
                                             else "Local dimming off")))
            elif e.action == "hub-plug" and e.value is not None:
                hub_out = max(0.0, min(C("hub_max_w"), e.value))
                log.append(LogEntry(t=t, severity="info",
                                    message=f"Laptop docked — {hub_out:.0f} W over USB-C"))
            elif e.action == "hub-unplug":
                hub_out = 0.0
                log.append(LogEntry(t=t, severity="info",
                                    message="Laptop undocked"))
            elif e.action == "standby":
                on = False
                log.append(LogEntry(t=t, severity="info",
                                    message="Display entered standby"))
            elif e.action == "wake":
                on = True
                log.append(LogEntry(t=t, severity="info", message="Display woke"))

        if on:
            electronics = _electronics_w(cfg)
            bl, content_lit = backlight_w(cfg, content, brightness, dimming)
            out = hub_out
            hub_loss = out / hub_eff - out if out > 0 else 0.0
            dc = electronics + bl + out + hub_loss
            ac = dc / psu_eff
            mini_dimming = cfg.model == "miniled-32" and dimming
            lit = max(C("zone_floor_fraction"), content_lit) if mini_dimming else 1.0
            zones_lit = round(zones * lit) if cfg.model == "miniled-32" else 0
        else:
            electronics = bl = out = hub_loss = dc = 0.0
            ac = C("standby_w")
            lit = 0.0
            zones_lit = 0

        cumulative_wh += ac * DT / 3600.0
        trace.append(SimState(
            t=t, on=on, brightness_pct=int(brightness), content=content,
            electronics_w=round(electronics, 2), backlight_w=round(bl, 2),
            hub_out_w=round(out, 2), hub_loss_w=round(hub_loss, 2),
            dc_power_w=round(dc, 2), ac_power_w=round(ac, 2),
            heat_w=round(dc - out, 2),
            lit_fraction=round(lit, 4), zones_lit=zones_lit,
            cumulative_wh=round(cumulative_wh, 4),
        ))

    # --- Lifetime carbon, from the steady on-state of this scenario --------
    on_states = [s for s in trace if s.on]
    steady = on_states[-1] if on_states else trace[-1]
    avg_on_w = (
        sum(s.ac_power_w for s in on_states) / len(on_states)
        if on_states else 0.0
    )
    on_hours = life.hours_per_day * life.days_per_year
    standby_hours = max(0.0, 24 * life.days_per_year - on_hours)
    annual_kwh = (
        avg_on_w * on_hours + C("standby_w") * standby_hours
    ) / 1000.0
    use_kg = annual_kwh * life.service_years * life.grid_kgco2_per_kwh
    embodied = (
        C("embodied_mini_kg") if cfg.model == "miniled-32"
        else C("embodied_edge_kg")
    )
    lifetime = embodied + use_kg
    carbon = CarbonBreakdown(
        embodied_kg=round(embodied, 1),
        use_kg=round(use_kg, 1),
        lifetime_kg=round(embodied + round(use_kg, 1), 1),
        embodied_pct=round(100.0 * embodied / lifetime, 1),
        use_pct=round(100.0 - 100.0 * embodied / lifetime, 1),
        annual_kwh=round(annual_kwh, 1),
        avg_on_power_w=round(avg_on_w, 1),
    )

    summary = Summary(
        peak_ac_w=round(max(s.ac_power_w for s in trace), 2),
        steady_ac_w=round(steady.ac_power_w, 2),
        standby_w=C("standby_w"),
        carbon=carbon,
    )
    return trace, log, summary
