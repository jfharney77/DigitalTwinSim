"""Graded labs for the telecom & sustainability simulator, following
``docs/LAB_PATTERN.md`` (pilot: ``DellPowerEdgeR760Thermal/backend/app/labs.py``).

A guided scenario sets the dials and narrates. A lab states a goal and leaves
the dials to the learner: build a Scenario with the ordinary controls, the
engine runs it, and ``grade_scenario`` scores the trace.

Pure module, same rule as ``engine.py``: no FastAPI, no IO, no clock, no
randomness (AST-checked in ``tests/test_labs.py``). ``main.py`` is the only
caller that touches HTTP, so the static build grades in the browser by running
this same file under Pyodide.

What is this app's own:

* ``measure()`` — one run as named numbers. Each product has a delivered-work
  rate averaged over the whole run with dark ticks counted as zero:
  ``meanSubscribersK`` (telecom: subscribers on air, a dark site serves
  nobody) and ``deliveredKwhPerYear`` (laptop: the owner's annual electricity
  use while the device is alive, a recycled device delivers nothing). Both are
  illustrative proxies for useful output and are labeled so.
* ``LABS`` — three labs of rising difficulty. Every criterion cites an Explain
  entry from ``presets.EXPLAINS`` and carries its equation verbatim.
* ``REFERENCE_SOLUTIONS`` / ``GAMING_ATTEMPTS`` — server-side only.

The engine is monotone in most dials (serviceable beats sealed, Blocks beats
DIY), so each lab is built on one of the places where it is not: update hours
scale with the fleet size at patch time, the embodied-vs-use crossover has to
be hit from both sides, and a sealed laptop gets worse per useful year the
longer it is kept.
"""

from __future__ import annotations

from twinkit.labs import Criterion, Lab, LabGoal, LabResult, Objective, grade

from .engine import simulate
from .leveling import L
from .models import (
    LifecycleConfig,
    Scenario,
    SimEvent,
    SimState,
    Summary,
    Validation,
)
from .presets import BLOCKS, EXPLAINS, SEALED, SERVICEABLE
from .validation import validate

# The equations, exactly as the Explain entries display them.
_EQ = {e.id: e.equation for e in EXPLAINS}
EQ_MATRIX = _EQ["matrix"]
EQ_NINES = _EQ["five-nines"]
EQ_LEDGER = _EQ["carbon-ledger"]
EQ_CROSS = _EQ["embodied-vs-use"]

#: Two update events closer together than this count as one patch cycle.
UPDATE_SPACING_D = 30
#: ``crossoverYear`` when use-phase carbon never overtakes embodied.
NEVER = 99.0


# --- Measurement ----------------------------------------------------------

def measure(
    scenario: Scenario,
    trace: list[SimState],
    summary: Summary,
    validations: list[Validation],
) -> dict[str, float]:
    """One run as named numbers. Keys are the wire names criteria refer to."""
    cfg = scenario.config
    telecom = cfg.product == "telecomblocks"
    n = len(trace)
    last = trace[-1]

    # Telecom. Replay the event list the way the engine does: sorted by day,
    # nothing after the last tick counts.
    events = sorted(scenario.events, key=lambda e: e.at_d)
    updates = 0
    last_update = -10 ** 9
    for ev in events:
        if not telecom or ev.at_d > last.t_d:
            continue
        if ev.action == "bundle-update" and ev.at_d - last_update >= UPDATE_SPACING_D:
            updates += 1
            last_update = ev.at_d
    density = max(
        (s.subscribers_served_k / s.sites_up for s in trace if s.sites_up > 0),
        default=0.0,
    )

    # Circular. The first day use-phase carbon has caught up with embodied.
    cross_day = next(
        (s.t_d for s in trace
         if s.t_d > 0 and s.use_kg_cum > 0 and s.use_kg_cum >= s.embodied_kg_cum),
        None,
    )
    alive_days = sum(1 for s in trace if s.device_alive) if not telecom else 0

    return {
        "durationD": float(last.t_d),
        "validationErrors": float(sum(1 for v in validations if v.level == "error")),
        # Telecom.
        "meanSubscribersK": round(sum(s.subscribers_served_k for s in trace) / n, 1),
        "availabilityPct": float(summary.availability_pct) if telecom else 0.0,
        "minCoveragePct": float(summary.min_coverage_pct) if telecom else 0.0,
        "sitesDeployed": float(last.sites_total - cfg.sites) if telecom else 0.0,
        "peakAmbientC": round(max(s.ambient_c for s in trace), 1) if telecom else 0.0,
        "updatesRolled": float(updates),
        "maxSubscribersPerSiteK": round(density, 1),
        "integrationHours": float(summary.integration_hours),
        "mismatchEvents": float(summary.mismatch_events),
        # Circular Design.
        "deliveredKwhPerYear": round(cfg.annual_kwh * alive_days / n, 1),
        "carbonPerUsefulYear": float(summary.carbon_per_useful_year),
        "crossoverYear": round(cross_day / 365.0, 2) if cross_day is not None else NEVER,
        "disassemblyMinutes": float(last.disassembly_minutes) if not telecom else 0.0,
        "usefulYears": float(last.useful_years) if not telecom else 0.0,
        "devicesConsumed": float(summary.devices_consumed),
    }


