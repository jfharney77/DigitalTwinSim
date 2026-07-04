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


_GPC_DESC_GH100 = (
    "Graphics Processing Cluster: 9 TPCs = 18 SMs. Each Hopper SM has 128 "
    "FP32 CUDA cores, 4 fourth-gen Tensor Cores, 256 KB L1/shared memory, "
    "and a Tensor Memory Accelerator (TMA)."
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
    overview=(
        "NVIDIA's Hopper flagship. 8 GPCs (144 SMs on the full die; 132 "
        "enabled on H100 SXM) surround a split 60 MB L2, with three HBM3 "
        "stacks on each edge feeding a 6144-bit bus (~3.35 TB/s) and 18 "
        "NVLink 4 ports along the bottom for GPU-to-GPU traffic."
    ),
    regions=[
        DieRegion(id="io", kind="io", label="PCIe Gen5 · GigaThread Engine",
                  x=2, y=2, w=96, h=5,
                  description=("Host interface (PCIe 5.0 x16) plus the "
                               "GigaThread Engine, the global scheduler that "
                               "distributes thread blocks to GPCs.")),
        *[DieRegion(id=f"hbm-l{i}", kind="mem", label="HBM3",
                    x=2, y=8 + i * 16.8, w=7, h=15.3, photo=P_GP100_PKG,
                    description=("HBM3 memory controller + PHY. One 1024-bit "
                                 "stack interface; GH100 has six (five "
                                 "enabled on H100 SXM), 3.35 TB/s total."))
          for i in range(3)],
        *[DieRegion(id=f"hbm-r{i}", kind="mem", label="HBM3",
                    x=91, y=8 + i * 16.8, w=7, h=15.3, photo=P_GP100_PKG,
                    description=("HBM3 memory controller + PHY. One 1024-bit "
                                 "stack interface; GH100 has six (five "
                                 "enabled on H100 SXM), 3.35 TB/s total."))
          for i in range(3)],
        DieRegion(id="l2-a", kind="l2", label="L2 · 25 MB",
                  x=10, y=30, w=39, h=4.5,
                  description=("Half of the 60 MB L2 (50 MB enabled on "
                               "H100). Physically split in two so each half "
                               "sits close to the memory controllers it "
                               "serves.")),
        DieRegion(id="l2-b", kind="l2", label="L2 · 25 MB",
                  x=51, y=30, w=39, h=4.5,
                  description=("Half of the 60 MB L2 (50 MB enabled on "
                               "H100). Physically split in two so each half "
                               "sits close to the memory controllers it "
                               "serves.")),
        *_gpc_row("gpc-t", 4, 10, 90, 8, 21, "GPC · 18 SM", _GPC_DESC_GH100,
                  photo=P_GA100_DIE),
        *_gpc_row("gpc-b", 4, 10, 90, 35.5, 21, "GPC · 18 SM", _GPC_DESC_GH100,
                  photo=P_GA100_DIE),
        DieRegion(id="nvlink", kind="nvlink", label="NVLink 4 × 18",
                  x=2, y=58, w=96, h=4, photo=P_NVLINK_CARDS,
                  description=("18 fourth-generation NVLink ports, 900 GB/s "
                               "aggregate — how H100s in a DGX/HGX node talk "
                               "to each other without going through PCIe.")),
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

_GPC_DESC_GA100 = (
    "Graphics Processing Cluster: 8 TPCs = 16 SMs. Each Ampere SM has 64 "
    "FP32 CUDA cores, 4 third-gen Tensor Cores, and 192 KB L1/shared memory."
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
    overview=(
        "Hopper's predecessor and the template for NVIDIA's data-center "
        "floorplan: 8 GPCs (128 SMs full, 108 enabled on A100) around a "
        "split 40 MB L2, six HBM2e stacks on the flanks, and 12 NVLink 3 "
        "ports on the bottom edge."
    ),
    regions=[
        DieRegion(id="io", kind="io", label="PCIe Gen4 · GigaThread Engine",
                  x=2, y=2, w=96, h=5,
                  description=("Host interface (PCIe 4.0 x16) plus the "
                               "GigaThread Engine global scheduler.")),
        *[DieRegion(id=f"hbm-l{i}", kind="mem", label="HBM2e",
                    x=2, y=8 + i * 16.8, w=7, h=15.3, photo=P_GP100_PKG,
                    description=("HBM2e memory controller + PHY. Six 1024-bit "
                                 "stack interfaces on the die (five enabled "
                                 "on A100), ~2 TB/s on the 80 GB part."))
          for i in range(3)],
        *[DieRegion(id=f"hbm-r{i}", kind="mem", label="HBM2e",
                    x=91, y=8 + i * 16.8, w=7, h=15.3, photo=P_GP100_PKG,
                    description=("HBM2e memory controller + PHY. Six 1024-bit "
                                 "stack interfaces on the die (five enabled "
                                 "on A100), ~2 TB/s on the 80 GB part."))
          for i in range(3)],
        DieRegion(id="l2-a", kind="l2", label="L2 · 20 MB",
                  x=10, y=30, w=39, h=4.5, photo=P_GA100_DIE,
                  description=("Half of the 40 MB L2, physically split so "
                               "each half sits near the HBM controllers it "
                               "serves — Ampere introduced this split-L2 "
                               "layout.")),
        DieRegion(id="l2-b", kind="l2", label="L2 · 20 MB",
                  x=51, y=30, w=39, h=4.5, photo=P_GA100_DIE,
                  description=("Half of the 40 MB L2, physically split so "
                               "each half sits near the HBM controllers it "
                               "serves — Ampere introduced this split-L2 "
                               "layout.")),
        *_gpc_row("gpc-t", 4, 10, 90, 8, 21, "GPC · 16 SM", _GPC_DESC_GA100,
                  photo=P_GA100_DIE),
        *_gpc_row("gpc-b", 4, 10, 90, 35.5, 21, "GPC · 16 SM", _GPC_DESC_GA100,
                  photo=P_GA100_DIE),
        DieRegion(id="nvlink", kind="nvlink", label="NVLink 3 × 12",
                  x=2, y=58, w=96, h=4, photo=P_NVLINK_CARDS,
                  description=("12 third-generation NVLink ports, 600 GB/s "
                               "aggregate.")),
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

_GPC_DESC_AD102 = (
    "Graphics Processing Cluster: 6 TPCs = 12 SMs, plus a raster engine and "
    "16 ROPs. Each Ada SM has 128 FP32 cores, a 3rd-gen RT core, and 4 "
    "4th-gen Tensor Cores."
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
    overview=(
        "The consumer flagship layout: no HBM, no NVLink. Twelve GDDR6X "
        "controllers wrap the left, right, and bottom edges; a huge central "
        "96 MB L2 (16× Ampere's) compensates for the narrower 384-bit bus; "
        "12 GPCs fill the space above and below it, with media engines and "
        "display up top."
    ),
    regions=[
        DieRegion(id="io", kind="io", label="PCIe Gen4 · Display",
                  x=2, y=2, w=58, h=5,
                  description=("Host interface (PCIe 4.0 x16) and display "
                               "engine (DP 1.4a / HDMI 2.1 heads).")),
        DieRegion(id="media", kind="media", label="NVENC ×2 · NVDEC",
                  x=61, y=2, w=37, h=5,
                  description=("Fixed-function video engines: dual AV1/H.265 "
                               "encoders and a decoder — independent of the "
                               "GPCs, which is why streaming barely costs "
                               "shader performance.")),
        *[DieRegion(id=f"gddr-l{i}", kind="mem", label="GDDR6X",
                    x=2, y=8 + i * 14.9, w=6, h=13.7, photo=P_GDDR6_PCB,
                    description=("Two 32-bit GDDR6X controllers + PHY. "
                                 "Twelve total ring the die for a 384-bit "
                                 "bus, ~1 TB/s."))
          for i in range(4)],
        *[DieRegion(id=f"gddr-r{i}", kind="mem", label="GDDR6X",
                    x=92, y=8 + i * 14.9, w=6, h=13.7, photo=P_GDDR6_PCB,
                    description=("Two 32-bit GDDR6X controllers + PHY. "
                                 "Twelve total ring the die for a 384-bit "
                                 "bus, ~1 TB/s."))
          for i in range(4)],
        *[DieRegion(id=f"gddr-b{i}", kind="mem", label="GDDR6X",
                    x=10 + i * 20.25, y=69.5, w=19.5, h=4.5, photo=P_GDDR6_PCB,
                    description=("Two 32-bit GDDR6X controllers + PHY. "
                                 "Twelve total ring the die for a 384-bit "
                                 "bus, ~1 TB/s."))
          for i in range(4)],
        DieRegion(id="l2", kind="l2", label="L2 CACHE · 96 MB",
                  x=9.5, y=35, w=81, h=7.5, photo=P_AD102_DIE,
                  description=("Ada's defining block: 96 MB of central L2 "
                               "(72 MB enabled on the 4090), 16× GA102's. A "
                               "giant on-die cache trades area for DRAM "
                               "traffic — the same bandwidth economics this "
                               "app's tiling/roofline model demonstrates.")),
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

_SE_DESC_NAVI31 = (
    "Shader Engine: 8 WGPs = 16 dual-issue RDNA 3 Compute Units (1024 "
    "stream processors) plus a raster unit, primitive unit, and 32 ROPs."
)

_MCD_DESC = (
    "Memory Cache Die — a separate 37 mm² chiplet on TSMC 6nm carrying 16 MB "
    "of Infinity Cache and a 64-bit GDDR6 PHY. Six MCDs give a 384-bit bus "
    "and 96 MB of cache; splitting them off keeps the expensive 5nm die "
    "purely compute."
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
    overview=(
        "The first chiplet gaming GPU. A central Graphics Compute Die holds "
        "six shader engines (96 CUs); memory controllers and Infinity Cache "
        "are broken out into six MCD chiplets flanking it, wired over "
        "Infinity Fanout links at ~5.3 TB/s. Compare with the monolithic "
        "NVIDIA dies, where L2 and PHYs share the die with the SMs."
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
                  description=("Infinity Fanout links: dense organic-substrate "
                               "wiring between GCD and MCDs, ~5.3 TB/s "
                               "aggregate — an off-die bandwidth problem the "
                               "monolithic dies don't have.")),
        DieRegion(id="fanout-r", kind="fabric", label="",
                  x=87, y=4, w=1.5, h=46.2,
                  description=("Infinity Fanout links: dense organic-substrate "
                               "wiring between GCD and MCDs, ~5.3 TB/s "
                               "aggregate — an off-die bandwidth problem the "
                               "monolithic dies don't have.")),
        DieRegion(id="frontend", kind="io", label="Command Processor · Geometry · PCIe Gen4",
                  x=13.5, y=4, w=73, h=5,
                  description=("GCD front end: command processor, geometry "
                               "engine, and host PCIe interface — AMD's "
                               "counterpart to NVIDIA's GigaThread Engine.")),
        *_gpc_row("se-t", 3, 13.5, 86.5, 10.2, 16.5,
                  "Shader Engine · 16 CU", _SE_DESC_NAVI31, photo=P_NAVI22_DIE),
        *_gpc_row("se-b", 3, 13.5, 86.5, 27.9, 16.5,
                  "Shader Engine · 16 CU", _SE_DESC_NAVI31, photo=P_NAVI22_DIE),
        DieRegion(id="media", kind="media", label="Media Engine · Display (Radiance)",
                  x=13.5, y=45.6, w=73, h=4.6,
                  description=("Dual media engines (AV1 encode/decode) and "
                               "the DisplayPort 2.1 display engine, on the "
                               "GCD's bottom edge.")),
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

_GPC_DESC_GB100 = (
    "Blackwell SM cluster (~20 SMs; NVIDIA has not published the exact GPC "
    "partitioning). Each die carries 80 SMs physically, 74 enabled on B200, "
    "with 5th-gen Tensor Cores adding FP4/FP6 precisions."
)

_HBM3E_DESC = (
    "HBM3e memory controller + PHY. Four 1024-bit stacks per die — eight "
    "across the package — for 192 GB and ~8 TB/s aggregate bandwidth."
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
    overview=(
        "NVIDIA's first multi-die GPU: two reticle-limited compute dies "
        "fused into one logical GPU by NV-HBI, a 10 TB/s die-to-die link "
        "down the center — software sees a single 148-SM device. Four HBM3e "
        "stacks flank each die (192 GB, ~8 TB/s), with 126 MB of L2 and "
        "NVLink 5 at 1.8 TB/s. The GB200 superchip pairs two of these GPUs "
        "with a Grace CPU."
    ),
    regions=[
        DieRegion(id="io", kind="io", label="Host Interface · GigaThread Engine",
                  x=2, y=2, w=126, h=5,
                  description=("Host interface and global scheduler, "
                               "spanning both dies — one logical GPU "
                               "front-end despite the split silicon.")),
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
                  description=("NV-High Bandwidth Interface: the 10 TB/s "
                               "die-to-die fabric that stitches the two "
                               "reticle-limited dies into one coherent GPU "
                               "— the defining Blackwell block, and NVIDIA's "
                               "answer to hitting the reticle limit that "
                               "AMD's Navi 31 chiplets also work around.")),
        DieRegion(id="l2-a", kind="l2", label="L2 · 63 MB",
                  x=10, y=30, w=52.5, h=4.5,
                  description=("Half of the 126 MB L2. Each die keeps its "
                               "own slice close to its HBM controllers; "
                               "NV-HBI keeps the two halves coherent.")),
        DieRegion(id="l2-b", kind="l2", label="L2 · 63 MB",
                  x=67.5, y=30, w=52.5, h=4.5,
                  description=("Half of the 126 MB L2. Each die keeps its "
                               "own slice close to its HBM controllers; "
                               "NV-HBI keeps the two halves coherent.")),
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
                  description=("18 fifth-generation NVLink ports, 1.8 TB/s "
                               "aggregate — double Hopper, and the backbone "
                               "of the 72-GPU NVL72 rack.")),
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

ANATOMIES: dict[str, DieAnatomy] = {
    a.id: a for a in (GH100, GA100, AD102, NAVI31, GB200)
}
