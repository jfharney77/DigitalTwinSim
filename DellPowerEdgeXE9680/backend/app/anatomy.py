"""Server-anatomy data: a PowerEdge XE9680 (8-GPU HGX) chassis, annotated.

Like the other twins, the layout is *data*, not code: regions placed in a
normalized coordinate space the frontend renders as SVG. Geometry is
stylized — favor a correct mental model over exact chassis millimetres
(project scope guardrail).

The view is a top-down look into the 6U chassis, front of the server at the
left edge. Air is the plot: it enters through the front NVMe bay, is driven
by the fan wall, and washes over the HGX baseboard — the field of eight SXM
GPUs plus the NVSwitch strip that fuses them — before leaving past the host
board, NICs, and PSUs at the rear. Two deliberate geometry lessons, both
pinned by tests: the GPU field is the biggest thing in the drawing (this
chassis exists to carry that baseboard), and the eight scale-out NICs at
the rear pair one-to-one with the eight GPUs — the wiring diagram of "one
GPU, one NIC" drawn as matching rows.
"""

from __future__ import annotations

from .leveling import L
from .models import Photo, ServerAnatomy, ServerRegion, SourceLink, Stat

# The only shipped visual is a self-contained schematic drawn for this
# project — not a Dell or NVIDIA product image — with an honest credit line.
CHASSIS_ILLO = Photo(
    url="/xe9680-chassis.svg",
    caption=(
        "A PowerEdge XE9680 chassis, schematically: front NVMe bay and fan "
        "wall, the HGX baseboard with eight SXM GPUs fused by the NVSwitch "
        "strip, and the rear I/O — two Xeons, eight per-GPU NICs, and the "
        "PSU bank."
    ),
    credit="Schematic illustration by this project — not a Dell product image",
)


_GPU_DESC = (
    "One of the eight SXM GPU modules on the HGX baseboard. SXM is the "
    "socketed, high-power form factor — no card edge, no power cable; the "
    "module bolts to the baseboard under a tall heatsink and can draw on "
    "the order of 700 W, several times what a PCIe card is allowed. Each "
    "GPU carries its own stacks of HBM (high-bandwidth memory) and its own "
    "NVLink ports into the NVSwitch strip; each is also paired with its "
    "own 400 GbE NIC at the rear of the chassis, its private on-ramp to "
    "the cluster fabric."
)

_NIC_DESC = (
    "One of the eight scale-out NICs — a ConnectX-class 400 GbE adapter "
    "dedicated to exactly one GPU. The pairing is the machine's design "
    "signature: inside the box, GPUs converse over NVLink; past the box, "
    "each GPU does RDMA (remote direct memory access — the NIC moves data "
    "without involving the host CPU) through its own port, never queueing "
    "behind its siblings. Eight NICs at 400 Gb/s is ~3.6 Tb/s of network "
    "per server — the figure xAI's Colossus reported per HGX box."
)


def _gpu(idx: int) -> ServerRegion:
    col = (idx - 1) % 4
    row = (idx - 1) // 4
    return ServerRegion(
        id=f"gpu-g{idx}", kind="gpu", label=f"SXM GPU {idx}",
        x=20 + 10 * col, y=1 + 28 * row, w=9, h=26,
        description=_GPU_DESC,
    )


def _nic(idx: int) -> ServerRegion:
    return ServerRegion(
        id=f"nic-g{idx}", kind="network", label=f"NIC · GPU {idx}",
        x=84, y=1 + 7 * (idx - 1), w=15, h=6,
        description=_NIC_DESC,
    )


