"""Integrity checks for the constants table, validation rules, loop map,
and presets — the twin's data contract."""

from __future__ import annotations

from typing import get_args

from app.anatomy import ANATOMY
from app.constants import CONSTANTS
from app.models import CduConfig, Environment, RegionKind, Scenario
from app.presets import (
    CONFIG_PRESETS,
    EXPLAINS,
    GUIDED_SCENARIOS,
    WORKLOAD_PRESETS,
)
from app.validation import validate

EXPECTED_KINDS = set(get_args(RegionKind))


# --- Constants ---------------------------------------------------------------

def test_every_constant_has_units_source_and_blurb():
    """The honesty rule: no invented Dell specs presented as fact —
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


def test_the_2026_products_keep_their_receipts():
    """The C7000/PowerRack/IRC are press-release-fresh: the one sourced
    capacity figure must cite the announcement, and the physics around
    it must be labeled estimate."""
    assert not CONSTANTS["hx_rated_kw"].estimated
    assert "2026" in CONSTANTS["hx_rated_kw"].source
    assert CONSTANTS["hx_ua_kw_per_k"].estimated
    assert CONSTANTS["pump_single_flow_lpm"].estimated


# --- Validation rules -----------------------------------------------------------

def _findings(cfg: CduConfig, **env) -> dict[str, str]:
    s = Scenario(config=cfg, environment=Environment(**env))
    return {v.rule_id: v.level for v in validate(s)}


def test_setpoint_below_dew_point_is_an_error():
    cfg = CduConfig(min_supply_c=18)
    assert _findings(cfg, dew_point_c=20)["dew-point"] == "error"
    cfg = CduConfig(min_supply_c=24)
    assert _findings(cfg, dew_point_c=20)["dew-point"] == "warning"
    cfg = CduConfig(min_supply_c=32)
    assert _findings(cfg, dew_point_c=20)["dew-point"] == "ok"


def test_two_pumps_warns_three_is_ok():
    assert _findings(CduConfig(pumps=2))["pump-redundancy"] == "warning"
    assert _findings(CduConfig(pumps=3))["pump-redundancy"] == "ok"


def test_oversized_rack_warns_but_does_not_block():
    assert _findings(CduConfig(tray_groups=6))["hx-sizing"] == "warning"
    assert _findings(CduConfig(tray_groups=5))["hx-sizing"] == "ok"


def test_warm_facility_water_is_flagged():
    assert _findings(CduConfig(), facility_supply_c=40).get(
        "facility-class") == "warning"
    assert "facility-class" not in _findings(CduConfig(), facility_supply_c=17)


def test_unreachable_flow_setpoint_warns():
    assert _findings(CduConfig(pumps=2, flow_setpoint_lpm=400)).get(
        "flow-setpoint") == "warning"
    assert "flow-setpoint" not in _findings(
        CduConfig(pumps=3, flow_setpoint_lpm=340))


def test_uncoordinated_policy_carries_its_warning():
    assert _findings(CduConfig(policy="uncoordinated"))["policy"] == "warning"
    assert "policy" not in _findings(CduConfig(policy="coordinated"))


def test_every_rule_carries_a_source():
    for v in validate(Scenario()):
        assert v.source.strip(), v.rule_id


# --- Loop map -----------------------------------------------------------------

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


def test_the_loop_reads_left_to_right():
    """The geometry carries the lesson: facility water, then the heat
    exchanger, then the manifolds, then the trays — heat flows the
    other way."""
    by_id = {r.id: r for r in ANATOMY.regions}
    plant = by_id["facility-plant"]
    hx = by_id["hx"]
    man_sup = by_id["manifold-supply"]
    man_ret = by_id["manifold-return"]
    trays = [r for r in ANATOMY.regions if r.kind == "tray"]
    assert plant.x + plant.w <= hx.x
    assert hx.x + hx.w <= man_sup.x
    assert man_sup.x + man_sup.w <= min(t.x for t in trays)
    assert max(t.x + t.w for t in trays) <= man_ret.x


def test_the_loop_hardware_counts():
    pumps = [r for r in ANATOMY.regions if r.kind == "pump"]
    trays = [r for r in ANATOMY.regions if r.kind == "tray"]
    assert len(pumps) == 3, "N+1 pumps drawn"
    assert len(trays) == 6, "six tray banks drawn"
    assert len({(p.w, p.h) for p in pumps}) == 1, "pumps identical"
    assert len({(t.w, t.h) for t in trays}) == 1, "tray banks identical"
    # Trays are one column, top to bottom.
    ys = [t.y for t in sorted(trays, key=lambda t: t.id)]
    assert ys == sorted(ys)
    assert len({t.x for t in trays}) == 1
    assert sum(1 for r in ANATOMY.regions if r.kind == "hx") == 1
    assert sum(1 for r in ANATOMY.regions if r.kind == "controller") == 1
    assert sum(1 for r in ANATOMY.regions if r.kind == "facility") == 1


def test_the_controller_sits_above_the_loop():
    """The IRC is a policy plane, not a wet part — drawn on top."""
    by_id = {r.id: r for r in ANATOMY.regions}
    irc = by_id["irc"]
    hx = by_id["hx"]
    assert irc.y + irc.h <= hx.y


# --- Presets & scenarios ----------------------------------------------------------

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
    assert len(GUIDED_SCENARIOS) >= 5
    for g in GUIDED_SCENARIOS:
        assert g.narration and all(p.strip() for p in g.narration), g.id
        assert g.question.strip().endswith("?"), g.id
        trace, _, _ = simulate(g.scenario)
        assert trace, g.id


def test_explain_entries_cover_the_required_readouts():
    """Live-substituted equations for the chain's links: approach, loop
    rise, pump hydraulics, silicon, and the dew floor."""
    ids = {e.id for e in EXPLAINS}
    assert {"approach", "loop-dt", "pump-flow", "chip-temp", "dew-floor"} <= ids
    for e in EXPLAINS:
        assert e.equation.strip() and e.explanation.strip(), e.id
        assert len(e.inputs) >= 3, f"{e.id}: causal chain too short"
