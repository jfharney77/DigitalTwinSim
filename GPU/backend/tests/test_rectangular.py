"""Rectangular matmul tests (spec_22 §4).

The gate is back-compat: m=0/k_dim=0 and m=n/k_dim=n must reproduce the square
trace and Summary exactly. Then the rectangular invariants: per-axis tile
counts, accumulation depth K on every C cell, tile-aware mapping, and the
fixed-work intensity comparison that is the whole point of splitting M/K/N.
"""

from __future__ import annotations

import math

import pytest
from fastapi.testclient import TestClient

from app.engine import analyze, resolve_dims, simulate
from app.models import Workload
from app.profiles import GENERIC_128

PHASE_ORDER = ["idle", "load", "compute", "writeback", "done"]


def wl(n: int, m: int = 0, k: int = 0, tile: int = 0, dbuf: bool = False,
       dtype: str = "fp32") -> Workload:
    return Workload(N=n, M=m, K=k, tile_size=tile, double_buffer=dbuf,
                    dtype=dtype)  # type: ignore[arg-type]


# Rectangular shapes with M, K, N pairwise distinct, tiled and not, both
# schedules.
RECT_CASES = [
    (4, 6, 8, 0, False),
    (4, 6, 8, 2, False),
    (4, 6, 8, 3, False),
    (4, 6, 8, 2, True),
    (8, 2, 5, 2, False),
    (8, 2, 5, 2, True),
    (3, 16, 6, 4, False),
]


# --- Byte-for-byte square regression (the gate; land it first) ---------------


@pytest.mark.parametrize(
    "n,tile,dbuf,dtype",
    [
        (4, 0, False, "fp32"),
        (6, 3, False, "fp32"),
        (8, 2, True, "fp16"),
        (5, 2, False, "int8"),
        (8, 4, True, "fp32"),
    ],
)
def test_square_sentinels_reproduce_todays_trace_and_summary(n, tile, dbuf, dtype):
    base_w = Workload(N=n, tile_size=tile, double_buffer=dbuf, dtype=dtype)  # type: ignore[arg-type]
    zero_w = wl(n, 0, 0, tile, dbuf, dtype)
    full_w = wl(n, n, n, tile, dbuf, dtype)

    base = [s.model_dump() for s in simulate(GENERIC_128, base_w)]
    for variant in (zero_w, full_w):
        trace = [s.model_dump() for s in simulate(GENERIC_128, variant)]
        assert trace == base
        assert analyze(GENERIC_128, variant) == analyze(GENERIC_128, base_w)


def test_resolve_dims_sentinel_rule():
    assert resolve_dims(wl(6)) == (6, 6, 6)
    assert resolve_dims(wl(6, 4, 0)) == (4, 6, 6)
    assert resolve_dims(wl(6, 0, 3)) == (6, 3, 6)
    assert resolve_dims(wl(6, 4, 3)) == (4, 3, 6)


def test_dim_bounds_zero_exempt():
    wl(4, 0, 0)  # sentinel ok
    wl(4, 2, 64)  # bounds ok
    with pytest.raises(ValueError):
        Workload(N=4, M=1)
    with pytest.raises(ValueError):
        Workload(N=4, K=65)


# --- Rectangular invariants --------------------------------------------------


@pytest.mark.parametrize("n,m,k,tile,dbuf", RECT_CASES)
def test_mac_totals_and_monotonicity(n, m, k, tile, dbuf):
    trace = simulate(GENERIC_128, wl(n, m, k, tile, dbuf))
    assert trace[-1].mac_total == m * k * n
    assert trace[-1].mac_done == m * k * n
    macs = [s.mac_done for s in trace]
    assert macs == sorted(macs)
    for s in trace:
        assert s.mac_done <= s.mac_total


@pytest.mark.parametrize("n,m,k,tile,dbuf", RECT_CASES)
def test_phase_order_and_cores(n, m, k, tile, dbuf):
    total = GENERIC_128.total_cores()
    trace = simulate(GENERIC_128, wl(n, m, k, tile, dbuf))
    assert trace[0].phase == "idle" and trace[-1].phase == "done"
    for s in trace:
        assert s.phase in PHASE_ORDER
        assert s.active_cores <= total
        assert len(s.core_state) == total
        assert s.utilization == pytest.approx(s.active_cores / total)


@pytest.mark.parametrize("n,m,k,tile", [(4, 6, 8, 2), (4, 6, 8, 3), (8, 2, 5, 2)])
def test_per_axis_load_and_writeback_counts(n, m, k, tile):
    trace = simulate(GENERIC_128, wl(n, m, k, tile))
    row_tiles = math.ceil(m / tile)
    col_tiles = math.ceil(n / tile)
    k_tiles = math.ceil(k / tile)
    loads = [s for s in trace if s.phase == "load"]
    writes = [s for s in trace if s.phase == "writeback"]
    assert len(loads) == row_tiles * col_tiles * k_tiles
    assert len(writes) == row_tiles * col_tiles


