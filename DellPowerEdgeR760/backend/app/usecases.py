"""Worked use cases: real deployments an R760 gets bought for.

Each ``UseCase`` tells the story for a technically skilled reader new to
the product, then grounds it in an actual bill of materials — every config
line references a real ``category_id``/``option_id`` pair from catalog.py
(enforced by tests/test_catalog.py).
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

VIRTUALIZATION = UseCase(
    id="virtualization",
    title="Virtualization consolidation host",
    summary=(
        "Three racks of aging single-purpose servers become a three-node "
        "cluster of R760s running a hypervisor — the single most common "
        "job this machine is bought for."
    ),
    narrative=[
        (
            "The scenario: a mid-size company has forty-odd physical "
            "servers, most under 10% CPU utilization, each with its own "
            "power feeds, warranty, and failure modes. The fix is the "
            "standard one — virtualize. Each R760 in a small cluster runs "
            "a hypervisor (VMware ESXi, Proxmox, or Hyper-V) and hosts "
            "dozens of those machines as virtual machines. What the "
            "hypervisor actually sells is cores and memory, which drives "
            "every line of the configuration below: two 32-core Gold "
            "processors give 64 cores/128 threads per node, and 1 TB of "
            "DDR5 across all 16 channels-worth of slots keeps VM density "
            "memory-bound rather than bandwidth-bound."
        ),
        (
            "Storage is the part that has changed since the last refresh "
            "cycle: instead of a separate SAN, the 24 front NVMe bays in "
            "each node pool into a software-defined datastore (vSAN-style) "
            "spanning the cluster. That is why the config carries the "
            "HBA355i pass-through adapter rather than a PERC RAID card — "
            "the storage layer wants raw drives it can watch and rebuild "
            "itself; a RAID controller in the path would hide exactly the "
            "drive state it needs. The hypervisor itself boots from the "
            "BOSS-N1 mirror at the rear, so all 24 bays stay in the "
            "datastore, and losing a boot stick is a hot-swap, not an "
            "outage."
        ),
        (
            "Day-to-day, the cluster runs itself and iDRAC9 Enterprise is "
            "how humans touch the hardware. New node? Mount the installer "
            "ISO over virtual media from a desk and never visit the rack. "
            "Failed DIMM at 2 a.m.? iDRAC already emailed the exact slot "
            "number, VMs migrated off automatically, and the part swap "
            "happens during business hours. The dual 25 GbE ports carry "
            "VM, storage, and live-migration traffic bonded across two "
            "top-of-rack switches; the 1500 W PSUs run 1+1 from separate "
            "power feeds, so a failed feed — like a failed fan, drive, or "
            "PSU — is an event in a log, not an incident."
        ),
    ],
    config=[
        UseCaseItem(
            category_id="processors", option_id="xeon-gold-6430", qty=2,
            rationale=(
                "64 cores/128 threads per node — VM density comes from "
                "core count, and Gold is the price/core sweet spot."
            ),
        ),
        UseCaseItem(
            category_id="memory", option_id="rdimm-32gb", qty=32,
            rationale=(
                "1 TB per node with every channel populated; hypervisor "
                "hosts run out of RAM long before they run out of CPU."
            ),
        ),
        UseCaseItem(
            category_id="storage-chassis", option_id="bay-24x25", qty=1,
            rationale="Maximum NVMe bays to feed the shared datastore.",
        ),
        UseCaseItem(
            category_id="drives", option_id="nvme-u2-gen4", qty=12,
            rationale=(
                "Half-populated to start; software-defined storage grows "
                "by hot-adding drives, not by forklift."
            ),
        ),
        UseCaseItem(
            category_id="raid", option_id="hba355i", qty=1,
            rationale=(
                "Pass-through, not RAID: the storage layer does its own "
                "redundancy and needs to see raw drives."
            ),
        ),
        UseCaseItem(
            category_id="boot", option_id="boss-n1", qty=1,
            rationale="Mirrored hypervisor boot without spending data bays.",
        ),
        UseCaseItem(
            category_id="network", option_id="ocp-broadcom-25gbe", qty=1,
            rationale=(
                "2× 25 GbE bonded across two switches carries VM, "
                "storage, and migration traffic."
            ),
        ),
        UseCaseItem(
            category_id="power", option_id="psu-1500w", qty=2,
            rationale="1+1 redundant with headroom for full drive growth.",
        ),
        UseCaseItem(
            category_id="management", option_id="idrac-enterprise", qty=1,
            rationale=(
                "Remote console + virtual media: nodes are installed and "
                "serviced without a datacenter visit."
            ),
        ),
        UseCaseItem(
            category_id="rack", option_id="readyrails", qty=1,
            rationale="Slide-out service for fans and DIMMs while running.",
        ),
    ],
    outcomes=[
        Stat(label="Consolidation", value="~40 legacy servers → 3 nodes"),
        Stat(label="Per-node capacity", value="64 cores · 1 TB RAM"),
        Stat(label="Storage", value="Shared NVMe datastore, no SAN"),
        Stat(label="Hardware touch", value="Remote via iDRAC; parts hot-swap"),
    ],
)

AI_INFERENCE = UseCase(
    id="ai-inference",
    title="AI inference node",
    summary=(
        "Two L40S GPUs turn the same 2U chassis into an on-prem inference "
        "box — serving LLM and vision models where the data already lives."
    ),
    narrative=[
        (
            "The scenario: a team wants to run language-model and vision "
            "inference against internal data that cannot leave the "
            "building. Training happens elsewhere (cloud, or a dedicated "
            "GPU chassis); what's needed on-prem is steady, private "
            "serving capacity. Two double-wide NVIDIA L40S cards — 96 GB "
            "of GPU memory combined — sit on the R760's risers and handle "
            "mid-size LLMs and high-volume embedding or vision loads. The "
            "CPUs matter less here: a pair of 12-core Silvers feeds the "
            "GPUs, tokenizes requests, and runs the serving stack, and "
            "spending the budget on the accelerators instead is the point."
        ),
        (
            "Everything else in the config is a consequence of those two "
            "cards. At 350 W each on passive heatsinks, they are cooled "
            "entirely by the chassis fan wall, so the build mandates the "
            "high-performance Gold fans; total draw approaches 1.4 kW, so "
            "the PSUs step up to 2400 W to keep 1+1 redundancy — which "
            "quietly assumes 200–240 V rack power. Models load from local "
            "NVMe (a multi-gigabyte model pull from network storage on "
            "every restart gets old fast), and a 100 GbE ConnectX card "
            "keeps batch traffic and model syncs off the management "
            "network."
        ),
        (
            "Operationally this node runs hotter and closer to its limits "
            "than a general-purpose server, which makes the management "
            "plane more, not less, important: iDRAC's per-sensor telemetry "
            "shows GPU inlet temperatures drifting weeks before thermal "
            "throttling would show up as mysteriously slow responses, and "
            "power capping can shave peak draw during a rack-level crunch. "
            "When the model outgrows 96 GB, the honest answer is not a "
            "third card — it is the XE-series purpose-built GPU chassis; "
            "the R760's job is the wide middle of the inference market, "
            "and it covers it in standard 2U."
        ),
    ],
    config=[
        UseCaseItem(
            category_id="gpu", option_id="gpu-l40s", qty=2,
            rationale=(
                "96 GB combined GPU memory serves mid-size LLMs; the "
                "chassis maximum for double-wide cards."
            ),
        ),
        UseCaseItem(
            category_id="processors", option_id="xeon-silver-4410y", qty=2,
            rationale=(
                "GPUs do the math; the CPUs feed them. Budget goes to "
                "accelerators, not cores."
            ),
        ),
        UseCaseItem(
            category_id="memory", option_id="rdimm-32gb", qty=16,
            rationale=(
                "512 GB at one DIMM per channel — full memory bandwidth "
                "for preprocessing without paying for capacity idle GPUs "
                "can't use."
            ),
        ),
        UseCaseItem(
            category_id="storage-chassis", option_id="bay-8x25", qty=1,
            rationale="Models and caches, not a data lake: 8 bays suffice.",
        ),
        UseCaseItem(
            category_id="drives", option_id="nvme-u2-gen4", qty=4,
            rationale="Local NVMe so model loads take seconds, not minutes.",
        ),
        UseCaseItem(
            category_id="boot", option_id="boss-n1", qty=1,
            rationale="OS on the mirrored rear module, as on every build.",
        ),
        UseCaseItem(
            category_id="network", option_id="nvidia-connectx-100gbe", qty=1,
            rationale=(
                "100 GbE with RDMA for batch inference traffic and fast "
                "model distribution."
            ),
        ),
        UseCaseItem(
            category_id="cooling", option_id="fans-hpr-gold", qty=6,
            rationale=(
                "Mandatory: the passive GPU cards rely wholly on chassis "
                "airflow."
            ),
        ),
        UseCaseItem(
            category_id="power", option_id="psu-2400w", qty=2,
            rationale=(
                "~1.4 kW peak with redundancy intact; assumes 200–240 V "
                "feeds."
            ),
        ),
        UseCaseItem(
            category_id="management", option_id="idrac-datacenter", qty=1,
            rationale=(
                "Streaming thermal/power telemetry catches GPU throttling "
                "before users do."
            ),
        ),
    ],
    outcomes=[
        Stat(label="GPU memory", value="2× 48 GB L40S"),
        Stat(label="Peak draw", value="~1.4 kW, 1+1 redundant"),
        Stat(label="Data locality", value="Inference stays on-prem"),
        Stat(label="Fit", value="Mid-size models; XE-series beyond"),
    ],
)

DATABASE = UseCase(
    id="database",
    title="OLTP database server",
    summary=(
        "A transactional database wants fast cores, a big cache, lots of "
        "RAM, and storage that never lies about a committed write — a "
        "different R760 than the virtualization build."
    ),
    narrative=[
        (
            "The scenario: the company's order-processing database — the "
            "system where a slow query is a slow checkout. OLTP (online "
            "transaction processing) is many small reads and writes with "
            "users waiting on each one, and it inverts the virtualization "
            "logic: per-core speed beats core count. The 5th-gen Gold "
            "6548Y+ is chosen for clock and its tripled L3 cache — hot "
            "rows served from cache never touch memory at all — and, just "
            "as decisive, because commercial databases are licensed per "
            "core: 64 fast cores can cost less to license than 128 slow "
            "ones doing the same work. 2 TB of RAM from 64 GB modules at "
            "one DIMM per channel keeps the working set in memory at full "
            "DDR5-5600 speed, with 16 slots still empty for growth."
        ),
        (
            "Storage is where a database build is conservative on purpose. "
            "SAS SSDs sit behind a PERC 12 H965i with battery-backed "
            "cache: when the database calls fsync on a transaction commit, "
            "the controller acknowledges from protected cache — fast — and "
            "that write survives a power cut. This is the classic "
            "operational model (RAID-10 volume, controller manages "
            "rebuilds) that database administrators have trusted for "
            "twenty years, chosen here over raw NVMe not for speed but "
            "for its failure semantics. The 16-bay chassis leaves the two "
            "rear bays as a separate mirrored pair for transaction logs, "
            "isolating log I/O from data I/O the way DBA doctrine says."
        ),
        (
            "The steady-state concern is uptime through change: firmware "
            "updates staged via iDRAC and applied in one planned reboot; "
            "a predictive drive failure emailed before it happens, fixed "
            "by hot-swap while the RAID volume keeps serving; quarterly "
            "DR tests run from the remote console. Optionally, direct "
            "liquid cooling keeps the high-clock parts at full boost in a "
            "warm datacenter — sustained clock speed is the resource this "
            "workload actually buys — though it commits the facility to "
            "rack plumbing. Ten years ago this role took a 4U box and an "
            "attached storage shelf; it is now one R760 and, for the "
            "standby replica, a second one in another rack."
        ),
    ],
    config=[
        UseCaseItem(
            category_id="processors", option_id="xeon-gold-6548y-plus", qty=2,
            rationale=(
                "Clock and cache over core count — and per-core licensing "
                "makes fast cores the cheap ones."
            ),
        ),
        UseCaseItem(
            category_id="memory", option_id="rdimm-64gb", qty=32,
            rationale=(
                "2 TB keeps the working set in RAM; buffer-cache hit rate "
                "is the database's real performance knob."
            ),
        ),
        UseCaseItem(
            category_id="storage-chassis", option_id="bay-16x25", qty=1,
            rationale=(
                "16 bays plus the rear pair — logs mirrored separately "
                "from data, per DBA doctrine."
            ),
        ),
        UseCaseItem(
            category_id="drives", option_id="sas-ssd", qty=10,
            rationale=(
                "Flash behind the RAID controller: dual-ported, "
                "controller-managed, boring in the good way."
            ),
        ),
        UseCaseItem(
            category_id="raid", option_id="perc-h965i", qty=1,
            rationale=(
                "Battery-backed cache makes committed writes survive a "
                "power cut — the feature the whole build leans on."
            ),
        ),
        UseCaseItem(
            category_id="boot", option_id="boss-n1", qty=1,
            rationale="OS mirror at the rear; every front bay stays data.",
        ),
        UseCaseItem(
            category_id="network", option_id="ocp-intel-10gbe", qty=1,
            rationale=(
                "Four 10 GbE ports: client traffic, replication to the "
                "standby, and backups on separate ports."
            ),
        ),
        UseCaseItem(
            category_id="power", option_id="psu-1500w", qty=2,
            rationale="Comfortable 1+1 for a CPU/flash build.",
        ),
        UseCaseItem(
            category_id="cooling", option_id="dlc", qty=1,
            rationale=(
                "Optional: cold plates hold full boost clocks — the "
                "resource OLTP actually pays for."
            ),
        ),
        UseCaseItem(
            category_id="management", option_id="idrac-enterprise", qty=1,
            rationale=(
                "Staged firmware, predictive failure alerts, remote "
                "console for DR drills."
            ),
        ),
    ],
    outcomes=[
        Stat(label="Memory", value="2 TB @ DDR5-5600, 16 slots free"),
        Stat(label="Commit safety", value="Battery-backed write cache"),
        Stat(label="Licensing", value="Fewer, faster cores"),
        Stat(label="Footprint", value="4U + shelf, ten years ago → 2U"),
    ],
)

USE_CASES: list[UseCase] = [VIRTUALIZATION, AI_INFERENCE, DATABASE]
