"""Graded labs for the PowerCool CDU loop simulator (``docs/LAB_PATTERN.md``).

A guided scenario sets the dials and tells you what to watch. A lab states a
goal and leaves the dials to you: build a Scenario with the ordinary controls,
the engine runs it, and ``grade_scenario`` scores the trace.

Pure module, same rule as ``engine.py`` and ``validation.py``: no FastAPI, no
IO, no clock, no randomness (AST-checked in ``tests/test_labs.py``). ``main.py``
is the only caller that touches HTTP, so a static-hosting build runs this same
grading in the browser from the same data.

Three things here are this app's own; everything else is ``twinkit.labs``:

* ``measure()`` — turns one run into named numbers. The un-gameable one is
  ``workRateKw``: banks online × 40 kW × requested utilization × the IRC's
  power cap, averaged over the whole run. An idle rack earns nothing, a
  capped rack earns less, and a tripped bank earns zero from the tick it
  latches off. It is an illustrative proxy for useful compute (idle heat is
  deliberately excluded — it warms the loop and computes nothing), not a
  benchmark, and is labeled so.
* ``LABS`` — three labs of rising difficulty, every criterion citing the
  Explain entry (``presets.EXPLAINS``) and the equation it tests.
* ``REFERENCE_SOLUTIONS`` / ``GAMING_ATTEMPTS`` — a scenario that passes each
  lab, and the cheap tricks that must not. They stay server-side: the API
  serves ``LABS`` only.
"""

from __future__ import annotations

from twinkit.labs import Criterion, Lab, LabGoal, LabResult, Objective, grade

from .constants import value as C
from .engine import simulate
from .leveling import L
from .models import (
    CduConfig,
    Environment,
    Scenario,
    SimEvent,
    SimState,
    Summary,
    Validation,
    Workload,
)
from .presets import FULL_RACK, FULL_TILT, NO_SPARE, PANIC
from .validation import validate

# The equations, exactly as the Explain entries display them.
EQ_APPROACH = "T_supply = T_facility + Q / (UA × (flow/nominal)^0.6)"
EQ_LOOP = "ΔT = Q / (ṁ × cp)"
EQ_PUMP = "Q_max(k) = Q₁ × k^0.65 · P_pump = k × P_max × speed³"
EQ_CHIP = "T_chip = T_supply + ΔT/2 + q_bank × R_th"
EQ_DEW = "T_supply ≥ max(setpoint, dew point + 2 K)"

WARM_C = 25.0  # lab 2 counts seconds with facility water at or above this


# --- Measurement ----------------------------------------------------------

def measure(
    scenario: Scenario,
    trace: list[SimState],
    summary: Summary,
    validations: list[Validation],
) -> dict[str, float]:
    """One run as named numbers. Keys are the wire names criteria refer to."""
    cfg = scenario.config
    events = sorted(scenario.events, key=lambda e: e.at_s)
    ei = 0
    util = scenario.workload.util_pct / 100.0
    group_kw = C("group_kw")
    work = 0.0
    for s in trace:
        # Replay the utilization dial exactly as the engine applied it.
        while ei < len(events) and events[ei].at_s <= s.t:
            ev = events[ei]
            ei += 1
            if ev.action == "set-util" and ev.value is not None:
                util = max(0.0, min(1.0, ev.value / 100.0))
        work += s.groups_online * group_kw * util * (s.cap_pct / 100.0)
    n = len(trace)
    return {
        "durationS": float(trace[-1].t),
        "workRateKw": round(work / n, 1),
        "cappedSeconds": float(summary.capped_seconds),
        "trips": float(summary.trips),
        "peakChipC": round(max(s.chip_temp_c for s in trace), 2),
        "minFacilitySupplyC": round(min(s.fac_supply_c for s in trace), 2),
        "warmSeconds": float(sum(1 for s in trace if s.fac_supply_c >= WARM_C)),
        "meanPumpKw": round(sum(s.pump_power_kw for s in trace) / n, 2),
        "allPumpsSeconds": float(sum(1 for s in trace if s.pumps_alive >= cfg.pumps)),
        "finalPumpsAlive": float(trace[-1].pumps_alive),
        "minDewMarginC": round(min(s.dew_margin_c for s in trace), 2),
        "validationErrors": float(sum(1 for v in validations if v.level == "error")),
    }


# --- Criteria shared between labs ------------------------------------------

