"""Integrity checks for the constants table, validation rules, chassis
map, and presets — the app's data contract."""

from __future__ import annotations

from typing import get_args

from app.anatomy import ANATOMY
from app.constants import CONSTANTS, PSU_EFFICIENCY_CURVE
from app.models import ChassisConfig, RegionKind, Scenario, SledConfig
from app.presets import (
    CONFIG_PRESETS,
    EIGHT_COMPUTE,
    EXPLAINS,
    GUIDED_SCENARIOS,
    WORKLOAD_PRESETS,
)
from app.validation import validate

EXPECTED_KINDS = set(get_args(RegionKind))


# --- Constants ---------------------------------------------------------------

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


def test_chassis_facts_are_sourced_not_estimated():
    """The spec flagged sled counts and PSU sizes `verify` — they were
    verified, so they must cite Dell documentation, not read `estimate`."""
    for name in ("sled_bays", "fan_count", "psu_capacity_w", "storage_sled_drives"):
        assert not CONSTANTS[name].estimated, name
        assert "Dell" in CONSTANTS[name].source, name


def test_efficiency_curve_is_monotone_in_load():
    loads = [x for x, _ in PSU_EFFICIENCY_CURVE]
    assert loads == sorted(loads)
    assert all(0.8 <= e <= 1.0 for _, e in PSU_EFFICIENCY_CURVE)


# --- Validation rules -----------------------------------------------------------

def _findings(cfg: ChassisConfig, **env) -> dict[str, str]:
    from app.models import Environment

    s = Scenario(config=cfg, environment=Environment(**env))
    return {v.rule_id: v.level for v in validate(s)}


def test_odd_psu_count_under_grid_is_an_error():
    cfg = EIGHT_COMPUTE.model_copy(update={"psu_count": 5})
    assert _findings(cfg)["grid-split"] == "error"
    assert _findings(EIGHT_COMPUTE)["grid-split"] == "ok"


def test_unowned_storage_sled_is_an_error():
    sleds = [SledConfig(kind="compute"), SledConfig(kind="storage", owner_slot=None)]
    cfg = ChassisConfig(sleds=sleds + [SledConfig() for _ in range(6)])
    assert _findings(cfg)["storage-owner"] == "error"
    # An owner pointing at an empty bay is just as broken.
    sleds = [SledConfig(kind="empty"), SledConfig(kind="storage", owner_slot=1)]
    cfg = ChassisConfig(sleds=sleds + [SledConfig() for _ in range(6)])
    assert _findings(cfg)["storage-owner"] == "error"


def test_single_feed_policies_warn():
    cfg = EIGHT_COMPUTE.model_copy(update={"redundancy": "n+1"})
    assert _findings(cfg)["feed"] == "warning"
    assert _findings(EIGHT_COMPUTE)["feed"] == "ok"


def test_pool_oversubscription_warns_but_does_not_block():
    hot = EIGHT_COMPUTE.model_copy(update={
        "sleds": [SledConfig(kind="compute", cpu_tdp_w=350, dimms=32)
                  for _ in range(8)],
        "psu_count": 2,
    })
    assert _findings(hot)["psu-budget"] == "warning"
    assert _findings(EIGHT_COMPUTE)["psu-budget"] == "ok"


def test_hot_room_with_350w_sleds_warns():
    hot = EIGHT_COMPUTE.model_copy(update={
        "sleds": [SledConfig(kind="compute", cpu_tdp_w=350) for _ in range(8)],
    })
    assert _findings(hot, inlet_c=32).get("ambient") == "warning"
    assert "ambient" not in _findings(hot, inlet_c=22)


def test_every_rule_carries_a_source():
    for v in validate(Scenario()):
        assert v.source.strip(), v.rule_id


# --- Chassis map -------------------------------------------------------------------

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


def test_shared_plant_is_drawn_chassis_wide():
    """The architecture in geometry: sled bays on top, then the fan wall,
    then the PSU pool — and the fan and PSU rows each span (nearly) the
    full chassis width, because they belong to nobody's bay."""
    bays = [r for r in ANATOMY.regions if r.kind == "bay"]
    fans = [r for r in ANATOMY.regions if r.kind == "cooling"]
    psus = [r for r in ANATOMY.regions if r.kind == "power"]
    assert len(bays) == 8 and len(fans) == 9 and len(psus) == 6
    assert max(b.y + b.h for b in bays) <= min(f.y for f in fans)
    assert max(f.y + f.h for f in fans) <= min(p.y for p in psus)
    for row in (fans, psus):
        span = max(r.x + r.w for r in row) - min(r.x for r in row)
        assert span >= ANATOMY.width * 0.9, "the shared row must span the chassis"


def test_kinds_are_expected_set():
    kinds = {r.kind for r in ANATOMY.regions}
    assert kinds == EXPECTED_KINDS


# --- Presets & scenarios ---------------------------------------------------------------

def test_preset_ids_unique_and_valid():
    ids = [p.id for p in CONFIG_PRESETS] + [w.id for w in WORKLOAD_PRESETS]
    assert len(ids) == len(set(ids))
    for p in CONFIG_PRESETS:
        assert p.blurb.strip(), p.id


def test_config_presets_pass_their_own_hard_rules():
    """No preset ships with an error-level validation — a taught example
    must be a legal build."""
    for p in CONFIG_PRESETS:
        errors = [
            v for v in validate(Scenario(config=p.config)) if v.level == "error"
        ]
        assert not errors, f"{p.id}: {[e.rule_id for e in errors]}"


def test_guided_scenarios_are_complete_and_runnable():
    from app.engine import simulate

    ids = [g.id for g in GUIDED_SCENARIOS]
    assert len(ids) == len(set(ids))
    assert len(GUIDED_SCENARIOS) >= 4, "both spec scenarios plus the chassis's own lessons"
    for g in GUIDED_SCENARIOS:
        assert g.narration and all(p.strip() for p in g.narration), g.id
        assert g.question.strip().endswith("?"), g.id
        trace, _, _ = simulate(g.scenario)
        assert trace, g.id


def test_the_two_spec_scenarios_are_present():
    ids = {g.id for g in GUIDED_SCENARIOS}
    assert {"noisy-neighbor", "grid-feed-loss", "nplus1-feed-loss"} <= ids


def test_explain_entries_cover_the_required_readouts():
    ids = {e.id for e in EXPLAINS}
    assert {"sled-power", "fan-tax", "wall-power", "redundancy"} <= ids
    for e in EXPLAINS:
        assert e.equation.strip() and e.explanation.strip(), e.id
        assert len(e.inputs) >= 3, f"{e.id}: causal chain too short"
