"""Graded labs for the AI-compute physics simulator (``docs/LAB_PATTERN.md``;
pilot: ``DellPowerEdgeR760Thermal/backend/app/labs.py``).

A guided scenario sets the dials and tells you what to watch. A lab states a
goal and leaves the dials to you: build a Scenario with the ordinary controls,
the engine runs it, and ``grade_scenario`` scores the trace.

Pure module, same rule as ``engine.py`` and ``validation.py``: no FastAPI, no
IO, no clock, no randomness (AST-checked in ``tests/test_labs.py``). ``main.py``
is the only caller that touches HTTP, so the static-hosting build grades in the
browser with this same file.

Three things here are this app's own; everything else is ``twinkit.labs``:

* ``measure()`` — one run as named numbers. The un-gameable one is
  ``workRateW``: effective GPU utilization (demand × data feed × throttle
  clamp, exactly the engine's ``effectiveGpuUtilPct``) × GPU count × the GPU's
  nominal TDP, averaged over the whole run with dark seconds counted as zero.
  An idle, starved, throttled or tripped system delivers less, so it passes
  less. It is an illustrative proxy for useful compute, not a benchmark.
* ``LABS`` — one lab per machine, rising difficulty, each the app's acceptance
  physics turned into a problem: the XE7745's unequal seats, the XE9680's
  starved HGX board, the XE9712's ΔT = Q/(ṁ·cp) with a pump down.
* ``REFERENCE_SOLUTIONS`` / ``GAMING_ATTEMPTS`` — a scenario that passes each
  lab, and the cheap tricks that must not. Server-side only.
"""

from __future__ import annotations

from twinkit.labs import Criterion, Lab, LabGoal, LabResult, Objective, grade

from .engine import gpu_count, simulate
from .leveling import L
from .models import (
    Environment,
    Scenario,
    SimEvent,
    SimState,
    Summary,
    SystemConfig,
    Validation,
    Workload,
)
from .presets import EXPLAINS, XE7745_8GPU, XE9680_B200, XE9680_H100, XE9712_FULL
from .validation import validate

# The equations, exactly as the Explain entries display them — read from the
# entries themselves so the citation can never drift from the source.
_EQ = {e.id: e.equation for e in EXPLAINS}
EQ_LIQUID = _EQ["liquid-balance"]
EQ_STARVE = _EQ["starvation"]
EQ_POSITIONAL = _EQ["positional"]
EQ_OVERHEAD = _EQ["cooling-overhead"]

#: A pump counts as degraded while the loop carries at most this fraction of
#: the design flow (the app's "Degrade pump now" button removes 75%).
DEGRADED_FLOW_FRACTION = 0.26


def nominal_gpu_tdp_w(cfg: SystemConfig) -> float:
    """The GPU's nameplate TDP — the yardstick for the work proxy."""
    if cfg.product == "xe7745":
        return float(cfg.pcie_gpu_tdp_w)
    if cfg.product == "xe9680":
        return float(cfg.sxm_gpu_tdp_w)
    return 1400.0  # GB200-class tray GPU, as constants.tray_gpu_w


# --- Measurement ----------------------------------------------------------

def measure(
    scenario: Scenario,
    trace: list[SimState],
    summary: Summary,
    validations: list[Validation],
) -> dict[str, float]:
    """One run as named numbers. Keys are the wire names criteria refer to."""
    cfg = scenario.config
    n_gpu = gpu_count(cfg)
    tdp = nominal_gpu_tdp_w(cfg)

    # Replay the dials exactly as the engine applied them, tick by tick.
    events = sorted(scenario.events, key=lambda e: e.at_s)
    ei = 0
    feed = float(scenario.workload.data_feed_pct)
    cpu = float(scenario.workload.cpu_pct)
    inlet = float(scenario.environment.inlet_c)
    max_feed, min_cpu, min_inlet = feed, cpu, inlet
    work = 0.0
    degraded_s = 0
    for s in trace:
        while ei < len(events) and events[ei].at_s <= s.t:
            ev = events[ei]
            ei += 1
            if ev.action == "set-workload" and ev.workload is not None:
                feed = float(ev.workload.data_feed_pct)
                cpu = float(ev.workload.cpu_pct)
            elif ev.action == "set-data-feed" and ev.value is not None:
                feed = float(int(ev.value))
            elif ev.action == "set-inlet" and ev.value is not None:
                inlet = float(ev.value)
        max_feed = max(max_feed, feed)
        min_cpu = min(min_cpu, cpu)
        min_inlet = min(min_inlet, inlet)
        if s.powered_on:
            # effective_gpu_util_pct already folds in feed and throttle clamp.
            work += (s.effective_gpu_util_pct / 100.0) * n_gpu * tdp
            if 0 < s.flow_lpm <= DEGRADED_FLOW_FRACTION * cfg.coolant_flow_lpm:
                degraded_s += 1

    n = len(trace)
    on = [s for s in trace if s.powered_on]
    return {
        "durationS": float(trace[-1].t),
        "workRateW": round(work / n, 1),
        "throttleSeconds": float(summary.throttle_seconds),
        "shutdown": 1.0 if summary.shutdown else 0.0,
        "validationErrors": float(sum(1 for v in validations if v.level == "error")),
        "peakGpuHotC": round(max(s.gpu_temp_hot_c for s in trace), 2),
        "minInletC": round(min_inlet, 2),
        "maxDataFeedPct": round(max_feed, 1),
        "minCpuPct": round(min_cpu, 1),
        "gpuHoursWasted": round(summary.gpu_hours_wasted, 3),
        "meanCoolingOverheadPct": round(
            sum(s.cooling_overhead_pct for s in on) / max(len(on), 1), 2
        ),
        "meanWallW": round(sum(s.ac_power_w for s in trace) / n, 1),
        "pcieGpusFitted": float(cfg.pcie_gpus if cfg.product == "xe7745" else 0),
        "hgxNics": float(cfg.nics if cfg.product == "xe9680" else 0),
        "rackTrays": float(cfg.trays if cfg.product == "xe9712" else 0),
        "minCoolantSupplyC": round(min(s.coolant_supply_c for s in trace), 2),
        "peakCoolantReturnC": round(max(s.coolant_return_c for s in trace), 2),
        "pumpDegradedSeconds": float(degraded_s),
    }


