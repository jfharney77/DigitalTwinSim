"""Full-trace invariants for the data-lifecycle engine (style of the GPU,
R760, and PowerStore twins): assert over the whole simulate() trace, no HTTP
layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import VAULT, simulate

PHASE_ORDER = [
    "idle", "backup", "dedupe", "replicate", "airgap", "scan",
    "attack", "recover", "restored",
]

GAP_OPEN_PHASES = {"replicate", "recover"}


def test_steps_sequential_from_zero():
    trace = simulate()
    assert [s.step for s in trace] == list(range(len(trace)))


def test_phase_order_never_regresses_and_all_phases_appear():
    trace = simulate()
    indices = [PHASE_ORDER.index(s.phase) for s in trace]
    assert indices == sorted(indices), "phase order regressed"
    assert set(s.phase for s in trace) == set(PHASE_ORDER)


def test_elapsed_hours_strictly_increasing():
    trace = simulate()
    elapsed = [s.elapsed_hours for s in trace]
    assert all(a < b for a, b in zip(elapsed, elapsed[1:]))


def test_dedupe_economics():
    """Physical never exceeds logical; protected data never shrinks; and
    once backups accumulate, the ratio is long — the arithmetic that makes
    an affordable vault possible."""
    trace = simulate()
    logical = [s.logical_tb for s in trace]
    assert logical == sorted(logical), "protected data regressed"
    for s in trace:
        assert s.stored_tb <= s.logical_tb, (
            f"step {s.step}: stored {s.stored_tb} > logical {s.logical_tb}"
        )
    reached_dedupe = False
    for s in trace:
        if s.phase == "dedupe":
            reached_dedupe = True
        if reached_dedupe:
            assert s.stored_tb > 0 and s.logical_tb / s.stored_tb >= 10, (
                f"step {s.step} ({s.phase}): dedupe ratio "
                f"{s.logical_tb}/{s.stored_tb} below 10:1"
            )


def test_air_gap_discipline():
    """The gap region is active only while the vault itself opens it —
    replication in, recovery out. Every other step of the data's life, the
    gap is closed and dark."""
    for s in simulate():
        if "gap" in s.active_regions:
            assert s.phase in GAP_OPEN_PHASES, (
                f"step {s.step}: gap open during {s.phase!r}"
            )
    # And it genuinely opens for both.
    open_phases = {s.phase for s in simulate() if "gap" in s.active_regions}
    assert open_phases == GAP_OPEN_PHASES


def test_attack_cannot_reach_the_vault():
    """The signature beat: at the attack step, nothing on the vault side
    lights — not the vault appliance, not CyberSense, not the clean room,
    and not the gap. What the malware cannot reach, it cannot encrypt."""
    attack = [s for s in simulate() if s.phase == "attack"]
    assert attack, "no attack step in the trace"
    for s in attack:
        active = set(s.active_regions)
        assert not (active & set(VAULT)), (
            f"step {s.step}: vault regions {active & set(VAULT)} lit during the attack"
        )
        assert "gap" not in active, f"step {s.step}: gap open during the attack"
        assert active, "the attack lights the production blast radius"


def test_vault_is_immutable_before_the_attack():
    """The vaulted copy exists and is sealed (airgap phase) strictly before
    ransomware detonates — a vault built after the incident is a wish."""
    trace = simulate()
    first_sealed = next(i for i, s in enumerate(trace) if s.phase == "airgap")
    first_attack = next(i for i, s in enumerate(trace) if s.phase == "attack")
    assert first_sealed < first_attack


def test_active_regions_exist_in_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    for state in simulate():
        for rid in state.active_regions:
            assert rid in region_ids, f"step {state.step}: unknown region {rid!r}"


def test_cycle_cost_at_least_one():
    assert all(s.cycle_cost >= 1 for s in simulate())


def test_cybersense_scan_is_the_longest_stage():
    """The CyberSense content scan is the single longest stage — like the
    R760's memory training or the IR7000's leak verification, the UI dwells
    here."""
    trace = simulate()
    scan = [s for s in trace if s.phase == "scan"]
    assert scan, "no scan step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert scan[0].cycle_cost == max_cost
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1


def test_recovery_flows_from_the_vault():
    """The recover step is driven from the vault side: the vault appliance
    and clean room are active, the gap is open, and production's appliance
    receives."""
    recover = [s for s in simulate() if s.phase == "recover"]
    assert recover, "no recover step"
    for s in recover:
        active = set(s.active_regions)
        assert "dd-vault" in active and "recovery-host" in active
        assert "gap" in active and "dd-prod" in active


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
