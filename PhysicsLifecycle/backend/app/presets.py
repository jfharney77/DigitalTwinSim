"""Presets and the teaching layer for the telecom & sustainability
simulator."""

from __future__ import annotations

from .leveling import L
from .models import (
    ConfigPreset,
    Explain,
    GuidedScenario,
    LifecycleConfig,
    Scenario,
    SimEvent,
)

# --- Config presets --------------------------------------------------------

BLOCKS = LifecycleConfig(
    product="telecomblocks", sites=100, deploy_mode="blocks",
    extended_temp=True, spare_capacity=True, remote_remediation=True,
)
DIY = BLOCKS.model_copy(update={"deploy_mode": "diy"})
STANDARD_TEMP = BLOCKS.model_copy(update={"extended_temp": False})
SERVICEABLE = LifecycleConfig(
    product="circulardesign", battery_replaceable=True, ram_socketed=True,
    chassis_recycled=True, ports_modular=True, grid="average",
    first_owner_years=4,
)
SEALED = SERVICEABLE.model_copy(update={
    "battery_replaceable": False, "ram_socketed": False,
    "ports_modular": False, "chassis_recycled": False,
})
COAL = SERVICEABLE.model_copy(update={"grid": "coal", "annual_kwh": 120})
CLEAN = SERVICEABLE.model_copy(update={"grid": "clean"})

CONFIG_PRESETS = [
    ConfigPreset(id="blocks", compare_preset_id="diy", name="Telecom · Blocks", config=BLOCKS,
                 blurb="Pre-validated bundles, XR-class, N+1 spares."),
    ConfigPreset(id="diy", name="Telecom · DIY", config=DIY,
                 blurb="The same network as an integration project."),
    ConfigPreset(id="standard-temp", name="Telecom · standard temp", config=STANDARD_TEMP,
                 blurb="Saved money on the spec sheet; meet the heatwave."),
    ConfigPreset(id="serviceable", compare_preset_id="sealed", name="Laptop · serviceable", config=SERVICEABLE,
                 blurb="Screwed, socketed, modular, recycled."),
    ConfigPreset(id="sealed", name="Laptop · sealed", config=SEALED,
                 blurb="Glued, soldered, integrated — the cascade."),
    ConfigPreset(id="coal-grid", name="Laptop · coal grid", config=COAL,
                 blurb="Where the use phase dominates the ledger."),
]

ROLLOUT = [
    SimEvent(at_d=10, action="deploy-sites", value=50),
    SimEvent(at_d=40, action="deploy-sites", value=50),
]

# --- Guided scenarios ------------------------------------------------------

