"""spec_26 invariants: LLM decode is the matmul that runs out of arithmetic."""

from __future__ import annotations

import ast
import math
from pathlib import Path

import pytest

from app.llm import (
    analyze_llm,
    cache_blocks,
    initial_kv_cache,
    llm_intensity,
    mac_total_decode,
    mac_total_prefill,
    matmul,
    simulate_llm,
    softmax_rows,
)
from app.matrices import make_llm_data
from app.models import Workload
from app.profiles import DEFAULT_PROFILE

# Modules the pure layer may import (mirrors test_live's purity contract; math
# is allowed — engine.py uses it too).
PURE_ALLOWED = {"__future__", "typing", "math", "app", ""}


def run(n: int = 4, steps: int = 1, kv_len: int = 8, **kw):
    wl = Workload(kind="llm_decode", N=n, steps=steps, kvLen=kv_len, **kw)
    return simulate_llm(DEFAULT_PROFILE, wl)


def expected_names(n: int, s: int) -> list[str]:
    """The a1..a13 op list for one decode token at cache length S, with the
    attention ops expanded to their B cache blocks in order (spec_26 §4)."""
    b = cache_blocks(s, n)
    return (
        ["Q = X·Wq", "K = X·Wk", "V = X·Wv", "cache append"]
        + [f"S = Q·Kᵀ/√N (block {i + 1}/{b})" for i in range(b)]
        + ["softmax"]
        + [f"A = P·V (block {i + 1}/{b})" for i in range(b)]
        + ["O = A·Wo", "H = norm(X + O)", "Z = H·Wup", "G = gelu(Z)",
           "M = G·Wdown", "X' = H + M"]
    )


