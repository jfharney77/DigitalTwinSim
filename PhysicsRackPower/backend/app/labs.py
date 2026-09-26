"""Graded labs for the rack PDU & UPS simulator (recipe: ``docs/LAB_PATTERN.md``;
pilot: ``DellPowerEdgeR760Thermal/backend/app/labs.py``).

A guided scenario sets the dials and tells you what to watch. A lab states a
goal and leaves the dials to you: build a Scenario with the ordinary controls,
the engine runs it, and ``grade_scenario`` scores the trace.

Pure module, same rule as ``engine.py`` and ``validation.py``: no FastAPI, no
IO, no clock, no randomness (AST-checked in ``tests/test_labs.py``). ``main.py``
is the only caller that touches HTTP, so the static-hosting build grades in
the browser by running this same file under Pyodide.

What is this app's own; everything else is ``twinkit.labs``:

* ``measure()`` — one run as named numbers. The un-gameable one is
  ``workRateW``: watts actually delivered to live outlets, averaged over the
  whole run. An empty rack, a tripped phase and a dark rack all deliver
  nothing for those seconds, so none of them is a way through. It is an
  illustrative proxy for useful work (a powered server at its set draw is a
  working server), not a benchmark, and is labeled so.
* ``LABS`` — three labs of rising difficulty, each the app's acceptance
  scenarios turned into a problem with a twist, every criterion citing the
  Explain entry (``presets.EXPLAINS``) and the equation it tests.
* ``REFERENCE_SOLUTIONS`` / ``GAMING_ATTEMPTS`` — a scenario that passes each
  lab, and the cheap tricks that must not. Server-side only: the API serves
  ``LABS``.
"""

from __future__ import annotations

from twinkit.labs import Criterion, Lab, LabGoal, LabResult, Objective, grade

from .engine import simulate
from .leveling import L
from .models import (
    Environment,
    RackConfig,
    RackLoad,
    Scenario,
    SimEvent,
    SimState,
    Summary,
    Validation,
)
from .validation import validate

# The equations, exactly as the Explain entries display them.
EQ_CURRENT = "I = P ÷ (V × PF)"
EQ_IMBALANCE = "imbalance = max|P_phase − avg| ÷ avg × 100"
EQ_TRIP = "heat += (I/I_rated)² − 1 per second → trips at threshold"
EQ_RUNTIME = "runtime = Wh_usable × η_inverter ÷ P_load × 60"
EQ_FADE = "capacity = 1 − rate × age × 2^((T−25) ÷ T_double)"

#: Lab 1's eight servers, in watts. The lab is a partition problem, so the
#: fleet is part of the question and ``fleetMismatchW`` measures any edit.
LAB_FLEET_W: tuple[float, ...] = (1400, 1200, 1100, 1000, 900, 800, 700, 500)

#: Lab 3's surge: a slot asking for at least this many watts is "at full tilt".
SURGE_SLOT_W = 2000.0
SURGE_SLOTS = 4

NO_FAILURE_S = 99999.0  # firstUtilityFailS when the utility never fails


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
    requested = [float(ld.power_w) for ld in cfg.loads]
    fleet = sorted(LAB_FLEET_W)

    n = len(trace)
    work = 0.0
    peak_pct = 0.0
    surge_seconds = 0
    fleet_mismatch = 0.0
    dark_seconds = 0
    off_seconds = 0
    first_fail = NO_FAILURE_S
    prediction_error = 100.0
    for s in trace:
        # Replay the set-load dial exactly as the engine applied it.
        while ei < len(events) and events[ei].at_s <= s.t:
            ev = events[ei]
            ei += 1
            if (
                ev.action == "set-load" and ev.index is not None
                and ev.value is not None and 0 <= ev.index < len(requested)
            ):
                requested[ev.index] = max(0.0, float(ev.value))
        work += s.pdu_input_w  # zero through an open breaker or a dark rack
        peak_pct = max(peak_pct, s.phase_a_pct, s.phase_b_pct, s.phase_c_pct)
        if sum(1 for w in requested if w >= SURGE_SLOT_W) >= SURGE_SLOTS:
            surge_seconds += 1
        fleet_mismatch = max(
            fleet_mismatch,
            sum(abs(a - b) for a, b in zip(sorted(requested), fleet)),
        )
        if not s.rack_powered:
            dark_seconds += 1
        if not s.utility_on:
            off_seconds += 1
            if first_fail == NO_FAILURE_S:
                first_fail = float(s.t)
                if s.actual_runtime_min > 0:
                    prediction_error = min(100.0, 100.0 * abs(
                        s.predicted_runtime_min - s.actual_runtime_min
                    ) / s.actual_runtime_min)

    return {
        "durationS": float(trace[-1].t),
        "workRateW": round(work / n, 1),
        "peakPhasePct": round(peak_pct, 1),
        "worstImbalancePct": float(summary.worst_imbalance_pct),
        "trippedPhases": float(len(summary.tripped_phases)),
        "darkSeconds": float(dark_seconds),
        "breakerAmps": float(cfg.breaker_amps),
        "fleetMismatchW": round(fleet_mismatch, 1),
        "surgeSeconds": float(surge_seconds),
        "firstUtilityFailS": first_fail,
        "utilityOffSeconds": float(off_seconds),
        "predictionErrorPct": round(prediction_error, 1),
        "batteryCapacityPct": round(100.0 * summary.battery_capacity_fraction, 1),
        "upsAgeYears": float(cfg.ups_age_years),
        "upsNameplateWh": float(cfg.ups_nameplate_wh),
        "roomTempC": float(scenario.environment.room_temp_c),
        "validationErrors": float(sum(1 for v in validations if v.level == "error")),
    }


