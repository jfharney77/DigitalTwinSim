"""The components-and-options menu for a PowerStore appliance.

Like the chassis anatomy, the catalog is data, not code. ``region_ids`` tie
each category to the floorplan regions it slots into, so the UI can light
up "where it lives". ``details`` are written for a technically skilled
reader who is new to storage arrays — Dell jargon is spelled out on first
use. Figures follow Dell's PowerStore Gen 2 spec sheet and the
"Introduction to the Platform" white paper (H18149), both linked from the
anatomy sources; treat them as product-literature numbers, not benchmarks.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="models",
        name="Appliance model",
        blurb=(
            "Every PowerStore T model is the same 2U dual-node chassis; the "
            "tiers differ in the CPUs, DRAM, and NVRAM inside each node — "
            "i.e., in how much data-service work the appliance can push. "
            "All are unified: block and file from the same box."
        ),
        limits="One model per appliance; nodes always come in matched pairs",
        region_ids=["cpu-a", "cpu-b"],
        options=[
            CatalogOption(
                id="model-500t",
                name="PowerStore 500T",
                summary="Entry model for smaller sites and edge deployments.",
                details=(
                    "The smallest tier: one Xeon per node instead of two (24 "
                    "cores and 192 GB per appliance on Dell's spec sheet), "
                    "and no NVMe NVRAM drives at all, so all 25 front slots "
                    "take data drives. Same PowerStoreOS, same always-on data reduction, same "
                    "dual-node availability — the ceiling is performance "
                    "and capacity, not features. A common choice where the "
                    "workload is real but modest: a branch site, a small "
                    "vSphere cluster, a lab that still needs array-class "
                    "resilience."
                ),
            ),
            CatalogOption(
                id="model-1200t",
                name="PowerStore 1200T",
                summary="Mainstream tier for general-purpose mixed workloads.",
                details=(
                    "The volume model: a comfortable fit for consolidated "
                    "virtualization, file serving, and departmental "
                    "databases. Steps up to two Xeons per node (40 cores and "
                    "384 GB per appliance) and adds a mirrored pair of NVRAM "
                    "write-cache drives over the 500T, which raises both IOPS headroom and how much "
                    "inline deduplication/compression the nodes can do "
                    "without breaking a sweat."
                ),
            ),
            CatalogOption(
                id="model-3200t",
                name="PowerStore 3200T",
                summary="Mid-range tier: more cores and twice the memory of the 1200T.",
                details=(
                    "64 cores and 768 GB per appliance on Dell's spec sheet, "
                    "with the same two NVMe NVRAM write-cache drives as the "
                    "1200T. Also sold as the 3200Q, which takes lower-cost "
                    "QLC flash instead of TLC. Suits heavier virtualization estates and "
                    "OLTP databases where sustained write latency matters "
                    "as much as peak reads."
                ),
            ),
            CatalogOption(
                id="model-5200t",
                name="PowerStore 5200T",
                summary="Performance tier for consolidation at scale.",
                details=(
                    "96 cores and 1,152 GB per appliance, and the first tier "
                    "with four NVMe NVRAM write-cache drives rather than "
                    "two. High core counts and large DRAM make this the "
                    "usual answer for consolidating many mixed workloads "
                    "onto one appliance — hundreds of VMs, multiple "
                    "databases, and file shares at once, with data "
                    "reduction still inline. A frequent building block for "
                    "multi-appliance clusters."
                ),
            ),
            CatalogOption(
                id="model-9200t",
                name="PowerStore 9200T",
                summary="Top tier: maximum IOPS, bandwidth, and capacity per appliance.",
                details=(
                    "The flagship of this generation: 112 cores and 2,560 GB "
                    "per appliance, with four NVRAM drives. Where sub-millisecond latency "
                    "under heavy concurrent load is the requirement — "
                    "large OLTP estates, analytics staging, or serving as "
                    "the anchor appliance of a four-appliance cluster."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="drives",
        name="Capacity drives",
        blurb=(
            "All 25 front slots speak PCIe — there are no spinning disks or "
            "SAS SSDs anywhere in the data path. Capacity SSDs populate up "
            "to 21 slots in the base enclosure (slots 21 through 24 are "
            "reserved for NVRAM on every model but the 500T), and drives can "
            "be added one at a time."
        ),
        limits="Minimum 6 drives; up to 21 capacity SSDs in the base enclosure",
        region_ids=["drive-bay"],
        options=[
            CatalogOption(
                id="drive-1_92tb",
                name="1.92 TB NVMe TLC SSD",
                summary="Smallest capacity point; most drives per terabyte.",
                details=(
                    "Triple-level-cell (TLC) NAND — the mainstream "
                    "enterprise flash grade, balancing endurance and cost. "
                    "Smaller drives mean more spindles-worth of controllers "
                    "per terabyte, which can actually help small-block "
                    "performance, at the price of more slots consumed."
                ),
            ),
            CatalogOption(
                id="drive-3_84tb",
                name="3.84 TB NVMe TLC SSD",
                summary="Common starting point for balanced builds.",
                details=(
                    "The usual default for general-purpose builds: enough "
                    "capacity per slot to leave growth room in the "
                    "enclosure, small enough that a single-drive rebuild "
                    "(spread across all drives by the resiliency engine) "
                    "completes quickly."
                ),
            ),
            CatalogOption(
                id="drive-7_68tb",
                name="7.68 TB NVMe TLC SSD",
                summary="Capacity-per-slot sweet spot for consolidation.",
                details=(
                    "Doubles the capacity per slot; at the 5:1 reduction "
                    "Dell guarantees on reducible data, less the share that "
                    "drive-failure protection takes, a dozen of these can "
                    "present around 370 TB effective (illustrative; real "
                    "ratios depend on the data). The typical choice when consolidating "
                    "many workloads onto one appliance."
                ),
            ),
            CatalogOption(
                id="drive-15_36tb",
                name="15.36 TB NVMe TLC SSD",
                summary="Maximum capacity per slot.",
                details=(
                    "The densest option — a base enclosure of these "
                    "approaches a third of a petabyte raw before data "
                    "reduction. Chosen when rack space and capacity "
                    "dominate; per-terabyte performance is lower simply "
                    "because fewer drive controllers share the work."
                ),
            ),
            CatalogOption(
                id="drive-sed",
                name="FIPS-validated self-encrypting drives",
                summary="Every drive self-encrypts; FIPS 140 validated drives are the option.",
                details=(
                    "Every PowerStore drive is a self-encrypting drive "
                    "(SED): it encrypts every block in hardware and the "
                    "array, or an external KMIP key manager, holds the keys "
                    "(Data at Rest Encryption). Performance is unchanged — "
                    "the crypto is in the drive controller — and a "
                    "decommissioned drive is unreadable the moment its key "
                    "is destroyed. What you choose at order time is whether "
                    "the drives are FIPS 140-2 or 140-3 Level 2 validated, "
                    "which regulated buyers may need."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="nvram",
        name="NVRAM write cache",
        blurb=(
            "The last front slots (21 through 24) hold dedicated NVMe NVRAM "
            "drives — the non-volatile write cache. Keeping write cache on its own "
            "devices, rather than in battery-backed DRAM alone, is what "
            "lets a tiny battery protect every acknowledged write."
        ),
        limits="None on 500T; 2 NVRAM drives on 1200T/3200T; 4 on 5200T/9200T",
        region_ids=["nvram"],
        options=[
            CatalogOption(
                id="nvram-dual",
                name="2× NVMe NVRAM (1200T · 3200T)",
                summary="Mirrored pair of write-cache drives on the mid tiers.",
                details=(
                    "Writes are acknowledged once they land in NVRAM with "
                    "both nodes able to reach them — mirrored, so a single "
                    "NVRAM device failure loses nothing. NVRAM devices are "
                    "small but built for constant write traffic; capacity "
                    "SSDs see only the calmer, already-reduced destage "
                    "stream."
                ),
            ),
            CatalogOption(
                id="nvram-quad",
                name="4× NVMe NVRAM (5200T · 9200T)",
                summary="Doubled write-cache lanes for the performance tiers.",
                details=(
                    "Four NVRAM devices double the cache bandwidth and let "
                    "heavy write bursts — database checkpoints, VM storms "
                    "— drain without queuing at the cache. This is a fixed "
                    "attribute of the model tier, not a field upgrade. The "
                    "entry 500T has no NVRAM drives; Dell's platform white "
                    "paper says its internal M.2 device holds the vaulted "
                    "cache data instead."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="expansion",
        name="Expansion enclosures (scale-up)",
        blurb=(
            "When 21 capacity slots aren't enough, expansion shelves add "
            "drives to the same appliance — 'scale-up': more capacity "
            "behind the same pair of controllers."
        ),
        limits="Up to 3 expansion enclosures per appliance",
        region_ids=["drive-bay"],
        options=[
            CatalogOption(
                id="exp-ens24",
                name="ENS24 NVMe expansion enclosure",
                summary="24 more NVMe slots, cabled to both nodes.",
                details=(
                    "A 2U shelf with 24 NVMe slots, attached over dedicated "
                    "100 GbE back-end links to both nodes so the dual-path rule "
                    "holds for every drive in the system. Three shelves "
                    "take one appliance past 90 drives. Scale-up adds "
                    "capacity but not compute — when the controllers "
                    "themselves are the ceiling, you scale out instead "
                    "(see Clustering)."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="clustering",
        name="Clustering (scale-out)",
        blurb=(
            "Up to four appliances join one cluster: one management plane, "
            "one pool of names, and volumes that migrate between "
            "appliances without hosts noticing — 'scale-out': more "
            "controllers, not just more drives."
        ),
        limits="Up to 4 appliances per cluster",
        region_ids=["interconnect", "embedded-a", "embedded-b"],
        options=[
            CatalogOption(
                id="cluster-single",
                name="Single appliance",
                summary="One appliance, still fully redundant inside.",
                details=(
                    "The starting point for most deployments. The dual-node "
                    "design already covers hardware failure; clustering "
                    "adds headroom, not basic availability. Every cluster "
                    "feature is present from day one, so growing later is "
                    "an addition, not a migration."
                ),
            ),
            CatalogOption(
                id="cluster-multi",
                name="Multi-appliance cluster (2–4)",
                summary="Scale out compute and capacity under one management plane.",
                details=(
                    "Additional appliances join over the mezzanine-port "
                    "cluster network. PowerStore Manager shows one system; "
                    "its resource balancer recommends placements and can "
                    "move volumes between appliances live. This is how you "
                    "grow past what one pair of controllers can do — and "
                    "how mixed generations coexist, since new appliances "
                    "can join an existing cluster."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="io-modules",
        name="I/O modules",
        blurb=(
            "The hot-swap cards in each node's two rear slots set the "
            "array's front-end personality — which fabrics hosts connect "
            "over. The orange handles mark them field-serviceable with the "
            "array online."
        ),
        limits="2 slots per node · always installed in matching pairs across nodes",
        region_ids=["iomod-a1", "iomod-a2", "iomod-b1", "iomod-b2"],
        options=[
            CatalogOption(
                id="iomod-25gbe",
                name="4-port 25 GbE optical",
                summary="The Ethernet workhorse: iSCSI, NVMe-TCP, and file.",
                details=(
                    "Four SFP28 ports per module for iSCSI and NVMe-TCP "
                    "block traffic and NFS/SMB file traffic. 25 GbE is the "
                    "current datacenter default — the same cabling plant as "
                    "10 GbE with 2.5× the bandwidth. Modules are installed "
                    "in matching pairs across nodes so every host path "
                    "exists on both — that symmetry is what makes failover "
                    "invisible to hosts."
                ),
            ),
            CatalogOption(
                id="iomod-10gbaset",
                name="4-port 10GBASE-T",
                summary="Ethernet over copper RJ45 for existing cable plants.",
                details=(
                    "The same protocols over ordinary Cat6A copper. Chosen "
                    "where the switch layer is already 10GBASE-T or optics "
                    "budgets are tight; latency is marginally higher than "
                    "optical but rarely decisive."
                ),
            ),
            CatalogOption(
                id="iomod-100gbe",
                name="2-port 100 GbE QSFP",
                summary="Maximum Ethernet bandwidth per slot — the orange-handled module in Dell's photos.",
                details=(
                    "Two QSFP ports per module for NVMe-TCP and iSCSI at "
                    "100 Gb/s — the option for bandwidth-hungry analytics "
                    "or dense virtualization behind a modern spine-leaf "
                    "network. One of these is the module shown mid-service "
                    "in Dell's close-up photography."
                ),
            ),
            CatalogOption(
                id="iomod-32gfc",
                name="4-port 32 Gb Fibre Channel",
                summary="The classic SAN fabric: FC-SCSI and FC-NVMe.",
                details=(
                    "Four ports of 32 Gb Fibre Channel (also runs at 16 Gb), "
                    "the fastest FC option on this generation — 64 Gb FC "
                    "arrives with the later PowerStore Elite. It speaks both "
                    "traditional SCSI-over-FC and NVMe-over-FC on the same "
                    "port. The default in shops with an existing FC SAN — "
                    "dedicated fabric, lossless by design, and mature "
                    "multipathing on every OS."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="mezzanine",
        name="Embedded module (mezzanine ports)",
        blurb=(
            "Each node's built-in 4-port card — connectivity that doesn't "
            "spend an I/O module slot. It carries host traffic and, in "
            "clusters, the intra-cluster network."
        ),
        limits="One embedded module per node, configured at ordering time",
        region_ids=["embedded-a", "embedded-b"],
        options=[
            CatalogOption(
                id="mezz-25gbe",
                name="4-port 25 GbE mezzanine",
                summary="Optical/DAC ports for host I/O and the cluster network.",
                details=(
                    "SFP28 ports usable for iSCSI, NVMe-TCP, NFS/SMB, and "
                    "— on multi-appliance systems — the cluster "
                    "interconnect between appliances. Keeping the cluster "
                    "network on the mezzanine leaves both I/O module slots "
                    "free for host-facing fabrics."
                ),
            ),
            CatalogOption(
                id="mezz-10gbaset",
                name="4-port 10GBASE-T mezzanine",
                summary="The same embedded connectivity over RJ45 copper.",
                details=(
                    "Identical role over Cat6A. Common at edge sites where "
                    "the top-of-rack switching is copper and simplicity "
                    "beats raw bandwidth."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="power",
        name="Power supplies",
        blurb=(
            "Two hot-swap PSUs, one per node canister. Feed them from "
            "separate rails: the appliance rides through a full circuit "
            "outage on the surviving supply."
        ),
        limits="2 PSUs per appliance (one per node) · hot-swap",
        region_ids=["psu-a", "psu-b"],
        options=[
            CatalogOption(
                id="psu-platinum",
                name="Hot-swap PSU pair (1800 W or 2100 W)",
                summary="Redundant supplies sized for a fully loaded enclosure.",
                details=(
                    "Two redundant supplies, 1800 W or 2100 W each depending "
                    "on model (the 9200T takes only the 2100 W part, and the "
                    "1800 W part needs 200–240 V power). Dell's spec sheet "
                    "puts a fully populated 5200T at about 1.4 kW in typical "
                    "conditions, so the pair has headroom to spare. Replacing "
                    "one is an online operation — slide out, slide in — "
                    "with the array serving I/O throughout. There is no "
                    "PSU sizing exercise as on a server: the pair ships "
                    "matched to the chassis."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="software",
        name="PowerStoreOS software & data services",
        blurb=(
            "Licensing is all-inclusive: every data service ships with the "
            "array, enabled by policy rather than purchase order. These "
            "are the ones that shape designs."
        ),
        limits="All-inclusive with the appliance; no per-feature licenses",
        region_ids=[],
        options=[
            CatalogOption(
                id="sw-data-reduction",
                name="Inline deduplication & compression",
                summary="Always-on data reduction, 5:1 guaranteed under Dell's program.",
                details=(
                    "Every write is deduplicated (identical blocks stored "
                    "once) and compressed before it reaches flash — "
                    "inline, not as a later cleanup pass, and with no off "
                    "switch. Dell's Future-Proof Program guarantees 5:1 "
                    "reduction on reducible data for this generation, and "
                    "the spec sheet's effective-capacity figures assume the "
                    "same 5:1 average. Already-compressed or encrypted data "
                    "will not reduce, guarantee or no."
                ),
            ),
            CatalogOption(
                id="sw-snapshots",
                name="Snapshots & thin clones",
                summary="Instant point-in-time copies that consume only changed blocks.",
                details=(
                    "Snapshots capture a volume at an instant by freezing "
                    "metadata pointers — creation is effectively free and "
                    "space grows only with change. Thin clones make a "
                    "snapshot writable: a full-size, independent-looking "
                    "copy of a production database for dev/test, in "
                    "seconds, at near-zero capacity."
                ),
            ),
            CatalogOption(
                id="sw-async-repl",
                name="Asynchronous replication",
                summary="Scheduled replication to another PowerStore for DR.",
                details=(
                    "Ships periodic deltas of a volume (or volume group) "
                    "to a partner array, typically at another site — RPOs "
                    "(recovery point objectives: how much data you can "
                    "afford to lose) of minutes. The replica can be tested "
                    "without breaking replication, which is how DR drills "
                    "should work."
                ),
            ),
            CatalogOption(
                id="sw-metro",
                name="Metro Volume (synchronous, active/active)",
                summary="The same volume live on two arrays at once — zero RPO.",
                details=(
                    "A Metro Volume exists on two PowerStore arrays "
                    "simultaneously; hosts see one volume with paths to "
                    "both sites and writes commit to both before "
                    "acknowledgement. An entire array — or site — can fail "
                    "with zero data loss and no host-side failover script. "
                    "Distance is bounded by latency (metro range, hence "
                    "the name)."
                ),
            ),
            CatalogOption(
                id="sw-vvols",
                name="vVols 2.0 (VMware Virtual Volumes)",
                summary="Per-VM storage objects instead of shared datastore LUNs.",
                details=(
                    "With vVols, each virtual machine's disks are "
                    "individual objects on the array rather than files in "
                    "a shared datastore LUN. Array features — snapshots, "
                    "replication, QoS — then apply per VM, driven from "
                    "vCenter through policy. PowerStore's vVols "
                    "implementation is among the most complete, a legacy "
                    "of its tight VMware integration (the discontinued "
                    "X-models could even run ESXi and VMs directly on the "
                    "array, a mode called AppsON)."
                ),
            ),
            CatalogOption(
                id="sw-security",
                name="Secure snapshots & ransomware detection",
                summary="Snapshots an attacker cannot delete, plus Dell Cyber Detect to find the clean one.",
                details=(
                    "PowerStoreOS includes immutable, secure snapshots: once "
                    "taken they cannot be changed or deleted before their "
                    "retention expires, so a known-good restore point "
                    "survives an attack. Detection is a separate product, "
                    "Dell Cyber Detect, which reads snapshot content to "
                    "find ransomware corruption; Dell announced it for "
                    "PowerStore in 2026 and states 99.99% accuracy, a "
                    "vendor figure. Not a substitute for host security — a "
                    "last line inside the storage layer."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="management",
        name="Management & monitoring",
        blurb=(
            "The array is driven from PowerStore Manager on the dedicated "
            "management ports; everything it can do is also automatable "
            "over REST."
        ),
        limits="Cluster IP floats across both nodes' management ports",
        region_ids=["mgmt-a", "mgmt-b"],
        options=[
            CatalogOption(
                id="mgmt-manager",
                name="PowerStore Manager + REST API",
                summary="The built-in web UI and its API — no management server to install.",
                details=(
                    "Served from the appliance itself at the cluster IP: "
                    "provisioning, monitoring, upgrades, and support "
                    "tooling in one place, with every operation available "
                    "over REST. Day-2 work — grow a volume, take a "
                    "snapshot, add a host — is minutes in the UI or one "
                    "API call."
                ),
            ),
            CatalogOption(
                id="mgmt-cloudiq",
                name="CloudIQ (now Dell AIOps)",
                summary="Dell's cloud monitoring: fleet health, capacity forecasting, anomaly alerts.",
                details=(
                    "The array phones telemetry home to Dell's cloud "
                    "service, which trends capacity, forecasts when you'll "
                    "run out, scores health, and alerts on anomalies "
                    "across your whole fleet. Read-only by design — "
                    "control stays on-prem."
                ),
            ),
            CatalogOption(
                id="mgmt-automation",
                name="Ansible / Terraform integration",
                summary="Supported modules and providers for infrastructure-as-code.",
                details=(
                    "Dell maintains Ansible collections and a Terraform "
                    "provider for PowerStore, so volumes, hosts, and "
                    "protection policies can live in the same pipelines "
                    "as the compute they serve — storage tickets become "
                    "pull requests."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="protection",
        name="Power-loss & node protection",
        blurb=(
            "The hardware that backs the array's core promise: an "
            "acknowledged write is never lost — not to a power cut, not "
            "to a dead controller."
        ),
        limits="1 BBU per node · vault is automatic and self-testing",
        region_ids=["bbu-a", "bbu-b"],
        options=[
            CatalogOption(
                id="prot-bbu",
                name="Battery backup units (vault power)",
                summary="Brief hold-up so the write cache can save itself on AC loss — not a UPS.",
                details=(
                    "Each node's BBU exists for one scenario: AC "
                    "disappears with dirty data in cache. The battery "
                    "powers the NVRAM drive slots and the node's management "
                    "controller just long enough for the NVRAM drives to "
                    "'vault' — copy their volatile contents into flash "
                    "inside the same drive — then the system powers off. "
                    "Dell says each BBU holds enough charge for several "
                    "back-to-back power failures. On power return the array "
                    "replays the vault and no acknowledged write is "
                    "missing. The power-on trace here shows a battery check "
                    "as the first gate; that sequencing is illustrative."
                ),
            ),
            CatalogOption(
                id="prot-dual-node",
                name="Dual-node redundancy semantics",
                summary="A node reboot — planned or not — is not downtime.",
                details=(
                    "Because both nodes are active and every drive is "
                    "dual-ported, one node can fail, reboot, or be "
                    "replaced while its partner carries all host paths. "
                    "Software upgrades use this deliberately: one node "
                    "updates and reboots, hands back, then the other — "
                    "the array never stops serving. Hosts need correctly "
                    "configured multipathing to ride through, which is "
                    "the one thing the array can't do for you."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="rack",
        name="Rack hardware",
        blurb="The unglamorous parts that make the 2U box a rack citizen.",
        limits="Per-appliance; expansion shelves rail separately",
        region_ids=[],
        options=[
            CatalogOption(
                id="rack-rails",
                name="Sliding rails",
                summary="Tool-less rails; nodes and PSUs service from the rear without unracking.",
                details=(
                    "Standard 19-inch rails. Note the service model: "
                    "drives swap from the front, and nodes, I/O modules, "
                    "and PSUs all swap from the rear — routine service "
                    "never requires pulling the enclosure out of the "
                    "rack."
                ),
            ),
            CatalogOption(
                id="rack-bezel",
                name="Front bezel",
                summary="The honeycomb face with status lighting; locks the drive bay.",
                details=(
                    "PowerStore's hexagon-pattern bezel covers the 25 "
                    "drive slots, carries the status LED bar, and locks — "
                    "casual physical access to hot-swap drives is a real "
                    "consideration in shared datacenter cages."
                ),
            ),
        ],
    ),
]
