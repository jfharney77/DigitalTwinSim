"""Graded labs for the R760 power & thermal simulator — the pilot of
``docs/LAB_PATTERN.md``.

A guided scenario sets the dials and tells you what to watch. A lab states a
goal and leaves the dials to you: build a Scenario with the ordinary controls,
the engine runs it, and ``grade_scenario`` scores the trace.

Pure module, same rule as ``engine.py`` and ``validation.py``: no FastAPI, no
IO, no clock, no randomness (AST-checked in ``tests/test_labs.py``). ``main.py``
is the only caller that touches HTTP, so a static-hosting build can run this
grading in the browser from the same data.

Three things here are this app's own; everything else is ``twinkit.labs``:

* ``measure()`` — turns one run into named numbers. The un-gameable one is
  ``workRateW``: requested CPU utilization × (1 − throttle loss) × sockets ×
  TDP, averaged over the whole run (dark seconds count as zero). An idle or
  tripped server delivers nothing, so it passes nothing. It is an
  illustrative proxy for useful compute, not a benchmark, and is labeled so.
* ``LABS`` — three labs of rising difficulty, every criterion citing the
  Explain entry (``presets.EXPLAINS``) and the equation it tests.
* ``REFERENCE_SOLUTIONS`` / ``GAMING_ATTEMPTS`` — a scenario that passes each
  lab, and the cheap tricks that must not. They stay server-side: the API
  serves ``LABS`` only.
"""

from __future__ import annotations

from twinkit.labs import Criterion, Lab, LabGoal, LabResult, Objective, grade

from .engine import simulate
from .leveling import L
from .models import (
    Environment,
    Scenario,
    ServerConfig,
    SimEvent,
    SimState,
    Summary,
    Validation,
    Workload,
)
from .presets import BALANCED, DATABASE, HPC, MAX_CPU
from .validation import validate

# The equations, exactly as the Explain entries display them.
EQ_CPU = "P_cpu = sockets × (P_idle + (TDP − P_idle) × util^1.4) × clamp"
EQ_ZONE = "T_out = T_in + Q / (ṁ × cp)"
EQ_FAN = "P_fan = N_alive × P_max × (rpm%)³"
EQ_WALL = "P_wall = P_dc / η(load fraction)"


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
    work = 0.0
    for s in trace:
        # Replay the workload dial exactly as the engine applied it.
        while ei < len(events) and events[ei].at_s <= s.t:
            ev = events[ei]
            ei += 1
            if ev.action == "set-workload" and ev.workload is not None:
                wl = ev.workload
        if s.powered_on:
            work += (
                (wl.cpu_pct / 100.0)
                * (1.0 - s.perf_lost_pct / 100.0)
                * cfg.sockets * cfg.cpu_tdp_w
            )
    n = len(trace)
    on = [s for s in trace if s.powered_on]
    fan_count = max(s.alive_fans for s in trace)
    first_dead = next((s.t for s in trace if s.alive_fans < fan_count), -1)
    return {
        "durationS": float(trace[-1].t),
        "workRateW": round(work / n, 1),
        "peakCpuTempC": round(max(s.cpu_temp_c for s in trace), 2),
        "throttleSeconds": float(summary.throttle_seconds),
        "shutdown": 1.0 if summary.shutdown else 0.0,
        "meanWallW": round(sum(s.ac_power_w for s in trace) / n, 1),
        "meanPsuEfficiencyPct": round(
            100.0 * sum(s.psu_efficiency for s in on) / max(len(on), 1), 2
        ),
        "psuHeadroomW": round(cfg.psu_capacity_w - summary.peak_dc_w, 1),
        "redundantPsus": 1.0 if (
            cfg.redundancy == "1+1" and cfg.psu_count == 2
            and trace[-1].alive_psus == 2
        ) else 0.0,
        "minInletC": round(min(s.inlet_effective_c for s in trace), 2),
        "deadFanSeconds": float(sum(1 for s in trace if s.alive_fans < fan_count)),
        "firstFanFailureS": float(first_dead),
        "finalAliveFans": float(trace[-1].alive_fans),
        "dimms": float(cfg.dimms),
        "drives": float(cfg.drives),
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
                f"Work is requested CPU utilization × (1 − throttle loss) × "
                f"sockets × TDP, averaged over the run; {floor_w} W-TDP is the "
                "floor. An idle, throttled, or tripped server delivers less, so "
                "turning the load down is not a way through. The proxy is "
                "illustrative, not a benchmark."
            ),
            novice=(
                f"The server has to do real work the whole time — at least "
                f"{floor_w} units. We count work as how hard you ask the "
                "processors to run (the CPU dial), times how big they are "
                "(their TDP, the watts they are built for), times how many "
                "there are. If the server slows itself down to stay cool "
                "(throttling) or switches off, that time counts for less or "
                "nothing. So you cannot win by leaving the server idle. This "
                "is a simple stand-in for useful computing, not a real "
                "benchmark score."
            ),
            expert=(
                f"Mean of util × (1 − clamp loss) × sockets × TDP over all "
                f"ticks, dark ticks zero; floor {floor_w} W-TDP. Illustrative proxy."
            ),
        ),
    )


