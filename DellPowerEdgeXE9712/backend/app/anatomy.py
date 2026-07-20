"""Rack-anatomy data: a PowerEdge XE9712 (GB200 NVL72) rack, annotated.

Like the other twins, the layout is *data*, not code: regions placed in a
normalized coordinate space the frontend renders as SVG. Geometry is
stylized — favor a correct mental model over exact rack units (project scope
guardrail).

The view is a front-of-rack elevation. A real XE9712 carries 18 compute
trays and 9 NVLink switch trays; this floorplan shows four compute trays and
two switch trays — enough to see the pattern without drawing 27 slivers.
Power shelves sit at the top, the NVLink switch trays sit in the middle of
the rack (they are physically central so the copper cable runs to every
compute tray stay short), and the liquid loop — the in-rack CDU and the
vertical supply/return manifolds — frames the right edge and the bottom.
Every compute tray is the same building block; the rack's power comes from
the fabric fusing them, not from any tray being special.
"""

from __future__ import annotations

from .models import Photo, RackAnatomy, RackRegion, SourceLink, Stat

# The only shipped visual is a self-contained schematic drawn for this
# project — not a Dell or NVIDIA product image — with an honest credit line.
RACK_ILLO = Photo(
    url="/xe9712-rack.svg",
    caption=(
        "A PowerEdge XE9712 rack, schematically: power shelves feeding a DC "
        "busbar, 18 GB200 compute trays (four drawn), 9 NVLink switch trays "
        "at mid-rack (two drawn), and the liquid-cooling loop — CDU and "
        "manifolds — that must flow before any GPU powers on."
    ),
    credit="Schematic illustration by this project — not a Dell product image",
)


# --- Per-tray region descriptions (shared across all drawn trays) ------------

_GPU_DESC = (
    "The tray's four NVIDIA Blackwell GPUs — two per GB200 superchip, "
    "mounted under cold plates with no fans and no heatsink fins. Each GPU "
    "carries HBM3e stacked memory and can draw on the order of a kilowatt, "
    "which is why it is liquid-cooled and why the whole rack's power story "
    "is really the GPU story. Until the NVLink fabric fuses, these four can "
    "talk only to each other and their tray's Grace CPUs."
)

_CPU_DESC = (
    "The tray's two NVIDIA Grace CPUs — 72-core Arm processors, one per "
    "GB200 superchip. Grace is not the star here; it is the feeder. Each "
    "Grace connects to its two Blackwell GPUs over NVLink-C2C (a "
    "chip-to-chip link far faster than PCIe) and holds LPDDR5X memory the "
    "GPUs can reach directly, so data staging never bottlenecks on a "
    "traditional host bus. The tray boots like an ordinary Arm server "
    "before its GPUs wake."
)

_NIC_DESC = (
    "The tray's scale-out networking: NVIDIA ConnectX NICs and BlueField "
    "DPUs (data processing units — NICs with their own Arm cores that "
    "offload networking, storage, and security from the host). NVLink joins "
    "the 72 GPUs *inside* the rack; these ports join the rack to *other* "
    "racks and to storage over InfiniBand or Spectrum-X Ethernet at 400–800 "
    "Gb/s. Training at AI-factory scale uses both fabrics at once."
)


def _tray(idx: int, y0: float) -> list[RackRegion]:
    """One GB200 compute tray as a horizontal slice of the elevation."""
    s = f"t{idx}"
    tag = f"Tray {idx}"
    h = 12.0
    return [
        RackRegion(
            id=f"gpu-{s}", kind="gpu", label=f"4× Blackwell · {tag}",
            x=2, y=y0, w=36, h=h, description=_GPU_DESC,
        ),
        RackRegion(
            id=f"cpu-{s}", kind="compute", label="2× Grace",
            x=40, y=y0, w=24, h=h, description=_CPU_DESC,
        ),
        RackRegion(
            id=f"nic-{s}", kind="network", label="NIC / DPU",
            x=66, y=y0, w=28, h=h, description=_NIC_DESC,
        ),
    ]


