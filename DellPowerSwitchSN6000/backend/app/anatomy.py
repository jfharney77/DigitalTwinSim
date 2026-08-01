"""Fabric anatomy data: an SN6000 leaf/spine AI fabric, annotated.

Like the other twins, the layout is *data*, not code: regions placed in a
normalized coordinate space the frontend renders as SVG. Geometry is
stylized — favor a correct mental model over rack accuracy (project scope
guardrail).

The view is a topology diagram drawn the way network engineers draw one:
spines across the top, leaves in a band beneath them, and the GPU racks
they serve at the bottom. Every leaf connects to every spine — that is the
whole point of the shape, and it is why any endpoint reaches any other in
two hops. The supporting subsystems (optics, telemetry and congestion
control, liquid cooling, management) sit in their own bands.

A real cluster has more of everything; two spines, four leaves, and four
endpoint racks are enough to show the pattern.
"""

from __future__ import annotations

from .leveling import L
from .models import FabricAnatomy, FabricRegion, Photo, SourceLink, Stat

# The only shipped visual is a self-contained schematic drawn for this
# project — not a Dell or NVIDIA product image — with an honest credit line.
FABRIC_ILLO = Photo(
    url="/sn6000-fabric.svg",
    caption=(
        "A leaf/spine AI fabric: every leaf switch connects to every spine, "
        "so any GPU rack reaches any other in two hops — and every "
        "leaf-to-spine pair gives adaptive routing another path to spread a "
        "congested flow onto."
    ),
    credit="Schematic illustration by this project — not a Dell product image",
)

_SPINE_DESC = (
    "A spine switch. Spines connect only to leaves — never to endpoints and "
    "never to each other — and every leaf connects to every spine. That "
    "discipline is what makes path lengths uniform: any GPU rack reaches "
    "any other in exactly two hops, so no pair of ranks in a collective is "
    "structurally slower than another. Adding a spine adds bandwidth *and* "
    "another equal-cost path for adaptive routing to use."
)

_LEAF_DESC = (
    "A leaf switch — top-of-rack, where the GPU racks actually attach. Each "
    "leaf carries endpoint ports downward and uplinks to every spine "
    "upward, and the ratio between those two (the oversubscription ratio) "
    "is the single most consequential number in the design: AI clusters are "
    "usually built at or near 1:1, because a collective that has to squeeze "
    "through a narrow uplink stalls the whole job."
)

_ENDPOINT_DESC = (
    "A GPU rack as the fabric sees it — an XE9712 in this repo's AI "
    "factory. Inside the rack, NVLink fuses 72 GPUs into one domain at "
    "1.8 TB/s per GPU; the moment traffic leaves the rack it becomes this "
    "fabric's problem, at roughly an order of magnitude less bandwidth. "
    "That gap is why jobs are mapped to keep the chattiest communication "
    "inside a rack and let only the calmer data-parallel traffic cross."
)


def _spine(idx: int, x0: float) -> FabricRegion:
    return FabricRegion(
        id=f"spine-s{idx}", kind="spine", label=f"Spine {idx}",
        x=x0, y=1, w=40, h=9, description=_SPINE_DESC,
    )


def _leaf(idx: int, x0: float) -> FabricRegion:
    return FabricRegion(
        id=f"leaf-l{idx}", kind="leaf", label=f"Leaf {idx}",
        x=x0, y=22, w=22, h=10, description=_LEAF_DESC,
    )


def _endpoint(idx: int, x0: float) -> FabricRegion:
    return FabricRegion(
        id=f"endpoint-e{idx}", kind="endpoint", label=f"GPU rack {idx}",
        x=x0, y=36, w=22, h=12, description=_ENDPOINT_DESC,
    )


_LEAF_X = [2, 26, 50, 74]


