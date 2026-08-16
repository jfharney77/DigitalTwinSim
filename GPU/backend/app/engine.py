"""Pure, deterministic simulation engine.

Given a GpuProfile + Workload it produces the entire SimState trace. There are
no timers and no I/O here -- the frontend owns the clock and just plays the
trace back (spec §1 principle 3, §2). Same inputs -> same trace.

Phases (idle -> load -> compute -> writeback -> done) follow the spec's 5-phase
model. With tiling (spec_03) the load/compute/writeback phases repeat per tile.
With double-buffering (spec_05) each non-prologue load overlaps the preceding
compute (prefetch) instead of stalling. With tile_size >= N (or 0) the whole
matrix is one tile and both schedules reduce to the original single-LOAD trace.
"""

from __future__ import annotations

import functools
import math

from .mapping import tile_aware_core
from .models import (
    DTYPE_BITS,
    CoreState,
    GpuProfile,
    Power,
    SimState,
    Summary,
    Workload,
    state_power_watts,
)
from .occupancy import theoretical_occupancy


def effective_tile_size(n: int, tile_size: int) -> int:
    """0 (or >= N) means 'whole matrix'; otherwise clamp into [1, N]."""
    if tile_size <= 0 or tile_size >= n:
        return n
    return tile_size


def resolve_dims(workload: Workload) -> tuple[int, int, int]:
    """Effective (M, K, N) under the spec_22 sentinel rule: 0 means '= n'.

    A is M×K, B is K×N, C is M×N. Square workloads resolve to (n, n, n).
    """
    return (workload.m or workload.n, workload.k_dim or workload.n, workload.n)


def _ranges(n: int, t: int) -> list[tuple[int, int]]:
    """Tile spans along one dimension; the last tile may be a partial edge."""
    return [(s, min(s + t, n)) for s in range(0, n, t)]


def _load_bytes(
    r0: int, r1: int, c0: int, c1: int, k0: int, k1: int, dtype_bits: int
) -> int:
    """Bytes to bring the A-tile (rows x k) and B-tile (k x cols) from HBM.

    spec_23: computed from bits so fp4 works; ceil(cells * bits / 8) equals
    cells * bytes exactly for every byte-aligned dtype (spec_04 unchanged)."""
    cells_a = (r1 - r0) * (k1 - k0)
    cells_b = (k1 - k0) * (c1 - c0)
    return math.ceil((cells_a + cells_b) * dtype_bits / 8)


def tensor_multiplier(profile: GpuProfile, workload: Workload) -> float | None:
    """The dtype's MMA throughput multiplier when the tensor path is active,
    else None (scalar path). Defensive by design: an unsupported dtype or a
    die with no TensorSpec falls back to the scalar path rather than raising —
    main.py rejects the pair with a 422 before the engine ever sees it."""
    if workload.execution != "tensor" or profile.tensor is None:
        return None
    return profile.tensor.multipliers.get(workload.dtype)


def effective_macs_per_cycle(profile: GpuProfile, workload: Workload) -> float:
    """macs_per_cycle scaled by the tensor multiplier (spec_23): tensor cores
    multiply compute throughput, never bytes_per_cycle."""
    mult = tensor_multiplier(profile, workload)
    return profile.bandwidth.macs_per_cycle * (mult if mult is not None else 1.0)


