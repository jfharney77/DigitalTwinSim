"""spec_26: one token step of a toy transformer block, as a chain of matmuls.

Pure like engine.py and mlp.py -- no timers, no IO, same inputs -> same trace.
Every matmul op reuses engine.simulate() unchanged (tiling, bandwidth stalls
and double-buffering apply per op); this module strips the per-op idle/done
bookends, restamps cycle/mac counters onto one continuous trace, and stamps
the op context (op_index/op_count/op_name/step_index — step_index is the
token). Pointwise ops (cache append, softmax, norm, gelu, residual) are one
flash state each.

The point is the KV cache: each decoded token re-reads the whole cache, so
the attention matmuls multiply while the arithmetic intensity falls. The
numerics are real, mlp.py-style — softmax rows genuinely sum to 1, the cache
contents come from running the seeded prompt through Wk/Wv, gelu and the
residuals are actual arithmetic. Honesty note (spec_26 §2): the *drawn*
attention matmuls share their cache-block operand across the N streams, which
under-charges KV traffic — real streams do not share caches. The trace is the
drawing; analyze_llm's Summary is the accounting.
"""

from __future__ import annotations

import math

from .engine import analyze, effective_macs_per_cycle, simulate
from .matrices import MatrixF, make_llm_data
from .models import (
    GpuProfile,
    LlmInfo,
    MlpOp,
    SimState,
    Summary,
    Workload,
    dtype_bytes,
    state_power_watts,
)

WEIGHT_MATMULS = 6  # Q/K/V projections, O, MLP up, MLP down
POINTWISE_OPS = 5  # cache append, softmax, residual+norm, gelu, residual
PREFILL_MATMULS = 8  # the six weight matmuls + one score + one value matmul


# --- the spec_26 §2 arithmetic ------------------------------------------------

