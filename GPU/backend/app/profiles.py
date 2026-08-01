"""Default GPU profiles. New dies are data, not code (spec §1, principle 4)."""

from __future__ import annotations

from .models import Bandwidth, GpuProfile, Memory, SMGrid

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
    bandwidth=Bandwidth(bytes_per_cycle=4, macs_per_cycle=8),
)

PROFILES: dict[str, GpuProfile] = {
    GENERIC_128.name: GENERIC_128,
    GENERIC_512.name: GENERIC_512,
    RTX_4060_LAPTOP.name: RTX_4060_LAPTOP,
}

DEFAULT_PROFILE = GENERIC_128
