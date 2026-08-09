"""Pure physics engine for the rack PDU & UPS simulator.

``simulate(scenario)`` returns the deterministic timestepped trace of a
rack's power layer: loads on three phase feeds behind per-phase breakers,
all fed by one rack UPS whose battery has honestly aged. Same purity rule
as every twin in this repo: no FastAPI, no IO, no timers, no randomness —
the frontend owns the playback clock, and each ``SimState`` is plain data.

Identities that hold by construction and are asserted in the tests, in
the house style of the Alienware energy identity and the IR7000 heat
balance:

* **Power conservation, every tick**: the live outlet watts sum exactly
  to the per-phase watts, which sum exactly to the PDU input. On utility,
  wall draw = PDU input ÷ pass-through efficiency (+ charger); on
  battery, battery output × inverter efficiency = PDU input.
* **The runtime gap is arithmetic, not drama**: the front panel predicts
  runtime from the battery's *nameplate* watt-hours until a self-test has
  measured the truth; the engine discharges the *faded* watt-hours. The
  ratio between the two runtimes is exactly the capacity fraction the
  fade model computed — the classic outage post-mortem, simulated.

The model is simplified and legible on purpose: a linear fade rate with
an exponential temperature multiplier, an I²t breaker curve, one lumped
load per slot. Correct relationships and orders of magnitude, not an
electrical-engineering tool.
"""

from __future__ import annotations

from .constants import value as C
from .models import (
    LogEntry,
    Phase,
    RackConfig,
    Scenario,
    SimState,
    Summary,
)

DT = 1.0  # sim timestep, seconds — fixed; playback pacing is the frontend's

PHASES: tuple[Phase, ...] = ("A", "B", "C")

RUNTIME_CAP_MIN = 9999.0


def battery_capacity_fraction(cfg: RackConfig, room_temp_c: float) -> float:
    """The fade model: a linear per-year loss whose clock runs faster in a
    hot room. VRLA ages twice as fast per +10 °C above 25 °C; lithium is
    markedly gentler. Floored — a battery below the floor would fail its
    self-test outright."""
    if cfg.ups_chemistry == "vrla":
        rate = C("vrla_fade_per_year")
        doubling = C("vrla_temp_doubling_c")
    else:
        rate = C("lithium_fade_per_year")
        doubling = C("lithium_temp_doubling_c")
    accel = 2.0 ** ((room_temp_c - C("reference_temp_c")) / doubling)
    equivalent_years = cfg.ups_age_years * accel
    return max(C("battery_capacity_floor"), 1.0 - rate * equivalent_years)


def _runtime_min(available_wh: float, load_w: float) -> float:
    if load_w <= 0.5:
        return RUNTIME_CAP_MIN
    return min(RUNTIME_CAP_MIN, available_wh * C("inverter_efficiency") / load_w * 60.0)


