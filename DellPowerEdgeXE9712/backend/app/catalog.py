"""Component catalog: what an XE9712 rack is built from, as data.

Same pattern as the other twins: categories map onto rack regions via
``region_ids`` (ids from anatomy.py; an empty list means the item is not a
physical part of this rack — software, external storage, services). Written
for a technically skilled reader new to rack-scale AI; Dell and NVIDIA
jargon (superchip, NVLink, CDU, DPU, IRSS, ...) is spelled out on first use.
Counts and speeds are illustrative, anchored to Dell's and NVIDIA's public
product pages.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

_TRAY_REGIONS = [f"{p}-t{i}" for i in (1, 2, 3, 4) for p in ("gpu", "cpu", "nic")]
_GPU_REGIONS = [f"gpu-t{i}" for i in (1, 2, 3, 4)]
_CPU_REGIONS = [f"cpu-t{i}" for i in (1, 2, 3, 4)]
_NIC_REGIONS = [f"nic-t{i}" for i in (1, 2, 3, 4)]

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="platform",
        name="Rack platform",
        blurb=(
            "The XE9712 is bought as a whole rack, not tray by tray. You "
            "choose which NVIDIA rack-scale generation the rack is built "
            "around; everything else — tray count, switch trays, power "
            "shelves, cabling — follows from that choice."
        ),
        limits="One integrated rack; an AI factory is many racks side by side",
        region_ids=[],
        options=[
            CatalogOption(
                id="plat-gb200",
                name="XE9712 · NVIDIA GB200 NVL72",
                summary="72 Blackwell GPUs + 36 Grace CPUs fused into one NVLink domain.",
                details=(
                    "The launch configuration. 18 compute trays each carry "
                    "two GB200 superchips (a superchip is one Grace CPU "
                    "joined to two Blackwell GPUs on a single board), and 9 "
                    "NVLink switch trays fuse all 72 GPUs into one domain "
                    "with 13.5 TB of pooled HBM3e memory. NVIDIA's headline "
                    "claim: up to 30× faster real-time inference on "
                    "trillion-parameter models than the prior generation, "
                    "because the model lives inside one rack-wide NVLink "
                    "domain instead of hopping between servers."
                ),
            ),
            CatalogOption(
                id="plat-gb300",
                name="XE9712 · NVIDIA GB300 NVL72",
                summary="The Blackwell Ultra refresh — more HBM, more inference throughput.",
                details=(
                    "The same rack architecture rebuilt around GB300 "
                    "(Blackwell Ultra) superchips: more HBM3e per GPU and "
                    "roughly 1.5× the AI inference throughput of GB200 "
                    "NVL72, aimed at reasoning models that spend far more "
                    "compute per query at inference time. Because the rack, "
                    "busbar, liquid loop, and NVLink cartridge are the "
                    "platform, the generation is a tray-and-switch change, "
                    "not a new data-center design."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="tray",
        name="Compute trays",
        blurb=(
            "The repeating building block: a slim liquid-cooled tray holding "
            "two superchips. Eighteen of them fill the rack, and they are "
            "deliberately identical — the fabric, not the tray, is what "
            "makes the rack more than 18 servers."
        ),
        limits="18 trays per rack · 2 superchips (2 CPUs + 4 GPUs) per tray",
        region_ids=_TRAY_REGIONS,
        options=[
            CatalogOption(
                id="tray-gb200",
                name="GB200 compute tray",
                summary="Two Grace-Blackwell superchips on cold plates, fed from the busbar.",
                details=(
                    "Each tray is a complete liquid-cooled computer: two "
                    "Grace CPUs, four Blackwell GPUs, LPDDR5X and HBM3e "
                    "memory, NVLink-C2C links between CPU and GPU, and "
                    "front-facing ConnectX/BlueField ports for the "
                    "scale-out network. No fans, no power supplies — "
                    "coolant and DC power arrive from the rack. A tray "
                    "pulls out for service on blind-mate liquid "
                    "quick-disconnects without draining the loop."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="gpu",
        name="GPUs",
        blurb=(
            "The reason the rack exists. All 72 GPUs are the same part, and "
            "after the NVLink fabric fuses they behave less like 72 cards "
            "than like one enormous accelerator."
        ),
        limits="72 GPUs per rack · ~1 kW each · liquid-cooled only",
        region_ids=_GPU_REGIONS,
        options=[
            CatalogOption(
                id="gpu-b200",
                name="NVIDIA Blackwell (GB200)",
                summary="The workhorse Blackwell GPU with HBM3e, two per superchip.",
                details=(
                    "Blackwell is NVIDIA's 2024-generation data-center GPU: "
                    "two reticle-limited dies joined into one chip, HBM3e "
                    "stacked memory, and a transformer engine that trains "
                    "and serves models in low-precision formats (FP8/FP4) "
                    "for speed. In this rack it never appears as a PCIe "
                    "card — it exists only soldered to a superchip under a "
                    "cold plate, drawing about a kilowatt."
                ),
            ),
            CatalogOption(
                id="gpu-b300",
                name="NVIDIA Blackwell Ultra (GB300)",
                summary="The refresh: ~50% more HBM and more low-precision throughput.",
                details=(
                    "Blackwell Ultra raises HBM3e capacity per GPU (288 GB "
                    "class) and low-precision compute, targeted at "
                    "inference-heavy 'reasoning' workloads where a model "
                    "generates long chains of tokens per request. Choosing "
                    "it means choosing the GB300 NVL72 platform — GPU "
                    "generation and rack generation move together."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="cpu",
        name="CPUs",
        blurb=(
            "There is no Xeon or EPYC option here — the host processor is "
            "NVIDIA Grace, chosen because it couples to the GPUs over "
            "NVLink-C2C instead of PCIe."
        ),
        limits="36 Grace CPUs per rack · 72 Arm cores each",
        region_ids=_CPU_REGIONS,
        options=[
            CatalogOption(
                id="cpu-grace",
                name="NVIDIA Grace (72-core Arm)",
                summary="The feeder CPU: Arm cores + LPDDR5X the GPUs address directly.",
                details=(
                    "Grace is a 72-core Arm server CPU whose defining "
                    "feature is NVLink-C2C: a 900 GB/s chip-to-chip link to "
                    "its two Blackwell GPUs, several times faster than "
                    "PCIe. Its LPDDR5X memory extends the GPUs' reach — a "
                    "model or KV-cache can spill from HBM into CPU memory "
                    "without crossing a slow bus. The trays boot standard "
                    "Arm Linux, so the software stack is ordinary NVIDIA "
                    "CUDA on an unusual amount of hardware."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="nvlink",
        name="NVLink scale-up fabric",
        blurb=(
            "The fabric inside the rack — what fuses 72 GPUs into one "
            "domain. This is the component that separates rack-scale "
            "systems from a rack full of servers."
        ),
        limits="9 switch trays per rack · 1.8 TB/s per GPU · ~130 TB/s total",
        region_ids=["nvswitch-a", "nvswitch-b"],
        options=[
            CatalogOption(
                id="nvl-switchtray",
                name="NVLink switch tray (NVSwitch, gen 5)",
                summary="NVSwitch ASICs cross-connecting every GPU to every other GPU.",
                details=(
                    "Each of the nine trays carries NVSwitch ASICs that "
                    "form an all-to-all crossbar: any GPU reaches any other "
                    "GPU's memory in one hop at NVLink generation-5 speed "
                    "(1.8 TB/s per GPU, both directions combined). The "
                    "trays sit at mid-rack so every copper run fits within "
                    "electrical reach — the fabric uses no optics at all "
                    "inside the rack."
                ),
            ),
            CatalogOption(
                id="nvl-cartridge",
                name="NVLink cable cartridge",
                summary="The pre-built copper spine: 5,000+ cables, ~2 miles of wire.",
                details=(
                    "At the back of the rack, a factory-built cartridge of "
                    "more than five thousand copper cables — on the order "
                    "of two miles of conductor — connects every compute "
                    "tray to every switch tray. Copper instead of optics "
                    "saves roughly 20 kW per rack in transceiver power and "
                    "removes thousands of failure-prone lasers; it is "
                    "possible only because the NVLink domain is kept inside "
                    "one physical rack. This cartridge is why the XE9712 "
                    "ships as an integrated rack rather than parts."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="scaleout",
        name="Scale-out networking",
        blurb=(
            "NVLink stops at the rack wall. These ports join racks into an "
            "AI factory — and carry every byte of training data and "
            "checkpoints in and out."
        ),
        limits="Per tray: 400–800 Gb/s class NICs/DPUs; fabric chosen per site",
        region_ids=_NIC_REGIONS,
        options=[
            CatalogOption(
                id="net-quantum",
                name="NVIDIA Quantum InfiniBand",
                summary="The classic HPC choice: lossless, in-network compute, lowest jitter.",
                details=(
                    "InfiniBand (Quantum-X switches with ConnectX adapters) "
                    "is the traditional fabric for large training clusters: "
                    "lossless delivery, remote direct memory access (RDMA), "
                    "and in-network reduction (SHARP) that sums gradients "
                    "inside the switches. Multi-rack training jobs "
                    "synchronize every step, so the slowest packet sets the "
                    "pace — which is why the scale-out fabric gets this "
                    "much engineering attention."
                ),
            ),
            CatalogOption(
                id="net-spectrumx",
                name="NVIDIA Spectrum-X Ethernet",
                summary="AI-tuned Ethernet: RoCE with congestion control built for training.",
                details=(
                    "Spectrum-X pairs Spectrum switches with BlueField "
                    "DPUs to make Ethernet behave for AI: RDMA over "
                    "Converged Ethernet (RoCE) with adaptive routing and "
                    "telemetry-driven congestion control. Sites choose it "
                    "to keep one network technology across the data center; "
                    "Dell pairs it with PowerSwitch SN-series hardware in "
                    "AI Factory designs."
                ),
            ),
            CatalogOption(
                id="net-bluefield",
                name="NVIDIA BlueField-3 DPU",
                summary="A NIC with its own Arm cores: offloads storage, security, telemetry.",
                details=(
                    "The DPU (data processing unit) is a network adapter "
                    "with its own Arm processors and accelerators. It "
                    "terminates storage protocols (so GPUs stream training "
                    "data from PowerScale without host CPU work), enforces "
                    "isolation between tenants, and feeds telemetry to the "
                    "management plane. In multi-tenant AI clouds it is the "
                    "trust boundary."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="cooling",
        name="Liquid cooling",
        blurb=(
            "About ninety percent of ~120 kW leaves through water. The "
            "cooling loop is a first-class subsystem with its own power-on "
            "phase — liquid before silicon."
        ),
        limits="Sized for ~120 kW per rack; facility water required",
        region_ids=["cdu", "manifold"],
        options=[
            CatalogOption(
                id="cool-rcdu",
                name="Dell PowerCool in-rack CDU (RCDU)",
                summary="Rack-mounted pumps + heat exchanger; isolates rack loop from facility water.",
                details=(
                    "The coolant distribution unit circulates treated "
                    "coolant through the rack's manifolds and cold plates, "
                    "exchanging heat with the facility water loop through a "
                    "plate heat exchanger so the two liquids never mix. "
                    "Dell's rack-mounted RCDU line delivers on the order of "
                    "160 kW of cooling per rack. It leak-checks and primes "
                    "the loop before the management plane allows GPU "
                    "power-on, and modulates pump speed against cold-plate "
                    "temperatures at steady state."
                ),
            ),
            CatalogOption(
                id="cool-erdhx",
                name="PowerCool enclosed rear-door heat exchanger (eRDHx)",
                summary="Catches the air-cooled remainder so the row needs no extra room cooling.",
                details=(
                    "Not everything has a cold plate — DIMM-class parts, "
                    "NICs, and power shelves still shed some heat to air. "
                    "The enclosed rear-door heat exchanger captures that "
                    "remainder at the back of the rack and returns it to "
                    "the water loop, letting a dense AI row run in a room "
                    "with ordinary air handling. Dell quotes up to 60% "
                    "cooling-energy savings versus conventional room "
                    "cooling."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="power",
        name="Power",
        blurb=(
            "Rack power is centralized: shelves rectify facility AC to DC "
            "once, and a busbar distributes it to every tray. At 120 kW, "
            "power engineering is product engineering."
        ),
        limits="~120 kW per rack; redundant facility feeds recommended",
        region_ids=["power-shelf-a", "power-shelf-b"],
        options=[
            CatalogOption(
                id="pow-shelf",
                name="Power shelves + DC busbar",
                summary="Hot-swap rectifier banks feeding a copper spine every tray clips onto.",
                details=(
                    "Power shelves hold banks of hot-swappable rectifiers "
                    "(redundant across separate facility feeds) that "
                    "convert AC to direct current and energize the busbar "
                    "running the height of the rack. Trays have no power "
                    "supplies of their own — they blind-mate onto the "
                    "busbar. Centralizing conversion cuts losses, and a "
                    "failed rectifier or even a lost feed derates the rack "
                    "instead of dropping it. The same Open Compute-inspired "
                    "design appears in Dell's IR7000 rack family."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="management",
        name="Management",
        blurb=(
            "One rack behaves like one system, so management spans levels: "
            "per-tray BMCs, whole-rack sequencing and interlocks, and "
            "cluster-level job health."
        ),
        limits="Rack management switch standard; cluster tools per site",
        region_ids=["mgmt"],
        options=[
            CatalogOption(
                id="mgmt-idrac",
                name="BMC path + Dell OpenManage",
                summary="Every tray's BMC reports to the rack switch; OME sees the fleet.",
                details=(
                    "Each tray carries a baseboard management controller — "
                    "the same always-on service-processor role the iDRAC "
                    "twin explores — reachable through the rack management "
                    "switch even when trays are off. Dell OpenManage "
                    "Enterprise (OME) aggregates inventory, firmware, "
                    "telemetry, and the power/coolant interlocks across "
                    "racks, the way it does for ordinary PowerEdge fleets."
                ),
            ),
            CatalogOption(
                id="mgmt-mission",
                name="NVIDIA Mission Control",
                summary="Cluster-level brain: job orchestration, fabric health, power steering.",
                details=(
                    "Mission Control operates the NVL72 fleet as an AI "
                    "factory: it validates the NVLink fabric, watches "
                    "per-GPU health, reroutes around failures, coordinates "
                    "checkpoint/restart for long training runs, and steers "
                    "power and cooling against the schedule. It is the "
                    "layer at which 'eight racks' starts to behave like "
                    "'one training computer'."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="storage",
        name="External storage",
        blurb=(
            "There are no data drives in the rack — training data, "
            "checkpoints, and models live on external storage reached over "
            "the scale-out fabric."
        ),
        limits="Not in this rack — attaches over InfiniBand/Ethernet",
        region_ids=[],
        options=[
            CatalogOption(
                id="stor-powerscale",
                name="Dell PowerScale (F710/F910)",
                summary="Scale-out all-flash NAS feeding GPUs over RDMA.",
                details=(
                    "PowerScale is Dell's scale-out file system: all-flash "
                    "nodes that pool into one namespace and stream training "
                    "data to thousands of GPUs, with GPUDirect and "
                    "S3-over-RDMA paths that bypass host CPUs. "
                    "Checkpointing a trillion-parameter model writes "
                    "terabytes at once, so storage bandwidth directly sets "
                    "how often you can afford to checkpoint."
                ),
            ),
            CatalogOption(
                id="stor-objectscale",
                name="Dell ObjectScale",
                summary="Software-defined S3 object storage for multi-petabyte data lakes.",
                details=(
                    "ObjectScale serves the S3 object protocol on dense "
                    "PowerEdge nodes, scaling to multi-petabyte data lakes "
                    "— the raw-corpus tier behind the hot PowerScale tier. "
                    "With S3 over RDMA it feeds preprocessing and training "
                    "jobs directly, so the same lake that archives the "
                    "corpus can serve it."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="software",
        name="AI software stack",
        blurb=(
            "The rack ships into a validated stack: NVIDIA's AI platform on "
            "top, Dell's AI Factory designs around it, so the first "
            "training job is a configuration exercise, not an integration "
            "project."
        ),
        limits="Licensed per GPU or per node; versions move with the platform",
        region_ids=[],
        options=[
            CatalogOption(
                id="sw-nvai",
                name="NVIDIA AI Enterprise + NIM",
                summary="The supported CUDA platform plus packaged inference microservices.",
                details=(
                    "NVIDIA AI Enterprise is the supported distribution of "
                    "the CUDA stack — frameworks, drivers, and NIM (NVIDIA "
                    "Inference Microservices): pre-optimized, containerized "
                    "model servers that make a fused NVL72 domain "
                    "consumable by an application team as an API endpoint "
                    "rather than 72 GPUs to program."
                ),
            ),
            CatalogOption(
                id="sw-aifactory",
                name="Dell AI Factory validated designs",
                summary="Dell's tested blueprints joining racks, network, storage, and software.",
                details=(
                    "The Dell AI Factory with NVIDIA is a set of validated, "
                    "sized designs — compute racks, Spectrum-X or "
                    "InfiniBand fabric, PowerScale storage, and the "
                    "software stack — with the integration tested before "
                    "anything ships. Dell counts hundreds of updates to the "
                    "program since 2024; the point is that an enterprise "
                    "buys an outcome (tokens per second, time to train) "
                    "rather than a parts list."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="deployment",
        name="Delivery & integration",
        blurb=(
            "A 120 kW liquid-cooled rack is not slid into place by the IT "
            "team. Dell builds and tests the rack in the factory and lands "
            "it as a unit."
        ),
        limits="Ships as an integrated rack; site needs power + water ready",
        region_ids=[],
        options=[
            CatalogOption(
                id="dep-irss",
                name="Integrated Rack Scalable Systems (IRSS)",
                summary="Factory-integrated, cabled, burn-tested racks delivered plug-in ready.",
                details=(
                    "Under IRSS, Dell assembles the full rack — trays, "
                    "switch trays, cable cartridge, shelves, CDU — then "
                    "burn-tests it as a system before shipping, with "
                    "one-call support for everything inside the rack "
                    "afterward. On site it rolls into position and connects "
                    "to power, water, and network; the days of on-site "
                    "cabling that a 5,000-cable fabric would otherwise "
                    "demand simply never happen."
                ),
            ),
            CatalogOption(
                id="dep-services",
                name="Dell AI Factory services",
                summary="Sizing, data-center readiness, and residency services around the rack.",
                details=(
                    "Services cover what surrounds the rack: facility "
                    "assessments for power and liquid readiness, cluster "
                    "design and bring-up, model-platform residencies. For "
                    "most enterprises the scarce resource is not budget but "
                    "people who have stood up an AI factory before — this "
                    "is how that experience is rented."
                ),
            ),
        ],
    ),
]
