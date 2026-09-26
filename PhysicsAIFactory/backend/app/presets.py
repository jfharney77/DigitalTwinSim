"""Presets and the teaching layer — backend data.

Factory presets (sizing bundles), training-job presets, guided scenarios
(scripted walkthroughs that set the scenario and narrate what to watch),
and Explain entries (the equation behind each headline instrument, with
placeholders the frontend substitutes live). Teaching prose carries
reading levels 1/3/5.
"""

from __future__ import annotations

from .leveling import L
from .models import (
    ComputeBlock,
    CostBlock,
    DataBlock,
    Explain,
    FabricBlock,
    FacilityBlock,
    FactoryConfig,
    FactoryPreset,
    GuidedScenario,
    JobPreset,
    ResilienceBlock,
    Scenario,
    SimEvent,
    TrainingJob,
)

# --- Factory presets --------------------------------------------------------

PILOT = FactoryConfig(
    compute=ComputeBlock(racks=1),
    data=DataBlock(storage_gbps=150),
    facility=FacilityBlock(mw_budget=0.15),
)

FACTORY = FactoryConfig(
    compute=ComputeBlock(racks=8),
    data=DataBlock(storage_gbps=1200),
    facility=FacilityBlock(mw_budget=1.2),
)

STARVED = FactoryConfig(
    compute=ComputeBlock(racks=16),
    data=DataBlock(storage_gbps=400),
    facility=FacilityBlock(mw_budget=2.5),
)

MEGA = FactoryConfig(
    compute=ComputeBlock(racks=64),
    data=DataBlock(storage_gbps=8000),
    facility=FacilityBlock(mw_budget=8.0),
)

FACTORY_PRESETS = [
    FactoryPreset(id="pilot", name="Pilot", config=PILOT,
                  blurb="One rack, one lesson: even a pilot is a factory in miniature."),
    FactoryPreset(id="factory", name="AI factory", config=FACTORY,
                  blurb="8 racks, 576 GPUs, a data platform that keeps up — the balanced build."),
    FactoryPreset(id="starved", name="Starved", config=STARVED,
                  blurb="16 racks of world-class compute behind a quarter of the storage it needs."),
    FactoryPreset(id="mega", name="Mega", config=MEGA,
                  blurb="64 racks at the edge of an 8 MW budget — no headroom for weather."),
]

# --- Training-job presets ---------------------------------------------------

FRONTIER_LLM = TrainingJob()
MOE = TrainingJob(tokens_per_gpu_s=350, data_gbps_per_gpu=2.5,
                  state_gb_per_gpu=16, ramp_h=24)
VISION = TrainingJob(tokens_per_gpu_s=60, data_gbps_per_gpu=6.0,
                     state_gb_per_gpu=4, ramp_h=12)

JOB_PRESETS = [
    JobPreset(id="frontier-llm", name="Frontier LLM", job=FRONTIER_LLM),
    JobPreset(id="moe", name="Mixture-of-experts", job=MOE),
    JobPreset(id="vision", name="Vision model", job=VISION),
]

# --- Guided scenarios --------------------------------------------------------

