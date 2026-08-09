"""Integrity checks for the constants table, validation rules, factory
map, and presets — the app's data contract."""

from __future__ import annotations

from typing import get_args

from app.anatomy import ANATOMY
from app.constants import CONSTANTS
from app.engine import REGION_IDS
from app.models import DataBlock, FabricBlock, FacilityBlock, RegionKind, ResilienceBlock, Scenario
from app.presets import (
    EXPLAINS,
    FACTORY,
    FACTORY_PRESETS,
    FRONTIER_LLM,
    GUIDED_SCENARIOS,
    JOB_PRESETS,
    STARVED,
)
from app.validation import optimal_checkpoint_min, validate

EXPECTED_KINDS = set(get_args(RegionKind))


# --- Constants ---------------------------------------------------------------

def test_every_constant_has_units_source_and_blurb():
    """The honesty rule: no invented figures presented as fact — every
    constant carries a source, and estimates say so."""
    for name, c in CONSTANTS.items():
        assert c.unit.strip(), name
        assert c.source.strip(), name
        assert c.blurb.strip(), name
        if "estimate" in c.source.lower():
            assert c.estimated, f"{name}: estimate in source but not flagged"
        if c.estimated:
            assert "estimate" in c.source.lower() or "arithmetic" in c.source.lower(), (
                f"{name}: flagged estimated but source doesn't say so"
            )


# --- Validation rules ----------------------------------------------------------

def _findings(scenario: Scenario) -> dict[str, str]:
    return {v.rule_id: v.level for v in validate(scenario)}


def test_overcommitted_budget_is_an_error():
    cfg = FACTORY.model_copy(update={"facility": FacilityBlock(mw_budget=0.5)})
    assert _findings(Scenario(config=cfg))["mw-budget"] == "error"
    assert _findings(Scenario(config=FACTORY))["mw-budget"] == "ok"


def test_tight_budget_warns():
    cfg = FACTORY.model_copy(update={"facility": FacilityBlock(mw_budget=0.95)})
    assert _findings(Scenario(config=cfg))["mw-budget"] == "warning"


def test_undersized_storage_warns_but_does_not_block():
    assert _findings(Scenario(config=STARVED))["storage"] == "warning"
    assert _findings(Scenario(config=FACTORY))["storage"] == "ok"


def test_checkpoint_interval_far_from_optimum_warns():
    cfg = FACTORY.model_copy(update={
        "resilience": ResilienceBlock(checkpoint_interval_min=480),
    })
    assert _findings(Scenario(config=cfg)).get("checkpoint") == "warning"
    assert "checkpoint" not in _findings(Scenario(config=FACTORY))
    opt = optimal_checkpoint_min(Scenario(config=FACTORY, job=FRONTIER_LLM))
    assert 10 <= opt <= 120, "Young/Daly optimum should be tens of minutes here"


def test_oversubscription_warns_on_a_training_fabric():
    cfg = FACTORY.model_copy(update={
        "fabric": FabricBlock(type="spectrum-x", oversubscription=2.0),
    })
    assert _findings(Scenario(config=cfg)).get("oversub") == "warning"
    assert "oversub" not in _findings(Scenario(config=FACTORY))


def test_every_rule_carries_a_source():
    for v in validate(Scenario()):
        assert v.source.strip(), v.rule_id


# --- Factory map -----------------------------------------------------------------

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


def test_the_fabric_sits_between_compute_and_data():
    """The geometry carries the lesson: every training byte crosses the
    fabric, so the diagram puts it physically between the two."""
    by_id = {r.id: r for r in ANATOMY.regions}
    compute, fabric, data = by_id["compute"], by_id["fabric"], by_id["data"]
    assert compute.x + compute.w <= fabric.x
    assert fabric.x + fabric.w <= data.x


def test_the_facility_row_underlies_everything():
    """Power and cooling are drawn beneath compute/fabric/data because
    every block above drains the same two budgets."""
    by_id = {r.id: r for r in ANATOMY.regions}
    row_bottom = max(
        by_id[k].y + by_id[k].h for k in ("compute", "fabric", "data")
    )
    for k in ("power", "cooling", "resilience"):
        assert by_id[k].y >= row_bottom, k


def test_engine_regions_match_the_map():
    assert set(REGION_IDS) == {r.id for r in ANATOMY.regions}


# --- Presets & scenarios ------------------------------------------------------------

def test_preset_ids_unique_and_valid():
    ids = [p.id for p in FACTORY_PRESETS] + [j.id for j in JOB_PRESETS]
    assert len(ids) == len(set(ids))
    for p in FACTORY_PRESETS:
        assert p.blurb.strip(), p.id


def test_factory_presets_pass_their_own_hard_rules():
    """No preset ships with an error-level validation — a taught example
    must be a legal build. (Warnings are allowed: 'Starved' exists to
    warn.)"""
    for p in FACTORY_PRESETS:
        errors = [
            v for v in validate(Scenario(config=p.config)) if v.level == "error"
        ]
        assert not errors, f"{p.id}: {[e.rule_id for e in errors]}"


def test_guided_scenarios_are_complete_and_runnable():
    from app.engine import simulate

    ids = [g.id for g in GUIDED_SCENARIOS]
    assert len(ids) == len(set(ids))
    assert len(GUIDED_SCENARIOS) >= 4
    for g in GUIDED_SCENARIOS:
        assert g.narration and all(p.strip() for p in g.narration), g.id
        assert g.question.strip().endswith("?"), g.id
        trace, _, _ = simulate(g.scenario)
        assert trace, g.id


def test_explain_entries_cover_the_headline_instruments():
    ids = {e.id for e in EXPLAINS}
    assert {"tokens-per-s", "idle-data", "facility-mw", "usd-per-mtok"} <= ids
    for e in EXPLAINS:
        assert e.equation.strip() and e.explanation.strip(), e.id
        assert len(e.inputs) >= 3, f"{e.id}: causal chain too short"
