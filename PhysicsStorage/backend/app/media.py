"""Product media (V1/V9, physics_specs/VISUAL_IMPROVEMENTS.md):
credited photos or labeled facsimiles behind each product personality's
hero panel and picker card. Ship-safe assets or labeled illustrations
only; ``tests/test_media.py`` enforces the credit rule."""

from __future__ import annotations

from .leveling import L
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
        caption=L(
            novice=(
                "The photograph is the appliance's real front: "
                "twenty-five drive slots and two controller canisters "
                "behind them. The diagram over it is not a picture of "
                "that metal — it is a map of where the work happens: "
                "two controllers, a cache, a shelf of media. The "
                "simulator's claims are about the map; the photo is "
                "what the map is loyal to."
            ),
            standard=(
                "The schematic is an architecture map (controllers, "
                "cache, media), not a chassis trace — the photo behind "
                "it shows the machine the map abstracts. The x-ray "
                "toggle keeps the difference visible."
            ),
            expert=(
                "Architecture map over chassis photo. Abstraction, "
                "labeled."
            ),
        ),
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
