"""Graded labs for the MX7000 shared-infrastructure simulator
(``docs/LAB_PATTERN.md``; pilot: ``DellPowerEdgeR760Thermal``).

A guided scenario sets the dials and tells you what to watch. A lab states a
goal and leaves the dials to you: build a Scenario with the ordinary controls,
the engine runs it, and ``grade_scenario`` scores the trace.

Pure module, same rule as ``engine.py`` and ``validation.py``: no FastAPI, no
IO, no clock, no randomness (AST-checked in ``tests/test_labs.py``). ``main.py``
is the only caller that touches HTTP, so the static-hosting build grades in
the browser by running this same file under Pyodide.

Three things here are this app's own; everything else is ``twinkit.labs``:

* ``measure()`` — turns one run into named numbers. The un-gameable one is
  ``workRateW``: for every compute sled, requested CPU utilization × the
  throttle clamp actually in force × 2 sockets × TDP, summed over the chassis
  and averaged over the whole run (dark seconds count as zero). An idle,
  capped, throttled or dark chassis delivers less, so it passes less. The
  clamp is read back out of the trace's own per-sled watts, so the grader
  never trusts anything but the run. An illustrative proxy for useful
  compute, not a benchmark, and labeled so.
* ``LABS`` — three labs of rising difficulty, each one of the engine's
  acceptance scenarios turned into a challenge with a twist, every criterion
  citing the Explain entry (``presets.EXPLAINS``) and the equation it tests.
* ``REFERENCE_SOLUTIONS`` / ``GAMING_ATTEMPTS`` — a scenario that passes each
  lab, and the cheap tricks that must not. They stay server-side: the API
  serves ``LABS`` only.
"""

from __future__ import annotations

from twinkit.labs import Criterion, Lab, LabGoal, LabResult, Objective, grade

from .engine import compute_sled_power, populated_psu_slots, simulate
from .leveling import L
from .models import (
    ChassisConfig,
    Environment,
    Scenario,
    SimEvent,
    SimState,
    SledConfig,
    SledLoad,
    Summary,
    Validation,
    Workload,
)
from .presets import EIGHT_COMPUTE, FULL, NPLUS1
from .validation import validate

# The equations, exactly as the Explain entries display them.
EQ_SLED = "P_sled = 2 × (P_idle + (TDP − P_idle) × util^1.4) + DIMMs + drives + base"
EQ_FAN = "rpm ← rpm + k × (max(T_sled) − target);  P_fan = N × P_max × (rpm%)³"
EQ_WALL = "P_wall = P_dc / η(load ÷ pool capacity)"
EQ_POOL = "survives(failure) ⇔ capacity(pool − failure) ≥ P_dc"
EQ_HEAT = "T_exhaust = T_inlet + P_dc / (ṁ × cp)"

SLEDS = 8


# --- Measurement ----------------------------------------------------------

def _clamp_in_force(sled: SledConfig, load: SledLoad, watts: float) -> float:
    """The throttle multiplier the engine applied to this sled this tick,
    read back from the sled's own power: P = rest + cpu_full × clamp."""
    rest = compute_sled_power(sled, load, 0.0)
    cpu_full = compute_sled_power(sled, load, 1.0) - rest
    if cpu_full <= 0:
        return 1.0
    clamp = max(0.0, min(1.0, (watts - rest) / cpu_full))
    return 1.0 if clamp >= 0.999 else clamp


def measure(
    scenario: Scenario,
    trace: list[SimState],
    summary: Summary,
    validations: list[Validation],
) -> dict[str, float]:
    """One run as named numbers. Keys are the wire names criteria refer to."""
    cfg = scenario.config
    sleds = list(cfg.sleds) + [SledConfig() for _ in range(SLEDS - len(cfg.sleds))]
    loads = [ld.model_copy() for ld in scenario.workload.loads]
    loads += [SledLoad() for _ in range(SLEDS - len(loads))]
    events = sorted(scenario.events, key=lambda e: e.at_s)
    ei = 0
    work = 0.0
    min_busy_mem = 100.0
    ever_busy = False  # any compute sled with its CPU dial above zero
    for s in trace:
        # Replay the workload dials exactly as the engine applied them.
        while ei < len(events) and events[ei].at_s <= s.t:
            ev = events[ei]
            ei += 1
            if ev.action == "set-sled-load" and ev.index is not None and ev.load is not None:
                if 0 <= ev.index < SLEDS:
                    loads[ev.index] = ev.load.model_copy()
            elif ev.action == "set-all-load" and ev.load is not None:
                loads = [ev.load.model_copy() for _ in range(SLEDS)]
        for i in range(SLEDS):
            sled = sleds[i]
            if sled.kind != "compute" or loads[i].cpu_pct <= 0:
                continue
            ever_busy = True
            min_busy_mem = min(min_busy_mem, float(loads[i].mem_pct))
            if s.powered_on:
                work += (
                    (loads[i].cpu_pct / 100.0)
                    * _clamp_in_force(sled, loads[i], s.sled_power_w[i])
                    * 2 * sled.cpu_tdp_w
                )
    n = len(trace)
    on = [s for s in trace if s.powered_on]
    fan_count = max(s.alive_fans for s in trace)
    first_dead_fan = next((s.t for s in trace if s.alive_fans < fan_count), -1)
    first_feed_loss = next(
        (s.t for s in trace if not (s.feed_a_up and s.feed_b_up)), -1
    )
    last = trace[-1]
    compute = [s for s in sleds if s.kind == "compute"]
    populated = len(populated_psu_slots(cfg))
    return {
        "durationS": float(last.t),
        "workRateW": round(work / n, 1),
        "meanFanW": round(sum(s.fan_power_w for s in trace) / n, 1),
        "meanWallW": round(sum(s.ac_power_w for s in trace) / n, 1),
        "meanPsuEfficiencyPct": round(
            100.0 * sum(s.psu_efficiency for s in on) / max(len(on), 1), 2
        ),
        "peakDcW": float(summary.peak_dc_w),
        "hottestSledC": round(max(max(s.sled_temp_c) for s in trace), 2),
        "throttleSeconds": float(summary.throttle_seconds),
        "shutdown": 1.0 if summary.shutdown else 0.0,
        "minInletC": round(min(s.inlet_c for s in trace), 2),
        "firstFanFailureS": float(first_dead_fan),
        "finalAliveFans": float(last.alive_fans),
        "firstFeedLossS": float(first_feed_loss),
        "feedsUpAtEnd": float(int(last.feed_a_up) + int(last.feed_b_up)),
        "psusDarkAtEnd": float(populated - last.alive_psus),
        "psuCount": float(populated),
        "minDimms": float(min((s.dimms for s in compute), default=0)),
        # No busy sled means nothing to starve; the work floor catches idling.
        "minBusyMemPct": min_busy_mem if ever_busy else 100.0,
        "validationErrors": float(sum(1 for v in validations if v.level == "error")),
    }


