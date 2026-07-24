"""Full-trace invariants for the Pro Max Plus inference engine (style of the
GPU, R760, and PowerStore twins): assert over the whole simulate() trace, no
HTTP layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import GENERATION_PHASES, HOST_KINDS, MODEL_GB, simulate

PHASE_ORDER = [
    "off", "compile", "load", "resident",
    "prefill", "decode", "sustained", "offline",
]

KIND_BY_REGION = {r.id: r.kind for r in ANATOMY.regions}


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


def test_weights_cross_the_link_exactly_once():
    """THE invariant, and this twin's reason for existing. The PCIe boundary
    carries traffic during the load phase and during no other phase — not
    prefill, not decode, not the long sustained generation. The standard
    objection to a discrete accelerator is that the bus becomes the
    bottleneck; that assumes work crosses it continuously, and here what
    crosses is the model, once."""
    trace = simulate()
    busy = [s for s in trace if s.link_gbps > 0]
    assert busy, "the weights have to cross the link at some point"
    assert {s.phase for s in busy} == {"load"}, (
        f"link traffic outside the load phase: "
        f"{[(s.step, s.phase, s.link_gbps) for s in busy]}"
    )


def test_weights_are_monotonic_and_never_evicted():
    """Residency only ever grows, reaches the full model, and then stays
    exactly there. Nothing is paged out and nothing is swapped back in —
    that absence is what makes token latency predictable."""
    trace = simulate()
    resident = [s.weights_resident_gb for s in trace]
    assert all(a <= b for a, b in zip(resident, resident[1:])), (
        "weights were evicted"
    )
    assert max(resident) == MODEL_GB
    first_full = next(i for i, v in enumerate(resident) if v == MODEL_GB)
    for s in trace[first_full:]:
        assert s.weights_resident_gb == MODEL_GB, (
            f"step {s.step} ({s.phase}): model no longer fully resident"
        )


def test_no_tokens_before_the_model_is_resident():
    """Nothing can be generated from a model that is not all there."""
    for s in simulate():
        if s.tokens_per_second > 0:
            assert s.weights_resident_gb == MODEL_GB, (
                f"step {s.step}: generating with a partial model"
            )


def test_host_is_idle_during_generation():
    """Once tokens are flowing, the whole computation lives on the card: no
    host-side region (CPU, system DRAM, SSD) lights up. The counterpart to
    the Exascale twin's 'metadata leaves the data path'."""
    for s in simulate():
        if s.phase not in GENERATION_PHASES:
            continue
        for rid in s.active_regions:
            assert KIND_BY_REGION[rid] not in HOST_KINDS, (
                f"step {s.step} ({s.phase}): host-side region {rid!r} active "
                f"during generation"
            )


def test_sustained_power_never_throttles():
    """The discrete-NPU claim versus a laptop GPU: from the moment tokens
    start flowing, wattage holds flat instead of spiking and then sagging.
    For interactive use the rate you can hold is what matters, not peak."""
    trace = simulate()
    window = [s for s in trace if s.phase in GENERATION_PHASES]
    assert window, "no generation phases in the trace"
    peak = max(s.npu_watts for s in window)
    for s in window:
        assert s.npu_watts >= 0.9 * peak, (
            f"step {s.step} ({s.phase}): {s.npu_watts} W is a throttle from "
            f"{peak} W"
        )


def test_disconnecting_the_network_changes_nothing():
    """The last step is a non-event, which is the entire point: no counter
    that matters moves when the machine goes offline."""
    trace = simulate()
    sustained = next(s for s in trace if s.phase == "sustained")
    offline = next(s for s in trace if s.phase == "offline")
    assert offline.tokens_per_second == sustained.tokens_per_second
    assert offline.npu_watts == sustained.npu_watts
    assert offline.weights_resident_gb == sustained.weights_resident_gb
    assert offline.link_gbps == 0


def test_tokens_only_flow_after_prefill():
    """Prefill reads the prompt; decode emits. Nothing is generated before
    the prompt has been processed."""
    trace = simulate()
    first_token = next(i for i, s in enumerate(trace) if s.tokens_per_second > 0)
    prefill = next(i for i, s in enumerate(trace) if s.phase == "prefill")
    assert prefill < first_token


def test_card_is_always_lit_when_generating():
    """Both NPUs and the AI memory are working on every generating step —
    the model is partitioned across the whole card, not half of it."""
    for s in simulate():
        if s.tokens_per_second > 0:
            active = set(s.active_regions)
            assert {"npu-1", "npu-2", "aimem"} <= active, (
                f"step {s.step}: generating without the whole card"
            )


def test_active_regions_exist_in_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    for state in simulate():
        for rid in state.active_regions:
            assert rid in region_ids, f"step {state.step}: unknown region {rid!r}"


def test_cycle_cost_at_least_one():
    assert all(s.cycle_cost >= 1 for s in simulate())


def test_model_load_is_the_longest_stage():
    """Moving 61 GB across PCIe is the single longest stage — as with the
    R760's memory training and the SN6000's link training, the UI dwells
    here. It is also the only stage whose cost is paid per model rather than
    per prompt."""
    trace = simulate()
    load = [s for s in trace if s.phase == "load"]
    assert load, "no load step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert load[0].cycle_cost == max_cost
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
