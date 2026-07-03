"""Maps output matrix cells onto physical cores.

Tile-aware (spec §4): a whole output tile is assigned to exactly one SM, and its
cells map to lanes *within that SM*. This mirrors real hardware -- an output tile
is a thread block resident in one SM's shared memory, so all of its output cells
compute on that SM's lanes and a tile never straddles two SMs (they do not share
memory). Independent tiles round-robin across SMs.

The legacy global round-robin (`cell_to_core`) is kept for reference; it ignored
tile/SM structure and could scatter one tile across several SMs.
"""

from __future__ import annotations


def cell_to_core(i: int, j: int, n: int, total_cores: int) -> int:
    """Legacy global round-robin: core = (i*N + j) % totalCores.

    Superseded by `tile_aware_core`; retained for whole-die enumeration and to
    document the original (deliberately naive) scheme.
    """
    return (i * n + j) % total_cores


def tile_aware_core(
    i: int,
    j: int,
    *,
    tile_size: int,
    tile_row: int,
    tile_col: int,
    num_tile_cols: int,
    num_sms: int,
    cores_per_sm: int,
) -> int:
    """Physical core for output cell (i, j), keeping its whole tile inside one SM.

    The tile is round-robined onto an SM by its linear index; the cell then maps
    to a lane within that SM by its position inside the tile. Returns a flat core
    index matching the die layout (sm * cores_per_sm + lane).
    """
    tile_index = tile_row * num_tile_cols + tile_col
    sm = tile_index % num_sms
    local_i = i - tile_row * tile_size
    local_j = j - tile_col * tile_size
    lane = (local_i * tile_size + local_j) % cores_per_sm
    return sm * cores_per_sm + lane