def test_llm_module_is_pure() -> None:
    src = (Path(__file__).parent.parent / "app" / "llm.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                assert a.name.split(".")[0] in PURE_ALLOWED, f"impure import {a.name}"
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")[0]
            assert node.level > 0 or mod in PURE_ALLOWED, f"impure import {mod}"
        elif isinstance(node, ast.Call):
            fn = node.func
            assert not (
                isinstance(fn, ast.Name) and fn.id == "open"
            ), "llm.py must not touch files"


def test_mac_total_is_the_specced_sum():
    # macTotal = Σ_t (6 + 2·ceil((kv_len + t)/N))·N³ over tokens t=1..steps.
    for n, kv_len, steps in [(4, 8, 1), (4, 8, 3), (8, 8, 2), (8, 64, 2), (2, 9, 1)]:
        expected = sum(
            (6 + 2 * math.ceil((kv_len + t) / n)) * n**3
            for t in range(1, steps + 1)
        )
        assert mac_total_decode(n, kv_len, steps) == expected
        trace, _ = run(n, steps, kv_len)
        assert all(s.mac_total == expected for s in trace)
        assert trace[-1].phase == "done"
        assert trace[-1].mac_done == expected


def test_prefill_mac_total_is_steps_times_eight_matmuls():
    for n, steps in [(4, 1), (8, 3)]:
        assert mac_total_prefill(n, steps) == steps * 8 * n**3
        trace, info = run(n, steps, prefill=True)
        assert info.prefill
        assert trace[-1].mac_done == steps * 8 * n**3


def test_op_order_is_pinned_per_token():
    steps = 2
    n, kv_len = 4, 8
    trace, info = run(n, steps, kv_len)
    want: list[str] = []
    for t in range(1, steps + 1):
        want += expected_names(n, kv_len + t)
    assert [op.name for op in info.ops] == want
    assert info.ops_per_token == [len(expected_names(n, kv_len + t))
                                  for t in range(1, steps + 1)]
    assert sum(info.ops_per_token) == len(info.ops)
    # 6+2B matmuls and exactly 5 pointwise per token.
    for t in range(1, steps + 1):
        start = sum(info.ops_per_token[: t - 1])
        tok_ops = info.ops[start : start + info.ops_per_token[t - 1]]
        assert sum(1 for o in tok_ops if o.kind == "pointwise") == 5
        assert sum(1 for o in tok_ops if o.kind == "matmul") == 6 + 2 * cache_blocks(
            kv_len + t, n
        )

    # SimState op context marches through ops in order, never backwards, and
    # step_index is the token the op belongs to.
    seen = [s.op_index for s in trace if s.op_index is not None]
    assert seen == sorted(seen)
    assert set(seen) == set(range(len(info.ops)))
    starts = [sum(info.ops_per_token[:i]) for i in range(steps + 1)]
    for s in trace:
        if s.op_index is not None:
            assert s.op_name == info.ops[s.op_index].name
            tok = next(i for i in range(steps) if starts[i] <= s.op_index < starts[i + 1])
            assert s.step_index == tok
            assert s.op_count == len(info.ops)


def test_spec01_invariants_hold_inside_ops():
    trace, _ = run(4, 2, tileSize=2, doubleBuffer=True)
    total_cores = DEFAULT_PROFILE.total_cores()
    prev_mac = 0
    for s in trace:
        assert s.active_cores <= total_cores
        assert s.utilization == pytest.approx(s.active_cores / total_cores)
        assert s.mac_done >= prev_mac  # monotonic across the whole chain
        assert s.mac_done <= s.mac_total
        prev_mac = s.mac_done


def test_intensity_pinned_fall_and_monotone_decrease():
    # The pinned §4 numbers at N=8, fp32: 0.314 < 0.571.
    assert llm_intensity(8, 8, 4) == pytest.approx(0.5714, abs=1e-3)
    assert llm_intensity(8, 64, 4) == pytest.approx(0.3143, abs=1e-3)
    assert llm_intensity(8, 64, 4) < llm_intensity(8, 8, 4)
    # Strict monotone decrease across kv_len for all N >= 4.
    for n in (4, 5, 6, 7, 8):
        vals = [llm_intensity(n, s, 4) for s in range(8, 65)]
        assert all(b < a for a, b in zip(vals, vals[1:])), f"not monotone at n={n}"


def test_regime_flips_across_the_ridge():
    def summary(kv_len: int, prefill: bool = False):
        wl = Workload(kind="llm_decode", N=8, dtype="fp32", kvLen=kv_len,
                      prefill=prefill)
        return analyze_llm(DEFAULT_PROFILE, wl)

    short = summary(8)
    long = summary(64)
    assert short.ridge_point == pytest.approx(0.5)
    assert short.regime == "compute"
    assert long.regime == "memory"
    assert long.arithmetic_intensity < short.arithmetic_intensity
    # Prefill keeps full operand reuse: compute-bound at either cache length.
    assert summary(8, prefill=True).regime == "compute"
    assert summary(64, prefill=True).regime == "compute"


def test_per_token_intensity_falls_and_matches_the_formula():
    _, info = run(8, steps=5, kv_len=8)
    assert info.kv_len == [9, 10, 11, 12, 13]  # S_t = kv_len + t
    for s_len, inten in zip(info.kv_len, info.intensity):
        assert inten == pytest.approx(llm_intensity(8, s_len, 4))
    assert all(b < a for a, b in zip(info.intensity, info.intensity[1:]))


def test_softmax_rows_sum_to_one_and_stay_finite():
    x, (wq, wk, _wv, *_), _ = make_llm_data(8, 16, seed=3)
    scores = matmul(matmul(x, wq), [list(r) for r in zip(*matmul(x, wk))])
    p = softmax_rows(scores)
    for row in p:
        assert sum(row) == pytest.approx(1.0, abs=1e-9)
        assert all(math.isfinite(v) and v >= 0 for v in row)
    # The response's display row is the real thing, not filler.
    for n, kv_len, steps in [(4, 8, 1), (8, 64, 3)]:
        _, info = run(n, steps, kv_len)
        assert len(info.softmax_row) == kv_len + steps
        assert sum(info.softmax_row) == pytest.approx(1.0, abs=1e-9)
        assert all(math.isfinite(v) for v in info.softmax_row)
    for op in info.ops:
        for m in (op.a, op.b):
            if m:
                assert all(math.isfinite(v) for row in m for v in row)


def test_kv_cache_is_really_run_from_the_prompt():
    n, kv_len, seed = 4, 10, 2
    _, (_, wk, wv, *_), prompt = make_llm_data(n, kv_len, seed)
    k_cache, v_cache = initial_kv_cache(n, kv_len, seed)
    assert len(k_cache) == kv_len
    for i in range(kv_len):
        for j in range(n):
            assert k_cache[i][j] == pytest.approx(
                sum(prompt[i][q] * wk[q][j] for q in range(n))
            )
            assert v_cache[i][j] == pytest.approx(
                sum(prompt[i][q] * wv[q][j] for q in range(n))
            )
    # Different seed, different cache — deterministic per seed.
    other, _ = initial_kv_cache(n, kv_len, seed + 1)
    assert other != k_cache
    again, _ = initial_kv_cache(n, kv_len, seed)
    assert again == k_cache


def test_same_seed_same_trace():
    a_trace, a_info = run(4, 2, seed=5)
    b_trace, b_info = run(4, 2, seed=5)
    assert [s.model_dump() for s in a_trace] == [s.model_dump() for s in b_trace]
    assert a_info.model_dump() == b_info.model_dump()


def test_matmul_ops_carry_operands_pointwise_do_not():
    _, info = run(4)
    for op in info.ops:
        if op.kind == "matmul":
            assert op.a and op.b and op.a_label and op.b_label and op.c_label
            assert len(op.a) == 4 and len(op.b) == 4  # square drawing, padded
        else:
            assert op.a is None and op.b is None
    # Cache-block matmuls label the re-read cache block for the panels.
    assert any(op.b_label and op.b_label.startswith("K-cache") for op in info.ops)


def test_llm_workload_validation():
    # kv_len bounds per spec (8–64) and the N<=8 cap.
    with pytest.raises(ValueError):
        Workload(kind="llm_decode", N=4, kvLen=7)
    with pytest.raises(ValueError):
        Workload(kind="llm_decode", N=4, kvLen=65)
    with pytest.raises(ValueError):
        Workload(kind="llm_decode", N=16)
    with pytest.raises(ValueError):
        Workload(kind="llm_decode", N=4, M=6)
    # kv_len/prefill on non-llm kinds are ignored, not rejected: the trace is
    # byte-identical with or without them (regression guard).
    from app.engine import simulate

    plain = simulate(DEFAULT_PROFILE, Workload(kind="matmul", N=4))
    decorated = simulate(
        DEFAULT_PROFILE, Workload(kind="matmul", N=4, kvLen=32, prefill=True)
    )
    assert [s.model_dump() for s in plain] == [s.model_dump() for s in decorated]


def test_prefill_op_list_has_no_block_ordinals():
    _, info = run(4, steps=2, prefill=True)
    assert info.ops_per_token == [13, 13]
    names = [op.name for op in info.ops[:13]]
    assert names == [
        "Q = X·Wq", "K = X·Wk", "V = X·Wv", "cache append",
        "S = Q·Kᵀ/√N", "softmax", "A = P·V",
        "O = A·Wo", "H = norm(X + O)", "Z = H·Wup", "G = gelu(Z)",
        "M = G·Wdown", "X' = H + M",
    ]
    assert info.kv_len == [4, 8]  # the cache grows a whole block per step


def test_wire_shape_is_camel_case():
    trace, info = run(4)
    payload = info.model_dump(by_alias=True)
    assert set(payload) == {
        "ops", "opsPerToken", "kvLen", "intensity", "softmaxRow", "prefill",
    }
    wl = Workload(kind="llm_decode", N=4, kvLen=12, prefill=False)
    dumped = wl.model_dump(by_alias=True)
    assert dumped["kvLen"] == 12 and dumped["prefill"] is False
    state = trace[1].model_dump(by_alias=True)
    assert "opIndex" in state and "stepIndex" in state
