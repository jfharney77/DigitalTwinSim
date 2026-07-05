"""spec_06: one SGD training step of a tiny 2-layer MLP, as a chain of matmuls.

Pure like engine.py -- no timers, no IO, same inputs -> same trace. Each of the
five matmuls per step reuses engine.simulate() unchanged (so tiling, bandwidth
costs, and double-buffering apply per op); this module strips the per-op
idle/done bookends, restamps cycle/mac counters onto one continuous trace, and
adds the op context (op_index/op_name/step_index). Pointwise ops (relu, loss,
SGD update) are one flash state each -- they exist so the pipeline reads
honestly, not to model elementwise bandwidth (spec_07 territory).

Numerics are real: the returned per-step losses come from actually running the
forward/backward math, so tests can assert the network learns. Operand
snapshots in the payload are display-rounded; gradients use full precision.
"""

from __future__ import annotations

from .engine import analyze, simulate
from .matrices import MatrixF, make_mlp_data
from .models import GpuProfile, MlpInfo, MlpOp, SimState, Summary, Workload

ETA = 0.01  # fixed learning rate (spec_06 §1); not a UI control (§5)
OPS_PER_STEP = 8  # 5 matmuls + relu + loss + update
MATMULS_PER_STEP = 5


# --- tiny pure-python matrix math -------------------------------------------

def matmul(a: MatrixF, b: MatrixF) -> MatrixF:
    n = len(a)
    return [
        [sum(a[i][k] * b[k][j] for k in range(n)) for j in range(n)]
        for i in range(n)
    ]


def transpose(a: MatrixF) -> MatrixF:
    return [list(row) for row in zip(*a)]


def relu(a: MatrixF) -> MatrixF:
    return [[v if v > 0 else 0.0 for v in row] for row in a]


def relu_mask(z: MatrixF, g: MatrixF) -> MatrixF:
    """g ⊙ relu′(z): zero the gradient where the activation was clipped."""
    return [
        [gv if zv > 0 else 0.0 for zv, gv in zip(zrow, grow)]
        for zrow, grow in zip(z, g)
    ]


def sub(a: MatrixF, b: MatrixF) -> MatrixF:
    return [[x - y for x, y in zip(ra, rb)] for ra, rb in zip(a, b)]


def sgd(w: MatrixF, dw: MatrixF, eta: float) -> MatrixF:
    return [[x - eta * y for x, y in zip(rw, rd)] for rw, rd in zip(w, dw)]


def mse(pred: MatrixF, target: MatrixF) -> float:
    return 0.5 * sum(
        (p - t) ** 2 for rp, rt in zip(pred, target) for p, t in zip(rp, rt)
    )


def _rounded(a: MatrixF) -> MatrixF:
    return [[round(v, 2) for v in row] for row in a]


# --- trace assembly ----------------------------------------------------------

def _pointwise_state(total_cores: int, n: int) -> SimState:
    """All mapped lanes flash for one cycle; memory idle (spec_06 §2)."""
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
    )


def simulate_mlp(
    profile: GpuProfile, workload: Workload
) -> tuple[list[SimState], MlpInfo]:
    """Full training-run trace plus the op/loss metadata for the UI."""
    n = workload.n
    steps = workload.steps
    total_cores = profile.total_cores()
    grand_total = steps * MATMULS_PER_STEP * n**3
    x, y, w1, w2 = make_mlp_data(n, workload.seed)

    matmul_workload = workload.model_copy(update={"kind": "matmul"})

    # One matmul sub-trace, reused for every matmul op: the schedule depends
    # only on (profile, N, T, dtype, double_buffer), not on operand values.
    sub_trace = simulate(profile, matmul_workload)[1:-1]  # strip idle/done

    trace: list[SimState] = []
    ops: list[MlpOp] = []
    losses: list[float] = []
    cycle = 0
    mac_offset = 0

    def bookend(phase: str, mac_done: int) -> SimState:
        return SimState(
            cycle=cycle, phase=phase, k=0, mac_done=mac_done,  # type: ignore[arg-type]
            mac_total=grand_total, mem_active=False,
            core_state=["idle"] * total_cores, active_cores=0, utilization=0.0,
        )

    def add_matmul(name: str, a: MatrixF, b: MatrixF,
                   a_label: str, b_label: str, c_label: str) -> MatrixF:
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
                "op_count": steps * OPS_PER_STEP,
                "op_name": name,
                "step_index": op_index // OPS_PER_STEP,
            }))
        mac_offset += n**3
        return matmul(a, b)

    def add_pointwise(name: str) -> None:
        nonlocal cycle
        op_index = len(ops)
        ops.append(MlpOp(name=name, kind="pointwise"))
        cycle += 1
        trace.append(_pointwise_state(total_cores, n).model_copy(update={
            "cycle": cycle,
            "mac_done": mac_offset,
            "mac_total": grand_total,
            "op_index": op_index,
            "op_count": steps * OPS_PER_STEP,
            "op_name": name,
            "step_index": op_index // OPS_PER_STEP,
        }))

    trace.append(bookend("idle", 0))
    for _ in range(steps):
        # Forward (spec_06 §1: f1-f3)
        z1 = add_matmul("Z1 = X·W1", x, w1, "X", "W1", "Z1")
        a1 = relu(z1)
        add_pointwise("A1 = relu(Z1)")
        z2 = add_matmul("Z2 = A1·W2", a1, w2, "A1", "W2", "Z2")
        # Loss and its gradient
        losses.append(mse(z2, y))
        d2 = sub(z2, y)
        add_pointwise("δ2 = Z2 − Y")
        # Backward (b1-b3)
        dw2 = add_matmul("dW2 = A1ᵀ·δ2", transpose(a1), d2, "A1ᵀ", "δ2", "dW2")
        d1 = relu_mask(z1, add_matmul(
            "δ1 = δ2·W2ᵀ ⊙ relu′", d2, transpose(w2), "δ2", "W2ᵀ", "δ2·W2ᵀ"))
        dw1 = add_matmul("dW1 = Xᵀ·δ1", transpose(x), d1, "Xᵀ", "δ1", "dW1")
        # SGD update
        w1 = sgd(w1, dw1, ETA)
        w2 = sgd(w2, dw2, ETA)
        add_pointwise("W ← W − η·dW")
    trace.append(bookend("done", grand_total))

    info = MlpInfo(ops=ops, ops_per_step=OPS_PER_STEP, loss=losses, eta=ETA)
    return trace, info


def analyze_mlp(profile: GpuProfile, workload: Workload) -> Summary:
    """Per-op roofline is identical for all five matmuls (same N/T/dtype), so
    the regime/intensity read straight through; totals scale by the op count."""
    per_op = analyze(profile, workload.model_copy(update={"kind": "matmul"}))
    k = workload.steps * MATMULS_PER_STEP
    return per_op.model_copy(update={
        "bytes_moved": per_op.bytes_moved * k,
        "load_cycles_total": per_op.load_cycles_total * k,
        "compute_cycles_total": per_op.compute_cycles_total * k,
        "serial_cycles": per_op.serial_cycles * k,
        "pipelined_cycles": per_op.pipelined_cycles * k,
    })