GUIDED_SCENARIOS = [
    GuidedScenario(
        id="hundred-sites",
        title="Roll out 100 sites",
        narration=[
            L(
                novice=(
                    "One hundred cell sites go up in two waves — as "
                    "pre-validated blocks, each site a delivery rather "
                    "than a project. Note the hours in the log. Then "
                    "rerun on the DIY preset: the same hundred sites "
                    "cost roughly seven times the hours, and eight of "
                    "them simply fail their software-combination check "
                    "and go dark until someone untangles which version "
                    "of what disagreed with which. Nothing about the "
                    "hardware differed. The product being sold is the "
                    "absence of that untangling."
                ),
                standard=(
                    "The integration-effort model, run both ways: "
                    "Blocks at 1.5 h/site vs DIY at 10 h/site plus a "
                    "deterministic mismatch every 12th site (16 h and "
                    "an outage each — the A×B×C combination count "
                    "always lands on someone). The validation panel "
                    "quoted the bill before the run; the summary "
                    "settles it. Spec 08 calls this the product's "
                    "reason to exist, and the ledger agrees."
                ),
                expert=(
                    "1.5 vs 10 h/site; ⌊n/12⌋ mismatches × (16 h + "
                    "outage). The bundle sells the absence of the "
                    "matrix."
                ),
            ),
        ],
        question="What did 100 sites cost in hours and mismatches on each preset?",
        scenario=Scenario(config=BLOCKS, duration_d=120, events=ROLLOUT),
    ),
    GuidedScenario(
        id="heatwave",
        title="Heatwave",
        narration=[
            L(
                novice=(
                    "Day sixty: three days at 48 degrees. This fleet "
                    "bought extended-temperature hardware, and the log "
                    "records a non-event — every site rides it out. "
                    "Rerun on the standard-temp preset: nearly a third "
                    "of the fleet crosses its ceiling and goes dark, "
                    "the coverage map grays out, and tens of thousands "
                    "of subscribers learn what their carrier saved on "
                    "the spec sheet. Extended temperature range looks "
                    "like an accessory until the first hot week of the "
                    "decade."
                ),
                standard=(
                    "48 °C for 3 days against the two envelopes: "
                    "XR-class (ceiling ~55 °C, to verify) loses "
                    "nothing; standard (~40 °C) loses ~30% of sites "
                    "for the duration plus MTTR, and coverage — "
                    "counted in subscribers — dips accordingly. "
                    "Remote remediation vs truck rolls decides the "
                    "recovery tail. The env slider exists on every "
                    "Archetype-A app in this suite; here it is the "
                    "buying decision."
                ),
                expert=(
                    "48 °C: XR −0%, standard −30% × (72 h + MTTR). "
                    "Coverage in subscribers. The ambient slider, "
                    "weaponized by procurement."
                ),
            ),
        ],
        question="How many subscriber-hours did the standard-temp fleet lose that the XR fleet didn't?",
        scenario=Scenario(
            config=STANDARD_TEMP, duration_d=120,
            events=[SimEvent(at_d=60, action="heatwave", value=48)],
        ),
    ),
    GuidedScenario(
        id="friday-patch",
        title="The Friday-night patch",
        narration=[
            L(
                novice=(
                    "A software update must roll across the whole "
                    "network. With spare site capacity and bundles, "
                    "it proceeds like a wave — neighbors cover each "
                    "site as it updates, and the coverage line never "
                    "moves. Rerun without spares: the same update "
                    "becomes a week of brief per-site outages, felt "
                    "by subscribers as a flaky Friday. Five-nines "
                    "networks rarely die of failures; they die of "
                    "maintenance done without slack."
                ),
                standard=(
                    "The bundle-update event under both regimes: "
                    "Blocks + N+1 spares roll in 2 days with zero "
                    "coverage loss; no spares (or DIY) pays per-site "
                    "outage hours fleet-wide across a week. "
                    "Availability arithmetic is the same site-hours "
                    "honesty as everywhere in the suite — and "
                    "maintenance, not failure, is where the nines "
                    "leak."
                ),
                expert=(
                    "N+1 roll: 2 d, 0 loss. Piecemeal: 7 d, Σ per-"
                    "site outages. Nines leak at maintenance."
                ),
            ),
        ],
        question="Where did the availability difference come from — failures, or the update itself?",
        scenario=Scenario(
            config=BLOCKS, duration_d=120,
            events=[SimEvent(at_d=60, action="bundle-update")],
        ),
    ),
    GuidedScenario(
        id="sealed-vs-serviceable",
        title="Sealed vs serviceable, 8 years",
        narration=[
            L(
                novice=(
                    "Eight years happen to this laptop: a port breaks "
                    "in year two and a half, the battery fades at "
                    "three and a half, the memory falls short at four "
                    "and a half. This design opens with a screwdriver, "
                    "so each crisis costs a small part, and at "
                    "handoff it is refurbished for a second owner. "
                    "Rerun the sealed preset: each crisis becomes a "
                    "whole new machine, the e-waste scale climbs, and "
                    "the only honest scoreboard — carbon per useful "
                    "year — roughly doubles. The glue was a design "
                    "decision; so was everything that followed from "
                    "it."
                ),
                standard=(
                    "Spec 08's core A/B: the same scheduled events "
                    "resolve as parts (6–12 kgCO2e each) or as whole "
                    "devices (~280 kgCO2e embodied, again), and "
                    "refurb success — a function of the disassembly "
                    "score — decides whether the carbon amortizes "
                    "over a second life. The tests pin the ordering: "
                    "sealed consumes ≥2 devices and lands materially "
                    "higher on carbon per useful-year. The ledger "
                    "closes every tick; the figures are labeled "
                    "estimates pointing at Dell's PCF reports."
                ),
                expert=(
                    "Events → part|device; refurb = f(minutes). "
                    "Sealed: ≥2 devices, ~2× kg/useful-yr "
                    "(pinned). Ledger closes; PCF calibrates."
                ),
            ),
        ],
        question="What is each design's carbon per useful-year, and how many devices did eight years consume?",
        scenario=Scenario(config=SERVICEABLE, duration_d=2920),
    ),
    GuidedScenario(
        id="grid-matters",
        title="Grid matters",
        narration=[
            L(
                novice=(
                    "The same serviceable laptop, twice: plugged into "
                    "a clean grid, and into a coal-heavy one with "
                    "heavier use. On the clean grid, almost the whole "
                    "footprint is the factory — the day it was made "
                    "outweighs every day it runs. On the coal grid "
                    "the electricity overtakes manufacturing within "
                    "the device's life. Neither answer generalizes: "
                    "where the power comes from decides which half "
                    "of the ledger deserves your attention."
                ),
                standard=(
                    "Embodied vs use-phase split, decided by the "
                    "grid: at 0.05 kgCO2e/kWh the use phase never "
                    "approaches the ~246 kg embodied; at 0.85 with "
                    "120 kWh/yr it crosses within the run — both "
                    "directions asserted. Policy implication, stated "
                    "flat: on clean grids, repairability dominates "
                    "the footprint; on dirty ones, efficiency does."
                ),
                expert=(
                    "U = kWh·g·t vs E ≈ 246: clean never crosses, "
                    "coal does (both pinned). Clean → repair "
                    "matters; coal → watts do."
                ),
            ),
        ],
        question="On which grid does the use phase overtake embodied carbon — and when?",
        scenario=Scenario(config=COAL, duration_d=2920),
    ),
    GuidedScenario(
        id="battery-year",
        title="The battery year",
        narration=[
            L(
                novice=(
                    "Fast-forward to day 1,278 — three and a half "
                    "years in — and watch one event with two prices. "
                    "In this serviceable design, a technician fits a "
                    "new pack: twelve kilograms of carbon, a small "
                    "invoice, and the machine doesn't notice. In the "
                    "sealed rerun the same chemistry-driven fade "
                    "totals the device: nearly three hundred "
                    "kilograms and a new purchase, for want of four "
                    "screws. Batteries wear out on schedule; whether "
                    "that schedule is maintenance or mortality is "
                    "chosen at the drawing board."
                ),
                standard=(
                    "The year-3.5 fork isolated: battery wear at day "
                    "1,278 resolves as +12 kgCO2e (replaceable) or "
                    "+~246 kg embodied and a device count increment "
                    "(sealed). The log narrates both branches; the "
                    "TCO line keeps the money score alongside the "
                    "carbon one. Wear is deterministic chemistry — "
                    "the design decides whether it is an event or an "
                    "ending."
                ),
                expert=(
                    "Day 1278: +12 kg | +246 kg + device. Chemistry "
                    "schedules; design sentences."
                ),
            ),
        ],
        question="What did the same worn battery cost each design, in kilograms and dollars?",
        scenario=Scenario(config=SEALED, duration_d=1600),
    ),
]

