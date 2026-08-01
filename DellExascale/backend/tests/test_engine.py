"""Full-trace invariants for the Exascale data-path engine (style of the
GPU, R760, and PowerStore twins): assert over the whole simulate() trace, no
HTTP layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import BULK_PHASES, DATA_SERVERS, simulate

PHASE_ORDER = [
    "idle", "mount", "layout", "stripe", "feed", "checkpoint", "tier", "steady",
]


def test_steps_sequential_from_zero():
    trace = simulate()
    assert [s.step for s in trace] == list(range(len(trace)))


def test_phase_order_never_regresses_and_all_phases_appear():
    trace = simulate()
    indices = [PHASE_ORDER.index(s.phase) for s in trace]
    assert indices == sorted(indices), "phase order regressed"
    assert set(s.phase for s in trace) == set(PHASE_ORDER)


def test_elapsed_seconds_strictly_increasing():
    trace = simulate()
    elapsed = [s.elapsed_seconds for s in trace]
    assert all(a < b for a, b in zip(elapsed, elapsed[1:]))


def test_metadata_leaves_the_data_path():
    """THE invariant of a parallel file system, and this twin's reason for
    existing: the metadata server answers one question (the layout) and is
    then absent from every phase that moves bulk data. Contrast the block
    twins, where every byte crosses a controller."""
    for s in simulate():
        if s.phase in BULK_PHASES:
            assert "metadata" not in s.active_regions, (
                f"step {s.step} ({s.phase}): metadata server in the data path"
            )
    # And it genuinely participates in the control path.
    control = {s.phase for s in simulate() if "metadata" in s.active_regions}
    assert control == {"mount", "layout"}


def test_layout_precedes_any_data_movement():
    """No stripe may be read before the client holds a layout — the client
    literally does not know which servers to ask until then."""
    trace = simulate()
    first_layout = next(i for i, s in enumerate(trace) if s.layout_held)
    first_bulk = next(i for i, s in enumerate(trace) if s.throughput_gbps > 0)
    assert first_layout < first_bulk
    # Once granted, the layout is held for the rest of the job.
    for s in trace[first_layout:]:
        assert s.layout_held, f"step {s.step}: layout lost mid-job"


def test_throughput_requires_parallel_fan_out():
    """Throughput comes from servers streaming in parallel, not from one
    controller: whenever bytes move, every drawn data server is streaming,
    and zero servers always means zero throughput."""
    n = len(DATA_SERVERS)
    for s in simulate():
        if s.throughput_gbps > 0:
            assert s.data_servers_streaming == n, (
                f"step {s.step}: {s.data_servers_streaming}/{n} servers "
                f"streaming while moving {s.throughput_gbps} Gbps"
            )
        else:
            assert s.data_servers_streaming == 0, (
                f"step {s.step}: servers streaming with no throughput"
            )


def test_data_servers_light_in_lockstep():
    """A striped read fans out to every data server at once — whenever any
    data server is active, all of them are, each with its media."""
    for state in simulate():
        active = set(state.active_regions)
        lit = {rid for rid in active if rid.startswith("data-")}
        if lit:
            assert lit == {f"data-{d}" for d in DATA_SERVERS}, (
                f"step {state.step}: partial fan-out {lit}"
            )
            for d in DATA_SERVERS:
                assert f"media-{d}" in active, (
                    f"step {state.step}: data-{d} streaming without its media"
                )


def test_peak_throughput_reaches_rack_scale():
    """The rack's headline number: ~6 TB/s ≈ 48,000 Gbps at full read."""
    trace = simulate()
    assert max(s.throughput_gbps for s in trace) >= 48000
    assert trace[0].throughput_gbps == 0, "starts idle with no job attached"


def test_active_regions_exist_in_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    for state in simulate():
        for rid in state.active_regions:
            assert rid in region_ids, f"step {state.step}: unknown region {rid!r}"


def test_cycle_cost_at_least_one():
    assert all(s.cycle_cost >= 1 for s in simulate())


def test_checkpoint_is_the_longest_stage():
    """The checkpoint burst is the single longest stage — pure overhead
    while it runs, and the thing that bounds how much work a failure can
    destroy. The UI dwells here."""
    trace = simulate()
    ckpt = [s for s in trace if s.phase == "checkpoint"]
    assert ckpt, "no checkpoint step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert ckpt[0].cycle_cost == max_cost
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