def _work(floor_kw: int) -> Criterion:
    return Criterion(
        id="work", label=f"Delivered work at least {floor_kw} kW-compute",
        metric="workRateKw", op=">=", threshold=floor_kw, unit="kW-compute",
        weight=2.0, guards_work=True, explain_id="loop-dt", equation=EQ_LOOP,
        why=L(
            standard=(
                "Work is banks online × 40 kW × requested utilization × the "
                f"IRC's power cap, averaged over the run; {floor_kw} kW-compute "
                "is the floor. It is the useful part of the Q the loop carries: "
                "an idle rack, a capped rack and a tripped bank all deliver "
                "less, so turning the load down is not a way through. The "
                "proxy is illustrative, not a benchmark."
            ),
            novice=(
                "The rack has to do real computing the whole time — at least "
                f"{floor_kw} units. We count work as how many banks of "
                "computers are running, times 40 kW each, times how hard you "
                "ask them to work (the Utilization dial), times the power cap "
                "the controller allows. If the controller slows the banks "
                "down (capping) the work shrinks, and a bank that has "
                "switched itself off earns nothing at all. So you cannot win "
                "by leaving the rack idle. Every kilowatt of work also becomes "
                "a kilowatt of heat the coolant must carry away, which is why "
                "this line points at the loop's heat equation. It is a simple "
                "stand-in for useful computing, not a real benchmark score."
            ),
            expert=(
                f"Mean of online × 40 kW × util × cap over all ticks; floor "
                f"{floor_kw} kW-compute. Tripped banks earn zero. Illustrative proxy."
            ),
        ),
    )


def _no_capping() -> Criterion:
    return Criterion(
        id="no-capping", label="The IRC never caps the rack",
        metric="cappedSeconds", op="<=", threshold=0, unit="s", weight=2.0,
        explain_id="chip-temp", equation=EQ_CHIP,
        why=L(
            standard=(
                "The Integrated Rack Controller (IRC) sheds load whenever the "
                "silicon passes its 63 °C target, and every capped second is "
                "compute a tenant did not get. The silicon is a sum — supply, "
                "plus half the loop rise, plus the cold plate's share — so "
                "any of the three terms can be the one you shrink."
            ),
            novice=(
                "The rack's controller (Dell calls it the Integrated Rack "
                "Controller, or IRC) watches the chip temperature. If the "
                "chips pass 63 °C it slows every bank down a little to cool "
                "them — that is called capping, and in this lab even one "
                "second of it counts as a miss. The chip temperature is built "
                "from three parts added together: how warm the coolant "
                "arrives, how much it warms while crossing the rack, and a "
                "small extra step through the metal cold plate. Make any one "
                "of those parts smaller and the chips run cooler."
            ),
            expert="capped_seconds = 0: chip never exceeds target + 0.25 K under the coordinated policy.",
        ),
    )


def _no_trips() -> Criterion:
    return Criterion(
        id="no-trips", label="No tray bank trips off",
        metric="trips", op="<=", threshold=0, unit="banks", weight=2.0,
        explain_id="chip-temp", equation=EQ_CHIP,
        why=L(
            standard=(
                "With the IRC's policy switched off each bank rides its own "
                "65 °C firmware trip, and a tripped bank latches off for the "
                "rest of the run. The loop's 60-second lag keeps the "
                "survivors hot after the first trip, so more banks follow "
                "than the heat required."
            ),
            novice=(
                "Every bank of computers has its own safety switch: if its "
                "chips stay above 65 °C for several seconds, it powers itself "
                "off and stays off until someone visits it. That only happens "
                "when the rack-level controller is switched off "
                "('uncoordinated'). Worse, the coolant takes about a minute to "
                "cool down after one bank drops out, so the other banks stay "
                "hot and start switching off too. No bank may trip in this lab."
            ),
            expert="trips = 0; trips latch, and τ_loop = 60 s makes the cascade overshoot.",
        ),
    )


def _chip_ceiling(c: float, reason: str) -> Criterion:
    standard = {
        "target": (
            f"Peak silicon at or under {c:g} °C — the IRC's own target. It "
            "holds for either policy: switching the controller off does not "
            "buy hotter chips, it only removes the thing that was watching "
            "them."
        ),
        "trip": (
            f"Peak silicon at or under {c:g} °C, half a kelvin inside the "
            "65 °C trip line. A capped rack overshoots its 63 °C target "
            "briefly while the loop catches up; an uncapped one that runs "
            "this close to the trip line has no margin left at all."
        ),
    }[reason]
    novice = {
        "target": (
            f"The hottest the chips ever get must be {c:g} °C or lower. That "
            "is the temperature the rack's controller aims for. The rule "
            "applies even if you switch the controller off: turning off the "
            "thing that watches the chips does not make hot chips acceptable. "
            "Remember the chip temperature is the coolant's arrival "
            "temperature, plus half of how much the coolant warms up in the "
            "rack, plus a small step through the metal cold plate."
        ),
        "trip": (
            f"The hottest the chips ever get must be {c:g} °C or lower. The "
            "banks switch themselves off at 65 °C, so this keeps a small "
            "safety gap. When the controller is slowing the rack down, the "
            "chips drift a little above its 63 °C goal for a minute while the "
            "coolant catches up — that is fine. Running the chips right next "
            "to the 65 °C line with no controller is not."
        ),
    }[reason]
    return Criterion(
        id="chip-ceiling", label=f"Peak silicon at most {c:g} °C",
        metric="peakChipC", op="<=", threshold=c, unit="°C",
        explain_id="chip-temp", equation=EQ_CHIP,
        why=L(standard=standard, novice=novice,
              expert=f"max(T_chip) ≤ {c:g} °C, policy-independent."),
    )


