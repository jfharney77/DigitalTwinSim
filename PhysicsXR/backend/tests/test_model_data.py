"""Integrity checks for the constants table, validation rules, chassis
map, and presets — the twin's data contract."""

from __future__ import annotations

from typing import get_args

from app.anatomy import ANATOMY
from app.constants import CONSTANTS, PSU_EFFICIENCY_CURVE
from app.models import Environment, RegionKind, Scenario, ServerConfig
from app.presets import (
    CELL_SITE,
    CONFIG_PRESETS,
    EXPLAINS,
    FACTORY_FLOOR,
    GUIDED_SCENARIOS,
    HDD_MISTAKE,
    WORKLOAD_PRESETS,
)
from app.validation import validate

EXPECTED_KINDS = set(get_args(RegionKind))


# --- Constants --------------------------------------------------------------

def test_every_constant_has_units_source_and_blurb():
    """The honesty rule: no invented Dell specs presented as fact — every
    constant carries a source, and estimates say so."""
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


def test_the_rated_envelopes_are_documented_not_estimated():
    """The one set of numbers this twin exists to teach must be Dell's own."""
    for name in ("xr_standard_min_c", "xr_standard_max_c",
                 "xr_extended_min_c", "xr_extended_max_c"):
        assert not CONSTANTS[name].estimated, name
        assert "dell" in CONSTANTS[name].source.lower(), name


def test_efficiency_curve_is_monotone_in_load():
    loads = [x for x, _ in PSU_EFFICIENCY_CURVE]
    assert loads == sorted(loads)
    assert all(0.8 <= e <= 1.0 for _, e in PSU_EFFICIENCY_CURVE)


# --- Validation rules --------------------------------------------------------

def _findings(cfg: ServerConfig, **env) -> dict[str, str]:
    s = Scenario(config=cfg, environment=Environment(**env))
    return {v.rule_id: v.level for v in validate(s)}


def test_wrong_platform_cpu_tier_is_an_error():
    cfg = ServerConfig(platform="xr4000", cpu_tdp_w=250)
    assert _findings(cfg)["cpu-tier"] == "error"
    assert _findings(CELL_SITE)["cpu-tier"] == "ok"


def test_extended_envelope_is_select_configs_only():
    ok = ServerConfig(platform="xr8000", cpu_tdp_w=185,
                      thermal_config="extended", drive_type="ssd")
    assert _findings(ok)["extended-envelope"] == "ok"
    too_hot = ok.model_copy(update={"cpu_tdp_w": 250})
    assert _findings(too_hot)["extended-envelope"] == "error"
    spinning = ok.model_copy(update={"drive_type": "hdd"})
    assert _findings(spinning)["extended-envelope"] == "error"
    wrong_box = ok.model_copy(update={"platform": "xr4000", "cpu_tdp_w": 100})
    assert _findings(wrong_box)["extended-envelope"] == "error"


def test_ambient_outside_the_envelope_warns_but_runs():
    assert _findings(CELL_SITE, inlet_c=60)["envelope"] == "warning"
    assert _findings(CELL_SITE, inlet_c=-10)["envelope"] == "warning"
    assert _findings(CELL_SITE, inlet_c=40)["envelope"] == "ok"
    # The extended config widens what counts as inside.
    ext = ServerConfig(platform="xr8000", cpu_tdp_w=185,
                       thermal_config="extended", drive_type="ssd")
    assert _findings(ext, inlet_c=-10)["envelope"] == "ok"
    assert _findings(ext, inlet_c=60)["envelope"] == "ok"


def test_hdd_under_vibration_warns_toward_ssds():
    assert _findings(HDD_MISTAKE, vibration="vehicle")["vibration"] == "warning"
    assert "vibration" not in _findings(HDD_MISTAKE, vibration="none")
    ssd = HDD_MISTAKE.model_copy(update={"drive_type": "ssd"})
    assert "vibration" not in _findings(ssd, vibration="vehicle")


def test_overdue_filter_warns():
    assert _findings(CELL_SITE, dust="heavy", filter_months=8)["filter"] == "warning"
    assert "filter" not in _findings(CELL_SITE, dust="heavy", filter_months=2)
    assert "filter" not in _findings(CELL_SITE, dust="clean", filter_months=8)


def test_psu_oversubscription_warns_but_does_not_block():
    cfg = FACTORY_FLOOR.model_copy(update={"psu_capacity_w": 500})
    assert _findings(cfg)["psu"] == "warning"
    assert _findings(FACTORY_FLOOR)["psu"] == "ok"


def test_altitude_advisory():
    assert _findings(CELL_SITE, altitude_m=2000).get("altitude") == "warning"
    assert "altitude" not in _findings(CELL_SITE, altitude_m=500)


def test_every_rule_carries_a_source():
    for v in validate(Scenario()):
        assert v.source.strip(), v.rule_id


# --- Chassis map -------------------------------------------------------------

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
    """Front-to-back is the model's spine, and here the *filter* leads it:
    filter, then drives, then fans, then PSUs at the rear — pinned so the
    geometry keeps telling this twin's particular truth."""
    by_id = {r.id: r for r in ANATOMY.regions}
    filt = by_id["filter"]
    drives = by_id["backplane"]
    fans = [r for r in ANATOMY.regions if r.kind == "cooling"]
    psus = [r for r in ANATOMY.regions if r.kind == "power"]
    assert len(fans) == 4 and len(psus) == 2
    assert filt.x + filt.w <= drives.x
    assert drives.x + drives.w <= min(f.x for f in fans)
    assert max(f.x + f.w for f in fans) <= min(p.x for p in psus)


def test_the_filter_is_first_and_full_height():
    """The region a data-hall map never draws is this map's first thermal
    component: leftmost, spanning the full intake."""
    filt = next(r for r in ANATOMY.regions if r.kind == "filter")
    assert filt.x == min(r.x for r in ANATOMY.regions)
    assert filt.h >= ANATOMY.height - 1


def test_kinds_are_expected_set():
    kinds = {r.kind for r in ANATOMY.regions}
    assert kinds == EXPECTED_KINDS


# --- Presets & scenarios -------------------------------------------------------

def test_preset_ids_unique_and_valid():
    ids = [p.id for p in CONFIG_PRESETS] + [w.id for w in WORKLOAD_PRESETS]
    assert len(ids) == len(set(ids))
    for p in CONFIG_PRESETS:
        assert p.blurb.strip(), p.id


def test_config_presets_pass_their_own_hard_rules():
    """No preset ships with an error-level validation — the presets are
    the taught examples, and a taught example must be a legal build. (The
    HDD-mistake preset is *warned*, which is the point; warned is legal.)"""
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
    """Live-substituted equations for the four house readouts plus the two
    XR-specific ones: fouling-loaded fan power and brownout current."""
    ids = {e.id for e in EXPLAINS}
    assert {
        "cpu-power", "zone-outlet", "fan-power", "wall-power",
        "brownout", "vibration",
    } <= ids
    for e in EXPLAINS:
        assert e.equation.strip() and e.explanation.strip(), e.id
        assert len(e.inputs) >= 3, f"{e.id}: causal chain too short"