def _state(
    total_cores: int,
    n: int,
    mac_total: int,
    tile_size: int,
    num_tile_cols: int,
    num_sms: int,
    cores_per_sm: int,
    power: Power,
    bpc: int,
    *,
    cycle: int,
    phase: str,
    k: int,
    mac_done: int,
    mem_active: bool,
    cells: list[tuple[int, int]] | None,
    label: CoreState | None,
    tile_row: int | None,
    tile_col: int | None,
    k_tile: int | None,
    stalled: bool = False,
    cycle_cost: int = 1,
    prefetching: bool = False,
    ranks: int | None = None,
) -> SimState:
    cs: list[CoreState] = ["idle"] * total_cores
    active_set: set[int] = set()
    if cells and label is not None and tile_row is not None and tile_col is not None:
        for i, j in cells:
            core = tile_aware_core(
                i,
                j,
                tile_size=tile_size,
                tile_row=tile_row,
                tile_col=tile_col,
                num_tile_cols=num_tile_cols,
                num_sms=num_sms,
                cores_per_sm=cores_per_sm,
            )
            cs[core] = label
            active_set.add(core)
        if label == "mma":
            # spec_23 rendering decision: an MMA is issued by the SM's tensor
            # units, not by individual scalar lanes — painting single lanes
            # would draw a falsehood. Light every lane of each owning SM.
            for sm_idx in {core // cores_per_sm for core in active_set}:
                for lane in range(
                    sm_idx * cores_per_sm, (sm_idx + 1) * cores_per_sm
                ):
                    cs[lane] = "mma"
                    active_set.add(lane)
    active = len(active_set)
    return SimState(
        cycle=cycle,
        phase=phase,  # type: ignore[arg-type]
        k=k,
        mac_done=mac_done,
        mac_total=mac_total,
        mem_active=mem_active,
        core_state=cs,
        active_cores=active,
        utilization=(active / total_cores) if total_cores else 0.0,
        tile_row=tile_row,
        tile_col=tile_col,
        k_tile=k_tile,
        stalled=stalled,
        cycle_cost=cycle_cost,
        prefetching=prefetching,
        mma=(label == "mma"),
        ranks_per_step=ranks,
        # spec_25: watts from fields this state already carries — pure.
        power_watts=state_power_watts(
            power,
            bpc,
            active_cores=active,
            stalled=stalled,
            mem_active=mem_active,
            prefetching=prefetching,
        ),
    )


def _die_serial_cycles(
    profile: GpuProfile, workload: Workload, m_dim: int, k_dim: int, n: int
) -> int:
    """Serial load+compute cycles for an explicit M×K×N on one die (spec_27:
    the per-die term of the max()-based two-GPU cost). Same tile/byte/rate
    arithmetic as analyze(), on the die's own re-tiled slice."""
    t = effective_tile_size(max(m_dim, k_dim, n), workload.tile_size)
    db = DTYPE_BITS[workload.dtype]
    bw = profile.bandwidth
    bytes_moved = sum(
        _load_bytes(r0, r1, c0, c1, k0, k1, db)
        for r0, r1 in _ranges(m_dim, t)
        for c0, c1 in _ranges(n, t)
        for k0, k1 in _ranges(k_dim, t)
    )
    load = math.ceil(bytes_moved / bw.bytes_per_cycle)
    compute = math.ceil(
        m_dim * k_dim * n / effective_macs_per_cycle(profile, workload)
    )
    return load + compute


def analyze(profile: GpuProfile, workload: Workload) -> Summary:
    """Roofline + scheduling summary for the whole workload. Pure, no trace."""
    m_dim, k_dim, n = resolve_dims(workload)
    t = effective_tile_size(max(m_dim, k_dim, n), workload.tile_size)
    db = DTYPE_BITS[workload.dtype]
    bw = profile.bandwidth
    mac_total = m_dim * k_dim * n
    # spec_23: tensor mode multiplies macs_per_cycle, never bytes_per_cycle —
    # the ridge point moves right by exactly the dtype factor while intensity
    # is untouched (same bytes, same MACs). In cuda mode this is 1.0×.
    eff_macs = effective_macs_per_cycle(profile, workload)

    bytes_moved = 0
    first_load_bytes = 0
    for ri, (r0, r1) in enumerate(_ranges(m_dim, t)):
        for ci, (c0, c1) in enumerate(_ranges(n, t)):
            for ki, (k0, k1) in enumerate(_ranges(k_dim, t)):
                lb = _load_bytes(r0, r1, c0, c1, k0, k1, db)
                bytes_moved += lb
                if ri == 0 and ci == 0 and ki == 0:
                    first_load_bytes = lb

    load_cycles_total = math.ceil(bytes_moved / bw.bytes_per_cycle)
    compute_cycles_total = math.ceil(mac_total / eff_macs)
    intensity = mac_total / bytes_moved if bytes_moved else 0.0
    ridge = eff_macs / bw.bytes_per_cycle
    regime = "memory" if intensity < ridge else "compute"

    # Scheduling estimates (spec_05). Serial pays for every load and every
    # compute; double-buffering hides all but the prologue load behind compute.
    first_load = max(1, math.ceil(first_load_bytes / bw.bytes_per_cycle))
    serial_cycles = load_cycles_total + compute_cycles_total
    pipelined_cycles = first_load + max(
        compute_cycles_total, load_cycles_total - first_load
    )

    # Occupancy (spec_24): fixed at launch. block_size == 0 derives today's
    # implicit rule — one output tile is one block (T² cells, clamped to 1024).
    eff_block = workload.block_size or min(1024, t * t)
    occupancy = theoretical_occupancy(
        eff_block,
        max_threads_per_sm=profile.max_threads_per_sm,
        max_blocks_per_sm=profile.max_blocks_per_sm,
        warp_size=profile.warp_size,
    )

    # NVLink scale-up read-outs (spec_27). two_gpu = max(die0, die1) +
    # exchange — the dies run concurrently in the cost model even though the
    # trace draws them serially (the DieView caption owns that honesty).
    # Speedup is always < 2 and approaches 2 as N³ compute swamps N² exchange.
    xc = exchange_cycles(profile, workload)
    speedup = 1.0
    if xc:
        rows0, rows1 = _split_rows(m_dim)
        die_cycles = max(
            _die_serial_cycles(profile, workload, rows, k_dim, n)
            for rows in (rows0, rows1)
        )
        speedup = serial_cycles / (die_cycles + xc)

    return Summary(
        bytes_moved=bytes_moved,
        load_cycles_total=load_cycles_total,
        compute_cycles_total=compute_cycles_total,
        arithmetic_intensity=intensity,
        ridge_point=ridge,
        regime=regime,  # type: ignore[arg-type]
        serial_cycles=serial_cycles,
        pipelined_cycles=pipelined_cycles,
        occupancy=occupancy,
        exchange_cycles=xc,
        scaleup_speedup=speedup,
    )


def attach_energy(summary: Summary, trace: list[SimState]) -> Summary:
    """spec_25: close the energy ledger over a built trace. Modeled time is
    cycle_cost, so joules = Σ powerWatts × cycle_cost — the exact plain sum
    tests re-compute with no tolerance. Lives here rather than in analyze()
    because analyze() is trace-free; main.py stamps the ledger onto every
    kind's Summary after the trace exists (mlp/llm traces included)."""
    energy = sum(s.power_watts * s.cycle_cost for s in trace)
    cycles = sum(s.cycle_cost for s in trace)
    mac_total = trace[-1].mac_total if trace else 0
    return summary.model_copy(
        update={
            "energy_joules": energy,
            "avg_power_watts": energy / cycles if cycles else 0.0,
            "joules_per_mac": energy / mac_total if mac_total else 0.0,
        }
    )


def _simulate_serial(
    mk, m_dim: int, k_dim: int, n: int, t: int, db: int, bpc: int,
    mma_k: int | None = None,
) -> list[SimState]:
    """Serial schedule: load (stall) then compute, per tile (spec_03/04).
    mma_k set => tensor mode (spec_23): each compute step consumes a whole
    mma_k-rank chunk (final chunk possibly partial)."""
    mac_total = m_dim * k_dim * n
    trace: list[SimState] = []
    cycle = 0
    mac_done = 0

    trace.append(
        mk(cycle=0, phase="idle", k=0, mac_done=0, mem_active=False,
           cells=None, label=None, tile_row=None, tile_col=None, k_tile=None)
    )

    k_ranges = _ranges(k_dim, t)
    for ti, (r0, r1) in enumerate(_ranges(m_dim, t)):
        for tj, (c0, c1) in enumerate(_ranges(n, t)):
            tile_cells = [(i, j) for i in range(r0, r1) for j in range(c0, c1)]
            for tk, (k0, k1) in enumerate(k_ranges):
                cycle += 1
                load_bytes = _load_bytes(r0, r1, c0, c1, k0, k1, db)
                load_cost = max(1, math.ceil(load_bytes / bpc))
                trace.append(
                    mk(cycle=cycle, phase="load", k=k0, mac_done=mac_done,
                       mem_active=True, cells=tile_cells, label="loading",
                       tile_row=ti, tile_col=tj, k_tile=tk,
                       stalled=True, cycle_cost=load_cost)
                )
                kk = k0
                while kk < k1:
                    ranks = min(mma_k, k1 - kk) if mma_k else 1
                    kk += ranks
                    cycle += 1
                    mac_done += len(tile_cells) * ranks
                    trace.append(
                        mk(cycle=cycle, phase="compute", k=kk, mac_done=mac_done,
                           mem_active=False, cells=tile_cells,
                           label="mma" if mma_k else "computing",
                           tile_row=ti, tile_col=tj, k_tile=tk,
                           ranks=ranks if mma_k else None)
                    )
            cycle += 1
            trace.append(
                mk(cycle=cycle, phase="writeback", k=k_dim, mac_done=mac_done,
                   mem_active=True, cells=tile_cells, label="wrote",
                   tile_row=ti, tile_col=tj, k_tile=None)
            )

    cycle += 1
    trace.append(
        mk(cycle=cycle, phase="done", k=k_dim, mac_done=mac_total,
           mem_active=False,
           cells=None, label=None, tile_row=None, tile_col=None, k_tile=None)
    )
    return trace


def _simulate_pipelined(
    mk, m_dim: int, k_dim: int, n: int, t: int, db: int, bpc: int,
    mma_k: int | None = None,
) -> list[SimState]:
    """Double-buffered schedule: one prologue load, then each compute overlaps
    the next tile's load (spec_05)."""
    mac_total = m_dim * k_dim * n
    trace: list[SimState] = []
    cycle = 0
    mac_done = 0

    trace.append(
        mk(cycle=0, phase="idle", k=0, mac_done=0, mem_active=False,
           cells=None, label=None, tile_row=None, tile_col=None, k_tile=None)
    )

    # Flatten the tile loop into an ordered list of load/compute events.
    k_ranges = _ranges(k_dim, t)
    events = []
    for ti, (r0, r1) in enumerate(_ranges(m_dim, t)):
        for tj, (c0, c1) in enumerate(_ranges(n, t)):
            cells = [(i, j) for i in range(r0, r1) for j in range(c0, c1)]
            for tk, (k0, k1) in enumerate(k_ranges):
                events.append(
                    {"ti": ti, "tj": tj, "tk": tk, "r0": r0, "r1": r1,
                     "c0": c0, "c1": c1, "k0": k0, "k1": k1, "cells": cells,
                     "last_k": tk == len(k_ranges) - 1}
                )

    # Prologue: the first load cannot be hidden -- nothing to compute yet.
    e0 = events[0]
    cycle += 1
    lb = _load_bytes(e0["r0"], e0["r1"], e0["c0"], e0["c1"], e0["k0"], e0["k1"], db)
    trace.append(
        mk(cycle=cycle, phase="load", k=e0["k0"], mac_done=mac_done, mem_active=True,
           cells=e0["cells"], label="loading", tile_row=e0["ti"], tile_col=e0["tj"],
           k_tile=e0["tk"], stalled=True, cycle_cost=max(1, math.ceil(lb / bpc)))
    )

    for i, e in enumerate(events):
        prefetch = i + 1 < len(events)  # a next tile is streaming in the background
        kk = e["k0"]
        while kk < e["k1"]:
            ranks = min(mma_k, e["k1"] - kk) if mma_k else 1
            kk += ranks
            cycle += 1
            mac_done += len(e["cells"]) * ranks
            trace.append(
                mk(cycle=cycle, phase="compute", k=kk, mac_done=mac_done,
                   mem_active=prefetch, cells=e["cells"],
                   label="mma" if mma_k else "computing",
                   tile_row=e["ti"], tile_col=e["tj"], k_tile=e["tk"],
                   prefetching=prefetch, ranks=ranks if mma_k else None)
            )
        if e["last_k"]:
            cycle += 1
            trace.append(
                mk(cycle=cycle, phase="writeback", k=k_dim, mac_done=mac_done,
                   mem_active=True, cells=e["cells"], label="wrote",
                   tile_row=e["ti"], tile_col=e["tj"], k_tile=None)
            )

    cycle += 1
    trace.append(
        mk(cycle=cycle, phase="done", k=k_dim, mac_done=mac_total,
           mem_active=False,
           cells=None, label=None, tile_row=None, tile_col=None, k_tile=None)
    )
    return trace


def exchange_cycles(profile: GpuProfile, workload: Workload) -> int:
    """spec_27: modeled cost of all-gathering C across the link. bytes(C) =
    ceil(M·N·dtype_bits/8) — the spec's N²·dtype_bytes, generalized to
    spec_22's rectangular shapes. 0 when the workload never crosses a link."""
    if workload.gpus < 2 or profile.link is None:
        return 0
    m_dim, _k_dim, n = resolve_dims(workload)
    c_bytes = math.ceil(m_dim * n * DTYPE_BITS[workload.dtype] / 8)
    return max(1, math.ceil(c_bytes / profile.link.bytes_per_cycle))


def _split_rows(m_dim: int) -> tuple[int, int]:
    """spec_27 decomposition: die 0 owns C's top ceil(M/2) rows, die 1 the
    rest. Each die re-tiles its own half, so a tile never straddles a die."""
    top = math.ceil(m_dim / 2)
    return top, m_dim - top


def _simulate_scaleup(profile: GpuProfile, workload: Workload) -> list[SimState]:
    """spec_27: two dies, one matmul, one explicit exchange.

    Each die runs the existing single-die builder unchanged on its row-slice
    of C (die-local coordinates — the dies share nothing but the link), then
    one stalled `exchange` state pays for the all-gather. The trace is one
    logical sequence: shared idle, die 0's states, die 1's states, exchange,
    done. mac_done stays globally monotonic; each die's subsequence
    contributes exactly its rows × K × N."""
    m_dim, k_dim, n = resolve_dims(workload)
    mac_total = m_dim * k_dim * n
    rows0, rows1 = _split_rows(m_dim)

    subs = [_build(profile, workload, rows, k_dim, n) for rows in (rows0, rows1)]

    trace: list[SimState] = []
    # Shared idle bookend: die 0's, restamped to the global MAC total.
    trace.append(subs[0][0].model_copy(update={"mac_total": mac_total}))
    cycle = 0
    mac_offset = 0
    for gpu, (sub, rows) in enumerate(zip(subs, (rows0, rows1))):
        for s in sub[1:-1]:  # strip the per-die idle/done bookends (mlp style)
            cycle += 1
            trace.append(
                s.model_copy(
                    update={
                        "gpu": gpu,
                        "cycle": cycle,
                        "mac_done": s.mac_done + mac_offset,
                        "mac_total": mac_total,
                    }
                )
            )
        mac_offset += rows * k_dim * n

    # The exchange: a single stalled state, dwelt on like a costly load. The
    # link, not HBM, moves the bytes (mem_active=False), so its watts are the
    # idle floor plus byte_w per link-byte/cycle — the spec_25 per-byte
    # constant billed at the link's own rate (documented in the spec's
    # implementation notes; lanes are parked, exactly as in a stalled load).
    xc = exchange_cycles(profile, workload)
    assert profile.link is not None  # guarded by the caller
    cycle += 1
    exchange = subs[0][-1].model_copy(
        update={
            "phase": "exchange",
            "gpu": None,
            "cycle": cycle,
            "mac_done": mac_total,
            "mac_total": mac_total,
            "stalled": True,
            "mem_active": False,
            "cycle_cost": xc,
            "power_watts": profile.power.idle_w
            + profile.power.byte_w * profile.link.bytes_per_cycle,
        }
    )
    trace.append(exchange)

    cycle += 1
    trace.append(
        subs[1][-1].model_copy(
            update={"cycle": cycle, "mac_done": mac_total, "mac_total": mac_total}
        )
    )
    return trace


def simulate(profile: GpuProfile, workload: Workload) -> list[SimState]:
    """Build the full deterministic SimState trace (serial or double-buffered).

    spec_27: gpus=2 splits C's rows across two dies and appends an exchange
    phase. Defensive like the tensor path: a linkless profile falls back to
    the single-die trace — main.py has already 422'd that pair at the edge."""
    if workload.gpus == 2 and profile.link is not None:
        return _simulate_scaleup(profile, workload)
    m_dim, k_dim, n = resolve_dims(workload)
    return _build(profile, workload, m_dim, k_dim, n)


def _build(
    profile: GpuProfile, workload: Workload, m_dim: int, k_dim: int, n: int
) -> list[SimState]:
    """Single-die trace for an explicit M×K×N (spec_27 factored this out of
    simulate() so each die of a scale-up run reuses it byte-for-byte)."""
    total_cores = profile.total_cores()
    t = effective_tile_size(max(m_dim, k_dim, n), workload.tile_size)
    db = DTYPE_BITS[workload.dtype]
    bpc = profile.bandwidth.bytes_per_cycle
    mac_total = m_dim * k_dim * n
    # spec_23: tensor mode active only when the die declares the dtype
    # (tensor_multiplier is the single gate — unsupported pairs fall back to
    # the scalar path; main.py has already 422'd them at the API edge).
    mma_k = (
        profile.tensor.mma_k
        if tensor_multiplier(profile, workload) is not None and profile.tensor
        else None
    )

    cores_per_sm = profile.cores_per_sm.rows * profile.cores_per_sm.cols
    num_sms = total_cores // cores_per_sm
    num_tile_cols = len(_ranges(n, t))  # C-tile grid is M×N; cols follow N

    mk = functools.partial(
        _state, total_cores, n, mac_total, t, num_tile_cols, num_sms, cores_per_sm,
        profile.power, bpc,
    )
    builder = _simulate_pipelined if workload.double_buffer else _simulate_serial
    return builder(mk, m_dim, k_dim, n, t, db, bpc, mma_k)
