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
    regions=[
        FactoryRegion(
            id="ops", kind="operations", label="Operations — procure → install → bring-up → train",
            x=2, y=2, w=96, h=8,
            description=(
                "The timeline layer: procurement, factory-integrated rack "
                "install (about two hours per rack — the Colossus pace), "
                "cluster bring-up, then the training ramp. Time-to-first-"
                "token is this block's headline: every hour here is an "
                "hour the capex meter runs with zero tokens out."
            ),
        ),
        FactoryRegion(
            id="compute", kind="compute", label="Compute — GPU racks",
            x=2, y=14, w=40, h=30,
            description=(
                "Racks of XE9712-class systems, 72 GPUs each, fused by "
                "NVLink inside the rack. This block turns megawatts into "
                "tokens at a rate everything else on this map multiplies "
                "or taxes. Its own physics — the fuse, the coolant, the "
                "HBM — lives in the DellPowerEdgeXE9712 twin."
            ),
        ),
        FactoryRegion(
            id="fabric", kind="fabric", label="Fabric",
            x=46, y=14, w=16, h=30,
            description=(
                "The scale-out network — Spectrum-X Ethernet or Quantum "
                "InfiniBand — drawn deliberately *between* compute and "
                "data, because every byte of training data and every "
                "collective crosses it. Oversubscribe it and every "
                "training step pays; the SN6000 and Quantum-X800 twins "
                "carry the packet-level story."
            ),
        ),
        FactoryRegion(
            id="data", kind="data", label="Data platform",
            x=66, y=14, w=32, h=30,
            description=(
                "The storage that feeds the cluster, reduced to the one "
                "number that gates training: aggregate GB/s. When supply "
                "falls below the cluster's demand, utilization follows "
                "supply/demand exactly and the dashboard's GPU-idle-due-"
                "to-data % rises to match — the cheapest block to get "
                "wrong and the most expensive to have gotten wrong. The "
                "DellExascale twin shows how the bytes actually move."
            ),
        ),
        FactoryRegion(
            id="power", kind="power", label="Power",
            x=2, y=48, w=30, h=10,
            description=(
                "The building's feed. The identity is merciless: facility "
                "MW = IT MW × PUE, and the budget is a wall. When the sum "
                "crosses it, this simulator sheds GPU clocks — the polite "
                "failure — because the impolite one is a breaker."
            ),
        ),
        FactoryRegion(
            id="cooling", kind="cooling", label="Cooling",
            x=36, y=48, w=30, h=10,
            description=(
                "Every IT watt becomes heat; PUE is the markup the "
                "building charges to remove it. Liquid cooling holds it "
                "near 1.15, air nearer 1.45, and a warm day adds to "
                "either — which, at a tight power budget, becomes a "
                "compute problem. The IR7000 twin owns this loop."
            ),
        ),
        FactoryRegion(
            id="resilience", kind="resilience", label="Resilience — checkpoints",
            x=70, y=48, w=28, h=10,
            description=(
                "At cluster scale, failure is a schedule, not a surprise: "
                "divide one GPU's MTBF by the GPU count. Checkpoints tax "
                "every hour a little so a failure costs minutes; skip "
                "them and it costs the time since the last one. The "
                "optimum interval is arithmetic, and the validation panel "
                "computes it."
            ),
        ),
    ],
    sources=[
        {"label": "Dell AI Factory",
         "url": "https://www.dell.com/en-us/lp/dt/ai-technologies"},
        {"label": "NVIDIA GB200 NVL72",
         "url": "https://www.nvidia.com/en-us/data-center/gb200-nvl72/"},
        {"label": "Meta — The Llama 3 Herd of Models (failure & throughput arithmetic)",
         "url": "https://arxiv.org/abs/2407.21783"},
        {"label": "Build plan for this suite (this repo)",
         "url": "../physics_specs/BUILD_PLAN.md"},
    ],
)
