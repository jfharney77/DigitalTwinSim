"""The components-and-options menu for a PowerMax array.

Like the chassis anatomy, the catalog is data, not code. ``region_ids`` tie
each category to the floorplan regions it slots into, so the UI can light up
"where it lives". ``details`` are written for a technically skilled reader who
is new to enterprise storage — Dell jargon (DME, SRDF, SnapVX, FICON,
zHyperlink, memory config) is spelled out on first use. Figures follow Dell's
PowerMax 2500/8500 spec sheet; treat them as product-literature numbers, not
benchmarks.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="array-family",
        name="Array family",
        blurb=(
            "PowerMax comes in two models built from the same modular parts. "
            "The difference is how far each scales out — how many node pairs, "
            "how many drives, how much cache — and whether the fabric is a "
            "direct link or a redundant mesh."
        ),
        limits="One family per array; both run PowerMaxOS 10",
        region_ids=["cpu-a", "cpu-b"],
        options=[
            CatalogOption(
                id="family-2500",
                name="PowerMax 2500",
                summary="Single-cabinet array: 1–2 node pairs, up to 8 PBe.",
                details=(
                    "The smaller model, and a single-floor-tile system — "
                    "everything fits in one cabinet. Scales from one to two "
                    "node pairs (up to 96 drives) and up to 8 PBe (petabytes "
                    "effective, after data reduction). The two nodes of a pair "
                    "connect over a direct InfiniBand fabric link. Same "
                    "PowerMaxOS 10, same data services, same six-nines "
                    "availability as the 8500 — the ceiling is scale, not "
                    "capability. Dell positions it as up to seven times the "
                    "capacity of the previous generation in half the footprint."
                ),
            ),
            CatalogOption(
                id="family-8500",
                name="PowerMax 8500",
                summary="Scale-out flagship: up to 8 node pairs, 18 PBe.",
                details=(
                    "The flagship for massive consolidation. Scales to eight "
                    "node pairs (up to 384 drives) and 18 PBe, with the node "
                    "pairs joined by a dual redundant InfiniBand fabric so any "
                    "director reaches any drive with no single fabric to lose. "
                    "System-bay dispersion lets cabinets sit up to 25 m apart "
                    "to work around data-center floor loading. This is the tier "
                    "for the largest mixed open-systems-plus-mainframe estates "
                    "and for Dell's Cyber Recovery vault service."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="node-pairs",
        name="Node pairs (scale-out)",
        blurb=(
            "The node pair is PowerMax's unit of compute: two directors, their "
            "cache, connectivity, and software, in a 3U module. Adding node "
            "pairs adds performance and front-end ports — this is scaling out, "
            "as opposed to just adding drives."
        ),
        limits="1–2 node pairs (2500) · 1–8 node pairs (8500)",
        region_ids=["board-a", "board-b", "fabric-bus"],
        options=[
            CatalogOption(
                id="np-single",
                name="Single node pair",
                summary="One 3U engine — two directors, fully redundant.",
                details=(
                    "The starting point. Two directors already cover hardware "
                    "failure: either can run the whole array while its partner "
                    "reboots or is replaced. A single node pair is a complete, "
                    "highly available array; adding more is about headroom, not "
                    "basic resilience."
                ),
            ),
            CatalogOption(
                id="np-multi",
                name="Multiple node pairs",
                summary="Scale compute and ports linearly under one array.",
                details=(
                    "Additional node pairs join over the Dynamic Fabric and "
                    "present as one array with one management plane. Each pair "
                    "adds directors, cache, and front-end I/O, so IOPS, "
                    "bandwidth, and host connectivity grow with the workload. "
                    "Because drives live in separate DMEs on the fabric, you "
                    "can add node pairs for performance without touching "
                    "capacity, or the reverse."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="cpu",
        name="Director CPUs (memory config)",
        blurb=(
            "Each director runs Intel Xeon Scalable processors. Dell packages "
            "the CPU/cache combinations as numbered 'memory configurations'; a "
            "higher config means faster Xeons with more cores and more cache."
        ),
        limits="Xeon per director; core count set by memory config tier",
        region_ids=["cpu-a", "cpu-b"],
        options=[
            CatalogOption(
                id="cpu-base",
                name="Base memory config (Xeon Gold, 16-core class)",
                summary="Entry Xeons — e.g. Gold 5218-class, 16 cores per CPU.",
                details=(
                    "The base memory configurations pair a 16-core-class Intel "
                    "Xeon Gold with the smaller cache options. Ample for a "
                    "great many workloads; PowerMax runs its CPUs continuously "
                    "in turbo, so even the base config sustains high clocks. "
                    "Data reduction runs in dedicated hardware, so it does not "
                    "have to compete with host I/O for these cores."
                ),
            ),
            CatalogOption(
                id="cpu-high",
                name="High memory config (Xeon Gold, 18–20-core class)",
                summary="Faster Xeons — up to 20 cores per CPU on the 8500.",
                details=(
                    "The upper memory configurations ship higher-core, "
                    "higher-clock Xeons (e.g. Gold 6254/8280L-class) and unlock "
                    "the largest cache options and the highest per-system core "
                    "counts — up to 736 cores across a fully populated 8500. "
                    "Chosen where sustained sub-millisecond latency under heavy "
                    "concurrent load is the requirement."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="cache",
        name="Cache (global memory)",
        blurb=(
            "PowerMax serves reads and writes from DRAM it calls 'cache' or "
            "global memory. More cache means more of the working set stays in "
            "memory and more write headroom before destaging to flash."
        ),
        limits="896 GB – 7.68 TB per node pair · mirrored across the pair",
        region_ids=["cache-a", "cache-b"],
        options=[
            CatalogOption(
                id="cache-896",
                name="896 GB per node pair",
                summary="Entry cache size — the system minimum on a 2500.",
                details=(
                    "The smallest cache option. Every dirty write is mirrored "
                    "to the partner director across the fabric before the host "
                    "is acknowledged, and the vault-to-flash modules protect "
                    "the whole of cache on power loss — so even the entry size "
                    "loses nothing across a failure. Fine for capacity-oriented "
                    "or moderate-throughput workloads."
                ),
            ),
            CatalogOption(
                id="cache-1792",
                name="1.792 TB per node pair",
                summary="Mainstream cache; the 8500's system minimum.",
                details=(
                    "A common middle option that widens the write buffer and "
                    "keeps more hot data resident. On the 8500 this is the "
                    "floor, since the flagship assumes heavier concurrency."
                ),
            ),
            CatalogOption(
                id="cache-3584",
                name="3.584 TB per node pair",
                summary="Large cache for latency-sensitive consolidation.",
                details=(
                    "Doubles the middle option. The usual pick when many "
                    "latency-critical databases share the array and cache-hit "
                    "rate is what protects response time under bursty load."
                ),
            ),
            CatalogOption(
                id="cache-7680",
                name="7.680 TB per node pair",
                summary="Maximum cache per node pair.",
                details=(
                    "The largest per-node-pair cache. A fully populated 8500 "
                    "reaches roughly 45 TB of raw cache across eight node "
                    "pairs. Chosen for the most demanding OLTP and mixed "
                    "estates where keeping the working set in memory is the "
                    "whole performance strategy."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="drives",
        name="NVMe flash drives",
        blurb=(
            "All capacity is dual-ported 2.5″ NVMe flash in the Dynamic Media "
            "Enclosures — no SAS, no spinning disk. Drives can be added a "
            "single drive at a time, and a pool can mix two adjacent "
            "capacities."
        ),
        limits="Min 10 drives (open) / 6 (mainframe); 1-drive increments",
        region_ids=["dme"],
        options=[
            CatalogOption(
                id="drive-3_84tb-tlc",
                name="3.84 TB NVMe TLC",
                summary="Small capacity point; most drives per terabyte.",
                details=(
                    "Triple-level-cell (TLC) NAND — the mainstream enterprise "
                    "flash grade. Smaller drives mean more drive controllers "
                    "per terabyte, which helps small-block performance, at the "
                    "cost of more slots consumed. A frequent base-capacity "
                    "choice."
                ),
            ),
            CatalogOption(
                id="drive-7_68tb-tlc",
                name="7.68 TB NVMe TLC",
                summary="Balanced capacity-per-slot for consolidation.",
                details=(
                    "Doubles capacity per slot while keeping TLC endurance. A "
                    "common default: enough density to consolidate broadly, "
                    "small enough that a Flexible-RAID rebuild spread across "
                    "the pool finishes quickly."
                ),
            ),
            CatalogOption(
                id="drive-15_36tb-tlc",
                name="15.36 TB NVMe TLC",
                summary="High density; the widest RAID support.",
                details=(
                    "Large TLC drives supporting every Flexible-RAID layout, "
                    "including the wide RAID 6 (24+2). Chosen when both "
                    "capacity and resilience options matter and rack space is "
                    "at a premium."
                ),
            ),
            CatalogOption(
                id="drive-30_72tb-qlc",
                name="30.72 TB NVMe (TLC / QLC)",
                summary="Maximum capacity per slot — petabytes in one DME.",
                details=(
                    "The densest drives, available in TLC and, for the most "
                    "capacity-oriented tiers, QLC (quad-level cell — four bits "
                    "per cell, more capacity per dollar, lower write "
                    "endurance). A DME of these is multiple petabytes raw "
                    "before data reduction; per-terabyte performance is lower "
                    "because fewer drive controllers share the work."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="dme",
        name="Dynamic Media Enclosure (scale-up)",
        blurb=(
            "The DME is the drive shelf: a 48-slot NVMe enclosure that "
            "attaches to the node pairs over the InfiniBand fabric. Adding "
            "DMEs is scaling up — more capacity behind the same directors."
        ),
        limits="48 slots per DME · up to 96 drives (2500) / 384 (8500)",
        region_ids=["dme"],
        options=[
            CatalogOption(
                id="dme-48",
                name="48-slot NVMe DME",
                summary="One drive enclosure, reached over the Dynamic Fabric.",
                details=(
                    "A 48-drive enclosure of dual-ported NVMe. Because it "
                    "attaches to the fabric rather than to one director's bus, "
                    "every director in the array can reach every drive in the "
                    "DME, and capacity grows without adding controllers. "
                    "Multiple DMEs stack per cabinet; the 8500 spreads them "
                    "across node pairs and, with dispersion, across cabinets "
                    "up to 25 m apart."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="raid",
        name="Flexible RAID",
        blurb=(
            "PowerMax protects the pool with Flexible RAID — a choice of RAID "
            "layouts spread across the DME drives with distributed spare "
            "capacity, so rebuilds draw on every remaining drive at once."
        ),
        limits="Set per storage resource pool; no mixed-RAID groups",
        region_ids=["dme"],
        options=[
            CatalogOption(
                id="raid-r1",
                name="RAID 1 (1+1) mirror",
                summary="Simple mirroring — highest overhead, simplest rebuild.",
                details=(
                    "Every block written twice. The most capacity you trade "
                    "for protection, but the simplest failure math and fastest "
                    "rebuild. Used where latency predictability outweighs "
                    "efficiency, or for the smallest configurations."
                ),
            ),
            CatalogOption(
                id="raid-r5",
                name="RAID 5 (8+1 / 12+1)",
                summary="Single-parity stripes — efficient, common default.",
                details=(
                    "Data plus one parity block per stripe: one drive of "
                    "overhead across many. The everyday choice for open-systems "
                    "workloads that want capacity efficiency and can tolerate "
                    "a single-drive failure with a fast distributed rebuild."
                ),
            ),
            CatalogOption(
                id="raid-r6",
                name="RAID 6 (12+2 / 24+2)",
                summary="Dual parity — survives two simultaneous drive failures.",
                details=(
                    "Two parity blocks per stripe, so the pool survives two "
                    "concurrent drive failures — important with the largest "
                    "drives, where rebuild windows are longer. The wide 24+2 "
                    "layout maximizes efficiency and is supported on the 15.36 "
                    "and 30.72 TB drives."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="fabric",
        name="Dynamic Fabric (InfiniBand)",
        blurb=(
            "The InfiniBand fabric is PowerMax's internal interconnect — cache "
            "mirroring, heartbeat, and the path from every director to every "
            "drive. Its topology is what most distinguishes the two models."
        ),
        limits="100 Gb/s per port · direct (2500) or dual redundant (8500)",
        region_ids=["fabric-a", "fabric-b", "fabric-bus"],
        options=[
            CatalogOption(
                id="fabric-direct",
                name="Direct fabric connection (PowerMax 2500)",
                summary="The two directors linked directly at 100 Gb/s.",
                details=(
                    "On a 2500, the pair's two directors connect over a direct "
                    "InfiniBand link. Cache mirrors and drives are reached "
                    "across it at 100 Gb/s per port. Simple and complete for a "
                    "one- or two-node-pair array."
                ),
            ),
            CatalogOption(
                id="fabric-redundant",
                name="Dual redundant fabric (PowerMax 8500)",
                summary="A redundant InfiniBand mesh joining all node pairs.",
                details=(
                    "The 8500 uses two independent InfiniBand fabrics so no "
                    "single fabric failure isolates a director. Every node "
                    "pair connects to every other, which is what lets eight "
                    "node pairs behave as one array and any director reach any "
                    "drive in any DME. This mesh is the backbone of "
                    "scale-out."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="front-end-io",
        name="Front-end I/O modules",
        blurb=(
            "The hot-swap modules in each director set which fabrics hosts "
            "connect over. Up to eight per node pair (four per director), "
            "always in matching pairs so every host path exists on both "
            "directors."
        ),
        limits="Up to 8 FE I/O modules per node pair",
        region_ids=["iomod-a1", "iomod-a2", "iomod-b1", "iomod-b2"],
        options=[
            CatalogOption(
                id="fe-fc32",
                name="32 Gb Fibre Channel (FC / FC-NVMe / FICON)",
                summary="The classic SAN fabric plus mainframe FICON.",
                details=(
                    "Four 32 Gb FC ports per module, speaking SCSI-over-FC, "
                    "NVMe-over-FC, and — for IBM mainframe — FICON on the same "
                    "hardware. The default in shops with an existing FC SAN: "
                    "dedicated, lossless fabric with mature multipathing on "
                    "every OS. SRDF replication can also ride these ports."
                ),
            ),
            CatalogOption(
                id="fe-fc64",
                name="64 Gb Fibre Channel (FC / FC-NVMe)",
                summary="Latest-generation FC for new SAN builds.",
                details=(
                    "Doubles per-port FC bandwidth (multi-mode only), "
                    "backward-compatible with existing switches. A "
                    "future-proofing pick for new fabrics carrying SCSI-FC and "
                    "NVMe-FC."
                ),
            ),
            CatalogOption(
                id="fe-eth100",
                name="100 GbE (iSCSI / NVMe-TCP / SRDF)",
                summary="Maximum Ethernet bandwidth for block over TCP.",
                details=(
                    "Two 100 Gb/s Ethernet ports per module for iSCSI, "
                    "NVMe/TCP (NVMe carried over ordinary TCP/IP, no special "
                    "fabric), and IP SRDF replication. The choice for "
                    "bandwidth-hungry workloads on a modern spine-leaf network "
                    "without a Fibre Channel SAN."
                ),
            ),
            CatalogOption(
                id="fe-eth25",
                name="25 / 10 GbE (iSCSI / NVMe-TCP / SRDF)",
                summary="Mainstream Ethernet block and replication ports.",
                details=(
                    "Four 25 Gb or 10 Gb Ethernet ports per module for iSCSI, "
                    "NVMe/TCP, and SRDF over IP. 25 GbE is the current "
                    "datacenter default; 10 GbE reuses existing optics and "
                    "cabling. Also carries the embedded file ports."
                ),
            ),
            CatalogOption(
                id="fe-zhyperlink",
                name="zHyperLink (IBM mainframe)",
                summary="Ultra-low-latency direct link to IBM Z.",
                details=(
                    "A short-distance, extremely low-latency point-to-point "
                    "connection to an IBM Z mainframe that shortcuts the "
                    "normal FICON I/O path for synchronous reads — cutting "
                    "response time by an order of magnitude for the hottest "
                    "mainframe data. Up to two ports per node pair."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="vault",
        name="Vault to flash & standby power",
        blurb=(
            "PowerMax's write cache is DRAM, which is volatile. Vault-to-flash "
            "plus the standby power supply is the hardware that guarantees an "
            "acknowledged write survives a power loss."
        ),
        limits="2–4 NVMe SED vault modules per node pair · SPS per director",
        region_ids=["vault-a", "vault-b", "sps-a", "sps-b"],
        options=[
            CatalogOption(
                id="vault-modules",
                name="NVMe SED vault-to-flash modules",
                summary="Non-volatile flash that cache is dumped to on power loss.",
                details=(
                    "Two to four NVMe SED (self-encrypting drive) flash "
                    "modules per node pair. On AC loss, the standby power "
                    "supply keeps the director alive just long enough to copy "
                    "the entire DRAM cache to these modules; on the next boot "
                    "the array validates the vault and restores cache if the "
                    "shutdown was dirty. Because the modules self-encrypt, a "
                    "vaulted copy of cache is never readable off a pulled "
                    "module."
                ),
            ),
            CatalogOption(
                id="vault-sps",
                name="Standby power supply (SPS)",
                summary="The battery that powers the vault flush — not a UPS.",
                details=(
                    "Each director's SPS exists for exactly one scenario: line "
                    "power disappears with dirty data in cache. It is sized for "
                    "the seconds needed to vault, not for minutes of "
                    "ride-through. The SPS self-tests before the array will "
                    "accept writes, so the vault promise is verified, not "
                    "assumed."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="software",
        name="PowerMaxOS 10 data services",
        blurb=(
            "PowerMax ships an inclusive software package — the data services "
            "that shape a design come with the array rather than as separate "
            "purchases. These are the ones that show up in architecture "
            "decisions."
        ),
        limits="Inclusive software package with the array",
        region_ids=["cpu-a", "cpu-b", "cache-a", "cache-b"],
        options=[
            CatalogOption(
                id="sw-data-reduction",
                name="Global inline data reduction",
                summary="Hardware dedup + compression; 5:1 open / 3:1 mainframe guaranteed.",
                details=(
                    "Deduplication (identical blocks stored once) and "
                    "compression run inline in dedicated hardware across the "
                    "whole array before data reaches flash — no post-process "
                    "pass, no off switch. Dell guarantees 5:1 reduction on open "
                    "systems and 3:1 on mainframe, which is why effective "
                    "capacity is quoted well above raw."
                ),
            ),
            CatalogOption(
                id="sw-snapvx",
                name="SnapVX snapshots & clones",
                summary="Space-efficient point-in-time copies, targetless or linked.",
                details=(
                    "SnapVX takes near-instant snapshots that consume only "
                    "changed data. Snapshots can be 'targetless' (kept purely "
                    "for restore) or linked to a target volume to become a "
                    "full-size, writable copy for dev/test — the mechanism "
                    "behind seconds-long database refreshes at near-zero "
                    "capacity."
                ),
            ),
            CatalogOption(
                id="sw-srdf",
                name="SRDF remote replication (incl. SRDF/Metro)",
                summary="Dell's flagship array replication — async, sync, and active/active.",
                details=(
                    "SRDF (Symmetrix Remote Data Facility) replicates volumes "
                    "to one or more remote PowerMax arrays. Asynchronous mode "
                    "gives cross-continent DR with a short RPO (recovery point "
                    "objective — how much data you can lose); synchronous gives "
                    "zero data loss within metro distance; and SRDF/Metro "
                    "presents the same volume active/active on two arrays so a "
                    "whole array or site can fail with zero RPO and no host "
                    "failover script. Decades of mainframe and open-systems DR "
                    "are built on SRDF."
                ),
            ),
            CatalogOption(
                id="sw-service-levels",
                name="Service-level provisioning",
                summary="Assign a performance target per storage group, not per drive.",
                details=(
                    "Rather than hand-placing data on tiers, an administrator "
                    "assigns a service level (e.g. Diamond, Gold) to a storage "
                    "group and PowerMaxOS holds that response-time target "
                    "automatically. Provisioning becomes a policy statement, "
                    "and the all-NVMe pool makes the targets easy to meet."
                ),
            ),
            CatalogOption(
                id="sw-cyber",
                name="Cyber resiliency & anomaly detection",
                summary="Hardware root of trust, secure snapshots, ransomware detection.",
                details=(
                    "PowerMax roots its firmware in a hardware root of trust, "
                    "offers secure (immutable, retention-locked) snapshots that "
                    "an attacker cannot delete, and analyzes I/O for "
                    "ransomware-like behavior. On the 8500 this extends to "
                    "Cyber Recovery for PowerMax — an isolated cyber vault, "
                    "delivered through Dell Professional Services — for a "
                    "known-good restore point kept off the production network."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="management",
        name="Management & monitoring",
        blurb=(
            "PowerMax is driven from Unisphere for PowerMax on the management "
            "network; everything it does is also automatable over REST and "
            "surfaced to Dell's cloud."
        ),
        limits="Management network kept off the data path",
        region_ids=["mgmt-a", "mgmt-b"],
        options=[
            CatalogOption(
                id="mgmt-unisphere",
                name="Unisphere for PowerMax + REST API",
                summary="The management application and its API.",
                details=(
                    "Provisioning, monitoring, SRDF configuration, and upgrades "
                    "in one console, with every operation available over a REST "
                    "API. Storage groups, service levels, and snapshots are "
                    "day-to-day objects; the API is what puts them into "
                    "automation pipelines."
                ),
            ),
            CatalogOption(
                id="mgmt-cloudiq",
                name="CloudIQ / APEX AIOps",
                summary="Dell's cloud monitoring: health, capacity forecasting, anomalies.",
                details=(
                    "The array streams telemetry to Dell's cloud service, "
                    "which trends capacity, forecasts exhaustion, scores "
                    "health, and flags anomalies across the whole fleet. "
                    "Read-only by design — control stays on-premises. Pairs "
                    "with the intelligent PDUs' real-time power and "
                    "environmental telemetry."
                ),
            ),
            CatalogOption(
                id="mgmt-automation",
                name="Ansible / Terraform integration",
                summary="Supported modules and providers for infrastructure-as-code.",
                details=(
                    "Dell maintains Ansible collections and a Terraform "
                    "provider for PowerMax, so storage groups, volumes, "
                    "snapshots, and SRDF pairs live in the same pipelines as "
                    "the compute they serve — storage changes become code "
                    "review, not tickets."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="power",
        name="Power & PDUs",
        blurb=(
            "PowerMax racks take utility power through intelligent PDUs and "
            "feed two independent power zones, so the array rides through the "
            "loss of a whole feed."
        ),
        limits="Two power zones · single- or three-phase input",
        region_ids=["psu-a", "psu-b"],
        options=[
            CatalogOption(
                id="pwr-single-phase",
                name="Single-phase input",
                summary="200–240 VAC single-phase line cords, two power zones.",
                details=(
                    "The simpler feed for smaller configurations: 30/32 A "
                    "single-phase cords, one per power zone, sized to the "
                    "number of node pairs and DMEs. A 2500 needs one to two "
                    "cords per zone depending on how full it is."
                ),
            ),
            CatalogOption(
                id="pwr-three-phase",
                name="Three-phase input (Delta or Wye)",
                summary="Higher-density feed for larger configurations.",
                details=(
                    "Three-phase power (North American Delta or International "
                    "Wye) for denser cabinets, delivering more capacity per "
                    "cord. A fully populated 8500 draws on the order of 15 kVA "
                    "per cabinet at high ambient temperature — three-phase "
                    "keeps the cord count and per-cord current manageable."
                ),
            ),
            CatalogOption(
                id="pwr-ipdu",
                name="Intelligent PDU",
                summary="Real-time power, voltage, current, temperature, humidity telemetry.",
                details=(
                    "Default from the PowerMax 10.1 release: the PDUs are "
                    "instrumented, streaming environmental and power telemetry "
                    "to Unisphere and CloudIQ so capacity planning includes the "
                    "power envelope, not just the terabytes."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="cabinet",
        name="Cabinet & dispersion",
        blurb=(
            "PowerMax is a rack-scale system delivered in a 19″ system bay. "
            "How the bays are arranged — and, on the 8500, how far apart — is "
            "part of the configuration."
        ),
        limits="Standard 19″ bay · third-party rack option · dispersion (8500)",
        region_ids=[],
        options=[
            CatalogOption(
                id="cab-system-bay",
                name="Dell system bay",
                summary="The engineered 19″ cabinet with PDUs and cable management.",
                details=(
                    "PowerMax ships in a Dell system bay carrying the node "
                    "pairs, DMEs, PDUs, and fabric cabling. A 2500 is a single "
                    "bay (single floor tile); an 8500 can pack up to six node "
                    "pairs into one bay in a dense configuration, or spread "
                    "them for a balanced one."
                ),
            ),
            CatalogOption(
                id="cab-third-party",
                name="Third-party rack mount",
                summary="Mount the components in an existing data-center rack.",
                details=(
                    "For sites standardized on their own racks, PowerMax "
                    "supports third-party rack mounting of the node pairs and "
                    "enclosures rather than the Dell system bay."
                ),
            ),
            CatalogOption(
                id="cab-dispersion",
                name="System-bay dispersion (PowerMax 8500)",
                summary="Separate bays by up to 25 m to work around floor limits.",
                details=(
                    "On the 8500, the Dynamic Fabric lets individual or "
                    "contiguous groups of system bays sit up to 82 feet (25 m) "
                    "from the first bay. That solves data-center floor-loading "
                    "constraints and lets a large array route around obstacles "
                    "instead of demanding one continuous run of tiles."
                ),
            ),
        ],
    ),
]
