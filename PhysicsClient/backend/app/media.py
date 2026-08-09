"""Product media (V1/V9, physics_specs/VISUAL_IMPROVEMENTS.md): the
credited photo or labeled facsimile behind each product personality's
hero panel and picker card. Ground rules: ship-safe local assets or
labeled illustrations only; the credit line always ships with the
image, and ``tests/test_media.py`` enforces it."""

from __future__ import annotations

from .leveling import L
from .models import CamelModel


class ProductMedia(CamelModel):
    name: str
    tagline: str
    kind: str                    # "photo" | "illustration"
    src: str | None = None       # file served from frontend/public
    shape: str | None = None     # facsimile silhouette key
    credit: str
    underlay: str | None = None  # V2: map-underlay asset, if any
    caption: str | None = None   # V10: x-ray caption


MEDIA: dict[str, ProductMedia] = {
    "alienware": ProductMedia(
        name="Alienware",
        tagline="Burst, shared budget, skin cap — the gaming machines.",
        kind="photo",
        src="/alienware-interior.jpg",
        credit="Dell Alienware service photo",
        underlay="/alienware-interior.jpg",
        caption=L(
            novice=(
                "The photograph shows the real machine with its bottom "
                "cover off — hundreds of visible parts, screws, cables, "
                "and copper. The colored schematic on top of it shows "
                "what the simulator actually reasons about: nine thermal "
                "zones. Everything the model says is true of the zones; "
                "the photograph is what those zones stand for."
            ),
            standard=(
                "The model sees nine thermal zones where the camera sees "
                "hundreds of parts. The schematic is a functional map, "
                "not a photo trace — the x-ray view exists to keep that "
                "abstraction honest."
            ),
            expert=(
                "Nine zones vs the parts they abstract. Map, not "
                "territory — shown."
            ),
        ),
    ),
    "promax": ProductMedia(
        name="Dell Pro Max Plus",
        tagline="The workstation with the discrete NPU — tokens per joule.",
        kind="illustration",
        shape="laptop",
        credit="Repo-drawn silhouette (physics suite V1)",
    ),
}
