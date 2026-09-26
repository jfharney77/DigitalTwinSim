"""Graded labs for the Alienware power-path twin (``docs/LAB_PATTERN.md``).

A guided tour sets the scenario and tells you what to watch. A lab states a
goal and leaves the five ordinary controls to you — machine, adapter, starting
charge, thermal mode, workload. The engine runs the scenario and
``grade_scenario`` scores the trace.

Pure module, same rule as ``engine.py``: no FastAPI, no IO, no clock, no
randomness (AST-checked in ``tests/test_labs.py``). ``main.py`` is the only
caller that touches HTTP, so the static-hosted build grades in the browser by
running this same file.

What is this app's own; everything else is ``twinkit.labs``:

* ``EXPLAINS`` — the power path's equations, one entry each. This twin had no
  Explain mode before the labs; the entries exist so every graded line can
  point at the physics that passed or failed it (``GET /api/explain``).
* ``measure()`` — one run as named numbers. The un-gameable one is ``workW``:
  CPU watts above the idle floor plus GPU watts, averaged over the load and
  steady steps. The trace always has the same three such steps, so there is
  no run length to stretch, and an idle, throttled or unrecognized-adapter
  machine earns next to nothing. It is an illustrative proxy for useful
  silicon work, not a benchmark.
* ``LABS`` — three labs of rising difficulty.
* ``REFERENCE_SOLUTIONS`` / ``GAMING_ATTEMPTS`` — a scenario that passes each
  lab and the cheap tricks that must not. Server-side only.
"""

from __future__ import annotations

from twinkit.labs import Criterion, Lab, LabGoal, LabResult, Objective, grade
from twinkit.models import CamelModel

from .catalog import PROFILES
from .engine import CPU_IDLE_FLOOR_W, HYBRID_FLOOR_PCT, simulate
from .leveling import L
from .models import AdapterOption, LaptopProfile, PowerState, Scenario

#: Reported as the hybrid runtime when the pack is not being drawn on at all.
NO_DRAIN_MIN = 999.0


# --- Explain entries --------------------------------------------------------

class Explain(CamelModel):
    """One equation of the power path, with a leveled reading of it."""

    id: str
    title: str
    equation: str
    body: str


EQ_SUPPLY = "P_ac + P_battery = P_system + P_charge"
EQ_CAP = "P_silicon = cap(mode) × (f_cpu × P_cpu,max + f_gpu × TGP)"
EQ_HYBRID = "P_battery = max(0, P_system − P_adapter), while the pack is above 20%"
EQ_CHARGE = "P_charge = min(P_cc, P_adapter − P_system); 0 once the pack reaches 94%"
EQ_RUNTIME = "t = (pack% − 20%) × Wh ÷ P_battery"
EQ_FAN = "fan% = base(mode) + 55 × P_system ÷ P_full; Full Speed pins 100%"
EQ_PSID = "PSID unreadable → P_cpu ≤ 25 W, P_gpu ≤ 10 W, P_charge = 0"