# --- Criteria shared between labs ------------------------------------------

def _work(floor_w: int, shown: str) -> Criterion:
    return Criterion(
        id="work", label=f"Delivered GPU work at least {shown}",
        metric="workRateW", op=">=", threshold=floor_w, unit="W-TDP",
        weight=2.0, guards_work=True, explain_id="starvation", equation=EQ_STARVE,
        why=L(
            standard=(
                f"Work is effective GPU utilization × GPU count × the GPU's "
                f"nameplate TDP, averaged over the whole run; {shown} is the "
                "floor. Effective utilization is demand × data feed × the "
                "throttle clamp, so an idle, starved, throttled or tripped "
                "system earns less and turning the load down is not a way "
                "through. The proxy is illustrative, not a benchmark."
            ),
            novice=(
                f"The GPUs have to do real work for the whole run — at least "
                f"{shown}. We count work as how busy the GPUs really are, "
                "times how many there are, times how big each one is (its "
                "TDP, the watts it is built for). 'Really busy' matters: a "
                "GPU waiting for data is not working, a GPU that has slowed "
                "itself down to stay cool (throttling) is working less, and a "
                "machine that has switched off is not working at all. So you "
                "cannot win by leaving the machine idle. This is a simple "
                "stand-in for useful computing, not a real benchmark score."
            ),
            expert=(
                f"Mean of util_eff × clamp × N_gpu × TDP over all ticks, dark "
                f"ticks zero; floor {shown}. Illustrative proxy."
            ),
        ),
    )


def _stays_up(what: str) -> Criterion:
    return Criterion(
        id="stays-up", label="System stays powered on",
        metric="shutdown", op="<=", threshold=0, unit="", weight=2.0,
        explain_id="liquid-balance" if what == "rack" else "cooling-overhead",
        equation=EQ_LIQUID if what == "rack" else EQ_OVERHEAD,
        why=L(
            standard=(
                f"A sustained draw above 105% of the power budget trips the "
                f"{what}'s supply, and on the liquid rack a coolant return of "
                "75 °C forces an emergency power-off. A dark machine draws "
                "nothing and delivers nothing."
            ),
            novice=(
                f"The {what} must stay switched on for the whole run. It "
                "switches itself off if it pulls more electrical power than "
                "its supplies can give for half a minute, and the liquid-"
                "cooled rack also switches off if the water coming back from "
                "the GPUs reaches 75 °C. A machine that is off uses no power, "
                "but it also does no work, so it cannot pass."
            ),
            expert=f"No overcurrent trip (>1.05× budget, 30 s) and no 75 °C return EPO on the {what}.",
        ),
    )


def _full_run(seconds: int) -> Criterion:
    return Criterion(
        id="full-run", label=f"Run lasts at least {seconds} s",
        metric="durationS", op=">=", threshold=seconds, unit="s",
        explain_id="cooling-overhead", equation=EQ_OVERHEAD,
        why=L(
            standard=(
                f"Silicon settles in about a minute, the fan loop and the "
                f"coolant loop take several; the lab needs the full "
                f"{seconds} s it starts with so it is graded on temperatures "
                "that have actually arrived."
            ),
            novice=(
                f"Heat takes time. The chips warm up in about a minute, and "
                f"the fans or the water loop then need several more minutes "
                f"to settle. A shorter run would end before the machine "
                f"reached the temperatures this lab is about, so the run "
                f"must last the full {seconds} seconds the lab starts with."
            ),
            expert=f"≥ {seconds} s: past τ_gpu = 20 s, the fan loop and τ_coolant = 60 s.",
        ),
    )


# --- Lab 1: the worst seat (XE7745) ----------------------------------------

_SEAT_START = Scenario(
    config=XE7745_8GPU, workload=Workload(gpu_pct=100, cpu_pct=50),
    environment=Environment(inlet_c=30), duration_s=900,
)

