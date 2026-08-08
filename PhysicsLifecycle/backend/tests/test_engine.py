"""Full-trace invariants for the telecom & sustainability engine —
spec 08's mechanics as pytest: the integration bill, the heatwave
split, five-nines arithmetic, the closing carbon ledger, the sealed-vs-
serviceable A/B, and the honesty rule itself."""

from __future__ import annotations

from app.anatomy import MAPS
from app.constants import CONSTANTS, value as C
from app.engine import refurb_success, simulate
from app.models import Scenario, SimEvent
from app.presets import (
    BLOCKS,
    CLEAN,
    COAL,
    DIY,
    ROLLOUT,
    SEALED,
    SERVICEABLE,
    STANDARD_TEMP,
)

EIGHT_YEARS = 2920


def run(s: Scenario):
    return simulate(s)


def test_determinism():
    s = Scenario(config=SERVICEABLE, duration_d=EIGHT_YEARS)
    a, _, _ = run(s)
    b, _, _ = run(s)
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]


def test_carbon_constants_are_never_invented():
    """Spec 08's absolute rule: every carbon figure is a labeled
    estimate, and the PCF calibration path is stated."""
    carbon_names = [n for n in CONSTANTS if "kg" in CONSTANTS[n].unit.lower()]
    assert carbon_names, "the carbon table must exist"
    for n in carbon_names:
        assert CONSTANTS[n].estimated, f"{n}: carbon figures must be estimates"
        assert "estimate" in CONSTANTS[n].source.lower(), n
    assert "PCF" in CONSTANTS["embodied_kg"].source or \
        "PCF" in CONSTANTS["embodied_kg"].blurb


def test_diy_costs_hours_and_mismatches_blocks_does_not():
    _, _, blocks = run(Scenario(config=BLOCKS, duration_d=120, events=ROLLOUT))
    _, log, diy = run(Scenario(config=DIY, duration_d=120, events=ROLLOUT))
    assert diy.integration_hours > blocks.integration_hours * 4
    assert diy.mismatch_events >= 8, "every 12th of 100 sites fails validation"
    assert blocks.mismatch_events == 0
    assert diy.availability_pct < blocks.availability_pct
    assert any("mismatches" in e.message for e in log)


def test_heatwave_separates_the_fleets():
    heat = [SimEvent(at_d=60, action="heatwave", value=48)]
    xr_trace, xr_log, xr = run(Scenario(config=BLOCKS, duration_d=120, events=heat))
    st_trace, st_log, st = run(
        Scenario(config=STANDARD_TEMP, duration_d=120, events=heat)
    )
    assert xr.min_coverage_pct == 100.0, "the XR fleet rides it out"
    assert st.min_coverage_pct < 75.0, "~30% of the standard fleet goes dark"
    assert any("rides it out" in e.message for e in xr_log)
    assert any("dark" in e.message for e in st_log)
    # And the sites come back after repair.
    assert st_trace[-1].coverage_pct == 100.0


def test_bundle_update_with_spares_keeps_coverage():
    ev = [SimEvent(at_d=60, action="bundle-update")]
    _, _, spared = run(Scenario(config=BLOCKS, duration_d=120, events=ev))
    bare = BLOCKS.model_copy(update={"spare_capacity": False})
    _, _, piecemeal = run(Scenario(config=bare, duration_d=120, events=ev))
    assert spared.availability_pct > piecemeal.availability_pct, (
        "maintenance without slack spends the nines"
    )


def test_the_ledger_closes_every_tick():
    """total = embodied + use, exactly — the app's conservation law."""
    for cfg in (SERVICEABLE, SEALED, COAL):
        trace, _, _ = run(Scenario(config=cfg, duration_d=EIGHT_YEARS))
        for s in trace[::37]:
            assert abs(s.total_carbon_kg - (s.embodied_kg_cum + s.use_kg_cum)) \
                <= 0.21, f"t={s.t_d}"


def test_sealed_vs_serviceable_eight_years():
    _, _, good = run(Scenario(config=SERVICEABLE, duration_d=EIGHT_YEARS))
    _, log, bad = run(Scenario(config=SEALED, duration_d=EIGHT_YEARS))
    assert good.devices_consumed == 1, "parts, not replacements"
    assert bad.devices_consumed >= 3, "each event totals the sealed device"
    assert bad.carbon_per_useful_year > good.carbon_per_useful_year * 1.7
    assert bad.ewaste_kg > good.ewaste_kg
    assert bad.tco_usd > good.tco_usd
    assert any("whole-device replacement" in e.message for e in log)


def test_second_life_follows_the_screwdriver():
    _, log_g, good = run(Scenario(config=SERVICEABLE, duration_d=EIGHT_YEARS))
    _, log_b, bad = run(Scenario(config=SEALED, duration_d=EIGHT_YEARS))
    assert refurb_success(SERVICEABLE) >= 0.5
    assert refurb_success(SEALED) < 0.5
    assert good.got_second_life
    assert not bad.got_second_life
    assert any("second" in e.message for e in log_g)
    assert any("recycled" in e.message.lower() for e in log_b)


def test_grid_decides_which_phase_dominates():
    clean_t, _, _ = run(Scenario(config=CLEAN, duration_d=EIGHT_YEARS))
    coal_t, _, _ = run(Scenario(config=COAL, duration_d=EIGHT_YEARS))
    c = clean_t[-1]
    k = coal_t[-1]
    assert c.use_kg_cum < c.embodied_kg_cum * 0.2, (
        "clean grid: the factory dominates forever"
    )
    assert k.use_kg_cum > k.embodied_kg_cum, (
        "coal grid + heavy use: the socket overtakes the factory"
    )


def test_battery_year_two_prices():
    trace_g, log_g, _ = run(Scenario(config=SERVICEABLE, duration_d=1600))
    trace_s, log_s, _ = run(Scenario(config=SEALED, duration_d=1600))
    day = int(C("battery_wear_day"))
    before_g = next(s for s in trace_g if s.t_d == day - 1)
    after_g = next(s for s in trace_g if s.t_d == day + 1)
    delta_g = after_g.embodied_kg_cum - before_g.embodied_kg_cum
    before_s = next(s for s in trace_s if s.t_d == day - 1)
    after_s = next(s for s in trace_s if s.t_d == day + 1)
    delta_s = after_s.embodied_kg_cum - before_s.embodied_kg_cum
    assert abs(delta_g - C("battery_part_kg")) < 0.5
    assert delta_s > 200, "the sealed design pays the embodied carbon again"
    assert any("replaceable part" in e.message for e in log_g)
    assert any("wore out" in e.message for e in log_s)


def test_recycled_chassis_lowers_embodied():
    _, _, recycled = run(Scenario(config=SERVICEABLE, duration_d=100))
    virgin = SERVICEABLE.model_copy(update={"chassis_recycled": False})
    _, _, v = run(Scenario(config=virgin, duration_d=100))
    assert recycled.total_carbon_kg < v.total_carbon_kg


def test_region_load_matches_map():
    region_ids = {r.id for r in MAPS["telecomblocks"].regions}
    for cfg in (BLOCKS, SERVICEABLE):
        trace, _, _ = run(Scenario(config=cfg, duration_d=60))
        for s in trace:
            assert set(s.region_load.keys()) == region_ids, cfg.product


def test_engine_is_pure():
    import ast

    import app.engine as engine_module

    tree = ast.parse(open(engine_module.__file__, encoding="utf-8").read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & {
        "fastapi", "time", "asyncio", "threading", "os", "io", "random",
    }
