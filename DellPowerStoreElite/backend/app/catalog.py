"""Catalog data: what a PowerStore Elite is configured from.

Backend data, not frontend code, like every twin. Written for a technically
skilled reader who is new to storage arrays: Dell vocabulary (E3 NVMe,
RDMA, data reduction ratio, multipathing, QLC/TLC) is spelled out on first
use. Figures come from Dell's DTW 2026 launch materials and press coverage
(see anatomy.py sources); they are the vendor's claims, labeled as such
where it matters.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="model",
        name="Appliance model",
        blurb=(
            "Three Elite models share the same 3U, 40-slot chassis and the "
            "same software; they differ in processor cores, memory, and how "
            "far they scale."
        ),
        limits="1 model per appliance · up to 4 appliances per cluster",
        region_ids=["elite-cpu-a", "elite-cpu-b", "elite-bay"],
        options=[
            CatalogOption(
                id="elite-1500",
                name="PowerStore Elite 1500",
                summary="The entry point to the Elite platform.",
                details=(
                    "The smallest Elite. Same 3U chassis, same E3 NVMe bay, "
                    "same PowerStoreOS and data services as its bigger "
                    "siblings — fewer cores and less DRAM per node. Because "
                    "clustering is mixed-generation and mixed-model, a 1500 "
                    "bought today can later share a cluster with a larger "
                    "Elite, or with the prior-generation array it arrived to "
                    "relieve."
                ),
            ),
            CatalogOption(
                id="elite-5500",
                name="PowerStore Elite 5500",
                summary="The midrange workhorse of the line.",
                details=(
                    "The volume model: the core-count and memory step where "
                    "the 3x-performance comparisons against the prior "
                    "generation's 5500 are drawn. For most consolidation "
                    "estates — block plus file plus VMs — this is the "
                    "default answer."
                ),
            ),
            CatalogOption(
                id="elite-9500",
                name="PowerStore Elite 9500",
                summary="The top model, for the heaviest consolidation.",
                details=(
                    "Maximum cores, maximum DRAM, maximum front-end ports. "
                    "Where a single 3U appliance is asked to hold the full "
                    "5.8 PB effective and serve it at the platform's "
                    "ceiling, this is the configuration doing it."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="processors",
        name="Processors & dynamic core allocation",
        blurb=(
            "Intel Xeon Scalable processors with up to 50% more cores than "
            "the prior generation's 3200T/5500 class — and software that "
            "moves those cores to where the load is."
        ),
        limits="2 nodes per appliance · active/active",
        region_ids=["elite-cpu-a", "elite-cpu-b"],
        options=[
            CatalogOption(
                id="xeon-scalable",
                name="Intel Xeon Scalable (per node)",
                summary="Up to 50% more cores per node than the prior generation.",
                details=(
                    "Each of the two controller nodes carries an Intel Xeon "
                    "Scalable processor. Every data service — deduplication, "
                    "compression, RAID math, replication — runs on these "
                    "cores, so the +50% core count is a direct input to the "
                    "3x performance claim."
                ),
            ),
            CatalogOption(
                id="dynamic-cores",
                name="Dynamic core allocation",
                summary="Built-in AI shifts cores between block, file and reduction work.",
                details=(
                    "PowerStore Elite's built-in AI reassigns processor "
                    "cores between front-end protocols, file services and "
                    "background data reduction as the workload mix shifts, "
                    "and rebalances placement across the cluster "
                    "continuously. Dell's claim for the automation layer as "
                    "a whole is up to 95% less manual effort than "
                    "traditional array management — the tuning the "
                    "administrator no longer does."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="memory",
        name="Memory & Metadata Acceleration",
        blurb=(
            "DDR5 DIMM banks per node, and a metadata layer engineered to "
            "live in them."
        ),
        limits="Per-node DIMM banks · mirrored write cache via NVRAM",
        region_ids=["elite-dimm-a", "elite-dimm-b"],
        options=[
            CatalogOption(
                id="ddr5",
                name="DDR5 system memory",
                summary="A memory generation up from the prior array.",
                details=(
                    "DDR5 feeds the nodes' caches and metadata structures "
                    "with more bandwidth per DIMM than the prior "
                    "generation's memory — necessary headroom once PCIe "
                    "Gen 5 doubles what the drives and ports can push."
                ),
            ),
            CatalogOption(
                id="metadata-acceleration",
                name="Metadata Acceleration",
                summary="Reads up to 70% faster by keeping hot metadata resident.",
                details=(
                    "Every read consults metadata — where a block lives, "
                    "whether it is deduplicated, which snapshot chain owns "
                    "it. Metadata Acceleration keeps those hot structures "
                    "pinned in DRAM rather than paging them from flash; "
                    "Dell credits it with reads up to 70% faster on the "
                    "Elite platform."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="drives",
        name="Drives — the E3 NVMe bay",
        blurb=(
            "40 low-profile E3 NVMe slots per 3U appliance, taking QLC or "
            "TLC flash — up to 3x the density of the prior generation."
        ),
        limits="40 slots per appliance · dual-ported · QLC or TLC",
        region_ids=["elite-bay", "elite-nvram"],
        options=[
            CatalogOption(
                id="e3-tlc",
                name="TLC E3 NVMe drives",
                summary="Triple-level-cell flash for the performance-first estate.",
                details=(
                    "TLC (triple-level cell) NAND stores three bits per "
                    "cell — the endurance-and-latency choice. E3 is the "
                    "EDSFF low-profile form factor replacing 2.5″ drives "
                    "industry-wide: more silicon per slot, better airflow, "
                    "and the reason 40 drives fit where 25 used to."
                ),
            ),
            CatalogOption(
                id="e3-qlc",
                name="QLC E3 NVMe drives",
                summary="Quad-level-cell flash for capacity-first economics.",
                details=(
                    "QLC (quad-level cell) NAND stores four bits per cell — "
                    "denser and cheaper per terabyte, at some cost in write "
                    "endurance the array's NVRAM-fronted write path is "
                    "designed to absorb. QLC behind the 6:1 reduction "
                    "guarantee is how the 5.8 PB-effective headline is "
                    "reached."
                ),
            ),
            CatalogOption(
                id="nvme-nvram",
                name="NVMe NVRAM write cache",
                summary="Writes acknowledge from mirrored non-volatile cache.",
                details=(
                    "Dedicated non-volatile NVMe devices take every "
                    "incoming write, mirrored across both nodes, before the "
                    "host is acknowledged — battery-backed vaulting covers "
                    "AC loss. Inherited from the prior generation; it is "
                    "why write latency stays flat while the capacity "
                    "drives are busy destaging."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="reduction",
        name="Data reduction — the 6:1 guarantee",
        blurb=(
            "Always-on inline deduplication and compression, now guaranteed "
            "at 6:1 — raised from the prior generation's 5:1."
        ),
        limits="Always-on · guarantee subject to Dell's program terms",
        region_ids=["elite-cpu-a", "elite-cpu-b", "elite-bay"],
        options=[
            CatalogOption(
                id="drr-guarantee",
                name="6:1 data reduction guarantee",
                summary="Dell contractually guarantees 6 TB stored per TB of flash.",
                details=(
                    "Data reduction ratio (DRR) is how many terabytes of "
                    "host data fit per terabyte of physical flash after "
                    "deduplication and compression. Elite raises Dell's "
                    "guaranteed floor from 5:1 to 6:1 — the vendor's own "
                    "'industry-best' claim — and it is the multiplier that "
                    "turns the 40-slot bay into up to 5.8 PB effective. As "
                    "with every reduction guarantee, real ratios depend on "
                    "the data; pre-compressed or encrypted workloads reduce "
                    "less."
                ),
            ),
            CatalogOption(
                id="inline-services",
                name="Enhanced inline dedupe & compression",
                summary="Reduction runs in the write path, not as an afterthought.",
                details=(
                    "Deduplication and compression happen inline, before "
                    "data lands on flash, on the nodes' extra cores. "
                    "Running reduction inline rather than as a scheduled "
                    "post-process is what lets the guarantee be a floor "
                    "rather than a best case."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="frontend",
        name="Front-end connectivity",
        blurb=(
            "Up to 40 network ports per appliance — twice the prior "
            "generation — fed by PCIe Gen 5."
        ),
        limits="Up to 40 ports per appliance · both nodes must match",
        region_ids=["elite-io-a", "elite-io-b"],
        options=[
            CatalogOption(
                id="fc64",
                name="64 Gb Fibre Channel (128 Gb-ready)",
                summary="The SAN personality, one speed grade ahead of the estate.",
                details=(
                    "Fibre Channel remains the enterprise SAN's transport "
                    "of record; Elite ships 64 Gb ports with the optics "
                    "path ready for 128 Gb. Both nodes carry matching "
                    "modules so either node can serve any host path — the "
                    "multipathing that makes the trace's cutover invisible."
                ),
            ),
            CatalogOption(
                id="eth100",
                name="100 Gb Ethernet (200/400 Gb-ready)",
                summary="iSCSI, NVMe-oF and file traffic at AI-era speeds.",
                details=(
                    "100 GbE ports carry iSCSI, NVMe over TCP, NFS and SMB, "
                    "with the platform ready for 200/400 Gb Ethernet. The "
                    "3x network-throughput claim (Dell's 70/30 read/write, "
                    "1 MB basis) rides on these ports plus the doubled port "
                    "count."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="interconnect",
        name="Cluster interconnect",
        blurb=(
            "A 200 Gb RDMA link between appliances — the wire "
            "mixed-generation clustering, rebalancing and failover run on."
        ),
        limits="Per-appliance-pair links within one cluster",
        region_ids=["cluster-mesh"],
        options=[
            CatalogOption(
                id="rdma-200",
                name="200 Gb RDMA node interconnect",
                summary="Zero-copy transfers between appliances, CPUs left alone.",
                details=(
                    "RDMA (remote direct memory access) lets one appliance "
                    "move data directly to and from another's memory "
                    "without a CPU round trip on either side. At 200 Gb it "
                    "is the freight corridor for live volume rebalancing, "
                    "cross-generation failover and load balancing — fast "
                    "enough that the background move never competes with "
                    "host service for processor time."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="modernization",
        name="Modernization — clustering & in-place upgrades",
        blurb=(
            "The launch's signature: grow, refresh and upgrade the estate "
            "without a migration project. This category is the twin's whole "
            "trace, sold as line items."
        ),
        limits="Mixed generations in one cluster · no forklift required",
        region_ids=["cluster-mesh", "prior-cpu-a", "prior-cpu-b", "elite-mgmt-a", "elite-mgmt-b"],
        options=[
            CatalogOption(
                id="mixed-gen-cluster",
                name="Mixed-generation clustering",
                summary="Existing PowerStore arrays join an Elite cluster live.",
                details=(
                    "A prior-generation PowerStore joins the Elite's "
                    "cluster with no service interruption: one management "
                    "plane, one pool, two hardware generations. Volumes "
                    "then rebalance live over the RDMA interconnect. This "
                    "is the option the twin's whole trace demonstrates — "
                    "the downtime counter pinned at zero is this line "
                    "item working."
                ),
            ),
            CatalogOption(
                id="controller-swap",
                name="In-place controller upgrades",
                summary="Swap the brains, keep the chassis, drives and data.",
                details=(
                    "Within an Elite appliance, future controller "
                    "generations swap into the same chassis without "
                    "replacing the E3 drives or migrating data — the "
                    "modular architecture TechTarget's coverage highlights. "
                    "The refresh cycle shrinks from 'replace the array' to "
                    "'replace the canisters'."
                ),
            ),
            CatalogOption(
                id="repurpose",
                name="Repurpose the prior generation",
                summary="The old array takes a second role instead of a skip.",
                details=(
                    "After cutover, the older appliance stays a cluster "
                    "member and is reassigned — replication target, "
                    "snapshot retention, test estate. Because it never left "
                    "the cluster, the reassignment is a policy change, not "
                    "a project. Refresh stops producing e-waste on a "
                    "schedule."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="autonomous",
        name="Autonomous operations",
        blurb=(
            "Built-in AI that balances, tunes and forecasts continuously — "
            "Dell's claim: up to 95% less manual effort."
        ),
        limits="Cluster-wide · always-on",
        region_ids=["elite-mgmt-a", "elite-mgmt-b"],
        options=[
            CatalogOption(
                id="ai-balancing",
                name="Continuous workload balancing",
                summary="Placement and load decisions made by the array, not a human.",
                details=(
                    "The platform watches every volume's behavior and "
                    "moves work between nodes, appliances and generations "
                    "to keep the cluster balanced — the day-2 form of the "
                    "same machinery the join trace shows once. Dell "
                    "attributes the 'up to 95% less manual effort' figure "
                    "to this automation layer; treat it as the vendor's "
                    "own benchmark of toil removed."
                ),
            ),
            CatalogOption(
                id="aiops",
                name="CloudIQ / APEX AIOps integration",
                summary="Fleet-level health, forecasting and anomaly detection.",
                details=(
                    "Telemetry streams to Dell's AIOps service for "
                    "capacity forecasting, performance anomaly detection "
                    "and fleet health scoring — the pipeline this repo's "
                    "DellCloudIQ twin walks through end to end."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="resilience",
        name="Resilience & cyber recovery",
        blurb=(
            "Replication, snapshots, and byte-level ransomware detection "
            "on the primary array."
        ),
        limits="Cyber Detect from Q3 2026 on PowerStore",
        region_ids=["elite-nvram", "elite-bbu-a", "elite-bbu-b", "prior-bay"],
        options=[
            CatalogOption(
                id="replication",
                name="Native replication & snapshots",
                summary="Async replication and space-efficient snapshots, in the OS.",
                details=(
                    "Volume snapshots and asynchronous replication are "
                    "PowerStoreOS features, not add-ons — and the "
                    "repurposed prior-generation array is their natural "
                    "target, which is exactly the second job the trace "
                    "assigns it."
                ),
            ),
            CatalogOption(
                id="cyber-detect",
                name="Dell Cyber Detect",
                summary="ML ransomware detection against snapshots, at the byte level.",
                details=(
                    "Cyber Detect inspects snapshot content at the byte "
                    "level — entropy, not file names — to name the last "
                    "clean copy after an attack, with Dell citing 99.99% "
                    "accuracy. It reaches PowerStore in Q3 2026; this "
                    "repo's DellCyberDetect twin is that product's own "
                    "story, told in full."
                ),
            ),
            CatalogOption(
                id="vaulting",
                name="BBU-backed cache vaulting",
                summary="No acknowledged write is lost to a power cut.",
                details=(
                    "Battery backup units power each node just long enough "
                    "on AC loss to flush cached writes to non-volatile "
                    "flash. The contract is inherited unchanged from the "
                    "prior generation — availability features carry "
                    "across generations the same way cluster membership "
                    "does."
                ),
            ),
        ],
    ),
]
