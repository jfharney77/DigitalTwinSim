"""Full-trace invariants for the Private Cloud engine (style of the GPU,
R760, and PowerStore twins): assert over the whole simulate() trace, no HTTP
layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import (
    COMPUTE_CHANGE_PHASES,
    HYPERVISORS,
    POOLS,
    SERVING_PHASES,
    STORAGE_CHANGE_PHASES,
    simulate,
)

PHASE_ORDER = [
    "off", "pools", "control", "install",
    "deploy", "run", "growstorage", "switch", "mixed",
]


def test_steps_sequential_from_zero():
    trace = simulate()
    assert [s.step for s in trace] == list(range(len(trace)))


def test_phase_order_never_regresses_and_all_phases_appear():
    trace = simulate()
    indices = [PHASE_ORDER.index(s.phase) for s in trace]
    assert indices == sorted(indices), "phase order regressed"
    assert set(s.phase for s in trace) == set(PHASE_ORDER)


def test_elapsed_minutes_strictly_increasing():
    trace = simulate()
    elapsed = [s.elapsed_minutes for s in trace]
    assert all(a < b for a, b in zip(elapsed, elapsed[1:]))


def test_compute_and_storage_scale_independently():
    """THE invariant, and this twin's reason for existing. At the storage
    expansion, capacity doubles and the compute pool does not move. On a
    hyperconverged cluster — this repo's VxRail twin — the same need is met
    by adding nodes, and a node brings processors whether or not anyone
    wanted them, which is why estates so routinely own a third more of one
    resource than they will ever use."""
    trace = simulate()
    grow = next(i for i, s in enumerate(trace) if s.phase == "growstorage")
    before, after = trace[grow - 1], trace[grow]
    assert after.storage_tb > before.storage_tb, "storage did not actually grow"
    assert after.compute_units == before.compute_units, (
        f"adding storage dragged compute along: "
        f"{before.compute_units} -> {after.compute_units}"
    )


def test_nothing_scales_that_was_not_asked_for():
    """The stricter form: across the whole trace, each resource changes only
    in the phases that exist to change it. Coupling would show up as a
    quantity moving in a step that had nothing to do with it."""
    trace = simulate()
    for prev, cur in zip(trace, trace[1:]):
        if cur.compute_units != prev.compute_units:
            assert cur.phase in COMPUTE_CHANGE_PHASES, (
                f"compute changed during {cur.phase}"
            )
        if cur.storage_tb != prev.storage_tb:
            assert cur.phase in STORAGE_CHANGE_PHASES, (
                f"storage changed during {cur.phase}"
            )


def test_one_control_plane_regardless_of_hypervisor_count():
    """Multi-hypervisor is only worth having if it does not also mean
    multi-management. Two hypervisors, one console — otherwise 'we support
    both' means 'we will sell you both problems'."""
    trace = simulate()
    for s in trace:
        assert s.control_planes <= 1, (
            f"step {s.step} ({s.phase}): {s.control_planes} control planes"
        )
    mixed = next(s for s in trace if s.phase == "mixed")
    assert mixed.hypervisors_active == 2, "the trace must actually run two"
    assert mixed.control_planes == 1


def test_the_workloads_never_notice():
    """Storage doubles and a second hypervisor arrives; the workload count
    and the downtime counter both hold still. Flexibility the applications
    can feel is flexibility nobody will use."""
    trace = simulate()
    for s in trace:
        assert s.workload_downtime_seconds == 0, (
            f"step {s.step} ({s.phase}): {s.workload_downtime_seconds}s of "
            f"downtime"
        )
    serving = [s for s in trace if s.phase in SERVING_PHASES]
    assert serving, "no serving phases"
    counts = {s.workloads for s in serving}
    assert len(counts) == 1, f"workload count moved during operations: {counts}"
    assert serving[0].workloads > 0


def test_the_hypervisor_is_a_choice_not_a_foundation():
    """No hypervisor is present in every step, and the estate acquires a
    second one without anything beneath it changing. In a hyperconverged
    system the hypervisor is not a layer you select — it is what the
    architecture is made of."""
    trace = simulate()
    for hv in HYPERVISORS:
        assert not all(hv in s.active_regions for s in trace), (
            f"{hv} is present on every step — that is a foundation, not a slot"
        )
    switch = next(s for s in trace if s.phase == "switch")
    before = trace[switch.step - 1]
    assert switch.hypervisors_active > before.hypervisors_active
    assert switch.compute_units == before.compute_units
    assert switch.storage_tb == before.storage_tb
    assert switch.control_planes == before.control_planes
    assert switch.workloads == before.workloads


def test_at_most_one_hypervisor_slot_stays_empty_unused():
    """The map offers four interchangeable slots and the trace uses two of
    them, which is the point — the other two are options that were not
    taken, not missing features."""
    trace = simulate()
    used = {hv for s in trace for hv in HYPERVISORS if hv in s.active_regions}
    assert 1 <= len(used) < len(HYPERVISORS), (
        "the trace should exercise some slots and leave others available"
    )


def test_the_control_plane_precedes_any_hypervisor():
    """Disaggregation without a unified control plane is just the old
    three-tier world, so the control plane is established before anything is
    layered on it."""
    trace = simulate()
    first_cp = next(i for i, s in enumerate(trace) if s.control_planes > 0)
    first_hv = next(i for i, s in enumerate(trace) if s.hypervisors_active > 0)
    assert first_cp < first_hv


def test_pools_exist_before_anything_runs_on_them():
    trace = simulate()
    first_pool = next(i for i, s in enumerate(trace) if s.storage_tb > 0)
    first_workload = next(i for i, s in enumerate(trace) if s.workloads > 0)
    assert first_pool < first_workload
    for s in trace:
        if s.workloads > 0:
            for pool in POOLS:
                assert pool in s.active_regions, (
                    f"step {s.step}: workloads running without the {pool} pool"
                )


def test_active_regions_exist_in_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    for state in simulate():
        for rid in state.active_regions:
            assert rid in region_ids, f"step {state.step}: unknown region {rid!r}"


def test_cycle_cost_at_least_one():
    assert all(s.cycle_cost >= 1 for s in simulate())


def test_hypervisor_migration_is_the_longest_stage():
    """Honesty about the cost of the freedom. Moving workloads between
    virtualization platforms is real work — format conversion, testing, and
    care about what does not translate — and the trace should not pretend
    otherwise. The claim is that it is possible without an outage, not that
    it is quick."""
    trace = simulate()
    sw = [s for s in trace if s.phase == "switch"]
    assert sw, "no migration step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert sw[0].cycle_cost == max_cost
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


def test_engine_is_pure():
    """The engine must not import FastAPI/IO — same rule as every twin."""
    import ast

    import app.engine as engine_module

    tree = ast.parse(open(engine_module.__file__, encoding="utf-8").read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & {"fastapi", "time", "asyncio", "threading", "os", "io"}
