"""Integrity checks for the constants, validation rules, fabric maps,
and presets."""

from __future__ import annotations

from typing import get_args

from app.anatomy import MAPS
from app.constants import CONSTANTS
from app.engine import simulate
from app.models import FabricConfig, RegionKind, Scenario, Workload
from app.presets import (
    CAMPUS,
    CONFIG_PRESETS,
    EXPLAINS,
    GUIDED_SCENARIOS,
    SN6000_STATIC,
    WORKLOAD_PRESETS,
    X800_FABRIC,
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


# --- Validation rules ------------------------------------------------------

def _findings(cfg: FabricConfig, wl: Workload | None = None) -> dict[str, str]:
    s = Scenario(config=cfg, workload=wl or Workload())
    return {v.rule_id: v.level for v in validate(s)}


def test_oversubscription_is_stated_up_front():
    heavy = SN6000_STATIC.model_copy(update={
        "spines": 1, "endpoints_per_leaf": 32, "downlink_gbps": 400,
        "uplink_gbps": 800,
    })
    assert _findings(heavy)["oversub"] == "warning"
    non_blocking = SN6000_STATIC.model_copy(update={
        "spines": 8, "endpoints_per_leaf": 16, "downlink_gbps": 400,
    })
    assert _findings(non_blocking)["oversub"] == "ok"


def test_bisection_warning():
    wl = Workload(demand_gbps=200000)
    assert _findings(SN6000_STATIC, wl)["bisection"] == "warning"


def test_poe_budget_error_and_warning():
    over = CAMPUS.model_copy(update={"poe_aps": 60, "poe_cameras": 40})
    assert _findings(over)["poe"] == "error"
    assert _findings(CAMPUS)["poe"] == "warning"  # the preset runs near 90%
    light = CAMPUS.model_copy(update={"poe_aps": 5, "poe_cameras": 5,
                                      "poe_phones": 5})
    assert _findings(light)["poe"] == "ok"


def test_feature_product_sanity():
    wrong = CAMPUS.model_copy(update={"adaptive_routing": True})
    assert _findings(wrong).get("features") == "error"
    sharp_on_ethernet = SN6000_STATIC.model_copy(update={"sharp": True})
    assert _findings(sharp_on_ethernet).get("sharp") == "error"
    assert "sharp" not in _findings(X800_FABRIC)


def test_elephants_without_adaptive_warns():
    wl = Workload(pattern="elephant", demand_gbps=10000)
    assert _findings(SN6000_STATIC, wl).get("elephants") == "warning"


def test_every_rule_carries_a_source():
    for p in CONFIG_PRESETS:
        for v in validate(Scenario(config=p.config)):
            assert v.source.strip(), v.rule_id


# --- Fabric maps -----------------------------------------------------------

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


def test_geometry_carries_the_arguments():
    """The worst link gets its own strip on both datacenter fabrics
    (averages hide the lesson); the subnet manager is drawn small and
    beside the X800 fabric; the E3200 has the PoE strip."""
    for fid in ("sn6000", "x800"):
        assert any(r.id == "worst-link" for r in MAPS[fid].regions), fid
    sm = next(r for r in MAPS["x800"].regions if r.id == "manager")
    spines = next(r for r in MAPS["x800"].regions if r.id == "spines")
    assert sm.w * sm.h < spines.w * spines.h * 0.5, (
        "the subnet manager must be drawn small — essential to the "
        "fabric's life, absent from every packet's"
    )
    assert any(r.id == "poe" for r in MAPS["e3200"].regions)
    assert not any(r.kind == "spine" for r in MAPS["e3200"].regions), (
        "the campus is a tree, not a leaf/spine"
    )


# --- Presets & scenarios ---------------------------------------------------

def test_preset_ids_unique_and_valid():
    ids = [p.id for p in CONFIG_PRESETS] + [w.id for w in WORKLOAD_PRESETS]
    assert len(ids) == len(set(ids))
    for p in CONFIG_PRESETS:
        assert p.blurb.strip(), p.id


def test_config_presets_pass_their_own_hard_rules():
    for p in CONFIG_PRESETS:
        errors = [
            v for v in validate(Scenario(config=p.config)) if v.level == "error"
        ]
        assert not errors, f"{p.id}: {[e.rule_id for e in errors]}"


def test_guided_scenarios_are_complete_and_runnable():
    ids = [g.id for g in GUIDED_SCENARIOS]
    assert len(ids) == len(set(ids))
    assert len(GUIDED_SCENARIOS) >= 6
    products = {g.scenario.config.product for g in GUIDED_SCENARIOS}
    assert products == {"e3200", "sn6000", "x800"}
    for g in GUIDED_SCENARIOS:
        assert g.narration and all(p.strip() for p in g.narration), g.id
        assert g.question.strip().endswith("?"), g.id
        trace, _, _ = simulate(g.scenario)
        assert trace, g.id


def test_explain_entries_cover_the_required_readouts():
    ids = {e.id for e in EXPLAINS}
    assert {"oversub", "queue-delay", "ecmp", "lossless", "optics-power"} <= ids
    for e in EXPLAINS:
        assert e.equation.strip() and e.explanation.strip(), e.id
        assert len(e.inputs) >= 3, f"{e.id}: causal chain too short"