def _facility_floor(c: int) -> Criterion:
    return Criterion(
        id="facility-floor", label=f"Facility water never below {c} °C",
        metric="minFacilitySupplyC", op=">=", threshold=c, unit="°C",
        explain_id="approach", equation=EQ_APPROACH,
        why=L(
            standard=(
                f"The building delivers {c} °C water and the lab does not let "
                "you order colder. Every temperature downstream is facility "
                "supply plus a rise, so T_facility is the one term you may "
                "not lower."
            ),
            novice=(
                f"The building's water arrives at {c} °C, and in this lab you "
                "are not allowed to make it colder. Colder building water "
                "would be the easy answer, because every temperature in the "
                "loop is the building water's temperature plus something — "
                f"so the Facility supply slider has to stay at {c} °C or "
                "higher for the whole run."
            ),
            expert=f"min(T_facility) ≥ {c} °C; the additive chain's first term is fixed.",
        ),
    )


def _full_run(seconds: int) -> Criterion:
    return Criterion(
        id="full-run", label=f"Run lasts at least {seconds} s",
        metric="durationS", op=">=", threshold=seconds, unit="s",
        explain_id="chip-temp", equation=EQ_CHIP,
        why=L(
            standard=(
                "The supply temperature trails the heat by a 60-second loop "
                "lag and the silicon trails the supply by another 15; a short "
                "run would be graded before the temperatures it is graded on "
                "had arrived."
            ),
            novice=(
                "Heat takes time. The coolant needs a few minutes to reach "
                "its final temperature after the load changes, and the chips "
                "follow a little behind it. If the run were shorter it would "
                "end before the chips reached the temperatures this lab is "
                "about, so the lab needs the full run length it starts with."
            ),
            expert="≥ 15 τ_loop: long enough for supply (τ 60 s) and silicon (τ 15 s) to settle.",
        ),
    )


def _valid_build() -> Criterion:
    return Criterion(
        id="valid-build", label="Build has no validation errors",
        metric="validationErrors", op="<=", threshold=0, unit="errors",
        explain_id="dew-floor", equation=EQ_DEW,
        why=L(
            standard=(
                "The validation panel's one hard error is a minimum-supply "
                "setpoint below the room's dew point + 2 K: a loop asked to "
                "run cold enough to condense on live electronics. Warnings "
                "are allowed; that error is not."
            ),
            novice=(
                "The panel on the left checks your build. Yellow warnings are "
                "allowed, red errors are not. The one red error in this app "
                "is asking for coolant colder than the room's dew point plus "
                "2 degrees — cold pipes 'sweat' like a cold drink in summer, "
                "and that water would drip onto live electronics."
            ),
            expert="Zero error-level findings (setpoint < dew + 2 K is the only one).",
        ),
    )


# --- Lab 1: the full rack on the leanest pumps ------------------------------

_LEAN_START = Scenario(
    config=FULL_RACK, workload=FULL_TILT, environment=Environment(), duration_s=900,
)

