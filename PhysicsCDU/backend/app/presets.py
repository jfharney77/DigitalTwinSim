"""Presets and the teaching layer — backend data.

Config presets, workload presets, guided scenarios (scripted
walkthroughs that set the scenario and narrate what to watch), and
Explain-mode entries (the equation behind each key readout, substituted
with live values in the UI). Teaching prose carries reading levels.
"""

from __future__ import annotations

from .leveling import L
from .models import (
    CduConfig,
    ConfigPreset,
    Environment,
    Explain,
    GuidedScenario,
    Scenario,
    SimEvent,
    Workload,
    WorkloadPreset,
)

# --- Config presets ---------------------------------------------------------

HALF_RACK = CduConfig(tray_groups=3, pumps=3)
STANDARD = CduConfig(tray_groups=5, pumps=3)
FULL_RACK = CduConfig(tray_groups=6, pumps=3)
NO_SPARE = CduConfig(tray_groups=5, pumps=2)
PANIC = CduConfig(tray_groups=6, pumps=3, policy="uncoordinated")

CONFIG_PRESETS = [
    ConfigPreset(id="half-rack", name="Half rack", config=HALF_RACK,
                 blurb="3 tray banks (~120 kW) — the CDU loafs."),
    ConfigPreset(id="standard", name="Standard", config=STANDARD,
                 blurb="5 banks (~200 kW), N+1 pumps — the balanced build."),
    ConfigPreset(id="full-rack", name="Full rack", config=FULL_RACK,
                 blurb="6 banks (~240 kW) — past the 220 kW class; the IRC earns its keep."),
    ConfigPreset(id="no-spare", name="No spare pump", config=NO_SPARE,
                 blurb="5 banks on N pumps — one failure from a derate."),
    ConfigPreset(id="uncoordinated", name="Uncoordinated", config=PANIC,
                 blurb="Full rack with the IRC's policy switched off — every tray for itself."),
]

# --- Workload presets ---------------------------------------------------------

FULL_TILT = Workload(util_pct=100)
STEADY = Workload(util_pct=60)
IDLE = Workload(util_pct=10)

WORKLOAD_PRESETS = [
    WorkloadPreset(id="full", name="Training (100%)", workload=FULL_TILT),
    WorkloadPreset(id="steady", name="Inference (60%)", workload=STEADY),
    WorkloadPreset(id="idle", name="Idle (10%)", workload=IDLE),
]

# --- Guided scenarios ---------------------------------------------------------