WORST_SEAT = Lab(
    id="worst-seat",
    title="Keep the worst seat cool",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "Eight PCIe GPUs in a 30 °C aisle. Each riser slot breathes "
                "air the slots in front of it have already warmed, so the "
                "last slot runs hottest and throttles first. Keep all eight "
                "cards, deliver the work, and hold the hottest slot at "
                "88.5 °C or less — a degree and a half under the throttle "
                "line — for the whole run."
            ),
            novice=(
                "This server holds eight GPU cards in a row, and the room is "
                "warm: 30 °C. The cooling air passes the cards one after "
                "another, so each card gets air that the cards before it "
                "have already heated. The last card in the row gets the "
                "warmest air and is always the hottest. At 90 °C a card "
                "slows itself down to stay safe (throttling). Your job: keep "
                "all eight cards in the server, get the work done, and keep "
                "the hottest card at 88.5 °C or less for the whole run, so "
                "there is a small safety margin."
            ),
            expert=(
                "XE7745, 8 cards, T_inlet ≥ 30 °C: max slot temperature "
                "≤ 88.5 °C, zero clamp, work floor 4,000 W-TDP."
            ),
        ),
        constraints=[
            L(standard="An XE7745 with all eight PCIe GPUs fitted.",
              novice="Use the XE7745 server and leave all eight GPU cards in it. Pulling cards out is not allowed.",
              expert="XE7745, 8 GPUs."),
            L(standard="Inlet air never below 30 °C, for the full 900 s.",
              novice="The room air stays at 30 °C or warmer for the whole 900-second run. Cooling the room is not allowed.",
              expert="min T_inlet ≥ 30 °C, 900 s."),
            L(standard="No GPU throttles at any point, and the hottest slot peaks at 88.5 °C or less.",
              novice="No card may slow itself down at any moment, and the hottest card must never go above 88.5 °C.",
              expert="throttle-seconds = 0; max T_slot ≤ 88.5 °C."),
        ],
        delivered_work=L(
            standard="At least 4,000 W-TDP of GPU work, averaged over the run.",
            novice="The cards must do at least 4,000 units of work on average — for example eight 600 W cards kept about 84% busy. An idle server does not count.",
            expert="workRateW ≥ 4000.",
        ),
    ),
    criteria=[
        _work(4000, "4,000 W-TDP"),
        Criterion(
            id="eight-cards", label="XE7745 with all eight GPUs fitted",
            metric="pcieGpusFitted", op=">=", threshold=8, unit="GPUs",
            explain_id="positional", equation=EQ_POSITIONAL,
            why=L(
                standard=(
                    "Pulling cards shortens the row, and the last slot's "
                    "preheat falls by 1.1 °C per card removed — but every "
                    "card removed takes an eighth of the work with it. The "
                    "lab keeps the row full so the problem stays the worst "
                    "seat, not the seating plan."
                ),
                novice=(
                    "If you take cards out, the row gets shorter and the "
                    "last card gets slightly cooler air (about 1.1 °C cooler "
                    "for each card removed). But each card you remove also "
                    "removes one eighth of the work. This lab asks you to "
                    "solve the problem with all eight cards in place, so "
                    "this line checks that the server is an XE7745 with "
                    "eight GPUs."
                ),
                expert="product = xe7745 and N = 8; preheat(7) = 7 × 1.1 K stays in play.",
            ),
        ),
        Criterion(
            id="hot-inlet", label="Inlet air never below 30 °C",
            metric="minInletC", op=">=", threshold=30, unit="°C",
            explain_id="positional", equation=EQ_POSITIONAL,
            why=L(
                standard=(
                    "Every slot's inlet is room air plus its positional "
                    "preheat, so T_room is the one term you may not lower. "
                    "The lab is set in a 30 °C aisle."
                ),
                novice=(
                    "Each card's air temperature is the room temperature "
                    "plus the warming from the cards in front of it. Cooling "
                    "the room would be the easy answer, so the lab does not "
                    "allow it: the Inlet slider has to stay at 30 °C or "
                    "higher for the whole run."
                ),
                expert="min T_room ≥ 30 °C; T_room is fixed.",
            ),
        ),
        Criterion(
            id="no-throttle", label="No GPU throttles at any point",
            metric="throttleSeconds", op="<=", threshold=0, unit="s", weight=2.0,
            explain_id="positional", equation=EQ_POSITIONAL,
            why=L(
                standard=(
                    "Above 90 °C a slot clamps its own power, and on this "
                    "machine the clamp always starts at the back of the row: "
                    "the last slot breathes air 7.7 °C warmer than the "
                    "first. Every clamped second is lost work."
                ),
                novice=(
                    "When a card goes above 90 °C it protects itself by "
                    "slowing down. That is throttling, and every second of "
                    "it is work you did not get. In this server it always "
                    "starts with the last card in the row, because that "
                    "card's air is 7.7 °C warmer than the first card's."
                ),
                expert="clamp < 1 above 90 °C; slot 7 sits 7 × 1.1 K above slot 0.",
            ),
        ),
        Criterion(
            id="margin", label="Hottest slot peaks at 88.5 °C or less",
            metric="peakGpuHotC", op="<=", threshold=88.5, unit="°C", weight=2.0,
            explain_id="positional", equation=EQ_POSITIONAL,
            why=L(
                standard=(
                    "A slot that settles at 89.9 °C is one warm afternoon "
                    "from throttling. The lab asks for 1.5 °C of margin on "
                    "the worst seat; the seven cooler seats get that margin "
                    "and more for free."
                ),
                novice=(
                    "A card sitting at 89.9 °C has not throttled yet, but "
                    "the smallest change in the room would push it over. So "
                    "the lab asks for a safety margin: the hottest card must "
                    "stay at 88.5 °C or less. The other seven cards sit in "
                    "cooler air, so if the last one passes, they all do."
                ),
                expert="max_t max_i T_slot(i) ≤ 88.5 °C — 1.5 K under the clamp.",
            ),
        ),
        _full_run(900),
        _stays_up("server"),
    ],
    objective=Objective(
        label="Delivered GPU work", metric="workRateW", direction="maximize",
        par=4320, worst=4000, unit="W-TDP",
        explain_id="positional", equation=EQ_POSITIONAL,
    ),
    hints=[
        L(standard="Play the start scenario and watch the GPU row on the chassis map: the throttle starts at the back slot, not everywhere. Open Positional preheat in Explain mode.",
          novice="Press Run on the starting setup and watch the row of GPU cards on the picture of the server. Only the cards at the back of the row turn hot enough to slow down. Turn on Explain mode and read 'Positional preheat' to see why.",
          expert="Watch gpu-7 vs gpu-0; read the positional entry."),
        L(standard="Two obvious fixes both cost too much work: 450 W cards at full load deliver only 3,600 W-TDP, and six 600 W cards deliver only 3,600 W-TDP. The floor is 4,000.",
          novice="Two fixes look tempting. Smaller 450 W cards stay cool, but eight of them at full load only do 3,600 units of work. Taking two cards out also cools the row, but six 600 W cards only do 3,600 units too. The lab needs 4,000, so neither works.",
          expert="8 × 450 W = 6 × 600 W = 3,600 W-TDP < floor."),
        L(standard="The worst seat sets the pace for the whole row. Keep the eight 600 W cards and turn the GPU dial down: at 90% the last slot peaks near 88.4 °C and the row still delivers 4,320 W-TDP.",
          novice="The hottest card decides how hard all eight can run. Keep the eight big 600 W cards and lower the GPU slider instead. At 90% the last card peaks at about 88.4 °C, inside the margin, and the eight cards together still do 4,320 units of work.",
          expert="8 × 600 W at 90%: T_max ≈ 88.4 °C, 4,320 W-TDP."),
    ],
    start=_SEAT_START.model_dump(by_alias=True),
)