EXPLAINS: list[Explain] = [
    Explain(
        id="supply-identity", title="Where every watt goes", equation=EQ_SUPPLY,
        body=L(
            standard=(
                "At every step the watts coming in equal the watts going out: "
                "adapter power plus any battery discharge equals what the "
                "system burns plus what goes into the pack. The pack is never "
                "charged and discharged at once, so one of P_battery and "
                "P_charge is always zero."
            ),
            novice=(
                "Power cannot appear or vanish. Whatever the charger brick "
                "supplies, plus whatever the battery gives up, is exactly what "
                "the laptop uses plus whatever is being stored in the battery. "
                "The battery is either filling or emptying, never both, so in "
                "this sum one of the two battery numbers is always zero. Every "
                "readout on the page obeys this at every step."
            ),
            expert="Energy balance per step; charge and discharge mutually exclusive.",
        ),
    ),
    Explain(
        id="thermal-cap", title="The thermal mode is the power dial", equation=EQ_CAP,
        body=L(
            standard=(
                "The AWCC thermal mode caps how much of the silicon's maximum "
                "may be sustained: 45% in Quiet, 65% in Balanced, 85% in "
                "Performance, 100% in Full Speed. The workload then asks for a "
                "fraction of that cap — gaming pegs the GPU and uses 60% of "
                "the CPU cap, full load pegs both. The fractions are "
                "illustrative."
            ),
            novice=(
                "The thermal mode in Alienware Command Center (AWCC) is really "
                "a power limit. Quiet lets the processor and graphics chip use "
                "45% of their top power, Balanced 65%, Performance 85% and "
                "Full Speed all of it. The workload decides how much of that "
                "allowance is asked for: a game uses all of the graphics "
                "allowance and 60% of the processor's, and a full-load test "
                "uses all of both. So a heavier workload in a lower mode can "
                "draw the same power as a lighter one in a higher mode. These "
                "percentages are illustrative, not measured."
            ),
            expert="cap = 0.45/0.65/0.85/1.0; gaming f = (0.6, 1.0), full load (1, 1). Illustrative.",
        ),
    ),
    Explain(
        id="hybrid-power", title="Hybrid power", equation=EQ_HYBRID,
        body=L(
            standard=(
                "When the system asks for more than the adapter is rated for, "
                "the charger IC lets the battery make up the difference. The "
                "laptop keeps its clocks, charging stops, and the pack drains "
                "while plugged in. Below 20% the EC (embedded controller) "
                "stops doing this and throttles the silicon to fit the adapter."
            ),
            novice=(
                "A charger brick has a fixed size, such as 280 watts. If the "
                "laptop wants more than that, it does not slow down: it takes "
                "the missing watts from its own battery. That is hybrid power. "
                "The game runs at full speed, but the battery stops charging "
                "and slowly empties even though the laptop is plugged in. "
                "Once the battery falls to 20% the laptop stops borrowing and "
                "slows itself down instead, to protect the battery."
            ),
            expert="Supplement = demand − adapter rating; disabled at ≤20% pack, then the EC scales CPU/GPU.",
        ),
    ),
    Explain(
        id="charge-headroom", title="Charging gets the leftovers", equation=EQ_CHARGE,
        body=L(
            standard=(
                "While the system runs, the pack is charged only from the "
                "headroom: the adapter's rating minus what the system is "
                "drawing, up to the 90 W constant-current rate. No headroom, "
                "no charge. Above 94% the charger holds off entirely, so the "
                "pack does not micro-cycle."
            ),
            novice=(
                "The laptop feeds itself first and the battery second. The "
                "battery can take up to 90 watts, but it only gets what the "
                "charger brick has left over after the processor, graphics "
                "chip and screen have taken theirs. If the game uses nearly "
                "the whole brick, the battery charges slowly or not at all. "
                "And once the battery is at 94% or more the charger stops on "
                "purpose, because topping up a nearly full lithium battery "
                "again and again wears it out."
            ),
            expert="Top-up = min(90 W CC, rating − system); 94–100% hold band charges nothing.",
        ),
    ),
    Explain(
        id="hybrid-runtime", title="How long hybrid power lasts", equation=EQ_RUNTIME,
        body=L(
            standard=(
                "Hybrid power ends when the pack reaches 20%. The time until "
                "then is the usable energy — the charge above 20%, times the "
                "pack's watt-hours — divided by the watts the battery is "
                "supplying. Halving the supplement doubles the time; so does "
                "doubling the charge above the floor."
            ),
            novice=(
                "While the battery is helping the charger, it is emptying. "
                "The help stops at 20%. To find how long you have, take the "
                "charge above 20%, turn it into energy using the battery's "
                "size in watt-hours (Wh), and divide by how many watts the "
                "battery is giving. A 96 Wh battery at 90% has about 67 Wh to "
                "spare; at 50 watts of help that is about 80 minutes. Ask for "
                "less help, or start with more charge, and it lasts longer."
            ),
            expert="Usable Wh above the 20% hybrid floor ÷ supplement W.",
        ),
    ),
    Explain(
        id="fan-duty", title="What sets the fan speed", equation=EQ_FAN,
        body=L(
            standard=(
                "Each thermal mode has a base fan duty — 22% Quiet, 35% "
                "Balanced, 60% Performance — and the fans add up to 55 points "
                "on top in proportion to system power. Full Speed ignores the "
                "load and pins the fans at 100%. The mode's base matters more "
                "than the watts. Duties are illustrative."
            ),
            novice=(
                "Fan noise comes from two things. First, the thermal mode "
                "sets a starting fan speed: 22% in Quiet, 35% in Balanced, "
                "60% in Performance. Second, the fans speed up as the laptop "
                "draws more power, by up to 55 more points. Full Speed is the "
                "exception: the fans run flat out whatever the laptop is "
                "doing. Because the starting speed differs so much between "
                "modes, picking a lower mode quiets the laptop more than "
                "picking a lighter workload does. The numbers are illustrative."
            ),
            expert="Duty = mode base + 55 × P_sys/P_full; Full Speed = 100%. Illustrative.",
        ),
    ),
    Explain(
        id="psid-handshake", title="An adapter the laptop cannot identify", equation=EQ_PSID,
        body=L(
            standard=(
                "A Dell barrel adapter reports its wattage over the PSID "
                "center pin. If the EC cannot read it, the BIOS shows the "
                "adapter as Unknown: the EC will not budget watts it cannot "
                "verify, so it refuses to charge and caps the CPU and GPU, "
                "whatever the label on the brick says."
            ),
            novice=(
                "A Dell charger tells the laptop how big it is through the "
                "thin pin in the middle of the plug. This is called PSID "
                "(power supply identification). If the pin is bent or the "
                "charger is a copy, the laptop cannot read the answer and "
                "calls the charger 'Unknown'. It then plays safe: it will not "
                "charge the battery at all and it holds the processor and "
                "graphics chip to a small fraction of their power. The watts "
                "printed on the charger no longer matter."
            ),
            expert="PSID read failure → 'Unknown' adapter: no charge, hard CPU/GPU caps.",
        ),
    ),
]
EXPLAINS_BY_ID: dict[str, Explain] = {e.id: e for e in EXPLAINS}


