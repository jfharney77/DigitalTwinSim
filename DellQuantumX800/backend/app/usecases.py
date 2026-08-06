"""Use-case build sheets for the Quantum-X800 twin — backend data. Every
``category_id``/``option_id`` must resolve against catalog.py (enforced in
tests/test_catalog.py). Quantities and outcomes are illustrative, anchored
to the public reporting cited in anatomy.py."""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="tacc-horizon",
        title="An academic frontier system: TACC Horizon's interconnect",
        summary=(
            "The sourced deployment: Quantum-X800 joining Dell IRSS Grace "
            "Blackwell racks — 4,000 GPUs, one million CPU cores, 300 "
            "petaflops, and a workload mix no one can predict."
        ),
        narrative=[
            (
                "Horizon (announced November 2025) is the largest academic "
                "supercomputer in the US, and its interconnect is named in "
                "the announcement: NVIDIA Quantum-X800 InfiniBand joining "
                "Dell IRSS racks of direct-liquid-cooled Grace Blackwell "
                "nodes. The choice follows from what an academic machine "
                "is. A cloud training cluster serves one workload it "
                "understands completely; a national research system serves "
                "thousands of allocations it has never seen — MPI codes "
                "from the 1990s, fresh PyTorch, and everything between — "
                "so the fabric must be non-blocking, general, and "
                "deterministic rather than tuned to one traffic pattern."
            ),
            (
                "InfiniBand is the incumbent grammar of that world. The "
                "MPI stacks, schedulers, and operational muscle of "
                "academic HPC grew up on subnet managers and RDMA verbs; "
                "TACC's own lineage (Frontera, Stampede3) runs on it. "
                "Horizon extends the tradition to the AI era: SHARP "
                "accelerates both an MPI_Allreduce and an NCCL gradient "
                "exchange, credit-based transport gives the fortnight-long "
                "climate run and the overnight fine-tune the same "
                "zero-loss floor, and the centrally computed routes make "
                "performance reproducible — which, for a machine whose "
                "product is published science, is a feature of the "
                "instrument itself."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="quantum-x800", qty=8,
                rationale=(
                    "The generation the Horizon announcement names — "
                    "spine capacity for a 4,000-GPU fat tree."
                ),
            ),
            UseCaseItem(
                category_id="topology", option_id="fat-tree", qty=1,
                rationale=(
                    "Unknowable workload mix — full bisection for any "
                    "traffic pattern, not one tuned pattern."
                ),
            ),
            UseCaseItem(
                category_id="management", option_id="ufm", qty=1,
                rationale=(
                    "One brain for a campus-scale fabric, plus the cable "
                    "telemetry thousands of transceivers demand."
                ),
            ),
            UseCaseItem(
                category_id="in-network-compute", option_id="sharp", qty=1,
                rationale=(
                    "Accelerates MPI and NCCL collectives alike — both "
                    "communities share the machine."
                ),
            ),
            UseCaseItem(
                category_id="endpoints", option_id="connectx8", qty=4000,
                rationale="One 800 Gb/s port per GPU, RDMA end to end.",
            ),
            UseCaseItem(
                category_id="delivery", option_id="irss", qty=1,
                rationale=(
                    "The fabric arrives inside Dell's factory-integrated "
                    "racks — Horizon's stated delivery model."
                ),
            ),
        ],
        outcomes=[
            Stat(label="System", value="300 PF · 4,000 GPUs · 1M CPU cores"),
            Stat(label="Fabric", value="Quantum-X800, non-blocking fat tree"),
            Stat(label="Lineage", value="10× Frontera — same InfiniBand grammar"),
        ],
    ),
    UseCase(
        id="ai-factory-ib",
        title="A training factory that chose InfiniBand",
        summary=(
            "The other fork of the AI Factory: XE9680-class fleets on NDR/XDR "
            "rails with SHARP, where the Colossus estate chose Spectrum-X."
        ),
        narrative=[
            (
                "Dell's AI Factory ships both fabrics, and the fork is "
                "real: xAI's Colossus put its XE9680 fleet on Spectrum-X "
                "Ethernet (the SN6000 twin's story), while operators with "
                "InfiniBand roots — national labs turned model shops, HPC "
                "cloud providers — buy the same servers on Quantum rails. "
                "The per-GPU adapter design carries over unchanged; what "
                "changes is everything underneath it: routes programmed "
                "instead of converged, losslessness constitutional instead "
                "of earned, and the all-reduce computed in the switches."
            ),
            (
                "A rail-optimized topology fits this buyer where it did "
                "not fit Horizon: a single-tenant training factory knows "
                "its traffic pattern completely, so it can wire GPU N of "
                "every server to rail N, shorten cables, and spend the "
                "savings on more endpoints. SHARP then removes a "
                "fraction of the collective's bytes before they exist. "
                "The honest summary of Ethernet-versus-InfiniBand at "
                "this scale: operational familiarity and ecosystem "
                "against determinism and in-network compute — a choice "
                "of grammar, not of speed."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="quantum-x800", qty=16,
                rationale="XDR spines sized for a multi-thousand-GPU fleet.",
            ),
            UseCaseItem(
                category_id="topology", option_id="rail-optimized", qty=1,
                rationale=(
                    "Single-tenant, known traffic — rails trade "
                    "generality for cost the factory can keep."
                ),
            ),
            UseCaseItem(
                category_id="in-network-compute", option_id="sharp", qty=1,
                rationale="Gradient bytes deleted in-flight, every step.",
            ),
            UseCaseItem(
                category_id="endpoints", option_id="connectx8", qty=8192,
                rationale="One adapter per GPU across the fleet.",
            ),
            UseCaseItem(
                category_id="endpoints", option_id="bluefield3", qty=1024,
                rationale="Storage and control traffic kept off the compute rails.",
            ),
            UseCaseItem(
                category_id="cooling", option_id="liquid-chassis", qty=16,
                rationale="XDR spines join the same loop as the GPU racks.",
            ),
        ],
        outcomes=[
            Stat(label="Fleet", value="8,192 GPUs on XDR rails"),
            Stat(label="Collectives", value="SHARP-offloaded, every training step"),
            Stat(label="The fork", value="Determinism chosen over Ethernet familiarity"),
        ],
    ),
    UseCase(
        id="campus-hpc",
        title="A campus cluster carrying two communities",
        summary=(
            "Sixteen XE9680s on a small fat tree: the MPI old guard and "
            "the deep-learning lab share one fabric without knowing it."
        ),
        narrative=[
            (
                "Most InfiniBand is not a frontier system. The common "
                "deployment is a campus or departmental cluster — a few "
                "racks, a two-tier tree, an embedded subnet manager — "
                "where the physics group's decades-old MPI code and the "
                "ML lab's PyTorch jobs schedule onto the same nodes. "
                "InfiniBand's virtue here is that neither community has "
                "to think about it: verbs and RDMA look identical to "
                "both stacks, and the credit-based floor means a "
                "misbehaving job can congest the fabric but cannot make "
                "it lose anyone else's packets."
            ),
            (
                "The build stays deliberately modest: Quantum-2 leaves "
                "are plentiful and cheap on the secondary market, copper "
                "runs in-rack skip transceiver costs, and the embedded "
                "SM spares a management host. The architecture is "
                "byte-for-byte the one Horizon runs — sweep, program, "
                "credits, SHARP — which is the point of the twin's "
                "story: the grammar scales down as faithfully as it "
                "scales up."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="quantum-2", qty=6,
                rationale=(
                    "NDR is the campus workhorse — same architecture, "
                    "budget-friendly."
                ),
            ),
            UseCaseItem(
                category_id="topology", option_id="fat-tree", qty=1,
                rationale="Two communities, unknowable mix — stay general.",
            ),
            UseCaseItem(
                category_id="management", option_id="embedded-sm", qty=1,
                rationale="A rack-scale fabric does not justify a UFM host.",
            ),
            UseCaseItem(
                category_id="in-network-compute", option_id="host-collectives", qty=1,
                rationale=(
                    "Honest default at this scale; SHARP arrives with "
                    "the next refresh."
                ),
            ),
            UseCaseItem(
                category_id="optics", option_id="dac-copper", qty=64,
                rationale="In-rack copper: no lasers to fail, no watts to pay.",
            ),
        ],
        outcomes=[
            Stat(label="Cluster", value="16 nodes · 128 GPUs · 2 racks"),
            Stat(label="Communities", value="MPI and NCCL on one fabric, unaware"),
            Stat(label="Grammar", value="Identical to Horizon's, scaled down"),
        ],
    ),
]
