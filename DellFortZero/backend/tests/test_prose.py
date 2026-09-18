"""The UI renders every prose field as plain text, so markdown emphasis
(``*word*``) would reach the reader as literal asterisks. Checked at every
reading level, since each level is its own authored string."""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.main import app

MARKDOWN = re.compile(r"\*\S|\S\*|`")


def _strings(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)
    elif isinstance(obj, str):
        yield obj


@pytest.mark.parametrize("level", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("path", ["/api/access", "/api/anatomy", "/api/catalog", "/api/usecases"])
def test_served_prose_has_no_markdown_markers(path, level):
    body = TestClient(app).get(path, params={"level": level}).json()
    offenders = [s for s in _strings(body) if MARKDOWN.search(s)]
    assert offenders == [], offenders[:3]
