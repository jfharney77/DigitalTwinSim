"""Integrity checks for the constants table, validation rules, chassis
map, and presets — the twin's data contract."""

from __future__ import annotations

from typing import get_args

from app.anatomy import ANATOMY
from app.constants import CONSTANTS, PSU_EFFICIENCY_CURVE
from app.models import RegionKind, Scenario, ServerConfig
from app.presets import (
    CONFIG_PRESETS,
    EXPLAINS,
    GPU_NODE,
    GUIDED_SCENARIOS,
    MAX_CPU,
    WORKLOAD_PRESETS,
)
from app.validation import validate

EXPECTED_KINDS = set(get_args(RegionKind))


# --- Constants (spec §2, §9.5, §9.7) --------------------------------------

def test_every_constant_has_units_source_and_blurb():
    """The spec's honesty rule: no invented Dell specs presented as fact —
    every constant carries a source, and estimates say so."""
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
    assert all(0.8 <= e <= 1.0 for _, e in PSU_EFFICIENCY_CURVE)


# --- Validation rules (spec §6) -------------------------------------------

def _findings(cfg: ServerConfig, **env) -> dict[str, str]:
    from app.models import Environment

    s = Scenario(config=cfg, environment=Environment(**env))
    return {v.rule_id: v.level for v in validate(s)}


def test_high_tdp_without_hp_heatsink_is_an_error():
    cfg = ServerConfig(cpu_tdp_w=250, heatsink="standard")
    assert _findings(cfg)["heatsink"] == "error"
    cfg = ServerConfig(cpu_tdp_w=205, heatsink="standard")
    assert _findings(cfg)["heatsink"] == "ok"


def test_double_wide_gpu_without_gold_fans_is_an_error():
    cfg = ServerConfig(gpus_double_wide=1, fan_kit="standard")
    assert _findings(cfg)["fan-kit"] == "error"
    cfg = ServerConfig(cpu_tdp_w=300, fan_kit="standard")
    assert _findings(cfg)["fan-kit"] == "error"
    assert _findings(GPU_NODE)["fan-kit"] == "ok"


def test_max_tdp_hot_room_warns():
    assert _findings(MAX_CPU, inlet_c=35).get("ambient") == "warning"
    assert "ambient" not in _findings(MAX_CPU, inlet_c=22)


def test_psu_oversubscription_warns_but_does_not_block():
    cfg = GPU_NODE.model_copy(update={"psu_capacity_w": 800})
    assert _findings(cfg)["psu"] == "warning"
    assert _findings(GPU_NODE)["psu"] == "ok"


def test_altitude_advisory():
    assert _findings(GPU_NODE, altitude_m=2000).get("altitude") == "warning"
    assert "altitude" not in _findings(GPU_NODE, altitude_m=500)


def test_every_rule_carries_a_source():
    for v in validate(Scenario()):
        assert v.source.strip(), v.rule_id


# --- Chassis map ----------------------------------------------------------

def test_region_ids_unique_and_in_bounds():
    ids = [r.id for r in ANATOMY.regions]
    assert len(ids) == len(set(ids))
    for r in ANATOMY.regions:
        assert 0 <= r.x and r.x + r.w <= ANATOMY.width, r.id
        assert 0 <= r.y and r.y + r.h <= ANATOMY.height, r.id
        assert r.w > 0 and r.h > 0, r.id
        assert r.description.strip(), r.id


def test_regions_do_not_overlap():
    rs = ANATOMY.regions
    for i, a in enumerate(rs):
        for b in rs[i + 1:]:
            disjoint = (
                a.x + a.w <= b.x or b.x + b.w <= a.x
                or a.y + a.h <= b.y or b.y + b.h <= a.y
            )
            assert disjoint, f"{a.id} overlaps {b.id}"


def test_airflow_axis_is_drawn():
    """Front-to-back is the model's spine: drives at the front, fans next,
    PSUs at the rear — pinned so the geometry keeps telling the truth."""
    by_id = {r.id: r for r in ANATOMY.regions}
    drives = by_id["backplane"]
    fans = [r for r in ANATOMY.regions if r.kind == "cooling"]
    psus = [r for r in ANATOMY.regions if r.kind == "power"]
    assert len(fans) == 6 and len(psus) == 2
    assert drives.x + drives.w <= min(f.x for f in fans)
    assert max(f.x + f.w for f in fans) <= min(p.x for p in psus)


def test_kinds_are_expected_set():
    kinds = {r.kind for r in ANATOMY.regions}
    assert kinds == EXPECTED_KINDS


# --- Presets & scenarios --------------------------------------------------

def test_preset_ids_unique_and_valid():
    ids = [p.id for p in CONFIG_PRESETS] + [w.id for w in WORKLOAD_PRESETS]
    assert len(ids) == len(set(ids))
    for p in CONFIG_PRESETS:
        assert p.blurb.strip(), p.id


def test_config_presets_pass_their_own_hard_rules():
    """No preset ships with an error-level validation — the presets are
    the taught examples, and a taught example must be a legal build."""
    for p in CONFIG_PRESETS:
        errors = [
            v for v in validate(Scenario(config=p.config)) if v.level == "error"
        ]
        assert not errors, f"{p.id}: {[e.rule_id for e in errors]}"


def test_guided_scenarios_are_complete_and_runnable():
    from app.engine import simulate

    ids = [g.id for g in GUIDED_SCENARIOS]
    assert len(ids) == len(set(ids))
    assert len(GUIDED_SCENARIOS) >= 5, "spec §8 asks for 5–8 walkthroughs"
    for g in GUIDED_SCENARIOS:
        assert g.narration and all(p.strip() for p in g.narration), g.id
        assert g.question.strip().endswith("?"), g.id
        trace, _, _ = simulate(g.scenario)
        assert trace, g.id


def test_explain_entries_cover_the_required_readouts():
    """Spec §9.6: live-substituted equations for at least CPU power, zone
    outlet temp, fan power, and PSU wall power."""
    ids = {e.id for e in EXPLAINS}
    assert {"cpu-power", "zone-outlet", "fan-power", "wall-power"} <= ids
    for e in EXPLAINS:
        assert e.equation.strip() and e.explanation.strip(), e.id
        assert len(e.inputs) >= 3, f"{e.id}: causal chain too short"