# --- Measurement ------------------------------------------------------------

def resolve(scenario: Scenario) -> tuple[LaptopProfile, AdapterOption]:
    """The catalog entries a scenario names. ``ValueError`` when it names none."""
    profile = PROFILES.get(scenario.profile_id)
    if profile is None:
        raise ValueError(f"unknown profileId {scenario.profile_id!r}")
    adapter = next((a for a in profile.adapters if a.id == scenario.adapter_id), None)
    if adapter is None:
        raise ValueError(
            f"unknown adapterId {scenario.adapter_id!r} for profile {profile.id!r}"
        )
    return profile, adapter


def measure(
    profile: LaptopProfile,
    adapter: AdapterOption,
    scenario: Scenario,
    trace: list[PowerState],
) -> dict[str, float]:
    """One run as named numbers. Keys are the wire names criteria refer to."""
    run = [s for s in trace if s.phase in ("load", "steady")]
    last = trace[-1]
    work = sum(max(0.0, s.cpu_w - CPU_IDLE_FLOOR_W) + s.gpu_w for s in run)
    if last.battery_w > 0:
        usable_wh = max(0.0, last.battery_pct - HYBRID_FLOOR_PCT) / 100.0 * profile.battery.wh
        runtime = min(NO_DRAIN_MIN, usable_wh / last.battery_w * 60.0)
    else:
        runtime = NO_DRAIN_MIN
    return {
        "workW": round(work / max(len(run), 1), 1),
        "adapterW": float(adapter.watts),
        "adapterRecognized": 1.0 if adapter.recognized else 0.0,
        "hybridPeakW": round(max((s.battery_w for s in run), default=0.0), 1),
        "steadyChargeW": float(last.charge_w),
        "steadySystemW": float(last.system_w),
        "headroomW": round(adapter.watts - last.system_w, 1),
        "peakFanPct": round(max((s.fan_pct for s in run), default=0.0), 1),
        "startBatteryPct": float(scenario.start_battery_pct),
        "endBatteryPct": float(last.battery_pct),
        "packGainPct": round(last.battery_pct - scenario.start_battery_pct, 1),
        "hybridRuntimeMin": round(runtime, 1),
    }


# --- Criteria shared between labs -------------------------------------------

def _work(floor_w: int) -> Criterion:
    return Criterion(
        id="work", label=f"Silicon work at least {floor_w} W",
        metric="workW", op=">=", threshold=floor_w, unit="W",
        weight=2.0, guards_work=True, explain_id="thermal-cap", equation=EQ_CAP,
        why=L(
            standard=(
                f"Work is CPU watts above the 6 W idle floor plus GPU watts, "
                f"averaged over the load and steady steps; {floor_w} W is the "
                "floor. An idle laptop, a low thermal mode or an unrecognized "
                "adapter delivers less, so turning the load down is not a way "
                "through. The proxy is illustrative, not a benchmark."
            ),
            novice=(
                f"The laptop has to do real work: at least {floor_w} watts of "
                "it. We count work as the power the processor and the "
                "graphics chip actually get to use once the laptop is under "
                "load, leaving out the 6 watts the processor uses doing "
                "nothing. A laptop left idle scores zero, a quiet thermal "
                "mode scores low, and a charger the laptop cannot identify "
                "scores almost nothing, because the laptop then holds its "
                "chips back. So you cannot win by asking for less. This is a "
                "simple stand-in for useful computing, not a real benchmark."
            ),
            expert=(
                f"Mean of (P_cpu − 6 W idle floor) + P_gpu over load and steady "
                f"steps; floor {floor_w} W. Illustrative proxy."
            ),
        ),
    )


