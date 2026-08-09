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
    "aidataplatform": ProductMedia(
        name="Dell AI Data Platform", tagline="min(stages) — and the GPUs grade the pipeline.",
        kind="illustration", shape="rack", credit=ILLO,
    ),
    "cloudiq": ProductMedia(
        name="CloudIQ / APEX AIOps", tagline="The console whose tuning gets a report card.",
        kind="illustration", shape="console", credit=ILLO,
    ),
}
