"""Worked use cases: what a PowerMax array actually gets deployed for.

Each use case is a narrative plus a bill of materials whose category/option
ids must resolve against catalog.py (enforced in tests/test_catalog.py).
Written for a technically skilled reader new to enterprise storage.
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="mainframe-open-consolidation",
        title="Mainframe + open-systems consolidation",
        summary=(
            "One PowerMax 8500 serving both an IBM Z mainframe (FICON and "
            "zHyperLink) and a large open-systems estate, with the array-wide "
            "data reduction and SRDF replication that mission-critical work "
            "demands."
        ),
        narrative=[
            (
                "The workload: a data center running an IBM Z mainframe "
                "alongside hundreds of open-systems hosts — databases, "
                "application servers, VMware — today split across separate "
                "storage platforms. The mainframe needs FICON connectivity and "
                "the lowest possible read latency for its hottest data; the "
                "open systems need Fibre Channel and NVMe at scale. The goal is "
                "one array that does both, with six-nines availability, so a "
                "single storage team and one replication strategy cover the "
                "whole floor."
            ),
            (
                "Why PowerMax fits: it is one of the few arrays designed for "
                "mixed mainframe and open-systems I/O in the same box. FICON "
                "and zHyperLink modules carry the mainframe; 32 Gb Fibre "
                "Channel carries the open systems; global inline data reduction "
                "(guaranteed 3:1 on mainframe, 5:1 on open) applies across all "
                "of it. The scale-out node-pair design lets the array grow to "
                "the combined load, and the dual redundant InfiniBand fabric "
                "means any director reaches any drive with no single fabric to "
                "lose. SRDF — the replication technology decades of mainframe "
                "DR is built on — protects both host types with one mechanism."
            ),
            (
                "Day to day: storage is provisioned by service level rather "
                "than by hand-placing data, so a storage group simply gets a "
                "response-time target the all-NVMe pool holds automatically. "
                "SRDF replicates the critical volumes to a second site; "
                "SnapVX takes local restore points; and the cyber-resiliency "
                "features keep secure, retention-locked snapshots an attacker "
                "cannot delete. zHyperLink shortcuts the FICON path for the "
                "mainframe's hottest synchronous reads, cutting their latency "
                "by an order of magnitude."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="array-family",
                option_id="family-8500",
                qty=1,
                rationale=(
                    "Mixed mainframe + large open-systems consolidation is "
                    "exactly the 8500's scale-out, dual-fabric brief."
                ),
            ),
            UseCaseItem(
                category_id="node-pairs",
                option_id="np-multi",
                qty=4,
                rationale=(
                    "Four node pairs give the directors, cache, and front-end "
                    "ports to carry both host types at once with headroom."
                ),
            ),
            UseCaseItem(
                category_id="cpu",
                option_id="cpu-high",
                qty=1,
                rationale=(
                    "High memory config: the fastest Xeons and largest cache "
                    "options for sustained low latency under mixed load."
                ),
            ),
            UseCaseItem(
                category_id="cache",
                option_id="cache-3584",
                qty=1,
                rationale=(
                    "Large cache per node pair keeps the working set resident "
                    "when many latency-critical workloads share the array."
                ),
            ),
            UseCaseItem(
                category_id="drives",
                option_id="drive-15_36tb-tlc",
                qty=48,
                rationale=(
                    "High-density TLC with full RAID 6 support; one DME's "
                    "worth as the starting capacity, growing a drive at a time."
                ),
            ),
            UseCaseItem(
                category_id="raid",
                option_id="raid-r6",
                qty=1,
                rationale=(
                    "Dual parity survives two concurrent failures — the right "
                    "posture with large drives and mission-critical data."
                ),
            ),
            UseCaseItem(
                category_id="front-end-io",
                option_id="fe-fc32",
                qty=8,
                rationale=(
                    "32 Gb FC carries the open-systems SAN and FICON for the "
                    "mainframe on the same module family; matched across nodes."
                ),
            ),
            UseCaseItem(
                category_id="front-end-io",
                option_id="fe-zhyperlink",
                qty=2,
                rationale=(
                    "zHyperLink shortcuts the FICON path for the mainframe's "
                    "hottest synchronous reads."
                ),
            ),
            UseCaseItem(
                category_id="software",
                option_id="sw-srdf",
                qty=1,
                rationale=(
                    "One replication technology — SRDF — protects both "
                    "mainframe and open-systems volumes to the DR site."
                ),
            ),
            UseCaseItem(
                category_id="software",
                option_id="sw-cyber",
                qty=1,
                rationale=(
                    "Secure snapshots and anomaly detection for a platform "
                    "hosting the organization's most critical data."
                ),
            ),
            UseCaseItem(
                category_id="management",
                option_id="mgmt-unisphere",
                qty=1,
                rationale=(
                    "One console and REST API for both host worlds — the "
                    "operational consolidation that pays for the project."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Host worlds served", value="Mainframe + open systems"),
            Stat(label="Data reduction", value="3:1 MF · 5:1 open (guaranteed)"),
            Stat(label="Drive-failure tolerance", value="2 concurrent (RAID 6)"),
            Stat(label="DR", value="One SRDF strategy for both"),
        ],
    ),
    UseCase(
        id="mission-critical-metro",
        title="Mission-critical database with zero-RPO SRDF/Metro",
        summary=(
            "A PowerMax 2500 serving OLTP databases over 64 Gb FC, stretched "
            "active/active across two sites with SRDF/Metro so an entire site "
            "can fail with zero data loss and no host-side failover script."
        ),
        narrative=[
            (
                "The workload: a portfolio of latency-critical Oracle and SQL "
                "Server databases behind a tier-1 application that the business "
                "will not allow to lose data or go dark. Requirements: "
                "consistent sub-millisecond writes, a zero recovery-point "
                "objective (no committed transaction may be lost), and "
                "transparent survival of losing a whole machine room."
            ),
            (
                "Why PowerMax fits: the all-NVMe pool with large cache and "
                "vault-to-flash protection gives the flat, predictable write "
                "latency OLTP lives on, and 64 Gb Fibre Channel carries it to "
                "the hosts. The zero-RPO requirement is met by SRDF/Metro — the "
                "same database volumes exist active/active on a PowerMax at "
                "each site, hosts see one volume with paths to both, and every "
                "write commits at both arrays before it is acknowledged. Losing "
                "an array, or an entire site, moves nothing but path traffic; "
                "there is no failover script to test because there is no "
                "failover. A single node pair is already fully redundant "
                "inside each site."
            ),
            (
                "Day to day: dev and test copies come from SnapVX — a linked "
                "snapshot of a multi-terabyte production volume is a full-size, "
                "writable clone in seconds that consumes only changed blocks, "
                "so weekly refreshes stop costing a DBA weekend and a full copy "
                "of capacity. Service-level provisioning holds each database's "
                "response-time target automatically, and the whole lifecycle — "
                "snapshot, clone, rescan — runs from Ansible next to the "
                "application code."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="array-family",
                option_id="family-2500",
                qty=1,
                rationale=(
                    "A single-cabinet 2500 per site is right-sized for a "
                    "focused, latency-critical database estate."
                ),
            ),
            UseCaseItem(
                category_id="node-pairs",
                option_id="np-single",
                qty=1,
                rationale=(
                    "One node pair is fully redundant inside each site; "
                    "cross-site resilience comes from SRDF/Metro, not more "
                    "node pairs."
                ),
            ),
            UseCaseItem(
                category_id="cpu",
                option_id="cpu-high",
                qty=1,
                rationale="High memory config for sustained OLTP latency.",
            ),
            UseCaseItem(
                category_id="cache",
                option_id="cache-7680",
                qty=1,
                rationale=(
                    "Maximum cache keeps the hot working set in memory — the "
                    "core performance strategy for OLTP."
                ),
            ),
            UseCaseItem(
                category_id="drives",
                option_id="drive-3_84tb-tlc",
                qty=24,
                rationale=(
                    "Many mid-size drives over a few large ones: more drive "
                    "controllers sharing small-block database I/O, wider "
                    "rebuilds."
                ),
            ),
            UseCaseItem(
                category_id="raid",
                option_id="raid-r5",
                qty=1,
                rationale=(
                    "Single-parity efficiency with a fast distributed rebuild "
                    "suits the smaller, high-IOPS drives."
                ),
            ),
            UseCaseItem(
                category_id="fabric",
                option_id="fabric-direct",
                qty=1,
                rationale=(
                    "A single node pair uses the 2500's direct fabric link "
                    "between its two directors."
                ),
            ),
            UseCaseItem(
                category_id="front-end-io",
                option_id="fe-fc64",
                qty=4,
                rationale=(
                    "64 Gb FC in matching pairs across the directors — fabric "
                    "bandwidth stops being the variable in query latency."
                ),
            ),
            UseCaseItem(
                category_id="software",
                option_id="sw-srdf",
                qty=1,
                rationale=(
                    "SRDF/Metro is the zero-RPO, active/active mechanism at the "
                    "heart of this design."
                ),
            ),
            UseCaseItem(
                category_id="software",
                option_id="sw-snapvx",
                qty=1,
                rationale=(
                    "Linked SnapVX snapshots turn dev/test refreshes into "
                    "seconds-long, near-zero-capacity operations."
                ),
            ),
            UseCaseItem(
                category_id="software",
                option_id="sw-service-levels",
                qty=1,
                rationale=(
                    "Per-storage-group response-time targets held "
                    "automatically across the database portfolio."
                ),
            ),
            UseCaseItem(
                category_id="management",
                option_id="mgmt-automation",
                qty=1,
                rationale=(
                    "The snapshot → clone → rescan refresh pipeline lives in "
                    "Ansible beside the app."
                ),
            ),
        ],
        outcomes=[
            Stat(label="RPO", value="Zero (SRDF/Metro active/active)"),
            Stat(label="Site failure", value="Transparent — no failover script"),
            Stat(label="Dev/test refresh", value="Weekend → minutes (SnapVX)"),
            Stat(label="Write latency", value="Flat sub-ms · vault-protected"),
        ],
    ),
    UseCase(
        id="cyber-resiliency-vault",
        title="Cyber resiliency: capacity tier with an isolated vault",
        summary=(
            "A capacity-oriented PowerMax 8500 with QLC drives, secure "
            "immutable snapshots, and an isolated Cyber Recovery vault — a "
            "known-good restore point kept off the production network."
        ),
        narrative=[
            (
                "The workload: the consolidation target for a large "
                "organization's primary data, plus a mandate — from "
                "regulators and the board alike — to guarantee recovery from a "
                "ransomware attack that has compromised the production "
                "environment. Capacity is large and growing; the defining "
                "requirement is not raw speed but a restore point an attacker "
                "cannot reach or delete."
            ),
            (
                "Why PowerMax fits: cyber resiliency is built into the "
                "platform, not bolted on. Firmware is anchored in a hardware "
                "root of trust; SnapVX can take secure snapshots that are "
                "immutable and retention-locked, so even an administrator "
                "credential cannot delete them within their window; and "
                "PowerMaxOS analyzes the I/O stream for the entropy signature "
                "of mass encryption. On the 8500 this extends to Cyber Recovery "
                "for PowerMax — an isolated vault, delivered through Dell "
                "Professional Services, holding a copy of critical data on an "
                "air-gapped network segment. Dense QLC drives make the capacity "
                "tier economical, and inline data reduction stretches it "
                "further."
            ),
            (
                "Day to day: production data replicates into the vault on a "
                "schedule through a link that is opened only for the copy and "
                "closed again, so the vault is unreachable from production the "
                "rest of the time. CloudIQ watches fleet health and capacity "
                "and surfaces the anomaly alerts, and system-bay dispersion "
                "lets the vault cabinet sit physically apart from the "
                "production bays within the same site while still on the "
                "fabric."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="array-family",
                option_id="family-8500",
                qty=1,
                rationale=(
                    "Cyber Recovery for PowerMax and system-bay dispersion are "
                    "8500 capabilities."
                ),
            ),
            UseCaseItem(
                category_id="node-pairs",
                option_id="np-multi",
                qty=2,
                rationale=(
                    "Two node pairs cover the consolidated capacity tier's "
                    "throughput without over-provisioning compute."
                ),
            ),
            UseCaseItem(
                category_id="cache",
                option_id="cache-1792",
                qty=1,
                rationale=(
                    "A capacity tier needs adequate, not maximal, cache — the "
                    "8500's mainstream size fits."
                ),
            ),
            UseCaseItem(
                category_id="drives",
                option_id="drive-30_72tb-qlc",
                qty=48,
                rationale=(
                    "Dense QLC drives make petabyte-scale capacity economical; "
                    "the workload is capacity-oriented, not IOPS-bound."
                ),
            ),
            UseCaseItem(
                category_id="dme",
                option_id="dme-48",
                qty=1,
                rationale=(
                    "A full 48-slot DME of dense drives as the capacity "
                    "building block, growing on the fabric."
                ),
            ),
            UseCaseItem(
                category_id="raid",
                option_id="raid-r6",
                qty=1,
                rationale=(
                    "Dual parity is essential with 30 TB drives, where rebuild "
                    "windows are long."
                ),
            ),
            UseCaseItem(
                category_id="software",
                option_id="sw-cyber",
                qty=1,
                rationale=(
                    "Secure immutable snapshots and anomaly detection are the "
                    "point of the design."
                ),
            ),
            UseCaseItem(
                category_id="software",
                option_id="sw-snapvx",
                qty=1,
                rationale=(
                    "SnapVX is the snapshot engine the secure restore points "
                    "are built on."
                ),
            ),
            UseCaseItem(
                category_id="vault",
                option_id="vault-modules",
                qty=1,
                rationale=(
                    "Vault-to-flash guarantees cache survives power loss — the "
                    "baseline durability under the cyber story."
                ),
            ),
            UseCaseItem(
                category_id="management",
                option_id="mgmt-cloudiq",
                qty=1,
                rationale=(
                    "CloudIQ surfaces the anomaly alerts and capacity trend "
                    "for the growing tier."
                ),
            ),
            UseCaseItem(
                category_id="cabinet",
                option_id="cab-dispersion",
                qty=1,
                rationale=(
                    "Dispersion lets the vault cabinet sit apart from "
                    "production bays while staying on the fabric."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Restore point", value="Immutable · retention-locked"),
            Stat(label="Vault", value="Isolated / air-gapped (Cyber Recovery)"),
            Stat(label="Capacity economics", value="Dense QLC + inline reduction"),
            Stat(label="Failure tolerance", value="2 drives (RAID 6)"),
        ],
    ),
]