# --- Criteria shared between labs ------------------------------------------

def _full_run(days: int, explain_id: str, equation: str) -> Criterion:
    years = days // 365
    span = f"{days} days" if days < 365 else f"{days} days ({years} years)"
    return Criterion(
        id="full-run", label=f"Run covers at least {days} days",
        metric="durationD", op=">=", threshold=days, unit="d",
        explain_id=explain_id, equation=equation,
        why=L(
            standard=(
                f"The run must cover {span}. Both headline numbers here are "
                "ratios over time, so a shorter run is a different question, "
                "not a better answer. The lab's start sets this length; Reset "
                "to the lab's start restores it."
            ),
            novice=(
                f"The run has to last the whole {span}. The numbers this lab "
                "grades are averages over time, so stopping early would not "
                "be a cleverer answer, it would be an answer to a different "
                "question. The lab sets this length for you when it opens. "
                "If it changes, press Reset to the lab's start to get it back."
            ),
            expert=f"durationD ≥ {days}; the graded ratios are time-averaged.",
        ),
    )


def _kwh_work(floor: int) -> Criterion:
    return Criterion(
        id="work", label=f"Delivered use at least {floor} kWh/yr over the run",
        metric="deliveredKwhPerYear", op=">=", threshold=floor, unit="kWh/yr",
        weight=2.0, guards_work=True, explain_id="embodied-vs-use", equation=EQ_CROSS,
        why=L(
            standard=(
                f"Delivered work is the owner's annual electricity use, counted "
                f"only on days the laptop is alive and averaged over the whole "
                f"run; the floor is {floor} kWh/yr. A laptop nobody uses has a "
                "tiny use phase and teaches nothing, and a recycled laptop "
                "delivers zero from that day on. Electricity used is an "
                "illustrative stand-in for useful computing, not a benchmark."
            ),
            novice=(
                f"The laptop has to be genuinely used: at least {floor} "
                "kilowatt-hours of electricity a year, averaged over the whole "
                "run. We only count days when the laptop is still working. "
                "Once it has been sent for recycling it counts as zero for "
                "every day after that. This closes the easy way out, which "
                "would be a laptop that sits in a drawer and so never uses "
                "any electricity. Electricity used is a simple stand-in for "
                "useful work done, not a real measurement of it."
            ),
            expert=(
                f"Mean over all ticks of annual kWh × alive; dead ticks zero; "
                f"floor {floor} kWh/yr. Illustrative proxy."
            ),
        ),
    )


# --- Lab 1: the outage budget ------------------------------------------------

_BUDGET_EVENTS = [
    SimEvent(at_d=10, action="deploy-sites", value=50),
    SimEvent(at_d=40, action="deploy-sites", value=50),
    SimEvent(at_d=60, action="heatwave", value=48),
    SimEvent(at_d=70, action="bundle-update"),
    SimEvent(at_d=100, action="bundle-update"),
]

_BUDGET_START = Scenario(
    config=BLOCKS.model_copy(update={
        "deploy_mode": "diy", "extended_temp": False, "spare_capacity": False,
    }),
    duration_d=120, events=_BUDGET_EVENTS,
)

