"""Full-trace invariants for the Exascale data-path engine (style of the
GPU, R760, and PowerStore twins): assert over the whole simulate() trace, no
HTTP layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import BULK_PHASES, DATA_SERVERS, simulate
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PHASE_ORDER = [
    "idle", "mount", "layout", "stripe", "feed", "checkpoint", "tier", "steady",
]


PROFILE = TraceProfile(phases=PHASE_ORDER, anatomy=ANATOMY)


def test_trace_invariants():
    """Steps from zero, phases in order and all reached, the clock advancing,
    only real regions lit, every step at least one cycle — and deterministic.
    The shared definitions live in twinkit.testing."""
    assert_trace_invariants(simulate(), PROFILE)
    assert_deterministic(simulate)


def test_engine_is_pure():
    import app.engine as engine_module

    assert_engine_is_pure(engine_module)


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