ANATOMY = RackAnatomy(
    id="xe9712",
    name="PowerEdge XE9712 · GB200 NVL72 rack",
    vendor="Dell Technologies + NVIDIA",
    form_factor="Integrated liquid-cooled rack — 18 compute + 9 NVLink switch trays",
    generation="Dell AI Factory with NVIDIA (Grace Blackwell)",
    year=2025,
    width=100,
    height=86,
    overview=(
        "The PowerEdge XE9712 is Dell's rack-scale AI system built around "
        "NVIDIA GB200 NVL72. It is sold and shipped as one integrated, "
        "liquid-cooled rack: 18 compute trays carrying 36 NVIDIA Grace CPUs "
        "and 72 Blackwell GPUs, joined through 9 NVLink switch trays and a "
        "rear copper cable cartridge into a single NVLink domain — software "
        "sees something close to one enormous GPU with 13.5 TB of pooled "
        "HBM3e, which is what makes real-time trillion-parameter inference "
        "and large-model training practical. Trays draw DC from a shared "
        "busbar fed by power shelves, and nearly all of the rack's roughly "
        "120 kW leaves through the liquid loop: an in-rack CDU pumps coolant "
        "through manifolds to cold plates on every chip. This elevation "
        "shows four of the 18 compute trays and two of the 9 switch trays; "
        "the layout is a stylized mental model, not a rack-accurate drawing."
    ),
    regions=[
        RackRegion(
            id="power-shelf-a", kind="power", label="Power shelf A",
            x=2, y=1, w=70, h=6,
            description=(
                "One of the rack's power shelves: banks of hot-swappable "
                "rectifiers that convert facility AC into direct current and "
                "feed the busbar — the copper spine running down the back of "
                "the rack that every tray clips onto. Centralizing "
                "rectification in shelves instead of giving each tray its "
                "own power supplies is how a single rack distributes more "
                "than 100 kW efficiently; lose one rectifier and the rest "
                "carry the load."
            ),
        ),
        RackRegion(
            id="mgmt", kind="management", label="Rack mgmt",
            x=74, y=1, w=20, h=6,
            description=(
                "The rack management switch and the management plane behind "
                "it. Every tray's BMC (baseboard management controller — the "
                "role iDRAC plays in a PowerEdge server) reports here, and "
                "Dell OpenManage or NVIDIA Mission Control uses this path to "
                "sequence power-on, watch cold-plate temperatures and "
                "coolant flow, and enforce the interlock that keeps GPUs off "
                "until the liquid loop is proven."
            ),
        ),
        *_tray(1, 9),
        *_tray(2, 23),
        RackRegion(
            id="nvswitch-a", kind="nvswitch", label="NVLink switch trays 1–5",
            x=2, y=38, w=45, h=8,
            description=(
                "NVLink switch trays — the scale-up fabric. Each tray "
                "carries NVSwitch ASICs that cross-connect every GPU in the "
                "rack; through the rear cable cartridge, each of the 72 GPUs "
                "gets 1.8 TB/s into the fabric. The switch trays sit at "
                "mid-rack so the copper runs to the farthest compute tray "
                "stay short enough to skip optics entirely — copper is "
                "cheaper, cooler, and more reliable at this scale."
            ),
        ),
        RackRegion(
            id="nvswitch-b", kind="nvswitch", label="NVLink switch trays 6–9",
            x=49, y=38, w=45, h=8,
            description=(
                "The rest of the NVLink switch complement (a real rack has "
                "nine trays). Together they form one non-blocking all-to-all "
                "fabric of roughly 130 TB/s — the thing that turns 72 "
                "individual GPUs into a single NVL72 domain. It is the same "
                "architectural move as PowerMax's InfiniBand Dynamic Fabric "
                "between directors, but roughly an order of magnitude faster, "
                "because model training moves tensors, not blocks."
            ),
        ),
        *_tray(3, 48),
        *_tray(4, 62),
        RackRegion(
            id="power-shelf-b", kind="power", label="Power shelf B",
            x=2, y=77, w=45, h=6,
            description=(
                "The second power shelf group. Shelves are fed from separate "
                "facility feeds so a single circuit failure derates the rack "
                "instead of dropping it; the busbar simply draws more from "
                "the surviving shelves. At around 120 kW per rack, power "
                "engineering — feeds, shelves, busbar — is as much a part of "
                "the product as the silicon."
            ),
        ),
        RackRegion(
            id="cdu", kind="cooling", label="CDU (liquid cooling)",
            x=49, y=77, w=45, h=6,
            description=(
                "The in-rack coolant distribution unit (CDU) — Dell's "
                "PowerCool RCDU family. Pumps circulate treated coolant "
                "through the manifolds and cold plates, and a heat exchanger "
                "hands the heat to the facility water loop without ever "
                "mixing the two. It primes and leak-checks the loop before "
                "any GPU is allowed on, and at steady state it removes on "
                "the order of 100+ kW — about ninety percent of the rack's "
                "heat — through water rather than air."
            ),
        ),
        RackRegion(
            id="manifold", kind="cooling", label="Manifolds",
            x=96, y=1, w=4, h=82,
            description=(
                "The vertical supply and return manifolds: pipes running the "
                "height of the rack that carry coolant from the CDU to every "
                "tray and back. Each tray taps in through blind-mate "
                "quick-disconnect fittings, so a tray can be pulled for "
                "service without draining the loop — the liquid-cooling "
                "equivalent of hot-swap."
            ),
        ),
    ],
    stats=[
        Stat(label="GPUs per rack", value="72 NVIDIA Blackwell (one NVLink domain)"),
        Stat(label="CPUs per rack", value="36 NVIDIA Grace (72-core Arm)"),
        Stat(label="Compute trays", value="18 (2× GB200 superchip each)"),
        Stat(label="NVLink switch trays", value="9 — 1.8 TB/s per GPU, ~130 TB/s total"),
        Stat(label="Pooled GPU memory", value="13.5 TB HBM3e across the domain"),
        Stat(label="Power", value="~120 kW per rack via shelves + DC busbar"),
        Stat(label="Cooling", value="Direct liquid — in-rack CDU + manifolds"),
        Stat(label="Scale-out", value="InfiniBand or Spectrum-X Ethernet, rack to rack"),
    ],
    photo=RACK_ILLO,
    sources=[
        SourceLink(
            label="Dell PowerEdge XE9712 (Dell AI Factory with NVIDIA)",
            url="https://www.dell.com/en-us/shop/ipovw/poweredge-xe9712",
        ),
        SourceLink(
            label="Dell announcement — AI Factory racks, IR7000 and PowerCool (OCP 2024)",
            url="https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2024~10~dell-servers-storage-at-ocp.htm",
        ),
        SourceLink(
            label="NVIDIA GB200 NVL72 product page",
            url="https://www.nvidia.com/en-us/data-center/gb200-nvl72/",
        ),
        SourceLink(
            label="Dell Integrated Rack Scalable Systems (IRSS)",
            url="https://www.dell.com/en-us/shop/storage-servers-and-networking-for-business/sf/integrated-rack-scalable-systems",
        ),
    ],
)
