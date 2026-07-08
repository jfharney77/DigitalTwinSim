"""Worked use cases: what a VxRail cluster actually gets deployed for.

Each use case is a narrative plus a bill of materials whose category/option
ids must resolve against catalog.py (enforced in tests/test_catalog.py).
Written for a technically skilled reader new to HCI. Quantities are per
cluster; qty on a per-node category means "this option, in each of N nodes".
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="vdi",
        title="Virtual desktop infrastructure (VDI)",
        summary=(
            "A GPU-accelerated VP-760 cluster serving hundreds of virtual "
            "desktops — high memory per node, all-NVMe vSAN ESA, and a "
            "100 GbE RoCE fabric so login storms and boot storms stay smooth."
        ),
        narrative=[
            (
                "The workload: replace aging desktop PCs with virtual "
                "desktops (VDI) for a few hundred office and engineering "
                "users. Each user expects a responsive machine with hardware "
                "graphics; IT wants them all running in the data center, "
                "centrally patched and backed up. VDI is notorious for "
                "'storms' — everyone logging in at 9am, or a mass reboot "
                "after patching — that hammer storage and memory at once."
            ),
            (
                "Why VxRail fits: VDI is gated by memory and graphics, not by "
                "raw cores, so the design is VP-760 nodes with 2 TB of memory "
                "and data-center GPUs partitioned across many desktops "
                "(vGPU). vSAN ESA on all-NVMe drives absorbs boot and login "
                "storms because every drive serves both cache and capacity "
                "and writes are logged efficiently; the 100 GbE RoCE fabric "
                "keeps the storage that vSAN mirrors between nodes off the "
                "latency path. Crucially for a desktop estate that only grows, "
                "the cluster scales one node at a time — add users, add a "
                "node, and its CPU, memory, GPU, and NVMe all join the running "
                "cluster."
            ),
            (
                "Day to day: VxRail Manager keeps the whole stack — firmware, "
                "ESXi, vSAN — on a Dell-validated bundle and upgrades it "
                "node-by-node with desktops migrating out of the way, so "
                "patching never means a maintenance window for users. "
                "Identical guest images deduplicate heavily on vSAN, so the "
                "effective capacity far exceeds the raw drive count, and "
                "CloudIQ forecasts when the next node is needed before users "
                "feel it."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="plat-vp760", qty=4,
                rationale=(
                    "The 2U performance platform is the only one with room "
                    "for GPUs and 2 TB of memory — the two things VDI needs."
                ),
            ),
            UseCaseItem(
                category_id="processor", option_id="cpu-xeon-5g", qty=4,
                rationale=(
                    "5th-gen Xeon's extra cache and clocks help desktop "
                    "responsiveness; VDI is not core-bound, so no need for EPYC."
                ),
            ),
            UseCaseItem(
                category_id="memory", option_id="mem-2048", qty=4,
                rationale="Desktops are memory-hungry; 2 TB/node keeps density high.",
            ),
            UseCaseItem(
                category_id="gpu", option_id="gpu-vdi", qty=4,
                rationale="Shared vGPU gives every desktop hardware graphics.",
            ),
            UseCaseItem(
                category_id="storage-arch", option_id="arch-esa", qty=1,
                rationale="All-NVMe single tier absorbs login/boot storms.",
            ),
            UseCaseItem(
                category_id="drives", option_id="drive-7_68", qty=24,
                rationale=(
                    "Six 7.68 TB drives per node; identical desktop images "
                    "deduplicate well, so effective capacity runs far higher."
                ),
            ),
            UseCaseItem(
                category_id="network", option_id="nic-100gbe", qty=4,
                rationale="100 GbE RoCE keeps vSAN mirroring off the latency path.",
            ),
            UseCaseItem(
                category_id="vxrail-software", option_id="sw-manager", qty=1,
                rationale="One-click lifecycle so patching never disrupts users.",
            ),
        ],
        outcomes=[
            Stat(label="Nodes", value="4× VP-760 (grows a node at a time)"),
            Stat(label="Memory", value="8 TB total (2 TB/node)"),
            Stat(label="Graphics", value="vGPU — hardware-accelerated desktops"),
            Stat(label="Storage fabric", value="100 GbE RoCE · vSAN ESA"),
        ],
    ),
    UseCase(
        id="edge-robo",
        title="Edge / remote-office cluster (ROBO)",
        summary=(
            "A rugged two-node VD-4000 cluster plus a witness at a site with "
            "no IT staff — full VxRail lifecycle automation and cloud "
            "monitoring in a short-depth, harsh-environment box."
        ),
        narrative=[
            (
                "The workload: a retail branch, a factory floor, or a telco "
                "cabinet needs to run a dozen local VMs — point-of-sale, "
                "cameras, a line-of-business app — close to where the work "
                "happens, for latency and for surviving a WAN outage. There "
                "is no rack room and no on-site IT; whatever is installed must "
                "run itself and tolerate heat, dust, and vibration."
            ),
            (
                "Why VxRail fits: the VD-4000 is a ruggedized, short-depth "
                "node built for exactly these places, and a two-node cluster "
                "is the smallest VxRail — the two nodes mirror each other's "
                "data, and a lightweight witness (a VM back at headquarters) "
                "casts the tie-breaking vote so the survivor knows to keep "
                "running if the partner or the link drops. SmartFabric "
                "Services lets VxRail program its own switches, so standing up "
                "a site needs no network engineer. It is the same VxRail "
                "software as the big clusters, so the branch is managed like "
                "everything else."
            ),
            (
                "Day to day: nobody local touches it. VxRail's lifecycle "
                "management applies validated firmware/ESXi/vSAN bundles "
                "remotely, node-by-node, with VMs migrating across the pair, "
                "and CloudIQ watches health and capacity from the cloud so "
                "the central team sees a failing drive before the branch "
                "does and Dell dispatches the part. The only on-site skill "
                "required is swapping a hot-plug component matched to a "
                "picture."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="plat-vd4000", qty=2,
                rationale=(
                    "Ruggedized short-depth nodes for a site with no proper "
                    "rack or climate control."
                ),
            ),
            UseCaseItem(
                category_id="memory", option_id="mem-256", qty=2,
                rationale="A dozen branch VMs fit comfortably in 256 GB/node.",
            ),
            UseCaseItem(
                category_id="storage-arch", option_id="arch-esa", qty=1,
                rationale="All-NVMe ESA keeps the tiny cluster simple and fast.",
            ),
            UseCaseItem(
                category_id="drives", option_id="drive-3_84", qty=8,
                rationale="Four 3.84 TB drives per node — matched, modest, mirrored.",
            ),
            UseCaseItem(
                category_id="network", option_id="nic-25gbe", qty=2,
                rationale="25 GbE is ample for two nodes; no RoCE fabric needed.",
            ),
            UseCaseItem(
                category_id="fabric", option_id="fab-smartfabric", qty=2,
                rationale="SmartFabric configures the switches so no network engineer visits.",
            ),
            UseCaseItem(
                category_id="topology", option_id="topo-2node", qty=1,
                rationale="Two nodes + a central witness is the minimum resilient cluster.",
            ),
            UseCaseItem(
                category_id="vxrail-software", option_id="sw-lcm", qty=1,
                rationale="Remote, validated, node-by-node upgrades with no site visit.",
            ),
            UseCaseItem(
                category_id="management", option_id="mgmt-cloudiq", qty=1,
                rationale="Cloud health/capacity monitoring for an unstaffed site.",
            ),
        ],
        outcomes=[
            Stat(label="Nodes on site", value="2× VD-4000 + remote witness"),
            Stat(label="Environment", value="Short-depth · ruggedized"),
            Stat(label="On-site IT", value="None required"),
            Stat(label="Upgrades", value="Remote, node-by-node, no downtime"),
        ],
    ),
    UseCase(
        id="vcf-private-cloud",
        title="VMware Cloud Foundation private cloud",
        summary=(
            "A VP-760 cluster under VMware Cloud Foundation, stretched across "
            "two sites for zero-RPO availability — the full software-defined "
            "data center with VxRail and SDDC Manager coordinating upgrades."
        ),
        narrative=[
            (
                "The workload: consolidate a mixed estate — business "
                "applications, databases, and container platforms — onto one "
                "private cloud with self-service provisioning, "
                "software-defined networking, and an availability bar high "
                "enough for tier-1 services. Losing a whole data-center room "
                "must not lose data or take applications down."
            ),
            (
                "Why VxRail fits: VMware Cloud Foundation (VCF) turns the "
                "cluster into a full software-defined data center — automated "
                "networking, and fleet lifecycle through SDDC Manager — and "
                "VxRail was the first HCI system with full VCF integration, so "
                "VxRail Manager and SDDC Manager coordinate rather than fight "
                "over upgrades. A stretched cluster puts half the nodes in "
                "each of two sites with synchronous vSAN mirroring and a "
                "third-site witness, so an entire room can fail and VMs "
                "restart across the link with zero RPO (no committed data "
                "lost). All-NVMe ESA with 4 TB per node and 100 GbE RoCE "
                "gives the performance headroom a tier-1 cloud demands."
            ),
            (
                "Day to day: application teams self-serve capacity through "
                "VCF while the platform team lets VxRail keep the full stack "
                "on validated states, upgraded without downtime because the "
                "stretched cluster always has a live copy elsewhere. Growth "
                "is per node and per site, and the same model extends to new "
                "clusters under one SDDC Manager."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="plat-vp760", qty=4,
                rationale="Performance 2U nodes for a tier-1 private cloud.",
            ),
            UseCaseItem(
                category_id="processor", option_id="cpu-epyc-4g", qty=4,
                rationale=(
                    "High EPYC core counts raise VMs-per-node and cut "
                    "per-core licensing across a large estate."
                ),
            ),
            UseCaseItem(
                category_id="memory", option_id="mem-4096", qty=4,
                rationale="Maximum memory for the densest, largest mixed workloads.",
            ),
            UseCaseItem(
                category_id="storage-arch", option_id="arch-esa", qty=1,
                rationale="ESA gives RAID-6 efficiency at RAID-1 performance for tier-1.",
            ),
            UseCaseItem(
                category_id="drives", option_id="drive-7_68", qty=32,
                rationale="Eight 7.68 TB drives per node for a large shared datastore.",
            ),
            UseCaseItem(
                category_id="network", option_id="nic-100gbe", qty=4,
                rationale="100 GbE RoCE, and the bandwidth a stretched cluster's mirroring needs.",
            ),
            UseCaseItem(
                category_id="topology", option_id="topo-stretched", qty=1,
                rationale="Split across two sites + witness for zero-RPO site failure.",
            ),
            UseCaseItem(
                category_id="vmware-software", option_id="vmw-vcf", qty=1,
                rationale="VCF is the private-cloud platform; VxRail integrates with SDDC Manager.",
            ),
            UseCaseItem(
                category_id="vxrail-software", option_id="sw-manager", qty=1,
                rationale="Coordinated full-stack lifecycle alongside SDDC Manager.",
            ),
        ],
        outcomes=[
            Stat(label="Platform", value="4× VP-760 · VMware Cloud Foundation"),
            Stat(label="Availability", value="Stretched cluster · zero RPO"),
            Stat(label="Memory", value="16 TB total (4 TB/node)"),
            Stat(label="Lifecycle", value="VxRail + SDDC Manager coordinated"),
        ],
    ),
]
