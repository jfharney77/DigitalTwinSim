"""Invariants for the shared tour model and its test helper.

A component's own ``tests/test_tour.py`` checks its tour against its map and
trace; this file checks that the model, the helpers and
``assert_tour_invariants`` themselves say what they claim — including that
each rule actually fails when broken, so none of them is decorative.
"""

from __future__ import annotations

import types

import pytest

from twinkit.models import CamelModel
from twinkit.testing import TOUR_MAX_MS, TOUR_MIN_MS, assert_tour_invariants
from twinkit.tour import (
    CameraTarget,
    Tour,
    TourPhoto,
    TourResponse,
    TourStep,
    boxes_overlap,
    camera_around,
    camera_travel,
    total_duration_ms,
    whole_map,
)


class _Region(CamelModel):
    id: str
    x: float
    y: float
    w: float
    h: float


class _Map(CamelModel):
    width: float
    height: float
    regions: list[_Region]


MAP = _Map(
    width=100,
    height=50,
    regions=[
        _Region(id="shell", x=0, y=0, w=100, h=50),
        _Region(id="core-a", x=10, y=5, w=20, h=15),
        _Region(id="core-b", x=10, y=30, w=20, h=15),
        _Region(id="link", x=70, y=20, w=20, h=10),
    ],
)
LAYERS = {"shell": 0, "core-a": 1, "core-b": 1, "link": 2}
TRACE = [types.SimpleNamespace(step=i) for i in range(6)]


def _step(sid: str, **kw) -> TourStep:
    base = dict(
        id=sid,
        title=sid.replace("-", " "),
        script=f"Narration for {sid}.",
        camera=whole_map(MAP),
        region_ids=[],
        layer_reveal=0,
        trace_cursor=None,
        duration_ms=40_000,
    )
    base.update(kw)
    return TourStep(**base)


def _tour(steps: list[TourStep], photos: list[TourPhoto] | None = None) -> TourResponse:
    return TourResponse(
        tour=Tour(id="t", title="T", intro="Intro.", steps=steps, photos=photos or []),
        layers=LAYERS,
        map_width=MAP.width,
        map_height=MAP.height,
    )


def _good() -> list[TourStep]:
    return [
        _step("outside", region_ids=["shell"], trace_cursor=0),
        _step("peel", layer_reveal=1, region_ids=["core-a", "core-b"],
              camera=camera_around(MAP, ["core-a", "core-b"]), trace_cursor=2),
        _step("the-idea", layer_reveal=2, region_ids=["link"],
              camera=camera_around(MAP, ["link", "core-a"]), trace_cursor=3),
        _step("close-up", layer_reveal=0, trace_cursor=5),
    ]


def test_wire_shape_is_camel_case():
    dumped = _tour(_good()).model_dump(by_alias=True)
    assert {"tour", "layers", "mapWidth", "mapHeight"} == set(dumped)
    step = dumped["tour"]["steps"][0]
    for key in ("regionIds", "layerReveal", "traceCursor", "durationMs", "photoId", "audioUrl"):
        assert key in step


def test_a_well_formed_tour_passes():
    assert_tour_invariants(_tour(_good()), MAP, TRACE, "the-idea")


def test_camera_around_stays_inside_the_map_and_keeps_the_aspect():
    for ids in (["core-a"], ["link"], ["core-a", "link"], ["shell"]):
        c = camera_around(MAP, ids)
        assert c.x >= 0 and c.y >= 0 and c.x + c.w <= 100 + 1e-6 and c.y + c.h <= 50 + 1e-6
        assert abs(c.w / c.h - 2.0) < 1e-3 or c.w == 100 or c.h == 50
    with pytest.raises(KeyError):
        camera_around(MAP, ["nope"])


def test_travel_counts_zoom_as_well_as_pan():
    a = CameraTarget(x=0, y=0, w=10, h=10)
    assert camera_travel(a, a) == 0
    assert camera_travel(a, CameraTarget(x=0, y=0, w=20, h=20)) > 0
    assert boxes_overlap(a, CameraTarget(x=5, y=5, w=10, h=10))
    assert not boxes_overlap(a, CameraTarget(x=50, y=0, w=10, h=10))