def _no_throttle() -> Criterion:
    return Criterion(
        id="no-throttle", label="No throttling at any point",
        metric="throttleSeconds", op="<=", threshold=0, unit="s", weight=2.0,
        explain_id="cpu-power", equation=EQ_CPU,
        why=L(
            standard=(
                "Above 98 °C the CPU clamps its own power — the clamp term in "
                "the power equation — and every clamped second is lost work. "
                "The 60-second turbo boost at exactly 100% utilization is the "
                "usual culprit: it adds 20% to CPU power just when the "
                "heatsink is still warming up."
            ),
            novice=(
                "When a processor gets too hot (above 98 °C here) it protects "
                "itself by slowing down. That is called throttling, and every "
                "second of it is work you did not get. Watch out for one "
                "thing in particular: if you ask for exactly 100% load, the "
                "processors run in a short 'turbo' burst for the first minute "
                "and draw about a fifth more power than their rating. That "
                "burst is often what tips a hot server over the edge."
            ),
            expert=(
                "clamp < 1 above 98 °C. The 60 s, 1.2× TDP boost at util = "
                "100% is the usual trigger."
            ),
        ),
    )


def _stays_up() -> Criterion:
    return Criterion(
        id="stays-up", label="Server stays powered on",
        metric="shutdown", op="<=", threshold=0, unit="", weight=2.0,
        explain_id="wall-power", equation=EQ_WALL,
        why=L(
            standard=(
                "A sustained draw above 105% of the surviving PSU budget "
                "trips the supply, and sustained critical temperature powers "
                "the server off. A dark server draws nothing and delivers "
                "nothing."
            ),
            novice=(
                "The server must stay switched on for the whole run. It can "
                "switch itself off in two ways: by pulling more electrical "
                "power than its power supply can give for several seconds, or "
                "by getting dangerously hot. A server that is off uses no "
                "power, but it also does no work, so it cannot pass."
            ),
            expert="No PSU overcurrent trip (>1.05× budget, sustained) and no overtemp power-off.",
        ),
    )


def _valid_build() -> Criterion:
    return Criterion(
        id="valid-build", label="Build has no validation errors",
        metric="validationErrors", op="<=", threshold=0, unit="errors",
        explain_id="zone-outlet", equation=EQ_ZONE,
        why=L(
            standard=(
                "The validation panel's errors are Dell's thermal restriction "
                "rules: CPUs above 165 W need the high-performance heatsink, "
                "and 300 W CPUs or double-wide GPUs need the Gold fans. A "
                "build Dell would not ship does not count."
            ),
            novice=(
                "The panel on the left checks your build against Dell's own "
                "rules, and red errors mean Dell would not sell that "
                "combination. Two rules matter most: bigger processors (above "
                "165 W) need the bigger heatsink, and the biggest processors "
                "(300 W and up) need the stronger 'Gold' fans, because only "
                "those move enough air to carry the heat away. Yellow "
                "warnings are allowed; red errors are not."
            ),
            expert="Zero error-level findings: HPR heatsink >165 W, Gold fans ≥300 W or DW GPU.",
        ),
    )