# --- Criteria shared between labs ------------------------------------------

def _work(floor_w: int) -> Criterion:
    return Criterion(
        id="work", label=f"Delivered work at least {floor_w} W-TDP",
        metric="workRateW", op=">=", threshold=floor_w, unit="W-TDP",
        weight=2.0, guards_work=True, explain_id="sled-power", equation=EQ_SLED,
        why=L(
            standard=(
                f"Work is each compute sled's requested CPU utilization × "
                f"(1 − throttle loss) × 2 sockets × TDP, summed over the "
                f"chassis and averaged over the run; {floor_w} W-TDP is the "
                "floor. An idle, capped, throttled or dark chassis delivers "
                "less, so turning the load down is not a way through. The "
                "proxy is illustrative, not a benchmark."
            ),
            novice=(
                f"The chassis has to do real work the whole time — at least "
                f"{floor_w} units. For each server sled we count how hard you "
                "ask its processors to run (the CPU dial), times how big they "
                "are (their TDP, the watts they are built for), times two "
                "because each sled has two processors. Then we add up all the "
                "sleds. If a sled slows itself down (throttling), if the "
                "chassis power budget slows everyone down, or if the chassis "
                "goes dark, that time counts for less or nothing. So you "
                "cannot win by leaving the sleds idle. This is a simple "
                "stand-in for useful computing, not a real benchmark score."
            ),
            expert=(
                f"Mean over all ticks of Σ util × clamp × 2 × TDP, dark ticks "
                f"zero; floor {floor_w} W-TDP. Illustrative proxy."
            ),
        ),
    )


def _no_throttle() -> Criterion:
    return Criterion(
        id="no-throttle", label="No throttling or capping at any point",
        metric="throttleSeconds", op="<=", threshold=0, unit="s", weight=2.0,
        explain_id="sled-power", equation=EQ_SLED,
        why=L(
            standard=(
                "Two things clamp a sled's CPU power: its own temperature "
                "passing 95 °C, and the chassis power budget walking every "
                "compute sled down together. Either way the clamped seconds "
                "are lost work, and this line counts both."
            ),
            novice=(
                "A sled's processors can be slowed down in two ways. If a "
                "sled gets too hot (above 95 °C) it slows itself to cool off. "
                "And if you set a chassis power budget that the sleds do not "
                "fit under, the chassis slows every sled at once until they "
                "do. Both are called throttling here, every second of either "
                "is work you did not get, and this line allows none."
            ),
            expert="Zero ticks with any per-sled clamp < 1 or the chassis cap engaged.",
        ),
    )


def _stays_up() -> Criterion:
    return Criterion(
        id="stays-up", label="Chassis stays powered on",
        metric="shutdown", op="<=", threshold=0, unit="", weight=2.0,
        explain_id="redundancy", equation=EQ_POOL,
        why=L(
            standard=(
                "The chassis goes dark when no PSU is left alive, when the "
                "surviving pool is held above 105% of its capacity for 30 "
                "seconds, or on sustained critical temperature. A dark "
                "chassis draws nothing and delivers nothing."
            ),
            novice=(
                "The chassis must stay switched on for the whole run. It can "
                "go dark in three ways: every power supply loses its "
                "electricity, the supplies that are left are asked for more "
                "power than they can give for half a minute, or a sled gets "
                "dangerously hot. A dark chassis uses no power, but it also "
                "does no work, so it cannot pass."
            ),
            expert="Pool non-empty, no sustained >1.05× overcurrent, no overtemp power-off.",
        ),
    )


