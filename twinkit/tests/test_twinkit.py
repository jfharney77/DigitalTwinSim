"""Invariants for the shared skeleton itself.

Everything here used to be true forty-two times over, once per component, and
was therefore only actually checked in the three components someone remembered
to update. It is checked once now.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from twinkit.api import make_app
from twinkit.leveling import LevelingConflict, make_leveling
from twinkit.models import CamelModel, camel
from twinkit.testing import TraceProfile, assert_engine_is_pure, assert_trace_invariants


# --- models -----------------------------------------------------------------

class _Region(CamelModel):
    region_id: str
    cycle_cost: int
    cores_per_sm: int = camel("coresPerSM", default=0)


def test_snake_case_in_python_camel_case_on_the_wire():
    dumped = _Region(region_id="cpu-a", cycle_cost=3).model_dump(by_alias=True)
    assert set(dumped) == {"regionId", "cycleCost", "coresPerSM"}


def test_an_explicit_alias_beats_the_generator():
    """``to_camel`` would give ``coresPerSm``; the TS types want ``coresPerSM``.
    This is the repo's oldest cross-cutting gotcha, pinned in one place."""
    assert "coresPerSM" in _Region.model_json_schema()["properties"]


def test_populate_by_name_so_python_construction_still_works():
    assert _Region(region_id="x", cycle_cost=1).region_id == "x"


# --- the shared app ---------------------------------------------------------

def test_health_exists_and_answers_the_shape_the_liveness_chips_expect():
    client = TestClient(make_app(title="T", frontend_port=5173))
    assert client.get("/api/health").json() == {"status": "ok"}


def test_levels_publishes_the_scale_so_the_ui_does_not_hard_code_it():
    body = TestClient(make_app(title="T", frontend_port=5173)).get("/api/levels").json()
    assert body["default"] == 3
    assert [entry["level"] for entry in body["levels"]] == [1, 2, 3, 4, 5]


def test_health_can_be_suppressed_for_a_component_that_answers_it_richly():
    app = make_app(title="T", frontend_port=5173, health=False)
    assert "/api/health" not in {route.path for route in app.routes}


def test_cors_opens_both_localhost_spellings_on_every_declared_port():
    app = make_app(title="T", frontend_port=(5173, 5174))
    origins = next(
        m.kwargs["allow_origins"] for m in app.user_middleware if "allow_origins" in m.kwargs
    )
    assert set(origins) == {
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
    }


# --- leveling ---------------------------------------------------------------

def test_a_component_registry_is_its_own():
    """Two components whose level-3 prose matches byte-for-byte must not
    collide now that a root pytest imports all of them into one process."""
    one, two = make_leveling("one"), make_leveling("two")
    one.L(standard="The power supplies energize.", novice="The plugs wake up.")
    two.L(standard="The power supplies energize.", novice="Something else.")
    assert one.variant_for("The power supplies energize.", 1) == "The plugs wake up."
    assert two.variant_for("The power supplies energize.", 1) == "Something else."


def test_conflicting_variants_within_one_component_still_raise():
    ns = make_leveling("x")
    ns.L(standard="same", novice="a")
    with pytest.raises(LevelingConflict):
        ns.L(standard="same", novice="b")


def test_L_returns_the_standard_text_unchanged():
    """Dropping ``L(...)`` from any call site has to stay a safe edit."""
    ns = make_leveling("x")
    assert ns.L(standard="plain text", expert="dense text") == "plain text"


def test_ties_break_away_from_the_standard_register():
    ns = make_leveling("x")
    ns.L(standard="s", novice="n")
    assert ns.variant_for("s", 2) == "n"
    ns.L(standard="t", expert="e")
    assert ns.variant_for("t", 4) == "e"


def test_unregistered_text_reads_the_same_at_every_level():
    ns = make_leveling("x")
    assert all(ns.variant_for("never wrapped", level) == "never wrapped" for level in range(1, 6))


def test_the_registry_is_bounded():
    ns = make_leveling("x")
    ns.max_registered = 2
    for i in range(5):
        ns.L(standard=f"block {i}", novice="n")
    assert len(ns.registry()) == 2


# --- trace invariants -------------------------------------------------------

class _State:
    def __init__(self, step, phase, elapsed_seconds, active_regions=(), cycle_cost=1):
        self.step = step
        self.phase = phase
        self.elapsed_seconds = elapsed_seconds
        self.active_regions = list(active_regions)
        self.cycle_cost = cycle_cost


PHASES = ["off", "power", "ready"]
PROFILE = TraceProfile(phases=PHASES, region_ids={"psu", "cpu"})


def _good_trace():
    return [
        _State(0, "off", 0),
        _State(1, "power", 5, ["psu"], cycle_cost=4),
        _State(2, "ready", 9, ["psu", "cpu"]),
    ]


def test_a_well_formed_trace_passes():
    assert_trace_invariants(_good_trace(), PROFILE)


@pytest.mark.parametrize(
    "break_it, expected",
    [
        (lambda t: t.__setitem__(1, _State(7, "power", 5)), "sequential"),
        (lambda t: setattr(t[2], "phase", "off"), "regressed"),
        (lambda t: setattr(t[2], "elapsed_seconds", 5), "did not advance"),
        (lambda t: setattr(t[1], "active_regions", ["nope"]), "unknown region"),
        (lambda t: setattr(t[1], "cycle_cost", 0), "cycle_cost"),
    ],
)
def test_each_invariant_fails_loudly_and_names_the_step(break_it, expected):
    trace = _good_trace()
    break_it(trace)
    with pytest.raises(AssertionError, match=expected):
        assert_trace_invariants(trace, PROFILE)


def test_a_phase_nobody_reaches_is_a_phase_nobody_tested():
    trace = _good_trace()[:2]
    with pytest.raises(AssertionError, match="never reached"):
        assert_trace_invariants(trace, PROFILE)


def test_region_ids_can_come_from_an_anatomy_object():
    class _Anatomy:
        regions = [type("R", (), {"id": "psu"})(), type("R", (), {"id": "cpu"})()]

    assert_trace_invariants(_good_trace(), TraceProfile(phases=PHASES, anatomy=_Anatomy()))


def test_purity_check_reads_the_source_not_sys_modules():
    """An engine importing ``time`` inside a function would pass a
    sys.modules check and still be able to put a clock in the trace."""
    import twinkit.testing as pure_module

    assert_engine_is_pure(pure_module, also_ban=())  # imports ast/dataclasses only

    import twinkit.api as impure_module

    with pytest.raises(AssertionError, match="fastapi"):
        assert_engine_is_pure(impure_module)
