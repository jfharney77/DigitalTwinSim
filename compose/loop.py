"""The C1 + C2 closed loop: a deterministic fixed point over whole runs.

Engines exchange whole traces, not ticks. Iteration 0 is the open-loop C1 run.
Iteration k runs PhysicsCompute with the events C2 derives from CDU run k−1
and the carried cap, then PhysicsCDU with the load C1 derives from that
compute run. The loop variable is run-integrated liquid energy. Fixed order,
fixed damping, fixed cap on iterations, no randomness: the same chain in gives
the same ``CoupledTrace`` out, byte for byte.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .couplings import c1_compute_heat_to_cdu as c1
from .couplings import c2_cdu_caps_to_compute as c2
from .models import IterationRecord
from .reader import series
from .resample import downsample, integral
from .loader import load_engine
from .runner import EngineRun, run_engine


@dataclass
class LoopResult:
    open_compute: EngineRun
    open_cdu: EngineRun
    compute: EngineRun
    cdu: EngineRun
    cdu_injected: list[dict]
    cdu_config: dict
    compute_injected: list[dict]
    iterations: int
    converged: bool
    residuals: list[float]
    records: list[IterationRecord]
    notes: list[str] = field(default_factory=list)
    supply_residual_c: float = 0.0
    racks: int = 1


def cdu_constants(handle: Any) -> dict:
    return {"group_kw": handle.C("group_kw"),
            "group_idle_fraction": handle.C("group_idle_fraction")}


def _trip_set(run: EngineRun) -> tuple[int, ...]:
    last = run.trace[-1]
    return tuple(i for i, s in enumerate(last.bank_status) if s == "tripped")


def fixed_point(
    compute_base: dict,
    cdu_base: dict,
    max_iter: int = 12,
    damping: float = 0.5,
    tol: float = 0.005,
    racks: int = 1,
) -> LoopResult:
    open_compute = run_engine("PhysicsCompute", compute_base)
    consts = cdu_constants(load_engine("PhysicsCDU"))
    cdu_scn, cdu_inj, cdu_cfg, notes = c1.adapt(open_compute.trace, cdu_base, cdu=consts, racks=racks)
    open_cdu = run_engine("PhysicsCDU", cdu_scn)

    n = len(open_compute.trace)
    carried = [1.0] * n
    energy = integral(series(open_compute.trace, "liquid_watts")) / 3.6e6
    records = [IterationRecord(
        index=0, loop_value=round(energy, 4), residual=1.0, note="open loop (C1 only)",
        series={"liquid_kw": downsample(c1.liquid_kw(open_compute.trace, racks)),
                "cap_pct": downsample(series(open_cdu.trace, "cap_pct")),
                "carried_cap_pct": downsample([100.0 * c for c in carried])},
    )]
    residuals: list[float] = []
    compute, cdu, comp_inj = open_compute, open_cdu, []
    converged = False
    pinned_note_done = False
    flow_setpoint = float(open_cdu.scenario.config.flow_setpoint_lpm)
    trays = int(open_compute.scenario.config.trays)
    iterations = 0
    supply_residual = 0.0

    for k in range(1, max_iter + 1):
        iterations = k
        cap = [c / 100.0 for c in series(cdu.trace, "cap_pct")]
        carried = [
            damping * (carried[t] * cap[t]) + (1.0 - damping) * carried[t]
            for t in range(n)
        ]
        comp_scn, comp_inj, c2_notes = c2.adapt(cdu.trace, compute_base, carried,
                                                flow_setpoint, trays)
        prev_cdu = cdu
        compute = run_engine("PhysicsCompute", comp_scn)
        cdu_scn, cdu_inj, cdu_cfg, c1_notes = c1.adapt(compute.trace, cdu_base, cdu=consts, racks=racks,
                                                        groups=open_cdu.scenario.config.tray_groups)
        cdu = run_engine("PhysicsCDU", cdu_scn)

        new_energy = integral(series(compute.trace, "liquid_watts")) / 3.6e6
        # Two things must stop moving: the loop variable, and the heat the CDU
        # still refuses (its remaining cap). Either alone can look settled early.
        #
        # "Refused" is read off the CDU's own cap, not off the difference between
        # the two engines' heat numbers. That difference also carries C1's
        # integer-utilization quantization, which is a fixed offset between the
        # engines: iterating cannot reduce it, so putting it in the residual gave
        # the loop a floor it could never clear and reported a stationary loop
        # (cap 100% on every tick, carried cap never moving) as not converged.
        moved = abs(new_energy - energy) / max(new_energy, 1e-9)
        # Ticks whose heat the CDU's bank formula cannot express are clamped on
        # the way in, so its cap on those ticks answers a load the rack never
        # had. C1 excludes them from the seam; the residual has to exclude them
        # too. An undersized CDU otherwise reads as a permanently unsettled loop:
        # the clamped run is identical every iteration, so the refused share is a
        # constant the iteration cannot move.
        ok = c1.expressible(compute.trace, consts, racks,
                            open_cdu.scenario.config.tray_groups)
        untripped = [i for i, st in enumerate(cdu.trace)
                     if st.trips == 0 and (i >= len(ok) or ok[i])]
        if not any(ok):
            undersized = (
                "No tick's heat fits the CDU's banks, so the refused-heat term has nothing "
                "to measure: the loop settles on its loop variable alone, and the C1 seam "
                "reports that the coupling does not hold."
            )
            if undersized not in notes:
                notes.append(undersized)
        weight = sum(cdu.trace[i].it_load_kw for i in untripped)
        refused = sum(
            cdu.trace[i].it_load_kw * (1.0 - cdu.trace[i].cap_pct / 100.0)
            for i in untripped
        ) / max(weight, 1e-9)
        residual = max(moved, refused)
        energy = new_energy
        residuals.append(round(residual, 6))
        # A latched trip set is recorded on every iteration that carries one —
        # it is the discontinuity the reader has to see, whether it arrived in
        # this iteration or came pinned out of the open-loop run. Only a set
        # that *moved* holds the solver back from declaring convergence.
        trips, prev_trips = _trip_set(cdu), _trip_set(prev_cdu)
        moved_trips = trips != prev_trips
        note = f"trip set pinned at iter {k}: banks {list(trips)}" if trips else ""
        if moved_trips:
            if not pinned_note_done:
                notes.append(
                    "Latched trips make the loop map discontinuous; the solver keeps the "
                    "trip set of the later iteration and continues."
                )
                pinned_note_done = True
        records.append(IterationRecord(
            index=k, loop_value=round(energy, 4), residual=round(residual, 6), note=note,
            series={"liquid_kw": downsample(c1.liquid_kw(compute.trace, racks)),
                    "cap_pct": downsample(series(cdu.trace, "cap_pct")),
                    "carried_cap_pct": downsample([100.0 * c for c in carried])},
        ))
        supply_residual = max(
            abs(a - b) for a, b in zip(series(cdu.trace, "sec_supply_c"),
                                       series(prev_cdu.trace, "sec_supply_c"))
        )
        for extra in c2_notes + c1_notes:
            if extra not in notes:
                notes.append(extra)
        if residual < tol and not moved_trips:
            converged = True
            break

    if not converged:
        notes.append(f"The loop did not settle within {max_iter} iterations; "
                     "the last iteration is reported and the seams say what is still open.")
    return LoopResult(
        open_compute=open_compute, open_cdu=open_cdu, compute=compute, cdu=cdu,
        cdu_injected=cdu_inj, cdu_config=cdu_cfg, compute_injected=comp_inj,
        iterations=iterations, converged=converged, residuals=residuals,
        records=records, notes=notes, supply_residual_c=round(supply_residual, 3), racks=racks,
    )