# --- Lab 2: starved, not stalled (XE9680) ----------------------------------

_STARVED_START = Scenario(
    config=XE9680_H100, workload=Workload(gpu_pct=100, cpu_pct=50, data_feed_pct=60),
    environment=Environment(), duration_s=900,
)

STARVED_NOT_STALLED = Lab(
    id="starved-not-stalled",
    title="Starved, not stalled",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "The storage pipeline can deliver only 60% of what the HGX "
                "board asks for, and you cannot fix the pipeline. A starved "
                "GPU busy-waits: it burns most of its power and produces no "
                "tokens, and the ledger books the gap as wasted GPU-hours. "
                "Deliver the work anyway while wasting no more than 0.60 "
                "GPU-hours in the run, without throttling and with cooling "
                "overhead at 2% or less."
            ),
            novice=(
                "GPUs need a steady stream of data to work on. Here the "
                "storage system can only supply 60% of what the eight GPUs "
                "ask for, and you are not allowed to fix that. A GPU that is "
                "waiting for data does no useful work, but it still uses "
                "most of its power while it waits. The simulator adds up "
                "that waiting time as 'GPU-hours wasted'. Your job: still "
                "get the work done, but waste no more than 0.60 GPU-hours "
                "during the run. The GPUs must not slow themselves down "
                "from heat, and the fans must use no more than 2% of the "
                "power the computing parts use."
            ),
            expert=(
                "XE9680, feed ≤ 60%: work ≥ 3,300 W-TDP, wasted ≤ 0.60 "
                "GPU-h over 900 s, zero clamp, mean cooling overhead ≤ 2%."
            ),
        ),
        constraints=[
            L(standard="An XE9680 with one NIC per GPU (eight or more).",
              novice="Use the XE9680 server and keep at least eight network cards, one for each GPU.",
              expert="XE9680, NICs ≥ 8."),
            L(standard="Data feed never above 60%, for the full 900 s.",
              novice="The Data feed slider must stay at 60% or lower for the whole 900-second run. Turning the feed up is not allowed.",
              expert="max feed ≤ 60%, 900 s."),
            L(standard="No more than 0.60 GPU-hours wasted, no throttling, mean cooling overhead 2% or less.",
              novice="Waste at most 0.60 GPU-hours, never let the GPUs throttle, and keep the fans' share of power at 2% or less on average.",
              expert="wasted ≤ 0.60 GPU-h; clamp-free; overhead ≤ 2%."),
        ],
        delivered_work=L(
            standard="At least 3,300 W-TDP of GPU work, averaged over the run.",
            novice="The GPUs must do at least 3,300 units of real work on average. Waiting for data does not count as work.",
            expert="workRateW ≥ 3300.",
        ),
    ),
    criteria=[
        _work(3300, "3,300 W-TDP"),
        Criterion(
            id="hgx-build", label="XE9680 with one NIC per GPU",
            metric="hgxNics", op=">=", threshold=8, unit="NICs",
            explain_id="starvation", equation=EQ_STARVE,
            why=L(
                standard=(
                    "The lab is about the HGX board: eight GPUs that starve "
                    "together. Each GPU keeps its own 400G NIC — pulling "
                    "NICs to save 30 W apiece would strip the path the data "
                    "arrives on."
                ),
                novice=(
                    "This lab is about the XE9680, where eight GPUs share "
                    "one board and run short of data together. Each GPU has "
                    "its own network card, which is how data reaches it. "
                    "Removing network cards to save a little power is not "
                    "allowed, so this line checks for the XE9680 with at "
                    "least eight of them."
                ),
                expert="product = xe9680, NICs ≥ 8; no stripping the 1:1 GPU:NIC build.",
            ),
        ),
        Criterion(
            id="short-feed", label="Data feed never above 60%",
            metric="maxDataFeedPct", op="<=", threshold=60, unit="%",
            explain_id="starvation", equation=EQ_STARVE,
            why=L(
                standard=(
                    "The feed term is the storage tier's delivery rate, and "
                    "in this lab it is somebody else's system: min(1, feed) "
                    "stays at 0.6 or below. Everything you do, you do on the "
                    "demand side."
                ),
                novice=(
                    "The Data feed slider stands for the storage system, "
                    "and in this lab that system belongs to another team and "
                    "cannot be made faster. So the slider has to stay at 60% "
                    "or lower for the whole run. Whatever you change, it has "
                    "to be on the GPU side."
                ),
                expert="max over the run of feed ≤ 60%; only util_demand and the build are yours.",
            ),
        ),
        Criterion(
            id="waste-cap", label="No more than 0.60 GPU-hours wasted",
            metric="gpuHoursWasted", op="<=", threshold=0.60, unit="GPU-h",
            weight=2.0, explain_id="starvation", equation=EQ_STARVE,
            why=L(
                standard=(
                    "Wasted GPU-hours are demand minus delivery, summed over "
                    "eight GPUs. At a 60% feed, 40% of whatever you demand "
                    "is wasted, so the waste scales with the GPU dial: 100% "
                    "demand wastes 0.80 GPU-hours in 900 s, and the stalled "
                    "share still burns 65% of its power."
                ),
                novice=(
                    "The simulator counts a GPU as wasted whenever it is "
                    "asked to work but has no data. With the feed at 60%, "
                    "four tenths of whatever you ask for is wasted. Ask for "
                    "100% and the eight GPUs waste 0.80 GPU-hours in this "
                    "run, which is too much. Worse, a waiting GPU still "
                    "uses about two thirds of its power while it waits. The "
                    "waste grows and shrinks with the GPU slider."
                ),
                expert="wasted = Σ N × (util_demand − util_eff) dt = 8 × 0.4 × util × 0.25 h; stall burns 0.65 P.",
            ),
        ),
        Criterion(
            id="no-throttle", label="HGX board never throttles",
            metric="throttleSeconds", op="<=", threshold=0, unit="s", weight=2.0,
            explain_id="cooling-overhead", equation=EQ_OVERHEAD,
            why=L(
                standard=(
                    "The HGX baseboard is one thermal zone: above 90 °C all "
                    "eight GPUs clamp together, so a throttle here costs the "
                    "whole board at once."
                ),
                novice=(
                    "In the XE9680 the eight GPUs sit on one shared board "
                    "and heat up together. If the board goes above 90 °C, "
                    "all eight slow down at the same moment, so throttling "
                    "here costs eight GPUs' worth of work at once."
                ),
                expert="One zone, shared fate: gpusThrottled ∈ {0, 8}.",
            ),
        ),
        Criterion(
            id="overhead", label="Mean cooling overhead 2% or less",
            metric="meanCoolingOverheadPct", op="<=", threshold=2.0, unit="%",
            explain_id="cooling-overhead", equation=EQ_OVERHEAD,
            why=L(
                standard=(
                    "Fan power grows with the cube of fan speed, and stalled "
                    "GPUs heat the board almost as much as working ones. "
                    "Demanding 100% of a 1,000 W board on a 60% feed pushes "
                    "the fan wall to nearly 10% of IT power to cool work that is "
                    "not happening."
                ),
                novice=(
                    "Fans use power too, and a fan running twice as fast "
                    "uses eight times the power. A GPU waiting for data is "
                    "nearly as hot as a working one, so the fans have to "
                    "cool it just the same. If you ask the big 1,000 W GPUs "
                    "for 100% while the data feed is only 60%, the fans end "
                    "up using nearly 10% of the computing power just to "
                    "cool GPUs that are mostly waiting."
                ),
                expert="P_fan ∝ rpm³; stall heat is real heat. B200 at 100% on a 0.6 feed: ≈ 9.8%.",
            ),
        ),
        _full_run(900),
        _stays_up("server"),
    ],
    objective=Objective(
        label="GPU-hours wasted", metric="gpuHoursWasted", direction="minimize",
        par=0.555, worst=0.60, unit="GPU-h",
        explain_id="starvation", equation=EQ_STARVE,
    ),
    hints=[
        L(standard="Open Data starvation in Explain mode and compare the two strip charts: tokens fall with the feed, watts fall far less. Then look at how the wasted-GPU-hours counter depends on the GPU dial.",
          novice="Turn on Explain mode and read 'Data starvation'. Then watch the charts: when data runs short the tokens drop a lot but the power hardly drops. Now move the GPU slider and watch how quickly the 'GPU-hours wasted' number climbs.",
          expert="Read the starvation entry; d(wasted)/d(util) is constant at fixed feed."),
        L(standard="On the 700 W board the two limits cannot both be met: the work floor needs the dial at 99% or more, the waste cap needs it at 74% or less. Work is utilization × TDP, waste is utilization alone.",
          novice="With the 700 W GPUs there is no answer. To do enough work you would need the GPU slider at 99% or more, but to keep the waste down you need it at 74% or less. Notice the difference: work depends on how busy the GPUs are AND how big they are, while waste only depends on how busy you ask them to be.",
          expert="H100: floor ⇒ util ≥ 0.99, cap ⇒ util ≤ 0.74. Work ∝ util × TDP; waste ∝ util."),
        L(standard="Buy work with silicon, not with demand: the 1,000 W board at 69% delivers 3,312 W-TDP, wastes about 0.55 GPU-hours, and keeps the fans near their floor.",
          novice="Get the work from bigger GPUs instead of from asking harder. Choose the 1,000 W GPUs and set the GPU slider to 69%. They deliver 3,312 units of work, waste only about 0.55 GPU-hours, and run cool enough that the fans stay slow.",
          expert="B200 at 69%: 3,312 W-TDP, ≈ 0.553 GPU-h, overhead ≈ 1.2%."),
    ],
    start=_STARVED_START.model_dump(by_alias=True),
)