# --- Criteria shared between labs ------------------------------------------

def _work(floor_w: int) -> Criterion:
    return Criterion(
        id="work", label=f"Delivered power at least {floor_w} W",
        metric="workRateW", op=">=", threshold=floor_w, unit="W",
        weight=2.0, guards_work=True, explain_id="phase-current",
        equation=EQ_CURRENT,
        why=L(
            standard=(
                f"Work is the watts that actually reach live outlets, averaged "
                f"over the whole run; {floor_w} W is the floor. A slot behind "
                "an open breaker, or any slot in a dark rack, delivers zero "
                "for those seconds, so unplugging servers is not a way "
                "through. The proxy is illustrative, not a benchmark."
            ),
            novice=(
                f"The rack has to keep its servers running — on average at "
                f"least {floor_w} watts must really arrive at the servers over "
                "the whole run. We count a server as working when it is "
                "getting the power it asks for. If a breaker (the safety "
                "switch on a power feed) opens, every server on that feed "
                "gets nothing, and if the whole rack goes dark nothing gets "
                "anything; those seconds count as zero. So you cannot pass by "
                "turning servers down or off. This is a simple stand-in for "
                "useful work, not a real benchmark."
            ),
            expert=(
                f"Mean PDU input over all ticks, tripped and dark ticks zero; "
                f"floor {floor_w} W. Illustrative proxy."
            ),
        ),
    )


def _no_trip() -> Criterion:
    return Criterion(
        id="no-trip", label="No breaker trips",
        metric="trippedPhases", op="<=", threshold=0, unit="phases", weight=2.0,
        explain_id="breaker-trip", equation=EQ_TRIP,
        why=L(
            standard=(
                "A breaker above its rating heats at (I/I_rated)² − 1 per "
                "second and opens at 60; below its rating it cools by 1 per "
                "second. A tripped phase takes every load on it down and "
                "does not reset."
            ),
            novice=(
                "Each power feed (phase) sits behind a breaker, a safety "
                "switch that opens when too much current flows for too long. "
                "A little over the limit it takes minutes to open; a lot over "
                "and it takes seconds. The simulator keeps a 'heat' score for "
                "each breaker: it climbs while the feed is over its rating, "
                "cools off while it is under, and the breaker opens when the "
                "score reaches 60. Once open it stays open, and every server "
                "on that feed is off."
            ),
            expert="Σ((I/I_r)² − 1)·dt < 60 on every phase; trips latch.",
        ),
    )


def _breaker_fixed(amps: int) -> Criterion:
    return Criterion(
        id="breaker-fixed", label=f"Breakers stay at {amps} A",
        metric="breakerAmps", op="<=", threshold=amps, unit="A",
        explain_id="phase-current", equation=EQ_CURRENT,
        why=L(
            standard=(
                f"The feed is a {amps} A circuit: at 230 V and PF 0.98 that is "
                "about 3,606 W per phase. A bigger breaker on the same wiring "
                "is not a fix, it is a fire."
            ),
            novice=(
                f"The building gives this rack three {amps}-amp feeds, and the "
                "wires in the wall are sized for that. Amps are watts divided "
                "by volts (230 V here, times a small correction called power "
                f"factor, 0.98), so {amps} A is about 3,606 W per feed. "
                "Choosing a bigger breaker would make the numbers look fine, "
                "but the wiring would be the thing that overheats instead, so "
                "the lab does not allow it."
            ),
            expert=f"I_rated ≤ {amps} A (≈3,606 W/phase at 230 V, PF 0.98).",
        ),
    )


def _continuous_rule() -> Criterion:
    return Criterion(
        id="continuous-rule", label="No phase above 80% of its breaker",
        metric="peakPhasePct", op="<=", threshold=80, unit="%", weight=2.0,
        explain_id="phase-current", equation=EQ_CURRENT,
        why=L(
            standard=(
                "A load that runs for hours may use at most 80% of the breaker "
                "rating (the NEC continuous-load rule): 12.8 A, about 2,885 W, "
                "on a 16 A phase. This is graded on the highest phase reading "
                "of the run."
            ),
            novice=(
                "Servers run all day, and a breaker that carries its full "
                "rating all day runs hot. The electrical code (the NEC, the "
                "US rulebook for wiring) therefore says a load that stays on "
                "for hours may use only 80% of the breaker's rating. On a "
                "16 A feed that is 12.8 A, which is about 2,885 W. The lab "
                "looks at the busiest moment of the busiest feed, and that "
                "reading must be 80% or lower."
            ),
            expert="max over ticks and phases of I/I_rated ≤ 0.80 (NEC continuous).",
        ),
    )


def _never_dark() -> Criterion:
    return Criterion(
        id="never-dark", label="Rack never goes dark",
        metric="darkSeconds", op="<=", threshold=0, unit="s", weight=2.0,
        explain_id="runtime", equation=EQ_RUNTIME,
        why=L(
            standard=(
                "On battery the rack lives for usable watt-hours × 0.93 "
                "inverter efficiency ÷ load. Usable means the faded capacity, "
                "not the nameplate; when it reaches zero every server drops "
                "at once."
            ),
            novice=(
                "When the wall power fails, the UPS (the battery box under "
                "the rack) carries the servers. How long it lasts is simple "
                "arithmetic: the energy really left in the battery, times "
                "0.93 because the converter that turns battery power into "
                "wall-style power wastes 7%, divided by how many watts the "
                "servers pull. The catch is 'really left': an old battery "
                "holds less than its label says. When it runs out, every "
                "server loses power in the same second."
            ),
            expert="No tick with rack_powered false: Wh_faded × 0.93 ÷ P must outlast the outage.",
        ),
    )