GUIDED_SCENARIOS = [
    GuidedScenario(
        id="stand-up",
        title="Stand up an AI factory",
        narration=[
            L(
                novice=(
                    "This is the whole story, squeezed into twenty days: "
                    "buying the racks, installing them, a day of testing, "
                    "and then, finally, training. A token is a small piece "
                    "of text the model learns from, and tokens per second "
                    "is the factory's output. Watch the top-left tile stay "
                    "at zero for the first four and a half days while the "
                    "cost tile counts up anyway. That wait is the time to "
                    "the first training token. The install pace used here, "
                    "two hours per rack, is the average xAI reached across "
                    "its whole Colossus build with many crews working at "
                    "once. It is not how long one crew needs for one rack. "
                    "Once training starts, each of the other tiles reports "
                    "on one of the blocks on the map."
                ),
                standard=(
                    "The full arc: procurement, rack install, bring-up, "
                    "ramp, steady training. Install runs at 2 h per rack, "
                    "which is the Colossus whole-project average (122 days "
                    "for about 1,500 racks, many crews in parallel), not "
                    "the time one crew needs for one liquid-cooled rack. "
                    "The headline is the time to the first training token: "
                    "the cost meter charges hardware amortization from hour "
                    "zero, and tokens start at hour 112. At steady state, "
                    "read the dashboard as a loop: tokens/s is compute × "
                    "fabric × data × resilience, MW and PUE price it, and "
                    "$/Mtok divides one by the other. Every earlier sim in "
                    "this suite is one line item here."
                ),
                expert=(
                    "Procure → install → bring-up → ramp; first training "
                    "token at t = 112 h (stand-up time, not serving-latency "
                    "TTFT). Install 2 h/rack is a project throughput "
                    "(Colossus, parallel crews), applied serially: a floor, "
                    "not a crew-hours model. Steady tokens/s = N·rate·Πgates; "
                    "$/Mtok = (energy + amortization)/tokens."
                ),
            ),
        ],
        question=(
            "Pause at hour 112, the first training token. How much does the "
            "cost tile say has been charged by then, and which phase of the "
            "wait would you shorten first?"
        ),
        scenario=Scenario(config=FACTORY, job=FRONTIER_LLM, duration_h=480),
    ),
    GuidedScenario(
        id="starved-cluster",
        title="The starved cluster",
        narration=[
            L(
                novice=(
                    "This factory trains on images, which are heavy to "
                    "read, so its storage is sized to match. Ten days in, "
                    "something breaks in the storage and it can deliver "
                    "only a quarter of what it did. The cause doesn't "
                    "matter. Watch the GPUs: nothing overheats and nothing "
                    "crashes. They wait. The storage now serves 1,200 of "
                    "the 3,456 GB/s the GPUs ask for, so the idle tile "
                    "jumps to 65% and tokens per second fall by the same "
                    "65%. Now look at facility power. It falls by only "
                    "about a quarter, because a GPU that is waiting for "
                    "data keeps spinning and still uses most of its "
                    "power. The hardware cost keeps counting too. So each "
                    "token costs more, and the cost tile climbs for the "
                    "rest of the run."
                ),
                standard=(
                    "A vision job (6 GB/s per GPU, 3,456 GB/s demand) on "
                    "a 4,800 GB/s platform. At t = 250 h the platform "
                    "degrades to 25% of nominal, 1,200 GB/s. Utilization "
                    "follows min(1, supply/demand) at once: idle due to "
                    "data jumps to 65% (not 75%, because the platform had "
                    "headroom) and tokens/s falls by the same 65%. Facility "
                    "power falls only about 23%, from 0.90 to 0.69 MW: a "
                    "starved GPU busy-waits and still burns an estimated "
                    "65% of the power of the work it was denied. "
                    "Amortization never pauses, so $/Mtok climbs from "
                    "about $11.4 to $13.9 by the end of the run. This is "
                    "the GPU twin's memory-bound roofline regime, "
                    "factory-sized. The job is a vision model on purpose: "
                    "text-only LLM pretraining reads far less than this, "
                    "and its storage pressure comes from checkpoint bursts."
                ),
                expert=(
                    "Vision job, D = 3,456 GB/s; S 4,800 → 1,200 at t = 250. "
                    "util = S/D = 0.35, idle 65%, tokens −65%. P_gpu follows "
                    "u + 0.65·(u_demanded − u) (stall estimate, shared with "
                    "PhysicsCompute), so facility −23%. $/Mtok ≈ k/util with "
                    "capex dominant. Text-only LLM ingest is kB/s per GPU; "
                    "there the storage term is t_ckpt, not S/D."
                ),
            ),
        ],
        question=(
            "Compare hour 249 with hour 300. By what share did tokens per "
            "second fall, by what share did facility power fall, and what "
            "happened to $ / million tokens between them?"
        ),
        scenario=Scenario(
            config=FACTORY.model_copy(update={"data": DataBlock(storage_gbps=4800)}),
            job=VISION, duration_h=480,
            events=[SimEvent(at_h=250, action="degrade-storage", value=25)],
        ),
    ),
    GuidedScenario(
        id="checkpoint-goldilocks",
        title="Checkpoint Goldilocks",
        narration=[
            L(
                novice=(
                    "This run saves its work only every eight hours. Watch "
                    "the token counter when a GPU fails. It doesn't only "
                    "pause, it goes backwards to the last save point, "
                    "because everything since then must be done again. The "
                    "event log shows how many billion tokens each failure "
                    "threw away. The losses get smaller through the run, "
                    "and that is arithmetic rather than luck: failures "
                    "arrive every 87 hours, saves happen every 8, and 87 "
                    "is not a whole number of 8s, so each failure lands "
                    "one hour closer to its save than the one before. "
                    "Nothing here is random. Now picture the opposite mistake: "
                    "saving every five minutes, so often that the saving "
                    "slows every hour of training. Between the two lies a "
                    "best interval, and you can work it out from how often "
                    "failures come and how long a save takes. Set the "
                    "checkpoint slider to 60 minutes, then to 5, and "
                    "compare 'tokens produced' in the run summary. The "
                    "panel on the left works the best interval out from "
                    "the formula — about 29 minutes here — but this "
                    "simulator counts in whole hours, so anything under "
                    "an hour looks the same to it: 60 minutes scores as "
                    "well as 29, and neither is wrong."
                ),
                standard=(
                    "Checkpoint interval set to 480 min. One checkpoint "
                    "write takes t_ckpt ≈ 4.8 s here (an estimate: 10 GB "
                    "of state per GPU × 576 GPUs ÷ 1,200 GB/s), and the "
                    "cluster fails about every 87 h (50k h per GPU ÷ 576). "
                    "The Young/Daly rule, the classic formula for the "
                    "interval that balances write time against lost work, "
                    "gives √(2·t_ckpt·MTBF) ≈ 29 min. Each failure rewinds "
                    "the token counter to the last checkpoint: the log "
                    "shows 2.39 B tokens lost at the first failure, "
                    "shrinking to 0.80 B by arithmetic rather than luck: "
                    "87 h is not a whole multiple of the 8 h save "
                    "interval, so each failure lands exactly an hour "
                    "closer to its checkpoint than the last, and the loss "
                    "falls by a flat 0.40 B each time. Re-run at 60 min and "
                    "at 5 min and read 'tokens produced': 60 wins. One "
                    "caveat: this engine ticks in whole hours, so rollback "
                    "loss under an hour rounds away and the curve is flat "
                    "below 60 min. 30 min scores slightly under 60 here "
                    "for that reason, and so does the panel's own 29 — "
                    "the validation panel reports the formula's optimum, "
                    "not this trace's, and near the top the curve is "
                    "broad enough that the two are within noise."
                ),
                expert=(
                    "I = 480 min ≫ I* = √(2·t_ckpt·MTBF) ≈ 29 min (t_ckpt ≈ "
                    "4.8 s, M ≈ 87 h). 600 h totals: 182.7 B at 480, 190.5 B "
                    "at 60, 187.7 B at 5. Two caveats: sub-hour rollback is "
                    "below the 1 h tick, so the curve is flat under 60 min "
                    "and 30 does not beat 60; and failures here are "
                    "periodic, not memoryless, so Young/Daly is a guide, "
                    "not this trace's exact optimum. The interior optimum "
                    "is test-pinned at 5/60/480 only."
                ),
            ),
        ],
        question=(
            "Run 5, 60 and 480 minutes and read 'tokens produced' in the run "
            "summary each time. Which finishes with the most, and how many "
            "billion tokens separate it from the other two?"
        ),
        scenario=Scenario(
            config=FACTORY.model_copy(update={
                "resilience": ResilienceBlock(checkpoint_interval_min=480),
            }),
            job=FRONTIER_LLM, duration_h=600,
        ),
    ),
    GuidedScenario(
        id="warm-day",
        title="Warm day at 90% of budget",
        narration=[
            L(
                novice=(
                    "This factory was sized close to its building's power "
                    "limit — 90% on a mild day. Ten days in, the weather "
                    "turns: the cooling plant works harder, so the same "
                    "computing suddenly needs more total power, and the "
                    "building has none to give. (The log calls this PUE: "
                    "total building power divided by computer power, so "
                    "PUE +0.2 means 20% more overhead.) Something must "
                    "yield, and "
                    "the least bad choice is the GPUs slowing down "
                    "gracefully. Watch tokens per second dip while the "
                    "power line hugs the budget ceiling — the weather, "
                    "showing up in the arithmetic. To price it, read "
                    "'tokens produced' in the run summary, then raise the "
                    "facility budget slider and read it again: the "
                    "difference is what the warm spell cost. Keep raising "
                    "the budget until the number stops improving, and "
                    "that is the headroom the day needed."
                ),
                standard=(
                    "Facility sized to ~90% of budget; at t=250 h a warm "
                    "day adds 0.2 to PUE. Facility = IT × PUE now exceeds "
                    "the budget, so the engine sheds load — GPU clocks "
                    "cap until facility sits exactly on the ceiling — and "
                    "tokens/s pays the difference until the weather "
                    "breaks at t=350 h. PUE headroom and compute headroom "
                    "are the same budget wearing different clothes. The "
                    "page shows no counterfactual, so measure it: note "
                    "'tokens produced', raise the facility budget, "
                    "re-read, and sweep upward until the total stops "
                    "moving — that budget is the headroom the warm day "
                    "would have needed."
                ),
                expert=(
                    "ΔPUE +0.2 at 90% budget → cap: u solved so IT·PUE = "
                    "budget; tokens ∝ u. Cooling excursions are compute "
                    "excursions at tight budgets. No counterfactual is "
                    "displayed: sweep B and re-read tokens_total."
                ),
            ),
        ],
        question=(
            "Note 'tokens produced' in the run summary, then raise the "
            "facility budget slider and read it again. How many billion "
            "tokens did the warm spell cost, and what budget stops the "
            "total improving?"
        ),
        scenario=Scenario(
            config=FACTORY.model_copy(update={
                "facility": FacilityBlock(mw_budget=0.95),
            }),
            job=FRONTIER_LLM, duration_h=480,
            events=[
                SimEvent(at_h=250, action="warm-day", value=0.2),
                SimEvent(at_h=350, action="end-warm-day"),
            ],
        ),
    ),
]