def _recognized() -> Criterion:
    return Criterion(
        id="recognized", label="The laptop identifies the adapter",
        metric="adapterRecognized", op=">=", threshold=1, unit="",
        explain_id="psid-handshake", equation=EQ_PSID,
        why=L(
            standard=(
                "An adapter whose PSID cannot be read is budgeted as Unknown: "
                "no charging and hard CPU/GPU caps. It never goes hybrid, but "
                "only because it never delivers the watts that would need it."
            ),
            novice=(
                "The charger has to be one the laptop can identify. With an "
                "'Unknown' charger the laptop refuses to charge the battery "
                "and holds its chips to a trickle of power. That does stop "
                "the battery from draining, but only because the laptop is "
                "barely doing anything, so it is not a real answer."
            ),
            expert="PSID read OK; the Unknown path caps silicon and charges nothing.",
        ),
    )


def _no_hybrid() -> Criterion:
    return Criterion(
        id="no-hybrid", label="The battery never supplements the adapter",
        metric="hybridPeakW", op="<=", threshold=0, unit="W", weight=2.0,
        explain_id="hybrid-power", equation=EQ_HYBRID,
        why=L(
            standard=(
                "Any step where system power exceeds the adapter's rating is "
                "paid for from the pack. It keeps the clocks up, but the pack "
                "drains while plugged in and charging stops — the state this "
                "lab asks you to avoid."
            ),
            novice=(
                "If the laptop ever wants more power than the charger can "
                "give, it takes the rest from the battery. The game keeps "
                "running at full speed, but the battery empties even though "
                "you are plugged in, and it stops charging. This lab asks you "
                "to stay out of that state, so the highest battery "
                "contribution during the run must be zero watts."
            ),
            expert="max(P_battery) = 0 over load and steady: P_system ≤ adapter rating.",
        ),
    )


def _adapter_at_most(watts: int, what: str) -> Criterion:
    return Criterion(
        id="adapter-size", label=f"Adapter rated {watts} W or less",
        metric="adapterW", op="<=", threshold=watts, unit="W",
        explain_id="supply-identity", equation=EQ_SUPPLY,
        why=L(
            standard=(
                f"The lab is set on {what}. P_ac can never exceed the "
                "adapter's rating, so the rating is the one term of the "
                "identity you may not raise; a bigger brick would be a "
                "different problem."
            ),
            novice=(
                f"This lab is about {what}. The charger can never supply more "
                "than the number printed on it, and everything else in the "
                "lab follows from that limit. Plugging in a bigger charger "
                "would make the problem disappear instead of solving it, so "
                f"the adapter you choose has to be {watts} watts or smaller."
            ),
            expert=f"P_ac ≤ {watts} W is the fixed term; a larger adapter is out of scope.",
        ),
    )


# --- Lab 1: fit the game inside the brick -----------------------------------

_BRICK_START = Scenario(
    profile_id="m18-r2", adapter_id="barrel-280", start_battery_pct=30,
    thermal_mode="fullSpeed", workload="gaming",
)

