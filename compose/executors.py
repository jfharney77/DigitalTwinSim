"""Run a chain on live engines. One executor per kind of chain.

Every executor is a pure function of the chain: engines are called in-process
through ``runner.run_engine``; nothing here opens a socket, reads a clock or
rolls a die.
"""

from __future__ import annotations

import copy
from typing import Any, Callable

from . import constants as K
from .chain import Chain, Link
from .couplings import c1_compute_heat_to_cdu as c1
from .couplings import c2_cdu_caps_to_compute as c2
from .couplings import c3_storage_to_compute_feed as c3
from .couplings import c4_fabric_gray_to_factory as c4
from .couplings import c5_wall_watts_to_rackpower as c5
from .couplings import c6_resilience_to_datadomain as c6
from .couplings import c7_xr_site_to_fleet as c7
from .couplings import c8_factory_fed as c8
from .loader import load_engine
from .loop import cdu_constants, fixed_point
from .models import Chart, ChartSeries, CoupledTrace, JoinedTick, Stage
from .reader import dump, get, series, slim_trace
from .resample import integral
from .runner import EngineRun, run_engine, stage_of
from .seam import compare


def _timeline(n: int, columns: dict[str, list[float]], t0: int = 0) -> list[JoinedTick]:
    out = []
    for i in range(n):
        out.append(JoinedTick(t=t0 + i, values={
            k: (round(float(v[i]), 4) if i < len(v) and v[i] is not None else None)
            for k, v in columns.items()
        }))
    return out


def _s(key: str, label: str, role: str) -> ChartSeries:
    return ChartSeries(key=key, label=label, role=role)


def _estimated(*handles_and_names: tuple[str, str]) -> list[str]:
    out = []
    for component, name in handles_and_names:
        const = load_engine(component).constant(name)
        if const.estimated:
            out.append(f"{component}.{name}")
    return out


def _link(chain: Chain, coupling: str) -> Link:
    for link in chain.links:
        if link.coupling == coupling:
            return link
    raise KeyError(f"chain {chain.id!r} has no {coupling} link")


# --- C1, open --------------------------------------------------------------------

def run_c1(chain: Chain) -> CoupledTrace:
    link = _link(chain, "c1")
    racks = int(link.params.get("racks", 1))
    compute = run_engine("PhysicsCompute", chain.scenarios.get("PhysicsCompute"))
    notes = []
    if compute.scenario.config.product != "xe9712":
        notes.append("C1 reads liquid heat; only the XE9712 personality has a liquid loop.")
    consts = cdu_constants(load_engine("PhysicsCDU"))
    scn, injected, cfg, adapt_notes = c1.adapt(
        compute.trace, chain.scenarios.get("PhysicsCDU"), cdu=consts, racks=racks)
    cdu = run_engine("PhysicsCDU", scn)
    seams = c1.check(compute.trace, cdu.trace, cdu=consts, racks=racks)
    air_kwh = racks * c1.air_share_kwh(compute.trace)
    dc_kwh = racks * integral(series(compute.trace, "dc_power_w")) / 3.6e6
    liq_kwh = racks * integral(series(compute.trace, "liquid_watts")) / 3.6e6
    seams.append(compare(
        "c1", "Compute.liquid + Compute.air == Compute.dc (nothing is lost; the air share goes to the room)",
        liq_kwh + air_kwh, dc_kwh, "kWh", 0.001 * max(dc_kwh, 1e-9) + 0.01,
        note=f"{air_kwh:.2f} kWh of air-side heat never crosses this seam — the CDU only sees liquid",
    ))
    n = min(len(compute.trace), len(cdu.trace))
    timeline = _timeline(n, {
        "PhysicsCompute.liquid_kw": c1.liquid_kw(compute.trace, racks),
        "PhysicsCDU.it_load_kw": series(cdu.trace, "it_load_kw"),
        "PhysicsCompute.air_kw": [racks * w / 1000.0 for w in series(compute.trace, "air_watts")],
        "PhysicsCompute.tokens_per_s": series(compute.trace, "tokens_per_s"),
        "PhysicsCDU.sec_supply_c": series(cdu.trace, "sec_supply_c"),
        "PhysicsCDU.sec_return_c": series(cdu.trace, "sec_return_c"),
        "PhysicsCDU.fac_return_c": series(cdu.trace, "fac_return_c"),
        "PhysicsCDU.cap_pct": series(cdu.trace, "cap_pct"),
    })
    charts = [
        Chart(title="Heat across the seam", unit="kW", seam=True, series=[
            _s("PhysicsCompute.liquid_kw", "XE9712 liquid heat (source)", "source"),
            _s("PhysicsCDU.it_load_kw", "CDU IT load (target)", "target"),
            _s("PhysicsCompute.air_kw", "air share (stays in the room)", "context")]),
        Chart(title="What the CDU does with it", unit="°C", series=[
            _s("PhysicsCDU.sec_supply_c", "rack supply", "target"),
            _s("PhysicsCDU.sec_return_c", "rack return", "target"),
            _s("PhysicsCDU.fac_return_c", "facility return", "context")]),
        Chart(title="Tokens", unit="tokens/s", series=[
            _s("PhysicsCompute.tokens_per_s", "XE9712 tokens/s", "source")]),
    ]
    return CoupledTrace(
        chain_id=chain.id, title=chain.title, time_unit="s",
        stages=[stage_of(compute, "PhysicsCompute", "XE9712 rack" + (f" ×{racks}" if racks > 1 else "")),
                stage_of(cdu, "PhysicsCDU", "PowerCool CDU", injected, cfg)],
        seams=seams, timeline=timeline, charts=charts, notes=notes + adapt_notes,
        estimated_constants=_estimated(("PhysicsCDU", "group_kw"), ("PhysicsCDU", "group_idle_fraction"),
                                       ("PhysicsCompute", "residual_air_fraction")),
    )


