"""Die-anatomy data: annotated floorplans of real GPUs.

Like profiles.py, new dies are data, not code. Each ``DieAnatomy`` describes
what a real GPU looks like *inside* — the major blocks (GPC/shader-engine
clusters, L2/Infinity Cache, memory PHYs, NVLink, media engines, ...) placed
in a normalized coordinate space the frontend renders as SVG.

Geometry is stylized, traced from the vendors' own whitepaper diagrams and
published die shots (see each entry's ``sources``). Per the project's scope
guardrails: favor a correct mental model over exact mm² placement.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .leveling import L
from .models import CamelModel

RegionKind = Literal[
    "compute",  # GPC / shader engine (SMs or CUs live here)
    "l2",       # on-die L2 / last-level cache
    "mem",      # memory controller + PHY (HBM / GDDR)
    "nvlink",   # die-to-die / GPU-to-GPU links
    "io",       # PCIe, display, host interface
    "media",    # NVENC / NVDEC / media engines
    "cache",    # cache chiplet (e.g. AMD MCD Infinity Cache)
    "fabric",   # on-package interconnect (e.g. Infinity Fanout)
]


class Photo(CamelModel):
    """A real photograph of the part (hotlinked from Wikimedia Commons).

    All photos are freely licensed (CC0 / CC BY / CC BY-SA); ``credit``
    carries the attribution the license requires and the UI must show it.
    """

    url: str
    caption: str
    credit: str


class DieRegion(CamelModel):
    id: str
    kind: RegionKind
    label: str
    x: float
    y: float
    w: float
    h: float
    description: str
    photo: Photo | None = None


class SourceLink(CamelModel):
    label: str
    url: str


class Stat(CamelModel):
    label: str
    value: str


class DieAnatomy(CamelModel):
    """One real GPU die, annotated. ``width``/``height`` set the viewBox."""

    id: str
    name: str
    vendor: str
    architecture: str
    process: str
    die_size: str
    transistors: str
    year: int
    width: float
    height: float
    regions: list[DieRegion]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


def _gpc_row(prefix: str, count: int, x0: float, x1: float, y: float,
             h: float, label: str, desc: str, gap: float = 0.8,
             photo: Photo | None = None) -> list[DieRegion]:
    """Evenly place ``count`` compute clusters between x0 and x1."""
    w = (x1 - x0 - gap * (count - 1)) / count
    return [
        DieRegion(
            id=f"{prefix}-{i}",
            kind="compute",
            label=label,
            x=x0 + i * (w + gap),
            y=y,
            w=w,
            h=h,
            description=desc,
            photo=photo,
        )
        for i in range(count)
    ]


# --- Part photographs (Wikimedia Commons, freely licensed) -------------------

_WM = "https://upload.wikimedia.org/wikipedia/commons/thumb"

P_GP100_PKG = Photo(
    url=f"{_WM}/4/4c/Nvidia%4016nm%40Pascal%40GP100%40Tesla_P100%40T_Taiwan_1912A1_PN9G70.S6W_GP100-897-A1_DSCx01%40SWIR.jpg/960px-Nvidia%4016nm%40Pascal%40GP100%40Tesla_P100%40T_Taiwan_1912A1_PN9G70.S6W_GP100-897-A1_DSCx01%40SWIR.jpg",
    caption=("HBM stacks flanking a GPU die on its silicon interposer — a "
             "Pascal GP100 package photographed in infrared."),
    credit="Fritzchens Fritz · CC0 · Wikimedia Commons",
)

P_GA100_DIE = Photo(
    url=f"{_WM}/b/be/GA100_Die_Shot.jpg/960px-GA100_Die_Shot.jpg",
    caption=("The actual GA100 silicon: GPC columns of SMs around the split "
             "L2, HBM PHYs on the flanks."),
    credit="CC BY 3.0 · Wikimedia Commons",
)

P_AD102_DIE = Photo(
    url=f"{_WM}/d/d4/Nvidia%405nm%40AdaLovelace%40AD102%40GeForce_RTX_4090%40S_TW_2324A1_U2F028.MOW_AD102-301-A1_DSCx3%40VIS.jpg/960px-Nvidia%405nm%40AdaLovelace%40AD102%40GeForce_RTX_4090%40S_TW_2324A1_U2F028.MOW_AD102-301-A1_DSCx3%40VIS.jpg",
    caption="The AD102 die of an RTX 4090, photographed on its board.",
    credit="Fritzchens Fritz · CC0 · Wikimedia Commons",
)

P_NAVI22_DIE = Photo(
    url=f"{_WM}/b/bc/AMD%407nm%40RDNA_2nd_gen%40Navi22%40Radeon_RX_6700_XT%40215-0932396%40_DSCx04%40SWIR.jpg/960px-AMD%407nm%40RDNA_2nd_gen%40Navi22%40Radeon_RX_6700_XT%40215-0932396%40_DSCx04%40SWIR.jpg",
    caption=("RDNA shader engines under infrared — the Navi 22 die (RDNA 2), "
             "Navi 31's monolithic cousin; no free Navi 31 die shot exists yet."),
    credit="Fritzchens Fritz · CC0 · Wikimedia Commons",
)

P_RX7900_CARD = Photo(
    url=f"{_WM}/a/a8/Sapphire_AMD_Radeon_RX_7900_XTX.jpg/960px-Sapphire_AMD_Radeon_RX_7900_XTX.jpg",
    caption="A Radeon RX 7900 XTX — the Navi 31 package lives under this cooler.",
    credit="Geni · CC BY-SA 4.0 · Wikimedia Commons",
)

P_GDDR6_PCB = Photo(
    url="https://upload.wikimedia.org/wikipedia/commons/7/75/RTX_3060_12GB_GDDR6_with_GA104.png",
    caption=("GDDR6 memory chips ringing a GPU on its board (RTX 3060 shown) "
             "— unlike HBM, GDDR lives outside the package, so its PHYs sit "
             "on the die edges."),
    credit="Inobump · CC0 · Wikimedia Commons",
)

P_H100_CARD = Photo(
    url=f"{_WM}/a/a6/NVIDIA_H100_%28%E6%9E%81%E5%AE%A2%E6%B9%BEGeekerwan%29_018.png/960px-NVIDIA_H100_%28%E6%9E%81%E5%AE%A2%E6%B9%BEGeekerwan%29_018.png",
    caption="An H100 PCIe accelerator — the GH100 die sits under this shroud.",
    credit="Geekerwan · CC BY 3.0 · Wikimedia Commons",
)

P_NVLINK_CARDS = Photo(
    url=f"{_WM}/6/66/NVIDIA_H100_%28%E6%9E%81%E5%AE%A2%E6%B9%BEGeekerwan%29_022.png/960px-NVIDIA_H100_%28%E6%9E%81%E5%AE%A2%E6%B9%BEGeekerwan%29_022.png",
    caption=("The black NVLINK connector strips on top of stacked H100 cards "
             "— where the on-die NVLink ports surface for bridges."),
    credit="Geekerwan · CC BY 3.0 · Wikimedia Commons",
)

P_A100_CARD = Photo(
    url=f"{_WM}/3/3b/Nvidia_Tesla_A100.png/960px-Nvidia_Tesla_A100.png",
    caption="An NVIDIA A100 accelerator, home of the GA100 die.",
    credit="NVIDIA · CC BY-SA 4.0 · Wikimedia Commons",
)

P_GB200_BOARD = Photo(
    url=f"{_WM}/f/f3/AI%E5%8A%A9%E6%89%8B%E8%83%BD%E5%B8%AE%E6%88%91%E8%B6%85%E9%A2%91%EF%BC%9FCOMPUTEX_NV%E5%B1%95%E5%8C%BA%E4%BD%93%E9%AA%8C_%28%E6%9E%81%E5%AE%A2%E6%B9%BEGeekerwan%29_07.png/960px-AI%E5%8A%A9%E6%89%8B%E8%83%BD%E5%B8%AE%E6%88%91%E8%B6%85%E9%A2%91%EF%BC%9FCOMPUTEX_NV%E5%B1%95%E5%8C%BA%E4%BD%93%E9%AA%8C_%28%E6%9E%81%E5%AE%A2%E6%B9%BEGeekerwan%29_07.png",
    caption=("A bare GB200 board at COMPUTEX: two Blackwell GPU packages "
             "(each holding the dual dies + HBM3e) beside the Grace CPU."),
    credit="Geekerwan · CC BY 3.0 · Wikimedia Commons",
)


# spec_29: every unique region description is a module-level constant wrapped
# in L(...) — levels 1/3/5 authored; 2/4 resolve by the tie-break rule.
# Shared strings (the HBM/L2/GDDR blocks reused across call sites and dies)
# author once here and serve every site, because registration keys on the
# level-3 text.

_GPC_DESC_GH100 = L(
    novice=(
        "A Graphics Processing Cluster — one of the big repeated blocks of "
        "compute. Inside are 18 SMs (streaming multiprocessors, the GPU's "
        "independent processing engines). Each SM carries 128 ordinary "
        "arithmetic units for 32-bit numbers, 4 Tensor Cores — specialized "
        "units that multiply small matrices in one step, the workhorse of AI "
        "math — a 256 KB pool of fast local memory, and a dedicated engine "
        "for moving tensor data in the background."
    ),
    standard=(
        "Graphics Processing Cluster: 9 TPCs = 18 SMs. Each Hopper SM has 128 "
        "FP32 CUDA cores, 4 fourth-gen Tensor Cores, 256 KB L1/shared memory, "
        "and a Tensor Memory Accelerator (TMA)."
    ),
    expert=(
        "GPC: 9 TPC / 18 SM; per SM 128 FP32 lanes, 4× gen-4 TC, 256 KB "
        "L1/smem, TMA."
    ),
)

_IO_DESC_GH100 = L(
    novice=(
        "The chip's front door. PCIe is the plug-in connection that links the "
        "GPU to the host computer, and beside it sits the GigaThread Engine — "
        "the global scheduler that takes each program's blocks of work and "
        "hands them out to the compute clusters across the die."
    ),
    standard=(
        "Host interface (PCIe 5.0 x16) plus the GigaThread Engine, the global "
        "scheduler that distributes thread blocks to GPCs."
    ),
    expert="PCIe 5.0 x16 host link + GigaThread Engine (global block scheduler).",
)

_HBM3_DESC_GH100 = L(
    novice=(
        "A controller for one stack of HBM3 — High Bandwidth Memory, DRAM "
        "chips stacked vertically right beside the GPU and wired to it with "
        "over a thousand connections each. The PHY is the physical wiring "
        "interface. Six of these controllers ring the die (five switched on "
        "in the H100 product), together moving up to 3.35 terabytes every "
        "second."
    ),
    standard=(
        "HBM3 memory controller + PHY. One 1024-bit stack interface; GH100 "
        "has six (five enabled on H100 SXM), 3.35 TB/s total."
    ),
    expert="HBM3 ctrl+PHY, 1024-bit/stack; 6 on die, 5 enabled, 3.35 TB/s aggregate.",
)

_L2_DESC_GH100 = L(
    novice=(
        "Half of the chip's L2 cache — a 60 MB pool of very fast on-chip "
        "memory (50 MB switched on in the H100 product) that holds recently "
        "used data so the GPU doesn't have to go out to main memory for it. "
        "It is built in two halves so each half can sit physically close to "
        "the memory controllers it serves."
    ),
    standard=(
        "Half of the 60 MB L2 (50 MB enabled on H100). Physically split in "
        "two so each half sits close to the memory controllers it serves."
    ),
    expert="Half the 60 MB L2 (50 enabled); split for proximity to its memory controllers.",
)

_NVLINK_DESC_GH100 = L(
    novice=(
        "Eighteen NVLink ports — NVIDIA's dedicated chip-to-chip connection, "
        "much faster than the ordinary PCIe plug. Together they move 900 "
        "gigabytes per second, and they are how several H100s in one server "
        "talk to each other directly instead of routing through the host."
    ),
    standard=(
        "18 fourth-generation NVLink ports, 900 GB/s aggregate — how H100s "
        "in a DGX/HGX node talk to each other without going through PCIe."
    ),
    expert="18× NVLink 4, 900 GB/s aggregate; intra-node GPU mesh, PCIe bypassed.",
)

GH100 = DieAnatomy(
    id="gh100",
    name="H100 (GH100)",
    vendor="NVIDIA",
    architecture="Hopper",
    process="TSMC 4N",
    die_size="814 mm²",
    transistors="80 B",
    year=2022,
    width=100,
    height=64,
    overview=L(
        novice=(
            "A GPU is a chip built to do enormous numbers of simple "
            "calculations at the same time, which is what both graphics and "
            "modern AI need. This is a floorplan of one — a map of what sits "
            "where on the silicon. The repeated blocks filling most of the "
            "area are the arithmetic units, grouped into clusters. The band "
            "through the middle is cache: a small pool of very fast memory "
            "that holds data the chip is about to reuse. Around the edges are "
            "the connections to the chip's main memory, stacked vertically "
            "right next to it so the distance the data travels stays short. "
            "Along the bottom are the links used to join this chip to others, "
            "because the largest AI jobs need many of them working together."
        ),
        plain=(
            "NVIDIA's Hopper data-centre flagship. Most of the area is "
            "arithmetic, organized into eight clusters of streaming "
            "multiprocessors — 144 on the full die, 132 enabled on the H100 "
            "SXM part, because some are disabled to improve manufacturing "
            "yield. A split 60 MB cache runs down the middle, three stacks of "
            "high-bandwidth memory sit on each edge feeding a very wide bus "
            "at about 3.35 TB/s, and 18 NVLink ports along the bottom carry "
            "traffic to other GPUs."
        ),
        standard=(
            "NVIDIA's Hopper flagship. 8 GPCs (144 SMs on the full die; 132 "
            "enabled on H100 SXM) surround a split 60 MB L2, with three HBM3 "
            "stacks on each edge feeding a 6144-bit bus (~3.35 TB/s) and 18 "
            "NVLink 4 ports along the bottom for GPU-to-GPU traffic."
        ),
        technical=(
            "Hopper flagship: 8 GPCs, 144 SMs on the full die and 132 enabled "
            "on H100 SXM, around a split 60 MB L2. Three HBM3 stacks per edge "
            "on a 6144-bit bus at ~3.35 TB/s; 18 NVLink 4 ports along the "
            "bottom edge for scale-up traffic."
        ),
        expert=(
            "GH100: 8 GPCs / 144 SMs (132 on H100 SXM), split 60 MB L2, 6× "
            "HBM3 on a 6144-bit bus at ~3.35 TB/s, 18× NVLink 4."
        ),
    ),
    regions=[
        DieRegion(id="io", kind="io", label="PCIe Gen5 · GigaThread Engine",
                  x=2, y=2, w=96, h=5,
                  description=_IO_DESC_GH100),
        *[DieRegion(id=f"hbm-l{i}", kind="mem", label="HBM3",
                    x=2, y=8 + i * 16.8, w=7, h=15.3, photo=P_GP100_PKG,
                    description=_HBM3_DESC_GH100)
          for i in range(3)],
        *[DieRegion(id=f"hbm-r{i}", kind="mem", label="HBM3",
                    x=91, y=8 + i * 16.8, w=7, h=15.3, photo=P_GP100_PKG,
                    description=_HBM3_DESC_GH100)
          for i in range(3)],
        DieRegion(id="l2-a", kind="l2", label="L2 · 25 MB",
                  x=10, y=30, w=39, h=4.5,
                  description=_L2_DESC_GH100),
        DieRegion(id="l2-b", kind="l2", label="L2 · 25 MB",
                  x=51, y=30, w=39, h=4.5,
                  description=_L2_DESC_GH100),
        *_gpc_row("gpc-t", 4, 10, 90, 8, 21, "GPC · 18 SM", _GPC_DESC_GH100,
                  photo=P_GA100_DIE),
        *_gpc_row("gpc-b", 4, 10, 90, 35.5, 21, "GPC · 18 SM", _GPC_DESC_GH100,
                  photo=P_GA100_DIE),
        DieRegion(id="nvlink", kind="nvlink", label="NVLink 4 × 18",
                  x=2, y=58, w=96, h=4, photo=P_NVLINK_CARDS,
                  description=_NVLINK_DESC_GH100),
    ],
    stats=[
        Stat(label="SMs (full / enabled)", value="144 / 132"),
        Stat(label="FP32 cores", value="16 896"),
        Stat(label="Tensor cores", value="528 (4th gen)"),
        Stat(label="L2 cache", value="60 MB (50 enabled)"),
        Stat(label="Memory", value="80 GB HBM3 · 3.35 TB/s"),
        Stat(label="NVLink", value="900 GB/s"),
    ],
    photo=P_H100_CARD,
    sources=[
        SourceLink(label="NVIDIA H100 Architecture Whitepaper",
                   url="https://resources.nvidia.com/en-us-tensor-core"),
        SourceLink(label="NVIDIA blog: Hopper Architecture In-Depth (die diagram)",
                   url="https://developer.nvidia.com/blog/nvidia-hopper-architecture-in-depth/"),
        SourceLink(label="TechPowerUp GPU DB: GH100 (die shot)",
                   url="https://www.techpowerup.com/gpu-specs/nvidia-gh100.g1011"),
    ],
)

_GPC_DESC_GA100 = L(
    novice=(
        "A Graphics Processing Cluster, one of the die's repeated compute "
        "blocks, holding 16 SMs (streaming multiprocessors — the GPU's "
        "independent processing engines). Each SM carries 64 arithmetic "
        "units for ordinary 32-bit numbers, 4 Tensor Cores — specialized "
        "units that multiply small matrices in one step — and 192 KB of fast "
        "local memory."
    ),
    standard=(
        "Graphics Processing Cluster: 8 TPCs = 16 SMs. Each Ampere SM has 64 "
        "FP32 CUDA cores, 4 third-gen Tensor Cores, and 192 KB L1/shared memory."
    ),
    expert="GPC: 8 TPC / 16 SM; per SM 64 FP32 lanes, 4× gen-3 TC, 192 KB L1/smem.",
)

_IO_DESC_GA100 = L(
    novice=(
        "The chip's front door: the PCIe connection to the host computer, "
        "plus the GigaThread Engine — the global scheduler that hands blocks "
        "of work out to the compute clusters."
    ),
    standard=(
        "Host interface (PCIe 4.0 x16) plus the GigaThread Engine global "
        "scheduler."
    ),
    expert="PCIe 4.0 x16 + GigaThread Engine.",
)

_HBM2E_DESC_GA100 = L(
    novice=(
        "A controller for one stack of HBM2e — High Bandwidth Memory, DRAM "
        "stacked vertically beside the GPU and wired to it with over a "
        "thousand connections per stack. Six such interfaces sit on the die, "
        "five switched on in the A100 product, together moving about 2 "
        "terabytes per second."
    ),
    standard=(
        "HBM2e memory controller + PHY. Six 1024-bit stack interfaces on the "
        "die (five enabled on A100), ~2 TB/s on the 80 GB part."
    ),
    expert="HBM2e ctrl+PHY; 6× 1024-bit on die, 5 enabled, ~2 TB/s (80 GB part).",
)

_L2_DESC_GA100 = L(
    novice=(
        "Half of a 40 MB L2 cache — fast on-chip memory holding recently "
        "used data so the GPU avoids trips to main memory. The cache is "
        "built in two halves so each sits near the memory controllers it "
        "serves; this split layout first appeared in this generation, and "
        "every data-centre die since has kept it."
    ),
    standard=(
        "Half of the 40 MB L2, physically split so each half sits near the "
        "HBM controllers it serves — Ampere introduced this split-L2 layout."
    ),
    expert="Half the 40 MB L2, split for HBM proximity — the layout Ampere introduced.",
)

_NVLINK_DESC_GA100 = L(
    novice=(
        "Twelve ports of NVLink — NVIDIA's dedicated GPU-to-GPU connection, "
        "far faster than the ordinary PCIe plug — together moving 600 "
        "gigabytes per second between A100s in one server."
    ),
    standard="12 third-generation NVLink ports, 600 GB/s aggregate.",
    expert="12× NVLink 3, 600 GB/s aggregate.",
)

GA100 = DieAnatomy(
    id="ga100",
    name="A100 (GA100)",
    vendor="NVIDIA",
    architecture="Ampere",
    process="TSMC 7N",
    die_size="826 mm²",
    transistors="54.2 B",
    year=2020,
    width=100,
    height=64,
    overview=L(
        novice=(
            "This is the chip that came before the Hopper design on the other "
            "tab, and the family resemblance is the point — the same basic "
            "arrangement of arithmetic clusters around a central cache, with "
            "memory stacked along the flanks. Comparing the two shows how "
            "this kind of chip evolves: the layout stays recognisable while "
            "the counts and the speeds climb. Note again that not every unit "
            "on the chip is switched on. Manufacturing silicon this large "
            "always produces some defects, so parts are deliberately disabled "
            "and the chip is sold with a lower count — which is why 128 are "
            "built and 108 are used."
        ),
        plain=(
            "Hopper's predecessor, and the template for NVIDIA's data-centre "
            "floorplan: eight clusters of streaming multiprocessors — 128 on "
            "the full die, 108 enabled on the A100 — around a split 40 MB "
            "cache, six stacks of high-bandwidth memory on the flanks, and 12 "
            "NVLink ports on the bottom edge. The gap between built and "
            "enabled is deliberate: disabling defective units is how large "
            "chips are made economically."
        ),
        standard=(
            "Hopper's predecessor and the template for NVIDIA's data-center "
            "floorplan: 8 GPCs (128 SMs full, 108 enabled on A100) around a "
            "split 40 MB L2, six HBM2e stacks on the flanks, and 12 NVLink 3 "
            "ports on the bottom edge."
        ),
        technical=(
            "The template for the data-centre floorplan: 8 GPCs, 128 SMs full "
            "and 108 enabled on A100, split 40 MB L2, six HBM2e stacks on the "
            "flanks, 12 NVLink 3 ports on the bottom edge."
        ),
        expert=(
            "GA100: 8 GPCs / 128 SMs (108 on A100), split 40 MB L2, 6× HBM2e, "
            "12× NVLink 3. The floorplan GH100 inherits."
        ),
    ),
    regions=[
        DieRegion(id="io", kind="io", label="PCIe Gen4 · GigaThread Engine",
                  x=2, y=2, w=96, h=5,
                  description=_IO_DESC_GA100),
        *[DieRegion(id=f"hbm-l{i}", kind="mem", label="HBM2e",
                    x=2, y=8 + i * 16.8, w=7, h=15.3, photo=P_GP100_PKG,
                    description=_HBM2E_DESC_GA100)
          for i in range(3)],
        *[DieRegion(id=f"hbm-r{i}", kind="mem", label="HBM2e",
                    x=91, y=8 + i * 16.8, w=7, h=15.3, photo=P_GP100_PKG,
                    description=_HBM2E_DESC_GA100)
          for i in range(3)],
        DieRegion(id="l2-a", kind="l2", label="L2 · 20 MB",
                  x=10, y=30, w=39, h=4.5, photo=P_GA100_DIE,
                  description=_L2_DESC_GA100),
        DieRegion(id="l2-b", kind="l2", label="L2 · 20 MB",
                  x=51, y=30, w=39, h=4.5, photo=P_GA100_DIE,
                  description=_L2_DESC_GA100),
        *_gpc_row("gpc-t", 4, 10, 90, 8, 21, "GPC · 16 SM", _GPC_DESC_GA100,
                  photo=P_GA100_DIE),
        *_gpc_row("gpc-b", 4, 10, 90, 35.5, 21, "GPC · 16 SM", _GPC_DESC_GA100,
                  photo=P_GA100_DIE),
        DieRegion(id="nvlink", kind="nvlink", label="NVLink 3 × 12",
                  x=2, y=58, w=96, h=4, photo=P_NVLINK_CARDS,
                  description=_NVLINK_DESC_GA100),
    ],
    stats=[
        Stat(label="SMs (full / enabled)", value="128 / 108"),
        Stat(label="FP32 cores", value="6 912"),
        Stat(label="Tensor cores", value="432 (3rd gen)"),
        Stat(label="L2 cache", value="40 MB"),
        Stat(label="Memory", value="80 GB HBM2e · ~2 TB/s"),
        Stat(label="NVLink", value="600 GB/s"),
    ],
    photo=P_A100_CARD,
    sources=[
        SourceLink(label="NVIDIA A100 / Ampere Architecture Whitepaper",
                   url="https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/nvidia-ampere-architecture-whitepaper.pdf"),
        SourceLink(label="NVIDIA blog: Ampere Architecture In-Depth (die diagram)",
                   url="https://developer.nvidia.com/blog/nvidia-ampere-architecture-in-depth/"),
        SourceLink(label="TechPowerUp GPU DB: GA100 (die shot)",
                   url="https://www.techpowerup.com/gpu-specs/nvidia-ga100.g931"),
    ],
)

_GPC_DESC_AD102 = L(
    novice=(
        "A Graphics Processing Cluster: 12 SMs (streaming multiprocessors, "
        "the GPU's processing engines) plus graphics-specific hardware — a "
        "raster engine that turns triangles into pixels and 16 output units "
        "that write them. Each SM carries 128 arithmetic units, a "
        "ray-tracing core for simulating light paths, and 4 Tensor Cores, "
        "the specialized matrix-math units behind DLSS upscaling."
    ),
    standard=(
        "Graphics Processing Cluster: 6 TPCs = 12 SMs, plus a raster engine and "
        "16 ROPs. Each Ada SM has 128 FP32 cores, a 3rd-gen RT core, and 4 "
        "4th-gen Tensor Cores."
    ),
    expert="GPC: 6 TPC / 12 SM + raster + 16 ROP; per SM 128 FP32, gen-3 RT, 4× gen-4 TC.",
)

_IO_DESC_AD102 = L(
    novice=(
        "The chip's connections to the outside: the PCIe link to the host "
        "computer, and the display engine that drives the monitor outputs "
        "(DisplayPort and HDMI)."
    ),
    standard=(
        "Host interface (PCIe 4.0 x16) and display engine (DP 1.4a / HDMI "
        "2.1 heads)."
    ),
    expert="PCIe 4.0 x16; display heads DP 1.4a / HDMI 2.1.",
)

_MEDIA_DESC_AD102 = L(
    novice=(
        "Dedicated video hardware: two encoders and a decoder for compressed "
        "video formats like AV1 and H.265. They are separate circuits from "
        "the compute clusters, which is why recording or streaming gameplay "
        "barely slows the game itself."
    ),
    standard=(
        "Fixed-function video engines: dual AV1/H.265 encoders and a decoder "
        "— independent of the GPCs, which is why streaming barely costs "
        "shader performance."
    ),
    expert="2× NVENC + NVDEC (AV1/H.265), decoupled from the GPCs — streaming ≈ free.",
)

_GDDR6X_DESC = L(
    novice=(
        "A pair of controllers for GDDR6X — the graphics memory soldered "
        "onto the card around the GPU, unlike the stacked memory that "
        "data-centre chips use. Twelve of these controller blocks ring "
        "three edges of the die; together they form a 384-wire connection "
        "moving about a terabyte per second."
    ),
    standard=(
        "Two 32-bit GDDR6X controllers + PHY. Twelve total ring the die for "
        "a 384-bit bus, ~1 TB/s."
    ),
    expert="2× 32-bit GDDR6X ctrl+PHY; ×12 → 384-bit, ~1 TB/s.",
)

_L2_DESC_AD102 = L(
    novice=(
        "The defining feature of this generation: 96 megabytes of L2 cache — "
        "fast memory built into the chip itself (72 MB switched on in the "
        "4090), sixteen times what the previous generation had. Every byte "
        "the cache catches is a trip to the graphics memory avoided, so the "
        "designers spent silicon area to buy back memory traffic — the same "
        "economics this app's tiling and roofline model teaches."
    ),
    standard=(
        "Ada's defining block: 96 MB of central L2 (72 MB enabled on the "
        "4090), 16× GA102's. A giant on-die cache trades area for DRAM "
        "traffic — the same bandwidth economics this app's tiling/roofline "
        "model demonstrates."
    ),
    expert=(
        "96 MB central L2 (72 on 4090), 16× GA102 — area spent to cut DRAM "
        "traffic; cf. the app's tiling/roofline model."
    ),
)

AD102 = DieAnatomy(
    id="ad102",
    name="RTX 4090 (AD102)",
    vendor="NVIDIA",
    architecture="Ada Lovelace",
    process="TSMC 4N",
    die_size="608 mm²",
    transistors="76.3 B",
    year=2022,
    width=100,
    height=76,
    overview=L(
        novice=(
            "This chip is for gaming rather than for data centres, and the "
            "differences in the floorplan tell you what that changes. There "
            "is no stacked memory hugging the die and no links for joining "
            "chips together, because a gaming card sits alone in one "
            "computer. Instead, twelve ordinary memory controllers wrap "
            "around three edges, connecting to memory chips soldered nearby "
            "on the board. That memory is narrower than the data-centre kind, "
            "so the designers compensated by making the on-chip cache "
            "enormous — sixteen times larger than the previous generation. "
            "Keeping data on the chip is the cheapest way to avoid needing to "
            "fetch it."
        ),
        plain=(
            "The consumer flagship layout, and it differs from the "
            "data-centre dies in instructive ways: no high-bandwidth memory "
            "and no NVLink, because a gaming card works alone. Twelve GDDR6X "
            "controllers wrap the left, right, and bottom edges; a very large "
            "central 96 MB cache — sixteen times Ampere's — compensates for "
            "the narrower 384-bit bus; twelve clusters fill the space above "
            "and below, with media and display engines up top."
        ),
        standard=(
            "The consumer flagship layout: no HBM, no NVLink. Twelve GDDR6X "
            "controllers wrap the left, right, and bottom edges; a huge central "
            "96 MB L2 (16× Ampere's) compensates for the narrower 384-bit bus; "
            "12 GPCs fill the space above and below it, with media engines and "
            "display up top."
        ),
        technical=(
            "Consumer flagship: no HBM, no NVLink. Twelve GDDR6X controllers "
            "on the left, right, and bottom edges; a 96 MB central L2 (16× "
            "Ampere) offsetting the 384-bit bus; 12 GPCs above and below; "
            "media and display up top."
        ),
        expert=(
            "AD102: GDDR6X ×12 on three edges, 384-bit, 96 MB L2 (16× Ampere) "
            "offsetting bus width, 12 GPCs, no HBM or NVLink."
        ),
    ),
    regions=[
        DieRegion(id="io", kind="io", label="PCIe Gen4 · Display",
                  x=2, y=2, w=58, h=5,
                  description=_IO_DESC_AD102),
        DieRegion(id="media", kind="media", label="NVENC ×2 · NVDEC",
                  x=61, y=2, w=37, h=5,
                  description=_MEDIA_DESC_AD102),
        *[DieRegion(id=f"gddr-l{i}", kind="mem", label="GDDR6X",
                    x=2, y=8 + i * 14.9, w=6, h=13.7, photo=P_GDDR6_PCB,
                    description=_GDDR6X_DESC)
          for i in range(4)],
        *[DieRegion(id=f"gddr-r{i}", kind="mem", label="GDDR6X",
                    x=92, y=8 + i * 14.9, w=6, h=13.7, photo=P_GDDR6_PCB,
                    description=_GDDR6X_DESC)
          for i in range(4)],
        *[DieRegion(id=f"gddr-b{i}", kind="mem", label="GDDR6X",
                    x=10 + i * 20.25, y=69.5, w=19.5, h=4.5, photo=P_GDDR6_PCB,
                    description=_GDDR6X_DESC)
          for i in range(4)],
        DieRegion(id="l2", kind="l2", label="L2 CACHE · 96 MB",
                  x=9.5, y=35, w=81, h=7.5, photo=P_AD102_DIE,
                  description=_L2_DESC_AD102),
        *_gpc_row("gpc-t", 6, 9.5, 90.5, 8, 25.5, "GPC · 12 SM", _GPC_DESC_AD102,
                  photo=P_AD102_DIE),
        *_gpc_row("gpc-b", 6, 9.5, 90.5, 44, 24, "GPC · 12 SM", _GPC_DESC_AD102,
                  photo=P_AD102_DIE),
    ],
    stats=[
        Stat(label="SMs (full / 4090)", value="144 / 128"),
        Stat(label="FP32 cores", value="18 432"),
        Stat(label="RT / Tensor cores", value="144 / 576"),
        Stat(label="L2 cache", value="96 MB (72 enabled)"),
        Stat(label="Memory", value="24 GB GDDR6X · 1 TB/s"),
        Stat(label="Bus width", value="384-bit"),
    ],
    photo=P_AD102_DIE,
    sources=[
        SourceLink(label="NVIDIA Ada GPU Architecture Whitepaper (die diagram)",
                   url="https://images.nvidia.com/aem-dam/Solutions/geforce/ada/nvidia-ada-gpu-architecture.pdf"),
        SourceLink(label="TechPowerUp GPU DB: AD102 (die shot)",
                   url="https://www.techpowerup.com/gpu-specs/nvidia-ad102.g1005"),
    ],
)

_SE_DESC_NAVI31 = L(
    novice=(
        "A Shader Engine — AMD's version of a compute cluster. It holds 16 "
        "Compute Units (AMD's equivalent of NVIDIA's SMs, the GPU's "
        "processing engines) totalling 1,024 arithmetic lanes, plus the "
        "graphics-specific units that turn triangles into finished pixels."
    ),
    standard=(
        "Shader Engine: 8 WGPs = 16 dual-issue RDNA 3 Compute Units (1024 "
        "stream processors) plus a raster unit, primitive unit, and 32 ROPs."
    ),
    expert="SE: 8 WGP / 16 dual-issue CU (1024 SP) + raster, primitive, 32 ROP.",
)

_MCD_DESC = L(
    novice=(
        "A Memory Cache Die — a small separate chip, not part of the main "
        "die, carrying 16 MB of cache (fast memory that spares trips to the "
        "graphics DRAM) and one 64-wire memory interface. Six of them "
        "surround the compute die, adding up to a 384-wire bus and 96 MB of "
        "cache. Splitting them off lets the expensive cutting-edge silicon "
        "be spent purely on compute, while cache and memory wiring — which "
        "gain little from newer manufacturing — are made more cheaply."
    ),
    standard=(
        "Memory Cache Die — a separate 37 mm² chiplet on TSMC 6nm carrying 16 MB "
        "of Infinity Cache and a 64-bit GDDR6 PHY. Six MCDs give a 384-bit bus "
        "and 96 MB of cache; splitting them off keeps the expensive 5nm die "
        "purely compute."
    ),
    expert=(
        "MCD: 37 mm² N6 chiplet, 16 MB IC + 64-bit GDDR6 PHY; ×6 → 384-bit "
        "/ 96 MB. Keeps the N5 GCD all-compute."
    ),
)

_FANOUT_DESC = L(
    novice=(
        "The links that wire the central compute die to its surrounding "
        "memory-cache chiplets, run through dense wiring in the package "
        "substrate. Together they carry about 5.3 terabytes per second — "
        "traffic that on a single-piece chip would simply be on-die wires, "
        "and which only exists as a problem because the design was split "
        "into pieces."
    ),
    standard=(
        "Infinity Fanout links: dense organic-substrate wiring between GCD "
        "and MCDs, ~5.3 TB/s aggregate — an off-die bandwidth problem the "
        "monolithic dies don't have."
    ),
    expert=(
        "Infinity Fanout: GCD↔MCD substrate links, ~5.3 TB/s — the off-die "
        "tax monolithic dies don't pay."
    ),
)

_FRONTEND_DESC_NAVI31 = L(
    novice=(
        "The front end of the compute die: the command processor that reads "
        "the host computer's instructions and hands work out across the "
        "chip, the geometry engine, and the PCIe connection to the host. It "
        "plays the same role NVIDIA's GigaThread Engine does on the other "
        "dies here."
    ),
    standard=(
        "GCD front end: command processor, geometry engine, and host PCIe "
        "interface — AMD's counterpart to NVIDIA's GigaThread Engine."
    ),
    expert="GCD front end: command processor, geometry, host PCIe — the GigaThread analogue.",
)

_MEDIA_DESC_NAVI31 = L(
    novice=(
        "Dedicated video hardware — two engines that compress and decompress "
        "video formats like AV1 without using the compute units — plus the "
        "display engine that drives the monitor outputs, along the compute "
        "die's bottom edge."
    ),
    standard=(
        "Dual media engines (AV1 encode/decode) and the DisplayPort 2.1 "
        "display engine, on the GCD's bottom edge."
    ),
    expert="2× media engines (AV1 enc/dec) + DP 2.1 display, bottom edge of the GCD.",
)

NAVI31 = DieAnatomy(
    id="navi31",
    name="RX 7900 XTX (Navi 31)",
    vendor="AMD",
    architecture="RDNA 3 (chiplet)",
    process="TSMC 5nm GCD + 6nm MCDs",
    die_size="300 mm² GCD + 6 × 37 mm² MCD",
    transistors="57.7 B",
    year=2022,
    width=100,
    height=54,
    overview=L(
        novice=(
            "Every other chip here is one single piece of silicon. This one "
            "is not: it is built from several smaller pieces mounted together "
            "on one package. The reasoning is economic. Large chips are "
            "disproportionately expensive to manufacture, because a single "
            "defect ruins the whole thing and bigger chips catch more "
            "defects. Splitting the design lets the parts that benefit from "
            "the newest, priciest manufacturing stay small, while the memory "
            "and cache blocks — which gain little from it — are made "
            "separately on cheaper processes. The cost is that the pieces "
            "must talk to each other across the package, which needs "
            "dedicated high-speed links."
        ),
        plain=(
            "The first chiplet gaming GPU, and the structural odd one out "
            "here. A central Graphics Compute Die holds six shader engines "
            "(96 compute units); the memory controllers and Infinity Cache "
            "are broken out into six separate cache chiplets flanking it, "
            "connected over Infinity Fanout links at about 5.3 TB/s. The "
            "motivation is manufacturing cost: large dies yield badly, so "
            "only the parts that need the newest process stay on the "
            "expensive one. Compare the monolithic NVIDIA dies, where cache "
            "and memory interfaces share silicon with the compute."
        ),
        standard=(
            "The first chiplet gaming GPU. A central Graphics Compute Die holds "
            "six shader engines (96 CUs); memory controllers and Infinity Cache "
            "are broken out into six MCD chiplets flanking it, wired over "
            "Infinity Fanout links at ~5.3 TB/s. Compare with the monolithic "
            "NVIDIA dies, where L2 and PHYs share the die with the SMs."
        ),
        technical=(
            "First chiplet gaming GPU: a central GCD with six shader engines "
            "(96 CUs), memory controllers and Infinity Cache disaggregated "
            "into six MCDs over Infinity Fanout at ~5.3 TB/s. Contrast the "
            "monolithic NVIDIA dies, where L2 and PHYs share silicon with the "
            "SMs — the trade is die cost against die-to-die interconnect."
        ),
        expert=(
            "Navi 31: GCD (6 SE / 96 CU) + 6 MCDs over Infinity Fanout at "
            "~5.3 TB/s. Disaggregates cache and PHYs off the leading-edge "
            "node; trades yield economics against die-to-die cost."
        ),
    ),
    regions=[
        *[DieRegion(id=f"mcd-l{i}", kind="cache", label="MCD · 16 MB IC",
                    x=2, y=4 + i * 15.8, w=9, h=14.6, description=_MCD_DESC)
          for i in range(3)],
        *[DieRegion(id=f"mcd-r{i}", kind="cache", label="MCD · 16 MB IC",
                    x=89, y=4 + i * 15.8, w=9, h=14.6, description=_MCD_DESC)
          for i in range(3)],
        DieRegion(id="fanout-l", kind="fabric", label="",
                  x=11.5, y=4, w=1.5, h=46.2,
                  description=_FANOUT_DESC),
        DieRegion(id="fanout-r", kind="fabric", label="",
                  x=87, y=4, w=1.5, h=46.2,
                  description=_FANOUT_DESC),
        DieRegion(id="frontend", kind="io", label="Command Processor · Geometry · PCIe Gen4",
                  x=13.5, y=4, w=73, h=5,
                  description=_FRONTEND_DESC_NAVI31),
        *_gpc_row("se-t", 3, 13.5, 86.5, 10.2, 16.5,
                  "Shader Engine · 16 CU", _SE_DESC_NAVI31, photo=P_NAVI22_DIE),
        *_gpc_row("se-b", 3, 13.5, 86.5, 27.9, 16.5,
                  "Shader Engine · 16 CU", _SE_DESC_NAVI31, photo=P_NAVI22_DIE),
        DieRegion(id="media", kind="media", label="Media Engine · Display (Radiance)",
                  x=13.5, y=45.6, w=73, h=4.6,
                  description=_MEDIA_DESC_NAVI31),
    ],
    stats=[
        Stat(label="Compute units", value="96 (6 144 SPs)"),
        Stat(label="Shader engines", value="6"),
        Stat(label="Infinity Cache", value="96 MB (on MCDs)"),
        Stat(label="Memory", value="24 GB GDDR6 · 960 GB/s"),
        Stat(label="GCD ↔ MCD fabric", value="~5.3 TB/s"),
        Stat(label="Chiplets", value="1 GCD + 6 MCD"),
    ],
    photo=P_RX7900_CARD,
    sources=[
        SourceLink(label="AMD RDNA 3 technology page",
                   url="https://www.amd.com/en/technologies/rdna"),
        SourceLink(label="TechPowerUp GPU DB: Navi 31 (die shot)",
                   url="https://www.techpowerup.com/gpu-specs/amd-navi-31.g998"),
        SourceLink(label="Chips and Cheese: RDNA 3 chiplet analysis",
                   url="https://chipsandcheese.com/p/amds-rdna-3-graphics-architecture"),
    ],
)

_GPC_DESC_GB100 = L(
    novice=(
        "A cluster of roughly 20 SMs (streaming multiprocessors — the GPU's "
        "processing engines; NVIDIA hasn't published the exact grouping). "
        "Each of the two dies physically carries 80 SMs, 74 of them switched "
        "on in the B200 product. Their Tensor Cores — the specialized "
        "matrix-math units behind AI throughput — add support for 4- and "
        "6-bit number formats, trading precision for speed."
    ),
    standard=(
        "Blackwell SM cluster (~20 SMs; NVIDIA has not published the exact GPC "
        "partitioning). Each die carries 80 SMs physically, 74 enabled on B200, "
        "with 5th-gen Tensor Cores adding FP4/FP6 precisions."
    ),
    expert=(
        "~20-SM cluster (GPC split unpublished); 80 SM/die, 74 enabled on "
        "B200; gen-5 TC adds FP4/FP6."
    ),
)

_HBM3E_DESC = L(
    novice=(
        "A controller for one stack of HBM3e — High Bandwidth Memory, DRAM "
        "chips stacked vertically beside the GPU and wired to it with over a "
        "thousand connections per stack. Each compute die has four, eight "
        "across the package, together holding 192 GB and moving about 8 "
        "terabytes per second."
    ),
    standard=(
        "HBM3e memory controller + PHY. Four 1024-bit stacks per die — eight "
        "across the package — for 192 GB and ~8 TB/s aggregate bandwidth."
    ),
    expert="HBM3e ctrl+PHY, 1024-bit/stack; 4/die, 8/package → 192 GB, ~8 TB/s.",
)

# Shared verbatim by GB200 and GB300 — one registration serves both dies.
_IO_DESC_GB = L(
    novice=(
        "The chip's front door — the connection to the host computer and the "
        "global scheduler that hands out work. It spans both halves of the "
        "package: even though the silicon is physically two dies, programs "
        "see a single GPU with a single front end."
    ),
    standard=(
        "Host interface and global scheduler, spanning both dies — one "
        "logical GPU front-end despite the split silicon."
    ),
    expert="Host IF + global scheduler across both dies: one logical front end.",
)

_L2_DESC_GB = L(
    novice=(
        "Half of a 126 MB L2 cache — fast on-chip memory that spares trips "
        "out to the memory stacks. Each of the two fused dies keeps its own "
        "slice next to its own memory controllers, and the die-to-die link "
        "keeps the halves in sync so software sees one cache."
    ),
    standard=(
        "Half of the 126 MB L2. Each die keeps its own slice close to its "
        "HBM controllers; NV-HBI keeps the two halves coherent."
    ),
    expert="Half the 126 MB L2, per-die slices; coherence over NV-HBI.",
)

_NVHBI_DESC_GB200 = L(
    novice=(
        "The seam down the middle of the package. Chip-printing machines can "
        "only expose a rectangle of a fixed maximum size — the reticle limit "
        "— so this design builds two chips at that limit and joins them with "
        "this link, fast enough (10 terabytes per second) that software "
        "cannot tell there are two. It is the defining feature of this "
        "generation, and a different answer to the same manufacturing wall "
        "AMD's chiplet designs work around."
    ),
    standard=(
        "NV-High Bandwidth Interface: the 10 TB/s die-to-die fabric that "
        "stitches the two reticle-limited dies into one coherent GPU — the "
        "defining Blackwell block, and NVIDIA's answer to hitting the "
        "reticle limit that AMD's Navi 31 chiplets also work around."
    ),
    expert=(
        "NV-HBI: 10 TB/s D2D fabric fusing two reticle-limited dies into "
        "one coherent GPU — Blackwell's defining block; cf. Navi 31's "
        "chiplet answer."
    ),
)

_NVLINK_DESC_GB200 = L(
    novice=(
        "Eighteen ports of NVLink, NVIDIA's dedicated GPU-to-GPU connection "
        "— together 1.8 terabytes per second, twice the previous generation. "
        "These ports are what let 72 of these GPUs in one rack be wired into "
        "a single working unit."
    ),
    standard=(
        "18 fifth-generation NVLink ports, 1.8 TB/s aggregate — double "
        "Hopper, and the backbone of the 72-GPU NVL72 rack."
    ),
    expert="18× NVLink 5, 1.8 TB/s — 2× Hopper; the NVL72 backbone.",
)

GB200 = DieAnatomy(
    id="gb200",
    name="B200 (GB200 · Blackwell)",
    vendor="NVIDIA",
    architecture="Blackwell (dual-die)",
    process="TSMC 4NP",
    die_size="2 × reticle-limited dies (~1600 mm² total)",
    transistors="208 B (104 B per die)",
    year=2024,
    width=130,
    height=64,
    overview=L(
        novice=(
            "There is a hard physical limit on how large a single chip can be "
            "— the machines that print the patterns onto silicon can only "
            "expose a rectangle of a certain size, and you cannot exceed it. "
            "This design reaches that limit and then goes past it by building "
            "two chips at the maximum size and fusing them with an extremely "
            "fast connection down the middle. The connection is quick enough "
            "that software cannot tell the difference: it sees one processor, "
            "not two. That trick — making several physical things behave as "
            "one logical thing — appears repeatedly in this repo, most "
            "dramatically in the rack twin where 72 of these are fused into a "
            "single unit."
        ),
        plain=(
            "NVIDIA's first multi-die GPU: two reticle-limited compute dies — "
            "each as large as the manufacturing process physically allows — "
            "fused into one logical GPU by a 10 TB/s die-to-die link down the "
            "centre, so software sees a single 148-SM device. Four stacks of "
            "HBM3e flank each die (192 GB, about 8 TB/s), with 126 MB of "
            "cache and NVLink 5 at 1.8 TB/s. The GB200 superchip pairs two of "
            "these with a Grace CPU, and this repo's XE9712 twin shows 72 of "
            "them fused into one domain."
        ),
        standard=(
            "NVIDIA's first multi-die GPU: two reticle-limited compute dies "
            "fused into one logical GPU by NV-HBI, a 10 TB/s die-to-die link "
            "down the center — software sees a single 148-SM device. Four HBM3e "
            "stacks flank each die (192 GB, ~8 TB/s), with 126 MB of L2 and "
            "NVLink 5 at 1.8 TB/s. The GB200 superchip pairs two of these GPUs "
            "with a Grace CPU."
        ),
        technical=(
            "First multi-die GPU: two reticle-limited compute dies fused by "
            "NV-HBI, a 10 TB/s die-to-die link — presented to software as a "
            "single 148-SM device. Four HBM3e stacks per die (192 GB, ~8 "
            "TB/s), 126 MB L2, NVLink 5 at 1.8 TB/s. The superchip pairs two "
            "with a Grace CPU; the XE9712 twin fuses 72 into one NVLink "
            "domain."
        ),
        expert=(
            "GB200: 2× reticle-limited dies over NV-HBI at 10 TB/s, single "
            "logical 148-SM device. 192 GB HBM3e at ~8 TB/s, 126 MB L2, "
            "NVLink 5 at 1.8 TB/s. Scales to a 72-GPU domain (see XE9712)."
        ),
    ),
    regions=[
        DieRegion(id="io", kind="io", label="Host Interface · GigaThread Engine",
                  x=2, y=2, w=126, h=5,
                  description=_IO_DESC_GB),
        *[DieRegion(id=f"hbm-l{i}", kind="mem", label="HBM3e",
                    x=2, y=8 + i * 12.4, w=7, h=10.9, description=_HBM3E_DESC,
                    photo=P_GP100_PKG)
          for i in range(4)],
        *[DieRegion(id=f"hbm-r{i}", kind="mem", label="HBM3e",
                    x=121, y=8 + i * 12.4, w=7, h=10.9, description=_HBM3E_DESC,
                    photo=P_GP100_PKG)
          for i in range(4)],
        DieRegion(id="nvhbi", kind="fabric", label="NV-HBI",
                  x=63.25, y=8, w=3.5, h=49, photo=P_GB200_BOARD,
                  description=_NVHBI_DESC_GB200),
        DieRegion(id="l2-a", kind="l2", label="L2 · 63 MB",
                  x=10, y=30, w=52.5, h=4.5,
                  description=_L2_DESC_GB),
        DieRegion(id="l2-b", kind="l2", label="L2 · 63 MB",
                  x=67.5, y=30, w=52.5, h=4.5,
                  description=_L2_DESC_GB),
        *_gpc_row("gpc-lt", 2, 10, 62.5, 8, 21, "GPC · ~20 SM", _GPC_DESC_GB100,
                  photo=P_GB200_BOARD),
        *_gpc_row("gpc-lb", 2, 10, 62.5, 35.5, 21, "GPC · ~20 SM", _GPC_DESC_GB100,
                  photo=P_GB200_BOARD),
        *_gpc_row("gpc-rt", 2, 67.5, 120, 8, 21, "GPC · ~20 SM", _GPC_DESC_GB100,
                  photo=P_GB200_BOARD),
        *_gpc_row("gpc-rb", 2, 67.5, 120, 35.5, 21, "GPC · ~20 SM", _GPC_DESC_GB100,
                  photo=P_GB200_BOARD),
        DieRegion(id="nvlink", kind="nvlink", label="NVLink 5 × 18",
                  x=2, y=58, w=126, h=4, photo=P_NVLINK_CARDS,
                  description=_NVLINK_DESC_GB200),
    ],
    stats=[
        Stat(label="SMs (physical / enabled)", value="160 / 148"),
        Stat(label="Dies", value="2 × 104 B transistors"),
        Stat(label="Die-to-die (NV-HBI)", value="10 TB/s"),
        Stat(label="L2 cache", value="126 MB"),
        Stat(label="Memory", value="192 GB HBM3e · 8 TB/s"),
        Stat(label="NVLink 5", value="1.8 TB/s"),
    ],
    photo=P_GB200_BOARD,
    sources=[
        SourceLink(label="NVIDIA Blackwell Architecture Technical Overview",
                   url="https://resources.nvidia.com/en-us-blackwell-architecture"),
        SourceLink(label="Chips and Cheese: NVIDIA's B200 analysis",
                   url="https://chipsandcheese.com/p/nvidias-b200-keeping-the-cuda-juggernaut"),
        SourceLink(label="Wikipedia: Blackwell (microarchitecture)",
                   url="https://en.wikipedia.org/wiki/Blackwell_(microarchitecture)"),
    ],
)

_GPC_DESC_GB202 = L(
    novice=(
        "A Graphics Processing Cluster: 16 SMs (streaming multiprocessors, "
        "the GPU's processing engines) plus the raster engine and output "
        "units that turn triangles into pixels. Each SM carries 128 "
        "arithmetic units, a ray-tracing core for simulating light, and 4 "
        "Tensor Cores — matrix-math units that here also support 4-bit "
        "numbers, so small neural networks can run inside the graphics "
        "pipeline itself."
    ),
    standard=(
        "Graphics Processing Cluster: 8 TPCs = 16 SMs, plus a raster engine and "
        "16 ROPs. Each consumer-Blackwell SM has 128 FP32 cores, a 4th-gen RT "
        "core, and 4 5th-gen Tensor Cores with FP4 support for neural shaders."
    ),
    expert=(
        "GPC: 8 TPC / 16 SM + raster + 16 ROP; per SM 128 FP32, gen-4 RT, "
        "4× gen-5 TC (FP4 neural shaders)."
    ),
)

_IO_DESC_GB202 = L(
    novice=(
        "The chip's connections to the outside: the PCIe link to the host "
        "computer and the display engine that drives the monitor outputs "
        "(DisplayPort and HDMI)."
    ),
    standard=(
        "Host interface (PCIe 5.0 x16) and the display engine (DP 2.1b / "
        "HDMI 2.1b heads)."
    ),
    expert="PCIe 5.0 x16; display heads DP 2.1b / HDMI 2.1b.",
)

_MEDIA_DESC_GB202 = L(
    novice=(
        "Dedicated video hardware: three encoders and two decoders for "
        "compressed formats like AV1 and H.265. They are separate circuits "
        "from the compute clusters, so recording or streaming barely touches "
        "game performance."
    ),
    standard=(
        "Fixed-function video engines: three 9th-gen AV1/H.265 encoders and "
        "two decoders, independent of the GPCs."
    ),
    expert="3× NVENC + 2× NVDEC (gen-9, AV1/H.265), decoupled from the GPCs.",
)

_GDDR7_DESC = L(
    novice=(
        "A controller block for GDDR7 — the graphics memory soldered onto "
        "the card around the GPU rather than stacked beside it. Sixteen "
        "controllers ring three edges of the die (the drawing groups them "
        "into twelve blocks), forming a 512-wire connection that moves about "
        "1.79 terabytes per second."
    ),
    standard=(
        "GDDR7 controller + PHY block. Sixteen 32-bit controllers ring three "
        "edges of the die (drawn here as twelve blocks) for a 512-bit bus, "
        "~1.79 TB/s."
    ),
    expert="GDDR7 ctrl+PHY; 16× 32-bit on three edges (drawn as 12) → 512-bit, ~1.79 TB/s.",
)

_L2_DESC_GB202 = L(
    novice=(
        "The central L2 cache: 128 megabytes of fast memory built into the "
        "chip, 96 switched on in the 5090. It carries forward the previous "
        "generation's bet — every byte this cache catches is a trip to the "
        "graphics memory avoided, the same economics this app's tiling and "
        "roofline model teaches."
    ),
    standard=(
        "The central L2 — 128 MB physically on GB202, 96 MB enabled on the "
        "5090. Ada's giant-cache bet carried forward: on-die SRAM buys back "
        "DRAM traffic, the same economics this app's tiling/roofline model "
        "demonstrates."
    ),
    expert=(
        "Central L2: 128 MB physical / 96 enabled — Ada's SRAM-for-DRAM-"
        "traffic bet continued; cf. the tiling/roofline model."
    ),
)

GB202 = DieAnatomy(
    id="gb202",
    name="RTX 5090 (GB202)",
    vendor="NVIDIA",
    architecture="Blackwell (consumer)",
    process="TSMC 4NP",
    die_size="750 mm²",
    transistors="92.2 B",
    year=2025,
    width=100,
    height=76,
    overview=L(
        novice=(
            "This is the gaming version of the Blackwell design. Where the "
            "data-centre part joins two maximum-size chips together, a gaming "
            "card gets one large chip, because it works alone in a single "
            "computer and has no need to talk to siblings. The layout follows "
            "the same consumer recipe as the previous generation: ordinary "
            "memory chips soldered around the processor on the board rather "
            "than stacked against it, a large on-chip cache in the middle to "
            "cut down trips to that memory, and dedicated video-encoding "
            "blocks along the top. What changed is scale — more arithmetic "
            "clusters, and a memory bus a third wider than before."
        ),
        plain=(
            "The consumer face of Blackwell: one monolithic die where the "
            "data-centre B200 fuses two. The AD102 recipe carries over — "
            "GDDR memory around three edges, a large central cache, media "
            "engines up top — but scaled: sixteen GDDR7 controllers make a "
            "512-bit bus (a third wider than the 4090's) at about 1.8 TB/s, "
            "and twelve clusters hold 170 enabled streaming multiprocessors. "
            "The new tensor cores add 4-bit float arithmetic, aimed at "
            "running neural networks inside the graphics pipeline itself."
        ),
        standard=(
            "The consumer face of Blackwell — one monolithic die where B200 "
            "fuses two. The AD102 floorplan carries over, scaled: sixteen "
            "GDDR7 controllers make a 512-bit bus (~1.8 TB/s, a third wider "
            "than the 4090's), 12 GPCs hold 170 enabled SMs of 192, and the "
            "5th-gen Tensor Cores add FP4 for in-pipeline neural shaders. "
            "No NVLink — a gaming card still works alone."
        ),
        technical=(
            "Consumer Blackwell: monolithic (no NV-HBI), the AD102 layout "
            "scaled up. 16 GDDR7 controllers on three edges for a 512-bit "
            "bus at ~1.79 TB/s; 12 GPCs, 192 SMs physical / 170 on the 5090; "
            "5th-gen Tensor Cores with FP4; PCIe Gen 5; no NVLink."
        ),
        expert=(
            "GB202: monolithic, 12 GPCs / 192 SMs (170 on 5090), 512-bit "
            "GDDR7 at ~1.79 TB/s, 96 MB L2 enabled, FP4 tensor path, PCIe "
            "Gen5, no NVLink. AD102 recipe at reticle-adjacent scale."
        ),
    ),
    regions=[
        DieRegion(id="io", kind="io", label="PCIe Gen5 · Display",
                  x=2, y=2, w=58, h=5,
                  description=_IO_DESC_GB202),
        DieRegion(id="media", kind="media", label="NVENC ×3 · NVDEC ×2",
                  x=61, y=2, w=37, h=5,
                  description=_MEDIA_DESC_GB202),
        *[DieRegion(id=f"gddr-l{i}", kind="mem", label="GDDR7",
                    x=2, y=8 + i * 14.9, w=6, h=13.7, photo=P_GDDR6_PCB,
                    description=_GDDR7_DESC)
          for i in range(4)],
        *[DieRegion(id=f"gddr-r{i}", kind="mem", label="GDDR7",
                    x=92, y=8 + i * 14.9, w=6, h=13.7, photo=P_GDDR6_PCB,
                    description=_GDDR7_DESC)
          for i in range(4)],
        *[DieRegion(id=f"gddr-b{i}", kind="mem", label="GDDR7",
                    x=10 + i * 20.25, y=69.5, w=19.5, h=4.5, photo=P_GDDR6_PCB,
                    description=_GDDR7_DESC)
          for i in range(4)],
        DieRegion(id="l2", kind="l2", label="L2 CACHE · 96 MB",
                  x=9.5, y=35, w=81, h=7.5,
                  description=_L2_DESC_GB202),
        *_gpc_row("gpc-t", 6, 9.5, 90.5, 8, 25.5, "GPC · 16 SM", _GPC_DESC_GB202),
        *_gpc_row("gpc-b", 6, 9.5, 90.5, 44, 24, "GPC · 16 SM", _GPC_DESC_GB202),
    ],
    stats=[
        Stat(label="SMs (full / 5090)", value="192 / 170"),
        Stat(label="FP32 cores", value="21 760"),
        Stat(label="RT / Tensor cores", value="170 / 680 (5th gen)"),
        Stat(label="L2 cache", value="128 MB (96 enabled)"),
        Stat(label="Memory", value="32 GB GDDR7 · 1.79 TB/s"),
        Stat(label="Bus width", value="512-bit"),
    ],
    sources=[
        SourceLink(label="NVIDIA RTX Blackwell GPU Architecture Whitepaper",
                   url="https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf"),
        SourceLink(label="TechPowerUp GPU DB: GB202",
                   url="https://www.techpowerup.com/gpu-specs/nvidia-gb202.g1072"),
        SourceLink(label="Chips and Cheese: RTX 5090 analysis",
                   url="https://chipsandcheese.com/p/blackwell-nvidias-massive-gpu"),
    ],
)

_GPC_DESC_GB300 = L(
    novice=(
        "A cluster of roughly 20 SMs (streaming multiprocessors — the GPU's "
        "processing engines; the exact grouping is unpublished). On this "
        "refresh every one of the 160 SMs across both dies is switched on. "
        "The B200 shipped with 148 of 160 as insurance against "
        "manufacturing defects; a year of factory learning made the "
        "insurance unnecessary."
    ),
    standard=(
        "Blackwell Ultra SM cluster (~20 SMs; NVIDIA has not published the exact "
        "GPC partitioning). All 160 SMs across both dies are enabled on B300 — "
        "the yield learning that shipped B200 at 148 now sells the full die."
    ),
    expert=(
        "~20-SM cluster; full 160/160 enablement on B300 — B200's 148 was "
        "yield insurance, now retired."
    ),
)

_HBM3E_12HI_DESC = L(
    novice=(
        "A controller for one stack of HBM3e — High Bandwidth Memory, DRAM "
        "stacked vertically beside the GPU. The interfaces are unchanged "
        "from the B200, but each stack grew from eight memory layers to "
        "twelve, lifting the package to 288 GB at the same ~8 terabytes per "
        "second. Capacity is the change, not speed: the point is that "
        "bigger AI models fit next to the processor."
    ),
    standard=(
        "HBM3e memory controller + PHY. Same interfaces as B200, but the stacks "
        "grew taller: 12-high instead of 8-high, for 288 GB per GPU at ~8 TB/s. "
        "Capacity, not bandwidth, is what changed — the point is holding bigger "
        "models resident."
    ),
    expert=(
        "HBM3e ctrl+PHY, B200 interfaces, 12-Hi stacks → 288 GB @ ~8 TB/s. "
        "Capacity bump, not bandwidth."
    ),
)

_NVHBI_DESC_GB300 = L(
    novice=(
        "The seam down the middle: the link that joins the two maximum-size "
        "dies into what software sees as one GPU, carried over unchanged "
        "from the B200 at 10 terabytes per second."
    ),
    standard=(
        "NV-High Bandwidth Interface: the 10 TB/s die-to-die fabric carried "
        "over from B200 — two reticle-limited dies, one coherent GPU."
    ),
    expert="NV-HBI, 10 TB/s D2D, unchanged from B200 — two dies, one GPU.",
)

_NVLINK_DESC_GB300 = L(
    novice=(
        "Eighteen ports of NVLink, NVIDIA's dedicated GPU-to-GPU connection, "
        "moving 1.8 terabytes per second — unchanged from the B200, and "
        "still what wires 72 of these into one rack-scale unit."
    ),
    standard=(
        "18 fifth-generation NVLink ports, 1.8 TB/s aggregate — unchanged "
        "from B200, and the backbone of the GB300 NVL72 rack."
    ),
    expert="18× NVLink 5, 1.8 TB/s, unchanged; GB300 NVL72 backbone.",
)

GB300 = DieAnatomy(
    id="gb300",
    name="B300 (GB300 · Blackwell Ultra)",
    vendor="NVIDIA",
    architecture="Blackwell Ultra (dual-die)",
    process="TSMC 4NP",
    die_size="2 × reticle-limited dies (~1600 mm² total)",
    transistors="208 B (104 B per die)",
    year=2025,
    width=130,
    height=64,
    overview=L(
        novice=(
            "This is a mid-generation refresh of the two-chips-fused design "
            "on the B200 tab, and comparing the two shows what a refresh "
            "actually changes. The silicon is the same size and shape; what "
            "improved is how much of it works — manufacturing matured enough "
            "to switch on every arithmetic unit instead of keeping some "
            "disabled as insurance against defects — and how much memory "
            "sits beside it, because the memory stacks grew taller: twelve "
            "layers of chips per stack instead of eight. Half again more "
            "memory matters because an AI model must fit next to the "
            "processor to run fast, so memory size decides which models a "
            "chip can serve at all."
        ),
        plain=(
            "The mid-generation refresh of the dual-die Blackwell. Same two "
            "reticle-limited dies fused by the 10 TB/s link down the centre, "
            "but manufacturing matured: all 160 streaming multiprocessors "
            "are enabled where B200 shipped 148, and the memory stacks grew "
            "from eight layers to twelve — 288 GB per GPU, half again B200's "
            "192. The tensor cores also double their 4-bit-float throughput. "
            "NVIDIA pitches it at inference on long-running reasoning "
            "models, where resident memory decides what fits."
        ),
        standard=(
            "The Blackwell mid-generation refresh: the same two "
            "reticle-limited dies fused by NV-HBI at 10 TB/s, matured — all "
            "160 SMs enabled (B200 ships 148), 12-high HBM3e stacks for "
            "288 GB (B200: 192), and doubled dense-FP4 tensor throughput. "
            "Aimed at reasoning-model inference, where resident capacity "
            "decides what fits. The GB300 NVL72 rack fuses 72 of these, as "
            "the XE9712 twin shows for GB200."
        ),
        technical=(
            "Blackwell Ultra: the GB200 silicon matured. All 160 SMs enabled "
            "across both dies (vs 148 on B200), 12-Hi HBM3e for 288 GB at "
            "~8 TB/s, ~1.5× dense FP4 tensor throughput, NVLink 5 at "
            "1.8 TB/s unchanged. The capacity bump, not bandwidth, is the "
            "headline — KV caches and reasoning-length contexts stay "
            "resident. Scales to the GB300 NVL72 domain."
        ),
        expert=(
            "GB300: GB200 silicon, full 160-SM enablement, 12-Hi HBM3e → "
            "288 GB @ ~8 TB/s, ~1.5× dense FP4, NVLink 5 @ 1.8 TB/s. "
            "Capacity refresh for reasoning inference; NVL72 domain "
            "unchanged."
        ),
    ),
    regions=[
        DieRegion(id="io", kind="io", label="Host Interface · GigaThread Engine",
                  x=2, y=2, w=126, h=5,
                  description=_IO_DESC_GB),
        *[DieRegion(id=f"hbm-l{i}", kind="mem", label="HBM3e 12-Hi",
                    x=2, y=8 + i * 12.4, w=7, h=10.9,
                    description=_HBM3E_12HI_DESC, photo=P_GP100_PKG)
          for i in range(4)],
        *[DieRegion(id=f"hbm-r{i}", kind="mem", label="HBM3e 12-Hi",
                    x=121, y=8 + i * 12.4, w=7, h=10.9,
                    description=_HBM3E_12HI_DESC, photo=P_GP100_PKG)
          for i in range(4)],
        DieRegion(id="nvhbi", kind="fabric", label="NV-HBI",
                  x=63.25, y=8, w=3.5, h=49, photo=P_GB200_BOARD,
                  description=_NVHBI_DESC_GB300),
        DieRegion(id="l2-a", kind="l2", label="L2 · 63 MB",
                  x=10, y=30, w=52.5, h=4.5,
                  description=_L2_DESC_GB),
        DieRegion(id="l2-b", kind="l2", label="L2 · 63 MB",
                  x=67.5, y=30, w=52.5, h=4.5,
                  description=_L2_DESC_GB),
        *_gpc_row("gpc-lt", 2, 10, 62.5, 8, 21, "GPC · ~20 SM", _GPC_DESC_GB300,
                  photo=P_GB200_BOARD),
        *_gpc_row("gpc-lb", 2, 10, 62.5, 35.5, 21, "GPC · ~20 SM", _GPC_DESC_GB300,
                  photo=P_GB200_BOARD),
        *_gpc_row("gpc-rt", 2, 67.5, 120, 8, 21, "GPC · ~20 SM", _GPC_DESC_GB300,
                  photo=P_GB200_BOARD),
        *_gpc_row("gpc-rb", 2, 67.5, 120, 35.5, 21, "GPC · ~20 SM", _GPC_DESC_GB300,
                  photo=P_GB200_BOARD),
        DieRegion(id="nvlink", kind="nvlink", label="NVLink 5 × 18",
                  x=2, y=58, w=126, h=4, photo=P_NVLINK_CARDS,
                  description=_NVLINK_DESC_GB300),
    ],
    stats=[
        Stat(label="SMs (enabled)", value="160 of 160"),
        Stat(label="FP32 cores", value="20 480"),
        Stat(label="Dense FP4", value="~15 PFLOPS (~1.5× B200)"),
        Stat(label="L2 cache", value="126 MB"),
        Stat(label="Memory", value="288 GB HBM3e 12-Hi · 8 TB/s"),
        Stat(label="NVLink 5", value="1.8 TB/s"),
    ],
    photo=P_GB200_BOARD,
    sources=[
        SourceLink(label="NVIDIA Blackwell Ultra (GB300) page",
                   url="https://www.nvidia.com/en-us/data-center/gb300-nvl72/"),
        SourceLink(label="NVIDIA blog: Blackwell Ultra for the Era of AI Reasoning",
                   url="https://developer.nvidia.com/blog/nvidia-blackwell-ultra-for-the-era-of-ai-reasoning/"),
        SourceLink(label="Wikipedia: Blackwell (microarchitecture)",
                   url="https://en.wikipedia.org/wiki/Blackwell_(microarchitecture)"),
    ],
)

_XCD_DESC = L(
    novice=(
        "An Accelerator Complex Die — a small compute chiplet carrying 38 "
        "Compute Units (AMD's equivalent of NVIDIA's SMs, the GPU's "
        "processing engines; 40 are built and 2 kept as spares against "
        "manufacturing defects). Eight of these chiplets are stacked "
        "vertically on top of the base dies, like buildings over a shared "
        "foundation, for 304 Compute Units in all."
    ),
    standard=(
        "Accelerator Complex Die: a 115 mm² TSMC 5nm compute chiplet carrying 38 "
        "CDNA 3 Compute Units (40 physical, 2 spared for yield). Eight XCDs are "
        "3D-stacked on top of the base I/O dies — 304 CUs total."
    ),
    expert=(
        "XCD: 115 mm² N5 chiplet, 38/40 CDNA 3 CUs (2 yield spares); 8× "
        "3D-stacked on the IODs → 304 CU."
    ),
)

_IOD_DESC = L(
    novice=(
        "One of four base slabs of silicon the whole package is built on. "
        "Each carries a quarter of the 256 MB cache (fast memory that "
        "spares trips to the memory stacks), two memory interfaces, and the "
        "internal fabric that joins the four quadrants. The compute "
        "chiplets are stacked directly on top — AMD building upward, where "
        "NVIDIA's dual-die designs join sideways."
    ),
    standard=(
        "Base I/O Die (one of four, TSMC 6nm): carries a quarter of the 256 MB "
        "Infinity Cache, two HBM3 PHYs, and the Infinity Fabric that stitches "
        "the quadrants together. The XCD compute chiplets are stacked directly "
        "on top — the third dimension AMD uses where NVIDIA's NV-HBI goes "
        "sideways."
    ),
    expert=(
        "IOD (×4, N6): ¼ of 256 MB IC, 2× HBM3 PHY, IF quadrant stitch; "
        "XCDs stacked on top — vertical where NV-HBI is lateral."
    ),
)

_IO_DESC_MI300X = L(
    novice=(
        "The chip's connections outward: the PCIe link to the host computer, "
        "plus seven Infinity Fabric links — AMD's dedicated chip-to-chip "
        "connection, each moving about 128 gigabytes per second. They are "
        "how eight of these accelerators on one server board talk to each "
        "other directly, playing the role NVLink plays for NVIDIA."
    ),
    standard=(
        "Host PCIe 5.0 x16 plus seven Infinity Fabric links (~128 GB/s "
        "each) — how eight MI300Xs in a UBB8 board mesh together, AMD's "
        "counterpart to NVLink."
    ),
    expert="PCIe 5.0 x16 + 7× IF links (~128 GB/s ea) — the UBB8 mesh; AMD's NVLink.",
)

_HBM3_DESC_MI300X = L(
    novice=(
        "A controller for one stack of HBM3 — High Bandwidth Memory, DRAM "
        "stacked vertically beside the processor — built into the base "
        "dies. Eight stacks ring the package, together holding 192 GB and "
        "moving 5.3 terabytes per second."
    ),
    standard=(
        "HBM3 memory controller + PHY on the base dies. Eight 1024-bit "
        "stacks ring the package: 192 GB, 5.3 TB/s aggregate."
    ),
    expert="HBM3 ctrl+PHY on the IODs; 8× 1024-bit stacks → 192 GB, 5.3 TB/s.",
)

_BOND_DESC_MI300X = L(
    novice=(
        "The bonding layer where the compute chiplets sit on the base dies: "
        "millions of microscopic vertical connections made by fusing the "
        "silicon surfaces directly together. It does the same job as the "
        "side-by-side links in the other multi-chip designs here, but in "
        "the third dimension."
    ),
    standard=(
        "The hybrid-bond interface between the base I/O dies and the "
        "compute chiplets stacked on them — vertical wires by the million, "
        "the 3D counterpart of Navi 31's lateral Infinity Fanout and "
        "NVIDIA's NV-HBI."
    ),
    expert=(
        "Hybrid-bond IOD↔XCD interface — millions of vertical wires; the "
        "3D analogue of Infinity Fanout / NV-HBI."
    ),
)

MI300X_DIE = DieAnatomy(
    id="mi300x",
    name="Instinct MI300X",
    vendor="AMD",
    architecture="CDNA 3 (3D chiplet)",
    process="TSMC 5nm XCDs on 6nm IODs",
    die_size="8 × 115 mm² XCD + 4 IODs (~1017 mm² silicon)",
    transistors="153 B",
    year=2023,
    width=100,
    height=62,
    overview=L(
        novice=(
            "AMD's answer to the data-centre chips on the other tabs, and "
            "the most extreme example here of building a processor out of "
            "pieces. The gaming chiplet design elsewhere in this app places "
            "its pieces side by side; this one also stacks them vertically. "
            "Four base slabs of silicon hold the cache and the memory "
            "connections, and eight compute chiplets are stacked directly on "
            "top of them, like buildings over a shared foundation. Stacking "
            "shortens the wires between compute and cache to fractions of a "
            "millimetre. Around the outside sit eight towers of memory — "
            "more than any of the NVIDIA parts here carry — which is the "
            "card's main selling point: bigger AI models fit beside the "
            "processor without splitting them across machines."
        ),
        plain=(
            "AMD's data-centre accelerator, and the most aggressive chiplet "
            "construction in this app: where the gaming Navi 31 places its "
            "chiplets side by side, MI300X stacks them. Four base I/O dies "
            "carry a 256 MB cache and the memory controllers; eight compute "
            "chiplets with 304 compute units total are 3D-stacked on top; "
            "eight stacks of HBM3 ring the package for 192 GB at 5.3 TB/s — "
            "more resident memory than H100 or B200, which is the card's "
            "pitch: models that fit on one GPU instead of two."
        ),
        standard=(
            "AMD's data-center accelerator and the most aggressive chiplet "
            "build here: Navi 31 places chiplets side by side, MI300X stacks "
            "them. Four base I/O dies carry the 256 MB Infinity Cache and "
            "HBM controllers; eight 5nm XCDs (304 CUs) are 3D-stacked on "
            "top; eight HBM3 stacks ring the package — 192 GB at 5.3 TB/s, "
            "more resident memory than H100 or B200. The same silicon also "
            "ships as MI300A with CPU chiplets swapped in."
        ),
        technical=(
            "CDNA 3 flagship: four 6nm base IODs (256 MB Infinity Cache, "
            "eight HBM3 PHYs, Infinity Fabric) with eight 5nm XCDs "
            "3D-stacked on top — 304 CUs, 19,456 SPs. 192 GB HBM3 at "
            "5.3 TB/s. Vertical stacking is AMD's answer to the reticle "
            "limit where NV-HBI goes sideways; MI300A swaps three XCDs for "
            "Zen 4 CCDs on the same base."
        ),
        expert=(
            "MI300X: 4× IOD (256 MB IC, HBM PHYs, IF) + 8× XCD 3D-stacked, "
            "304 CU / 19,456 SP, 192 GB HBM3 @ 5.3 TB/s, 7× IF links. "
            "Vertical disaggregation vs NV-HBI's lateral fuse; MI300A is "
            "the APU variant on the same base."
        ),
    ),
    regions=[
        DieRegion(id="io", kind="io", label="PCIe Gen5 · Infinity Fabric ×7",
                  x=2, y=2, w=96, h=5,
                  description=_IO_DESC_MI300X),
        *[DieRegion(id=f"hbm-l{i}", kind="mem", label="HBM3",
                    x=2, y=8 + i * 12.9, w=7, h=11.7, photo=P_GP100_PKG,
                    description=_HBM3_DESC_MI300X)
          for i in range(4)],
        *[DieRegion(id=f"hbm-r{i}", kind="mem", label="HBM3",
                    x=91, y=8 + i * 12.9, w=7, h=11.7, photo=P_GP100_PKG,
                    description=_HBM3_DESC_MI300X)
          for i in range(4)],
        *_gpc_row("xcd-t", 4, 10, 90, 8, 20, "XCD · 38 CU", _XCD_DESC),
        DieRegion(id="ic", kind="cache", label="INFINITY CACHE · 256 MB (on 4 IODs)",
                  x=10, y=29.5, w=80, h=5,
                  description=_IOD_DESC),
        *_gpc_row("xcd-b", 4, 10, 90, 36, 20, "XCD · 38 CU", _XCD_DESC),
        DieRegion(id="fabric", kind="fabric", label="IOD ↔ XCD 3D bond",
                  x=10, y=57.5, w=80, h=3,
                  description=_BOND_DESC_MI300X),
    ],
    stats=[
        Stat(label="Compute units", value="304 (19 456 SPs)"),
        Stat(label="Chiplets", value="8 XCD + 4 IOD"),
        Stat(label="Infinity Cache", value="256 MB (on IODs)"),
        Stat(label="Memory", value="192 GB HBM3 · 5.3 TB/s"),
        Stat(label="Infinity Fabric", value="7 links · ~128 GB/s each"),
        Stat(label="Matrix FP16", value="1.3 PFLOPS"),
    ],
    sources=[
        SourceLink(label="AMD CDNA 3 Architecture Whitepaper",
                   url="https://www.amd.com/content/dam/amd/en/documents/instinct-tech-docs/white-papers/amd-cdna-3-white-paper.pdf"),
        SourceLink(label="TechPowerUp GPU DB: MI300X",
                   url="https://www.techpowerup.com/gpu-specs/radeon-instinct-mi300x.c4179"),
        SourceLink(label="Chips and Cheese: MI300 — chiplets to the max",
                   url="https://chipsandcheese.com/p/amds-cdna-3-compute-architecture"),
    ],
)

ANATOMIES: dict[str, DieAnatomy] = {
    a.id: a for a in (GH100, GA100, AD102, NAVI31, GB200, GB300, GB202,
                      MI300X_DIE)
}
