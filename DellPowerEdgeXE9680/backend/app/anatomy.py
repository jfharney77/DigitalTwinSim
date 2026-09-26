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
    "module bolts to the baseboard under a tall heatsink and can draw up "
    "to 700 W on H100 and H200 boards, about double the PCIe-card version "
    "of the same GPU. Each "
    "GPU carries its own stacks of HBM (high-bandwidth memory) and its own "
    "NVLink ports into the NVSwitch strip; each is also paired with its "
    "own 400 GbE NIC at the rear of the chassis, its private on-ramp to "
    "the cluster fabric."
)

_NIC_DESC = (
    "One of the eight scale-out NICs — a 400 GbE adapter (ConnectX-7 or a "
    "BlueField-3 SuperNIC) "
    "dedicated to exactly one GPU. The pairing is the machine's design "
    "signature: inside the box, GPUs converse over NVLink; past the box, "
    "each GPU does RDMA (remote direct memory access — the NIC moves data "
    "without involving the host CPU) through its own port, never queueing "
    "behind its siblings. Eight NICs at 400 Gb/s is 3.2 Tb/s of GPU "
    "networking per server; the roughly 3.6 Tb/s reported from xAI's "
    "Colossus counts a ninth 400 GbE link for the host."
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
            "work with the GPUs in the next box, each chip has its own "
            "network cable — eight cables per server, one per chip. That is "
            "the whole trick of building giant AI computers out of this "
            "machine: the box is ordinary enough to install by the thousand, "
            "and the network does the rest. xAI's Colossus supercomputer was "
            "first built from this kind of server, supplied by Dell and "
            "Supermicro — a reported one hundred thousand GPUs, eight at "
            "a time."
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
            "parallel, which is how xAI's Colossus (8-GPU servers from Dell "
            "and Supermicro) was reported to reach 100,000 GPUs in 122 "
            "days."
        ),
        standard=(
            "The PowerEdge XE9680 is Dell's flagship 8-GPU server, the class "
            "of machine xAI's Colossus was first built from (Dell and "
            "Supermicro each supplied racks). Inside the 6U "
            "chassis, one NVIDIA HGX baseboard carries eight SXM GPUs "
            "(H100 or H200; Blackwell B200 in the liquid-cooled XE9680L) "
            "fused by an NVSwitch "
            "complex into a single NVLink domain — software addresses "
            "something close to one large accelerator. Around that board "
            "sits an ordinary server: two Xeon hosts, 32 DIMMs, a front "
            "NVMe bay, six PSUs, and a fan wall that holds ~700 W devices "
            "at temperature with air alone (the 4U XE9680L variant moves "
            "this line to direct liquid cooling for denser racks). "
            "The geometry of this drawing is the argument: the GPU field "
            "dominates the chassis, and the eight NICs at the rear pair "
            "one-to-one with the eight GPUs, because the NVLink domain "
            "ends at the chassis wall and every GPU needs its own on-ramp "
            "to the fabric that continues past it."
        ),
        technical=(
            "8-GPU HGX server: one baseboard, 8× SXM fused by NVSwitch "
            "into one NVLink domain (900 GB/s per GPU on H100/H200), dual-Xeon host, "
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
            "HGX box: 8× SXM + NVSwitch (one domain, 900 GB/s/GPU on H100/H200), dual "
            "Xeon, 6U air (L: 4U DLC). Atomic fuse, ceiling 8. 1:1 "
            "NIC:GPU, 8× 400 GbE = 3.2 Tb/s/server. gpuinit holds max dwell; fans "
            "track GPU power."
        ),
    ),
    regions=[
        ServerRegion(
            id="nvme-bay", kind="storage", label="NVMe bay",
            x=0, y=0, w=8, h=56,
            description=(
                "The front drive bay: up to eight hot-swappable 2.5-inch NVMe "
                "SSDs (or sixteen E3.S drives). "
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
                "aisle that can swallow on the order of 11 kW per box "
                "(illustrative)."
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
                "read or write any other's HBM at 900 GB/s on H100 and H200 "
                "boards (1.8 TB/s on Blackwell). It is the same "
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
                "The x86 host: two 4th- or 5th-generation Intel Xeon Scalable "
                "processors and 32 DDR5 DIMM slots (up to 4 TB). "
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
                "server: at the scale of a 100,000-GPU cluster nobody walks "
                "to a machine, so roughly 12,500 management controllers "
                "are how the operators see roughly 12,500 boxes."
            ),
        ),
        ServerRegion(
            id="psu-bank", kind="power", label="6× PSU",
            x=68, y=47, w=14, h=8,
            description=(
                "The power supply bank: six hot-swappable 2,800 W Titanium "
                "supplies where an ordinary server carries two, feeding on "
                "the order of 11 kW at full load (illustrative). The count buys redundancy as well as "
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
        Stat(label="NVLink", value="NVSwitch complex — 900 GB/s per GPU (H100/H200), in-box only"),
        Stat(label="Scale-out", value="8× 400 GbE NICs — one per GPU, 3.2 Tb/s per server"),
        Stat(label="Host", value="2× Intel Xeon Scalable (4th/5th Gen), 32× DDR5 DIMM, up to 4 TB"),
        Stat(label="Storage", value="8× 2.5-inch NVMe or 16× E3.S + BOSS-N1 boot"),
        Stat(label="Power", value="6× 2,800 W Titanium hot-swap PSUs; ~11 kW full load (illustrative)"),
        Stat(label="Cooling", value="Air at 6U; XE9680L variant is 4U direct liquid"),
        Stat(label="At Colossus (reported)", value="8 servers × 8 GPUs = 64 GPUs per liquid-cooled rack, ~1,500 racks, Dell + Supermicro"),
    ],
    photo=CHASSIS_ILLO,
    sources=[
        SourceLink(
            label="Dell PowerEdge XE9680 product page",
            url="https://www.dell.com/en-us/shop/dell-poweredge-servers/poweredge-xe9680-rack-server/spd/poweredge-xe9680",
        ),
        SourceLink(
            label="Dell PowerEdge XE9680L announcement (May 20, 2024)",
            url="https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2024~05~20240520-dell-technologies-expands-dell-ai-factory-with-nvidia-to-turbocharge-ai-adoption.htm",
        ),
        SourceLink(
            label="Dell PowerEdge XE9680L spec sheet (4U, HGX B200/H200, IR5000 rack)",
            url="https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/poweredge-xe9680l-spec-sheet.pdf",
        ),
        SourceLink(
            label="Dell blog — integrated rack solutions (IR5000: 72 to 96 GPUs per rack)",
            url="https://www.dell.com/en-us/blog/accelerating-ai-innovation-with-new-servers-and-racksolutions/",
        ),
        SourceLink(
            label="NVIDIA HGX platform page (HGX B200: 1.4 TB, 1.8 TB/s NVLink)",
            url="https://www.nvidia.com/en-us/data-center/hgx/",
        ),
        SourceLink(
            label="NVIDIA H100 page (SXM: 80 GB, 900 GB/s NVLink, up to 700 W)",
            url="https://www.nvidia.com/en-us/data-center/h100/",
        ),
        SourceLink(
            label="NVIDIA newsroom — Spectrum-X at xAI Colossus (122 days, 100,000 GPUs, BlueField-3 SuperNICs)",
            url="https://nvidianews.nvidia.com/news/spectrum-x-ethernet-networking-xai-colossus",
        ),
        SourceLink(
            label="ServeTheHome — inside the xAI Colossus cluster (Supermicro racks, nine 400 GbE links per server)",
            url="https://www.servethehome.com/inside-100000-nvidia-gpu-xai-colossus-cluster-supermicro-helped-build-for-elon-musk/",
        ),
        SourceLink(
            label="DCD — Dell and Supermicro to provide servers for xAI's Colossus",
            url="https://www.datacenterdynamics.com/en/news/dell-and-super-micro-computer-to-provide-server-racks-for-xai-supercomputer/",
        ),
    ],
)


# The Power-on page's landing prose. It lives here, beside the anatomy
# overview, so the first paragraph a reader meets is leveled by the same
# mechanism as everything else — the frontend renders whatever it is sent.
POWERON_INTRO_TITLE = L(
    novice="What happens inside when this AI server is switched on",
    plain="What happens when an eight-GPU AI server powers on",
    standard="What happens when an 8-GPU HGX server powers on",
    technical="XE9680 power-on: host, GPU init, the fuse, then the fabric",
    expert="XE9680 power-on trace",
)

POWERON_INTRO = L(
    novice=(
        "Switch this machine on and the ordinary computer inside it starts "
        "first: for all its size, it is still a server, and it boots like "
        "one. Then eight AI chips — bolted onto one shared circuit board — "
        "wake up, and the fans speed up to carry away the heat they make. A "
        "set of switch chips on that board wires all eight together in a "
        "single step, so software can work with them as if they were one "
        "very large chip. That wiring stops at the metal wall of the box. To "
        "reach the chips in the next box, eight network cards at the back — "
        "one for each chip — join the data-center network. Play the trace "
        "and watch each stage light up the part of the machine it runs on."
    ),
    plain=(
        "The XE9680 is Dell's eight-GPU AI server: eight accelerators on one "
        "shared board, in a box that fits a standard rack. The host computer "
        "boots first — a GPU server is still a server — then the eight "
        "accelerators wake and the fans ramp to hold them on air. Switch "
        "chips on the board fuse the eight into one NVLink domain, the fast "
        "private network they share, and there it stops: the chassis wall is "
        "the boundary. Then eight network cards, one per GPU, join the "
        "fabric — the data-center network that scales past this box. Play "
        "the trace and watch each stage light up the hardware it runs on."
    ),
    standard=(
        "The XE9680 is the class of machine xAI's Colossus was first built "
        "from, with servers from Dell and Supermicro: eight SXM GPUs on one "
        "HGX baseboard, in a box that fits a standard rack. The host boots "
        "first — a GPU server is still a server — then the eight "
        "accelerators wake and the fans ramp to hold them on air. The "
        "NVSwitch complex fuses the eight into one NVLink domain, "
        "atomically, and there the domain stops: the chassis wall is the "
        "boundary. Then eight network cards (NICs), one per GPU, join the "
        "fabric, the data-center network that scales past it. Play the trace "
        "and watch each stage light up the hardware it runs on."
    ),
    technical=(
        "Power-on of a 6U HGX server: PSUs energize, the dual-Xeon host "
        "POSTs, eight SXM GPUs initialize (HBM training holds the longest "
        "dwell), the NVSwitch complex fuses them into one NVLink domain "
        "atomically — gpusInDomain goes 0 to 8, never partial and never "
        "above 8 — and eight 400 GbE NICs then train onto the fabric, 1:1 "
        "with the GPUs. Play the trace and watch each phase light its "
        "regions."
    ),
    expert=(
        "6U HGX bring-up: power, POST, gpuinit, atomic fuse (0 to 8, ceiling "
        "8), then 8× 400 GbE up 1:1 with the GPUs. The domain ends at the "
        "sheet metal."
    ),
)
