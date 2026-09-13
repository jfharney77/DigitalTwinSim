"""Full-trace invariants for the server power-on engine (style of the GPU,
R760, and XE9712 twins): assert over the whole simulate() trace, no HTTP
layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import GPUS, simulate
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PHASE_ORDER = ["off", "power", "post", "gpuinit", "fuse", "fabric", "ready"]


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