FIT_THE_BRICK = Lab(
    id="fit-the-brick",
    title="Fit the game inside the brick",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "On a 280 W adapter, Full Speed gaming pulls more than the "
                "brick can give and the pack drains while plugged in. Find "
                "the fastest setup that stays inside the adapter, with the "
                "pack still charging at steady state."
            ),
            novice=(
                "The lab starts with a game running in the 'Full Speed' "
                "thermal mode on a 280 watt charger. The laptop wants more "
                "than 280 watts, so it borrows the rest from its battery, and "
                "the battery goes down even though the laptop is plugged in. "
                "Your job is to find the fastest setup that the charger can "
                "carry on its own, with some power left over so the battery "
                "is still charging once the laptop has settled."
            ),
            expert=(
                "280 W adapter: P_system ≤ rating, steady P_charge ≥ 20 W, "
                "work floor 150 W; maximize work."
            ),
        ),
        constraints=[
            L(standard="An adapter of 280 W or less that the laptop identifies.",
              novice="Use a charger of 280 watts or less, and it must be one the laptop can identify (not the 'Unknown' one).",
              expert="Recognized adapter, ≤ 280 W."),
            L(standard="The battery never supplements the adapter under load.",
              novice="The battery must never have to help the charger while the laptop is working.",
              expert="No hybrid step."),
            L(standard="At steady state the pack is still charging at 20 W or more.",
              novice="When the laptop has settled, the battery must still be charging at 20 watts or more.",
              expert="Steady P_charge ≥ 20 W."),
        ],
        delivered_work=L(
            standard="At least 150 W of silicon work, averaged over the load and steady steps.",
            novice="The processor and graphics chip together must average at least 150 watts of real work while under load. An idle laptop does not count.",
            expert="workW ≥ 150.",
        ),
    ),
    criteria=[
        _work(150),
        _no_hybrid(),
        Criterion(
            id="still-charging", label="Pack still charging at steady state, 20 W or more",
            metric="steadyChargeW", op=">=", threshold=20, unit="W",
            explain_id="charge-headroom", equation=EQ_CHARGE,
            why=L(
                standard=(
                    "The pack gets the adapter's leftovers: 280 W minus "
                    "system power, up to 90 W. It also gets nothing once it "
                    "reaches the 94% hold band, so a run that starts nearly "
                    "full ends with the charger off."
                ),
                novice=(
                    "The battery only gets the power the charger has left "
                    "over after the laptop has taken what it needs: 280 "
                    "watts minus what the laptop is using. If that leftover "
                    "is under 20 watts, this line fails. There is a second "
                    "way to fail it: a battery that reaches 94% stops "
                    "charging on purpose, so do not start the run with a "
                    "nearly full battery."
                ),
                expert="Headroom = 280 − P_system ≥ 20 W, and the pack below the 94% hold band at the end.",
            ),
        ),
        _adapter_at_most(280, "the 280 W brick that ships with the m18"),
        _recognized(),
    ],
    objective=Objective(
        label="Silicon work", metric="workW", direction="maximize",
        par=185, worst=150, unit="W", explain_id="thermal-cap", equation=EQ_CAP,
    ),
    hints=[
        L(standard="Play the start scenario to the end and read the battery line: it is supplying watts, and the adapter is pinned at 280 W.",
          novice="Press Run on the starting setup and watch the battery line in the picture near the end. The battery is giving power, not taking it, and the charger is stuck at its 280 watt limit. That is the state you have to get out of.",
          expert="Start state: P_ac = 280 W, P_battery > 0."),
        L(standard="System power is the rest of the platform plus the silicon, and the silicon is the thermal-mode cap times what the workload asks for. You need about 260 W or less to leave 20 W for the pack.",
          novice="What the laptop draws is the screen and other parts (about 25 watts) plus the processor and graphics chip. The thermal mode sets how much those two chips may use, and the workload sets how much of that they ask for. To leave 20 watts for the battery the whole laptop has to draw about 260 watts or less.",
          expert="Need P_system ≤ 260 W: pick cap(mode) × demand accordingly."),
        L(standard="One mode down is enough: Performance with the gaming workload draws about 254 W and leaves 26 W for the pack. Full load in Performance goes hybrid again, and Balanced gives up work you did not need to give up.",
          novice="You only need to go one thermal mode down. In 'Performance' the game makes the laptop draw about 254 watts, which leaves 26 watts for the battery. The 'Full load' workload in Performance is too much again, and 'Balanced' works but gives away speed you could have kept. Start the battery well below 94% so it is still charging at the end.",
          expert="Performance + gaming: 254 W system, 26 W charge; start pack well under 94%."),
    ],
    start=_BRICK_START.model_dump(by_alias=True),
)


# --- Lab 2: an hour on the travel charger ------------------------------------

_TRAVEL_START = Scenario(
    profile_id="area51-18", adapter_id="usbc-100", start_battery_pct=30,
    thermal_mode="balanced", workload="gaming",
)

