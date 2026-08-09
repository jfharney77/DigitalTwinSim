"""Presets and the teaching layer — backend data.

Config presets, guided scenarios (scripted walkthroughs that set the
scenario and narrate what to watch), and Explain-mode entries (the
equation behind each key readout, with placeholders the frontend
substitutes with live values). Explain and scenario prose carries
reading levels — the natural authoring surface in a twin whose trace
states are numbers rather than sentences.
"""

from __future__ import annotations

from .leveling import L
from .models import (
    ConfigPreset,
    Environment,
    Explain,
    GuidedScenario,
    RackConfig,
    RackLoad,
    Scenario,
    SimEvent,
)


def _loads(*specs: tuple[str, float, str]) -> list[RackLoad]:
    """Eight slots; unspecified slots are 0 W empties on phase C."""
    out = [RackLoad(label=lbl, power_w=w, phase=p) for lbl, w, p in specs]  # type: ignore[arg-type]
    while len(out) < 8:
        out.append(RackLoad(label=f"Empty {len(out) + 1}", power_w=0, phase="C"))
    return out


# --- Config presets ---------------------------------------------------------

BALANCED = RackConfig(
    loads=_loads(
        ("Web 1", 300, "A"), ("Web 2", 300, "B"), ("DB 1", 400, "C"),
        ("DB 2", 400, "A"), ("App 1", 300, "B"), ("App 2", 300, "C"),
    ),
    breaker_amps=16, ups_chemistry="vrla", ups_nameplate_wh=2000,
    ups_age_years=1,
)

LOPSIDED = RackConfig(
    loads=_loads(
        ("Web 1", 300, "A"), ("Web 2", 300, "A"), ("DB 1", 400, "A"),
        ("DB 2", 400, "A"), ("App 1", 300, "A"), ("App 2", 300, "A"),
    ),
    breaker_amps=16, ups_chemistry="vrla", ups_nameplate_wh=2000,
    ups_age_years=1,
)

OLD_BATTERIES = RackConfig(
    loads=_loads(
        ("Web 1", 300, "A"), ("Web 2", 300, "B"), ("DB 1", 400, "C"),
        ("DB 2", 400, "A"), ("App 1", 300, "B"), ("App 2", 300, "C"),
    ),
    breaker_amps=16, ups_chemistry="vrla", ups_nameplate_wh=500,
    ups_age_years=4,
)

HEAVY_PHASE = RackConfig(
    loads=_loads(
        ("GPU 1", 800, "A"), ("GPU 2", 800, "A"), ("GPU 3", 800, "A"),
        ("GPU 4", 800, "A"),
    ),
    breaker_amps=16, ups_chemistry="lithium", ups_nameplate_wh=2000,
    ups_age_years=1,
)

LITHIUM_AGED = RackConfig(
    loads=_loads(
        ("Web 1", 300, "A"), ("Web 2", 300, "B"), ("DB 1", 400, "C"),
        ("DB 2", 400, "A"), ("App 1", 300, "B"), ("App 2", 300, "C"),
    ),
    breaker_amps=16, ups_chemistry="lithium", ups_nameplate_wh=500,
    ups_age_years=4,
)

CONFIG_PRESETS = [
    ConfigPreset(
        id="balanced", name="Balanced rack", config=BALANCED,
        blurb="Six servers spread 2/2/2 across the phases — the tidy baseline.",
    ),
    ConfigPreset(
        id="lopsided", name="Lopsided rack", config=LOPSIDED,
        blurb="The same six servers, all on phase A — the convenient-outlet rack.",
    ),
    ConfigPreset(
        id="old-batteries", name="4-year-old batteries", config=OLD_BATTERIES,
        blurb="A balanced rack on a small VRLA pack that has quietly aged.",
    ),
    ConfigPreset(
        id="heavy-phase", name="One heavy phase", config=HEAVY_PHASE,
        blurb="Four 800 W GPU boxes on one 16 A feed — 89% of the breaker.",
    ),
]

# --- Guided scenarios ---------------------------------------------------------

