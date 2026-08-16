"""spec_25 — the power model and its energy ledger, in the house
conservation-identity idiom: the ledger closes exactly (no tolerance), power
lives inside the profile's derived envelope on every state, stalls burn
above idle while macDone stands still, reuse never costs more joules, the
fleet's power ratios are honest, and the peak_power_w calibration rides the
spec_15 measurement path with no new route.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.engine import analyze, attach_energy, simulate
from app.llm import analyze_llm, simulate_llm
from app.mlp import analyze_mlp, simulate_mlp
from app.models import GpuProfile, Workload
from app.profiles import (
    B300_ULTRA,
    GENERIC_128,
    H100_SXM,
    PROFILES,
    RTX_4060_LAPTOP,
)

APP = Path(__file__).parent.parent / "app"

# A spread of workloads: whole-matrix, tiled, double-buffered, rectangular,
# tensor-mode, plus the chained kinds. (profile, workload) pairs.
CASES: list[tuple[GpuProfile, Workload]] = [
    (GENERIC_128, Workload(kind="matmul", n=8)),
    (GENERIC_128, Workload(kind="matmul", n=8, tile_size=2)),
    (GENERIC_128, Workload(kind="matmul", n=8, tile_size=4, double_buffer=True)),
    (RTX_4060_LAPTOP, Workload(kind="matmul", n=16, tile_size=4, dtype="fp16",
                               execution="tensor")),
    (H100_SXM, Workload(kind="matmul", n=12, m=8, k_dim=16, tile_size=4)),
    (B300_ULTRA, Workload(kind="matmul", n=8, tile_size=2, dtype="fp4",
                          execution="tensor", double_buffer=True)),
    (GENERIC_128, Workload(kind="mlp_step", n=4, steps=2, tile_size=2)),
    (GENERIC_128, Workload(kind="llm_decode", n=4, steps=2, kv_len=8)),
]


def _run(profile: GpuProfile, workload: Workload):
    if workload.kind == "mlp_step":
        trace, _ = simulate_mlp(profile, workload)
        summary = analyze_mlp(profile, workload)
    elif workload.kind == "llm_decode":
        trace, _ = simulate_llm(profile, workload)
        summary = analyze_llm(profile, workload)
    else:
        trace = simulate(profile, workload)
        summary = analyze(profile, workload)
    return trace, attach_energy(summary, trace)


# --- Purity ------------------------------------------------------------------


def test_engine_stays_pure_with_power() -> None:
    """The power model adds no import to engine.py: typing/math machinery,
    functools, and the app's own pure modules only."""
    allowed = {"__future__", "typing", "math", "functools", "app", ""}
    tree = ast.parse((APP / "engine.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                assert a.name.split(".")[0] in allowed, f"impure import {a.name}"
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")[0]
            assert node.level > 0 or mod in allowed, f"impure import {mod}"


# --- The ledger closes exactly ----------------------------------------------


@pytest.mark.parametrize("profile,workload", CASES)
def test_the_ledger_closes_exactly(profile: GpuProfile, workload: Workload):
    trace, summary = _run(profile, workload)
    energy = sum(s.power_watts * s.cycle_cost for s in trace)
    cycles = sum(s.cycle_cost for s in trace)
    assert summary.energy_joules == energy  # no tolerance
    assert summary.avg_power_watts == energy / cycles
    assert summary.joules_per_mac == energy / trace[-1].mac_total


# --- Power lives in the envelope --------------------------------------------


@pytest.mark.parametrize("profile", PROFILES.values(), ids=lambda p: p.name)
def test_power_lives_in_the_envelope(profile: GpuProfile):
    for workload in (
        Workload(kind="matmul", n=8),
        Workload(kind="matmul", n=8, tile_size=2, double_buffer=True),
        Workload(kind="mlp_step", n=4, steps=1),
    ):
        trace, _ = _run(profile, workload)
        env = profile.envelope_watts()
        for s in trace:
            assert profile.power.idle_w <= s.power_watts <= env


# --- Stalls burn without progressing ----------------------------------------


def test_stalls_burn_above_idle_while_mac_done_stands_still():
    trace = simulate(GENERIC_128, Workload(kind="matmul", n=8, tile_size=2))
    stalls = 0
    for prev, s in zip(trace, trace[1:]):
        if s.stalled:
            stalls += 1
            assert s.power_watts > GENERIC_128.power.idle_w
            assert s.mac_done == prev.mac_done  # no progress while burning
    assert stalls > 1  # the lesson actually occurred


# --- Reuse never costs more joules ------------------------------------------


@pytest.mark.parametrize(
    "profile", [GENERIC_128, RTX_4060_LAPTOP], ids=lambda p: p.name
)
def test_whole_matrix_reuse_beats_the_smallest_tile(profile: GpuProfile):
    """Same N, same macTotal — shrinking the tile only ever raises J/MAC:
    the die idles hot through more dwelling loads for identical math."""
    whole = _run(profile, Workload(kind="matmul", n=8))[1]
    for t in (4, 2, 1):
        tiled = _run(profile, Workload(kind="matmul", n=8, tile_size=t))[1]
        assert whole.joules_per_mac <= tiled.joules_per_mac
    smallest = _run(profile, Workload(kind="matmul", n=8, tile_size=1))[1]
    assert whole.joules_per_mac < smallest.joules_per_mac  # strictly


@pytest.mark.parametrize("tile", [1, 2, 4])
@pytest.mark.parametrize("dtype", ["fp32", "fp16", "fp4"])
def test_double_buffering_never_costs_more_joules(tile: int, dtype: str):
    profile = B300_ULTRA if dtype == "fp4" else GENERIC_128
    base = dict(kind="matmul", n=8, tile_size=tile, dtype=dtype)
    serial = _run(profile, Workload(**base))[1]
    pipelined = _run(profile, Workload(**base, double_buffer=True))[1]
    assert pipelined.energy_joules <= serial.energy_joules


# --- Fleet ratios hold, determinism is absolute ------------------------------


def test_fleet_power_ratios_hold():
    assert H100_SXM.envelope_watts() > 5 * RTX_4060_LAPTOP.envelope_watts()
    assert B300_ULTRA.envelope_watts() > H100_SXM.envelope_watts()
    for profile in PROFILES.values():
        assert profile.power.idle_w < profile.envelope_watts()


def test_same_inputs_same_joules():
    for profile, workload in CASES:
        t1, s1 = _run(profile, workload)
        t2, s2 = _run(profile, workload)
        assert s1.energy_joules == s2.energy_joules
        assert [a.power_watts for a in t1] == [b.power_watts for b in t2]


# --- The chained kinds carry consistent power --------------------------------


def test_mlp_trace_power_is_consistent():
    profile = GENERIC_128
    trace, summary = _run(profile, Workload(kind="mlp_step", n=4, steps=2))
    assert trace[0].power_watts == profile.power.idle_w  # idle bookend
    assert trace[-1].power_watts == profile.power.idle_w  # done bookend
    env = profile.envelope_watts()
    for s in trace:
        assert profile.power.idle_w <= s.power_watts <= env
    assert summary.energy_joules == sum(
        s.power_watts * s.cycle_cost for s in trace
    )


def test_llm_trace_power_is_consistent():
    profile = RTX_4060_LAPTOP
    trace, summary = _run(
        profile, Workload(kind="llm_decode", n=4, steps=2, kv_len=8)
    )
    assert trace[0].power_watts == profile.power.idle_w
    assert trace[-1].power_watts == profile.power.idle_w
    env = profile.envelope_watts()
    for s in trace:
        assert profile.power.idle_w <= s.power_watts <= env
    # Restamping (cycle/mac/op fields) must not have disturbed the watts:
    # every load state still reads idle + memory, no lane watts.
    mem_w = profile.power.byte_w * profile.bandwidth.bytes_per_cycle
    stalls = [s for s in trace if s.stalled]
    assert stalls
    for s in stalls:
        assert s.power_watts == profile.power.idle_w + mem_w
    assert summary.energy_joules == sum(
        s.power_watts * s.cycle_cost for s in trace
    )


# --- peak_power_w calibration (spec_15 path, no new route) --------------------


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app import live_store
    from app.main import app

    monkeypatch.setattr(live_store, "SESSIONS_DIR", tmp_path)
    live_store.HUB.stop_session()
    # A prior test's peak must not leak into this tmp store.
    (tmp_path / live_store.MEASUREMENTS_FILE).unlink(missing_ok=True)
    return TestClient(app)


def test_peak_power_measurement_is_accepted(client: TestClient) -> None:
    r = client.post(
        "/api/live/ingest",
        json={"type": "measurement", "metric": "peak_power_w", "value": 67.2,
              "kernel": "lesson06"},
    )
    assert r.status_code == 200
    m = client.get("/api/measurements").json()
    assert m["peak_power_w"]["value"] == 67.2
    assert m["peak_power_w"]["kernel"] == "lesson06"
    assert m["peak_power_w"]["measuredAt"]


def test_unknown_metric_is_still_rejected(client: TestClient) -> None:
    r = client.post(
        "/api/live/ingest",
        json={"type": "measurement", "metric": "vibes", "value": 5},
    )
    assert r.status_code == 422


def test_session_stop_calibrates_peak_from_gpu_samples(
    client: TestClient,
) -> None:
    """gpu_sample.powerW inside a kernel window feeds the calibration when
    the session closes — the transport edge, never the pure fold."""
    client.post("/api/live/session", json={"name": "power-run"})
    # A sample before any kernel is ambient, not a kernel window: ignored.
    client.post("/api/live/ingest", json={"type": "gpu_sample", "powerW": 90})
    client.post(
        "/api/live/ingest",
        json={"type": "kernel_launch", "kernel": "saxpy",
              "grid": [1, 1, 1], "block": [64, 1, 1], "blocks": []},
    )
    for w in (55.0, 61.5, 58.0):
        client.post(
            "/api/live/ingest", json={"type": "gpu_sample", "powerW": w}
        )
    client.delete("/api/live/session")
    m = client.get("/api/measurements").json()
    assert m["peak_power_w"]["value"] == 61.5
    assert m["peak_power_w"]["kernel"] == "saxpy"


def test_no_kernel_no_calibration(client: TestClient) -> None:
    client.post("/api/live/session", json={"name": "idle-run"})
    client.post("/api/live/ingest", json={"type": "gpu_sample", "powerW": 40})
    client.delete("/api/live/session")
    assert "peak_power_w" not in client.get("/api/measurements").json()