# --- C1 + C2, closed -------------------------------------------------------------

def run_loop(chain: Chain) -> CoupledTrace:
    racks = int(_link(chain, "c1").params.get("racks", 1))
    r = fixed_point(chain.scenarios.get("PhysicsCompute") or {}, chain.scenarios.get("PhysicsCDU") or {},
                    max_iter=chain.max_iter, damping=chain.damping, tol=chain.tol, racks=racks)
    consts = cdu_constants(load_engine("PhysicsCDU"))
    groups = int(r.open_cdu.scenario.config.tray_groups)
    seams = c1.check(r.compute.trace, r.cdu.trace, cdu=consts, racks=racks, groups=groups,
                     extra_note="closed loop: ticks the CDU still caps are excluded")
    seams += c2.check(r.compute.trace, r.cdu.trace, r.open_compute.trace, r.supply_residual_c)
    last = r.residuals[-1] if r.residuals else 0.0
    seams.append(compare(
        "c2", "fixed point: the loop stopped moving (residual < tolerance)",
        last, 0.0, "relative", chain.tol, holds=r.converged,
        note=f"{r.iterations} iteration(s), damping {chain.damping:g}, cap {chain.max_iter}",
    ))
    n = min(len(r.compute.trace), len(r.cdu.trace))
    timeline = _timeline(n, {
        "PhysicsCompute.liquid_kw": c1.liquid_kw(r.compute.trace, racks),
        "PhysicsCDU.it_load_kw": series(r.cdu.trace, "it_load_kw"),
        "open.liquid_kw": c1.liquid_kw(r.open_compute.trace, racks),
        "PhysicsCDU.sec_supply_c": series(r.cdu.trace, "sec_supply_c"),
        "PhysicsCompute.coolant_supply_c": series(r.compute.trace, "coolant_supply_c"),
        "PhysicsCDU.chip_temp_c": series(r.cdu.trace, "chip_temp_c"),
        "PhysicsCDU.cap_pct": series(r.cdu.trace, "cap_pct"),
        "open.cap_pct": series(r.open_cdu.trace, "cap_pct"),
        "PhysicsCompute.tokens_per_s": series(r.compute.trace, "tokens_per_s"),
        "open.tokens_per_s": series(r.open_compute.trace, "tokens_per_s"),
    })
    charts = [
        Chart(title="Heat across the seam", unit="kW", seam=True, series=[
            _s("PhysicsCompute.liquid_kw", "XE9712 liquid heat, coupled (source)", "source"),
            _s("PhysicsCDU.it_load_kw", "CDU IT load (target)", "target"),
            _s("open.liquid_kw", "XE9712 liquid heat, open loop", "context")]),
        Chart(title="Supply temperature coming back", unit="°C", seam=True, series=[
            _s("PhysicsCDU.sec_supply_c", "CDU rack supply (source)", "source"),
            _s("PhysicsCompute.coolant_supply_c", "XE9712 coolant supply (target)", "target"),
            _s("PhysicsCDU.chip_temp_c", "CDU's silicon estimate", "context")]),
        Chart(title="IRC cap the CDU still asks for", unit="%", series=[
            _s("open.cap_pct", "open loop", "context"),
            _s("PhysicsCDU.cap_pct", "at the fixed point", "target")]),
        Chart(title="Tokens", unit="tokens/s", series=[
            _s("open.tokens_per_s", "open loop", "context"),
            _s("PhysicsCompute.tokens_per_s", "coupled", "target")]),
    ]
    label = "XE9712 rack" + (f" ×{racks}" if racks > 1 else "")
    return CoupledTrace(
        chain_id=chain.id, title=chain.title, time_unit="s",
        stages=[
            stage_of(r.open_compute, "PhysicsCompute/open", label + ", open loop"),
            stage_of(r.compute, "PhysicsCompute", label + ", coupled", r.compute_injected),
            stage_of(r.cdu, "PhysicsCDU", "PowerCool CDU", r.cdu_injected, r.cdu_config),
        ],
        seams=seams, iterations=r.iterations, converged=r.converged,
        residual_history=r.residuals, iteration_log=r.records,
        timeline=timeline, charts=charts,
        notes=r.notes + [
            "Engines exchange whole runs, not ticks: the loop is a fixed point over traces. "
            "It cannot honestly show transients faster than the CDU's 60 s loop lag.",
            "PhysicsCompute has no power-cap event; the IRC cap is applied as demanded gpu_pct × cap.",
        ],
        estimated_constants=_estimated(("PhysicsCDU", "group_kw"), ("PhysicsCDU", "group_idle_fraction"),
                                       ("PhysicsCDU", "tau_loop_s"), ("PhysicsCDU", "chip_target_c"),
                                       ("PhysicsCompute", "residual_air_fraction")),
    )


# --- C3 ----------------------------------------------------------------------------

