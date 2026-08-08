"""Integrity checks for the constants, validation rules, maps, and
presets."""

from __future__ import annotations

from typing import get_args

from app.anatomy import MAPS
from app.constants import CONSTANTS
from app.engine import simulate
from app.models import DataConfig, RegionKind, Scenario, Workload
from app.presets import (
    CONFIG_PRESETS,
    CONSOLE_TOUCHY,
    EXPLAINS,
    GUIDED_SCENARIOS,
    PIPELINE_CPU,
)
from app.validation import validate

EXPECTED_KINDS = set(get_args(RegionKind))


def test_every_constant_has_units_source_and_blurb():
    for name, c in CONSTANTS.items():
        assert c.unit.strip(), name
        assert c.source.strip(), name
        assert c.blurb.strip(), name
        if "estimate" in c.source.lower():
            assert c.estimated, f"{name}: estimate in source but not flagged"
        if c.estimated:
            assert "estimate" in c.source.lower(), (
                f"{name}: flagged estimated but source doesn't say so"
            )


def test_vendor_claims_are_labeled_verify():
    """The 6×-class GPU claims must carry the verify discipline."""
    for name in ("gpu_process_speedup", "gpu_analytics_speedup"):
        assert "verify" in CONSTANTS[name].source.lower(), name


# --- Validation rules ------------------------------------------------------

def _findings(cfg: DataConfig, wl: Workload | None = None) -> dict[str, str]:
    s = Scenario(config=cfg, workload=wl or Workload())
    return {v.rule_id: v.level for v in validate(s)}


def test_bottleneck_is_always_named():
    assert _findings(PIPELINE_CPU)["bottleneck"] == "ok"


def test_arrival_beyond_constraint_warns():
    wl = Workload(raw_arrival_tbh=12)
    assert _findings(PIPELINE_CPU, wl)["arrival"] == "warning"
    assert "arrival" not in _findings(PIPELINE_CPU, Workload(raw_arrival_tbh=4))


def test_starvation_warning():
    wl = Workload(gpu_read_demand_tbh=50)
    assert _findings(PIPELINE_CPU, wl)["starvation"] == "warning"


def test_kv_capacity_warning():
    wl = Workload(inference_sessions_demand=300, long_context_pct=60)
    assert _findings(PIPELINE_CPU, wl)["kv"] == "warning"
    offload = PIPELINE_CPU.model_copy(update={"kv_offload": True})
    wl_ok = Workload(inference_sessions_demand=100, long_context_pct=60)
    assert "kv" not in _findings(offload, wl_ok)


def test_detector_extremes_warn():
    assert _findings(CONSOLE_TOUCHY)["detector"] == "warning"
    deaf = CONSOLE_TOUCHY.model_copy(update={"anomaly_k": 6.0})
    assert _findings(deaf)["detector"] == "warning"


def test_every_rule_carries_a_source():
    for p in CONFIG_PRESETS:
        for v in validate(Scenario(config=p.config)):
            assert v.source.strip(), v.rule_id


# --- Maps -------------------------------------------------------------------

def test_region_ids_unique_and_in_bounds():
    for m in MAPS.values():
        ids = [r.id for r in m.regions]
        assert len(ids) == len(set(ids)), m.id
        for r in m.regions:
            assert 0 <= r.x and r.x + r.w <= m.width, (m.id, r.id)
            assert 0 <= r.y and r.y + r.h <= m.height, (m.id, r.id)
            assert r.w > 0 and r.h > 0, (m.id, r.id)
            assert r.description.strip(), (m.id, r.id)


def test_regions_do_not_overlap():
    for m in MAPS.values():
        rs = m.regions
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                disjoint = (
                    a.x + a.w <= b.x or b.x + b.w <= a.x
                    or a.y + a.h <= b.y or b.y + b.h <= a.y
                )
                assert disjoint, f"{m.id}: {a.id} overlaps {b.id}"


def test_kinds_union_is_expected_set():
    kinds = {r.kind for m in MAPS.values() for r in m.regions}
    assert kinds == EXPECTED_KINDS


def test_the_journey_reads_left_to_right_and_the_console_underlines_it():
    """Geometry carries the lesson: the four stages ascend in x toward
    the GPUs, and the console band spans the bottom watching all of it."""
    m = MAPS["aidataplatform"]
    by_id = {r.id: r for r in m.regions}
    xs = [by_id[s].x for s in ("sources", "ingest", "process", "index", "serve", "gpus")]
    assert xs == sorted(xs), "the dataset's journey must read left to right"
    console = by_id["console"]
    assert console.w >= 90, "the console watches everything"
    assert console.y > max(r.y for r in m.regions if r.id != "console") - 1


# --- Presets & scenarios ---------------------------------------------------

def test_preset_ids_unique_and_valid():
    ids = [p.id for p in CONFIG_PRESETS]
    assert len(ids) == len(set(ids))
    for p in CONFIG_PRESETS:
        assert p.blurb.strip(), p.id


def test_guided_scenarios_are_complete_and_runnable():
    ids = [g.id for g in GUIDED_SCENARIOS]
    assert len(ids) == len(set(ids))
    assert len(GUIDED_SCENARIOS) >= 6
    products = {g.scenario.config.product for g in GUIDED_SCENARIOS}
    assert products == {"aidataplatform", "cloudiq"}
    for g in GUIDED_SCENARIOS:
        assert g.narration and all(p.strip() for p in g.narration), g.id
        assert g.question.strip().endswith("?"), g.id
        trace, _, _ = simulate(g.scenario)
        assert trace, g.id


def test_explain_entries_cover_the_required_readouts():
    """Spec 06 names its required equations: pipeline min(), Little's
    law, and the KV session math."""
    ids = {e.id for e in EXPLAINS}
    assert {"min-stages", "littles-law", "kv-sessions", "scored-detection",
            "forecast-lag"} <= ids
    for e in EXPLAINS:
        assert e.equation.strip() and e.explanation.strip(), e.id
        assert len(e.inputs) >= 3, f"{e.id}: causal chain too short"
