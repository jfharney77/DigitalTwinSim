"""Full-trace invariants for the data & observability engine — spec
06's mechanics as pytest: min(stages) and the moving bottleneck, the
freshness lag, GPU idle, KV offload, and the scored console."""

from __future__ import annotations

from app.anatomy import MAPS
from app.engine import simulate, stage_rates
from app.models import Scenario, SimEvent, Workload
from app.presets import (
    CONSOLE,
    CONSOLE_DEAF,
    CONSOLE_TOUCHY,
    DEFAULT_WL,
    HUNGRY_WL,
    PIPELINE_CPU,
    PIPELINE_GPU,
    PIPELINE_KV,
)
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

ISSUES = [
    SimEvent(at_h=48, action="inject-capacity"),
    SimEvent(at_h=120, action="inject-gray"),
    SimEvent(at_h=240, action="inject-fan-drift"),
]


def run(s: Scenario):
    return simulate(s)


# Scenario-driven: no step index or phase order to check, but the tick has to
# advance and the same scenario has to give the same trace. The conservation
# identities below are this app's own.
PROFILE = TraceProfile()


def test_trace_invariants():
    s = Scenario(config=CONSOLE, duration_h=200, events=ISSUES[:2])
    assert_trace_invariants(run(s)[0], PROFILE)
    assert_deterministic(lambda: run(s))


def test_throughput_is_min_of_stage_rates():
    trace, _, _ = run(Scenario(config=PIPELINE_CPU, workload=DEFAULT_WL, duration_h=48))
    rates = stage_rates(PIPELINE_CPU)
    slowest = min(rates.values())
    s = trace[-1]
    assert s.bottleneck == "process"
    assert s.throughput_tbh <= slowest + 0.01
    # Arrival (8) exceeds the constraint (6): throughput pins at min().
    assert abs(s.throughput_tbh - slowest) < 0.1


def test_fixing_the_bottleneck_moves_it():
    trace, log, _ = run(
        Scenario(
            config=PIPELINE_CPU, workload=DEFAULT_WL, duration_h=360,
            events=[SimEvent(at_h=120, action="toggle-gpu-process")],
        )
    )
    before = trace[100]
    after = trace[200]
    assert before.bottleneck == "process"
    assert after.bottleneck != "process", "the constraint must relocate"
    assert after.throughput_tbh >= before.throughput_tbh
    assert any("GPU processing ON" in e.message for e in log)


def test_backlog_and_freshness_grow_when_arrival_exceeds_the_constraint():
    wl = DEFAULT_WL.model_copy(update={"raw_arrival_tbh": 12})
    trace, _, summary = run(Scenario(config=PIPELINE_CPU, workload=wl, duration_h=360))
    mid = trace[150]
    end = trace[-1]
    assert end.stage_backlogs_tb["process"] > mid.stage_backlogs_tb["process"]
    assert end.freshness_lag_h > mid.freshness_lag_h
    assert summary.peak_freshness_lag_h > 24, "days-old data, no error message"


def test_gpu_idle_reflects_serving_shortfall():
    hungry = DEFAULT_WL.model_copy(update={"gpu_read_demand_tbh": 30})
    starved, _, _ = run(Scenario(config=PIPELINE_CPU, workload=hungry, duration_h=48))
    assert starved[-1].gpu_idle_due_to_data_pct > 20
    fed, _, _ = run(
        Scenario(config=PIPELINE_GPU,
                 workload=DEFAULT_WL.model_copy(update={"gpu_read_demand_tbh": 8}),
                 duration_h=48)
    )
    assert fed[-1].gpu_idle_due_to_data_pct < 5


def test_the_starvation_warning_and_the_idle_gauge_agree():
    """The validation rule and the gauge use one expression: a warning
    means the gauge opens above zero, and no warning means it opens at zero."""
    from app.presets import GUIDED_SCENARIOS
    from app.validation import validate

    for demand in (8, 10, 11, 12, 16, 30, 40):
        sc = Scenario(
            config=PIPELINE_CPU,
            workload=DEFAULT_WL.model_copy(update={"gpu_read_demand_tbh": demand}),
            duration_h=48,
        )
        warned = any(v.rule_id == "starvation" for v in validate(sc))
        first = run(sc)[0][1].gpu_idle_due_to_data_pct
        assert warned == (first > 0), (demand, warned, first)

    guided = next(g for g in GUIDED_SCENARIOS if g.id == "find-the-bottleneck")
    assert any(v.rule_id == "starvation" for v in validate(guided.scenario))
    trace = run(guided.scenario)[0]
    assert trace[1].gpu_idle_due_to_data_pct > 20, "the shortfall must be visible"


def test_the_limiter_names_what_sets_the_pace():
    """process binds, then index while the backlog drains, then the
    sources: once nothing is full the limiter is 'arrival', even though
    the slowest stage is still index."""
    from app.presets import GUIDED_SCENARIOS

    guided = next(g for g in GUIDED_SCENARIOS if g.id == "find-the-bottleneck")
    trace = run(guided.scenario)[0]
    assert trace[60].limiter == "process" and trace[60].throughput_tbh == 6
    assert trace[130].limiter == "index" and trace[130].throughput_tbh == 15
    end = trace[-1]
    assert end.bottleneck == "index" and end.limiter == "arrival"
    assert end.throughput_tbh == guided.scenario.workload.raw_arrival_tbh
    assert sum(end.stage_backlogs_tb.values()) == 0
    assert 0 < end.gpu_idle_due_to_data_pct < trace[60].gpu_idle_due_to_data_pct


