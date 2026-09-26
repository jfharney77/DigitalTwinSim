"""The charging-diagnostics trace: a second pure trace beside ``engine.simulate``.

The support genre this models is "it stopped charging at 80%" and "it charges
slowly". Four different mechanisms produce that one complaint, and only one of
them is a fault:

* a BIOS charge mode (Primarily AC Use, Adaptive, Custom) stopping the charge
  below 100% on purpose;
* the constant-voltage taper, where the cells — not the adapter — set the pace;
* heat: a pack over its charge-temperature limit is not charged, even with
  watts to spare, and a gaming load is what heats it;
* an adapter the EC (embedded controller) could not identify, which it will
  power the system from but will not charge from.

The trace walks one machine through all four in one sitting, and each state
carries what the owner could read off the machine at that moment: the BIOS
"AC Adapter" line, the battery status line, and the pack temperature. The
``charge_limiter`` field is the diagnosis — the single reason the pack is
taking less than the full constant-current rate.

Same rules as ``engine.py``: no FastAPI, no IO, no timers, no randomness; the
energy identity ``acW + batteryW == systemW + chargeW`` holds on every state
because ``ac_w`` is derived, never set. Every charge decision goes through one
gate (``_Walk.charge``), so "no charge over the temperature limit" and "no
charge from an unrecognized adapter" are properties of the gate rather than
of each step's author remembering them.

Numbers are illustrative. The sourced anchors are the charge modes and their
limits (Dell KB 000123069), the BIOS adapter line (same KB and 000125125), the
CC/CV shape and 3-5% termination current (Battery University BU-409), and the
0-45 degC lithium-ion charge window (BU-410). Dell does not publish the m18's
firmware thresholds, so the exact knee, limit and rates here are stand-ins.
"""

from __future__ import annotations

from .engine import (
    CPU_IDLE_FLOOR_W,
    HYBRID_FLOOR_PCT,
    THERMAL_CAP,
    THROTTLED_CPU_W,
    THROTTLED_GPU_W,
    WORKLOAD_FRAC,
    _cc_rate,
)
from .leveling import L
from .models import (
    AdapterOption,
    ChargeLimiter,
    ChargeMode,
    ChargeStage,
    DiagnosticCheck,
    DiagnosticState,
    LaptopProfile,
    Scenario,
    SourceLink,
    Summary,
    TraceScenario,
)

SCENARIO_ID = "charge-taper-diagnostics"
BASELINE_ID = "plug-in"

DIAGNOSTIC_PHASES = [
    "off", "detect", "handshake", "budget", "charge", "cap", "taper",
    "load", "heat", "resume", "swap", "steady",
]
BASELINE_PHASES = [
    "off", "detect", "handshake", "budget", "charge", "boot", "load", "steady",
]

# The walk is a fixed script: it ignores the scenario's start level, thermal
# mode and workload so that every symptom is reached on every machine.
START_PCT = 62.0
WALK_THERMAL_MODE = "fullSpeed"
WALK_WORKLOAD = "gaming"

# Primarily AC Use "limits your battery charge to only 50-80%" (Dell KB
# 000123069). The walk uses the top of that range.
AC_USE_CAP_PCT = 80.0
# Where constant current hands over to constant voltage. Illustrative: the
# real knee depends on charge rate and cell age (BU-409 puts it near 85% for
# a fast charge); 80% lines up with ExpressCharge's "80% in about an hour".
TAPER_KNEE_PCT = 80.0
# Charge terminates when current falls to 3-5% of the rated figure (BU-409).
TERMINATION_FRAC = 0.05
# Lithium-ion's charge window is 0-45 degC (BU-410). Dell does not publish
# the m18's firmware threshold; 45 degC is the cell-level figure.
PACK_CHARGE_LIMIT_C = 45.0
# Once inhibited, the charge stays off until the pack is this cool: charger
# ICs resume a few degrees under the trip point so the charge does not
# chatter on and off at the limit. Illustrative; the width is a stand-in.
PACK_CHARGE_RESUME_C = 42.0

SOURCES = [
    SourceLink(
        label="Dell KB 000123069 — How to troubleshoot Dell laptop battery issues "
        "(charge modes, charge thresholds, the BIOS AC Adapter line)",
        url="https://www.dell.com/support/kbdoc/en-us/000123069/how-to-troubleshoot-dell-laptop-battery-issues",
    ),
    SourceLink(
        label="Dell KB 000125125 — How to troubleshoot AC adapter issues "
        "(adapter type unknown, slow or no charging)",
        url="https://www.dell.com/support/kbdoc/en-us/000125125/how-to-troubleshoot-ac-adapter-issues",
    ),
    SourceLink(
        label="Dell KB 000143915 — Performance issue or battery drain while the "
        "AC adapter is connected (hybrid power on Alienware)",
        url="https://www.dell.com/support/kbdoc/en-us/000143915/alienware-15-r3-15-r4-17-r4-17-r5-m15-m17-performance-issue-or-battery-drain-while-ac-adapter-is-connected",
    ),
    SourceLink(
        label="Battery University BU-409 — Charging lithium-ion "
        "(constant current, constant voltage, 3-5% termination)",
        url="https://batteryuniversity.com/article/bu-409-charging-lithium-ion",
    ),
    SourceLink(
        label="Battery University BU-410 — Charging at high and low temperatures "
        "(0–45 °C charge window)",
        url="https://batteryuniversity.com/article/bu-410-charging-at-high-and-low-temperatures",
    ),
    SourceLink(
        label="Dell Community — m18 R2 'not warm battery charger' (an owner "
        "asking whether a cool brick means a fault; the thread has no answer)",
        url="https://www.dell.com/community/en/conversations/alienware/m18-r2-not-warm-battery-charger/66c6745d47effa74c486d959",
    ),
]