# --- Lab 3: warm water, one pump down (XE9712) -----------------------------

_PUMP_DOWN = [SimEvent(at_s=300, action="degrade-pump", value=0.75)]

_WARM_START = Scenario(
    config=XE9712_FULL.model_copy(update={"coolant_supply_c": 32}),
    workload=Workload(gpu_pct=100, cpu_pct=50), environment=Environment(),
    duration_s=1200, events=_PUMP_DOWN,
)

WARM_WATER_PUMP_DOWN = Lab(
    id="warm-water-pump-down",
    title="Warm water, one pump down",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "The facility wants the warmest coolant it can get — every "
                "degree of supply temperature is chiller energy not spent. "
                "The full 18-tray rack must also ride through a pump "
                "failure: by t+300 s the loop loses 75% of its flow and "
                "never gets it back. Deliver the work without throttling, "
                "then push the supply temperature as high as the degraded "
                "loop allows."
            ),
            novice=(
                "This rack is cooled by water instead of air. The building "
                "would like that water to be as warm as possible, because "
                "warm water is cheap to make and cold water needs "
                "power-hungry chillers. But there is a catch: 300 seconds "
                "into the run one of the rack's pumps fails, the water slows "
                "to a quarter of its normal flow, and it stays that way. "
                "Slow water picks up more heat on its way through the rack. "
                "Your job: keep all 18 trays of GPUs working through the "
                "pump failure with no throttling, and then make the supply "
                "water as warm as you can."
            ),
            expert=(
                "XE9712 × 18, −75% flow from t ≤ 300 s, T_supply ≥ 32 °C, "
                "zero clamp, work ≥ 90 kW-TDP; maximize T_supply."
            ),
        ),
        constraints=[
            L(standard="An XE9712 rack with all 18 compute trays and no validation errors.",
              novice="Use the XE9712 rack with all 18 trays in it, and no red errors in the build panel.",
              expert="18 trays, zero errors."),
            L(standard="The pump is degraded by 75% from t+300 s to the end of the 1,200 s run (at least 900 degraded seconds).",
              novice="The pump failure that the lab starts with must stay in the run: from 300 seconds to the end of the 1,200-second run the water flows at a quarter of its normal rate. If you press Reset and lose the failure, use 'Reset to the lab's start'.",
              expert="flow ≤ 0.26 × design for ≥ 900 s of 1,200."),
            L(standard="Coolant supply never below 32 °C, host CPUs never below 50%, no throttling, rack stays up.",
              novice="Keep the supply water at 32 °C or warmer, keep the CPU slider at 50% or higher (the CPUs feed the GPUs), never let the GPUs throttle, and keep the rack switched on.",
              expert="T_supply ≥ 32 °C; CPU ≥ 50%; clamp-free; no EPO."),
        ],
        delivered_work=L(
            standard="At least 90 kW-TDP (90,000 W-TDP) of GPU work, averaged over the run.",
            novice="The 72 GPUs must do at least 90,000 units of work on average — that is 72 GPUs of 1,400 W kept about 90% busy. A throttled or idle rack does not count.",
            expert="workRateW ≥ 90000.",
        ),
    ),
    criteria=[
        _work(90000, "90 kW-TDP"),
        Criterion(
            id="full-rack", label="XE9712 rack with all 18 trays",
            metric="rackTrays", op=">=", threshold=18, unit="trays",
            explain_id="liquid-balance", equation=EQ_LIQUID,
            why=L(
                standard=(
                    "Q_liquid is the whole rack's heat. Pulling trays lowers "
                    "Q and with it ΔT, but the lab is about carrying the "
                    "full 100 kW-class load on a quarter of the flow."
                ),
                novice=(
                    "All the heat the rack makes ends up in the water. Fewer "
                    "trays would mean less heat and an easier problem, but "
                    "this lab is about the full rack, so this line checks "
                    "for the XE9712 with all 18 trays."
                ),
                expert="product = xe9712, trays = 18; Q stays rack-scale.",
            ),
        ),
        Criterion(
            id="pump-down", label="Pump degraded 75% for at least 900 s",
            metric="pumpDegradedSeconds", op=">=", threshold=900, unit="s",
            weight=2.0, explain_id="liquid-balance", equation=EQ_LIQUID,
            why=L(
                standard=(
                    "ṁ sits in the denominator: a quarter of the flow is "
                    "four times the ΔT for the same heat. The lab counts the "
                    "seconds the loop ran at 26% of design flow or less; the "
                    "failure must arrive by t+300 s and stay."
                ),
                novice=(
                    "The water's temperature rise equals the heat divided by "
                    "how much water is flowing. A quarter of the flow means "
                    "four times the temperature rise for the same heat. This "
                    "line counts how many seconds the rack really ran on a "
                    "quarter of its flow. It must be at least 900 seconds, "
                    "so the pump failure has to happen by 300 seconds and "
                    "last to the end."
                ),
                expert="Σ ticks with 0 < ṁ ≤ 0.26 × ṁ_design ≥ 900 s.",
            ),
        ),
        Criterion(
            id="warm-supply", label="Coolant supply never below 32 °C",
            metric="minCoolantSupplyC", op=">=", threshold=32, unit="°C",
            explain_id="liquid-balance", equation=EQ_LIQUID,
            why=L(
                standard=(
                    "Return temperature is supply plus ΔT, so cold supply "
                    "water hides any amount of ΔT. The facility runs a W32 "
                    "warm-water loop: 32 °C is the coldest water on offer."
                ),
                novice=(
                    "The water coming back is as warm as the water going in "
                    "plus the heat it picked up. Very cold supply water "
                    "would hide the problem, but it needs chillers, and this "
                    "building does not run them: 32 °C is the coldest water "
                    "you can have."
                ),
                expert="min T_supply ≥ 32 °C (W32 class); T_return = T_supply + ΔT.",
            ),
        ),
        Criterion(
            id="hosts-busy", label="Host CPUs never below 50%",
            metric="minCpuPct", op=">=", threshold=50, unit="%",
            explain_id="liquid-balance", equation=EQ_LIQUID,
            why=L(
                standard=(
                    "Q_liquid + Q_air = P_dc: every watt in the rack, the 36 "
                    "host CPUs' included, leaves as heat and 88% of it "
                    "leaves in the water. Idling the hosts would trim Q, but "
                    "the hosts are what feeds the GPUs."
                ),
                novice=(
                    "Every watt the rack uses turns into heat, and most of "
                    "that heat goes into the water — including the heat from "
                    "the 36 ordinary processors (CPUs) that prepare data for "
                    "the GPUs. Switching those to idle would make less heat, "
                    "but then nothing would feed the GPUs, so the CPU slider "
                    "must stay at 50% or higher."
                ),
                expert="min CPU util ≥ 50%: host heat is part of Q; no trimming it to zero.",
            ),
        ),
        Criterion(
            id="no-throttle", label="No tray throttles at any point",
            metric="throttleSeconds", op="<=", threshold=0, unit="s", weight=2.0,
            explain_id="liquid-balance", equation=EQ_LIQUID,
            why=L(
                standard=(
                    "When the return passes 65 °C the loop's protection "
                    "clamps every tray together, and a cold plate fed 65 °C "
                    "water puts its GPU at the 90 °C line as well. After the "
                    "pump fails, return = supply + 4 × the healthy ΔT."
                ),
                novice=(
                    "If the water coming back from the GPUs goes above "
                    "65 °C, the rack protects itself by slowing every tray "
                    "down at once. After the pump fails the water heats up "
                    "four times as much on its way through, so the return "
                    "temperature is the supply temperature plus four times "
                    "the normal rise. That sum has to stay under 65 °C."
                ),
                expert="T_return > 65 °C clamps all trays; post-failure ΔT = 4 × ΔT_design.",
            ),
        ),
        Criterion(
            id="valid-build", label="Build has no validation errors",
            metric="validationErrors", op="<=", threshold=0, unit="errors",
            explain_id="liquid-balance", equation=EQ_LIQUID,
            why=L(
                standard=(
                    "At rack scale the budgets are the product: tray power "
                    "against shelf capacity, tray coolant demand against the "
                    "manifolds. A rack that fails either is not a rack Dell "
                    "would integrate."
                ),
                novice=(
                    "The build panel checks the rack against its budgets: "
                    "the power shelves must be able to supply all the trays, "
                    "and the pipes (manifolds) must be able to carry enough "
                    "water. Red errors mean the rack could not be built, so "
                    "it does not count. Yellow warnings are allowed."
                ),
                expert="Zero error-level findings: shelf kW and manifold L/min budgets hold.",
            ),
        ),
        _full_run(1200),
        _stays_up("rack"),
    ],
    objective=Objective(
        label="Coldest coolant supply in the run", metric="minCoolantSupplyC",
        direction="maximize", par=43, worst=32, unit="°C",
        explain_id="liquid-balance", equation=EQ_LIQUID,
    ),
    hints=[
        L(standard="Play the start scenario with The liquid heat balance open in Explain mode and watch coolant ΔT at t+300 s: it quadruples, and the return crosses 65 °C within two minutes.",
          novice="Turn on Explain mode, open 'The liquid heat balance', press Run and watch the coolant numbers at 300 seconds. The temperature rise across the rack becomes four times bigger, and within two minutes the return water passes 65 °C and the GPUs slow down.",
          expert="Watch ΔT step ×4 at t = 300 s; τ_coolant = 60 s."),
        L(standard="ΔT = Q / (ṁ × cp). You cannot stop the pump failing, but the design flow is yours: the failure takes 75% of whatever you start with. Size the loop for the degraded day, not the healthy one.",
          novice="The temperature rise is the heat divided by the flow. You cannot stop the pump from failing, but you choose how much flow the rack starts with, and the failure leaves you a quarter of that. So plan the flow for the bad day, not the good day: start with as much as the slider allows.",
          expert="Post-failure ṁ = 0.25 × ṁ_design. Max the design flow."),
        L(standard="At 240 L/min the degraded loop carries 60 L/min, and the full rack at 100% still returns only about 24 °C above supply. The other lever is Q: work needs 90 kW-TDP, which is the GPU dial at 90%, and every watt you do not demand is a degree of supply you can add.",
          novice="Set the design flow to 240 litres a minute. After the failure that leaves 60, and even at full load the water only warms by about 24 °C. The second thing you control is the heat itself: the lab only needs 90,000 units of work, which is the GPU slider at 90%. Less heat means a smaller temperature rise, and that lets you raise the supply temperature.",
          expert="240 L/min → 60 L/min; trade util for T_supply down to the 90 kW-TDP floor."),
        L(standard="240 L/min, GPUs at 90%, CPUs at 50%: the return peaks near 64.7 °C with the supply at 43 °C. At 44 °C the loop protection trips the clamp.",
          novice="With the flow at 240 litres a minute, the GPU slider at 90% and the CPU slider at 50%, you can raise the coolant supply to 43 °C: the return water peaks at about 64.7 °C, just under the limit. At 44 °C it goes over and the GPUs throttle.",
          expert="240 L/min, 90% / 50%: T_supply = 43 °C → T_return ≈ 64.7 °C; 44 °C clamps."),
    ],
    start=_WARM_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [WORST_SEAT, STARVED_NOT_STALLED, WARM_WATER_PUMP_DOWN]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Reference solutions and the tricks that must not work -----------------
