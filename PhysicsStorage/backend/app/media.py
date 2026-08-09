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
    "powerstore": ProductMedia(
        name="PowerStore", tagline="The dual-controller knee, found and moved.",
        kind="photo", src="/powerstore1.webp",
        credit="Dell Technologies product image",
        underlay="/powerstore2.webp",
    ),
    "powermax": ProductMedia(
        name="PowerMax", tagline="Blip, not outage — and replication at the speed of light.",
        kind="illustration", shape="rack", credit=ILLO,
    ),
    "powerscale": ProductMedia(
        name="PowerScale", tagline="Rebuilds that get faster as the cluster grows.",
        kind="illustration", shape="storage", credit=ILLO,
    ),
    "objectscale": ProductMedia(
        name="ObjectScale", tagline="S3 at archive scale; deletes bounce off WORM.",
        kind="illustration", shape="storage", credit=ILLO,
    ),
    "powerflex": ProductMedia(
        name="PowerFlex", tagline="The network IS the array.",
        kind="illustration", shape="server", credit=ILLO,
    ),
    "exascale": ProductMedia(
        name="Exascale", tagline="Partition one rack; the GPUs grade the split.",
        kind="illustration", shape="rack", credit=ILLO,
    ),
}