CHECKS = [
    DiagnosticCheck(
        id="charge-cap",
        phase="cap",
        limiter="charge-cap",
        symptom="Plugged in, stuck at 80%, nothing moving.",
        readout="BIOS battery settings: Primarily AC Use. AC Adapter line shows the full wattage.",
        cause="A charge mode is doing its job. Primarily AC Use, Adaptive and "
        "Custom all stop the charge below 100% to slow cell ageing.",
        action="Nothing is broken. Switch the mode to Standard if the full "
        "capacity is wanted, in BIOS setup (F2 at start-up).",
    ),
    DiagnosticCheck(
        id="taper",
        phase="taper",
        limiter="taper",
        symptom="Charges slowly past 80%, and the adapter brick stays cool.",
        readout="Battery status: Charging. Adapter wattage correct. AC draw far below the rating.",
        cause="Constant-voltage taper. The cells are at their voltage limit and "
        "accept less current every minute; a cool brick is a lightly loaded brick.",
        action="Nothing to do. The last fifth of the charge takes about as long as the first four.",
    ),
    DiagnosticCheck(
        id="temperature",
        phase="heat",
        limiter="temperature",
        symptom="Plugged in, not charging after a gaming session, below full.",
        readout="Battery status: Not charging. Adapter wattage correct. The pack reads hot.",
        cause="The pack is above its charge-temperature limit. Charging hot "
        "lithium-ion cells costs cycle life, so the charger waits.",
        action="Let it cool: leave the fans running, clear the vents, lift the "
        "rear. Charging resumes unprompted a few degrees under the limit.",
    ),
    DiagnosticCheck(
        id="adapter",
        phase="swap",
        limiter="adapter",
        symptom="Plugged in, not charging, and the machine is slow.",
        readout="BIOS AC Adapter line: Unknown.",
        cause="The PSID handshake failed: a third-party brick with no ID chip, "
        "or a bent centre pin. The EC will not budget watts it cannot verify, "
        "so the pack charges slowly or, as modelled here, not at all.",
        action="Reseat the plug, inspect the centre pin, then use the Dell "
        "adapter. The only one of the four that needs a part.",
    ),
]

DIAGNOSTIC_SCENARIO = TraceScenario(
    id=SCENARIO_ID,
    title="Charging diagnostics",
    kind="failure",
    summary=L(
        novice=(
            "One complaint, four different causes. A laptop that stops charging "
            "at 80%, or charges slowly, may be obeying a battery-care setting, "
            "finishing the slow last part of a normal charge, waiting for a hot "
            "battery to cool down, or refusing a charger it could not identify. "
            "This walk puts one machine through all four and shows what its "
            "own screens say each time, so you can tell them apart."
        ),
        standard=(
            "One complaint, four causes. A laptop that stops at 80% or charges "
            "slowly may be obeying a BIOS charge mode, finishing a "
            "constant-voltage taper, waiting for a hot pack to cool, or "
            "refusing an adapter it could not identify. The walk takes one "
            "machine through all four and shows the BIOS adapter line, the "
            "battery status and the pack temperature at each."
        ),
        expert=(
            "Four limiters behind one symptom: charge-mode cap, CV taper, pack "
            "over-temperature, PSID failure. One trace, with the BIOS readouts "
            "that separate them."
        ),
    ),
    phases=DIAGNOSTIC_PHASES,
    hero_label="what is limiting the charge",
    checks=CHECKS,
    sources=SOURCES,
    illustrative=(
        "Watts, percentages and temperatures are illustrative. The charge "
        "modes, the BIOS adapter line, the constant-current/constant-voltage "
        "shape and the 0–45 °C cell-level charge window are sourced. Dell "
        "does not publish this machine's firmware thresholds, so the 45 °C "
        "trip and 42 °C re-arm are stand-ins, and an unrecognized adapter "
        "is modelled as no charge where Dell says it may not charge or may "
        "charge slowly. The thermal behaviour is simplified in the same "
        "direction: production charger ICs usually reduce the charge current "
        "through a warm band before cutting it off, where this walk stops "
        "the charge outright at one threshold."
    ),
)

BASELINE_SCENARIO = TraceScenario(
    id=BASELINE_ID,
    title="Plug-in power path",
    kind="baseline",
    summary=(
        "The plug-in sequence with everything working: detect, PSID handshake, "
        "power budget, charge, boot, load."
    ),
    phases=BASELINE_PHASES,
    hero_label="battery supplement",
)

TRACE_SCENARIOS: dict[str, TraceScenario] = {
    BASELINE_ID: BASELINE_SCENARIO,
    SCENARIO_ID: DIAGNOSTIC_SCENARIO,
}


def taper_w(cc_w: float, pct: float) -> float:
    """Charge power the cells accept at ``pct`` on the constant-voltage leg.

    Linear from the full constant-current rate at the knee down to the
    termination floor, then zero at 100%. A straight line stands in for the
    real exponential decay; what matters is that it only ever falls.
    """
    if pct >= 100.0:
        return 0.0
    if pct <= TAPER_KNEE_PCT:
        return cc_w
    frac = (100.0 - pct) / (100.0 - TAPER_KNEE_PCT)
    return cc_w * max(TERMINATION_FRAC, frac)


def walk_adapters(
    profile: LaptopProfile, adapter: AdapterOption
) -> tuple[AdapterOption, AdapterOption]:
    """The (genuine, third-party) pair the walk uses.

    The selected adapter is the genuine one when it is a recognized barrel
    adapter; otherwise the profile's default stands in. The walk needs a
    working charge to diagnose before it reaches the adapter that does not
    work, and its handshake is the barrel plug's PSID read, which a USB-C
    charger does not perform.
    """
    good = adapter
    if not good.recognized or good.connector != "barrel":
        good = next(a for a in profile.adapters if a.id == profile.default_adapter_id)
    bad = next(a for a in profile.adapters if not a.recognized)
    return good, bad


