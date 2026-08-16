"""spec_23 — tensor-core mode: MMA stepping and the moving ridge point.

Four contracts pinned here:
- default off: execution="cuda" (and omitted) is byte-for-byte today's path;
- MMA stepping: whole mma_k-rank chunks per compute state, monotonic macDone,
  the partial final chunk landing exactly on macTotal;
- the roofline lesson: multipliers scale macs_per_cycle, never bytes_per_cycle,
  so the ridge point moves right per dtype while intensity is unchanged;
- unsupported dtype x profile pairs 422 at the API edge and the pure engine
  never raises (it falls back to the scalar path).
"""

from __future__ import annotations

import math

import pytest
from fastapi.testclient import TestClient

from app.engine import (
    _ranges,
    analyze,
    effective_tile_size,
    simulate,
)
from app.main import app
from app.mlp import simulate_mlp
from app.llm import analyze_llm, simulate_llm
from app.models import (
    DTYPE_BITS,
    Bandwidth,
    GpuProfile,
    Memory,
    SMGrid,
    TensorSpec,
    Workload,
)
from app.profiles import PROFILES

client = TestClient(app)

TENSOR_DIES = [name for name, p in PROFILES.items() if p.tensor is not None]
SCALAR_DIES = [name for name, p in PROFILES.items() if p.tensor is None]

# A tiny tensor-capable die so stepping tests stay fast (16 lanes per state,
# not 3072). mma shape is the spec's 16x16x16 default.
TINY_TENSOR = GpuProfile(
    name="Tiny-Tensor",
    sm=SMGrid(rows=2, cols=2),
    cores_per_sm=SMGrid(rows=2, cols=2),
    memory=Memory(stacks=1, label="HBM"),
    tensor=TensorSpec(units_per_sm=1, multipliers={"fp16": 4.0, "fp8": 8.0}),
)


# --- default off: byte-for-byte regression -----------------------------------

REGRESSION_WORKLOADS = [
    dict(N=4),
    dict(N=8, tile_size=3, dtype="fp16"),
    dict(N=8, tile_size=3, double_buffer=True, dtype="int8"),
    dict(N=6, M=3, K=5, tile_size=2, dtype="bf16"),
]


@pytest.mark.parametrize("profile_name", list(PROFILES))
@pytest.mark.parametrize("wl", REGRESSION_WORKLOADS)
def test_default_execution_is_byte_for_byte_the_cuda_path(profile_name, wl):
    p = PROFILES[profile_name]
    omitted = Workload(**wl)  # type: ignore[arg-type]
    explicit = Workload(**wl, execution="cuda")  # type: ignore[arg-type]
    assert omitted.execution == "cuda"
    trace_o = simulate(p, omitted)
    trace_e = simulate(p, explicit)
    assert [s.model_dump_json(by_alias=True) for s in trace_o] == [
        s.model_dump_json(by_alias=True) for s in trace_e
    ]
    assert analyze(p, omitted) == analyze(p, explicit)
    # The scalar path never emits the tensor render signal.
    for s in trace_o:
        assert s.mma is False
        assert s.ranks_per_step is None
        assert "mma" not in s.core_state


def test_scalar_summary_numbers_are_pinned_pre_spec23():
    # Hand-computed spec_04 numbers for Generic-128, N=4, fp32, whole-tile:
    # bytes = (16 + 16) * 4 = 128; load = ceil(128/8) = 16;
    # compute = ceil(64/4) = 16; ridge = 4/8 = 0.5; intensity = 64/128 = 0.5.
    s = analyze(PROFILES["Generic-128"], Workload(N=4))  # type: ignore[arg-type]
    assert s.bytes_moved == 128
    assert s.load_cycles_total == 16
    assert s.compute_cycles_total == 16
    assert s.ridge_point == 0.5
    assert s.arithmetic_intensity == 0.5


@pytest.mark.parametrize("dtype,old_bytes", [
    ("fp32", 4), ("fp16", 2), ("bf16", 2), ("int8", 1),
])
def test_bits_generalization_keeps_every_byte_count(dtype, old_bytes):
    # DTYPE_BYTES became DTYPE_BITS for fp4; ceil(cells * bits / 8) must equal
    # cells * bytes exactly for every byte-aligned dtype.
    assert DTYPE_BITS[dtype] == old_bytes * 8
    n = 5  # odd cell counts too
    s = analyze(PROFILES["Generic-128"], Workload(N=n, dtype=dtype))  # type: ignore[arg-type]
    assert s.bytes_moved == 2 * n * n * old_bytes


def test_fp4_bytes_are_half_a_byte_per_element():
    # 2 * 4 * 4 = 32 cells at 4 bits = 16 bytes.
    s = analyze(PROFILES["Generic-128"], Workload(N=4, dtype="fp4"))  # type: ignore[arg-type]
    assert s.bytes_moved == 16


# --- MMA stepping invariants --------------------------------------------------

