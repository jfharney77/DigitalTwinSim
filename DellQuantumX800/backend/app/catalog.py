"""Component catalog for the Quantum-X800 InfiniBand fabric twin — backend
data, not frontend code, exactly like the other twins. Categories map onto
the anatomy's regions via ``region_ids`` so the UI can light up where an
option lives. Copy is written for a technically skilled reader new to
InfiniBand: vocabulary (subnet manager, credit-based flow control, SHARP,
fat tree, rail-optimized, OSFP, SuperNIC, GPUDirect) is spelled out on
first use. Counts and capacities are illustrative, anchored to the NVIDIA
and Dell sources carried in anatomy.py."""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

_SPINE_REGIONS = ["spine-s1", "spine-s2"]
_LEAF_REGIONS = [f"leaf-l{i}" for i in range(1, 5)]
_ENDPOINT_REGIONS = [f"endpoint-e{i}" for i in range(1, 5)]

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="platform",
        name="Switch platform",
        blurb=(
            "The InfiniBand generation sets the fabric's speed of light — "
            "and the previous one is still most of the installed base."
        ),
        limits="144× 800 Gb/s ports per Q3400 spine chassis",
        region_ids=_SPINE_REGIONS + _LEAF_REGIONS,
        options=[
            CatalogOption(
                id="quantum-x800",
                name="Quantum-X800 (Q3400, 800 Gb/s XDR)",
                summary=(
                    "The current generation: 144 ports of 800 Gb/s per "
                    "liquid-cooled chassis, SHARP v4 in the ASIC — "
                    "Horizon's fabric."
                ),
                details=(
                    "The Q3400 spine chassis switches over 100 Tb/s: 144 "
                    "ports of 800 Gb/s InfiniBand (the XDR generation), "
                    "liquid-cooled because at that density air cannot "
                    "carry the ASIC's heat away. SHARP v4 reduction "
                    "engines sit in the switch silicon itself, and the "
                    "same platform scales from one rack to "
                    "tens-of-thousands-of-endpoint fat trees. This is "
                    "the generation TACC's Horizon names, joining Dell "
                    "IRSS Grace Blackwell racks at 4,000 GPUs."
                ),
            ),
            CatalogOption(
                id="quantum-2",
                name="Quantum-2 (QM9700, 400 Gb/s NDR)",
                summary=(
                    "The previous generation, and most of the installed "
                    "base — same architecture at half the port rate."
                ),
                details=(
                    "Quantum-2 carries the identical architectural story "
                    "— central subnet manager, credit-based flow "
                    "control, SHARP — at 400 Gb/s per port. It matters "
                    "here for honesty's sake: most production InfiniBand "
                    "clusters run this or older generations, and a "
                    "campus upgrading to X800 spines can keep NDR "
                    "leaves during the transition, because the "
                    "architecture, not the port rate, is what the "
                    "software stack depends on."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="topology",
        name="Topology",
        blurb=(
            "How the tree is shaped decides what the fabric guarantees — "
            "full bisection for any traffic, or rails tuned to training."
        ),
        limits="Two-tier fat tree shown; three tiers past ~100k endpoints",
        region_ids=_SPINE_REGIONS + _LEAF_REGIONS,
        options=[
            CatalogOption(
                id="fat-tree",
                name="Non-blocking fat tree",
                summary=(
                    "Every leaf to every spine at full bandwidth: any "
                    "traffic pattern, no oversubscription, two hops."
                ),
                details=(
                    "A fat tree keeps total uplink bandwidth equal to "
                    "total downlink bandwidth at every tier, so the "
                    "fabric is non-blocking: any set of pairs can "
                    "converse at line rate simultaneously. The subnet "
                    "manager exploits the symmetry when it computes "
                    "routes, spreading pairs evenly across spines. "
                    "Academic systems like Horizon choose this shape "
                    "because their workload mix is unknowable in "
                    "advance — MPI codes today, training jobs tomorrow."
                ),
            ),
            CatalogOption(
                id="rail-optimized",
                name="Rail-optimized (training-tuned)",
                summary=(
                    "Each GPU position gets its own rail of the fabric — "
                    "cheaper at scale, tuned for collective traffic."
                ),
                details=(
                    "AI-factory builds often wire GPU N of every server "
                    "to the same leaf, forming per-position 'rails' that "
                    "match how collective libraries schedule traffic. It "
                    "buys cost and cable-length savings at hyperscale in "
                    "exchange for generality — the exact trade a "
                    "single-tenant training factory can take and a "
                    "shared academic machine usually cannot."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="transport",
        name="Lossless transport",
        blurb=(
            "Not an option but the constitution: permission precedes "
            "transmission on every link."
        ),
        limits="Credit-based flow control on every link, always on",
        region_ids=_LEAF_REGIONS + _SPINE_REGIONS,
        options=[
            CatalogOption(
                id="credit-flow-control",
                name="Credit-based flow control",
                summary=(
                    "Senders transmit only against granted receiver "
                    "buffers — loss is unexpressible, waiting is the "
                    "worst case."
                ),
                details=(
                    "On every InfiniBand link the receiver advertises "
                    "its free buffer space as credits and the sender "
                    "spends them to transmit, pausing when they run "
                    "out. There is no configuration in which this is "
                    "off — it is the link layer's constitution, and the "
                    "reason the twin's packets-sent-without-credit "
                    "counter cannot move. Contrast the SN6000 twin: "
                    "Ethernet drops by default and Spectrum-X earns "
                    "losslessness with ECN, PFC, and adaptive routing "
                    "reacting in time. Constructive versus reactive is "
                    "the deepest line between the two fabrics."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="management",
        name="Subnet management",
        blurb=(
            "One brain maps the fabric and programs every route — then "
            "leaves the data path."
        ),
        limits="One active SM per fabric (with standbys)",
        region_ids=["manager"],
        options=[
            CatalogOption(
                id="ufm",
                name="NVIDIA UFM (Unified Fabric Manager)",
                summary=(
                    "The subnet manager plus fleet telemetry: topology, "
                    "routes, cable health, and congestion analytics."
                ),
                details=(
                    "UFM hosts the subnet manager — the process that "
                    "discovers the fabric, assigns addresses, computes "
                    "every forwarding table, and installs them — and "
                    "wraps it in operations tooling: cable and "
                    "transceiver health, congestion telemetry, "
                    "predictive maintenance. It runs beside the fabric, "
                    "not in the data path; standby instances take over "
                    "management if it fails, and traffic never notices. "
                    "The twin's trace dwells on its route computation "
                    "because at Horizon scale that is genuinely the "
                    "slow step of bring-up."
                ),
            ),
            CatalogOption(
                id="embedded-sm",
                name="Embedded subnet manager",
                summary=(
                    "The SM run on a switch itself — right-sized for "
                    "small fabrics and edge pods."
                ),
                details=(
                    "Small fabrics — a rack or two of nodes — can run "
                    "the subnet manager directly on a switch's "
                    "management CPU instead of dedicating a UFM host. "
                    "Same protocol, same central authority, none of the "
                    "fleet analytics; the honest option when the fabric "
                    "is eight cables and a dashboard would outnumber "
                    "the switches."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="in-network-compute",
        name="In-network computing",
        blurb=(
            "The switch as part of the calculator: reductions computed "
            "as the data travels."
        ),
        limits="SHARP engines per switch ASIC; trees span the fabric",
        region_ids=_SPINE_REGIONS + _LEAF_REGIONS,
        options=[
            CatalogOption(
                id="sharp",
                name="SHARP v4 (in-fabric reductions)",
                summary=(
                    "All-reduce arithmetic in the switch ASICs — data "
                    "crosses once, pre-summed."
                ),
                details=(
                    "SHARP (Scalable Hierarchical Aggregation and "
                    "Reduction Protocol) builds a reduction tree "
                    "through the switches: leaves add their racks' "
                    "gradient streams, spines merge partial sums, and "
                    "one result multicasts back down. Raw traffic "
                    "falls while effective all-reduce throughput "
                    "rises — the twin's sharp step shows the counters "
                    "crossing. NCCL and MPI both offload to it "
                    "transparently. This is the qualitative capability "
                    "Ethernet fabrics lack: not moving bytes faster, "
                    "but moving fewer bytes because the network did "
                    "the math."
                ),
            ),
            CatalogOption(
                id="host-collectives",
                name="Host-based collectives (fallback)",
                summary=(
                    "The classical path: endpoints do all the "
                    "arithmetic, the fabric only carries."
                ),
                details=(
                    "Without SHARP, collective libraries run "
                    "ring or tree all-reduce entirely on the "
                    "endpoints: every gradient crosses the fabric "
                    "twice (up as inputs, down as results) and the "
                    "GPUs spend cycles adding. It works everywhere — "
                    "it is how the twin's collective step runs before "
                    "the sharp step — and its cost is exactly what "
                    "SHARP exists to delete."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="endpoints",
        name="Endpoints & adapters",
        blurb="The fabric ends at a SuperNIC in every node — one port per GPU.",
        limits="One 800 Gb/s port per GPU at Horizon-class density",
        region_ids=_ENDPOINT_REGIONS,
        options=[
            CatalogOption(
                id="connectx8",
                name="ConnectX-8 SuperNIC",
                summary=(
                    "800 Gb/s InfiniBand per adapter, RDMA and GPUDirect "
                    "— the host CPU never touches a tensor."
                ),
                details=(
                    "The ConnectX-8 SuperNIC terminates the fabric in "
                    "every node: RDMA (remote direct memory access) "
                    "moves data between GPU memories without the host "
                    "CPU, and GPUDirect lets the NIC read and write HBM "
                    "directly. One adapter per GPU is the same design "
                    "signature the XE9680 twin draws as paired rows — "
                    "every accelerator with its own private on-ramp, no "
                    "queueing behind siblings."
                ),
            ),
            CatalogOption(
                id="bluefield3",
                name="BlueField-3 DPU",
                summary=(
                    "An adapter with its own Arm cores for storage, "
                    "isolation, and services traffic."
                ),
                details=(
                    "A DPU (data processing unit) is a NIC that runs "
                    "software: storage access, tenant isolation, and "
                    "telemetry execute on the adapter instead of the "
                    "host. In a shared academic machine it keeps "
                    "management and storage traffic off the compute "
                    "rails; the per-GPU ConnectX ports move tensors "
                    "while the DPU moves everything else."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="optics",
        name="Optics & cabling",
        blurb=(
            "At 800 Gb/s the cable plant is a first-class engineering "
            "problem, not an accessory."
        ),
        limits="Thousands of transceivers at Horizon scale",
        region_ids=["optics"],
        options=[
            CatalogOption(
                id="osfp-optics",
                name="OSFP twin-port optics",
                summary=(
                    "The workhorse: two 400 Gb/s lanes per OSFP cage, "
                    "fibre runs between tiers."
                ),
                details=(
                    "OSFP (octal small form-factor pluggable) "
                    "transceivers carry the 800 Gb/s links between "
                    "tiers over fibre. At fabric scale their power "
                    "draw and failure rate are budget lines of their "
                    "own — thousands of transceivers, each a small "
                    "laser — which is why UFM tracks per-cable health "
                    "and why co-packaged optics (lasers moved onto the "
                    "switch package) is the direction the SN6000 twin's "
                    "catalog also points."
                ),
            ),
            CatalogOption(
                id="dac-copper",
                name="Passive copper (in-rack)",
                summary=(
                    "Short runs skip the lasers: cheaper, cooler, more "
                    "reliable — where distance allows."
                ),
                details=(
                    "Leaf-to-node runs inside a rack are short enough "
                    "for passive copper, which has no laser to fail "
                    "and no transceiver watts to pay. The rule of "
                    "thumb across this repo's fabric twins: copper "
                    "wherever geometry permits (the XE9712's NVLink "
                    "cartridge is the extreme case), optics only where "
                    "distance forces them."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="cooling",
        name="Switch cooling",
        blurb="The network joined the liquid loop when its ASICs got GPU-dense.",
        limits="Liquid-cooled Q3400 chassis; air-cooled leaf options",
        region_ids=["cooling"],
        options=[
            CatalogOption(
                id="liquid-chassis",
                name="Liquid-cooled spine chassis",
                summary=(
                    "Cold plates on the switch ASICs, plumbed to the "
                    "same loop as the GPU racks."
                ),
                details=(
                    "A Q3400 spine moves over 100 Tb/s through one "
                    "chassis, and the ASIC density that implies has "
                    "pushed the switch onto cold plates — the same "
                    "CDU-and-manifold story the IR7000 twin tells for "
                    "compute, extended to the network. A Horizon-class "
                    "machine room plumbs its spines like its racks."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="delivery",
        name="Delivery & integration",
        blurb=(
            "How a fabric this size actually arrives: in Dell's "
            "factory-integrated racks, pre-cabled and burned in."
        ),
        limits="Fabric delivered with the racks it joins",
        options=[
            CatalogOption(
                id="irss",
                name="Dell IRSS (Integrated Rack Scalable Systems)",
                summary=(
                    "Racks arrive with leaves installed and cabled; "
                    "on-site work is spine uplinks and validation."
                ),
                details=(
                    "Dell's factory integration puts the leaf switches, "
                    "node cabling, and (for liquid racks) the plumbing "
                    "in before delivery — the same program behind the "
                    "XE9712 rack twin and TACC's Horizon build. "
                    "On-site, a fabric of thousands of cables reduces "
                    "to running spine uplinks, then letting the subnet "
                    "manager sweep and validate what the factory "
                    "built."
                ),
            ),
            CatalogOption(
                id="fabric-services",
                name="Fabric design & validation services",
                summary=(
                    "Topology sizing, cable plans, and acceptance runs "
                    "before the machine is handed over."
                ),
                details=(
                    "A supercomputer fabric is commissioned, not "
                    "plugged in: topology sizing against the workload "
                    "mix, cable-length planning, and acceptance "
                    "testing — sweeping the fabric, driving synthetic "
                    "collectives and incasts, and comparing measured "
                    "bandwidth against the design — before handover. "
                    "The twin's burst step is a one-screen version of "
                    "an acceptance test."
                ),
            ),
        ],
    ),
]
