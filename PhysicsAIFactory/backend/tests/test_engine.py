"""Full-trace invariants for the AI Factory roll-up engine — the three
identities (power balance, throughput coupling, checkpoint economics) as
pytest, in the house style of the Alienware energy identity and the
IR7000 heat balance."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.engine import REPAIR_H, simulate
from app.models import (
    DataBlock,
    ResilienceBlock,
    Scenario,
    SimEvent,
)
from app.presets import FACTORY, FRONTIER_LLM, GUIDED_SCENARIOS, MEGA, PILOT, STARVED

TOL_MW = 1e-3  # rounding tolerance on the 4-decimal MW readouts


def run(scenario: Scenario):
    return simulate(scenario)


def factory_scenario(**updates) -> Scenario:
    cfg = FACTORY.model_copy(update=updates) if updates else FACTORY
    return Scenario(config=cfg, job=FRONTIER_LLM, duration_h=480)


def test_determinism():
    s = factory_scenario()
    a, _, _ = run(s)
    b, _, _ = run(s)
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]


def test_power_balance_every_tick():
    """THE identity: subsystem draws sum to IT MW and facility = IT × PUE,
    on every tick of every preset."""
    for cfg in (PILOT, FACTORY, STARVED, MEGA):
        trace, _, _ = run(Scenario(config=cfg, job=FRONTIER_LLM, duration_h=300))
        for s in trace:
            parts = s.gpu_mw + s.fabric_mw + s.storage_mw + s.other_mw
            assert abs(parts - s.it_mw) <= TOL_MW, f"t={s.t_h}"
            assert abs(s.facility_mw - s.it_mw * s.pue) <= TOL_MW * 2, f"t={s.t_h}"


def test_facility_never_exceeds_budget():
    """The cap is a wall, not a suggestion: facility ≤ budget on every
    tick, including under the warm-day PUE excursion."""
    warm = next(g for g in GUIDED_SCENARIOS if g.id == "warm-day")
    for s_def in (factory_scenario(), warm.scenario):
        trace, _, _ = run(s_def)
        for s in trace:
            assert s.facility_mw <= s.mw_budget + TOL_MW, f"t={s.t_h}"


def test_starvation_emerges_from_the_arithmetic():
    """Halve storage below demand and the idle % rises to match the
    shortfall while tokens/s falls proportionally — the throughput
    coupling is emergent, not scripted."""
    demand = 576 * FRONTIER_LLM.data_gbps_per_gpu  # 864 GB/s
    fed = Scenario(
        config=FACTORY.model_copy(update={"data": DataBlock(storage_gbps=demand * 2)}),
        job=FRONTIER_LLM, duration_h=480,
    )
    starved = Scenario(
        config=FACTORY.model_copy(update={"data": DataBlock(storage_gbps=demand / 2)}),
        job=FRONTIER_LLM, duration_h=480,
    )
    a, _, _ = run(fed)
    b, _, _ = run(starved)
    probe = 430  # steady state, between the deterministic failure ticks
    assert a[probe].gpu_idle_data_pct <= 1.0
    assert abs(b[probe].gpu_idle_data_pct - 50.0) <= 3.0
    ratio = b[probe].tokens_per_s / a[probe].tokens_per_s
    assert abs(ratio - 0.5) <= 0.05, ratio


def test_checkpoint_goldilocks_interior_optimum():
    """Too-frequent checkpoints tax every hour; too-rare ones lose more
    to rollbacks. The middle interval must beat both ends in total
    tokens — the interior optimum, emergent from the trace."""
    totals = {}
    for interval in (5, 60, 480):
        cfg = FACTORY.model_copy(update={
            "resilience": ResilienceBlock(checkpoint_interval_min=interval),
        })
        _, _, summary = run(Scenario(config=cfg, job=FRONTIER_LLM, duration_h=600))
        totals[interval] = summary.tokens_total_b
    assert totals[60] > totals[5], totals
    assert totals[60] > totals[480], totals


def test_warm_day_sheds_load_and_logs_it():
    warm = next(g for g in GUIDED_SCENARIOS if g.id == "warm-day")
    trace, log, summary = run(warm.scenario)
    during = trace[300]
    after = trace[420]
    assert during.power_capped and not after.power_capped
    assert during.tokens_per_s < after.tokens_per_s
    assert abs(during.facility_mw - during.mw_budget) <= TOL_MW * 2, (
        "capped means sitting on the ceiling, not below it"
    )
    assert any("capped" in e.message for e in log)
    assert summary.power_capped_hours > 0


def test_time_to_first_token_is_the_install_arithmetic():
    """TTFT = procure + racks × install-rate + bring-up: more racks means
    a later first token (the Colossus arithmetic, inverted)."""
    _, _, s8 = run(factory_scenario())
    cfg16 = FACTORY.model_copy(deep=True)
    cfg16.compute.racks = 16
    _, _, s16 = run(Scenario(config=cfg16, job=FRONTIER_LLM, duration_h=480))
    assert s8.time_to_first_token_h == 72 + 16 + 24
    assert s16.time_to_first_token_h == 72 + 32 + 24
    assert s16.time_to_first_token_h > s8.time_to_first_token_h


def test_failures_arrive_on_the_mtbf_schedule_and_roll_back_tokens():
    trace, log, summary = run(factory_scenario())
    n = 576
    mtbf_cluster = FACTORY.resilience.gpu_mtbf_h / n  # ≈ 86.8 h
    train_hours = 480 - 112
    expected = int(train_hours / mtbf_cluster)
    assert summary.failures == expected, (summary.failures, expected)
    # The token counter genuinely rewinds at the 480-min-interval variant
    # (rollback visible above the 1 h tick granularity).
    cfg = FACTORY.model_copy(update={
        "resilience": ResilienceBlock(checkpoint_interval_min=480),
    })
    t2, _, _ = run(Scenario(config=cfg, job=FRONTIER_LLM, duration_h=480))
    dips = [
        (a.t_h, b.t_h) for a, b in zip(t2, t2[1:])
        if b.tokens_total_b < a.tokens_total_b
    ]
    assert dips, "a failure must visibly rewind the token counter"
    assert any("rolled back" in e.message for e in log)


def test_fail_gpus_event_takes_gpus_offline_then_repairs_them():
    s = factory_scenario()
    s = s.model_copy(update={
        "events": [SimEvent(at_h=300, action="fail-gpus", value=144)],
    })
    trace, log, _ = run(s)
    assert trace[299].gpus_online == 576
    assert trace[301].gpus_online == 576 - 144
    assert trace[300 + REPAIR_H].gpus_online == 576
    assert any("repaired" in e.message for e in log)


def test_storage_degrade_event_moves_the_idle_gauge():
    starved = next(g for g in GUIDED_SCENARIOS if g.id == "starved-cluster")
    trace, log, _ = run(starved.scenario)
    before = trace[240]
    after = trace[300]
    assert before.gpu_idle_data_pct <= 1.0
    assert after.gpu_idle_data_pct >= 60.0
    assert after.tokens_per_s < before.tokens_per_s * 0.5
    assert any("degraded" in e.message for e in log)


def test_cost_meter_runs_before_tokens_do():
    trace, _, _ = run(factory_scenario())
    assert trace[50].cost_usd_m > 0, "amortization runs from hour zero"
    assert trace[50].tokens_per_s == 0 and trace[50].usd_per_mtok == 0
    last = trace[-1]
    assert last.usd_per_mtok > 0
    assert last.cost_usd_m > trace[50].cost_usd_m


def test_phases_progress_in_order():
    trace, _, _ = run(factory_scenario())
    order = {"procure": 0, "install": 1, "bringup": 2, "train": 3}
    seq = [order[s.phase] for s in trace]
    assert seq == sorted(seq)
    assert seq[0] == 0 and seq[-1] == 3


def test_region_status_matches_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    trace, _, _ = run(Scenario(config=PILOT, job=FRONTIER_LLM, duration_h=200))
    for s in trace:
        assert set(s.region_status.keys()) == region_ids


def test_trace_length_and_monotonic_time():
    trace, _, _ = run(Scenario(config=PILOT, job=FRONTIER_LLM, duration_h=200))
    assert len(trace) == 201
    assert [s.t_h for s in trace] == sorted(s.t_h for s in trace)


def test_engine_is_pure():
    """The engine must not import FastAPI/IO/randomness — same rule as
    every twin."""
    import ast

    import app.engine as engine_module

    tree = ast.parse(open(engine_module.__file__, encoding="utf-8").read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & {
        "fastapi", "time", "asyncio", "threading", "os", "io", "random",
    }
