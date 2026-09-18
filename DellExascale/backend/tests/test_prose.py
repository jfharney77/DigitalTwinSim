"""Served prose is rendered as plain text, so it must carry no markdown.

The UI prints every description verbatim; a `*layout*` in the data showed up
on screen with its asterisks. Emphasis is also off-limits under the
dell-clean-design skin (no highlighted text), so the words carry it alone.
"""

import re

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
MARKDOWN_EMPHASIS = re.compile(r"(?<![\w*])\*{1,2}\w[^*\n]*\*{1,2}(?![\w*])")


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)


@pytest.mark.parametrize("path", ["/api/anatomy", "/api/datapath", "/api/catalog", "/api/usecases", "/api/tour"])
@pytest.mark.parametrize("level", [1, 2, 3, 4, 5])
def test_served_prose_has_no_markdown_emphasis(path, level):
    res = client.get(path, params={"level": level})
    assert res.status_code == 200
    bad = [s for s in _strings(res.json()) if MARKDOWN_EMPHASIS.search(s)]
    assert bad == [], f"markdown emphasis in {path}?level={level}: {bad[:3]}"