TRAVEL_CHARGER = Lab(
    id="travel-charger",
    title="An hour on the travel charger",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "You packed the 100 W USB-C charger instead of the brick. Any "
                "real load on the Area-51 now runs on hybrid power, so the "
                "question is how long the pack lasts. Get real work done and "
                "keep hybrid power alive for at least 75 minutes."
            ),
            novice=(
                "You are travelling with the small 100 watt USB-C charger "
                "instead of the big charger brick. The Area-51 laptop wants "
                "more than 100 watts for any real work, so its battery will "
                "be helping the charger the whole time and slowly emptying. "
                "That help stops when the battery reaches 20%. Set things up "
                "so the laptop still does real work and the battery can keep "
                "helping for at least 75 minutes."
            ),
            expert=(
                "100 W USB-C: hybrid is unavoidable. Work floor 90 W, time to "
                "the 20% hybrid floor ≥ 75 min; maximize that time."
            ),
        ),
        constraints=[
            L(standard="An adapter of 100 W or less that the laptop identifies.",
              novice="Use a charger of 100 watts or less that the laptop can identify. In this app that is the USB-C charger on the Area-51.",
              expert="Recognized adapter, ≤ 100 W."),
            L(standard="At the end of the run, at least 75 minutes remain before the pack reaches the 20% hybrid floor.",
              novice="When the run ends, the battery must be able to keep helping the charger for at least 75 more minutes before it falls to 20%.",
              expert="Hybrid runtime ≥ 75 min at the steady state."),
        ],
        delivered_work=L(
            standard="At least 90 W of silicon work, averaged over the load and steady steps.",
            novice="The processor and graphics chip together must average at least 90 watts of real work while under load. An idle laptop lasts forever and does not count.",
            expert="workW ≥ 90.",
        ),
    ),
    criteria=[
        _work(90),
        Criterion(
            id="runtime", label="Hybrid power lasts at least 75 min",
            metric="hybridRuntimeMin", op=">=", threshold=75, unit="min",
            weight=2.0, explain_id="hybrid-runtime", equation=EQ_RUNTIME,
            why=L(
                standard=(
                    "Runtime is the charge above 20%, times the 96 Wh pack, "
                    "divided by the watts the battery supplies at steady "
                    "state. Both terms are yours: the thermal mode and "
                    "workload set the supplement, the starting charge sets "
                    "the numerator. 999 means the pack is not being drawn on."
                ),
                novice=(
                    "The time left is the battery's spare energy divided by "
                    "how fast it is being used. Spare energy is the charge "
                    "above 20% of a 96 watt-hour battery. How fast it is "
                    "used is the number of watts the battery is adding to "
                    "the charger. You control both: a gentler thermal mode "
                    "or workload asks for fewer watts, and a fuller battery "
                    "has more to give. A reading of 999 means the battery "
                    "is not being used at all."
                ),
                expert="(pack% − 20) × 0.96 Wh ÷ steady P_battery × 60; 999 = no drain.",
            ),
        ),
        _adapter_at_most(100, "the 100 W USB-C travel charger"),
        _recognized(),
    ],
    objective=Objective(
        label="Hybrid runtime", metric="hybridRuntimeMin", direction="maximize",
        par=88.9, worst=75, unit="min", explain_id="hybrid-runtime", equation=EQ_RUNTIME,
    ),
    hints=[
        L(standard="Read the steady-state battery watts in the start scenario: about 104 W from a pack that ends near 65%. Put those two numbers in the runtime equation.",
          novice="Run the starting setup to the end and read two numbers: how many watts the battery is giving (about 104) and how full it is (about 65%). The spare charge is 65 − 20 = 45% of 96 watt-hours, about 43 watt-hours. At 104 watts that lasts about 25 minutes. You need three times that.",
          expert="Start: ~104 W supplement from ~65% → ~25 min."),
        L(standard="The supplement is system power minus 100 W, so every watt you take off the silicon comes straight off the battery. Quiet with the gaming workload needs about 50 W of help and still clears the work floor; Quiet at full load needs 79 W and does not last.",
          novice="The battery supplies whatever the laptop wants above 100 watts. So each watt you save comes directly off the battery's share. In the 'Quiet' thermal mode a game needs only about 50 watts of help and still does enough work to pass. The 'Full load' workload in Quiet needs about 79 watts of help, which runs the battery down too fast.",
          expert="Quiet + gaming: ~50 W supplement, work ≈ 96 W. Quiet + full load: 79 W, too short."),
        L(standard="Then fix the numerator. The pack charges at up to 90 W before boot, so a start of 50% reaches the load near 90%; 30% does not get there. A full pack at the start gives the longest runtime.",
          novice="Now look at how full the battery is. Before the laptop boots, the charger has the battery to itself and fills it quickly, so starting at 50% gets you to about 90% by the time the game starts. Starting at 30% does not get high enough. Starting with a full battery gives the longest time of all.",
          expert="Pre-boot CC lifts the pack ~40 points; start ≥ ~45% to pass, 100% for par."),
    ],
    start=_TRAVEL_START.model_dump(by_alias=True),
)


# --- Lab 3: charge fast, play hard, stay quiet -------------------------------

_QUIET_START = Scenario(
    profile_id="m18-r2", adapter_id="barrel-280", start_battery_pct=30,
    thermal_mode="balanced", workload="fullLoad",
)

