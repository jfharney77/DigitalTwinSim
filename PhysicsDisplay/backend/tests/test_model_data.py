"""Integrity checks for the constants table, validation rules, panel map,
and presets — the app's data contract. Includes the suite's sustainability
rule: every carbon constant is labeled and cited, never invented."""

from __future__ import annotations

from typing import get_args

from app.anatomy import ANATOMY
from app.constants import CONSTANTS
from app.models import DisplayConfig, Lifecycle, RegionKind, Scenario
from app.presets import EDGE, EXPLAINS, GUIDED_SCENARIOS, MINILED, MODEL_PRESETS
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


def test_carbon_constants_are_cited_not_invented():
    """The Circular Design rule: no invented sustainability numbers. Every
    kgCO2e constant must cite a Dell PCF document by name."""
    carbon = {k: c for k, c in CONSTANTS.items() if c.unit == "kgCO2e"}
    assert carbon, "the carbon constants went missing"
    for name, c in carbon.items():
        assert "pcf" in c.source.lower() or "carbon footprint" in c.source.lower(), (
            f"{name}: carbon figure without a PCF citation"
        )
        assert not c.estimated, f"{name}: carbon constants must be sourced, not invented"


def test_lit_fractions_are_ordered():
    assert (CONSTANTS["lit_dark"].value
            < CONSTANTS["lit_mixed"].value
            < CONSTANTS["lit_bright"].value)
    assert 0 < CONSTANTS["lit_hdr"].value < 1


# --- Validation rules --------------------------------------------------------

def _findings(cfg: DisplayConfig, **life) -> dict[str, str]:
    s = Scenario(config=cfg, lifecycle=Lifecycle(**life))
    return {v.rule_id: v.level for v in validate(s)}


def test_dimming_on_edge_lit_warns():
    cfg = DisplayConfig(model="edge-27", local_dimming=True)
    assert _findings(cfg)["dimming"] == "warning"
    assert _findings(MINILED)["dimming"] == "ok"


def test_hdr_without_dimming_warns():
    cfg = DisplayConfig(model="miniled-32", content="hdr", local_dimming=False)
    assert _findings(cfg).get("hdr") == "warning"
    assert "hdr" not in _findings(MINILED)


def test_signage_duty_warns():
    assert _findings(EDGE, hours_per_day=22).get("duty") == "warning"
    assert "duty" not in _findings(EDGE, hours_per_day=8)


def test_every_rule_carries_a_source():
    for v in validate(Scenario()):
        assert v.source.strip(), v.rule_id


# --- Panel map ---------------------------------------------------------------

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


def test_the_panel_dominates_the_map():
    """On a monitor the screen is the product; the geometry must say so."""
    by_kind = {}
    for r in ANATOMY.regions:
        by_kind.setdefault(r.kind, 0.0)
        by_kind[r.kind] += r.w * r.h
    panel_area = by_kind.pop("panel")
    assert panel_area > max(by_kind.values()) * 2


def test_there_is_no_cooling_region():
    """Fanless is a fact of the product, pinned so nobody 'completes' the
    map with a fan later."""
    assert all(r.kind != "cooling" for r in ANATOMY.regions)  # type: ignore[comparison-overlap]
    assert ANATOMY.sources, "the map must cite its sources"


# --- Presets & scenarios -------------------------------------------------------

def test_model_presets_are_the_two_classes():
    ids = {p.id for p in MODEL_PRESETS}
    assert ids == {"edge-27", "miniled-32"}
    for p in MODEL_PRESETS:
        assert p.blurb.strip(), p.id


def test_presets_pass_their_own_hard_rules():
    for p in MODEL_PRESETS:
        errors = [v for v in validate(Scenario(config=p.config))
                  if v.level == "error"]
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


def test_explain_entries_cover_the_key_readouts():
    ids = {e.id for e in EXPLAINS}
    assert {"backlight-power", "wall-power", "heat", "use-carbon"} <= ids
    for e in EXPLAINS:
        assert e.equation.strip() and e.explanation.strip(), e.id
        assert len(e.inputs) >= 2, f"{e.id}: causal chain too short"
