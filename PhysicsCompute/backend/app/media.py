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
    "xe7745": ProductMedia(
        name="PowerEdge XE7745", tagline="Eight PCIe GPUs, unequal seats — air-cooled density.",
        kind="illustration", shape="server", credit=ILLO,
    ),
    "xe9680": ProductMedia(
        name="PowerEdge XE9680", tagline="Eight SXM GPUs, one thermal fate — the flagship trainer.",
        kind="illustration", shape="server", credit=ILLO,
    ),
    "xe9712": ProductMedia(
        name="PowerEdge XE9712 + IR7000", tagline="The rack is the machine; the heat leaves in water.",
        kind="illustration", shape="rack", credit=ILLO,
    ),
}