CHARGE_PLAY_QUIET = Lab(
    id="charge-play-quiet",
    title="Charge fast, play hard, stay quiet",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "You arrive with a low pack and an hour to work in a shared "
                "room. You want three things at once: the pack charging at "
                "its full rate the whole time, real silicon work, and fans "
                "at 75% or less. Each one is easy alone."
            ),
            novice=(
                "You sit down in a shared room with a low battery. You want "
                "three things at the same time. The battery should charge as "
                "fast as it can for the whole run. The laptop should do heavy "
                "work. And the fans should stay at 75% or less so you do not "
                "annoy the room. Any one of these is easy. The lab is getting "
                "all three together."
            ),
            expert=(
                "Pack gain ≥ 49.5 points (full CC throughout), work ≥ 160 W, "
                "fan ≤ 75%, no hybrid; maximize work."
            ),
        ),
        constraints=[
            L(standard="The pack gains at least 49.5 percentage points over the run.",
              novice="The battery must end the run at least 49.5 points higher than it started (for example, from 30% to 79.5%).",
              expert="End − start ≥ 49.5 points."),
            L(standard="Fan duty under load never above 75%.",
              novice="While the laptop is working, the fans must never go above 75%.",
              expert="max(fan%) ≤ 75 over load and steady."),
            L(standard="The battery never supplements the adapter, and the laptop identifies the adapter.",
              novice="The battery must never have to help the charger, and the charger must be one the laptop can identify.",
              expert="No hybrid step; recognized adapter."),
        ],
        delivered_work=L(
            standard="At least 160 W of silicon work, averaged over the load and steady steps.",
            novice="The processor and graphics chip together must average at least 160 watts of real work while under load. An idle laptop charges fast and stays quiet, and does not count.",
            expert="workW ≥ 160.",
        ),
    ),
    criteria=[
        _work(160),
        Criterion(
            id="pack-gain", label="Pack gains at least 49.5 points",
            metric="packGainPct", op=">=", threshold=49.5, unit="points",
            weight=2.0, explain_id="charge-headroom", equation=EQ_CHARGE,
            why=L(
                standard=(
                    "49.5 points is what the pack gains when it gets the full "
                    "90 W at every step. That needs 90 W of headroom under "
                    "load — adapter rating minus system power — and a start "
                    "low enough that the 94% hold band never cuts the "
                    "charge off."
                ),
                novice=(
                    "The battery only gains this much if it is charged at "
                    "its full 90 watts at every step, including while the "
                    "laptop is working hard. For that, the charger needs 90 "
                    "watts to spare after the laptop has taken its share. It "
                    "also means you must start low enough: a battery that "
                    "reaches 94% stops charging, and then it cannot gain "
                    "the full amount."
                ),
                expert="Requires rating − P_system ≥ 90 W at every loaded step and no 94% cutoff.",
            ),
        ),
        Criterion(
            id="quiet-fans", label="Fans at 75% or less under load",
            metric="peakFanPct", op="<=", threshold=75, unit="%",
            explain_id="fan-duty", equation=EQ_FAN,
            why=L(
                standard=(
                    "Fan duty is the mode's base plus up to 55 points for "
                    "system power. Performance starts at 60% and Full Speed "
                    "is pinned at 100%, so the mode decides this line far "
                    "more than the workload does."
                ),
                novice=(
                    "Fan speed starts from a level set by the thermal mode "
                    "and rises with the power the laptop draws. 'Performance' "
                    "starts at 60% and 'Full Speed' is always 100%, so both "
                    "go past 75% under any real load. The thermal mode "
                    "matters much more here than which workload you pick."
                ),
                expert="base(mode) + 55 × P_sys/P_full ≤ 75: rules out Performance and Full Speed under load.",
            ),
        ),
        _no_hybrid(),
        _recognized(),
    ],
    objective=Objective(
        label="Silicon work", metric="workW", direction="maximize",
        par=174, worst=160, unit="W", explain_id="thermal-cap", equation=EQ_CAP,
    ),
    hints=[
        L(standard="Grade the start scenario and look at what fails: only the pack gain. Balanced at full load draws about 241 W, so a 280 W adapter has 39 W left for a pack that wants 90 W.",
          novice="Grade the starting setup first. Only one line fails: the battery did not gain enough. In 'Balanced' at full load the laptop draws about 241 watts. A 280 watt charger then has only 39 watts left for a battery that could take 90.",
          expert="Start fails on headroom only: 280 − 241 = 39 W < 90 W."),
        L(standard="There are two ways to find 90 W of headroom: draw less, or supply more. Drawing less means Quiet, which misses the work floor. A bigger adapter does not make the laptop faster; it makes the leftovers bigger.",
          novice="To give the battery 90 spare watts you can either make the laptop use less or give it a bigger charger. Using less means the 'Quiet' mode, and that does too little work to pass. A bigger charger does not make the laptop any faster. What it does is leave more power over for the battery.",
          expert="Quiet fails the work floor; raise the rating instead of cutting the load."),
        L(standard="On the 360 W adapter, Performance gaming would do more work but its fans start at 60% and pass 75%. Balanced at full load does nearly as much work at 72% fans, because full load in a lower mode asks for more than gaming does. Start below 45% so the pack never reaches the hold band.",
          novice="With the 360 watt charger, 'Performance' with a game would do the most work, but its fans go far past 75%. 'Balanced' with the 'Full load' workload does nearly as much work and keeps the fans at about 72%, because full load uses all of the processor's allowance where a game uses only part. Start the battery below 45% so it never reaches 94% and stops charging.",
          expert="360 W + Balanced + full load: 241 W system, 90 W charge, 72% fans; start < 45%."),
    ],
    start=_QUIET_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [FIT_THE_BRICK, TRAVEL_CHARGER, CHARGE_PLAY_QUIET]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Reference solutions and the tricks that must not work -------------------