def _valid_build() -> Criterion:
    return Criterion(
        id="valid-build", label="Build has no validation errors",
        metric="validationErrors", op="<=", threshold=0, unit="errors",
        explain_id="redundancy", equation=EQ_POOL,
        why=L(
            standard=(
                "The configuration rules' errors are builds the chassis "
                "would refuse: grid redundancy needs an even PSU count so "
                "the two feeds split the pool evenly, and every storage sled "
                "needs a compute sled as its owner. Warnings are allowed — "
                "the simulator lets you try them and shows the consequence."
            ),
            novice=(
                "The 'Configuration rules' list under the build checks your "
                "chassis. A red error means the chassis would not accept "
                "that build. Two rules can go red: 'grid' power needs an "
                "even number of power supplies (2, 4 or 6) so each wall feed "
                "gets half, and every storage sled has to belong to a server "
                "sled. Yellow warnings are allowed; red errors are not."
            ),
            expert="Zero error-level findings (grid-split, storage-owner).",
        ),
    )


def _room(c: int) -> Criterion:
    return Criterion(
        id="room", label=f"Inlet air never below {c} °C",
        metric="minInletC", op=">=", threshold=c, unit="°C",
        explain_id="heat-balance", equation=EQ_HEAT,
        why=L(
            standard=(
                f"The lab is set in a {c} °C cold aisle. Every temperature in "
                "the chassis is inlet plus a rise, so cooling the room lowers "
                "the hottest sled and the fan bill for free. T_inlet is the "
                "one term you may not lower."
            ),
            novice=(
                f"This lab happens in a room where the air going into the "
                f"front of the chassis is {c} °C. Everything inside is as hot "
                "as that air plus whatever heat it adds itself. Making the "
                "room colder would be the easy answer, so the lab does not "
                f"allow it: the Inlet slider has to stay at {c} °C or higher "
                "for the whole run."
            ),
            expert=f"min(T_inlet) ≥ {c} °C; T_inlet is fixed.",
        ),
    )


def _full_run(seconds: int) -> Criterion:
    return Criterion(
        id="full-run", label=f"Run lasts at least {seconds} s",
        metric="durationS", op=">=", threshold=seconds, unit="s",
        explain_id="fan-tax", equation=EQ_FAN,
        why=L(
            standard=(
                "A sled settles in about half a minute, but the shared fan "
                "loop then takes minutes to find its speed. A short run "
                "would be graded before the fan bill it is graded on had "
                "arrived."
            ),
            novice=(
                "Heat takes time. A sled warms up in about half a minute, "
                "and then the fans spend a few more minutes finding the "
                "speed that holds the temperature steady. If the run were "
                "shorter, it would end before the fans had reached the speed "
                f"this lab is about, so the run must last at least {seconds} "
                "seconds (the Duration slider)."
            ),
            expert=f"≥ {seconds} s: past the τ ≈ 25 s sleds and the integrating fan loop.",
        ),
    )


# --- Lab 1: spread the heat -------------------------------------------------

_HOT4 = SledLoad(cpu_pct=100, mem_pct=40, storage_pct=30)
_CONSOLIDATED = Workload(loads=[*[_HOT4.model_copy() for _ in range(4)],
                                *[SledLoad() for _ in range(4)]])

_SPREAD_START = Scenario(
    config=EIGHT_COMPUTE, workload=_CONSOLIDATED, environment=Environment(),
    duration_s=600,
)

