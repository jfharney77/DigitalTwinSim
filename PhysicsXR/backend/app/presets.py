"""Presets and the teaching layer — backend data.

Config presets, workload presets, guided scenarios (scripted walkthroughs
that set the scenario and narrate what to watch), and Explain-mode entries
(the equation behind each key readout, with placeholders the frontend
substitutes with live values). Explain and scenario prose carries reading
levels — the trace states are numbers, so the teaching prose is where the
leveling lives.
"""

from __future__ import annotations

from .leveling import L
from .models import (
    ConfigPreset,
    Environment,
    Explain,
    GuidedScenario,
    Scenario,
    ServerConfig,
    SimEvent,
    Workload,
    WorkloadPreset,
)

# --- Config presets --------------------------------------------------------

CELL_SITE = ServerConfig(
    platform="xr8000", cpu_tdp_w=225, thermal_config="standard",
    dimms=8, drive_type="ssd", drives=2, accels_single_wide=2,
    io_card_w=100, psu_count=1, psu_capacity_w=800, redundancy="1+0",
)

FACTORY_FLOOR = ServerConfig(
    platform="xr8000", cpu_tdp_w=250, thermal_config="standard",
    dimms=16, drive_type="ssd", drives=4, accels_single_wide=2,
    io_card_w=25, psu_count=2, psu_capacity_w=1400, redundancy="1+1",
)

VEHICLE = ServerConfig(
    platform="xr4000", cpu_tdp_w=100, thermal_config="standard",
    dimms=4, drive_type="ssd", drives=2, accels_single_wide=1,
    io_card_w=15, psu_count=2, psu_capacity_w=800, redundancy="1+1",
)

HDD_MISTAKE = ServerConfig(
    platform="xr8000", cpu_tdp_w=185, thermal_config="standard",
    dimms=8, drive_type="hdd", drives=4, accels_single_wide=0,
    io_card_w=25, psu_count=2, psu_capacity_w=1100, redundancy="1+1",
)

EXTENDED = ServerConfig(
    platform="xr8000", cpu_tdp_w=185, thermal_config="extended",
    dimms=8, drive_type="ssd", drives=2, accels_single_wide=0,
    io_card_w=25, psu_count=2, psu_capacity_w=1100, redundancy="1+1",
)

CONFIG_PRESETS = [
    ConfigPreset(id="cell-site", name="Cell site", config=CELL_SITE,
                 blurb="225 W single socket, RAN acceleration cards, "
                       "fronthaul NICs, one 800 W PSU on one feed — the "
                       "classic telco cabinet build."),
    ConfigPreset(id="factory-floor", name="Factory floor", config=FACTORY_FLOOR,
                 blurb="250 W + two inference accelerators — vision "
                       "analytics beside the line, in the line's dust."),
    ConfigPreset(id="vehicle", name="Vehicle", config=VEHICLE,
                 blurb="XR4000 stackable, Xeon D, SSDs only — the rack is "
                       "moving."),
    ConfigPreset(id="hdd-mistake", name="The HDD mistake", config=HDD_MISTAKE,
                 blurb="Spinning drives specced for a vibrating site — "
                       "legal, warned, and instructive."),
    ConfigPreset(id="extended", name="Extended envelope", config=EXTENDED,
                 blurb="A select config rated −20…65 °C — smaller CPU, "
                       "SSDs only; that is what 'select' means."),
]

# --- Workload presets ------------------------------------------------------

IDLE = Workload()
RAN = Workload(cpu_pct=85, mem_pct=50, storage_pct=10, accel_pct=60)
VIDEO = Workload(cpu_pct=50, mem_pct=60, storage_pct=40, accel_pct=100)
EDGE_DB = Workload(cpu_pct=60, mem_pct=75, storage_pct=70, accel_pct=0)
FULL = Workload(cpu_pct=100, mem_pct=80, storage_pct=50, accel_pct=100)

WORKLOAD_PRESETS = [
    WorkloadPreset(id="idle", name="Idle", workload=IDLE),
    WorkloadPreset(id="ran", name="RAN / vRAN", workload=RAN),
    WorkloadPreset(id="video", name="Video analytics", workload=VIDEO),
    WorkloadPreset(id="edge-db", name="Edge database", workload=EDGE_DB),
    WorkloadPreset(id="full", name="Everything at 100%", workload=FULL),
]

# --- Guided scenarios ------------------------------------------------------