def _hot_inlet(c: int) -> Criterion:
    return Criterion(
        id="hot-inlet", label=f"Inlet air never below {c} °C",
        metric="minInletC", op=">=", threshold=c, unit="°C",
        explain_id="zone-outlet", equation=EQ_ZONE,
        why=L(
            standard=(
                f"The lab is set in a {c} °C cold aisle — the top of ASHRAE "
                "A2's allowable range. Every temperature in the box is inlet "
                "plus a rise, so T_in is the one term you may not lower."
            ),
            novice=(
                f"This lab happens in a warm room: the air going into the "
                f"front of the server is {c} °C, which is as warm as the "
                "industry guideline (ASHRAE class A2) allows. Every part "
                "inside is as hot as that air plus whatever heat the part "
                "adds. Cooling the room would be the easy answer, so the lab "
                "does not allow it: the Inlet slider has to stay at "
                f"{c} °C or higher for the whole run."
            ),
            expert=f"min(T_inlet_eff) ≥ {c} °C, the A2 allowable ceiling; T_in is fixed.",
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
                "several; a short run would be graded before the temperatures "
                "it is graded on had arrived."
            ),
            novice=(
                "Heat takes time. The processors warm up in about a minute, "
                "and the fans then spend several more minutes finding the "
                "speed that holds the temperature steady. If the run were "
                "shorter, it would end before the server reached the "
                "temperatures this lab is about, so the lab needs the full "
                "run length it starts with."
            ),
            expert="Long enough for the τ ≈ 20 s silicon and the fan loop to settle.",
        ),
    )


# --- Lab 1: the PSU sweet spot ---------------------------------------------

_SWEET_START = Scenario(
    config=BALANCED, workload=DATABASE, environment=Environment(), duration_s=600,
)

