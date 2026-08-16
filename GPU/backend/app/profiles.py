"""Default GPU profiles. New dies are data, not code (spec §1, principle 4)."""

from __future__ import annotations

from .models import Bandwidth, GpuProfile, Link, Memory, Power, SMGrid, TensorSpec

# spec_25 power blocks: every idle_w / lane_w / byte_w below is a labeled
# ESTIMATE — teaching numbers, not measurements. What is honest is the fleet
# *ratio*: each real die's derived envelope (idle + lane·lanes + byte·bpc)
# lands near the part's public TDP/TGP anchor named in its comment, and the
# idle floors sit in believable proportion (a few watts on the laptop part,
# tens on the SXM/OAM parts). The generic teaching dies keep Power's model
# defaults, exactly as they keep Bandwidth's.

# spec_30: the generic dies carry no die_id on purpose — they are teaching
# abstractions, not silicon; there is nothing in the anatomy museum to link.
GENERIC_128 = GpuProfile(
    name="Generic-128",
    sm=SMGrid(rows=2, cols=4),  # 8 SMs
    cores_per_sm=SMGrid(rows=4, cols=4),  # 16 cores/SM -> 128 lanes
    memory=Memory(stacks=2, label="HBM"),
    has_l2_bus=True,
)

GENERIC_512 = GpuProfile(
    name="Generic-512",
    sm=SMGrid(rows=4, cols=4),  # 16 SMs
    cores_per_sm=SMGrid(rows=4, cols=8),  # 32 cores/SM -> 512 lanes
    memory=Memory(stacks=4, label="HBM"),
    has_l2_bus=True,
)

# The user's real die (spec_07): AD107, Ada Lovelace — 24 SMs x 128 FP32 cores.
# Geometry matches what the driver reports (nvidia-smi sees 24 SMs / 8 GB), so
# the live CUDA mode (spec_08) can light the same tiles the hardware schedules
# blocks onto. Bandwidth is illustrative like everything else, but its *ratio*
# is honest: a 128-bit GDDR6 laptop bus next to strong Ada compute puts the
# roofline ridge point far right of the generic dies — this die goes
# memory-bound at much smaller sizes.
RTX_4060_LAPTOP = GpuProfile(
    name="RTX-4060-Laptop",
    sm=SMGrid(rows=4, cols=6),  # 24 SMs, as on AD107
    cores_per_sm=SMGrid(rows=8, cols=16),  # 128 lanes/SM -> 3072 total
    memory=Memory(stacks=2, label="GDDR6 128-bit"),
    has_l2_bus=True,  # rendered as "L2" — AD107's outsized 32 MB is the point
    # spec_30: no die_id — anatomy.py has no AD107 entry, so the machine's own
    # die is the one floorplan we cannot show. The gap stays visible in the
    # atlas (test_atlas.py pins it) until an AD107 die lands as its own spec.
    bandwidth=Bandwidth(bytes_per_cycle=4, macs_per_cycle=8),
    # spec_24: explicit Ada residency limits (= the model defaults) so lesson
    # 00's device-query reality-check has a pinned counterpart.
    max_threads_per_sm=1536,
    max_blocks_per_sm=24,
    warp_size=32,
    # spec_23: Ada's 4th-gen tensor cores (4 per SM). fp32 is deliberately
    # absent — the scalar path is fp32's home; TF32 is out of scope. Ratios
    # follow NVIDIA's Ada whitepaper dense-throughput table: fp16 2x fp32
    # FLOPS becomes 4x MACs/cycle here (illustrative scale), int8/fp8 = 2x
    # fp16. No fp4 — that dtype is a Blackwell-era property of the die.
    tensor=TensorSpec(
        units_per_sm=4,
        multipliers={"fp16": 4.0, "int8": 8.0, "fp8": 8.0},
    ),
    # spec_25 (estimates): anchor is the 4060 Laptop's ~35–115 W configurable
    # TGP — envelope 5 + 0.02·3072 + 3·4 ≈ 78 W, a laptop-class ceiling with
    # a laptop-class single-digit idle floor.
    power=Power(idle_w=5.0, lane_w=0.02, byte_w=3.0),
)

# --- The wider fleet ---------------------------------------------------------
# Real dies as data. SM counts match the shipping parts (that is the number the
# die view draws and the live mode keys on); lanes per SM are *representative*
# (real SMs have 128 FP32 lanes / real CUs have 64 SPs — drawing thousands of
# rects per state violates the scope guardrail, and above 512 lanes the UI is
# in per-SM dense mode anyway). Bandwidth numbers are illustrative; their
# *ratios* are honest, scaled so each die's ridge point (macs/bytes) orders
# the same way the real parts' FP32-per-byte figures do (~1/10 of real MAC/B):
# RTX 5090 > RTX 4060 > MI300X > H100 > B300.