SPREAD_THE_HEAT = Lab(
    id="spread-the-heat",
    title="Spread the heat",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "Four sleds run flat out and four sit idle — tidy, and the "
                "fan wall is paying for it. Deliver the same 1600 W-TDP of "
                "work with the shared fans averaging 10 W or less, then get "
                "the mean wall power as low as you can."
            ),
            novice=(
                "The chassis starts with all its work packed onto four "
                "server sleds running at full speed, while the other four do "
                "nothing. That looks neat, but the nine fans belong to the "
                "whole chassis and they spin fast enough to cool the hottest "
                "sled — so four hot sleds make everybody's fans work hard. "
                "Your job: get the same amount of work done (1600 units), "
                "but arrange it so the fans use 10 W or less on average. "
                "Once that works, see how little electricity from the wall "
                "you can use."
            ),
            expert=(
                "Work ≥ 1600 W-TDP, mean P_fan ≤ 10 W, T_inlet ≥ 22 °C, "
                "600 s; minimize mean P_wall."
            ),
        ),
        constraints=[
            L(standard="Inlet stays at 22 °C or above for the whole run.",
              novice="Leave the Inlet slider at 22 °C or higher from start to finish — no cooling the room.",
              expert="min T_inlet ≥ 22 °C."),
            L(standard="Mean fan power 10 W or less over a run of at least 600 seconds.",
              novice="Over a run of at least 600 seconds, the 'fan power' readout has to average 10 W or less.",
              expert="mean P_fan ≤ 10 W, ≥ 600 s."),
            L(standard="No throttling, no validation errors; the chassis stays on.",
              novice="No sled may slow itself down, the rules list may show no red errors, and the chassis must not go dark.",
              expert="Zero clamp, zero errors, no trip."),
        ],
        delivered_work=L(
            standard="At least 1600 W-TDP of CPU work across the chassis, averaged over the run — what four dual-205 W sleds deliver at 98%.",
            novice="All the sleds together must average at least 1600 units of work. That is about what the four busy sleds are doing when you start, so you may move the work around but you may not do less of it.",
            expert="workRateW ≥ 1600.",
        ),
    ),
    criteria=[
        _work(1600),
        Criterion(
            id="fan-bill", label="Mean fan power 10 W or less",
            metric="meanFanW", op="<=", threshold=10, unit="W", weight=2.0,
            explain_id="fan-tax", equation=EQ_FAN,
            why=L(
                standard=(
                    "The controller holds the hottest sled to 78 °C, so rpm "
                    "is set by max(T_sled), not by the average — and fan "
                    "power is cubic in rpm. Four sleds at 100% and eight "
                    "sleds at 50% do the same work; only one of them has a "
                    "sled above the target."
                ),
                novice=(
                    "The fans do not care about the average sled. They look "
                    "only at the hottest one and spin faster until it is "
                    "down to 78 °C. And fan power rises very steeply with "
                    "speed: twice the speed costs eight times the power. "
                    "Four sleds running flat out and eight sleds running at "
                    "half speed do the same total work, but only the first "
                    "arrangement has a sled hot enough to make the fans "
                    "speed up."
                ),
                expert="rpm tracks max(T_sled) − 78 °C; P_fan ∝ rpm³. Flatten the max.",
            ),
        ),
        _room(22),
        _no_throttle(),
        _stays_up(),
        _full_run(600),
        _valid_build(),
    ],
    objective=Objective(
        label="Mean wall power", metric="meanWallW", direction="minimize",
        par=2865, worst=3000, unit="W", explain_id="wall-power", equation=EQ_WALL,
    ),
    hints=[
        L(standard="Watch the 'hottest sled' readout and the fan rpm together. The fans leave their 20% floor only when some sled is above 78 °C.",
          novice="Find the 'hottest sled' number and the fan speed in the instruments and watch them together. The fans sit at their slowest speed (20%) until some sled goes above 78 °C. Then they speed up — for everyone.",
          expert="rpm leaves the 20% floor only while max(T_sled) > 78 °C."),
        L(standard="Sled power grows as util^1.4 but work grows as util. Halving a sled's load more than halves its CPU watts, so the same work spread wider is both cooler and cheaper.",
          novice="Here is the key. A sled's power rises faster than the load you give it. So a sled at half load uses quite a bit less than half the processor power of a sled at full load, and runs much cooler. But our work score rises in a straight line with load. Two sleds at 50% do the work of one sled at 100% — for fewer watts and less heat.",
          expert="Convex P(util), linear work: spreading lowers both max(T) and ΣP."),
        L(standard="Use the 'Editing sled' slider to give every one of the eight sleds about 50% CPU. No sled passes 78 °C, the fans stay on the floor near 3 W, and the wall meter drops by about 300 W.",
          novice="Use the 'Editing sled' slider to visit each of the eight sleds in turn and set its CPU dial to about 50% (the 'All steady' button does this in one click). Now no sled goes above 78 °C, the fans stay at their slowest speed and use about 3 W, and the power from the wall drops by about 300 W.",
          expert="8 × 50%: fans on the floor (~3 W), ~300 W off the wall."),
    ],
    start=_SPREAD_START.model_dump(by_alias=True),
)


# --- Lab 2: the feed you were not covered for --------------------------------

_LOSE_A = [SimEvent(at_s=300, action="lose-feed", index=0)]

_FEED_START = Scenario(
    config=NPLUS1, workload=FULL, environment=Environment(),
    duration_s=600, events=_LOSE_A,
)