def _outage(first_s: int, off_s: int) -> list[Criterion]:
    return [
        Criterion(
            id="outage-early", label=f"Utility fails by t+{first_s} s",
            metric="firstUtilityFailS", op="<=", threshold=first_s, unit="s",
            explain_id="runtime", equation=EQ_RUNTIME,
            why=L(
                standard=(
                    "The lab is the outage. A failure in the last seconds of "
                    "the run tests nothing, so the utility has to drop within "
                    f"the first {first_s} s."
                ),
                novice=(
                    "This lab is about surviving a power cut, so the power "
                    f"cut has to happen, and early: within the first "
                    f"{first_s} seconds. The lab starts with one already "
                    "scheduled. If you press Reset or load a preset it "
                    "disappears; use 'Reset to the lab's start' to get it back."
                ),
                expert=f"First tick with utility off ≤ {first_s} s.",
            ),
        ),
        Criterion(
            id="outage-long", label=f"Utility stays off at least {off_s} s",
            metric="utilityOffSeconds", op=">=", threshold=off_s, unit="s",
            explain_id="runtime", equation=EQ_RUNTIME,
            why=L(
                standard=(
                    f"The outage lasts {off_s // 60} minutes or more. Runtime "
                    "is inversely proportional to load, so restoring the "
                    "utility early would let any battery pass."
                ),
                novice=(
                    f"The power cut has to last at least {off_s} seconds "
                    f"({off_s // 60} minutes). Any battery can survive a cut "
                    "that ends straight away, so switching the wall power "
                    "back on early does not count."
                ),
                expert=f"Ticks with utility off ≥ {off_s}.",
            ),
        ),
    ]


def _aged_pack(years: int, room_c: int, max_wh: int) -> list[Criterion]:
    return [
        Criterion(
            id="aged-pack", label=f"Battery is at least {years} years old",
            metric="upsAgeYears", op=">=", threshold=years, unit="y",
            explain_id="fade", equation=EQ_FADE,
            why=L(
                standard=(
                    f"The pack in this rack has {years} years on it. Age is "
                    "the multiplier in the fade equation you are being asked "
                    "to work with, not a term you may zero."
                ),
                novice=(
                    f"The battery in this lab is {years} years old, and "
                    "batteries lose capacity every year. The lab is about "
                    "coping with that, so sliding the age back to zero (a "
                    f"brand-new battery) is not allowed: keep it at {years} "
                    "years or more."
                ),
                expert=f"age ≥ {years} y; the fade term is given.",
            ),
        ),
        Criterion(
            id="hot-room", label=f"Room at least {room_c} °C",
            metric="roomTempC", op=">=", threshold=room_c, unit="°C",
            explain_id="fade", equation=EQ_FADE,
            why=L(
                standard=(
                    f"The UPS sits in a {room_c} °C room. The 2^((T−25) ÷ "
                    "T_double) term doubles VRLA's aging per +10 °C but "
                    "lithium's only per +20 °C, and that difference is the lab."
                ),
                novice=(
                    f"This UPS lives in a warm room, {room_c} °C, and heat "
                    "ages batteries faster. Lead-acid batteries (VRLA) age "
                    "twice as fast for every 10 °C above 25 °C; lithium ones "
                    "need 20 °C of extra heat to age twice as fast. Cooling "
                    "the room would be the easy answer, so the Room "
                    f"temperature slider has to stay at {room_c} °C or higher."
                ),
                expert=f"T_room ≥ {room_c} °C; T is given, T_double is the choice.",
            ),
        ),
        Criterion(
            id="real-pack", label=f"Battery nameplate at most {max_wh} Wh",
            metric="upsNameplateWh", op="<=", threshold=max_wh, unit="Wh",
            explain_id="runtime", equation=EQ_RUNTIME,
            why=L(
                standard=(
                    f"{max_wh} Wh is the largest pack this rack UPS takes. "
                    "Runtime scales with watt-hours, so an imaginary battery "
                    "would pass anything."
                ),
                novice=(
                    f"The biggest battery this UPS can hold is {max_wh} "
                    "watt-hours (a watt-hour is one watt for one hour). A "
                    "bigger battery always lasts longer, so the lab caps the "
                    "size at what the menu offers."
                ),
                expert=f"Wh_nameplate ≤ {max_wh}.",
            ),
        ),
    ]


def _loads(watts: list[float], phases: str, names: list[str] | None = None) -> list[RackLoad]:
    return [
        RackLoad(label=(names[i] if names else f"Server {i + 1}"), power_w=w, phase=p)  # type: ignore[arg-type]
        for i, (w, p) in enumerate(zip(watts, phases))
    ]


# --- Lab 1: eight unequal servers, three 16 A feeds ---------------------------

_FLEET_NAMES = ["DB 1", "DB 2", "App 1", "App 2", "App 3", "Web 1", "Web 2", "Log 1"]

_PARTITION_START = Scenario(
    config=RackConfig(
        loads=_loads(list(LAB_FLEET_W), "ABCABCAB", _FLEET_NAMES),
        breaker_amps=16, ups_chemistry="vrla", ups_nameplate_wh=2000,
        ups_age_years=1,
    ),
    environment=Environment(), duration_s=600,
)

