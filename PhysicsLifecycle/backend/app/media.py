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
    "telecomblocks": ProductMedia(
        name="Telecom Infrastructure Blocks", tagline="The absence of the compatibility matrix, sold as a bundle.",
        kind="illustration", shape="server", credit=ILLO,
    ),
    "circulardesign": ProductMedia(
        name="Circular Design", tagline="Four checkboxes, eight years of consequences.",
        kind="illustration", shape="laptop", credit=ILLO,
    ),
}