SMALLEST_POOL = Lab(
    id="smallest-pool-that-survives",
    title="The smallest pool that survives",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "Eight sleds at full load, and AC feed A dies at t+300 s and "
                "stays dead. The N+1 pool you start with goes dark. Keep the "
                "chassis up and the work flowing through the loss — with as "
                "few power supplies as will do it."
            ),
            novice=(
                "Eight server sleds are running flat out. Five minutes in, "
                "one of the two wall feeds (feed A) fails and never comes "
                "back. The chassis you start with has four power supplies "
                "and a policy called 'N+1', and it goes completely dark when "
                "the feed dies. Your job: change the power supplies and the "
                "policy so the chassis keeps running at full work right "
                "through the failure. Power supplies cost money, so once it "
                "survives, do it with as few as you can."
            ),
            expert=(
                "Work ≥ 3200 W-TDP over 600 s through a permanent feed loss "
                "at t ≤ 300 s that darkens ≥ 1 PSU; minimize psuCount."
            ),
        ),
        constraints=[
            L(standard="An AC feed is lost by t+300 s, takes at least one PSU with it, and is never restored.",
              novice="A wall feed has to fail in the first 300 seconds (the lab starts with that already set up), it has to actually switch off at least one power supply, and it may never come back. If you press Reset, pause, drag the time slider to before 300 s and press 'Lose feed A now' to set it up again.",
              expert="lose-feed at t ≤ 300 s, ≥ 1 PSU dark at the end, no restore."),
            L(standard="The chassis stays on, with no throttling, for a run of at least 600 seconds.",
              novice="The chassis may not go dark, no sled may be slowed down, and the run has to last at least 600 seconds.",
              expert="No trip, zero clamp, ≥ 600 s."),
            L(standard="No validation errors.",
              novice="No red errors in the 'Configuration rules' list.",
              expert="Zero errors."),
        ],
        delivered_work=L(
            standard="At least 3200 W-TDP of CPU work across the chassis, averaged over the whole run — eight dual-205 W sleds at 98% or better, before and after the failure.",
            novice="All the sleds together must average at least 3200 units of work over the whole run. Eight sleds at full speed make 3280, so there is almost no room to turn the load down — and any time the chassis spends dark counts as zero.",
            expert="workRateW ≥ 3200 (8 × 2 × 205 W at ≥ 98%).",
        ),
    ),
    criteria=[
        _work(3200),
        Criterion(
            id="feed-lost", label="An AC feed is lost by t+300 s",
            metric="firstFeedLossS", op="<=", threshold=300, unit="s",
            explain_id="redundancy", equation=EQ_POOL,
            why=L(
                standard="The failure has to arrive while there is still half a run left to survive; a feed lost on the last tick tests nothing.",
                novice="The feed has to fail in the first 300 seconds, so that the chassis has to keep going for a long time afterwards. A feed that fails in the very last second would not test anything.",
                expert="Failure at t ≤ 300 s leaves ≥ 300 s on the reduced pool.",
            ),
        ),
        Criterion(
            id="feed-really-lost", label="A feed has actually been lost",
            metric="firstFeedLossS", op=">=", threshold=0, unit="s", weight=2.0,
            explain_id="redundancy", equation=EQ_POOL,
            why=L(
                standard="No failure, no lab: the run is graded on surviving with the pool minus a feed.",
                novice="If no wall feed ever fails, this line fails — the whole lab is about getting through that failure. Use the 'Lose feed A now' button early in the run.",
                expert="Requires a feed down at some tick.",
            ),
        ),
        Criterion(
            id="feed-stays-lost", label="The feed is never restored",
            metric="feedsUpAtEnd", op="<=", threshold=1, unit="feeds",
            explain_id="redundancy", equation=EQ_POOL,
            why=L(
                standard="The survivors have to carry the chassis to the end of the run, not for one second until the feed comes back.",
                novice="The feed that failed has to stay failed until the end, so that the power supplies that are left really do carry the whole chassis by themselves.",
                expert="≤ 1 feed up at the last tick.",
            ),
        ),
        Criterion(
            id="failure-bites", label="The lost feed took at least one PSU with it",
            metric="psusDarkAtEnd", op=">=", threshold=1, unit="PSUs",
            explain_id="redundancy", equation=EQ_POOL,
            why=L(
                standard=(
                    "Outside grid redundancy this model wires the whole pool "
                    "to feed A, so losing feed B darkens nothing — a failure "
                    "that removes nothing from the pool is not the failure "
                    "in the equation."
                ),
                novice=(
                    "There is a trick this line closes. Unless the policy is "
                    "'grid', every power supply in this simulator is plugged "
                    "into feed A. So if you fail feed B instead, nothing is "
                    "plugged into it and nothing happens. That is not "
                    "surviving a failure; that is picking a failure that "
                    "does not touch you. At least one power supply has to "
                    "have gone dark by the end."
                ),
                expert="pool − failure must be a strict subset: ≥ 1 PSU dark at the end.",
            ),
        ),
        _stays_up(),
        _no_throttle(),
        _full_run(600),
        _valid_build(),
    ],
    objective=Objective(
        label="PSUs in the pool", metric="psuCount", direction="minimize",
        par=4, worst=6, unit="PSUs", explain_id="redundancy", equation=EQ_POOL,
    ),
    hints=[
        L(standard="Read the event log at t+300 s: how many of the pool's PSUs were on the lost feed? Redundancy is a statement about which failures leave a non-empty pool.",
          novice="Let the run play past 300 seconds and read the event log under the picture. It tells you how many of the power supplies were plugged into the feed that died. A spare power supply does not help if the spare is plugged into the same dead feed.",
          expert="Which failure classes leave pool − failure non-empty?"),
        L(standard="The start did not need more PSUs, it needed the same PSUs arranged differently: grid redundancy puts slots 1–3 on feed A and slots 4–6 on feed B.",
          novice="The starting chassis does not need more power supplies. It needs them plugged in differently. Change 'Redundancy' to 'grid': now half the supplies are on feed A and half on feed B, so losing one feed only takes half of them.",
          expert="Grid: slots 1–3 on A, 4–6 on B. Same count, disjoint outcome."),
        L(standard="Now size the survivors: the full chassis draws about 4600 W DC. After the loss a grid pool of two has one 3000 W PSU left — past 105% for 30 seconds, and it trips. A pool of four leaves two.",
          novice="Last step: make sure the supplies that are left are big enough. The full chassis draws about 4600 W. Each supply gives 3000 W. With only two supplies on 'grid', one is left after the failure — 3000 W is not enough, and half a minute later it trips and the chassis goes dark anyway. With four, two are left: 6000 W, plenty. Six also works, but you were asked for as few as possible.",
          expert="P_dc ≈ 4.6 kW: grid 2 leaves 3 kW and trips; grid 4 leaves 6 kW."),
    ],
    start=_FEED_START.model_dump(by_alias=True),
)


# --- Lab 3: the budget is a wall ---------------------------------------------

_BUSY = SledLoad(cpu_pct=100, mem_pct=80, storage_pct=60)

_BUDGET_START = Scenario(
    config=EIGHT_COMPUTE.model_copy(update={"power_cap_w": 4000}),
    workload=FULL, environment=Environment(inlet_c=30), duration_s=600,
)