PSU_SWEET_SPOT = Lab(
    id="psu-sweet-spot",
    title="Find the PSU sweet spot",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "Size the power supplies to the load. Keep the redundant pair, "
                "deliver real work, and get the mean PSU efficiency to 95.2% "
                "or better — with enough headroom that one supply could carry "
                "the peak alone."
            ),
            novice=(
                "A power supply turns wall electricity into the kind the "
                "server uses, and it always wastes a little as heat. It wastes "
                "the least when it is about half loaded. Your job: keep two "
                "power supplies (so one can fail safely), keep the server "
                "busy, and choose the supply size and the load so that, on "
                "average, at least 95.2% of the wall power reaches the "
                "server. One supply must still be big enough to carry the "
                "highest power the server ever draws."
            ),
            expert=(
                "1+1 pair, mean η ≥ 95.2%, peak DC ≤ one PSU's rating, work "
                "floor 450 W-TDP."
            ),
        ),
        constraints=[
            L(standard="Two PSUs in 1+1 redundancy, both alive at the end.",
              novice="Keep two power supplies, set to '1+1' (each one can carry the server alone), and do not fail either of them.",
              expert="1+1, both alive."),
            L(standard="Peak DC power no higher than one PSU's capacity.",
              novice="The most power the server ever draws must fit inside a single power supply's rating, or the spare is not really a spare.",
              expert="max(P_dc) ≤ P_psu."),
            L(standard="No validation errors; the server stays on.",
              novice="No red errors in the build panel, and the server must not switch itself off.",
              expert="Zero errors, no trip."),
        ],
        delivered_work=L(
            standard="At least 450 W-TDP of CPU work, averaged over the run.",
            novice="The processors must do at least 450 units of work on average — roughly two 250 W processors at 90% load. An idle server does not count.",
            expert="workRateW ≥ 450.",
        ),
    ),
    criteria=[
        _work(450),
        Criterion(
            id="efficiency", label="Mean PSU efficiency at least 95.2%",
            metric="meanPsuEfficiencyPct", op=">=", threshold=95.2, unit="%",
            weight=2.0, explain_id="wall-power", equation=EQ_WALL,
            why=L(
                standard=(
                    "Efficiency follows the load fraction: 94% at 20% load, "
                    "96% at 50%, 91% at 100%. A 1+1 pair shares the load, so "
                    "each supply sits at DC ÷ (2 × capacity). Oversized "
                    "supplies idle far down the curve; the pair peaks when DC "
                    "is close to one supply's rating."
                ),
                novice=(
                    "How much a power supply wastes depends on how hard it is "
                    "working. Lightly loaded (a fifth of its rating) it is "
                    "about 94% efficient; at half load it peaks at about 96%; "
                    "flat out it drops to 91%. With two supplies sharing the "
                    "job, each one carries only half the server's power. So "
                    "big supplies on a modest server sit at the wasteful low "
                    "end. The pair is happiest when the server draws about "
                    "as much as ONE supply is rated for — then each is near "
                    "half load."
                ),
                expert=(
                    "η(load), Titanium-class curve; shared 1+1 load fraction "
                    "= P_dc / 2P_psu. Peak at P_dc ≈ P_psu."
                ),
            ),
        ),
        Criterion(
            id="headroom", label="One PSU could carry the peak alone",
            metric="psuHeadroomW", op=">=", threshold=0, unit="W", weight=2.0,
            explain_id="wall-power", equation=EQ_WALL,
            why=L(
                standard=(
                    "Redundancy is only real if the survivor can carry the "
                    "peak. The efficiency target pushes DC up toward one "
                    "supply's rating; this line stops it going past. The "
                    "turbo boost at 100% utilization is part of the peak."
                ),
                novice=(
                    "Two supplies only protect you if one of them can run "
                    "the whole server by itself. The efficiency goal tempts "
                    "you to load the supplies heavily; this line is the "
                    "limit. Look at the highest power the server reaches — "
                    "including the short turbo burst in the first minute at "
                    "100% load — and make sure it fits inside one supply."
                ),
                expert="P_psu − max(P_dc) ≥ 0, boost included.",
            ),
        ),
        Criterion(
            id="redundant", label="Two PSUs, 1+1, both alive",
            metric="redundantPsus", op=">=", threshold=1, unit="",
            explain_id="wall-power", equation=EQ_WALL,
            why=L(
                standard=(
                    "Dropping to a single supply doubles its load fraction "
                    "and lifts efficiency for free — and removes the "
                    "redundancy the pair exists for. Not allowed here."
                ),
                novice=(
                    "There is a shortcut: use only one power supply, and it "
                    "works twice as hard and lands nearer its efficient "
                    "middle. But then one failure turns the server off. Real "
                    "data centers keep the spare, so this lab does too."
                ),
                expert="1+0 doubles load fraction; disallowed.",
            ),
        ),
        _stays_up(),
        _valid_build(),
    ],
    objective=Objective(
        label="Mean PSU efficiency", metric="meanPsuEfficiencyPct",
        direction="maximize", par=95.45, worst=95.2, unit="%",
        explain_id="wall-power", equation=EQ_WALL,
    ),
    hints=[
        L(standard="Look at the PSU load readout. With a 1+1 pair it is DC ÷ (2 × capacity), and the curve peaks at 50%.",
          novice="Find the 'PSU load' number in the instruments. With two supplies sharing, it is the server's power divided by both supplies together. The supplies waste the least when that number is near 50%.",
          expert="Shared load fraction = P_dc / 2P_psu; η peaks at 0.5."),
        L(standard="The Balanced build draws about 450 W from a pair of 1400 W supplies — 16% load. Either shrink the supplies or grow the load; the work floor says grow the load too.",
          novice="The starting server draws about 450 W, but its two supplies could give 2800 W together, so they are barely working (16%). You can choose smaller supplies, or make the server work harder, or both. The work goal means you have to raise the CPU load anyway.",
          expert="450 W on 2×1400 W is 16%. Downsize and load up."),
        L(standard="800 W supplies with two 250 W CPUs nearly does it, but at exactly 100% utilization the 60-second boost pushes the peak past 800 W. Try 99%.",
          novice="Two 250 W processors with 800 W supplies is close to perfect. The catch: at exactly 100% CPU load, the processors 'turbo' for the first minute and the peak power goes above 800 W, which breaks the one-supply-can-carry-it rule. Set the CPU dial to 99% and the burst never happens.",
          expert="800 W, 2×250 W at 99% — sidesteps the 1.2× boost peak."),
    ],
    start=_SWEET_START.model_dump(by_alias=True),
)


# --- Lab 2: hot aisle, lean wall -------------------------------------------

