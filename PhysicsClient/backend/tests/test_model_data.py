"""Integrity checks for the constants table, validation rules, device
maps, and presets — the app's data contract."""

from __future__ import annotations

from typing import get_args

from app.anatomy import ALIENWARE_DESKTOP, ALIENWARE_LAPTOP, MAPS, PROMAX
from app.constants import CONSTANTS, PSU_EFFICIENCY_CURVE
from app.models import DeviceConfig, Environment, RegionKind, Scenario
from app.presets import (
    AW_DESKTOP,
    AW_LAPTOP_MAX,
    CONFIG_PRESETS,
    EXPLAINS,
    GUIDED_SCENARIOS,
    PROMAX_NPU,
    WORKLOAD_PRESETS,
)
from app.validation import validate

EXPECTED_KINDS = set(get_args(RegionKind))


# --- Constants -------------------------------------------------------------

def test_every_constant_has_units_source_and_blurb():
    """The suite's honesty rule: every constant carries a source, and
    estimates say so — both directions."""
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
    assert all(0.75 <= e <= 1.0 for _, e in PSU_EFFICIENCY_CURVE)


# --- Validation rules ------------------------------------------------------

def _findings(cfg: DeviceConfig, **env) -> dict[str, str]:
    s = Scenario(config=cfg, environment=Environment(**env))
    return {v.rule_id: v.level for v in validate(s)}


def test_npu_on_alienware_is_an_error():
    cfg = DeviceConfig(product="alienware", npu=True)
    assert _findings(cfg)["npu"] == "error"
    assert _findings(PROMAX_NPU)["npu"] == "ok"


def test_promax_desktop_is_an_error():
    cfg = DeviceConfig(product="promax", form_factor="desktop")
    assert _findings(cfg)["form-factor"] == "error"


def test_undersized_charger_warns_but_does_not_block():
    cfg = AW_LAPTOP_MAX.model_copy(update={"charger_w": 130})
    assert _findings(cfg)["charger"] == "warning"
    assert _findings(AW_LAPTOP_MAX)["charger"] == "ok"


def test_over_budget_build_warns():
    assert _findings(AW_LAPTOP_MAX)["budget"] == "warning"
    modest = DeviceConfig(cpu_pl1_w=45, gpu_tgp_w=80)
    assert _findings(modest)["budget"] == "ok"


def test_desktop_psu_oversubscription_warns():
    cfg = AW_DESKTOP.model_copy(update={"psu_capacity_w": 750, "gpu_tgp_w": 450})
    assert _findings(cfg)["psu"] == "warning"
    assert _findings(AW_DESKTOP)["psu"] == "ok"


def test_worn_battery_and_on_lap_advisories():
    worn = DeviceConfig(battery_health_pct=80)
    assert _findings(worn).get("battery-health") == "warning"
    assert _findings(
        DeviceConfig(), on_lap=True, perf_mode="performance"
    ).get("on-lap") == "warning"


def test_every_rule_carries_a_source():
    for v in validate(Scenario()):
        assert v.source.strip(), v.rule_id


# --- Device maps -----------------------------------------------------------

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


def test_the_laptops_have_a_skin_and_a_battery_and_the_tower_does_not_battery():
    """The geometry carries the client lesson: both laptop maps carry
    skin + battery zones; the tower has no battery, and its 'skin' is a
    side panel nobody touches (present for symmetry, non-binding)."""
    for m in (ALIENWARE_LAPTOP, PROMAX):
        kinds = {r.kind for r in m.regions}
        assert "skin" in kinds and "battery" in kinds, m.id
    tower_kinds = {r.kind for r in ALIENWARE_DESKTOP.regions}
    assert "battery" not in tower_kinds
    assert "power" in tower_kinds, "the tower's supply is a PSU, not a pack"


def test_only_the_promax_carries_an_npu():
    assert any(r.kind == "npu" for r in PROMAX.regions)
    assert not any(r.kind == "npu" for r in ALIENWARE_LAPTOP.regions)
    assert not any(r.kind == "npu" for r in ALIENWARE_DESKTOP.regions)


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
    from app.engine import simulate

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
        "power-limits", "thermal-budget", "skin-cap",
        "battery-runtime", "energy-identity", "tokens-per-joule",
    } <= ids
    for e in EXPLAINS:
        assert e.equation.strip() and e.explanation.strip(), e.id
        assert len(e.inputs) >= 3, f"{e.id}: causal chain too short"