# Server-side only: GET /api/labs serves LABS, never these.

def _sc(profile: str, adapter: str, pct: float, mode: str, workload: str) -> Scenario:
    return Scenario(
        profile_id=profile, adapter_id=adapter, start_battery_pct=pct,
        thermal_mode=mode, workload=workload,
    )


REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    "fit-the-brick": _sc("m18-r2", "barrel-280", 30, "performance", "gaming"),
    "travel-charger": _sc("area51-18", "usbc-100", 100, "quiet", "gaming"),
    "charge-play-quiet": _sc("m18-r2", "barrel-360", 30, "balanced", "fullLoad"),
}

GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "fit-the-brick": {
        "zero load": _sc("m18-r2", "barrel-280", 30, "performance", "idle"),
        "bigger brick": _sc("m18-r2", "barrel-360", 30, "fullSpeed", "gaming"),
        "unknown adapter never goes hybrid": _sc("m18-r2", "barrel-unknown", 30, "fullSpeed", "fullLoad"),
        "quiet mode": _sc("m18-r2", "barrel-280", 30, "quiet", "fullLoad"),
        "full load one mode down": _sc("m18-r2", "barrel-280", 30, "performance", "fullLoad"),
        "start with a full pack": _sc("m18-r2", "barrel-280", 96, "performance", "gaming"),
    },
    "travel-charger": {
        "zero load lasts forever": _sc("area51-18", "usbc-100", 100, "quiet", "idle"),
        "bring the brick after all": _sc("area51-18", "barrel-360", 100, "quiet", "gaming"),
        "other laptop on its brick": _sc("m18-r2", "barrel-280", 100, "quiet", "gaming"),
        "unknown adapter": _sc("area51-18", "barrel-unknown", 100, "quiet", "gaming"),
        "right mode, low pack": _sc("area51-18", "usbc-100", 30, "quiet", "gaming"),
        "full pack, greedy workload": _sc("area51-18", "usbc-100", 100, "quiet", "fullLoad"),
        "full pack, start mode": _sc("area51-18", "usbc-100", 100, "balanced", "gaming"),
    },
    "charge-play-quiet": {
        "zero load": _sc("m18-r2", "barrel-360", 30, "balanced", "idle"),
        "quiet mode charges and whispers": _sc("m18-r2", "barrel-360", 30, "quiet", "fullLoad"),
        "most work, loud fans": _sc("m18-r2", "barrel-360", 30, "performance", "gaming"),
        "right settings, small brick": _sc("m18-r2", "barrel-280", 30, "balanced", "fullLoad"),
        "start nearly full": _sc("m18-r2", "barrel-360", 60, "balanced", "fullLoad"),
        "unknown adapter": _sc("m18-r2", "barrel-unknown", 30, "balanced", "fullLoad"),
    },
}


# --- Grading ------------------------------------------------------------------

def grade_scenario(lab_id: str, scenario: Scenario) -> LabResult:
    """Run the engine on the learner's scenario and grade the trace.

    Pure and deterministic. Raises ``KeyError`` for an unknown lab id and
    ``ValueError`` for a scenario naming a machine or adapter the catalog
    does not have (``main.py`` turns those into 404 and 422).
    """
    lab = LABS_BY_ID[lab_id]
    profile, adapter = resolve(scenario)
    trace = simulate(profile, adapter, scenario)
    return grade(lab, measure(profile, adapter, scenario, trace))
