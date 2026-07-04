"""The components-and-options menu for the PowerEdge R760.

Like anatomy.py, the catalog is data, not code: each ``CatalogCategory``
maps to the chassis regions it slots into (``region_ids`` from anatomy.py)
and lists the orderable options, described for a technically skilled reader
who is new to Dell servers. Contents follow Dell's R760 spec sheet; option
lists are representative, not exhaustive.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="processors",
        name="Processors",
        blurb=(
            "4th- or 5th-generation Intel Xeon Scalable processors. Intel's "
            "tier names — Silver, Gold, Platinum — track core count, clock, "
            "and features like memory speed and UPI links between sockets."
        ),
        limits="1 or 2 sockets, up to 350 W TDP each",
        region_ids=["cpu1", "cpu2"],
        options=[
            CatalogOption(
                id="xeon-silver-4410y",
                name="Xeon Silver 4410Y · 12 cores",
                summary="Entry two-socket part for light, steady workloads.",
                details=(
                    "12 cores at 2.0 GHz base, 150 W. Silver is Intel's "
                    "value tier: lower clocks, memory capped at 4400 MT/s, "
                    "fewer inter-socket links. A sensible pick when the "
                    "server's job is file/print, a small hypervisor, or "
                    "network services that never saturate a modern core — "
                    "you keep the R760's reliability features without "
                    "paying for compute you won't use."
                ),
            ),
            CatalogOption(
                id="xeon-gold-6430",
                name="Xeon Gold 6430 · 32 cores",
                summary="The mainstream virtualization workhorse.",
                details=(
                    "32 cores at 2.1 GHz, 270 W, 4th generation (Sapphire "
                    "Rapids). Gold is the mid tier most R760s ship with: "
                    "full 8-channel DDR5 support and enough cores that a "
                    "pair yields 64 cores / 128 threads in one 2U box — "
                    "the sweet spot for consolidating VMs, where you sell "
                    "cores and memory rather than clock speed."
                ),
            ),
            CatalogOption(
                id="xeon-gold-6548y-plus",
                name="Xeon Gold 6548Y+ · 32 cores",
                summary="5th-gen Gold: same cores, faster memory and cache.",
                details=(
                    "32 cores at 2.5 GHz, 250 W, 5th generation (Emerald "
                    "Rapids). The '+' parts raise base clocks and triple "
                    "the L3 cache versus 4th gen, and unlock DDR5-5600. "
                    "Databases and latency-sensitive services feel the "
                    "bigger cache more than an extra handful of cores."
                ),
            ),
            CatalogOption(
                id="xeon-platinum-8592-plus",
                name="Xeon Platinum 8592+ · 64 cores",
                summary="Maximum core count: 128 cores across two sockets.",
                details=(
                    "64 cores at 1.9 GHz, 350 W — the top of the Emerald "
                    "Rapids stack. Platinum buys the highest core counts, "
                    "fastest UPI links between the two sockets, and the "
                    "full accelerator set (AMX for AI inference on-CPU). "
                    "At 350 W each these mandate the high-performance "
                    "cooling options, and per-core software licensing can "
                    "cost more than the silicon — count licenses before "
                    "counting cores."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="memory",
        name="Memory",
        blurb=(
            "32 DDR5 RDIMM slots — 16 per processor, 8 channels each. "
            "RDIMMs (registered DIMMs) buffer the command lines so many "
            "large modules can share a channel, standard in servers."
        ),
        limits=(
            "32 slots, up to 8 TB; 5600 MT/s on 5th-gen CPUs (4800 on "
            "4th-gen), dropping to ~4400 MT/s with 2 DIMMs per channel; "
            "16 slots usable per populated socket"
        ),
        region_ids=["dimm-a1", "dimm-a2", "dimm-b1", "dimm-b2"],
        options=[
            CatalogOption(
                id="rdimm-16gb",
                name="16 GB RDIMM",
                summary="Smallest module; fills channels cheaply.",
                details=(
                    "One 16 GB module per channel gets a two-socket box to "
                    "256 GB while keeping every memory channel busy — "
                    "bandwidth comes from populated channels, not from "
                    "module size, so eight small DIMMs per CPU beat two "
                    "big ones for throughput-bound work."
                ),
            ),
            CatalogOption(
                id="rdimm-32gb",
                name="32 GB RDIMM",
                summary="The default building block for general builds.",
                details=(
                    "The usual choice for virtualization and general "
                    "compute: 16 modules give 512 GB, 32 give 1 TB, at the "
                    "best price per gigabyte on the sheet. Populating one "
                    "DIMM per channel (16 total) preserves full memory "
                    "speed; adding the second slot per channel raises "
                    "capacity but steps the clock down a bin."
                ),
            ),
            CatalogOption(
                id="rdimm-64gb",
                name="64 GB RDIMM",
                summary="Dense capacity without touching 2 DIMMs per channel.",
                details=(
                    "2 TB from just 16 modules — full speed, and 16 empty "
                    "slots left for growth. The go-to for in-memory "
                    "databases and memory-hungry VM hosts that will expand "
                    "over the server's life."
                ),
            ),
            CatalogOption(
                id="rdimm-128gb",
                name="128 GB RDIMM",
                summary="Big-memory tier: 4 TB fully populated.",
                details=(
                    "For SAP HANA-class in-memory workloads. 32 of these "
                    "reach 4 TB; 256 GB modules exist for the full 8 TB "
                    "ceiling but at a steep price premium per gigabyte — "
                    "capacities this size are bought because the workload "
                    "demands one box, not because they are economical."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="storage-chassis",
        name="Drive bay configuration",
        blurb=(
            "The R760 chassis is ordered in one of several front-bay "
            "layouts; the backplane is factory-fitted and defines what "
            "drives the server can ever hold, so this choice is permanent."
        ),
        limits="One configuration per chassis, chosen at order time",
        region_ids=["backplane"],
        options=[
            CatalogOption(
                id="bay-12x35",
                name="12× 3.5″ SAS/SATA",
                summary="Big spinning disks for bulk capacity.",
                details=(
                    "Twelve large-form-factor bays for high-capacity hard "
                    "drives (20 TB+ each): a quarter petabyte of raw bulk "
                    "storage in 2U. The choice for backup targets and "
                    "media/object stores where capacity per dollar beats "
                    "IOPS."
                ),
            ),
            CatalogOption(
                id="bay-8x25",
                name="8× 2.5″",
                summary="Entry small-form-factor layout.",
                details=(
                    "Eight hot-swap 2.5-inch bays — plenty when the server "
                    "computes more than it stores, or when the real data "
                    "lives on a SAN or NAS elsewhere."
                ),
            ),
            CatalogOption(
                id="bay-16x25",
                name="16× 2.5″ (+2 rear)",
                summary="Balanced bays with optional rear pair.",
                details=(
                    "Sixteen front bays with room for two more at the rear "
                    "— the rear pair is handy as a dedicated mirrored pair "
                    "for logs or metadata, physically separate from the "
                    "data set."
                ),
            ),
            CatalogOption(
                id="bay-24x25",
                name="24× 2.5″ NVMe/SAS/SATA",
                summary="Maximum small-form-factor density (as pictured).",
                details=(
                    "The fully loaded front: 24 hot-swap bays, mixable "
                    "between NVMe (drives on PCIe lanes straight to the "
                    "CPUs) and SAS/SATA through the PERC controller. The "
                    "layout shown in this app's chassis view, and the "
                    "basis of software-defined storage builds like vSAN."
                ),
            ),
            CatalogOption(
                id="bay-16xe3s",
                name="16× EDSFF E3.S NVMe",
                summary="All-flash, direct to the CPUs — no RAID card.",
                details=(
                    "EDSFF E3.S is the ruler-style flash form factor "
                    "designed for NVMe rather than adapted from disks: "
                    "better cooling, denser packing. All sixteen attach "
                    "directly to CPU PCIe Gen5 lanes with no controller in "
                    "the path — lowest latency, with redundancy handled in "
                    "software instead of a PERC."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="drives",
        name="Drives",
        blurb=(
            "What goes in the bays. The split that matters: NVMe rides "
            "PCIe lanes directly for latency; SAS/SATA go through the PERC "
            "controller for hardware RAID."
        ),
        limits="Must match the ordered backplane; mixable within it",
        region_ids=["backplane"],
        options=[
            CatalogOption(
                id="nvme-u2-gen4",
                name="NVMe U.2 SSD (Gen4/Gen5)",
                summary="The performance tier: flash on PCIe lanes.",
                details=(
                    "U.2 is the 2.5-inch hot-swap package for NVMe flash — "
                    "up to 15.36 TB per drive, hundreds of thousands of "
                    "IOPS, latency in microseconds. Gen5 doubles Gen4's "
                    "per-drive bandwidth. The default for databases and "
                    "any software-defined storage tier."
                ),
            ),
            CatalogOption(
                id="sas-ssd",
                name="SAS SSD (24 Gb/s)",
                summary="Flash behind the RAID controller.",
                details=(
                    "Solid-state, but on the SAS bus through the PERC — "
                    "slower than NVMe, in exchange for battery-backed "
                    "hardware RAID and dual-port paths. The conservative "
                    "choice where the operational model is 'RAID card "
                    "manages the disks'."
                ),
            ),
            CatalogOption(
                id="sas-10k",
                name="2.4 TB 10K SAS HDD",
                summary="Legacy fast spinning disk.",
                details=(
                    "10 000-RPM enterprise disks — the performance tier "
                    "before flash. Still ordered to extend existing arrays "
                    "or meet like-for-like replacement policies; new "
                    "designs almost always favor SSDs."
                ),
            ),
            CatalogOption(
                id="nlsas-20tb",
                name="20 TB NL-SAS HDD",
                summary="Maximum capacity per bay.",
                details=(
                    "Near-line SAS: 7200-RPM high-capacity mechanics with "
                    "a SAS interface. Slow per drive but unbeatable per "
                    "terabyte — the fill for the 12× 3.5″ chassis in "
                    "backup and archive roles."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="raid",
        name="RAID / storage controllers",
        blurb=(
            "PERC (PowerEdge RAID Controller) is Dell's hardware RAID "
            "line: it builds redundant volumes across the front drives and "
            "adds battery-backed write cache. Software-defined stacks skip "
            "it for a plain pass-through HBA."
        ),
        limits="One front controller; must match backplane and drive types",
        region_ids=["perc"],
        options=[
            CatalogOption(
                id="perc-h965i",
                name="PERC 12 H965i",
                summary="Current-generation hardware RAID, NVMe-capable.",
                details=(
                    "The PERC 12 generation can RAID NVMe drives as well "
                    "as SAS/SATA, with 8 GB of cache protected by a "
                    "battery — writes acknowledged to the OS survive a "
                    "power cut in cache. Pick it when you want classic "
                    "RAID semantics at today's drive speeds."
                ),
            ),
            CatalogOption(
                id="perc-h755",
                name="PERC 11 H755",
                summary="Previous-gen RAID for SAS/SATA builds.",
                details=(
                    "The proven PERC 11 part: full hardware RAID for "
                    "SAS/SATA with battery-backed cache. Costs less than "
                    "the H965i and is entirely adequate when the drives "
                    "behind it are not NVMe."
                ),
            ),
            CatalogOption(
                id="hba355i",
                name="HBA355i (pass-through)",
                summary="No RAID — drives exposed raw to the OS.",
                details=(
                    "A plain host bus adapter: every drive appears to the "
                    "OS as itself, no volumes, no cache. Exactly what "
                    "software-defined storage (vSAN, Ceph, Storage Spaces, "
                    "ZFS) wants — those stacks do their own redundancy and "
                    "a RAID card in the path only hides drive state from "
                    "them."
                ),
            ),
            CatalogOption(
                id="s160",
                name="S160 software RAID",
                summary="Chipset-assisted RAID for boot-simple builds.",
                details=(
                    "RAID in firmware/driver rather than dedicated "
                    "silicon: no cache, no battery, modest performance, "
                    "minimal cost. Defensible for a small mirrored pair on "
                    "a machine whose real storage is elsewhere; most R760 "
                    "buyers who want cheap mirroring use the BOSS-N1 "
                    "instead."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="boot",
        name="Boot device",
        blurb=(
            "Dell's answer to 'where does the OS live': a dedicated "
            "mirrored module at the rear, so data bays stay data bays."
        ),
        limits="One BOSS-N1 module (2× M.2, RAID-1)",
        region_ids=["boss"],
        options=[
            CatalogOption(
                id="boss-n1",
                name="BOSS-N1 · 2× 480 GB M.2 NVMe",
                summary="Hot-serviceable mirrored boot module.",
                details=(
                    "BOSS (Boot Optimized Storage Solution) holds two M.2 "
                    "NVMe sticks in a hardware RAID-1 mirror, slid in from "
                    "the rear. The OS or hypervisor lives here: either "
                    "stick can fail and be swapped without opening the lid "
                    "or touching the 24 data bays. Almost every serious "
                    "R760 order includes one — the alternative is burning "
                    "two front bays and PERC configuration on the boot "
                    "volume."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="network",
        name="Networking",
        blurb=(
            "Primary NIC goes in the OCP 3.0 slot — a standardized "
            "mezzanine from the Open Compute Project that slides in from "
            "the rear without tools and without consuming a PCIe riser "
            "slot. Extra ports go on riser cards."
        ),
        limits="1 OCP 3.0 slot; additional NICs use riser PCIe slots",
        region_ids=["ocp", "riser1", "riser2"],
        options=[
            CatalogOption(
                id="ocp-broadcom-1gbe",
                name="Broadcom quad-port 1 GbE (OCP)",
                summary="Basic connectivity for management-heavy roles.",
                details=(
                    "Four gigabit ports — enough for services that talk "
                    "little (domain controllers, small appliances) or for "
                    "out-of-band segregation of management traffic. "
                    "Costs almost nothing and leaves the risers free."
                ),
            ),
            CatalogOption(
                id="ocp-intel-10gbe",
                name="Intel quad-port 10 GbE (OCP)",
                summary="The general-purpose standard.",
                details=(
                    "Four 10 GbE ports covers most enterprise roles: VM "
                    "traffic, backup windows, storage replication. SFP+ "
                    "and Base-T variants exist — match your top-of-rack "
                    "switches."
                ),
            ),
            CatalogOption(
                id="ocp-broadcom-25gbe",
                name="Broadcom dual-port 25 GbE (OCP)",
                summary="Virtualization-cluster mainstay.",
                details=(
                    "25 GbE is the current per-lane sweet spot in the "
                    "datacenter: one lane of the same signaling 100 GbE "
                    "uses, so switch ports are cheap. Two ports, bonded, "
                    "carry VM, storage (vSAN/NFS), and migration traffic "
                    "for a typical cluster node."
                ),
            ),
            CatalogOption(
                id="nvidia-connectx-100gbe",
                name="NVIDIA ConnectX-6 100 GbE (PCIe)",
                summary="High-bandwidth fabric for GPU and storage nodes.",
                details=(
                    "A riser-slot card with RDMA (remote direct memory "
                    "access — NIC-to-NIC transfers that bypass the CPU), "
                    "which GPU clusters and NVMe-over-Fabrics storage "
                    "depend on. Pair with the OCP slot for management "
                    "networks so the 100 GbE ports stay dedicated to data."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="gpu",
        name="GPUs & accelerators",
        blurb=(
            "The riser slots take datacenter GPUs — passively cooled "
            "cards that rely entirely on the chassis fan wall for airflow."
        ),
        limits=(
            "Up to 2 double-wide 300 W cards, or up to 6 single-wide; "
            "requires high-performance fans and PSUs sized for the draw"
        ),
        region_ids=["riser1", "riser2"],
        options=[
            CatalogOption(
                id="gpu-l4",
                name="NVIDIA L4 · 24 GB (single-wide, 72 W)",
                summary="Light inference and video at minimal power.",
                details=(
                    "A low-profile 72 W card needing no extra power "
                    "cables; up to six fit one R760. Right-sized for "
                    "video transcode, virtual desktop graphics, and "
                    "modest ML inference — the 'sprinkle some GPU on it' "
                    "option."
                ),
            ),
            CatalogOption(
                id="gpu-l40s",
                name="NVIDIA L40S · 48 GB (double-wide, 350 W)",
                summary="The versatile inference/graphics workhorse.",
                details=(
                    "Ada Lovelace silicon with 48 GB — strong for LLM "
                    "inference, fine-tuning, rendering, and virtual "
                    "workstations. Two fit an R760; at 350 W each they "
                    "push the build to high-performance fans and 2400 W+ "
                    "power supplies."
                ),
            ),
            CatalogOption(
                id="gpu-h100",
                name="NVIDIA H100 NVL · 94 GB (double-wide, 400 W)",
                summary="Top-end AI card for the most demanding inference.",
                details=(
                    "Hopper architecture with HBM3 memory — the card for "
                    "serving large language models. In an R760 it is "
                    "usually one or two cards for inference; training at "
                    "scale moves to purpose-built GPU chassis (XE-series) "
                    "with more power and cooling headroom."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="power",
        name="Power supplies",
        blurb=(
            "Two hot-swap PSU bays at the rear, normally run 1+1 "
            "redundant: either unit can carry the whole load, each fed "
            "from an independent power feed."
        ),
        limits="2 bays; size for full config draw on ONE unit (redundancy)",
        region_ids=["psu1", "psu2", "pdb"],
        options=[
            CatalogOption(
                id="psu-800w",
                name="800 W Titanium",
                summary="Entry sizing for CPU-only builds.",
                details=(
                    "Covers modest dual-socket configurations without "
                    "GPUs. 80 PLUS Titanium means ~96% efficiency at half "
                    "load — at datacenter scale the efficiency class is a "
                    "real line item on the power bill."
                ),
            ),
            CatalogOption(
                id="psu-1500w",
                name="1500 W Titanium",
                summary="The common choice for loaded two-socket builds.",
                details=(
                    "Headroom for two high-TDP CPUs, 24 drives, and full "
                    "DIMM population with redundancy intact. The default "
                    "on most virtualization and database configurations."
                ),
            ),
            CatalogOption(
                id="psu-2400w",
                name="2400 W Platinum",
                summary="GPU-build sizing.",
                details=(
                    "Required territory once double-wide GPUs join two "
                    "300 W+ CPUs. Note the input side: at full tilt this "
                    "draws more than a 15 A / 120 V circuit supplies — "
                    "these builds assume 200–240 V datacenter power "
                    "distribution."
                ),
            ),
            CatalogOption(
                id="psu-2800w",
                name="2800 W Titanium",
                summary="Maximum: dual 400 W GPUs plus everything else.",
                details=(
                    "The top of the range, for the heaviest accelerator "
                    "configurations while preserving 1+1 redundancy. At "
                    "this level rack power budgeting, not the server, is "
                    "usually the binding constraint."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="cooling",
        name="Cooling",
        blurb=(
            "Six hot-swap fan modules form a wall behind the drives, "
            "pulling air front-to-rear; iDRAC sets speeds from dozens of "
            "thermal sensors. The fan grade must match the config's heat."
        ),
        limits="6 fan slots; grade dictated by CPU TDP and GPU count",
        region_ids=[f"fan-{i}" for i in range(6)],
        options=[
            CatalogOption(
                id="fans-standard",
                name="Standard fans",
                summary="Quietest and cheapest; CPU-only builds.",
                details=(
                    "Sufficient for mainstream processors and no "
                    "accelerators. Lowest acoustic and power overhead — "
                    "fans are themselves a measurable share of a server's "
                    "idle draw."
                ),
            ),
            CatalogOption(
                id="fans-hpr-gold",
                name="High-performance (Gold) fans",
                summary="Mandatory for GPUs and 350 W processors.",
                details=(
                    "Higher static pressure to force air through dense "
                    "heatsinks and passively cooled GPU cards. Dell's "
                    "configurator adds these automatically once the "
                    "thermal load demands them; they are louder and "
                    "hungrier, which is the price of air-cooling 1 kW+ "
                    "of silicon in 2U."
                ),
            ),
            CatalogOption(
                id="dlc",
                name="Direct Liquid Cooling (DLC)",
                summary="Cold plates on the CPUs for top-TDP parts.",
                details=(
                    "Coolant loops to cold plates on each processor, "
                    "removing most CPU heat without airflow. Requires "
                    "rack-level plumbing (manifolds, coolant distribution "
                    "units) — a facility decision, not just a server "
                    "option — but cuts fan power sharply and keeps "
                    "350 W parts at full boost in warm datacenters."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="management",
        name="Systems management",
        blurb=(
            "iDRAC9 — the always-on management controller — is on every "
            "R760; the license tier sets which of its capabilities are "
            "unlocked. Fleet tooling (OpenManage) builds on it."
        ),
        limits="One iDRAC9, always present; tier is a license key",
        region_ids=["idrac"],
        options=[
            CatalogOption(
                id="idrac-basic",
                name="iDRAC9 Basic",
                summary="Inventory, sensors, and power control.",
                details=(
                    "The no-cost tier: hardware inventory, health "
                    "sensors, logs, and remote power on/off over the "
                    "dedicated management port. Enough for a server that "
                    "lives down the hall."
                ),
            ),
            CatalogOption(
                id="idrac-express",
                name="iDRAC9 Express",
                summary="Adds the web console and Redfish API basics.",
                details=(
                    "The usual minimum for managed environments: full web "
                    "UI, scriptable Redfish REST API, and firmware update "
                    "orchestration."
                ),
            ),
            CatalogOption(
                id="idrac-enterprise",
                name="iDRAC9 Enterprise",
                summary="Remote console and virtual media — no crash cart.",
                details=(
                    "Adds the HTML5 remote console (screen, keyboard, "
                    "mouse as if standing at the machine) and virtual "
                    "media (mount an ISO over the network and install an "
                    "OS from your desk). The feature that makes truly "
                    "remote datacenters practical; most fleets license it "
                    "on everything."
                ),
            ),
            CatalogOption(
                id="idrac-datacenter",
                name="iDRAC9 Datacenter",
                summary="Deep telemetry streaming for large fleets.",
                details=(
                    "Everything in Enterprise plus high-frequency "
                    "telemetry streaming (power, thermals, per-component "
                    "metrics pushed to analytics pipelines), automatic "
                    "certificate management, and idle-server detection. "
                    "Aimed at operators running thousands of nodes."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="rack",
        name="Rack & chassis hardware",
        blurb=(
            "The parts between the server and the rack — ordered with the "
            "system so the rails match the chassis."
        ),
        limits="Per-chassis accessories",
        region_ids=[],
        options=[
            CatalogOption(
                id="readyrails",
                name="ReadyRails sliding rails",
                summary="Tool-less rails; slide the server out live.",
                details=(
                    "Snap into square-hole racks without tools and let "
                    "the running server slide forward for lid-off service "
                    "— which is how the fans, DIMMs, and risers in this "
                    "app's chassis view are actually reached."
                ),
            ),
            CatalogOption(
                id="cable-arm",
                name="Cable management arm",
                summary="Keeps cabling attached while the server slides.",
                details=(
                    "A folding arm that carries power and network cables "
                    "behind the chassis, so sliding the server out on its "
                    "rails doesn't unplug it. Slightly restricts rear "
                    "airflow — dense GPU builds sometimes omit it and "
                    "accept unplugging instead."
                ),
            ),
            CatalogOption(
                id="bezel",
                name="Locking bezel",
                summary="Front cover: dust filter plus physical lock.",
                details=(
                    "Clips over the drive bays with a key lock — 24 "
                    "hot-swap drives are otherwise removable by anyone "
                    "who can touch the rack. Includes a status LED "
                    "pass-through and, on some models, a dust filter."
                ),
            ),
        ],
    ),
]