_HOT_START = Scenario(
    config=BALANCED, workload=DATABASE,
    environment=Environment(inlet_c=35), duration_s=600,
)

HOT_AISLE = Lab(
    id="hot-aisle-lean-wall",
    title="Hot aisle, lean wall",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "The room is 35 °C. Deliver 450 W-TDP of work with the CPUs "
                "never above 90 °C and no throttling — then get the mean wall "
                "power as low as you can."
            ),
            novice=(
                "The air entering the server is a hot 35 °C and you cannot "
                "change that. Keep the processors busy (450 units of work), "
                "keep them at or below 90 °C, and never let them slow down to "
                "protect themselves. Once that works, the real game starts: "
                "use as little electricity from the wall as you can while "
                "still meeting every rule."
            ),
            expert=(
                "T_in = 35 °C, work ≥ 450 W-TDP, peak T_cpu ≤ 90 °C, zero "
                "clamp; minimize mean P_wall."
            ),
        ),
        constraints=[
            L(standard="Inlet stays at 35 °C or above for the whole run.",
              novice="Leave the Inlet slider at 35 °C or higher from start to finish.",
              expert="min T_in ≥ 35 °C."),
            L(standard="Peak CPU temperature 90 °C or less; no throttling; the server stays on.",
              novice="The processors may never go above 90 °C, may never throttle (slow themselves down), and the server may not switch off.",
              expert="max T_cpu ≤ 90 °C, no clamp, no trip."),
            L(standard="Keep at least 16 DIMMs and 8 drives; no validation errors.",
              novice="Do not strip the server to save power: keep at least 16 memory modules (DIMMs) and 8 drives, and no red errors in the build panel.",
              expert="≥16 DIMMs, ≥8 drives, zero errors."),
        ],
        delivered_work=L(
            standard="At least 450 W-TDP of CPU work, averaged over the 600-second run.",
            novice="The processors must average at least 450 units of work over the ten-minute run — for example two 250 W processors at 90% load.",
            expert="workRateW ≥ 450 over 600 s.",
        ),
    ),
    criteria=[
        _work(450),
        _hot_inlet(35),
        Criterion(
            id="cpu-temp", label="Peak CPU temperature 90 °C or less",
            metric="peakCpuTempC", op="<=", threshold=90, unit="°C", weight=2.0,
            explain_id="zone-outlet", equation=EQ_ZONE,
            why=L(
                standard=(
                    "CPU temperature is the air reaching the heatsink plus "
                    "per-socket watts × heatsink resistance, and that "
                    "resistance falls as airflow rises. At 35 °C inlet the "
                    "standard fans cannot move enough air to hold 90 °C at "
                    "this load; more airflow per watt, or fewer watts per "
                    "unit of work, can."
                ),
                novice=(
                    "A processor's temperature is the temperature of the air "
                    "blowing over its heatsink, plus an extra amount that "
                    "grows with the watts it burns. More air makes the "
                    "heatsink work better and lowers that extra amount. "
                    "Starting from 35 °C air there is not much room below "
                    "90 °C, and the standard fans cannot move enough air at "
                    "this load. You need either more air for each watt "
                    "(stronger fans) or fewer watts for the same work."
                ),
                expert=(
                    "T_cpu = T_air + P_socket × R_th(ṁ); R_th ∝ flow^−n. "
                    "Standard kit is airflow-limited at 35 °C."
                ),
            ),
        ),
        _no_throttle(),
        _stays_up(),
        Criterion(
            id="dimms", label="At least 16 DIMMs installed",
            metric="dimms", op=">=", threshold=16, unit="DIMMs",
            explain_id="zone-outlet", equation=EQ_ZONE,
            why=L(
                standard="Every DIMM removed is a few watts off Q — true, and not the lesson. The memory stays.",
                novice="Taking memory out does save a few watts, because every part adds heat. But a server with too little memory is not the server the customer asked for, so at least 16 modules must stay.",
                expert="Q reduction by de-population is out of scope.",
            ),
        ),
        Criterion(
            id="drives", label="At least 8 drives installed",
            metric="drives", op=">=", threshold=8, unit="drives",
            explain_id="zone-outlet", equation=EQ_ZONE,
            why=L(
                standard="Drives preheat the air every other part breathes and cost airflow, so pulling them helps twice — and is not allowed.",
                novice="Drives sit at the very front, so they warm the air before it reaches anything else, and they also block some of it. Removing them would help in two ways, which is exactly why the lab does not let you: keep at least 8.",
                expert="Front-zone preheat and airflow penalty stay in play.",
            ),
        ),
        _full_run(600),
        _valid_build(),
    ],
    objective=Objective(
        label="Mean wall power", metric="meanWallW", direction="minimize",
        par=602, worst=680, unit="W", explain_id="wall-power", equation=EQ_WALL,
    ),
    hints=[
        L(standard="Raise the CPU dial to reach the work floor and watch the peak: the standard fans run out of airflow just above 90 °C. Gold fans move more air for the same rpm.",
          novice="First turn the CPU dial up until the work goal is met. You will see the processors peak just above 90 °C. The standard fans simply cannot push enough air. Switch the fan kit to Gold: those fans move more air at the same speed.",
          expert="Standard kit is flow-limited; Gold CFM buys R_th."),
        L(standard="CPU power grows as util^1.4, but work grows as util × TDP. The same 450 W-TDP costs fewer watts on bigger CPUs run gently than on smaller CPUs run hard.",
          novice="Here is the surprising part. The power a processor burns rises faster than the load you give it — double the load, more than double the extra power. But our work score rises in a straight line with load and with processor size. So a big processor loafing along at 65% does the same work as a smaller one straining at 90%, and burns less power doing it.",
          expert="Convex P(util) vs linear work: high TDP, low util wins W per W-TDP."),
        L(standard="Then look at the wall: at about 650 W DC a pair of 1400 W supplies sits near 23% load. 800 W supplies put the same load near the top of the efficiency curve.",
          novice="Last step: the power supplies. Your server now draws about 650 W, but two 1400 W supplies share it, so each is loafing at under a quarter load, where they waste more. Choose 800 W supplies and the same server lands near the most efficient part of the curve, so less power is pulled from the wall.",
          expert="Right-size the pair: 800 W puts P_dc/2P_psu near 0.4."),
    ],
    start=_HOT_START.model_dump(by_alias=True),
)


