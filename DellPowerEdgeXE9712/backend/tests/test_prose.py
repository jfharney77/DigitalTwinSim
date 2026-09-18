"""The UI renders prose as plain text, so Markdown markers show up literally.

Emphasis like *is* or code spans like `gpusInDomain` read as stray symbols on
the page; keep every served string free of them at every reading level.
"""

import re

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
MARKUP = re.compile(r"\*[^*\s][^*]*\*|`")


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


@pytest.mark.parametrize("level", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("path", ["/api/anatomy", "/api/poweron", "/api/catalog", "/api/usecases", "/api/tour"])
def test_served_prose_has_no_markdown_markers(path, level):
    body = client.get(path, params={"level": level}).json()
    offenders = [s for s in _strings(body) if MARKUP.search(s)]
    assert offenders == []
