"""Integrity checks for the catalog and use cases: ids unique, region
references real, and every use-case config line resolves to a real option."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.catalog import CATALOG
from app.usecases import USE_CASES


def test_category_ids_unique():
    ids = [c.id for c in CATALOG]
    assert len(ids) == len(set(ids))


def test_option_ids_unique_across_catalog():
    ids = [o.id for c in CATALOG for o in c.options]
    assert len(ids) == len(set(ids))


def test_region_ids_are_real_anatomy_regions():
    region_ids = {r.id for r in ANATOMY.regions}
    for cat in CATALOG:
        for rid in cat.region_ids:
            assert rid in region_ids, f"{cat.id}: unknown region {rid!r}"


def test_categories_have_content():
    for cat in CATALOG:
        assert cat.options, f"{cat.id} has no options"
        assert cat.blurb and cat.limits
        for opt in cat.options:
            assert opt.summary and opt.details


def test_use_case_configs_reference_real_options():
    by_category = {c.id: {o.id for o in c.options} for c in CATALOG}
    for uc in USE_CASES:
        for item in uc.config:
            assert item.category_id in by_category, (
                f"{uc.id}: unknown category {item.category_id!r}"
            )
            assert item.option_id in by_category[item.category_id], (
                f"{uc.id}: option {item.option_id!r} not in {item.category_id!r}"
            )


def test_use_case_quantities_positive():
    for uc in USE_CASES:
        assert all(item.qty >= 1 for item in uc.config)


def test_use_cases_have_narrative_and_rationale():
    ids = [uc.id for uc in USE_CASES]
    assert len(ids) == len(set(ids))
    for uc in USE_CASES:
        assert len(uc.narrative) >= 2, f"{uc.id}: needs >=2 narrative paragraphs"
        assert uc.config, f"{uc.id}: empty config"
        assert all(item.rationale for item in uc.config)
