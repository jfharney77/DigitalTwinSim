"""Worked use cases: what a PowerStore actually gets deployed for.

Each use case is a narrative plus a bill of materials whose category/option
ids must resolve against catalog.py (enforced in tests/test_catalog.py).
Written for a technically skilled reader new to storage arrays.
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="vmware-consolidation",
        title="VMware storage consolidation",
        summary=(
            "One appliance as the storage backend for a vSphere cluster — "
            "per-VM storage via vVols, sub-millisecond NVMe latency, and "
            "optional zero-RPO stretching across two sites."
        ),
        narrative=[
            (
                "The workload: a vSphere cluster of a dozen ESXi hosts "
                "running a few hundred mixed VMs — application servers, "
                "middleware, a scatter of departmental databases — whose "
                "storage today is spread across aging arrays and local "
                "disks. The goal is one storage target with predictable "
                "latency, per-VM manageability, and enough headroom that "
                "nobody re-architects next year."
            ),
            (
                "Why PowerStore fits: the dual active/active nodes mean "
                "an ESXi host always has two live paths to every "
                "datastore, so a controller failure or an array software "
                "upgrade is invisible to VMs. vVols 2.0 (VMware Virtual "
                "Volumes) replaces shared datastore LUNs with per-VM "
                "objects, so snapshots and replication apply to a single "
                "VM from vCenter policy rather than to whole datastores. "
                "Always-on inline deduplication and compression thrive on "
                "VM images — hundreds of near-identical guest OS disks "
                "routinely reduce well beyond the guaranteed 4:1 — and "
                "the all-NVMe pool keeps latency flat as the estate "
                "grows. If the cluster later outgrows one appliance, "
                "scale-out clustering adds a second under the same "
                "management plane and migrates volumes live."
            ),
            (
                "Day to day: provisioning happens from vCenter (through "
                "the vVols policy engine) or PowerStore Manager, and "
                "capacity forecasting comes from CloudIQ, which trends "
                "the fleet and warns months ahead of exhaustion. Where "
                "the business demands zero data loss, a Metro Volume "
                "pairs this appliance with a twin at a second site — "
                "both arrays serve the same volumes live, and losing an "
                "entire room moves nothing but path traffic. OS upgrades "
                "roll node by node with I/O flowing throughout; the "
                "operational cost of ownership is one web UI and the "
                "occasional firmware click."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="models",
                option_id="model-5200t",
                qty=1,
                rationale=(
                    "Consolidating a few hundred VMs wants the performance "
                    "tier: high core counts keep inline data reduction "
                    "free even at peak IOPS."
                ),
            ),
            UseCaseItem(
                category_id="drives",
                option_id="drive-7_68tb",
                qty=12,
                rationale=(
                    "~92 TB raw → ~368 TB effective at 4:1; nine empty "
                    "slots left for growth before any shelf is needed."
                ),
            ),
            UseCaseItem(
                category_id="io-modules",
                option_id="iomod-32gfc",
                qty=4,
                rationale=(
                    "The shop runs an existing FC SAN; matching 32 Gb FC "
                    "modules in both nodes give every host four redundant "
                    "fabric paths (FC-NVMe capable for later)."
                ),
            ),
            UseCaseItem(
                category_id="mezzanine",
                option_id="mezz-25gbe",
                qty=2,
                rationale=(
                    "Embedded 25 GbE carries NAS/file odds-and-ends and "
                    "stands ready as the cluster network if a second "
                    "appliance arrives."
                ),
            ),
            UseCaseItem(
                category_id="software",
                option_id="sw-vvols",
                qty=1,
                rationale=(
                    "Per-VM storage policy from vCenter is the point of "
                    "the design; included in the all-inclusive license."
                ),
            ),
            UseCaseItem(
                category_id="software",
                option_id="sw-metro",
                qty=1,
                rationale=(
                    "Optional second phase: stretch the critical volume "
                    "group across the two machine rooms for zero RPO."
                ),
            ),
            UseCaseItem(
                category_id="management",
                option_id="mgmt-cloudiq",
                qty=1,
                rationale=(
                    "Capacity forecasting and fleet health without "
                    "standing up any monitoring infrastructure."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Effective capacity", value="~368 TB from 12 drives"),
            Stat(label="Host paths per volume", value="4 (2 per node)"),
            Stat(label="Controller failover", value="Seconds · invisible to VMs"),
            Stat(label="RPO with Metro", value="Zero"),
        ],
    ),
    UseCase(
        id="sql-databases",
        title="Database consolidation (OLTP + dev/test)",
        summary=(
            "The flagship tier serving production SQL over NVMe-oF, with "
            "thin clones turning full-size dev/test refreshes into "
            "seconds-long, near-zero-capacity operations."
        ),
        narrative=[
            (
                "The workload: a portfolio of SQL Server and PostgreSQL "
                "instances — a handful of latency-critical OLTP databases "
                "and a long tail of dev, test, and staging copies that "
                "developers refresh from production weekly. The pain is "
                "classic: production wants consistent sub-millisecond "
                "writes; the copies consume five times production's "
                "capacity and a weekend of DBA time per refresh."
            ),
            (
                "Why PowerStore fits: the 9200T's NVRAM-fronted write "
                "path acknowledges transaction-log writes from mirrored "
                "NVMe NVRAM — the flat write latency OLTP lives on — and "
                "NVMe-oF (NVMe-over-Fabrics, here NVMe over TCP on 100 "
                "GbE) carries that latency to the hosts without SCSI "
                "translation overhead. The copy problem collapses into "
                "thin clones: a clone of a multi-terabyte production "
                "volume is created from a snapshot in seconds and "
                "consumes only the blocks dev/test actually changes. "
                "Inline data reduction then deduplicates whatever the "
                "clones share anyway."
            ),
            (
                "Day to day: refreshes become an Ansible job — snapshot "
                "production, re-clone the dev volumes, rescan the hosts "
                "— minutes, no DBA weekend. Asynchronous replication "
                "ships the production volume group to a DR-site "
                "PowerStore on a 15-minute RPO, and DR tests run against "
                "a clone of the replica without ever pausing "
                "replication. The ransomware detection in PowerStoreOS "
                "watches the write stream and pins hardened snapshots "
                "as restore points of last resort."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="models",
                option_id="model-9200t",
                qty=1,
                rationale=(
                    "OLTP consolidation is exactly what the top tier's "
                    "cores, DRAM, and quad NVRAM are for."
                ),
            ),
            UseCaseItem(
                category_id="drives",
                option_id="drive-3_84tb",
                qty=18,
                rationale=(
                    "Many mid-size drives over few large ones: rebuilds "
                    "spread wider and per-TB performance stays high for "
                    "small-block database I/O."
                ),
            ),
            UseCaseItem(
                category_id="io-modules",
                option_id="iomod-100gbe",
                qty=4,
                rationale=(
                    "NVMe-TCP at 100 GbE in matching pairs across nodes — "
                    "fabric bandwidth stops being the variable in query "
                    "latency."
                ),
            ),
            UseCaseItem(
                category_id="software",
                option_id="sw-snapshots",
                qty=1,
                rationale=(
                    "Thin clones are the dev/test refresh mechanism — the "
                    "capacity and time win that pays for the array."
                ),
            ),
            UseCaseItem(
                category_id="software",
                option_id="sw-async-repl",
                qty=1,
                rationale="15-minute-RPO replication of production to the DR site.",
            ),
            UseCaseItem(
                category_id="software",
                option_id="sw-security",
                qty=1,
                rationale=(
                    "Databases are the ransomware target; hardened "
                    "snapshots give a restore point the attacker can't "
                    "encrypt."
                ),
            ),
            UseCaseItem(
                category_id="management",
                option_id="mgmt-automation",
                qty=1,
                rationale=(
                    "The snapshot→clone→rescan refresh pipeline lives in "
                    "Ansible next to the app code."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Log-write latency", value="Sub-ms via mirrored NVRAM"),
            Stat(label="Dev/test refresh", value="Weekend → minutes"),
            Stat(label="Copy capacity", value="Near-zero (thin clones)"),
            Stat(label="DR posture", value="15-min RPO · testable replicas"),
        ],
    ),
    UseCase(
        id="edge-file",
        title="Edge site: block + file from one box",
        summary=(
            "A unified 1200T at a branch site serving iSCSI to the local "
            "hypervisors and SMB/NFS to users — one appliance instead of "
            "an array plus a filer — replicating back to the core."
        ),
        narrative=[
            (
                "The workload: a manufacturing site with a small "
                "virtualization cluster (a dozen production VMs), a CAD "
                "file share for engineering, and a compliance requirement "
                "that site data lands back at headquarters nightly. "
                "There is no storage administrator on site — whatever "
                "gets racked must run itself."
            ),
            (
                "Why PowerStore fits: the T-series is unified, so the "
                "same two nodes serve iSCSI block volumes to the "
                "hypervisors and SMB/NFS shares to users — no separate "
                "NAS filer to buy, power, or patch. The 1200T tier "
                "matches the modest load while keeping every availability "
                "property of the bigger tiers: dual active/active nodes, "
                "vaulted write cache, online upgrades. Data reduction is "
                "the same always-on engine, and CAD data — many "
                "revisions of similar files — deduplicates well."
            ),
            (
                "Day to day: there isn't much, which is the point. "
                "Asynchronous replication ships both the VM volumes and "
                "the file systems to the headquarters cluster overnight; "
                "CloudIQ watches health and capacity from the cloud, so "
                "the central team sees a failing drive before anyone on "
                "site does, and Dell dispatches the part. Drives, PSUs, "
                "I/O modules, and even whole nodes swap in the field "
                "with the array online — the only local skill required "
                "is matching an orange handle to a picture."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="models",
                option_id="model-1200t",
                qty=1,
                rationale=(
                    "The mainstream tier fits a branch: full availability "
                    "story, sized for a dozen VMs plus file."
                ),
            ),
            UseCaseItem(
                category_id="drives",
                option_id="drive-3_84tb",
                qty=8,
                rationale=(
                    "~31 TB raw / ~123 TB effective covers VMs plus the "
                    "CAD share with 13 slots of growth room."
                ),
            ),
            UseCaseItem(
                category_id="mezzanine",
                option_id="mezz-10gbaset",
                qty=2,
                rationale=(
                    "The site's switching is copper; embedded 10GBASE-T "
                    "carries iSCSI and SMB/NFS without optics."
                ),
            ),
            UseCaseItem(
                category_id="io-modules",
                option_id="iomod-25gbe",
                qty=2,
                rationale=(
                    "One matching pair of 25 GbE modules as the dedicated "
                    "replication path back to the core (second slot per "
                    "node left empty for growth)."
                ),
            ),
            UseCaseItem(
                category_id="software",
                option_id="sw-async-repl",
                qty=1,
                rationale="The nightly compliance copy to headquarters.",
            ),
            UseCaseItem(
                category_id="management",
                option_id="mgmt-cloudiq",
                qty=1,
                rationale=(
                    "Remote health and capacity monitoring for a site "
                    "with no storage admin."
                ),
            ),
            UseCaseItem(
                category_id="rack",
                option_id="rack-bezel",
                qty=1,
                rationale=(
                    "The rack sits in a shared site closet — the locking "
                    "bezel keeps hot-swap drives honest."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Boxes on site", value="1 (block + file unified)"),
            Stat(label="Effective capacity", value="~123 TB from 8 drives"),
            Stat(label="On-site storage admin", value="None required"),
            Stat(label="Compliance copy", value="Nightly async to core"),
        ],
    ),
]
