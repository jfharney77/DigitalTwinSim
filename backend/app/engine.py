"""Pure, deterministic simulation engine.

Given a GpuProfile + Workload it produces the entire SimState trace. There are
no timers and no I/O here -- the frontend owns the clock and just plays the
trace back (spec §1 principle 3, §2). Same inputs -> same trace.

This implements the spec's 5-phase model (idle -> load -> compute -> writeback
-> done), which differs from the original gpu-sim.html oracle (3 phases, with
writeback folded into the last compute step). See CLAUDE.md "Oracle vs. spec".
"""

from __future__ import annotations

from .mapping import mapped_cores
from .models import CoreState, GpuProfile, SimState, Workload


def _state(
    cycle: int,
    phase: str,
    k: int,
    mac_done: int,
    mac_total: int,
    mem_active: bool,
    core_state: list[CoreState],
    active_cores: int,
    total_cores: int,
) -> SimState:
    return SimState(
        cycle=cycle,
        phase=phase,  # type: ignore[arg-type]
        k=k,
        mac_done=mac_done,
        mac_total=mac_total,
        mem_active=mem_active,
        core_state=core_state,
        active_cores=active_cores,
        utilization=(active_cores / total_cores) if total_cores else 0.0,
    )


def simulate(profile: GpuProfile, workload: Workload) -> list[SimState]:
    """Build the full deterministic SimState trace."""
    total_cores = profile.total_cores()
    n = workload.n
    mac_total = n * n * n
    mapped = mapped_cores(n, total_cores)
    active = len(mapped)

    def cores(label: CoreState | None) -> list[CoreState]:
        cs: list[CoreState] = ["idle"] * total_cores
        if label is not None:
            for c in mapped:
                cs[c] = label
        return cs

    trace: list[SimState] = []
    cycle = 0

    # idle -- before Run
    trace.append(
        _state(cycle, "idle", 0, 0, mac_total, False, cores(None), 0, total_cores)
    )

    # LOAD -- operand tiles HBM -> shared mem (one step)
    cycle += 1
    trace.append(
        _state(
            cycle, "load", 0, 0, mac_total, True, cores("loading"), active, total_cores
        )
    )

    # COMPUTE -- N accumulation steps; each adds N*N MACs
    mac_done = 0
    for k in range(1, n + 1):
        cycle += 1
        mac_done += n * n
        trace.append(
            _state(
                cycle,
                "compute",
                k,
                mac_done,
                mac_total,
                False,
                cores("computing"),
                active,
                total_cores,
            )
        )

    # WRITEBACK -- results flush to C
    cycle += 1
    trace.append(
        _state(
            cycle,
            "writeback",
            n,
            mac_total,
            mac_total,
            True,
            cores("wrote"),
            active,
            total_cores,
        )
    )

    # DONE
    cycle += 1
    trace.append(
        _state(cycle, "done", n, mac_total, mac_total, False, cores(None), 0, total_cores)
    )

    return trace