LEAN_PUMPS = Lab(
    id="full-rack-lean-pumps",
    title="Full rack, leanest pumps",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "Six banks flat out is about 240 kW against a 220 kW-class "
                "CDU, and at the default flow the IRC caps it. Run the full "
                "rack at full utilization with no capping and the silicon at "
                "or under 63 °C — then spend as little pump power as you can "
                "doing it."
            ),
            novice=(
                "A full rack of six banks makes about 240 kW of heat, a "
                "little more than this cooling unit is rated for. With the "
                "starting settings the chips get too warm and the controller "
                "slows the computers down. Your job: keep all six banks "
                "running at full speed with no slow-downs and the chips at "
                "63 °C or cooler. Then, once that works, use as little "
                "electricity in the coolant pumps as you can."
            ),
            expert=(
                "6 banks at 100%, capped_seconds = 0, peak chip ≤ 63 °C, "
                "T_facility ≥ 17 °C; minimize mean pump kW."
            ),
        ),
        constraints=[
            L(standard="No capping, no trips, and peak silicon at or under 63 °C.",
              novice="The controller must never slow the rack down, no bank may switch itself off, and the chips must never pass 63 °C.",
              expert="cap = 1 throughout, trips = 0, T_chip ≤ 63."),
            L(standard="Facility water stays at 17 °C or warmer; the run lasts 900 s.",
              novice="You may not make the building's water colder than 17 °C, and the run has to last its full 900 seconds.",
              expert="T_facility ≥ 17 °C, 900 s."),
            L(standard="No validation errors.",
              novice="No red errors in the build panel (yellow warnings are fine).",
              expert="Zero errors."),
        ],
        delivered_work=L(
            standard="At least 238 kW-compute averaged over the run — six banks at full utilization, uncapped.",
            novice="The rack must do at least 238 units of work on average. Only six banks at 100% load, never slowed down, reach that.",
            expert="workRateKw ≥ 238.",
        ),
    ),
    criteria=[
        _work(238),
        _no_capping(),
        _no_trips(),
        _chip_ceiling(63, "target"),
        _facility_floor(17),
        _full_run(900),
        _valid_build(),
    ],
    objective=Objective(
        label="Mean pump power", metric="meanPumpKw", direction="minimize",
        par=5.1, worst=7.3, unit="kW", explain_id="pump-flow", equation=EQ_PUMP,
    ),
    hints=[
        L(standard="The load is fixed by the work floor, so Q is fixed. Look at which terms of the silicon chain still move when Q does not: the approach and the loop rise both have flow in the denominator.",
          novice="You cannot lower the load here — the work floor needs all six banks at 100%. So look for something else that cools the chips. Open Explain mode and read 'Approach temperature' and 'Loop temperature rise': both get smaller when more coolant flows.",
          expert="Q is pinned; flow is the free variable in approach and ΔT/2."),
        L(standard="Raising the flow setpoint to 400 L/min clears the cap easily — and costs 7.3 kW of pumping against 4.5 kW at 340. Pump power goes with speed cubed, so the last few L/min are the expensive ones.",
          novice="Push the Flow setpoint all the way up to 400 and the slow-downs stop. But look at the pump power: about 7.3 kW instead of 4.5 kW. Pumps get expensive fast — doubling their speed costs eight times the electricity — so you have paid for more flow than you needed.",
          expert="400 L/min passes at 7.3 kW; P ∝ speed³ makes the margin expensive."),
        L(standard="Walk the setpoint back down until the silicon sits just under 63 °C. About 355 L/min does it at roughly 5.1 kW; 350 leaves the chips at 63.1 °C. Keep all three pumps — two pumps top out near 330 L/min and cost more per litre.",
          novice="Now lower the Flow setpoint a little at a time and grade again. Around 355 L/min the chips stay just under 63 °C and the pumps use only about 5.1 kW. At 350 the chips reach 63.1 °C, which is just too warm. Keep all three pumps installed: two pumps cannot push this much coolant, and they use more electricity for the same flow.",
          expert="≈355 L/min on 3 pumps: 62.7 °C at 5.1 kW. k = 2 saturates at 329 L/min."),
    ],
    start=_LEAN_START.model_dump(by_alias=True),
)


# --- Lab 2: ride out a chiller trip ------------------------------------------

_CHILLER_TRIP = [
    SimEvent(at_s=120, action="set-facility-supply", value=25),
    SimEvent(at_s=520, action="set-facility-supply", value=17),
]

_TRIP_START = Scenario(
    config=PANIC, workload=FULL_TILT, environment=Environment(),
    duration_s=900, events=_CHILLER_TRIP,
)