def run_c3(chain: Chain) -> CoupledTrace:
    link = _link(chain, "c3")
    storage = run_engine("PhysicsStorage", chain.scenarios.get("PhysicsStorage"))
    base = chain.scenarios.get("PhysicsCompute") or {}
    scn, injected, points, notes = c3.adapt(storage.trace, base, dict(link.params))
    compute = run_engine("PhysicsCompute", scn)
    from .loader import load_engine as _le
    gpus = _le("PhysicsCompute").engine.gpu_count(compute.scenario.config)
    gpu_pct = float(compute.scenario.workload.gpu_pct)
    c3.measure(compute.trace, points, gpu_pct, gpus)
    seams = c3.check(points)
    healthy = max(points, key=lambda p: p["feedPct"])
    starved = min(points, key=lambda p: p["feedPct"])
    if starved["feedPct"] < healthy["feedPct"] and healthy["tokensPerS"] > 0:
        tok = starved["tokensPerS"] / healthy["tokensPerS"]
        pwr = starved["dcW"] / healthy["dcW"]
        seams.append(compare(
            "c3", "starved GPUs still burn power: DC power falls by less than tokens fall",
            pwr, tok, "ratio", 0.0, holds=pwr > tok,
            note=f"at feed {starved['feedPct']}%: tokens ×{tok:.2f}, DC power ×{pwr:.2f} "
                 "(PhysicsCompute stall_power_fraction)",
        ))
    by_feed = {p["feedPct"]: p for p in points}
    fed_store = c3.feed_series(storage.trace)
    fed_compute = [by_feed.get(int(round(f)), {}).get("computeFedPct") for f in fed_store]
    wasted_rate = [
        (100.0 - (c if c is not None else 100.0)) / 100.0 * gpus * gpu_pct / 100.0
        for c in fed_compute
    ]
    timeline = _timeline(len(storage.trace), {
        "PhysicsStorage.fed_pct": fed_store,
        "PhysicsCompute.fed_pct": fed_compute,
        "PhysicsStorage.iops_demand_k": series(storage.trace, "iops_demand_k"),
        "PhysicsStorage.iops_delivered_k": series(storage.trace, "iops_delivered_k"),
        "PhysicsCompute.gpus_idle": wasted_rate,
    })
    charts = [
        Chart(title="How fed the GPUs are", unit="%", seam=True, series=[
            _s("PhysicsStorage.fed_pct", "Storage: 100 − GPU idle due to data (source)", "source"),
            _s("PhysicsCompute.fed_pct", "Compute: effective ÷ demanded GPU utilization (target)", "target")]),
        Chart(title="Storage demand and delivery", unit="k IOPS", series=[
            _s("PhysicsStorage.iops_demand_k", "demanded", "context"),
            _s("PhysicsStorage.iops_delivered_k", "delivered", "source")]),
        Chart(title="GPUs waiting on data", unit="GPUs", series=[
            _s("PhysicsCompute.gpus_idle", "GPU-hours wasted per hour", "target")]),
    ]
    return CoupledTrace(
        chain_id=chain.id, title=chain.title, time_unit="h",
        stages=[stage_of(storage, "PhysicsStorage", "Exascale rack"),
                stage_of(compute, "PhysicsCompute", "GPU system, one window per operating point",
                         injected, {"operatingPoints": points})],
        seams=seams, timeline=timeline, charts=charts,
        notes=notes + [
            f"{len(storage.trace)} storage hours reduce to {len(points)} distinct operating "
            "point(s); the compute run visits each once.",
            "PhysicsStorage's exascale pool view reads the configured node count, so a node loss "
            "does not move its GPU-idle gauge; demand surges and checkpoint bursts do.",
        ],
        estimated_constants=_estimated(("PhysicsCompute", "stall_power_fraction"),
                                       ("PhysicsStorage", "checkpoint_period_h")),
    )


# --- C4 ----------------------------------------------------------------------------

def _factory_regime_runs(base: dict, regimes: list[dict]) -> tuple[list[EngineRun], list[list[dict]]]:
    runs, dumps, cache = [], [], {}
    for r in regimes:
        key = r["tokensScale"]
        if key not in cache:
            run = run_engine("PhysicsAIFactory", c4.adapt(base, key))
            cache[key] = (run, slim_trace(run.trace))
        runs.append(cache[key][0])
        dumps.append(cache[key][1])
    return runs, dumps