PARTITION = Lab(
    id="three-feeds-eight-servers",
    title="Three feeds, eight unequal servers",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "Eight servers from 500 W to 1,400 W, 7,600 W in all, share "
                "three 16 A phases. Dealt out in order, phase A sits at 86% "
                "of its breaker. Re-plug them so every phase stays at or "
                "under the 80% continuous-load line, then get the imbalance "
                "as low as it will go."
            ),
            novice=(
                "A rack gets its power from three separate feeds, called "
                "phases A, B and C, each behind its own 16-amp breaker (a "
                "safety switch). This rack has eight servers of different "
                "sizes, from 500 W to 1,400 W, 7,600 W altogether. Someone "
                "plugged them in one after another — A, B, C, A, B, C — and "
                "feed A ended up carrying 86% of what its breaker allows. "
                "The rule for equipment that runs all day is 80% at most. "
                "Move servers between feeds (the A/B/C buttons beside each "
                "server) until every feed is at 80% or less, and then make "
                "the three feeds as equal as you can."
            ),
            expert=(
                "Partition {1400,1200,1100,1000,900,800,700,500} W over "
                "three 16 A phases: max phase ≤ 80%, then minimize imbalance."
            ),
        ),
        constraints=[
            L(standard="The eight servers keep their wattages; only the phase assignment is yours.",
              novice="Do not change how many watts any server draws. The servers are what they are; you only choose which feed each one plugs into.",
              expert="Fleet fixed; assignment free."),
            L(standard="Breakers stay at 16 A, and none may trip.",
              novice="Keep the 16-amp breakers (the wall wiring is sized for them), and no breaker may open during the run.",
              expert="16 A, no trips."),
            L(standard="No phase above 80% of its breaker at any point in the 600 s run.",
              novice="At no moment in the 600-second run may any feed read above 80% of its breaker.",
              expert="max I/I_rated ≤ 0.80 over 600 s."),
        ],
        delivered_work=L(
            standard="At least 7,500 W delivered to live outlets, averaged over the run.",
            novice="On average at least 7,500 watts must really reach the servers, so all eight have to stay plugged in and powered.",
            expert="workRateW ≥ 7500.",
        ),
    ),
    criteria=[
        _work(7500),
        _continuous_rule(),
        _no_trip(),
        Criterion(
            id="same-fleet", label="Server wattages unchanged",
            metric="fleetMismatchW", op="<=", threshold=0, unit="W",
            explain_id="imbalance", equation=EQ_IMBALANCE,
            why=L(
                standard=(
                    "Imbalance is about where watts sit, not how many there "
                    "are: moving a load changes P_phase and leaves the "
                    "average alone. Resizing the servers until they divide "
                    "evenly is a different rack, not a balanced one."
                ),
                novice=(
                    "Balancing means spreading the same servers more evenly "
                    "across the three feeds. If you change a server's watts "
                    "until the sums come out equal, you have not balanced "
                    "this rack, you have invented another one. The lab "
                    "compares your eight wattages with the eight it started "
                    "with; the difference must be zero."
                ),
                expert="Σ|sorted(P_slot) − sorted(fleet)| = 0 on every tick.",
            ),
        ),
        _breaker_fixed(16),
        Criterion(
            id="full-run", label="Run lasts at least 600 s",
            metric="durationS", op=">=", threshold=600, unit="s",
            explain_id="breaker-trip", equation=EQ_TRIP,
            why=L(
                standard=(
                    "Breaker heat accumulates: a mild overload takes minutes "
                    "to trip. A run shorter than the lab's 600 s could end "
                    "before a breaker that was going to open had opened."
                ),
                novice=(
                    "A breaker that is only a little overloaded can take "
                    "minutes to open. If the run were cut short, it could "
                    "finish before the breaker had its say, so the lab needs "
                    "the full 600 seconds it starts with."
                ),
                expert="600 s: longer than any trip the fleet can produce at 16 A.",
            ),
        ),
    ],
    objective=Objective(
        label="Worst phase imbalance", metric="worstImbalancePct",
        direction="minimize", par=2.7, worst=25.0, unit="%",
        explain_id="imbalance", equation=EQ_IMBALANCE,
    ),
    hints=[
        L(standard="Open Explain mode on the phase meters. 7,600 W over three phases averages 2,533 W, and the 80% line on 16 A is 2,885 W, so there is room — but only if no phase strays far from the average.",
          novice="Turn on Explain mode and look at the three phase meters. Your servers total 7,600 W; shared equally that would be about 2,533 W per feed. The 80% limit on a 16-amp feed is about 2,885 W. So a fair split fits comfortably — the trouble is only that feed A has far more than its share.",
          expert="avg 2,533 W/phase vs 2,885 W at 80%: feasible only near-balanced."),
        L(standard="Dealing servers out largest-first in A-B-C order always hands phase A the biggest of each round. Imbalance is the largest deviation from the average, so think in sums near 2,533 W, not in server counts: a phase with two big servers can equal one with three small ones.",
          novice="Plugging servers in A, B, C, A, B, C sounds fair, but when the list runs from biggest to smallest, feed A gets the biggest server of every round. What matters is the total watts on each feed, not how many servers it has. Two large servers can weigh the same as three small ones. Aim for each feed's total to land near 2,533 W.",
          expert="Count-balanced is not watt-balanced; target sums ≈ 2,533 W."),
        L(standard="The fleet cannot split exactly three ways (7,600 is not divisible into equal hundreds), so the best split is 2,500 / 2,500 / 2,600 W — about 2.6% imbalance. Find two groups that total 2,500 W; 1,400 + 1,100 is one of them.",
          novice="These eight servers cannot be split perfectly evenly, because every server is a whole number of hundreds of watts and 7,600 does not divide by three that way. The best possible is 2,500 W, 2,500 W and 2,600 W, which is about 2.6% imbalance. Look for groups that add up to 2,500 W: the 1,400 W and 1,100 W servers together make one such group.",
          expert="Optimum 2,500/2,500/2,600 W (2.6%); {1400,1100} is one bin."),
    ],
    start=_PARTITION_START.model_dump(by_alias=True),
)