GUIDED_SCENARIOS = [
    GuidedScenario(
        id="size-the-cdu",
        title="Size the CDU",
        narration=[
            L(
                novice=(
                    "The rack starts half full and gains a bank of "
                    "computers every three minutes. Each bank adds about "
                    "40 kW of heat, and for a long time nothing "
                    "interesting happens — the loop just runs a little "
                    "warmer each time. Then the sixth bank arrives and "
                    "something new appears: the controller starts "
                    "slowing the computers down, because the heat "
                    "exchanger in the middle has run out of capacity. "
                    "That moment — the load at which a cooling box "
                    "stops being invisible — is what 'sizing a CDU' "
                    "means."
                ),
                standard=(
                    "Banks land at t=180, 360, and 540, taking the rack "
                    "from 3 to 6 (~240 kW worst case against a 220 kW-"
                    "class CDU). Watch the chain: each bank raises the "
                    "approach (heat Q divided by UA, the exchanger's "
                    "heat-transfer capacity), the approach raises the "
                    "coolant supply, "
                    "the supply raises the silicon — linearly, until "
                    "the silicon meets the IRC's target and the cap "
                    "gauge dips below 100%. The heat the loop settles "
                    "at right there is the CDU's real capacity for this "
                    "facility temperature, and it lands near the "
                    "nameplate."
                ),
                expert=(
                    "+40 kW at 180/360/540. Chip rises linearly in Q "
                    "via approach + ΔT/2; cap engages when chip hits "
                    "target. Settled Q at cap < 1 ≈ capacity at this "
                    "T_fac ≈ nameplate. Sizing, observed."
                ),
            ),
        ],
        question="How many kilowatts is the loop actually moving once the cap gauge settles below 100%?",
        answer=(
            "About 235 kW, with the caps settled near 98%. That is a "
            "little above the 220 kW nameplate, because the facility "
            "water here is a cool 17 °C. The figures are this model's."
        ),
        scenario=Scenario(
            config=HALF_RACK, workload=FULL_TILT, environment=Environment(),
            duration_s=1200,
            events=[
                SimEvent(at_s=180, action="add-tray-group"),
                SimEvent(at_s=360, action="add-tray-group"),
                SimEvent(at_s=540, action="add-tray-group"),
            ],
        ),
    ),
    GuidedScenario(
        id="warm-water-day",
        title="Warm water day (coordinated)",
        narration=[
            L(
                novice=(
                    "For the first few minutes nothing is wrong: the rack "
                    "has just been switched on, and the temperatures you "
                    "see racing up are everything warming to its normal "
                    "running level. This full rack makes slightly more "
                    "heat than the cooling box is built for, so around "
                    "the four-minute mark the rack controller already "
                    "slows the computers a touch, to about 98% of full "
                    "speed. Note the 'heat moved' reading once it "
                    "settles, near 235 kW. Then, seven minutes in, the "
                    "building's water arrives six degrees warmer — say a "
                    "heat wave, or the building's cooling plant has a "
                    "fault. From that moment nothing in the rack "
                    "changes, but every temperature downstream must "
                    "shift up by the same six degrees, and the chips "
                    "don't have six degrees to give. Watch the "
                    "controller respond: it trims every bank's power a "
                    "little, together, and the whole rack glides down to "
                    "what the warm water can carry. Every computer stays "
                    "up. None shuts itself off. The cost is about an "
                    "eighth of the rack's speed, paid evenly."
                ),
                standard=(
                    "A full six-bank rack (~240 kW) on a 220 kW-class "
                    "CDU, started cold. The first minutes are warm-up: "
                    "coolant supply and silicon climb to their running "
                    "temperatures, and because this rack sits slightly "
                    "over the CDU's class, the IRC (Integrated Rack "
                    "Controller) already trims the power caps to about "
                    "98% near t=223, settling around 235 kW. At t=420 "
                    "the facility supply steps 17 → 23 °C. The "
                    "temperature chain reacts in order: facility supply, "
                    "then coolant supply (one loop time-constant, about "
                    "a minute, behind), then silicon. The IRC meets the "
                    "silicon at its target and shaves the caps until the "
                    "heat matches the water: they dip to about 80% and "
                    "settle near 85%, spread across every bank. Zero "
                    "trips; the banks-online chart never moves. Compare "
                    "this run against 'Warm water day (panic)' — same "
                    "physics, opposite policy."
                ),
                expert=(
                    "6 banks, cold start; baseline already caps ≈98% "
                    "(≈235 kW, rack > class) by t≈223. T_fac +6 K at "
                    "t=420. Supply lags τ≈60 s, chip meets target, caps "
                    "settle ≈85% (≈205 kW) uniformly. Trips = 0. Diff "
                    "against the uncoordinated run: same plant, "
                    "different controller, different day."
                ),
            ),
        ],
        question=(
            "Read 'heat moved' just before t+420 s and again at the end: "
            "how many kilowatts did six degrees of facility water cost "
            "this rack?"
        ),
        answer=(
            "About 30 kW. Heat moved settles near 235 kW before the warm "
            "water arrives and near 205 kW after it, with all six banks "
            "online throughout. That is less than one 40 kW bank. The "
            "figures are this model's, not measurements."
        ),
        scenario=Scenario(
            config=FULL_RACK, workload=FULL_TILT, environment=Environment(),
            duration_s=1200,
            events=[SimEvent(at_s=420, action="set-facility-supply", value=23)],
        ),
    ),
    GuidedScenario(
        id="warm-water-panic",
        title="Warm water day (panic)",
        narration=[
            L(
                novice=(
                    "The same warm-water afternoon — the rack warms up "
                    "for a few minutes, then the building's water turns "
                    "six degrees warmer at the seven-minute mark. This "
                    "time the rack controller is switched off (its "
                    "speed-limit readout says 'off'), and each bank of "
                    "computers protects only itself. Watch what "
                    "independence buys: the chips warm past their "
                    "safety line, and one bank shuts itself off. The "
                    "loop is slow, so the others stay hot for a while — "
                    "and they start shutting off too, one after another, "
                    "even though the first had already freed enough "
                    "heat. When it's over, more computers are dark than "
                    "the warm water ever required. One caution: in this "
                    "model a bank has only two states, full speed or "
                    "off. Real computers also slow themselves down "
                    "before they shut off, so read this run as the "
                    "worst case."
                ),
                standard=(
                    "Identical to the coordinated run — six banks, "
                    "+6 °C at t=420 — but the IRC's policy is off, so "
                    "the cap readout shows 'off' and every bank rides "
                    "its own firmware trip at 65 °C. The silicon crosses "
                    "the trip line and the first bank latches off near "
                    "t=454; the loop's 60 s time constant keeps the "
                    "survivors hot long after the heat dropped, so "
                    "their trip timers keep running and two more banks "
                    "follow. All banks share one silicon reading here, "
                    "so the 5 s spacing between trips is a modeled "
                    "stand-in for position and part-to-part spread, not "
                    "something the map can show. At the end compare "
                    "'energy delivered' and 'banks online' with the "
                    "coordinated run: about 55 kWh against 72 kWh. Read "
                    "it as the worst case. Tray protection here is "
                    "trip-only; real trays throttle their own clocks "
                    "before a hard trip, so an uncoordinated rack in "
                    "practice slows unevenly and late rather than "
                    "always cascading. What the run does show is the "
                    "mechanism: loop lag makes independent protection "
                    "over-correct."
                ),
                expert=(
                    "Same disturbance, no coordination. First trip at "
                    "the sustain threshold (t≈454); τ_loop keeps "
                    "survivors above trip → the imposed 5 s stagger "
                    "cascades to 3 banks, 120 kW shed against the "
                    "≈30 kW the step required. Delivered ≈55 vs ≈72 "
                    "kWh. Caveat: trip-only tray protection, no local "
                    "throttling modeled — a worst case, not a proof."
                ),
            ),
        ],
        question="How many banks tripped — and how many did the heat actually require?",
        answer=(
            "Three banks tripped, taking 120 kW offline. In the "
            "coordinated run the same warm water cost about 30 kW, less "
            "than one 40 kW bank, so the cascade shed about four times "
            "what the heat required. Energy delivered by the end: about "
            "55 kWh here against about 72 kWh coordinated. The figures "
            "are this model's, and the trip-only trays make this the "
            "worst case."
        ),
        scenario=Scenario(
            config=PANIC, workload=FULL_TILT, environment=Environment(),
            duration_s=1200,
            events=[SimEvent(at_s=420, action="set-facility-supply", value=23)],
        ),
    ),
    GuidedScenario(
        id="one-pump-down",
        title="One pump down (N+1)",
        narration=[
            L(
                novice=(
                    "Three pumps share the loop, and only two are "
                    "really needed — the third is the spare you hope "
                    "never matters. Five minutes in, one dies. The "
                    "survivors speed up, the flow barely dips, and the "
                    "computers never notice. That non-event is what "
                    "redundancy is for: you paid for a pump whose job "
                    "is to make a failure boring."
                ),
                standard=(
                    "N+1 pumps at ~200 kW; pump 1 fails at t=300. The "
                    "survivors ramp to 100% and deliver ~97% of the "
                    "flow setpoint — parallel pumps on a shared system "
                    "curve overlap, so two pumps were always most of "
                    "the flow. The approach widens a fraction of a "
                    "kelvin, the silicon barely moves, and the caps "
                    "never engage. Now run 'No spare pump' and watch "
                    "the same failure with N instead of N+1."
                ),
                expert=(
                    "3→2 pumps at t=300: Q(2)/setpoint ≈ 0.97 "
                    "(k^0.65 overlap), ff barely moves, chip Δ < 1 K, "
                    "cap = 1 throughout. Redundancy = a boring "
                    "failure."
                ),
            ),
        ],
        question="How much flow did the failure actually cost, in percent?",
        answer=(
            "About 3%. Coolant flow goes from 340 L/min to about "
            "330 L/min, and the caps stay at 100%."
        ),
        scenario=Scenario(
            config=STANDARD, workload=FULL_TILT, environment=Environment(),
            duration_s=700,
            events=[SimEvent(at_s=300, action="fail-pump", index=0)],
        ),
    ),
    GuidedScenario(
        id="no-spare",
        title="No spare pump",
        narration=[
            L(
                novice=(
                    "The same failure as before — one pump dies at five "
                    "minutes — but this loop only had two to begin "
                    "with. Now the single survivor can push barely "
                    "sixty percent of the flow, the coolant crosses the "
                    "heat exchanger too slowly and comes out warmer, "
                    "and the rack's chips climb until the controller "
                    "must slow everything down. Nothing broke except a "
                    "pump; the computers pay anyway. The difference "
                    "between this run and the last one is one purchase "
                    "order."
                ),
                standard=(
                    "Two pumps (N), ~200 kW; pump 1 fails at t=300. One "
                    "pump alone pushes ~62% of the setpoint, the flow "
                    "factor degrades the heat exchanger, and the "
                    "silicon settles ~7 K hotter — past the IRC target, "
                    "so the caps engage and hold. Same failure as the "
                    "N+1 run; the derate is the price of the missing "
                    "third pump. Capacity planning for pumps, in one "
                    "A/B."
                ),
                expert=(
                    "2→1 pump: flow ≈ 0.62·setpoint, ff = 0.75 → "
                    "approach +9 K, ΔT/2 +3 K → chip > target → caps "
                    "hold a derated steady state. N vs N+1, priced."
                ),
            ),
        ],
        question="At what percent does the cap gauge settle with one pump carrying the loop?",
        answer=(
            "Near 86%, moving about 173 kW, after dipping to about 81% "
            "on the way. The one surviving pump delivers 210 L/min, "
            "about 62% of the setpoint."
        ),
        scenario=Scenario(
            config=NO_SPARE, workload=FULL_TILT, environment=Environment(),
            duration_s=700,
            events=[SimEvent(at_s=300, action="fail-pump", index=0)],
        ),
    ),
    GuidedScenario(
        id="humid-morning",
        title="The dew-point floor",
        narration=[
            L(
                novice=(
                    "A nearly idle rack on a humid morning. You might "
                    "expect the coolant to run as cold as the building "
                    "water — but look: the supply line holds at 32 "
                    "degrees, well above it. The CDU is refusing to go "
                    "colder, because pipes below the room's dew point "
                    "sweat like a cold drink in summer, and water drips "
                    "onto live electronics. Mid-run, an operator lowers "
                    "the setpoint anyway — and then the humidity rises, "
                    "and the floor chases the dew point up regardless "
                    "of what anyone asked for. The room's moisture, not "
                    "the operator, owns the bottom of this loop."
                ),
                standard=(
                    "One bank at 10% utilization: the emergent supply "
                    "would sit near the facility's 17 °C, but the "
                    "mixing valve floors it at the 32 °C setpoint. At "
                    "t=200 the setpoint drops to 24 °C — legal, dew "
                    "point is 20 — and the supply follows. At t=400 the "
                    "dew point climbs to 23 °C and the floor becomes "
                    "dew + 2 = 25 °C: the valve overrides the setpoint, "
                    "the dew-margin strip chart pins at 2 K, and the "
                    "log says why. Condensation is the constraint "
                    "liquid cooling newcomers forget; the floor is "
                    "always max(setpoint, dew + margin)."
                ),
                expert=(
                    "Idle bank: supply = floor, not T_fac. Setpoint "
                    "32→24 at t=200 (dew 20, legal); dew →23 at t=400 "
                    "→ floor = dew+2 = 25 overrides. Margin chart pins "
                    "at 2 K. Floor = max(setpoint, dew+2), always."
                ),
            ),
        ],
        question="After the humid air arrives, who sets the supply temperature — the operator or the room?",
        answer=(
            "The room. The operator asked for 24 °C, but the supply "
            "holds 25 °C: the 23 °C dew point plus the 2 K margin."
        ),
        scenario=Scenario(
            config=CduConfig(tray_groups=1, pumps=3),
            workload=IDLE,
            environment=Environment(facility_supply_c=17, dew_point_c=20),
            duration_s=600,
            events=[
                SimEvent(at_s=200, action="set-min-supply", value=24),
                SimEvent(at_s=400, action="set-dew-point", value=23),
            ],
        ),
    ),
]

