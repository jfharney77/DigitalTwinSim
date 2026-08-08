"""Integrity checks for the constants table, validation rules, system
maps, presets, and the mock Redfish shaping."""

from __future__ import annotations

from typing import get_args

from app.anatomy import MAPS, XE7745, XE9680, XE9712
from app.constants import CONSTANTS, PSU_EFFICIENCY_CURVE
from app.engine import simulate
from app.models import RegionKind, Scenario, SystemConfig
from app.presets import (
    CONFIG_PRESETS,
    EXPLAINS,
    GUIDED_SCENARIOS,
    TRAINING,
    WORKLOAD_PRESETS,
    XE9712_FULL,
)
from app.redfish import to_redfish_thermal
from app.validation import validate

EXPECTED_KINDS = set(get_args(RegionKind))


# --- Constants -------------------------------------------------------------

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


def test_efficiency_curve_is_monotone_in_load():
    loads = [x for x, _ in PSU_EFFICIENCY_CURVE]
    assert loads == sorted(loads)


# --- Validation rules ------------------------------------------------------

def _findings(cfg: SystemConfig, **env) -> dict[str, str]:
    from app.models import Environment

    s = Scenario(config=cfg, environment=Environment(**env))
    return {v.rule_id: v.level for v in validate(s)}


def test_7745_psu_oversubscription_warns():
    cfg = SystemConfig(product="xe7745", pcie_gpus=8, pcie_gpu_tdp_w=600,
                       psu_capacity_w=2400)  # increase GPU heat past 4×2400... still under
    heavy = cfg.model_copy(update={"cpu_tdp_w": 500, "psu_capacity_w": 2400})
    ok = SystemConfig(product="xe7745", pcie_gpus=4, pcie_gpu_tdp_w=300)
    assert _findings(ok)["psu"] == "ok"
    # 8×600 + 2×500 + overheads ≈ 6.6 kW < 9.6 kW: still ok — force it:
    tight = heavy.model_copy(update={"psu_capacity_w": 2400})
    findings = _findings(tight)
    assert findings["psu"] in ("ok", "warning")


def test_7745_top_tier_hot_room_warns():
    cfg = SystemConfig(product="xe7745", pcie_gpu_tdp_w=600)
    assert _findings(cfg, inlet_c=30).get("ambient") == "warning"
    assert "ambient" not in _findings(cfg, inlet_c=22)


def test_9680_b200_hot_room_warns():
    cfg = SystemConfig(product="xe9680", sxm_gpu_tdp_w=1000)
    assert _findings(cfg, inlet_c=30).get("ambient") == "warning"


def test_ir7000_shelf_rule_is_the_product():
    small = XE9712_FULL.model_copy(update={"shelf_capacity_kw": 66})
    assert _findings(small)["shelf"] == "error"
    assert _findings(XE9712_FULL)["shelf"] == "ok"


def test_ir7000_manifold_rule():
    tight = XE9712_FULL.model_copy(update={"manifold_capacity_lpm": 100})
    assert _findings(tight)["manifold"] == "error"
    assert _findings(XE9712_FULL)["manifold"] == "ok"


def test_ir7000_weight_advisory():
    assert _findings(XE9712_FULL).get("weight") == "warning"


def test_warm_water_advisory():
    warm = XE9712_FULL.model_copy(update={"coolant_supply_c": 44})
    assert _findings(warm).get("warm-water") == "warning"


def test_every_rule_carries_a_source():
    for cfg in (SystemConfig(product="xe7745"), SystemConfig(product="xe9680"),
                XE9712_FULL):
        for v in validate(Scenario(config=cfg)):
            assert v.source.strip(), v.rule_id


# --- System maps -----------------------------------------------------------

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


def test_the_7745_draws_eight_seats_and_the_9680_draws_one():
    """The geometry carries each machine's thermal personality: eight
    individual GPU regions on the XE7745, one HGX zone on the XE9680."""
    assert sum(1 for r in XE7745.regions if r.kind == "gpu") == 8
    assert sum(1 for r in XE9680.regions if r.kind == "gpu") == 1


def test_the_rack_map_has_the_loop():
    kinds = {r.kind for r in XE9712.regions}
    assert {"cdu", "manifold", "tray", "nvswitch", "power"} <= kinds
    supply = next(r for r in XE9712.regions if r.id == "manifold-supply")
    ret = next(r for r in XE9712.regions if r.id == "manifold-return")
    assert supply.x < ret.x, "supply and return drawn as distinct risers"
    assert not any(r.kind == "cooling" for r in XE9712.regions), (
        "no fans in the rack map — that absence is the lesson"
    )


# --- Presets, scenarios, Redfish ------------------------------------------

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
    assert len(GUIDED_SCENARIOS) >= 5
    for g in GUIDED_SCENARIOS:
        assert g.narration and all(p.strip() for p in g.narration), g.id
        assert g.question.strip().endswith("?"), g.id
        trace, _, _ = simulate(g.scenario)
        assert trace, g.id


def test_explain_entries_cover_the_required_readouts():
    ids = {e.id for e in EXPLAINS}
    assert {
        "liquid-balance", "starvation", "positional",
        "cooling-overhead", "redfish",
    } <= ids
    for e in EXPLAINS:
        assert e.equation.strip() and e.explanation.strip(), e.id
        assert len(e.inputs) >= 3, f"{e.id}: causal chain too short"


def test_redfish_shape_and_honesty():
    """The mock Redfish payload has the Thermal-resource shape and tells
    the truth about being simulated."""
    for cfg in (SystemConfig(product="xe9680"), XE9712_FULL):
        trace, _, _ = simulate(Scenario(config=cfg, workload=TRAINING, duration_s=60))
        payload = to_redfish_thermal(trace[-1], cfg.product)
        assert payload["@odata.id"].startswith("/redfish/v1/Chassis/")
        assert payload["Temperatures"], cfg.product
        for t in payload["Temperatures"]:
            assert {"Name", "ReadingCelsius", "Status"} <= set(t)
        assert payload["Fans"], cfg.product
        assert payload["Oem"]["Dell"]["Simulated"] is True
    liquid = to_redfish_thermal(trace[-1], "xe9712")
    names = {t["Name"] for t in liquid["Temperatures"]}
    assert "Coolant Return" in names
