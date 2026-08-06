"""Full-trace invariants for the server power-on engine (style of the GPU,
R760, and XE9712 twins): assert over the whole simulate() trace, no HTTP
layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import GPUS, simulate

PHASE_ORDER = ["off", "power", "post", "gpuinit", "fuse", "fabric", "ready"]


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


def test_power_watts_monotonic_with_the_jump_at_gpuinit():
    """Power only climbs during bring-up, ending on the order of 11 kW, and
    the single biggest jump is the eight SXM GPUs waking — in this box the
    power story *is* the GPU story."""
    trace = simulate()
    watts = [s.power_watts for s in trace]
    assert watts[0] == 0, "starts dark before the PSUs energize"
    assert watts == sorted(watts), "power draw regressed during bring-up"
    assert watts[-1] == max(watts) and watts[-1] >= 10_000, "ends near full load"
    jumps = {b.phase: b.power_watts - a.power_watts for a, b in zip(trace, trace[1:])}
    assert max(jumps, key=lambda p: jumps[p]) == "gpuinit"


def test_the_host_boots_before_any_gpu():
    """A GPU server is still a server: the Xeons must POST before the first
    accelerator comes out of reset."""
    trace = simulate()
    first_post = next(i for i, s in enumerate(trace) if s.phase == "post")
    first_gpu = next(i for i, s in enumerate(trace) if s.phase == "gpuinit")
    assert first_post < first_gpu


def test_active_regions_exist_in_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    for state in simulate():
        for rid in state.active_regions:
            assert rid in region_ids, f"step {state.step}: unknown region {rid!r}"


def test_cycle_cost_at_least_one():
    assert all(s.cycle_cost >= 1 for s in simulate())


def test_gpu_init_is_the_longest_stage():
    """Waking eight SXM GPUs and training their HBM is the single longest
    stage — the in-box counterpart of the XE9712's NVLink cable training,
    which this server does not need: its fuse is board traces."""
    trace = simulate()
    gpuinit = [s for s in trace if s.phase == "gpuinit"]
    assert gpuinit, "no gpuinit step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert gpuinit[0].cycle_cost == max_cost
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


def test_gpus_light_in_lockstep():
    """Whatever lights on one SXM socket lights on all eight — the
    baseboard's GPUs are identical and wake in parallel."""
    for state in simulate():
        active = set(state.active_regions)
        for rid in active:
            base, _, suffix = rid.rpartition("-")
            if suffix in GPUS:
                for g in GPUS:
                    twin = f"{base}-{g}"
                    assert twin in active, (
                        f"step {state.step}: {rid} lit without its twin {twin}"
                    )


def test_the_fuse_is_atomic_and_the_domain_stops_at_eight():
    """The signature pair of facts. gpus_in_domain is zero through the whole
    bring-up and snaps to 8 exactly at the fuse — no partial domain — and it
    never exceeds 8 afterward: joining the cluster fabric does not grow the
    NVLink domain, because the domain ends at the chassis wall."""
    trace = simulate()
    fuse_at = next(i for i, s in enumerate(trace) if s.phase == "fuse")
    for i, s in enumerate(trace):
        assert s.gpus_in_domain == (0 if i < fuse_at else 8), (
            f"step {s.step} ({s.phase}): gpus_in_domain={s.gpus_in_domain}"
        )
    # At the fuse moment, every GPU region is active alongside the NVSwitch.
    gpu_regions = {r.id for r in ANATOMY.regions if r.kind == "gpu"}
    fuse_active = set(trace[fuse_at].active_regions)
    assert gpu_regions <= fuse_active, "fuse step must light every GPU region"
    assert "nvswitch" in fuse_active


def test_one_nic_per_gpu_joins_the_fabric_after_the_fuse():
    """Scale past eight is the fabric's job: nics_up is zero until the
    fabric phase, then exactly 8 — one per GPU — and the fabric step lights
    every NIC region. The fuse must already be complete: NVLink inside the
    box, Ethernet beyond it, in that order."""
    trace = simulate()
    fuse_at = next(i for i, s in enumerate(trace) if s.phase == "fuse")
    fabric_at = next(i for i, s in enumerate(trace) if s.phase == "fabric")
    assert fuse_at < fabric_at, "the domain fuses before the box reaches outward"
    for i, s in enumerate(trace):
        assert s.nics_up == (0 if i < fabric_at else 8), (
            f"step {s.step} ({s.phase}): nics_up={s.nics_up}"
        )
    nic_regions = {r.id for r in ANATOMY.regions if r.kind == "network"}
    assert nic_regions <= set(trace[fabric_at].active_regions), (
        "fabric step must light every per-GPU NIC"
    )
    # At the end, both counters read 8 — the box's whole architecture in
    # two numbers.
    assert trace[-1].gpus_in_domain == 8 and trace[-1].nics_up == 8


def test_fans_run_whenever_gpus_draw_power():
    """Air is the coolant: from the first gpuinit step to the end of the
    trace, the fan banks are active on every step. In an air-cooled server
    cooling is not a phase of bring-up — it is a condition of staying up."""
    trace = simulate()
    fan_regions = {r.id for r in ANATOMY.regions if r.kind == "cooling"}
    assert fan_regions, "anatomy has no fan banks"
    first_gpu = next(i for i, s in enumerate(trace) if s.phase == "gpuinit")
    for s in trace[first_gpu:]:
        assert fan_regions <= set(s.active_regions), (
            f"step {s.step} ({s.phase}): GPUs are powered but fans are dark"
        )


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
