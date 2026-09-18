"""Narrated tour mode: the shared data model and its pure helpers.

A tour is a video-like walk through a twin — a camera that moves across and
into the map, layers that peel away, regions that light, and a narration track
— driven entirely by data served next to the anatomy (``ACTIVE_TWIN_SPEC.md``
sections 3–6). The engine and its trace are untouched: a step may *pin* the
existing trace cursor, and the frontend player, which owns the clock, drives
that cursor. Nothing here imports anything impure, so a component's
``tour.py`` built on it passes the same AST purity check as its engine.

    twinkit.tour      CameraTarget, TourStep, TourPhoto, TourSource, Tour,
                      TourResponse, camera_around(), whole_map(), ...
    twinkit.testing   assert_tour_invariants()

**Layers are not part of the anatomy wire model.** Each component's
``tour.py`` carries a ``region id -> layer`` mapping (0 = the outside of the
product, higher = further in) and the endpoint returns it inside
:class:`TourResponse`. The map models of 42 components stay as they are.

**Narration prose is leveled like every other prose block.** Wrap each
``script`` in the component's ``L(...)``; ``GET /api/tour`` resolves it with
``leveled(...)`` the same way ``/api/anatomy`` does. Titles are short labels
and are usually left unwrapped.
"""

from __future__ import annotations

import math
from typing import Any, Iterable

from pydantic import Field

from .models import CamelModel

__all__ = [
    "CameraTarget",
    "TourStep",
    "TourPhoto",
    "TourSource",
    "Tour",
    "TourResponse",
    "whole_map",
    "camera_around",
    "boxes_overlap",
    "camera_travel",
    "total_duration_ms",
    "step_ids",
    "region_boxes",
]


class CameraTarget(CamelModel):
    """A viewBox in the anatomy's own normalized coordinate space.

    The frontend adds whatever margin its renderer draws around the map; the
    tour never needs to know about it. Test-enforced: inside the map bounds,
    positive area.
    """

    x: float
    y: float
    w: float
    h: float


class TourStep(CamelModel):
    """One beat of the tour."""

    #: Stable, kebab-case. Deep links (``#tour/<id>``) and the optional
    #: pre-rendered audio file key on it; renaming one breaks both.
    id: str
    #: Short beat title for the step list. No numbering — a list of titles.
    title: str
    #: Narration text, which is also the caption. Spell vocabulary out on first
    #: use. Wrap it in the component's ``L(...)``.
    script: str
    camera: CameraTarget
    #: Regions lit while the step plays; every id must resolve on the map.
    region_ids: list[str] = Field(default_factory=list)
    #: 0 = the whole product; N = regions on layers below N become ghosts.
    layer_reveal: int = 0
    #: Pin the simulation trace to this index while the step plays.
    trace_cursor: int | None = None
    #: How long the step holds when there is no audio to time it (tiers 0/1).
    duration_ms: int
    #: Optional credited photo shown with the step (an id into ``Tour.photos``).
    photo_id: str | None = None
    #: Optional pre-rendered narration (tier 2). Not used by the pilot.
    audio_url: str | None = None


class TourPhoto(CamelModel):
    """A local, credited photo a step may show. ``credit`` is always rendered."""

    id: str
    url: str
    caption: str
    credit: str


class TourSource(CamelModel):
    label: str
    url: str


class Tour(CamelModel):
    id: str
    title: str
    intro: str
    steps: list[TourStep]
    photos: list[TourPhoto] = Field(default_factory=list)
    sources: list[TourSource] = Field(default_factory=list)


class TourResponse(CamelModel):
    """What ``GET /api/tour`` returns.

    ``layers`` maps every region id to its layer. It rides with the tour rather
    than on the anatomy so no component's map model has to change.
    ``map_width``/``map_height`` are the bounds the camera boxes live in, so the
    player can frame the whole map without a second request.
    """

    tour: Tour
    layers: dict[str, int]
    map_width: float
    map_height: float


# --- pure helpers -----------------------------------------------------------

def _items(anatomy: Any) -> list[Any]:
    for attr in ("regions", "blocks", "pillars", "areas"):
        items = getattr(anatomy, attr, None)
        if items:
            return list(items)
    raise ValueError("anatomy has no regions/blocks/pillars/areas list")


def region_boxes(anatomy: Any) -> dict[str, tuple[float, float, float, float]]:
    """``{region id: (x, y, w, h)}`` for any of the repo's map models."""
    return {r.id: (r.x, r.y, r.w, r.h) for r in _items(anatomy)}


def whole_map(anatomy: Any) -> CameraTarget:
    """The camera box that shows the entire map."""
    return CameraTarget(x=0, y=0, w=anatomy.width, h=anatomy.height)


def camera_around(
    anatomy: Any,
    region_ids: Iterable[str],
    pad: float = 3.0,
    aspect: float | None = None,
) -> CameraTarget:
    """Frame a set of regions: their bounding box, padded, clamped to the map.

    ``aspect`` (width / height) widens or heightens the box to match the
    renderer, defaulting to the map's own aspect so a zoom never distorts. The
    result always lies inside ``[0, width] x [0, height]``.
    """
    boxes = region_boxes(anatomy)
    ids = list(region_ids)
    if not ids:
        return whole_map(anatomy)
    missing = [i for i in ids if i not in boxes]
    if missing:
        raise KeyError(f"unknown region ids: {missing}")
    W, H = float(anatomy.width), float(anatomy.height)
    x0 = min(boxes[i][0] for i in ids) - pad
    y0 = min(boxes[i][1] for i in ids) - pad
    x1 = max(boxes[i][0] + boxes[i][2] for i in ids) + pad
    y1 = max(boxes[i][1] + boxes[i][3] for i in ids) + pad
    w, h = x1 - x0, y1 - y0
    ratio = aspect if aspect is not None else W / H
    if w / h < ratio:
        grow = h * ratio - w
        x0, w = x0 - grow / 2, w + grow
    else:
        grow = w / ratio - h
        y0, h = y0 - grow / 2, h + grow
    w, h = min(w, W), min(h, H)
    x0 = min(max(x0, 0.0), W - w)
    y0 = min(max(y0, 0.0), H - h)
    return CameraTarget(
        x=round(x0, 3), y=round(y0, 3), w=round(w, 3), h=round(h, 3)
    )


def boxes_overlap(a: CameraTarget, b: CameraTarget) -> bool:
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h


def camera_travel(a: CameraTarget, b: CameraTarget) -> float:
    """Distance between two boxes' centres, plus the change in their size.

    What a viewer perceives as camera movement is both the pan and the zoom,
    so the size change counts too.
    """
    pan = math.hypot((a.x + a.w / 2) - (b.x + b.w / 2), (a.y + a.h / 2) - (b.y + b.h / 2))
    zoom = abs(a.w - b.w) + abs(a.h - b.h)
    return pan + zoom


def total_duration_ms(tour: Tour) -> int:
    return sum(step.duration_ms for step in tour.steps)


def step_ids(tour: Tour) -> list[str]:
    return [step.id for step in tour.steps]