GUIDED_SCENARIOS = [
    GuidedScenario(
        id="phoenix-rooftop",
        title="Rooftop in Phoenix",
        narration=[
            L(
                novice=(
                    "The same computer you could run in a cool machine "
                    "room is bolted to a rooftop in Phoenix. The morning "
                    "starts at 38 degrees — already hotter than any data "
                    "center — and in the afternoon the air reaches 48. "
                    "Watch the fans climb toward their maximum as the day "
                    "heats up, and watch what happens when they get "
                    "there: the processor starts slowing itself down to "
                    "survive, because there is no colder air to be had. "
                    "The machine is rated for 55 degrees, and this run "
                    "shows you what living near that edge actually looks "
                    "like."
                ),
                standard=(
                    "The cell-site build under RAN load, starting at "
                    "38 °C; at t=240 s the afternoon arrives and ambient "
                    "steps to 48 °C — inside the −5…55 °C rating, far "
                    "outside anything a data hall permits. Watch the "
                    "controller spend its entire authority: fans toward "
                    "100%, then throttle steps when rpm runs out. The "
                    "rating is real, but the top of the envelope is paid "
                    "for in fan watts and shaved clocks."
                ),
                expert=(
                    "RAN load, 38→48 °C at t=240. Fans pin, then clamp "
                    "steps. In-envelope ≠ free: the top decade costs rpm³ "
                    "and clocks."
                ),
            ),
        ],
        question="How many watts of fan power did the afternoon cost, and when did the first throttle step land?",
        scenario=Scenario(
            config=CELL_SITE, workload=RAN,
            environment=Environment(inlet_c=38, dust="moderate"),
            duration_s=900,
            events=[SimEvent(at_s=240, action="set-inlet", value=48)],
        ),
    ),
    GuidedScenario(
        id="fargo-february",
        title="February in Fargo",
        narration=[
            L(
                novice=(
                    "Now take the identical computer to a rooftop in "
                    "Fargo, North Dakota, in February: fifteen below "
                    "zero. The same work runs, and almost nothing "
                    "happens — the fans idle at their minimum speed, the "
                    "processor sits far below any temperature that "
                    "worries it, and the power bill is lower because the "
                    "fans barely turn. Cold, for electronics, is nearly "
                    "free. The reason the spec sheet still has a lower "
                    "limit is what lives below it: condensation when "
                    "things warm up, batteries and plastics that turn "
                    "brittle, drives that refuse to spin up. One "
                    "machine, two climates, and the whole cost lives on "
                    "the hot side."
                ),
                standard=(
                    "The identical build and workload at −15 °C — below "
                    "the standard −5 °C rating (the validation panel "
                    "says so; an extended config would cover it). "
                    "Thermally it is a non-event: fans at the floor, "
                    "silicon cozy, wall power lower than Phoenix by the "
                    "whole fan budget. That asymmetry is the lesson — "
                    "heat is the expensive direction, and the cold "
                    "limit exists for reasons this model is honest "
                    "about not simulating: condensation, brittleness, "
                    "spin-up."
                ),
                expert=(
                    "Same build, −15 °C: fans at floor, no throttle, "
                    "wall = Phoenix minus the fan budget. Cold limit is "
                    "about condensation/materials, not steady-state "
                    "thermals — unmodeled, footnoted."
                ),
            ),
        ],
        question="Compare wall power here to the Phoenix run at the same workload — where did the difference go?",
        scenario=Scenario(
            config=CELL_SITE, workload=RAN,
            environment=Environment(inlet_c=-15, dust="clean"),
            duration_s=600,
        ),
    ),
    GuidedScenario(
        id="filter-nobody-changed",
        title="The filter nobody changed",
        narration=[
            L(
                novice=(
                    "Six months ago somebody was supposed to change this "
                    "machine's dust filter, and nobody did. The site is "
                    "dusty, so the filter is now half-clogged: the fans "
                    "must spin faster all the time just to move the same "
                    "air. Then a heat wave arrives. Watch the fans reach "
                    "their maximum with nothing left to give, and the "
                    "processor slow itself down — on a day a clean "
                    "filter would have survived comfortably. The dust "
                    "did not get hot; it just quietly stole the fans' "
                    "headroom, months before the day it mattered."
                ),
                standard=(
                    "The cell-site build at full load, heavy dust, six "
                    "months since filter service — a ~42% airflow "
                    "penalty before anything happens. At t=300 s a heat "
                    "wave takes ambient from 38 to 45 °C. The fans, "
                    "already pinned buying back the fouling deficit, "
                    "have nothing left, and the CPU throttles. Re-run "
                    "with a clean filter (click the filter region) and "
                    "the same heat wave passes without a single clipped "
                    "cycle. Fouling is a debt with a variable due date."
                ),
                expert=(
                    "Heavy dust ×6 mo ≈ 42% resistance. 38→45 °C at "
                    "t=300: fouled build clamps; clean build rides it "
                    "out. Deferred maintenance, priced in rpm headroom."
                ),
            ),
        ],
        question="Re-run this with the filter cleaned — how many degrees of heat wave was the dirty filter worth?",
        scenario=Scenario(
            config=CELL_SITE, workload=FULL,
            environment=Environment(inlet_c=38, dust="heavy", filter_months=6),
            duration_s=900,
            events=[SimEvent(at_s=300, action="set-inlet", value=45)],
        ),
    ),
    GuidedScenario(
        id="brownout",
        title="Brownout at the cell site",
        narration=[
            L(
                novice=(
                    "A cell site hangs off a single power line, and on a "
                    "bad afternoon that line's voltage sags — the lights "
                    "dim but nothing switches off. For this server the "
                    "danger is arithmetic: it still needs the same "
                    "amount of power, and power is voltage times "
                    "current, so when voltage drops the current rises. "
                    "At light load the extra current is small and the "
                    "sag passes unnoticed. At full load the current "
                    "climbs past what the power supply can safely draw, "
                    "and it shuts off to protect itself. The same sag, "
                    "on the same machine, is harmless or fatal depending "
                    "on how busy the machine happened to be."
                ),
                standard=(
                    "The single-PSU cell-site build at full RAN load; at "
                    "t=300 s the feed sags to 65% of nominal for ten "
                    "seconds. Constant power at falling voltage means "
                    "rising current (I = P/V); past the PSU's input "
                    "limit for a few sustained seconds, it trips. Slide "
                    "the workload down and re-run: the identical sag "
                    "rides through, because the current never reached "
                    "the limit. Brownout ride-through is a function of "
                    "load — the classic post-mortem finding."
                ),
                expert=(
                    "1+0 build, full load, V→65% ×10 s at t=300: I = "
                    "P/V crosses the input limit, trip. Same sag at "
                    "idle: no event. Ride-through is load-dependent."
                ),
            ),
        ],
        question="What is the highest CPU load at which this sag still rides through?",
        scenario=Scenario(
            config=CELL_SITE, workload=FULL,
            environment=Environment(inlet_c=30),
            duration_s=600,
            events=[SimEvent(at_s=300, action="voltage-sag", value=65, seconds=10)],
        ),
    ),
    GuidedScenario(
        id="hdd-mistake",
        title="The HDD mistake",
        narration=[
            L(
                novice=(
                    "Somebody specced spinning hard drives for a server "
                    "that lives beside a busy road, because they were "
                    "cheaper per terabyte. Spinning drives read by "
                    "flying a head a few nanometres over the platter, "
                    "and vibration makes the head miss and retry — so "
                    "beside the road, these drives quietly lose part of "
                    "their speed. Watch the storage-performance readout: "
                    "the machine is healthy, nothing is broken, and forty "
                    "percent of the storage throughput is simply gone. "
                    "Solid-state drives have no moving parts and lose "
                    "nothing. Rugged sites buy SSDs; this run is why."
                ),
                standard=(
                    "The HDD build under vehicle-class vibration, "
                    "database workload. Nothing fails: the instrument "
                    "to watch is storage performance lost — the head-"
                    "repositioning tax, ~40% at this vibration class "
                    "(an estimate, honestly labeled). Flip the build to "
                    "SSDs and the number goes to zero. The validation "
                    "panel warned at configuration time; this is the "
                    "warning, lived."
                ),
                expert=(
                    "HDD + vehicle vibe: ~40% throughput tax, no "
                    "failure event. SSD: 0. The warning panel, "
                    "demonstrated."
                ),
            ),
        ],
        question="Switch the build to SSDs mid-comparison — what changed, and what stayed exactly the same?",
        scenario=Scenario(
            config=HDD_MISTAKE, workload=EDGE_DB,
            environment=Environment(inlet_c=30, vibration="vehicle"),
            duration_s=600,
        ),
    ),
    GuidedScenario(
        id="mountain-site",
        title="The mountain site",
        narration=[
            L(
                novice=(
                    "This cell site sits at 2,500 metres. Thin mountain "
                    "air carries less heat per litre, so the fans must "
                    "move more of it for the same cooling — they run "
                    "faster, use more power, and have less left in "
                    "reserve for a hot day. Add the mountain sun and a "
                    "dusty summer, and a machine that was comfortable at "
                    "sea level spends the afternoon near its limits. "
                    "Altitude is one more slider the outside world gets "
                    "to move."
                ),
                standard=(
                    "The cell-site build at 2,500 m: air density is "
                    "down ~22%, mass flow per CFM with it, so the fans "
                    "run measurably faster for the same silicon "
                    "temperatures — and the derating advisory (~1 °C of "
                    "supported ambient per 300 m above 950 m) stacks "
                    "onto whatever the day brings. At t=300 the "
                    "afternoon adds 42 °C ambient on top."
                ),
                expert=(
                    "2,500 m: ρ −22%, rpm up, margin down; +42 °C "
                    "afternoon at t=300. Altitude derate stacks with "
                    "everything else."
                ),
            ),
        ],
        question="How much earlier does this site throttle than the identical build at sea level?",
        scenario=Scenario(
            config=CELL_SITE, workload=RAN,
            environment=Environment(inlet_c=35, altitude_m=2500, dust="moderate"),
            duration_s=900,
            events=[SimEvent(at_s=300, action="set-inlet", value=42)],
        ),
    ),
]