OUTAGE_BUDGET = Lab(
    id="outage-budget",
    title="Spend the outage budget",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "Grow a 100-site network by 100 more sites in 120 days, ride "
                "out a 45 °C+ heatwave, patch the fleet twice, and still end "
                "at five nines (99.999%) availability. Then spend as few "
                "integration hours as you can."
            ),
            novice=(
                "You run a mobile network of 100 cell sites. In the next 120 "
                "days you have to add 100 more sites, get through a heatwave "
                "of 45 °C or hotter, and update the software on every site "
                "twice. At the end the network must still have been working "
                "99.999% of the time, which people call five nines. Once you "
                "can do that, try to do it with as few hours of engineering "
                "work (integration hours) as you can."
            ),
            expert=(
                "+100 sites in 120 d, ≥45 °C heatwave, 2 patch cycles, "
                "availability ≥ 99.999%; minimize integration hours."
            ),
        ),
        constraints=[
            L(standard="Deploy at least 100 new sites during the run; sites that exist on day 0 do not count.",
              novice="Add at least 100 new sites while the run is going, using the Deploy 50 sites button. Sites the network already had on day 0 do not count toward the 100.",
              expert="sitesDeployed ≥ 100 (events only; the day-0 fleet is excluded)."),
            L(standard="A heatwave of at least 45 °C must happen during the run.",
              novice="A heatwave of at least 45 °C has to happen at some point in the run. The Heatwave 48 °C button adds one on the day the timeline is showing.",
              expert="peakAmbientC ≥ 45."),
            L(standard="Roll at least 2 updates, 30 or more days apart.",
              novice="Update the fleet's software at least 2 times, with 30 or more days between the updates. Two updates in the same month count as one.",
              expert="updatesRolled ≥ 2 at ≥ 30 d spacing."),
            L(standard="No more than 20 thousand subscribers per site: the towns are the size they are.",
              novice="Each site can serve at most 20 thousand subscribers. You do not get to decide how many people live near a tower.",
              expert="maxSubscribersPerSiteK ≤ 20."),
            L(standard="The run covers at least 120 days.",
              novice="The run has to last at least 120 days. The lab sets this for you.",
              expert="durationD ≥ 120."),
        ],
        delivered_work=L(
            standard=(
                "Work is subscribers on air, averaged over every day of the "
                "run: at least 3400 thousand. A dark site serves nobody. "
                "Illustrative proxy."
            ),
            novice=(
                "Work here means people with a working phone signal, averaged "
                "over every day of the run. You need at least 3400 thousand. "
                "A site that has gone dark serves nobody, so it adds nothing. "
                "This is a simple stand-in for a network's useful output."
            ),
            expert="Mean subscribers served ≥ 3400 k over all ticks; dark sites zero. Illustrative.",
        ),
    ),
    criteria=[
        Criterion(
            id="work", label="Subscribers on air average at least 3400 k",
            metric="meanSubscribersK", op=">=", threshold=3400, unit="k",
            weight=2.0, guards_work=True, explain_id="five-nines", equation=EQ_NINES,
            why=L(
                standard=(
                    "Work is subscribers served, averaged over every day of "
                    "the run; the floor is 3400 thousand, about 170 sites on "
                    "air at 20 thousand each. A dark site counts as zero and a "
                    "site deployed late earns only for the days it exists, so "
                    "a tiny network or a last-day rollout does not pass. The "
                    "proxy is illustrative."
                ),
                novice=(
                    "We count how many people have a working signal on each "
                    "day and take the average over the whole run. You need at "
                    "least 3400 thousand, which is about 170 sites on air with "
                    "20 thousand people each. A site that is dark counts as "
                    "zero. A site you add late only counts for the days after "
                    "you add it. So a very small network, or adding all the "
                    "sites on the last day, will not pass. This is a simple "
                    "stand-in for useful output, not a real measurement."
                ),
                expert="Mean subscribers served over all ticks ≥ 3400 k; dark or undeployed sites earn zero. Illustrative.",
            ),
        ),
        Criterion(
            id="five-nines", label="Availability at least 99.999%",
            metric="availabilityPct", op=">=", threshold=99.999, unit="%",
            weight=2.0, explain_id="five-nines", equation=EQ_NINES,
            why=L(
                standard=(
                    "Five nines is a budget. About 180 sites × 24 h × 120 days "
                    "is roughly 520000 site-hours, and 0.001% of that is about "
                    "5 site-hours of outage for the whole run. One DIY version "
                    "mismatch costs 8. One piecemeal update costs 0.5 h at "
                    "every site, about 100. A heatwave on standard-temperature "
                    "hardware costs thousands. Any one of them overspends the "
                    "budget by itself."
                ),
                novice=(
                    "Five nines sounds like a quality, but it is really a "
                    "budget of allowed downtime. Add up every site for every "
                    "hour of the 120 days and you get roughly 520000 "
                    "site-hours. You are allowed to lose 0.001% of that, which "
                    "is only about 5 site-hours in the whole run. Now look at "
                    "what things cost. One software-combination failure on a "
                    "DIY site costs 8 site-hours. An update without spare "
                    "capacity takes every site down for 0.5 hours, about 100 "
                    "site-hours. A heatwave on ordinary hardware costs "
                    "thousands. Any single one of these spends more than the "
                    "whole budget."
                ),
                expert="Budget ≈ 1e-5 × ~520000 site-h ≈ 5 site-h. Mismatch 8, piecemeal update 0.5 × sites, standard-temp heatwave 0.3 × sites × 76: each alone overspends.",
            ),
        ),
        Criterion(
            id="growth", label="At least 100 sites deployed during the run",
            metric="sitesDeployed", op=">=", threshold=100, unit="sites",
            explain_id="matrix", equation=EQ_MATRIX,
            why=L(
                standard=(
                    "Growth is measured as sites added by deploy events. Those "
                    "are the sites that pay integration hours: 1.5 h each as a "
                    "validated bundle, 10 h each as DIY plus a version "
                    "mismatch on every 12th site. A bigger day-0 fleet is not "
                    "growth."
                ),
                novice=(
                    "We count the sites you add during the run with the Deploy "
                    "button. Those are the ones that cost engineering hours. "
                    "As a pre-tested bundle a site costs 1.5 hours. Built "
                    "DIY, where your team checks every hardware and software "
                    "combination itself, a site costs 10 hours, and every 12th "
                    "site fails its check. Starting with a bigger network on "
                    "day 0 does not count as growing it."
                ),
                expert="Final − day-0 site count ≥ 100. Deploys pay 1.5 h (bundle) or 10 h + ⌊n/12⌋ mismatches (DIY).",
            ),
        ),
        Criterion(
            id="heatwave", label="A heatwave of at least 45 °C happens",
            metric="peakAmbientC", op=">=", threshold=45, unit="°C",
            explain_id="five-nines", equation=EQ_NINES,
            why=L(
                standard=(
                    "The weather is not a dial. The peak ambient in the trace "
                    "must reach 45 °C. Standard-temperature hardware has a "
                    "40 °C ceiling (estimate) and loses 30% of sites for three "
                    "days plus repair time; extended-temperature hardware is "
                    "rated to 55 °C and loses none."
                ),
                novice=(
                    "You do not get to skip the hot week. Somewhere in the run "
                    "the outside temperature has to reach 45 °C. Ordinary "
                    "hardware stops working above about 40 °C (an estimate), "
                    "and 30% of the sites go dark for three days plus the time "
                    "to repair them. Extended-temperature hardware is built "
                    "for up to 55 °C and loses nothing. If you pressed Reset "
                    "and the heatwave disappeared, add it again with the "
                    "Heatwave 48 °C button."
                ),
                expert="max ambient ≥ 45 °C. Standard ceiling 40 °C (est.) → 0.3 × sites × (72 h + MTTR); XR-class 55 °C → 0.",
            ),
        ),
        Criterion(
            id="patched", label="At least 2 updates, 30 or more days apart",
            metric="updatesRolled", op=">=", threshold=2, unit="updates",
            explain_id="five-nines", equation=EQ_NINES,
            why=L(
                standard=(
                    "A network that never patches keeps its nines by skipping "
                    "the maintenance, so the lab requires 2 patch cycles at "
                    "least 30 days apart. With N+1 spare capacity on validated "
                    "bundles an update costs no outage and 0.1 h per site. "
                    "Without spares it costs 0.5 h of outage at every site."
                ),
                novice=(
                    "Never updating would keep the network up, but that is "
                    "cheating: real networks have to be patched. So you must "
                    "update 2 times, at least 30 days apart. With spare "
                    "capacity (N+1, meaning one site more than you need so a "
                    "neighbour can cover) on pre-tested bundles, an update "
                    "takes no site off air and costs 0.1 hours of work per "
                    "site. Without spare capacity every site goes off air for "
                    "0.5 hours."
                ),
                expert="≥ 2 bundle-update events at ≥ 30 d spacing. Blocks + N+1: 0 outage, 0.1 h/site; otherwise 0.5 site-h outage per site.",
            ),
        ),
        Criterion(
            id="density", label="At most 20 k subscribers per site",
            metric="maxSubscribersPerSiteK", op="<=", threshold=20, unit="k/site",
            explain_id="five-nines", equation=EQ_NINES,
            why=L(
                standard=(
                    "Subscribers per site is read back from the trace and "
                    "capped at 20 thousand. Raising it would lift the work "
                    "number without building anything."
                ),
                novice=(
                    "We check how many subscribers each site served, and the "
                    "limit is 20 thousand. Turning that number up would make "
                    "the network look busier without you building a single "
                    "new site, so it does not count."
                ),
                expert="max(subscribers ÷ sites up) ≤ 20 k, measured from the trace.",
            ),
        ),
        _full_run(120, "five-nines", EQ_NINES),
    ],
    objective=Objective(
        label="Integration hours", metric="integrationHours",
        direction="minimize", par=180, worst=200, unit="h",
        explain_id="matrix", equation=EQ_MATRIX,
    ),
    hints=[
        L(standard="Work out the outage budget first: 0.001% of about 180 sites × 24 h × 120 days. Then price each line of the event log against it.",
          novice="Start by working out how much downtime you are allowed. Multiply about 180 sites by 24 hours by 120 days, then take 0.001% of that. Then read the event log and see how many site-hours each bad event cost you.",
          expert="Budget ≈ 5 site-h. Price the log against it."),
        L(standard="Three dials each overspend the budget alone: DIY (8 h per mismatch), standard temperature (30% of sites for 76 h), and no spare capacity (0.5 h at every site per update). All three have to go.",
          novice="Three of the choices in the Build-out panel each break the budget by themselves. DIY integration costs 8 site-hours every time a site fails its check. Standard temperature hardware loses 30% of sites for 76 hours in the heatwave. No spare capacity costs 0.5 hours at every site for each update. You need to fix all three, not just one.",
          expert="DIY, standard temp and no N+1 are each individually fatal to 99.999%."),
        L(standard="With every criterion met, look at what an update costs: 0.1 h × the sites that exist that day. The first patch is cheaper before the fleet doubles. Press Reset, scrub the timeline to an early day, and add the events in a better order.",
          novice="Once everything passes, look at the hours. An update costs 0.1 hours for every site that exists on the day you roll it. So the first update is cheaper if you do it while the network is still 100 sites, before you add the new ones. Press Reset to clear the events, drag the timeline to an early day, press Roll an update, then move forward and add the deployments, the heatwave and the second update.",
          expert="Update hours = 0.1 × sites at patch time: patch, then grow. 180 h beats 190 h."),
    ],
    start=_BUDGET_START.model_dump(by_alias=True),
)