def simulate(scenario: Scenario) -> tuple[list[SimState], list[LogEntry], Summary]:
    cfg = scenario.config
    env = scenario.environment
    events = sorted(scenario.events, key=lambda e: e.at_s)

    volts = C("phase_voltage_v")
    pf = C("power_factor")
    rating_amps = float(cfg.breaker_amps)
    inverter_eff = C("inverter_efficiency")
    pass_eff = C("ups_pass_efficiency")

    # Battery truth vs battery belief.
    capacity_fraction = battery_capacity_fraction(cfg, env.room_temp_c)
    effective_wh = cfg.ups_nameplate_wh * capacity_fraction
    remaining_wh = effective_wh * cfg.start_charge_pct / 100.0

    # Mutable machine state.
    phase_of: list[Phase] = [ld.phase for ld in cfg.loads]
    watts_of: list[float] = [float(ld.power_w) for ld in cfg.loads]
    utility_on = True
    rack_powered = True
    self_tested = False
    tripped: set[Phase] = set()
    trip_heat: dict[Phase, float] = {p: 0.0 for p in PHASES}
    dark_reason = ""

    trace: list[SimState] = []
    log: list[LogEntry] = []
    ei = 0
    peak_input = 0.0
    worst_imbalance = 0.0
    predicted_at_failure = 0.0
    fail_started_at: int | None = None
    battery_seconds = 0.0

    steps = int(scenario.duration_s / DT)
    for step in range(steps + 1):
        t = int(step * DT)

        # Apply due events.
        while ei < len(events) and events[ei].at_s <= t:
            ev = events[ei]
            ei += 1
            if ev.action == "utility-fail" and utility_on:
                utility_on = False
                if fail_started_at is None:
                    fail_started_at = t
                log.append(LogEntry(
                    t=t, severity="critical",
                    message="Utility power lost — UPS on battery",
                ))
            elif ev.action == "utility-restore" and not utility_on:
                utility_on = True
                if not rack_powered and dark_reason == "battery exhausted":
                    rack_powered = True
                    log.append(LogEntry(
                        t=t, severity="info",
                        message="Utility restored — rack repowered from mains",
                    ))
                else:
                    log.append(LogEntry(
                        t=t, severity="info",
                        message="Utility restored — UPS back on pass-through",
                    ))
            elif ev.action == "move-load" and ev.index is not None and ev.phase:
                if 0 <= ev.index < len(phase_of) and phase_of[ev.index] != ev.phase:
                    old = phase_of[ev.index]
                    phase_of[ev.index] = ev.phase
                    log.append(LogEntry(
                        t=t, severity="info",
                        message=(
                            f"{cfg.loads[ev.index].label} moved from phase "
                            f"{old} to phase {ev.phase}"
                        ),
                    ))
            elif ev.action == "set-load" and ev.index is not None and ev.value is not None:
                if 0 <= ev.index < len(watts_of):
                    watts_of[ev.index] = max(0.0, float(ev.value))
                    log.append(LogEntry(
                        t=t, severity="info",
                        message=(
                            f"{cfg.loads[ev.index].label} load set to "
                            f"{ev.value:g} W"
                        ),
                    ))
            elif ev.action == "self-test" and utility_on and rack_powered:
                self_tested = True
                # A brief transfer to battery costs a sliver of charge.
                live_now = sum(
                    w for w, p in zip(watts_of, phase_of) if p not in tripped
                )
                remaining_wh = max(
                    0.0,
                    remaining_wh
                    - (live_now / inverter_eff) * C("self_test_seconds") / 3600.0,
                )
                pct = 100.0 * capacity_fraction
                severity = "warning" if capacity_fraction < 0.8 else "info"
                log.append(LogEntry(
                    t=t, severity=severity,
                    message=(
                        f"UPS self-test: battery holds {pct:.0f}% of "
                        "nameplate capacity — runtime prediction corrected"
                    ),
                ))

        # --- Live outlet watts ------------------------------------------
        live: list[float] = []
        for w, p in zip(watts_of, phase_of):
            if not rack_powered or p in tripped:
                live.append(0.0)
            else:
                live.append(w)

        phase_w = {
            p: sum(w for w, lp in zip(live, phase_of) if lp == p)
            for p in PHASES
        }
        pdu_input = sum(phase_w.values())

        # --- Breakers (thermal-magnetic, simplified I²t) -----------------
        for p in PHASES:
            if p in tripped:
                continue
            amps = phase_w[p] / (volts * pf)
            if amps >= C("breaker_magnetic_multiple") * rating_amps:
                tripped.add(p)
                log.append(LogEntry(
                    t=t, severity="critical",
                    message=f"Phase {p} breaker tripped instantly "
                            f"({amps:.0f} A on a {rating_amps:.0f} A breaker)",
                ))
            elif amps > rating_amps:
                overload = amps / rating_amps
                trip_heat[p] += (overload * overload - 1.0) * DT
                if trip_heat[p] >= C("breaker_i2t_threshold"):
                    tripped.add(p)
                    log.append(LogEntry(
                        t=t, severity="critical",
                        message=(
                            f"Phase {p} breaker tripped — sustained "
                            f"{100 * overload:.0f}% of rating; every load "
                            "on the phase is dark"
                        ),
                    ))
            else:
                trip_heat[p] = max(0.0, trip_heat[p] - DT)

        # Recompute after any trip this tick so the trace never shows
        # watts flowing through an open breaker.
        live = [
            0.0 if (not rack_powered or p in tripped) else w
            for w, p in zip(watts_of, phase_of)
        ]
        phase_w = {
            p: sum(w for w, lp in zip(live, phase_of) if lp == p)
            for p in PHASES
        }
        pdu_input = sum(phase_w.values())

        # --- UPS ----------------------------------------------------------
        if utility_on:
            on_battery = False
            battery_out = 0.0
            charge_draw = 0.0
            if rack_powered and remaining_wh < effective_wh - 1e-9:
                charge_draw = C("charge_power_w")
                remaining_wh = min(
                    effective_wh,
                    remaining_wh + charge_draw * C("charge_efficiency") * DT / 3600.0,
                )
            ac_input = pdu_input / pass_eff + charge_draw
            inverter_loss = ac_input - charge_draw - pdu_input
        else:
            on_battery = rack_powered and pdu_input > 0
            charge_draw = 0.0
            ac_input = 0.0
            if rack_powered:
                battery_out = pdu_input / inverter_eff
                remaining_wh -= battery_out * DT / 3600.0
                if pdu_input > 0:
                    battery_seconds += DT
                if remaining_wh <= 0.0:
                    remaining_wh = 0.0
                    rack_powered = False
                    on_battery = False
                    battery_out = 0.0
                    dark_reason = "battery exhausted"
                    log.append(LogEntry(
                        t=t, severity="critical",
                        message="Battery exhausted — rack dark",
                    ))
                    live = [0.0] * len(live)
                    phase_w = {p: 0.0 for p in PHASES}
                    pdu_input = 0.0
            else:
                battery_out = 0.0
            inverter_loss = battery_out - pdu_input

        # --- Instruments ---------------------------------------------------
        amps = {p: phase_w[p] / (volts * pf) for p in PHASES}
        pcts = {p: 100.0 * amps[p] / rating_amps for p in PHASES}
        avg = pdu_input / 3.0
        imbalance = (
            100.0 * max(abs(phase_w[p] - avg) for p in PHASES) / avg
            if avg > 0 else 0.0
        )
        believed_full_wh = (
            effective_wh if self_tested else float(cfg.ups_nameplate_wh)
        )
        charge_fraction = remaining_wh / effective_wh if effective_wh > 0 else 0.0
        predicted_min = _runtime_min(believed_full_wh * charge_fraction, pdu_input)
        actual_min = _runtime_min(remaining_wh, pdu_input)

        if fail_started_at is not None and predicted_at_failure == 0.0:
            predicted_at_failure = predicted_min

        peak_input = max(peak_input, pdu_input)
        worst_imbalance = max(worst_imbalance, imbalance)

        region_watts = {
            **{f"load-{i + 1}": round(w, 1) for i, w in enumerate(live)},
            "pdu-a": round(phase_w["A"], 1),
            "pdu-b": round(phase_w["B"], 1),
            "pdu-c": round(phase_w["C"], 1),
            "ups": round(pdu_input, 1),
            "battery": round(battery_out, 1),
        }

        trace.append(SimState(
            t=t,
            utility_on=utility_on,
            on_battery=on_battery,
            rack_powered=rack_powered,
            phase_a_w=round(phase_w["A"], 1),
            phase_b_w=round(phase_w["B"], 1),
            phase_c_w=round(phase_w["C"], 1),
            phase_a_amps=round(amps["A"], 2),
            phase_b_amps=round(amps["B"], 2),
            phase_c_amps=round(amps["C"], 2),
            phase_a_pct=round(pcts["A"], 1),
            phase_b_pct=round(pcts["B"], 1),
            phase_c_pct=round(pcts["C"], 1),
            tripped_phases=sorted(tripped),
            imbalance_pct=round(imbalance, 1),
            pdu_input_w=round(pdu_input, 1),
            ac_input_w=round(ac_input, 1),
            battery_output_w=round(battery_out, 1),
            inverter_loss_w=round(inverter_loss, 1),
            charge_draw_w=round(charge_draw, 1),
            charge_pct=round(100.0 * charge_fraction, 1),
            battery_wh_remaining=round(remaining_wh, 1),
            predicted_runtime_min=round(predicted_min, 1),
            actual_runtime_min=round(actual_min, 1),
            self_tested=self_tested,
            region_watts=region_watts,
        ))

    summary = Summary(
        peak_input_w=round(peak_input, 1),
        worst_imbalance_pct=round(worst_imbalance, 1),
        battery_capacity_fraction=round(capacity_fraction, 3),
        predicted_runtime_min_at_failure=round(predicted_at_failure, 1),
        actual_runtime_min_survived=round(battery_seconds / 60.0, 1),
        tripped_phases=sorted(tripped),
        rack_went_dark=not trace[-1].rack_powered,
        dark_reason=dark_reason,
    )
    return trace, log, summary
