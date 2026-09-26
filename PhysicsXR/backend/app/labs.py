"""Graded labs for the PowerEdge XR rugged-edge simulator
(recipe: ``docs/LAB_PATTERN.md``; pilot: ``DellPowerEdgeR760Thermal``).

A guided scenario sets the dials and tells you what to watch. A lab states a
goal and leaves the dials to you: build a Scenario with the ordinary controls,
the engine runs it, and ``grade_scenario`` scores the trace.

Pure module, same rule as ``engine.py`` and ``validation.py``: no FastAPI, no
IO, no clock, no randomness (AST-checked in ``tests/test_labs.py``). ``main.py``
is the only caller that touches HTTP, so the static-hosting build grades in
the browser from the same code and the same data.

Three things here are this app's own; everything else is ``twinkit.labs``:

* ``measure()`` — turns one run into named numbers. The un-gameable one is
  ``workRateW``: CPU utilization × (1 − throttle loss) × TDP, plus accelerator
  utilization × cards × card TDP on every tick the cards are not throttling,
  averaged over the whole run (dark seconds count as zero). An idle, throttled
  or tripped sled delivers nothing, so it passes nothing. It is an
  illustrative proxy for useful compute, not a benchmark, and is labeled so.
* ``LABS`` — three labs of rising difficulty built from the engine's
  acceptance scenarios (the fouled filter in a heat wave, the brownout at
  load) with a twist each, every criterion citing the Explain entry
  (``presets.EXPLAINS``) and the equation it tests.
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
    Environment,
    Scenario,
    SimEvent,
    SimState,
    Summary,
    Validation,
    Workload,
)
from .presets import CELL_SITE, FULL, IDLE
from .validation import validate

# The equations, exactly as the Explain entries display them.
EQ_CPU = "P_cpu = (P_idle + (TDP − P_idle) × util^1.4) × clamp"
EQ_ZONE = "T_out = T_in + Q / (ṁ × cp)"
EQ_FAN = "P_fan = N_alive × P_max × (rpm%)³ · CFM = f(rpm) × (1 − fouling)"
EQ_WALL = "P_wall = P_dc / η(load fraction)"
EQ_SAG = "I_input = P_wall / V_feed"

#: A tick counts as "in the sag" when the feed is at or below this % of nominal.
SAG_PCT = 65.0
#: A tick counts as "hot" when the ambient air is at or above this.
HOT_C = 45.0
#: The cell-site cabinet's feed breaker, in amps (illustrative). It is the
#: same number as one 800 W supply's input limit at 120 V — on purpose: a
#: bigger supply moves the supply's limit, never the site's.
BREAKER_A = 7.0


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
    wl = scenario.workload
    accel_tdp = C("accel_sw_tdp")
    work = 0.0
    sag_work = 0.0
    sag_ticks = 0
    first_sag = -1
    sag_inlet = 999.0
    for s in trace:
        # Replay the workload dial exactly as the engine applied it.
        while ei < len(events) and events[ei].at_s <= s.t:
            ev = events[ei]
            ei += 1
            if ev.action == "set-workload" and ev.workload is not None:
                wl = ev.workload
        tick = 0.0
        if s.powered_on:
            tick = (
                (wl.cpu_pct / 100.0)
                * (1.0 - s.perf_lost_pct / 100.0)
                * cfg.cpu_tdp_w
            )
            if not s.accel_throttling:
                tick += (
                    (wl.accel_pct / 100.0) * cfg.accels_single_wide * accel_tdp
                )
        work += tick
        if s.input_v_pct <= SAG_PCT:
            sag_ticks += 1
            sag_work += tick
            sag_inlet = min(sag_inlet, s.inlet_effective_c)
            if first_sag < 0:
                first_sag = s.t
    n = len(trace)
    on = [s for s in trace if s.powered_on]
    intact = (
        cfg.accels_single_wide >= 2 and cfg.io_card_w >= 100
        and cfg.dimms >= 8 and cfg.drives >= 2
    )
    return {
        "durationS": float(trace[-1].t),
        "workRateW": round(work / n, 1),
        "sagWorkRateW": round(sag_work / sag_ticks, 1) if sag_ticks else 0.0,
        "sagSeconds": float(sag_ticks),
        "firstSagS": float(first_sag),
        "minSagInletC": round(sag_inlet, 2) if sag_ticks else -99.0,
        "peakInputCurrentA": round(max(s.input_current_a for s in trace), 2),
        "peakCpuTempC": round(max(s.cpu_temp_c for s in trace), 2),
        "peakAccelTempC": round(max(s.accel_temp_c for s in trace), 2),
        "throttleSeconds": float(summary.throttle_seconds),
        "shutdown": 1.0 if summary.shutdown else 0.0,
        "meanWallW": round(sum(s.ac_power_w for s in trace) / n, 1),
        "meanFanW": round(sum(s.fan_power_w for s in trace) / n, 1),
        "meanPsuEfficiencyPct": round(
            100.0 * sum(s.psu_efficiency for s in on) / max(len(on), 1), 2
        ),
        "minInletC": round(min(s.inlet_effective_c for s in trace), 2),
        "hotSeconds": float(sum(1 for s in trace if s.inlet_effective_c >= HOT_C)),
        "minFoulingPct": round(min(s.fouling_pct for s in trace), 1),
        "buildIntact": 1.0 if intact else 0.0,
        "validationErrors": float(sum(1 for v in validations if v.level == "error")),
    }


# --- Criteria shared between labs ------------------------------------------

def _work(floor_w: int) -> Criterion:
    return Criterion(
        id="work", label=f"Delivered work at least {floor_w} W-TDP",
        metric="workRateW", op=">=", threshold=floor_w, unit="W-TDP",
        weight=2.0, guards_work=True, explain_id="cpu-power", equation=EQ_CPU,
        why=L(
            standard=(
                f"Work is CPU utilization × (1 − throttle loss) × TDP, plus "
                f"accelerator utilization × cards × 75 W on every second the "
                f"cards are not throttling, averaged over the run; {floor_w} "
                "W-TDP is the floor. An idle, throttled or tripped sled "
                "delivers less, so turning the load down is not a way "
                "through. The proxy is illustrative, not a benchmark."
            ),
            novice=(
                f"The machine has to do real work the whole time — at least "
                f"{floor_w} units. We count work as how hard you ask the "
                "processor to run (the CPU dial) times how big it is (its "
                "TDP, the watts it is built for), plus how hard you ask the "
                "two accelerator cards to run (the accelerator dial) times "
                "their size (75 W each). If the processor slows itself down "
                "to stay cool (throttling), that time counts for less; while "
                "the cards are throttling, their share counts for nothing; "
                "and a machine that has switched off earns nothing at all. "
                "So you cannot win by leaving the machine idle. This is a "
                "simple stand-in for useful computing, not a real benchmark "
                "score."
            ),
            expert=(
                f"Mean over all ticks of util × (1 − clamp loss) × TDP + "
                f"accel util × n × 75 W (zero while accel clamps; dark ticks "
                f"zero); floor {floor_w} W-TDP. Illustrative proxy."
            ),
        ),
    )


def _no_throttle() -> Criterion:
    return Criterion(
        id="no-throttle", label="No throttling at any point",
        metric="throttleSeconds", op="<=", threshold=0, unit="s", weight=2.0,
        explain_id="zone-outlet", equation=EQ_ZONE,
        why=L(
            standard=(
                "The CPU clamps above 98 °C and the accelerator cards above "
                "92 °C, and they sit in separate air lanes behind the fan "
                "wall: the CPU and its DIMMs in one, the cards and the "
                "fronthaul NIC in the other. Each part's temperature is its "
                "own lane's air plus its own watts, so the part that "
                "throttles is cooled only by turning down the heat in its "
                "own lane."
            ),
            novice=(
                "When a chip gets too hot it protects itself by slowing "
                "down. That is called throttling. The processor does it "
                "above 98 °C and the accelerator cards above 92 °C. Here is "
                "the part people miss: behind the fans the air splits into "
                "two lanes. One lane cools the processor and the memory. The "
                "other cools the accelerator cards and the network card. "
                "Heat made in one lane never reaches the other, so look at "
                "which part is actually throttling (the event log says) and "
                "turn down the heat in that part's lane."
            ),
            expert=(
                "Clamp at 98 °C (CPU) / 92 °C (accel). Split lanes: CPU + "
                "DIMMs vs accel + NIC; Q is per lane."
            ),
        ),
    )


def _stays_up() -> Criterion:
    return Criterion(
        id="stays-up", label="Sled stays powered on",
        metric="shutdown", op="<=", threshold=0, unit="", weight=2.0,
        explain_id="brownout", equation=EQ_SAG,
        why=L(
            standard=(
                "Input current over the supply's limit for 3 seconds trips "
                "it, a feed below 60% of nominal drops it at once, and "
                "sustained critical temperature powers the sled off. A dark "
                "sled draws nothing and delivers nothing."
            ),
            novice=(
                "The machine must stay switched on for the whole run. It can "
                "switch itself off in three ways: by pulling more electrical "
                "current than its power supply allows for three seconds in a "
                "row, by losing so much feed voltage (below 60%) that the "
                "supply simply drops out, or by getting dangerously hot. A "
                "machine that is off uses no power, but it also does no "
                "work, so it cannot pass."
            ),
            expert="No input-overcurrent trip (3 s), no deep-sag dropout (<60%), no overtemp power-off.",
        ),
    )


def _build_intact() -> Criterion:
    return Criterion(
        id="build-intact", label="The cell-site build is intact",
        metric="buildIntact", op=">=", threshold=1, unit="",
        explain_id="zone-outlet", equation=EQ_ZONE,
        why=L(
            standard=(
                "Every part removed is watts off Q — true, and not the "
                "lesson. The site still needs both accelerator cards, the "
                "100 W fronthaul NIC, all 8 DIMMs and at least 2 drives. The "
                "CPU tier, the power supplies and every workload dial are "
                "yours to change."
            ),
            novice=(
                "Pulling parts out does save power and heat, because every "
                "part adds some. But a cell site with no radio network card "
                "is not a cell site. So these must stay: both accelerator "
                "cards, the 100 W network card (the 'fronthaul NIC' that "
                "talks to the radios), all 8 memory modules, and at least 2 "
                "drives. You are free to change the processor size, the "
                "power supplies, and every workload dial."
            ),
            expert="accels ≥ 2, NIC ≥ 100 W, DIMMs ≥ 8, drives ≥ 2. De-population is out of scope.",
        ),
    )


def _valid_build() -> Criterion:
    return Criterion(
        id="valid-build", label="Build has no validation errors",
        metric="validationErrors", op="<=", threshold=0, unit="errors",
        explain_id="zone-outlet", equation=EQ_ZONE,
        why=L(
            standard=(
                "The validation panel's errors are builds Dell does not "
                "offer: a CPU wattage the platform has no tier for, or the "
                "extended −20…65 °C envelope on a build that does not "
                "qualify for it. Warnings are allowed; errors are not."
            ),
            novice=(
                "The panel on the left checks your build against Dell's own "
                "rules, and red errors mean Dell does not sell that "
                "combination — for example a processor size this machine "
                "does not come with, or the special extra-wide temperature "
                "rating on a build that is not allowed to have it. Yellow "
                "warnings are fine; red errors are not."
            ),
            expert="Zero error-level findings (CPU tier, extended-envelope select-config rule).",
        ),
    )


def _full_run(seconds: int) -> Criterion:
    return Criterion(
        id="full-run", label=f"Run lasts at least {seconds} s",
        metric="durationS", op=">=", threshold=seconds, unit="s",
        explain_id="zone-outlet", equation=EQ_ZONE,
        why=L(
            standard=(
                "Silicon settles in about a minute but the fan loop takes "
                "several; a short run would be graded before the "
                "temperatures and fan watts it is graded on had arrived."
            ),
            novice=(
                "Heat takes time. The chips warm up in about a minute, and "
                "the fans then spend several more minutes finding the speed "
                "that holds the temperature steady. If the run were shorter "
                "it would end before the machine reached the state this lab "
                "is about, so the lab needs the full run length it starts "
                "with."
            ),
            expert="Long enough for the silicon τ and the fan loop to settle.",
        ),
    )


def _hot_afternoon() -> Criterion:
    return Criterion(
        id="hot-afternoon", label="At least 600 s at 45 °C ambient or hotter",
        metric="hotSeconds", op=">=", threshold=600, unit="s",
        explain_id="zone-outlet", equation=EQ_ZONE,
        why=L(
            standard=(
                "The afternoon is the lab: 45 °C is inside the sled's "
                "−5…55 °C rating and far outside any data hall. Every "
                "temperature in the box is ambient plus a rise, so T_in is "
                "the one term you may not lower."
            ),
            novice=(
                "This lab is about a hot afternoon, so the outside air has "
                "to be 45 °C or hotter for at least 600 seconds of the run. "
                "The machine is rated for up to 55 °C, so this is allowed — "
                "just hard. Every part inside is as hot as the outside air "
                "plus whatever heat the part adds, so cooling the air would "
                "be the easy answer, and the lab does not allow it. Leave "
                "the afternoon heat step in place (or set the Ambient "
                "slider to 45 °C or more)."
            ),
            expert="≥ 600 ticks with T_in ≥ 45 °C; T_in is fixed by the site.",
        ),
    )


def _fouled() -> Criterion:
    return Criterion(
        id="fouled-filter", label="Filter fouling never below 40%",
        metric="minFoulingPct", op=">=", threshold=40, unit="%", weight=2.0,
        explain_id="fan-power", equation=EQ_FAN,
        why=L(
            standard=(
                "Nobody can reach the site today. Six months of heavy dust "
                "is 42% added resistance, so every rpm delivers 42% less "
                "air, and the fans pay for the difference at rpm³ until "
                "they pin at 100%. Changing the filter would fix it — and "
                "fails this line."
            ),
            novice=(
                "The dust filter has not been changed for six months at a "
                "very dusty site, and today nobody can drive out to change "
                "it. The dust blocks 42% of the air, so the fans must spin "
                "much faster to push the same air through — and fan power "
                "rises very steeply with speed (twice the speed costs eight "
                "times the power) until the fans are flat out. Clicking the "
                "filter to change it would be the easy fix, which is why it "
                "fails this line: the filter must stay at least 40% blocked "
                "for the whole run."
            ),
            expert="min fouling ≥ 40% (heavy × 6 months = 42%); no clean-filter.",
        ),
    )


def _sag_happens() -> Criterion:
    return Criterion(
        id="sag-happens", label="The feed sags to 65% or lower for at least 10 s",
        metric="sagSeconds", op=">=", threshold=10, unit="s", weight=2.0,
        explain_id="brownout", equation=EQ_SAG,
        why=L(
            standard=(
                "No brownout, no lab. At 65% of nominal the same wall watts "
                "need 1 ÷ 0.65 ≈ 1.54× the current, for ten seconds — long "
                "enough to outlast the 3-second trip delay."
            ),
            novice=(
                "This lab is about a brownout, so one has to happen: the "
                "feed voltage must drop to 65% of normal (or lower) for at "
                "least 10 seconds. When voltage drops, the machine pulls "
                "more current to get the same power — about one and a half "
                "times as much at 65%. Ten seconds is long enough that the "
                "power supply's three-second patience runs out. Use the "
                "brownout button, or keep the one the lab starts with."
            ),
            expert="≥ 10 ticks at V ≤ 65%: I × 1.54, beyond the 3 s trip delay.",
        ),
    )


def _sag_after(seconds: int) -> Criterion:
    return Criterion(
        id="sag-settled", label=f"The sag arrives at t+{seconds} s or later",
        metric="firstSagS", op=">=", threshold=seconds, unit="s",
        explain_id="fan-power", equation=EQ_FAN,
        why=L(
            standard=(
                "A sag at cold start meets fans still near their floor and "
                "chips that have not warmed up, so the wall draw it "
                "multiplies is smaller than the one the site really runs "
                f"at. The brownout has to land on the settled machine, "
                f"t+{seconds} s or later."
            ),
            novice=(
                "In the first minutes of a run the machine is still warming "
                "up and its fans are still slow, so it uses less power than "
                "it will later. A brownout that early would be an easier "
                "test than the real one. So the first brownout must come "
                f"at {seconds} seconds or later, when the fans have reached "
                "the speed the heat really needs. (If no brownout happens at "
                "all, this line fails too.)"
            ),
            expert=f"First V ≤ 65% tick at t ≥ {seconds} s: fan loop settled, P_fan at its real value.",
        ),
    )


def _sag_work(floor_w: int) -> Criterion:
    return Criterion(
        id="sag-work", label=f"At least {floor_w} W-TDP of work during the sag itself",
        metric="sagWorkRateW", op=">=", threshold=floor_w, unit="W-TDP",
        weight=2.0, guards_work=True, explain_id="brownout", equation=EQ_SAG,
        why=L(
            standard=(
                "Ride-through is a function of the load at the moment the "
                "sag arrives. Idling through the ten seconds and working "
                "the rest of the run would pass the average and miss the "
                f"point, so the sag seconds carry the same {floor_w} W-TDP "
                "floor on their own."
            ),
            novice=(
                "Whether a machine survives a brownout depends on how busy "
                "it is at that moment: an idle machine sails through. So it "
                "would be cheating to go quiet for the ten seconds of the "
                "brownout and work hard the rest of the time. This line "
                f"checks the work done during the brownout itself: it must "
                f"also be at least {floor_w} units."
            ),
            expert=f"Mean work over V ≤ 65% ticks ≥ {floor_w} W-TDP; no load-shedding through the sag.",
        ),
    )


def _breaker() -> Criterion:
    return Criterion(
        id="breaker", label="Peak input current 7 A or less",
        metric="peakInputCurrentA", op="<=", threshold=BREAKER_A, unit="A",
        weight=2.0, explain_id="brownout", equation=EQ_SAG,
        why=L(
            standard=(
                "The cabinet's feed breaker is 7 A (illustrative). At 65% of "
                "a 120 V feed that is 7 × 78 = 546 W at the wall while the "
                "sag lasts. A bigger or second supply raises the supply's "
                "own input limit and does nothing for the breaker upstream "
                "of it; only fewer wall watts during the sag does."
            ),
            novice=(
                "The cabinet this machine lives in has a 7-amp breaker on "
                "its power feed (an illustrative number). Current is power "
                "divided by voltage. In the brownout the voltage is only "
                "78 V (65% of 120 V), so 7 amps is just 546 watts at the "
                "wall. Buying a bigger power supply, or a second one, stops "
                "the supply from switching itself off — but the breaker is "
                "outside the machine and does not care. The only thing that "
                "lowers the current is drawing fewer watts while the "
                "voltage is down."
            ),
            expert="max I_input ≤ 7 A: P_wall ≤ 546 W at 78 V. PSU sizing moves the PSU limit, not the breaker.",
        ),
    )


def _cabinet_air(c: int) -> Criterion:
    return Criterion(
        id="cabinet-air", label=f"Ambient air never below {c} °C",
        metric="minInletC", op=">=", threshold=c, unit="°C",
        explain_id="fan-power", equation=EQ_FAN,
        why=L(
            standard=(
                f"The cabinet is {c} °C. Colder air would let the fans idle, "
                "and fan watts are wall watts — a cheaper brownout than the "
                "one this site gets."
            ),
            novice=(
                f"The air in this cabinet is {c} °C, and the Ambient slider "
                f"must stay at {c} °C or higher for the whole run. Colder "
                "air would let the fans slow down, and slow fans use less "
                "electricity, which would make the brownout easier than it "
                "really is at this site."
            ),
            expert=f"min T_in ≥ {c} °C; no buying P_fan back with ambient.",
        ),
    )


_KEEP_THE_BUILD = L(
    standard="Keep both accelerator cards, the 100 W fronthaul NIC, 8 DIMMs and 2 drives.",
    novice=(
        "Do not pull parts out to save power or heat: keep both accelerator "
        "cards, the 100 W network card, all 8 memory modules and at least 2 "
        "drives."
    ),
    expert="accels ≥ 2, NIC ≥ 100 W, DIMMs ≥ 8, drives ≥ 2.",
)


# --- The stage the labs share ------------------------------------------------

_DUSTY = Environment(inlet_c=38, dust="heavy", filter_months=6)
_HEAT_STEP = SimEvent(at_s=300, action="set-inlet", value=45)
_CABINET = Environment(inlet_c=30)


def _sag(at_s: int) -> SimEvent:
    return SimEvent(at_s=at_s, action="voltage-sag", value=65, seconds=10)


# --- Lab 1: six months of dust, one hot afternoon ---------------------------

_DUST_START = Scenario(
    config=CELL_SITE, workload=FULL, environment=_DUSTY,
    duration_s=900, events=[_HEAT_STEP],
)

DUST_AND_HEAT = Lab(
    id="dust-and-heat",
    title="Six months of dust, one hot afternoon",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "The filter is six months fouled, the afternoon steps to "
                "45 °C, and nobody can reach the site. Deliver at least 290 "
                "W-TDP of work for the full 900 seconds without one second "
                "of throttling — then push the work as high as it will go."
            ),
            novice=(
                "A cell-site computer sits in a dusty cabinet. Its air "
                "filter should have been changed six months ago, and this "
                "afternoon the outside air climbs to 45 °C. Nobody can "
                "drive out to help. Your job: keep the machine doing real "
                "work (at least 290 units) for the whole 900 seconds, and "
                "never let any chip slow itself down to stay cool. You may "
                "not change the filter or cool the air. Once that works, "
                "see how much more work you can get."
            ),
            expert=(
                "Fouling ≥ 40%, ≥ 600 s at T_in ≥ 45 °C, work ≥ 290 W-TDP "
                "over 900 s, zero clamp; maximize work."
            ),
        ),
        constraints=[
            L(standard="At least 600 seconds at 45 °C ambient or hotter.",
              novice="The outside air must be 45 °C or hotter for at least 600 seconds: leave the afternoon heat step alone, or set the Ambient slider to 45 °C or more.",
              expert="≥ 600 s at T_in ≥ 45 °C."),
            L(standard="The filter stays at least 40% fouled for the whole run: no filter change.",
              novice="Do not change the filter, and do not pick a cleaner site: the filter must stay at least 40% blocked from start to finish.",
              expert="min fouling ≥ 40%."),
            L(standard="No throttling, no shutdown, no validation errors, full 900-second run.",
              novice="No chip may throttle (slow itself down), the machine may not switch off, the build panel may show no red errors, and the run must be the full 900 seconds it starts with.",
              expert="Zero clamp, no trip, zero errors, 900 s."),
            _KEEP_THE_BUILD,
        ],
        delivered_work=L(
            standard="At least 290 W-TDP of CPU plus accelerator work, averaged over the 900-second run.",
            novice="The processor and the two accelerator cards together must average at least 290 units of work over the fifteen-minute run — for example the 205 W processor flat out plus both 75 W cards at a little under 60%.",
            expert="workRateW ≥ 290 over 900 s.",
        ),
    ),
    criteria=[
        _work(290),
        _hot_afternoon(),
        _fouled(),
        _no_throttle(),
        _stays_up(),
        _build_intact(),
        _full_run(900),
        _valid_build(),
    ],
    objective=Objective(
        label="Delivered work", metric="workRateW", direction="maximize",
        par=307, worst=290, unit="W-TDP", explain_id="zone-outlet",
        equation=EQ_ZONE,
    ),
    hints=[
        L(standard="Run the start as it is and read the event log: something throttles within the first minutes. Note which part it is.",
          novice="Press Run and grade once without changing anything, then read the event log under the picture. It tells you which chip started throttling. Is it the processor, or the accelerator cards?",
          expert="Read the log: which clamp engages?"),
        L(standard="It is the accelerators, not the CPU. Turning the CPU dial down costs work and changes nothing: the cards share an air lane with the 100 W NIC, and the CPU's heat never enters it.",
          novice="It is the accelerator cards that throttle, not the processor. The obvious move — turning the CPU dial down — loses work and does not help at all, because the processor sits in a different air lane. The cards share their lane with the 100 W network card, and only heat made in that lane reaches them.",
          expert="Accel clamp; split lanes. CPU util is irrelevant to lane B."),
        L(standard="Leave the CPU at 100% and bring the accelerator dial down until the cards hold under 92 °C with the fans pinned — about 68%. That is 205 + 102 = 307 W-TDP.",
          novice="Put the CPU dial back to 100% and lower only the accelerator dial. Around 68% the cards stay just under their 92 °C limit even with the fans flat out. That gives 205 units from the processor plus 102 from the cards: 307 in all.",
          expert="CPU 100%, accel ≈ 68%: T_accel < 92 °C at pinned rpm, 307 W-TDP."),
    ],
    start=_DUST_START.model_dump(by_alias=True),
)


# --- Lab 2: ride the sag on a 7 A breaker -----------------------------------

_SAG_START = Scenario(
    config=CELL_SITE, workload=FULL, environment=_CABINET,
    duration_s=600, events=[_sag(300)],
)

RIDE_THE_SAG = Lab(
    id="ride-the-sag",
    title="Ride the sag on a 7 A breaker",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "At t+300 s the feed sags to 65% for ten seconds. Stay up "
                "through it on the cabinet's 7 A breaker while delivering "
                "at least 315 W-TDP — during the sag too — then push the "
                "work as high as the breaker allows."
            ),
            novice=(
                "Five minutes into the run, the site's electricity sags: "
                "the voltage drops to 65% of normal for ten seconds (a "
                "brownout). The machine must stay on through it, must keep "
                "working through it (at least 315 units of work, in the "
                "brownout as well as on average), and must never pull more "
                "than 7 amps, because that is the size of the breaker on "
                "this cabinet's feed. Once that works, see how much work "
                "you can fit under the breaker."
            ),
            expert=(
                "65% × 10 s sag at t ≥ 300 s, T_in ≥ 30 °C, peak I ≤ 7 A, "
                "work ≥ 315 W-TDP (mean and in-sag), no trip; maximize work."
            ),
        ),
        constraints=[
            L(standard="A sag to 65% or lower, at least 10 seconds long, arriving at t+300 s or later.",
              novice="There must be a brownout: voltage at 65% or lower for at least 10 seconds, starting at 300 seconds or later. The lab starts with one already in place.",
              expert="V ≤ 65% for ≥ 10 s, first at t ≥ 300 s."),
            L(standard="Peak input current 7 A or less, and the sled stays on.",
              novice="The current drawn from the feed may never go above 7 amps, and the machine may not switch off.",
              expert="max I ≤ 7 A, no trip."),
            L(standard="Ambient stays at 30 °C or above; no throttling; no validation errors; full 600-second run.",
              novice="Leave the Ambient slider at 30 °C or higher, no chip may throttle, the build panel may show no red errors, and the run must be the full 600 seconds.",
              expert="min T_in ≥ 30 °C, zero clamp, zero errors, 600 s."),
            _KEEP_THE_BUILD,
        ],
        delivered_work=L(
            standard="At least 315 W-TDP of CPU plus accelerator work, averaged over the run and again over the sag seconds alone.",
            novice="The processor and the accelerator cards together must average at least 315 units of work over the ten-minute run, and also at least 315 during the ten seconds of the brownout itself.",
            expert="workRateW ≥ 315 and sagWorkRateW ≥ 315.",
        ),
    ),
    criteria=[
        _work(315),
        _sag_work(315),
        _sag_happens(),
        _sag_after(300),
        _breaker(),
        _stays_up(),
        _cabinet_air(30),
        _no_throttle(),
        _build_intact(),
        _full_run(600),
        _valid_build(),
    ],
    objective=Objective(
        label="Delivered work", metric="workRateW", direction="maximize",
        par=338, worst=315, unit="W-TDP", explain_id="brownout",
        equation=EQ_SAG,
    ),
    hints=[
        L(standard="Watch the input-current readout as the sag arrives: at 65% of 120 V the same wall watts need 1.54× the amps. 7 A × 78 V = 546 W is the whole wall budget while it lasts.",
          novice="Find the 'input current' number in the instruments and watch it when the brownout arrives at 300 seconds. Current is power divided by voltage, and the voltage has dropped to 78 V. Seven amps at 78 volts is only 546 watts at the wall — that is all you may draw during the brownout.",
          expert="Budget: 7 A × 0.65 × 120 V = 546 W at the wall during the sag."),
        L(standard="A second or bigger supply stops the supply from tripping and leaves the breaker exactly where it was — a lightly loaded 1+1 pair is also less efficient, so it draws more amps for the same work. Shed watts instead, and shed the ones that are not work first.",
          novice="Adding a second power supply, or choosing a bigger one, only stops the power supply from switching off. The breaker is outside the machine and still sees too many amps. Worse, two supplies sharing a small load waste more, so they pull more current for the same work. You have to draw fewer watts. Start with watts that earn no work in this lab: the memory and storage dials.",
          expert="PSU sizing moves the PSU limit only; 1+1 at low load fraction costs η. Shed non-work watts first."),
        L(standard="Accelerators at 100% pin the fans, and fan power is cubic: CPU at 100% with the cards near 89% delivers more work per wall watt than any other split. A single 1100 W supply sits near 50% load, the top of the efficiency curve, and buys the last point.",
          novice="Running the accelerator cards at 100% forces the fans flat out, and fan power rises very steeply with speed. Easing the cards back to about 89%, with the CPU still at 100%, gives the most work for each watt. Last trick: one 1100 W power supply ends up about half loaded, which is where a supply wastes the least — so the same work needs slightly fewer amps.",
          expert="CPU 100 / accel ≈ 89, mem 50 / storage 10, 1 × 1100 W (η peak near 0.5): 338 W-TDP at 6.98 A."),
    ],
    start=_SAG_START.model_dump(by_alias=True),
)


# --- Lab 3: the worst afternoon ----------------------------------------------

_WORST_START = Scenario(
    config=CELL_SITE, workload=FULL, environment=_DUSTY,
    duration_s=900, events=[_HEAT_STEP, _sag(600)],
)

WORST_AFTERNOON = Lab(
    id="worst-afternoon",
    title="The worst afternoon at the cell site",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "Everything at once: six months of dust, 45 °C from t+300 s, "
                "and at t+600 s a ten-second sag to 65% on the 7 A breaker. "
                "Deliver at least 275 W-TDP — during the sag too — with no "
                "throttling and no trip, then maximize the work."
            ),
            novice=(
                "The hardest lab puts the first two together. The filter is "
                "six months dirty and cannot be changed. The outside air "
                "climbs to 45 °C at 300 seconds. Then, at 600 seconds, the "
                "voltage sags to 65% for ten seconds, on the same 7-amp "
                "breaker. The machine must stay on, no chip may throttle, "
                "and it must keep doing at least 275 units of work — in the "
                "brownout as well as on average. The answers to the first "
                "two labs both fail here; find out why, then get as much "
                "work as you can."
            ),
            expert=(
                "Fouling ≥ 40%, ≥ 600 s at ≥ 45 °C, 65% × 10 s sag at t ≥ "
                "600 s in the heat, peak I ≤ 7 A, zero clamp, work ≥ 275 "
                "W-TDP (mean and in-sag); maximize work."
            ),
        ),
        constraints=[
            L(standard="At least 600 seconds at 45 °C or hotter, with the filter at least 40% fouled throughout.",
              novice="The outside air must be 45 °C or hotter for at least 600 seconds, and the filter must stay at least 40% blocked the whole time: no filter change.",
              expert="≥ 600 s at T_in ≥ 45 °C; min fouling ≥ 40%."),
            L(standard="A sag to 65% or lower for at least 10 seconds, arriving at t+600 s or later, in 45 °C air.",
              novice="There must be a brownout (65% or lower, at least 10 seconds), it must start at 600 seconds or later, and the air must be 45 °C or hotter while it happens. The lab starts with one in the right place.",
              expert="V ≤ 65% for ≥ 10 s, first at t ≥ 600 s, T_in ≥ 45 °C during it."),
            L(standard="Peak input current 7 A or less; no throttling; the sled stays on; no validation errors; full 900-second run.",
              novice="Never more than 7 amps from the feed, no chip may throttle, the machine may not switch off, no red errors in the build panel, and the full 900 seconds.",
              expert="max I ≤ 7 A, zero clamp, no trip, zero errors, 900 s."),
            _KEEP_THE_BUILD,
        ],
        delivered_work=L(
            standard="At least 275 W-TDP of CPU plus accelerator work, averaged over the run and again over the sag seconds alone.",
            novice="The processor and the accelerator cards together must average at least 275 units of work over the fifteen-minute run, and also at least 275 during the ten seconds of the brownout itself.",
            expert="workRateW ≥ 275 and sagWorkRateW ≥ 275.",
        ),
    ),
    criteria=[
        _work(275),
        _sag_work(275),
        _hot_afternoon(),
        _fouled(),
        _sag_happens(),
        _sag_after(600),
        Criterion(
            id="sag-in-the-heat", label="Ambient 45 °C or hotter throughout the sag",
            metric="minSagInletC", op=">=", threshold=45, unit="°C",
            explain_id="fan-power", equation=EQ_FAN,
            why=L(
                standard=(
                    "The point of this lab is the coupling: dust and heat "
                    "pin the fans at about 70 W, and those fan watts are "
                    "wall watts the sag multiplies into amps. A sag in cool "
                    "air would uncouple them."
                ),
                novice=(
                    "This lab is about two problems making each other "
                    "worse. The dust and the heat force the fans flat out, "
                    "which costs about 70 watts — and in a brownout every "
                    "watt becomes extra current against the 7-amp breaker. "
                    "If the brownout came while the air was cool, the fans "
                    "would be slow and the two problems would not meet. So "
                    "the air must be 45 °C or hotter during the brownout."
                ),
                expert="T_in ≥ 45 °C on every V ≤ 65% tick: pinned P_fan is inside the sag's P_wall.",
            ),
        ),
        _breaker(),
        _no_throttle(),
        _stays_up(),
        _build_intact(),
        _full_run(900),
        _valid_build(),
    ],
    objective=Objective(
        label="Delivered work", metric="workRateW", direction="maximize",
        par=291, worst=275, unit="W-TDP", explain_id="fan-power",
        equation=EQ_FAN,
    ),
    hints=[
        L(standard="Try the first two labs' answers here and read which lines fail. The dust lab's load trips the breaker in the sag; the sag lab's load throttles the accelerators. Both limits now bind at once.",
          novice="Load your answer from the dust lab: it breaks the 7-amp line when the brownout comes. Load your answer from the brownout lab: the accelerator cards throttle in the heat. In this lab you have to satisfy both limits at the same time.",
          expert="Lab 1's point violates I ≤ 7 A; lab 2's violates the accel clamp. Intersect the constraints."),
        L(standard="Look at fan power: about 70 W here against about 15 W in the cool cabinet. Those 55 W come straight out of the 546 W the breaker allows during the sag, so the load must drop further than in the sag lab — and because fan power is cubic, a small cut that lets the fans come off 100% gives some of it back.",
          novice="Find the 'fan power' number. In the cool cabinet of the brownout lab it was about 15 watts; here, with dust and heat, it is about 70. Those extra 55 watts count against the 546 watts the breaker allows in the brownout. So you must turn the load down further than before. There is a small reward hiding here: fan power rises so steeply with speed that a slightly lighter load, which lets the fans drop just below flat out, saves more fan watts than you would expect.",
          expert="P_fan ≈ 70 W vs ≈ 15 W: −55 W of sag budget. rpm³ makes the first percent off the pin cheap to buy."),
        L(standard="The CPU is now the expensive watt: ease it to about 93% and hold the accelerators near 67%, just under their 92 °C clamp. Drop the memory and storage dials to the RAN levels, and use a single 1100 W supply so the 530 W load sits at the top of the efficiency curve: 291 W-TDP at 7.0 A.",
          novice="With the cards held near 67% (just under their 92 °C limit), the remaining watts have to come off the processor: about 93% works. Set the memory dial to 50% and storage to 10% so fewer watts go to things that earn no work here. Finally choose one 1100 W power supply: at about half load it wastes the least, which is worth a couple of percent of work under the breaker. That gets you 291 units at exactly 7.0 amps.",
          expert="CPU ≈ 93 / accel ≈ 67, mem 50 / storage 10, 1 × 1100 W: 291 W-TDP at 7.0 A."),
    ],
    start=_WORST_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [DUST_AND_HEAT, RIDE_THE_SAG, WORST_AFTERNOON]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Reference solutions and the tricks that must not work -----------------
# Server-side only: GET /api/labs serves LABS, never these.

_ONE_1100 = CELL_SITE.model_copy(update={"psu_capacity_w": 1100})
_PAIR_1400 = CELL_SITE.model_copy(update={
    "psu_count": 2, "psu_capacity_w": 1400, "redundancy": "1+1",
})
_NO_NIC = CELL_SITE.model_copy(update={"io_card_w": 25})

_DUST_WL = Workload(cpu_pct=100, mem_pct=80, storage_pct=50, accel_pct=68)
_SAG_WL = Workload(cpu_pct=100, mem_pct=50, storage_pct=10, accel_pct=89)
_WORST_WL = Workload(cpu_pct=93, mem_pct=50, storage_pct=10, accel_pct=67)

REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    "dust-and-heat": Scenario(
        config=CELL_SITE, workload=_DUST_WL, environment=_DUSTY,
        duration_s=900, events=[_HEAT_STEP],
    ),
    "ride-the-sag": Scenario(
        config=_ONE_1100, workload=_SAG_WL, environment=_CABINET,
        duration_s=600, events=[_sag(300)],
    ),
    "worst-afternoon": Scenario(
        config=_ONE_1100, workload=_WORST_WL, environment=_DUSTY,
        duration_s=900, events=[_HEAT_STEP, _sag(600)],
    ),
}


def _load_at(at_s: int, wl: Workload) -> SimEvent:
    return SimEvent(at_s=at_s, action="set-workload", workload=wl)


GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "dust-and-heat": {
        "zero load": Scenario(
            config=CELL_SITE, workload=IDLE, environment=_DUSTY,
            duration_s=900, events=[_HEAT_STEP]),
        "turn the cpu down instead": Scenario(
            config=CELL_SITE,
            workload=Workload(cpu_pct=40, mem_pct=80, storage_pct=50, accel_pct=100),
            environment=_DUSTY, duration_s=900, events=[_HEAT_STEP]),
        "change the filter": Scenario(
            config=CELL_SITE, workload=_DUST_WL, environment=_DUSTY,
            duration_s=900,
            events=[SimEvent(at_s=0, action="clean-filter"), _HEAT_STEP]),
        "pick a cleaner site": Scenario(
            config=CELL_SITE, workload=_DUST_WL,
            environment=Environment(inlet_c=38, dust="clean", filter_months=6),
            duration_s=900, events=[_HEAT_STEP]),
        "cancel the afternoon": Scenario(
            config=CELL_SITE, workload=_DUST_WL, environment=_DUSTY,
            duration_s=900),
        "pull the fronthaul nic": Scenario(
            config=_NO_NIC,
            workload=Workload(cpu_pct=100, mem_pct=80, storage_pct=50, accel_pct=80),
            environment=_DUSTY, duration_s=900, events=[_HEAT_STEP]),
        "short run": Scenario(
            config=CELL_SITE, workload=FULL,
            environment=Environment(inlet_c=45, dust="heavy", filter_months=6),
            duration_s=30),
        "long run at low load": Scenario(
            config=CELL_SITE, workload=Workload(cpu_pct=10, accel_pct=10),
            environment=Environment(inlet_c=45, dust="heavy", filter_months=6),
            duration_s=7200),
        "idle first, load later": Scenario(
            config=CELL_SITE, workload=IDLE, environment=_DUSTY,
            duration_s=900, events=[_HEAT_STEP, _load_at(800, _DUST_WL)]),
    },
    "ride-the-sag": {
        "zero load": Scenario(
            config=CELL_SITE, workload=IDLE, environment=_CABINET,
            duration_s=600, events=[_sag(300)]),
        "second supply, full load": Scenario(
            config=_PAIR_1400, workload=FULL, environment=_CABINET,
            duration_s=600, events=[_sag(300)]),
        "no sag": Scenario(
            config=_ONE_1100, workload=FULL, environment=_CABINET,
            duration_s=600),
        "sag at cold start": Scenario(
            config=_ONE_1100, workload=_SAG_WL, environment=_CABINET,
            duration_s=600, events=[_sag(0)]),
        "a shallow, short sag": Scenario(
            config=_ONE_1100, workload=FULL, environment=_CABINET,
            duration_s=600,
            events=[SimEvent(at_s=300, action="voltage-sag", value=90, seconds=2)]),
        "idle through the sag": Scenario(
            config=_ONE_1100, workload=FULL, environment=_CABINET,
            duration_s=600,
            events=[_load_at(295, IDLE), _sag(300), _load_at(315, FULL)]),
        "cool the cabinet": Scenario(
            config=_ONE_1100,
            workload=Workload(cpu_pct=100, mem_pct=50, storage_pct=10, accel_pct=92),
            environment=Environment(inlet_c=-20), duration_s=600,
            events=[_sag(300)]),
        "pull the fronthaul nic": Scenario(
            config=_NO_NIC.model_copy(update={"psu_capacity_w": 1100}),
            workload=FULL, environment=_CABINET, duration_s=600,
            events=[_sag(300)]),
        "long run at low load": Scenario(
            config=CELL_SITE, workload=Workload(cpu_pct=10, accel_pct=10),
            environment=_CABINET, duration_s=7200, events=[_sag(300)]),
    },
    "worst-afternoon": {
        "zero load": Scenario(
            config=CELL_SITE, workload=IDLE, environment=_DUSTY,
            duration_s=900, events=[_HEAT_STEP, _sag(600)]),
        "the dust lab's answer": Scenario(
            config=CELL_SITE, workload=_DUST_WL, environment=_DUSTY,
            duration_s=900, events=[_HEAT_STEP, _sag(600)]),
        "the sag lab's answer": Scenario(
            config=_ONE_1100, workload=_SAG_WL, environment=_DUSTY,
            duration_s=900, events=[_HEAT_STEP, _sag(600)]),
        "second supply, dust lab's load": Scenario(
            config=_PAIR_1400, workload=_DUST_WL, environment=_DUSTY,
            duration_s=900, events=[_HEAT_STEP, _sag(600)]),
        "change the filter before the sag": Scenario(
            config=_ONE_1100, workload=_SAG_WL, environment=_DUSTY,
            duration_s=900,
            events=[_HEAT_STEP, SimEvent(at_s=590, action="clean-filter"), _sag(600)]),
        "sag before the heat": Scenario(
            config=_ONE_1100, workload=_DUST_WL, environment=_DUSTY,
            duration_s=900, events=[_sag(100), _HEAT_STEP]),
        "cool snap for the sag": Scenario(
            config=_ONE_1100, workload=_DUST_WL,
            environment=Environment(inlet_c=45, dust="heavy", filter_months=6),
            duration_s=900,
            events=[SimEvent(at_s=605, action="set-inlet", value=10), _sag(640)]),
        "no sag": Scenario(
            config=_ONE_1100, workload=_DUST_WL, environment=_DUSTY,
            duration_s=900, events=[_HEAT_STEP]),
        "idle through the sag": Scenario(
            config=_ONE_1100, workload=_DUST_WL, environment=_DUSTY,
            duration_s=900,
            events=[_HEAT_STEP, _load_at(595, IDLE), _sag(600),
                    _load_at(615, _DUST_WL)]),
        "pull the fronthaul nic": Scenario(
            config=_NO_NIC.model_copy(update={"psu_capacity_w": 1100}),
            workload=_DUST_WL, environment=_DUSTY, duration_s=900,
            events=[_HEAT_STEP, _sag(600)]),
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