CHILLER_TRIP = Lab(
    id="ride-the-chiller-trip",
    title="Ride out a chiller trip",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "Two minutes in, a chiller trips and the facility water "
                "steps from 17 °C to 25 °C; it recovers at t+520 s. Keep "
                "every bank alive through it, keep the silicon half a kelvin "
                "inside the trip line, and deliver as much compute over the "
                "whole 900 s as the water allows."
            ),
            novice=(
                "Two minutes into the run, one of the building's chillers "
                "fails and the water reaching the cooling unit jumps from "
                "17 °C to 25 °C. Almost seven minutes later the chiller comes "
                "back. The rack starts with its controller switched off, and "
                "banks of computers overheat and switch themselves off. Your "
                "job: get through the warm spell with every bank still "
                "running, never let the chips pass 64.5 °C, and get as much "
                "computing done over the whole 900 seconds as you can."
            ),
            expert=(
                "T_facility 17→25 °C at t=120, back at t=520. trips = 0, "
                "peak chip ≤ 64.5 °C; maximize mean work over 900 s."
            ),
        ),
        constraints=[
            L(standard="No bank trips, and peak silicon stays at or under 64.5 °C. Capping is allowed.",
              novice="No bank may switch itself off, and the chips must never pass 64.5 °C. The controller IS allowed to slow the rack down in this lab.",
              expert="trips = 0, T_chip ≤ 64.5; capping permitted."),
            L(standard="The warm spell is real: at least 300 s with facility water at 25 °C or above, and never below 17 °C.",
              novice="The warm water has to really happen: at least 300 seconds with the building water at 25 °C or warmer, and never colder than 17 °C. (Reset to the lab's start brings the chiller trip back if you lose it.)",
              expert="≥ 300 s at T_facility ≥ 25 °C; min 17 °C."),
            L(standard="The run lasts 900 s, with no validation errors.",
              novice="The run has to last its full 900 seconds, with no red errors in the build panel.",
              expert="900 s, zero errors."),
        ],
        delivered_work=L(
            standard="At least 225 kW-compute averaged over the whole run, warm spell included.",
            novice="The rack must do at least 225 units of work on average across the whole run — including the warm minutes.",
            expert="workRateKw ≥ 225.",
        ),
    ),
    criteria=[
        _work(225),
        _no_trips(),
        _chip_ceiling(64.5, "trip"),
        Criterion(
            id="warm-spell", label="At least 300 s on 25 °C facility water",
            metric="warmSeconds", op=">=", threshold=300, unit="s",
            explain_id="approach", equation=EQ_APPROACH,
            why=L(
                standard=(
                    "The chiller trip is the lab. Eight kelvin of facility "
                    "water lands on the supply unchanged — the approach does "
                    "not care what the building is doing — so the disturbance "
                    "has to be in the trace for the grade to mean anything."
                ),
                novice=(
                    "The warm water is the whole point of this lab, so the "
                    "grader checks that it really happened: the building "
                    "water has to be at 25 °C or warmer for at least 300 "
                    "seconds. When the building water warms by 8 degrees, the "
                    "coolant going to the chips warms by the same 8 degrees, "
                    "because the heat exchanger always adds the same gap on "
                    "top. If you pressed Reset and lost the chiller trip, use "
                    "'Reset to the lab's start' to get it back."
                ),
                expert="≥ 300 ticks at T_facility ≥ 25 °C; +8 K passes to T_supply 1:1.",
            ),
        ),
        _facility_floor(17),
        _full_run(900),
        _valid_build(),
    ],
    objective=Objective(
        label="Delivered work", metric="workRateKw", direction="maximize",
        par=229.0, worst=225.0, unit="kW-compute",
        explain_id="chip-temp", equation=EQ_CHIP,
    ),
    hints=[
        L(standard="Watch the banks-online line in the start run. Each bank is protecting itself, and the loop's 60-second lag keeps the survivors hot after the first one drops. Look at the IRC policy control in the build panel.",
          novice="Play the starting run and watch the 'banks online' number fall. Each bank is looking after only itself, and because the coolant takes a minute to cool down, banks keep switching off even after enough heat has gone. Look in the build panel on the left for the controller's policy setting.",
          expert="Uncoordinated trips cascade past the required shed (τ_loop). Check the policy."),
        L(standard="Turning the load down yourself avoids the trips, but a fixed derate is paid for all 900 s, including the 500 s when the water was fine. The coordinated IRC caps only while the water is warm, and only by what the water requires.",
          novice="You could avoid the trouble by lowering the Utilization dial — but then the rack runs slowly for the whole run, even the 500 seconds when the water was perfectly cold. The 'coordinated' controller is smarter: it slows the rack down only while the water is warm, only as much as needed, and speeds back up afterwards.",
          expert="Static derate costs 900 s; coordinated capping costs ~400 s at the required depth."),
        L(standard="Coordinated at the default 340 L/min still falls short of the floor, because the cap has to cut deep. Flow shrinks the approach and the loop rise, so at 400 L/min the IRC sheds less for the same warm water: six banks, 100%, coordinated, 400 L/min delivers about 229.",
          novice="With the controller set to 'coordinated' nothing switches off, but the work still comes up short, because the controller has to slow the rack down a lot. Help it: raise the Flow setpoint to 400. More coolant flow means cooler chips for the same warm water, so the controller slows things down less. Six banks at 100%, coordinated, 400 L/min gives about 229 units of work.",
          expert="6 × 100%, coordinated, 400 L/min: ≈229 kW-compute, peak 64.2 °C."),
    ],
    start=_TRIP_START.model_dump(by_alias=True),
)