BUDGET_WALL = Lab(
    id="the-budget-is-a-wall",
    title="The budget is a wall",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "The rack circuit allows this chassis 4000 W DC, the room is "
                "30 °C, and a fan dies in the first 100 seconds and stays "
                "dead. Deliver at least 2800 W-TDP without the peak ever "
                "crossing 4000 W and without one second of throttling or "
                "capping — then push the work as high as it will go."
            ),
            novice=(
                "The hardest lab. The electrical circuit feeding this "
                "chassis can give it only 4000 W. The room is warm (30 °C), "
                "and you must break one of the nine fans yourself early in "
                "the run — click a fan in the picture before 100 seconds "
                "have passed — and leave it broken. The chassis starts with "
                "a 'power budget' of 4000 W switched on, which keeps it "
                "under the limit by slowing every sled down. That counts as "
                "throttling, and this lab allows none. You have to build and "
                "load a chassis that stays under 4000 W by itself, and still "
                "does a lot of work (2800 units). After you pass, see how "
                "much more work you can squeeze out of the same 4000 W."
            ),
            expert=(
                "max P_dc ≤ 4000 W, T_inlet ≥ 30 °C, N−1 fans from t ≤ 100 s, "
                "work ≥ 2800 W-TDP over 600 s, zero clamp; maximize work."
            ),
        ),
        constraints=[
            L(standard="Peak DC power never above 4000 W — fans, fabric and management included.",
              novice="The 'total DC power' readout may never go above 4000 W at any moment. That total includes the fans, the network modules and the management modules, not just the sleds.",
              expert="max P_dc ≤ 4000 W, shared plant included."),
            L(standard="Inlet 30 °C or above; a fan fails by t+100 s and is never replaced (click a fan in the chassis view early in the run).",
              novice="Leave the Inlet slider at 30 °C or higher. Break a fan early: press Reset, pause, drag the time slider to somewhere before 100 seconds, and click one of the nine fans in the picture. Do not click it again — that would replace it.",
              expert="T_inlet ≥ 30 °C; kill-fan at t ≤ 100 s, no restore."),
            L(standard="No throttling or capping, no shutdown, no validation errors, at least 600 seconds.",
              novice="No sled may be slowed down — not by heat and not by the power budget — the chassis may not go dark, the rules list may show no red errors, and the run must last at least 600 seconds.",
              expert="Zero clamp, no trip, zero errors, ≥ 600 s."),
            L(standard="Every compute sled keeps at least 16 DIMMs, and every busy sled keeps its memory dial at 80% or above.",
              novice="Do not starve the sleds to save power: every server sled keeps at least 16 memory modules (DIMMs), and every sled that is doing work keeps its Memory dial at 80% or higher.",
              expert="≥ 16 DIMMs per compute sled; mem ≥ 80% on busy sleds."),
        ],
        delivered_work=L(
            standard="At least 2800 W-TDP of CPU work across the chassis, averaged over the 600-second run — more than eight dual-205 W sleds can deliver inside 4000 W.",
            novice="All the sleds together must average at least 2800 units of work. Eight of the starting 205 W sleds cannot quite reach that inside 4000 W however you set their dials, so something about the build has to change.",
            expert="workRateW ≥ 2800 (> the 205 W tier's best under the budget).",
        ),
    ),
    criteria=[
        _work(2800),
        Criterion(
            id="budget", label="Peak DC power 4000 W or less",
            metric="peakDcW", op="<=", threshold=4000, unit="W", weight=2.0,
            explain_id="sled-power", equation=EQ_SLED,
            why=L(
                standard=(
                    "The budget is on chassis DC: Σ sled powers plus fabric, "
                    "management and the fan wall. The power-budget dial does "
                    "not hold this line — the clamp engages only after DC "
                    "has already crossed the cap — and the fan watts a hot "
                    "sled provokes are spent out of the same 4000 W."
                ),
                novice=(
                    "The 4000 W limit covers everything in the chassis: all "
                    "the sleds, plus the network and management modules, "
                    "plus the fans. Two things to know. First, the 'Power "
                    "budget' dial will not save you: it only reacts after "
                    "the power has already gone over, so the peak still "
                    "breaks this line. Second, the fans are inside the "
                    "limit. Every watt the fans use to cool a hot sled is a "
                    "watt the processors do not get."
                ),
                expert="max(ΣP_sled + fabric + mgmt + P_fan) ≤ 4000 W; the cap dial reacts after the overshoot.",
            ),
        ),
        _room(30),
        Criterion(
            id="fan-dies-early", label="A fan fails by t+100 s",
            metric="firstFanFailureS", op="<=", threshold=100, unit="s",
            explain_id="fan-tax", equation=EQ_FAN,
            why=L(
                standard="The failure has to be in force for nearly the whole run, so the survivors' higher rpm is part of the budget you plan for.",
                novice="The fan has to break early, so that the chassis spends almost the whole run on eight fans and you have to plan your 4000 W around that. Losing a fan in the last few seconds would change nothing.",
                expert="N−1 for ≥ 500 s of the run.",
            ),
        ),
        Criterion(
            id="fan-dead", label="A fan has actually failed",
            metric="firstFanFailureS", op=">=", threshold=0, unit="s", weight=2.0,
            explain_id="fan-tax", equation=EQ_FAN,
            why=L(
                standard="No fan failure, no lab: the run is graded on fitting the budget with N = 8.",
                novice="If no fan ever breaks, this line fails — the lab is about fitting inside 4000 W with eight fans instead of nine. Click a fan in the picture to break it.",
                expert="Requires N_alive < 9 at some tick.",
            ),
        ),
        Criterion(
            id="fan-stays-dead", label="The fan is never replaced",
            metric="finalAliveFans", op="<=", threshold=8, unit="fans",
            explain_id="fan-tax", equation=EQ_FAN,
            why=L(
                standard="Eight survivors replace the ninth's airflow by spinning faster, and fan power is cubic in rpm — the failure's price is paid in P_fan, inside the budget.",
                novice="The broken fan has to stay broken to the end. The eight fans that are left make up for it by spinning faster, and a fan's power rises very steeply with speed. You can see that cost in the 'fan power' readout — and it comes out of your 4000 W.",
                expert="N_alive = 8 to the end; survivors pay rpm³ out of the budget.",
            ),
        ),
        _no_throttle(),
        _stays_up(),
        Criterion(
            id="dimms", label="At least 16 DIMMs in every compute sled",
            metric="minDimms", op=">=", threshold=16, unit="DIMMs",
            explain_id="sled-power", equation=EQ_SLED,
            why=L(
                standard="Every DIMM removed is a few watts back in the budget — true, and not the lesson. The memory stays.",
                novice="Taking memory out does give a few watts back, because every part uses power. But a sled with too little memory is not the sled the customer asked for, so every server sled keeps at least 16 modules.",
                expert="De-population of the DIMMs term is out of scope.",
            ),
        ),
        Criterion(
            id="memory-busy", label="Busy sleds keep memory at 80% or above",
            metric="minBusyMemPct", op=">=", threshold=80, unit="%",
            explain_id="sled-power", equation=EQ_SLED,
            why=L(
                standard="The work proxy counts CPU only, so zeroing the memory dial would free a few hundred watts for nothing. The job is memory-hungry: any sled with its CPU dial above zero keeps memory at 80% or more.",
                novice="Our work score only looks at the processors, so you could cheat by turning every Memory dial to zero and spending the saved watts on the processors. Real work needs its memory. So any sled whose CPU dial is above zero must keep its Memory dial at 80% or higher.",
                expert="mem ≥ 80% wherever util > 0; closes the DIMM-term loophole in a CPU-only proxy.",
            ),
        ),
        _full_run(600),
        _valid_build(),
    ],
    objective=Objective(
        label="Delivered work", metric="workRateW", direction="maximize",
        par=2856, worst=2800, unit="W-TDP", explain_id="sled-power", equation=EQ_SLED,
    ),
    hints=[
        L(standard="Turn the power budget off and read the peak: the eight sleds at 100% draw about 4800 W. The cap dial never passes this lab — capped seconds are throttled seconds, and the peak has crossed the line before the clamp bites.",
          novice="Start by setting the 'Power budget' dial to off and look at the highest 'total DC power': about 4800 W, far over the limit. Turning the budget back on is not the answer — every second it slows the sleds counts as throttling, and the power has already gone over 4000 W before it reacts. You have to get under the limit with the ordinary dials.",
          expert="Uncapped peak ≈ 4.8 kW. The cap fails both the clamp line and the peak line."),
        L(standard="Turning all eight 205 W sleds down evenly fits the budget at about 84% — and lands just short of the work floor. Keep the load even (one hotter sled spends budget on fans) and ask what else sets watts per unit of work.",
          novice="Try turning all eight sleds down by the same amount. At about 84% CPU they fit under 4000 W — but the work comes out just under 2800. Keep the sleds even, because one hotter sled makes the fans speed up and the fans eat into your 4000 W. Then ask: is there a way to get more work out of each watt?",
          expert="205 W tier tops out near 84% / 2755 W-TDP. Keep max(T) flat; change W per W-TDP."),
        L(standard="Power grows as util^1.4 but work grows as util × TDP, so work per watt peaks near 56% utilization. Eight 350 W sleds at about 51% deliver more work inside 4000 W than eight 205 W sleds at 84%.",
          novice="Here is the surprising part. A processor's power rises faster than its load, but our work score rises in a straight line with load and with processor size. That means a processor gives the most work for each watt at roughly half load, not at full load. So choose bigger processors and run them gently: change every bay to 350 W and set every CPU dial to about 51%. Same 4000 W, more work than the 205 W sleds could ever reach.",
          expert="d(work/P)/du = 0 near u ≈ 0.56: 8 × 350 W at ~51% beats 8 × 205 W at 84%."),
    ],
    start=_BUDGET_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [SPREAD_THE_HEAT, SMALLEST_POOL, BUDGET_WALL]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Reference solutions and the tricks that must not work -----------------