# --- Explain-mode entries ------------------------------------------------------

EXPLAINS = [
    Explain(
        id="approach",
        title="Approach temperature",
        equation="T_supply = T_facility + Q / (UA × (flow/nominal)^0.6)",
        inputs=["facility supply", "heat", "flow", "coolant supply"],
        explanation=L(
            novice=(
                "A heat exchanger is a wall between two liquids, and "
                "pushing heat through a wall needs a temperature "
                "difference. So the rack's coolant always comes out "
                "warmer than the building water going in — by more "
                "when there's more heat, and by more when the flow is "
                "weak. That gap is called the approach, and it is the "
                "toll every CDU charges. One warning: this model's gap "
                "is far wider than a real unit's, about 30 degrees at "
                "full load where real ones manage 2 to 5. It was set "
                "that way so the box runs out of capacity on cool "
                "17-degree water."
            ),
            standard=(
                "The approach is the gap the heat exchanger needs to "
                "move Q kilowatts: Q divided by its conductance (UA, "
                "the exchanger's heat-transfer capacity in kW per "
                "kelvin), degraded when flow falls below nominal. The "
                "readout is coolant supply minus facility supply, and "
                "the supply lags by about a minute, so it matches the "
                "equation only once the loop has settled. This model's "
                "exchanger is deliberately loose: about 30 K at rated "
                "load, where a real plate exchanger runs 2–5 K. It's "
                "why the "
                "rack's coolant can never match the facility water, "
                "and why a warm-water facility design spends silicon "
                "margin: every kelvin of facility supply and every "
                "kelvin of approach lands on the chips unchanged."
            ),
            expert=(
                "Approach = Q/(UA·ff), ff = (flow/nom)^0.6. Lumped UA "
                "stands in for the NTU integral. Facility + approach "
                "= supply at steady state (τ≈60 s); additive to the "
                "die. UA = 7 kW/K is ~10× loose (≈31 K at rating vs "
                "2–5 K real), tuned so the class binds on W17 — don't "
                "size from it."
            ),
        ),
    ),
    Explain(
        id="loop-dt",
        title="Loop temperature rise",
        equation="ΔT = Q / (ṁ × cp)",
        inputs=["heat", "flow", "supply", "return"],
        explanation=L(
            novice=(
                "Liquid warms as it collects heat, by a knowable "
                "amount: the heat added, divided by how much liquid is "
                "flowing and how much heat that liquid can hold. Less "
                "flow or more heat means a hotter return pipe. The "
                "same one-line rule runs the building side too — and "
                "the two sides must always carry the same total heat."
            ),
            standard=(
                "Return = supply + Q/(ṁ·cp), where ṁ·cp is mass flow "
                "times the liquid's specific heat, on both loops, every "
                "tick — the IR7000 twin's identity with coolant in "
                "place of air. The engine derives both return "
                "temperatures from the same Q, so the two loops carry "
                "equal heat by construction, and the tests assert it. "
                "A CDU is a device for making three numbers equal: IT "
                "heat, rack-side ṁ·cp·ΔT, facility-side ṁ·cp·ΔT."
            ),
            expert=(
                "Q = ṁ₂cp₂ΔT₂ = ṁ₁cp₁ΔT₁ per tick, asserted. PG25 "
                "cp 3.8, water 4.186 kJ/kg·K; primary valve holds "
                "ΔT₁ = 6 K by modulating ṁ₁."
            ),
        ),
    ),
    Explain(
        id="pump-flow",
        title="Pump flow & power",
        equation="Q_max(k) = Q₁ × k^0.65 · P_pump = k × P_max × speed³",
        inputs=["pumps alive", "flow", "pump speed", "pump power"],
        explanation=L(
            novice=(
                "Two pumps pushing the same loop don't give twice the "
                "flow — the pipes push back harder as flow rises, so "
                "the second pump adds only about sixty percent more. "
                "The upside: losing one pump costs much less than half "
                "the flow. Pump electricity grows with the cube of "
                "speed, the same steep law as the server fans in the "
                "R760 twin."
            ),
            standard=(
                "Parallel pumps share one system curve: delivered flow "
                "scales like k^0.65, so 3 pumps ≈ 2× one pump, and the "
                "controller normally runs N+1 pumps at partial speed. "
                "A failure makes survivors ramp — and because power "
                "goes with speed cubed, the ramp is expensive per "
                "L/min. The flow factor then feeds the heat exchanger: "
                "hydraulics and heat transfer are one chain."
            ),
            expert=(
                "Pump∩system: Q(k) ∝ k^0.65 (lumped), speed = "
                "setpoint/Q_max(k) clamped, P = k·P_max·s³. Affinity "
                "laws; ff couples flow into UA."
            ),
        ),
    ),
    Explain(
        id="chip-temp",
        title="Silicon temperature",
        equation="T_chip = T_supply + ΔT/2 + q_bank × R_th",
        inputs=["coolant supply", "loop rise", "bank heat", "silicon temp"],
        explanation=L(
            novice=(
                "A chip under a cold plate runs warmer than the "
                "coolant by two steps: the coolant itself warms as it "
                "crosses the rack (the average bank sees about half "
                "that rise), and the cold plate's metal adds its own "
                "small resistance. Add the supply temperature and "
                "that's the chip. Everything upstream — the building "
                "water, the heat exchanger's toll, the pumps' flow — "
                "shows up in this one number."
            ),
            standard=(
                "The chain's last link: supply + half the loop rise "
                "(the mean bank position) + the cold plate's R_th "
                "times the bank's heat. It's why the IRC can steer "
                "silicon with any of three levers — facility water, "
                "flow, or power caps — and why this twin's warm-water "
                "day is really a chip-temperature story told from the "
                "building's side."
            ),
            expert=(
                "T_die ≈ T_sup + Q/(2ṁcp) + R_th·q_bank, first-order "
                "lag τ=15 s. Additive chain: T_fac + approach + ΔT/2 "
                "+ R_th·q. Three levers, one number."
            ),
        ),
    ),
    Explain(
        id="dew-floor",
        title="The condensation floor",
        equation="T_supply ≥ max(setpoint, dew point + 2 K)",
        inputs=["dew point", "setpoint", "coolant supply", "dew margin"],
        explanation=L(
            novice=(
                "Anything colder than the room's dew point sweats — "
                "the cold-drink effect. Inside a rack, that sweat is "
                "water on live electronics. So the CDU has a hard "
                "floor: its mixing valve blends warm return coolant "
                "into the supply so the pipes never get cold enough to "
                "condense, no matter what an operator asks for. On a "
                "humid day, the room sets your coolant temperature."
            ),
            standard=(
                "The mixing valve enforces supply ≥ dew point + "
                "margin on every tick — an instantaneous constraint, "
                "not a controller chasing one. The operator's minimum-"
                "supply setpoint only matters while it's above the "
                "dew floor; when humidity rises, the floor rises "
                "through it and the log says so. Colder is not "
                "always available, which surprises people used to "
                "air."
            ),
            expert=(
                "Hard constraint: T_sup = max(emergent, setpoint, "
                "dew+2), applied post-lag. Humidity moves the binding "
                "term; operator setpoint is advisory below it."
            ),
        ),
    ),
]