# --- Lab 3: a pump down on a warm day, inside a pump-power budget ----------------

_PUMP_FAIL = [SimEvent(at_s=60, action="fail-pump", index=0)]
_WARM = Environment(facility_supply_c=23)

_PUMP_START = Scenario(
    config=NO_SPARE, workload=FULL_TILT, environment=_WARM,
    duration_s=900, events=_PUMP_FAIL,
)

PUMP_DOWN = Lab(
    id="pump-down-warm-day",
    title="A pump down on a warm day",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "The facility is on 23 °C water and a pump fails at t+60 s "
                "and stays failed. Inside a 4 kW mean pump-power budget, with "
                "no capping and the silicon at or under 63 °C, deliver as "
                "much compute as the loop will carry."
            ),
            novice=(
                "It is a warm day: the building's water arrives at 23 °C. One "
                "minute into the run a coolant pump breaks and is not "
                "repaired. You also have an electricity budget for the "
                "pumps: 4 kW on average. Your job: keep the controller from "
                "ever slowing the rack down, keep the chips at 63 °C or "
                "cooler, stay inside the pump budget — and get as much "
                "computing done as you can."
            ),
            expert=(
                "T_facility ≥ 23 °C, one pump lost by t=100 for good, mean "
                "pump ≤ 4 kW, cap = 1, T_chip ≤ 63; maximize work."
            ),
        ),
        constraints=[
            L(standard="A pump fails within the first 100 s and stays failed: at most 100 s with every installed pump running.",
              novice="A pump must break in the first 100 seconds and stay broken — the run may have at most 100 seconds with all its pumps working. (Click a pump on the map to fail it; 'Reset to the lab's start' brings the failure back.)",
              expert="≤ 100 ticks with pumps_alive = installed."),
            L(standard="Mean pump power at or under 4 kW.",
              novice="The pumps may use at most 4 kW of electricity on average over the run.",
              expert="mean P_pump ≤ 4 kW."),
            L(standard="No capping, no trips, and peak silicon at or under 63 °C.",
              novice="The controller must never slow the rack down, no bank may switch itself off, and the chips must never pass 63 °C.",
              expert="cap = 1 throughout, trips = 0, T_chip ≤ 63."),
            L(standard="Facility water stays at 23 °C or warmer; 900 s; no validation errors.",
              novice="You may not make the building's water colder than 23 °C, the run lasts its full 900 seconds, and there are no red errors in the build panel.",
              expert="T_facility ≥ 23 °C, 900 s, zero errors."),
        ],
        delivered_work=L(
            standard="At least 165 kW-compute averaged over the run.",
            novice="The rack must do at least 165 units of work on average — roughly four banks flat out, or more banks run more gently.",
            expert="workRateKw ≥ 165.",
        ),
    ),
    criteria=[
        _work(165),
        Criterion(
            id="pump-lost", label="At most 100 s with every pump running",
            metric="allPumpsSeconds", op="<=", threshold=100, unit="s",
            explain_id="pump-flow", equation=EQ_PUMP,
            why=L(
                standard=(
                    "The failure is the lab: a pump must be lost early and "
                    "stay lost. What the survivors can deliver is Q₁ × k^0.65 "
                    "— one pump tops out near 210 L/min, two near 330 — so "
                    "how many you installed decides what is left."
                ),
                novice=(
                    "A broken pump is the whole point of this lab, so the "
                    "grader checks it: the run may have at most 100 seconds "
                    "with every installed pump working. Repairing the pump, "
                    "or breaking it only at the very end, does not count. How "
                    "much coolant the remaining pumps can push depends on how "
                    "many are left: one pump alone manages about 210 L/min, "
                    "two manage about 330."
                ),
                expert="Σ[pumps_alive = k_installed] ≤ 100 s. Q_max(1) = 210, Q_max(2) ≈ 330 L/min.",
            ),
        ),
        Criterion(
            id="pump-budget", label="Mean pump power at most 4 kW",
            metric="meanPumpKw", op="<=", threshold=4.0, unit="kW", weight=2.0,
            explain_id="pump-flow", equation=EQ_PUMP,
            why=L(
                standard=(
                    "Survivors ramp to hold the setpoint, and pump power goes "
                    "with speed cubed: two pumps holding 340 L/min run flat "
                    "out at 6 kW. The setpoint is a request, and after a "
                    "failure it is an expensive one."
                ),
                novice=(
                    "When a pump breaks, the others speed up to keep the same "
                    "coolant flow. Pumps get expensive fast when they speed "
                    "up: twice the speed costs eight times the electricity. "
                    "Two pumps trying to hold the starting 340 L/min run at "
                    "full speed and use 6 kW — over the 4 kW budget. The Flow "
                    "setpoint is only a request, and after a failure it is a "
                    "costly one."
                ),
                expert="P = k × P_max × s³; k = 2 at 340 L/min pins s = 1 → 6 kW.",
            ),
        ),
        _no_capping(),
        _no_trips(),
        _chip_ceiling(63, "target"),
        _facility_floor(23),
        _full_run(900),
        _valid_build(),
    ],
    objective=Objective(
        label="Delivered work", metric="workRateKw", direction="maximize",
        par=182.0, worst=165.0, unit="kW-compute",
        explain_id="chip-temp", equation=EQ_CHIP,
    ),
    hints=[
        L(standard="Start with the pumps. With two installed, the lone survivor tops out near 210 L/min whatever the setpoint says, and on 23 °C water that flow cannot carry 165 kW-compute under 63 °C. The spare pump is what makes the rest of the lab possible.",
          novice="Look at the pumps first. The lab starts with only two pumps, so after one breaks a single pump is left, and one pump can push only about 210 L/min no matter what you ask for. On this warm day that is not enough coolant to keep the chips under 63 °C at the work the lab needs. Install the third (spare) pump in the build panel.",
          expert="k = 1 → 210 L/min: infeasible at 23 °C for W ≥ 165. Install N+1."),
        L(standard="With three installed, two survive — and at 340 L/min they run flat out at 6 kW. Power goes with speed cubed: bring the setpoint down to about 290 L/min and the same two pumps draw about 4 kW.",
          novice="With three pumps, two are left after the failure. At the starting 340 L/min those two run at full speed and use 6 kW — too much. Lower the Flow setpoint: because pump electricity falls very quickly as the pumps slow down, about 290 L/min brings them to about 4 kW.",
          expert="k = 2: s = flow/329.5; 290 L/min ≈ 4.0 kW."),
        L(standard="Less flow means warmer silicon, so buy the margin back from the last term of the chain, q_bank × R_th: the same work spread across more banks puts less heat through each cold plate. Six banks at 76% on 290 L/min carry about 182 kW-compute; five banks have to run at 90% to get near that, and four cannot reach the floor at all.",
          novice="Less coolant flow makes the chips warmer, so you need to cool them another way. Look at the last part of the chip equation: the heat from each bank passing through its metal cold plate. If you spread the same work over more banks, each bank makes less heat and its chips run cooler. Try all six banks at 76% load with the flow at 290 L/min — that delivers about 182 units of work. Five banks have to run at 90% load to get close to that, and four banks cannot reach the work floor at all.",
          expert="Minimize q_bank × R_th: 6 banks × 76% at 290 L/min ≈ 182 kW-compute at 4.0 kW."),
    ],
    start=_PUMP_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [LEAN_PUMPS, CHILLER_TRIP, PUMP_DOWN]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Reference solutions and the tricks that must not work -----------------
