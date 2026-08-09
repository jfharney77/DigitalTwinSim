"""Product media (V1/V9, physics_specs/VISUAL_IMPROVEMENTS.md):
credited photos or labeled facsimiles behind each product personality's
hero panel and picker card. Ship-safe assets or labeled illustrations
only; ``tests/test_media.py`` enforces the credit rule."""

from __future__ import annotations

from .models import CamelModel


class ProductMedia(CamelModel):
    name: str
    tagline: str
    kind: str
    src: str | None = None
    shape: str | None = None
    credit: str
    underlay: str | None = None
    caption: str | None = None


ILLO = "Repo-drawn silhouette (physics suite V1)"

MEDIA: dict[str, ProductMedia] = {
    "e3200": ProductMedia(
        name="PowerSwitch E3200", tagline="The same physics at human scale — and a PoE wallet.",
        kind="illustration", shape="switch", credit=ILLO,
    ),
    "sn6000": ProductMedia(
        name="PowerSwitch SN6000", tagline="Hash collisions, adaptive routing, and the optics bill.",
        kind="illustration", shape="switch", credit=ILLO,
    ),
    "x800": ProductMedia(
        name="Quantum-X800", tagline="Lossless by construction; the switches do the math.",
        kind="illustration", shape="switch", credit=ILLO,
    ),
}
