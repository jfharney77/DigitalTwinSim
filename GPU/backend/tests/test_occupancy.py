"""spec_24 — occupancy in the simulator's mental model.

The helper is pure (AST-checked like the engine), the lesson-03 narration is
pinned exactly, defaults change nothing (byte-for-byte trace regression), and
the same arithmetic is cross-tested against the lesson-03 probe fixture the
Live tab replays — one formula, two sources, no GPU required.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from app.engine import analyze, simulate
from app.models import GpuProfile, Workload
from app.occupancy import theoretical_occupancy
from app.profiles import PROFILES, RTX_4060_LAPTOP

APP = Path(__file__).parent.parent / "app"
FIXTURE = Path(__file__).parent / "fixtures" / "probe_samples" / "03_block_size.json"

# The 4060's Ada residency limits (lesson 00's device query pins these).
ADA = dict(max_threads_per_sm=1536, max_blocks_per_sm=24, warp_size=32)

LESSON_SIZES = [32, 64, 128, 256, 512, 1024]


# --- Purity ------------------------------------------------------------------


def test_occupancy_module_is_pure() -> None:
    """occupancy.py may import only typing/math machinery and its own models."""
    allowed = {"typing", "math", "__future__", "models", "occupancy"}
    tree = ast.parse((APP / "occupancy.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                assert a.name.split(".")[0] in allowed, f"impure import {a.name}"
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")[0]
            assert node.level > 0 or mod in allowed, f"impure import {mod}"


# --- Lesson 03, exactly as narrated ------------------------------------------


def test_lesson_03_tiny_blocks_hit_the_block_ceiling() -> None:
    occ = theoretical_occupancy(32, **ADA)
    assert occ.blocks_resident == 24
    assert occ.warps_per_block == 1
    assert occ.occupancy_pct == 50.0
    assert occ.limiter == "blocks"


def test_lesson_03_huge_blocks_hit_the_thread_ceiling() -> None:
    occ = theoretical_occupancy(1024, **ADA)
    assert occ.blocks_resident == 1
    assert occ.warps_per_block == 32
    assert occ.occupancy_pct == pytest.approx(66.7, abs=0.05)  # 1024 of 1536
    assert occ.limiter == "threads"


def test_full_occupancy_names_no_limiter() -> None:
    # 256-thread blocks on Ada: 6 blocks × 8 warps = all 48 slots.
    occ = theoretical_occupancy(256, **ADA)
    assert occ.occupancy_pct == 100.0
    assert occ.limiter == "none"


def test_warp_granularity_is_hardware_like() -> None:
    # A 33-thread block claims 2 warp slots, like the hardware would.
    occ = theoretical_occupancy(33, **ADA)
    assert occ.warps_per_block == 2


def test_occupancy_in_range_for_every_shipped_profile() -> None:
    for profile in PROFILES.values():
        for bs in LESSON_SIZES:
            occ = theoretical_occupancy(
                bs,
                max_threads_per_sm=profile.max_threads_per_sm,
                max_blocks_per_sm=profile.max_blocks_per_sm,
                warp_size=profile.warp_size,
            )
            assert 0 < occ.occupancy_pct <= 100, (profile.name, bs)


# --- Cross-test with the Live tab's lesson-03 fixture ------------------------


def test_lesson_03_fixture_agrees_with_the_helper() -> None:
    """The probe fixture's theoretical occupancyPct is this same formula run
    through the CUDA occupancy API on the 4060 — assert agreement."""
    checked = 0
    for line in FIXTURE.read_text().splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        if ev.get("type") != "kernel_launch" or "occupancyPct" not in ev:
            continue
        bx, by, bz = ev["block"]
        occ = theoretical_occupancy(bx * by * bz, **ADA)
        assert occ.occupancy_pct == pytest.approx(ev["occupancyPct"], abs=0.05)
        checked += 1
    assert checked >= 1  # the fixture must actually exercise this


def test_lesson_03_fixture_is_the_32_thread_story() -> None:
    """Pin the narration: the fixture's bs32 kernel is the block-limited half."""
    launches = [
        json.loads(line)
        for line in FIXTURE.read_text().splitlines()
        if line.strip() and json.loads(line).get("type") == "kernel_launch"
    ]
    with_occ = [ev for ev in launches if "occupancyPct" in ev]
    assert with_occ, "fixture lost its occupancy-bearing launch"
    ev = with_occ[0]
    assert ev["block"][0] == 32
    occ = theoretical_occupancy(32, **ADA)
    assert occ.occupancy_pct == ev["occupancyPct"] == 50.0
    assert occ.limiter == "blocks"


# --- Trace regression: block_size feeds the read-out only --------------------


@pytest.mark.parametrize("n,tile,dtype,dbuf", [
    (4, 0, "fp32", False),
    (6, 2, "fp16", False),
    (8, 3, "int8", True),
])
def test_block_size_never_touches_the_trace(
    n: int, tile: int, dtype: str, dbuf: bool
) -> None:
    """Default (0) and any explicit block_size produce byte-identical traces —
    the knob is a launch-configuration read-out, not a scheduler."""
    profile = RTX_4060_LAPTOP
    base = Workload(n=n, tile_size=tile, dtype=dtype, double_buffer=dbuf)
    baseline = [
        s.model_dump_json(by_alias=True) for s in simulate(profile, base)
    ]
    for bs in (0, 32, 1024):
        w = base.model_copy(update={"block_size": bs})
        got = [s.model_dump_json(by_alias=True) for s in simulate(profile, w)]
        assert got == baseline


def test_profiles_deserialize_without_the_new_fields() -> None:
    """Old profile JSON (no residency limits) still validates, on Ada defaults."""
    p = GpuProfile.model_validate(
        {
            "name": "old",
            "sm": {"rows": 2, "cols": 4},
            "coresPerSM": {"rows": 4, "cols": 4},
            "memory": {"stacks": 2, "label": "HBM"},
        }
    )
    assert (p.max_threads_per_sm, p.max_blocks_per_sm, p.warp_size) == (1536, 24, 32)


# --- Summary exposure + wire casing ------------------------------------------


def test_summary_carries_occupancy_with_camel_keys() -> None:
    summary = analyze(RTX_4060_LAPTOP, Workload(n=4, block_size=32))
    occ = summary.occupancy
    assert occ.occupancy_pct == 50.0
    wire = json.loads(summary.model_dump_json(by_alias=True))
    assert set(wire["occupancy"]) == {
        "blockSize", "warpsPerBlock", "blocksResident", "occupancyPct", "limiter",
    }
    # Profile fields camelize to the DeviceInfo casing live.py already uses.
    pw = json.loads(RTX_4060_LAPTOP.model_dump_json(by_alias=True))
    assert pw["maxThreadsPerSm"] == 1536
    assert pw["maxBlocksPerSm"] == 24
    assert pw["warpSize"] == 32


def test_derived_block_size_is_one_tile_one_block() -> None:
    # T=2 → a 4-cell block: 1 warp resident per block, block-limited on Ada.
    summary = analyze(RTX_4060_LAPTOP, Workload(n=4, tile_size=2))
    assert summary.occupancy.block_size == 4
    assert summary.occupancy.warps_per_block == 1
    assert summary.occupancy.limiter == "blocks"
    # Whole-matrix N=8 → 64-cell block = 2 warps.
    summary = analyze(RTX_4060_LAPTOP, Workload(n=8))
    assert summary.occupancy.block_size == 64
    assert summary.occupancy.warps_per_block == 2