# --- Lab 3: lose a fan, keep the clocks --------------------------------------

_FAN_START = Scenario(
    config=BALANCED, workload=HPC,
    environment=Environment(inlet_c=35), duration_s=900,
)

LOSE_A_FAN = Lab(
    id="lose-a-fan",
    title="Lose a fan, keep the clocks",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "35 °C inlet, and a fan dies in the first 100 seconds and "
                "stays dead. Deliver at least 650 W-TDP for the full 900 "
                "seconds without one second of throttling — then push the "
                "work as high as it will go."
            ),
            novice=(
                "The hardest lab. The room is hot (35 °C), and you must break "
                "one of the six fans yourself early in the run — click a fan "
                "in the picture before 100 seconds have passed — and leave it "
                "broken. With only five fans, the server still has to do a "
                "lot of work (650 units, more than the starting build can "
                "give) for fifteen minutes, and the processors may not slow "
                "down to protect themselves even for one second. After you "
                "pass, see how much more work you can squeeze out."
            ),
            expert=(
                "T_in = 35 °C, N−1 fans from t ≤ 100 s, work ≥ 650 W-TDP over "
                "900 s, zero clamp; maximize work."
            ),
        ),
        constraints=[
            L(standard="Inlet stays at 35 °C or above.",
              novice="Leave the Inlet slider at 35 °C or higher the whole time.",
              expert="min T_in ≥ 35 °C."),
            L(standard="A fan fails by t+100 s and is never replaced (click a fan in the chassis view early in the run).",
              novice="Break a fan early: press 'Reset to cold start', pause, drag the time slider to somewhere before 100 seconds, and click one of the six fans in the picture. Do not click it again — that would replace it.",
              expert="kill-fan at t ≤ 100 s, no restore."),
            L(standard="No throttling, no shutdown, no validation errors, full 900-second run.",
              novice="The processors may never throttle, the server may not switch off, the build panel may show no red errors, and the run must be the full 900 seconds it starts with.",
              expert="Zero clamp, no trip, zero errors, 900 s."),
        ],
        delivered_work=L(
            standard="At least 650 W-TDP of CPU work, averaged over the 900-second run — beyond what two 300 W CPUs can deliver.",
            novice="The processors must average at least 650 units of work. Two 300 W processors flat out only reach 600, so you will need bigger ones — and bigger ones run hotter.",
            expert="workRateW ≥ 650 (> 2 × 300 W at 100%).",
        ),
    ),
    criteria=[
        _work(650),
        _hot_inlet(35),
        Criterion(
            id="fan-dies-early", label="A fan fails by t+100 s",
            metric="firstFanFailureS", op="<=", threshold=100, unit="s",
            explain_id="fan-power", equation=EQ_FAN,
            why=L(
                standard="The failure has to land while the boost and warm-up are still in play; a fan lost after the box has settled is a gentler test.",
                novice="The fan has to break early, while the processors are still heating up and may still be in their turbo burst. Losing a fan later, after everything has settled, is an easier problem than this lab is asking about.",
                expert="Failure inside the boost/warm-up transient.",
            ),
        ),
        Criterion(
            id="fan-dead", label="A fan has actually failed",
            metric="firstFanFailureS", op=">=", threshold=0, unit="s", weight=2.0,
            explain_id="fan-power", equation=EQ_FAN,
            why=L(
                standard="No fan failure, no lab: the run is graded on surviving with N_alive = 5.",
                novice="If no fan ever breaks, this line fails — the whole lab is about getting through with five fans instead of six. Click a fan in the picture to break it.",
                expert="Requires N_alive < 6 at some tick.",
            ),
        ),
        Criterion(
            id="fan-stays-dead", label="The fan is never replaced",
            metric="finalAliveFans", op="<=", threshold=5, unit="fans",
            explain_id="fan-power", equation=EQ_FAN,
            why=L(
                standard="Five survivors must replace the sixth's airflow by spinning faster, and fan power grows with the cube of speed — the price of the failure is in P_fan.",
                novice="The broken fan has to stay broken to the end. The five fans that are left make up for it by spinning faster, and a fan's power rises very steeply with speed (twice the speed costs eight times the power). You can see that cost in the 'fan power' readout.",
                expert="N_alive = 5 to the end; survivors pay rpm³.",
            ),
        ),
        _no_throttle(),
        _stays_up(),
        _full_run(900),
        _valid_build(),
    ],
    objective=Objective(
        label="Delivered work", metric="workRateW", direction="maximize",
        par=693, worst=650, unit="W-TDP", explain_id="cpu-power", equation=EQ_CPU,
    ),
    hints=[
        L(standard="650 W-TDP needs 330 W or 350 W CPUs, and those need Gold fans — the validation panel will say so.",
          novice="To reach 650 units of work you need the big processors: 330 W or 350 W each. Those are only allowed with the Gold fan kit, and the build panel will show a red error until you choose it.",
          expert="≥330 W parts; Gold kit mandatory."),
        L(standard="Run the Max CPU preset at 100% and read the event log: the throttle arrives inside the first minute or two, during the boost, not at steady state.",
          novice="Try the 'Max CPU' build at 100% load, break a fan, and read the event log under the picture. The throttling happens early — in the first minute or two, during the turbo burst — and not later, once things have settled. That tells you what the real problem is.",
          expert="Clamp is a boost-transient event, not a steady-state one."),
        L(standard="The boost only fires at exactly 100% utilization. 350 W CPUs at 99% skip the 1.2× minute, never touch 98 °C on five fans, and deliver more work than 330 W CPUs at 100%.",
          novice="The turbo burst only happens at exactly 100% load. Set 350 W processors to 99% instead: no burst, so the temperature never reaches the 98 °C throttle point even on five fans — and 99% of a 350 W processor is more work than 100% of a 330 W one.",
          expert="2×350 W at 99%: no boost, no clamp at N−1, 693 W-TDP."),
    ],
    start=_FAN_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [PSU_SWEET_SPOT, HOT_AISLE, LOSE_A_FAN]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Reference solutions and the tricks that must not work -----------------
