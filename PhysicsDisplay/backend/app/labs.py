"""Graded labs for the UltraSharp display simulator (``docs/LAB_PATTERN.md``).

A guided scenario sets the dials and tells you what to watch. A lab states a
goal and leaves the dials to you: build a Scenario with the ordinary controls,
the engine runs it, and ``grade_scenario`` scores the trace.

Pure module, same rule as ``engine.py`` and ``validation.py``: no FastAPI, no
IO, no clock, no randomness (AST-checked in ``tests/test_labs.py``). ``main.py``
is the only caller that touches HTTP, so a static-hosting build runs this same
grading in the browser.

Three things here are this app's own; everything else is ``twinkit.labs``:

* ``measure()`` — turns one run into named numbers. The un-gameable one is
  ``usefulLightPct``: backlight drive (the brightness setting, or the HDR
  overdrive) × the share of the picture that actually needs light, averaged
  over the whole run with standby seconds counted as zero. A dark, dimmed or
  sleeping screen shows nothing, so it passes nothing. It is an illustrative
  proxy for "picture delivered to the viewer", not a photometric measurement,
  and is labeled so.
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
    DisplayConfig,
    Lifecycle,
    Scenario,
    SimEvent,
    SimState,
    Summary,
    Validation,
)
from .validation import validate

# The equations, exactly as the Explain entries display them.
EQ_BL = "P_bl = P_max × brightness × lit"
EQ_WALL = "P_ac = (P_elec + P_bl + P_hub/η_hub) / η_psu"
EQ_HEAT = "Q = P_dc − P_hub_out"
EQ_CO2 = "CO2_use = kWh/yr × years × grid"


# --- Measurement ----------------------------------------------------------

def _content_lit(content: str) -> float:
    return {
        "dark": C("lit_dark"),
        "mixed": C("lit_mixed"),
        "bright": C("lit_bright"),
        "hdr": C("lit_hdr"),
    }[content]


def measure(
    scenario: Scenario,
    trace: list[SimState],
    summary: Summary,
    validations: list[Validation],
) -> dict[str, float]:
    """One run as named numbers. Keys are the wire names criteria refer to."""
    cfg = scenario.config
    life = scenario.lifecycle
    mini = cfg.model == "miniled-32"
    events = sorted(scenario.events, key=lambda e: e.at_s)
    ei = 0
    brightness = float(cfg.brightness_pct)
    light = 0.0
    for s in trace:
        # Replay the brightness dial exactly as the engine applied it (the
        # trace carries brightness as an int; the engine used the float).
        while ei < len(events) and events[ei].at_s <= s.t:
            ev = events[ei]
            ei += 1
            if ev.action == "set-brightness" and ev.value is not None:
                brightness = max(0.0, min(100.0, ev.value))
        if s.on:
            if s.content == "hdr":
                drive = C("hdr_boost") if mini else C("hdr_boost_edge")
            else:
                drive = brightness / 100.0
            light += drive * _content_lit(s.content) * 100.0
    n = len(trace)
    lits = [_content_lit(s.content) for s in trace]
    return {
        "durationS": float(trace[-1].t),
        "usefulLightPct": round(light / n, 1),
        "meanWallW": round(sum(s.ac_power_w for s in trace) / n, 2),
        "peakWallW": round(max(s.ac_power_w for s in trace), 2),
        "peakHeatW": round(max(s.heat_w for s in trace), 2),
        "meanHubW": round(sum(s.hub_out_w for s in trace) / n, 1),
        "minContentLit": round(min(lits), 2),
        "maxContentLit": round(max(lits), 2),
        "standbySeconds": float(sum(1 for s in trace if not s.on)),
        "hoursPerDay": float(life.hours_per_day),
        "daysPerYear": float(life.days_per_year),
        "serviceYears": float(life.service_years),
        "gridKgPerKwh": float(life.grid_kgco2_per_kwh),
        "carbonPerYearKg": round(summary.carbon.lifetime_kg / life.service_years, 1),
        "usePhasePct": float(summary.carbon.use_pct),
        "validationErrors": float(sum(1 for v in validations if v.level == "error")),
    }


# --- Criteria shared between labs ------------------------------------------

def _light(floor: int, example: str) -> Criterion:
    return Criterion(
        id="light", label=f"Useful light at least {floor} %-field",
        metric="usefulLightPct", op=">=", threshold=floor, unit="%-field",
        weight=2.0, guards_work=True, explain_id="backlight-power",
        equation=EQ_BL,
        why=L(
            standard=(
                f"Useful light is brightness × the share of the picture that "
                f"needs light, averaged over the whole run with standby "
                f"seconds counted as zero; {floor} %-field is the floor "
                f"({example}). Dimming the screen or putting it to sleep "
                "lowers every watt figure and delivers less picture, so it is "
                "not a way through. The proxy is illustrative, not a "
                "photometric measurement."
            ),
            novice=(
                f"A monitor's job is to put light where the picture needs it, "
                f"and this lab insists it keeps doing that job: at least "
                f"{floor} units ({example}). We count useful light as how "
                "bright the backlight is driven (the Brightness slider), "
                "times how much of the picture is actually bright rather "
                "than black. Seconds the screen spends asleep count as zero, "
                "and the score is an average over the whole run. So you "
                "cannot win by turning the brightness down or putting the "
                "monitor to sleep: the watts fall, but so does this number. "
                "It is a simple stand-in for 'picture delivered', not a real "
                "light-meter reading."
            ),
            expert=(
                f"Mean of drive × content lit × 100 over all ticks, standby "
                f"zero; floor {floor} %-field ({example}). Illustrative proxy."
            ),
        ),
    )


def _full_run(seconds: int) -> Criterion:
    return Criterion(
        id="full-run", label=f"Run lasts at least {seconds} s",
        metric="durationS", op=">=", threshold=seconds, unit="s",
        explain_id="wall-power", equation=EQ_WALL,
        why=L(
            standard=(
                f"Every figure in this lab is a mean or a peak over one "
                f"session at the wall, so the session has to be a whole one: "
                f"{seconds} seconds, the length the lab starts with."
            ),
            novice=(
                f"The lab grades averages and peaks taken over a whole "
                f"session of at least {seconds} seconds, which is the length "
                "it starts with. A much shorter run would be graded on a "
                "snapshot instead of a session, so it does not count."
            ),
            expert=f"Means and peaks are taken over ≥ {seconds} s.",
        ),
    )


def _valid_build() -> Criterion:
    return Criterion(
        id="valid-build", label="Setup has no validation errors",
        metric="validationErrors", op="<=", threshold=0, unit="errors",
        explain_id="wall-power", equation=EQ_WALL,
        why=L(
            standard=(
                "The USB-C port delivers at most 90 W on this class; a setup "
                "asking for more is an error, not a plan. Warnings (dimming "
                "on an edge-lit panel, signage-length hours) are allowed."
            ),
            novice=(
                "The panel on the left checks your setup. A red error means "
                "the monitor could not really do what you asked — for "
                "example, its USB-C port can hand a laptop at most 90 W. "
                "Yellow warnings are allowed; red errors are not."
            ),
            expert="Zero error-level findings (PD ≤ 90 W); warnings pass.",
        ),
    )


def _dark_content() -> Criterion:
    return Criterion(
        id="dark-content", label="Content stays dark for the whole run",
        metric="maxContentLit", op="<=", threshold=0.12, unit="lit fraction",
        explain_id="backlight-power", equation=EQ_BL,
        why=L(
            standard=(
                "The job is a dark interface — a lit fraction of 0.12, the "
                "'dark' content profile — from the first second to the last. "
                "The content is the work, not a dial: the lab is about what "
                "the hardware does with a dark picture, so the picture may "
                "not change."
            ),
            novice=(
                "The person at this screen works in dark mode: a dark editor "
                "or dark dashboards, where only about an eighth of the "
                "picture (0.12) is bright. That is the 'dark' button in the "
                "content row, and it has to stay selected for the whole run. "
                "Careful: choosing a panel preset puts the content back to "
                "'mixed', so check the content row after you switch panels."
            ),
            expert="max content lit ≤ 0.12 on every tick: 'dark' throughout.",
        ),
    )


# --- Lab 1: dark mode that pays --------------------------------------------

_DARK_START = Scenario(
    config=DisplayConfig(model="edge-27", brightness_pct=75, content="dark",
                         local_dimming=False, hub_laptop_w=0),
    duration_s=300,
)

DARK_MODE_PAYS = Lab(
    id="dark-mode-that-pays",
    title="Make dark mode pay",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "A developer works in a dark editor all day. Keep the content "
                "dark and the picture properly visible, and get the mean wall "
                "power to 25 W or less — then as low as it will go."
            ),
            novice=(
                "Someone works in a dark-mode editor all day and has heard "
                "that dark mode saves electricity. Make that true. Keep the "
                "content dark, keep the screen bright enough to read "
                "comfortably, and get the average power drawn from the wall "
                "socket down to 25 W or less. Once you pass, see how much "
                "lower you can get it without breaking a rule."
            ),
            expert=(
                "Dark content throughout, useful light ≥ 9 %-field, mean "
                "P_ac ≤ 25 W; minimize mean P_ac."
            ),
        ),
        constraints=[
            L(standard="Content stays on the dark profile for the whole run.",
              novice="The 'dark' content button stays selected from start to finish (check it again after switching panels).",
              expert="Content lit ≤ 0.12 throughout."),
            L(standard="Mean wall power 25 W or less over the full 300-second run.",
              novice="Averaged over the whole 300-second run, the wall meter reads 25 W or less.",
              expert="Mean P_ac ≤ 25 W over 300 s."),
            L(standard="No validation errors.",
              novice="No red errors in the panel on the left.",
              expert="Zero errors."),
        ],
        delivered_work=L(
            standard="At least 9 %-field of useful light, averaged over the run — dark content at 75% brightness.",
            novice="The screen must deliver at least 9 units of useful light on average, which is what dark content gives at 75% brightness. A dimmer or sleeping screen does not count.",
            expert="usefulLightPct ≥ 9 (0.75 × 0.12).",
        ),
    ),
    criteria=[
        _light(9, "dark content at 75% brightness"),
        _dark_content(),
        Criterion(
            id="wall", label="Mean wall power 25 W or less",
            metric="meanWallW", op="<=", threshold=25, unit="W", weight=2.0,
            explain_id="backlight-power", equation=EQ_BL,
            why=L(
                standard=(
                    "Backlight watts are maximum × brightness × lit, and the "
                    "lit term only follows the picture when the backlight has "
                    "zones that can switch off. An edge-lit strip lights the "
                    "full field behind a dark picture (lit = 1.0), and so "
                    "does a mini-LED panel with local dimming turned off. "
                    "With zones dimming, dark content drives about 12% of "
                    "the array."
                ),
                novice=(
                    "The light behind the screen uses power in proportion to "
                    "three things: how big it is, how bright you set it, and "
                    "how much of it is switched on. That last part is the "
                    "catch. A 27-inch edge-lit monitor has one strip of "
                    "lights that is either all on or all off, so a dark "
                    "picture is just a fully lit backlight hidden behind "
                    "black pixels — no saving. The mini-LED panel has 2,000 "
                    "small zones that can switch off behind the dark parts, "
                    "but only while 'Local dimming' is ticked. With dark "
                    "content and dimming on, only about 12% of the zones "
                    "are lit."
                ),
                expert=(
                    "lit ≡ 1.0 on edge-lit and on FALD with dimming off; "
                    "FALD + dimming: lit = 0.12 on dark content."
                ),
            ),
        ),
        _full_run(300),
        _valid_build(),
    ],
    objective=Objective(
        label="Mean wall power", metric="meanWallW", direction="minimize",
        par=22.67, worst=25, unit="W", explain_id="backlight-power",
        equation=EQ_BL,
    ),
    hints=[
        L(standard="On the edge-lit panel, switch between bright and dark content and watch the wall meter: it does not move. The lit fraction is pinned at 1.0.",
          novice="Start by experimenting. On the 27-inch panel, click 'bright' and then 'dark' in the content row and watch the wall power number. It does not change at all. This monitor's single light strip stays fully on whatever the picture shows.",
          expert="Edge-lit: lit ≡ 1.0, ΔP(content) = 0."),
        L(standard="Lowering the brightness does cut the watts on the edge-lit panel, but 25 W needs about 45% brightness, and the useful-light floor needs 75%.",
          novice="You could turn the brightness down, and the power does fall. But to reach 25 W on the 27-inch panel you would have to go down to about 45% brightness, and the lab needs the screen at 75% to count as readable. The brightness slider alone cannot get you there.",
          expert="Edge needs b ≈ 0.45 for 25 W; floor needs b ≥ 0.75."),
        L(standard="The mini-LED preset resets the content to mixed. Select it, set the content back to dark, leave local dimming on and hold 75% brightness: about 5 W of backlight on top of a 15 W electronics floor.",
          novice="Choose the Mini-LED 32\" panel. Picking it puts the content back on 'mixed', so click 'dark' again. Keep the 'Local dimming' box ticked and the brightness at 75%. Now only the zones behind the bright parts are lit: about 5 W of light, plus 15 W for the monitor's electronics. Any brightness above 75% just adds watts.",
          expert="miniled-32, dark, dimming on, b = 0.75: 15 + 55 × 0.75 × 0.12 W DC."),
    ],
    start=_DARK_START.model_dump(by_alias=True),
)


# --- Lab 2: dock the laptop, keep the desk cool ------------------------------

_DOCK_START = Scenario(
    config=DisplayConfig(model="miniled-32", brightness_pct=75, content="bright",
                         local_dimming=True, hub_laptop_w=90),
    duration_s=300,
)

DOCK_COOL_DESK = Lab(
    id="dock-cool-desk",
    title="Dock the laptop, keep the desk cool",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "A hot-desk pod allows each monitor 38 W of heat. Show bright "
                "documents at a usable brightness, never put more than 38 W "
                "of heat into the room, and charge the docked laptop as fast "
                "as that budget allows."
            ),
            novice=(
                "A small, poorly ventilated desk pod lets each monitor give "
                "off at most 38 W of heat. The person there reads bright "
                "white documents and charges a laptop through the monitor's "
                "USB-C cable. Keep the documents readable, never let the "
                "monitor's heat go above 38 W, and hand the laptop as many "
                "watts as you can inside that limit. Watch two different "
                "readouts: the wall power and the heat are not the same "
                "number."
            ),
            expert=(
                "Bright content, useful light ≥ 60 %-field, peak Q ≤ 38 W, "
                "mean PD ≥ 60 W; maximize mean PD."
            ),
        ),
        constraints=[
            L(standard="Content stays on the bright profile for the whole run.",
              novice="The 'bright' content button stays selected from start to finish (check it again after switching panels).",
              expert="Content lit ≥ 0.9 throughout."),
            L(standard="Heat into the room never above 38 W.",
              novice="The 'heat' readout may never go above 38 W, not even for a second.",
              expert="max Q ≤ 38 W."),
            L(standard="At least 60 W delivered to the laptop, averaged over the full 300-second run; no validation errors.",
              novice="The laptop must receive at least 60 W on average over the whole 300-second run, so docking it late does not count. No red errors in the panel on the left.",
              expert="Mean PD ≥ 60 W over 300 s; zero errors."),
        ],
        delivered_work=L(
            standard="At least 60 %-field of useful light, averaged over the run — bright content at 67% brightness or more.",
            novice="The screen must deliver at least 60 units of useful light on average. With bright documents that means a brightness of 67% or more. A dim or sleeping screen does not count.",
            expert="usefulLightPct ≥ 60 (b ≥ 0.67 at lit 0.9).",
        ),
    ),
    criteria=[
        _light(60, "bright content at 67% brightness"),
        Criterion(
            id="bright-content", label="Content stays bright for the whole run",
            metric="minContentLit", op=">=", threshold=0.9, unit="lit fraction",
            explain_id="backlight-power", equation=EQ_BL,
            why=L(
                standard=(
                    "The job is white documents — a lit fraction of 0.9, the "
                    "'bright' profile — throughout. A darker picture would "
                    "cut the backlight's heat on a zoned panel, and it is "
                    "not the picture this desk shows."
                ),
                novice=(
                    "The person at this desk reads white documents, where "
                    "nine-tenths of the picture (0.9) is bright. That is the "
                    "'bright' button in the content row, and it has to stay "
                    "selected for the whole run. A darker picture would make "
                    "less heat on the zoned panel, but it is not the work "
                    "this desk does. Choosing a panel preset puts the "
                    "content back to 'mixed', so check it after you switch."
                ),
                expert="min content lit ≥ 0.9 on every tick: 'bright' throughout.",
            ),
        ),
        Criterion(
            id="heat", label="Heat into the room never above 38 W",
            metric="peakHeatW", op="<=", threshold=38, unit="W", weight=2.0,
            explain_id="heat", equation=EQ_HEAT,
            why=L(
                standard=(
                    "Heat is DC power minus the watts that leave over the "
                    "USB-C cable. Electronics and backlight become heat in "
                    "full; of every watt handed to the laptop, only the "
                    "conversion loss — about 0.11 W — stays in the monitor. "
                    "So the heat budget is spent almost entirely on the "
                    "panel, and the wall meter is the wrong gauge to steer by."
                ),
                novice=(
                    "Nearly all the electricity a monitor uses ends up as "
                    "warmth in the room. The exception is the power it "
                    "passes to a charging laptop: that leaves down the cable "
                    "and warms the laptop instead. The monitor keeps only a "
                    "small conversion loss, about 0.11 W for every watt it "
                    "hands over. So when the wall meter shows 170 W with a "
                    "laptop docked, most of that is not heating this desk. "
                    "What does heat the desk is the monitor's own "
                    "electronics and, above all, its backlight. Steer by "
                    "the heat readout, not the wall readout."
                ),
                expert=(
                    "Q = P_elec + P_bl + PD × (1/η_hub − 1); ∂Q/∂PD ≈ 0.11. "
                    "The panel, not the hub, spends the budget."
                ),
            ),
        ),
        Criterion(
            id="laptop-charges", label="At least 60 W to the laptop on average",
            metric="meanHubW", op=">=", threshold=60, unit="W", weight=2.0,
            explain_id="wall-power", equation=EQ_WALL,
            why=L(
                standard=(
                    "Hub delivery rides the same wall cord as the panel: the "
                    "wall sees P_hub ÷ η_hub on top of electronics and "
                    "backlight. The figure is a mean over the run, so a "
                    "laptop docked in the last seconds has not been charged."
                ),
                novice=(
                    "The laptop charges through the monitor, so its watts "
                    "come through the monitor's own power cord and show up "
                    "on the wall meter, plus a little extra for the "
                    "conversion. This lab needs the laptop to get at least "
                    "60 W averaged over the entire run. Undocking it to "
                    "save heat, or docking it only near the end, brings the "
                    "average below 60 W."
                ),
                expert="Mean P_hub_out ≥ 60 W; the wall carries P_hub/η_hub.",
            ),
        ),
        _full_run(300),
        _valid_build(),
    ],
    objective=Objective(
        label="Mean power to the laptop", metric="meanHubW",
        direction="maximize", par=85, worst=60, unit="W",
        explain_id="heat", equation=EQ_HEAT,
    ),
    hints=[
        L(standard="Move the USB-C slider from 90 W to 0 W and compare the two readouts: the wall falls by about 114 W, the heat by only 10 W. The laptop is not what is heating the desk.",
          novice="Try this first: drag the 'USB-C to laptop' slider from 90 W all the way down to 0 W and watch both readouts. The wall power drops by about 114 W, but the heat drops by only 10 W. Almost all the laptop's power was leaving down the cable. So the laptop is not the reason the desk is too warm.",
          expert="ΔPD = 90 W: ΔP_ac ≈ 114 W, ΔQ = 10 W."),
        L(standard="The heat is the panel's. On bright documents the mini-LED's zones are nearly all lit, so it burns 15 W of electronics plus up to 55 W of backlight; the edge-lit panel is 9 W plus up to 29 W.",
          novice="The heat comes from the monitor itself. White documents light almost every zone of the mini-LED panel, so its clever dimming saves nothing here, and it is a bigger, brighter panel: 15 W of electronics plus up to 55 W of backlight. The 27-inch edge-lit panel needs only 9 W plus up to 29 W. For this job the simpler panel is the cooler one.",
          expert="Bright content: FALD lit 0.9 of 55 W + 15 W vs edge 29 W + 9 W."),
        L(standard="On the edge-lit panel (content back on bright), brightness and charging share the 38 W: each brightness point costs 0.29 W of heat, each 5 W of charging about 0.56 W. Hold brightness at the 67% floor and 85 W fits; 90 W does not.",
          novice="Pick the Edge-lit 27\" panel and click 'bright' again. Now the brightness and the laptop share the 38 W heat allowance. Every point of brightness costs 0.29 W of heat, and every 5 W step of charging costs about 0.56 W. Set the brightness to 67%, the lowest the lab allows, and raise the laptop slider one step at a time: 85 W fits under 38 W of heat, and 90 W goes just over.",
          expert="edge-27, bright, b = 0.67: Q = 28.4 + PD/9 → PD = 85 W."),
    ],
    start=_DOCK_START.model_dump(by_alias=True),
)


# --- Lab 3: the greener control-room panel -----------------------------------

_CONTROL_ROOM = Lifecycle(hours_per_day=16, days_per_year=360,
                          service_years=6, grid_kgco2_per_kwh=0.4)

_GREEN_START = Scenario(
    config=DisplayConfig(model="edge-27", brightness_pct=75, content="dark",
                         local_dimming=False, hub_laptop_w=0),
    lifecycle=_CONTROL_ROOM,
    duration_s=300,
)

GREENER_PANEL = Lab(
    id="greener-control-room",
    title="The greener control-room panel",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "A control room shows dark dashboards 16 hours a day, 360 "
                "days a year, on a 0.40 kgCO2e/kWh grid. Get the monitor's "
                "lifetime carbon — building it plus running it — down to "
                "100 kgCO2e per year of service or less, then lower."
            ),
            novice=(
                "A control room keeps dark dashboards on screen 16 hours a "
                "day, almost every day of the year, on an ordinary "
                "electricity grid. A monitor's carbon footprint has two "
                "parts: what it cost to build (fixed, paid once) and what "
                "it costs to run (grows with every hour). Add the two over "
                "the monitor's whole life, divide by the years it serves, "
                "and get that figure to 100 kg of CO2 per year or less. The "
                "hours and the grid are given; the panel, the brightness "
                "and how long you keep the monitor are yours to choose. "
                "Once you pass, push the figure lower."
            ),
            expert=(
                "Dark content, 16 h × 360 d, grid ≥ 0.40; useful light ≥ 9 "
                "%-field; (embodied + use) ÷ years ≤ 100 kgCO2e/yr; minimize."
            ),
        ),
        constraints=[
            L(standard="Content stays dark; at least 16 on-hours a day, 360 days a year.",
              novice="The 'dark' content button stays selected, and the 'On-hours per day' slider stays at 16 or more. The 360 days a year are set by the lab.",
              expert="Dark content; ≥ 16 h/day, ≥ 360 d/yr."),
            L(standard="Grid intensity stays at 0.40 kgCO2e/kWh or above.",
              novice="Leave the 'Grid intensity' slider at 0.40 or higher. You cannot pass by pretending the electricity is cleaner than it is.",
              expert="Grid ≥ 0.40 kgCO2e/kWh."),
            L(standard="Lifetime carbon per service year 100 kgCO2e or less; no validation errors.",
              novice="Lifetime carbon (build plus use) divided by the service years must be 100 kg or less, with no red errors in the panel on the left. Yellow warnings about long hours are fine.",
              expert="(embodied + use)/years ≤ 100; zero errors."),
        ],
        delivered_work=L(
            standard="At least 9 %-field of useful light, averaged over the run — dark dashboards at 75% brightness.",
            novice="The screen must deliver at least 9 units of useful light on average, which is what dark dashboards give at 75% brightness. Operators have to be able to read it.",
            expert="usefulLightPct ≥ 9 (0.75 × 0.12).",
        ),
    ),
    criteria=[
        _light(9, "dark content at 75% brightness"),
        _dark_content(),
        Criterion(
            id="carbon", label="Lifetime carbon 100 kgCO2e per service year or less",
            metric="carbonPerYearKg", op="<=", threshold=100, unit="kgCO2e/yr",
            weight=3.0, explain_id="use-carbon", equation=EQ_CO2,
            why=L(
                standard=(
                    "Lifetime carbon is the embodied figure (422 kgCO2e for "
                    "the edge-lit class, 516 for the mini-LED class — PCF "
                    "class proxies) plus kWh per year × years × grid. Per "
                    "service year, the embodied part shrinks as the monitor "
                    "is kept longer and the use part does not. At desk hours "
                    "the embodied part decides and the cheaper-to-build "
                    "panel wins; at 16 hours a day the use part is the "
                    "larger, and a panel that draws 12 W less on dark "
                    "content repays its extra 94 kg several times over."
                ),
                novice=(
                    "Think of two bills. The building bill is paid once: "
                    "about 422 kg of CO2 for the 27-inch monitor and 516 kg "
                    "for the mini-LED one (figures from Dell's carbon "
                    "datasheets for similar monitors). The running bill "
                    "comes every year: the electricity it uses, times how "
                    "dirty the grid is. Spread over the monitor's life, the "
                    "building bill gets smaller each extra year you keep "
                    "it; the running bill stays the same every year. In an "
                    "office, eight hours a day, the building bill is the "
                    "big one, so the monitor that is cheaper to build is "
                    "greener. Here the screen is on 16 hours a day, so the "
                    "running bill is the big one, and a monitor that draws "
                    "12 W less on dark dashboards pays back its extra 94 kg "
                    "of building carbon several times over."
                ),
                expert=(
                    "(E + kWh/yr × yrs × g)/yrs. E: 422 vs 516 kgCO2e (PCF "
                    "proxies). At 5,760 h/yr a 12 W saving outweighs ΔE = "
                    "94 kg; at desk duty it does not."
                ),
            ),
        ),
        Criterion(
            id="duty", label="At least 16 on-hours per day",
            metric="hoursPerDay", op=">=", threshold=16, unit="h/day",
            explain_id="use-carbon", equation=EQ_CO2,
            why=L(
                standard="The room runs two shifts. Fewer on-hours would shrink kWh per year, and would describe a different room.",
                novice="This control room is staffed 16 hours a day and the screens stay on. Sliding the hours down would make the carbon number smaller, but it would be the answer for a different room, so the slider has to stay at 16 or more.",
                expert="hours/day ≥ 16; the kWh/yr term is given.",
            ),
        ),
        Criterion(
            id="calendar", label="At least 360 days per year",
            metric="daysPerYear", op=">=", threshold=360, unit="days/yr",
            explain_id="use-carbon", equation=EQ_CO2,
            why=L(
                standard="The lab's start sets a 360-day year; the page has no control for it, and a scenario that shortens it is graded as shortened.",
                novice="A control room runs nearly every day: 360 days a year, which the lab sets for you. There is no slider for it on the page, so this line only fails if the scenario was changed some other way.",
                expert="days/yr ≥ 360, set by the start scenario.",
            ),
        ),
        Criterion(
            id="grid", label="Grid intensity at least 0.40 kgCO2e/kWh",
            metric="gridKgPerKwh", op=">=", threshold=0.4, unit="kgCO2e/kWh",
            explain_id="use-carbon", equation=EQ_CO2,
            why=L(
                standard="Grid intensity multiplies every kWh. A cleaner grid is a real lever for a real site and not one this room has; 0.40 is an estimate of a mixed grid.",
                novice="Every unit of electricity counts for more carbon on a dirty grid and less on a clean one. Moving to cleaner power is a real way to cut carbon, but this room cannot choose its grid, so the slider stays at 0.40 or higher. The 0.40 itself is an estimate for a typical mixed grid.",
                expert="g ≥ 0.40 kgCO2e/kWh (estimate); not a free variable here.",
            ),
        ),
        _full_run(300),
        _valid_build(),
    ],
    objective=Objective(
        label="Lifetime carbon per service year", metric="carbonPerYearKg",
        direction="minimize", par=95.6, worst=100, unit="kgCO2e/yr",
        explain_id="use-carbon", equation=EQ_CO2,
    ),
    hints=[
        L(standard="Read the carbon bar. At these hours the use share is larger than the embodied share — the reverse of the same monitor at desk duty — so both halves of the ledger need work.",
          novice="Look at the 'Lifetime carbon' bar on the right. At 16 hours a day the 'use' part of the bar is bigger than the 'embodied' (building) part. At normal office hours it is the other way round. So here you have to shrink both parts, and they shrink in different ways.",
          expert="Use share > embodied share at 5,760 h/yr: two terms, two levers."),
        L(standard="Service years divide the embodied term. Stretching the edge-lit panel from 6 to 12 years takes it from about 151 to 116 kgCO2e per year — better, and still short, because the use term has not moved.",
          novice="The building carbon is paid once, so every extra year you keep the monitor spreads it thinner. Slide 'Service years' from 6 up to 12 on the 27-inch panel and the figure falls from about 151 to 116 kg per year. That is a big improvement and still not enough, because the running part has not changed at all.",
          expert="Edge: 151 → 116 kgCO2e/yr at 12 y; use term untouched."),
        L(standard="On dark content the mini-LED panel with local dimming draws about 23 W against the edge-lit panel's 35 W. Over 5,760 hours a year that saves roughly 28 kgCO2e a year, against an embodied premium of 94 kg spread over the service life. Mini-LED, dark, dimming on, 75% brightness, 11 or 12 years.",
          novice="Now the running part. On dark dashboards the mini-LED panel, with 'Local dimming' ticked, draws about 23 W; the 27-inch panel draws about 35 W, because its light strip cannot switch off behind the dark areas. Over 5,760 hours a year that difference saves roughly 28 kg of CO2 every year. The mini-LED costs 94 kg more to build, but spread over 12 years that is under 8 kg a year. So: choose Mini-LED, click 'dark' again, keep dimming on, hold 75% brightness, and keep the monitor 11 or 12 years.",
          expert="FALD: −12 W × 5,760 h × 0.4 ≈ −28 kg/yr vs +94 kg/12 y. miniled-32, 12 y: 95.6."),
    ],
    start=_GREEN_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [DARK_MODE_PAYS, DOCK_COOL_DESK, GREENER_PANEL]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Reference solutions and the tricks that must not work -----------------
# Server-side only: GET /api/labs serves LABS, never these.

_MINI_DARK = DisplayConfig(model="miniled-32", brightness_pct=75, content="dark",
                           local_dimming=True, hub_laptop_w=0)
_EDGE_DARK = DisplayConfig(model="edge-27", brightness_pct=75, content="dark",
                           local_dimming=False, hub_laptop_w=0)
_EDGE_DOCK = DisplayConfig(model="edge-27", brightness_pct=67, content="bright",
                           local_dimming=False, hub_laptop_w=85)
_LONG_LIFE = _CONTROL_ROOM.model_copy(update={"service_years": 12})

REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    "dark-mode-that-pays": Scenario(config=_MINI_DARK, duration_s=300),
    "dock-cool-desk": Scenario(config=_EDGE_DOCK, duration_s=300),
    "greener-control-room": Scenario(
        config=_MINI_DARK, lifecycle=_LONG_LIFE, duration_s=300),
}

GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "dark-mode-that-pays": {
        "zero load": Scenario(
            config=_MINI_DARK.model_copy(update={"brightness_pct": 0}),
            duration_s=300),
        "dim the edge-lit panel": Scenario(
            config=_EDGE_DARK.model_copy(update={"brightness_pct": 40}),
            duration_s=300),
        "sleep through the run": Scenario(
            config=_EDGE_DARK.model_copy(update={"brightness_pct": 100}),
            events=[SimEvent(at_s=60, action="standby")], duration_s=300),
        "mini-LED with dimming off": Scenario(
            config=_MINI_DARK.model_copy(update={"local_dimming": False}),
            duration_s=300),
        "hdr for cheap light": Scenario(
            config=_MINI_DARK.model_copy(update={"content": "hdr"}),
            duration_s=300),
        "dark only at the end": Scenario(
            config=_MINI_DARK.model_copy(update={"content": "mixed"}),
            events=[SimEvent(at_s=299, action="set-content", content="dark")],
            duration_s=300),
        "short run": Scenario(config=_MINI_DARK, duration_s=10),
    },
    "dock-cool-desk": {
        "zero load": Scenario(
            config=_EDGE_DOCK.model_copy(update={"brightness_pct": 0}),
            duration_s=300),
        "undock the laptop": Scenario(
            config=_EDGE_DOCK.model_copy(update={"hub_laptop_w": 0}),
            duration_s=300),
        "dock at the last tick": Scenario(
            config=_EDGE_DOCK.model_copy(update={"hub_laptop_w": 0}),
            events=[SimEvent(at_s=299, action="hub-plug", value=90)],
            duration_s=300),
        "dark content on the zoned panel": Scenario(
            config=_MINI_DARK.model_copy(update={
                "brightness_pct": 100, "hub_laptop_w": 90}),
            duration_s=300),
        "sleep with the laptop charging": Scenario(
            config=_EDGE_DOCK.model_copy(update={"hub_laptop_w": 90}),
            events=[SimEvent(at_s=1, action="standby")], duration_s=300),
        "full charge at the floor": Scenario(
            config=_EDGE_DOCK.model_copy(update={"hub_laptop_w": 90}),
            duration_s=300),
        "short run": Scenario(config=_EDGE_DOCK, duration_s=10),
    },
    "greener-control-room": {
        "zero load": Scenario(
            config=_MINI_DARK.model_copy(update={"brightness_pct": 0}),
            lifecycle=_LONG_LIFE, duration_s=300),
        "clean the grid": Scenario(
            config=_EDGE_DARK,
            lifecycle=_LONG_LIFE.model_copy(update={"grid_kgco2_per_kwh": 0.05}),
            duration_s=300),
        "desk hours": Scenario(
            config=_EDGE_DARK,
            lifecycle=_LONG_LIFE.model_copy(update={"hours_per_day": 8}),
            duration_s=300),
        "short year": Scenario(
            config=_MINI_DARK,
            lifecycle=_LONG_LIFE.model_copy(update={"days_per_year": 100}),
            duration_s=300),
        "keep the edge-lit panel twelve years": Scenario(
            config=_EDGE_DARK, lifecycle=_LONG_LIFE, duration_s=300),
        "mini-LED on a six-year refresh": Scenario(
            config=_MINI_DARK, lifecycle=_CONTROL_ROOM, duration_s=300),
        "bright content": Scenario(
            config=_MINI_DARK.model_copy(update={"content": "mixed"}),
            lifecycle=_LONG_LIFE, duration_s=300),
        "sleep through the run": Scenario(
            config=_MINI_DARK, lifecycle=_LONG_LIFE,
            events=[SimEvent(at_s=30, action="standby")], duration_s=300),
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
