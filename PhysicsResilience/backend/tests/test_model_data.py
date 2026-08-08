"""Integrity checks for the constants, validation rules, maps, and
presets — including the scope boundary's presence on every surface."""

from __future__ import annotations

from typing import get_args

from app.anatomy import MAPS
from app.constants import CONSTANTS
from app.engine import simulate
from app.models import SCOPE_NOTE, RegionKind, ResilienceConfig, Scenario
from app.presets import (
    CONFIG_PRESETS,
    EXPLAINS,
    GUIDED_SCENARIOS,
    INHOUSE,
    VAULTED,
    ZT,
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


def test_scope_note_rides_on_every_map():
    for m in MAPS.values():
        assert any(SCOPE_NOTE in str(s.values()) for s in m.sources), m.id


# --- Validation rules ------------------------------------------------------

def _findings(cfg: ResilienceConfig) -> dict[str, str]:
    return {v.rule_id: v.level for v in validate(Scenario(config=cfg))}


def test_no_vault_warns():
    bare = VAULTED.model_copy(update={"vault": False})
    assert _findings(bare)["three-two-one"] == "warning"
    assert _findings(VAULTED)["three-two-one"] == "ok"


def test_rto_arithmetic_warns_at_scale():
    big = VAULTED.model_copy(update={"estate_tb": 500, "restore_gbps": 1.0})
    assert _findings(big)["rto"] == "warning"
    fast = VAULTED.model_copy(update={"estate_tb": 50, "restore_gbps": 5.0})
    assert _findings(fast)["rto"] == "ok"


def test_sparse_backups_warn():
    weekly = VAULTED.model_copy(update={"backup_every_h": 168})
    assert _findings(weekly).get("rpo") == "warning"


def test_max_sensitivity_warns_about_the_afternoons():
    keen = VAULTED.model_copy(update={"detection": True, "sensitivity": 10})
    assert _findings(keen).get("sensitivity") == "warning"


def test_noise_beyond_capacity_warns():
    noisy = INHOUSE.model_copy(update={"noise_alerts_day": 300})
    assert _findings(noisy).get("fatigue") == "warning"


def test_zero_trust_without_review_warns():
    lazy = ZT.model_copy(update={"review_cadence_days": 0})
    assert _findings(lazy).get("review") == "warning"


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


def test_the_vault_is_strictly_right_of_the_gap():
    """The PowerProtect twin's geometry, honored: everything the
    incident can reach lies left of the gap; the vault lies right."""
    m = MAPS["powerprotect"]
    gap = next(r for r in m.regions if r.kind == "gap")
    vault = next(r for r in m.regions if r.kind == "vault")
    estate = next(r for r in m.regions if r.kind == "estate")
    backup = next(r for r in m.regions if r.kind == "backup")
    assert estate.x + estate.w <= gap.x
    assert backup.x + backup.w <= gap.x
    assert vault.x >= gap.x + gap.w


# --- Presets & scenarios ---------------------------------------------------

def test_preset_ids_unique_and_valid():
    ids = [p.id for p in CONFIG_PRESETS]
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
    assert len(GUIDED_SCENARIOS) >= 6
    products = {g.scenario.config.product for g in GUIDED_SCENARIOS}
    assert products == {"powerprotect", "cyberdetect", "mdr", "fortzero"}
    for g in GUIDED_SCENARIOS:
        assert g.narration and all(p.strip() for p in g.narration), g.id
        assert g.question.strip().endswith("?"), g.id
        trace, _, _ = simulate(g.scenario)
        assert trace, g.id


def test_scenarios_stay_inside_the_scope_boundary():
    """No scenario narration describes technique — spot-check the
    vocabulary the boundary forbids."""
    banned = ("exploit", "payload", "vulnerability", "CVE", "phish")
    for g in GUIDED_SCENARIOS:
        text = " ".join(g.narration).lower()
        for word in banned:
            assert word.lower() not in text, (g.id, word)


def test_explain_entries_cover_the_required_readouts():
    ids = {e.id for e in EXPLAINS}
    assert {"rpo", "rto", "blast", "roc"} <= ids
    for e in EXPLAINS:
        assert e.equation.strip() and e.explanation.strip(), e.id
        assert len(e.inputs) >= 3, f"{e.id}: causal chain too short"
