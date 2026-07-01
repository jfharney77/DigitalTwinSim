"""Pure, deterministic simulation engine.

Given a GpuProfile + Workload it produces the entire SimState trace. There are
no timers and no I/O here -- the frontend owns the clock and just plays the
trace back (spec §1 principle 3, §2). Same inputs -> same trace.

Phases (idle -> load -> compute -> writeback -> done) follow the spec's 5-phase
model. With tiling (spec_03) the load/compute/writeback phases repeat per tile;
with tile_size >= N (or 0) the whole matrix is one tile and the trace is exactly
the original single-LOAD trace.
"""

from __future__ import annotations

import math

from .mapping import cell_to_core
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


def analyze(profile: GpuProfile, workload: Workload) -> Summary:
    """Roofline summary for the whole workload (spec_04). Pure, no trace needed."""
    n = workload.n
    t = effective_tile_size(n, workload.tile_size)
    db = DTYPE_BYTES[workload.dtype]
    bw = profile.bandwidth
    mac_total = n * n * n

    bytes_moved = 0
    for r0, r1 in _ranges(n, t):
        for c0, c1 in _ranges(n, t):
            for k0, k1 in _ranges(n, t):
                bytes_moved += _load_bytes(r0, r1, c0, c1, k0, k1, db)

    load_cycles_total = math.ceil(bytes_moved / bw.bytes_per_cycle)
    compute_cycles_total = math.ceil(mac_total / bw.macs_per_cycle)
    intensity = mac_total / bytes_moved if bytes_moved else 0.0
    ridge = bw.macs_per_cycle / bw.bytes_per_cycle
    regime = "memory" if intensity < ridge else "compute"
    return Summary(
        bytes_moved=bytes_moved,
        load_cycles_total=load_cycles_total,
        compute_cycles_total=compute_cycles_total,
        arithmetic_intensity=intensity,
        ridge_point=ridge,
        regime=regime,  # type: ignore[arg-type]
    )


def simulate(profile: GpuProfile, workload: Workload) -> list[SimState]:
    """Build the full deterministic SimState trace."""
    total_cores = profile.total_cores()
    n = workload.n
    t = effective_tile_size(n, workload.tile_size)
    db = DTYPE_BYTES[workload.dtype]
    bpc = profile.bandwidth.bytes_per_cycle
    mac_total = n * n * n

    def make_state(
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
    ) -> SimState:
        cs: list[CoreState] = ["idle"] * total_cores
        active_set: set[int] = set()
        if cells and label is not None:
            for i, j in cells:
                core = cell_to_core(i, j, n, total_cores)
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
        )

    trace: list[SimState] = []
    cycle = 0
    mac_done = 0

    # idle -- before Run
    trace.append(make_state(0, "idle", 0, 0, False, None, None, None, None, None))

    row_tiles = _ranges(n, t)
    col_tiles = _ranges(n, t)
    k_tiles = _ranges(n, t)

    for ti, (r0, r1) in enumerate(row_tiles):
        for tj, (c0, c1) in enumerate(col_tiles):
            tile_cells = [(i, j) for i in range(r0, r1) for j in range(c0, c1)]

            for tk, (k0, k1) in enumerate(k_tiles):
                # LOAD A-tile (ti,tk) + B-tile (tk,tj) HBM -> shared mem.
                # Cost scales with bytes moved: the cores stall while they wait.
                cycle += 1
                load_bytes = _load_bytes(r0, r1, c0, c1, k0, k1, db)
                load_cost = max(1, math.ceil(load_bytes / bpc))
                trace.append(
                    make_state(
                        cycle, "load", k0, mac_done, True,
                        tile_cells, "loading", ti, tj, tk,
                        stalled=True, cycle_cost=load_cost,
                    )
                )
                # COMPUTE one accumulation step per kk within this k-tile
                for kk in range(k0, k1):
                    cycle += 1
                    mac_done += len(tile_cells)  # one MAC per cell this step
                    trace.append(
                        make_state(
                            cycle, "compute", kk + 1, mac_done, False,
                            tile_cells, "computing", ti, tj, tk,
                        )
                    )

            # WRITEBACK this finished C-tile -> HBM
            cycle += 1
            trace.append(
                make_state(
                    cycle, "writeback", n, mac_done, True,
                    tile_cells, "wrote", ti, tj, None,
                )
            )

    # DONE
    cycle += 1
    trace.append(
        make_state(cycle, "done", n, mac_total, False, None, None, None, None, None)
    )

    return trace