# --- Lab 2: the crossover window ---------------------------------------------

_CROSS_START = Scenario(config=SERVICEABLE, duration_d=2920)

CROSSOVER_WINDOW = Lab(
    id="crossover-window",
    title="Find the crossover window",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "A brochure says a laptop's footprint is mostly the "
                "electricity it uses. Build the 8-year lifecycle where that "
                "is true by year 6, for a laptop that is genuinely used, "
                "without carbon per useful-year going above 85 kg. Then push "
                "carbon per useful-year as low as the window allows."
            ),
            novice=(
                "A brochure claims that most of a laptop's carbon footprint "
                "comes from the electricity it uses, not from making it. Your "
                "job is to find the laptop and owner for which that is true: "
                "by year 6 of an 8-year life, the carbon from electricity "
                "(use-phase carbon) must have caught up with the carbon from "
                "manufacturing (embodied carbon). The laptop must be properly "
                "used, and its carbon per useful-year must stay at or below "
                "85 kg. When you have found it, make carbon per useful-year "
                "as low as you can."
            ),
            expert=(
                "Use ≥ embodied by year 6 over 8 y, delivered use ≥ 100 kWh/yr, "
                "carbon per useful-year ≤ 85 kg; then minimize it."
            ),
        ),
        constraints=[
            L(standard="Use-phase carbon overtakes embodied carbon by year 6.",
              novice="By the end of year 6, the carbon from electricity must be at least as big as the carbon from manufacturing and spare parts.",
              expert="crossoverYear ≤ 6."),
            L(standard="Carbon per useful-year ends at 85 kg or less.",
              novice="At the end of the 8 years, total carbon divided by the years the laptop was useful must be 85 kg or less.",
              expert="carbonPerUsefulYear ≤ 85 kg."),
            L(standard="The run covers the full 2920 days (8 years).",
              novice="The run has to cover the full 2920 days, which is 8 years. The lab sets this for you.",
              expert="durationD ≥ 2920."),
        ],
        delivered_work=L(
            standard=(
                "Work is the owner's annual electricity use while the laptop "
                "is alive, averaged over all 8 years: at least 100 kWh/yr. "
                "Illustrative proxy for useful computing."
            ),
            novice=(
                "Work here means the laptop is really being used. We measure "
                "that by the electricity it uses in a year, counted only while "
                "the laptop is still working and averaged over all 8 years. "
                "You need at least 100 kWh a year. It is a simple stand-in for "
                "useful computing."
            ),
            expert="Mean annual kWh × alive over all ticks ≥ 100. Illustrative.",
        ),
    ),
    criteria=[
        _kwh_work(100),
        Criterion(
            id="crossover", label="Use-phase overtakes embodied by year 6",
            metric="crossoverYear", op="<=", threshold=6, unit="y",
            weight=2.0, explain_id="embodied-vs-use", equation=EQ_CROSS,
            why=L(
                standard=(
                    "The crossover year is embodied carbon divided by the "
                    "use-phase rate, annual kWh × grid intensity. To land it "
                    "by year 6 the rate has to be at least a sixth of "
                    "everything embodied, including each spare part and each "
                    "replacement device. A sealed design adds a whole device "
                    "at every mid-life event, so its crossover never comes. "
                    "A value of 99 means it never happened in the run."
                ),
                novice=(
                    "Making the laptop releases a lump of carbon on day one. "
                    "That is embodied carbon. Using it releases a little more "
                    "every day. That is use-phase carbon. The crossover year "
                    "is when the daily trickle has added up to the lump. You "
                    "find it by dividing the embodied carbon by the carbon "
                    "released per year of use, and carbon per year of use is "
                    "the annual kWh times how dirty the grid is. To cross "
                    "over by year 6, a year of use has to release at least "
                    "one sixth of the embodied carbon. Spare parts and "
                    "replacement laptops add to the lump, so a sealed design "
                    "that needs a whole new laptop at each failure never "
                    "crosses over. If you see 99 here, it never happened."
                ),
                expert="First day use ≥ embodied, ÷ 365; needs kWh × g ≥ Σ embodied ÷ 6. Replacement devices push it out of reach. 99 = never.",
            ),
        ),
        Criterion(
            id="footprint", label="Carbon per useful-year at most 85 kg",
            metric="carbonPerUsefulYear", op="<=", threshold=85, unit="kg/y",
            weight=2.0, explain_id="carbon-ledger", equation=EQ_LEDGER,
            why=L(
                standard=(
                    "The headline is total carbon divided by useful years. "
                    "The cheap way to an early crossover is a dirty grid and "
                    "heavy use, and the ledger charges for it: every kg/yr of "
                    "use-phase lands in this number one for one. The cap of "
                    "85 kg leaves room for an embodied share of about 34 kg/yr "
                    "and a use-phase rate of about 51, and no more."
                ),
                novice=(
                    "The headline number is all the carbon, from making the "
                    "laptop and from using it, divided by the years it was "
                    "useful. The easy way to make electricity the bigger share "
                    "is a dirty grid and lots of use, but every extra kg of "
                    "carbon from electricity also goes straight into this "
                    "number. The limit of 85 kg leaves room for about 34 kg a "
                    "year from manufacturing and parts, plus about 51 kg a "
                    "year from electricity, and nothing more."
                ),
                expert="(Σ embodied + Σ use) ÷ useful-years ≤ 85: about 34 embodied + at most 51 use per year.",
            ),
        ),
        _full_run(2920, "carbon-ledger", EQ_LEDGER),
    ],
    objective=Objective(
        label="Carbon per useful-year", metric="carbonPerUsefulYear",
        direction="minimize", par=79.6, worst=85, unit="kg/y",
        explain_id="carbon-ledger", equation=EQ_LEDGER,
    ),
    hints=[
        L(standard="Open Explain mode on the embodied-vs-use entry. The crossover year is a division, and you control three of its terms: what is embodied, the annual kWh, and the grid.",
          novice="Turn on Explain mode and read the entry about embodied versus use. The crossover year is one number divided by another. You control three things in it: how much carbon goes into making the laptop and its parts, how many kWh it uses a year, and which grid it is plugged into.",
          expert="crossover = embodied ÷ (kWh × g). Three of its terms are yours."),
        L(standard="The two criteria squeeze the use-phase rate from both sides. It has to be at least embodied ÷ 6 to cross over in time, and at most 85 minus the embodied share to stay under the cap. A coal grid at 100 kWh overshoots; a clean grid never gets there.",
          novice="The two main criteria pull in opposite directions. To cross over by year 6, a year of electricity has to release at least one sixth of the embodied carbon. To stay under 85 kg, a year of electricity cannot release more than 85 minus the yearly share of embodied carbon. On a coal grid, 100 kWh a year is already too much. On a clean grid you never get enough. So it has to be the grid in the middle.",
          expert="embodied ÷ 6 ≤ kWh × g ≤ 85 − embodied ÷ 8. Coal overshoots at 100 kWh; clean never crosses."),
        L(standard="Make the numerator small so the window opens: every serviceable choice and the recycled chassis, about 272 kg embodied over the life. Then 272 ÷ 6 is about 45 kg/yr, which on the mixed grid (0.35) is 130 kWh. Virgin aluminum moves the window past the cap.",
          novice="Make the embodied carbon as small as you can, because that lowers both walls of the window. Choose the replaceable battery, socketed RAM, modular ports and the recycled chassis. That comes to about 272 kg over the life. Divide by 6 years and you need about 45 kg a year from electricity. On the mixed grid (0.35 kg per kWh) that is 130 kWh a year. With a virgin aluminum chassis the embodied carbon is higher, and the use you would need pushes the total over 85.",
          expert="All serviceable + recycled: ~272 kg → ≥ 45 kg/yr → 130 kWh at 0.35. Virgin chassis closes the window."),
    ],
    start=_CROSS_START.model_dump(by_alias=True),
)


