"""The factory map — the block diagram the dashboard paints.

Not a floorplan of a building: a diagram of the *couplings*. Compute,
fabric, and data sit on one row because they pass work to each other every
training step; power and cooling underlie them because every block above
drains the same two budgets; operations spans the top because the
timeline (procure → install → bring-up → train) is its axis. Geometry
invariants in the tests pin the story: the fabric sits between compute
and data, and the facility row is beneath everything it feeds.
"""

from __future__ import annotations

from .leveling import L
from .models import FactoryMap, FactoryRegion

ANATOMY = FactoryMap(
    id="ai-factory",
    name="Dell AI Factory · integrated roll-up",
    vendor="Dell Technologies (with NVIDIA)",
    form_factor="factory-scale system of systems",
    generation="XE9712-class racks · Spectrum-X / Quantum fabrics · 2024–26",
    year=2026,
    width=100,
    height=60,
    overview=L(
        novice=(
            "An AI factory is a building full of computers whose only "
            "product is a trained model, and this page shows the whole "
            "thing as six connected blocks. The compute block holds the "
            "racks of GPUs that do the arithmetic. The fabric block is "
            "the network that lets thousands of GPUs act like one "
            "machine. The data block is the storage that feeds them — "
            "and if it feeds them too slowly, the expensive GPUs simply "
            "wait, which is the number this dashboard watches most "
            "closely. Underneath, the power block and the cooling block "
            "are the building itself: every watt the computers use must "
            "come in through one and leave as heat through the other. "
            "The resilience block is the insurance policy — regular "
            "save-points so a failure loses minutes, not days. Size any "
            "block wrong and the mistake shows up as a number on the "
            "dashboard, usually on a different block than the one you "
            "got wrong. That coupling is the whole lesson."
        ),
        standard=(
            "The factory as six coupled blocks. Compute (racks of "
            "XE9712-class 72-GPU systems) produces tokens at a rate the "
            "other blocks gate: the fabric multiplies every training "
            "step by its efficiency, the data platform's throughput "
            "caps utilization at min(1, supply/demand) — the "
            "GPU-idle-due-to-data % on the dashboard — and the "
            "resilience block taxes every hour with checkpoint writes "
            "so that failures roll back minutes instead of days. The "
            "facility row underlies it all: IT megawatts times PUE must "
            "fit the building's budget, and when it doesn't, the engine "
            "sheds GPU clocks rather than trip the feed. Each block is "
            "a first-order aggregate of a product this repo simulates "
            "in detail elsewhere; this map is where their couplings "
            "become one dashboard."
        ),
        expert=(
            "Six blocks, three couplings: tokens/s = N·rate·(data_util "
            "× fabric_eff × (1−ckpt tax) × ramp); facility = IT×PUE ≤ "
            "budget via clock shed; rollback-to-checkpoint on "
            "MTBF-deterministic failures. Aggregates stand in for the "
            "per-product engines. The map is the coupling graph."
        ),
    ),
    intro=L(
        novice=(
            "Build an AI factory and watch it run. You choose how many "
            "GPU racks to buy, how fast the storage is, how much power the "
            "building can supply, and how often the work is saved. Six "
            "tiles then tell you how it is going: how much work gets done "
            "each second, how much power the building draws, how much of "
            "that power is overhead, how long the GPUs sit waiting for "
            "data, what each unit of work costs, and how long you waited "
            "for the first result. Each block on the map is a simple "
            "stand-in for a product that has its own detailed simulator "
            "in this collection. What this page adds is how the blocks "
            "affect each other."
        ),
        standard=(
            "Size a training cluster, its fabric, its data platform, its "
            "facility, and its checkpoint discipline, then watch one "
            "dashboard: tokens per second, megawatts, PUE, the share of "
            "GPU time lost waiting for data, cost per million tokens, and "
            "the time until the first training token exists at all. Each "
            "block is a first-order stand-in for a product this repo "
            "simulates in detail. The couplings between them are what "
            "this page adds."
        ),
        expert=(
            "Size compute, fabric, data, facility and checkpointing; read "
            "six coupled instruments. Blocks are first-order aggregates of "
            "the per-product sims; the couplings are this page's content."
        ),
    ),
    regions=[
        FactoryRegion(
            id="ops", kind="operations", label="Operations — procure → install → bring-up → train",
            x=2, y=2, w=96, h=8,
            description=L(
                novice=(
                    "The timeline. First the racks are bought, then "
                    "installed, then tested for a day, and only then does "
                    "training start. The install pace here, about two "
                    "hours per rack, is the average xAI reached on its "
                    "Colossus build with many crews working at once. The "
                    "cost of the hardware is charged from the first hour, "
                    "so every hour spent in this block is paid for with "
                    "nothing produced yet."
                ),
                standard=(
                    "The timeline layer: procurement, factory-integrated rack "
                    "install (about two hours per rack, the Colossus "
                    "whole-project average rather than one crew's time on "
                    "one rack), cluster bring-up, then the training ramp. "
                    "Time to the first training token is this block's "
                    "headline: every hour here is an hour the amortization "
                    "meter runs with zero tokens out."
                ),
                expert=(
                    "procure 72 h (compressed) + 2 h/rack (Colossus "
                    "throughput, applied serially) + 24 h bring-up. "
                    "Amortization accrues from t = 0."
                ),
            ),
        ),
        FactoryRegion(
            id="compute", kind="compute", label="Compute — GPU racks",
            x=2, y=14, w=40, h=30,
            description=L(
                novice=(
                    "The racks of GPUs, the chips that do the training "
                    "arithmetic. Each rack holds 72 of them, wired together "
                    "so tightly that they behave like one very large GPU. "
                    "This block turns electricity into finished work, and "
                    "every other block on the map either feeds it or slows "
                    "it down. The small squares are the racks; they light "
                    "up as they are installed."
                ),
                standard=(
                    "Racks of XE9712-class systems, 72 GPUs each, fused by "
                    "NVLink inside the rack. This block turns megawatts into "
                    "tokens at a rate everything else on this map multiplies "
                    "or taxes. Its own physics (the NVLink fuse, the "
                    "coolant, the on-package HBM memory) lives in the "
                    "DellPowerEdgeXE9712 twin."
                ),
                expert=(
                    "N × 72 GPUs, NVL72 domains. tokens/s = N·r·Πgates; "
                    "P_gpu = P_idle + (P_peak − P_idle)·u_power. Rack "
                    "physics: DellPowerEdgeXE9712."
                ),
            ),
        ),
        FactoryRegion(
            id="fabric", kind="fabric", label="Fabric",
            x=46, y=14, w=16, h=30,
            description=L(
                novice=(
                    "The network that joins the racks. It is drawn between "
                    "the GPUs and the storage because everything crosses "
                    "it: the training data on its way in, and the results "
                    "the GPUs must share with each other after every step "
                    "(a group exchange called a collective). If you buy "
                    "less network capacity than the racks can use, which "
                    "is called oversubscribing it, every training step "
                    "waits a little, and the efficiency number on this "
                    "block drops. That is the percentage in the corner "
                    "of the block, written with the Greek letter eta (η) "
                    "at the higher reading levels: 100% would be a "
                    "network that costs nothing to cross."
                ),
                standard=(
                    "The scale-out network (Spectrum-X Ethernet or Quantum "
                    "InfiniBand), drawn between compute and data because "
                    "every byte of training data and every collective, the "
                    "all-GPU exchange that ends each training step, "
                    "crosses it. Oversubscribe it (less uplink capacity "
                    "than the racks can offer) and every training step "
                    "pays; the SN6000 and Quantum-X800 twins carry the "
                    "packet-level story."
                ),
                expert=(
                    "η_fabric = base (0.96 IB / 0.95 Spectrum-X, vendor "
                    "claims) − 0.10 per unit of oversubscription. One "
                    "number; SN6000 and Quantum-X800 hold the rest."
                ),
            ),
        ),
        FactoryRegion(
            id="data", kind="data", label="Data platform",
            x=66, y=14, w=32, h=30,
            description=L(
                novice=(
                    "The storage that feeds training data to the GPUs. "
                    "Only one number matters here: how many gigabytes it "
                    "can deliver each second. If the GPUs ask for more "
                    "than it can deliver, they wait, and the 'GPU idle — "
                    "waiting for data' tile shows how much of their time "
                    "is lost. Storage is the cheapest block to buy and the "
                    "most expensive one to get wrong, because the waiting "
                    "GPUs cost far more than the storage would have."
                ),
                standard=(
                    "The storage that feeds the cluster, reduced to the one "
                    "number that gates training: aggregate GB/s. When supply "
                    "falls below the cluster's demand, utilization follows "
                    "supply/demand exactly and the dashboard's GPU-idle-due-"
                    "to-data % rises to match. It is the cheapest block to "
                    "get wrong and the most expensive to have gotten wrong. "
                    "The DellExascale twin shows how the bytes actually move."
                ),
                expert=(
                    "S GB/s aggregate. util = min(1, S/D); t_ckpt = "
                    "state/S. 10 W per GB/s (estimate). Data path: "
                    "DellExascale."
                ),
            ),
        ),
        FactoryRegion(
            id="power", kind="power", label="Power",
            x=2, y=48, w=30, h=10,
            description=L(
                novice=(
                    "The building's electricity supply, which has a fixed "
                    "limit. Everything the computers draw, plus the "
                    "overhead for cooling, has to fit under it. When it "
                    "doesn't fit, this simulator slows the GPUs down until "
                    "it does, and the power tile reads CAPPED. That is the "
                    "gentle way to fail. The other way is a tripped "
                    "breaker and a dark hall."
                ),
                standard=(
                    "The building's feed. The identity is merciless: facility "
                    "MW = IT MW × PUE, and the budget is a wall. When the sum "
                    "crosses it, this simulator lowers GPU clock speeds "
                    "until it fits (the polite failure) because the "
                    "impolite one is a breaker."
                ),
                expert=(
                    "P_IT·PUE ≤ B, enforced by solving u at equality. No "
                    "breaker model; see PhysicsRackPower."
                ),
            ),
        ),
        FactoryRegion(
            id="cooling", kind="cooling", label="Cooling",
            x=36, y=48, w=30, h=10,
            description=L(
                novice=(
                    "Every watt the computers use turns into heat, and "
                    "removing that heat takes more electricity. PUE "
                    "measures that overhead: total building power divided "
                    "by computer power. Liquid cooling keeps it near 1.15, "
                    "so 15% extra. Air cooling is nearer 1.45. A warm day "
                    "pushes either one up, and if the building is already "
                    "close to its power limit, the GPUs have to slow down "
                    "to make room."
                ),
                standard=(
                    "Every IT watt becomes heat; PUE (facility power ÷ IT "
                    "power) is the markup the building charges to remove "
                    "it. Liquid cooling holds it near 1.15, air nearer "
                    "1.45, and a warm day adds to either. At a tight power "
                    "budget that becomes a compute problem. The IR7000 "
                    "twin owns this loop."
                ),
                expert=(
                    "PUE exogenous: 1.15 liquid, 1.45 air (estimates), + "
                    "event Δ. Couples to compute only through the cap. "
                    "Loop physics: DellIR7000, PhysicsCDU."
                ),
            ),
        ),
        FactoryRegion(
            id="resilience", kind="resilience", label="Resilience — checkpoints",
            x=70, y=48, w=28, h=10,
            description=L(
                novice=(
                    "The save points. One GPU fails very rarely, about "
                    "once in 50,000 hours on average (that average is "
                    "called its MTBF, mean time between failures). But "
                    "with 576 GPUs, one of them fails about every 87 "
                    "hours, so failures arrive almost on a schedule. "
                    "Saving the work regularly costs a little time every "
                    "hour, and it means a failure only loses the work "
                    "since the last save. This block lights up when the "
                    "factory is busy saving or restarting."
                ),
                standard=(
                    "At cluster scale, failure is a schedule, not a surprise: "
                    "divide one GPU's MTBF (mean time between failures) by "
                    "the GPU count. Checkpoints tax every hour a little so a "
                    "failure costs minutes; skip them and it costs the time "
                    "since the last one. The optimum interval is arithmetic, "
                    "and the validation panel computes it. The block is "
                    "painted by the share of each hour spent saving or "
                    "restarting."
                ),
                expert=(
                    "M_cluster = M_gpu/N; tax t_c/(I + t_c); rollback to "
                    "last checkpoint is literal. Status = overhead share."
                ),
            ),
        ),
    ],
    sources=[
        {"label": "Dell AI Factory with NVIDIA",
         "url": "https://www.dell.com/en-us/lp/dt/nvidia-ai"},
        {"label": "NVIDIA GB200 NVL72",
         "url": "https://www.nvidia.com/en-us/data-center/gb200-nvl72/"},
        {"label": "Meta — The Llama 3 Herd of Models (failure arithmetic: 419 interruptions, 54-day snapshot, 16,384 GPUs)",
         "url": "https://arxiv.org/abs/2407.21783"},
        {"label": "Meta — Llama 3.1 405B model card (throughput arithmetic: 30.84M GPU-hours, ~15T tokens)",
         "url": "https://huggingface.co/meta-llama/Llama-3.1-405B"},
        {"label": "NVIDIA newsroom — Spectrum-X on xAI Colossus (122 days; vendor's 95% vs 60% throughput claim)",
         "url": "https://nvidianews.nvidia.com/news/spectrum-x-ethernet-networking-xai-colossus"},
        {"label": "ServeTheHome — inside xAI Colossus (64 GPUs per rack; 100,000 / 64 ≈ 1,500 racks)",
         "url": "https://www.servethehome.com/inside-100000-nvidia-gpu-xai-colossus-cluster-supermicro-helped-build-for-elon-musk/"},
        {"label": "Build plan for this suite (this repo)",
         "url": "../physics_specs/BUILD_PLAN.md"},
    ],
)
