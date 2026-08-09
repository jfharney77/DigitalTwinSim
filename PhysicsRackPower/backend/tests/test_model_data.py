"""Integrity checks for the constants table, validation rules, rack map,
and presets — the twin's data contract."""

from __future__ import annotations

from typing import get_args

from app.anatomy import ANATOMY
from app.constants import CONSTANTS
from app.models import (
    Environment,
    RackConfig,
    RackLoad,
    RegionKind,
    Scenario,
)
from app.presets import (
    BALANCED,
    CONFIG_PRESETS,
    EXPLAINS,
    GUIDED_SCENARIOS,
    HEAVY_PHASE,
    OLD_BATTERIES,
    _loads,
)
from app.validation import validate

EXPECTED_KINDS = set(get_args(RegionKind))


# --- Constants ---------------------------------------------------------------

def test_every_constant_has_units_source_and_blurb():
    """The suite's honesty rule: no invented specs presented as fact —
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


# --- Validation rules ----------------------------------------------------------

def _findings(cfg: RackConfig, **env) -> dict[str, str]:
    s = Scenario(config=cfg, environment=Environment(**env))
    return {v.rule_id: v.level for v in validate(s)}


def test_80_percent_rule_warns_and_100_percent_warns_harder():
    assert _findings(BALANCED)["breaker"] == "ok"
    assert _findings(HEAVY_PHASE)["breaker"] == "warning"  # 89% of rating
    over = HEAVY_PHASE.model_copy(deep=True)
    over.loads = _loads(
        ("GPU 1", 1200, "A"), ("GPU 2", 1200, "A"),
        ("GPU 3", 1200, "A"), ("GPU 4", 1200, "A"),
    )
    finding = [v for v in validate(Scenario(config=over)) if v.rule_id == "breaker"]
    assert finding[0].level == "warning"
    assert "trip" in finding[0].message.lower(), "over-rating must promise the trip"


def test_imbalance_warns_when_lopsided():
    lop = RackConfig(loads=_loads(
        ("S1", 400, "A"), ("S2", 400, "A"), ("S3", 400, "A"),
    ))
    assert _findings(lop)["imbalance"] == "warning"
    assert _findings(BALANCED)["imbalance"] == "ok"


def test_battery_age_warns_past_end_of_life():
    assert _findings(OLD_BATTERIES)["battery-age"] == "warning"
    assert _findings(BALANCED)["battery-age"] == "ok"


def test_hot_room_vrla_advisory():
    assert _findings(BALANCED, room_temp_c=35).get("room-temp") == "warning"
    assert "room-temp" not in _findings(BALANCED, room_temp_c=25)
    lith = BALANCED.model_copy(update={"ups_chemistry": "lithium"})
    assert "room-temp" not in _findings(lith, room_temp_c=35)


def test_every_rule_carries_a_source():
    for v in validate(Scenario()):
        assert v.source.strip(), v.rule_id


# --- Rack map -------------------------------------------------------------------

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


def test_kinds_are_expected_set():
    kinds = {r.kind for r in ANATOMY.regions}
    assert kinds == EXPECTED_KINDS


def test_the_geometry_tells_the_power_story():
    """Eight uniform load slots in one column, three uniform phase strips
    beside them, the UPS and battery across the bottom — the drawing is
    the electrical hierarchy."""
    loads = [r for r in ANATOMY.regions if r.kind == "load"]
    pdus = [r for r in ANATOMY.regions if r.kind == "pdu"]
    ups = [r for r in ANATOMY.regions if r.kind == "ups"]
    batt = [r for r in ANATOMY.regions if r.kind == "battery"]
    assert len(loads) == 8 and len(pdus) == 3
    assert len(ups) == 1 and len(batt) == 1
    assert len({(r.w, r.h, r.x) for r in loads}) == 1, "slots uniform, one column"
    assert len({(r.w, r.h, r.y) for r in pdus}) == 1, "strips uniform, one row"
    assert min(p.x for p in pdus) >= max(r.x + r.w for r in loads), (
        "phase strips sit beside the load column"
    )
    for r in ups + batt:
        assert r.y >= max(ld.y + ld.h for ld in loads), (
            "the UPS layer underlies everything"
        )


def test_sources_are_present():
    assert len(ANATOMY.sources) >= 2
    for s in ANATOMY.sources:
        assert s["label"].strip() and s["url"].startswith("http")


# --- Presets & scenarios -----------------------------------------------------------

def test_preset_ids_unique_and_valid():
    ids = [p.id for p in CONFIG_PRESETS]
    assert len(ids) == len(set(ids))
    for p in CONFIG_PRESETS:
        assert p.blurb.strip(), p.id
        assert len(p.config.loads) == 8, p.id


def test_config_presets_pass_their_own_hard_rules():
    """No preset ships with an error-level validation — presets are the
    taught examples, and a taught example must be a legal build."""
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
    """Live-substituted equations for at least phase current, imbalance,
    the breaker curve, runtime, fade, and wall power."""
    ids = {e.id for e in EXPLAINS}
    assert {
        "phase-current", "imbalance", "breaker-trip",
        "runtime", "fade", "wall-power",
    } <= ids
    for e in EXPLAINS:
        assert e.equation.strip() and e.explanation.strip(), e.id
        assert len(e.inputs) >= 3, f"{e.id}: causal chain too short"


def test_loads_are_validated_to_eight_slots():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RackConfig(loads=[RackLoad()])
