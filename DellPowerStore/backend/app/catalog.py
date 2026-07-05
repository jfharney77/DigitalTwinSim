"""The components-and-options menu for a PowerStore appliance.

Like the chassis anatomy, the catalog is data, not code. ``region_ids`` tie
each category to the floorplan regions it slots into, so the UI can light
up "where it lives". ``details`` are written for a technically skilled
reader who is new to storage arrays — Dell jargon is spelled out on first
use. Figures follow Dell's PowerStore spec sheet; treat them as
product-literature numbers, not benchmarks.
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
                    "The smallest tier: fewer cores and less DRAM per node, "
                    "and two NVMe NVRAM drives instead of four. Same "
                    "PowerStoreOS, same always-on data reduction, same "
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
                    "databases. Steps up cores, DRAM, and NVRAM over the "
                    "500T, which raises both IOPS headroom and how much "
                    "inline deduplication/compression the nodes can do "
                    "without breaking a sweat."
                ),
            ),
            CatalogOption(
                id="model-3200t",
                name="PowerStore 3200T",
                summary="Mid-range tier; the first with the full 4-NVRAM complement.",
                details=(
                    "From the 3200T up, each appliance carries four NVMe "
                    "NVRAM write-cache drives, doubling write-cache "
                    "bandwidth. Suits heavier virtualization estates and "
                    "OLTP databases where sustained write latency matters "
                    "as much as peak reads."
                ),
            ),
            CatalogOption(
                id="model-5200t",
                name="PowerStore 5200T",
                summary="Performance tier for consolidation at scale.",
                details=(
                    "High core counts and large DRAM per node make this the "
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
                    "The flagship: the most cores, DRAM, and front-end "
                    "bandwidth per node. Where sub-millisecond latency "
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
            "to 21 slots in the base enclosure (the last four are reserved "
            "for NVRAM), and drives can be added one at a time."
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
                    "Doubles the capacity per slot; with always-on 4:1 data "
                    "reduction, a dozen of these can present well over 300 "
                    "TB effective. The typical choice when consolidating "
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
                name="Self-encrypting drive (SED) variants",
                summary="FIPS-capable encryption at the drive, key-managed by the array.",
                details=(
                    "Each capacity point is available as a self-encrypting "
                    "drive: the drive encrypts every block in hardware and "
                    "the array manages the keys (Data at Rest Encryption). "
                    "Performance is unchanged — the crypto is in the drive "
                    "controller — and a decommissioned drive is unreadable "
                    "the moment its key is destroyed. Note: an appliance is "
                    "all-SED or all-non-SED, decided at first configuration."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="nvram",
        name="NVRAM write cache",
        blurb=(
            "The last four front slots hold dedicated NVMe NVRAM drives — "
            "the non-volatile write cache. Keeping write cache on its own "
            "devices, rather than in battery-backed DRAM alone, is what "
            "lets a tiny battery protect every acknowledged write."
        ),
        limits="2 NVRAM drives on 500T/1200T; 4 on 3200T and above",
        region_ids=["nvram"],
        options=[
            CatalogOption(
                id="nvram-dual",
                name="2× NVMe NVRAM (500T · 1200T)",
                summary="Mirrored pair of write-cache drives on the entry tiers.",
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
                name="4× NVMe NVRAM (3200T and up)",
                summary="Doubled write-cache lanes for the performance tiers.",
                details=(
                    "Four NVRAM devices double the cache bandwidth and let "
                    "heavy write bursts — database checkpoints, VM storms "
                    "— drain without queuing at the cache. This is a fixed "
                    "attribute of the model tier, not a field upgrade."
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
                    "back-end links to both nodes so the dual-path rule "
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
                    "Four ports of 32 Gb Fibre Channel, speaking both "
                    "traditional SCSI-over-FC and NVMe-over-FC on the same "
                    "port. The default in shops with an existing FC SAN — "
                    "dedicated fabric, lossless by design, and mature "
                    "multipathing on every OS."
                ),
            ),
            CatalogOption(
                id="iomod-64gfc",
                name="4-port 64 Gb Fibre Channel",
                summary="Latest-generation FC for new SAN builds.",
                details=(
                    "Doubles per-port FC bandwidth for new fabrics; "
                    "backward-compatible with 32/16 Gb switches, so it's a "
                    "future-proofing pick as much as a performance one."
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
                name="Hot-swap PSU pair (Platinum efficiency)",
                summary="Redundant supplies sized for a fully loaded enclosure.",
                details=(
                    "80 PLUS Platinum-rated supplies; either one alone can "
                    "carry the whole enclosure, drives included. Replacing "
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
                summary="Always-on data reduction, 4:1 guaranteed under Dell's program.",
                details=(
                    "Every write is deduplicated (identical blocks stored "
                    "once) and compressed before it reaches flash — "
                    "inline, not as a later cleanup pass, and with no off "
                    "switch. Dell contractually guarantees 4:1 reduction "
                    "on typical workloads, which is why effective-capacity "
                    "math is quoted at 4× raw."
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
                name="Anomaly & ransomware detection",
                summary="PowerStoreOS watches I/O patterns for encryption-like behavior.",
                details=(
                    "Recent PowerStoreOS releases analyze write entropy and "
                    "access patterns to flag ransomware-like activity, and "
                    "pair it with hardened snapshot policies so a "
                    "known-good restore point survives an attack. Not a "
                    "substitute for host security — a last line inside the "
                    "storage layer."
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
                name="CloudIQ / APEX AIOps",
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
                summary="Seconds of ride-through to flush cache on AC loss — not a UPS.",
                details=(
                    "Each node's BBU exists for one scenario: AC "
                    "disappears with dirty data in cache. The battery "
                    "powers the node just long enough to 'vault' — flush "
                    "cached writes to non-volatile NVMe NVRAM — then the "
                    "node shuts down cleanly. On power return the array "
                    "replays the vault and no acknowledged write is "
                    "missing. BBUs self-test on every boot and "
                    "periodically after."
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