# --- Explain entries ----------------------------------------------------------

EXPLAINS = [
    Explain(
        id="tokens-per-s",
        title="Tokens per second",
        equation="tokens/s = GPUs × rate × (data_util × fabric_eff × (1 − ckpt tax) × ramp)",
        inputs=["GPUs online", "data availability", "fabric efficiency",
                "checkpoint tax", "tokens/s"],
        explanation=L(
            novice=(
                "A token is a small piece of text (or of an image) that "
                "the model learns from, and tokens per second is the "
                "factory's output. Start with what the GPUs could do — "
                "each one works through tokens at some rate when nothing "
                "holds it back — and "
                "then multiply by every gate that does hold it back: "
                "whether data arrives fast enough, how much the network "
                "loses coordinating thousands of chips, the time spent "
                "saving progress, and the early-days ramp while the run "
                "is being tuned. Each gate is a number between zero and "
                "one, so the gates only ever subtract. The factory's "
                "output is the product of its weakest links."
            ),
            standard=(
                "Peak throughput (GPUs × per-GPU rate — an illustrative "
                "200 tokens/s for a frontier model; Meta's Llama 3.1 405B "
                "figures work out to ~140 on H100s) is multiplied by "
                "four gates, each 0–1: data availability min(1, "
                "supply/demand), fabric efficiency (topology and "
                "oversubscription), the checkpoint write tax, and the "
                "ramp. The gates are the earlier sims in this suite, "
                "reduced to their one number each."
            ),
            expert=(
                "N·r·Πg, g ∈ {min(1,S/D), η_fabric, 1−τ_ckpt, ramp}. "
                "Each gate is one sibling sim's summary statistic."
            ),
        ),
    ),
    Explain(
        id="idle-data",
        title="GPU idle due to data",
        equation="idle% = (1 − min(1, storage GB/s ÷ demand GB/s)) × 100",
        inputs=["storage supply", "cluster demand", "idle %", "tokens/s"],
        explanation=L(
            novice=(
                "Every GPU wants a steady diet of training data. Add up "
                "the appetite of every GPU and compare it with what the "
                "storage can serve: if the kitchen can only deliver a "
                "quarter of the orders, the diners spend three quarters "
                "of their time waiting, no matter how fast they could "
                "eat. This gauge is that waiting, as a percentage — the "
                "single most common way expensive AI clusters are "
                "quietly wasted."
            ),
            standard=(
                "Demand is GPUs × per-GPU data rate; supply is the "
                "platform's aggregate GB/s. Utilization is their ratio, "
                "capped at 1, and this gauge is the shortfall. It is the "
                "GPU twin's memory-bound roofline regime one level up: "
                "same shape, the axis relabeled from HBM bandwidth to "
                "storage bandwidth."
            ),
            expert=(
                "1 − min(1, S/D). The roofline's memory-bound branch, "
                "promoted from HBM to the data platform."
            ),
        ),
    ),
    Explain(
        id="facility-mw",
        title="Facility power",
        equation="facility MW = (GPU + fabric + storage + other) × PUE ≤ budget",
        inputs=["GPU MW", "fabric MW", "storage MW", "PUE", "facility MW", "budget"],
        explanation=L(
            novice=(
                "Add up what the computers draw, then multiply by the "
                "building's overhead — mostly cooling, and the number on "
                "the PUE tile — to get what the "
                "utility actually bills. That total must fit under the "
                "building's limit at every moment. In this simulator, "
                "when it doesn't fit, the GPUs slow down until it does: "
                "the gentlest of the available failures, and one you can "
                "watch happen on a warm day."
            ),
            standard=(
                "The power identity, asserted every tick: subsystem "
                "draws sum to IT MW, facility = IT × PUE (≈1.15 liquid, "
                "≈1.45 air), and the budget is enforced by shedding GPU "
                "clocks — solving for the utilization at which facility "
                "sits exactly on the ceiling (the tile then reads "
                "CAPPED). The multiplier is the PUE tile's number. The "
                "R760Thermal and IR7000 "
                "sims are this identity at one-box and one-rack scale."
            ),
            expert=(
                "ΣP·PUE ≤ B enforced by solving u s.t. equality. Same "
                "identity as R760Thermal/IR7000, top of the stack."
            ),
        ),
    ),
    Explain(
        id="pue",
        title="PUE — power usage effectiveness",
        equation="PUE = facility MW ÷ IT MW",
        inputs=["cooling type", "weather", "PUE", "facility MW", "budget"],
        explanation=L(
            novice=(
                "PUE stands for power usage effectiveness: total building "
                "power divided by the power the computers use. A PUE of "
                "1.15 means that for every 100 watts of computing the "
                "building draws 115, and the extra 15 goes mostly to "
                "cooling. Lower is better and 1.0 would be perfect. On a "
                "warm day the cooling works harder, so PUE rises, and the "
                "same computing needs more total power. If that total "
                "would go over the building's limit, the facility power "
                "tile reads CAPPED and the GPUs slow down to fit."
            ),
            standard=(
                "Power usage effectiveness: facility power ÷ IT power, "
                "the building's overhead multiplier. Here it is an input "
                "rather than a result: about 1.15 for direct liquid "
                "cooling and 1.45 for air (both estimates), plus whatever "
                "a warm-day event adds. Because facility = IT × PUE must "
                "stay under the budget, a PUE excursion at a tight budget "
                "comes straight out of GPU clocks. That is the CAPPED "
                "state on the facility power tile."
            ),
            expert=(
                "PUE = P_facility/P_IT; exogenous here (1.15 liquid, 1.45 "
                "air, + event Δ). At fixed B, ΔPUE maps to Δu via the cap."
            ),
        ),
    ),
    Explain(
        id="usd-per-mtok",
        title="Cost per million tokens",
        equation="$/Mtok = (energy $ + amortized capex $) ÷ tokens produced",
        inputs=["facility MW", "$ per kWh", "hardware cost, spread over its life",
                "tokens total", "$/Mtok"],
        explanation=L(
            novice=(
                "The dollar figures here are illustrative, and 'charged so "
                "far' is not cash paid out: it is what the run has used "
                "up. Two meters run all the time: the electricity bill "
                "(facility power times the tariff) and the cost of the "
                "hardware itself, spread over its useful life — and the "
                "hardware meter is usually the bigger one. Divide "
                "everything spent by every token produced and you get "
                "the factory's unit price. Notice that anything that "
                "wastes tokens — starved storage, missed checkpoints, a "
                "warm day — raises this number without touching either "
                "meter."
            ),
            standard=(
                "Energy (facility MW × tariff) plus straight-line rack "
                "amortization ($3.0 M per rack over four years, "
                "illustrative), divided by cumulative tokens. The "
                "'charged so far' figure is that sum to date, not cash "
                "out. Amortization "
                "dominates at today's rack prices, which is why the idle "
                "gauge is priced in dollars: a GPU waiting for data costs "
                "nearly as much as one working. Every inefficiency on "
                "this dashboard reappears here, divided by fewer tokens."
            ),
            expert=(
                "(MW·tariff + capex/amort)/tokens; capex-dominated, so "
                "$/Mtok ≈ k/utilization. Idle is priced, not just shown."
            ),
        ),
    ),
    Explain(
        id="ttft",
        title="Time to the first training token",
        equation="TTFT = procure 72 h + racks × 2 h install + bring-up 24 h",
        inputs=["racks", "install hours per rack", "bring-up", "TTFT",
                "hardware cost, spread over its life"],
        explanation=L(
            novice=(
                "How long after the order until the first piece of work "
                "gets done. Three waits, added up: about three days to "
                "get the hardware (compressed here — in real life it is "
                "months), then roughly two hours for each rack to be "
                "installed and plumbed, then a day of testing the whole "
                "cluster before training starts. Eight racks make that "
                "72 + 16 + 24 = 112 hours. The tile counts down to it. "
                "The two hours per rack is the average pace xAI reached "
                "across its whole Colossus build, with many crews "
                "working at once — not how long one crew needs for one "
                "rack. This is the only tile that measures waiting, and "
                "the hardware meter runs through all of it."
            ),
            standard=(
                "Stand-up time, not serving latency: procurement (72 h, "
                "compressed for the sim) + racks × install_h_per_rack "
                "(2 h, the Colossus whole-project average — 122 days for "
                "about 1,500 racks with parallel crews, applied serially "
                "here as a floor) + bring-up (24 h, estimate). Eight "
                "racks give 112 h. Doubling the cluster lengthens only "
                "the middle term, so TTFT grows sub-linearly while "
                "amortization, which runs from hour zero, grows linearly "
                "— which is why the cost tile reads high on day one."
            ),
            expert=(
                "TTFT = 72 + 2N + 24 h (N racks); install rate is a "
                "project throughput applied serially. Only the 2N term "
                "scales; capex accrual is linear in N from t = 0, so "
                "$/Mtok at first token rises with N."
            ),
        ),
    ),
    Explain(
        id="checkpoint",
        title="Checkpoint economics",
        equation="overhead(I) = t_ckpt/(I + t_ckpt) + rollback(I)/MTBF  →  I* = √(2·t_ckpt·MTBF)",
        inputs=["checkpoint interval", "write time", "cluster MTBF", "overhead %"],
        explanation=L(
            novice=(
                "Saving your work costs a little time every time you do "
                "it; losing your work costs everything back to the last "
                "save. Save too often and the saving is the waste; too "
                "rarely and one failure erases hours. Because a big "
                "cluster fails on a near-schedule — one GPU's rarity "
                "divided by thousands of GPUs — the best interval is a "
                "formula, not a feeling, and the validation panel works "
                "it out for your build."
            ),
            standard=(
                "t_ckpt is the time one checkpoint write takes: state per "
                "GPU × GPUs ÷ storage GB/s, about 4.8 s on the default "
                "build (an estimate). I is the interval between "
                "checkpoints. The write tax is t_ckpt/(I + t_ckpt); the failure cost "
                "is the expected rollback per cluster-MTBF. They trade "
                "with an interior optimum at the Young/Daly point "
                "I* = √(2·t_ckpt·MTBF). In the engine the rollback is "
                "not a formula but an event: the token counter genuinely "
                "rewinds to the last checkpoint, so the optimum emerges "
                "in the totals. The engine ticks in whole hours, so "
                "rollback loss under an hour rounds away and intervals "
                "below 60 min score about the same."
            ),
            expert=(
                "Young/Daly: I* = √(2·t_c·M), t_c = state/S. Engine "
                "implements rollback literally on periodic (not "
                "memoryless) failures at a 1 h tick: flat below 60 min; "
                "interior optimum test-pinned at 5/60/480."
            ),
        ),
    ),
]