# Server-side only: GET /api/labs serves LABS, never these.

def _all(load: SledLoad) -> Workload:
    return Workload(loads=[load.model_copy() for _ in range(SLEDS)])


def _sleds(tdp: int, dimms: int = 16) -> list[SledConfig]:
    return [SledConfig(kind="compute", cpu_tdp_w=tdp, dimms=dimms, drives=2)
            for _ in range(SLEDS)]


_KILL_FAN = [SimEvent(at_s=60, action="kill-fan", index=4)]
_WARM = Environment(inlet_c=30)
_GRID4 = ChassisConfig(sleds=_sleds(205), psu_count=4, redundancy="grid")
_BIG = ChassisConfig(sleds=_sleds(350), psu_count=6, redundancy="grid")
_GENTLE = SledLoad(cpu_pct=51, mem_pct=80, storage_pct=60)

REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    "spread-the-heat": Scenario(
        config=EIGHT_COMPUTE,
        workload=_all(SledLoad(cpu_pct=50, mem_pct=40, storage_pct=30)),
        duration_s=600,
    ),
    "smallest-pool-that-survives": Scenario(
        config=_GRID4, workload=FULL, duration_s=600, events=_LOSE_A,
    ),
    "the-budget-is-a-wall": Scenario(
        config=_BIG, workload=_all(_GENTLE), environment=_WARM,
        duration_s=600, events=_KILL_FAN,
    ),
}

