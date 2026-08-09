"""Integrity checks for the constants table, appliance table, validation
rules, pipeline map, and presets — the app's data contract."""

from __future__ import annotations

from typing import get_args

from app.anatomy import ANATOMY
from app.constants import APPLIANCES, CONSTANTS
from app.models import Dataset, RegionKind, Scenario, Schedule, SimEvent
from app.presets import DATASET_PRESETS, EXPLAINS, GUIDED_SCENARIOS
from app.validation import validate

EXPECTED_KINDS = set(get_args(RegionKind))


# --- Constants (the suite's honesty rule) ----------------------------------

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


def test_appliance_table_is_honest_and_sane():
    for a in APPLIANCES.values():
        assert a.source.strip() and a.blurb.strip(), a.id
        assert a.usable_tb > 0 and a.index_ram_gb > 0 and a.base_ingest_gbps > 0
        if a.estimated:
            assert "estimate" in a.source.lower(), a.id
    # The lineup keeps its shape: edge < all-flash < disk flagship on capacity.
    assert (
        APPLIANCES["dd3410"].usable_tb
        < APPLIANCES["dd-all-flash"].usable_tb
        < APPLIANCES["dd9910"].usable_tb
    )


# --- Validation rules --------------------------------------------------------

def _findings(scenario: Scenario) -> dict[str, str]:
    return {v.rule_id: v.level for v in validate(scenario)}


def test_one_backup_that_cannot_fit_is_an_error():
    s = Scenario(
        appliance="dd3410",
        dataset=Dataset(full_tb=100, daily_change_pct=1, entropy_pct=30),
    )
    assert _findings(s)["first-fit"] == "error"
    s2 = Scenario(appliance="dd9910")
    assert _findings(s2)["first-fit"] == "ok"


def test_oversubscribed_retention_warns_but_does_not_block():
    s = Scenario(
        appliance="dd3410",
        dataset=Dataset(full_tb=20, daily_change_pct=10, entropy_pct=30),
        schedule=Schedule(retention_days=365),
    )
    assert _findings(s)["capacity-forecast"] == "warning"


def test_host_encryption_in_the_plan_warns():
    s = Scenario(events=[SimEvent(at_day=10, action="enable-host-encryption")])
    assert _findings(s).get("encrypted-source") == "warning"
    assert "encrypted-source" not in _findings(Scenario())


def test_high_entropy_warns():
    s = Scenario(dataset=Dataset(full_tb=50, daily_change_pct=2, entropy_pct=90))
    assert _findings(s).get("entropy") == "warning"


def test_index_pressure_forecast_warns_on_the_knee_build():
    s = Scenario(
        appliance="dd3410",
        dataset=Dataset(full_tb=20, daily_change_pct=3, entropy_pct=30),
        schedule=Schedule(retention_days=60),
    )
    assert _findings(s).get("index-pressure") == "warning"
    assert _findings(Scenario())["index-pressure"] == "ok"


def test_every_rule_carries_a_source():
    for v in validate(Scenario()):
        assert v.source.strip(), v.rule_id


# --- Pipeline map -------------------------------------------------------------

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


def test_the_pipeline_reads_left_to_right():
    """The geometry carries the lesson: streams → Boost → chunker →
    index/store → cleaning, in x order — data flows one way."""
    by_id = {r.id: r for r in ANATOMY.regions}
    order = ["streams", "boost", "chunker", "index", "cleaner"]
    xs = [by_id[i].x for i in order]
    assert xs == sorted(xs)
    assert by_id["chunker"].x + by_id["chunker"].w <= by_id["store"].x
    # Index above store: the lookup is metadata, the store is bytes.
    assert by_id["index"].y + by_id["index"].h <= by_id["store"].y


def test_kinds_are_expected_set():
    kinds = {r.kind for r in ANATOMY.regions}
    assert kinds == EXPECTED_KINDS


# --- Presets & scenarios --------------------------------------------------------

def test_preset_ids_unique_and_pass_their_own_hard_rules():
    ids = [p.id for p in DATASET_PRESETS]
    assert len(ids) == len(set(ids))
    for p in DATASET_PRESETS:
        assert p.blurb.strip(), p.id
        s = Scenario(appliance=p.appliance, dataset=p.dataset, schedule=p.schedule)
        errors = [v for v in validate(s) if v.level == "error"]
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


def test_explain_entries_cover_the_key_readouts():
    ids = {e.id for e in EXPLAINS}
    assert {"dedupe-ratio", "novelty", "index-pressure", "backup-window"} <= ids
    for e in EXPLAINS:
        assert e.equation.strip() and e.explanation.strip(), e.id
        assert len(e.inputs) >= 3, f"{e.id}: causal chain too short"
