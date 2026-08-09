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
    "vxrail": ProductMedia(
        name="VxRail", tagline="The lifecycle bundle is the product.",
        kind="illustration", shape="server", credit=ILLO,
    ),
    "privatecloud": ProductMedia(
        name="Dell Private Cloud", tagline="Two stacks, one pane, one invoice of hours.",
        kind="illustration", shape="console", credit=ILLO,
    ),
    "apex": ProductMedia(
        name="APEX", tagline="The demand curve's shape picks the winner.",
        kind="illustration", shape="console", credit=ILLO,
    ),
    "nativeedge": ProductMedia(
        name="NativeEdge", tagline="Half an hour of remote effort vs a day's site visit.",
        kind="illustration", shape="server", credit=ILLO,
    ),
    "automationstudio": ProductMedia(
        name="Automation Studio", tagline="The gate that makes the same mistake cheap.",
        kind="illustration", shape="console", credit=ILLO,
    ),
}
