"""Component catalog for the PowerEdge XE9680 twin — backend data, not
frontend code, exactly like the chassis twins. Categories map onto the
anatomy's regions via ``region_ids`` so the UI can light up where an option
physically lives. Copy is written for a technically skilled reader new to
GPU servers: Dell and NVIDIA vocabulary (HGX, SXM, NVSwitch, DPU, RDMA,
BOSS-N1, DLC) is spelled out on first use. Counts and wattages are
illustrative, anchored to the Dell spec sources carried in anatomy.py."""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

_GPU_REGIONS = [f"gpu-g{i}" for i in range(1, 9)]
_NIC_REGIONS = [f"nic-g{i}" for i in range(1, 9)]

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="platform",
        name="Chassis platform",
        blurb=(
            "The same 8-GPU machine at two densities: air-cooled in 6U, or "
            "direct liquid-cooled in 4U for denser racks, the shape "
            "reported at Colossus."
        ),
        limits="One 8-way accelerator baseboard per chassis, either way (Dell also lists AMD and Intel OAM boards for the 6U)",
        region_ids=["fan-bank-a", "fan-bank-b"],
        options=[
            CatalogOption(
                id="xe9680-air",
                name="XE9680 — 6U air-cooled",
                summary=(
                    "The standard configuration: eight SXM GPUs held at "
                    "temperature by a fan wall, in any rack with power and a "
                    "hot aisle."
                ),
                details=(
                    "Six rack units of chassis, most of it airflow path: a "
                    "front-to-back tunnel of high-static-pressure fans and "
                    "heatsinks that keeps eight ~700 W GPUs inside their "
                    "thermal envelope with no liquid anywhere. The price is "
                    "volume (6U per 8 GPUs), acoustics, and a facility that "
                    "can absorb ~11 kW of hot air per box — but the prize is "
                    "that nothing about the building has to change. Any data "
                    "center that can rack a server can rack this one, which "
                    "is precisely why the first wave of large AI clusters "
                    "was built from boxes like it."
                ),
            ),
            CatalogOption(
                id="xe9680l-dlc",
                name="XE9680L — 4U direct liquid-cooled",
                summary=(
                    "The dense variant: cold plates on GPUs and CPUs shrink "
                    "the box to 4U, so eight or more servers share a rack — "
                    "the geometry reported at Colossus."
                ),
                details=(
                    "DLC (direct liquid cooling) puts cold plates on the "
                    "eight SXM modules and both Xeons, moving most of the "
                    "heat into a coolant loop instead of the room's air. "
                    "Dropping the giant heatsinks and half the airflow path "
                    "shrinks the chassis to 4U, with the loop plumbed to a CDU "
                    "(coolant distribution unit; the IR7000 twin is that "
                    "machine's story). Dell announced the XE9680L in May "
                    "2024 for HGX B200 and H200 boards, in its IR5000 rack, "
                    "and quotes 72 to 96 GPUs per rack depending on the "
                    "cooling design (Dell's figures). The reported shape "
                    "of xAI's Colossus racks is the same idea: 4U "
                    "liquid-cooled 8-GPU HGX servers, 64 GPUs per rack, "
                    "roughly 1,500 racks in the first build. The racks "
                    "toured publicly were Supermicro's; Dell built about "
                    "half, and the Dell server model was not published."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="gpu-baseboard",
        name="GPU baseboard",
        blurb=(
            "The reason the server exists: one HGX baseboard carrying eight "
            "SXM accelerators and the NVSwitch complex that fuses them."
        ),
        limits="Eight SXM modules per baseboard; all eight identical",
        region_ids=_GPU_REGIONS,
        options=[
            CatalogOption(
                id="hgx-h100",
                name="NVIDIA HGX H100 (8× H100 SXM)",
                summary=(
                    "The Hopper-generation baseboard the XE9680 launched "
                    "with, and the GPU generation the first build of "
                    "Colossus was reported to run."
                ),
                details=(
                    "Eight H100 SXM modules, each with 80 GB of HBM3 "
                    "(high-bandwidth memory — DRAM stacked directly beside "
                    "the GPU die) and 900 GB/s of NVLink into the NVSwitch "
                    "complex, pooling to 640 GB across the domain. SXM is "
                    "the socketed form factor: no card edge, no power "
                    "cables, just a module bolted to the baseboard, which "
                    "is what lets each GPU draw up to 700 W — double "
                    "the 350 to 400 W of the H100's PCIe-card versions."
                ),
            ),
            CatalogOption(
                id="hgx-h200",
                name="NVIDIA HGX H200 (8× H200 SXM)",
                summary=(
                    "Same Hopper compute, nearly double the memory — the "
                    "mid-life upgrade that made bigger models fit."
                ),
                details=(
                    "The H200 keeps Hopper's arithmetic and raises each "
                    "module to 141 GB of faster HBM3e, pooling 1.1 TB "
                    "across the eight-GPU domain. Memory capacity, not "
                    "compute, decides which models fit in the box — the "
                    "same lesson the Pro Max Plus twin teaches at laptop "
                    "scale — so a drop-in baseboard swap that nearly "
                    "doubles pooled HBM extends the platform's life "
                    "without touching the host, NICs, or cooling design."
                ),
            ),
            CatalogOption(
                id="hgx-b200",
                name="NVIDIA HGX B200 (8× Blackwell SXM)",
                summary=(
                    "The Blackwell-generation baseboard, which Dell lists "
                    "for the liquid-cooled XE9680L."
                ),
                details=(
                    "Eight Blackwell B200 modules with 180 GB of HBM3e "
                    "each — 1.4 TB pooled, 1.8 TB/s of NVLink per GPU — "
                    "at 1,000 W per module, which is why Dell's spec "
                    "sheets pair this board with the liquid-cooled "
                    "XE9680L and 3,000 W supplies. "
                    "The three baseboards tell one story: the chassis, "
                    "host, and one-NIC-per-GPU design carry across GPU "
                    "generations, and the accelerator inside is the part "
                    "that turns over fastest."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="nvlink",
        name="In-box scale-up (NVLink)",
        blurb=(
            "What fuses eight GPUs into one domain — and why the domain "
            "ends at the sheet metal."
        ),
        limits="One NVSwitch complex per baseboard; the domain is 8, always",
        region_ids=["nvswitch"],
        options=[
            CatalogOption(
                id="nvswitch-complex",
                name="NVSwitch complex (on-baseboard)",
                summary=(
                    "Switch silicon soldered to the HGX board: every GPU "
                    "reads every other's memory at 900 GB/s (H100/H200)."
                ),
                details=(
                    "The NVSwitch chips cross-connect all eight SXM "
                    "modules so any GPU can load or store directly against "
                    "any other's HBM — no host involvement, no copies. It "
                    "is the same kind of switch silicon the XE9712 rack fills "
                    "nine trays with, here as a strip of board: the fuse "
                    "takes seconds instead of minutes of cable training, "
                    "and the domain it makes is exactly eight, forever. "
                    "Everything larger is the fabric's job."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="scale-out",
        name="Scale-out networking",
        blurb=(
            "One NIC per GPU: eight private on-ramps to the fabric that "
            "continues where NVLink stops."
        ),
        limits="Eight GPU-paired adapters + host/management ports",
        region_ids=_NIC_REGIONS,
        options=[
            CatalogOption(
                id="connectx-400",
                name="8× 400 GbE, one per GPU (ConnectX-7 or BlueField-3 SuperNIC)",
                summary=(
                    "The Colossus pattern: every GPU gets its own "
                    "400 GbE port onto a Spectrum-X Ethernet fabric."
                ),
                details=(
                    "Each adapter is dedicated to one GPU and "
                    "carries its RDMA traffic (remote direct memory "
                    "access — the NIC moves data between GPU memories "
                    "without the host CPU touching it) straight onto the "
                    "data-center fabric. One NIC per GPU means all-to-all "
                    "training traffic never queues behind a shared port: "
                    "8 × 400 GbE is 3.2 Tb/s of GPU networking per "
                    "server. At Colossus the per-GPU adapters were "
                    "reported as BlueField-3 SuperNICs, with a ninth "
                    "400 GbE ConnectX-7 for the host — the roughly "
                    "3.6 Tb/s per server in the published tour. The "
                    "SN6000 twin is the other end of these cables."
                ),
            ),
            CatalogOption(
                id="bluefield-dpu",
                name="BlueField-3 DPUs (host + services)",
                summary=(
                    "NICs with their own Arm cores that offload storage, "
                    "security, and tenancy from the host."
                ),
                details=(
                    "A DPU (data processing unit) is a NIC that runs its "
                    "own software: storage access, encryption, and network "
                    "isolation execute on the adapter's Arm cores instead "
                    "of the Xeons. In multi-tenant clusters the DPU is "
                    "what keeps one customer's training job invisible to "
                    "another's while both share the same fabric. In this "
                    "option the per-GPU ports move tensors and a "
                    "host-side BlueField moves everything else."
                ),
            ),
            CatalogOption(
                id="infiniband-ndr",
                name="8× ConnectX-7 NDR InfiniBand option",
                summary=(
                    "The same one-per-GPU pairing on 400 Gb/s InfiniBand "
                    "for clusters standardized on IB."
                ),
                details=(
                    "The adapters speak InfiniBand as readily as Ethernet, "
                    "so sites standardized on InfiniBand — much of "
                    "academic HPC — run the "
                    "identical one-NIC-per-GPU design on IB instead of "
                    "Spectrum-X. The architectural point survives the "
                    "protocol choice: the domain is the box, and every "
                    "GPU keeps a private path past it."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="host",
        name="Host processors & memory",
        blurb=(
            "Two Xeons and 32 DIMMs whose job is keeping eight "
            "accelerators fed."
        ),
        limits="2 sockets, 32× DDR5 DIMM",
        region_ids=["host-cpus"],
        options=[
            CatalogOption(
                id="xeon-4th",
                name="2× Intel Xeon (4th Gen, Sapphire Rapids)",
                summary="The launch host: PCIe Gen5 lanes to every GPU, NIC, and drive.",
                details=(
                    "The XE9680 launched with dual 4th-Gen Xeon Scalable "
                    "processors. What matters here is less core count than "
                    "lanes and memory: PCIe Gen5 fans out to eight GPUs, "
                    "eight-plus NICs, and the NVMe bay, while 32 DIMM slots "
                    "of DDR5 (eight memory channels per socket, up to "
                    "4 TB) stage training batches on their way into HBM. "
                    "In an accelerator server the host spec follows the "
                    "GPU spec — it is sized to never be the bottleneck."
                ),
            ),
            CatalogOption(
                id="xeon-5th",
                name="2× Intel Xeon (5th Gen, Emerald Rapids)",
                summary="The refresh host: faster DDR5 and more cache, same feeder role.",
                details=(
                    "The mid-life refresh moves to 5th-Gen Xeons with "
                    "faster DDR5 and larger caches — worth real minutes on "
                    "data-loading-bound epochs and nothing at all when the "
                    "job is HBM-bound, which is an honest summary of host "
                    "upgrades in GPU servers generally. The GPU twin's "
                    "roofline page is the same lesson drawn as a chart."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="storage",
        name="Local storage",
        blurb="NVMe cache for data on its way to HBM; boot kept off the data slots.",
        limits="Up to 8× 2.5-inch NVMe (or 16× E3.S) front bays + BOSS-N1 boot module",
        region_ids=["nvme-bay"],
        options=[
            CatalogOption(
                id="nvme-front",
                name="Front NVMe bay (up to 8× 2.5-inch U.2)",
                summary="Hot-swap NVMe for staging batches and landing checkpoints.",
                details=(
                    "Training data stages here on its way to the GPUs, and "
                    "checkpoints land here on their way out — and at these "
                    "GPU speeds a slow checkpoint is idle silicon, so the "
                    "bay is all NVMe. In cluster deployments the corpus "
                    "itself lives on external parallel storage (the "
                    "Exascale twin) and this bay works as cache; a "
                    "standalone box may hold whole datasets locally."
                ),
            ),
            CatalogOption(
                id="boss-n1",
                name="BOSS-N1 boot module",
                summary="Mirrored boot drives that spend no data bay on the OS.",
                details=(
                    "The BOSS-N1 (Boot Optimized Storage Solution) is a "
                    "pair of hardware-mirrored M.2 NVMe drives on a small module, "
                    "dedicated to the operating system — the same part the "
                    "R760 and VxRail twins carry. Losing a boot drive "
                    "never touches the data bay, and reimaging 12,500 "
                    "servers is a fleet operation against 12,500 identical "
                    "boot modules."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="power",
        name="Power",
        blurb="Six supplies where a server normally has two, for ~11 kW per box.",
        limits="6× hot-swap PSUs",
        region_ids=["psu-bank"],
        options=[
            CatalogOption(
                id="psu-2800",
                name="6× 2,800 W hot-swap PSUs",
                summary="Capacity plus redundancy for a server that draws like a rack.",
                details=(
                    "Six 2,800 W Titanium supplies feed the chassis's "
                    "full-load draw (on the order of 11 kW, illustrative) "
                    "with headroom to lose units and keep "
                    "running, hot-swappable from the rear. The arithmetic "
                    "deserves saying plainly: one XE9680 draws roughly what "
                    "an entire rack of ordinary 1U servers draws, so power "
                    "delivery and heat rejection — not floor space — are "
                    "what actually limit how many of these a building can "
                    "hold. Colossus's reported grid-plus-Megapack story "
                    "starts at a PSU bank like this one, times roughly "
                    "12,500."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="management",
        name="Management",
        blurb="The BMC that runs the power-on you can play, times the fleet.",
        limits="1× iDRAC9 per server; OpenManage above it",
        region_ids=["idrac"],
        options=[
            CatalogOption(
                id="idrac9",
                name="iDRAC9 Datacenter",
                summary="The always-on controller that sequences and watches the box.",
                details=(
                    "The iDRAC9 (integrated Dell Remote Access Controller — "
                    "this repo's DellIDRAC twin is its full story) wakes on "
                    "standby power, sequences the bring-up this twin "
                    "animates, and streams telemetry — temperatures, watts, "
                    "fan speeds, GPU health — without the host OS's "
                    "involvement. At fleet scale it is the product: nobody "
                    "walks to a server in a 1,500-rack hall."
                ),
            ),
            CatalogOption(
                id="openmanage",
                name="OpenManage Enterprise",
                summary="Fleet console: 12,500 iDRACs as one pane and one API.",
                details=(
                    "OpenManage aggregates every iDRAC into inventory, "
                    "firmware baselines, and alerting — the difference "
                    "between managing servers and managing a fleet. Its "
                    "telemetry is also what an observability layer like "
                    "the CloudIQ twin consumes to say something useful "
                    "about 100,000 GPUs at once."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="rack-integration",
        name="Rack & cluster integration",
        blurb=(
            "How boxes become a machine: liquid racks, integrated delivery, "
            "and the fabric above."
        ),
        limits="8 servers (64 GPUs) per liquid-cooled rack at the density reported for Colossus",
        options=[
            CatalogOption(
                id="irss",
                name="Integrated Rack Scalable Systems (IRSS)",
                summary="Racks arrive built: servers, switches, and plumbing factory-tested.",
                details=(
                    "IRSS is Dell's factory-integration program — racks "
                    "show up populated, cabled, leak-tested, and burned "
                    "in, so on-site work is placement, power, and fabric "
                    "uplinks. Stand-up speed is the product: Colossus's "
                    "reported 122 days (19 from first rack to first "
                    "training run) and TACC Horizon's build both lean on "
                    "rack integration rather than server-by-server assembly, "
                    "and the XE9712 twin's 'the rack is the unit of "
                    "delivery' idea starts here."
                ),
            ),
            CatalogOption(
                id="colossus-rack",
                name="64-GPU liquid rack (8× 4U liquid-cooled servers)",
                summary="The reported Colossus building block: eight boxes, one loop.",
                details=(
                    "Eight 4U liquid-cooled 8-GPU servers (the XE9680L is "
                    "Dell's box of this shape) share one rack and one "
                    "coolant loop — 64 GPUs and 64 GPU-facing 400 GbE "
                    "ports per rack, times roughly 1,500 racks in the "
                    "first build, as reported from the Supermicro half "
                    "of Colossus. Note "
                    "what the rack is not: the NVLink domains inside it "
                    "stay eight GPUs each. The rack is a plumbing and "
                    "cabling unit, and the cluster exists in the fabric — "
                    "the exact opposite of the XE9712, where the rack "
                    "itself is the domain."
                ),
            ),
        ],
    ),
]