def run_c4(chain: Chain) -> CoupledTrace:
    fabric = run_engine("PhysicsFabric", chain.scenarios.get("PhysicsFabric"))
    base = chain.scenarios.get("PhysicsAIFactory") or {}
    rs = c4.plan(fabric.trace)
    healthy = run_engine("PhysicsAIFactory", base)
    healthy_rows = slim_trace(healthy.trace)
    c4.boundaries(rs, healthy_rows)
    runs, dumps = _factory_regime_runs(base, rs)
    spliced = c4.splice(dumps, rs)
    seams = c4.check(fabric.trace, healthy_rows, spliced, rs)
    # Cumulative counters survive the joins: only the factory's own rewinds go down.
    drops = [h for h in range(1, len(spliced))
             if spliced[h]["tokensTotalB"] < spliced[h - 1]["tokensTotalB"] - 1e-9
             and spliced[h]["failuresCum"] == spliced[h - 1]["failuresCum"]]
    seams.append(compare(
        "c4", "spliced tokens_total is monotone except at the factory's own failure rewinds",
        float(len(drops)), 0.0, "hours", 0.0,
        note="cumulative tokens and cost are restamped at each regime boundary"))
    scale_by_hour = [1.0] * len(spliced)
    green_by_hour = [1.0] * len(spliced)
    for r in rs:
        for h in range(r["startH"], r["endH"]):
            scale_by_hour[h] = r["tokensScale"]
            green_by_hour[h] = 1.0 if r["allGreen"] else 0.0
    ratio = [
        (spliced[h]["tokensPerS"] / healthy_rows[h]["tokensPerS"])
        if healthy_rows[h]["tokensPerS"] > 0 else None for h in range(len(spliced))
    ]
    timeline = _timeline(len(spliced), {
        "PhysicsFabric.tokens_scale": scale_by_hour,
        "PhysicsAIFactory.tokens_ratio": ratio,
        "PhysicsFabric.status_all_green": green_by_hour,
        "PhysicsAIFactory.tokens_per_s": [row["tokensPerS"] for row in spliced],
        "healthy.tokens_per_s": [row["tokensPerS"] for row in healthy_rows],
        "PhysicsAIFactory.tokens_total_b": [row["tokensTotalB"] for row in spliced],
        "healthy.tokens_total_b": [row["tokensTotalB"] for row in healthy_rows],
    })
    charts = [
        Chart(title="Step-time scale across the seam", unit="ratio", seam=True, series=[
            _s("PhysicsFabric.tokens_scale", "Fabric: 1 ÷ step stretch (source)", "source"),
            _s("PhysicsAIFactory.tokens_ratio", "Factory: tokens/s ÷ healthy tokens/s (target)", "target"),
            _s("PhysicsFabric.status_all_green", "Fabric status all green (1 = yes)", "context")]),
        Chart(title="Factory tokens per second", unit="tokens/s", series=[
            _s("healthy.tokens_per_s", "healthy fabric", "context"),
            _s("PhysicsAIFactory.tokens_per_s", "with the gray link", "target")]),
        Chart(title="Tokens produced", unit="B tokens", series=[
            _s("healthy.tokens_total_b", "healthy fabric", "context"),
            _s("PhysicsAIFactory.tokens_total_b", "with the gray link", "target")]),
    ]
    spliced_stage = Stage(
        id="PhysicsAIFactory", component="PhysicsAIFactory", label="AI factory, spliced per fabric regime",
        time_unit="h", scenario=dump(healthy.scenario),
        injected_events=[], injected_config={"regimes": rs},
        trace=spliced, summary={"tokensTotalB": spliced[-1]["tokensTotalB"],
                                "healthyTokensTotalB": healthy_rows[-1]["tokensTotalB"],
                                "usdPerMtok": spliced[-1]["usdPerMtok"]},
        validations=[v for v in dump(healthy.validations) if v.get("level") != "ok"],
    )
    return CoupledTrace(
        chain_id=chain.id, title=chain.title, time_unit="h",
        stages=[stage_of(fabric, "PhysicsFabric", "Scale-out fabric"), spliced_stage],
        seams=seams, timeline=timeline, charts=charts,
        notes=["PhysicsAIFactory has no mid-run fabric event: the factory runs once per fabric "
               "regime and the traces are spliced at the boundaries.",
               "The fabric run stands for the factory's training span, start to end."],
        estimated_constants=K.estimated_names("comm_fraction")
        + _estimated(("PhysicsFabric", "gray_goodput_penalty")),
    )


# --- C5 ----------------------------------------------------------------------------

def run_c5(chain: Chain) -> CoupledTrace:
    link = _link(chain, "c5")
    specs = list(link.params.get("servers") or [])
    if not specs:
        specs = [{"label": "R760", "component": "DellPowerEdgeR760Thermal"}]
    runs: list[tuple[str, EngineRun]] = []
    for i, spec in enumerate(specs):
        component = spec.get("component", "DellPowerEdgeR760Thermal")
        scenario = spec.get("scenario") or chain.scenarios.get(component) or {}
        if component == "PhysicsCompute" and (scenario.get("config", {}) or {}).get("product") == "xe9712":
            raise c5.OversizedServer("The XE9712 is busbar-fed; PhysicsRackPower models PDU outlets.")
        runs.append((spec.get("label", f"Server {i + 1}"), run_engine(component, scenario)))
    sources = [(label, run.trace) for label, run in runs]
    scn, injected, cfg, notes = c5.adapt(sources, chain.scenarios.get("PhysicsRackPower"),
                                         dict(link.params))
    rack = run_engine("PhysicsRackPower", scn)
    seams = c5.check(sources, rack.trace, cfg["slotsUsed"], cfg["deadbandW"])
    wall = c5.total_wall_w(sources)
    n = min(len(wall), len(rack.trace))
    cols = {
        "servers.ac_power_w": wall,
        "PhysicsRackPower.pdu_input_w": series(rack.trace, "pdu_input_w"),
        "PhysicsRackPower.phase_a_amps": series(rack.trace, "phase_a_amps"),
        "PhysicsRackPower.phase_b_amps": series(rack.trace, "phase_b_amps"),
        "PhysicsRackPower.phase_c_amps": series(rack.trace, "phase_c_amps"),
        "PhysicsRackPower.ac_input_w": series(rack.trace, "ac_input_w"),
    }
    first = runs[0][1]
    if hasattr(first.trace[0], "fan_power_w"):
        cols["servers.fan_power_w"] = [
            sum(float(get(run.trace[i], "fan_power_w", 0.0)) for _, run in runs) for i in range(n)]
    charts = [
        Chart(title="Wall watts across the seam", unit="W", seam=True, series=[
            _s("servers.ac_power_w", "Σ servers' AC draw (source)", "source"),
            _s("PhysicsRackPower.pdu_input_w", "PDU input (target)", "target"),
            _s("PhysicsRackPower.ac_input_w", "UPS draw from the utility", "context")]),
        Chart(title="Phase current at the breakers", unit="A", series=[
            _s("PhysicsRackPower.phase_a_amps", "phase A", "target"),
            _s("PhysicsRackPower.phase_b_amps", "phase B", "target"),
            _s("PhysicsRackPower.phase_c_amps", "phase C", "target")]),
    ]
    if "servers.fan_power_w" in cols:
        charts.append(Chart(title="Fan power upstream", unit="W", series=[
            _s("servers.fan_power_w", "Σ servers' fan power", "source")]))
    stages = [stage_of(run, f"{run.component}/{i}", label) for i, (label, run) in enumerate(runs)]
    stages.append(stage_of(rack, "PhysicsRackPower", "Rack PDU and UPS", injected, cfg))
    est = []
    for component in sorted({run.component for _, run in runs}):
        est.append(f"{component}.PSU_EFFICIENCY_CURVE")
    return CoupledTrace(
        chain_id=chain.id, title=chain.title, time_unit="s", stages=stages, seams=seams,
        timeline=_timeline(n, cols), charts=charts,
        notes=notes + ["A server above 2000 W is split one slot per PSU feed, or refused. "
                       "The busbar-fed XE9712 is out of scope for this seam."],
        estimated_constants=est,
    )


