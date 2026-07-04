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
from .models import DTYPE_BYTES, CoreState, GpuProfile, SimState, Summary, Workload


def effective_tile_size(n: int, tile_size: int) -> int:
    """0 (or >= N) means 'whole matrix'; otherwise clamp into [1, N]."""
    if tile_size <= 0 or tile_size >= n:
        return n
    return tile_size


def _ranges(n: int, t: int) -> list[tuple[int, int]]:
    """Tile spans along one dimension; the last tile may be a partial edge."""
    return [(s, min(s + t, n)) for s in range(0, n, t)]


def _load_bytes(
    r0: int, r1: int, c0: int, c1: int, k0: int, k1: int, dtype_bytes: int
) -> int:
    """Bytes to bring the A-tile (rows x k) and B-tile (k x cols) from HBM."""
    cells_a = (r1 - r0) * (k1 - k0)
    cells_b = (k1 - k0) * (c1 - c0)
    return (cells_a + cells_b) * dtype_bytes


def _state(
    total_cores: int,
    n: int,
    mac_total: int,
    tile_size: int,
    num_tile_cols: int,
    num_sms: int,
    cores_per_sm: int,
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
    )


def analyze(profile: GpuProfile, workload: Workload) -> Summary:
    """Roofline + scheduling summary for the whole workload. Pure, no trace."""
    n = workload.n
    t = effective_tile_size(n, workload.tile_size)
    db = DTYPE_BYTES[workload.dtype]
    bw = profile.bandwidth
    mac_total = n * n * n

    bytes_moved = 0
    first_load_bytes = 0
    ranges = _ranges(n, t)
    for ri, (r0, r1) in enumerate(ranges):
        for ci, (c0, c1) in enumerate(ranges):
            for ki, (k0, k1) in enumerate(ranges):
                lb = _load_bytes(r0, r1, c0, c1, k0, k1, db)
                bytes_moved += lb
                if ri == 0 and ci == 0 and ki == 0:
                    first_load_bytes = lb

    load_cycles_total = math.ceil(bytes_moved / bw.bytes_per_cycle)
    compute_cycles_total = math.ceil(mac_total / bw.macs_per_cycle)
    intensity = mac_total / bytes_moved if bytes_moved else 0.0
    ridge = bw.macs_per_cycle / bw.bytes_per_cycle
    regime = "memory" if intensity < ridge else "compute"

    # Scheduling estimates (spec_05). Serial pays for every load and every
    # compute; double-buffering hides all but the prologue load behind compute.
    first_load = max(1, math.ceil(first_load_bytes / bw.bytes_per_cycle))
    serial_cycles = load_cycles_total + compute_cycles_total
    pipelined_cycles = first_load + max(
        compute_cycles_total, load_cycles_total - first_load
    )

    return Summary(
        bytes_moved=bytes_moved,
        load_cycles_total=load_cycles_total,
        compute_cycles_total=compute_cycles_total,
        arithmetic_intensity=intensity,
        ridge_point=ridge,
        regime=regime,  # type: ignore[arg-type]
        serial_cycles=serial_cycles,
        pipelined_cycles=pipelined_cycles,
    )


