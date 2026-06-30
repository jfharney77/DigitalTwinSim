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

from .mapping import cell_to_core
from .models import CoreState, GpuProfile, SimState, Workload


def effective_tile_size(n: int, tile_size: int) -> int:
    """0 (or >= N) means 'whole matrix'; otherwise clamp into [1, N]."""
    if tile_size <= 0 or tile_size >= n:
        return n
    return tile_size


def _ranges(n: int, t: int) -> list[tuple[int, int]]:
    """Tile spans along one dimension; the last tile may be a partial edge."""
    return [(s, min(s + t, n)) for s in range(0, n, t)]


def simulate(profile: GpuProfile, workload: Workload) -> list[SimState]:
    """Build the full deterministic SimState trace."""
    total_cores = profile.total_cores()
    n = workload.n
    t = effective_tile_size(n, workload.tile_size)
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
                # LOAD A-tile (ti,tk) + B-tile (tk,tj) HBM -> shared mem
                cycle += 1
                trace.append(
                    make_state(
                        cycle, "load", k0, mac_done, True,
                        tile_cells, "loading", ti, tj, tk,
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