STEPPING_CASES = [
    (4, 0), (8, 3), (16, 8), (17, 0), (17, 3), (64, 0), (64, 8),
]


@pytest.mark.parametrize("n,tile", STEPPING_CASES)
@pytest.mark.parametrize("dbuf", [False, True])
def test_mma_stepping_invariants(n: int, tile: int, dbuf: bool):
    p = TINY_TENSOR
    mma_k = p.tensor.mma_k  # 16
    w = Workload(N=n, tile_size=tile, double_buffer=dbuf, dtype="fp16",
                 execution="tensor")  # type: ignore[arg-type]
    trace = simulate(p, w)
    total = p.total_cores()

    prev = 0
    for s in trace:
        assert s.mac_done >= prev, "macDone must be monotonic"
        assert s.mac_done <= s.mac_total
        prev = s.mac_done
    last = trace[-1]
    assert last.phase == "done"
    assert last.mac_done == last.mac_total == n**3

    # Compute-state count per (C-tile, k-tile) == ceil(tile_k_span / mma_k),
    # and each group's ranks sum to the span (partial final chunk included).
    t = effective_tile_size(n, tile)
    spans = {ki: k1 - k0 for ki, (k0, k1) in enumerate(_ranges(n, t))}
    groups: dict[tuple, list] = {}
    for s in trace:
        if s.phase == "compute":
            assert s.mma is True
            assert s.ranks_per_step is not None
            assert 1 <= s.ranks_per_step <= mma_k
            groups.setdefault((s.tile_row, s.tile_col, s.k_tile), []).append(s)
    for (_, _, ki), states in groups.items():
        span = spans[ki]
        assert len(states) == math.ceil(span / mma_k)
        assert sum(s.ranks_per_step for s in states) == span

    # Loads are untouched: same bytes at the same rate is the whole point.
    scalar = simulate(p, w.model_copy(update={"execution": "cuda"}))
    assert [s.cycle_cost for s in trace if s.phase == "load"] == [
        s.cycle_cost for s in scalar if s.phase == "load"
    ]

    # Render signal: an MMA lights the owning SM's lanes as one block.
    cps = p.cores_per_sm.rows * p.cores_per_sm.cols
    for s in trace:
        if not s.mma:
            continue
        lit = [i for i, cs in enumerate(s.core_state) if cs != "idle"]
        assert lit and all(s.core_state[i] == "mma" for i in lit)
        for sm_idx in {i // cps for i in lit}:
            block = list(range(sm_idx * cps, (sm_idx + 1) * cps))
            assert all(s.core_state[i] == "mma" for i in block), (
                "a lit SM must light every lane, not individual scalar lanes"
            )
        assert s.active_cores == len(lit) <= total
        assert abs(s.utilization - len(lit) / total) < 1e-9


# --- the roofline lesson ------------------------------------------------------

def test_ridge_moves_right_per_dtype_and_intensity_is_unchanged():
    for name in TENSOR_DIES:
        p = PROFILES[name]
        for dtype, mult in p.tensor.multipliers.items():
            scalar = analyze(p, Workload(N=8, dtype=dtype))  # type: ignore[arg-type]
            tensor = analyze(
                p, Workload(N=8, dtype=dtype, execution="tensor")  # type: ignore[arg-type]
            )
            # Multipliers scale macs_per_cycle, never bytes_per_cycle.
            assert tensor.ridge_point == pytest.approx(
                scalar.ridge_point * mult
            ), (name, dtype)
            assert tensor.bytes_moved == scalar.bytes_moved
            assert tensor.arithmetic_intensity == scalar.arithmetic_intensity
            assert tensor.load_cycles_total == scalar.load_cycles_total
            assert tensor.compute_cycles_total <= scalar.compute_cycles_total
            # The regime can only flip memory-ward, never compute-ward.
            if scalar.regime == "memory":
                assert tensor.regime == "memory", (name, dtype)


def test_ridge_orders_by_dtype_ladder_where_declared():
    for name in TENSOR_DIES:
        p = PROFILES[name]
        ridge = {
            d: analyze(
                p, Workload(N=8, dtype=d, execution="tensor")  # type: ignore[arg-type]
            ).ridge_point
            for d in p.tensor.multipliers
        }
        scalar_ridge = analyze(p, Workload(N=8)).ridge_point  # type: ignore[arg-type]
        ladder = [d for d in ("fp16", "fp8", "fp4") if d in ridge]
        vals = [ridge[d] for d in ladder]
        assert all(a < b for a, b in zip(vals, vals[1:])), (name, ridge)
        assert all(v > scalar_ridge for v in vals), name


def test_pipelined_win_narrows_under_tensor_mode():
    # Less compute to hide loads behind: double-buffering's advantage shrinks.
    p = PROFILES["RTX-4060-Laptop"]
    scalar = analyze(p, Workload(N=8, tile_size=4, dtype="fp16"))  # type: ignore[arg-type]
    tensor = analyze(
        p, Workload(N=8, tile_size=4, dtype="fp16", execution="tensor")  # type: ignore[arg-type]
    )
    assert scalar.serial_cycles - scalar.pipelined_cycles >= (
        tensor.serial_cycles - tensor.pipelined_cycles
    )


def test_fp4_is_a_property_of_the_b300_alone():
    for name, p in PROFILES.items():
        declares_fp4 = p.tensor is not None and "fp4" in p.tensor.multipliers
        assert declares_fp4 == (name == "B300-Blackwell-Ultra"), name
    # And the generic teaching dies stay scalar.
    assert set(SCALAR_DIES) == {"Generic-128", "Generic-512"}


# --- unsupported pairs --------------------------------------------------------

def _simulate_status(profile_name: str, workload: dict):
    body = {
        "profile": PROFILES[profile_name].model_dump(by_alias=True),
        "workload": workload,
    }
    return client.post("/api/simulate", json=body)


@pytest.mark.parametrize("profile_name,dtype", [
    ("H100-SXM", "fp4"),
    ("RTX-4060-Laptop", "fp4"),
    ("RTX-4060-Laptop", "fp32"),
])
def test_unsupported_dtype_is_a_422_naming_the_supported_set(profile_name, dtype):
    r = _simulate_status(
        profile_name, {"N": 4, "dtype": dtype, "execution": "tensor"}
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert profile_name in detail and dtype in detail
    for supported in PROFILES[profile_name].tensor.multipliers:
        assert supported in detail


def test_tensor_on_a_scalar_die_is_a_422():
    r = _simulate_status(
        "Generic-128", {"N": 4, "dtype": "fp16", "execution": "tensor"}
    )
    assert r.status_code == 422
    assert "no tensor units" in r.json()["detail"]


def test_engine_never_raises_on_an_unsupported_pair():
    # Defense in depth: called directly with a pair main.py would have 422'd,
    # the pure engine falls back to the scalar path rather than raising.
    p = PROFILES["H100-SXM"]
    bad = Workload(N=4, dtype="fp4", execution="tensor")  # type: ignore[arg-type]
    good = Workload(N=4, dtype="fp4")  # type: ignore[arg-type]
    assert [s.model_dump_json(by_alias=True) for s in simulate(p, bad)] == [
        s.model_dump_json(by_alias=True) for s in simulate(p, good)
    ]
    assert analyze(p, bad) == analyze(p, good)


def test_supported_pair_succeeds_end_to_end():
    r = _simulate_status(
        "B300-Blackwell-Ultra", {"N": 8, "dtype": "fp4", "execution": "tensor"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["workload"]["execution"] == "tensor"
    assert any(s["mma"] for s in body["trace"])
    assert body["trace"][-1]["macDone"] == 8**3


# --- mlp_step / llm_decode flow through engine.simulate -----------------------

def test_mlp_step_gains_tensor_mode_for_free():
    p = PROFILES["RTX-4060-Laptop"]
    w = Workload(kind="mlp_step", N=4, dtype="fp16", steps=2,
                 execution="tensor")  # type: ignore[arg-type]
    trace, info = simulate_mlp(p, w)
    assert any(s.mma for s in trace)
    assert trace[-1].mac_done == trace[-1].mac_total == 2 * 5 * 4**3
    # Loss numerics stay fp32 — the network still genuinely learns.
    assert info.loss == sorted(info.loss, reverse=True)


def test_llm_decode_gains_tensor_mode_for_free():
    p = PROFILES["H100-SXM"]
    w = Workload(kind="llm_decode", N=4, dtype="fp8", steps=2,
                 kv_len=8, execution="tensor")  # type: ignore[arg-type]
    trace, _info = simulate_llm(p, w)
    assert any(s.mma for s in trace)
    assert trace[-1].mac_done == trace[-1].mac_total
    # Tensor mode shrinks decode's compute term only.
    scalar = analyze_llm(p, w.model_copy(update={"execution": "cuda"}))
    tensor = analyze_llm(p, w)
    assert tensor.compute_cycles_total < scalar.compute_cycles_total
    assert tensor.bytes_moved == scalar.bytes_moved


# --- wire shape ---------------------------------------------------------------

def test_camelcase_wire_keys_match_types_ts():
    p = PROFILES["B300-Blackwell-Ultra"]
    dump = p.model_dump(by_alias=True)
    ts = dump["tensor"]
    # The cores_per_sm gotcha, again: unitsPerSM, not unitsPerSm.
    assert set(ts) == {"unitsPerSM", "mmaM", "mmaN", "mmaK", "multipliers"}
    assert ts["mmaK"] == 16
    w = Workload(N=4, execution="tensor", dtype="fp16")  # type: ignore[arg-type]
    assert w.model_dump(by_alias=True)["execution"] == "tensor"
    s = simulate(PROFILES["RTX-4060-Laptop"], w)[2]
    state = s.model_dump(by_alias=True)
    assert "mma" in state and "ranksPerStep" in state