@pytest.mark.parametrize("n,m,k,tile,dbuf", RECT_CASES)
def test_every_c_cell_ends_at_depth_k(n, m, k, tile, dbuf):
    # The MatrixPanels replay algorithm, run server-side: each C cell's
    # accumulation depth must finish at exactly K.
    trace = simulate(GENERIC_128, wl(n, m, k, tile, dbuf))
    t = tile if 0 < tile < max(m, k, n) else max(m, k, n)
    depth = [[0] * n for _ in range(m)]
    for s in trace:
        if s.tile_row is None or s.tile_col is None:
            continue
        r0, r1 = s.tile_row * t, min(s.tile_row * t + t, m)
        c0, c1 = s.tile_col * t, min(s.tile_col * t + t, n)
        if s.phase == "compute":
            for i in range(r0, r1):
                for j in range(c0, c1):
                    depth[i][j] = s.k
        elif s.phase == "writeback":
            for i in range(r0, r1):
                for j in range(c0, c1):
                    depth[i][j] = k
    assert all(d == k for row in depth for d in row)
    # ... and no state ever reports an accumulation depth beyond K.
    assert all(s.k <= k for s in trace)


@pytest.mark.parametrize("n,m,k,tile", [(4, 6, 8, 2), (8, 2, 5, 2), (3, 16, 6, 4)])
def test_tile_cells_stay_within_one_sm(n, m, k, tile):
    cores_per_sm = GENERIC_128.cores_per_sm.rows * GENERIC_128.cores_per_sm.cols
    trace = simulate(GENERIC_128, wl(n, m, k, tile))
    for s in trace:
        if s.phase != "compute":
            continue
        active = [i for i, c in enumerate(s.core_state) if c == "computing"]
        sms = {a // cores_per_sm for a in active}
        assert len(sms) <= 1, f"tile ({s.tile_row},{s.tile_col}) straddles SMs {sms}"


def test_rectangular_operands_shape_and_square_regression():
    from app.matrices import make_operands

    a, b = make_operands(6, 0, m=4, k=3)
    assert len(a) == 4 and all(len(row) == 3 for row in a)  # A is M×K
    assert len(b) == 3 and all(len(row) == 6 for row in b)  # B is K×N
    # Indices, not shape, drive the values: square call is bit-identical.
    assert make_operands(4, 2) == make_operands(4, 2, m=4, k=4)


# --- Roofline: the M/K/N lesson ----------------------------------------------


@pytest.mark.parametrize("n,m,k,tile,dbuf", RECT_CASES)
def test_intensity_is_macs_per_byte(n, m, k, tile, dbuf):
    s = analyze(GENERIC_128, wl(n, m, k, tile, dbuf))
    assert s.arithmetic_intensity == pytest.approx(m * k * n / s.bytes_moved)


def test_fixed_work_intensity_comparison():
    # Same total work (M·K·N = 256 MACs), three shapes, untiled: intensity =
    # M·N / ((M+N)·bytes) once K cancels — so the shapes are measurably
    # different even at identical MAC counts. That the numbers move when only
    # the shape moves is the feature.
    tall_skinny = analyze(GENERIC_128, wl(2, 2, 64))  # 2×64×2: long K, few cells
    square = analyze(GENERIC_128, wl(4, 4, 16))  # 4×16×4
    short_fat = analyze(GENERIC_128, wl(8, 8, 4))  # 8×4×8: short K, many cells
    shapes = [tall_skinny, square, short_fat]
    assert all(
        s.arithmetic_intensity == pytest.approx(256 / s.bytes_moved) for s in shapes
    )
    # Fixed work, different bytes moved -> genuinely different intensities.
    intensities = [s.arithmetic_intensity for s in shapes]
    assert len(set(intensities)) == 3
    assert tall_skinny.arithmetic_intensity < square.arithmetic_intensity
    assert square.arithmetic_intensity < short_fat.arithmetic_intensity
    # ... and the regime can flip on shape alone (same MACs, same dtype).
    assert tall_skinny.regime == "memory"
    assert short_fat.regime == "compute"


# --- MLP stays square, loudly ------------------------------------------------


def test_mlp_step_rejects_rectangular_params():
    with pytest.raises(ValueError):
        Workload(kind="mlp_step", N=4, M=6)
    with pytest.raises(ValueError):
        Workload(kind="mlp_step", N=4, K=6)


def test_mlp_step_rectangular_is_422_on_the_wire():
    from app.main import app

    client = TestClient(app)
    profile = GENERIC_128.model_dump(by_alias=True)
    body = {
        "profile": profile,
        "workload": {"kind": "mlp_step", "N": 4, "M": 6},
    }
    r = client.post("/api/simulate", json=body)
    assert r.status_code == 422

    # Square mlp_step (M/K omitted or 0) still works and echoes n thrice.
    body["workload"] = {"kind": "mlp_step", "N": 4}
    r = client.post("/api/simulate", json=body)
    assert r.status_code == 200
    assert (r.json()["m"], r.json()["k"], r.json()["n"]) == (4, 4, 4)


def test_simulate_response_echoes_resolved_dims():
    from app.main import app

    client = TestClient(app)
    profile = GENERIC_128.model_dump(by_alias=True)
    body = {"profile": profile, "workload": {"kind": "matmul", "N": 8, "M": 4, "K": 6}}
    r = client.post("/api/simulate", json=body)
    assert r.status_code == 200
    data = r.json()
    assert (data["m"], data["k"], data["n"]) == (4, 6, 8)
    assert data["macTotal"] == 4 * 6 * 8
    assert len(data["a"]) == 4 and len(data["a"][0]) == 6
    assert len(data["b"]) == 6 and len(data["b"][0]) == 8