# Server-side only: GET /api/labs serves LABS, never these.

def _cfg(banks: int, pumps: int, flow: int, policy: str = "coordinated") -> CduConfig:
    return CduConfig(tray_groups=banks, pumps=pumps, flow_setpoint_lpm=flow,
                     policy=policy)


_IDLE = Workload(util_pct=0)

REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    "full-rack-lean-pumps": Scenario(
        config=_cfg(6, 3, 355), workload=FULL_TILT, duration_s=900,
    ),
    "ride-the-chiller-trip": Scenario(
        config=_cfg(6, 3, 400), workload=FULL_TILT, duration_s=900,
        events=_CHILLER_TRIP,
    ),
    "pump-down-warm-day": Scenario(
        config=_cfg(6, 3, 290), workload=Workload(util_pct=76),
        environment=_WARM, duration_s=900, events=_PUMP_FAIL,
    ),
}

GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "full-rack-lean-pumps": {
        "zero load": Scenario(config=_cfg(6, 3, 200), workload=_IDLE, duration_s=900),
        "turn the load down a little": Scenario(
            config=_cfg(6, 3, 340), workload=Workload(util_pct=97), duration_s=900),
        "chill the building water": Scenario(
            config=_cfg(6, 3, 340), workload=FULL_TILT,
            environment=Environment(facility_supply_c=8), duration_s=900),
        "switch the controller off": Scenario(
            config=_cfg(6, 3, 340, "uncoordinated"), workload=FULL_TILT,
            duration_s=900),
        "short run": Scenario(
            config=_cfg(6, 3, 200), workload=FULL_TILT, duration_s=60),
        "long run at low load": Scenario(
            config=_cfg(6, 3, 200), workload=Workload(util_pct=10), duration_s=7200),
        "two pumps to save power": Scenario(
            config=_cfg(6, 2, 340), workload=FULL_TILT, duration_s=900),
    },
    "ride-the-chiller-trip": {
        "zero load": Scenario(config=_cfg(6, 3, 400), workload=_IDLE,
                              duration_s=900, events=_CHILLER_TRIP),
        "delete the chiller trip": Scenario(
            config=_cfg(6, 3, 400), workload=FULL_TILT, duration_s=900),
        "a one-second warm blip": Scenario(
            config=_cfg(6, 3, 400), workload=FULL_TILT, duration_s=900,
            events=[SimEvent(at_s=120, action="set-facility-supply", value=25),
                    SimEvent(at_s=121, action="set-facility-supply", value=17)]),
        "static derate, controller off": Scenario(
            config=_cfg(6, 3, 400, "uncoordinated"), workload=Workload(util_pct=92),
            duration_s=900, events=_CHILLER_TRIP),
        "static derate, controller on": Scenario(
            config=_cfg(6, 3, 400), workload=Workload(util_pct=88),
            duration_s=900, events=_CHILLER_TRIP),
        "coordinated at the default flow": Scenario(
            config=_cfg(6, 3, 340), workload=FULL_TILT, duration_s=900,
            events=_CHILLER_TRIP),
        "chilled water before and after": Scenario(
            config=_cfg(6, 3, 400), workload=FULL_TILT,
            environment=Environment(facility_supply_c=8), duration_s=900,
            events=[SimEvent(at_s=120, action="set-facility-supply", value=25),
                    SimEvent(at_s=520, action="set-facility-supply", value=8)]),
        "short run": Scenario(
            config=_cfg(6, 3, 400), workload=FULL_TILT, duration_s=100,
            events=_CHILLER_TRIP),
    },
    "pump-down-warm-day": {
        "zero load": Scenario(config=_cfg(6, 3, 200), workload=_IDLE,
                              environment=_WARM, duration_s=900, events=_PUMP_FAIL),
        "no pump failure": Scenario(
            config=_cfg(6, 3, 290), workload=Workload(util_pct=85),
            environment=_WARM, duration_s=900),
        "repair the pump": Scenario(
            config=_cfg(6, 3, 290), workload=Workload(util_pct=85),
            environment=_WARM, duration_s=900,
            events=_PUMP_FAIL + [SimEvent(at_s=61, action="restore-pump", index=0)]),
        "fail the pump at the end": Scenario(
            config=_cfg(6, 3, 290), workload=Workload(util_pct=85),
            environment=_WARM, duration_s=900,
            events=[SimEvent(at_s=899, action="fail-pump", index=0)]),
        "cool the building water": Scenario(
            config=_cfg(6, 3, 290), workload=Workload(util_pct=90),
            environment=Environment(facility_supply_c=17), duration_s=900,
            events=_PUMP_FAIL),
        "ignore the pump budget": Scenario(
            config=_cfg(6, 3, 340), workload=Workload(util_pct=82),
            environment=_WARM, duration_s=900, events=_PUMP_FAIL),
        "no spare, sized to the survivor": Scenario(
            config=_cfg(6, 2, 340), workload=Workload(util_pct=62),
            environment=_WARM, duration_s=900, events=_PUMP_FAIL),
        "switch the controller off and run hot": Scenario(
            config=_cfg(6, 3, 290, "uncoordinated"), workload=Workload(util_pct=80),
            environment=_WARM, duration_s=900, events=_PUMP_FAIL),
        "idle first, load later": Scenario(
            config=_cfg(6, 3, 290), workload=_IDLE, environment=_WARM,
            duration_s=900,
            events=_PUMP_FAIL + [SimEvent(at_s=800, action="set-util", value=100)]),
        "short run": Scenario(
            config=_cfg(6, 3, 290), workload=FULL_TILT, environment=_WARM,
            duration_s=100, events=_PUMP_FAIL),
    },
}


# --- Grading ----------------------------------------------------------------

def grade_scenario(lab_id: str, scenario: Scenario) -> LabResult:
    """Run the engine on the learner's scenario and grade the trace.

    Pure and deterministic: no state is kept between calls, and the same
    scenario always earns the same result. Raises ``KeyError`` for an
    unknown lab id (``main.py`` turns that into a 404).
    """
    lab = LABS_BY_ID[lab_id]
    trace, _log, summary = simulate(scenario)
    metrics = measure(scenario, trace, summary, validate(scenario))
    return grade(lab, metrics)