# --- C6 ----------------------------------------------------------------------------

def run_c6(chain: Chain) -> CoupledTrace:
    base_res = chain.scenarios.get("PhysicsResilience") or {}
    pass1 = run_engine("PhysicsResilience", base_res)
    res_scn = dump(pass1.scenario)
    dd_scn, dd_injected, dd_cfg, notes = c6.adapt(res_scn, pass1.trace,
                                                  chain.scenarios.get("PhysicsDataDomain"))
    dd = run_engine("PhysicsDataDomain", dd_scn)
    res_handle = load_engine("PhysicsResilience")
    scn2, info, notes2 = c6.detection_from_alarm(
        res_scn, dd.summary, dd_injected, res_handle.C("detect_threshold_base_h"))
    pass2 = run_engine("PhysicsResilience", scn2)
    full_tb = float(dd.scenario.dataset.full_tb)
    seams = [
        c6.check_encrypted(res_scn, pass1.trace, dd.trace, dd_injected, full_tb),
        c6.check_rto(scn2, pass2.summary, res_handle.C("decision_hours")),
        compare("c6", "pass-2 blast radius <= pass-1 blast radius (earlier detection can only shrink it)",
                float(pass2.summary.blast_radius_gb), float(pass1.summary.blast_radius_gb), "GB", 0.0,
                holds=float(pass2.summary.blast_radius_gb) <= float(pass1.summary.blast_radius_gb) + 1e-9,
                note=f"entropy alarm on day {info['alarmDay']}; detection latency "
                     f"{info.get('modelLatencyH')} h in pass 2"),
    ]
    days = len(dd.trace)
    def daily(trace: list, field: str) -> list[float]:
        vals = series(trace, field)
        return [vals[min(d * 24, len(vals) - 1)] for d in range(days)]
    timeline = _timeline(days, {
        "PhysicsResilience.corrupted_tb": daily(pass1.trace, "corrupted_tb"),
        "PhysicsDataDomain.encrypted_tb": [
            float(s.encrypted_fraction_pct) / 100.0 * full_tb for s in dd.trace],
        "pass2.corrupted_tb": daily(pass2.trace, "corrupted_tb"),
        "PhysicsDataDomain.stream_entropy_pct": series(dd.trace, "stream_entropy_pct"),
        "PhysicsDataDomain.physical_tb": series(dd.trace, "physical_tb"),
        "PhysicsDataDomain.capacity_trend_tb": series(dd.trace, "capacity_trend_tb"),
    })
    charts = [
        Chart(title="Encrypted data, read from both sides", unit="TB", seam=True, series=[
            _s("PhysicsResilience.corrupted_tb", "Resilience: corrupted (source)", "source"),
            _s("PhysicsDataDomain.encrypted_tb", "Data Domain: encrypted share × full (target)", "target"),
            _s("pass2.corrupted_tb", "Resilience pass 2, alarm-timed detection", "context")]),
        Chart(title="The smoke alarm", unit="% entropy", series=[
            _s("PhysicsDataDomain.stream_entropy_pct", "entropy of today's changed data", "target")]),
        Chart(title="The capacity curve, weeks later", unit="TB", series=[
            _s("PhysicsDataDomain.physical_tb", "physical stored", "target"),
            _s("PhysicsDataDomain.capacity_trend_tb", "pre-incident trend", "context")]),
    ]
    return CoupledTrace(
        chain_id=chain.id, title=chain.title, time_unit="d",
        stages=[stage_of(pass1, "PhysicsResilience/pass1", "Attack timeline, pass 1"),
                stage_of(dd, "PhysicsDataDomain", "Backup appliance", dd_injected, dd_cfg),
                stage_of(pass2, "PhysicsResilience", "Attack timeline, pass 2 (detection from the alarm)",
                         [], {"detection": info})],
        seams=seams, timeline=timeline, charts=charts,
        notes=notes + notes2 + [
            "Defensive architecture only: the seam carries a rate, a size and a timestamp. "
            "Nothing about technique exists on either side of it.",
            "PhysicsResilience has no detection-latency input; the adapter picks the sensitivity "
            "whose modeled latency is closest to the alarm's without beating it.",
        ],
        estimated_constants=_estimated(("PhysicsResilience", "detect_threshold_base_h"),
                                       ("PhysicsResilience", "decision_hours"),
                                       ("PhysicsDataDomain", "entropy_alarm_delta")),
    )