# --- Lab 2: the honest front panel ------------------------------------------

_SIX_NAMES = ["Web 1", "Web 2", "DB 1", "DB 2", "App 1", "App 2", "Empty 7", "Empty 8"]


def _six(watts_each: float) -> list[RackLoad]:
    return _loads([watts_each] * 6 + [0, 0], "ABCABCCC", _SIX_NAMES)


_HOT = Environment(room_temp_c=35)
_FAIL_60 = SimEvent(at_s=60, action="utility-fail")

_PANEL_START = Scenario(
    config=RackConfig(
        loads=_six(1000), breaker_amps=16, ups_chemistry="vrla",
        ups_nameplate_wh=2000, ups_age_years=4,
    ),
    environment=_HOT, duration_s=900, events=[_FAIL_60],
)

HONEST_PANEL = Lab(
    id="honest-front-panel",
    title="Fourteen minutes on a four-year-old battery",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "A 6,000 W rack in a 35 °C room sits on a four-year-old "
                "2,000 Wh pack, and the utility fails 60 s into a 900 s run "
                "and does not come back. Keep the rack alive to the end, "
                "make the front panel's runtime prediction at the moment of "
                "failure true to within 5%, then carry as many watts "
                "through the outage as the battery honestly allows."
            ),
            novice=(
                "This rack draws 6,000 W and lives in a warm room (35 °C). "
                "Its UPS battery is four years old and is labelled 2,000 "
                "watt-hours. One minute into the run the wall power fails "
                "and stays off for the remaining 14 minutes. You have three "
                "jobs. First, the servers must stay on to the end. Second, "
                "at the moment the power fails, the runtime shown on the "
                "UPS front panel must be right to within 5% — out of the "
                "box it is not, because the panel trusts the label and the "
                "battery has aged. Third, once that works, see how many "
                "watts of servers this battery can really carry."
            ),
            expert=(
                "35 °C, 4 y pack ≤ 2,000 Wh, utility off from t+60 s to "
                "900 s: never dark, |predicted − actual| ≤ 5% at failure, "
                "maximize delivered W."
            ),
        ),
        constraints=[
            L(standard="The utility fails by t+120 s and stays off for at least 720 s.",
              novice="The power cut must start within the first 120 seconds and last at least 720 seconds (12 minutes). The lab starts with one scheduled at 60 seconds.",
              expert="Fail ≤ 120 s, off ≥ 720 s."),
            L(standard="Battery at least 4 years old, at most 2,000 Wh, in a room of at least 35 °C.",
              novice="Keep the battery at 4 years old or more, no bigger than 2,000 Wh, and keep the room at 35 °C or warmer. You may change what kind of battery it is.",
              expert="age ≥ 4 y, Wh ≤ 2,000, T ≥ 35 °C; chemistry free."),
            L(standard="The front panel's predicted runtime at the moment of failure is within 5% of the actual runtime.",
              novice="At the second the power fails, compare the two runtime numbers in the UPS panel: 'predicted (front panel)' and the actual one. They must agree to within 5%.",
              expert="Prediction error at failure ≤ 5%."),
            L(standard="No phase above 80% of its breaker, no trips, and the rack never goes dark.",
              novice="No feed above 80% of its breaker, no breaker opening, and the servers never lose power.",
              expert="≤ 80%/phase, no trips, never dark."),
        ],
        delivered_work=L(
            standard="At least 6,000 W delivered to live outlets, averaged over the run; more earns more.",
            novice="On average at least 6,000 watts must really reach the servers over the whole 900 seconds. Seconds after the battery runs out count as zero. Carrying more than 6,000 W raises your score.",
            expert="workRateW ≥ 6000; objective is the same metric.",
        ),
    ),
    criteria=[
        _work(6000),
        _never_dark(),
        Criterion(
            id="honest-panel", label="Runtime prediction within 5% at failure",
            metric="predictionErrorPct", op="<=", threshold=5, unit="%",
            weight=2.0, explain_id="fade", equation=EQ_FADE,
            why=L(
                standard=(
                    "Until a self-test has run, the front panel computes "
                    "runtime from nameplate watt-hours; the battery "
                    "discharges its faded watt-hours. The error is exactly "
                    "1 ÷ capacity − 1, whatever the chemistry, and a "
                    "self-test only runs while the utility is still on."
                ),
                novice=(
                    "The UPS front panel guesses how long the battery will "
                    "last. Until it has tested the battery, it uses the "
                    "number printed on the label. An aged battery holds less "
                    "than its label says, so the guess is too long — by "
                    "exactly as much as the battery has faded. A self-test "
                    "(the button in the UPS panel) briefly runs the rack on "
                    "the battery to measure what it really holds, and after "
                    "that the guess is right. It can only be run while the "
                    "wall power is still on, so it has to come before the "
                    "power cut, not after."
                ),
                expert="Error = 1 ÷ capacity − 1 until a self-test; self-test requires utility on.",
            ),
        ),
        *_outage(120, 720),
        *_aged_pack(4, 35, 2000),
        _continuous_rule(),
        _no_trip(),
    ],
    objective=Objective(
        label="Delivered power", metric="workRateW", direction="maximize",
        par=6900, worst=6000, unit="W",
        explain_id="runtime", equation=EQ_RUNTIME,
    ),
    hints=[
        L(standard="Run the start as it is and read the two runtimes in the UPS panel when the utility drops: the panel promises about 18.6 minutes and the rack is dark in under 10. Open Explain mode on the fade entry to see where the other half went.",
          novice="Press Run and grade, or just watch the start scenario play. When the power fails, the UPS panel shows two runtimes: the front panel promises about 18.6 minutes, but the rack goes dark in less than 10. Turn on Explain mode and read the 'fade' entry to see why the battery holds so much less than its label.",
          expert="Start: 18.6 min predicted, < 10 min delivered. See fade."),
        L(standard="Four VRLA years at 35 °C count as eight: 1 − 0.06 × 4 × 2 leaves 52%. Lithium loses 2% a year and its clock doubles per +20 °C, not +10: 1 − 0.02 × 4 × 1.41 leaves about 89%. Age and room are fixed; T_double is not.",
          novice="A lead-acid (VRLA) battery loses about 6% a year, and at 35 °C — ten degrees above the 25 °C it is rated for — it ages twice as fast. Four years count as eight: 6% × 8 = 48% gone, 52% left. A lithium battery loses about 2% a year and needs twenty extra degrees to age twice as fast, so the same four years in the same room leave about 89%. You cannot change the age or the room, but you can change the chemistry.",
          expert="VRLA: 52% left. Lithium: ≈ 89%. Chemistry is the free variable."),
        L(standard="Lithium alone survives, but the panel still over-promises by about 13% (1 ÷ 0.887 − 1). Pause before t+60 s and run a self-test while the utility is on; the prediction then uses the measured capacity.",
          novice="With a lithium battery the rack survives, but the front panel is still about 13% too hopeful, because it still trusts the label. Pause the playback, drag the time slider to somewhere before 60 seconds, and press Self-test in the UPS panel. It must happen while the wall power is still on. After that the prediction uses the measured capacity and matches reality.",
          expert="Lithium still errs ≈ 13% without a self-test; test before t+60 s."),
        L(standard="Now size the load with the runtime equation: about 1,774 Wh × 0.93 over a 14-minute outage is roughly 7,000 W, less the sliver the self-test spends. Six servers at 1,150 W (6,900 W) ride through; 7,050 W goes dark in the last seconds.",
          novice="Now use the runtime equation backwards. The lithium battery really holds about 1,774 Wh; times 0.93 for converter losses, spread over a 14-minute outage, that is roughly 7,000 W. The self-test itself uses a little energy, so stay slightly under. Six servers at 1,150 W each (6,900 W in total) make it to the end; at 7,050 W the rack goes dark a few seconds before the finish.",
          expert="P ≈ 1,774 × 0.93 ÷ (14/60) ≈ 7,000 W; 6,900 W passes, 7,050 W does not."),
    ],
    start=_PANEL_START.model_dump(by_alias=True),
)


