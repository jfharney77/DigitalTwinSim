"""Fabric-anatomy data: a Quantum-X800 InfiniBand leaf/spine fabric, annotated.

Like the other twins, the layout is *data*, not code: regions placed in a
normalized coordinate space the frontend renders as SVG. Geometry is
stylized — favor a correct mental model over port-accurate drawings
(project scope guardrail).

The map reads top to bottom the way the SN6000 twin's does — spines above
leaves above the GPU racks, the two-hop path drawn in space — with one
deliberate addition that carries this twin's argument: the **subnet
manager**, drawn small and off to the side. It is the most important thing
in the fabric's life and the least important thing in a packet's life: it
maps the network, computes every route, installs them, and then no byte
ever passes through it. Drawing it large or central would tell the reader
something false about where data goes; ``test_anatomy.py`` pins both the
size and the position.
"""

from __future__ import annotations

from .leveling import L
from .models import FabricAnatomy, FabricRegion, Photo, SourceLink, Stat

# The only shipped visual is a self-contained schematic drawn for this
# project — not an NVIDIA or Dell product image — with an honest credit line.
FABRIC_ILLO = Photo(
    url="/quantum-fabric.svg",
    caption=(
        "A Quantum-X800 InfiniBand fabric, schematically: two spines over "
        "four leaves over four GPU racks, the OSFP cabling layer between "
        "them, and the subnet manager beside the fabric — the brain that "
        "programs every route and then leaves the data path."
    ),
    credit="Schematic illustration by this project — not an NVIDIA or Dell product image",
)

_SPINE_DESC = (
    "A Quantum-X800 spine switch — the Q3400 chassis: 144 ports of "
    "800 Gb/s across 72 OSFP cages, with SHARP reduction engines in the "
    "ASIC. NVIDIA ships it air-cooled (Q3400-RA, 4U) and liquid-cooled "
    "(Q3400-LD); this twin draws the liquid-cooled variant. "
    "Every leaf connects to every spine, so any two racks are exactly two "
    "hops apart and the subnet manager can spread routes across the whole "
    "spine layer. During SHARP collectives the spines are where partial "
    "sums merge — the switch is part of the calculator, not just the road."
)

_LEAF_DESC = (
    "A leaf switch — top-of-rack for one GPU rack. Downlinks carry each "
    "node's ConnectX-8 ports; uplinks fan out to every spine. Under SHARP "
    "the leaf performs the first level of aggregation, adding its rack's "
    "gradient streams into one partial sum before anything crosses the "
    "spine layer — the reason raw fabric traffic falls when the switches "
    "start computing."
)

_ENDPOINT_DESC = (
    "A GPU rack as the fabric sees it: a set of ConnectX-8 SuperNIC "
    "endpoints at 800 Gb/s a port — drawn here one port per GPU, the "
    "densest design — RDMA all the way: remote memory reads and writes "
    "with no host CPU in the path. At TACC's Horizon these are Dell IRSS "
    "racks of Grace Blackwell nodes, each node on a full 800 Gb/s link "
    "per TACC's user guide; inside the node NVLink does the talking, and "
    "past it every conversation rides these ports."
)


def _spine(idx: int, x: float) -> FabricRegion:
    return FabricRegion(
        id=f"spine-s{idx}", kind="spine", label=f"Quantum spine {idx}",
        x=x, y=8, w=22, h=10, description=_SPINE_DESC,
    )


def _leaf(idx: int, x: float) -> FabricRegion:
    return FabricRegion(
        id=f"leaf-l{idx}", kind="leaf", label=f"Leaf {idx}",
        x=x, y=28, w=16, h=10, description=_LEAF_DESC,
    )


def _endpoint(idx: int, x: float) -> FabricRegion:
    return FabricRegion(
        id=f"endpoint-e{idx}", kind="endpoint", label=f"GPU rack {idx}",
        x=x, y=50, w=16, h=12, description=_ENDPOINT_DESC,
    )


