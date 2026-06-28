"""Default GPU profiles. New dies are data, not code (spec §1, principle 4)."""

from __future__ import annotations

from .models import GpuProfile, Memory, SMGrid

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

PROFILES: dict[str, GpuProfile] = {
    GENERIC_128.name: GENERIC_128,
    GENERIC_512.name: GENERIC_512,
}

DEFAULT_PROFILE = GENERIC_128