# --- C7 ----------------------------------------------------------------------------

def run_c7(chain: Chain) -> CoupledTrace:
    link = _link(chain, "c7")
    params = dict(link.params)
    mix = list(params.get("site_mix") or [])
    threshold = float(params.get("throttle_fault_fraction", c7.THROTTLE_FAULT_FRACTION))
    outcomes, stages = [], []
    for site in mix:
        run = run_engine("PhysicsXR", site.get("scenario") or {})
        o = c7.site_outcome(run.summary, int(run.scenario.duration_s), threshold)
        o.update({"id": site["id"], "label": site.get("label", site["id"]), "sites": int(site["sites"])})
        outcomes.append(o)
        stages.append(stage_of(run, f"PhysicsXR/{site['id']}", f"{o['label']} × {o['sites']} sites"))
    base = copy.deepcopy(chain.scenarios.get("PhysicsFleet") or {})
    base.setdefault("config", {})["product"] = "nativeedge"
    base["config"]["sites"] = max(1, min(1000, sum(o["sites"] for o in outcomes)))
    baseline = run_engine("PhysicsFleet", base)
    scn, injected, cfg, notes = c7.adapt(outcomes, base, params)
    fleet = run_engine("PhysicsFleet", scn)
    fh = load_engine("PhysicsFleet")
    consts = {k: fh.C(k) for k in ("remediate_auto_h", "remediate_manual_h", "truck_roll_h")}
    per_fault = c7.per_fault_hours(scn, consts)
    n = cfg["faultsInjected"]
    seams = c7.check(baseline.trace, fleet.trace, n, per_fault)
    days = len(fleet.trace)
    cum, k = [], 0
    sched = sorted(e["atD"] for e in injected)
    for d in range(days):
        while k < len(sched) and sched[k] <= d:
            k += 1
        cum.append(float(k))
    timeline = _timeline(days, {
        "PhysicsXR.faults_injected": cum,
        "PhysicsFleet.extra_faults": [
            float(fleet.trace[d].faults_cum - baseline.trace[d].faults_cum) for d in range(days)],
        "PhysicsXR.expected_admin_hours": [c * per_fault for c in cum],
        "PhysicsFleet.extra_admin_hours": [
            fleet.trace[d].admin_hours_cum - baseline.trace[d].admin_hours_cum for d in range(days)],
        "PhysicsFleet.truck_rolls": [float(s.truck_rolls) for s in fleet.trace],
        "baseline.admin_hours_cum": series(baseline.trace, "admin_hours_cum"),
        "PhysicsFleet.admin_hours_cum": series(fleet.trace, "admin_hours_cum"),
    })
    charts = [
        Chart(title="Faults across the seam", unit="faults", seam=True, series=[
            _s("PhysicsXR.faults_injected", "scheduled from the hostile sites (source)", "source"),
            _s("PhysicsFleet.extra_faults", "Fleet faults above its own baseline (target)", "target")]),
        Chart(title="What they cost", unit="admin-hours", seam=True, series=[
            _s("PhysicsXR.expected_admin_hours", "faults × per-fault hours (source)", "source"),
            _s("PhysicsFleet.extra_admin_hours", "Fleet admin hours above baseline (target)", "target")]),
        Chart(title="The whole ledger", unit="admin-hours", series=[
            _s("baseline.admin_hours_cum", "fleet in benign sites", "context"),
            _s("PhysicsFleet.admin_hours_cum", "fleet with the hostile sites", "target")]),
    ]
    stages.append(stage_of(baseline, "PhysicsFleet/baseline", "NativeEdge fleet, benign sites"))
    stages.append(stage_of(fleet, "PhysicsFleet", "NativeEdge fleet, with the hostile sites",
                           injected, {**cfg, "siteOutcomes": outcomes, "perFaultHours": per_fault}))
    return CoupledTrace(
        chain_id=chain.id, title=chain.title, time_unit="d", stages=stages, seams=seams,
        timeline=timeline, charts=charts,
        notes=notes + [
            "One PhysicsXR run stands for a hostile day at that class of site. A day that ends in a "
            "shutdown, or is mostly spent throttled, raises one service fault each time it recurs.",
            "Faults are scheduled by division, not dice, and land in the first 90% of the run so "
            "the admin backlog can drain before the ledger is read.",
        ],
        estimated_constants=K.estimated_names("heatwave_days_per_year")
        + _estimated(("PhysicsFleet", "remediate_auto_h"), ("PhysicsFleet", "truck_roll_h")),
    )


# --- C8 ----------------------------------------------------------------------------

