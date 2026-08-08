"""Integrity checks for the constants, validation rules, product maps,
and presets."""

from __future__ import annotations

from typing import get_args

from app.anatomy import MAPS
from app.constants import CONSTANTS, PROTECTION_OVERHEAD, PROTECTION_SURVIVES
from app.engine import simulate
from app.models import RegionKind, Scenario, StorageConfig, Workload
from app.presets import (
    CONFIG_PRESETS,
    EXASCALE_32,
    EXPLAINS,
    GUIDED_SCENARIOS,
    POWERFLEX_20,
    POWERMAX_4,
    WORKLOAD_PRESETS,
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


def test_protection_tables_are_complete_and_sane():
    from app.models import Protection

    schemes = set(get_args(Protection))
    assert set(PROTECTION_OVERHEAD) == schemes
    assert set(PROTECTION_SURVIVES) == schemes
    assert PROTECTION_SURVIVES["raid6"] > PROTECTION_SURVIVES["raid5"]
    assert PROTECTION_SURVIVES["ec16+4"] > PROTECTION_SURVIVES["ec8+2"]


# --- Validation rules ------------------------------------------------------

def _findings(cfg: StorageConfig, wl: Workload | None = None) -> dict[str, str]:
    s = Scenario(config=cfg, workload=wl or Workload())
    return {v.rule_id: v.level for v in validate(s)}


def test_cluster_size_envelope():
    tiny = StorageConfig(product="powerscale", units=2)
    assert _findings(tiny)["units"] == "error"
    assert _findings(StorageConfig(product="powerscale", units=20))["units"] == "ok"


def test_oversubscribed_demand_warns_not_blocks():
    wl = Workload(iops_demand_k=5000)
    assert _findings(StorageConfig(product="powerstore", units=2), wl)["capacity"] == "warning"


def test_powerflex_network_bound_warns():
    slow = POWERFLEX_20.model_copy(update={"nic_gbps": 10})
    assert _findings(slow).get("network") == "warning"
    assert "network" not in _findings(POWERFLEX_20)


def test_sync_distance_warns_past_metro():
    far = POWERMAX_4.model_copy(update={"srdf": "sync", "distance_km": 500})
    assert _findings(far).get("srdf-distance") == "warning"


def test_hdd_oltp_warns():
    cfg = StorageConfig(product="powerscale", units=10, drive_class="hdd")
    wl = Workload(iops_demand_k=200, block_kb=8)
    assert _findings(cfg, wl).get("hdd-oltp") == "warning"


def test_thin_protection_at_scale_warns():
    cfg = StorageConfig(product="powerflex", units=40, protection="mirror")
    assert _findings(cfg).get("protection") == "warning"


def test_exascale_partition_must_cover_the_pool():
    bad = EXASCALE_32.model_copy(update={"block_units": 0})
    assert _findings(bad)["partition"] == "error"
    assert _findings(EXASCALE_32)["partition"] == "ok"


def test_every_rule_carries_a_source():
    for p in CONFIG_PRESETS:
        for v in validate(Scenario(config=p.config)):
            assert v.source.strip(), v.rule_id


# --- Product maps ----------------------------------------------------------

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


def test_geometry_carries_each_architecture():
    """Controllers only on the arrays; a node band only on scale-out;
    the network as a first-class block on PowerFlex; four pools on
    Exascale."""
    assert any(r.kind == "controller" for r in MAPS["powerstore"].regions)
    assert any(r.kind == "controller" for r in MAPS["powermax"].regions)
    for scale_out in ("powerscale", "objectscale", "powerflex"):
        assert not any(r.kind == "controller" for r in MAPS[scale_out].regions), (
            f"{scale_out} must not draw a controller — there isn't one"
        )
        assert any(r.kind == "node" for r in MAPS[scale_out].regions)
    assert any(r.kind == "replication" for r in MAPS["powermax"].regions)
    assert sum(1 for r in MAPS["exascale"].regions if r.kind == "pool") == 4


# --- Presets & scenarios ---------------------------------------------------

def test_preset_ids_unique_and_valid():
    ids = [p.id for p in CONFIG_PRESETS] + [w.id for w in WORKLOAD_PRESETS]
    assert len(ids) == len(set(ids))
    assert len(CONFIG_PRESETS) == 6, "one preset per product"
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
    assert len(GUIDED_SCENARIOS) >= 8
    products_covered = {g.scenario.config.product for g in GUIDED_SCENARIOS}
    assert products_covered == {
        "powerstore", "powermax", "powerscale", "objectscale", "powerflex",
        "exascale",
    }, "every product gets at least one scenario"
    for g in GUIDED_SCENARIOS:
        assert g.narration and all(p.strip() for p in g.narration), g.id
        assert g.question.strip().endswith("?"), g.id
        trace, _, _ = simulate(g.scenario)
        assert trace, g.id


def test_explain_entries_cover_the_required_readouts():
    ids = {e.id for e in EXPLAINS}
    assert {"queueing", "capacity", "rebuild", "srdf", "gpu-idle"} <= ids
    for e in EXPLAINS:
        assert e.equation.strip() and e.explanation.strip(), e.id
        assert len(e.inputs) >= 3, f"{e.id}: causal chain too short"