def test_kv_offload_quadruples_sessions_for_a_token_tax():
    trace, log, _ = run(
        Scenario(
            config=PIPELINE_GPU, workload=HUNGRY_WL, duration_h=240,
            events=[SimEvent(at_h=120, action="toggle-kv")],
        )
    )
    before = trace[100]
    after = trace[200]
    assert before.sessions_capacity == 40
    assert after.sessions_capacity == 160
    assert after.sessions_active > before.sessions_active * 2
    assert before.token_latency_tax_pct == 0
    assert after.token_latency_tax_pct > 5, "the tax must be visible"
    assert any("KV-cache offload ON" in e.message for e in log)


def test_gpu_analytics_toggle():
    slow, _, _ = run(Scenario(config=PIPELINE_CPU, workload=DEFAULT_WL, duration_h=24))
    cfg = PIPELINE_CPU.model_copy(update={"gpu_analytics": True})
    fast, _, _ = run(Scenario(config=cfg, workload=DEFAULT_WL, duration_h=24))
    assert fast[-1].analytics_scan_rate_tbh > slow[-1].analytics_scan_rate_tbh * 4


def test_detector_is_scored_and_k_trades_the_scores():
    _, _, balanced = run(Scenario(config=CONSOLE, duration_h=480, events=ISSUES))
    _, _, touchy = run(Scenario(config=CONSOLE_TOUCHY, duration_h=480, events=ISSUES))
    _, _, deaf = run(Scenario(config=CONSOLE_DEAF, duration_h=480, events=ISSUES))
    # Touchier: found things sooner, at worse precision.
    assert touchy.mttd_h < balanced.mttd_h
    assert touchy.precision_pct < balanced.precision_pct
    # Deafer: cleaner feed, slower/less finding.
    assert deaf.precision_pct >= balanced.precision_pct
    assert deaf.mttd_h > balanced.mttd_h or deaf.recall_pct < balanced.recall_pct


def test_recall_reaches_all_planted_issues_at_reasonable_k():
    _, _, summary = run(Scenario(config=CONSOLE, duration_h=720, events=ISSUES))
    assert summary.recall_pct == 100.0, "k=3 must eventually find all three plants"
    assert summary.precision_pct < 100.0, "and pay something in false alarms"


def test_green_but_sick():
    """The gray failure's payoff: status stays green for the whole run
    while the anomaly feed flags the trend — both halves asserted."""
    trace, log, _ = run(
        Scenario(config=CONSOLE, duration_h=360,
                 events=[SimEvent(at_h=72, action="inject-gray")])
    )
    assert all(s.device_status_all_green for s in trace)
    assert trace[-1].issues_detected >= 1, "the trend must catch it"
    assert any("gray" in e.message for e in log)


def test_forecast_converges_then_lags_on_demand_change():
    trace, _, _ = run(
        Scenario(
            config=CONSOLE, duration_h=720,
            events=[SimEvent(at_h=200, action="demand-change")],
        )
    )
    settled = next(s for s in trace if s.t_h == 190)
    assert settled.forecast_error_days < 10, "a steady slope converges"
    just_after = next(s for s in trace if s.t_h == 240)
    assert just_after.forecast_error_days > settled.forecast_error_days + 10, (
        "a slope change makes the windowed fit confidently wrong"
    )
    later = trace[-1]
    assert later.forecast_error_days < just_after.forecast_error_days / 2, (
        "and the window relearns"
    )


def test_acting_on_the_forecast_averts_the_outage():
    acted = Scenario(
        config=CONSOLE, duration_h=720,
        events=[
            SimEvent(at_h=48, action="inject-capacity"),
            SimEvent(at_h=240, action="expand-capacity"),
        ],
    )
    ignored = Scenario(
        config=CONSOLE, duration_h=720,
        events=[SimEvent(at_h=48, action="inject-capacity")],
    )
    _, _, a = run(acted)
    _, _, i = run(ignored)
    assert not a.capacity_outage
    assert i.capacity_outage, "inaction fills the array"


def test_health_score_weights_are_opinions():
    ev = [SimEvent(at_h=48, action="inject-capacity")]
    cap_weighted = CONSOLE.model_copy(update={
        "weight_capacity": 90, "weight_performance": 5, "weight_config": 5,
    })
    perf_weighted = CONSOLE.model_copy(update={
        "weight_capacity": 5, "weight_performance": 90, "weight_config": 5,
    })
    a, _, _ = run(Scenario(config=cap_weighted, duration_h=480, events=ev))
    b, _, _ = run(Scenario(config=perf_weighted, duration_h=480, events=ev))
    assert a[-1].health_score_worst < b[-1].health_score_worst, (
        "re-weighting the same facts changes the score — scores are opinions"
    )


def test_region_load_matches_map():
    region_ids = {r.id for r in MAPS["aidataplatform"].regions}
    trace, _, _ = run(Scenario(config=PIPELINE_CPU, workload=DEFAULT_WL, duration_h=48))
    for s in trace:
        assert set(s.region_load.keys()) == region_ids


def test_engine_is_pure():
    import app.engine as engine_module

    assert_engine_is_pure(engine_module)