def cache_blocks(s: int, n: int) -> int:
    """B = ceil(S/N): square N×N blocks the cache is drawn as."""
    return -(-s // n)


def matmuls_for_token(s: int, n: int) -> int:
    return WEIGHT_MATMULS + 2 * cache_blocks(s, n)


def ops_for_token(s: int, n: int) -> int:
    return matmuls_for_token(s, n) + POINTWISE_OPS


def llm_intensity(n: int, s: int, dtype_bytes: float) -> float:
    """intensity(S) = (6N + 2S) / (b·(12 + 2S)) — MACs per byte at cache
    length S. Starts near the plain matmul's N/2b, falls monotonically for
    every N > 2, floors at 1/b as S → ∞ (spec_26 §2). b is a float since
    spec_23 (fp4 = 0.5 bytes)."""
    return (6 * n + 2 * s) / (dtype_bytes * (12 + 2 * s))


def mac_total_decode(n: int, kv_len: int, steps: int) -> int:
    """Σ over tokens t=1..steps of (6 + 2·ceil((kv_len+t)/N))·N³ (spec_26 §4)."""
    return sum(matmuls_for_token(kv_len + t, n) for t in range(1, steps + 1)) * n**3


def mac_total_prefill(n: int, steps: int) -> int:
    return steps * PREFILL_MATMULS * n**3


# --- tiny pure-python matrix math (rectangular-capable) -----------------------

def matmul(a: MatrixF, b: MatrixF) -> MatrixF:
    """a is p×q, b is q×r → p×r."""
    q = len(b)
    r = len(b[0]) if b else 0
    return [
        [sum(row[k] * b[k][j] for k in range(q)) for j in range(r)] for row in a
    ]


def transpose(a: MatrixF) -> MatrixF:
    return [list(row) for row in zip(*a)]


def add_m(a: MatrixF, b: MatrixF) -> MatrixF:
    return [[x + y for x, y in zip(ra, rb)] for ra, rb in zip(a, b)]


def scale_m(a: MatrixF, f: float) -> MatrixF:
    return [[v * f for v in row] for row in a]


def softmax_rows(a: MatrixF) -> MatrixF:
    """True exp/normalize per row (max-subtracted for stability): every row
    sums to 1 exactly up to float rounding."""
    out: MatrixF = []
    for row in a:
        hi = max(row)
        e = [math.exp(v - hi) for v in row]
        z = sum(e)
        out.append([v / z for v in e])
    return out


def gelu_m(a: MatrixF) -> MatrixF:
    def g(v: float) -> float:
        return 0.5 * v * (1.0 + math.tanh(0.7978845608028654 * (v + 0.044715 * v**3)))

    return [[g(v) for v in row] for row in a]


def layer_norm(a: MatrixF, eps: float = 1e-6) -> MatrixF:
    out: MatrixF = []
    for row in a:
        mean = sum(row) / len(row)
        var = sum((v - mean) ** 2 for v in row) / len(row)
        inv = 1.0 / math.sqrt(var + eps)
        out.append([(v - mean) * inv for v in row])
    return out


def initial_kv_cache(
    n: int, kv_len: int, seed: int = 0
) -> tuple[MatrixF, MatrixF]:
    """The cache contents are true arithmetic: the seeded prompt really run
    through Wk and Wv (spec_26 §1)."""
    _, (_, wk, wv, _, _, _), prompt = make_llm_data(n, kv_len, seed)
    return matmul(prompt, wk), matmul(prompt, wv)


def _rounded(a: MatrixF) -> MatrixF:
    return [[round(v, 2) for v in row] for row in a]


def _pad_rows(rows: MatrixF, n: int) -> MatrixF:
    """Zero-pad a partial cache block to N rows for the square drawing."""
    out = [list(r) for r in rows]
    while len(out) < n:
        out.append([0.0] * n)
    return out


def _cols_padded(a: MatrixF, c0: int, c1: int, n: int) -> MatrixF:
    """Column slice [c0, c1) of each row, zero-padded to N columns."""
    return [row[c0:c1] + [0.0] * (n - (c1 - c0)) for row in a]


# --- trace assembly (mirrors mlp.py) ------------------------------------------

def _pointwise_state(profile: GpuProfile, n: int) -> SimState:
    """All mapped lanes flash for one cycle; memory idle (spec_06 §2 idiom)."""
    total_cores = profile.total_cores()
    active = min(n * n, total_cores)
    return SimState(
        cycle=0,  # restamped by the caller
        phase="compute",
        k=0,
        mac_done=0,  # restamped
        mac_total=0,  # restamped
        mem_active=False,
        core_state=["computing"] * active + ["idle"] * (total_cores - active),
        active_cores=active,
        utilization=(active / total_cores) if total_cores else 0.0,
        # spec_25: lanes flashing, memory idle.
        power_watts=state_power_watts(
            profile.power, profile.bandwidth.bytes_per_cycle,
            active_cores=active, stalled=False,
            mem_active=False, prefetching=False,
        ),
    )


def simulate_llm(
    profile: GpuProfile, workload: Workload
) -> tuple[list[SimState], LlmInfo]:
    """Full decode-run (or prefill-run) trace plus the op/intensity metadata."""
    n = workload.n
    steps = workload.steps  # tokens generated (decode) / prompt blocks (prefill)
    kv0 = workload.kv_len
    prefill = workload.prefill
    db = dtype_bytes(workload.dtype)
    total_cores = profile.total_cores()
    grand_total = (
        mac_total_prefill(n, steps) if prefill else mac_total_decode(n, kv0, steps)
    )
    if prefill:
        op_count = steps * (PREFILL_MATMULS + POINTWISE_OPS)
    else:
        op_count = sum(ops_for_token(kv0 + t, n) for t in range(1, steps + 1))

    x, (wq, wk, wv, wo, wup, wdown), _prompt = make_llm_data(n, kv0, workload.seed)

    # One matmul sub-trace reused for every matmul op: all ops are N×N, and
    # the schedule depends only on (profile, N, T, dtype, double_buffer).
    matmul_workload = workload.model_copy(update={"kind": "matmul"})
    sub_trace = simulate(profile, matmul_workload)[1:-1]  # strip idle/done

    trace: list[SimState] = []
    ops: list[MlpOp] = []
    ops_per_token: list[int] = []
    kv_lens: list[int] = []
    intensities: list[float] = []
    softmax_row: list[float] = []
    cycle = 0
    mac_offset = 0
    token_idx = 0

    def bookend(phase: str, mac_done: int) -> SimState:
        return SimState(
            cycle=cycle, phase=phase, k=0, mac_done=mac_done,  # type: ignore[arg-type]
            mac_total=grand_total, mem_active=False,
            core_state=["idle"] * total_cores, active_cores=0, utilization=0.0,
            power_watts=profile.power.idle_w,  # spec_25: bookends idle
        )

    def add_matmul(name: str, a: MatrixF, b: MatrixF,
                   a_label: str, b_label: str, c_label: str) -> None:
        nonlocal cycle, mac_offset
        op_index = len(ops)
        ops.append(MlpOp(name=name, kind="matmul", a=_rounded(a), b=_rounded(b),
                         a_label=a_label, b_label=b_label, c_label=c_label))
        for s in sub_trace:
            cycle += 1
            trace.append(s.model_copy(update={
                "cycle": cycle,
                "mac_done": mac_offset + s.mac_done,
                "mac_total": grand_total,
                "op_index": op_index,
                "op_count": op_count,
                "op_name": name,
                "step_index": token_idx,
            }))
        mac_offset += n**3

    def add_pointwise(name: str) -> None:
        nonlocal cycle
        op_index = len(ops)
        ops.append(MlpOp(name=name, kind="pointwise"))
        cycle += 1
        trace.append(_pointwise_state(profile, n).model_copy(update={
            "cycle": cycle,
            "mac_done": mac_offset,
            "mac_total": grand_total,
            "op_index": op_index,
            "op_count": op_count,
            "op_name": name,
            "step_index": token_idx,
        }))

    trace.append(bookend("idle", 0))
    if prefill:
        # The prefill *is* the prompt run — the cache starts empty and each
        # step fills a whole N-token block with full operand reuse.
        k_cache: MatrixF = []
        v_cache: MatrixF = []
    else:
        k_cache, v_cache = initial_kv_cache(n, kv0, workload.seed)
    inv_sqrt = 1.0 / math.sqrt(n)

    for t in range(1, steps + 1):
        token_idx = t - 1
        ops_before = len(ops)

        # a1–a3: Q/K/V projections (shared square weights — the batch trick).
        q = matmul(x, wq)
        add_matmul("Q = X·Wq", x, wq, "X", "Wq", "Q")
        k_new = matmul(x, wk)
        add_matmul("K = X·Wk", x, wk, "X", "Wk", "K")
        v_new = matmul(x, wv)
        add_matmul("V = X·Wv", x, wv, "X", "Wv", "V")

        if prefill:
            # a4: the whole block joins the cache at once.
            k_cache.extend([list(r) for r in k_new])
            v_cache.extend([list(r) for r in v_new])
            add_pointwise("cache append")
            s_len = len(k_cache)
            # a5–a7: attention over the current block only — one ordinary
            # square matmul each, full reuse. This is the whole contrast.
            scores = scale_m(matmul(q, transpose(k_new)), inv_sqrt)
            add_matmul("S = Q·Kᵀ/√N", q, transpose(k_new), "Q", "Kᵀ", "S")
            p = softmax_rows(scores)
            add_pointwise("softmax")
            a_mat = matmul(p, v_new)
            add_matmul("A = P·V", p, v_new, "P", "V", "A")
            intensities.append(n / (2 * db))
        else:
            # a4: one new K,V row joins the (drawn-shared) cache per token.
            k_cache.append(list(k_new[0]))
            v_cache.append(list(v_new[0]))
            add_pointwise("cache append")
            s_len = len(k_cache)  # kv_len + t
            blocks = cache_blocks(s_len, n)
            # a5: scores over the full cache — drawn as B square matmuls.
            scores = scale_m(matmul(q, transpose(k_cache)), inv_sqrt)
            for i in range(blocks):
                kb = _pad_rows(k_cache[i * n:(i + 1) * n], n)
                add_matmul(
                    f"S = Q·Kᵀ/√N (block {i + 1}/{blocks})", q, transpose(kb),
                    "Q", f"K-cache {i + 1}/{blocks}", f"S {i + 1}/{blocks}",
                )
            # a6: real softmax over the true S positions (no padding).
            p = softmax_rows(scores)
            add_pointwise("softmax")
            # a7: weighted values, drawn per cache block.
            for i in range(blocks):
                c1 = min((i + 1) * n, s_len)
                vb = _pad_rows(v_cache[i * n:(i + 1) * n], n)
                add_matmul(
                    f"A = P·V (block {i + 1}/{blocks})",
                    _cols_padded(p, i * n, c1, n), vb,
                    f"P {i + 1}/{blocks}", f"V-cache {i + 1}/{blocks}", "A",
                )
            a_mat = matmul(p, v_cache)
            intensities.append(llm_intensity(n, s_len, db))
        kv_lens.append(s_len)

        # a8–a13: output projection and the MLP, shared with both regimes.
        o = matmul(a_mat, wo)
        add_matmul("O = A·Wo", a_mat, wo, "A", "Wo", "O")
        h = layer_norm(add_m(x, o))
        add_pointwise("H = norm(X + O)")
        z = matmul(h, wup)
        add_matmul("Z = H·Wup", h, wup, "H", "Wup", "Z")
        g = gelu_m(z)
        add_pointwise("G = gelu(Z)")
        m_mat = matmul(g, wdown)
        add_matmul("M = G·Wdown", g, wdown, "G", "Wdown", "M")
        x = add_m(h, m_mat)
        add_pointwise("X' = H + M")

        ops_per_token.append(len(ops) - ops_before)
        softmax_row = list(p[0])
    trace.append(bookend("done", grand_total))

    info = LlmInfo(
        ops=ops,
        ops_per_token=ops_per_token,
        kv_len=kv_lens,
        intensity=intensities,
        softmax_row=softmax_row,
        prefill=prefill,
    )
    return trace, info


def analyze_llm(profile: GpuProfile, workload: Workload) -> Summary:
    """Roofline accounting for the run (spec_26 §2). Decode charges the K and
    V caches read once per token, unshared — the honest books the drawn trace
    under-charges. Prefill uses the engine's ordinary per-matmul accounting
    (full reuse), so the two regimes differ exactly where reality differs."""
    per_op = analyze(profile, workload.model_copy(update={"kind": "matmul"}))
    n = workload.n
    steps = workload.steps
    b = dtype_bytes(workload.dtype)  # float since spec_23 (fp4 = 0.5)
    bw = profile.bandwidth
    # spec_23: tensor mode scales compute throughput only; bytes are bytes.
    eff_macs = effective_macs_per_cycle(profile, workload)

    if workload.prefill:
        k = steps * PREFILL_MATMULS
        return per_op.model_copy(update={
            "bytes_moved": per_op.bytes_moved * k,
            "load_cycles_total": per_op.load_cycles_total * k,
            "compute_cycles_total": per_op.compute_cycles_total * k,
            "serial_cycles": per_op.serial_cycles * k,
            "pipelined_cycles": per_op.pipelined_cycles * k,
        })

    macs = 0
    bytes_moved = 0
    for t in range(1, steps + 1):
        s = workload.kv_len + t
        macs += n * n * (6 * n + 2 * s)
        # (12 + 2s) is even, so this is integral for every dtype incl. fp4.
        bytes_moved += math.ceil(b * n * n * (12 + 2 * s))
    load_cycles = math.ceil(bytes_moved / bw.bytes_per_cycle)
    compute_cycles = math.ceil(macs / eff_macs)
    intensity = macs / bytes_moved if bytes_moved else 0.0
    regime = "memory" if intensity < per_op.ridge_point else "compute"
    # Same pipelining shape as the engine: one un-hideable prologue load
    # (one matmul's A+B tiles), everything else overlapped.
    first_load = max(1, math.ceil(2 * n * n * b / bw.bytes_per_cycle))
    return per_op.model_copy(update={
        "bytes_moved": bytes_moved,
        "load_cycles_total": load_cycles,
        "compute_cycles_total": compute_cycles,
        "arithmetic_intensity": intensity,
        "regime": regime,
        "serial_cycles": load_cycles + compute_cycles,
        "pipelined_cycles": first_load + max(compute_cycles, load_cycles - first_load),
    })