class _Walk:
    """Mutable pack/adapter state plus the one gate every charge goes through."""

    def __init__(self, profile: LaptopProfile, adapter: AdapterOption) -> None:
        self.profile = profile
        self.adapter = adapter
        self.cc_w = _cc_rate(profile, adapter)
        self.pct = START_PCT
        self.temp_c = 31.0
        self.mode: ChargeMode = "primarily-ac"
        self.cap_pct = AC_USE_CAP_PCT
        self.plugged = False
        self.heat_inhibit = False  # latched over the limit, cleared at resume
        self.states: list[DiagnosticState] = []

    # -- the gate ---------------------------------------------------------
    def too_hot(self) -> bool:
        """The thermal inhibit, with hysteresis: it trips above the limit and
        clears only at or below the resume temperature."""
        if self.temp_c > PACK_CHARGE_LIMIT_C:
            self.heat_inhibit = True
        elif self.temp_c <= PACK_CHARGE_RESUME_C:
            self.heat_inhibit = False
        return self.heat_inhibit

    def charge(
        self, system_w: float, target_pct: float
    ) -> tuple[float, ChargeLimiter, ChargeStage]:
        """Decide charge power for one state and move ``pct`` accordingly.

        Order matters and is the order a technician checks in: is the adapter
        trusted, is the pack cool enough, has a limit been reached, is there
        any adapter budget left — and only then what the cells will accept.
        """
        if not self.plugged:
            return 0.0, "none", "idle"
        if not self.adapter.recognized:
            return 0.0, "adapter", "idle"
        if self.too_hot():
            return 0.0, "temperature", "idle"
        if self.pct >= self.cap_pct:
            if self.cap_pct >= 100.0:
                return 0.0, "full", "full"
            return 0.0, "charge-cap", "idle"
        headroom = self.adapter.watts - system_w
        if headroom <= 0.0:
            return 0.0, "budget", "idle"
        target = max(self.pct, min(target_pct, self.cap_pct))
        if target <= TAPER_KNEE_PCT:
            want, stage, limiter = self.cc_w, "cc", "none"
        else:
            want, stage, limiter = taper_w(self.cc_w, target), "cv", "taper"
        if want <= 0.0:  # the last step to 100%: termination
            self.pct = target
            return 0.0, "full", "full"
        if headroom < want:
            want, limiter = headroom, "budget"
        self.pct = target
        return want, limiter, stage

    def battery_readout(self, limiter: ChargeLimiter, charge_w: float,
                        battery_w: float) -> str:
        if battery_w > 0:
            return "Discharging"
        if charge_w > 0:
            return "Charging"
        return {
            # The machine's status line names no cause: three of the four
            # symptoms read the same, which is why the other readouts matter.
            "charge-cap": "Not charging",
            "temperature": "Not charging",
            "adapter": "Not charging",
            "budget": "Not charging",
            "full": "Fully charged",
        }.get(limiter, "Idle")

    def adapter_readout(self) -> str:
        if not self.plugged:
            return "None"
        return f"{self.adapter.watts:g} W" if self.adapter.recognized else "Unknown"

    # -- emit -------------------------------------------------------------
    def emit(
        self,
        *,
        phase: str,
        stage_id: str,
        label: str,
        description: str,
        active: list[str],
        system_w: float,
        target_pct: float | None = None,
        cpu_w: float = 0.0,
        gpu_w: float = 0.0,
        fan_pct: float = 22.0,
        failed: list[str] | None = None,
        adapter_readout: str | None = None,
        hold: ChargeLimiter | None = None,
        stalled: bool = False,
        cycle_cost: int = 1,
    ) -> DiagnosticState:
        """Append one state. ``hold`` names why the charger is not armed on
        this step (before the handshake, or while a setting is being saved);
        it can only ever force the charge to zero, never permit one."""
        battery_w = 0.0
        hybrid = False
        if not self.plugged:
            battery_w = system_w
            charge_w, limiter, stage = 0.0, "none", "idle"
        elif system_w > self.adapter.watts and self.pct > HYBRID_FLOOR_PCT:
            # Hybrid power: the battery supplements the adapter.
            battery_w = system_w - self.adapter.watts
            hybrid = True
            self.pct = max(self.pct - battery_w * 0.03, 0.0)
            charge_w, stage = 0.0, "idle"
            limiter = "temperature" if self.too_hot() else "budget"
        elif hold is not None:
            charge_w, limiter, stage = 0.0, hold, "idle"
        else:
            charge_w, limiter, stage = self.charge(
                system_w, self.pct if target_pct is None else target_pct
            )
        # Round the independent terms, then derive acW, so the identity holds
        # exactly on the wire (the engine's rule).
        system_w = round(system_w, 1)
        charge_w = round(charge_w, 1)
        battery_w = round(battery_w, 1)
        state = DiagnosticState(
            cycle=len(self.states),
            phase=phase,
            stage_id=stage_id,
            label=label,
            description=description,
            active_regions=active,
            ac_w=round(system_w + charge_w - battery_w, 1),
            system_w=system_w,
            charge_w=charge_w,
            battery_w=battery_w,
            battery_pct=round(self.pct, 1),
            charge_stage=stage,
            cpu_w=round(cpu_w, 1),
            gpu_w=round(gpu_w, 1),
            fan_pct=fan_pct,
            hybrid=hybrid,
            stalled=stalled,
            cycle_cost=cycle_cost,
            charge_limiter=limiter,
            charge_mode=self.mode,
            charge_cap_pct=self.cap_pct,
            pack_temp_c=self.temp_c,
            adapter_readout=adapter_readout or self.adapter_readout(),
            battery_readout=self.battery_readout(limiter, charge_w, battery_w),
            failed_regions=failed or [],
        )
        self.states.append(state)
        return state


