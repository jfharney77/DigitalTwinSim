"""Full-trace invariants for the rack power-on engine (style of the GPU,
R760, and PowerStore twins): assert over the whole simulate() trace, no HTTP
layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import TRAYS, simulate
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PHASE_ORDER = [
    "off", "power", "coolant", "trayboot", "gpuinit", "fabric", "fused", "ready",
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


def test_power_watts_monotonic_to_full_load():
    """Power only climbs during bring-up — the rack never sheds load on the
    way to ~120 kW, and the GPU-init step is where draw goes vertical."""
    trace = simulate()
    watts = [s.power_watts for s in trace]
    assert watts[0] == 0, "starts dark before the shelves energize"
    assert watts == sorted(watts), "power draw regressed during bring-up"
    assert watts[-1] == max(watts) and watts[-1] >= 100_000, "ends near full load"
    # The single biggest jump in draw is the Blackwell GPUs waking up.
    jumps = {b.phase: b.power_watts - a.power_watts for a, b in zip(trace, trace[1:])}
    assert max(jumps, key=lambda p: jumps[p]) == "gpuinit"


def test_coolant_flows_before_any_silicon():
    """Liquid before silicon: the coolant phase must complete its first step
    before the first compute tray powers on — the inversion that makes a
    liquid-cooled rack different from every air-cooled twin in this repo."""
    trace = simulate()
    first_coolant = next(i for i, s in enumerate(trace) if s.phase == "coolant")
    first_tray = next(i for i, s in enumerate(trace) if s.phase == "trayboot")
    assert first_coolant < first_tray


def test_fabric_training_is_the_longest_stage():
    """Training the NVLink links (over 5,000+ copper cables) is the single longest stage — like the
    R760's memory training or VxRail's cluster build, the UI dwells here."""
    trace = simulate()
    fabric = [s for s in trace if s.phase == "fabric"]
    assert fabric, "no fabric-training step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert fabric[0].cycle_cost == max_cost
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


def test_trays_boot_in_lockstep():
    """In the trayboot/gpuinit phases, whatever lights on one tray lights on
    all trays — the rack's trays are identical and wake in parallel."""
    for state in simulate():
        if state.phase not in ("trayboot", "gpuinit"):
            continue
        active = set(state.active_regions)
        for rid in active:
            base, _, suffix = rid.rpartition("-")
            if suffix in TRAYS:
                for t in TRAYS:
                    twin = f"{base}-{t}"
                    assert twin in active, (
                        f"step {state.step}: {rid} lit without its twin {twin}"
                    )


def test_fuse_joins_all_72_gpus_at_once():
    """The signature beat: gpus_in_domain is zero for the entire bring-up and
    snaps to 72 exactly when the fabric fuses — there is no partial domain."""
    trace = simulate()
    fused_at = next(i for i, s in enumerate(trace) if s.phase == "fused")
    for i, s in enumerate(trace):
        assert s.gpus_in_domain == (0 if i < fused_at else 72), (
            f"step {s.step} ({s.phase}): gpus_in_domain={s.gpus_in_domain}"
        )
    # And at the fuse moment, every GPU region is active alongside the fabric.
    gpu_regions = {r.id for r in ANATOMY.regions if r.kind == "gpu"}
    fused_active = set(trace[fused_at].active_regions)
    assert gpu_regions <= fused_active, "fuse step must light every GPU region"
    assert any(r.startswith("nvswitch") for r in fused_active)
