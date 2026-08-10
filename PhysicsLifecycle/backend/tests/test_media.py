"""V1/V9 media contract: every product has an entry, every entry has a
credit, illustrations never masquerade as photos, and referenced asset
files actually exist in frontend/public."""

from __future__ import annotations

from pathlib import Path
from typing import get_args

from app.media import MEDIA
from app.models import Product

PUBLIC = Path(__file__).resolve().parents[2] / "frontend" / "public"


def test_every_product_has_media():
    assert set(MEDIA) == set(get_args(Product))


def test_credit_is_mandatory_and_kinds_are_honest():
    for pid, m in MEDIA.items():
        assert m.credit.strip(), pid
        assert m.kind in ("photo", "illustration"), pid
        if m.kind == "photo":
            assert m.src, f"{pid}: a photo entry must reference an asset"
        else:
            assert m.shape, f"{pid}: an illustration entry needs a silhouette"
            assert m.src is None, f"{pid}: illustrations are drawn, not files"


def test_referenced_assets_exist_and_are_local():
    for pid, m in MEDIA.items():
        for ref in (m.src, m.underlay):
            if ref:
                assert ref.startswith("/"), f"{pid}: assets must be local"
                assert (PUBLIC / ref.lstrip("/")).exists(), (pid, ref)


def test_compare_pairs_resolve():
    """V8: every declared A/B foil names a real preset (and never itself)."""
    from app.presets import CONFIG_PRESETS

    ids = {p.id for p in CONFIG_PRESETS}
    declared = [p for p in CONFIG_PRESETS if p.compare_preset_id]
    assert declared, "at least one canonical foil pair must exist"
    for p in declared:
        assert p.compare_preset_id in ids, (p.id, p.compare_preset_id)
        assert p.compare_preset_id != p.id