H100_SXM = GpuProfile(
    name="H100-SXM",
    die_id="gh100",  # spec_30: the anatomy tab's GH100 floorplan is this die
    sm=SMGrid(rows=12, cols=11),  # 132 SMs enabled on H100 SXM (144 physical)
    cores_per_sm=SMGrid(rows=4, cols=8),  # 32 representative lanes (real: 128)
    memory=Memory(stacks=5, label="HBM3"),  # 5 of 6 stacks enabled, ~3.35 TB/s
    has_l2_bus=True,
    bandwidth=Bandwidth(bytes_per_cycle=16, macs_per_cycle=16),  # ridge 1.0
    # spec_24: Hopper's real per-SM residency ceilings (vs Ada's 1536/24).
    max_threads_per_sm=2048,
    max_blocks_per_sm=32,
    # spec_23: Hopper's 4th-gen tensor cores. Per NVIDIA's H100 datasheet the
    # dense ratios are bf16 = fp16, fp8 = int8 = 2x fp16 — and nothing below
    # fp8: fp4 does not exist on this die, which is half the lesson.
    tensor=TensorSpec(
        units_per_sm=4,
        multipliers={"fp16": 4.0, "bf16": 4.0, "int8": 8.0, "fp8": 8.0},
    ),
    # spec_25 (estimates): anchor is the H100 SXM's 700 W TDP — envelope
    # 60 + 0.13·4224 + 6·16 ≈ 705 W, with a tens-of-watts SXM idle floor.
    power=Power(idle_w=60.0, lane_w=0.13, byte_w=6.0),
    # spec_27: NVLink 4 at 900 GB/s. Illustrative rate; the honest ratio is
    # that NVLink 5 (B300) is exactly 2x, and both sit far below HBM's
    # bytes_per_cycle — the link crosses the board, HBM sits on package.
    link=Link(label="NVLink4", bytes_per_cycle=4),
)

B300_ULTRA = GpuProfile(
    name="B300-Blackwell-Ultra",
    die_id="gb300",  # spec_30
    sm=SMGrid(rows=10, cols=16),  # 160 SMs — both reticle-limited dies, fully enabled
    cores_per_sm=SMGrid(rows=4, cols=8),  # 32 representative lanes (real: 128)
    memory=Memory(stacks=8, label="HBM3e"),  # 288 GB, ~8 TB/s
    has_l2_bus=True,
    bandwidth=Bandwidth(bytes_per_cycle=24, macs_per_cycle=12),  # ridge 0.5:
    # HBM3e grew faster than FP32 — the hardest die here to leave memory-bound
    # spec_24: datacenter Blackwell keeps Hopper's 2048/32 residency ceilings.
    max_threads_per_sm=2048,
    max_blocks_per_sm=32,
    # spec_23: 5th-gen tensor cores. Per NVIDIA's Blackwell Ultra datasheet
    # the dense ladder is fp16 -> fp8 -> fp4, each rung ~2x the last — and
    # this is the ONLY die here that declares fp4. Blackwell Ultra dropped
    # int8 tensor throughput to token rates (fp8 is the quantized path), so
    # int8 is deliberately absent.
    tensor=TensorSpec(
        units_per_sm=4,
        multipliers={"fp16": 4.0, "bf16": 4.0, "fp8": 8.0, "fp4": 16.0},
    ),
    # spec_25 (estimates): anchor is Blackwell Ultra's ~1.4 kW per-GPU
    # envelope — 90 + 0.22·5120 + 8·24 ≈ 1408 W. HBM3e's byte_w is the
    # fleet's highest: 8 stacks moving 24 B/cycle is where this die's
    # power increasingly goes.
    power=Power(idle_w=90.0, lane_w=0.22, byte_w=8.0),
    # spec_27: NVLink 5 at 1.8 TB/s = exactly 2x H100's NVLink 4 (900 GB/s) —
    # the one ratio this Link block exists to keep honest.
    link=Link(label="NVLink5", bytes_per_cycle=8),
)