# Server-side only: GET /api/labs serves LABS, never these.

_AISLE_30 = Environment(inlet_c=30)
_RACK_REF = XE9712_FULL.model_copy(update={
    "coolant_flow_lpm": 240, "coolant_supply_c": 43,
})

REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    "worst-seat": Scenario(
        config=XE7745_8GPU, workload=Workload(gpu_pct=90, cpu_pct=50),
        environment=_AISLE_30, duration_s=900,
    ),
    "starved-not-stalled": Scenario(
        config=XE9680_B200,
        workload=Workload(gpu_pct=69, cpu_pct=50, data_feed_pct=60),
        duration_s=900,
    ),
    "warm-water-pump-down": Scenario(
        config=_RACK_REF, workload=Workload(gpu_pct=90, cpu_pct=50),
        duration_s=1200, events=_PUMP_DOWN,
    ),
}

_IDLE = Workload()

GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "worst-seat": {
        "zero load": Scenario(config=XE7745_8GPU, workload=_IDLE,
                              environment=_AISLE_30, duration_s=900),
        "cool the room": Scenario(
            config=XE7745_8GPU, workload=Workload(gpu_pct=100, cpu_pct=50),
            environment=Environment(inlet_c=18), duration_s=900),
        "pull two cards": Scenario(
            config=XE7745_8GPU.model_copy(update={"pcie_gpus": 6}),
            workload=Workload(gpu_pct=100, cpu_pct=50),
            environment=_AISLE_30, duration_s=900),
        "smaller cards at full load": Scenario(
            config=XE7745_8GPU.model_copy(update={"pcie_gpu_tdp_w": 450}),
            workload=Workload(gpu_pct=100, cpu_pct=50),
            environment=_AISLE_30, duration_s=900),
        "short run": Scenario(
            config=XE7745_8GPU, workload=Workload(gpu_pct=100, cpu_pct=50),
            environment=_AISLE_30, duration_s=30),
        "ride the throttle line": Scenario(
            config=XE7745_8GPU, workload=Workload(gpu_pct=95, cpu_pct=50),
            environment=_AISLE_30, duration_s=900),
        "another machine": Scenario(
            config=XE9680_B200, workload=Workload(gpu_pct=60, cpu_pct=50),
            environment=_AISLE_30, duration_s=900),
        "cool the room halfway": Scenario(
            config=XE7745_8GPU, workload=Workload(gpu_pct=100, cpu_pct=50),
            environment=_AISLE_30, duration_s=900,
            events=[SimEvent(at_s=5, action="set-inlet", value=15)]),
    },
    "starved-not-stalled": {
        "zero load": Scenario(
            config=XE9680_B200, workload=Workload(data_feed_pct=60), duration_s=900),
        "fix the pipeline": Scenario(
            config=XE9680_H100, workload=Workload(gpu_pct=100, cpu_pct=50),
            duration_s=900),
        "fix the pipeline after a second": Scenario(
            config=XE9680_B200,
            workload=Workload(gpu_pct=69, cpu_pct=50, data_feed_pct=60),
            duration_s=900,
            events=[SimEvent(at_s=1, action="set-data-feed", value=100)]),
        "demand everything on the big board": Scenario(
            config=XE9680_B200,
            workload=Workload(gpu_pct=100, cpu_pct=50, data_feed_pct=60),
            duration_s=900),
        "turn the small board down": Scenario(
            config=XE9680_H100,
            workload=Workload(gpu_pct=70, cpu_pct=50, data_feed_pct=60),
            duration_s=900),
        "short run": Scenario(
            config=XE9680_B200,
            workload=Workload(gpu_pct=100, cpu_pct=50, data_feed_pct=60),
            duration_s=60),
        "pull the NICs": Scenario(
            config=XE9680_B200.model_copy(update={"nics": 0}),
            workload=Workload(gpu_pct=69, cpu_pct=50, data_feed_pct=60),
            duration_s=900),
        "the liquid rack instead": Scenario(
            config=XE9712_FULL,
            workload=Workload(gpu_pct=10, cpu_pct=50, data_feed_pct=60),
            duration_s=900),
        "idle first, load later": Scenario(
            config=XE9680_B200, workload=Workload(data_feed_pct=60),
            duration_s=900,
            events=[SimEvent(at_s=800, action="set-workload",
                             workload=Workload(gpu_pct=100, cpu_pct=50,
                                               data_feed_pct=60))]),
    },
    "warm-water-pump-down": {
        "zero load": Scenario(config=_RACK_REF, workload=_IDLE,
                              duration_s=1200, events=_PUMP_DOWN),
        "no pump failure": Scenario(
            config=_RACK_REF, workload=Workload(gpu_pct=100, cpu_pct=50),
            duration_s=1200),
        "fail the pump at the end": Scenario(
            config=_RACK_REF, workload=Workload(gpu_pct=100, cpu_pct=50),
            duration_s=1200,
            events=[SimEvent(at_s=1199, action="degrade-pump", value=0.75)]),
        "a gentler failure": Scenario(
            config=_RACK_REF, workload=Workload(gpu_pct=100, cpu_pct=50),
            duration_s=1200,
            events=[SimEvent(at_s=300, action="degrade-pump", value=0.30)]),
        "fail it, then mend it": Scenario(
            config=_RACK_REF, workload=Workload(gpu_pct=100, cpu_pct=50),
            duration_s=1200,
            events=_PUMP_DOWN + [SimEvent(at_s=301, action="degrade-pump", value=0.0)]),
        "cold water": Scenario(
            config=_RACK_REF.model_copy(update={"coolant_supply_c": 20}),
            workload=Workload(gpu_pct=100, cpu_pct=50),
            duration_s=1200, events=_PUMP_DOWN),
        "cold water after the grade starts": Scenario(
            config=_RACK_REF, workload=Workload(gpu_pct=100, cpu_pct=50),
            duration_s=1200,
            events=_PUMP_DOWN + [SimEvent(at_s=2, action="set-coolant-supply", value=17)]),
        "idle the hosts": Scenario(
            config=_RACK_REF.model_copy(update={"coolant_supply_c": 44}),
            workload=Workload(gpu_pct=90, cpu_pct=0),
            duration_s=1200, events=_PUMP_DOWN),
        "half a rack": Scenario(
            config=_RACK_REF.model_copy(update={"trays": 9}),
            workload=Workload(gpu_pct=100, cpu_pct=50),
            duration_s=1200, events=_PUMP_DOWN),
        "short run": Scenario(
            config=_RACK_REF, workload=Workload(gpu_pct=100, cpu_pct=50),
            duration_s=320, events=_PUMP_DOWN),
        "warmest water at full load": Scenario(
            config=_RACK_REF.model_copy(update={"coolant_supply_c": 45}),
            workload=Workload(gpu_pct=100, cpu_pct=50),
            duration_s=1200, events=_PUMP_DOWN),
        "undersized shelves": Scenario(
            config=_RACK_REF.model_copy(update={"shelf_capacity_kw": 66}),
            workload=Workload(gpu_pct=90, cpu_pct=50),
            duration_s=1200, events=_PUMP_DOWN),
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
