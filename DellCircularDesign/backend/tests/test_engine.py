"""Full-trace invariants for the circular-design lifecycle engine (style
of the GPU, IR7000, and PowerScale twins): assert over the whole
simulate() trace, no HTTP layer."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import (
    ACCOUNTED_PHASES,
    COHORT_MASS_KG,
    FIRST_PASS_RECYCLED_PERCENT,
    LOST_KG,
    RECLAIMED_KG,
    REUSED_KG,
    UNREPAIRED_SERVICE_YEARS,
    simulate,
)

PHASE_ORDER = [
    "materials", "manufacture", "ship", "deploy", "serve",
    "repair", "extend", "recover", "sort", "reborn",
]


def test_steps_sequential_from_zero():
    trace = simulate()
    assert [s.step for s in trace] == list(range(len(trace)))


def test_phase_order_never_regresses_and_all_phases_appear():
    trace = simulate()
    indices = [PHASE_ORDER.index(s.phase) for s in trace]
    assert indices == sorted(indices), "phase order regressed"
    assert set(s.phase for s in trace) == set(PHASE_ORDER)


def test_elapsed_months_strictly_increasing():
    trace = simulate()
    elapsed = [s.elapsed_months for s in trace]
    assert all(a < b for a, b in zip(elapsed, elapsed[1:]))


def test_mass_is_conserved():
    """THE invariant, and the direct analogue of the IR7000's heat balance
    (liquid_watts + air_watts == it_load_watts, no tolerance) — applied to
    matter instead of energy. From the recover step onward, every kilogram
    is accounted for: reused + reclaimed + lost == mass, exactly. Before
    recovery the accounting has not opened, so all three destinations are
    zero. Mass itself never changes — matter is not created or destroyed
    by accounting."""
    trace = simulate()
    assert any(s.phase in ACCOUNTED_PHASES for s in trace), (
        "no accounted step — the invariant would be untested"
    )
    for s in trace:
        assert s.mass_kg == COHORT_MASS_KG, (
            f"step {s.step} ({s.phase}): mass changed to {s.mass_kg}"
        )
        if s.phase in ACCOUNTED_PHASES:
            total = s.reused_kg + s.reclaimed_kg + s.lost_kg
            assert total == s.mass_kg, (
                f"step {s.step} ({s.phase}): {total} kg accounted for, "
                f"{s.mass_kg} kg went in — {s.mass_kg - total} kg vanished "
                f"from the ledger"
            )
        else:
            assert s.reused_kg == s.reclaimed_kg == s.lost_kg == 0, (
                f"step {s.step} ({s.phase}): destinations nonzero before "
                f"the accounting opened"
            )


def test_the_loss_is_stated_not_hidden():
    """lost_kg > 0 at the end, and the loss region is lit when the sort
    happens. A twin claiming a perfectly closed loop would be lying, and
    this test makes lying impossible: the leak is measured, nonzero, and
    drawn."""
    trace = simulate()
    final = trace[-1]
    assert final.lost_kg > 0, (
        "zero loss claimed — no real supply chain does that; the leak "
        "must be stated"
    )
    sort_steps = [s for s in trace if s.phase == "sort"]
    assert sort_steps, "no sort step — the loss would never be shown"
    for s in sort_steps:
        assert "loss" in s.active_regions, (
            f"step {s.step}: sorting without lighting the loss region — "
            f"the leak is being hidden"
        )
    # And the loss never shrinks once stated: lost material does not
    # quietly come back.
    losses = [s.lost_kg for s in trace]
    assert all(a <= b for a, b in zip(losses, losses[1:])), (
        "lost_kg fell — lost material does not come back"
    )


def test_reuse_is_preferred_to_reclaim():
    """reused_kg > 0, reuse carries more mass than reclamation, and the
    trace attempts refurbishment before material reclamation: the
    refurbish region lights strictly before the reclaim region ever does.
    A device broken down for materials that could have been refurbished
    is a loss even though the mass balances."""
    trace = simulate()
    final = trace[-1]
    assert final.reused_kg > 0, "nothing refurbished — reuse was skipped"
    assert final.reused_kg > final.reclaimed_kg, (
        "reclamation outweighs reuse — the preference is inverted"
    )
    first_refurb = next(
        (i for i, s in enumerate(trace) if "refurbish" in s.active_regions),
        None,
    )
    first_reclaim = next(
        (i for i, s in enumerate(trace) if "reclaim" in s.active_regions),
        None,
    )
    assert first_refurb is not None, "the refurbish path is never attempted"
    assert first_reclaim is not None, "the reclaim path never runs"
    assert first_refurb < first_reclaim, (
        "reclamation started before refurbishment was attempted"
    )


def test_repair_extends_service_life():
    """The deferral, demonstrated rather than asserted: at the recover
    step the cohort has repairs on the books and strictly more service
    years than the no-repair baseline (UNREPAIRED_SERVICE_YEARS — the
    year the fleet would have been refreshed with a glued-in battery).
    Each repair postpones an entire manufacturing cycle, which is the
    largest lever in the whole trace."""
    trace = simulate()
    recover = next(s for s in trace if s.phase == "recover")
    assert recover.repairs > 0, "no repairs — the deferral is untested"
    assert recover.years_in_service > UNREPAIRED_SERVICE_YEARS, (
        f"{recover.years_in_service} years at recovery does not beat the "
        f"no-repair baseline of {UNREPAIRED_SERVICE_YEARS}"
    )
    # The repair phases are where the count moves, and it never decreases.
    repairs = [s.repairs for s in trace]
    assert all(a <= b for a, b in zip(repairs, repairs[1:]))
    first_repair = next(s for s in trace if s.phase == "repair")
    assert first_repair.repairs > 0
    # Years accrue only while devices are in service — never after
    # recovery begins.
    recover_idx = trace.index(recover)
    for s in trace[recover_idx:]:
        assert s.years_in_service == recover.years_in_service


def test_the_loop_closes():
    """The final phase is reborn, its active regions include the materials
    region the trace started from, and the second pass starts richer:
    recycled_input_percent is strictly higher than step 0's. The output of
    one cycle is the input of the next — the entire thesis."""
    trace = simulate()
    final = trace[-1]
    assert final.phase == "reborn"
    assert "materials" in final.active_regions, (
        "the reborn step does not reach the materials region — the loop "
        "did not close"
    )
    assert final.recycled_input_percent > trace[0].recycled_input_percent, (
        f"second pass starts at {final.recycled_input_percent}% vs "
        f"{trace[0].recycled_input_percent}% — the loop closed without "
        f"enriching its own input"
    )


def test_recycled_input_is_never_zero():
    """The cohort does not start from virgin material: recycled cobalt,
    copper, steel, and plastics are inputs from step 0, not an aspiration
    for later passes."""
    for s in simulate():
        assert s.recycled_input_percent > 0, (
            f"step {s.step} ({s.phase}): zero recycled input"
        )
    assert simulate()[0].recycled_input_percent == FIRST_PASS_RECYCLED_PERCENT


def test_manufacture_is_the_longest_stage():
    """Unique max cycle_cost. Fabrication and assembly is where the
    lifetime footprint concentrates — and it is the step every repair
    avoids repeating, which is why repair matters more than recycling."""
    trace = simulate()
    manufacture = next(s for s in trace if s.phase == "manufacture")
    max_cost = max(s.cycle_cost for s in trace)
    assert manufacture.cycle_cost == max_cost
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1, (
        "manufacture must be the single longest stage"
    )


def test_the_split_totals_are_the_documented_constants():
    """The engine's constants are its own documentation; keep the trace
    honest against them."""
    final = simulate()[-1]
    assert final.reused_kg == REUSED_KG
    assert final.reclaimed_kg == RECLAIMED_KG
    assert final.lost_kg == LOST_KG


def test_active_regions_exist_in_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    for state in simulate():
        for rid in state.active_regions:
            assert rid in region_ids, f"step {state.step}: unknown region {rid!r}"


def test_every_step_lights_something():
    for s in simulate():
        assert s.active_regions, f"step {s.step} ({s.phase}) lights nothing"


def test_cycle_cost_at_least_one():
    assert all(s.cycle_cost >= 1 for s in simulate())


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