# --- Lab 3: the fleet you cannot redesign ------------------------------------

_SEALED_START = Scenario(config=SEALED, duration_d=2920)

SEALED_FLEET = Lab(
    id="sealed-fleet",
    title="The fleet you cannot redesign",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "The laptops are already bought: glued battery, soldered RAM, "
                "integrated ports. You still choose the chassis material, the "
                "grid, how hard the laptop is used and how long the first "
                "owner keeps it. Over an 8-year window, get carbon per "
                "useful-year to 180 kg or less while delivering real use, "
                "then lower it as far as it goes."
            ),
            novice=(
                "Your company has already bought sealed laptops. The battery "
                "is glued in, the memory (RAM) is soldered to the board and "
                "the ports are part of the main board, so none of them can be "
                "replaced by themselves. You cannot change that. You can "
                "still choose what the case is made of, which electricity "
                "grid the laptop runs on, how much it is used, and how many "
                "years the first owner keeps it. Looking at an 8-year window, "
                "get carbon per useful-year down to 180 kg or less while the "
                "laptop is genuinely used. Then get it as low as it will go."
            ),
            expert=(
                "Sealed design locked. 8-year window, delivered use ≥ 60 kWh/yr, "
                "carbon per useful-year ≤ 180 kg; minimize."
            ),
        ),
        constraints=[
            L(standard="The design stays sealed: disassembly time 45 minutes, no replaceable battery, socketed RAM or modular ports.",
              novice="The design has to stay sealed. That shows up as a disassembly time of 45 minutes. If you switch on a replaceable battery, socketed RAM or modular ports, the time drops and this line fails.",
              expert="disassemblyMinutes ≥ 45 (zero serviceable choices)."),
            L(standard="The window covers the full 2920 days (8 years), including any years after the laptop is recycled.",
              novice="The run has to cover the full 2920 days, which is 8 years. That includes any years after the laptop has been recycled, when it delivers nothing.",
              expert="durationD ≥ 2920, dead years included."),
        ],
        delivered_work=L(
            standard=(
                "Work is annual electricity use while the laptop is alive, "
                "averaged over all 8 years with recycled years counted as "
                "zero: at least 60 kWh/yr. Illustrative proxy."
            ),
            novice=(
                "Work means the laptop is really being used, measured by the "
                "electricity it uses in a year. We average over all 8 years, "
                "and every year after the laptop is recycled counts as zero. "
                "You need at least 60 kWh a year on that average. It is a "
                "simple stand-in for useful computing."
            ),
            expert="Mean annual kWh × alive over all ticks ≥ 60; dead years zero. Illustrative.",
        ),
    ),
    criteria=[
        _kwh_work(60),
        Criterion(
            id="sealed", label="The design stays sealed (45 min disassembly)",
            metric="disassemblyMinutes", op=">=", threshold=45, unit="min",
            explain_id="carbon-ledger", equation=EQ_LEDGER,
            why=L(
                standard=(
                    "The purchase is the constraint, so it is measured: a "
                    "fully sealed design reads 45 minutes of disassembly in "
                    "the trace, and any serviceable choice lowers it. With "
                    "zero serviceable choices the refurbishment odds are 35%, "
                    "below the 50% needed for a second life, so the laptop is "
                    "recycled when the first owner is done."
                ),
                novice=(
                    "This lab is about laptops you have already bought, so we "
                    "check that you did not quietly swap them for better ones. "
                    "A fully sealed laptop takes 45 minutes to take apart. Any "
                    "replaceable part makes that shorter and fails this line. "
                    "A sealed laptop has only a 35% chance of being "
                    "refurbished for a second owner. The simulator needs 50%, "
                    "so this laptop is recycled as soon as its first owner is "
                    "finished with it."
                ),
                expert="45 min ⇔ zero serviceable choices ⇒ refurb odds 35% < 50% ⇒ recycled at handoff.",
            ),
        ),
        Criterion(
            id="footprint", label="Carbon per useful-year at most 180 kg",
            metric="carbonPerUsefulYear", op="<=", threshold=180, unit="kg/y",
            weight=2.0, explain_id="carbon-ledger", equation=EQ_LEDGER,
            why=L(
                standard=(
                    "Total carbon divided by useful years. On a sealed design "
                    "each scheduled failure (port at day 912, battery at day "
                    "1278, RAM at day 1642) adds a whole device to the top of "
                    "the fraction, while keeping the laptop a year longer adds "
                    "only one year to the bottom. Three years means 2 devices, "
                    "four means 3, five means 4: about 164, 185 and 197 kg/yr "
                    "of embodied carbon alone with a recycled chassis."
                ),
                novice=(
                    "The headline number is all the carbon divided by the "
                    "years the laptop was useful. Normally keeping a laptop "
                    "longer makes this number better. On a sealed laptop it "
                    "does not. The port fails around day 912, the battery "
                    "wears out around day 1278 and the RAM runs short around "
                    "day 1642, and each time the only fix is a whole new "
                    "laptop. So keeping it 3 years uses 2 laptops, 4 years "
                    "uses 3, and 5 years uses 4. With a recycled chassis "
                    "that is about 164, 185 and 197 kg a year from "
                    "manufacturing alone. Each extra year adds one year to "
                    "the bottom of the fraction and a whole laptop to the top."
                ),
                expert="Sealed: devices = 1 + events before handoff. fo 3/4/5 y → 2/3/4 devices → ~164/185/197 kg/yr embodied (recycled chassis).",
            ),
        ),
        _full_run(2920, "carbon-ledger", EQ_LEDGER),
    ],
    objective=Objective(
        label="Carbon per useful-year", metric="carbonPerUsefulYear",
        direction="minimize", par=172.3, worst=180, unit="kg/y",
        explain_id="carbon-ledger", equation=EQ_LEDGER,
    ),
    hints=[
        L(standard="Run the start and read the event log. Count the whole-device replacements and note the day of each one against the day the first owner is done.",
          novice="Run the lab as it opens and read the event log. Count how many times it says a whole new device was needed, and write down the day of each. Compare those days with the day the first owner hands the laptop back.",
          expert="Count replacement events before the handoff day."),
        L(standard="Keeping a sealed laptop longer is the instinct and it is wrong here: each extra first-owner year walks into the next scheduled failure. But a short life leaves dead years in the 8-year window, and they count as zero work.",
          novice="Your instinct is probably to keep the laptop longer. On a sealed laptop that backfires, because each extra year runs into the next part failure and costs a whole new laptop. But there is a catch in the other direction. If the laptop is recycled early, the rest of the 8 years count as zero work, so the years it is alive have to make up for them.",
          expert="Longer ownership adds devices faster than years; shorter ownership adds zero-work years."),
        L(standard="First owner 3 years, recycled chassis, clean grid. Three live years out of eight means the use has to be 160 kWh/yr to average 60, and on a clean grid that costs only 8 kg/yr. The result, about 172, is still more than double what the serviceable laptop in the previous lab manages.",
          novice="Set the first owner to 3 years, choose the recycled chassis and the clean grid. The laptop is then alive for 3 of the 8 years, so to average 60 kWh a year it has to use 160 kWh a year while it is alive. On the clean grid that only costs 8 kg of carbon a year. You end at about 172 kg per useful year. Notice that this best case is still more than double what the serviceable laptop in the previous lab manages. The real lever was the design.",
          expert="fo = 3 y, recycled, clean, 160 kWh → 172.3 kg/yr; still > 2× the serviceable result. The lever was the design."),
    ],
    start=_SEALED_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [OUTAGE_BUDGET, CROSSOVER_WINDOW, SEALED_FLEET]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Reference solutions and the tricks that must not work -----------------