GUIDED_SCENARIOS = [
    GuidedScenario(
        id="balance-the-phases",
        title="Balance the phases",
        narration=[
            L(
                novice=(
                    "Every server in this rack was plugged into the same "
                    "electrical feed — phase A — because that outlet strip "
                    "was closest. Nothing is broken: the total power is "
                    "well within what the rack can supply. But watch the "
                    "three bar meters. Phase A is working hard while B and "
                    "C sit empty, which means one breaker carries "
                    "everything and the other two protect nothing. Over "
                    "the next few minutes the servers are moved, one at a "
                    "time, onto the empty feeds. The imbalance number "
                    "falls, the meters even out, and the total never "
                    "changes — moving a load never creates or destroys a "
                    "watt."
                ),
                standard=(
                    "Six servers, all on phase A. At t=120, 150, and 180 s "
                    "loads move to phases B and C. Watch the imbalance "
                    "readout collapse and the per-phase meters converge "
                    "while total PDU input stays flat — conservation "
                    "across the moves is asserted in the tests. Balance "
                    "buys headroom: the same rack now sits three breakers "
                    "wide instead of leaning on one."
                ),
                expert=(
                    "All-on-A → staged moves to B/C at t=120/150/180. "
                    "Imbalance → ~0, ΣP constant. Headroom per breaker "
                    "triples; nothing else changes."
                ),
            ),
        ],
        question=(
            "After the last move, how many watts of headroom does phase A "
            "have that it lacked at t=0?"
        ),
        scenario=Scenario(
            config=LOPSIDED, environment=Environment(), duration_s=600,
            events=[
                SimEvent(at_s=120, action="move-load", index=1, phase="B"),
                SimEvent(at_s=120, action="move-load", index=2, phase="C"),
                SimEvent(at_s=150, action="move-load", index=4, phase="B"),
                SimEvent(at_s=180, action="move-load", index=5, phase="C"),
            ],
        ),
    ),
    GuidedScenario(
        id="old-batteries",
        title="The 4-year-old batteries",
        narration=[
            L(
                novice=(
                    "The building power fails one minute in. The UPS "
                    "display has been promising about fifteen minutes of "
                    "battery — plenty of time for a graceful shutdown. "
                    "But the batteries are four years old, and lead-acid "
                    "batteries quietly lose capacity every year they sit "
                    "on the shelf. The display never noticed, because a "
                    "prediction based on the battery's original size "
                    "cannot see fade. Watch the two runtime numbers: the "
                    "promised one and the real one. The rack goes dark "
                    "when the real one runs out — a quarter earlier than "
                    "promised. This is the classic outage post-mortem, "
                    "simulated."
                ),
                standard=(
                    "Utility fails at t=60. The front panel predicts "
                    "runtime from nameplate watt-hours; the engine "
                    "discharges the faded pack (VRLA, 4 years at 25 °C "
                    "→ 76% of nameplate under the fade model). The rack "
                    "goes dark at roughly three-quarters of the promised "
                    "runtime — the ratio between the two numbers is "
                    "exactly the capacity fraction, and the acceptance "
                    "test asserts it."
                ),
                expert=(
                    "Fail at t=60. Panel predicts from nameplate; engine "
                    "discharges 0.76 × nameplate (VRLA, 4 y, 25 °C). "
                    "Actual/predicted = capacity fraction. Dark at ~76% "
                    "of promise."
                ),
            ),
        ],
        question=(
            "The prediction missed by what fraction — and what single "
            "maintenance action would have corrected it?"
        ),
        scenario=Scenario(
            config=OLD_BATTERIES, environment=Environment(), duration_s=900,
            events=[SimEvent(at_s=60, action="utility-fail")],
        ),
    ),
    GuidedScenario(
        id="self-test-truth",
        title="The self-test that told the truth",
        narration=[
            L(
                novice=(
                    "Same rack, same tired four-year-old batteries — but "
                    "this time the UPS runs its periodic self-test before "
                    "anything goes wrong. A self-test briefly runs the "
                    "rack from the battery and measures what the battery "
                    "actually delivers. The moment it finishes, the "
                    "runtime prediction drops to the honest number. When "
                    "the building power fails a minute later, the display "
                    "and reality agree: less time than you would like, "
                    "but no surprise. The battery is just as faded as in "
                    "the previous scenario — the only thing that changed "
                    "is that somebody measured."
                ),
                standard=(
                    "Identical to the previous scenario, plus a self-test "
                    "at t=30. The test transfers to battery for ten "
                    "seconds, measures capacity at 76% of nameplate, and "
                    "corrects the prediction — so when the utility fails "
                    "at t=60 the predicted and actual runtimes agree. "
                    "The fade did not change; the knowledge did."
                ),
                expert=(
                    "Prior scenario + self-test at t=30. Prediction "
                    "switches to faded Wh; predicted ≈ actual through "
                    "the outage. Measurement, not maintenance."
                ),
            ),
        ],
        question=(
            "The battery is equally faded in both scenarios — what, "
            "precisely, did the self-test change?"
        ),
        scenario=Scenario(
            config=OLD_BATTERIES, environment=Environment(), duration_s=900,
            events=[
                SimEvent(at_s=30, action="self-test"),
                SimEvent(at_s=60, action="utility-fail"),
            ],
        ),
    ),
    GuidedScenario(
        id="breaker-math",
        title="Breaker math",
        narration=[
            L(
                novice=(
                    "Four GPU servers share one 16-amp feed, drawing "
                    "about 89% of what the breaker allows. The validation "
                    "panel is already unhappy: the electrical code says a "
                    "circuit loaded continuously should stay under 80%. "
                    "Two minutes in, the servers start a training job and "
                    "their draw rises past the breaker's rating. Nothing "
                    "happens immediately — breakers tolerate brief "
                    "overloads — but heat accumulates inside the breaker "
                    "on a curve, and about a minute later it trips. Every "
                    "server on the phase goes dark at once. The breaker "
                    "did its job; the planning failed weeks earlier."
                ),
                standard=(
                    "Four 800 W boxes on one 16 A phase: 89% of rating — "
                    "past the NEC 80% continuous line, so the panel warns "
                    "at t=0. At t=120 the loads step to 1,200 W each "
                    "(133% of rating). The simplified I²t curve "
                    "accumulates (overload²−1) per second and trips "
                    "roughly 80 seconds later, dropping the whole phase. "
                    "Warn, don't block — then simulate the consequence."
                ),
                expert=(
                    "4×800 W on A (89% of 16 A) → warn. t=120: 4×1,200 W "
                    "(133%). I²t: (1.33²−1)·t ≥ 60 → trip ≈ t+78 s. "
                    "Phase dark; B/C untouched."
                ),
            ),
        ],
        question=(
            "Reading the trip curve backwards: at 110% of rating, roughly "
            "how long would the breaker have held?"
        ),
        scenario=Scenario(
            config=HEAVY_PHASE, environment=Environment(), duration_s=600,
            events=[
                SimEvent(at_s=120, action="set-load", index=0, value=1200),
                SimEvent(at_s=120, action="set-load", index=1, value=1200),
                SimEvent(at_s=120, action="set-load", index=2, value=1200),
                SimEvent(at_s=120, action="set-load", index=3, value=1200),
            ],
        ),
    ),
    GuidedScenario(
        id="chemistry-choice",
        title="Lithium ages differently",
        narration=[
            L(
                novice=(
                    "This is the four-year-old-battery outage again, with "
                    "one change: the battery is lithium instead of "
                    "lead-acid. Four years of aging cost this pack only a "
                    "small slice of its capacity, so the optimistic "
                    "display and the honest battery nearly agree, and the "
                    "rack rides out most of the promised time. Lead-acid "
                    "is cheaper on the day you buy it; lithium is often "
                    "cheaper over the years you own it — and this "
                    "difference in how they age is most of the reason."
                ),
                standard=(
                    "The old-batteries scenario re-run on lithium: 4 "
                    "years at 25 °C costs ~8% under the fade model "
                    "(versus 24% for VRLA), so predicted and actual "
                    "runtime nearly coincide without any self-test. Flip "
                    "the room to 35 °C and re-run both chemistries: VRLA "
                    "aging doubles; lithium barely notices."
                ),
                expert=(
                    "Same outage, Li pack: 4 y → ~0.92 capacity vs "
                    "VRLA's 0.76. Temp doubling 20 °C vs 10 °C. "
                    "Prediction error shrinks to noise."
                ),
            ),
        ],
        question=(
            "At a 35 °C room, what capacity fraction does the fade model "
            "give each chemistry after the same four years?"
        ),
        scenario=Scenario(
            config=LITHIUM_AGED, environment=Environment(), duration_s=900,
            events=[SimEvent(at_s=60, action="utility-fail")],
        ),
    ),
]