ANATOMY = FabricAnatomy(
    id="sn6000",
    name="PowerSwitch SN6000 leaf/spine AI fabric",
    vendor="Dell Technologies + NVIDIA",
    form_factor="Leaf/spine Ethernet fabric — 1.6 Tb/s ports, Spectrum-6",
    generation="Dell AI Factory with NVIDIA (Spectrum-X)",
    year=2026,
    width=100,
    height=62,
    overview=L(
        novice=(
            "When thousands of graphics processors work on one problem "
            "together, they have to stop and exchange results constantly, and "
            "every one of them must finish that exchange before any of them can "
            "continue. That makes the network between them unusually "
            "unforgiving. An ordinary network, when it gets busy, simply throws "
            "away some traffic and lets the sender notice and try again — which "
            "is fine for a web page and disastrous here, because that one "
            "delayed message stalls every processor in the job, not just one. "
            "So this network is built never to discard anything. It warns "
            "senders early, pauses selectively, and shifts traffic onto "
            "alternative routes. Watch the dropped-message counter during the "
            "busiest moment: the hardest-worked link is at 98% and the counter "
            "still reads zero."
        ),
        plain=(
            "The SN6000 uses NVIDIA Spectrum-6 silicon — 1.6 Tb/s ports, up to "
            "409.6 Tb/s of switching capacity — and the subject here is not one "
            "switch but the leaf/spine fabric several of them form. Every leaf "
            "connects to every spine, so any two GPU racks are always the same "
            "two hops apart; uniform distance matters more than raw speed, "
            "because a collective operation finishes only when its slowest "
            "participant does. The defining property is what the fabric refuses "
            "to do. Ordinary Ethernet drops packets when buffers fill and lets "
            "senders retransmit, and in distributed training one retransmission "
            "stalls the entire fleet. Dropped packets stay at zero on every "
            "step, including at 98% link utilisation."
        ),
        standard=(
            "The Dell PowerSwitch SN6000 series is built on NVIDIA Spectrum-6 "
            "silicon: 1.6 Tb/s ports, up to 409.6 Tb/s of switching capacity, "
            "up to 2,048 breakout connections, with liquid cooling and "
            "co-packaged optics options, optimized for NVIDIA Spectrum-X "
            "Ethernet. This twin draws not one switch but the fabric they form. "
            "The topology is leaf/spine — every leaf connected to every spine — "
            "because a collective operation finishes only when its slowest "
            "participant does, so uniform path length between any two endpoints "
            "matters more than any single link's speed. The property that "
            "defines an AI fabric is what it refuses to do: ordinary Ethernet "
            "drops packets when buffers fill and lets senders retransmit, but "
            "in distributed training a retransmission stalls every GPU in the "
            "job, not just one flow. So this fabric signals congestion early, "
            "pauses selectively, and spreads flows across the alternate paths "
            "the topology holds in reserve — and never drops. The layout is a "
            "stylized mental model; a real cluster has far more of everything."
        ),
        technical=(
            "Spectrum-6: 1.6 Tb/s ports, up to 409.6 Tb/s switching capacity, "
            "2,048 breakout connections, liquid cooling and co-packaged optics "
            "options, Spectrum-X Ethernet. The subject is the leaf/spine "
            "fabric, not the switch — full leaf-to-spine mesh gives uniform "
            "two-hop reachability, which matters because a collective completes "
            "at the rate of its slowest participant. Asserted: zero drops on "
            "every step; the congestion step drives the busiest link ≥95%, so "
            "losslessness is proven under stress rather than at idle; adaptive "
            "routing relieves without losing work — 98%@24 Tb/s → 71%@31 Tb/s; "
            "link training holds max dwell."
        ),
        expert=(
            "Spectrum-6 leaf/spine: 1.6 Tb/s ports, 409.6 Tb/s capacity, "
            "uniform two-hop reachability. Zero drops asserted on every step, "
            "with the congestion step forced ≥95% so losslessness is proven "
            "under stress. Adaptive routing: 98%@24 Tb/s → 71%@31 Tb/s — hot "
            "link cooler, aggregate not reduced. Link training holds max dwell."
        ),
    ),
    regions=[
        _spine(1, 6),
        _spine(2, 54),
        FabricRegion(
            id="optics", kind="optics", label="Optics — pluggable or co-packaged",
            x=6, y=12, w=88, h=7,
            description=(
                "The optics layer between leaves and spines. At 1.6 Tb/s "
                "per port the transceivers become a serious share of the "
                "fabric's power draw and failure rate, which is why the "
                "SN6000 offers co-packaged optics (CPO): the optical engine "
                "moves onto the switch package itself, shortening the "
                "electrical path, cutting signal loss and power, and "
                "removing thousands of pluggable modules from the estate. "
                "The XE9712's NVLink cartridge makes the same trade "
                "differently — it avoids optics entirely by keeping the "
                "domain inside one rack, an option a cross-rack fabric does "
                "not have."
            ),
        ),
        *[_leaf(i + 1, x) for i, x in enumerate(_LEAF_X)],
        *[_endpoint(i + 1, x) for i, x in enumerate(_LEAF_X)],
        FabricRegion(
            id="telemetry", kind="telemetry", label="Congestion control & telemetry",
            x=2, y=52, w=30, h=8,
            description=(
                "The fabric's reflexes. Spectrum-X pairs switch telemetry "
                "with congestion control that acts before buffers overflow: "
                "explicit congestion notification (ECN) marks packets so "
                "senders slow down, priority flow control (PFC) pauses one "
                "traffic class instead of dropping it, and adaptive routing "
                "moves flows onto alternate equal-cost paths using live "
                "load data rather than a static hash. Conventional Ethernet "
                "pins a flow to one path for its lifetime, so an unlucky "
                "collision stays unlucky for the whole job; this is the "
                "machinery that fixes it."
            ),
        ),
        FabricRegion(
            id="cooling", kind="cooling", label="Liquid cooling",
            x=34, y=52, w=30, h=8,
            description=(
                "Liquid cooling for the switch silicon. Spectrum-6 at "
                "409.6 Tb/s is dense enough that the SN6000 offers the same "
                "cold-plate treatment the GPUs get, served by the same "
                "facility loop this repo's IR7000 twin models. It is a "
                "useful reminder that in an AI factory the network is not a "
                "quiet accessory in the corner — it is another kilowatt-"
                "class heat source that the cooling design must account "
                "for."
            ),
        ),
        FabricRegion(
            id="mgmt", kind="management", label="Fabric management",
            x=66, y=52, w=32, h=8,
            description=(
                "The control plane: the network operating system on each "
                "switch plus the fabric-wide management that validates "
                "topology, watches link health, and reroutes around "
                "failures. At this scale the fabric is expected to lose "
                "links routinely — thousands of ports means something is "
                "always degraded — so the operational goal is not a "
                "perfect fabric but one whose failures never surface to the "
                "job as a stall."
            ),
        ),
    ],
    stats=[
        Stat(label="Silicon", value="NVIDIA Spectrum-6"),
        Stat(label="Port speed", value="1.6 Tb/s"),
        Stat(label="Switching capacity", value="Up to 409.6 Tb/s"),
        Stat(label="Breakout connections", value="Up to 2,048 per system"),
        Stat(label="Topology", value="Leaf/spine — any endpoint pair, two hops"),
        Stat(label="Lossless", value="ECN + PFC + adaptive routing; zero drops"),
        Stat(label="Options", value="Liquid cooling · co-packaged optics"),
        Stat(label="Availability", value="Globally available from July 2026"),
    ],
    photo=FABRIC_ILLO,
    sources=[
        SourceLink(
            label="Dell PowerSwitch SN6000 series spec sheet",
            url="https://www.delltechnologies.com/asset/en-us/products/networking/technical-support/dell-powerswitch-sn6000-series-spec-sheet.pdf",
        ),
        SourceLink(
            label="Dell AI Factory with NVIDIA (March 2026 announcement)",
            url="https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2026~03~dell-ai-factory-with-nvidia-delivers-proven-path-to-enterprise-ai-roi.htm",
        ),
        SourceLink(
            label="Dell — integrated compute and networking with NVIDIA",
            url="https://www.dell.com/en-us/blog/deploy-ai-faster-with-integrated-compute-and-networking-from-dell-and-nvidia/",
        ),
        SourceLink(
            label="Dell Technologies World 2026 announcements",
            url="https://www.dell.com/en-us/blog/dell-technologies-world-2026-enterprise-ai-announcements-this-week/",
        ),
    ],
)