# Server-side only: GET /api/labs serves LABS, never these.

_PATCH_THEN_GROW = [
    SimEvent(at_d=1, action="bundle-update"),
    SimEvent(at_d=2, action="deploy-sites", value=50),
    SimEvent(at_d=3, action="deploy-sites", value=50),
    SimEvent(at_d=60, action="heatwave", value=48),
    SimEvent(at_d=90, action="bundle-update"),
]

_WINDOW = SERVICEABLE.model_copy(update={"annual_kwh": 130})
_EARLY_CLEAN = SEALED.model_copy(update={
    "first_owner_years": 3, "chassis_recycled": True, "grid": "clean",
    "annual_kwh": 160,
})

REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    "outage-budget": Scenario(config=BLOCKS, duration_d=120, events=_PATCH_THEN_GROW),
    "crossover-window": Scenario(config=_WINDOW, duration_d=2920),
    "sealed-fleet": Scenario(config=_EARLY_CLEAN, duration_d=2920),
}


def _cfg(base: LifecycleConfig, **update: object) -> LifecycleConfig:
    return base.model_copy(update=update)


GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "outage-budget": {
        "zero load": Scenario(
            config=_cfg(BLOCKS, sites=10, subscribers_per_site_k=1),
            duration_d=120, events=_PATCH_THEN_GROW),
        "skip the heatwave": Scenario(
            config=_cfg(BLOCKS, extended_temp=False), duration_d=120,
            events=[e for e in _PATCH_THEN_GROW if e.action != "heatwave"]),
        "a mild heatwave": Scenario(
            config=_cfg(BLOCKS, extended_temp=False), duration_d=120,
            events=[e if e.action != "heatwave" else
                    SimEvent(at_d=60, action="heatwave", value=39)
                    for e in _PATCH_THEN_GROW]),
        "never patch": Scenario(
            config=_cfg(BLOCKS, spare_capacity=False), duration_d=120,
            events=[e for e in _PATCH_THEN_GROW if e.action != "bundle-update"]),
        "two patches in one week": Scenario(
            config=BLOCKS, duration_d=120,
            events=[SimEvent(at_d=1, action="bundle-update"),
                    SimEvent(at_d=4, action="bundle-update"),
                    SimEvent(at_d=5, action="deploy-sites", value=100),
                    SimEvent(at_d=60, action="heatwave", value=48)]),
        "a bigger day-0 fleet instead of growth": Scenario(
            config=_cfg(BLOCKS, sites=200), duration_d=120,
            events=[e for e in _PATCH_THEN_GROW if e.action != "deploy-sites"]),
        "dense towns on a small network": Scenario(
            config=_cfg(BLOCKS, sites=10, subscribers_per_site_k=100),
            duration_d=120, events=_PATCH_THEN_GROW),
        "deploy on the last day": Scenario(
            config=BLOCKS, duration_d=120,
            events=[SimEvent(at_d=1, action="bundle-update"),
                    SimEvent(at_d=60, action="heatwave", value=48),
                    SimEvent(at_d=90, action="bundle-update"),
                    SimEvent(at_d=120, action="deploy-sites", value=100)]),
        "short run": Scenario(
            config=BLOCKS, duration_d=30,
            events=[SimEvent(at_d=1, action="deploy-sites", value=100),
                    SimEvent(at_d=2, action="heatwave", value=48)]),
        "diy with everything else right": Scenario(
            config=_cfg(BLOCKS, deploy_mode="diy"), duration_d=120,
            events=_PATCH_THEN_GROW),
        "no spare capacity": Scenario(
            config=_cfg(BLOCKS, spare_capacity=False), duration_d=120,
            events=_PATCH_THEN_GROW),
        "the wrong product": Scenario(config=_WINDOW, duration_d=2920),
    },
    "crossover-window": {
        "zero load": Scenario(config=_cfg(SERVICEABLE, annual_kwh=20, grid="coal"),
                              duration_d=2920),
        "coal and heavy use": Scenario(
            config=_cfg(SERVICEABLE, annual_kwh=200, grid="coal"), duration_d=2920),
        "coal and light use": Scenario(
            config=_cfg(SERVICEABLE, annual_kwh=60, grid="coal"), duration_d=2920),
        "clean grid": Scenario(
            config=_cfg(SERVICEABLE, annual_kwh=200, grid="clean"), duration_d=2920),
        "virgin chassis": Scenario(
            config=_cfg(SERVICEABLE, annual_kwh=140, chassis_recycled=False),
            duration_d=2920),
        "sealed design": Scenario(
            config=_cfg(SEALED, annual_kwh=130, chassis_recycled=True),
            duration_d=2920),
        "short run": Scenario(config=_WINDOW, duration_d=365),
        "the wrong product": Scenario(config=BLOCKS, duration_d=2920),
    },
    "sealed-fleet": {
        "zero load": Scenario(
            config=_cfg(_EARLY_CLEAN, annual_kwh=20), duration_d=2920),
        "keep it longer": Scenario(
            config=_cfg(_EARLY_CLEAN, first_owner_years=5, annual_kwh=100),
            duration_d=2920),
        "stop the run at the handoff": Scenario(config=_EARLY_CLEAN, duration_d=1095),
        "swap in one screw": Scenario(
            config=_cfg(_EARLY_CLEAN, ports_modular=True, annual_kwh=60),
            duration_d=2920),
        "the serviceable laptop": Scenario(config=SERVICEABLE, duration_d=2920),
        "light use on three live years": Scenario(
            config=_cfg(_EARLY_CLEAN, annual_kwh=100), duration_d=2920),
        "virgin chassis": Scenario(
            config=_cfg(_EARLY_CLEAN, chassis_recycled=False), duration_d=2920),
        "the wrong product": Scenario(config=BLOCKS, duration_d=2920),
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