# --- Lab 3: the surge on battery ------------------------------------------------

_GPU_NAMES = ["GPU 1", "GPU 2", "GPU 3", "GPU 4", "Web 1", "Web 2", "App 1", "App 2"]
_SURGE = (
    [SimEvent(at_s=120, action="set-load", index=i, value=2000) for i in range(4)]
    + [SimEvent(at_s=320, action="set-load", index=i, value=1300) for i in range(4)]
)
_SURGE_OUTAGE = _SURGE + [SimEvent(at_s=150, action="utility-fail")]


def _gpu_rack(phases: str, others_w: float, chemistry: str = "lithium",
              breaker: int = 16, age: float = 4, wh: int = 2000) -> RackConfig:
    return RackConfig(
        loads=_loads([1300] * 4 + [others_w] * 4, phases, _GPU_NAMES),
        breaker_amps=breaker, ups_chemistry=chemistry,  # type: ignore[arg-type]
        ups_nameplate_wh=wh, ups_age_years=age,
    )


_SURGE_START = Scenario(
    config=_gpu_rack("AAABCCCC", 300, chemistry="vrla"),
    environment=_HOT, duration_s=900, events=_SURGE_OUTAGE,
)

SURGE = Lab(
    id="surge-on-battery",
    title="A surge you cannot balance away",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "Four GPU servers idle at 1,300 W and surge to 2,000 W each "
                "from t+120 s to t+320 s; thirty seconds into the surge the "
                "utility fails for the rest of the 900 s run. Four 2,000 W "
                "servers cannot fit on three 16 A phases without one phase "
                "going over its rating. Get through with no trip and no "
                "dark rack on the four-year-old pack in the 35 °C room, "
                "then carry as much other load as both budgets allow."
            ),
            novice=(
                "Four GPU servers normally draw 1,300 W each. From 120 to "
                "320 seconds into the run a big job makes each of them draw "
                "2,000 W, and 30 seconds after that starts, the wall power "
                "fails and stays off until the run ends at 900 seconds. "
                "Here is the catch: a 16-amp feed can carry about 3,606 W, "
                "and you have four 2,000 W servers but only three feeds, so "
                "two of them must share a feed and push it over its limit "
                "for a while. A breaker tolerates a small overload for a "
                "limited time. Arrange the servers and choose the battery so "
                "that no breaker opens and the rack never loses power — in "
                "the same warm room, with the same four-year-old battery, "
                "as the previous lab. Then add as much load to the four "
                "smaller servers as you can get away with."
            ),
            expert=(
                "4 × 1,300→2,000 W for 200 s on 3 × 16 A, utility off from "
                "t+150 s, 35 °C, 4 y pack ≤ 2,000 Wh: no trip, never dark, "
                "maximize delivered W."
            ),
        ),
        constraints=[
            L(standard="The surge happens: four slots at 2,000 W or more for at least 200 s.",
              novice="The surge has to happen: four servers drawing 2,000 W or more for at least 200 seconds. The lab starts with it scheduled. Reset and the presets remove it; 'Reset to the lab's start' brings it back.",
              expert="≥ 4 slots at ≥ 2,000 W for ≥ 200 s."),
            L(standard="The utility fails by t+150 s and stays off for at least 720 s.",
              novice="The power cut must start within the first 150 seconds and last at least 720 seconds. The lab starts with one scheduled at 150 seconds.",
              expert="Fail ≤ 150 s, off ≥ 720 s."),
            L(standard="Breakers stay at 16 A; battery at least 4 years old, at most 2,000 Wh, room at least 35 °C.",
              novice="Keep the 16-amp breakers, keep the battery at 4 years old or more and 2,000 Wh or less, and keep the room at 35 °C or warmer.",
              expert="16 A; age ≥ 4 y, Wh ≤ 2,000, T ≥ 35 °C."),
            L(standard="No breaker trips and the rack never goes dark.",
              novice="No breaker may open, and the servers must never lose power.",
              expert="No trips, never dark."),
        ],
        delivered_work=L(
            standard="At least 7,000 W delivered to live outlets, averaged over the run; more earns more.",
            novice="On average at least 7,000 watts must really reach the servers over the whole 900 seconds. A feed whose breaker has opened delivers nothing, and neither does a dark rack. Carrying more than 7,000 W raises your score.",
            expert="workRateW ≥ 7000; objective is the same metric.",
        ),
    ),
    criteria=[
        _work(7000),
        _no_trip(),
        _never_dark(),
        Criterion(
            id="surge-happens", label="Four slots at 2,000 W for at least 200 s",
            metric="surgeSeconds", op=">=", threshold=200, unit="s",
            explain_id="breaker-trip", equation=EQ_TRIP,
            why=L(
                standard=(
                    "The surge is the lab. Two 2,000 W servers on one 16 A "
                    "phase run it at 111%, which heats the breaker at 0.23 "
                    "per second: 200 s spends 46 of the 60 it can take."
                ),
                novice=(
                    "The lab is about living through the surge, so the "
                    "surge must be in the run: four servers at 2,000 W or "
                    "more for 200 seconds. Two of them on one feed make "
                    "4,000 W, which is 111% of what a 16-amp breaker is "
                    "rated for. At 111% the breaker's heat score climbs by "
                    "about 0.23 every second, so 200 seconds uses up about "
                    "46 of the 60 points it can take before opening."
                ),
                expert="(1.109² − 1) × 200 s ≈ 46 < 60: the surge fits the I²t budget, once.",
            ),
        ),
        *_outage(150, 720),
        _breaker_fixed(16),
        *_aged_pack(4, 35, 2000),
    ],
    objective=Objective(
        label="Delivered power", metric="workRateW", direction="maximize",
        par=7800, worst=7000, unit="W",
        explain_id="runtime", equation=EQ_RUNTIME,
    ),
    hints=[
        L(standard="Run the start and read the event log. Three GPU servers share phase A: 3,900 W is already 108% before the surge and 6,000 W is 166% during it, so the breaker opens within a minute of t+120 s and three servers go dark while the battery has plenty left.",
          novice="Run the start scenario and read the event log under the rack. Three of the GPU servers are plugged into feed A. Even before the surge that is 3,900 W, already 108% of the breaker's rating; during the surge it is 6,000 W, 166%. The breaker opens less than a minute after the surge begins, and those three servers switch off — even though the battery still has plenty of energy.",
          expert="Start: phase A at 108% then 166%; trips within a minute of the surge."),
        L(standard="Overload is a time budget, not a wall. Open Explain mode on the breaker entry: heat grows with (I/I_rated)² − 1. At 166% that is 1.77 per second, 34 s to a trip. At 111% it is 0.23 per second, 260 s — longer than the 200 s surge.",
          novice="A breaker does not open the instant it is overloaded; it allows a small overload for a while. Turn on Explain mode and read the breaker entry: the heat score grows faster the further over the rating you are. At 166% it gains 1.77 a second and reaches 60 in about 34 seconds. At 111% it gains only 0.23 a second and would need 260 seconds — and the surge lasts only 200.",
          expert="166% → 34 s to trip; 111% → 260 s > 200 s surge."),
        L(standard="So put exactly two GPU servers on one phase, one on each of the others, and keep everything else off the doubled phase: even 150 W more there trips it before the surge ends. The battery is the previous lab's problem again: VRLA at 52% goes dark, lithium at about 89% does not.",
          novice="So let exactly two GPU servers share one feed, and give each of the other two its own feed. Put nothing else on the shared feed: even 150 W more makes the breaker open before the surge ends. The battery is the same problem as in the previous lab: the lead-acid pack has only 52% left and the rack goes dark, while a lithium pack of the same age still has about 89%.",
          expert="2/1/1 GPU split, nothing else on the doubled phase; lithium."),
        L(standard="Both budgets are now live. The other two phases have about 1,600 W of breaker room each during the surge, but the battery runs out first: with the four small servers at 500 W each the pack ends with about 16 Wh, and at 550 W the rack goes dark before t+900 s.",
          novice="Now raise the four smaller servers to earn a higher score. There are two limits. The two feeds with one GPU server each have about 1,600 W of room during the surge, so the breakers are not the problem. The battery is: with the four small servers at 500 W each, it finishes the run with only about 16 Wh left, and at 550 W each the rack goes dark just before 900 seconds.",
          expert="Battery binds before the breakers: 4 × 500 W passes, 4 × 550 W goes dark."),
    ],
    start=_SURGE_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [PARTITION, HONEST_PANEL, SURGE]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Reference solutions and the tricks that must not work -----------------