# --- Explain-mode entries --------------------------------------------------

EXPLAINS = [
    Explain(
        id="matrix",
        title="Why compatibility matrices explode",
        equation="combinations = servers × OS builds × RAN versions;  bundles collapse it to 1",
        inputs=["versions per layer", "combinations", "mismatch rate", "hours"],
        explanation=L(
            novice=(
                "Three servers times four operating-system builds "
                "times five radio-software versions is sixty "
                "combinations — and somebody's site is always running "
                "the one nobody tested. Pre-validated bundles don't "
                "make the software better; they make the tested set "
                "and the deployed set the same set."
            ),
            standard=(
                "The A×B×C explosion the integration model prices: "
                "DIY validation samples the matrix per site and hits "
                "the untested cell deterministically (every 12th site "
                "here); a bundle pins one column and updates arrive "
                "as tested units. Spec 08 lists this equation as "
                "required explain content, and it is the whole "
                "product in one multiplication."
            ),
            expert=(
                "|A|·|B|·|C| cells, sites sample it → guaranteed "
                "misses. Bundle: 1 tested cell. The product is a "
                "projection."
            ),
        ),
    ),
    Explain(
        id="five-nines",
        title="Five nines at the edge",
        equation="availability = 1 − Σ site-outage-hours / (sites × hours)",
        inputs=["outage hours", "MTTR", "spares", "availability"],
        explanation=L(
            novice=(
                "99.999% allows about five minutes of downtime per "
                "site per year — which a single truck roll to a "
                "hilltop obliterates. The levers are boring and "
                "decisive: hardware that survives the weather, "
                "remote repair instead of a drive, and enough slack "
                "that maintenance isn't an outage."
            ),
            standard=(
                "Site-hours honesty: every outage source in this app "
                "is a named decision (temperature envelope, "
                "remediation mode, spare capacity, deployment mode's "
                "mismatches), so the availability figure decomposes "
                "into procurement choices. The heatwave and "
                "Friday-patch scenarios are the two big line items."
            ),
            expert=(
                "1 − Σout/(N·T); every term ← a config bit. Weather "
                "and maintenance, not failures, spend the nines."
            ),
        ),
    ),
    Explain(
        id="carbon-ledger",
        title="The carbon ledger",
        equation="total = Σ embodied + Σ use;  headline = total ÷ useful-years",
        inputs=["embodied", "use phase", "useful years", "kg per useful-year"],
        explanation=L(
            novice=(
                "Two columns: what it cost to make everything you "
                "ended up buying, and what it cost to run it. Divide "
                "by the years of service you actually got. That last "
                "division is the honest part — a device that died "
                "young makes its manufacturing carbon expensive per "
                "year no matter how efficient it was."
            ),
            standard=(
                "The closing identity (asserted every tick): total = "
                "cumulative embodied (device + parts + replacement "
                "cascades) + cumulative use (kWh × grid). The "
                "headline divides by useful years, which is what "
                "second lives buy and early shredding forfeits — "
                "the only metric on which sealed and serviceable "
                "designs can be compared without cheating."
            ),
            expert=(
                "Σᴱ + Σᵁ, closed per tick; ÷ useful-years. Longevity "
                "is a denominator play; the metric can't be gamed."
            ),
        ),
    ),
    Explain(
        id="embodied-vs-use",
        title="Embodied vs use phase",
        equation="crossover year = embodied ÷ (annual kWh × grid intensity)",
        inputs=["embodied kg", "annual kWh", "grid", "crossover"],
        explanation=L(
            novice=(
                "The factory emits once; the wall socket emits "
                "forever. Divide the factory's cost by a year of "
                "electricity's cost and you get the year the socket "
                "overtakes the factory — a handful of years on a "
                "coal grid, never within the device's life on a "
                "clean one. Which side deserves the engineering "
                "effort depends entirely on that division."
            ),
            standard=(
                "E ÷ (kWh × g): at 246 kg embodied and 60 kWh/yr, "
                "clean-grid use (3 kg/yr) never crosses; coal at "
                "120 kWh (102 kg/yr) crosses in year ~2.4. The "
                "grid-matters scenario runs both, and the policy "
                "corollary is stated in the overview: clean grids "
                "make repairability the lever, dirty ones make "
                "efficiency the lever."
            ),
            expert=(
                "t* = E/(kWh·g): ∞ on clean, ~2.4 y on coal here. "
                "The lever depends on the grid, not the laptop."
            ),
        ),
    ),
]