RTX_5090 = GpuProfile(
    name="RTX-5090",
    die_id="gb202",  # spec_30
    sm=SMGrid(rows=10, cols=17),  # 170 SMs enabled on the 5090 (GB202: 192)
    cores_per_sm=SMGrid(rows=4, cols=8),  # 32 representative lanes (real: 128)
    memory=Memory(stacks=2, label="GDDR7 512-bit"),  # ~1.79 TB/s, off-package
    has_l2_bus=True,
    bandwidth=Bandwidth(bytes_per_cycle=8, macs_per_cycle=22),  # ridge 2.75 —
    # the 4060's laptop story at flagship scale: compute grows faster than GDDR
    # spec_23: consumer Blackwell (GB202) 5th-gen tensor cores. fp8 = int8 =
    # 2x fp16 per the RTX Blackwell whitepaper; fp4 stays exclusive to the
    # B300 here (the teaching contrast this fleet exists for).
    tensor=TensorSpec(
        units_per_sm=4,
        multipliers={"fp16": 4.0, "int8": 8.0, "fp8": 8.0},
    ),
    # spec_25 (estimates): anchor is the RTX 5090's 575 W TGP — envelope
    # 30 + 0.093·5440 + 5·8 ≈ 576 W; consumer idle floor below the SXM parts.
    power=Power(idle_w=30.0, lane_w=0.093, byte_w=5.0),
)

MI300X = GpuProfile(
    name="MI300X",
    die_id="mi300x",  # spec_30
    sm=SMGrid(rows=16, cols=19),  # 304 CUs (8 XCD chiplets x 38)
    cores_per_sm=SMGrid(rows=4, cols=4),  # 16 representative lanes (real: 64 SPs)
    memory=Memory(stacks=8, label="HBM3"),  # 192 GB, ~5.3 TB/s
    has_l2_bus=True,  # rendered as "L2" — stands in for the 256 MB Infinity Cache
    bandwidth=Bandwidth(bytes_per_cycle=16, macs_per_cycle=24),  # ridge 1.5
    # spec_24: CDNA 3 per-CU ceilings — 2048 threads / 32 workgroups, and AMD's
    # 64-wide wavefront where NVIDIA has the 32-wide warp.
    max_threads_per_sm=2048,
    max_blocks_per_sm=32,
    warp_size=64,
    # spec_23: CDNA 3 matrix cores (4 per CU). Per AMD's MI300X datasheet the
    # dense ratios are bf16 = fp16, fp8 = int8 = 2x fp16; no fp4 on CDNA 3.
    tensor=TensorSpec(
        units_per_sm=4,
        multipliers={"fp16": 4.0, "bf16": 4.0, "int8": 8.0, "fp8": 8.0},
    ),
    # spec_25 (estimates): anchor is the MI300X OAM's 750 W TDP — envelope
    # 65 + 0.121·4864 + 6·16 ≈ 750 W, idle floor in the H100's neighborhood.
    power=Power(idle_w=65.0, lane_w=0.121, byte_w=6.0),
    # spec_27: no link yet, per the spec's own wording — "MI300X may carry an
    # Infinity-Fabric link later". Until it does, gpus=2 refuses here too.
)

PROFILES: dict[str, GpuProfile] = {
    GENERIC_128.name: GENERIC_128,
    GENERIC_512.name: GENERIC_512,
    RTX_4060_LAPTOP.name: RTX_4060_LAPTOP,
    H100_SXM.name: H100_SXM,
    B300_ULTRA.name: B300_ULTRA,
    RTX_5090.name: RTX_5090,
    MI300X.name: MI300X,
}

DEFAULT_PROFILE = GENERIC_128

# --- spec_30: the profile↔die atlas ------------------------------------------
# The reverse map is DERIVED from PROFILES at import time, never authored
# twice (test_atlas.py pins injectivity and both unmapped sets by name —
# anatomy is a museum, the simulator is a bench; the museum may be bigger).
DIE_TO_PROFILE: dict[str, str] = {
    p.die_id: p.name for p in PROFILES.values() if p.die_id is not None
}

# Substrings a live session's reported device name is checked against, so the
# Live tab can badge a recording with its die's anatomy (e.g. the lesson-07
# goldens report "NVIDIA H100 80GB HBM3" / "NVIDIA B300 288GB HBM3e").
# Served by GET /api/atlas — the frontend hardcodes nothing.
DEVICE_MATCHES: dict[str, list[str]] = {
    H100_SXM.name: ["H100"],
    B300_ULTRA.name: ["B300", "GB300"],
    RTX_5090.name: ["RTX 5090"],
    MI300X.name: ["MI300X"],
}
