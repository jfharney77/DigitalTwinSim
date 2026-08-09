"""Full-trace invariants for the display engine: the power-balance and
heat-vs-delivery identities every tick, carbon closure, and the spec's
acceptance behaviors (dark-content savings are architecture-dependent;
HDR bursts past SDR peaks; the hub dominates the nameplate)."""

from __future__ import annotations

from app.anatomy import ANATOMY  # noqa: F401  (imported for leveling side effect)
from app.constants import value as C
from app.engine import DT, simulate
from app.models import DisplayConfig, Lifecycle, Scenario, SimEvent
from app.presets import EDGE, MINILED

ROUND_TOL = 0.5


def run(scenario: Scenario):
    return simulate(scenario)


def test_determinism():
    s = Scenario(config=MINILED)
    a, _, _ = run(s)
    b, _, _ = run(s)
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]


def test_power_balance_every_tick():
    """THE identity: electronics + backlight + hub delivered + hub loss
    == DC, and AC == DC / PSU efficiency, on every tick."""
    for cfg in (EDGE, MINILED,
                EDGE.model_copy(update={"hub_laptop_w": 65}),
                MINILED.model_copy(update={"content": "hdr"})):
        trace, _, _ = run(Scenario(config=cfg))
        for s in trace:
            parts = s.electronics_w + s.backlight_w + s.hub_out_w + s.hub_loss_w
            assert abs(parts - s.dc_power_w) <= ROUND_TOL, f"t={s.t}"
            if s.on:
                assert abs(s.ac_power_w - s.dc_power_w / C("psu_efficiency")) <= 1.0
                assert s.ac_power_w > s.dc_power_w, "conversion loss must exist"


def test_heat_is_dc_minus_delivery():
    cfg = EDGE.model_copy(update={"hub_laptop_w": 90})
    trace, _, _ = run(Scenario(config=cfg))
    for s in trace:
        assert abs(s.heat_w - (s.dc_power_w - s.hub_out_w)) <= ROUND_TOL
    s = trace[-1]
    assert s.hub_loss_w > 0, "delivering 90 W is not free"
    assert s.heat_w < s.dc_power_w, "delivered watts must leave the box"


def test_dark_content_saves_on_miniled_not_on_edge():
    """The app's reason for existing: same brightness, dark vs bright
    content — a material saving on the zoned panel, none on the strip."""
    def steady_w(cfg):
        trace, _, _ = run(Scenario(config=cfg, duration_s=60))
        return trace[-1].ac_power_w

    mini_dark = steady_w(MINILED.model_copy(update={"content": "dark"}))
    mini_bright = steady_w(MINILED.model_copy(update={"content": "bright"}))
    edge_dark = steady_w(EDGE.model_copy(update={"content": "dark"}))
    edge_bright = steady_w(EDGE.model_copy(update={"content": "bright"}))

    assert mini_bright - mini_dark > 15, "FALD must save real watts on dark content"
    assert abs(edge_bright - edge_dark) < 0.5, "the strip cannot dim locally"


def test_dimming_off_makes_the_miniled_behave_edge_lit():
    on = run(Scenario(config=MINILED.model_copy(update={"content": "dark"})))[0][-1]
    off = run(Scenario(config=MINILED.model_copy(
        update={"content": "dark", "local_dimming": False})))[0][-1]
    assert off.backlight_w > on.backlight_w * 2
    assert off.lit_fraction == 1.0 and on.lit_fraction < 0.2


def test_hdr_burst_exceeds_sdr_peak():
    for base in (EDGE.model_copy(update={"local_dimming": False}), MINILED):
        sdr = run(Scenario(config=base.model_copy(
            update={"content": "bright", "brightness_pct": 100})))[0][-1]
        hdr = run(Scenario(config=base.model_copy(
            update={"content": "hdr", "brightness_pct": 100})))[0][-1]
        assert hdr.backlight_w > sdr.backlight_w, base.model


def test_brightness_is_monotone_in_power():
    watts = []
    for b in (0, 25, 50, 75, 100):
        trace, _, _ = run(Scenario(config=EDGE.model_copy(
            update={"brightness_pct": b}), duration_s=30))
        watts.append(trace[-1].ac_power_w)
    assert watts == sorted(watts)
    assert watts[0] > 0, "the electronics floor keeps 0% brightness above zero"


def test_standby_and_wake():
    trace, log, _ = run(Scenario(
        config=EDGE, duration_s=200,
        events=[SimEvent(at_s=60, action="standby"),
                SimEvent(at_s=140, action="wake")],
    ))
    asleep = [s for s in trace if not s.on]
    assert asleep and all(s.ac_power_w == C("standby_w") for s in asleep)
    assert all(s.zones_lit == 0 and s.backlight_w == 0 for s in asleep)
    assert trace[-1].on
    assert any("standby" in e.message.lower() for e in log)


def test_hub_plug_jumps_wall_not_heat():
    trace, log, _ = run(Scenario(
        config=EDGE, duration_s=200,
        events=[SimEvent(at_s=60, action="hub-plug", value=90)],
    ))
    before = trace[50]
    after = trace[-1]
    assert after.ac_power_w - before.ac_power_w > 90, "delivery + losses at the wall"
    assert after.heat_w - before.heat_w < 15, "but the room barely notices"
    assert any("docked" in e.message.lower() for e in log)


def test_carbon_closure():
    """Embodied + use == lifetime, shares sum to 100 — the Circular
    Design closure rule, one product at a time."""
    for cfg in (EDGE, MINILED):
        _, _, summary = run(Scenario(config=cfg))
        c = summary.carbon
        assert abs(c.embodied_kg + c.use_kg - c.lifetime_kg) <= 0.11
        assert abs(c.embodied_pct + c.use_pct - 100.0) <= 0.11
        assert c.embodied_kg > 0 and c.use_kg > 0


def test_monitor_use_share_beats_laptop_use_share():
    """The embodied-carbon surprise: at desk duty the monitor's use-phase
    share materially exceeds a business laptop's ~20%."""
    _, _, summary = run(Scenario(config=EDGE, lifecycle=Lifecycle()))
    assert summary.carbon.use_pct > C("laptop_use_pct")


def test_heavy_duty_tilts_toward_use_phase():
    desk = run(Scenario(config=EDGE))[2].carbon
    signage = run(Scenario(config=EDGE, lifecycle=Lifecycle(
        hours_per_day=16, days_per_year=360, service_years=8)))[2].carbon
    assert signage.use_pct > desk.use_pct


def test_zones_track_content_on_miniled_only():
    mini = run(Scenario(config=MINILED.model_copy(update={"content": "dark"})))[0][-1]
    edge = run(Scenario(config=EDGE))[0][-1]
    assert 0 < mini.zones_lit < C("mini_zones") * 0.2
    assert edge.zones_lit == 0


def test_timestep_and_trace_length():
    trace, _, _ = run(Scenario(config=EDGE, duration_s=120))
    assert len(trace) == int(120 / DT) + 1
    assert [x.t for x in trace] == sorted(x.t for x in trace)


def test_engine_is_pure():
    """No FastAPI/IO/time/random in the engine — same rule as every twin."""
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