ANATOMY = FabricAnatomy(
    id="quantum-x800",
    name="Quantum-X800 InfiniBand fabric",
    vendor="NVIDIA + Dell Technologies (IRSS delivery)",
    form_factor="Two-tier fat tree — Q3400 spines, leaf switches, ConnectX-8 endpoints",
    generation="NVIDIA Quantum-X800 (800 Gb/s InfiniBand)",
    year=2025,
    width=100,
    height=64,
    overview=L(
        novice=(
            "This is the network inside a supercomputer — specifically the "
            "kind TACC's Horizon uses to join thousands of processors into "
            "one machine. It looks like a family tree: racks of computers at "
            "the bottom, a switch on top of each rack, and core switches "
            "above those that every rack shares, so any two computers can "
            "reach each other in two hops. Three things make it unusual. "
            "First, one small computer off to the side — the subnet manager "
            "— maps the whole network and writes every route into the "
            "switches before any data moves; after that it steps aside. "
            "Second, no sender may transmit until the receiver has granted "
            "it space, so data cannot be lost the way an ordinary network "
            "loses it — the worst case is a brief wait. Third, the switches "
            "themselves do part of the mathematics, adding numbers as they "
            "pass through. It is less like an office network and more like "
            "wiring inside one enormous computer, which is exactly what it "
            "is."
        ),
        plain=(
            "A Quantum-X800 InfiniBand fabric: ConnectX-8 endpoints in GPU "
            "racks, a leaf per rack, every leaf to every spine — a two-tier "
            "fat tree where any pair of racks is two hops apart. Three "
            "architectural facts distinguish it from the SN6000 Ethernet "
            "twin. The subnet manager (drawn small, beside the fabric) maps "
            "the network and installs every route centrally before a byte "
            "moves, then leaves the data path. Credit-based flow control "
            "makes loss unexpressible — senders transmit only against "
            "granted receiver buffers, so congestion means microsecond "
            "stalls, never drops. And SHARP puts reduction arithmetic in "
            "the switch ASICs, so all-reduce data crosses the fabric once "
            "and pre-summed. This is the interconnect TACC's Horizon "
            "names, delivered over Dell IRSS racks."
        ),
        standard=(
            "The Quantum-X800 fabric is NVIDIA's 800 Gb/s InfiniBand "
            "platform — Q3400 spine switches, leaf switches, ConnectX-8 "
            "SuperNIC endpoints — drawn here as the two-tier fat tree "
            "joining four GPU racks, the shape it takes at TACC's Horizon "
            "over Dell IRSS Grace Blackwell racks. It is the deliberate "
            "counterpart to the SN6000 Spectrum-X twin, and the contrast "
            "is architectural, not a speed grade. Ethernet drops by "
            "default, so Spectrum-X must prove losslessness under stress; "
            "InfiniBand's link layer grants transmission only against "
            "receiver buffer credits, so a packet is never sent without a "
            "reserved place to land and the failure mode is a microsecond "
            "stall, never a loss. Ethernet routing converges by "
            "distributed protocol; here a centralized subnet manager maps "
            "the fabric and installs every forwarding table before any "
            "traffic — then steps off the data path, which is why it is "
            "drawn small and beside the fabric rather than atop it. And "
            "SHARP puts reduction engines in the switch ASICs, so the "
            "all-reduce that gates every training step is computed as it "
            "travels. The geometry encodes all three: tiers stacked for "
            "the two-hop path, the manager marginal by design."
        ),
        technical=(
            "Two-tier fat tree: Q3400 spines (144× 800 Gb/s, liquid-cooled "
            "variant drawn, SHARP engines), leaves, ConnectX-8 endpoints. Phase order "
            "off → power → discover → routes → credits → ready → "
            "collective → sharp → burst → steady. Asserted: uncredited "
            "transmission is zero on every step (constructive, not "
            "reactive); the SM is active in exactly {discover, routes} and "
            "absent from every traffic phase; route computation holds max "
            "dwell; SHARP strictly lowers fabric_tbps while raising "
            "allreduce_gbps; the burst stalls senders (only nonzero-stall "
            "step) at ≥95% peak link with zero loss. Geometry pinned: "
            "tiers vertically ordered, SM smaller than every fabric block "
            "and strictly beside the spine tier."
        ),
        expert=(
            "X800 fat tree: Q3400 spines, CX-8 endpoints. Uncredited tx ≡ "
            "0; SM ∈ {discover, routes} only, off data path; routes = max "
            "dwell; SHARP: Tbps↓ allreduce↑; burst: stalls>0 once, peak "
            "≥95%, zero loss. SM drawn smallest, beside the tree."
        ),
    ),
    regions=[
        FabricRegion(
            id="manager", kind="manager",
            label=L(standard="UFM / SM", novice="Manager"),
            x=0, y=1, w=8, h=6,
            description=(
                "The subnet manager — NVIDIA UFM, the fabric's "
                "centralized brain. It discovers every switch, adapter, "
                "and cable; computes every forwarding table; installs "
                "them; and then gets out of the way — no data packet ever "
                "passes through it, and an SM outage stops management, "
                "not traffic. It is drawn deliberately small and beside "
                "the fabric: the most important thing in the fabric's "
                "life, and the least important thing in a packet's."
            ),
        ),
        _spine(1, 24),
        _spine(2, 56),
        _leaf(1, 8),
        _leaf(2, 32),
        _leaf(3, 56),
        _leaf(4, 80),
        FabricRegion(
            id="optics", kind="optics", label="OSFP optics & fibre",
            x=8, y=42, w=64, h=4,
            description=(
                "The cabling layer: OSFP twin-port transceivers — two "
                "800 Gb/s ports per cage — and the fibre plant between "
                "tiers. At "
                "these rates the optics budget — power, cost, and failure "
                "rate — is a first-class design constraint; a "
                "Horizon-scale fabric carries thousands of transceivers, "
                "and cable health is one of the things UFM watches "
                "continuously."
            ),
        ),
        FabricRegion(
            id="cooling", kind="cooling", label="Liquid cooling",
            x=74, y=42, w=22, h=4,
            description=(
                "The switch silicon's liquid loop. A Q3400 spine moves "
                "115.2 Tb/s through one chassis. NVIDIA sells it "
                "air-cooled (Q3400-RA) and liquid-cooled (Q3400-LD); the "
                "liquid variant, drawn here, cold-plates the ASICs like "
                "the GPUs they serve — the same plumbing story the IR7000 "
                "twin tells for the compute racks, extended to the "
                "network that joins them."
            ),
        ),
        _endpoint(1, 8),
        _endpoint(2, 32),
        _endpoint(3, 56),
        _endpoint(4, 80),
    ],
    stats=[
        Stat(label="Port speed", value="800 Gb/s InfiniBand (XDR generation)"),
        Stat(label="Spine chassis", value="Q3400 — 144 ports in 72 OSFP cages; air- or liquid-cooled"),
        Stat(label="Topology", value="Two-tier fat tree — any pair, two hops"),
        Stat(label="Flow control", value="Credit-based — no send without a granted buffer"),
        Stat(label="Routing", value="Computed centrally by the subnet manager, pre-installed"),
        Stat(label="In-network compute", value="SHARP v4 — reductions in the switch ASICs"),
        Stat(label="Endpoints", value="ConnectX-8 SuperNICs — RDMA, 800 Gb/s a port"),
        Stat(label="At TACC Horizon", value="Joins Dell IRSS Grace Blackwell racks — 4,000 GPUs, 800 Gb/s per GPU node"),
    ],
    photo=FABRIC_ILLO,
    sources=[
        SourceLink(
            label="NVIDIA Quantum-X800 InfiniBand platform",
            url="https://www.nvidia.com/en-us/networking/products/infiniband/quantum-x800/",
        ),
        SourceLink(
            label="Dell Technologies powers TACC's new supercomputer Horizon",
            url="https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2025~11~dell-technologies-powers-taccs-new-supercomputer-horizon.htm",
        ),
        SourceLink(
            label="NVIDIA UFM fabric management",
            url="https://www.nvidia.com/en-us/networking/infiniband/ufm/",
        ),
        SourceLink(
            label="NVIDIA SHARP (in-network computing) documentation",
            url="https://networking-docs.nvidia.com/sharpum/3.16.0",
        ),
        SourceLink(
            label="NVIDIA Q32xx/Q34xx XDR switch systems user manual (models, ports, cooling)",
            url="https://networking-docs.nvidia.com/xdrswitcheshw/introduction",
        ),
        SourceLink(
            label="TACC Horizon user guide (node counts, XDR link speeds, topology)",
            url="https://docs.tacc.utexas.edu/hpc/horizon/",
        ),
    ],
)
