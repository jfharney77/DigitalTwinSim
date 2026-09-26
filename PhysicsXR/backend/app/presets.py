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
    platform="xr8000", cpu_tdp_w=205, thermal_config="standard",
    dimms=8, drive_type="ssd", drives=2, accels_single_wide=2,
    io_card_w=100, psu_count=1, psu_capacity_w=800, redundancy="1+0",
)

FACTORY_FLOOR = ServerConfig(
    platform="xr8000", cpu_tdp_w=205, thermal_config="standard",
    dimms=8, drive_type="ssd", drives=4, accels_single_wide=2,
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
                 blurb="205 W single socket (the XR8000's largest CPU), RAN acceleration cards, "
                       "fronthaul NICs, one 800 W PSU on one feed — the "
                       "classic telco cabinet build."),
    ConfigPreset(id="factory-floor", name="Factory floor", config=FACTORY_FLOOR,
                 blurb="205 W + two inference accelerators — vision "
                       "analytics beside the line, in the line's dust."),
    ConfigPreset(id="vehicle", name="Vehicle", config=VEHICLE,
                 blurb="XR4000, Xeon D, four DIMMs, SSDs only — the rack "
                       "is moving."),
    ConfigPreset(id="hdd-mistake", name="The HDD mistake", config=HDD_MISTAKE,
                 blurb="Spinning drives specced for a vibrating site — a "
                       "thought experiment (Dell's XR8000 and XR4000 take "
                       "M.2 flash only), warned and instructive."),
    ConfigPreset(id="extended", name="Extended envelope", config=EXTENDED,
                 blurb="A select config rated −20…65 °C — CPU at 195 W or "
                       "below, dual PSUs, flash only; on the real product, "
                       "the 2U XR8620t sled with Heater Manager. That is "
                       "what 'select' means."),
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
                    "center — and by afternoon the rooftop air reaches 52. "
                    "Watch the fans climb toward their maximum as the day "
                    "heats up. They get there about twenty seconds after the "
                    "afternoon arrives, and from then on they have "
                    "nothing left to give. The processor stays below the "
                    "temperature where it would start slowing itself "
                    "down, but only just. The machine is rated for 55 "
                    "degrees, and this run shows you what living near "
                    "that edge actually looks like: loud, hungry fans and "
                    "very little room to spare."
                ),
                standard=(
                    "The cell-site build under RAN load, starting at "
                    "38 °C; at t=240 s the afternoon arrives and ambient "
                    "steps to 52 °C — inside the −5…55 °C rating, far "
                    "outside anything a data hall permits. Watch the "
                    "controller spend its entire authority: fans pinned at "
                    "100% about 20 s after the step, the CPU holding about "
                    "11 °C under its throttle point with no rpm left to "
                    "buy more. The rating is real, but the top of the "
                    "envelope is paid for in fan watts and lost headroom — "
                    "the next thing that goes wrong (a fouled filter, a "
                    "dead fan) lands straight on the clocks."
                ),
                expert=(
                    "RAN load, 38→52 °C at t=240. Fans pin; CPU ~11 °C "
                    "under clamp, zero rpm reserve. In-envelope ≠ free: "
                    "the top decade costs rpm³ and all the margin."
                ),
            ),
        ],
        question="How many watts of fan power did the afternoon cost, and how much CPU headroom is left once the fans are pinned?",
        scenario=Scenario(
            config=CELL_SITE, workload=RAN,
            environment=Environment(inlet_c=38, dust="moderate"),
            duration_s=900,
            events=[SimEvent(at_s=240, action="set-inlet", value=52)],
            warm_start=True,
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
                    "free, once the machine is running. The reason the "
                    "spec sheet still has a lower limit is starting up: "
                    "Dell's guide says the processor and the memory must "
                    "be at least zero degrees before they are switched "
                    "on, so the builds rated for minus twenty carry small "
                    "heaters that warm the board for about four minutes "
                    "first. One machine, two climates, and the running "
                    "cost lives on the hot side."
                ),
                standard=(
                    "The identical build and workload at −15 °C — below "
                    "the standard −5 °C rating (the validation panel "
                    "says so; an extended config would cover it). "
                    "Thermally it is a non-event: fans at the floor, "
                    "silicon cozy, wall power lower than Phoenix by the "
                    "whole fan budget. That asymmetry is the lesson — "
                    "heat is the expensive direction. The cold limit is "
                    "about starting, which this model does not simulate: "
                    "Dell's technical guide lists 0 °C minimums for the "
                    "CPU, chipset, and DIMMs, forbids a cold start below "
                    "+5 °C without the Heater Manager option, and gives "
                    "that heater about four minutes to bring a −20 °C "
                    "XR8620t sled up to +5 °C before power is applied."
                ),
                expert=(
                    "Same build, −15 °C: fans at floor, no throttle, "
                    "wall = Phoenix minus the fan budget. Cold limit is "
                    "a cold-boot limit (0 °C silicon minimums; Heater "
                    "Manager, XR8620t only), not steady-state thermals — "
                    "unmodeled, footnoted."
                ),
            ),
        ],
        question="Compare wall power here to the Phoenix run at the same workload — where did the difference go?",
        scenario=Scenario(
            config=CELL_SITE, workload=RAN,
            environment=Environment(inlet_c=-15, dust="clean"),
            duration_s=600,
            warm_start=True,
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
                    "dusty, so the filter is now nearly half clogged. The "
                    "run opens on an ordinary 30-degree day with the "
                    "machine already warmed up and busy. Look at the fans "
                    "line in the instruments: they are at 100% already, "
                    "spending everything they have to pull air through "
                    "the dust, and nothing is slowing down yet. At 300 "
                    "seconds a heat wave takes the air to 45 degrees. The "
                    "fans have no more speed to give, so a few seconds "
                    "later the event log reads 'Accelerator throttling "
                    "engaged': the accelerator cards (the add-in chips "
                    "doing the heavy arithmetic) cut their own speed to "
                    "stay under their temperature limit, and the "
                    "'accelerator work lost' line settles near 30%. The "
                    "main processor gets hotter and keeps its full speed. "
                    "Now set 'Months since filter service' to 0 and press "
                    "'Restart run'. With a clean filter the fans start "
                    "the day near 73%, reach 100% in the same heat wave, "
                    "and nothing slows down. The dust did not get hot. It "
                    "used up the fans' spare speed months before the day "
                    "it was needed."
                ),
                standard=(
                    "The cell-site build at full load, heavy dust, six "
                    "months since filter service: a ~42% airflow penalty. "
                    "The run opens warmed up at 30 °C ambient with the "
                    "fans already pinned at 100%, buying back the fouling "
                    "deficit, and no throttling. At t=300 s a heat wave "
                    "takes ambient to 45 °C. The fans have nothing left, "
                    "and within about ten seconds the accelerators cross "
                    "92 °C and throttle; they settle near 30% of their "
                    "work lost, and wall power falls with them. The CPU "
                    "warms to about 95 °C, under its 98 °C limit, and "
                    "keeps full clocks. Set Months since filter service "
                    "to 0 and press Restart run: the clean build opens "
                    "near 73% fan speed, pins in the same heat wave, and "
                    "never clips a cycle. Fouling is a debt with a "
                    "variable due date."
                ),
                expert=(
                    "Heavy dust ×6 mo ≈ 42% resistance; warm start, "
                    "30 °C, fans 100%, no clamp. 30→45 °C at t=300: "
                    "accelerators clamp ~30% within ~10 s, CPU holds "
                    "under 98 °C. Filter months 0, restart: ~73% rpm "
                    "before, pinned after, zero throttle seconds."
                ),
            ),
        ],
        question=(
            "Read the fans line just before t+300 s on the fouled run and "
            "again on the clean run. Which build still had fan speed in "
            "hand when the heat wave arrived, and which part throttled on "
            "the one that did not?"
        ),
        scenario=Scenario(
            config=CELL_SITE, workload=FULL,
            environment=Environment(inlet_c=30, dust="heavy", filter_months=6),
            duration_s=900,
            events=[SimEvent(at_s=300, action="set-inlet", value=45)],
            warm_start=True,
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
            warm_start=True,
        ),
    ),
    GuidedScenario(
        id="hdd-mistake",
        title="The HDD mistake",
        narration=[
            L(
                novice=(
                    "Suppose somebody specced spinning hard drives for a "
                    "server that lives beside a busy road, because they "
                    "were cheaper per terabyte. (Dell does not offer them "
                    "on these sleds, which take flash only; this run "
                    "shows why.) Spinning drives read by "
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
                    "A thought experiment: Dell's XR8000 and XR4000 take "
                    "M.2 flash only, and this build shows what that "
                    "choice avoids. The HDD build under vehicle-class "
                    "vibration, database workload. Nothing fails: the instrument "
                    "to watch is storage performance lost — the head-"
                    "repositioning tax, ~40% at this vibration class "
                    "(an estimate, honestly labeled). Flip the build to "
                    "SSDs and the number goes to zero. The validation "
                    "panel warned at configuration time; this is the "
                    "warning, lived."
                ),
                expert=(
                    "Counterfactual (real sleds are M.2-only). HDD + "
                    "vehicle vibe: ~40% throughput tax (estimate), no "
                    "failure event. SSD: 0."
                ),
            ),
        ],
        question="Switch the build to SSDs mid-comparison — what changed, and what stayed exactly the same?",
        scenario=Scenario(
            config=HDD_MISTAKE, workload=EDGE_DB,
            environment=Environment(inlet_c=30, vibration="vehicle"),
            duration_s=600,
            warm_start=True,
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
                    "reserve for a hot day. Dell's guide also lowers the "
                    "rated maximum temperature as a site climbs — by "
                    "about twenty degrees at this height, to roughly 35. "
                    "Add the mountain sun and a "
                    "dusty summer, and a machine that was comfortable at "
                    "sea level spends the afternoon near its limits. "
                    "Altitude is one more slider the outside world gets "
                    "to move."
                ),
                standard=(
                    "The cell-site build at 2,500 m: air density is "
                    "down ~22%, mass flow per CFM with it, so the fans "
                    "run measurably faster for the same silicon "
                    "temperatures. Dell's derating is steep in the "
                    "rugged classes: 1 °C of rated maximum per 80 m "
                    "above 900 m in the −5…55 °C class, so 2,500 m takes "
                    "20 °C off and the rated ceiling here is about "
                    "35 °C. At t=300 the afternoon brings 42 °C — a run "
                    "outside the derated rating, which the validation "
                    "panel flags. The sim holds without throttling; the "
                    "rating is what Dell will stand behind."
                ),
                expert=(
                    "2,500 m: ρ −22%, rpm up, margin down. NEBS3 derate "
                    "1 °C/80 m above 900 m → rated max ≈35 °C; the 42 °C "
                    "afternoon at t=300 is out of rating, in-sim "
                    "survivable."
                ),
            ),
        ],
        question="Set altitude to 0 m and re-run — how much harder were the fans working here to hold the same CPU temperature?",
        scenario=Scenario(
            config=CELL_SITE, workload=RAN,
            environment=Environment(inlet_c=35, altitude_m=2500, dust="moderate"),
            duration_s=900,
            events=[SimEvent(at_s=300, action="set-inlet", value=42)],
            warm_start=True,
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
                "make hotter exhaust than they would in a data hall. "
                "For the first seconds after a cold start or a change "
                "of load, the chips are still soaking up some of their "
                "own heat, so the exhaust lags a little behind this "
                "sum until they settle."
            ),
            standard=(
                "Each zone's outlet is its inlet plus Q/(ṁ·cp): heat "
                "in watts over mass flow times air's specific heat "
                "(1005 J/kg·K). Zones chain front to back, and summing "
                "them gives the whole-box identity exhaust = inlet + "
                "DC/(ṁ·cp). The rugged twist is that ṁ is contested: "
                "fouling shrinks CFM at a given rpm, and altitude "
                "shrinks the mass each CFM carries. The identity is "
                "exact once temperatures settle; while the CPU and "
                "accelerator masses are still warming, the watts they "
                "store are subtracted from the exhaust."
            ),
            expert=(
                "T_out = T_in + Q/(ṁcp); zones chain; Σ gives the "
                "exhaust identity at steady state (transient: minus "
                "heat stored in the CPU/accel masses). ṁ eroded by "
                "fouling (CFM) and altitude (ρ)."
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
                "rpm³. Six months of heavy dust (~42%) takes the fan "
                "wall from part speed to its full 72 W at load, and — "
                "the sharper cost — leaves the controller no headroom "
                "when the heat wave lands."
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
                "(≈90% at 10% load, 96% near 50%, 94% at 100% — an "
                "approximation; Dell's XR supplies are Platinum or "
                "Titanium depending on the unit). In 1+1 the pair "
                "shares load so each sits lower on the curve; "
                "single-feed edge sites sometimes run 1+0 and take the "
                "availability risk instead, though Dell's XR8000 guide "
                "requires dual PSUs for its NEBS ratings."
            ),
            expert=(
                "AC = DC/η(load). Piecewise Titanium-class curve "
                "(estimate). 1+0 is a site decision; Dell's NEBS "
                "ratings on the XR8000 assume dual PSUs."
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
