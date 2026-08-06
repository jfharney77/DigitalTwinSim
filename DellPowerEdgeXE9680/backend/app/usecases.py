"""Use-case build sheets for the XE9680 twin — backend data. Every
``category_id``/``option_id`` must resolve against catalog.py (enforced in
tests/test_catalog.py). Quantities and outcomes are illustrative, anchored
to the public reporting cited in anatomy.py."""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="hyperscale-training",
        title="A hyperscale training cluster, one identical box at a time",
        summary=(
            "The Colossus pattern: thousands of liquid-cooled 8-GPU servers, "
            "one NIC per GPU, and a fabric that does what NVLink stops doing "
            "at the chassis wall."
        ),
        narrative=[
            (
                "xAI's Colossus is the public proof of this build: 100,000 "
                "GPUs running within 122 days of the first rack arriving, "
                "then 200,000 — built not from exotic rack-scale machines "
                "but from 8-GPU HGX servers, 64 GPUs to a liquid-cooled "
                "rack, roughly 1,500 racks. The choice of box *is* the "
                "schedule. A factory-integrated NVL72 rack is a single "
                "delivery with a single commissioning path; a fleet of "
                "identical servers is thousands of independent rack jobs "
                "that crews run in parallel, and the machine grows as fast "
                "as people can bolt and cable."
            ),
            (
                "The architecture accepts a trade to get there. Inside each "
                "box, NVSwitch fuses eight GPUs into one 900 GB/s domain; "
                "past the sheet metal, every GPU's traffic rides its own "
                "400 GbE NIC onto a Spectrum-X Ethernet fabric — about "
                "3.6 Tb/s per server. Model parallelism spanning boxes "
                "therefore lives at fabric speed, not NVLink speed, and "
                "the training frameworks are built around exactly that "
                "hierarchy: tensor-parallel inside the domain, data- and "
                "pipeline-parallel across it. The fabric twin (SN6000) and "
                "the cooling twin (IR7000) are the other two thirds of "
                "this story."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="xe9680l-dlc", qty=12500,
                rationale=(
                    "The liquid-cooled 4U variant is what packs 64 GPUs "
                    "into a rack — ~12,500 servers is the 100k-GPU build."
                ),
            ),
            UseCaseItem(
                category_id="gpu-baseboard", option_id="hgx-h100", qty=12500,
                rationale="The first build ran Hopper-generation HGX baseboards.",
            ),
            UseCaseItem(
                category_id="scale-out", option_id="connectx-400", qty=12500,
                rationale=(
                    "One 400 GbE NIC per GPU is the reported Colossus "
                    "design — the cluster exists in these ports."
                ),
            ),
            UseCaseItem(
                category_id="rack-integration", option_id="colossus-rack", qty=1500,
                rationale="Eight servers per rack, one loop, one leaf pair.",
            ),
            UseCaseItem(
                category_id="management", option_id="openmanage", qty=1,
                rationale="12,500 iDRACs need to read as one fleet, not 12,500 tabs.",
            ),
        ],
        outcomes=[
            Stat(label="GPUs", value="100,000 in 122 days, then 200,000"),
            Stat(label="Per rack", value="64 GPUs · 8 servers · one coolant loop"),
            Stat(label="Network", value="~3.6 Tb/s per server, one port per GPU"),
        ],
    ),
    UseCase(
        id="enterprise-ai",
        title="An enterprise AI pod in an ordinary data hall",
        summary=(
            "Four air-cooled boxes in existing racks: fine-tuning and "
            "serving on the same silicon as the hyperscalers, with nothing "
            "about the building changed."
        ),
        narrative=[
            (
                "Most XE9680s are not at xAI. The common deployment is a "
                "handful of air-cooled 6U boxes in a data hall that was "
                "never designed for AI: standard racks, standard power "
                "feeds beefed up per-rack, no liquid anywhere. That is the "
                "6U configuration's whole argument — the fan wall holds "
                "eight ~700 W GPUs at temperature with air, so adopting "
                "the same silicon as a frontier lab is a procurement "
                "decision, not a construction project."
            ),
            (
                "Four servers is 32 GPUs and over 4 TB of pooled HBM in "
                "H200 trim — enough to fine-tune large open-weight models "
                "on private data and serve them inside the firewall. The "
                "same one-NIC-per-GPU design carries over at smaller "
                "scale: the pod's all-to-all traffic crosses two leaf "
                "switches instead of a hall-sized fabric, and a job that "
                "outgrows the pod moves to rented capacity without "
                "changing frameworks, because the hierarchy — NVLink in "
                "the box, RDMA past it — is identical everywhere."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="xe9680-air", qty=4,
                rationale="Air-cooled 6U fits the existing hall — no plumbing.",
            ),
            UseCaseItem(
                category_id="gpu-baseboard", option_id="hgx-h200", qty=4,
                rationale=(
                    "Memory decides which models fit: 1.1 TB pooled HBM "
                    "per box for fine-tuning and long-context serving."
                ),
            ),
            UseCaseItem(
                category_id="host", option_id="xeon-5th", qty=4,
                rationale="Faster DDR5 keeps data loading off the critical path.",
            ),
            UseCaseItem(
                category_id="storage", option_id="nvme-front", qty=4,
                rationale="Local NVMe stages private corpora without a SAN hop.",
            ),
            UseCaseItem(
                category_id="scale-out", option_id="connectx-400", qty=4,
                rationale="The same per-GPU ports, two leaves instead of a hall.",
            ),
            UseCaseItem(
                category_id="management", option_id="idrac9", qty=4,
                rationale="Remote hands from day one — the pod has no on-call DC staff.",
            ),
        ],
        outcomes=[
            Stat(label="GPUs", value="32 across four 6U boxes"),
            Stat(label="Pooled HBM", value="~4.5 TB (H200 trim)"),
            Stat(label="Facility work", value="Power upgrade only — no liquid, no rebuild"),
        ],
    ),
    UseCase(
        id="academic-hpc",
        title="A university cluster on InfiniBand",
        summary=(
            "The same box, the same one-port-per-GPU design, on the NDR "
            "InfiniBand fabric academic HPC already runs."
        ),
        narrative=[
            (
                "University and national-lab clusters — TACC's lineage of "
                "Dell systems is the marquee example — standardized on "
                "InfiniBand years before AI reshaped their workloads, and "
                "their schedulers, MPI stacks, and operations assume it. "
                "The XE9680 meets them where they are: the same ConnectX "
                "adapters that speak 400 GbE at Colossus speak NDR "
                "InfiniBand here, one per GPU, so the machine drops into "
                "an existing fabric without an architectural argument."
            ),
            (
                "The mixed workload is the real design driver. The same "
                "boxes run CFD on the Xeons overnight, distributed "
                "training across the fleet for one lab, and single-domain "
                "inference for another — which rewards a general server "
                "with a strong host over a training-only appliance. "
                "Sixteen boxes is 128 GPUs: small next to a hyperscaler, "
                "transformative next to what most campuses had the year "
                "before."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="xe9680-air", qty=16,
                rationale="Machine-room air handling exists; liquid retrofit does not.",
            ),
            UseCaseItem(
                category_id="gpu-baseboard", option_id="hgx-h100", qty=16,
                rationale="Procurement-friendly and proven across the existing software stack.",
            ),
            UseCaseItem(
                category_id="scale-out", option_id="infiniband-ndr", qty=16,
                rationale="The campus fabric is NDR InfiniBand; the design ports over 1:1.",
            ),
            UseCaseItem(
                category_id="storage", option_id="boss-n1", qty=16,
                rationale="Reimaging happens every maintenance window; boot stays mirrored.",
            ),
            UseCaseItem(
                category_id="power", option_id="psu-2800", qty=16,
                rationale="~11 kW per box is the machine room's real constraint to plan.",
            ),
        ],
        outcomes=[
            Stat(label="GPUs", value="128 across 16 boxes"),
            Stat(label="Fabric", value="NDR InfiniBand, one port per GPU"),
            Stat(label="Workloads", value="Training, inference, and CPU HPC on one fleet"),
        ],
    ),
]
