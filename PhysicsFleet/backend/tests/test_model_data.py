"""Integrity checks for the constants, validation rules, fleet maps,
and presets."""

from __future__ import annotations

from typing import get_args

from app.anatomy import MAPS
from app.constants import CONSTANTS
from app.engine import simulate
from app.models import FleetConfig, RegionKind, Scenario, Workload
from app.presets import (
    APEX_SPIKY,
    CONFIG_PRESETS,
    EXPLAINS,
    GUIDED_SCENARIOS,
    VXRAIL_3NODE,
    VXRAIL_MANUAL,
    WORKLOAD_PRESETS,
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


def test_the_automation_gap_is_an_order_of_magnitude_in_the_table():
    """The constants themselves must carry the lesson."""
    from app.constants import value as C

    assert C("deploy_site_manual_h") / C("deploy_site_zerotouch_h") >= 10
    assert C("patch_node_manual_h") / C("patch_node_auto_h") >= 5
    assert C("artisanal_deploy_h") / C("catalog_deploy_h") >= 20


# --- Validation rules ------------------------------------------------------

def _findings(cfg: FleetConfig, wl: Workload | None = None) -> dict[str, str]:
    s = Scenario(config=cfg, workload=wl or Workload())
    return {v.rule_id: v.level for v in validate(s)}


def test_three_node_trap_rule():
    assert _findings(VXRAIL_3NODE)["three-node"] == "warning"
    ok = VXRAIL_3NODE.model_copy(update={"nodes_per_site": 4})
    assert _findings(ok)["three-node"] == "ok"


def test_capacity_rules():
    cfg = FleetConfig(product="vxrail", nodes_per_site=4)
    over = Workload(vms_per_site=50, vm_size_capacity=10)
    assert _findings(cfg, over)["capacity"] == "error"
    tight = Workload(vms_per_site=35, vm_size_capacity=10)
    assert _findings(cfg, tight)["capacity"] == "warning"
    fine = Workload(vms_per_site=20, vm_size_capacity=10)
    assert _findings(cfg, fine)["capacity"] == "ok"


def test_manual_at_scale_warns():
    big = VXRAIL_MANUAL.model_copy(update={"sites": 20, "nodes_per_site": 16})
    assert _findings(big).get("ops-scale") == "warning"


def test_edge_single_node_warns():
    solo = FleetConfig(product="nativeedge", sites=100, nodes_per_site=1,
                       two_node_ha=False)
    assert _findings(solo).get("edge-ha") == "warning"


def test_apex_buffer_rules():
    airy = APEX_SPIKY.model_copy(update={"committed_vms": 2000})
    assert _findings(airy, Workload(vms_per_site=100))["buffer"] == "warning"
    tight = APEX_SPIKY.model_copy(update={"committed_vms": 50, "buffer_pct": 0})
    assert _findings(tight, Workload(vms_per_site=100))["buffer"] == "warning"


def test_every_rule_carries_a_source():
    for p in CONFIG_PRESETS:
        for v in validate(Scenario(config=p.config)):
            assert v.source.strip(), v.rule_id


# --- Fleet maps ------------------------------------------------------------

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


def test_five_products_share_one_geometry():
    """Deliberate: five management philosophies over the same estate —
    identical regions, different overviews."""
    assert set(MAPS) == {
        "vxrail", "privatecloud", "apex", "nativeedge", "automationstudio",
    }
    shapes = {
        tuple((r.id, r.x, r.y, r.w, r.h) for r in m.regions)
        for m in MAPS.values()
    }
    assert len(shapes) == 1, "the geometry must be shared"
    overviews = {m.overview for m in MAPS.values()}
    assert len(overviews) == 5, "the overviews must not be"


# --- Presets & scenarios ---------------------------------------------------

def test_preset_ids_unique_and_valid():
    ids = [p.id for p in CONFIG_PRESETS] + [w.id for w in WORKLOAD_PRESETS]
    assert len(ids) == len(set(ids))
    for p in CONFIG_PRESETS:
        assert p.blurb.strip(), p.id


def test_config_presets_pass_their_own_hard_rules():
    from app.presets import EDGE_WL

    for p in CONFIG_PRESETS:
        # Edge presets are sized for edge workloads, not datacenter ones.
        wl = EDGE_WL if p.config.product == "nativeedge" else Workload()
        errors = [
            v for v in validate(Scenario(config=p.config, workload=wl))
            if v.level == "error"
        ]
        assert not errors, f"{p.id}: {[e.rule_id for e in errors]}"


def test_guided_scenarios_are_complete_and_runnable():
    ids = [g.id for g in GUIDED_SCENARIOS]
    assert len(ids) == len(set(ids))
    assert len(GUIDED_SCENARIOS) >= 6
    products = {g.scenario.config.product for g in GUIDED_SCENARIOS}
    assert products == {
        "vxrail", "privatecloud", "apex", "nativeedge", "automationstudio",
    }
    for g in GUIDED_SCENARIOS:
        assert g.narration and all(p.strip() for p in g.narration), g.id
        assert g.question.strip().endswith("?"), g.id
        trace, _, _ = simulate(g.scenario)
        assert trace, g.id


def test_explain_entries_cover_the_required_readouts():
    ids = {e.id for e in EXPLAINS}
    assert {"admin-hours", "n-plus-one", "availability", "apex-econ"} <= ids
    for e in EXPLAINS:
        assert e.equation.strip() and e.explanation.strip(), e.id
        assert len(e.inputs) >= 3, f"{e.id}: causal chain too short"