# Server-side only: GET /api/labs serves LABS, never these.

_SELF_TEST_30 = SimEvent(at_s=30, action="self-test")
_BEST_SPLIT = "AABCBCCB"  # 1400+1100 / 1200+800+500 / 1000+900+700


def _panel(watts_each: float, chemistry: str = "lithium", *, age: float = 4,
           wh: int = 2000, room: float = 35, events: list[SimEvent] | None = None,
           duration_s: int = 900) -> Scenario:
    return Scenario(
        config=RackConfig(
            loads=_six(watts_each), breaker_amps=16,
            ups_chemistry=chemistry,  # type: ignore[arg-type]
            ups_nameplate_wh=wh, ups_age_years=age,
        ),
        environment=Environment(room_temp_c=room), duration_s=duration_s,
        events=[_SELF_TEST_30, _FAIL_60] if events is None else events,
    )


def _surge(phases: str = "AABCBCBC", others_w: float = 500, *,
           chemistry: str = "lithium", breaker: int = 16, age: float = 4,
           wh: int = 2000, room: float = 35,
           events: list[SimEvent] | None = None) -> Scenario:
    return Scenario(
        config=_gpu_rack(phases, others_w, chemistry, breaker, age, wh),
        environment=Environment(room_temp_c=room), duration_s=900,
        events=_SURGE_OUTAGE if events is None else events,
    )