# --- Explain-mode entries ---------------------------------------------------

EXPLAINS = [
    Explain(
        id="cpu-power",
        title="CPU power",
        equation="P_cpu = (P_idle + (TDP − P_idle) × util^1.4) × clamp",
        inputs=["CPU util", "CPU power", "CPU heat", "fan rpm", "fan power", "total power"],
        explanation=L(
            novice=(
                "A processor never drops to zero watts — even idle it "
                "spends around fifteen percent of its maximum just being "
                "on. From there, power rises with load, and faster than "
                "you might expect: the curve bends upward, so the last "
                "stretch to 100% costs more than the first. If the chip "
                "gets too hot, the 'clamp' cuts this number down to "
                "protect it — that is throttling, and on a hot rooftop "
                "it is a daily fact of life rather than a rare event."
            ),
            standard=(
                "CPU package power interpolates from an idle floor "
                "(~15% of TDP) to full TDP along util^1.4 — superlinear "
                "because higher utilization brings higher clocks and "
                "voltages. At sustained 100% the package briefly boosts "
                "~15% over TDP before settling. The clamp term is the "
                "throttle multiplier: 1.0 normally, stepped down 10% "
                "per tick above 98 °C — and the ambient decides how "
                "often that clause fires."
            ),
            expert=(
                "Idle-floor + (TDP−idle)·util^1.4, ×1.15 boost ≤60 s, "
                "×throttle clamp. Single socket; ambient sets clamp duty."
            ),
        ),
    ),
    Explain(
        id="zone-outlet",
        title="Zone outlet temperature",
        equation="T_out = T_in + Q / (ṁ × cp)",
        inputs=["zone heat", "airflow", "inlet temp", "outlet temp"],
        explanation=L(
            novice=(
                "Air warms as it crosses each part of the server, by a "
                "knowable amount: the heat added, divided by how much "
                "air is passing and how much heat air can hold. Out "
                "here both inputs are under attack — dust cuts the "
                "airflow, altitude thins the air — so the same watts "
                "make hotter exhaust than they would in a data hall."
            ),
            standard=(
                "Each zone's outlet is its inlet plus Q/(ṁ·cp): heat "
                "in watts over mass flow times air's specific heat "
                "(1005 J/kg·K). Zones chain front to back, and summing "
                "them gives the whole-box identity exhaust = inlet + "
                "DC/(ṁ·cp). The rugged twist is that ṁ is contested: "
                "fouling shrinks CFM at a given rpm, and altitude "
                "shrinks the mass each CFM carries."
            ),
            expert=(
                "T_out = T_in + Q/(ṁcp); zones chain; Σ gives the "
                "exhaust identity. ṁ eroded by fouling (CFM) and "
                "altitude (ρ)."
            ),
        ),
    ),
    Explain(
        id="fan-power",
        title="Fan power & the fouled filter",
        equation="P_fan = N_alive × P_max × (rpm%)³ · CFM = f(rpm) × (1 − fouling)",
        inputs=["filter fouling", "airflow", "CPU temp", "fan rpm", "fan power", "total power"],
        explanation=L(
            novice=(
                "Fan power grows with the cube of speed: twice the "
                "speed costs eight times the electricity. A dusty "
                "filter makes every fan speed deliver less air, so the "
                "machine must run its fans faster all the time to stay "
                "cool — which is why months of dust quietly turn into "
                "a bigger power bill and, on the wrong hot day, into a "
                "machine with no fan speed left to give."
            ),
            standard=(
                "Cubic fan law, with the filter ahead of it: fouling "
                "raises the system's flow resistance, so delivered CFM "
                "at a given rpm falls by the fouling fraction, and the "
                "controller buys the deficit back with rpm — priced at "
                "rpm³. Six months of heavy dust (~36%) is hundreds of "
                "extra fan-watts at load, and — the sharper cost — "
                "headroom the controller no longer has when the heat "
                "wave lands."
            ),
            expert=(
                "P ∝ rpm³; CFM × (1 − fouling). Fouling converts to "
                "rpm demand at cube pricing, and to lost ceiling when "
                "rpm pins."
            ),
        ),
    ),
    Explain(
        id="wall-power",
        title="Wall (AC) power",
        equation="P_wall = P_dc / η(load fraction)",
        inputs=["total DC power", "PSU load point", "efficiency", "wall power"],
        explanation=L(
            novice=(
                "The power supplies convert the site's electricity to "
                "the voltages the parts use, losing a few percent doing "
                "it — least efficient when barely loaded, best around "
                "half load. So the wall meter always reads higher than "
                "the sum of the parts."
            ),
            standard=(
                "Wall power is DC load divided by efficiency at the "
                "current load fraction, read off a Titanium-class curve "
                "(≈90% at 10% load, 96% near 50%, 94% at 100%). In 1+1 "
                "the pair shares load so each sits lower on the curve; "
                "single-feed edge sites often run 1+0 and take the "
                "availability risk instead."
            ),
            expert=(
                "AC = DC/η(load). Piecewise Titanium curve; 1+0 common "
                "at the edge — the redundancy tradeoff is a site "
                "decision."
            ),
        ),
    ),
    Explain(
        id="brownout",
        title="Brownout ride-through",
        equation="I_input = P_wall / V_feed",
        inputs=["wall power", "feed voltage", "input current", "PSU input limit"],
        explanation=L(
            novice=(
                "When the site's voltage sags, the server still needs "
                "the same power — and power is voltage times current, "
                "so the current rises to make up the difference. The "
                "power supply can only draw so much current before it "
                "shuts off to protect itself. That is why the same "
                "brownout is harmless when the machine is idle and "
                "fatal when it is busy: the busy machine was already "
                "drawing most of the current budget before the voltage "
                "fell."
            ),
            standard=(
                "At constant power, input current is P/V: a sag to 65% "
                "of nominal multiplies the current by ~1.5. Whether "
                "that crosses the PSU's input limit depends entirely "
                "on the load at the moment the sag arrives — the "
                "ride-through a site *has* is a function of the "
                "workload, not just the hardware. Deep sags (below "
                "~60% here) drop the supplies outright regardless."
            ),
            expert=(
                "I = P/V vs per-PSU input limit; trip after sustained "
                "seconds. Ride-through is load-dependent; deep sag "
                "< 60% is an immediate dropout. Limits estimated."
            ),
        ),
    ),
    Explain(
        id="vibration",
        title="Vibration & spinning drives",
        equation="throughput_lost ≈ derate(vibration class), HDD only",
        inputs=["vibration class", "drive type", "storage performance"],
        explanation=L(
            novice=(
                "A spinning hard drive reads by flying a tiny head a "
                "hair's width above a spinning platter. Shake it and "
                "the head misses, waits for the platter to come around, "
                "and tries again — so vibration silently steals speed "
                "without breaking anything. Chips with no moving parts "
                "(SSDs) do not care. That is the whole reason rugged "
                "sites pay extra for SSDs."
            ),
            standard=(
                "Rotational media loses throughput to head-"
                "repositioning retries under vibration — modeled as a "
                "flat derate per class (~15% roadside, ~40% vehicle; "
                "estimates, honestly labeled) applied only to HDD "
                "builds. It is a performance tax, not a failure event, "
                "which is exactly what makes it easy to miss in "
                "deployment."
            ),
            expert=(
                "HDD-only flat derate per vibe class (est. 15/40%). "
                "Tax, not fault — invisible to health checks, visible "
                "to throughput."
            ),
        ),
    ),
]
