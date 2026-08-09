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
                    "This is the whole arc, compressed: buying the racks, "
                    "installing them at about two hours each (the pace xAI "
                    "managed for its Colossus system), a day of bring-up, "
                    "and then — finally — tokens. Watch the top-left "
                    "instrument stay at zero for the first several days "
                    "while the cost meter runs anyway: that gap is "
                    "time-to-first-token, and shrinking it is why "
                    "factory-integrated racks exist. Once training starts, "
                    "every other instrument becomes a report card on one "
                    "of the six blocks."
                ),
                standard=(
                    "The full arc: procurement, rack install at the "
                    "Colossus pace (~2 h/rack), bring-up, ramp, steady "
                    "training. Time-to-first-token is the headline — the "
                    "capex meter runs from hour zero, tokens start at hour "
                    "~112. At steady state, read the dashboard as a loop: "
                    "tokens/s is compute × fabric × data × resilience, MW "
                    "and PUE price it, and $/Mtok divides one by the other. "
                    "Every earlier sim in this suite is one line item here."
                ),
                expert=(
                    "Procure → install (2 h/rack) → bring-up → ramp. TTFT "
                    "≈ 112 h; steady tokens/s = N·rate·Πgates; $/Mtok = "
                    "(energy + amortization)/tokens. The suite, as line items."
                ),
            ),
        ],
        question="How many dollars had the factory spent before its first token — and which block would you shrink to cut that?",
        scenario=Scenario(config=FACTORY, job=FRONTIER_LLM, duration_h=480),
    ),
    GuidedScenario(
        id="starved-cluster",
        title="The starved cluster",
        narration=[
            L(
                novice=(
                    "Ten days in, the data platform loses three quarters "
                    "of its throughput — a failed pool, a bad rebuild, it "
                    "doesn't matter. Watch what happens to the GPUs: "
                    "nothing breaks, nothing overheats, they just wait. "
                    "The idle-due-to-data gauge jumps, tokens per second "
                    "falls by the same fraction, and the cost per token "
                    "climbs — because the meter keeps running while the "
                    "arithmetic doesn't. The most expensive part of the "
                    "factory is now pacing the cheapest."
                ),
                standard=(
                    "At t=250 h the data platform degrades to 25% of "
                    "nominal. Utilization follows min(1, supply/demand) "
                    "immediately: idle-due-to-data jumps to ~75%, tokens/s "
                    "falls in proportion, and $/Mtok inflates while the "
                    "facility keeps drawing near-full power — idle GPUs "
                    "still sip, and the amortization clock never pauses. "
                    "This is the GPU twin's memory-bound roofline regime, "
                    "factory-sized."
                ),
                expert=(
                    "Storage ×0.25 at t=250: util snaps to supply/demand, "
                    "idle% = 1−that, tokens ∝ supply, $/Mtok ∝ 1/tokens "
                    "while power barely moves. Roofline, at building scale."
                ),
            ),
        ],
        question="After the degradation, does facility power fall as far as tokens/s does — and what does that asymmetry cost per million tokens?",
        scenario=Scenario(
            config=FACTORY, job=FRONTIER_LLM, duration_h=480,
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
                    "the token counter when a GPU fails — it doesn't just "
                    "pause, it rolls *backwards* to the last save point, "
                    "because everything since then must be redone. Now "
                    "imagine the opposite mistake: saving every five "
                    "minutes, so often that the saving itself slows every "
                    "hour of training. Between the two lies a best "
                    "interval, and it isn't a matter of taste — it's a "
                    "square root you can compute from how often failures "
                    "come and how long a save takes. Try 60 minutes in "
                    "the build panel and compare the final token count."
                ),
                standard=(
                    "Checkpoint interval set to 480 min — far above this "
                    "cluster's Young/Daly optimum (√(2·t_ckpt·MTBF) ≈ 29 "
                    "min; the validation panel computes it). Failures "
                    "arrive on the MTBF schedule (~87 h for 576 GPUs at "
                    "50k h/GPU), and each one rolls the token counter back "
                    "hours. Re-run at 60 min and at 5 min: the middle "
                    "setting wins, because the tax of writing and the "
                    "cost of rewinding trade against each other with an "
                    "interior optimum."
                ),
                expert=(
                    "I=480 min ≫ I*=√(2·t_ckpt·MTBF)≈29 min. Rollbacks "
                    "dominate; at I=5 min the write tax dominates. "
                    "Interior optimum — tested, not asserted."
                ),
            ),
        ],
        question="Which interval — 5, 60, or 480 minutes — finishes this run with the most tokens, and by how much?",
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
                    "building has none to give. Something must yield, and "
                    "the least bad choice is the GPUs slowing down "
                    "gracefully. Watch tokens per second dip while the "
                    "power line hugs the budget ceiling — the weather, "
                    "showing up in the arithmetic."
                ),
                standard=(
                    "Facility sized to ~90% of budget; at t=250 h a warm "
                    "day adds 0.2 to PUE. Facility = IT × PUE now exceeds "
                    "the budget, so the engine sheds load — GPU clocks "
                    "cap until facility sits exactly on the ceiling — and "
                    "tokens/s pays the difference until the weather "
                    "breaks at t=350 h. PUE headroom and compute headroom "
                    "are the same budget wearing different clothes."
                ),
                expert=(
                    "ΔPUE +0.2 at 90% budget → cap: u solved so IT·PUE = "
                    "budget; tokens ∝ u. Cooling excursions are compute "
                    "excursions at tight budgets."
                ),
            ),
        ],
        question="How many billion tokens did the warm spell cost, and what budget headroom would have made it free?",
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
                "Start with what the GPUs could do — each one produces "
                "tokens at some rate when nothing holds it back — and "
                "then multiply by every gate that does hold it back: "
                "whether data arrives fast enough, how much the network "
                "loses coordinating thousands of chips, the time spent "
                "saving progress, and the early-days ramp while the run "
                "is being tuned. Each gate is a number between zero and "
                "one, so the gates only ever subtract. The factory's "
                "output is the product of its weakest links."
            ),
            standard=(
                "Peak throughput (GPUs × per-GPU rate, ~200 tokens/s for "
                "a frontier model — Llama-3 arithmetic) is multiplied by "
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
                "building's overhead — mostly cooling — to get what the "
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
                "sits exactly on the ceiling. The R760Thermal and IR7000 "
                "sims are this identity at one-box and one-rack scale."
            ),
            expert=(
                "ΣP·PUE ≤ B enforced by solving u s.t. equality. Same "
                "identity as R760Thermal/IR7000, top of the stack."
            ),
        ),
    ),
    Explain(
        id="usd-per-mtok",
        title="Cost per million tokens",
        equation="$/Mtok = (energy $ + amortized capex $) ÷ tokens produced",
        inputs=["facility MW", "$ per kWh", "capex amortization", "tokens total", "$/Mtok"],
        explanation=L(
            novice=(
                "Two meters run all the time: the electricity bill "
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
                "amortization, divided by cumulative tokens. Amortization "
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
                "The write tax is t_ckpt/(I + t_ckpt); the failure cost "
                "is the expected rollback per cluster-MTBF. They trade "
                "with an interior optimum at the Young/Daly point "
                "I* = √(2·t_ckpt·MTBF). In the engine the rollback is "
                "not a formula but an event: the token counter genuinely "
                "rewinds to the last checkpoint, so the optimum emerges "
                "in the totals."
            ),
            expert=(
                "Young/Daly: I* = √(2·t_c·M). Engine implements rollback "
                "literally; the optimum is emergent and test-pinned."
            ),
        ),
    ),
]