def _fleet(phases: str, watts: list[float] | None = None, *, breaker: int = 16,
           duration_s: int = 600) -> Scenario:
    return Scenario(
        config=RackConfig(
            loads=_loads(watts or list(LAB_FLEET_W), phases, _FLEET_NAMES),
            breaker_amps=breaker, ups_chemistry="vrla",
            ups_nameplate_wh=2000, ups_age_years=1,
        ),
        duration_s=duration_s,
    )


REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    "three-feeds-eight-servers": _fleet(_BEST_SPLIT),
    "honest-front-panel": _panel(1150),
    "surge-on-battery": _surge(),
}

GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "three-feeds-eight-servers": {
        "zero load": _fleet(_BEST_SPLIT, [0.0] * 8),
        "bigger breakers": _fleet("ABCABCAB", breaker=32),
        "resize the servers until they divide evenly": _fleet(
            "AAABBBCC", [950, 950, 950, 950, 950, 950, 1400, 1400]),
        "everything on the convenient outlet": _fleet("AAAABBCC"),
        "short run": _fleet(_BEST_SPLIT, duration_s=30),
        "unplug the big server": _fleet(
            "ABCABCAB", [0, 1200, 1100, 1000, 900, 800, 700, 500]),
    },
    "honest-front-panel": {
        "zero load": _panel(0),
        "lithium but no self-test": _panel(1150, events=[_FAIL_60]),
        "self-test but still VRLA": _panel(1000, "vrla"),
        "self-test after the lights go out": _panel(
            1150, events=[_FAIL_60, SimEvent(at_s=90, action="self-test")]),
        "cool the room": _panel(1000, "vrla", room=20),
        "a new battery": _panel(1000, "vrla", age=0),
        "a battery that does not exist": _panel(1000, "vrla", wh=20000),
        "restore the utility straight away": _panel(
            1150, events=[_SELF_TEST_30, _FAIL_60,
                          SimEvent(at_s=70, action="utility-restore")]),
        "fail the utility at the last tick": _panel(
            1150, events=[_SELF_TEST_30, SimEvent(at_s=899, action="utility-fail")]),
        "idle through the outage, load at the end": _panel(
            0, events=[_SELF_TEST_30, _FAIL_60] + [
                SimEvent(at_s=850, action="set-load", index=i, value=2000)
                for i in range(6)]),
        "too greedy": _panel(1200),
    },
    "surge-on-battery": {
        "zero load": Scenario(
            config=_gpu_rack("AABCBCBC", 0).model_copy(update={
                "loads": _loads([0.0] * 8, "AABCBCBC", _GPU_NAMES)}),
            environment=_HOT, duration_s=900,
            events=[SimEvent(at_s=150, action="utility-fail")]),
        "skip the surge": _surge(events=[SimEvent(at_s=150, action="utility-fail")]),
        "bigger breakers": _surge("AAABCCCC", 300, breaker=32),
        "balanced but still VRLA": _surge(chemistry="vrla"),
        "lithium but three GPUs on one phase": _surge("AAABCCCC", 300),
        "a little extra on the doubled phase": _surge("AABCABCB", 500),
        "restore the utility straight away": _surge(
            events=_SURGE_OUTAGE + [SimEvent(at_s=160, action="utility-restore")]),
        "no outage": _surge(events=_SURGE),
        "cool the room": _surge(chemistry="vrla", room=15),
        "a new battery": _surge(chemistry="vrla", age=0),
        "a battery that does not exist": _surge(chemistry="vrla", wh=20000),
        "too greedy": _surge(others_w=600),
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