def simulate_charge_diagnostics(
    profile: LaptopProfile, adapter: AdapterOption, scenario: Scenario
) -> list[DiagnosticState]:
    """One machine, one sitting, four reasons the pack is not filling fast."""
    del scenario  # a fixed script; see START_PCT / WALK_* above
    good, bad = walk_adapters(profile, adapter)
    w = _Walk(profile, good)
    rest_w = float(profile.idle_w)
    cc = w.cc_w
    watts = f"{good.watts:g}"
    limit = f"{PACK_CHARGE_LIMIT_C:g}"
    resume = f"{PACK_CHARGE_RESUME_C:g}"

    # ---- off ------------------------------------------------------------
    w.emit(
        phase="off",
        stage_id="d0-on-battery",
        label=f"On battery at {START_PCT:g}%",
        description=L(
            novice=(
                f"The laptop is awake on the desk, unplugged, with {START_PCT:g}% "
                f"in the battery. It is doing very little, so it draws about "
                f"{rest_w:g} watts, all of it from the battery pack. Its battery "
                "setting is 'Primarily AC Use', a battery-care mode the owner "
                "switched on months ago and forgot. That forgotten setting is "
                "the first thing this walk will trip over."
            ),
            standard=(
                f"Awake, unplugged, {START_PCT:g}% in the pack, drawing about "
                f"{rest_w:g} W from it. The BIOS battery setting is Primarily AC "
                "Use — a charge mode for machines that live on the adapter — "
                "set months ago and forgotten."
            ),
            expert=(
                f"On pack, {START_PCT:g}%, ~{rest_w:g} W. Charge mode: Primarily "
                "AC Use."
            ),
        ),
        active=["ec", "battery"],
        system_w=rest_w,
    )

    # ---- detect ---------------------------------------------------------
    w.plugged = True
    w.emit(
        phase="detect",
        stage_id="d1-plug-in",
        label="Adapter plugged in",
        description=L(
            novice=(
                f"The {good.name} goes in. The laptop's small always-on power "
                "chip, the embedded controller, notices voltage at the socket "
                "and moves the machine's draw from the battery to the wall. "
                "Nothing is charging yet: the laptop has not worked out what "
                "kind of adapter this is, so the BIOS screen's 'AC Adapter' "
                "line is still blank."
            ),
            standard=(
                f"The {good.name} seats. The EC (embedded controller) senses "
                "DC-in and moves the system's draw from pack to adapter. No "
                "charging yet: the adapter has not been identified, so the "
                "BIOS AC Adapter line is still empty."
            ),
            expert=(
                "DC-in detected; system load moves to the adapter. Adapter "
                "unidentified, charge disabled."
            ),
        ),
        active=["dc-in", "ec"],
        system_w=rest_w,
        hold="none",
        adapter_readout="Reading",
    )

    # ---- handshake ------------------------------------------------------
    w.emit(
        phase="handshake",
        stage_id="d2-psid-ok",
        label=f"Adapter identified: {watts} W",
        description=L(
            novice=(
                "The embedded controller reads the adapter's identity chip and "
                f"gets a clean answer: a Dell adapter rated {watts} watts. The "
                f"BIOS screen's 'AC Adapter' line now reads {watts} W. This is "
                "the first thing to check whenever a Dell laptop will not "
                "charge. If that line shows the right wattage, the laptop "
                "has identified the adapter through the cable and the socket, "
                "and the cause is most likely somewhere else."
            ),
            standard=(
                "The EC reads the adapter's PSID (power supply ID) and gets a "
                f"valid answer: {watts} W. The BIOS AC Adapter line now reads "
                f"{watts} W — the first check in any charging complaint. A "
                "correct wattage there means the ID line is intact through "
                "brick, cable and DC-in jack, which moves suspicion elsewhere."
            ),
            expert=(
                f"PSID valid: {watts} W. BIOS adapter line correct: ID path "
                "intact through brick, cable and jack."
            ),
        ),
        active=["dc-in", "ec"],
        system_w=rest_w,
        hold="none",
        stalled=True,
        cycle_cost=4,
    )

    # ---- budget ---------------------------------------------------------
    w.emit(
        phase="budget",
        stage_id="d3-charge-enabled",
        label="Charging allowed",
        description=L(
            novice=(
                f"With the adapter trusted, the controller plans how to spend "
                f"its {watts} watts. The idle machine needs about {rest_w:g}, "
                "which leaves plenty for the battery, so it tells the charging "
                "chip to start. The battery is cool, well below the 80% its "
                "care setting allows, and the adapter is genuine. Every "
                "condition for a fast charge is met."
            ),
            standard=(
                f"The EC budgets {watts} W: about {rest_w:g} W for the idle "
                "system, the rest available to the charger IC. The pack is "
                "cool, under its charge limit, and the adapter is trusted, so "
                "charging is enabled at the full rate."
            ),
            expert=(
                f"Budget {watts} W, ~{rest_w:g} W system. No limiter active; "
                "charge enabled."
            ),
        ),
        active=["ec", "charger"],
        system_w=rest_w,
        hold="none",
    )

    # ---- charge: constant current ----------------------------------------
    w.temp_c = 34.0
    w.emit(
        phase="charge",
        stage_id="d4-cc-1",
        label="Constant current",
        description=L(
            novice=(
                f"The fast part of the charge. The charging chip pushes a steady "
                f"current into the battery, about {min(cc, good.watts - rest_w):.0f} "
                "watts, and the percentage climbs quickly. Engineers call this "
                "stage constant current because the current is what stays "
                "fixed; the battery's voltage rises underneath it. The adapter "
                "brick is working and feels warm."
            ),
            standard=(
                "Constant-current (CC) bulk charge at about "
                f"{min(cc, good.watts - rest_w):.0f} W. Current is held fixed "
                "while cell voltage rises; the percentage climbs fast and the "
                "brick runs warm."
            ),
            expert=(
                f"CC bulk, ~{min(cc, good.watts - rest_w):.0f} W. Cell voltage "
                "rising toward the limit."
            ),
        ),
        active=["dc-in", "charger", "battery"],
        system_w=rest_w,
        target_pct=71.0,
        cycle_cost=3,
    )
    w.temp_c = 36.0
    w.emit(
        phase="charge",
        stage_id="d5-cc-2",
        label=f"Constant current to {AC_USE_CAP_PCT:g}%",
        description=L(
            novice=(
                f"Still the fast stage, and the battery reaches {AC_USE_CAP_PCT:g}%. "
                "Dell's ExpressCharge figure, about 80% in an hour with the "
                "machine switched off, describes "
                "exactly this stretch. It is quick because a partly empty "
                "lithium-ion battery will take nearly any current offered. "
                "That stops being true from here on."
            ),
            standard=(
                f"CC continues to {AC_USE_CAP_PCT:g}%. This is the stretch "
                "ExpressCharge's '80% in about an hour', powered off, "
                "describes: a partly "
                "empty lithium-ion pack accepts almost any current. Past this "
                "point it does not."
            ),
            expert=f"CC to {AC_USE_CAP_PCT:g}%: the ExpressCharge stretch.",
        ),
        active=["dc-in", "charger", "battery"],
        system_w=rest_w,
        target_pct=AC_USE_CAP_PCT,
        cycle_cost=3,
    )

    # ---- cap: the charge mode stops the charge ---------------------------
    w.emit(
        phase="cap",
        stage_id="d6-stuck-at-cap",
        label=f"Stuck at {AC_USE_CAP_PCT:g}%",
        description=L(
            novice=(
                f"The first symptom. The battery reaches {AC_USE_CAP_PCT:g}% and "
                "charging stops dead: zero watts into the battery, though the "
                f"adapter is fine and the BIOS still shows {watts} W. Nothing "
                "has failed. 'Primarily AC Use' is a battery-care mode that "
                "stops the charge early on purpose, because a lithium-ion "
                "battery held at 100% for months ages faster. Dell's Adaptive "
                "and Custom modes can do the same thing. The clue is in the "
                "BIOS battery settings, not in the hardware."
            ),
            standard=(
                f"First symptom: the pack reaches {AC_USE_CAP_PCT:g}% and charge "
                f"power drops to zero with the adapter line still reading "
                f"{watts} W. Nothing has failed. Primarily AC Use stops the "
                "charge early on purpose, because cells held at 100% age "
                "faster; Adaptive and Custom modes can do the same. The "
                "evidence is in the BIOS battery settings."
            ),
            expert=(
                f"Charge-mode cap at {AC_USE_CAP_PCT:g}%: charge 0 W, adapter "
                "line correct. Policy, not fault."
            ),
        ),
        active=["ec", "charger", "battery"],
        system_w=rest_w,
        target_pct=100.0,
        cycle_cost=2,
    )
    w.emit(
        phase="cap",
        stage_id="d7-mode-standard",
        label="Charge mode set to Standard",
        description=L(
            novice=(
                "The fix for the first symptom is a setting. The owner opens "
                "the BIOS battery screen and changes the mode from 'Primarily "
                "AC Use' to 'Standard', which charges to 100%. Nothing moves "
                "yet: until the change is saved the readouts still show the "
                f"old mode and its {AC_USE_CAP_PCT:g}% limit, and the battery "
                "still sits at that limit, not charging. The new limit applies "
                "from the next step. For a laptop that rarely leaves its desk, "
                "leaving the limit on is the better choice for the battery."
            ),
            standard=(
                "The recovery is a setting. The owner changes the BIOS battery "
                f"mode from Primarily AC Use to Standard. The {AC_USE_CAP_PCT:g}% "
                "limit is still what the readouts show and still what the EC "
                "enforces on this step; the new limit, and the charge, take "
                "effect on the next one. On a machine that rarely leaves its "
                "desk, the limit is the better choice for the cells."
            ),
            expert=(
                f"Mode change entered; {AC_USE_CAP_PCT:g}% cap still in force "
                "this step. Cap lifts to 100% and charge re-arms next step."
            ),
        ),
        active=["ec", "battery"],
        system_w=rest_w,
        target_pct=100.0,
    )
    # The saved setting takes effect between the two states: from here the EC
    # enforces 100%, so no state ever shows a limiter its own readouts deny.
    w.mode = "standard"
    w.cap_pct = 100.0

    # ---- taper: constant voltage ----------------------------------------
    w.emit(
        phase="taper",
        stage_id="d8-cv-1",
        label="Constant-voltage taper begins",
        description=L(
            novice=(
                "Charging resumes, but more slowly, and that is the second "
                "symptom. Above about 80% the battery's cells have reached the "
                "highest voltage they may safely be held at. The charging chip "
                "stops forcing a fixed current and holds that voltage instead, "
                "and the cells take in less and less as they fill, the way a "
                f"nearly full glass has to be topped up slowly. Charge power "
                f"has dropped from about {cc:.0f} watts to about "
                f"{taper_w(cc, 85.0):.0f}."
            ),
            standard=(
                "Charging resumes, slower: the second symptom. Above the knee "
                "the cells sit at their voltage limit, so the charger IC holds "
                "voltage and lets current fall — constant voltage (CV). Charge "
                f"power is down from about {cc:.0f} W to about "
                f"{taper_w(cc, 85.0):.0f} W, set by the cells rather than by "
                "the adapter."
            ),
            expert=(
                f"CV leg: ~{cc:.0f} W to ~{taper_w(cc, 85.0):.0f} W. The cells "
                "set the rate."
            ),
        ),
        active=["dc-in", "charger", "battery"],
        system_w=rest_w,
        target_pct=85.0,
        cycle_cost=3,
    )
    w.temp_c = 35.0
    w.emit(
        phase="taper",
        stage_id="d9-cv-2",
        label="The brick runs cool",
        description=L(
            novice=(
                f"Charge power keeps falling, now about {taper_w(cc, 90.0):.0f} "
                "watts. Owners notice two things here and worry about both: "
                "the last part of the charge drags, and the adapter brick "
                "feels cool. They are the same fact. A brick rated "
                f"{watts} watts that is delivering well under half of that has "
                "little waste heat to shed. The BIOS still reads 'Charging' "
                "and the right wattage, which is how to tell a taper from a "
                "fault."
            ),
            standard=(
                f"Charge power is down to about {taper_w(cc, 90.0):.0f} W. Two "
                "owner worries are one fact: the tail of the charge drags, and "
                f"the brick feels cool because a {watts} W adapter delivering "
                "a fraction of its rating sheds little heat. Battery status "
                "still reads Charging with the correct adapter wattage, which "
                "separates a taper from a fault."
            ),
            expert=(
                f"Taper at ~{taper_w(cc, 90.0):.0f} W. Cool brick is low load. "
                "Status Charging, adapter line correct."
            ),
        ),
        active=["dc-in", "charger", "battery"],
        system_w=rest_w,
        target_pct=90.0,
        stalled=True,
        cycle_cost=3,
    )

    # ---- load: a game starts ---------------------------------------------
    cap_cpu = profile.cpu_max_w * THERMAL_CAP[WALK_THERMAL_MODE]
    cap_gpu = profile.gpu_tgp_w * THERMAL_CAP[WALK_THERMAL_MODE]
    frac_cpu, frac_gpu = WORKLOAD_FRAC[WALK_WORKLOAD]
    cpu_game = max(CPU_IDLE_FLOOR_W, cap_cpu * frac_cpu)
    gpu_game = cap_gpu * frac_gpu
    game_w = rest_w + cpu_game + gpu_game
    over = game_w > good.watts
    load_regions = ["cpu", "gpu", "vram", "heatpipes", "fan-left", "fan-right"]

    w.temp_c = 43.0
    w.emit(
        phase="load",
        stage_id="d10-game-starts",
        label="A game starts",
        description=L(
            novice=(
                "The owner launches a game in Full Speed mode. The processor "
                f"and graphics chip together pull the system to about "
                f"{game_w:.0f} watts. "
                + (
                    f"That is more than the {watts}-watt adapter can give, so "
                    "the battery makes up the difference and its level starts "
                    "to slip even though the laptop is plugged in. Nothing is "
                    "left over for charging."
                    if over
                    else f"The {watts}-watt adapter covers that with some to "
                    "spare, so the slow top-up continues."
                )
                + " The battery sits between two hot chips and begins to warm."
            ),
            standard=(
                f"A game starts in Full Speed mode: about {game_w:.0f} W of "
                "system draw. "
                + (
                    f"That exceeds the {watts} W adapter, so hybrid power pulls "
                    "the difference from the pack and the level slips while "
                    "plugged in; no budget is left for charging."
                    if over
                    else f"The {watts} W adapter covers it with headroom, so "
                    "the taper continues."
                )
                + " The pack, beside the heat pipes, starts to warm."
            ),
            expert=(
                f"Gaming load ~{game_w:.0f} W; "
                + ("hybrid, charge budget zero." if over else "taper continues.")
                + " Pack warming."
            ),
        ),
        active=load_regions + (["battery"] if over else ["charger", "battery"]),
        system_w=game_w,
        target_pct=w.pct + 1.0,
        cpu_w=cpu_game,
        gpu_w=gpu_game,
        fan_pct=100.0,
    )
    w.temp_c = 47.0
    w.emit(
        phase="load",
        stage_id="d11-pack-hot",
        label=f"Pack passes {limit} °C",
        description=L(
            novice=(
                f"Half an hour in, the battery has soaked up heat from the "
                f"chassis and reads {w.temp_c:g} °C. Lithium-ion cells may "
                f"be charged only between freezing and about {limit} °C; "
                "charging them hotter wears them out quickly. So the charging "
                "chip now refuses to charge at all. While the game runs this "
                "is easy to miss. The machine is still allowed to draw from "
                "the battery when hot, which is a separate and wider limit."
            ),
            standard=(
                f"Thirty minutes in, the pack reads {w.temp_c:g} °C. "
                f"Lithium-ion's charge window tops out near {limit} °C, so "
                "the charger IC now inhibits charge outright. Discharge has a "
                "wider window, so hybrid supplement carries on. Under load "
                "the inhibit is easy to miss."
            ),
            expert=(
                f"Pack {w.temp_c:g} °C, over the {limit} °C charge window: "
                "charge inhibited, discharge still permitted."
            ),
        ),
        active=load_regions + ["battery"],
        system_w=game_w,
        target_pct=w.pct + 1.0,
        cpu_w=cpu_game,
        gpu_w=gpu_game,
        fan_pct=100.0,
        failed=["battery"],
    )

    # ---- heat: plugged in, headroom to spare, not charging ---------------
    paused_cpu, paused_gpu = 20.0, 15.0
    paused_w = rest_w + paused_cpu + paused_gpu
    w.temp_c = 46.5
    w.emit(
        phase="heat",
        stage_id="d12-not-charging-hot",
        label="Plugged in, not charging",
        description=L(
            novice=(
                "The third symptom. The game is paused, the system draw falls "
                f"to about {paused_w:.0f} watts, and the adapter has more than "
                f"{good.watts - paused_w:.0f} watts to spare. The battery is at "
                f"{w.pct:.0f}% and the charge limit is now 100%. Yet charge "
                f"power is zero. The reason is the pack temperature, "
                f"{w.temp_c:g} °C, still over the {limit} °C limit. The BIOS "
                "shows the correct adapter wattage, so the adapter is not the "
                "problem. The heat is what is stopping the charge."
            ),
            standard=(
                f"Third symptom. The game is paused, draw falls to about "
                f"{paused_w:.0f} W, and the adapter has over "
                f"{good.watts - paused_w:.0f} W of headroom. The pack is at "
                f"{w.pct:.0f}% under a 100% limit, and charge power is zero: "
                f"the pack reads {w.temp_c:g} °C, above the {limit} °C limit. "
                "The adapter line is correct, which rules the adapter out."
            ),
            expert=(
                f"Headroom >{good.watts - paused_w:.0f} W, {w.pct:.0f}%, cap "
                f"100%, charge 0 W: pack {w.temp_c:g} °C. Thermal inhibit."
            ),
        ),
        active=["ec", "charger", "battery", "fan-left", "fan-right"],
        system_w=paused_w,
        target_pct=94.0,
        cpu_w=paused_cpu,
        gpu_w=paused_gpu,
        fan_pct=100.0,
        failed=["battery"],
        stalled=True,
        cycle_cost=3,
    )
    w.temp_c = 43.8
    w.emit(
        phase="heat",
        stage_id="d13-cooling",
        label="Fans pull the pack down",
        description=L(
            novice=(
                "The recovery here is patience and airflow. The fans keep "
                f"running and the battery cools to {w.temp_c:g} °C. That is "
                f"back under the {limit} °C limit, yet the charge stays off. "
                "The charging chip waits until the battery is a few degrees "
                f"cooler still, about {resume} °C in this walk, so that it "
                "does not flick on and off right at the limit. Nobody has to "
                "do anything. Keeping the vents "
                "clear and lifting the back of the laptop off the desk "
                "shortens the wait. Unplugging and replugging does not."
            ),
            standard=(
                f"Recovery is airflow and time. The pack cools to "
                f"{w.temp_c:g} °C, under the {limit} °C limit, and the charge "
                "stays inhibited: the charger IC re-arms with hysteresis, "
                f"here at {resume} °C, so it does not chatter at the "
                "threshold. Clear vents and a raised rear edge shorten the "
                "wait; replugging the adapter does not."
            ),
            expert=(
                f"Pack {w.temp_c:g} °C, under trip, above the {resume} °C "
                "re-arm; inhibit holds. Airflow is the only lever."
            ),
        ),
        active=["ec", "battery", "fan-left", "fan-right"],
        system_w=paused_w,
        target_pct=94.0,
        cpu_w=paused_cpu,
        gpu_w=paused_gpu,
        fan_pct=100.0,
        failed=["battery"],
        cycle_cost=2,
    )

    # ---- resume -----------------------------------------------------------
    w.temp_c = 41.0
    w.emit(
        phase="resume",
        stage_id="d14-charge-resumes",
        label="Cool enough: charging resumes",
        description=L(
            novice=(
                f"The battery drops to {w.temp_c:g} °C, cool enough to re-arm, "
                "and the charging chip starts again without being asked. It "
                "picks up where the battery's level puts it on the slow "
                f"curve: about {taper_w(cc, 94.0):.0f} watts, lower than "
                "before the game, because the battery is fuller than it was. "
                "The status line reads 'Charging' again."
            ),
            standard=(
                f"The pack reaches {w.temp_c:g} °C, under the {resume} °C "
                "re-arm point, and the charger restarts unprompted. It rejoins the taper where the level puts it, at "
                f"about {taper_w(cc, 94.0):.0f} W: lower than before the game, "
                "because the pack is fuller."
            ),
            expert=(
                f"Pack {w.temp_c:g} °C: inhibit clears, CV resumes at "
                f"~{taper_w(cc, 94.0):.0f} W."
            ),
        ),
        active=["dc-in", "charger", "battery"],
        system_w=paused_w,
        target_pct=94.0,
        cpu_w=paused_cpu,
        gpu_w=paused_gpu,
        fan_pct=60.0,
        cycle_cost=2,
    )
    w.temp_c = 38.0
    w.emit(
        phase="resume",
        stage_id="d15-tail",
        label="The long tail",
        description=L(
            novice=(
                f"At 97% the battery accepts only about {taper_w(cc, 97.0):.0f} "
                "watts. The last fifth of a lithium-ion charge takes about "
                "as long as the first four fifths, and no larger adapter "
                "would change that, because the battery is setting the pace."
            ),
            standard=(
                f"At 97% the cells accept about {taper_w(cc, 97.0):.0f} W. The "
                "last fifth of the charge takes about as long as the first "
                "four, and "
                "a larger adapter would change nothing: the cells set the "
                "rate."
            ),
            expert=f"97%, ~{taper_w(cc, 97.0):.0f} W. Cell-limited.",
        ),
        active=["dc-in", "charger", "battery"],
        system_w=rest_w,
        target_pct=97.0,
        fan_pct=35.0,
        cycle_cost=3,
    )

    # ---- swap: a third-party brick ----------------------------------------
    w.adapter = bad
    idle_cpu = CPU_IDLE_FLOOR_W
    w.emit(
        phase="swap",
        stage_id="d16-psid-fails",
        label="Third-party brick: handshake fails",
        description=L(
            novice=(
                "The fourth symptom, and the only real fault. The owner packs "
                f"for a trip and plugs in a different charger, the {bad.name}. "
                "It supplies the right voltage, but the controller's "
                "identity check gets no valid answer back: there is no "
                "identity chip inside, or the thin centre pin of the plug is "
                "bent. The BIOS 'AC Adapter' line now reads 'Unknown'. That "
                "one word separates this case from the other three, where the "
                "wattage was always shown correctly."
            ),
            standard=(
                f"Fourth symptom, and the only fault. The owner plugs in the "
                f"{bad.name}. Voltage is present but the PSID read returns "
                "nothing valid — no ID chip, or a bent centre pin. The BIOS "
                "AC Adapter line reads Unknown, the one readout that "
                "separates this case from the other three."
            ),
            expert=(
                f"{bad.name}: PSID read fails, BIOS adapter line Unknown."
            ),
        ),
        active=["dc-in", "ec"],
        system_w=rest_w + idle_cpu,
        target_pct=100.0,
        cpu_w=idle_cpu,
        fan_pct=30.0,
        failed=["dc-in"],
        stalled=True,
        cycle_cost=4,
    )
    throttled_w = rest_w + THROTTLED_CPU_W + THROTTLED_GPU_W
    w.temp_c = 36.0
    w.emit(
        phase="swap",
        stage_id="d17-throttled-no-charge",
        label="Powered, throttled, not charging",
        description=L(
            novice=(
                "The controller will run the laptop from a charger it cannot "
                "identify, but carefully. Dell's own guidance for an adapter "
                "line reading 'Unknown' is that the laptop may not charge "
                "properly, or may charge slowly. In this walk the "
                "controller does not charge the battery at all, and it holds the processor and graphics chip to a small "
                f"fraction of their power, about {throttled_w:.0f} watts for "
                "the whole machine, because it has no way to know how much "
                "current this charger can safely supply. The battery stays "
                f"at {w.pct:.0f}%. The fix is physical: reseat the plug, look "
                "for a bent centre pin, and go back to the Dell adapter."
            ),
            standard=(
                "The EC powers the system from the unknown adapter but will "
                "not budget watts it cannot verify. Dell says an adapter "
                "reading 'Unknown' may not charge the pack properly or may "
                "charge it slowly; the walk models the strict case, where "
                "charge is disabled and "
                f"CPU and GPU are capped, about {throttled_w:.0f} W for the "
                f"whole machine. The pack holds at {w.pct:.0f}%. Recovery is "
                "physical: reseat the plug, inspect the centre pin, return to "
                "the Dell adapter."
            ),
            expert=(
                f"Unknown adapter: charge disabled, CPU/GPU capped, "
                f"~{throttled_w:.0f} W system. Pack holds."
            ),
        ),
        active=["dc-in", "ec", "cpu", "gpu"],
        system_w=throttled_w,
        target_pct=100.0,
        cpu_w=THROTTLED_CPU_W,
        gpu_w=THROTTLED_GPU_W,
        fan_pct=35.0,
        failed=["dc-in"],
        cycle_cost=2,
    )

    # ---- steady: the Dell adapter returns ---------------------------------
    w.adapter = good
    w.temp_c = 33.0
    w.emit(
        phase="steady",
        stage_id="d18-adapter-restored",
        label=f"Dell adapter back: {watts} W",
        description=L(
            novice=(
                f"The original adapter goes back in. The identity check "
                f"passes, the BIOS line reads {watts} W again, the power caps "
                "lift, and charging restarts only now, after the handshake "
                f"succeeds. It rejoins the slow curve at about "
                f"{taper_w(cc, 99.0):.0f} watts, the smallest trickle the "
                "charging chip will bother with."
            ),
            standard=(
                f"The Dell adapter returns. The PSID read succeeds, the BIOS "
                f"line reads {watts} W, the caps lift, and charge re-arms "
                "only after the handshake. It rejoins the taper near its "
                f"floor, about {taper_w(cc, 99.0):.0f} W."
            ),
            expert=(
                f"PSID valid again: caps lift, CV resumes at "
                f"~{taper_w(cc, 99.0):.0f} W."
            ),
        ),
        active=["dc-in", "ec", "charger", "battery"],
        system_w=rest_w,
        target_pct=99.0,
        fan_pct=25.0,
    )
    w.emit(
        phase="steady",
        stage_id="d19-full",
        label="Full: charge terminates",
        description=L(
            novice=(
                "The current the battery accepts has fallen to a few percent "
                "of the fast-charge rate, which is the charging chip's signal "
                "that the battery is full. It switches the charge off. The "
                "laptop now runs from the adapter alone. Four times in one "
                "sitting this battery was not charging at full speed, and "
                "only once was anything wrong."
            ),
            standard=(
                "Accepted current falls to a few percent of the CC rate, the "
                "charger IC's termination condition, and charge switches off. "
                "The system runs from the adapter alone. Four times in one "
                "sitting the pack was not filling at full speed; once was a "
                "fault."
            ),
            expert="Termination current reached: charge off, system on AC.",
        ),
        active=["dc-in", "ec", "battery"],
        system_w=rest_w,
        target_pct=100.0,
        fan_pct=22.0,
    )
    return w.states