def _simulate_serial(mk, n: int, t: int, db: int, bpc: int) -> list[SimState]:
    """Serial schedule: load (stall) then compute, per tile (spec_03/04)."""
    mac_total = n * n * n
    trace: list[SimState] = []
    cycle = 0
    mac_done = 0

    trace.append(
        mk(cycle=0, phase="idle", k=0, mac_done=0, mem_active=False,
           cells=None, label=None, tile_row=None, tile_col=None, k_tile=None)
    )

    ranges = _ranges(n, t)
    for ti, (r0, r1) in enumerate(ranges):
        for tj, (c0, c1) in enumerate(ranges):
            tile_cells = [(i, j) for i in range(r0, r1) for j in range(c0, c1)]
            for tk, (k0, k1) in enumerate(ranges):
                cycle += 1
                load_bytes = _load_bytes(r0, r1, c0, c1, k0, k1, db)
                load_cost = max(1, math.ceil(load_bytes / bpc))
                trace.append(
                    mk(cycle=cycle, phase="load", k=k0, mac_done=mac_done,
                       mem_active=True, cells=tile_cells, label="loading",
                       tile_row=ti, tile_col=tj, k_tile=tk,
                       stalled=True, cycle_cost=load_cost)
                )
                for kk in range(k0, k1):
                    cycle += 1
                    mac_done += len(tile_cells)
                    trace.append(
                        mk(cycle=cycle, phase="compute", k=kk + 1, mac_done=mac_done,
                           mem_active=False, cells=tile_cells, label="computing",
                           tile_row=ti, tile_col=tj, k_tile=tk)
                    )
            cycle += 1
            trace.append(
                mk(cycle=cycle, phase="writeback", k=n, mac_done=mac_done,
                   mem_active=True, cells=tile_cells, label="wrote",
                   tile_row=ti, tile_col=tj, k_tile=None)
            )

    cycle += 1
    trace.append(
        mk(cycle=cycle, phase="done", k=n, mac_done=mac_total, mem_active=False,
           cells=None, label=None, tile_row=None, tile_col=None, k_tile=None)
    )
    return trace


def _simulate_pipelined(mk, n: int, t: int, db: int, bpc: int) -> list[SimState]:
    """Double-buffered schedule: one prologue load, then each compute overlaps
    the next tile's load (spec_05)."""
    mac_total = n * n * n
    trace: list[SimState] = []
    cycle = 0
    mac_done = 0

    trace.append(
        mk(cycle=0, phase="idle", k=0, mac_done=0, mem_active=False,
           cells=None, label=None, tile_row=None, tile_col=None, k_tile=None)
    )

    # Flatten the tile loop into an ordered list of load/compute events.
    ranges = _ranges(n, t)
    events = []
    for ti, (r0, r1) in enumerate(ranges):
        for tj, (c0, c1) in enumerate(ranges):
            cells = [(i, j) for i in range(r0, r1) for j in range(c0, c1)]
            for tk, (k0, k1) in enumerate(ranges):
                events.append(
                    {"ti": ti, "tj": tj, "tk": tk, "r0": r0, "r1": r1,
                     "c0": c0, "c1": c1, "k0": k0, "k1": k1, "cells": cells,
                     "last_k": tk == len(ranges) - 1}
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
        for kk in range(e["k0"], e["k1"]):
            cycle += 1
            mac_done += len(e["cells"])
            trace.append(
                mk(cycle=cycle, phase="compute", k=kk + 1, mac_done=mac_done,
                   mem_active=prefetch, cells=e["cells"], label="computing",
                   tile_row=e["ti"], tile_col=e["tj"], k_tile=e["tk"],
                   prefetching=prefetch)
            )
        if e["last_k"]:
            cycle += 1
            trace.append(
                mk(cycle=cycle, phase="writeback", k=n, mac_done=mac_done,
                   mem_active=True, cells=e["cells"], label="wrote",
                   tile_row=e["ti"], tile_col=e["tj"], k_tile=None)
            )

    cycle += 1
    trace.append(
        mk(cycle=cycle, phase="done", k=n, mac_done=mac_total, mem_active=False,
           cells=None, label=None, tile_row=None, tile_col=None, k_tile=None)
    )
    return trace


def simulate(profile: GpuProfile, workload: Workload) -> list[SimState]:
    """Build the full deterministic SimState trace (serial or double-buffered)."""
    total_cores = profile.total_cores()
    n = workload.n
    t = effective_tile_size(n, workload.tile_size)
    db = DTYPE_BYTES[workload.dtype]
    bpc = profile.bandwidth.bytes_per_cycle
    mac_total = n * n * n

    cores_per_sm = profile.cores_per_sm.rows * profile.cores_per_sm.cols
    num_sms = total_cores // cores_per_sm
    num_tile_cols = len(_ranges(n, t))

    mk = functools.partial(
        _state, total_cores, n, mac_total, t, num_tile_cols, num_sms, cores_per_sm
    )
    builder = _simulate_pipelined if workload.double_buffer else _simulate_serial
    return builder(mk, n, t, db, bpc)