# Server-side only: GET /api/labs serves LABS, never these.

_KILL = [SimEvent(at_s=60, action="kill-fan", index=2)]
_HOT = Environment(inlet_c=35)

REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    "psu-sweet-spot": Scenario(
        config=BALANCED.model_copy(update={"psu_capacity_w": 800}),
        workload=Workload(cpu_pct=99, mem_pct=75, storage_pct=70),
        duration_s=600,
    ),
    "hot-aisle-lean-wall": Scenario(
        config=BALANCED.model_copy(update={
            "cpu_tdp_w": 350, "fan_kit": "gold", "psu_capacity_w": 800,
        }),
        workload=Workload(cpu_pct=65), environment=_HOT, duration_s=600,
    ),
    "lose-a-fan": Scenario(
        config=BALANCED.model_copy(update={"cpu_tdp_w": 350, "fan_kit": "gold"}),
        workload=Workload(cpu_pct=99, mem_pct=80, storage_pct=10),
        environment=_HOT, events=_KILL, duration_s=900,
    ),
}

_IDLE = Workload()

GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "psu-sweet-spot": {
        "zero load": Scenario(
            config=BALANCED.model_copy(update={"psu_capacity_w": 800}),
            workload=_IDLE, duration_s=600),
        "single PSU": Scenario(
            config=BALANCED.model_copy(update={
                "psu_capacity_w": 1400, "psu_count": 1, "redundancy": "1+0"}),
            workload=Workload(cpu_pct=99, mem_pct=75, storage_pct=70),
            duration_s=600),
        "undersized PSU that trips": Scenario(
            config=BALANCED.model_copy(update={
                "cpu_tdp_w": 350, "fan_kit": "gold", "psu_capacity_w": 800}),
            workload=Workload(cpu_pct=100, mem_pct=100, storage_pct=100),
            duration_s=600),
    },
    "hot-aisle-lean-wall": {
        "zero load": Scenario(config=BALANCED, workload=_IDLE,
                              environment=_HOT, duration_s=600),
        "cool the room": Scenario(
            config=BALANCED, workload=Workload(cpu_pct=90),
            environment=Environment(inlet_c=18), duration_s=600),
        "long run at low load": Scenario(
            config=BALANCED, workload=Workload(cpu_pct=10),
            environment=_HOT, duration_s=7200),
        "short run": Scenario(
            config=BALANCED.model_copy(update={"fan_kit": "gold"}),
            workload=Workload(cpu_pct=90), environment=_HOT, duration_s=30),
        "strip the server": Scenario(
            config=BALANCED.model_copy(update={
                "cpu_tdp_w": 350, "fan_kit": "gold", "dimms": 8, "drives": 0}),
            workload=Workload(cpu_pct=65), environment=_HOT, duration_s=600),
    },
    "lose-a-fan": {
        "zero load": Scenario(config=BALANCED, workload=_IDLE,
                              environment=_HOT, events=_KILL, duration_s=900),
        "no fan failure": Scenario(
            config=BALANCED.model_copy(update={"cpu_tdp_w": 350, "fan_kit": "gold"}),
            workload=Workload(cpu_pct=99), environment=_HOT, duration_s=900),
        "replace the fan": Scenario(
            config=BALANCED.model_copy(update={"cpu_tdp_w": 350, "fan_kit": "gold"}),
            workload=Workload(cpu_pct=99), environment=_HOT,
            events=_KILL + [SimEvent(at_s=61, action="restore-fan", index=2)],
            duration_s=900),
        "kill the fan at the end": Scenario(
            config=BALANCED.model_copy(update={"cpu_tdp_w": 350, "fan_kit": "gold"}),
            workload=Workload(cpu_pct=99), environment=_HOT,
            events=[SimEvent(at_s=899, action="kill-fan", index=2)],
            duration_s=900),
        "max cpu preset at full load": Scenario(
            config=MAX_CPU, workload=HPC, environment=_HOT, events=_KILL,
            duration_s=900),
        "idle first, load later": Scenario(
            config=BALANCED.model_copy(update={"cpu_tdp_w": 350, "fan_kit": "gold"}),
            workload=_IDLE, environment=_HOT,
            events=_KILL + [SimEvent(at_s=800, action="set-workload",
                                     workload=Workload(cpu_pct=99))],
            duration_s=900),
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
