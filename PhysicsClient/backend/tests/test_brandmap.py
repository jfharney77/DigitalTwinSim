"""Invariants for the client-brand-map explainer (physics_specs/10 §8):
the 2025 scheme is complete, the prose is honestly labeled where the
sources are thin, the reading levels are real, and the page cross-links
the two narrative twins whose products it names."""

from __future__ import annotations

from app.brandmap import BRAND_MAP, BRANDS
from app.leveling import LEVELS, leveled


def test_the_four_brands_are_present_in_order():
    assert [b.id for b in BRANDS] == [
        "dell", "dell-pro", "dell-pro-max", "alienware",
    ]


def test_the_three_dell_brands_carry_the_tier_ladder():
    for b in BRANDS:
        if b.id == "alienware":
            # Deliberately outside the scheme — and the entry says so.
            assert b.tiers != ["Base", "Plus", "Premium"]
        else:
            assert b.tiers == ["Base", "Plus", "Premium"], b.id


def test_every_brand_names_what_it_replaced():
    formerly = {b.id: b.formerly for b in BRANDS}
    assert "Inspiron" in formerly["dell"] and "XPS" in formerly["dell"]
    assert "Latitude" in formerly["dell-pro"]
    assert "OptiPlex" in formerly["dell-pro"]
    assert "Precision" in formerly["dell-pro-max"]
    assert "unchanged" in formerly["alienware"].lower()


def test_pro_max_plus_is_placed_on_the_map():
    """The whole point of the page inside this app: 'Pro Max Plus' is
    the Plus tier of the workstation brand — the promax personality."""
    pm = next(b for b in BRANDS if b.id == "dell-pro-max")
    assert "Pro Max Plus" in pm.description


def test_unconfirmed_2026_claims_are_labeled_reported():
    """The `verify` discipline: the Pro Precision rename has thinner
    sourcing than the XPS revival and must say so."""
    assert "reported" in BRAND_MAP.since_note.lower()
    pm = next(b for b in BRANDS if b.id == "dell-pro-max")
    assert "reported" in pm.description.lower()


def test_cross_links_to_the_two_narrative_twins():
    labels = " ".join(s["label"] for s in BRAND_MAP.sources)
    assert "DellProMaxPlus" in labels
    assert "DellAlienware" in labels
    urls = [s["url"] for s in BRAND_MAP.sources]
    assert any("5186" in u for u in urls), "ProMaxPlus twin port"
    assert any("5176" in u for u in urls), "Alienware twin port"


def test_external_sources_cover_both_the_rebrand_and_the_reversal():
    urls = " ".join(s["url"] for s in BRAND_MAP.sources)
    assert "tomshardware" in urls or "techradar" in urls, "CES 2025 coverage"
    assert "windowscentral" in urls or "channelpro" in urls, "CES 2026 XPS revival"


def test_the_prose_is_leveled_and_total():
    for level in LEVELS:
        m = leveled(BRAND_MAP, level)
        assert m.overview.strip()
        assert m.naming_note.strip()
        assert m.since_note.strip()
        for b in m.brands:
            assert b.description.strip(), b.id
    assert leveled(BRAND_MAP, 1).overview != leveled(BRAND_MAP, 5).overview