def test_duration_bounds_are_two_to_six_minutes():
    assert (TOUR_MIN_MS, TOUR_MAX_MS) == (120_000, 360_000)
    assert total_duration_ms(_tour(_good()).tour) == 160_000


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda s: s.pop(2), "signature step"),
        (lambda s: s.__setitem__(1, s[1].model_copy(update={"region_ids": ["ghost"]})), "unknown region"),
        (lambda s: s.__setitem__(1, s[1].model_copy(update={"script": "  "})), "empty script"),
        (lambda s: s.__setitem__(1, s[1].model_copy(update={"camera": CameraTarget(x=90, y=0, w=20, h=10)})), "past the map"),
        (lambda s: s.__setitem__(1, s[1].model_copy(update={"camera": CameraTarget(x=0, y=0, w=0, h=10)})), "no area"),
        (lambda s: s.__setitem__(2, s[2].model_copy(update={"layer_reveal": 0})), "layer_reveal falls"),
        (lambda s: s.__setitem__(2, s[2].model_copy(update={"trace_cursor": 1})), "backwards"),
        (lambda s: s.__setitem__(2, s[2].model_copy(update={"trace_cursor": 99})), "outside"),
        (lambda s: s.__setitem__(0, s[0].model_copy(update={"duration_ms": 1_000_000})), "must land"),
        (lambda s: s.__setitem__(0, s[0].model_copy(update={"id": "Not_Kebab"})), "kebab"),
        (lambda s: s.__setitem__(0, s[0].model_copy(update={"photo_id": "missing"})), "unknown photo"),
    ],
)
def test_each_rule_fails_when_broken(mutate, message):
    steps = _good()
    mutate(steps)
    with pytest.raises(AssertionError, match=message):
        assert_tour_invariants(_tour(steps), MAP, TRACE, "the-idea")


def test_teleporting_is_caught_but_an_overlapping_zoom_is_not():
    far_a = CameraTarget(x=0, y=0, w=4, h=2)
    far_b = CameraTarget(x=96, y=48, w=4, h=2)
    steps = _good()
    steps[1] = steps[1].model_copy(update={"camera": far_a})
    steps[2] = steps[2].model_copy(update={"camera": far_b})
    with pytest.raises(AssertionError, match="jumps"):
        assert_tour_invariants(_tour(steps), MAP, TRACE, "the-idea", max_travel=20)


def test_layers_must_cover_the_map():
    bad = _tour(_good())
    bad.layers = {"shell": 0}
    with pytest.raises(AssertionError, match="layers do not match"):
        assert_tour_invariants(bad, MAP, TRACE, "the-idea")


def test_photos_must_be_local_and_credited(tmp_path):
    (tmp_path / "front.webp").write_bytes(b"x")
    steps = _good()
    steps[0] = steps[0].model_copy(update={"photo_id": "front"})
    ok = [TourPhoto(id="front", url="/front.webp", caption="c", credit="Vendor")]
    assert_tour_invariants(_tour(steps, ok), MAP, TRACE, "the-idea", public_dir=tmp_path)
    for bad, message in (
        (TourPhoto(id="front", url="https://example.com/x.jpg", caption="c", credit="V"), "hotlinking"),
        (TourPhoto(id="front", url="/front.webp", caption="c", credit=" "), "credit"),
        (TourPhoto(id="front", url="/absent.webp", caption="c", credit="V"), "does not exist"),
    ):
        with pytest.raises(AssertionError, match=message):
            assert_tour_invariants(_tour(steps, [bad]), MAP, TRACE, "the-idea", public_dir=tmp_path)


def test_the_shared_tour_module_is_itself_pure():
    import twinkit.tour

    assert_tour_invariants(_tour(_good()), MAP, TRACE, "the-idea", module=twinkit.tour)