def run_c8(chain: Chain) -> CoupledTrace:
    link = _link(chain, "c8")
    params = dict(link.params)
    factory_base = copy.deepcopy(chain.scenarios.get("PhysicsAIFactory") or {})
    aggregate = run_engine("PhysicsAIFactory", factory_base)
    agg_rows = slim_trace(aggregate.trace)
    fb = dump(aggregate.scenario)
    gpus_total = aggregate.scenario.config.compute.racks * aggregate.scenario.config.compute.gpus_per_rack
    demand_gbps = gpus_total * aggregate.scenario.job.data_gbps_per_gpu
    hours = int(aggregate.scenario.duration_h)

    # Storage -> storage_gbps and degrade-storage events.
    sh = load_engine("PhysicsStorage")
    per_k = sh.C("gbps_per_iopsk_8k")
    st_scn = c8.storage_workload_for(fb, chain.scenarios.get("PhysicsStorage") or {}, per_k)
    st_scn["durationH"] = min(2160, max(6, hours))
    storage = run_engine("PhysicsStorage", st_scn)
    block_kb = int(storage.scenario.workload.block_kb)
    supply, st_events, bursts = c8.storage_inputs(
        storage.trace, per_k, block_kb, int(params.get("storage_racks", 1)), demand_gbps)

    # Compute <-> CDU closed loop -> gpu_peak_w, PUE, and the warm-water cap.
    racks_per_cdu = int(params.get("racks_per_cdu", 2))
    compute_base = chain.scenarios.get("PhysicsCompute") or {}
    cdu_base = chain.scenarios.get("PhysicsCDU") or {}
    design = fixed_point(compute_base, cdu_base, chain.max_iter, chain.damping, chain.tol, racks_per_cdu)
    peak_w = c8.gpu_peak_w(design.open_compute.trace, c8_gpus(design.open_compute))
    pue = c8.derived_pue(design.cdu.trace)
    warm = params.get("warm_water")
    cap_scale, warm_loop = 1.0, None
    if warm:
        warm_cdu = copy.deepcopy(cdu_base)
        warm_cdu.setdefault("events", []).append(
            {"atS": int(warm.get("atS", 120)), "action": "set-facility-supply",
             "value": float(warm["facilitySupplyC"])})
        warm_loop = fixed_point(compute_base, warm_cdu, chain.max_iter, chain.damping,
                                chain.tol, racks_per_cdu)
        from .resample import steady_window
        free = steady_window(design.compute.trace, "tokens_per_s")
        held = steady_window(warm_loop.compute.trace, "tokens_per_s")
        cap_scale = round(held / free, 6) if free else 1.0

    # Fabric -> tokens_scale per regime.
    fabric = run_engine("PhysicsFabric", chain.scenarios.get("PhysicsFabric"))
    rs = c4.plan(fabric.trace)
    c4.boundaries(rs, agg_rows)
    fabric_scale = min(r["tokensScale"] for r in rs)

    # The fed factory scenario.
    fed_base = copy.deepcopy(fb)
    fed_base["config"]["compute"]["gpuPeakW"] = peak_w
    fed_base["config"]["data"]["storageGbps"] = supply
    fh = load_engine("PhysicsAIFactory")
    base_pue = fh.C("pue_liquid") if aggregate.scenario.config.facility.cooling == "liquid" \
        else fh.C("pue_air")
    injected = list(st_events)
    if abs(pue - base_pue) > 0.0005:
        injected.append({"atH": 0, "action": "warm-day", "value": round(pue - base_pue, 3)})
    fed_base["events"] = sorted(list(fed_base.get("events") or []) + injected, key=lambda e: e["atH"])

    # Regimes: fabric regimes, further cut by the warm-water window.
    segments = []
    for r in rs:
        segments.append({"startH": r["startH"], "endH": r["endH"], "tokensScale": r["tokensScale"],
                         "gray": r["gray"], "warm": False})
    if warm and cap_scale < 1.0:
        a, b = int(warm.get("fromH", 0)), int(warm.get("toH", hours + 1))
        cut = []
        for seg in segments:
            for lo, hi, is_warm in ((seg["startH"], min(seg["endH"], a), False),
                                    (max(seg["startH"], a), min(seg["endH"], b), True),
                                    (max(seg["startH"], b), seg["endH"], False)):
                if hi > lo:
                    cut.append({**seg, "startH": lo, "endH": hi, "warm": is_warm,
                                "tokensScale": round(seg["tokensScale"] * (cap_scale if is_warm else 1.0), 6)})
        segments = cut
    runs, dumps = _factory_regime_runs(fed_base, segments)
    fed_rows = c4.splice(dumps, segments)

    # What was true during the hours the steady-state comparison reads.
    train = [h for h, row in enumerate(agg_rows) if row["phase"] == "train"]
    window = train[int(0.8 * len(train)):] or train
    def _mean_over_window(key: str, default: float) -> float:
        vals = []
        for h in window:
            seg = next((sg for sg in segments if sg["startH"] <= h < sg["endH"]), None)
            vals.append(seg[key] if seg else default)
        return sum(vals) / max(len(vals), 1)
    for seg in segments:
        seg["fabricScale"] = next(r["tokensScale"] for r in rs
                                  if r["startH"] <= seg["startH"] < r["endH"])
        seg["capScale"] = cap_scale if seg["warm"] else 1.0
    cap_scale_w = round(_mean_over_window("capScale", 1.0), 6)
    fabric_scale = round(_mean_over_window("fabricScale", 1.0), 6)
    bursts = [h for h in bursts if h in set(window)]
    facts = {"fedGpuPeakW": peak_w,
             "aggregateGpuPeakW": int(aggregate.scenario.config.compute.gpu_peak_w),
             "capScale": cap_scale_w, "fabricScale": fabric_scale, "burstHours": bursts,
             "fedPue": pue, "fedStorageGbps": supply}
    divergences = c8.compare_modes(agg_rows, fed_rows, facts)

    seams = []
    for instrument, (tol, kind) in c8.TOLERANCES.items():
        a = c8.steady(agg_rows, c8.INSTRUMENT_KEYS[instrument])
        f = c8.steady(fed_rows, c8.INSTRUMENT_KEYS[instrument])
        named = next((d for d in divergences if d.instrument == instrument), None)
        abs_tol = tol * abs(a) if kind == "relative" else tol
        seams.append(compare(
            "c8", f"steady-state {instrument}: fed == aggregate, or the gap is named",
            f, a, {"tokens_per_s": "tokens/s", "facility_mw": "MW",
                   "gpu_idle_data_pct": "points", "pue": "PUE"}[instrument], abs_tol,
            holds=(named is None) or (named.cause is not None),
            note=("within tolerance" if named is None else
                  (f"outside tolerance — named: {named.cause}. {named.explanation}"
                   if named.cause else "outside tolerance and UNEXPLAINED")),
            lhs_key=f"fed.{instrument}", rhs_key=f"aggregate.{instrument}",
        ))
    cols = {}
    for instrument, key in c8.INSTRUMENT_KEYS.items():
        cols[f"aggregate.{instrument}"] = [row[key] for row in agg_rows]
        cols[f"fed.{instrument}"] = [row[key] for row in fed_rows]
    units = {"tokens_per_s": "tokens/s", "facility_mw": "MW", "gpu_idle_data_pct": "%", "pue": "PUE"}
    titles = {"tokens_per_s": "Tokens per second", "facility_mw": "Facility power",
              "gpu_idle_data_pct": "GPUs idle because data was late", "pue": "PUE"}
    charts = [Chart(title=titles[i], unit=units[i], seam=True, series=[
        _s(f"aggregate.{i}", "aggregate (one number per block)", "source"),
        _s(f"fed.{i}", "fed by engines", "target")]) for i in c8.INSTRUMENT_KEYS]

    fed_stage = Stage(
        id="PhysicsAIFactory", component="PhysicsAIFactory", label="AI factory, fed by engines",
        time_unit="h", scenario=fed_base, injected_events=injected,
        injected_config={"gpuPeakW": peak_w, "storageGbps": supply, "pue": pue,
                         "segments": segments, "facts": {k: v for k, v in facts.items() if k != "burstHours"},
                         "burstHours": len(bursts)},
        trace=fed_rows,
        summary={"tokensTotalB": fed_rows[-1]["tokensTotalB"],
                 "aggregateTokensTotalB": agg_rows[-1]["tokensTotalB"],
                 "usdPerMtok": fed_rows[-1]["usdPerMtok"]},
        validations=[v for v in dump(runs[0].validations) if v.get("level") != "ok"],
    )
    # Upstream traces are summarized, not shipped: the factory's hours are the page's time base.
    def brief(run: EngineRun, sid: str, label: str, injected_events: list[dict] | None = None) -> Stage:
        st = stage_of(run, sid, label, injected_events)
        st.trace = st.trace[:: max(1, len(st.trace) // 120)]
        st.log = st.log[:40]
        return st
    stages = [
        stage_of(aggregate, "PhysicsAIFactory/aggregate", "AI factory, aggregate mode"),
        brief(storage, "PhysicsStorage", "Exascale rack, demand sized from the factory"),
        brief(fabric, "PhysicsFabric", "Scale-out fabric"),
        brief(design.compute, "PhysicsCompute", f"XE9712 rack ×{racks_per_cdu} per CDU, coupled",
              design.compute_injected),
        brief(design.cdu, "PhysicsCDU", "PowerCool CDU, design day", design.cdu_injected),
    ]
    if warm_loop is not None:
        stages.append(brief(warm_loop.cdu, "PhysicsCDU/warm", "PowerCool CDU, warm water",
                            warm_loop.cdu_injected))
    stages.append(fed_stage)
    return CoupledTrace(
        chain_id=chain.id, title=chain.title, time_unit="h", stages=stages, seams=seams,
        iterations=design.iterations if warm_loop is None else warm_loop.iterations,
        converged=design.converged and (warm_loop is None or warm_loop.converged),
        residual_history=(warm_loop or design).residuals,
        iteration_log=(warm_loop or design).records,
        timeline=_timeline(len(fed_rows), cols), charts=charts, divergences=divergences,
        notes=[
            "The factory engine is unchanged; only its inputs differ between the two modes.",
            "The storage run's demand is sized from the factory's GPUs, so both idle gauges "
            "answer the same question.",
            "PhysicsAIFactory already charges starved GPUs stall power (its stall_power_fraction), "
            "so the two modes agree on MW under starvation; the design expected them not to.",
            "PUE has no direct input: the derived value is injected as a warm-day offset at hour 0 "
            "(negative when the detailed loop is cheaper than the class constant).",
        ],
        estimated_constants=K.estimated_names("comm_fraction", "facility_overhead_pue")
        + _estimated(("PhysicsCompute", "tray_gpu_w"), ("PhysicsAIFactory", "pue_liquid"),
                     ("PhysicsStorage", "iops_per_node_lightning_k")),
    )


def c8_gpus(run: EngineRun) -> int:
    return load_engine("PhysicsCompute").engine.gpu_count(run.scenario.config)


# --- dispatch ----------------------------------------------------------------------

def execute(chain: Chain) -> CoupledTrace:
    kinds = {link.coupling for link in chain.links}
    table: list[tuple[set[str], Callable[[Chain], CoupledTrace]]] = [
        ({"c8"}, run_c8), ({"c1", "c2"}, run_loop), ({"c1"}, run_c1), ({"c3"}, run_c3),
        ({"c4"}, run_c4), ({"c5"}, run_c5), ({"c6"}, run_c6), ({"c7"}, run_c7),
    ]
    for need, fn in table:
        if need <= kinds and (need == kinds or "c8" in need):
            if need == {"c1", "c2"} and not chain.closed:
                raise ValueError("a chain with both C1 and C2 is a loop; set closed=True")
            return fn(chain)
    raise ValueError(f"no executor for the couplings {sorted(kinds)}")