_IDLE = _all(SledLoad())

GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "spread-the-heat": {
        "zero load": Scenario(config=EIGHT_COMPUTE, workload=_IDLE, duration_s=600),
        "cool the room": Scenario(
            config=EIGHT_COMPUTE, workload=_CONSOLIDATED,
            environment=Environment(inlet_c=15), duration_s=600),
        "short run": Scenario(
            config=EIGHT_COMPUTE, workload=_CONSOLIDATED, duration_s=20),
        "long run at low load": Scenario(
            config=EIGHT_COMPUTE,
            workload=_all(SledLoad(cpu_pct=10)), duration_s=7200),
        "idle first, load later": Scenario(
            config=EIGHT_COMPUTE, workload=_IDLE, duration_s=600,
            events=[SimEvent(at_s=500, action="set-all-load", load=_HOT4)]),
        "cap the chassis instead": Scenario(
            config=EIGHT_COMPUTE.model_copy(update={"power_cap_w": 2600}),
            workload=_CONSOLIDATED, duration_s=600),
    },
    "smallest-pool-that-survives": {
        "zero load": Scenario(config=_GRID4, workload=_IDLE,
                              duration_s=600, events=_LOSE_A),
        "no feed loss": Scenario(config=_GRID4, workload=FULL, duration_s=600),
        "lose the feed nothing is plugged into": Scenario(
            config=NPLUS1, workload=FULL, duration_s=600,
            events=[SimEvent(at_s=300, action="lose-feed", index=1)]),
        "restore the feed": Scenario(
            config=_GRID4, workload=FULL, duration_s=600,
            events=_LOSE_A + [SimEvent(at_s=301, action="restore-feed", index=0)]),
        "lose the feed on the last tick": Scenario(
            config=_GRID4, workload=FULL, duration_s=600,
            events=[SimEvent(at_s=600, action="lose-feed", index=0)]),
        "grid pool of two trips": Scenario(
            config=_GRID4.model_copy(update={"psu_count": 2}),
            workload=FULL, duration_s=600, events=_LOSE_A),
        "more PSUs on n+1": Scenario(
            config=NPLUS1.model_copy(update={"psu_count": 6}),
            workload=FULL, duration_s=600, events=_LOSE_A),
        "odd grid pool": Scenario(
            config=_GRID4.model_copy(update={"psu_count": 3}),
            workload=FULL, duration_s=600, events=_LOSE_A),
        "short run": Scenario(
            config=_GRID4, workload=FULL, duration_s=30,
            events=[SimEvent(at_s=10, action="lose-feed", index=0)]),
    },
    "the-budget-is-a-wall": {
        "zero load": Scenario(config=_BIG, workload=_IDLE, environment=_WARM,
                              duration_s=600, events=_KILL_FAN),
        "lean on the power cap": Scenario(
            config=EIGHT_COMPUTE.model_copy(update={"power_cap_w": 4000}),
            workload=FULL, environment=_WARM, duration_s=600, events=_KILL_FAN),
        "205 W sleds turned down": Scenario(
            config=EIGHT_COMPUTE,
            workload=_all(SledLoad(cpu_pct=84, mem_pct=80, storage_pct=60)),
            environment=_WARM, duration_s=600, events=_KILL_FAN),
        "cool the room": Scenario(
            config=_BIG, workload=_all(_GENTLE),
            environment=Environment(inlet_c=15), duration_s=600, events=_KILL_FAN),
        "no fan failure": Scenario(
            config=_BIG, workload=_all(_GENTLE), environment=_WARM, duration_s=600),
        "replace the fan": Scenario(
            config=_BIG, workload=_all(_GENTLE), environment=_WARM, duration_s=600,
            events=_KILL_FAN + [SimEvent(at_s=61, action="restore-fan", index=4)]),
        "kill the fan at the end": Scenario(
            config=_BIG, workload=_all(_GENTLE), environment=_WARM, duration_s=600,
            events=[SimEvent(at_s=599, action="kill-fan", index=4)]),
        "zero the memory dial": Scenario(
            config=EIGHT_COMPUTE,
            workload=_all(SledLoad(cpu_pct=90, mem_pct=0, storage_pct=0)),
            environment=_WARM, duration_s=600, events=_KILL_FAN),
        "strip the DIMMs": Scenario(
            config=ChassisConfig(sleds=_sleds(350, dimms=8), psu_count=6,
                                 redundancy="grid"),
            workload=_all(SledLoad(cpu_pct=53, mem_pct=80, storage_pct=60)),
            environment=_WARM, duration_s=600, events=_KILL_FAN),
        "idle first, load later": Scenario(
            config=_BIG, workload=_IDLE, environment=_WARM, duration_s=600,
            events=_KILL_FAN + [SimEvent(at_s=500, action="set-all-load", load=_GENTLE)]),
        "short run": Scenario(
            config=_BIG, workload=_all(_GENTLE), environment=_WARM, duration_s=30,
            events=[SimEvent(at_s=5, action="kill-fan", index=4)]),
        "everything flat out": Scenario(
            config=_BIG, workload=_all(_BUSY), environment=_WARM,
            duration_s=600, events=_KILL_FAN),
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