# --- Explain-mode entries -------------------------------------------------------

EXPLAINS = [
    Explain(
        id="phase-current",
        title="Phase current",
        equation="I = P ÷ (V × PF)",
        inputs=["phase watts", "phase voltage", "power factor"],
        explanation=L(
            novice=(
                "Breakers care about current (amps), not power (watts). "
                "To get amps, divide the watts flowing on the phase by "
                "the voltage, times a correction called power factor "
                "that is nearly 1 for modern servers. This is the number "
                "the bar meters compare against the breaker rating."
            ),
            standard=(
                "The breaker trips on current, so every phase meter "
                "converts watts to amps: I = P ÷ (V × PF). Modern server "
                "PSUs with active power-factor correction hold PF near "
                "0.98, so at 230 V each amp carries about 225 W."
            ),
            expert="I = P/(V·PF); PF≈0.98 (active PFC), 230 V L-N.",
        ),
    ),
    Explain(
        id="imbalance",
        title="Phase imbalance",
        equation="imbalance = max|P_phase − avg| ÷ avg × 100",
        inputs=["phase A watts", "phase B watts", "phase C watts"],
        explanation=L(
            novice=(
                "Add the three phases, divide by three to get the "
                "average, and see how far the worst phase strays from "
                "it. Zero means perfectly even; big numbers mean one "
                "feed does the work while the others watch."
            ),
            standard=(
                "Max deviation of any phase from the three-phase "
                "average, as a percentage of that average. High "
                "imbalance wastes breaker headroom — the heaviest phase "
                "hits its limit while capacity idles on the others."
            ),
            expert="max|P_φ − P̄|/P̄. Headroom is per-phase; imbalance strands it.",
        ),
    ),
    Explain(
        id="breaker-trip",
        title="Breaker trip curve",
        equation="heat += (I/I_rated)² − 1 per second → trips at threshold",
        inputs=["phase amps", "breaker rating", "seconds of overload"],
        explanation=L(
            novice=(
                "A breaker does not trip the instant you exceed its "
                "rating — it heats up on a curve. A small overload takes "
                "minutes to trip; double the rating takes seconds; a "
                "short circuit trips instantly. The simulator uses a "
                "simplified version of this curve, so how long an "
                "overload survives depends on how big it is."
            ),
            standard=(
                "Simplified thermal-magnetic model: while I > rating, "
                "thermal 'heat' accumulates as (overload² − 1) per "
                "second and the breaker trips when it crosses the "
                "threshold; ≥5× rating trips magnetically, instantly. "
                "At 110% that is minutes, at 133% about 80 seconds."
            ),
            expert=(
                "I²t: ∫(I/I_r)²−1 dt ≥ K → trip; magnetic at 5×. "
                "K=60 here (estimate)."
            ),
        ),
    ),
    Explain(
        id="runtime",
        title="UPS runtime",
        equation="runtime = Wh_usable × η_inverter ÷ P_load × 60",
        inputs=["battery watt-hours", "inverter efficiency", "rack load watts"],
        explanation=L(
            novice=(
                "Battery runtime is division: the energy in the battery, "
                "times the ~93% the inverter delivers, divided by the "
                "watts the rack is drawing. The catch is which "
                "watt-hours you divide — the number on the label, or the "
                "number four years of aging left behind. The display "
                "uses the label until a self-test measures the truth."
            ),
            standard=(
                "Runtime = usable Wh × η_inv ÷ load W. The front panel "
                "substitutes nameplate Wh until a self-test has measured "
                "the faded pack; the engine always discharges the faded "
                "Wh. The predicted/actual gap is therefore exactly the "
                "capacity fraction — arithmetic, not mystery."
            ),
            expert=(
                "t = Wh·η/P. Panel: nameplate (or measured post-test); "
                "engine: faded. Gap ratio = capacity fraction."
            ),
        ),
    ),
    Explain(
        id="fade",
        title="Battery fade",
        equation="capacity = 1 − rate × age × 2^((T−25) ÷ T_double)",
        inputs=["chemistry fade rate", "age in years", "room temperature"],
        explanation=L(
            novice=(
                "Batteries lose capacity every year even if never used, "
                "and heat speeds the loss. For lead-acid (VRLA), every "
                "10 °C above a 25 °C room roughly doubles the aging "
                "rate; lithium loses less per year and cares less about "
                "heat. The model multiplies the yearly loss by an aging "
                "clock that runs faster in a hot room."
            ),
            standard=(
                "Linear fade per equivalent year, with the clock "
                "accelerated exponentially by room temperature: VRLA "
                "~6%/year doubling per +10 °C; lithium ~2%/year "
                "doubling per +20 °C. Both rates are estimates anchored "
                "to industry service-life rules of thumb."
            ),
            expert=(
                "cap = max(floor, 1 − r·a·2^((T−25)/ΔT)); VRLA r=0.06 "
                "ΔT=10, Li r=0.02 ΔT=20 (estimates)."
            ),
        ),
    ),
    Explain(
        id="wall-power",
        title="Wall draw",
        equation="AC input = PDU input ÷ η_passthrough + charger",
        inputs=["PDU input watts", "pass-through efficiency", "charger watts"],
        explanation=L(
            novice=(
                "While the building power is up, the UPS mostly passes "
                "it straight through, losing about 2% on the way, and "
                "adds a couple of hundred watts if it is recharging the "
                "battery. When the building power fails, the wall number "
                "drops to zero and the battery pays instead — through "
                "the less-efficient inverter path."
            ),
            standard=(
                "On utility: AC = PDU ÷ 0.98 + charger draw. On "
                "battery: AC = 0 and battery output × 0.93 = PDU input "
                "— the conservation identity the tests assert on every "
                "tick of both regimes."
            ),
            expert=(
                "Utility: AC = P/η_pass + P_chg. Battery: P_batt·η_inv "
                "= P. Asserted per tick."
            ),
        ),
    ),
]