def analyze_charge_diagnostics(
    profile: LaptopProfile,
    adapter: AdapterOption,
    trace: list[DiagnosticState],
) -> Summary:
    """The same Summary shape the plug-in trace reports, for the walk."""
    good, bad = walk_adapters(profile, adapter)
    hybrid_used = any(s.hybrid for s in trace)
    not_charging = [s for s in trace if s.phase != "off" and s.charge_w == 0]
    faults = sorted({s.charge_limiter for s in trace if s.failed_regions})
    notes = [
        f"{len(not_charging)} of {len(trace)} states are plugged in with zero "
        "charge power; the adapter is at fault in only the 'swap' phase.",
        "Check order: the BIOS AC Adapter line first (Unknown means the "
        "adapter or the centre pin), then the battery charge mode, then the "
        "pack temperature. What is left is the taper, which is normal.",
        f"This walk uses the {good.name} as the Dell adapter and the "
        f"{bad.name} as the third-party one. Start level, thermal mode and "
        "workload are fixed by the script.",
        "Regions drawn in the error colour: the pack from the moment it "
        f"passes its {PACK_CHARGE_LIMIT_C:g} °C charge limit until it cools "
        f"to the {PACK_CHARGE_RESUME_C:g} °C re-arm, and the DC-in jack while "
        f"the handshake fails ({', '.join(faults)}).",
        DIAGNOSTIC_SCENARIO.illustrative,
    ]
    return Summary(
        adapter_w=good.watts,
        peak_system_w=max(s.system_w for s in trace),
        peak_hybrid_w=max((s.battery_w for s in trace if s.hybrid), default=0.0),
        hybrid_used=hybrid_used,
        end_battery_pct=trace[-1].battery_pct,
        regime="adapter-limited" if hybrid_used else "within-budget",
        minutes_to_80_pct=None,
        notes=notes,
    )
