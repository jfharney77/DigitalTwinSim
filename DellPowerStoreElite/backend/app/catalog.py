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
            "Three Elite models — Dell names them PowerStore 1500, 5500 and "
            "9500 — share the same 3U chassis and the same software; they "
            "differ in processor cores, memory, and how many bays are open. "
            "Per-model figures below are from StorageReview's hands-on "
            "review."
        ),
        limits="1 model per appliance · up to 4 appliances per cluster",
        region_ids=["elite-cpu-a", "elite-cpu-b", "elite-bay"],
        options=[
            CatalogOption(
                id="elite-1500",
                name="PowerStore 1500 (Elite)",
                summary="The entry point to the Elite platform.",
                details=(
                    "The smallest Elite, and the successor to the 1200T. "
                    "Same 3U chassis, same PowerStoreOS and data services "
                    "as its bigger siblings, with one processor per node "
                    "(48 cores in all), 512 GB of memory, 24 drive bays "
                    "open at launch and a 100 Gb node interconnect; a later "
                    "controller swap is reported to unlock all 40 bays. "
                    "Dell's 3x IOPS claim compares this model with the "
                    "1200T. Because "
                    "clustering is mixed-generation and mixed-model, a 1500 "
                    "bought today can later share a cluster with a larger "
                    "Elite, or with the prior-generation array it arrived to "
                    "relieve."
                ),
            ),
            CatalogOption(
                id="elite-5500",
                name="PowerStore 5500 (Elite)",
                summary="The midrange workhorse of the line.",
                details=(
                    "The volume model: two processors per node (96 cores "
                    "in all), 1 TB of memory, all 40 bays. Dell's 'up to "
                    "50% more cores' figure compares this model with the "
                    "prior generation's 3200T. For most consolidation "
                    "estates — block plus file plus VMs — this is the "
                    "default answer."
                ),
            ),
            CatalogOption(
                id="elite-9500",
                name="PowerStore 9500 (Elite)",
                summary="The top model, for the heaviest consolidation.",
                details=(
                    "Maximum cores (128 in all) and 2 TB of memory. Dell's "
                    "5.8 PB, 3x throughput and 3x density figures are all "
                    "drawn on this model, against the 9200T. "
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
            "Intel Xeon Scalable processors with up to 50% more cores "
            "(Dell's comparison: the new 5500 against the 3200T) — and "
            "software that moves those cores to where the load is."
        ),
        limits="2 nodes per appliance · active/active",
        region_ids=["elite-cpu-a", "elite-cpu-b"],
        options=[
            CatalogOption(
                id="xeon-scalable",
                name="Intel Xeon Scalable (per node)",
                summary="Up to 50% more cores than the prior generation, by Dell's count.",
                details=(
                    "Each of the two controller nodes carries one Intel "
                    "Xeon Scalable processor on the 1500 and two on the "
                    "5500 and 9500. Every data service — deduplication, "
                    "compression, RAID math, replication — runs on these "
                    "cores, so the +50% core count is a direct input to the "
                    "3x performance claim."
                ),
            ),
            CatalogOption(
                id="dynamic-cores",
                name="Dynamic core allocation",
                summary="CPU resources follow the workload as it shifts.",
                details=(
                    "Dell's launch material says dynamic core allocation "
                    "adjusts CPU resources as workloads fluctuate, and "
                    "StorageReview describes resources shared dynamically "
                    "between block and file services. Dell has not "
                    "published the mechanism in more detail than that. "
                    "Dell's claim for the automation layer as "
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
            "DDR5 DIMM banks per node, and a software change to the "
            "metadata layer that Dell credits with faster reads."
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
                    "generation's memory — necessary headroom once the "
                    "fabric moves from PCIe Gen 3 to Gen 5. Part of it "
                    "also serves as the battery-backed write cache."
                ),
            ),
            CatalogOption(
                id="metadata-acceleration",
                name="Metadata Acceleration",
                summary="Reads up to 70% faster, by Dell's own test.",
                details=(
                    "Every read consults metadata — where a block lives, "
                    "whether it is deduplicated, which snapshot chain owns "
                    "it — so a faster metadata path is a faster read. "
                    "Metadata Acceleration is a PowerStoreOS 5.0 feature "
                    "that Dell says serves all PowerStore customers, not "
                    "only Elite. The 'up to 70% faster' figure is Dell's "
                    "internal test of a PowerStore 500T on OS 4.3 against "
                    "OS 5.0, with a read-only 8 KB workload. Dell has not "
                    "published how it works."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="drives",
        name="Drives — the E3 NVMe bay",
        blurb=(
            "40 low-profile E3 NVMe slots per 3U appliance, taking QLC or "
            "TLC flash — up to 3x the density of the prior generation, by "
            "Dell's comparison of a 9500 at 6:1 with a 9200T at 5:1."
        ),
        limits="Up to 40 slots per appliance (24 on the 1500 at launch) · dual-ported · QLC or TLC",
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
                    "and part of how 40 drives fit in 3U where 25 fit in "
                    "2U. StorageReview lists TLC drives at 3.84, 7.68 and "
                    "15.36 TB."
                ),
            ),
            CatalogOption(
                id="e3-qlc",
                name="QLC E3 NVMe drives",
                summary="Quad-level-cell flash for capacity-first economics.",
                details=(
                    "QLC (quad-level cell) NAND stores four bits per cell — "
                    "denser and cheaper per terabyte, at some cost in write "
                    "endurance the array's cache-fronted write path is "
                    "designed to absorb. StorageReview lists the QLC drive "
                    "at 30.72 TB. QLC behind the 6:1 reduction "
                    "guarantee is how the 5.8 PB-effective headline is "
                    "reached."
                ),
            ),
            CatalogOption(
                id="nvme-nvram",
                name="Persistent write cache (SDPM)",
                summary="Writes acknowledge from mirrored, battery-backed memory.",
                details=(
                    "Every incoming write lands in a persistent cache, "
                    "mirrored across both nodes, before the host is "
                    "acknowledged — it is why write latency stays flat "
                    "while the capacity drives are busy destaging. The "
                    "prior generation used NVRAM drives in the front bay "
                    "for this. By StorageReview's account Elite uses "
                    "software-defined persistent memory instead: "
                    "battery-backed DDR5 that the firmware copies to an "
                    "M.2 flash device on power loss, which hands the drive "
                    "slots back to capacity."
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
                summary="Dell guarantees 6 TB stored per TB of flash, under its program terms.",
                details=(
                    "Data reduction ratio (DRR) is how many terabytes of "
                    "host data fit per terabyte of physical flash after "
                    "deduplication and compression. Elite raises Dell's "
                    "guaranteed floor from 5:1 to 6:1 — the vendor's own "
                    "'industry-best' claim — and it is the multiplier that "
                    "turns the 40-slot bay into up to 5.8 PB effective. "
                    "Dell's footnote limits it to new arrays first "
                    "installed with PowerStoreOS 5.0. As "
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
            "Up to 40 network ports per appliance — twice the current "
            "generation, in Dell's words — fed by PCIe Gen 5."
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
                    "with the platform ready for 200/400 Gb Ethernet. "
                    "Dell's 3x throughput claim (a 9500 against a 9200T, "
                    "70/30 read/write, 1 MB blocks) rides on these ports "
                    "plus the larger port count."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="interconnect",
        name="Node interconnect & cluster network",
        blurb=(
            "Two different wires. A 200 Gb RDMA link joins the two "
            "controller nodes inside the Elite; an Ethernet cluster network "
            "joins the appliances, and mixed-generation rebalancing runs "
            "on that one."
        ),
        limits="Node link inside each appliance · cluster network via top-of-rack switches",
        region_ids=["cluster-mesh", "elite-board-a", "elite-board-b"],
        options=[
            CatalogOption(
                id="rdma-200",
                name="200 Gb RDMA node interconnect",
                summary="The in-chassis link that mirrors writes between the two nodes.",
                details=(
                    "RDMA (remote direct memory access) lets one node "
                    "place data directly in its partner's memory without "
                    "a CPU round trip on either side. On Elite the link "
                    "is cable-free, routed across the midplane, and "
                    "dedicated to write ingest — the mirroring every "
                    "acknowledged write needs. StorageReview puts it at "
                    "200 GbE on the 5500 and 9500 and 100 GbE on the "
                    "1500, against 2× 10 GbE in the prior generation. It "
                    "does not leave the chassis."
                ),
            ),
            CatalogOption(
                id="cluster-network",
                name="Intra-cluster Ethernet network",
                summary="The path between appliances, and the one migrations take.",
                details=(
                    "Appliances in one PowerStore cluster reach each other "
                    "over internal management and data networks that run "
                    "through the top-of-rack Ethernet switches; Dell's "
                    "clustering white paper says volume migration between "
                    "appliances uses the data network. This is the strip "
                    "drawn between the two generations, and the wire the "
                    "twin's rebalance runs on. Its speed in the trace is "
                    "illustrative."
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
        limits="Mixed generations in one cluster · up to 4 appliances · no forklift required",
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
                    "then rebalance live over the cluster network. This "
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
                    "generations are meant to swap into the same chassis "
                    "without replacing the E3 drives or migrating data — "
                    "the modular architecture TechTarget's coverage "
                    "highlights, and what Dell's Lifecycle Extension "
                    "program calls data-in-place upgrades. "
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
                    "member and is reassigned — snapshot retention, test "
                    "and development estate. Because it never left "
                    "the cluster, the reassignment is a policy change, not "
                    "a project. Making it a replication target is a different "
                    "move: PowerStore replicates between clusters, so the "
                    "appliance is removed and redeployed as a remote system. "
                    "Either way, refresh stops producing e-waste on a "
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
                    "clean copy after an attack. Dell cites 99.99% "
                    "effectiveness from an Omdia/ESG report commissioned "
                    "by Index Engines, whose analysis engine it uses. It "
                    "reaches PowerStore in Q3 2026; this "
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
                    "on AC loss to copy cached writes from memory to "
                    "non-volatile flash. The contract is inherited unchanged from the "
                    "prior generation — availability features carry "
                    "across generations the same way cluster membership "
                    "does."
                ),
            ),
        ],
    ),
]
