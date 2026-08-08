"""Integrity checks for constants, validation rules, maps, and presets
— including the PCF honesty footnote's presence."""

from __future__ import annotations

from typing import get_args

from app.anatomy import MAPS
from app.constants import CONSTANTS
from app.engine import simulate
from app.models import PCF_NOTE, LifecycleConfig, RegionKind, Scenario
from app.presets import (
    BLOCKS,
    CONFIG_PRESETS,
    DIY,
    EXPLAINS,
    GUIDED_SCENARIOS,
    SEALED,
    SERVICEABLE,
    STANDARD_TEMP,
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


def test_pcf_note_exists_and_rides_on_every_map():
    assert "Product Carbon Footprint" in PCF_NOTE
    assert "estimates" in PCF_NOTE
    for m in MAPS.values():
        assert any(PCF_NOTE in str(s.values()) for s in m.sources), m.id


# --- Validation rules ------------------------------------------------------

def _findings(cfg: LifecycleConfig) -> dict[str, str]:
    return {v.rule_id: v.level for v in validate(Scenario(config=cfg))}


def test_diy_bill_is_quoted_up_front():
    assert _findings(DIY)["integration"] == "warning"
    assert _findings(BLOCKS)["integration"] == "ok"


def test_standard_temp_warns():
    assert _findings(STANDARD_TEMP).get("temp") == "warning"
    assert "temp" not in _findings(BLOCKS)


def test_no_spares_warns():
    bare = BLOCKS.model_copy(update={"spare_capacity": False})
    assert _findings(bare).get("spares") == "warning"


def test_sealed_design_warns_and_pcf_always_shows():
    assert _findings(SEALED)["sealed"] == "warning"
    assert _findings(SEALED).get("second-life") == "warning"
    assert _findings(SERVICEABLE)["sealed"] == "ok"
    assert _findings(SERVICEABLE)["pcf"] == "ok"
    assert _findings(SEALED)["pcf"] == "ok", "the honest footnote is unconditional"


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
    assert products == {"telecomblocks", "circulardesign"}
    for g in GUIDED_SCENARIOS:
        assert g.narration and all(p.strip() for p in g.narration), g.id
        assert g.question.strip().endswith("?"), g.id
        trace, _, _ = simulate(g.scenario)
        assert trace, g.id


def test_explain_entries_cover_the_required_readouts():
    ids = {e.id for e in EXPLAINS}
    assert {"matrix", "five-nines", "carbon-ledger", "embodied-vs-use"} <= ids
    for e in EXPLAINS:
        assert e.equation.strip() and e.explanation.strip(), e.id
        assert len(e.inputs) >= 3, f"{e.id}: causal chain too short"
