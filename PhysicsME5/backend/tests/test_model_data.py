"""Integrity checks for the constants table, validation rules, enclosure
map, and presets — the twin's data contract."""

from __future__ import annotations

from typing import get_args

from app.anatomy import ANATOMY
from app.constants import CONSTANTS, RISK_FACTOR
from app.models import (
    ArrayConfig,
    RegionKind,
    Scenario,
    WRITE_PENALTY,
    Workload,
)
from app.presets import (
    ALL_FLASH,
    CONFIG_PRESETS,
    EXPLAINS,
    GUIDED_SCENARIOS,
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
        if "estimate" in c.source.lower() or "verify" in c.source.lower():
            assert c.estimated, f"{name}: uncertain source but not flagged"
        if c.estimated:
            assert (
                "estimate" in c.source.lower()
                or "verify" in c.source.lower()
                or "modeling choice" in c.source.lower()
            ), f"{name}: flagged estimated but source doesn't say why"


def test_write_penalties_are_the_classic_arithmetic():
    assert WRITE_PENALTY == {"1": 2, "10": 2, "5": 4, "6": 6}


def test_risk_factors_order_r5_worst_r6_best():
    assert RISK_FACTOR["5"] > RISK_FACTOR["10"] >= RISK_FACTOR["1"] > RISK_FACTOR["6"]


def test_ssd_is_orders_of_magnitude_over_spindles():
    assert CONSTANTS["ssd_iops"].value >= 50 * CONSTANTS["hdd_10k_iops"].value
    assert CONSTANTS["hdd_10k_iops"].value > CONSTANTS["hdd_72k_iops"].value


# --- Validation rules --------------------------------------------------------

def _findings(cfg: ArrayConfig, wl: Workload | None = None) -> dict[str, str]:
    s = Scenario(config=cfg, workload=wl or Workload())
    return {v.rule_id: v.level for v in validate(s)}


def test_too_many_drives_for_the_model_is_an_error():
    cfg = ArrayConfig(model="ME5012", drive_count=24)
    assert _findings(cfg)["slots"] == "error"
    assert _findings(ArrayConfig(model="ME5024", drive_count=24))["slots"] == "ok"


def test_raid_member_minimums():
    assert _findings(ArrayConfig(model="ME5012", drive_count=3, raid_level="6",
                                 spares=0))["raid-members"] == "error"
    assert _findings(ArrayConfig(model="ME5012", drive_count=5, raid_level="10",
                                 spares=0))["raid-members"] == "error"
    assert _findings(ArrayConfig(model="ME5012", drive_count=4, raid_level="1",
                                 spares=0))["raid-members"] == "error"
    assert _findings(ArrayConfig(model="ME5012", drive_count=4, raid_level="10",
                                 spares=0))["raid-members"] == "ok"


def test_big_drive_raid5_warns_about_the_window():
    cfg = ArrayConfig(model="ME5012", drive_count=8, drive_tb=20,
                      raid_level="5", drive_type="hdd-7.2k")
    assert _findings(cfg).get("rebuild-window") == "warning"
    cfg6 = cfg.model_copy(update={"raid_level": "6"})
    assert "rebuild-window" not in _findings(cfg6)


def test_no_spare_on_parity_warns():
    cfg = ArrayConfig(drive_count=12, raid_level="6", spares=0)
    assert _findings(cfg).get("spare") == "warning"
    assert "spare" not in _findings(ArrayConfig(drive_count=12, raid_level="6",
                                                spares=1))


def test_single_controller_warns():
    assert _findings(ArrayConfig(controllers=1)).get("controller") == "warning"


def test_oversubscribed_load_warns_but_does_not_block():
    wl = Workload(offered_kiops=100, read_pct=30, block_kb=8)
    cfg = ArrayConfig(drive_type="hdd-10k", drive_count=24, raid_level="6")
    assert _findings(cfg, wl)["headroom"] == "warning"
    assert _findings(ALL_FLASH, Workload(offered_kiops=50))["headroom"] == "ok"


def test_every_rule_carries_a_source():
    for v in validate(Scenario()):
        assert v.source.strip(), v.rule_id


# --- Enclosure map ------------------------------------------------------------

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


def test_the_enclosure_is_24_slots_and_dual_everything():
    drives = [r for r in ANATOMY.regions if r.kind == "drive"]
    ctrls = [r for r in ANATOMY.regions if r.kind == "controller"]
    caches = [r for r in ANATOMY.regions if r.kind == "cache"]
    psus = [r for r in ANATOMY.regions if r.kind == "power"]
    assert len(drives) == 24
    assert len(ctrls) == 2 and len(caches) == 2 and len(psus) == 2
    # Slot uniformity: an enclosure is one building block repeated.
    assert len({(r.w, r.h, r.y) for r in drives}) == 1
    # Slots are ordered left to right.
    xs = [r.x for r in sorted(drives, key=lambda r: int(r.id.split("-")[1]))]
    assert xs == sorted(xs)


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
    assert len(GUIDED_SCENARIOS) >= 5
    for g in GUIDED_SCENARIOS:
        assert g.narration and all(p.strip() for p in g.narration), g.id
        assert g.question.strip().endswith("?"), g.id
        trace, _, _ = simulate(g.scenario)
        assert trace, g.id


def test_explain_entries_cover_the_required_readouts():
    ids = {e.id for e in EXPLAINS}
    assert {"write-penalty", "usable-capacity", "rebuild-time",
            "latency-knee"} <= ids
    for e in EXPLAINS:
        assert e.equation.strip() and e.explanation.strip(), e.id
        assert len(e.inputs) >= 3, f"{e.id}: causal chain too short"
