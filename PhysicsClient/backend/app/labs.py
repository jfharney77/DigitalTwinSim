"""Graded labs for the client-device physics simulator (docs/LAB_PATTERN.md;
pilot: ``DellPowerEdgeR760Thermal/backend/app/labs.py``).

A guided scenario sets the dials and tells you what to watch. A lab states a
goal and leaves the dials to you: build a Scenario with the ordinary controls,
the engine runs it, and ``grade_scenario`` scores the trace.

Pure module, same rule as ``engine.py`` and ``validation.py``: no FastAPI, no
IO, no clock, no randomness (AST-checked in ``tests/test_labs.py``). ``main.py``
is the only caller that touches HTTP, so the static-hosting build runs this
same grading in the browser.

What is this app's own; everything else is ``twinkit.labs``:

* ``measure()`` — turns one run into named numbers. Two of them are delivered
  work, and both are **rates averaged over the whole run** with dark seconds
  counted as zero. ``workRateW`` is the compute power the silicon actually
  received above its idle floor (CPU + GPU + NPU watts, after the budget
  allocator, the skin governor and the throttles have had their say).
  ``meanTokensPerS`` is the inference output of the active engine. An idle,
  clamped or dead machine earns less of both. They are illustrative proxies
  for useful work, not benchmarks, and the UI says so.
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
    DeviceConfig,
    Environment,
    Scenario,
    SimEvent,
    SimState,
    Summary,
    Validation,
    Workload,
)
from .presets import AAA, AW_LAPTOP, EXPLAINS, LLM_NPU, PROMAX_NPU
from .validation import validate

# The equations, exactly as the Explain entries display them — read from the
# entries themselves, so an edit to an Explain equation cannot leave a lab
# quoting the old one.
_EQ = {e.id: e.equation for e in EXPLAINS}
EQ_LIMITS = _EQ["power-limits"]
EQ_BUDGET = _EQ["thermal-budget"]
EQ_SKIN = _EQ["skin-cap"]
EQ_RUNTIME = _EQ["battery-runtime"]
EQ_SUPPLY = _EQ["energy-identity"]
EQ_TOKENS = _EQ["tokens-per-joule"]


# --- Measurement ----------------------------------------------------------

def measure(
    scenario: Scenario,
    trace: list[SimState],
    summary: Summary,
    validations: list[Validation],
) -> dict[str, float]:
    """One run as named numbers. Keys are the wire names criteria refer to."""
    cfg = scenario.config
    laptop = cfg.form_factor == "laptop"
    cpu_idle = C("cpu_idle_fraction") * cfg.cpu_pl1_w
    gpu_idle = C("gpu_idle_fraction") * cfg.gpu_tgp_w
    npu_idle = C("npu_idle_w") if cfg.npu else 0.0

    # Replay the environment events exactly as the engine applies them, so
    # "on the lap the whole time" and "the room never cooled" are measured
    # rather than taken on trust.
    events = sorted(scenario.events, key=lambda e: e.at_s)
    ei = 0
    on_lap = scenario.environment.on_lap
    ambient = scenario.environment.ambient_c
    min_ambient = ambient
    off_lap_s = 0

    work = 0.0
    tokens = 0.0
    energy_j = 0.0
    for s in trace:
        while ei < len(events) and events[ei].at_s <= s.t:
            ev = events[ei]
            ei += 1
            if ev.action == "set-on-lap" and ev.value is not None:
                on_lap = ev.value >= 1
            elif ev.action == "set-ambient" and ev.value is not None:
                ambient = ev.value
        min_ambient = min(min_ambient, ambient)
        if not on_lap:
            off_lap_s += 1
        if s.powered_on:
            work += (
                max(0.0, s.cpu_power_w - cpu_idle)
                + max(0.0, s.gpu_power_w - gpu_idle)
                + max(0.0, s.npu_power_w - npu_idle)
            )
            tokens += s.tokens_per_s
            energy_j += s.system_power_w

    n = len(trace)
    wh = energy_j / 3600.0
    return {
        "durationS": float(trace[-1].t),
        "workRateW": round(work / n, 1),
        "meanTokensPerS": round(tokens / n, 2),
        "tokensPerWh": round(tokens / wh, 0) if wh > 0 else 0.0,
        "throttleSeconds": float(summary.throttle_seconds),
        "skinLimitedSeconds": float(
            sum(1 for s in trace if s.pl_state == "skin-limited")
        ),
        "peakSkinTempC": round(max(s.skin_temp_c for s in trace), 2),
        "shutdown": 1.0 if summary.shutdown else 0.0,
        "dischargeSeconds": float(
            sum(1 for s in trace if s.battery_discharge_w > 0)
        ),
        "acSeconds": float(sum(1 for s in trace if s.ac_input_w > 0)),
        "startChargePct": float(scenario.environment.start_charge_pct),
        "endBatteryPct": round(trace[-1].battery_pct, 2) if laptop else 0.0,
        "batteryHealthPct": float(cfg.battery_health_pct),
        "minAmbientC": round(min_ambient, 2),
        "offLapSeconds": float(off_lap_s),
        "isLaptop": 1.0 if laptop else 0.0,
        "ramGb": float(cfg.ram_gb),
        "validationErrors": float(sum(1 for v in validations if v.level == "error")),
    }


# --- Criteria shared between labs ------------------------------------------

def _work(floor_w: int) -> Criterion:
    return Criterion(
        id="work", label=f"Delivered compute at least {floor_w} W",
        metric="workRateW", op=">=", threshold=floor_w, unit="W",
        weight=2.0, guards_work=True, explain_id="thermal-budget",
        equation=EQ_BUDGET,
        why=L(
            standard=(
                f"Work is the power the CPU, GPU and NPU actually received "
                f"above their idle floors, averaged over the whole run; "
                f"{floor_w} W is the floor. The budget allocator, the skin "
                "governor and the throttles all take watts away before this "
                "number is counted, and a dead machine earns zero — so turning "
                "the load down is not a way through. The proxy is "
                "illustrative, not a benchmark."
            ),
            novice=(
                f"The laptop has to do real work the whole time: at least "
                f"{floor_w} watts of it, on average. We count work as the "
                "electrical power that actually reaches the three chips that "
                "compute (the CPU, the graphics chip or GPU, and the AI chip "
                "or NPU), not counting the little they draw when resting. "
                "When the laptop protects itself by cutting power to those "
                "chips, the score falls with it, and a laptop that has "
                "switched off scores nothing. So you cannot win by leaving "
                "the machine idle. This is a simple stand-in for useful "
                "computing, not a real benchmark score."
            ),
            expert=(
                f"Mean of Σ(P_cpu, P_gpu, P_npu above idle) over all ticks, "
                f"dark ticks zero; floor {floor_w} W. Illustrative proxy."
            ),
        ),
    )


def _no_throttle(lesson: str, lesson_novice: str, lesson_expert: str) -> Criterion:
    return Criterion(
        id="no-throttle", label="No throttling or skin limiting at any point",
        metric="throttleSeconds", op="<=", threshold=0, unit="s", weight=2.0,
        explain_id="power-limits", equation=EQ_LIMITS,
        why=L(
            standard=(
                "The clamps in the power-limit equation are the silicon "
                "throttles (CPU above 100 °C, GPU above 87 °C) and the skin "
                "governor (chassis above 46 °C). Every clamped second is work "
                "the build promised and did not deliver. " + lesson
            ),
            novice=(
                "A laptop protects itself in two ways. If a chip gets too hot "
                "(the processor above 100 °C, the graphics chip above 87 °C) "
                "it slows that chip down; that is called throttling. If the "
                "case gets too hot to touch (above 46 °C) it slows everything "
                "down. Either way you asked for work and did not get it, so "
                "this lab allows zero seconds of it. " + lesson_novice
            ),
            expert="Zero ticks with any clamp < 1 (CPU, GPU or skin). " + lesson_expert,
        ),
    )


def _stays_up() -> Criterion:
    return Criterion(
        id="stays-up", label="Machine stays powered on",
        metric="shutdown", op="<=", threshold=0, unit="", weight=2.0,
        explain_id="battery-runtime", equation=EQ_RUNTIME,
        why=L(
            standard=(
                "An unplugged laptop powers off when the pack reaches 2%, and "
                "a tower trips its supply on sustained overcurrent. A dark "
                "machine draws nothing and delivers nothing."
            ),
            novice=(
                "The machine must stay switched on for the whole run. A "
                "laptop running on its battery switches itself off when the "
                "battery is nearly empty (2%), and a desktop switches off if "
                "it pulls more power than its power supply can give. A "
                "machine that is off does no work, so it cannot pass."
            ),
            expert="No battery-exhaustion power-off (≤2%) and no PSU overcurrent trip.",
        ),
    )


def _laptop() -> Criterion:
    return Criterion(
        id="laptop", label="The machine is a laptop",
        metric="isLaptop", op=">=", threshold=1, unit="",
        explain_id="thermal-budget", equation=EQ_BUDGET,
        why=L(
            standard=(
                "The tower is the control group: separate coolers per part, "
                "no shared budget, no battery, no skin anyone touches. Every "
                "tension this lab is about exists only in the laptop chassis."
            ),
            novice=(
                "This lab is about a laptop. The desktop tower has a big "
                "separate cooler for each chip, no battery, and a case nobody "
                "holds, so none of the problems in this lab happen to it. "
                "Switching the form factor to desktop would skip the lesson, "
                "so it does not count."
            ),
            expert="Shared budget, pack and skin zone exist only for form factor = laptop.",
        ),
    )


def _valid_build() -> Criterion:
    return Criterion(
        id="valid-build", label="Build has no validation errors",
        metric="validationErrors", op="<=", threshold=0, unit="errors",
        explain_id="thermal-budget", equation=EQ_BUDGET,
        why=L(
            standard=(
                "The rules panel's errors are builds that do not exist: a Pro "
                "Max Plus tower, or the discrete NPU in an Alienware. "
                "Warnings are allowed — the simulator demonstrates those — "
                "but a machine nobody can buy does not count."
            ),
            novice=(
                "The rules panel checks your build. A red error means the "
                "machine does not exist: for example the Pro Max Plus is only "
                "sold as a laptop, and the AI card (NPU) is only sold in the "
                "Pro Max Plus. Yellow warnings are fine, because the "
                "simulator will show you what they mean. Red errors are not."
            ),
            expert="Zero error-level findings (promax-desktop, NPU-on-Alienware).",
        ),
    )


# --- Lab 1: charge while you play -------------------------------------------

_CHARGE_START = Scenario(
    config=AW_LAPTOP, workload=AAA,
    environment=Environment(start_charge_pct=30), duration_s=1800,
)

CHARGE_WHILE_YOU_PLAY = Lab(
    id="charge-while-you-play",
    title="Charge while you play",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "The pack is at 30% and the session is half an hour. Build an "
                "Alienware laptop and a load that delivers at least 150 W of "
                "compute the whole time and still ends the run at 75% charge "
                "or better — without the battery discharging for a single "
                "second and without any throttling. Then deliver as much "
                "compute as you can."
            ),
            novice=(
                "You sit down to play for half an hour with the battery at "
                "30%. You want two things at once: a laptop that works hard "
                "the whole time (at least 150 watts reaching its chips), and "
                "a battery that is back up to 75% or more when you finish. "
                "The charger has to pay for both. The battery may never be "
                "drained, not even for one second, and the laptop may never "
                "slow itself down because of heat. Once that works, push the "
                "amount of work as high as you can."
            ),
            expert=(
                "30% → ≥75% in 1800 s, zero discharge ticks, zero clamp "
                "ticks, work ≥ 150 W; maximize work."
            ),
        ),
        constraints=[
            L(standard="Start at 30% charge or less; the run is 1800 seconds or shorter.",
              novice="The battery starts at 30% (or lower), and the run is half an hour (1800 seconds) or shorter. A longer run would give the charger more time, so it does not count.",
              expert="Start ≤ 30%, duration ≤ 1800 s."),
            L(standard="The battery never discharges — not while plugged in, and not by unplugging.",
              novice="The battery may never give power to the laptop during the run. That means you stay plugged in, and the charger must always be big enough for what the laptop is drawing, even during short bursts.",
              expert="Zero ticks with P_battery_discharge > 0."),
            L(standard="End the run at 75% charge or more.",
              novice="When the run ends, the battery gauge must read 75% or higher.",
              expert="Final SoC ≥ 75%."),
            L(standard="A laptop, no throttling or skin limiting, no validation errors, still powered on.",
              novice="It must be a laptop, it may never slow itself down because of heat, the rules panel may show no red errors, and it must still be on at the end.",
              expert="Laptop, zero clamp, zero errors, no power-off."),
        ],
        delivered_work=L(
            standard="At least 150 W of compute delivered to the CPU and GPU above idle, averaged over the run.",
            novice="On average, at least 150 watts must reach the processor and the graphics chip, not counting what they draw when resting. An idle laptop charges beautifully and does not count.",
            expert="workRateW ≥ 150.",
        ),
    ),
    criteria=[
        _work(150),
        Criterion(
            id="never-discharges", label="Battery never discharges",
            metric="dischargeSeconds", op="<=", threshold=0, unit="s",
            weight=2.0, explain_id="energy-identity", equation=EQ_SUPPLY,
            why=L(
                standard=(
                    "When system power exceeds the charger, the identity "
                    "balances with P_battery_discharge — plugged in or not. "
                    "The catch is the first 28 seconds: the PL2 burst and the "
                    "GPU's 1.15× boost put the peak well above the sustained "
                    "draw, so a charger that covers the steady load can still "
                    "be undersized for the spike."
                ),
                novice=(
                    "The power a laptop uses has to come from somewhere. If "
                    "the laptop wants more than the charger can give, the "
                    "battery quietly makes up the difference, even though "
                    "you are plugged in. Watch the first half minute: the "
                    "chips run in a short 'turbo' burst and draw much more "
                    "than they do later. A charger that is big enough for "
                    "the rest of the run can still be too small for that "
                    "burst."
                ),
                expert="P_system > P_charger ⇒ P_battery_discharge > 0. The PL2 + 1.15× TGP spike sets the peak.",
            ),
        ),
        Criterion(
            id="ends-charged", label="Ends at 75% charge or more",
            metric="endBatteryPct", op=">=", threshold=75, unit="%",
            weight=2.0, explain_id="energy-identity", equation=EQ_SUPPLY,
            why=L(
                standard=(
                    "P_charge is what is left of the charger after the system "
                    "has eaten: charger − P_system, capped at 90 W. Going "
                    "from 30% to 75% of a 90 Wh pack in half an hour needs "
                    "about 81 W of charge the whole time, so the charger has "
                    "to beat the system draw by roughly that much."
                ),
                novice=(
                    "The battery only gets what the laptop leaves over. If "
                    "the charger gives 240 watts and the laptop uses 230, "
                    "just 10 watts go into the battery. To go from 30% to "
                    "75% in half an hour, a 90 watt-hour battery needs about "
                    "81 watts going in the whole time (it cannot take more "
                    "than 90). So the charger must be about 81 watts bigger "
                    "than what the laptop is using."
                ),
                expert="P_charge = min(P_charger − P_system, 90 W); ≈81 W mean needed on 90 Wh.",
            ),
        ),
        Criterion(
            id="starts-low", label="Starts at 30% charge or less",
            metric="startChargePct", op="<=", threshold=30, unit="%",
            explain_id="battery-runtime", equation=EQ_RUNTIME,
            why=L(
                standard="The lab is the low pack. A run that starts full has nothing to charge and proves nothing about the surplus.",
                novice="The whole point is that the battery starts low. If you start with a full battery there is nothing to charge, so the run does not count.",
                expert="Initial SoC ≤ 30% is the premise.",
            ),
        ),
        Criterion(
            id="half-hour", label="Run is 1800 s or shorter",
            metric="durationS", op="<=", threshold=1800, unit="s",
            explain_id="energy-identity", equation=EQ_SUPPLY,
            why=L(
                standard="Any surplus at all reaches 75% eventually. Half an hour is what turns the surplus into a number the charger has to hit.",
                novice="Given enough time, even a tiny trickle fills a battery. The half-hour limit is what makes the size of the charger matter, so a longer run does not count.",
                expert="Energy target over fixed time ⇒ a power floor on P_charge.",
            ),
        ),
        _no_throttle(
            lesson=(
                "Here the usual culprit is the GPU's boost: for the first 28 "
                "seconds a 140 W GPU at 100% runs at 161 W, which carries it "
                "past 87 °C before the fans have caught up."
            ),
            lesson_novice=(
                "In this lab, watch the graphics chip in the first half "
                "minute: at exactly 100% load its turbo burst makes it draw "
                "about a seventh more than its rating, and that is enough to "
                "overheat it before the fans have sped up."
            ),
            lesson_expert="The 1.15× TGP boost at 100% GPU is the usual trigger.",
        ),
        _stays_up(),
        _laptop(),
        _valid_build(),
    ],
    objective=Objective(
        label="Delivered compute", metric="workRateW", direction="maximize",
        par=182, worst=150, unit="W", explain_id="energy-identity",
        equation=EQ_SUPPLY,
    ),
    hints=[
        L(standard="Watch the Charge and Battery discharge readouts. With the 240 W charger under the AAA load there is almost nothing left over for the pack — and for two seconds of the opening burst the pack is paying in.",
          novice="Look at the 'Charge' and 'Battery discharge' numbers in the instruments. The starting laptop has a 240 watt charger and uses almost all of it for the game, so very little is left to fill the battery. In the first seconds, during the turbo burst, the battery even has to help out.",
          expert="240 W − P_system ≈ 0 under AAA; the PL2 spike tips it negative."),
        L(standard="The supply identity is a budget: charger = system + charge. You need about 81 W of charge, so the charger has to be roughly 81 W bigger than the system draw. Turning the load down fails the work floor; the other term is the charger.",
          novice="Think of the charger as a wallet. Everything the laptop spends comes out of it, and only the change goes into the battery. You need about 81 watts of change. You could spend less by turning the game down, but then you fail the work goal. The other way is a bigger wallet: choose a bigger charger.",
          expert="P_charger ≥ P_system + ~81 W. The work floor forbids shrinking P_system."),
        L(standard="With the 330 W charger the power side closes; what is left is heat. A GPU at exactly 100% boosts to 1.15× TGP for 28 seconds and throttles. Try the 140 W GPU at 95% with the 65 W CPU tier.",
          novice="The 330 watt charger fixes the power problem. What remains is heat: at exactly 100% load the graphics chip bursts above its rating for the first half minute and overheats. Set the GPU dial to 95% instead of 100%, keep the 140 W graphics chip, and pick the 65 W processor for a little more work.",
          expert="330 W, 140 W TGP at 95% sidesteps the boost throttle; PL1 65 W adds work."),
    ],
    start=_CHARGE_START.model_dump(by_alias=True),
)


# --- Lab 2: an hour of tokens on a worn pack ---------------------------------

_FIELD_PACK = PROMAX_NPU.model_copy(update={"battery_health_pct": 80})
_UNPLUGGED = Environment(plugged_in=False)

_TOKENS_START = Scenario(
    config=_FIELD_PACK, workload=LLM_NPU, environment=_UNPLUGGED,
    duration_s=3600,
)

HOUR_OF_TOKENS = Lab(
    id="hour-of-tokens",
    title="An hour of tokens on a worn pack",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "A field engineer's Pro Max Plus has a two-year-old pack at "
                "80% health and no outlet for an hour. Run a local model "
                "unplugged for the full 3600 seconds at 27 tokens per second "
                "or better, and finish with at least 7% in the pack. Then "
                "get the most tokens out of every watt-hour the whole "
                "machine draws."
            ),
            novice=(
                "An engineer is out in the field with a Pro Max Plus laptop. "
                "Its battery is two years old and only holds 80% of what it "
                "used to, and there is no wall socket for the next hour. The "
                "laptop has to run an AI language model the whole hour, "
                "producing at least 27 tokens (word pieces) every second, "
                "and still have at least 7% battery left at the end. Once "
                "that works, make it as efficient as you can: the most "
                "tokens for every watt-hour of battery the whole laptop uses."
            ),
            expert=(
                "Unplugged 3600 s at 80% health: mean ≥ 27 tok/s, final SoC "
                "≥ 7%; maximize system tokens per Wh."
            ),
        ),
        constraints=[
            L(standard="Never on AC power: unplugged from the first second to the last.",
              novice="The laptop must run on its battery for the whole run. Do not plug it in at any point.",
              expert="Zero ticks with P_ac > 0."),
            L(standard="Battery health 80% or lower; the full 3600-second run.",
              novice="Leave the battery health slider at 80% (or lower), and keep the run at the full hour (3600 seconds) it starts with.",
              expert="Health ≤ 80%, duration ≥ 3600 s."),
            L(standard="Finish with at least 7% charge, still powered on.",
              novice="At the end of the hour the battery must show 7% or more, and the laptop must still be switched on.",
              expert="Final SoC ≥ 7%, no exhaustion power-off."),
            L(standard="Keep at least 32 GB of RAM; no validation errors.",
              novice="Keep at least 32 GB of memory, because the engineer still needs to use the laptop, and no red errors in the rules panel.",
              expert="RAM ≥ 32 GB, zero errors."),
        ],
        delivered_work=L(
            standard="At least 27 tokens per second, averaged over the whole hour — seconds after a power-off count as zero.",
            novice="On average over the whole hour, the model must produce at least 27 tokens every second. If the laptop dies early, the rest of the hour counts as zero.",
            expert="meanTokensPerS ≥ 27, dark ticks zero.",
        ),
    ),
    criteria=[
        Criterion(
            id="tokens", label="At least 27 tokens per second, averaged",
            metric="meanTokensPerS", op=">=", threshold=27, unit="tok/s",
            weight=2.0, guards_work=True, explain_id="tokens-per-joule",
            equation=EQ_TOKENS,
            why=L(
                standard=(
                    "Tokens per second, averaged over every second of the "
                    "run, dark seconds counted as zero. The NPU tops out at "
                    "30 tok/s, the GPU at 45 and the CPU at 6 — so the floor "
                    "rules the CPU out, and a machine that dies at minute 50 "
                    "loses a sixth of its average. Rates are illustrative."
                ),
                novice=(
                    "We add up every token the model produced and divide by "
                    "the full hour. The laptop can run the model on three "
                    "different chips: the AI chip (NPU) manages 30 tokens a "
                    "second, the graphics chip (GPU) 45, and the ordinary "
                    "processor (CPU) only 6. So the CPU is too slow to pass. "
                    "And if the battery runs out after 50 minutes, the last "
                    "10 minutes count as zero and pull the average down. "
                    "These speeds are illustrative, not measured."
                ),
                expert="Mean tok/s over all ticks, dark ticks zero; NPU 30, GPU 45, CPU 6 (illustrative).",
            ),
        ),
        Criterion(
            id="reserve", label="Ends with at least 7% charge",
            metric="endBatteryPct", op=">=", threshold=7, unit="%",
            weight=2.0, explain_id="battery-runtime", equation=EQ_RUNTIME,
            why=L(
                standard=(
                    "Runtime is usable watt-hours over system watts. At 80% "
                    "health a 96 Wh pack holds about 71 Wh after discharge "
                    "losses, so an hour with reserve means the whole machine "
                    "— not the NPU, the whole machine — has to average under "
                    "about 66 W."
                ),
                novice=(
                    "How long a battery lasts is simple division: the energy "
                    "in it, divided by the power the laptop uses. A worn "
                    "96 watt-hour battery at 80% health really only delivers "
                    "about 71 watt-hours. To last an hour and keep a little "
                    "in reserve, the whole laptop has to average under about "
                    "66 watts. Notice the word 'whole': every part that is "
                    "switched on counts, not just the chip doing the work."
                ),
                expert="Wh × 0.80 × 0.92 ≈ 71 Wh usable ⇒ mean P_system ≲ 66 W.",
            ),
        ),
        Criterion(
            id="on-battery", label="Never on AC power",
            metric="acSeconds", op="<=", threshold=0, unit="s",
            explain_id="energy-identity", equation=EQ_SUPPLY,
            why=L(
                standard="Unplugged, P_adapter is zero and the identity collapses to P_battery_discharge = P_system. That is the premise; any second on the adapter breaks it.",
                novice="There is no wall socket in this story. Without a charger, every watt the laptop uses comes out of the battery. If the laptop is plugged in for even one second, it is a different problem, so it does not count.",
                expert="P_adapter = 0 on every tick.",
            ),
        ),
        Criterion(
            id="worn-pack", label="Battery health 80% or lower",
            metric="batteryHealthPct", op="<=", threshold=80, unit="%",
            explain_id="battery-runtime", equation=EQ_RUNTIME,
            why=L(
                standard="Health multiplies capacity directly. A fresh pack has 20% more energy and hides every passenger this lab is about.",
                novice="Battery health is the share of its original energy the battery can still hold. A brand-new battery would have a fifth more energy and would let you pass without fixing anything, so the lab needs the worn one.",
                expert="Health scales Wh linearly; 80% is the premise.",
            ),
        ),
        Criterion(
            id="full-hour", label="Run lasts at least 3600 s",
            metric="durationS", op=">=", threshold=3600, unit="s",
            explain_id="battery-runtime", equation=EQ_RUNTIME,
            why=L(
                standard="Any pack survives a ten-minute run. The hour is what turns system watts into a pass or a power-off.",
                novice="Any battery can last ten minutes. The lab is about lasting the full hour, so a shorter run does not count.",
                expert="Fixed duration turns P_system into an energy bound.",
            ),
        ),
        Criterion(
            id="ram", label="At least 32 GB of RAM",
            metric="ramGb", op=">=", threshold=32, unit="GB",
            explain_id="battery-runtime", equation=EQ_RUNTIME,
            why=L(
                standard="Memory draws about 1.5 W per 16 GB whether or not the model touches it — a real lever, and worth pulling down to 32 GB. Below that the machine stops being the engineer's workstation.",
                novice="Memory uses a little power all the time, about 1.5 watts for every 16 GB, even when the AI model is not using it. Trimming it helps the battery. But the engineer still needs a usable laptop, so at least 32 GB must stay.",
                expert="≈1.5 W per 16 GB of always-on base load; floor 32 GB.",
            ),
        ),
        _stays_up(),
        _valid_build(),
    ],
    objective=Objective(
        label="System tokens per watt-hour", metric="tokensPerWh",
        direction="maximize", par=1665, worst=1580, unit="tok/Wh",
        explain_id="tokens-per-joule", equation=EQ_TOKENS,
    ),
    hints=[
        L(standard="The start machine dies before the hour is out. Look at the power bars: the NPU is 40 W, but the system is nearly 80 W. The Explain entry divides tokens by P_engine; the battery divides by P_system.",
          novice="The starting laptop runs out of battery before the hour ends. Look at the power bars: the AI chip (NPU) uses 40 watts, but the whole laptop uses nearly 80. The 'tokens per joule' number only looks at the AI chip. The battery pays for everything that is switched on.",
          expert="P_engine = 40 W, P_system ≈ 79 W. The pack sees the second one."),
        L(standard="Find the passengers. A 115 W GPU idles at about 7 W doing nothing, 64 GB of RAM costs 3 W more than 32 GB, and the workload preset's 10% CPU dial is another 3 W.",
          novice="Some parts use power without helping. The big graphics chip draws about 7 watts just sitting there. 64 GB of memory uses 3 watts more than 32 GB. And the workload button sets the ordinary processor to 10%, which costs another 3 watts. Each one is a passenger the battery is carrying.",
          expert="GPU idle 0.06 × TGP, RAM 1.5 W/16 GB, CPU at 10% — ≈13 W of passengers."),
        L(standard="Once the passengers are gone, resist turning the NPU down to save the pack. Base power is a fixed cost per second, so the fastest engine setting spreads it over the most tokens: 100% NPU beats 90% on tokens per watt-hour.",
          novice="After removing the passengers you may want to turn the NPU dial down a bit to save battery. Do not. The rest of the laptop uses the same power every second no matter how fast the tokens come, so going full speed gives you more tokens for that fixed cost. Set GPU to none, memory to 32 GB, the CPU dial to 0, pick the 45 W processor and the 97 Wh battery, and leave the NPU at 100%.",
          expert="Fixed base ⇒ system tok/Wh rises with NPU load. TGP 0, 32 GB, CPU 0%, PL1 45 W, 97 Wh, NPU 100%."),
    ],
    start=_TOKENS_START.model_dump(by_alias=True),
)


# --- Lab 3: warm lap, no clamp -------------------------------------------------

_LAP = Environment(on_lap=True, start_charge_pct=50)

_LAP_START = Scenario(
    config=AW_LAPTOP, workload=AAA, environment=_LAP, duration_s=1200,
)

WARM_LAP = Lab(
    id="warm-lap-no-clamp",
    title="Warm lap, no clamp",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "Twenty minutes of gaming on the sofa: laptop on your lap the "
                "whole time, pack at 50%, room at 22 °C or warmer. Deliver at "
                "least 97 W of compute without the skin governor or any "
                "throttle engaging for a single second, never discharge the "
                "battery, and end at 60% charge or better. Then deliver as "
                "much compute as the lap allows."
            ),
            novice=(
                "You are playing on the sofa for twenty minutes with the "
                "laptop on your lap, the battery at half, and the room at a "
                "normal 22 °C or warmer. A lap blocks the air holes on the "
                "bottom, so the case heats up fast, and the laptop will cut "
                "its own power if the case goes above 46 °C. Your job: get at "
                "least 97 watts of real work out of it without that safety "
                "cut ever happening, without ever draining the battery, and "
                "with the battery at 60% or more when you finish. Then "
                "squeeze out as much work as the lap allows."
            ),
            expert=(
                "On-lap 1200 s, ambient ≥ 22 °C, SoC 50% → ≥60%, zero "
                "discharge, zero clamp, work ≥ 97 W; maximize work."
            ),
        ),
        constraints=[
            L(standard="On the lap for the whole run; ambient never below 22 °C; the full 1200 seconds.",
              novice="The laptop stays on your lap from start to finish (do not press 'Back on desk'), the Ambient slider stays at 22 °C or higher, and the run is the full 1200 seconds it starts with.",
              expert="Zero off-lap ticks, min ambient ≥ 22 °C, duration ≥ 1200 s."),
            L(standard="No skin limiting and no throttling at any point.",
              novice="The laptop may never slow itself down, either because the case got too hot to touch or because a chip overheated.",
              expert="Zero clamp ticks (skin, CPU, GPU)."),
            L(standard="Start at 50% charge or less, never discharge, end at 60% or more.",
              novice="The battery starts at 50% (or lower), may never be drained during the run, and must read 60% or more at the end. So you stay plugged in, and the battery has to be charging.",
              expert="SoC₀ ≤ 50%, zero discharge ticks, final SoC ≥ 60%."),
            L(standard="A laptop with at least 32 GB of RAM, no validation errors, still powered on.",
              novice="It must be a laptop with at least 32 GB of memory, the rules panel may show no red errors, and it must still be on at the end.",
              expert="Laptop, RAM ≥ 32 GB, zero errors, no power-off."),
        ],
        delivered_work=L(
            standard="At least 97 W of compute delivered to the CPU and GPU above idle, averaged over the 1200-second run.",
            novice="On average over the twenty minutes, at least 97 watts must reach the processor and the graphics chip, not counting what they draw when resting.",
            expert="workRateW ≥ 97 over 1200 s.",
        ),
    ),
    criteria=[
        _work(97),
        _no_throttle(
            lesson=(
                "On a lap the skin governor arrives first: the blocked intake "
                "roughly doubles the skin's thermal resistance, so about "
                "130 W of total internal heat is all a 22 °C room allows."
            ),
            lesson_novice=(
                "On a lap the hot case is what trips first. With the air "
                "holes blocked, the case warms up about twice as much for "
                "the same heat, so in a 22 °C room the whole laptop can only "
                "turn about 130 watts into heat before the case passes 46 °C."
            ),
            lesson_expert="On-lap R_skin/0.55 ⇒ Q_internal ≲ 132 W at 22 °C; skin binds before silicon.",
        ),
        Criterion(
            id="on-lap", label="On the lap for the whole run",
            metric="offLapSeconds", op="<=", threshold=0, unit="s",
            explain_id="skin-cap", equation=EQ_SKIN,
            why=L(
                standard="A desk restores the intake and with it the skin's thermal resistance. The lap is the term you may not change.",
                novice="Putting the laptop back on a desk opens the air holes again and the case cools down. That would be the easy answer, so the lab does not allow it: the laptop stays on the lap every second.",
                expert="R_skin stays at its on-lap value on every tick.",
            ),
        ),
        Criterion(
            id="room", label="Ambient never below 22 °C",
            metric="minAmbientC", op=">=", threshold=22, unit="°C",
            explain_id="skin-cap", equation=EQ_SKIN,
            why=L(
                standard="Skin temperature is ambient plus a rise. Every degree taken off the room is a degree of headroom under the 46 °C cap, so the room is fixed.",
                novice="The case is as warm as the room plus whatever the laptop adds. A colder room would give you free headroom under the 46 °C limit, so the Ambient slider has to stay at 22 °C or higher for the whole run.",
                expert="T_skin = T_amb + rise; T_amb ≥ 22 °C is fixed.",
            ),
        ),
        Criterion(
            id="never-discharges", label="Battery never discharges",
            metric="dischargeSeconds", op="<=", threshold=0, unit="s",
            weight=2.0, explain_id="energy-identity", equation=EQ_SUPPLY,
            why=L(
                standard=(
                    "A charger smaller than the system draw stops the charging "
                    "— and its heat — by making the pack pay instead. That "
                    "trade is closed: the charger must cover the system on "
                    "every tick, the opening PL2 burst included."
                ),
                novice=(
                    "If the charger is smaller than what the laptop uses, the "
                    "battery makes up the difference and stops charging. That "
                    "would remove the charging heat, but it drains the "
                    "battery, so it is not allowed. The charger has to cover "
                    "everything the laptop draws at every moment, including "
                    "the turbo burst in the first half minute."
                ),
                expert="P_charger ≥ P_system on every tick, PL2 spike included.",
            ),
        ),
        Criterion(
            id="ends-charged", label="Ends at 60% charge or more",
            metric="endBatteryPct", op=">=", threshold=60, unit="%",
            weight=2.0, explain_id="energy-identity", equation=EQ_SUPPLY,
            why=L(
                standard=(
                    "P_charge is the charger's surplus over the system, and a "
                    "tenth of it becomes heat inside the chassis. Ten points "
                    "on a 90 Wh pack in twenty minutes needs about 27 W of "
                    "charge; the 240 W charger pushes the full 90 W, and those "
                    "extra 6 W of heat come straight out of the compute the "
                    "skin cap allows."
                ),
                novice=(
                    "Whatever the charger has left over after the laptop has "
                    "taken its share goes into the battery, and about a tenth "
                    "of that turns into heat inside the case. You only need "
                    "about 27 watts of charging to gain ten points in twenty "
                    "minutes. A big 240 watt charger pushes the maximum "
                    "90 watts instead, which makes about 9 watts of heat "
                    "rather than 3. On a lap, where heat is the limit, those "
                    "extra watts of heat are watts of work you lose."
                ),
                expert="Q_charge = 0.1 × min(P_charger − P_system, 90 W) counts against the skin cap; ≈27 W suffices.",
            ),
        ),
        Criterion(
            id="starts-half", label="Starts at 50% charge or less",
            metric="startChargePct", op="<=", threshold=50, unit="%",
            explain_id="energy-identity", equation=EQ_SUPPLY,
            why=L(
                standard="A full pack takes no charge and makes no charge heat. Starting at half is what puts P_charge into the skin's heat budget.",
                novice="A full battery does not charge, so it makes no charging heat, and the hard part of this lab disappears. The battery has to start at 50% or lower.",
                expert="SoC₀ ≤ 50% keeps P_charge > 0 for the run.",
            ),
        ),
        Criterion(
            id="full-run", label="Run lasts at least 1200 s",
            metric="durationS", op=">=", threshold=1200, unit="s",
            explain_id="skin-cap", equation=EQ_SKIN,
            why=L(
                standard="The skin zone has a time constant of about two minutes; a short run ends before the chassis has reached the temperature it is graded on.",
                novice="The case warms up slowly, over several minutes. A short run would end before it got hot, so the lab needs the full twenty minutes.",
                expert="τ_skin ≈ 120 s; 1200 s is ten time constants.",
            ),
        ),
        Criterion(
            id="ram", label="At least 32 GB of RAM",
            metric="ramGb", op=">=", threshold=32, unit="GB",
            explain_id="skin-cap", equation=EQ_SKIN,
            why=L(
                standard="Every always-on watt is part of Q_internal, so pulling memory buys skin headroom — true, and not the lesson. The 32 GB stays.",
                novice="Memory makes a little heat all the time, so taking some out would leave a bit more room under the 46 °C limit. That is true, but it is not what this lab is about, and a gaming laptop with too little memory is not the laptop you wanted. Keep at least 32 GB.",
                expert="Base-load de-population is out of scope; RAM ≥ 32 GB.",
            ),
        ),
        _stays_up(),
        _laptop(),
        _valid_build(),
    ],
    objective=Objective(
        label="Delivered compute", metric="workRateW", direction="maximize",
        par=100, worst=97, unit="W", explain_id="skin-cap", equation=EQ_SKIN,
    ),
    hints=[
        L(standard="Watch the skin temperature and the power-limit state. Under the AAA load the skin passes 46 °C in a few minutes and the governor clamps for the rest of the run. Quiet mode avoids the clamp — by cutting the budget so far that the work floor fails.",
          novice="Watch the 'Skin' temperature and the power-limit label. With the starting game load, the case passes 46 °C after a few minutes and the laptop cuts its power for the rest of the run. Quiet mode stops that from happening, but only because it allows so little power that you fail the work goal instead.",
          expert="AAA on-lap is skin-limited by ~t+300 s; quiet's 0.62× budget fails the work floor."),
        L(standard="The skin cap is a ceiling on total internal heat — about 130 W on a lap at 22 °C — and it does not care which part made it. Turn the CPU and GPU dials down together until the skin settles just under 46 °C.",
          novice="The case temperature depends on all the heat inside the laptop added together, about 130 watts at most on a lap in a 22 °C room. It does not matter which chip makes the heat. Lower the CPU and GPU dials, a little at a time, until the skin temperature levels off just below 46 °C.",
          expert="Q_internal ≲ 132 W on-lap at 22 °C, source-agnostic. Tune the dials to sit under the cap."),
        L(standard="Now look for heat that is not compute. At 50% the pack takes all the surplus a 240 W charger has — 90 W of charge, 9 W of heat. You only need about 27 W of charge to reach 60%. A 165 W charger covers the system, charges enough, and hands about 6 W of the skin's budget back to the chips.",
          novice="Now find heat that does no work. The battery is charging, and a tenth of the charging power becomes heat. A 240 watt charger pours the maximum 90 watts into the battery, which is 9 watts of heat. You only need about 27 watts of charging to reach 60%. Pick the 165 watt charger: it still runs the laptop and charges the battery enough, but makes much less heat, and that freed-up heat allowance can go to the chips. With the 80 W graphics chip and the 65 W processor, try CPU 65% and GPU 70%.",
          expert="Right-size the charger: 165 W ⇒ P_charge ≈ 30 W, Q_charge ≈ 3 W. 80 W TGP + PL1 65 W at 65/70%."),
    ],
    start=_LAP_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [CHARGE_WHILE_YOU_PLAY, HOUR_OF_TOKENS, WARM_LAP]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Reference solutions and gaming attempts (server-side only) --------------

_LOW_PACK = Environment(start_charge_pct=30)
_IDLE = Workload()

_CHARGE_REF_CFG = AW_LAPTOP.model_copy(update={"cpu_pl1_w": 65, "charger_w": 330})
_TOKENS_REF_CFG = _FIELD_PACK.model_copy(update={
    "cpu_pl1_w": 45, "gpu_tgp_w": 0, "ram_gb": 32, "battery_wh": 97,
})
_LAP_REF_CFG = AW_LAPTOP.model_copy(update={
    "cpu_pl1_w": 65, "gpu_tgp_w": 80, "charger_w": 165,
})
_NPU_FULL = Workload(npu_pct=100, inference=True)

REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    "charge-while-you-play": Scenario(
        config=_CHARGE_REF_CFG, workload=Workload(cpu_pct=70, gpu_pct=95),
        environment=_LOW_PACK, duration_s=1800,
    ),
    "hour-of-tokens": Scenario(
        config=_TOKENS_REF_CFG, workload=_NPU_FULL, environment=_UNPLUGGED,
        duration_s=3600,
    ),
    "warm-lap-no-clamp": Scenario(
        config=_LAP_REF_CFG, workload=Workload(cpu_pct=65, gpu_pct=70),
        environment=_LAP, duration_s=1200,
    ),
}

GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "charge-while-you-play": {
        "zero load": Scenario(
            config=_CHARGE_REF_CFG, workload=_IDLE, environment=_LOW_PACK,
            duration_s=1800),
        "start with a full pack": Scenario(
            config=_CHARGE_REF_CFG, workload=Workload(cpu_pct=70, gpu_pct=95),
            environment=Environment(start_charge_pct=100), duration_s=1800),
        "long run to let the trickle finish": Scenario(
            config=AW_LAPTOP, workload=Workload(cpu_pct=70, gpu_pct=95),
            environment=_LOW_PACK, duration_s=7200),
        "desktop tower": Scenario(
            config=DeviceConfig(form_factor="desktop", cpu_pl1_w=125,
                                gpu_tgp_w=300, psu_capacity_w=1000),
            workload=AAA, environment=_LOW_PACK, duration_s=1800),
        "biggest everything at full load": Scenario(
            config=AW_LAPTOP.model_copy(update={
                "cpu_pl1_w": 65, "gpu_tgp_w": 175, "charger_w": 330}),
            workload=Workload(cpu_pct=100, gpu_pct=100),
            environment=_LOW_PACK, duration_s=1800),
        "big charger, exactly 100% GPU": Scenario(
            config=_CHARGE_REF_CFG, workload=Workload(cpu_pct=70, gpu_pct=100),
            environment=_LOW_PACK, duration_s=1800),
        "idle first, load later": Scenario(
            config=_CHARGE_REF_CFG, workload=_IDLE, environment=_LOW_PACK,
            events=[SimEvent(at_s=1500, action="set-workload",
                             workload=Workload(cpu_pct=70, gpu_pct=95))],
            duration_s=1800),
    },
    "hour-of-tokens": {
        "zero load": Scenario(
            config=_TOKENS_REF_CFG, workload=_IDLE, environment=_UNPLUGGED,
            duration_s=3600),
        "plug it in": Scenario(
            config=_FIELD_PACK, workload=LLM_NPU, environment=Environment(),
            duration_s=3600),
        "plug in after the first second": Scenario(
            config=_FIELD_PACK, workload=LLM_NPU, environment=_UNPLUGGED,
            events=[SimEvent(at_s=1, action="plug-in")], duration_s=3600),
        "fresh battery": Scenario(
            config=PROMAX_NPU.model_copy(update={"gpu_tgp_w": 0}),
            workload=_NPU_FULL, environment=_UNPLUGGED, duration_s=3600),
        "short run": Scenario(
            config=_FIELD_PACK, workload=LLM_NPU, environment=_UNPLUGGED,
            duration_s=600),
        "faster engine: the GPU": Scenario(
            config=_FIELD_PACK.model_copy(update={"npu": False, "gpu_tgp_w": 80,
                                                  "ram_gb": 32}),
            workload=Workload(gpu_pct=100, inference=True),
            environment=_UNPLUGGED, duration_s=3600),
        "strip the memory": Scenario(
            config=_TOKENS_REF_CFG.model_copy(update={"ram_gb": 16}),
            workload=_NPU_FULL, environment=_UNPLUGGED, duration_s=3600),
        "sip power at half speed": Scenario(
            config=_TOKENS_REF_CFG, workload=Workload(npu_pct=50, inference=True),
            environment=_UNPLUGGED, duration_s=3600),
    },
    "warm-lap-no-clamp": {
        "zero load": Scenario(
            config=_LAP_REF_CFG, workload=_IDLE, environment=_LAP,
            duration_s=1200),
        "cool the room": Scenario(
            config=AW_LAPTOP, workload=AAA,
            environment=Environment(on_lap=True, start_charge_pct=50,
                                    ambient_c=10),
            duration_s=1200),
        "back on the desk": Scenario(
            config=AW_LAPTOP, workload=Workload(cpu_pct=70, gpu_pct=95),
            environment=_LAP,
            events=[SimEvent(at_s=1, action="set-on-lap", value=0)],
            duration_s=1200),
        "quiet mode": Scenario(
            config=AW_LAPTOP, workload=AAA,
            environment=Environment(on_lap=True, start_charge_pct=50,
                                    perf_mode="quiet"),
            duration_s=1200),
        "start with a full pack": Scenario(
            config=AW_LAPTOP, workload=Workload(cpu_pct=50, gpu_pct=65),
            environment=Environment(on_lap=True, start_charge_pct=100),
            duration_s=1200),
        "undersized charger so nothing charges": Scenario(
            config=_LAP_REF_CFG.model_copy(update={"charger_w": 130}),
            workload=Workload(cpu_pct=70, gpu_pct=75), environment=_LAP,
            duration_s=1200),
        "short run": Scenario(
            config=AW_LAPTOP, workload=AAA, environment=_LAP, duration_s=60),
        "desktop tower": Scenario(
            config=DeviceConfig(form_factor="desktop", cpu_pl1_w=125,
                                gpu_tgp_w=300, psu_capacity_w=1000),
            workload=AAA, environment=_LAP, duration_s=1200),
        "long run at low load": Scenario(
            config=AW_LAPTOP, workload=Workload(cpu_pct=20, gpu_pct=20),
            environment=_LAP, duration_s=7200),
        "big charger, best possible tuning": Scenario(
            config=_LAP_REF_CFG.model_copy(update={
                "charger_w": 240, "battery_wh": 68}),
            workload=Workload(cpu_pct=86, gpu_pct=58), environment=_LAP,
            duration_s=1200),
        "big charger, strip the memory": Scenario(
            config=_LAP_REF_CFG.model_copy(update={
                "charger_w": 240, "battery_wh": 68, "ram_gb": 16}),
            workload=Workload(cpu_pct=59, gpu_pct=74), environment=_LAP,
            duration_s=1200),
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