ANATOMY = ServerAnatomy(
    id="xe9680",
    name="PowerEdge XE9680 · 8-GPU HGX server",
    vendor="Dell Technologies + NVIDIA",
    form_factor="6U air-cooled server (XE9680L: 4U direct liquid-cooled)",
    generation="Dell AI Factory with NVIDIA (HGX H100/H200/B200)",
    year=2023,
    width=100,
    height=56,
    overview=L(
        novice=(
            "This is Dell's workhorse AI server: one big box, eight graphics "
            "processors — the chips that do the mathematics behind modern AI — "
            "and everything needed to keep them fed, cooled, and connected. "
            "The eight chips sit together on one large board and are wired to "
            "each other so tightly that software can treat them as one large "
            "processor. But that tight wiring ends at the edge of the box: to "
            "work with the GPUs in the *next* box, each chip has its own "
            "network cable — eight cables per server, one per chip. That is "
            "the whole trick of building giant AI computers out of this "
            "machine: the box is ordinary enough to install by the thousand, "
            "and the network does the rest. xAI's Colossus supercomputer was "
            "first built from exactly this kind of server — one hundred "
            "thousand GPUs, eight at a time."
        ),
        plain=(
            "The XE9680 is Dell's 8-GPU HGX server: a 6U box carrying one "
            "NVIDIA HGX baseboard (eight SXM GPUs fused by NVSwitch chips "
            "into a single NVLink domain), two Xeon hosts to feed it, a "
            "front NVMe bay, and eight 400 GbE NICs — one per GPU. The "
            "NVLink domain stops at the chassis wall; everything past eight "
            "GPUs rides the data-center fabric through those per-GPU NICs. "
            "It is the counterpoint to the XE9712 rack twin: a smaller "
            "domain in exchange for a box any data center can rack in "
            "parallel, which is how Colossus reached 100,000 GPUs in 122 "
            "days."
        ),
        standard=(
            "The PowerEdge XE9680 is Dell's flagship 8-GPU server and the "
            "machine xAI's Colossus was first built from. Inside the 6U "
            "chassis, one NVIDIA HGX baseboard carries eight SXM GPUs "
            "(H100, H200, or Blackwell-generation) fused by an NVSwitch "
            "complex into a single NVLink domain — software addresses "
            "something close to one large accelerator. Around that board "
            "sits an ordinary server: two Xeon hosts, 32 DIMMs, a front "
            "NVMe bay, six PSUs, and a fan wall that holds ~700 W devices "
            "at temperature with air alone (the XE9680L variant moves this "
            "line to direct liquid cooling and packs 64 GPUs in a rack). "
            "The geometry of this drawing is the argument: the GPU field "
            "dominates the chassis, and the eight NICs at the rear pair "
            "one-to-one with the eight GPUs, because the NVLink domain "
            "ends at the chassis wall and every GPU needs its own on-ramp "
            "to the fabric that continues past it."
        ),
        technical=(
            "8-GPU HGX server: one baseboard, 8× SXM fused by NVSwitch "
            "into one NVLink domain (900 GB/s per GPU), dual-Xeon host, "
            "32 DIMMs, front NVMe, 6 PSUs, air-cooled at 6U (XE9680L: 4U "
            "DLC). Phase order power → post → gpuinit → fuse → fabric → "
            "ready. Asserted: the fuse is atomic with a hard ceiling of 8 "
            "(gpusInDomain ∈ {0, 8}, never more); NICs pair 1:1 with GPUs "
            "and nicsUp reaches 8 only in the fabric phase; GPU init holds "
            "max dwell; fans are lit on every step where GPUs draw power. "
            "Geometry pinned: GPU area dominates, NIC:GPU pairing is "
            "drawn."
        ),
        expert=(
            "HGX box: 8× SXM + NVSwitch (one domain, 900 GB/s/GPU), dual "
            "Xeon, 6U air (L: 4U DLC). Atomic fuse, ceiling 8. 1:1 "
            "NIC:GPU, ~3.6 Tb/s/server. gpuinit holds max dwell; fans "
            "track GPU power."
        ),
    ),
    regions=[
        ServerRegion(
            id="nvme-bay", kind="storage", label="NVMe bay",
            x=0, y=0, w=8, h=56,
            description=(
                "The front drive bay: up to eight hot-swappable NVMe SSDs. "
                "Training data stages here on its way to the GPUs — checkpoints "
                "land here too, and at these GPU speeds a slow checkpoint is "
                "idle silicon, so the bay is all NVMe. In cluster deployments "
                "the heavy data lives on external parallel storage (the "
                "Exascale twin) and this bay is cache and boot; a BOSS-N1 "
                "module carries the OS so no data slot is wasted on it."
            ),
        ),
        ServerRegion(
            id="fan-bank-a", kind="cooling", label="Fan wall A",
            x=9, y=0, w=10, h=27,
            description=(
                "Half of the fan wall: high-static-pressure counter-rotating "
                "fans that pull air through the front bay and drive it over "
                "the HGX baseboard's heatsinks. This is the machine's answer "
                "to the question the XE9712 answers with building water — "
                "eight ~700 W GPUs held at temperature by airflow alone, at "
                "the cost of a 6U chassis, serious acoustics, and a hot "
                "aisle that can swallow ~11 kW per box."
            ),
        ),
        ServerRegion(
            id="fan-bank-b", kind="cooling", label="Fan wall B",
            x=9, y=29, w=10, h=27,
            description=(
                "The other half of the fan wall. The banks are redundant: "
                "lose a fan and the rest spin harder while iDRAC flags the "
                "swap. Watch these regions during playback — they light the "
                "moment the GPUs first draw power and never go dark again, "
                "because in an air-cooled server cooling is not a phase of "
                "bring-up, it is a condition of staying up."
            ),
        ),
        *[_gpu(i) for i in range(1, 9)],
        ServerRegion(
            id="nvswitch", kind="nvswitch", label="NVSwitch",
            x=60, y=1, w=6, h=54,
            description=(
                "The NVSwitch complex on the HGX baseboard — the switch "
                "silicon that cross-connects all eight GPUs so any one can "
                "read or write any other's HBM at 900 GB/s. It is the same "
                "architectural part the XE9712 rack twin fills nine switch "
                "trays with; here it is a strip of chips on one board, which "
                "is why this server's fuse takes seconds, not minutes of "
                "cable training — and why the domain it makes can never grow "
                "past the board's edge."
            ),
        ),
        ServerRegion(
            id="host-cpus", kind="compute", label="2× Xeon + 32 DIMM",
            x=68, y=1, w=14, h=34,
            description=(
                "The x86 host: two Intel Xeon processors and 32 DDR5 DIMMs. "
                "In this machine the host is the feeder, not the star — it "
                "boots the OS, stages training data from storage into GPU "
                "memory, and launches kernels; the mathematics happens on "
                "the other side of the chassis. Its PCIe Gen5 lanes fan out "
                "to the GPUs, the NICs, and the NVMe bay, and everything "
                "the accelerators consume passes through here first."
            ),
        ),
        ServerRegion(
            id="idrac", kind="management", label="iDRAC",
            x=68, y=37, w=14, h=8,
            description=(
                "The iDRAC9 — the server's BMC (baseboard management "
                "controller), a small always-on computer with its own "
                "network port; this repo has a whole twin about it. It "
                "wakes on standby power before anything else, sequences the "
                "power-on you can play on the first tab, watches every "
                "temperature in the box, and is the fleet's handle on this "
                "server: at Colossus scale nobody walks to a machine, so "
                "12,500 iDRACs are how the operators see 12,500 boxes."
            ),
        ),
        ServerRegion(
            id="psu-bank", kind="power", label="6× PSU",
            x=68, y=47, w=14, h=8,
            description=(
                "The power supply bank: six hot-swappable supplies where an "
                "ordinary server carries two, feeding on the order of 11 kW "
                "at full load. The count buys redundancy as well as "
                "capacity — supplies can fail or be swapped with the box "
                "under load. One 6U server drawing what a whole rack of "
                "ordinary servers draws is the arithmetic behind every "
                "AI-datacenter power story."
            ),
        ),
        *[_nic(i) for i in range(1, 9)],
    ],
    stats=[
        Stat(label="GPUs per server", value="8× SXM on one HGX baseboard, one NVLink domain"),
        Stat(label="NVLink", value="NVSwitch complex — 900 GB/s per GPU, in-box only"),
        Stat(label="Scale-out", value="8× 400 GbE NICs — one per GPU, ~3.6 Tb/s per server"),
        Stat(label="Host", value="2× Intel Xeon, 32× DDR5 DIMM"),
        Stat(label="Storage", value="Front NVMe bay + BOSS-N1 boot"),
        Stat(label="Power", value="~11 kW at full load, 6× hot-swap PSUs"),
        Stat(label="Cooling", value="Air at 6U; XE9680L variant is 4U direct liquid"),
        Stat(label="At Colossus", value="8 servers × 8 GPUs = 64 GPUs per rack, ~1,500 racks"),
    ],
    photo=CHASSIS_ILLO,
    sources=[
        SourceLink(
            label="Dell PowerEdge XE9680 product page",
            url="https://www.dell.com/en-us/shop/dell-poweredge-servers/poweredge-xe9680-rack-server/spd/poweredge-xe9680",
        ),
        SourceLink(
            label="Dell PowerEdge XE9680L (direct liquid-cooled) announcement",
            url="https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2024~05~20240520-dell-technologies-accelerates-ai-innovation.htm",
        ),
        SourceLink(
            label="NVIDIA HGX platform page",
            url="https://www.nvidia.com/en-us/data-center/hgx/",
        ),
        SourceLink(
            label="DCD — Dell and Supermicro to provide servers for xAI's Colossus",
            url="https://www.datacenterdynamics.com/en/news/dell-and-super-micro-computer-to-provide-server-racks-for-xai-supercomputer/",
        ),
    ],
)
